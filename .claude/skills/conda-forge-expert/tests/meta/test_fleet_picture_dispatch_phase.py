"""Meta-test: factory-dispatch phase labels in fleet_picture.py.

When marshal status reports ``dispatch_phase`` alongside a running station,
``station_state()`` names the tail explicitly — especially ``merged, chaining``
when the tracked ledger already marks the current story done but marshal still
carries it while the drain chains to the next dispatch.
"""
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
    )
    kwargs.update(overrides)
    return mod.station_state(**kwargs)


def test_merged_chaining_when_ledger_done_and_phase_chaining():
    mod = _load_fleet_picture()
    cell = _state(mod, dispatch_phase="chaining", ledger_done=True)
    assert cell.startswith("RUNNING")
    assert "28-9-planning-graph-retrieval-behind-t" in cell
    assert "(merged, chaining)" in cell


def test_verifying_suffix_without_ledger_done():
    mod = _load_fleet_picture()
    cell = _state(mod, dispatch_phase="verifying", ledger_done=False)
    assert "(verifying)" in cell
    assert "merged" not in cell


def test_building_stays_plain_running():
    mod = _load_fleet_picture()
    cell = _state(mod, dispatch_phase="building")
    assert cell == "RUNNING  28-9-planning-graph-retrieval-behind-t"


def test_ledger_story_done_matches_epic_seq_prefix():
    mod = _load_fleet_picture()
    stories = {
        "28-9-planning-graph-retrieval-behind-the-scribe-seam": "done",
        "28-10-next-story": "backlog",
    }
    assert mod.ledger_story_done(stories, "28-9-planning-graph-retrieval-behind-the-scribe-seam")
    assert not mod.ledger_story_done(stories, "28-10-next-story")
