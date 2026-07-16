"""meta.yaml (v0) non-rendering extraction (Story 2.2) — parse-as-data
ONLY, never rendered. Unlike v1's ``context:`` block, v0's ``{% set NAME =
VALUE %}`` tags, other ``{% ... %}`` statement tags, and ``{# ... #}``
comment spans are NOT valid YAML — they must be regex-captured/stripped
BEFORE ``yaml.safe_load`` runs, WHEREVER on a line they appear (a whole-line-
only anchor missed same-line multi-statement Jinja and a tag/comment sharing
a line with other content — fixed 2026-07-16, see ``_JINJA_SPAN_RE``). A
bare (un-``$``-prefixed) ``{{ VAR }}`` at the START of a YAML scalar is
ALSO not safely parseable as-is (a leading ``{`` triggers YAML flow-mapping
detection — empirically confirmed: an unquoted ``- {{ pin_compatible(...)
}}`` list item raises a ``yaml.YAMLError``), so any such line is
defensively single-quoted BEFORE ``yaml.safe_load`` too. No ``jinja2``
import, no execution primitive (NFR-S1 — the ``extract/`` AST-denylist
meta-test covers this file automatically).

Ownership decisions recorded:

* **Two-pass neutralize-then-load** (Design Notes): (1) regex-capture
  every ``{% set NAME = "literal" %}``/``{% set NAME = 1.2 %}`` tag's
  RHS into a ``dict[str, str]`` and blank it (a captured literal is either
  a quoted string or a bare number — anything else, e.g. a function call
  RHS, is NOT captured, but the tag is still blanked so it never reaches
  ``yaml.safe_load`` as raw Jinja); every OTHER ``{% ... %}`` statement
  tag (``if``/``for``/``endif``/``endfor``/...) AND every ``{# ... #}``
  comment span is ALSO blanked — this is 2.2's common-case allowance: it
  makes a multi-line ``{% for %}`` block degrade to its individual
  (still-templated, still-degraded) list-item entries rather than
  crashing the WHOLE document's YAML parse, without attempting the full
  loop-expansion Story 2.3 owns. A single ``re.sub`` tokenizer pass over
  the WHOLE text (not line-by-line) finds and blanks EVERY tag/comment
  span independently, however many share one line (Fixes 1 and 3,
  2026-07-16 — a bare ``{# comment #}`` used to crash the whole parse, and
  two ``{% set %}`` tags sharing a line used to lose the second variable
  or leave garbled leftover delimiter text). (2) any remaining list-item/
  mapping-value line whose content starts with a bare ``{{`` is
  defensively single-quoted (YAML-escaping any embedded ``'``) so
  ``yaml.safe_load`` sees a valid string scalar instead of misinterpreting
  the leading ``{`` as flow-mapping syntax.
* **Bare-token substitution, requirement walking, and the degrade ladder**
  are IDENTICAL to v1's (shared, not reimplemented — ``walk_requirements``/
  ``requirement_component`` are imported from ``recipe_v1.py``, whose own
  bare-var regex already tolerates v0's un-``$``-prefixed ``{{ VAR }}``
  form alongside v1's ``${{ VAR }}``).
* **Sections walked**: ``requirements.{build,host,run}`` + the v0
  SINGULAR ``test.requires`` (a flat list, no per-test entries) +
  ``outputs[].requirements`` (multi-output, same ``{build,host,run}``
  shape). ``requirements.run_constrained`` (v0's spelling) is recognized
  ONLY by never appearing in the walked ``sections`` tuple — excluded
  entirely, never a ``Component``.
* NFR-S5: mirrors ``recipe_v1.py``/``extract/lockfiles.py`` via the shared
  ``extract/_identity.py::read_bounded_text``; no compiled pattern here
  carries a nested unbounded quantifier.
* Error taxonomy: identical to ``recipe_v1.py`` — a structurally corrupt
  document raises ``UnparsableManifestError`` for the WHOLE manifest; a
  content-degenerate row degrades to one component instead.

This module parses YAML as DATA (``yaml.safe_load`` only) after a
regex-only neutralization pass: no subprocess, no network, no exec, no
Jinja engine.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path

import yaml

from ..interfaces import Router
from ..inventory import Component, Provenance
from ..models import ScannedManifest
from . import UnparsableManifestError
from ._identity import read_bounded_text
from .recipe_v1 import requirement_component, walk_requirements

# The single static routing token this format ever needs (mirrors
# recipe_v1.py's own design — one ecosystem regardless of WHICH
# requirements section a dep came from).
META_V0_REQUIREMENTS_SECTION = "requirements"

_MAX_MANIFEST_BYTES = 5_000_000
_MAX_LINE_BYTES = 8_192

# ONE tokenizer pass over every `{% ... %}` statement tag OR `{# ... #}`
# comment span ANYWHERE on a line (Fix 3, 2026-07-16: the previous
# `^...$`-anchored, whole-line-only regexes missed same-line multi-statement
# Jinja -- `{% set a = "x" %}{% set b = "y" %}` on one line -- and any
# `{% set %}`/statement tag sharing a line with trailing content, e.g. a
# comment). The `set` alternative (with named capture groups) is tried FIRST
# at each match position so its RHS is captured before falling through to the
# generic statement alternative; the comment alternative closes Fix 1 (a bare
# `{# comment #}` is equally valid Jinja and equally invalid raw YAML,
# previously unrecognized by either alternative and left to crash
# yaml.safe_load). Every branch's `.*?` is non-greedy, so `re.sub`'s
# left-to-right, non-overlapping matching finds and blanks each tag/comment
# on a line independently rather than one greedy match spanning from the
# first `{%`/`{#` to the LAST `%}`/`#}`. No nested unbounded quantifiers
# (NFR-S5); a match never crosses a newline (`.` does not match `\n` by
# default), so this is safe to run over the WHOLE text at once rather than
# line-by-line.
_JINJA_SET_TAG_RE = re.compile(
    r"\{%-?\s*set\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<value>.*?)\s*-?%\}"
)
_JINJA_SPAN_RE = re.compile(
    _JINJA_SET_TAG_RE.pattern + r"|\{%-?.*?-?%\}|\{#.*?#\}"
)
# A YAML list-item (`- {{...`) or mapping-value (`key: {{...`) line whose
# content starts with a BARE (un-`$`-prefixed) `{{` — the one shape that
# breaks yaml.safe_load if left unquoted (a plain scalar starting with `{`
# triggers flow-mapping detection).
_LIST_ITEM_BRACE_RE = re.compile(r"^(\s*-\s+)(\{\{.*)$")
_MAPPING_VALUE_BRACE_RE = re.compile(r"^(\s*[^\s:#][^:]*:\s+)(\{\{.*)$")


def _parse_set_literal(raw: str) -> str | None:
    """A ``{% set NAME = RHS %}``'s RHS, if it is a bare literal (a quoted
    string or a bare number) — ``None`` for anything else (a function
    call, concatenation, ...), which is simply not captured (the line is
    still blanked by the caller regardless, so it never reaches
    ``yaml.safe_load`` as raw Jinja)."""
    text = raw.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return text[1:-1]
    try:
        float(text)
    except ValueError:
        return None
    return text


def strip_jinja_statements(text: str) -> tuple[str, dict[str, str]]:
    """Pass 1 (Design Notes): capture every ``{% set %}`` tag's literal value
    into a ``dict[str, str]`` and blank it; blank every OTHER ``{% ... %}``
    statement tag AND every ``{# ... #}`` comment span too (none of the three
    are valid YAML on their own) — wherever on a line they appear, however
    many share one line (Fixes 1 and 3, 2026-07-16; see ``_JINJA_SPAN_RE``'s
    own docstring comment)."""
    context: dict[str, str] = {}

    def _replace(match: re.Match[str]) -> str:
        name = match.group("name")
        if name is not None:
            value = _parse_set_literal(match.group("value"))
            if value is not None:
                context[name] = value
        return ""

    stripped = _JINJA_SPAN_RE.sub(_replace, text)
    return stripped, context


def _quote_yaml_single(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def neutralize_unquoted_braces(text: str) -> str:
    """Pass 2 (Design Notes): defensively single-quote any remaining
    list-item/mapping-value line whose content starts with a bare ``{{`` —
    a leftover unresolved construct (``{{ pin_compatible(...) }}`` etc.)
    would otherwise be misparsed as YAML flow-mapping syntax. The quoted
    text is handed to the SAME bare-var-substitution + degrade path as
    every other entry once parsed (the quoting only affects YAML
    structure, not the string's own content)."""
    lines: list[str] = []
    for line in text.split("\n"):
        match = _LIST_ITEM_BRACE_RE.match(line) or _MAPPING_VALUE_BRACE_RE.match(line)
        if match:
            prefix, expr = match.group(1), match.group(2)
            line = prefix + _quote_yaml_single(expr)
        lines.append(line)
    return "\n".join(lines)


class MetaV0Extractor:
    """Extract the common-case conda dependency set from a v0 ``meta.yaml``
    (Story 2.2) — parse-as-data, never rendered."""

    def __init__(self, router: Router) -> None:
        self._router = router

    def extract(
        self, manifest_path: Path, manifest: ScannedManifest
    ) -> tuple[Component, ...]:
        raw_text = read_bounded_text(
            manifest_path,
            manifest,
            max_bytes=_MAX_MANIFEST_BYTES,
            max_line_bytes=_MAX_LINE_BYTES,
        )
        stripped_text, context = strip_jinja_statements(raw_text)
        neutralized_text = neutralize_unquoted_braces(stripped_text)
        try:
            document = yaml.safe_load(neutralized_text)
        except yaml.YAMLError as exc:
            raise UnparsableManifestError(
                f"unparsable manifest {manifest.path}: {exc}"
            ) from exc
        if document is None:
            return ()
        if not isinstance(document, dict):
            raise UnparsableManifestError(
                f"unparsable manifest {manifest.path}: top-level document "
                "is not a mapping"
            )
        components: list[Component] = []
        components += walk_requirements(
            document.get("requirements"),
            "requirements",
            context,
            manifest,
            self._router,
        )
        components += self._walk_test(document.get("test"), context, manifest)
        components += self._walk_outputs(document.get("outputs"), context, manifest)
        return tuple(components)

    def _walk_test(
        self, test: object, context: Mapping[str, str], manifest: ScannedManifest
    ) -> list[Component]:
        if not isinstance(test, dict):
            return []
        requires = test.get("requires")
        if not isinstance(requires, list):
            return []
        ecosystem = self._router.route(manifest.kind, META_V0_REQUIREMENTS_SECTION)
        provenance = (Provenance(manifest=manifest.path, section="test.requires"),)
        return [
            requirement_component(entry, context, provenance, ecosystem)
            for entry in requires
        ]

    def _walk_outputs(
        self, outputs: object, context: Mapping[str, str], manifest: ScannedManifest
    ) -> list[Component]:
        if not isinstance(outputs, list):
            return []
        components: list[Component] = []
        for index, output in enumerate(outputs):
            if not isinstance(output, dict):
                continue
            components += walk_requirements(
                output.get("requirements"),
                f"outputs[{index}].requirements",
                context,
                manifest,
                self._router,
            )
        return components
