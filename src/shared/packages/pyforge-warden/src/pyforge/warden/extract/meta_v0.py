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
  comment span is ALSO blanked — a multi-line ``{% for %}`` block degrades
  to its individual (still-templated, still-degraded) list-item entries
  rather than crashing the WHOLE document's YAML parse; per-iteration
  ``{% for %}`` EXPANSION itself is explicitly out of scope (Story 2.3's
  Boundaries: "Never" list) — this module only ever sees the blanked tag,
  never the loop body it would have generated. A single ``re.sub`` tokenizer
  pass over
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
  form alongside v1's ``${{ VAR }}``, and whose ``compiler()``/``stdlib()``/
  ``pin_subpackage()`` whole-value exclude applies unchanged to v0's bare
  ``{{ ... }}`` call syntax too). v1's ``if``/``then``/``else`` STRUCTURAL
  selector construct (a dict-shaped requirements-list entry) is not part of
  v0's grammar at all — no legitimate meta.yaml authoring produces it; v0's
  ONLY real selector idiom is the trailing ``# [cond]`` COMMENT on an
  otherwise-ordinary list-item line (see the next bullet). Conflating the
  two as EQUIVALENT constructs would be wrong. Precisely worded (review
  pass 3 correction — the prior wording overclaimed): because
  ``walk_requirements``'s dict-with-``if``-key dispatch is genuinely SHARED
  code with no format-awareness guard, a v0 requirements-list entry that
  were HAND-AUTHORED into that exact non-native shape would still route
  through v1's union walker rather than degrade — safely (the walker's own
  "never silently vanish" guarantees hold, so worst case is a `# [cond]`
  comment on that same line going untagged, never a crash or a dropped
  dependency), just via the wrong mechanism for a shape v0 was never meant
  to produce in the first place.
* **Selector-comment union (Story 2.3)**: a ``# [cond]`` trailing comment on
  a requirements-list-item line is captured by ``capture_selector_comments``
  over the RAW manifest text (before any stripping), keyed by the comment's
  0-indexed SOURCE LINE NUMBER — never by the entry's text content, which
  would mis-attribute a tag whenever the same dependency text appears
  elsewhere, commented or not (see ``capture_selector_comments`` and
  ``LineStr``'s own docstrings for the full rationale). The parsed document
  is loaded through ``_LineTrackingLoader`` so every string scalar carries
  its own originating line, letting ``requirements.{build,host,run}``/
  ``test.requires``/``outputs[].*`` correlate each entry back to its
  captured comment (if any) with zero ambiguity, then tag it
  ``[sel:COND]`` and escalate to ``UNION_MARKED`` (see
  ``_identity.py::apply_union_tag``) — both sibling entries of a
  ``# [win]``/``# [unix]`` pair survive extraction, union semantics,
  exactly like v1's ``if``/``then``/``else``.
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
  content-degenerate row degrades to one component instead. ``RecursionError``
  (a pathologically nested YAML document) is caught alongside
  ``yaml.YAMLError`` and re-raised the same way (Story 2.3 — mirrors
  ``recipe_v1.py``'s identical guard, kept even though v0 has no recursive
  WALKER of its own, purely so both extractors fail closed identically on
  hostile input).

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
from ._identity import (
    _StrictSafeLoader,
    apply_union_tag,
    read_bounded_text,
    truncate_for_name,
)
from .recipe_v1 import requirement_component, selector_tag_suffix, walk_requirements

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


# --- Story 2.3: the v0 `# [cond]` selector-comment union, correlated by
# SOURCE LINE NUMBER (Design Notes' "Review Pass 2 corrections" -- the
# content-keyed FIFO-queue mechanism review pass 1 shipped was PROVEN wrong
# by live reproduction: `requirements.run: [helper, "helper  # [win]"]`
# (an uncommented occurrence walked BEFORE the commented one, same list)
# wrongly tags the FIRST occurrence, since the queue holds exactly one entry
# and ANY lookup by that content pops it regardless of which occurrence
# actually carries the comment -- a content-keying bug, not an ordering bug,
# so a FIFO queue never fixed it, no matter how document-order-faithful. A
# source LINE NUMBER has zero collision risk: it is unambiguous regardless
# of duplicate text, walk order, or which section/output a line lives in.

# `<indent>- <content>  # [<cond>]` -- a v0 selector-comment on a
# REQUIREMENTS-LIST-ITEM line ONLY (the leading `-` anchor is what excludes
# a non-list-item line like `skip: true  # [win]` -- Boundaries' own "Never"
# clause: selector capture never applies there). No nested unbounded
# quantifiers (NFR-S5).
_SELECTOR_COMMENT_RE = re.compile(r"^\s*-\s+.*?\s+#\s*\[(?P<cond>[^\]]*)\]\s*$")


def capture_selector_comments(raw_text: str) -> dict[int, str]:
    """Scan the RAW, un-neutralized manifest text for
    ``<indent>- <content>  # [<cond>]`` list-item lines, keyed by the
    matched line's 0-indexed index — the SAME index
    ``_LineTrackingLoader``'s parsed ``LineStr`` scalars carry
    (``node.start_mark.line``), which is what lets
    ``recipe_v1.py::selector_tag_suffix`` correlate a parsed entry back to
    its comment with zero ambiguity (see the section banner above for why
    content-keying was unsound).

    Must run BEFORE ``strip_jinja_statements``/``neutralize_unquoted_braces``
    touch the text (same ordering requirement review pass 1 already
    established — a comment could otherwise be blanked/relocated before
    capture); LINE NUMBERS, unlike raw content, stay valid across that whole
    pipeline regardless (neither regex pass ever removes a newline — see
    each function's own docstring).

    A blank/whitespace-only bracket (``# []``, ``# [   ]`` — a plausible
    editing leftover) is NOT captured (review pass 3 fix): it carries no
    real condition, so tagging it would produce a meaningless ``[sel:]``
    suffix and wrongly escalate an otherwise-``PARSED`` entry to
    ``UNION_MARKED`` for a distinction that doesn't exist."""
    line_to_condition: dict[int, str] = {}
    for index, line in enumerate(raw_text.split("\n")):
        match = _SELECTOR_COMMENT_RE.match(line)
        if match:
            cond = match.group("cond").strip()
            if cond:
                line_to_condition[index] = truncate_for_name(cond)
    return line_to_condition


class LineStr(str):
    """A genuine ``str`` subclass (``isinstance(x, str)`` stays ``True``
    everywhere downstream, so this is safe to use as the parsed VALUE for
    every string scalar without touching any consumer) carrying the
    ORIGINATING source line number (0-indexed, ``node.start_mark.line``) of
    the YAML scalar it was parsed from. Exists ONLY to correlate a
    requirements-list entry with its raw-text ``# [cond]`` selector comment
    by an unambiguous LINE NUMBER instead of by CONTENT — see the section
    banner above ``capture_selector_comments`` for the full rationale."""

    __slots__ = ("source_line",)


def _construct_str_with_line(loader: yaml.Loader, node: yaml.Node) -> LineStr:
    value = loader.construct_scalar(node)
    tagged = LineStr(value)
    tagged.source_line = node.start_mark.line  # 0-indexed
    return tagged


class _LineTrackingLoader(_StrictSafeLoader):
    """A NEW loader, local to THIS module — never modifies the shared
    ``_identity.py::_StrictSafeLoader`` the other 3 YAML extractors depend
    on (this is a v0-only, comment-correlation-only concern). Subclasses
    ``_StrictSafeLoader`` (not bare ``yaml.SafeLoader``) so the SAME
    alias-refusal + duplicate-mapping-key-rejection hardening applies here
    too — only the string-scalar constructor is added on top.
    ``add_constructor`` below copy-on-writes onto THIS subclass's own
    ``yaml_constructors`` dict (PyYAML's own documented
    ``BaseConstructor.add_constructor`` mechanism), so the parent classes'
    constructors are never mutated."""


_LineTrackingLoader.add_constructor("tag:yaml.org,2002:str", _construct_str_with_line)


def _yaml_load_line_tracking(text: str) -> object:
    """``_LineTrackingLoader``'s load entrypoint — drives the loader
    protocol directly (mirrors ``_identity.py::yaml_safe_load_strict``
    exactly: construct -> ``get_single_data`` -> ``dispose``, never
    ``yaml.load(..., Loader=...)``, which the ``extract/`` AST-denylist
    meta-test bans outright). Raises ``yaml.YAMLError`` exactly like
    ``safe_load``/``yaml_safe_load_strict`` (callers' existing
    except-wrapping is unchanged)."""
    loader = _LineTrackingLoader(text)
    try:
        return loader.get_single_data()
    finally:
        loader.dispose()


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
        # Captured over the RAW text, BEFORE any stripping/neutralizing --
        # correlated to the parsed document below by LINE NUMBER (Story
        # 2.3), which survives the neutralize pipeline unchanged (neither
        # pass ever removes a newline -- see capture_selector_comments'
        # own docstring).
        selector_comments = capture_selector_comments(raw_text)
        stripped_text, context = strip_jinja_statements(raw_text)
        neutralized_text = neutralize_unquoted_braces(stripped_text)
        try:
            # _yaml_load_line_tracking (not yaml_safe_load_strict): every
            # parsed string scalar is tagged with its source line (a
            # LineStr), which selector_tag_suffix below looks up against
            # `selector_comments` -- while still carrying
            # _StrictSafeLoader's alias-refusal + duplicate-mapping-key
            # rejection (see _LineTrackingLoader's own docstring). Duplicate
            # mapping keys are REJECTED -- after `{% if %}`/`{% else %}`
            # blanking, the classic v0 duplicated-KEY branch idiom would
            # otherwise last-wins-DROP one branch's whole dependency subtree
            # with no degrade marker at all (verified live, fixed
            # 2026-07-16); it fails closed as a typed whole-manifest error
            # instead. That idiom is NOT the same construct as Story 2.3's
            # `# [cond]` comment-selector union below -- it stays out of
            # scope (a duplicate-mapping-KEY branch, not a same-list
            # sibling-entry comment) and continues to fail closed. Alias
            # amplification is refused by the same loader (NFR-S5).
            document = _yaml_load_line_tracking(neutralized_text)
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
                selector_comments=selector_comments,
            )
            components += self._walk_test(
                document.get("test"), context, manifest, selector_comments
            )
            components += self._walk_outputs(
                document.get("outputs"), context, manifest, selector_comments
            )
        except (yaml.YAMLError, RecursionError) as exc:
            # RecursionError: v0 has no structural if/then/else walker of
            # its own (that construct is v1-only -- see the module
            # docstring), so nothing here recurses on MANIFEST content the
            # way recipe_v1.py's walker does; this guard exists purely to
            # mirror recipe_v1.py's identical precedent for a pathologically
            # nested (but well within the 5MB manifest cap) YAML document --
            # an intentional, documented tradeoff, not an oversight (Story
            # 2.3, Review Pass 1 correction #2).
            raise UnparsableManifestError(
                f"unparsable manifest {manifest.path}: {exc}"
            ) from exc
        return tuple(components)

    def _walk_test(
        self,
        test: object,
        context: Mapping[str, str],
        manifest: ScannedManifest,
        selector_comments: Mapping[int, str] | None = None,
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
        components: list[Component] = []
        for entry in requires:
            component = requirement_component(entry, context, provenance, ecosystem)
            if component is None:
                continue
            suffix = selector_tag_suffix(entry, selector_comments)
            if suffix is not None:
                component = apply_union_tag(component, suffix)
            components.append(component)
        return components

    def _walk_outputs(
        self,
        outputs: object,
        context: Mapping[str, str],
        manifest: ScannedManifest,
        selector_comments: Mapping[int, str] | None = None,
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
                selector_comments=selector_comments,
            )
            # A multi-output recipe's PER-OUTPUT test deps (`outputs[].test.
            # requires`, same singular v0 shape as the top level) -- walked
            # since 2026-07-16: the top-level `test.requires` was walked but
            # its per-output analog silently produced no components.
            components += self._walk_test(
                output.get("test"),
                context,
                manifest,
                selector_comments,
                section=f"outputs[{index}].test.requires",
            )
        return components
