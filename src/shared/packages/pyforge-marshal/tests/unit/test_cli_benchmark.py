"""Story 28.5 — ``marshal benchmark compare`` CLI tests."""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

import pytest

from pyforge.marshal.cli import benchmark as benchmark_cli
from pyforge.marshal.core import structure_graph_dispatch_benchmark as sg_bench
from pyforge.marshal.core import token_economy_benchmark as bench
from pyforge.marshal.core.model import Verdict
from pyforge.marshal.core.verdict import EXIT_OK, exit_code_for
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
    def __init__(self, usage: UsageSnapshot | None, snapshot: RunStatusSnapshot | None) -> None:
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


def test_compare_per_layer_from_json_files(tmp_path, monkeypatch):
    baseline_path = tmp_path / "baseline.json"
    layer_map_path = tmp_path / "layers.json"
    baseline_path.write_text(
        json.dumps(_leg_dict(layers_mode="off", tokens=5000) | {"prompt_cache_hit_rate": 0.2}),
        encoding="utf-8",
    )
    layer_specs = {}
    for layer in ("wire", "output", "structure-graph", "derived-context", "planning-graph"):
        leg_path = tmp_path / f"{layer}.json"
        leg_path.write_text(
            json.dumps(
                _leg_dict(layers_mode="on", tokens=4000, savings={"wire_compression_saved": 100})
                | {"prompt_cache_hit_rate": 0.4}
            ),
            encoding="utf-8",
        )
        layer_specs[layer] = str(leg_path)
    layer_map_path.write_text(json.dumps(layer_specs), encoding="utf-8")
    out_path = tmp_path / "per-layer.json"
    monkeypatch.chdir(tmp_path)
    (tmp_path / "_bmad-output/projects/pyforge-marshal/planning-artifacts").mkdir(parents=True)

    args = argparse.Namespace(
        project="pyforge-marshal",
        off=str(baseline_path),
        on="unused-on.json",
        home=None,
        story=bench.PINNED_BENCHMARK_STORY_KEY,
        output=str(out_path),
        format="json",
        per_layer=True,
        layer_legs=str(layer_map_path),
    )
    assert benchmark_cli.run_benchmark_compare(args) == EXIT_OK
    artifact = json.loads(out_path.read_text(encoding="utf-8"))
    assert artifact["schema"] == bench.PER_LAYER_ARTIFACT_SCHEMA
    assert len(artifact["layer_legs"]) == 5
    assert all("prompt_cache_hit_rate_isolated" in row for row in artifact["layer_legs"])


# --- Story 46.9 coverage: refusals, edge cases and per-layer void isolation ---

STORY = bench.PINNED_BENCHMARK_STORY_KEY
EXIT_ERROR = exit_code_for(Verdict.ERROR)
_LAYERS = ("wire", "output", "structure-graph", "derived-context", "planning-graph")


class _ClosedStdout(io.StringIO):
    """A stdout whose reader went away (``marshal benchmark ... | head -0``)."""

    def write(self, s: str) -> int:
        raise BrokenPipeError(32, "Broken pipe")


def _compare_args(**overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "project": "pyforge-marshal",
        "off": "off.json",
        "on": "on.json",
        "home": None,
        "story": STORY,
        "output": None,
        "format": "json",
        "per_layer": False,
        "layer_legs": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def _sg_args(**overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "project": "pyforge-marshal",
        "index_build_seconds": 19.0,
        "index_bytes": 1024,
        "sync_seconds": 4.0,
        "codegraph_reported_seconds": 11.0,
        "files_indexed": 10,
        "nodes": 20,
        "edges": 30,
        "output": None,
        "format": "json",
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def _envelope(capsys: pytest.CaptureFixture[str]) -> dict:
    return json.loads(capsys.readouterr().out)


def _codes(envelope: dict) -> list[str]:
    return [finding["code"] for finding in envelope["findings"]]


def _snapshot(*tasks: TaskPhaseSnapshot) -> RunStatusSnapshot:
    return RunStatusSnapshot(
        paused_stage=None,
        paused_story_key=None,
        paused_reason=None,
        escalated_spec_file=None,
        escalated_task_phase=None,
        deferred=(),
        finished=True,
        tasks=tuple(tasks),
    )


def _usage(sample_path: Path, *, tokens: int = 200) -> UsageSnapshot:
    return UsageSnapshot(
        story_key=STORY,
        story_weighted_tokens=tokens,
        run_weighted_tokens=tokens,
        sample_path=sample_path,
        layer_savings=None,
    )


def _write_state(home: Path, run_id: str, payload: object) -> Path:
    run_dir = home / ".bmad-loop" / "runs" / run_id
    run_dir.mkdir(parents=True)
    state_path = run_dir / "state.json"
    state_path.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")
    return state_path


def _write_leg(path: Path, payload: dict) -> str:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def _write_compare_legs(tmp_path: Path) -> tuple[str, str]:
    off = _write_leg(tmp_path / "off.json", _leg_dict(layers_mode="off", tokens=5000))
    on = _write_leg(
        tmp_path / "on.json",
        _leg_dict(layers_mode="on", tokens=3600, savings={"wire_compression_saved": 1800}),
    )
    return off, on


def _write_per_layer_legs(tmp_path: Path, *, phases: dict[str, str] | None = None) -> tuple[str, str]:
    """A baseline leg (cache-hit 0.2) and a layer map of five isolated legs
    (cache-hit 0.4, 1000 weighted tokens cheaper); ``phases`` overrides one
    isolated leg's landing phase."""
    baseline = _write_leg(
        tmp_path / "baseline.json",
        _leg_dict(layers_mode="off", tokens=5000) | {"prompt_cache_hit_rate": 0.2},
    )
    specs: dict[str, str] = {}
    for layer in _LAYERS:
        leg = _leg_dict(layers_mode="on", tokens=4000) | {"prompt_cache_hit_rate": 0.4}
        if phases and layer in phases:
            leg["task_phase"] = phases[layer]
        specs[layer] = _write_leg(tmp_path / f"{layer}.json", leg)
    layer_map = tmp_path / "layers.json"
    layer_map.write_text(json.dumps(specs), encoding="utf-8")
    return baseline, str(layer_map)


@pytest.fixture
def tmp_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the CLI's repo root at ``tmp_path`` so default artifact paths and
    the structure-graph navigation manifest never touch the real checkout."""
    monkeypatch.setattr(benchmark_cli, "repo_root", lambda: tmp_path)
    return tmp_path


# -- prompt-cache hit rate read from bmad-loop state (CAP-196) --


@pytest.mark.parametrize(
    "state",
    [
        pytest.param(None, id="state-json-missing"),
        pytest.param("{truncated", id="state-json-malformed"),
        pytest.param({"tasks": ["not", "a", "mapping"]}, id="tasks-not-a-mapping"),
        pytest.param(
            {"tasks": {"other": {"story_key": "99-9-other", "tokens": {"input_tokens": 1, "cache_read_tokens": 9}}}},
            id="story-not-in-run",
        ),
        pytest.param({"tasks": {"ours": {"story_key": STORY, "tokens": ["bad"]}}}, id="tokens-not-a-mapping"),
        pytest.param(
            {"tasks": {"ours": {"story_key": STORY, "tokens": {"input_tokens": "lots"}}}}, id="tokens-not-numeric"
        ),
        pytest.param(
            {"tasks": {"ours": {"story_key": STORY, "tokens": {"input_tokens": 0, "cache_read_tokens": 0}}}},
            id="no-billed-prompt-tokens",
        ),
    ],
)
def test_prompt_cache_hit_rate_is_unknown_when_state_cannot_answer(tmp_path, state):
    home = tmp_path / "home"
    if state is None:
        (home / ".bmad-loop" / "runs" / "run-1").mkdir(parents=True)
    else:
        _write_state(home, "run-1", state)
    assert benchmark_cli._prompt_cache_hit_rate_for_story(home, "run-1", STORY) is None


def test_prompt_cache_hit_rate_reads_only_the_named_story(tmp_path):
    home = tmp_path / "home"
    _write_state(
        home,
        "run-1",
        {
            "tasks": {
                "junk": "not-a-task",
                "other": {"story_key": "99-9-other", "tokens": {"input_tokens": 1, "cache_read_tokens": 99}},
                # bmad-loop's short token keys (input / cache_read / cache_write)
                "ours": {"story_key": STORY, "tokens": {"input": 60, "cache_read": 30, "cache_write": 10}},
            }
        },
    )
    assert benchmark_cli._prompt_cache_hit_rate_for_story(home, "run-1", STORY) == 0.3


# -- review cycle read from bmad-loop state --


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        pytest.param(None, 0, id="state-json-missing"),
        pytest.param({"tasks": []}, 0, id="tasks-not-a-mapping"),
        pytest.param(
            {"tasks": {"junk": 7, "other": {"story_key": "99-9-other", "review_cycle": 5}}},
            0,
            id="story-not-in-run",
        ),
        pytest.param({"tasks": {"ours": {"story_key": STORY, "review_cycle": "twice"}}}, 0, id="cycle-not-numeric"),
        pytest.param(
            {
                "tasks": {
                    "junk": 7,
                    "other": {"story_key": "99-9-other", "review_cycle": 5},
                    "ours": {"story_key": STORY, "review_cycle": 2},
                }
            },
            2,
            id="named-story-cycle",
        ),
    ],
)
def test_review_cycle_from_state(tmp_path, state, expected):
    home = tmp_path / "home"
    if state is None:
        (home / ".bmad-loop" / "runs" / "run-1").mkdir(parents=True)
    else:
        _write_state(home, "run-1", state)
    assert benchmark_cli._review_cycle_from_state(home, "run-1", STORY) == expected


# -- collecting a leg from a harness run --


def test_collect_leg_from_harness_refuses_a_run_without_snapshots(tmp_path):
    harness = _FakeHarness(None, _snapshot())
    with pytest.raises(ValueError, match="could not read usage/status snapshot"):
        benchmark_cli.collect_leg_from_harness(
            home=tmp_path,
            run_id="run-x",
            story_key=STORY,
            layers_mode="on",
            context_layers={},
            harness=harness,
        )


def test_collect_leg_from_harness_marks_a_story_absent_from_the_run(tmp_path):
    harness = _FakeHarness(
        _usage(tmp_path / "state.json"),
        _snapshot(TaskPhaseSnapshot(story_key="99-9-other", phase="done", commit_sha="abc123")),
    )
    leg = benchmark_cli.collect_leg_from_harness(
        home=tmp_path,
        run_id="run-x",
        story_key=STORY,
        layers_mode="on",
        context_layers={},
        harness=harness,
    )
    assert leg.task_phase == "missing"
    assert leg.reviewer_ran is False
    assert leg.prompt_cache_hit_rate is None


def test_compare_loads_legs_from_run_ids(tmp_path, tmp_root, capsys):
    """An ``--on`` that is not a file is a run id: the leg comes from the
    harness and carries the story's prompt-cache hit rate from state.json."""
    home = tmp_path / "loop" / "pyforge-marshal"
    run_id = "run-off-on"
    state_path = _write_state(
        home,
        run_id,
        {
            "run_id": run_id,
            "tasks": {
                STORY: {
                    "story_key": STORY,
                    "phase": "done",
                    "review_cycle": 0,
                    "tokens": {"input_tokens": 100, "cache_read_tokens": 50, "cache_creation_tokens": 0},
                }
            },
        },
    )
    harness = _FakeHarness(
        _usage(state_path),
        _snapshot(TaskPhaseSnapshot(story_key=STORY, phase="done", commit_sha="abc123")),
    )
    off, _ = _write_compare_legs(tmp_path)
    out_path = tmp_path / "artifact.json"
    args = _compare_args(off=off, on=run_id, home=str(home), output=str(out_path))
    assert benchmark_cli.run_benchmark_compare(args, harness=harness) == EXIT_OK
    artifact = json.loads(out_path.read_text(encoding="utf-8"))
    assert artifact["void"] is False
    assert artifact["legs"]["layers_on"]["run_id"] == run_id
    assert artifact["legs"]["layers_on"]["prompt_cache_hit_rate"] == round(50 / 150, 6)
    assert artifact["legs"]["layers_on"]["reviewer_ran"] is True  # phase done, no review cycle recorded
    assert _envelope(capsys)["data"]["artifact_path"] == str(out_path)


def test_load_leg_rejects_layers_mode_mismatch(tmp_path):
    leg_path = _write_leg(tmp_path / "leg.json", _leg_dict(layers_mode="on", tokens=100))
    with pytest.raises(ValueError, match="layers_mode"):
        benchmark_cli._load_leg(
            leg_path,
            home=tmp_path,
            story_key=STORY,
            layers_mode="off",
            context_layers={},
            harness=_FakeHarness(None, None),
            policy_digest=None,
        )


# -- marshal benchmark compare: refusals --


def test_compare_rejects_invalid_project_slug(tmp_root, capsys):
    code = benchmark_cli.run_benchmark_compare(_compare_args(project="not a slug!"))
    envelope = _envelope(capsys)
    assert code == EXIT_ERROR
    assert _codes(envelope) == ["MRS-BENCH-001"]
    assert envelope["data"] == {}


@pytest.mark.parametrize(
    ("per_layer", "layer_legs", "message"),
    [
        pytest.param(True, None, "--per-layer requires --layer-legs", id="per-layer-without-map"),
        pytest.param(False, "layers.json", "--layer-legs requires --per-layer", id="map-without-per-layer"),
    ],
)
def test_compare_refuses_unpaired_per_layer_flags(tmp_root, capsys, per_layer, layer_legs, message):
    code = benchmark_cli.run_benchmark_compare(_compare_args(per_layer=per_layer, layer_legs=layer_legs))
    envelope = _envelope(capsys)
    assert code == EXIT_ERROR
    assert _codes(envelope) == ["MRS-BENCH-005"]
    assert message in envelope["findings"][0]["message"]


@pytest.mark.parametrize(
    ("off_text", "fragment"),
    [
        pytest.param("{truncated", "could not load benchmark leg", id="malformed-json"),
        pytest.param(json.dumps(_leg_dict(layers_mode="on", tokens=5000)), "layers_mode", id="wrong-layers-mode"),
        pytest.param(json.dumps({"layers_mode": "off"}), "malformed benchmark leg", id="missing-required-key"),
        pytest.param(json.dumps(["not", "a", "leg"]), "must be a JSON object", id="leg-not-an-object"),
    ],
)
def test_compare_reports_an_unloadable_leg_as_a_finding(tmp_path, tmp_root, capsys, off_text, fragment):
    _, on = _write_compare_legs(tmp_path)
    (tmp_path / "off.json").write_text(off_text, encoding="utf-8")
    out_path = tmp_path / "artifact.json"
    code = benchmark_cli.run_benchmark_compare(
        _compare_args(off=str(tmp_path / "off.json"), on=on, output=str(out_path))
    )
    envelope = _envelope(capsys)
    assert code == EXIT_ERROR
    assert _codes(envelope) == ["MRS-BENCH-002"]
    assert fragment in envelope["findings"][0]["message"]
    assert not out_path.exists()


def test_compare_reports_an_unreadable_harness_run(tmp_path, tmp_root, capsys):
    off, _ = _write_compare_legs(tmp_path)
    harness = _FakeHarness(None, None)
    code = benchmark_cli.run_benchmark_compare(
        _compare_args(off=off, on="run-with-no-state", home=str(tmp_path / "home")),
        harness=harness,
    )
    envelope = _envelope(capsys)
    assert code == EXIT_ERROR
    assert _codes(envelope) == ["MRS-BENCH-002"]
    assert "run-with-no-state" in envelope["findings"][0]["message"]


def test_compare_reports_an_unwritable_artifact(tmp_path, tmp_root, capsys):
    off, on = _write_compare_legs(tmp_path)
    blocker = tmp_path / "blocker"
    blocker.write_text("a file, not a directory", encoding="utf-8")
    code = benchmark_cli.run_benchmark_compare(_compare_args(off=off, on=on, output=str(blocker / "artifact.json")))
    envelope = _envelope(capsys)
    assert code == EXIT_ERROR
    assert _codes(envelope) == ["MRS-BENCH-003"]
    assert envelope["data"] == {}


def test_compare_text_refusal_prints_the_finding_and_no_totals(tmp_root, capsys):
    code = benchmark_cli.run_benchmark_compare(_compare_args(project="not a slug!", format="text"))
    out = capsys.readouterr().out
    assert code == EXIT_ERROR
    assert out.splitlines()[0] == "benchmark compare void=False equivalence_passed=None verdict=error"
    assert "MRS-BENCH-001 error: invalid project slug: 'not a slug!'" in out
    assert "artifact:" not in out
    assert "weighted tokens:" not in out
    assert "per-layer:" not in out


def test_compare_text_void_artifact_prints_the_equivalence_warning(tmp_path, tmp_root, capsys):
    off = _write_leg(tmp_path / "off.json", _leg_dict(layers_mode="off", tokens=5000))
    on_leg = _leg_dict(layers_mode="on", tokens=3600)
    on_leg["task_phase"] = "deferred"
    on = _write_leg(tmp_path / "on.json", on_leg)
    code = benchmark_cli.run_benchmark_compare(
        _compare_args(off=off, on=on, output=str(tmp_path / "void.json"), format="text")
    )
    out = capsys.readouterr().out
    assert code == EXIT_OK  # advisory WARN
    assert "void=True" in out.splitlines()[0]
    assert "MRS-BENCH-004 warn: equivalence gate failed" in out
    assert "on leg did not land (phase='deferred')" in out


def test_compare_text_format_includes_layer_rows(tmp_path, tmp_root, capsys):
    off, on = _write_compare_legs(tmp_path)
    out_path = tmp_path / "out.json"
    code = benchmark_cli.run_benchmark_compare(_compare_args(off=off, on=on, output=str(out_path), format="text"))
    out = capsys.readouterr().out
    assert code == EXIT_OK
    assert f"artifact: {out_path}" in out
    assert "weighted tokens: before=5000 after=3600 delta=-1400" in out
    assert "per-layer:" in out
    assert "  - wire: savings before=" in out


def test_compare_default_artifact_lands_under_implementation_artifacts(tmp_path, tmp_root, capsys):
    off, on = _write_compare_legs(tmp_path)
    assert benchmark_cli.run_benchmark_compare(_compare_args(off=off, on=on)) == EXIT_OK
    artifact_path = Path(_envelope(capsys)["data"]["artifact_path"])
    assert artifact_path.parent == tmp_path / "_bmad-output/projects/pyforge-marshal/implementation-artifacts"
    assert artifact_path.name.startswith("token-economy-benchmark-")
    assert not artifact_path.name.startswith("token-economy-benchmark-per-layer-")
    assert json.loads(artifact_path.read_text(encoding="utf-8"))["void"] is False


def test_compare_survives_a_closed_stdout(tmp_path, tmp_root, monkeypatch):
    off, on = _write_compare_legs(tmp_path)
    out_path = tmp_path / "artifact.json"
    monkeypatch.setattr(sys, "stdout", _ClosedStdout())
    assert benchmark_cli.run_benchmark_compare(_compare_args(off=off, on=on, output=str(out_path))) == EXIT_OK
    assert out_path.is_file()


def test_print_text_skips_malformed_layer_rows(capsys):
    benchmark_cli._print_text(
        {
            "artifact_path": "artifact.json",
            "totals": "not-a-mapping",
            "layer_comparison": ["junk", {"layer": "wire", "savings_before": 0, "savings_after": 5}],
        },
        [],
        "clean",
        void=False,
    )
    lines = capsys.readouterr().out.splitlines()
    assert lines == [
        "benchmark compare void=False equivalence_passed=None verdict=clean",
        "artifact: artifact.json",
        "per-layer:",
        "  - wire: savings before=0 after=5",
    ]


# -- marshal benchmark compare --per-layer (AC: a non-identical landing voids that leg only) --


def test_compare_per_layer_voids_only_the_non_identical_leg(tmp_path, tmp_root, capsys):
    baseline, layer_map = _write_per_layer_legs(tmp_path, phases={"wire": "deferred"})
    out_path = tmp_path / "per-layer.json"
    code = benchmark_cli.run_benchmark_compare(
        _compare_args(off=baseline, on="unused", output=str(out_path), per_layer=True, layer_legs=layer_map)
    )
    envelope = _envelope(capsys)
    assert code == EXIT_OK  # advisory WARN: siblings stay valid
    assert _codes(envelope) == ["MRS-BENCH-004"]
    assert "void layers: wire" in envelope["findings"][0]["message"]
    assert envelope["data"]["void_layer_count"] == 1

    rows = {row["layer"]: row for row in json.loads(out_path.read_text(encoding="utf-8"))["layer_legs"]}
    assert list(rows) == list(_LAYERS)
    assert rows["wire"]["void"] is True
    assert rows["wire"]["weighted_tokens_delta"] is None
    for layer in _LAYERS[1:]:
        assert rows[layer]["void"] is False
        assert rows[layer]["weighted_tokens_delta"] == -1000
        assert rows[layer]["prompt_cache_hit_rate_baseline"] == 0.2
        assert rows[layer]["prompt_cache_hit_rate_isolated"] == 0.4


def test_compare_per_layer_text_lists_every_layer_and_the_warning(tmp_path, tmp_root, capsys):
    baseline, layer_map = _write_per_layer_legs(tmp_path, phases={"output": "escalated"})
    out_path = tmp_path / "per-layer.json"
    code = benchmark_cli.run_benchmark_compare(
        _compare_args(
            off=baseline,
            on="unused",
            output=str(out_path),
            format="text",
            per_layer=True,
            layer_legs=layer_map,
        )
    )
    out = capsys.readouterr().out
    assert code == EXIT_OK
    assert out.splitlines()[0] == "benchmark compare per-layer void_layer_count=1 verdict=warn"
    assert f"artifact: {out_path}" in out
    assert "  - output: void=True weighted_delta=None cache_hit_baseline=0.2 cache_hit_isolated=0.4" in out
    assert "  - wire: void=False weighted_delta=-1000 cache_hit_baseline=0.2 cache_hit_isolated=0.4" in out
    assert "MRS-BENCH-004 warn: equivalence gate failed for layer leg(s)" in out


@pytest.mark.parametrize(
    ("layer_map", "fragment"),
    [
        pytest.param(["wire.json"], "must be an object mapping layer name", id="map-not-an-object"),
        pytest.param({"wire": "wire.json"}, "missing key for layer 'output'", id="layer-missing"),
    ],
)
def test_compare_per_layer_refuses_a_malformed_layer_map(tmp_path, tmp_root, capsys, layer_map, fragment):
    baseline, _ = _write_per_layer_legs(tmp_path)
    if isinstance(layer_map, dict):
        layer_map = {layer: str(tmp_path / spec) for layer, spec in layer_map.items()}
    map_path = tmp_path / "bad-layers.json"
    map_path.write_text(json.dumps(layer_map), encoding="utf-8")
    out_path = tmp_path / "per-layer.json"
    code = benchmark_cli.run_benchmark_compare(
        _compare_args(off=baseline, output=str(out_path), per_layer=True, layer_legs=str(map_path))
    )
    envelope = _envelope(capsys)
    assert code == EXIT_ERROR
    assert _codes(envelope) == ["MRS-BENCH-002"]
    assert fragment in envelope["findings"][0]["message"]
    assert not out_path.exists()


def test_compare_per_layer_reports_an_unwritable_artifact(tmp_path, tmp_root, capsys):
    baseline, layer_map = _write_per_layer_legs(tmp_path)
    blocker = tmp_path / "blocker"
    blocker.write_text("a file, not a directory", encoding="utf-8")
    code = benchmark_cli.run_benchmark_compare(
        _compare_args(off=baseline, output=str(blocker / "per-layer.json"), per_layer=True, layer_legs=layer_map)
    )
    envelope = _envelope(capsys)
    assert code == EXIT_ERROR
    assert _codes(envelope) == ["MRS-BENCH-003"]


def test_compare_per_layer_default_artifact_path(tmp_path, tmp_root, capsys):
    baseline, layer_map = _write_per_layer_legs(tmp_path)
    code = benchmark_cli.run_benchmark_compare(_compare_args(off=baseline, per_layer=True, layer_legs=layer_map))
    envelope = _envelope(capsys)
    assert code == EXIT_OK
    assert _codes(envelope) == []
    artifact_path = Path(envelope["data"]["artifact_path"])
    assert artifact_path.parent == tmp_path / "_bmad-output/projects/pyforge-marshal/implementation-artifacts"
    assert artifact_path.name.startswith("token-economy-benchmark-per-layer-")
    assert json.loads(artifact_path.read_text(encoding="utf-8"))["schema"] == bench.PER_LAYER_ARTIFACT_SCHEMA


def test_compare_per_layer_survives_a_closed_stdout(tmp_path, tmp_root, monkeypatch):
    baseline, layer_map = _write_per_layer_legs(tmp_path)
    out_path = tmp_path / "per-layer.json"
    monkeypatch.setattr(sys, "stdout", _ClosedStdout())
    code = benchmark_cli.run_benchmark_compare(
        _compare_args(off=baseline, output=str(out_path), per_layer=True, layer_legs=layer_map)
    )
    assert code == EXIT_OK
    assert out_path.is_file()


def test_emit_per_layer_text_skips_malformed_rows(capsys):
    code = benchmark_cli._emit_per_layer(
        argparse.Namespace(format="text"),
        [],
        {"void_layer_count": 0, "layer_legs": ["junk", {"layer": "wire", "void": False}]},
    )
    lines = capsys.readouterr().out.splitlines()
    assert code == EXIT_OK
    assert lines[0] == "benchmark compare per-layer void_layer_count=0 verdict=clean"
    assert not any(line.startswith("artifact:") for line in lines)
    assert lines[1:] == ["  - wire: void=False weighted_delta=None cache_hit_baseline=None cache_hit_isolated=None"]


def test_emit_per_layer_text_ignores_a_non_list_layer_payload(capsys):
    code = benchmark_cli._emit_per_layer(
        argparse.Namespace(format="text"),
        [],
        {"artifact_path": "per-layer.json", "void_layer_count": 0, "layer_legs": "not-a-list"},
    )
    assert code == EXIT_OK
    assert capsys.readouterr().out.splitlines() == [
        "benchmark compare per-layer void_layer_count=0 verdict=clean",
        "artifact: per-layer.json",
    ]


# -- marshal benchmark structure-graph-dispatch (Story 28.31 artifact) --


def test_structure_graph_dispatch_measure_writes_artifact(tmp_path, tmp_root, capsys):
    out_path = tmp_path / "sg-bench.json"
    code = benchmark_cli.run_structure_graph_dispatch_measure(_sg_args(output=str(out_path)))
    envelope = _envelope(capsys)
    assert code == EXIT_OK
    assert envelope["command"] == "benchmark structure-graph-dispatch"
    assert envelope["data"]["artifact_path"] == str(out_path)
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["index_build"]["wall_clock_seconds"] == 19.0
    assert payload["index_build"]["index_bytes"] == 1024
    assert payload["sync_from_base"]["wall_clock_seconds"] == 4.0
    assert payload["recommendation"] == envelope["data"]["recommendation"]


def test_structure_graph_dispatch_measure_default_path_and_text_summary(tmp_path, tmp_root, capsys):
    code = benchmark_cli.run_structure_graph_dispatch_measure(_sg_args(sync_seconds=None, format="text"))
    out = capsys.readouterr().out
    expected = sg_bench.default_artifact_path(tmp_path, "pyforge-marshal")
    assert code == EXIT_OK
    assert expected.is_file()
    assert json.loads(expected.read_text(encoding="utf-8"))["sync_from_base"] is None
    assert out.splitlines()[0].startswith("structure-graph-dispatch recommendation=")
    assert f"artifact: {expected}" in out
    assert "rationale: " in out


def test_structure_graph_dispatch_measure_refuses_invalid_slug(tmp_path, tmp_root, capsys):
    out_path = tmp_path / "sg.json"
    code = benchmark_cli.run_structure_graph_dispatch_measure(_sg_args(project="Not A Slug!", output=str(out_path)))
    envelope = _envelope(capsys)
    assert code == EXIT_ERROR
    assert _codes(envelope) == ["MRS-BENCH-001"]
    assert envelope["data"] == {}
    assert not out_path.exists()


def test_structure_graph_dispatch_measure_text_refusal_prints_the_finding(tmp_root, capsys):
    code = benchmark_cli.run_structure_graph_dispatch_measure(_sg_args(project="Not A Slug!", format="text"))
    lines = capsys.readouterr().out.splitlines()
    assert code == EXIT_ERROR
    assert lines == [
        "structure-graph-dispatch recommendation=None verdict=error",
        "MRS-BENCH-001 error: invalid project slug: 'Not A Slug!'",
    ]


def test_structure_graph_dispatch_measure_reports_an_unwritable_artifact(tmp_path, tmp_root, capsys):
    blocker = tmp_path / "blocker"
    blocker.write_text("a file, not a directory", encoding="utf-8")
    code = benchmark_cli.run_structure_graph_dispatch_measure(_sg_args(output=str(blocker / "sg.json")))
    envelope = _envelope(capsys)
    assert code == EXIT_ERROR
    assert _codes(envelope) == ["MRS-BENCH-003"]


def test_structure_graph_dispatch_measure_survives_a_closed_stdout(tmp_root, monkeypatch):
    monkeypatch.setattr(sys, "stdout", _ClosedStdout())
    code = benchmark_cli.run_structure_graph_dispatch_measure(_sg_args(project="Not A Slug!", format="text"))
    assert code == EXIT_ERROR
