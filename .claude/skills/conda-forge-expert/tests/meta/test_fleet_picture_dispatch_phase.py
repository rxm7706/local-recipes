"""Meta-test: factory-dispatch phase labels and completeness/projection in fleet_picture.py."""
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
FLEET_PICTURE = REPO_ROOT / "scripts" / "fleet_picture.py"


def _load_fleet_picture():
    spec = importlib.util.spec_from_file_location(
        "fleet_picture_dispatch_phase_under_test", FLEET_PICTURE
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["fleet_picture_dispatch_phase_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def _state(mod, **overrides):
    kwargs = dict(
        running=True,
        story="28-9-planning-graph-retrieval-behind-the-scribe-seam",
        hstate="running",
        done=100,
        total=120,
        backlog=20,
        dispatch_phase=None,
        ledger_done=False,
        queued_backlog=None,
    )
    kwargs.update(overrides)
    return mod.station_state(**kwargs)


def test_merged_chaining_when_ledger_done_and_phase_chaining():
    mod = _load_fleet_picture()
    cell = _state(mod, dispatch_phase="chaining", ledger_done=True)
    assert cell.startswith("CHAIN")
    assert "28-9-planning-graph-retrieva" in cell
    assert "(merged)" in cell


def test_verifying_uses_verify_prefix():
    mod = _load_fleet_picture()
    cell = _state(mod, dispatch_phase="verifying", ledger_done=False)
    assert cell.startswith("VERIFY")


def test_building_shows_queued_suffix():
    mod = _load_fleet_picture()
    cell = _state(mod, dispatch_phase="building", queued_backlog=6)
    assert cell.startswith("BUILDING")
    assert "[6 queued]" in cell


def test_stuck_on_verify_refused():
    mod = _load_fleet_picture()
    cell = _state(
        mod,
        dispatch_phase="building",
        verification_verdict="refused",
        verification_failed_gate="MRS-GATE-007",
    )
    assert cell.startswith("STUCK")
    assert "MRS-GATE-007" in cell


def test_not_stuck_when_refused_verdict_is_stale_and_a_different_engine_is_running():
    """Live incident 2026-09-10: `dispatch_verification_verdict` persists on
    the row until the NEXT dispatch run overwrites it -- it is not cleared
    when a different engine (spin) starts running on the same station. A
    station whose CURRENT live run is a spin session (`dispatch_phase=None`)
    must not be labeled STUCK off a `refused` verdict from an unrelated,
    much older dispatch attempt."""
    mod = _load_fleet_picture()
    cell = _state(
        mod,
        dispatch_phase=None,
        verification_verdict="refused",
        verification_failed_gate="MRS-GATE-007",
    )
    assert not cell.startswith("STUCK")
    assert cell.startswith("RUNNING")


def test_story_completeness_includes_all_backlog():
    mod = _load_fleet_picture()
    stories = {"a": "done", "b": "backlog", "c": "blocked"}
    assert mod.story_completeness(stories) == 2


def test_story_projection_idle_is_done_only():
    mod = _load_fleet_picture()
    stories = {"a": "done", "b": "backlog"}
    assert mod.story_projection(stories, queue_keys=["b"], dispatch_in_flight=False) == 1


def test_story_projection_active_uses_queue_keys():
    mod = _load_fleet_picture()
    stories = {
        "28-6-x": "backlog",
        "28-10-y": "backlog",
        "28-5-z": "done",
        "other": "backlog",
    }
    queue = ["28-5-z", "28-6-x", "28-10-y"]
    assert mod.story_projection(stories, queue_keys=queue, dispatch_in_flight=True) == 3
