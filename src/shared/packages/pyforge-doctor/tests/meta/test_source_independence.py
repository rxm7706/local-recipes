"""Independence is a property of the registry, not six habits (Story 6.10).

FR-15; AD-11, AD-12, AD-13. Charter §6: *"the Doctor holds the verdict on the
Marshal's conformance — the one station that would otherwise grade itself,"*
and more generally, the station that owns an artifact must never be the
final word on judging it. Six near-identical AST-walk tests used to encode
this one property, one per ``sources/*.py`` file
(``test_sources_marshal_independence.py``, ``_ledger_``, ``_board_``,
``_chain_``, ``_deps_``, ``_factory_``) — each hand-copied, each covering
only the file it was written for. ``sources/atlas.py`` had none of its own
and so had ZERO independence coverage despite judging six ``Source``
members (five wired axes plus the registered-but-not-yet-dispatched
``BEHIND_UPSTREAM``).

This module replaces all six: it is driven by ``sources.REGISTRY`` (Story
6.2) via ``SOURCE_MODULE``, a hand-maintained map from every in-scope
``Source`` to the ``sources/<file>.py`` that backs it, checked exhaustive in
BOTH directions below. A ``Source`` newly added to the registry without a
matching ``SOURCE_MODULE`` entry fails ``test_every_in_scope_source_is_
mapped_to_exactly_one_file`` — it cannot silently ship uncovered the way a
seventh per-file test could always be forgotten.

**Generalized rule (this story's one substantive decision).** The old
``deps.py`` file was stricter than its five siblings: AD-13 has it bar
``bmad_loop`` (the harness whose blindness it judges) in addition to every
station package. The pre-authored planning spec's own stated preference —
"generalise the rule to include harness packages, so 6.7's stricter
guarantee becomes the fleet default rather than a local accident" — is
applied here: every source's forbidden set includes ``bmad_loop``, not just
``deps.py``'s. Investigation (this story) confirmed this costs nothing today
— no other ``sources/*.py`` file references ``bmad_loop`` in any form.

**The one allowlisted exception.** ``sources/warden.py`` (AD-1, AD-11)
deliberately DOES import ``pyforge.warden`` — it relays warden's own
self-report about its own environment, which is not judging an artifact.
Recorded in ``_ALLOWLIST`` as an explicit ``{Source: reason}`` entry, not a
bare ``if`` skip, and it is still checked against every OTHER station plus
``bmad_loop`` (proved by ``test_warden_doctor_is_the_one_allowlisted_
exception``).

**Doctor itself is not in the forbidden set.** Every module here lives
inside ``pyforge.doctor.sources`` and legitimately self-references its own
package (``from ..models import Finding``, ``from ..cli_bridge import
run_cli_json``). ``owning_station`` is always ``"doctor"`` (Story 6.2's own
docstring: "Doctor holds every verdict"), so forbidding ``pyforge.doctor``
would flag every source's own necessary plumbing. This mirrors
``test_sources_chain_independence.py``/``test_sources_factory_
independence.py``'s own already-reviewed exclusion ("``doctor`` is
deliberately absent from the list: it is this module's OWN owning
station") — lifted here rather than re-litigated.

**``ENV_HYGIENE`` is out of scope, by construction, not by a hardcoded
exception list.** Its ``subject_station == owning_station == "doctor"``
(Doctor judging itself, via ``checks/env_hygiene.py`` — not a file in
``sources/`` at all). "In scope" is derived from ``REGISTRY`` as "every
source whose subject differs from its owner" rather than hand-enumerated,
so ``ENV_HYGIENE`` falls out of scope automatically and a future
self-judging source would too.

**The AST walk is lifted, not re-derived.** ``_resolve_relative``/
``_imported_modules`` are ``test_sources_chain_independence.py``'s /
``test_sources_factory_independence.py``'s fixed, RESOLVING variant —
verbatim, not the buggy ``if node.level: continue`` skip that four of the
six old files used, which let ``from ...marshal import policy`` through
undetected (that file's own docstring records the discovery). The
docstring-stripping logic for the string-constant scan is likewise
byte-identical across all six old files and reused here unchanged.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from pyforge.doctor.models import Source
from pyforge.doctor.sources import REGISTRY, SourceRegistration

# --- source -> backing file, exhaustive in both directions -----------------

#: Every ``sources/*.py`` file lives directly under this package -- a single
#: constant suffices for every file scanned here, unlike
#: ``test_no_warden_import.py``'s per-module resolution (which walks the
#: whole ``pyforge.doctor`` tree at varying depths).
SOURCE_PACKAGE = ("pyforge", "doctor", "sources")

SOURCES_DIR = Path(__file__).resolve().parents[2] / "src" / "pyforge" / "doctor" / "sources"

#: Hand-maintained: every ``Source`` "in scope" (see ``_in_scope_sources``)
#: mapped to the ONE ``sources/<file>.py`` that backs it. Multiple sources
#: legitimately share a file (e.g. every atlas Watch axis lives in
#: ``atlas.py``); ``test_every_real_sources_file_is_mapped_by_at_least_one_
#: source`` is what closes the OTHER direction, so a stray new file cannot
#: hide unmapped.
SOURCE_MODULE: dict[Source, str] = {
    Source.WARDEN_DOCTOR: "warden.py",
    Source.STALENESS_REPORT: "atlas.py",
    Source.CVE_WATCHER: "atlas.py",
    Source.BEHIND_UPSTREAM: "atlas.py",  # registered (Story 6.2), not yet
    # dispatched by atlas.py's own gather() -- still atlas's own subject and
    # atlas's own file, so it belongs here regardless of wiring status.
    Source.FEEDSTOCK_HEALTH: "atlas.py",
    Source.RELEASE_CADENCE: "atlas.py",
    Source.MARSHAL_DURABILITY: "marshal.py",
    Source.ADOPTION: "atlas.py",
    Source.LEDGER_REGRESSION: "ledger.py",
    Source.LEDGER_DIRECTION: "ledger.py",  # Story 15.2 (marshal FR-137/138)
    Source.STORY_STATUS: "marshal.py",
    Source.CHAIN_COMPLETENESS: "board.py",
    Source.DASHBOARD_DRIFT: "board.py",
    Source.CHECK_LAYOUT: "board.py",
    Source.DREAM_CHAIN: "chain.py",
    Source.SPEC_SURFACE: "chain.py",
    Source.DEFERRED_WORK: "chain.py",
    Source.FORWARD_DEPENDENCY: "deps.py",
    Source.BMAD_DRIFT: "factory.py",
    Source.BMAD_OUTPUT_HYGIENE: "hygiene.py",
    Source.DUE_FOR_VERIFICATION: "chain.py",  # Story 11.1 (Epic 11/CAP-1)
    Source.BMAD_METHOD_VERSION_DRIFT: "bmad_method.py",  # Story 10.1 (Epic 10/CAP-1)
    Source.BACKLOG_INTAKE: "backlog_intake.py",  # Story 13.1 (Epic 13/CAP-1)
    Source.SIBLING_DREAMS_DRIFT: "sibling_dreams.py",  # Story 16.1 (Epic 16/CAP-1)
    Source.DREAMS_HYGIENE: "chain.py",  # Story 17.2 (Epic 17 / FR-147)
    Source.CHAIN_LAYERS_AUDIT: "board.py",  # Story 17.3 (Epic 17 / FR-150)
    Source.PLATFORM_POLICY_SUITE: "platform_policy.py",  # retro action item 3
    # (retro-pyforge-steward-2026-09-04.md, 2026-09-05)
    Source.BMAD_RENDER_CONFIG_AMBIGUITY: "bmad_config.py",  # Story 20.2 (Epic 20)
    Source.FROZEN_PATH_CHANGED: "frozen_path.py",  # Story 20.3 (Epic 20)
    Source.CAPABILITY_EFFECT: "capability_effect.py",  # Story 21.10 (Epic 21)
    Source.STATUS_BODY_CONSISTENCY: "status_body_consistency.py",  # Story 21.12
    Source.PIXI_CURRENCY_LEDGER: "pixi_currency.py",  # Story 21.7
    Source.GENERAL_DOCS_CONSISTENCY: "general_docs_consistency.py",  # Story 22.3
    Source.CAPABILITY_LEDGER: "capability_ledger.py",  # Story 55.2
    Source.CHAIN_SPRAWL: "one_chain.py",  # Story 25.1 (spec-one-chain-per-station CAP-2)
    Source.FR_WITHOUT_CAP: "one_chain.py",  # Story 25.2 (spec-one-chain-per-station CAP-5)
    Source.DOCS_MAP_HYGIENE: "docs_map_hygiene.py",  # Story 30.1 (spec-pyforge-doctor CAP-83)
    Source.DOCS_SHELF_OCCUPANCY: "docs_shelf.py",  # Story 23.7 (spec-pyforge-doctor CAP-54)
    Source.LIVE_PROOF_SURFACE: "live_proof_surfaces.py",  # Story 26.1 (spec-pyforge-doctor CAP-77)
    Source.DOCS_CURRENCY: "docs_currency.py",  # Story 30.2 (spec-pyforge-doctor CAP-84)
}

#: The one allowlisted exception (AD-11) -- a mapping, not a bare ``if``
#: skip, so the reason is recorded in code where the rule lives.
_ALLOWLIST: dict[Source, str] = {
    Source.WARDEN_DOCTOR: (
        "AD-11's stated exception: sources/warden.py relays warden's own "
        "self-report about its own environment (AD-1) -- it is not judging "
        "an artifact, so importing pyforge.warden here is not the Charter "
        "§6 violation the rest of this file guards against."
    ),
}

#: The closed roster of station packages this file can forbid. ``doctor`` is
#: deliberately excluded -- see the module docstring's "Doctor itself is not
#: in the forbidden set" section.
_ALL_STATIONS: tuple[str, ...] = (
    "herald",
    "marshal",
    "atlas",
    "warden",
    "mason",
    "scribe",
    "steward",
)


def _in_scope_sources() -> frozenset[Source]:
    """Every ``Source`` whose subject differs from its owner -- derived from
    ``REGISTRY``, never hand-enumerated, so ``ENV_HYGIENE`` (subject ==
    owner == "doctor", Doctor judging itself) falls out of scope by
    construction, and any future self-judging source would too."""
    return frozenset(
        registration.source for registration in REGISTRY if registration.subject_station != registration.owning_station
    )


def _subject_station_of(source: Source) -> str:
    for registration in REGISTRY:
        if registration.source is source:
            return registration.subject_station
    raise ValueError(f"{source!r} has no REGISTRY entry")  # exhaustiveness
    # tests below already guarantee every SOURCE_MODULE key resolves here.


def _forbidden_stations_for(source: Source) -> tuple[str, ...]:
    """``_ALL_STATIONS``, minus the subject a ``_ALLOWLIST`` entry excuses.
    ``bmad_loop`` is handled separately (added unconditionally, below) --
    it is harness machinery, not a ``pyforge.<station>`` package."""
    if source in _ALLOWLIST:
        subject = _subject_station_of(source)
        return tuple(station for station in _ALL_STATIONS if station != subject)
    return _ALL_STATIONS


# --- the AST walk (lifted verbatim from chain.py's/factory.py's fixed,
# resolving variant -- NOT the buggy `if node.level: continue` skip four of
# the six old files used) -----------------------------------------------


def _resolve_relative(level: int, module: str | None) -> str | None:
    """A relative import's ABSOLUTE dotted name, as Python itself would
    resolve it from a ``sources/*.py`` module's own package. Relative
    imports must be resolved, not skipped: from ``pyforge/doctor/sources/``,
    level 3 IS the ``pyforge`` namespace, so ``from ...marshal import
    policy`` reaches the judged station and would pass a scan that skips
    ``node.level`` outright (the bug four of the six old files carried).

    ``level - 1 >= len(SOURCE_PACKAGE)`` (review pass 1 fix): a level one
    past the package root (e.g. 4 dots from ``sources/``) must resolve to
    nothing, not to a bare, unprefixed name -- the prior ``>`` let exactly
    that one boundary level through, which real Python would refuse to
    import (``ImportError: attempted relative import beyond top-level
    package``) but which would otherwise have produced a name too short to
    ever match a ``pyforge.<station>`` forbidden check."""
    base = SOURCE_PACKAGE[: len(SOURCE_PACKAGE) - (level - 1)]
    if len(base) != len(SOURCE_PACKAGE) - (level - 1) or level - 1 >= len(SOURCE_PACKAGE):
        return None
    parts = [*base, *(module.split(".") if module else [])]
    return ".".join(parts) if parts else None


def _imported_modules(tree: ast.AST) -> set[str]:
    """Every module named by an import, including inside function bodies --
    a lazy import in a ``gather()`` would evade a module-header-only scan,
    and lazy is exactly how ``sources/warden.py`` legitimately imports
    warden. Relative imports are RESOLVED against the module's own package
    (see ``_resolve_relative``) rather than skipped.

    Both the base module AND ``base.name`` for each imported name are
    recorded (review pass 1 fix): ``from pyforge import marshal`` names the
    judged station only via ``node.names``, never combined with
    ``node.module`` -- a scan that added just ``node.module`` ("pyforge")
    let this absolute symbol-import form through completely undetected."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                resolved = _resolve_relative(node.level, node.module)
                if resolved:
                    names.add(resolved)
                    names.update(f"{resolved}.{alias.name}" for alias in node.names)
            elif node.module:
                names.add(node.module)
                names.update(f"{node.module}.{alias.name}" for alias in node.names)
    return names


def _forbidden_import_offenders(tree: ast.AST, forbidden_stations: tuple[str, ...]) -> list[str]:
    """Every imported module that names a forbidden station package or
    ``bmad_loop`` (checked unconditionally -- the generalized AD-13 rule)."""
    imported = _imported_modules(tree)
    offenders = {
        module
        for module in imported
        if any(
            module == f"pyforge.{station}" or module.startswith(f"pyforge.{station}.") for station in forbidden_stations
        )
        or module == "bmad_loop"
        or module.startswith("bmad_loop.")
    }
    return sorted(offenders)


def _docstring_node_ids(tree: ast.AST) -> set[int]:
    """The ``id()`` of every module/class/function docstring's ``Constant``
    node -- every ``sources/*.py`` module names its own forbidden packages
    repeatedly while explaining why it must not import them, so a naive
    string scan fails on the documentation itself."""
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                docstrings.add(id(body[0].value))
    return docstrings


def _string_constant_offenders(tree: ast.AST, forbidden_texts: tuple[str, ...]) -> list[str]:
    """Every forbidden substring found in a non-docstring string constant --
    catches an import smuggled past the AST scan (``importlib.import_
    module``, ``__import__``, a subprocess invoking the CLI).

    Matched at word boundaries (review pass 1 fix): a plain ``in`` substring
    check flagged ``"see pyforge.marshaling_utils for the json-marshal
    helper"`` as containing ``"pyforge.marshal"`` -- an unrelated identifier
    that merely starts with the forbidden dotted name. ``\\b`` around the
    escaped forbidden text still matches a real reference immediately
    followed by ``.`` (a submodule, e.g. ``pyforge.marshal.policy``) or by
    nothing, since ``.`` is itself a non-word character."""
    docstrings = _docstring_node_ids(tree)
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
            for forbidden in forbidden_texts:
                if re.search(rf"\b{re.escape(forbidden)}\b", node.value):
                    found.append(forbidden)
    return found


def _forbidden_texts_for(source: Source) -> tuple[str, ...]:
    texts: list[str] = []
    for station in _forbidden_stations_for(source):
        texts.append(f"pyforge.{station}")
        texts.append(f"pyforge_{station}")
    texts.append("bmad_loop")
    return tuple(texts)


# --- exhaustiveness: the mapping cannot silently drift from either side ----


def test_every_in_scope_source_is_mapped_to_exactly_one_file():
    # Two-directional-in-spirit: SOURCE_MODULE's keys must equal exactly the
    # in-scope Source set -- a Source with no entry, or a stray entry for a
    # Source no longer in scope, both fail here rather than passing silently
    # (mirrors test_sources_registry.py's own REGISTRY<->Source discipline).
    assert set(SOURCE_MODULE.keys()) == _in_scope_sources()


def test_env_hygiene_is_out_of_scope_by_design():
    """The one Source excluded from SOURCE_MODULE, and why: it judges
    Doctor's own artifact (self), not another station's -- there is no
    "judged station package" to forbid, and no backing file in sources/ for
    it (its gather lives in checks/env_hygiene.py)."""
    assert Source.ENV_HYGIENE not in SOURCE_MODULE
    registration = next(r for r in REGISTRY if r.source is Source.ENV_HYGIENE)
    assert registration.subject_station == registration.owning_station == "doctor"


#: Dunder modules in ``sources/`` that are packaging/entrypoint machinery, never a
#: ``Source`` implementation, and therefore have no ``SOURCE_MODULE`` entry to map and
#: no single "judged station" to scan for independence. Named exhaustively rather than
#: matched by a ``__*__`` pattern, so adding a third one is a deliberate edit here and
#: not an accident that silently widens the exemption. ``__main__.py`` joined on
#: 2026-08-10 when doctor story 6-9 landed the sources dispatcher: it imports EVERY
#: source by design, so an independence scan over it is meaningless, and it gathers
#: nothing itself.
NON_SOURCE_MODULES = frozenset({"__init__.py", "__main__.py"})


def test_every_real_sources_file_is_mapped_by_at_least_one_source():
    # rglob, not glob (review pass 1 fix): a future sources/<subpkg>/impl.py
    # must still be caught as unmapped here, not left invisible to a
    # top-level-only scan.
    real_files = {path.name for path in SOURCES_DIR.rglob("*.py") if path.name not in NON_SOURCE_MODULES}
    mapped_files = set(SOURCE_MODULE.values())
    unmapped = real_files - mapped_files
    assert not unmapped, (
        f"sources/ file(s) with no SOURCE_MODULE entry: {sorted(unmapped)} -- "
        "an unmapped file must be a failure here, never a silent gap"
    )


def test_every_mapped_filename_actually_exists():
    # The reverse typo-guard: a SOURCE_MODULE entry naming a file that
    # doesn't exist would otherwise silently never be scanned below.
    real_files = {path.name for path in SOURCES_DIR.rglob("*.py") if path.name not in NON_SOURCE_MODULES}
    missing = set(SOURCE_MODULE.values()) - real_files
    assert not missing, f"SOURCE_MODULE references missing file(s): {sorted(missing)}"


def test_warden_doctor_is_the_one_allowlisted_exception():
    assert set(_ALLOWLIST) == {Source.WARDEN_DOCTOR}
    forbidden = _forbidden_stations_for(Source.WARDEN_DOCTOR)
    assert "warden" not in forbidden
    assert set(forbidden) == set(_ALL_STATIONS) - {"warden"}


# --- SourceRegistration.__post_init__ fails loud (proven here too, so this
# file stands alone -- mirrors test_sources_registry.py's own proof) -------


def test_a_registration_missing_subject_station_fails_loud_at_construction():
    with pytest.raises(ValueError, match="subject_station"):
        SourceRegistration(
            source=Source.MARSHAL_DURABILITY,
            scope="repo",
            subject_station="",
            owning_station="doctor",
        )


# --- the real scan, parametrized over the registry-derived mapping --------

_SOURCE_MODULE_CASES = sorted(SOURCE_MODULE.items(), key=lambda kv: kv[0].value)
_SOURCE_MODULE_IDS = [f"{source.value}:{filename}" for source, filename in _SOURCE_MODULE_CASES]


@pytest.mark.parametrize("source,filename", _SOURCE_MODULE_CASES, ids=_SOURCE_MODULE_IDS)
def test_source_never_imports_a_forbidden_station_or_the_harness(source: Source, filename: str) -> None:
    """No source imports the package of the station it judges (or any other
    non-self, non-allowlisted station), and none imports ``bmad_loop`` --
    including lazy imports and resolved relative imports."""
    tree = ast.parse((SOURCES_DIR / filename).read_text(encoding="utf-8"))
    offenders = _forbidden_import_offenders(tree, _forbidden_stations_for(source))
    assert not offenders, (
        f"sources/{filename} (judging {source.value!r}) imports forbidden "
        f"package(s): {offenders}. Charter §6 -- a judging source must not "
        "depend on the machinery of the station (or harness) it judges."
    )


@pytest.mark.parametrize("source,filename", _SOURCE_MODULE_CASES, ids=_SOURCE_MODULE_IDS)
def test_source_has_no_textual_reference_that_would_execute(source: Source, filename: str) -> None:
    """Catches an import smuggled past the AST scan via a string constant
    that could reach ``importlib.import_module``/``__import__`` -- comments
    and docstrings are stripped first, since every one of these modules
    names its own forbidden packages while explaining why it must not
    import them."""
    tree = ast.parse((SOURCES_DIR / filename).read_text(encoding="utf-8"))
    offenders = _string_constant_offenders(tree, _forbidden_texts_for(source))
    assert not offenders, (
        f"a string constant in sources/{filename} (judging {source.value!r}) "
        f"contains forbidden text: {offenders}, which could be used to "
        "import or invoke the judged station/harness dynamically."
    )


# --- the guard actually fires: one synthetic proof per violation shape ----


def test_guard_fires_on_synthetic_module_level_import():
    tree = ast.parse("import pyforge.marshal\n")
    assert _forbidden_import_offenders(tree, _ALL_STATIONS) == ["pyforge.marshal"]


def test_guard_fires_on_synthetic_lazy_import():
    # A lazy import inside a function body is exactly how sources/warden.py
    # legitimately imports warden -- the guard must catch it just as surely
    # as a module-level import when it is NOT the allowlisted exception.
    tree = ast.parse("def gather():\n    from pyforge.marshal import policy\n    return policy\n")
    assert "pyforge.marshal" in _forbidden_import_offenders(tree, _ALL_STATIONS)


def test_guard_fires_on_synthetic_relative_import_resolving_to_a_station():
    # The bug this file must not re-introduce: a naive `node.level: continue`
    # skip lets `from ...marshal import policy` through undetected, because
    # it resolves to pyforge.marshal from sources/'s own package depth.
    tree = ast.parse("from ...marshal import policy\nfrom ..models import Finding\n")
    assert _imported_modules(tree) == {
        "pyforge.marshal",
        "pyforge.marshal.policy",
        "pyforge.doctor.models",
        "pyforge.doctor.models.Finding",
    }
    assert "pyforge.marshal" in _forbidden_import_offenders(tree, _ALL_STATIONS)


def test_guard_fires_on_synthetic_absolute_symbol_import():
    # Review pass 1 fix: `from pyforge import marshal` names the judged
    # station only via node.names, never combined with node.module ("pyforge"
    # alone) -- a scan that recorded just the base module let this absolute
    # symbol-import form through completely undetected.
    tree = ast.parse("from pyforge import marshal\n")
    assert "pyforge.marshal" in _imported_modules(tree)
    assert _forbidden_import_offenders(tree, _ALL_STATIONS) == ["pyforge.marshal"]


def test_guard_fires_on_synthetic_bmad_loop_import():
    # The generalized AD-13 rule: bmad_loop is forbidden for every source,
    # not only deps.py.
    tree = ast.parse("import bmad_loop\n")
    assert _forbidden_import_offenders(tree, _ALL_STATIONS) == ["bmad_loop"]
    lazy = ast.parse(
        "def gather():\n    from bmad_loop.sprintstatus import ACTIONABLE_STATUSES\n    return ACTIONABLE_STATUSES\n"
    )
    assert "bmad_loop.sprintstatus" in _forbidden_import_offenders(lazy, _ALL_STATIONS)


def test_guard_does_not_fire_on_a_lookalike_identifier_past_the_word_boundary():
    # Review pass 1 fix: a plain substring check flagged an unrelated
    # identifier ("pyforge.marshaling_utils") merely starting with the
    # forbidden dotted name -- word-boundary matching must not repeat it.
    tree = ast.parse('DOC_LINK = "see pyforge.marshaling_utils for the json-marshal helper"\n')
    assert _string_constant_offenders(tree, ("pyforge.marshal",)) == []


def test_guard_fires_on_a_real_reference_immediately_followed_by_a_dot():
    # The word-boundary fix must not overcorrect: a real submodule reference
    # is still caught even with no trailing space.
    tree = ast.parse('BAD = "reach pyforge.marshal.policy dynamically"\n')
    assert _string_constant_offenders(tree, ("pyforge.marshal",)) == ["pyforge.marshal"]


def test_resolve_relative_rejects_the_level_one_past_the_package_root():
    # Review pass 1 fix: level - 1 == len(SOURCE_PACKAGE) (4 dots from
    # sources/) used to fall through to a bare, unprefixed name instead of
    # None -- real Python refuses this import entirely (attempted relative
    # import beyond top-level package).
    assert _resolve_relative(4, "marshal") is None
    assert _resolve_relative(3, "marshal") == "pyforge.marshal"  # still valid


def test_guard_fires_on_synthetic_string_constant_past_stripped_docstring():
    tree = ast.parse(
        '"""explains why this module must never reach pyforge.marshal."""\nBAD = "reach pyforge.marshal dynamically"\n'
    )
    assert _string_constant_offenders(tree, ("pyforge.marshal",)) == ["pyforge.marshal"]


def test_guard_does_not_fire_on_a_docstring_mentioning_the_forbidden_name():
    # Every real sources/*.py module names its own forbidden package(s)
    # repeatedly while explaining why it must not import them -- a naive
    # scan that didn't strip docstrings first would fail every one of them.
    tree = ast.parse(
        '"""this module must never import pyforge.marshal or bmad_loop."""\nGOOD = "a perfectly ordinary string"\n'
    )
    assert _string_constant_offenders(tree, ("pyforge.marshal", "bmad_loop")) == []
