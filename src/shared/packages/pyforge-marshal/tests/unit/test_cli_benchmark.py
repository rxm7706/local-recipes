"""Story 28.5 — ``marshal benchmark compare`` CLI tests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pyforge.marshal.cli import benchmark as benchmark_cli
from pyforge.marshal.core import token_economy_benchmark as bench
from pyforge.marshal.core.verdict import EXIT_OK
from pyforge.marshal.ports.harness import LayerSavings, RunStatusSnapshot, TaskPhaseSnapshot, UsageSnapshot


def _leg_dict(*, layers_mode: str, tokens: int, savings: dict | None = None) -> dict:
    payload = {
        "layers_mode": layers_mode,
        "story_key": bench.PINNED_BENCHMARK_STORY_KEY,
        "task_phase": "done",
        "reviewer_ran": True,
        "gate_fingerprint": [],
        "story_weighted_tokens": tokens,
        "run_weighted_tokens": tokens,
        "cache_read_weight": 0.1,
        "layer_savings": savings,
        "context_layers": {
            name: {"enabled": layers_mode == "on", "aggressiveness": "medium"}
            for name in ("wire", "output", "structure-graph", "derived-context", "planning-graph")
        },
    }
    return payload


class _FakeHarness:
    def __init__(self, usage: UsageSnapshot, snapshot: RunStatusSnapshot) -> None:
        self.usage = usage
        self.snapshot = snapshot

    def usage_snapshot(self, project: Path, run_id: str) -> UsageSnapshot | None:
        return self.usage

    def run_status_snapshot(self, project: Path, run_id: str) -> RunStatusSnapshot | None:
        return self.snapshot


def test_compare_from_json_files_writes_artifact(tmp_path, monkeypatch):
    off_path = tmp_path / "off.json"
    on_path = tmp_path / "on.json"
    off_path.write_text(
        json.dumps(_leg_dict(layers_mode="off", tokens=5000)),
        encoding="utf-8",
    )
    on_path.write_text(
        json.dumps(
            _leg_dict(
                layers_mode="on",
                tokens=3600,
                savings={"wire_compression_saved": 1800, "output_compression_saved": 640},
            )
        ),
        encoding="utf-8",
    )
    out_path = tmp_path / "artifact.json"
    monkeypatch.chdir(tmp_path)
    (tmp_path / "_bmad-output/projects/pyforge-marshal/planning-artifacts").mkdir(parents=True)

    args = argparse.Namespace(
        project="pyforge-marshal",
        off=str(off_path),
        on=str(on_path),
        home=None,
        story=bench.PINNED_BENCHMARK_STORY_KEY,
        output=str(out_path),
        format="json",
    )
    assert benchmark_cli.run_benchmark_compare(args) == EXIT_OK
    assert out_path.is_file()
    artifact = json.loads(out_path.read_text(encoding="utf-8"))
    assert artifact["void"] is False
    assert artifact["equivalence_gate"]["passed"] is True
    assert artifact["totals"]["weighted_tokens_delta"] == -1400
    assert len(artifact["layer_comparison"]) == 5


def test_compare_voids_artifact_when_equivalence_fails(tmp_path, monkeypatch):
    off_path = tmp_path / "off.json"
    on_path = tmp_path / "on.json"
    off = _leg_dict(layers_mode="off", tokens=5000)
    on = _leg_dict(layers_mode="on", tokens=3600)
    on["task_phase"] = "deferred"
    off_path.write_text(json.dumps(off), encoding="utf-8")
    on_path.write_text(json.dumps(on), encoding="utf-8")
    out_path = tmp_path / "void.json"
    monkeypatch.chdir(tmp_path)
    (tmp_path / "_bmad-output/projects/pyforge-marshal/planning-artifacts").mkdir(parents=True)

    args = argparse.Namespace(
        project="pyforge-marshal",
        off=str(off_path),
        on=str(on_path),
        home=None,
        story=bench.PINNED_BENCHMARK_STORY_KEY,
        output=str(out_path),
        format="text",
    )
    code = benchmark_cli.run_benchmark_compare(args)
    assert code == EXIT_OK  # advisory WARN, not HARD
    artifact = json.loads(out_path.read_text(encoding="utf-8"))
    assert artifact["void"] is True


def test_collect_leg_from_harness_reads_review_cycle(tmp_path):
    home = tmp_path / "loop" / "acme"
    run_id = "acme-run-1"
    run_dir = home / ".bmad-loop" / "runs" / run_id
    run_dir.mkdir(parents=True)
    story = bench.PINNED_BENCHMARK_STORY_KEY
    state = {
        "run_id": run_id,
        "tasks": {
            story: {
                "story_key": story,
                "phase": "done",
                "review_cycle": 1,
                "tokens": {"input": 100, "output": 50, "cache_read": 0, "cache_write": 0},
            }
        },
        "finished": True,
        "sweeps_refused": {},
    }
    (run_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")

    usage = UsageSnapshot(
        story_key=story,
        story_weighted_tokens=150,
        run_weighted_tokens=150,
        sample_path=run_dir / "state.json",
        layer_savings=LayerSavings(wire_compression_saved=50),
    )
    snapshot = RunStatusSnapshot(
        paused_stage=None,
        paused_story_key=None,
        paused_reason=None,
        escalated_spec_file=None,
        escalated_task_phase=None,
        deferred=(),
        finished=True,
        tasks=(TaskPhaseSnapshot(story_key=story, phase="done", commit_sha="abc123"),),
    )
    harness = _FakeHarness(usage, snapshot)
    leg = benchmark_cli.collect_leg_from_harness(
        home=home,
        run_id=run_id,
        story_key=story,
        layers_mode="on",
        context_layers={"wire": {"enabled": True, "aggressiveness": "medium"}},
        harness=harness,
    )
    assert leg.reviewer_ran is True
    assert leg.story_weighted_tokens == 150
    assert leg.layer_savings is not None
    assert leg.layer_savings.wire_compression_saved == 50
