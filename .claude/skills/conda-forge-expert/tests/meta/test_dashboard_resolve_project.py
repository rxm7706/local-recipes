"""Meta: `pyforge.doctor.sources.fleet_scan`'s `resolve_project()` is the one place
a roster/campaign slug becomes real filesystem state (marshal S-16.1,
FR-140..143 -- spec-dashboard-project-path-derivation CAP-1..CAP-4).

Loads the REAL `generate.py` via the same `importlib.util.spec_from_file_
location` dynamic-load mechanism `pyforge-doctor`'s own
`_load_dashboard_generate` uses (see
`src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_dashboard_
drift.py`), so these tests exercise the shipped resolver, not a
reimplementation of it that could drift from the real logic.

Covers every row of the story's I/O & Edge-Case Matrix:
  * bare-key happy path (default derivation, real project)
  * slug != directory override (presenton-pixi-image -> pyforge-mason)
  * dissolved, no tree (pyforge-genesis -> docs/governance redirect)
  * a newly discovered project directory resolves with zero table edits
  * an unresolvable slug raises (FR-143's loud failure)
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# .claude/skills/conda-forge-expert/tests/meta/<file> -> repo root.
REPO_ROOT = Path(__file__).resolve().parents[5]
GENERATE_PY = REPO_ROOT / "scripts" / "fleet_scan.py"


def _load_generate():
    """Fresh module object per call -- callers that monkeypatch REPO_ROOT
    must not leak that patch into another test's import."""
    spec = importlib.util.spec_from_file_location(
        "_test_dashboard_generate_resolve_project", GENERATE_PY)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.modules.pop(spec.name, None)
    return mod


@pytest.fixture(scope="module")
def gen():
    if not GENERATE_PY.is_file():
        pytest.skip("pyforge.doctor.sources.fleet_scan not present in this checkout")
    return _load_generate()


# --- I/O Matrix: bare-key happy path -----------------------------------------


def test_bare_key_happy_path_resolves_default_project_dir(gen):
    """`resolve_project("marshal")` -> project_dir="pyforge-marshal" with the
    standard per-project paths, no override consulted."""
    r = gen.resolve_project("marshal")
    assert r.project_dir == "pyforge-marshal"
    assert r.epics_path == "_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md"
    assert r.sprint_status_path == (
        "_bmad-output/projects/pyforge-marshal/implementation-artifacts/sprint-status.yaml")
    assert r.ledger_path == (
        "_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml")
    assert r.redirect is None


def test_bare_key_already_prefixed_is_left_alone(gen):
    """A slug that already carries the `pyforge-` prefix (as CAMPAIGN_ROSTER's
    slugs do) is not double-prefixed."""
    r = gen.resolve_project("pyforge-marshal")
    assert r.project_dir == "pyforge-marshal"


# --- I/O Matrix: slug != directory override ----------------------------------


def test_slug_directory_override_resolves_to_owning_project(gen):
    """`resolve_project("presenton-pixi-image")` -> project_dir="pyforge-mason"
    with an explicit epics_path pointing at the non-default filename inside
    mason's tree -- the live proof the resolver handles slug != directory."""
    r = gen.resolve_project("presenton-pixi-image")
    assert r.project_dir == "pyforge-mason"
    assert r.epics_path == (
        "_bmad-output/projects/pyforge-mason/planning-artifacts/"
        "epics-presenton-pixi-image.md")
    assert r.ledger_path is None  # not cleanly split from mason's shared ledger
    # Explicit None, not a silent default onto mason's own real sprint-status
    # feed -- presenton-pixi-image has no live feed of its own.
    assert r.sprint_status_path is None
    assert r.redirect is None


def test_absorbed_satellite_with_no_epics_yet_is_explicit_none(gen):
    """wasm-analytics-stack/unity-data-stack: absorbed into pyforge-atlas,
    PRD+architecture only by design -- epics_path is explicit None, never a
    guessed (and wrong) pyforge-atlas/planning-artifacts/epics.md."""
    for slug in ("wasm-analytics-stack", "unity-data-stack"):
        r = gen.resolve_project(slug)
        assert r.project_dir == "pyforge-atlas"
        assert r.epics_path is None
        assert r.ledger_path is None
        # Explicit None, not a silent default onto atlas's own real feed.
        assert r.sprint_status_path is None


# --- I/O Matrix: dissolved, no tree ------------------------------------------


def test_dissolved_slug_has_no_project_dir_and_an_explicit_redirect(gen):
    """`resolve_project("pyforge-genesis")` -> project_dir=None,
    redirect="docs/governance", and none of the three derived paths guess a
    tree that no longer exists -- its own data shape, never force-fit into
    the absorbed-satellite shape."""
    r = gen.resolve_project("pyforge-genesis")
    assert r.project_dir is None
    assert r.redirect == "docs/governance"
    assert r.epics_path is None
    assert r.sprint_status_path is None
    assert r.ledger_path is None


# --- I/O Matrix: new station, zero table edits -------------------------------


def test_new_station_resolves_via_discovery_with_zero_table_edits(gen, tmp_path, monkeypatch):
    """A brand-new `_bmad-output/projects/pyforge-<x>/planning-artifacts/
    epics.md` appearing resolves through the DEFAULT branch -- no
    `_PROJECT_OVERRIDES` edit required -- as long as its directory exists."""
    proj = tmp_path / "_bmad-output" / "projects" / "pyforge-newstation" / "planning-artifacts"
    proj.mkdir(parents=True)
    (proj / "epics.md").write_text("# epics\n", encoding="utf-8")

    monkeypatch.setattr(gen, "REPO_ROOT", tmp_path)
    r = gen.resolve_project("newstation")
    assert r.project_dir == "pyforge-newstation"
    assert r.epics_path == "_bmad-output/projects/pyforge-newstation/planning-artifacts/epics.md"
    assert "newstation" not in gen._PROJECT_OVERRIDES


def test_discovered_board_keys_picks_up_the_new_station(gen, tmp_path, monkeypatch):
    """CAP-2: PROJECT_SOURCES's key set is DISCOVERED from the tracked
    epics.md glob, not hand-declared -- a fresh project appears with zero
    generate.py edits."""
    proj = tmp_path / "_bmad-output" / "projects" / "pyforge-newstation" / "planning-artifacts"
    proj.mkdir(parents=True)
    (proj / "epics.md").write_text("# epics\n", encoding="utf-8")

    monkeypatch.setattr(gen, "REPO_ROOT", tmp_path)
    assert gen._discovered_board_keys() == ["newstation"]


def test_discovered_board_keys_raises_on_key_collision(gen, tmp_path, monkeypatch):
    """Two directories that strip to the same bare board key (e.g. a future
    non-`pyforge-`-prefixed sibling of an existing station) must not
    silently clobber one another in the PROJECT_SOURCES dict comprehension
    -- that would drop a whole station's board line with no warning, the
    exact silent-misrouting class CAP-4 exists to make loud."""
    projects = tmp_path / "_bmad-output" / "projects"
    for dir_name in ("pyforge-collide", "collide"):
        proj = projects / dir_name / "planning-artifacts"
        proj.mkdir(parents=True)
        (proj / "epics.md").write_text("# epics\n", encoding="utf-8")

    monkeypatch.setattr(gen, "REPO_ROOT", tmp_path)
    with pytest.raises(ValueError, match="collide"):
        gen._discovered_board_keys()


# --- I/O Matrix: unresolvable slug (FR-143 loud failure) ---------------------


def test_unresolvable_slug_raises(gen):
    """A slug with no override and no matching `_bmad-output/projects/<dir>`
    is unresolvable -- the exception names the offending slug (FR-143)."""
    with pytest.raises(gen.UnresolvableProjectError) as exc_info:
        gen.resolve_project("definitely-not-a-real-station")
    assert exc_info.value.slug == "definitely-not-a-real-station"
    assert "definitely-not-a-real-station" in str(exc_info.value)


def test_unresolvable_slug_against_empty_tree_still_raises(gen, tmp_path, monkeypatch):
    """Same scenario, isolated from the live repo: an empty `_bmad-output/
    projects/` tree resolves nothing for a bare key with no override."""
    (tmp_path / "_bmad-output" / "projects").mkdir(parents=True)
    monkeypatch.setattr(gen, "REPO_ROOT", tmp_path)
    with pytest.raises(gen.UnresolvableProjectError):
        gen.resolve_project("ghost-station")


# --- one resolver, one override table: attribute-surface + no-second-place --


def test_project_sources_is_derived_and_non_empty(gen):
    """CAP-2: PROJECT_SOURCES is populated, and every value matches what
    resolve_project() itself would compute for that key -- a single source
    of truth, not two producers that could drift apart."""
    assert gen.PROJECT_SOURCES
    for key, rel in gen.PROJECT_SOURCES.items():
        assert gen.resolve_project(key).sprint_status_path == rel


def test_backward_compat_attributes_present_for_doctor_pin(gen):
    """`pyforge-doctor`'s dynamic-load contract test pins these three
    attributes by name and shape -- verify the shape holds after the
    resolver refactor (Boundaries: equivalent shape/values to today)."""
    assert isinstance(gen.PROJECT_SOURCES, dict) and gen.PROJECT_SOURCES
    assert isinstance(gen._KEY_SLUG_OVERRIDE, dict)
    assert isinstance(gen._DERIVE_EXCLUDE, set)


def test_project_overrides_table_holds_only_dissolved_absorbed_entries(gen):
    """CAP-1: one override table, dissolved/absorbed divergences only."""
    assert set(gen._PROJECT_OVERRIDES) == {
        "pyforge-genesis", "presenton-pixi-image",
        "wasm-analytics-stack", "unity-data-stack",
    }


# --- _PROJECT_OVERRIDES schema validation ------------------------------------


def test_validate_project_overrides_accepts_the_real_table(gen):
    """The live table must pass its own validation (it does, at import time
    -- re-running it here pins that it keeps passing as the table evolves)."""
    gen._validate_project_overrides(gen._PROJECT_OVERRIDES)


def test_validate_project_overrides_rejects_missing_project_dir(gen):
    with pytest.raises(ValueError, match="omits required key 'project_dir'"):
        gen._validate_project_overrides({"bad-slug": {"redirect": "docs/governance"}})


def test_validate_project_overrides_rejects_unknown_key(gen):
    with pytest.raises(ValueError, match="unknown key"):
        gen._validate_project_overrides(
            {"bad-slug": {"project_dir": "pyforge-mason", "epic_path": "typo.md"}})


def test_validate_project_overrides_rejects_no_tree_without_redirect(gen):
    with pytest.raises(ValueError, match="no redirect"):
        gen._validate_project_overrides({"bad-slug": {"project_dir": None}})
