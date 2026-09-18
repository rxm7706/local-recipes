"""Meta-test: the `awaiting-operator` state naming in fleet_picture.py.

Marshal Story 25.5 (spec-bmad-611-era-alignment CAP-5, absorbing DW-BL011-1):
bmad-loop 0.11's operator-parked run state must be NAMED
`awaiting-operator (run bmad-loop confirm)` wherever run state is shown —
never folded into the stopped/unsupervised "needs dispatch" bucket (the parked
story's work is already committed; `bmad-loop confirm` is the next action, not
a restart) and never shown as running/stalled/dead.

`station_state()` is the pure state-column helper extracted for exactly this
pin (driving `main()` would spawn the real `marshal status` subprocess sweep);
same importlib harness as test_fleet_picture_loop_home_staleness.py.
"""
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
FLEET_PICTURE = REPO_ROOT / "scripts" / "fleet_picture.py"

AWAITING_LABEL = "awaiting-operator (run bmad-loop confirm)"


def _load_fleet_picture():
    spec = importlib.util.spec_from_file_location(
        "fleet_picture_under_test", FLEET_PICTURE
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["fleet_picture_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def _state(mod, **overrides):
    kwargs = dict(running=False, story="", hstate="idle", done=0, total=5, backlog=0)
    kwargs.update(overrides)
    return mod.station_state(**kwargs)


def test_awaiting_operator_state_is_named_with_the_confirm_remedy():
    mod = _load_fleet_picture()
    cell = _state(mod, hstate="awaiting-operator", done=4, backlog=1)
    assert cell == AWAITING_LABEL
    assert cell == mod.AWAITING_OPERATOR_LABEL


def test_awaiting_operator_outranks_the_needs_dispatch_bucket():
    """The mislabel DW-BL011-1 names: a parked station with backlog left
    must NOT read '... left, needs dispatch' (the stopped/unsupervised
    shape) — the confirm is the next action, not a restart."""
    mod = _load_fleet_picture()
    cell = _state(mod, hstate="awaiting-operator", done=3, backlog=2)
    assert "needs dispatch" not in cell
    assert "re-spin" not in cell
    assert "STOPPED" not in cell and "UNSUPERVISED" not in cell
    assert cell == AWAITING_LABEL


def test_a_running_station_stays_running_never_the_parked_label():
    """A run actively driving another story stays RUNNING (a park never
    blocks siblings) — marshal only ever derives `awaiting-operator` when
    nothing is active, and the column mirrors that precedence."""
    mod = _load_fleet_picture()
    cell = _state(mod, running=True, story="25-3-active-story",
                  hstate="running", done=3, backlog=2)
    assert cell.startswith("RUNNING")
    assert "25-3-active-story" in cell
    assert AWAITING_LABEL not in cell


def test_every_pre_existing_state_cell_is_unchanged():
    """Regression guard for the extraction: the helper must reproduce
    main()'s original if/elif chain byte-for-byte for every non-parked
    shape."""
    mod = _load_fleet_picture()
    assert _state(mod, running=True, story="x" * 60, hstate="running") == (
        "RUNNING " + "x" * 28
    )
    assert _state(mod, hstate="paused-on-escalation") == (
        "PAUSED - needs you (escalation)"
    )
    assert _state(mod, hstate="stopped", backlog=2) == (
        "STOPPED - 2 left, needs dispatch"
    )
    assert _state(mod, hstate="unsupervised", backlog=1) == (
        "UNSUPERVISED - 1 left, needs dispatch"
    )
    assert _state(mod, hstate="unknown", backlog=3) == (
        "UNKNOWN - 3 left, needs dispatch"
    )
    assert _state(mod, hstate="idle", done=5, total=5) == "complete"
    assert _state(mod, hstate="idle", done=2, total=5, backlog=3) == (
        "idle - 3 not started"
    )
    assert _state(mod, hstate="idle", done=2, total=5, backlog=0) == "idle"
    # A stopped station with NO backlog falls through to the completion
    # branches, exactly as before the extraction.
    assert _state(mod, hstate="stopped", done=5, total=5, backlog=0) == "complete"
