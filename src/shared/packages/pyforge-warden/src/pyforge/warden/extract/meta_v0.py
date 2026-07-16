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
  ``outputs[].requirements`` AND ``outputs[].test.requires`` (multi-output
  — the per-output test analog walked since 2026-07-16; it previously
  produced no components while its top-level twin did).
  ``requirements.run_constrained`` (v0's spelling) is recognized
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
from ..models import Ecosystem, ScannedManifest
from . import UnparsableManifestError
from ._identity import read_bounded_text, yaml_safe_load_strict
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


# The two bare NUMERIC literal shapes a `{% set %}` RHS may take. Jinja
# evaluates a numeric literal through Python's own int/float semantics and
# renders it back via str(), so the render of `{% set version = 2.10 %}` is
# '2.1' -- NOT the source spelling '2.10'. Capturing the raw text used to
# feed the never-rendered spelling to CVE matching as a confident exact
# version while the real conda-build render disagreed (verified live, fixed
# 2026-07-16). Deliberately narrow: exponents (`1e3`), `inf`/`nan` (which
# jinja treats as NAMES, not literals), underscores, and leading `+` are all
# rejected -> not captured -> the uses degrade (never guess). No nested
# unbounded quantifiers (NFR-S5).
_INT_LITERAL_RE = re.compile(r"^-?\d+$")
_FLOAT_LITERAL_RE = re.compile(r"^-?\d+\.\d+$")


def _parse_set_literal(raw: str) -> str | None:
    """A ``{% set NAME = RHS %}``'s RHS, if it is a bare literal (a quoted
    string or a bare number) — ``None`` for anything else (a function
    call, concatenation, ...), which is simply not captured (the line is
    still blanked by the caller regardless, so it never reaches
    ``yaml.safe_load`` as raw Jinja). A first-char==last-char quote check
    alone is NOT enough: a conditional EXPRESSION like
    ``"1.0" if unix else "2.0"`` both starts and ends with a quote, and
    capturing its raw text used to yield a corrupted
    ``'1.0" if unix else "2.0'`` "literal" silently treated as a resolved
    exact version (fixed 2026-07-16) — so any RHS whose INTERIOR contains
    the quote character is rejected as not-a-bare-literal too.

    A bare NUMERIC literal is captured as Jinja itself would RENDER it
    (``str(int(...))``/``str(float(...))`` — Python semantics), not as its
    source spelling: ``{% set version = 2.10 %}`` renders ``2.1`` in the
    real conda-build pass, so ``2.1`` is the honest capture (see
    ``_INT_LITERAL_RE``/``_FLOAT_LITERAL_RE``; fixed 2026-07-16)."""
    text = raw.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        inner = text[1:-1]
        if text[0] in inner:
            return None
        return inner
    if _INT_LITERAL_RE.match(text):
        return str(int(text))
    if _FLOAT_LITERAL_RE.match(text):
        return str(float(text))
    return None


def strip_jinja_statements(text: str) -> tuple[str, dict[str, str]]:
    """Pass 1 (Design Notes): capture every ``{% set %}`` tag's literal value
    into a ``dict[str, str]`` and blank it; blank every OTHER ``{% ... %}``
    statement tag AND every ``{# ... #}`` comment span too (none of the three
    are valid YAML on their own) — wherever on a line they appear, however
    many share one line (Fixes 1 and 3, 2026-07-16; see ``_JINJA_SPAN_RE``'s
    own docstring comment).

    A name ``{% set %}``-assigned MORE than once is AMBIGUOUS — the extra
    assignments live under ``{% if %}`` branches this parse-as-data module
    never evaluates (Story 2.3 owns control flow), so last-wins capture used
    to silently report the wrong branch's value as a confidently-resolved
    literal (fixed 2026-07-16). A re-assigned name is dropped from the
    captured context entirely: its uses degrade per-entry
    (``NAME_ONLY``/``RAW_MALFORMED``), never guess a branch."""
    context: dict[str, str] = {}
    seen: set[str] = set()

    def _replace(match: re.Match[str]) -> str:
        name = match.group("name")
        if name is not None:
            if name in seen:
                context.pop(name, None)
            else:
                seen.add(name)
                value = _parse_set_literal(match.group("value"))
                if value is not None:
                    context[name] = value
        return ""

    stripped = _JINJA_SPAN_RE.sub(_replace, text)
    return stripped, context


def _quote_yaml_single(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


# A trailing YAML comment (whitespace + `#` + rest-of-line) AFTER the last
# `}}` of a brace expression about to be defensively quoted. Quoting to
# end-of-line would otherwise bake the comment INTO the string content
# (YAML can no longer strip what is now inside quotes), so a selector
# comment on a templated dep line (`- {{ nv }}  # [linux]`) used to end up
# as a component "version" of `# [linux]` (fixed 2026-07-16). Comments on
# UN-quoted lines are untouched — YAML's own comment handling strips those.
_TRAILING_COMMENT_RE = re.compile(r"\s#.*$")


def _strip_trailing_yaml_comment(expr: str) -> str:
    idx = expr.rfind("}}")
    if idx == -1:
        return expr
    tail = expr[idx + 2 :]
    match = _TRAILING_COMMENT_RE.search(tail)
    if match:
        return expr[: idx + 2 + match.start()].rstrip()
    return expr


def neutralize_unquoted_braces(text: str) -> str:
    """Pass 2 (Design Notes): defensively single-quote any remaining
    list-item/mapping-value line whose content starts with a bare ``{{`` —
    a leftover unresolved construct (``{{ pin_compatible(...) }}`` etc.)
    would otherwise be misparsed as YAML flow-mapping syntax. Any trailing
    YAML comment after the expression's last ``}}`` is stripped BEFORE
    quoting (see ``_TRAILING_COMMENT_RE``). The quoted text is handed to
    the SAME bare-var-substitution + degrade path as every other entry once
    parsed (the quoting only affects YAML structure, not the string's own
    content)."""
    lines: list[str] = []
    for line in text.split("\n"):
        match = _LIST_ITEM_BRACE_RE.match(line) or _MAPPING_VALUE_BRACE_RE.match(line)
        if match:
            prefix, expr = match.group(1), match.group(2)
            line = prefix + _quote_yaml_single(_strip_trailing_yaml_comment(expr))
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
            # yaml_safe_load_strict (not plain safe_load): duplicate mapping
            # keys are REJECTED -- after `{% if %}`/`{% else %}` blanking,
            # the classic v0 duplicated-key branch idiom would otherwise
            # last-wins-DROP one branch's whole dependency subtree with no
            # degrade marker at all (verified live, fixed 2026-07-16); it
            # fails closed as a typed whole-manifest error instead (branch-
            # union semantics are Story 2.3's control-flow work). Alias
            # amplification is refused by the same loader (NFR-S5).
            document = yaml_safe_load_strict(neutralized_text)
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
        self,
        test: object,
        context: Mapping[str, str],
        manifest: ScannedManifest,
        *,
        section: str = "test.requires",
    ) -> list[Component]:
        if not isinstance(test, dict):
            return []
        requires = test.get("requires")
        if not isinstance(requires, list):
            return []
        # fail-loud gate: asserted (not just called for its side effect) so a
        # future `_ROUTES` edit is caught HERE rather than silently continuing
        # to hardcode CONDA via `requirement_component`'s success path --
        # mirrors `extract/pixi.py`/`environment_yml.py`'s identical Fix 7
        # (completed for this walker 2026-07-16; the first pass patched only
        # 2 of the 4 extractors).
        ecosystem = self._router.route(manifest.kind, META_V0_REQUIREMENTS_SECTION)
        assert ecosystem is Ecosystem.CONDA
        provenance = (Provenance(manifest=manifest.path, section=section),)
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
            # A multi-output recipe's PER-OUTPUT test deps (`outputs[].test.
            # requires`, same singular v0 shape as the top level) -- walked
            # since 2026-07-16: the top-level `test.requires` was walked but
            # its per-output analog silently produced no components.
            components += self._walk_test(
                output.get("test"),
                context,
                manifest,
                section=f"outputs[{index}].test.requires",
            )
        return components
