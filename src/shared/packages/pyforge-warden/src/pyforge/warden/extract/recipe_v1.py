"""recipe.yaml (v1) non-rendering extraction (Story 2.2) — parse-as-data
ONLY, never rendered: ``context:`` is itself valid YAML (a bare ``${{ VAR
}}`` is just a plain string scalar, since a plain YAML scalar starting with
``$`` never triggers flow-mapping detection the way a bare ``{{`` would), so
the document only needs a small defensive neutralize pass — never a full
statement-blanking pass like ``meta_v0.py``'s — BEFORE ``yaml.safe_load``
runs: ``strip_jinja_comments`` blanks any ``{# ... #}`` Jinja comment span
(equally valid Jinja/minijinja syntax, equally invalid raw YAML — recipe.yaml
v1 IS minijinja-templated even though its own substitution syntax is
``$``-prefixed) and ``neutralize_bare_braces`` defensively single-quotes any
BARE (un-``$``-prefixed) ``{{ ... }}`` list-item/mapping-value (fixed
2026-07-16 — this module previously ran NO neutralize pass at all, so either
shape crashed the WHOLE document's parse; see both functions' own
docstrings). ``${{ VAR }}``/``{{ VAR }}`` bare-token substitution then runs
on the ALREADY-PARSED structure's string scalars. No ``jinja2`` import, no
execution primitive (NFR-S1 — the ``extract/`` AST-denylist meta-test covers
this file automatically).

Ownership decisions recorded:

* **Bare-token substitution only** (Boundaries): ``${{ VAR }}``/``{{ VAR
  }}`` where ``VAR`` is a plain identifier already captured in
  ``context:`` resolves to its literal value. A filter/expression/
  function-call construct (``${{ version.replace(...) }}``, ...)
  structurally can't match the bare-token regex, so it is left untouched by
  substitution — the caller then degrades that ONE entry to ``NAME_ONLY``
  (a usable best-effort name survives — the text before the first
  remaining marker) or ``RAW_MALFORMED`` (nothing usable at all). Never a
  crash, never a guessed version.
* **The full construct matrix (Story 2.3)**: ``compiler()``/``stdlib()``/
  ``pin_subpackage()`` calls are recognized by a whole-value regex (post
  bare-var substitution) and EXCLUDED entirely — ``None``, never a
  ``Component`` (mirrors ``run_constrained``'s existing exclude precedent;
  see ``requirement_component``). A structural ``if:``/``then:``/``else:``
  requirements-list entry (a dict, not a string) is recursively expanded
  into leaf entries from BOTH branches via ``walk_if_then_else`` — each
  leaf tagged with a ``[if:COND]``/``[else:COND]`` ``Provenance.section``
  suffix and escalated to ``UNION_MARKED`` when it would otherwise be
  ``PARSED`` (see ``walk_if_then_else``'s own docstring). Expression-logic
  on a resolved name (``${{ name }}==${{ version.replace(...) }}``) still
  degrades to ``NAME_ONLY`` via the SAME pre-2.3 mechanism above — nothing
  new needed there.
* **Sections walked**: ``requirements.{build,host,run}`` +
  ``tests[].requirements.{build,run}`` (v1's list-valued test entries) +
  ``outputs[].requirements`` AND ``outputs[].tests[]`` (multi-output — the
  per-output tests analog walked since 2026-07-16; it previously produced
  no components while its top-level twin did).
  ``requirements.run_constraints`` is recognized
  ONLY by never appearing in the walked ``sections`` tuple — excluded
  entirely, never a ``Component`` (no schema change, no
  ``provenance: constraint`` field — the Boundaries' explicit call).
* **Conda matchspec parsing** (``split_conda_dep_string`` +
  ``classify_conda_specifier``, both shared via ``extract/_identity.py``)
  mirrors ``pyproject.py::_exact_pin``'s discipline. A genuinely bare
  version WITHOUT an operator or wildcard is invalid rattler-build v1
  matchspec syntax (empirically confirmed against a live render: ``mypkg
  1.2.3`` raises ``PyRattlerBuildError``, ``mypkg ==1.2.3``/``mypkg
  1.2.3.*`` do not) — real v1 recipes never carry this form, so this
  extractor's own EXACT-classification of a bare specifier token is a
  dead path for genuinely valid v1 input, never a source of false
  precision.
* **Every conda-ecosystem row consults the shared ``extract/_identity.py``
  path**: only a ``verified``-confidence conda->pypi map hit sets
  ``pypi_identity``; anything else withholds ``UNMAPPED_ECOSYSTEM``.
* NFR-S5: the whole file is size-capped and line-length-capped BEFORE
  ``yaml.safe_load`` (mirrors ``extract/lockfiles.py::_read_bounded`` via
  the shared ``extract/_identity.py::read_bounded_text``); no compiled
  pattern here carries a nested unbounded quantifier.
* Error taxonomy (mirrors ``extract/lockfiles.py``): a structurally
  corrupt document (not a mapping) raises ``UnparsableManifestError`` for
  the WHOLE manifest; a content-degenerate ROW (a non-string requirement
  entry, an unrecognized template construct) degrades to one
  ``NAME_ONLY``/``RAW_MALFORMED`` component instead — never dropped,
  never crashes.

This module parses YAML as DATA (``yaml.safe_load`` only) after a small
regex-only neutralize pass: no subprocess, no network, no exec, no Jinja
engine.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path

import yaml

from ..interfaces import Router
from ..inventory import Component, Provenance
from ..models import Ecosystem, ExtractionMode, ScannedManifest, WithholdReason
from . import UnparsableManifestError
from ._identity import (
    _conda_component,
    _raw_malformed,
    apply_union_tag,
    classify_conda_specifier,
    read_bounded_text,
    split_conda_dep_string,
    truncate_for_name,
    yaml_safe_load_strict,
)

# The single static routing token this format ever needs (recipe.yaml has
# exactly one ecosystem regardless of WHICH requirements section a dep
# came from) — the section NAME (top-level/tests[i]/outputs[i]) is carried
# on Provenance.section, never baked into the routing key (mirrors
# pixi.toml's feature/target token design, Story 2.2).
RECIPE_V1_REQUIREMENTS_SECTION = "requirements"

_MAX_MANIFEST_BYTES = 5_000_000
_MAX_LINE_BYTES = 8_192

# A BARE `{{ VAR }}`/`${{ VAR }}` token — VAR must be a plain identifier
# with nothing else between the braces (no filter/expression/function
# call); anything else structurally can't match, so substitution leaves it
# untouched and the caller degrades on the leftover marker. No nested
# unbounded quantifiers (NFR-S5).
_BARE_VAR_RE = re.compile(r"\$?\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")
# Any remaining `{{`/`${{` marker after substitution — used only to DETECT
# an unresolved/unrecognized construct (the document is already parsed by
# this point; this never re-feeds anything to yaml.safe_load).
_TEMPLATE_MARKER_RE = re.compile(r"\$?\{\{")

# `compiler("c")`/`stdlib("c")`/`pin_subpackage("x", ...)` — a BUILD-TOOL or
# INTRA-RECIPE-OUTPUT reference, never a real external dependency (Story
# 2.3; mirrors `run_constrained`'s existing exclude precedent: recognized
# only to be skipped, never a `Component`). Matched against the ALREADY
# bare-var-substituted string, before the generic degrade fallback.
# `[^{}]*` (not `.*`) inside the parens is a fix for a live-confirmed C0b
# silent-drop: a greedy `.*` lets `fullmatch` backtrack PAST the first
# `)`/`}}` and swallow a SECOND, unrelated `{{ }}`/`${{ }}` expression
# sharing the line (e.g. `${{ compiler("c") }} ${{ pin_compatible("numpy")
# }}`), wrongly excluding a real dependency (`numpy`) with zero degrade
# marker. `[^{}]*` can never cross a `{`/`}` boundary, so a multi-expression
# line now correctly falls through to the generic degrade ladder instead of
# being wrongly excluded whole. No nested unbounded quantifiers (NFR-S5).
_EXCLUDE_CALL_RE = re.compile(
    r"^\$?\{\{\s*(compiler|stdlib|pin_subpackage)\s*\([^{}]*\)\s*\}\}$"
)

# A `{# ... #}` Jinja comment span (Fix 1) — see ``strip_jinja_comments``.
# Non-greedy so multiple comments per line are each matched independently.
_JINJA_COMMENT_RE = re.compile(r"\{#.*?#\}")
# A YAML list-item (`- {{...`) or mapping-value (`key: {{...`) line whose
# content starts with a BARE (un-`$`-prefixed) `{{` (Fix 2) — see
# ``neutralize_bare_braces``.
_LIST_ITEM_BRACE_RE = re.compile(r"^(\s*-\s+)(\{\{.*)$")
_MAPPING_VALUE_BRACE_RE = re.compile(r"^(\s*[^\s:#][^:]*:\s+)(\{\{.*)$")

# requirements.run_constraints (v1's plural spelling; run_constrained is
# v0's) is deliberately absent from every `sections` tuple below — that IS
# the exclusion mechanism (Boundaries: recognized only to be skipped).
_TOP_LEVEL_SECTIONS = ("build", "host", "run")
_TEST_SECTIONS = ("build", "run")

# --- Fixes 1+2 (2026-07-16): a neutralize-before-load pass this module was
# missing entirely -- unlike meta_v0.py (which already neutralized `{% ...
# %}`), recipe_v1.py ran `yaml.safe_load` directly, trusting v1's own valid
# syntax (`context:` is native YAML, `${{ VAR }}` is a plain scalar starting
# with `$` that never triggers flow-mapping detection) to never need one.
# Two shapes broke that trust, both crashing the WHOLE document's parse: (1)
# a bare `{# ... #}` Jinja comment (equally valid Jinja/minijinja syntax,
# equally invalid raw YAML -- recipe.yaml v1 IS minijinja-templated even
# though its documented substitution syntax is `$`-prefixed); (2) a bare
# (un-`$`-prefixed) `{{ VAR }}` list-item/mapping-value -- not valid v1
# syntax on its own, but `_BARE_VAR_RE`'s optional `$` prefix already treats
# it as an equally detectable substitution target once parsed (by design --
# it is v0's ONLY form, and `meta_v0.py` reuses this module's
# `substitute_bare_vars`/`walk_requirements` unmodified), so quoting it
# defensively here lets that existing substitution still resolve it when the
# var is known, and degrade gracefully (NAME_ONLY/RAW_MALFORMED) when it is
# not -- never a crash either way.


def strip_jinja_comments(text: str) -> str:
    """Blank every ``{# ... #}`` Jinja comment span (Fix 1) BEFORE
    ``yaml.safe_load`` sees the text -- mirrors ``meta_v0.py``'s own
    comment-stripping (duplicated, not imported: ``meta_v0.py`` already
    depends on THIS module for its shared bare-token substitution, so
    importing the reverse direction would create a cycle). Non-greedy so
    multiple comments sharing one line are each stripped independently."""
    return _JINJA_COMMENT_RE.sub("", text)


def _quote_yaml_single(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


# A trailing YAML comment after the last `}}` of a brace expression about to
# be defensively quoted -- stripped BEFORE quoting so a selector comment on a
# templated dep line (`- {{ nv }}  # [linux]`) is never baked INTO the quoted
# string content as a garbage "version" (fixed 2026-07-16; mirrors
# `meta_v0.py`'s identical `_strip_trailing_yaml_comment` -- same duplication
# rationale as `strip_jinja_comments` below). Comments on UN-quoted lines are
# untouched: YAML's own comment handling strips those.
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


def neutralize_bare_braces(text: str) -> str:
    """Defensively single-quote any list-item/mapping-value line whose
    content starts with a BARE (un-``$``-prefixed) ``{{`` (Fix 2) -- the one
    shape that breaks ``yaml.safe_load`` if left unquoted (a plain scalar
    starting with ``{`` triggers YAML flow-mapping detection). Any trailing
    YAML comment after the expression's last ``}}`` is stripped BEFORE
    quoting (see ``_TRAILING_COMMENT_RE``). Mirrors ``meta_v0.py``'s
    identical ``neutralize_unquoted_braces`` (duplicated, not imported --
    same one-directional-dependency reason as ``strip_jinja_comments``
    above). The quoting only affects YAML structure, never the string's own
    content -- the quoted text is handed to the SAME bare-var-substitution +
    degrade path as every other entry once parsed."""
    lines: list[str] = []
    for line in text.split("\n"):
        match = _LIST_ITEM_BRACE_RE.match(line) or _MAPPING_VALUE_BRACE_RE.match(line)
        if match:
            prefix, expr = match.group(1), match.group(2)
            line = prefix + _quote_yaml_single(_strip_trailing_yaml_comment(expr))
        lines.append(line)
    return "\n".join(lines)


def substitute_bare_vars(text: str, context: Mapping[str, str]) -> str:
    """Replace every BARE ``{{ VAR }}``/``${{ VAR }}`` occurrence in
    ``text`` whose ``VAR`` is a captured ``context`` entry with its literal
    value; anything else (an unknown ``VAR``, or a non-bare construct) is
    left untouched — the caller degrades on a leftover marker, never
    guesses."""

    def _replace(match: re.Match[str]) -> str:
        var = match.group(1)
        return context[var] if var in context else match.group(0)

    return _BARE_VAR_RE.sub(_replace, text)


def best_effort_name(raw: str) -> str | None:
    """The FIRST TOKEN of the text before the first remaining template
    marker, with any trailing comparison-operator debris stripped — the
    Design Notes' "raw-text name scrape" for a degraded entry. ``None``
    when nothing usable precedes the marker (or the marker is at
    position 0). Taking the whole prefix verbatim used to turn the
    canonical conda-forge templated-pin shape (``python >=${{ python_min
    }}`` — ``python_min`` is a variant variable, never in ``context:``, so
    this hits essentially every real noarch v1 recipe) into a component
    literally named ``"python >="`` — a garbage token that can never hit
    the conda->pypi map (fixed 2026-07-16): the name is the first
    whitespace-token only, and a trailing operator fragment (the contiguous
    ``numpy>=${{ v }}`` form) is stripped from it.

    A marker that ABUTS the name token itself (``mypkg-data-${{ version
    }}`` — a templated-SUFFIX name, no whitespace and no operator between
    the token and the marker) means the NAME is templated, not the
    version: no truncation of it can be honest (``mypkg-data-`` is an
    impossible conda name presented as a plausible component, and
    stripping further would fabricate a DIFFERENT package's identity), so
    it returns ``None`` and the entry degrades to ``RAW_MALFORMED``
    (fixed 2026-07-16)."""
    marker = _TEMPLATE_MARKER_RE.search(raw)
    prefix = raw[: marker.start()] if marker else raw
    stripped = prefix.strip()
    if not stripped:
        return None
    raw_token = stripped.split()[0]
    token = raw_token.rstrip("<>=!~,")
    if not token:
        return None
    if (
        marker is not None
        and len(stripped.split()) == 1
        and prefix == prefix.rstrip()
        and token == raw_token
    ):
        # The single pre-marker token runs straight into the marker with no
        # operator debris between them: the name itself is templated.
        return None
    return token


def context_map(document: Mapping[str, object]) -> dict[str, str]:
    """Extract ``context:``'s bare string/integer scalars into a
    ``dict[str, str]`` — non-scalar values (lists/mappings) are not "a
    literal string/number already captured" (Boundaries), so they are
    excluded from substitution entirely (a use of such a var degrades that
    entry, never crashes).

    FLOAT-typed values are excluded too (fixed 2026-07-16): YAML has
    already destroyed the source spelling by the time this runs
    (``version: 1.20`` parses as the float ``1.2``), while the real
    rattler-build renderer preserves the raw text (verified live: the
    identical document renders ``==1.20``) — so ``str(value)`` would
    fabricate a confidently-wrong exact version (``'1.2'``) and feed it to
    CVE matching, the exact C0 corrupted-version class the exactness shape
    gate exists to prevent. An un-capturable value's uses degrade to
    ``NAME_ONLY`` (never guess); integers round-trip unambiguously and stay
    captured."""
    context = document.get("context")
    if not isinstance(context, dict):
        return {}
    result: dict[str, str] = {}
    for key, value in context.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, bool):
            continue  # bool is an int subtype pitfall — never a dep token
        if isinstance(value, (str, int)):
            result[key] = str(value)
    return result


def requirement_component(
    raw: object,
    context: Mapping[str, str],
    provenance: tuple[Provenance, ...],
    ecosystem: Ecosystem,
) -> Component | None:
    """Turn ONE ``requirements.*``/``tests[].requirements.*``/
    ``outputs[].requirements.*`` list entry into a ``Component`` — a
    literal dep passes through PARSED; a bare context-var reference
    resolves to its captured literal (still PARSED — the Approach
    section's own wording); anything else degrades to ``NAME_ONLY`` (a
    usable best-effort name survives) or ``RAW_MALFORMED`` (nothing usable
    at all) — never a crash, never a guessed version.

    ``None`` (Story 2.3) — a whole-value ``compiler()``/``stdlib()``/
    ``pin_subpackage()`` call (post bare-var substitution): a build-tool
    reference or an intra-recipe subpackage reference, neither a real
    external dependency (mirrors ``run_constrained``'s existing exclude
    precedent). Every caller must filter ``None`` out."""
    if not isinstance(raw, str):
        # truncate_for_name: str() of a parsed YAML structure is unbounded
        # by the raw-byte caps -- never let it become a multi-MB "name".
        return _raw_malformed(ecosystem, truncate_for_name(str(raw)), provenance)
    substituted = substitute_bare_vars(raw, context)
    if _EXCLUDE_CALL_RE.fullmatch(substituted):
        return None
    if _TEMPLATE_MARKER_RE.search(substituted):
        name = best_effort_name(substituted)
        if name:
            return _conda_component(
                name, None, provenance, extraction_mode=ExtractionMode.NAME_ONLY
            )
        # str(raw), not raw: meta_v0.py may hand this a `LineStr` (a `str`
        # subclass carrying `.source_line` for selector-comment correlation,
        # review pass 3) -- Component.name must stay a plain str, never leak
        # that internal carrier type into the frozen contract.
        return _raw_malformed(ecosystem, str(raw), provenance)
    split = split_conda_dep_string(substituted)
    if split is None:
        return _raw_malformed(ecosystem, str(raw), provenance)
    name, specifier = split
    exact, reason = classify_conda_specifier(specifier)
    return _conda_component(
        name,
        exact,
        provenance,
        no_version_reason=reason or WithholdReason.NO_VERSION,
    )


def walk_if_then_else(
    entry: Mapping[str, object],
    context: Mapping[str, str],
    provenance: tuple[Provenance, ...],
    ecosystem: Ecosystem,
    *,
    outer_suffix: str = "",
) -> list[Component]:
    """Recursively expand ONE ``if``/``then``/``else`` requirements-list
    entry (a dict, not a string) into leaf components from BOTH branches —
    the v1 selector-union construct (Story 2.3). ``then`` ALWAYS
    contributes — even when its value is missing/``None``/an unrecognized
    shape, which degrades to a marked ``RAW_MALFORMED`` leaf via
    ``_walk_if_branch`` rather than silently contributing nothing; ``else``
    is walked ONLY when the key is present at all (an absent ``else``
    contributes nothing — a two-way branch with no ``else`` is ordinary,
    valid v1 syntax, e.g. ``if: win / then: posix``). An entry carrying
    NEITHER key at all therefore still yields exactly ONE ``RAW_MALFORMED``
    leaf (from the ``then``-side degrade) rather than silently zero
    components (Review Pass 2 correction).

    Each leaf is tagged with a ``[if:COND]``/``[else:COND]``
    ``Provenance.section`` suffix and escalated to ``UNION_MARKED`` when it
    would otherwise be ``PARSED`` — see ``_identity.py::apply_union_tag``.
    ``outer_suffix`` carries the accumulated parent tags so nesting
    concatenates (an inner ``if`` inside an outer ``then``/``else`` yields
    e.g. ``[if:linux][if:x86_64]``, never overwriting the outer tag).

    The condition label is ``truncate_for_name``-bounded UNCONDITIONALLY —
    an arbitrary YAML scalar (string or not) must never embed unbounded
    into ``Provenance.section`` (NFR-S5; Review Pass 1 correction #5)."""
    cond_label = truncate_for_name(str(entry.get("if")))
    components: list[Component] = []
    components += _walk_if_branch(
        entry.get("then"),
        context,
        provenance,
        ecosystem,
        f"{outer_suffix}[if:{cond_label}]",
    )
    if "else" in entry:
        components += _walk_if_branch(
            entry.get("else"),
            context,
            provenance,
            ecosystem,
            f"{outer_suffix}[else:{cond_label}]",
        )
    return components


def _walk_if_branch(
    value: object,
    context: Mapping[str, str],
    provenance: tuple[Provenance, ...],
    ecosystem: Ecosystem,
    section_suffix: str,
) -> list[Component]:
    """ONE ``then``/``else`` value: a plain string is a leaf (through
    ``requirement_component`` — the SAME path any other entry takes); a
    list is walked item-by-item, RECURSING through this same function for
    each item (so a list item that is itself a nested ``if`` dict, or even
    another list, is handled identically to the top-level case — the exact
    "may nest" shape the Boundaries describe); a dict carrying an ``if``
    key is a NESTED conditional (recurse into ``walk_if_then_else``,
    concatenating the section suffix). Anything else — missing/``None``, a
    bare int, an ``if``-less dict, ... — is an unrecognized shape that
    degrades to ONE marked ``RAW_MALFORMED`` leaf rather than silently
    vanishing (Review Pass 1 correction #4, and its Review Pass 2
    extension: a missing/``None`` value — the shape ``entry.get("then")``
    yields when ``then`` is absent entirely — degrades exactly the same
    way, never a bare empty-list return). An explicitly EMPTY list
    (``then: []``) is the SAME class of degenerate shape (Review Pass 3
    fix) — contradicts "``then`` ALWAYS contributes" just as silently as a
    missing key would, so it degrades identically rather than falling
    through the loop below to a quiet empty return."""
    if isinstance(value, list) and value:
        components: list[Component] = []
        for item in value:
            components += _walk_if_branch(
                item, context, provenance, ecosystem, section_suffix
            )
        return components
    if isinstance(value, dict) and "if" in value:
        return walk_if_then_else(
            value, context, provenance, ecosystem, outer_suffix=section_suffix
        )
    if isinstance(value, str):
        component = requirement_component(value, context, provenance, ecosystem)
        if component is None:
            return []  # a compiler()/stdlib()/pin_subpackage() leaf: excluded
        return [apply_union_tag(component, section_suffix)]
    return [
        apply_union_tag(
            _raw_malformed(ecosystem, truncate_for_name(str(value)), provenance),
            section_suffix,
        )
    ]


def selector_tag_suffix(
    entry: object, selector_comments: Mapping[int, str] | None
) -> str | None:
    """The shared "look up a selector tag" half of the tag-building logic
    (the other half, "build the suffix, apply it, escalate the mode", is
    ``_identity.py::apply_union_tag``) — both ``walk_requirements`` below
    and ``meta_v0.py``'s own ``_walk_test`` call this, so the lookup lives
    in exactly one place. ``None`` unless ``entry`` carries a
    ``.source_line`` attribute (duck-typed, not an ``isinstance`` check
    against ``meta_v0.py::LineStr`` — importing it here would be circular:
    ``meta_v0.py`` already imports FROM this module) whose line was
    captured by ``meta_v0.py::capture_selector_comments``. Always ``None``
    for v1 (a plain ``str`` never carries ``.source_line``; v1's own call
    sites never pass ``selector_comments`` at all — v1 has no
    comment-selector idiom)."""
    if not selector_comments:
        return None
    line = getattr(entry, "source_line", None)
    if line is None:
        return None
    condition = selector_comments.get(line)
    if condition is None:
        return None
    return f"[sel:{condition}]"


def walk_requirements(
    requirements: object,
    path_prefix: str,
    context: Mapping[str, str],
    manifest: ScannedManifest,
    router: Router,
    *,
    sections: tuple[str, ...] = _TOP_LEVEL_SECTIONS,
    selector_comments: Mapping[int, str] | None = None,
) -> list[Component]:
    """Walk one ``requirements:``-shaped dict's ``sections`` lists.
    ``None``/a missing key/a non-list value degrade to "nothing here"
    rather than crash.

    A list entry that is a dict carrying an ``if`` key dispatches to
    ``walk_if_then_else`` (Story 2.3's v1 selector-union construct) instead
    of ``requirement_component``. ``requirement_component`` may now return
    ``None`` (a recognized build-tool/subpackage exclude) — filtered here.

    ``selector_comments`` (default ``None`` — every pre-2.3 AND every v1
    call site's behavior, unchanged) is ``meta_v0.py``'s v0-only ``#
    [cond]`` line->condition map, threaded here (rather than duplicated in
    a parallel walker) so v0's ``requirements.{build,host,run}``/
    ``outputs[].requirements`` sections get the SAME selector-tag
    application as ``meta_v0.py``'s own ``_walk_test``."""
    if not isinstance(requirements, dict):
        return []
    # fail-loud gate: asserted (not just called for its side effect) so a
    # future `_ROUTES` edit is caught HERE rather than silently continuing to
    # hardcode CONDA via `requirement_component`'s success path -- mirrors
    # `extract/pixi.py`/`environment_yml.py`'s identical Fix 7 (completed for
    # this walker 2026-07-16; the first pass patched only 2 of the 4
    # extractors). Holds for BOTH kinds routed through this shared walker
    # (recipe.yaml and meta.yaml both map (kind, "requirements") to CONDA).
    ecosystem = router.route(manifest.kind, RECIPE_V1_REQUIREMENTS_SECTION)
    assert ecosystem is Ecosystem.CONDA
    components: list[Component] = []
    for section in sections:
        entries = requirements.get(section)
        if not isinstance(entries, list):
            continue
        section_path = f"{path_prefix}.{section}"
        provenance = (Provenance(manifest=manifest.path, section=section_path),)
        for entry in entries:
            if isinstance(entry, dict) and "if" in entry:
                components += walk_if_then_else(entry, context, provenance, ecosystem)
                continue
            component = requirement_component(entry, context, provenance, ecosystem)
            if component is None:
                continue
            suffix = selector_tag_suffix(entry, selector_comments)
            if suffix is not None:
                component = apply_union_tag(component, suffix)
            components.append(component)
    return components


class RecipeV1Extractor:
    """Extract the common-case conda dependency set from a v1
    ``recipe.yaml`` (Story 2.2) — parse-as-data, never rendered."""

    def __init__(self, router: Router) -> None:
        self._router = router

    def extract(
        self, manifest_path: Path, manifest: ScannedManifest
    ) -> tuple[Component, ...]:
        text = read_bounded_text(
            manifest_path,
            manifest,
            max_bytes=_MAX_MANIFEST_BYTES,
            max_line_bytes=_MAX_LINE_BYTES,
        )
        text = strip_jinja_comments(text)
        text = neutralize_bare_braces(text)
        try:
            document = yaml_safe_load_strict(text)
            if document is None:
                return ()
            if not isinstance(document, dict):
                raise UnparsableManifestError(
                    f"unparsable manifest {manifest.path}: top-level document "
                    "is not a mapping"
                )
            context = context_map(document)
            components: list[Component] = []
            components += walk_requirements(
                document.get("requirements"),
                "requirements",
                context,
                manifest,
                self._router,
            )
            components += self._walk_tests(document.get("tests"), context, manifest)
            components += self._walk_outputs(document.get("outputs"), context, manifest)
        except (yaml.YAMLError, RecursionError) as exc:
            # RecursionError: not just yaml.safe_load's own parser recursion
            # on a hostile document -- ALSO the recursive if/then/else
            # walker above, on a pathologically nested (but well within the
            # 5MB manifest cap) construct (Story 2.3, Review Pass 1
            # correction #2, mirroring extract/pyproject.py's tomllib
            # precedent). This except clause is broader than that
            # precedent (which wraps only the parse call) BECAUSE it also
            # has to cover the walk -- an intentional, documented tradeoff,
            # not an oversight.
            raise UnparsableManifestError(
                f"unparsable manifest {manifest.path}: {exc}"
            ) from exc
        return tuple(components)

    def _walk_tests(
        self,
        tests: object,
        context: Mapping[str, str],
        manifest: ScannedManifest,
        *,
        prefix: str = "tests",
    ) -> list[Component]:
        if not isinstance(tests, list):
            return []
        components: list[Component] = []
        for index, test in enumerate(tests):
            if not isinstance(test, dict):
                continue
            components += walk_requirements(
                test.get("requirements"),
                f"{prefix}[{index}].requirements",
                context,
                manifest,
                self._router,
                sections=_TEST_SECTIONS,
            )
        return components

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
            # A multi-output recipe's PER-OUTPUT test deps
            # (`outputs[].tests[]`, same list-valued v1 shape as the top
            # level) -- walked since 2026-07-16: the top-level `tests[]` was
            # walked but its per-output analog silently produced no
            # components.
            components += self._walk_tests(
                output.get("tests"),
                context,
                manifest,
                prefix=f"outputs[{index}].tests",
            )
        return components
