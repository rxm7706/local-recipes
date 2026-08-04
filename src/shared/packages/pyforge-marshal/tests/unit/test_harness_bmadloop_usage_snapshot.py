"""Unit tests for ``pyforge.marshal.adapters.harness_bmadloop.BmadLoopHarness``'s
Story 3.6 addition (``usage_snapshot``, AD-9/AD-32) -- the budget ceilings'
own usage-read seam.

Exercised against REAL ``state.json`` fixtures written to ``tmp_path``, read
back through the REAL installed ``bmad_loop`` 0.9.0 (``bmad_loop.journal.
load_state``, mirroring ``test_harness_bmadloop_spin.py``'s own
``story_feed_keys`` convention of exercising the real package rather than a
fake -- no subprocess involved here, unlike ``spin``/``stop``/``resume``,
since ``usage_snapshot`` never shells out at all).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pyforge.marshal.adapters.harness_bmadloop import BmadLoopHarness
from pyforge.marshal.ports.harness import UsageSnapshot


@pytest.fixture
def harness() -> BmadLoopHarness:
    return BmadLoopHarness()


def _write_state(
    project: Path, run_id: str, *, tasks: dict[str, object], cache_read_weight: float = 0.1
) -> Path:
    run_dir = project / ".bmad-loop" / "runs" / run_id
    run_dir.mkdir(parents=True)
    state = {
        "run_id": run_id,
        "project": str(project),
        "started_at": "2026-08-03T00:00:00Z",
        "policy_snapshot": {"limits": {"cache_read_weight": cache_read_weight}},
        "tasks": tasks,
    }
    state_path = run_dir / "state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    return state_path


def _task(
    story_key: str,
    phase: str,
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
) -> dict[str, object]:
    return {
        "story_key": story_key,
        "epic": 3,
        "phase": phase,
        "tokens": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_tokens": cache_read_tokens,
            "cache_creation_tokens": cache_creation_tokens,
        },
    }


# --- the sole non-terminal task is the current story ----------------------------


def test_usage_snapshot_attributes_the_sole_non_terminal_task(harness, tmp_path):
    _write_state(
        tmp_path,
        "acme-run-1",
        tasks={
            "3.5": _task("3.5", "done", input_tokens=1_000, output_tokens=200, cache_read_tokens=500),
            "3.6": _task("3.6", "dev-running", input_tokens=300, output_tokens=50, cache_read_tokens=100),
        },
    )

    snapshot = harness.usage_snapshot(tmp_path, "acme-run-1")

    assert snapshot is not None
    assert snapshot.story_key == "3.6"
    # 300 + 50 + round(100 * 0.1) = 360.
    assert snapshot.story_weighted_tokens == 360
    # Run-wide: task 3.5 (1000 + 200 + round(500*0.1) = 1250) + task 3.6 (360).
    assert snapshot.run_weighted_tokens == 1610
    assert snapshot.sample_path == tmp_path / ".bmad-loop" / "runs" / "acme-run-1" / "state.json"


def test_usage_snapshot_uses_the_default_cache_read_weight_when_absent(harness, tmp_path):
    """``RunState.cache_read_weight()`` falls back to the product default
    (0.1) when the persisted ``policy_snapshot`` predates the field or is
    malformed -- ``usage_snapshot`` inherits that fallback, never a second
    notion of the weight."""
    run_dir = tmp_path / ".bmad-loop" / "runs" / "acme-run-1"
    run_dir.mkdir(parents=True)
    state = {
        "run_id": "acme-run-1",
        "project": str(tmp_path),
        "started_at": "2026-08-03T00:00:00Z",
        "tasks": {"3.6": _task("3.6", "dev-running", cache_read_tokens=1_000)},
    }
    (run_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")

    snapshot = harness.usage_snapshot(tmp_path, "acme-run-1")

    assert snapshot is not None
    assert snapshot.story_weighted_tokens == round(1_000 * 0.1)


# --- I/O matrix: no single current story -----------------------------------------


def test_usage_snapshot_reports_no_story_when_zero_non_terminal_tasks(harness, tmp_path):
    _write_state(
        tmp_path,
        "acme-run-1",
        tasks={"3.5": _task("3.5", "done", input_tokens=100)},
    )

    snapshot = harness.usage_snapshot(tmp_path, "acme-run-1")

    assert snapshot is not None
    assert snapshot.story_key is None
    assert snapshot.story_weighted_tokens is None
    assert snapshot.run_weighted_tokens == 100


def test_usage_snapshot_reports_no_story_when_more_than_one_non_terminal_task(harness, tmp_path):
    _write_state(
        tmp_path,
        "acme-run-1",
        tasks={
            "3.5": _task("3.5", "dev-running", input_tokens=100),
            "3.6": _task("3.6", "review-running", input_tokens=200),
        },
    )

    snapshot = harness.usage_snapshot(tmp_path, "acme-run-1")

    assert snapshot is not None
    assert snapshot.story_key is None
    assert snapshot.story_weighted_tokens is None
    assert snapshot.run_weighted_tokens == 300


def test_usage_snapshot_zero_tasks_reports_no_story_and_zero_run_tokens(harness, tmp_path):
    _write_state(tmp_path, "acme-run-1", tasks={})

    snapshot = harness.usage_snapshot(tmp_path, "acme-run-1")

    assert snapshot is not None
    assert snapshot.story_key is None
    assert snapshot.run_weighted_tokens == 0


# --- never raises: every plausible read/parse failure degrades to None ----------


def test_usage_snapshot_returns_none_for_a_missing_run(harness, tmp_path):
    assert harness.usage_snapshot(tmp_path, "no-such-run") is None


def test_usage_snapshot_returns_none_for_malformed_json(harness, tmp_path):
    run_dir = tmp_path / ".bmad-loop" / "runs" / "acme-run-1"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text("{not valid json at all", encoding="utf-8")

    assert harness.usage_snapshot(tmp_path, "acme-run-1") is None


def test_usage_snapshot_returns_none_for_a_missing_required_field(harness, tmp_path):
    """``RunState.from_dict`` requires ``run_id``/``project``/``started_at``
    (bare ``d["..."]`` lookups) -- a document missing one raises ``KeyError``,
    caught alongside the other plausible failures."""
    run_dir = tmp_path / ".bmad-loop" / "runs" / "acme-run-1"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(json.dumps({"tasks": {}}), encoding="utf-8")

    assert harness.usage_snapshot(tmp_path, "acme-run-1") is None


def test_usage_snapshot_returns_none_for_a_wrong_typed_field(harness, tmp_path):
    """``int(d["epic"])`` inside ``StoryTask.from_dict`` raises ``ValueError``
    for a non-numeric ``epic`` -- caught alongside every other plausible
    failure, never propagated raw."""
    run_dir = tmp_path / ".bmad-loop" / "runs" / "acme-run-1"
    run_dir.mkdir(parents=True)
    state = {
        "run_id": "acme-run-1",
        "project": str(tmp_path),
        "started_at": "2026-08-03T00:00:00Z",
        "tasks": {"3.6": {"story_key": "3.6", "epic": "not-a-number", "phase": "dev-running"}},
    }
    (run_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")

    assert harness.usage_snapshot(tmp_path, "acme-run-1") is None


def test_usage_snapshot_returns_none_for_a_non_mapping_policy_snapshot(harness, tmp_path):
    """Review finding (Edge Case Hunter): ``RunState.from_dict`` never
    validates that a PRESENT ``policy_snapshot`` field is actually a
    ``Mapping`` -- it assigns whatever JSON type was there verbatim. A
    syntactically-valid document carrying ``"policy_snapshot": "corrupted"``
    (a plain string, not an object) therefore loads cleanly, and
    ``RunState.cache_read_weight()``'s own ``self.policy_snapshot.get(...)``
    call raises a bare ``AttributeError`` (a ``str`` has no ``.get``) --
    OUTSIDE the ``(OSError, ValueError, KeyError, TypeError)`` tuple this
    method previously caught only around ``load_state`` itself, escaping
    ``usage_snapshot``'s own documented ``never raises`` contract and, in
    production, the supervisor's tick loop entirely."""
    run_dir = tmp_path / ".bmad-loop" / "runs" / "acme-run-1"
    run_dir.mkdir(parents=True)
    state = {
        "run_id": "acme-run-1",
        "project": str(tmp_path),
        "started_at": "2026-08-03T00:00:00Z",
        "policy_snapshot": "corrupted",
        "tasks": {"3.6": _task("3.6", "dev-running")},
    }
    (run_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")

    assert harness.usage_snapshot(tmp_path, "acme-run-1") is None


def test_usage_snapshot_returns_none_for_a_non_finite_cache_read_weight(harness, tmp_path):
    """Review finding: a syntactically-valid document carrying
    ``"cache_read_weight": Infinity`` (which ``json`` both emits and accepts
    by default) makes ``TokenUsage.weighted_total``'s own
    ``round(cache_read * weight)`` raise ``OverflowError`` -- an
    ``ArithmeticError``, not a ``ValueError``, so it escaped every exception
    this method caught and, in production, killed the supervisor sidecar
    with a dangling ``supervisor-attach`` and no matching detach."""
    run_dir = tmp_path / ".bmad-loop" / "runs" / "acme-run-1"
    run_dir.mkdir(parents=True)
    state = {
        "run_id": "acme-run-1",
        "project": str(tmp_path),
        "started_at": "2026-08-03T00:00:00Z",
        "policy_snapshot": {"limits": {"cache_read_weight": float("inf")}},
        "tasks": {"3.6": _task("3.6", "dev-running", cache_read_tokens=1_000)},
    }
    (run_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")

    assert harness.usage_snapshot(tmp_path, "acme-run-1") is None


def test_usage_snapshot_returns_none_for_a_deeply_nested_document(harness, tmp_path):
    """``json.loads`` raises ``RecursionError`` -- NOT a ``ValueError`` -- on
    a deeply nested document (review finding, same "never raises" contract
    as the case above)."""
    run_dir = tmp_path / ".bmad-loop" / "runs" / "acme-run-1"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        "[" * 200_000 + "]" * 200_000, encoding="utf-8"
    )

    assert harness.usage_snapshot(tmp_path, "acme-run-1") is None


def test_usage_snapshot_reports_bmad_loops_own_slug_key_form(harness, tmp_path):
    """Documents what this port actually returns (review finding): the RAW
    ``task.story_key`` bmad-loop wrote, which live data shows is the full
    sprint-status slug -- NOT Marshal's own dot-form feed key. Every other
    test in this file uses a fabricated ``"3.6"``; this one pins the real
    shape, and ``supervisor/__main__.py::_feed_key_form`` is what normalizes
    it before journaling."""
    _write_state(
        tmp_path,
        "acme-run-1",
        tasks={
            "3-6-budget-ceilings-and-the-heaviest-story-advisory": _task(
                "3-6-budget-ceilings-and-the-heaviest-story-advisory", "dev-running"
            )
        },
    )

    snapshot = harness.usage_snapshot(tmp_path, "acme-run-1")

    assert snapshot is not None
    assert snapshot.story_key == "3-6-budget-ceilings-and-the-heaviest-story-advisory"


def test_usage_snapshot_returns_none_for_an_unknown_phase(harness, tmp_path):
    """``Phase(d["phase"])`` raises ``ValueError`` for a phase string
    outside the closed enum -- e.g. a document written by a NEWER
    ``bmad_loop`` minor version with a phase this installed one doesn't
    know."""
    run_dir = tmp_path / ".bmad-loop" / "runs" / "acme-run-1"
    run_dir.mkdir(parents=True)
    state = {
        "run_id": "acme-run-1",
        "project": str(tmp_path),
        "started_at": "2026-08-03T00:00:00Z",
        "tasks": {"3.6": {"story_key": "3.6", "epic": 3, "phase": "not-a-real-phase"}},
    }
    (run_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")

    assert harness.usage_snapshot(tmp_path, "acme-run-1") is None


def test_usage_snapshot_result_is_a_frozen_dataclass(harness, tmp_path):
    _write_state(tmp_path, "acme-run-1", tasks={"3.6": _task("3.6", "dev-running")})
    snapshot = harness.usage_snapshot(tmp_path, "acme-run-1")
    assert isinstance(snapshot, UsageSnapshot)
    with pytest.raises(AttributeError):
        snapshot.story_key = "mutated"  # type: ignore[misc]
