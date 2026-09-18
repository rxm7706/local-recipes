"""Story 33.1 — real savings getters (CAP-7)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from pyforge.marshal.adapters.harness_bmadloop import BmadLoopHarness
from pyforge.marshal.cli.status import _format_savings_summary
from pyforge.marshal.core import layer_savings_sources as sources
from pyforge.marshal.core import token_economy_benchmark as bench
from pyforge.marshal.core.token_economy_benchmark import check_equivalence
from pyforge.marshal.ports.harness import LayerSavings
from pyforge.marshal.seed.model.kit import (
    CAVEMAN_SKILL_RELPATH,
    CCR_STORE_RELPATH,
    CODEGRAPH_INDEX_RELPATH,
)


def _write_ccr_db(path: Path, *, original: int, compressed: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = json.dumps(
        {"original_tokens": original, "compressed_tokens": compressed}
    )
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE ccr_entries (hash TEXT PRIMARY KEY, entry_json TEXT NOT NULL, "
        "created_at REAL NOT NULL, ttl INTEGER NOT NULL)"
    )
    conn.execute(
        "INSERT INTO ccr_entries VALUES (?, ?, ?, ?)",
        ("abc", entry, 1.0, 1800),
    )
    conn.commit()
    conn.close()


def test_headroom_wire_saved_sums_ccr_entries(tmp_path: Path) -> None:
    home = tmp_path / "loop-home"
    _write_ccr_db(home / CCR_STORE_RELPATH / "ccr_store.db", original=1000, compressed=400)
    assert sources.read_headroom_wire_saved(home) == 600


def test_headroom_wire_saved_names_missing_store(tmp_path: Path) -> None:
    home = tmp_path / "empty-home"
    home.mkdir()
    assert sources.read_headroom_wire_saved(home) == "ccr-store-directory-missing"


def test_caveman_output_saved_reads_output_ledger(tmp_path: Path) -> None:
    home = tmp_path / "home"
    skill = home / CAVEMAN_SKILL_RELPATH
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: caveman\n---\n", encoding="utf-8")
    ledger = home / CCR_STORE_RELPATH / "output_savings.json"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        json.dumps({"estimate": {"tokens_saved": 640}}),
        encoding="utf-8",
    )
    assert sources.read_caveman_output_saved(home) == 640


def test_caveman_output_saved_without_skill_is_named(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    assert sources.read_caveman_output_saved(home) == "caveman-skill-not-deployed"


def test_codegraph_stats_reads_sidecar(tmp_path: Path) -> None:
    home = tmp_path / "home"
    stats = home / sources.CODEGRAPH_STATS_RELPATH
    stats.parent.mkdir(parents=True)
    stats.write_text(json.dumps({"graph_hits": 12, "file_reads": 3}), encoding="utf-8")
    assert sources.read_codegraph_hits_vs_reads(home) == (12, 3)


def test_codegraph_stats_without_sidecar_names_missing_index(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    assert sources.read_codegraph_hits_vs_reads(home) == "codegraph-index-missing"


def test_cocoindex_cache_hits_reads_index(tmp_path: Path) -> None:
    home = tmp_path / "home"
    index = home / sources.COCOINDEX_INDEX_RELPATH
    index.parent.mkdir(parents=True)
    index.write_text(json.dumps({"cache_hits": 4}), encoding="utf-8")
    assert sources.read_cocoindex_cache_hits(home) == 4


def test_planning_graph_tokens_saved_reads_telemetry(tmp_path: Path) -> None:
    home = tmp_path / "home"
    telemetry = home / sources.PLANNING_GRAPH_TELEMETRY_RELPATH
    telemetry.parent.mkdir(parents=True)
    telemetry.write_text(json.dumps({"tokens_saved": 109500, "grounded": True}), encoding="utf-8")
    assert sources.read_planning_graph_tokens_saved(home) == 109500


def test_gather_layer_savings_never_returns_none_for_named_reasons(tmp_path: Path) -> None:
    run_dir = tmp_path / "home" / ".bmad-loop" / "runs" / "run-1"
    run_dir.mkdir(parents=True)
    harness = BmadLoopHarness()
    savings = harness._gather_layer_savings(run_dir)
    assert savings is not None
    assert savings.output_compression_saved == "caveman-skill-not-deployed"
    assert savings.wire_compression_saved == "ccr-store-directory-missing"
    assert savings.graph_hits_vs_file_reads == "codegraph-index-missing"
    assert savings.derived_context_cache_hits == "cocoindex-index-missing"
    assert savings.planning_graph_tokens_saved == "planning-graph-store-missing"


def test_format_savings_summary_renders_named_reasons_and_zero() -> None:
    degraded = {
        "output_compression_saved": "caveman-skill-not-deployed",
        "wire_compression_saved": 0,
        "graph_hits_vs_file_reads": "codegraph-index-missing",
    }
    summary = _format_savings_summary(degraded)
    assert "output:caveman-skill-not-deployed" in summary
    assert "wire:0B" in summary
    assert "graph:codegraph-index-missing" in summary


def test_leg_from_mapping_accepts_string_measurements() -> None:
    payload = {
        "layers_mode": "off",
        "story_key": bench.PINNED_BENCHMARK_STORY_KEY,
        "task_phase": "done",
        "reviewer_ran": True,
        "run_weighted_tokens": 0,
        "layer_savings": {
            "wire_compression_saved": "ccr-store-directory-missing",
            "graph_hits_vs_file_reads": "codegraph-index-missing",
        },
    }
    leg = bench.leg_from_mapping(payload)
    assert leg.layer_savings is not None
    assert leg.layer_savings.wire_compression_saved == "ccr-store-directory-missing"
    assert leg.layer_savings.graph_hits_vs_file_reads == "codegraph-index-missing"


def test_leg_from_mapping_reconstructs_split_graph_keys() -> None:
    payload = {
        "layers_mode": "off",
        "story_key": bench.PINNED_BENCHMARK_STORY_KEY,
        "task_phase": "done",
        "reviewer_ran": True,
        "run_weighted_tokens": 0,
        "layer_savings": {"graph_hits": 12, "file_reads": 3},
    }
    leg = bench.leg_from_mapping(payload)
    assert leg.layer_savings is not None
    assert leg.layer_savings.graph_hits_vs_file_reads == (12, 3)


def test_benchmark_compare_voids_on_verdict_mismatch() -> None:
    off = bench.BenchmarkLegRecord(
        layers_mode="off",
        story_key=bench.PINNED_BENCHMARK_STORY_KEY,
        task_phase="done",
        reviewer_ran=True,
        gate_fingerprint=(),
        story_weighted_tokens=5000,
        run_weighted_tokens=5000,
        cache_read_weight=0.1,
        layer_savings=LayerSavings(wire_compression_saved="ccr-store-directory-missing"),
        context_layers={},
    )
    on = bench.BenchmarkLegRecord(
        layers_mode="on",
        story_key=bench.PINNED_BENCHMARK_STORY_KEY,
        task_phase="deferred",
        reviewer_ran=True,
        gate_fingerprint=(),
        story_weighted_tokens=3600,
        run_weighted_tokens=3600,
        cache_read_weight=0.1,
        layer_savings=LayerSavings(wire_compression_saved=1800),
        context_layers={},
    )
    result = check_equivalence(off, on)
    assert result.passed is False


def test_classify_layer_kind_covers_every_silent_and_configured_key() -> None:
    for key in sources.SILENT_LAYER_KEYS:
        assert sources.classify_layer_kind(key) == "silent"
    for key in sources.CONFIGURED_LAYER_KEYS:
        assert sources.classify_layer_kind(key) == "configured"


def test_classify_layer_kind_raises_on_unrecognized_key() -> None:
    with pytest.raises(ValueError):
        sources.classify_layer_kind("not_a_real_layer")


def test_currency_for_harness_covers_every_known_profile() -> None:
    assert sources.currency_for_harness("claude") == "usd"
    assert sources.currency_for_harness("cursor") == "quota-burn"
    assert sources.currency_for_harness("copilot") == "quota-burn"
    assert sources.currency_for_harness("gemini") == "request-count"
    assert sources.currency_for_harness("devin") == "acus"


def test_currency_for_harness_degrades_honestly_for_none_and_unrecognized() -> None:
    assert sources.currency_for_harness(None) == sources.UNKNOWN_HARNESS_CURRENCY
    assert sources.currency_for_harness("some-future-harness") == sources.UNKNOWN_HARNESS_CURRENCY


def _write_run_journal(
    runs_dir: Path,
    run_id: str,
    *,
    harness_profile: str | None,
    layer_savings: dict[str, object] | None,
    include_launch: bool = True,
    include_usage: bool = True,
) -> None:
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True)
    lines = []
    if include_launch:
        lines.append(
            json.dumps(
                {
                    "kind": "dispatch-launch",
                    "phase": "outcome",
                    "payload": {"harness_profile": harness_profile},
                }
            )
        )
    if include_usage:
        lines.append(
            json.dumps(
                {
                    "kind": "budget-usage",
                    "phase": "observation",
                    "payload": {
                        "story_key": f"{run_id}-story",
                        "layer_savings": layer_savings,
                    },
                }
            )
        )
    (run_dir / "journal.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_read_rollup_by_harness_splits_two_harnesses_by_currency(tmp_path: Path) -> None:
    runs_dir = (
        tmp_path
        / "_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs"
    )
    _write_run_journal(
        runs_dir,
        "run-claude",
        harness_profile="claude",
        layer_savings={
            "output_compression_saved": 500,
            "wire_compression_saved": 200,
            "graph_hits": 8,
            "file_reads": 2,
            "derived_context_cache_hits": 3,
            "planning_graph_tokens_saved": 100,
        },
    )
    _write_run_journal(
        runs_dir,
        "run-cursor",
        harness_profile="cursor",
        layer_savings={
            "output_compression_saved": "caveman-skill-not-deployed",
            "wire_compression_saved": "wrapper-not-declared",
        },
    )

    report = sources.read_rollup_by_harness(tmp_path)

    assert report["status"] == "ok"
    harnesses = report["harnesses"]
    assert set(harnesses) == {"claude", "cursor"}

    claude = harnesses["claude"]
    assert claude["currency"] == "usd"
    assert claude["runs"] == 1
    assert claude["silent"]["output_compression_saved"] == [500]
    assert claude["silent"]["graph_hits_vs_file_reads"] == [(8, 2)]
    assert claude["silent"]["derived_context_cache_hits"] == [3]
    assert claude["silent"]["planning_graph_tokens_saved"] == [100]
    assert claude["configured"]["wire_compression_saved"] == [200]

    cursor = harnesses["cursor"]
    assert cursor["currency"] == "quota-burn"
    assert cursor["runs"] == 1
    assert cursor["silent"]["output_compression_saved"] == ["caveman-skill-not-deployed"]
    assert cursor["configured"]["wire_compression_saved"] == ["wrapper-not-declared"]

    # Never a single cross-harness summed total anywhere in the envelope.
    assert "total" not in report
    assert "total" not in claude
    assert "total" not in cursor


def test_read_rollup_by_harness_skips_run_missing_launch_or_usage(tmp_path: Path) -> None:
    runs_dir = (
        tmp_path
        / "_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs"
    )
    _write_run_journal(
        runs_dir,
        "run-no-launch",
        harness_profile=None,
        layer_savings={"wire_compression_saved": 42},
        include_launch=False,
    )
    _write_run_journal(
        runs_dir,
        "run-no-usage",
        harness_profile="gemini",
        layer_savings=None,
        include_usage=False,
    )

    report = sources.read_rollup_by_harness(tmp_path)

    assert report["status"] == "no-savings-samples"
    assert report["harnesses"] == {}


def test_read_rollup_by_harness_names_missing_dispatch_runs_dir(tmp_path: Path) -> None:
    report = sources.read_rollup_by_harness(tmp_path)
    assert report["status"] == "no-dispatch-journals"
    assert report["harnesses"] == {}


def test_dispatch_idle_timing_reads_journal_samples(tmp_path: Path) -> None:
    runs = (
        tmp_path
        / "_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs/run-a"
    )
    runs.mkdir(parents=True)
    journal = runs / "journal.jsonl"
    journal.write_text(
        "\n".join(
            [
                json.dumps({"payload": {"idle_seconds": 1200}}),
                json.dumps({"payload": {"idle_seconds": 900}}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    report = sources.read_dispatch_idle_timing(tmp_path)
    assert report["status"] == "ok"
    assert report["sessions"][0]["idle_samples"] == 2
