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
    entry = json.dumps({"original_tokens": original, "compressed_tokens": compressed})
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


def test_classify_layer_kind_silent_keys() -> None:
    for key in sources.SILENT_LAYER_KEYS:
        assert sources.classify_layer_kind(key) == "silent"


def test_classify_layer_kind_configured_key() -> None:
    for key in sources.CONFIGURED_LAYER_KEYS:
        assert sources.classify_layer_kind(key) == "configured"


def test_classify_layer_kind_unrecognized_raises() -> None:
    with pytest.raises(ValueError):
        sources.classify_layer_kind("not_a_real_layer_key")


def test_currency_for_harness_known_names() -> None:
    assert sources.currency_for_harness("claude") == "usd"
    assert sources.currency_for_harness("cursor") == "quota-burn"
    assert sources.currency_for_harness("copilot") == "quota-burn"
    assert sources.currency_for_harness("gemini") == "request-count"
    assert sources.currency_for_harness("devin") == "acus"


def test_currency_for_harness_none_and_unrecognized() -> None:
    assert sources.currency_for_harness(None) == sources.UNKNOWN_HARNESS_CURRENCY
    assert sources.currency_for_harness("some-future-harness") == sources.UNKNOWN_HARNESS_CURRENCY


def _write_run_journal(
    runs_dir: Path,
    run_id: str,
    *,
    include_launch: bool = True,
    harness_profile: str | None = None,
    layer_savings_entries: tuple[dict[str, object] | None, ...] = (),
) -> None:
    """Test-fixture helper (Story 46.5): writes a run's `journal.jsonl` with
    an optional `dispatch-launch` outcome entry naming `harness_profile`,
    followed by one `budget-usage` entry per `layer_savings_entries` item
    (`None` writes a `budget-usage` entry with no `layer_savings` key at
    all, e.g. a terminal cost-only flush)."""
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True)
    lines: list[str] = []
    if include_launch:
        lines.append(
            json.dumps(
                {
                    "kind": "dispatch-launch",
                    "phase": "outcome",
                    "payload": {"ok": True, "harness_profile": harness_profile},
                }
            )
        )
    for entry in layer_savings_entries:
        payload: dict[str, object] = {"story_key": run_id}
        if entry is not None:
            payload["layer_savings"] = entry
        lines.append(json.dumps({"kind": "budget-usage", "phase": "observation", "payload": payload}))
    (run_dir / "journal.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_read_rollup_by_harness_no_dispatch_runs_dir(tmp_path: Path) -> None:
    report = sources.read_rollup_by_harness(tmp_path)
    assert report == {"status": "no-dispatch-journals", "harnesses": {}}


def test_read_rollup_by_harness_splits_two_harnesses(tmp_path: Path) -> None:
    runs_dir = tmp_path / "_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs"
    _write_run_journal(
        runs_dir,
        "run-claude",
        harness_profile="claude",
        layer_savings_entries=[{"output_compression_saved": 500, "wire_compression_saved": 200}],
    )
    _write_run_journal(
        runs_dir,
        "run-cursor",
        harness_profile="cursor",
        layer_savings_entries=[{"derived_context_cache_hits": 3}],
    )
    report = sources.read_rollup_by_harness(tmp_path)
    assert report["status"] == "ok"
    harnesses = report["harnesses"]
    assert set(harnesses) == {"claude", "cursor"}
    assert harnesses["claude"]["currency"] == "usd"
    assert harnesses["claude"]["silent"] == {"output_compression_saved": [500]}
    assert harnesses["claude"]["configured"] == {"wire_compression_saved": [200]}
    assert harnesses["claude"]["runs"] == 1
    assert harnesses["cursor"]["currency"] == "quota-burn"
    assert harnesses["cursor"]["silent"] == {"derived_context_cache_hits": [3]}
    assert harnesses["cursor"]["configured"] == {}
    assert harnesses["cursor"]["runs"] == 1


def test_read_rollup_by_harness_last_non_empty_wins(tmp_path: Path) -> None:
    # Proves last-*non-empty*-wins, not literal-last-entry-wins: the LATER
    # budget-usage entry omits `layer_savings` entirely (a terminal
    # cost-only flush), so the rollup must fall back to the EARLIER entry
    # that actually carried data rather than reporting nothing.
    runs_dir = tmp_path / "_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs"
    _write_run_journal(
        runs_dir,
        "run-a",
        harness_profile="claude",
        layer_savings_entries=[
            {"output_compression_saved": 700},
            None,
        ],
    )
    report = sources.read_rollup_by_harness(tmp_path)
    assert report["harnesses"]["claude"]["silent"] == {"output_compression_saved": [700]}


def test_read_rollup_by_harness_accumulates_across_runs_same_harness(
    tmp_path: Path,
) -> None:
    runs_dir = tmp_path / "_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs"
    _write_run_journal(
        runs_dir,
        "run-a",
        harness_profile="claude",
        layer_savings_entries=[{"output_compression_saved": 100}],
    )
    _write_run_journal(
        runs_dir,
        "run-b",
        harness_profile="claude",
        layer_savings_entries=[{"output_compression_saved": 250}],
    )
    report = sources.read_rollup_by_harness(tmp_path)
    claude = report["harnesses"]["claude"]
    assert claude["runs"] == 2
    assert claude["silent"] == {"output_compression_saved": [100, 250]}


def test_read_rollup_by_harness_skips_run_missing_launch_or_usage(
    tmp_path: Path,
) -> None:
    runs_dir = tmp_path / "_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs"
    _write_run_journal(
        runs_dir,
        "run-no-launch",
        include_launch=False,
        layer_savings_entries=[{"output_compression_saved": 400}],
    )
    _write_run_journal(
        runs_dir,
        "run-no-usage",
        harness_profile="claude",
        layer_savings_entries=[],
    )
    report = sources.read_rollup_by_harness(tmp_path)
    assert report == {"status": "no-savings-samples", "harnesses": {}}


def test_read_rollup_by_harness_recombines_split_graph_hits_wire_shape(
    tmp_path: Path,
) -> None:
    # `supervisor/__main__.py::_layer_savings_payload` writes a tuple-valued
    # `graph_hits_vs_file_reads` (the normal case) as two separate on-wire
    # keys, `graph_hits`/`file_reads` -- neither of which is a recognized
    # `SILENT_LAYER_KEYS`/`CONFIGURED_LAYER_KEYS` name on its own. The rollup
    # must recombine them under the canonical key rather than raising.
    runs_dir = tmp_path / "_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs"
    _write_run_journal(
        runs_dir,
        "run-claude",
        harness_profile="claude",
        layer_savings_entries=[{"graph_hits": 12, "file_reads": 3}],
    )
    report = sources.read_rollup_by_harness(tmp_path)
    assert report["harnesses"]["claude"]["silent"] == {"graph_hits_vs_file_reads": [(12, 3)]}


def test_read_rollup_by_harness_tolerates_malformed_and_non_dict(tmp_path: Path) -> None:
    runs_dir = tmp_path / "_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs"
    run_dir = runs_dir / "run-malformed"
    run_dir.mkdir(parents=True)
    (run_dir / "journal.jsonl").write_text(
        "\n".join(
            [
                "not valid json",
                json.dumps(
                    {
                        "kind": "dispatch-launch",
                        "phase": "outcome",
                        "payload": {"ok": True, "harness_profile": "claude"},
                    }
                ),
                json.dumps(
                    {
                        "kind": "budget-usage",
                        "phase": "observation",
                        "payload": {"layer_savings": "not-a-dict"},
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    report = sources.read_rollup_by_harness(tmp_path)
    assert report == {"status": "no-savings-samples", "harnesses": {}}


def test_read_rollup_by_harness_skips_unrecognized_layer_key(tmp_path: Path) -> None:
    # A schema-drift key (not yet added to the taxonomy) must not crash the
    # whole rollup via an uncaught `ValueError` -- only that key is skipped;
    # the run's other, recognized keys still bucket normally.
    runs_dir = tmp_path / "_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs"
    _write_run_journal(
        runs_dir,
        "run-claude",
        harness_profile="claude",
        layer_savings_entries=[{"output_compression_saved": 500, "some_future_layer_key": 42}],
    )
    report = sources.read_rollup_by_harness(tmp_path)
    assert report["status"] == "ok"
    claude = report["harnesses"]["claude"]
    assert claude["silent"] == {"output_compression_saved": [500]}
    assert "some_future_layer_key" not in claude["silent"]
    assert "some_future_layer_key" not in claude["configured"]


def test_read_rollup_by_harness_skips_non_utf8_journal(tmp_path: Path) -> None:
    # A non-UTF-8 journal file raises `UnicodeDecodeError` from
    # `read_text(encoding="utf-8")` -- a `ValueError` subclass, NOT an
    # `OSError` subclass -- so it needs its own tolerance, not just the
    # `OSError` guard. Skips that one run; other runs still roll up.
    runs_dir = tmp_path / "_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs"
    bad_run_dir = runs_dir / "run-bad-encoding"
    bad_run_dir.mkdir(parents=True)
    (bad_run_dir / "journal.jsonl").write_bytes(b"\xff\xfe\x00\x01not utf-8 at all")
    _write_run_journal(
        runs_dir,
        "run-claude",
        harness_profile="claude",
        layer_savings_entries=[{"output_compression_saved": 500}],
    )
    report = sources.read_rollup_by_harness(tmp_path)
    assert report["status"] == "ok"
    assert set(report["harnesses"]) == {"claude"}
    assert report["harnesses"]["claude"]["silent"] == {"output_compression_saved": [500]}


def test_read_rollup_by_harness_merges_nonoverlapping_keys_across_entries(
    tmp_path: Path,
) -> None:
    # Two non-empty `budget-usage` entries in the same run can carry
    # different, non-overlapping key subsets (`_layer_savings_payload` only
    # includes a key when its `LayerSavings` field `is not None`) -- both
    # must survive in the rollup via per-key merge, not whole-payload
    # replacement (which would drop whichever entry came first).
    runs_dir = tmp_path / "_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs"
    _write_run_journal(
        runs_dir,
        "run-claude",
        harness_profile="claude",
        layer_savings_entries=[
            {"output_compression_saved": 500},
            {"wire_compression_saved": 200},
        ],
    )
    report = sources.read_rollup_by_harness(tmp_path)
    claude = report["harnesses"]["claude"]
    assert claude["silent"] == {"output_compression_saved": [500]}
    assert claude["configured"] == {"wire_compression_saved": [200]}


def test_headroom_wire_saved_names_missing_database(tmp_path: Path) -> None:
    home = tmp_path / "home"
    (home / CCR_STORE_RELPATH).mkdir(parents=True)
    assert sources.read_headroom_wire_saved(home) == "ccr-store-database-missing"


def test_headroom_wire_saved_names_unreadable_database(tmp_path: Path) -> None:
    home = tmp_path / "home"
    store_dir = home / CCR_STORE_RELPATH
    store_dir.mkdir(parents=True)
    (store_dir / "ccr_store.db").write_text("not a sqlite file", encoding="utf-8")
    assert sources.read_headroom_wire_saved(home) == "ccr-store-schema-unreadable"


def test_headroom_wire_saved_names_unreadable_uri(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    store_dir = home / CCR_STORE_RELPATH
    store_dir.mkdir(parents=True)
    (store_dir / "ccr_store.db").write_text("", encoding="utf-8")

    def _raises(*_a, **_k):
        raise sqlite3.Error("simulated connect failure")

    monkeypatch.setattr(sqlite3, "connect", _raises)
    assert sources.read_headroom_wire_saved(home) == "ccr-store-database-unreadable"


def test_headroom_wire_saved_zero_on_empty_store(tmp_path: Path) -> None:
    home = tmp_path / "home"
    store_dir = home / CCR_STORE_RELPATH
    store_dir.mkdir(parents=True)
    conn = sqlite3.connect(store_dir / "ccr_store.db")
    conn.execute(
        "CREATE TABLE ccr_entries (hash TEXT PRIMARY KEY, entry_json TEXT NOT NULL, "
        "created_at REAL NOT NULL, ttl INTEGER NOT NULL)"
    )
    conn.commit()
    conn.close()
    assert sources.read_headroom_wire_saved(home) == 0


def test_headroom_wire_saved_skips_malformed_and_incomplete_entries(tmp_path: Path) -> None:
    home = tmp_path / "home"
    store_dir = home / CCR_STORE_RELPATH
    store_dir.mkdir(parents=True)
    db_path = store_dir / "ccr_store.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE ccr_entries (hash TEXT PRIMARY KEY, entry_json TEXT NOT NULL, "
        "created_at REAL NOT NULL, ttl INTEGER NOT NULL)"
    )
    conn.executemany(
        "INSERT INTO ccr_entries VALUES (?, ?, ?, ?)",
        [
            ("bad-json", "not valid json", 1.0, 1800),
            ("incomplete", json.dumps({"original_tokens": 1000}), 1.0, 1800),
            (
                "good",
                json.dumps({"original_tokens": 1000, "compressed_tokens": 700}),
                1.0,
                1800,
            ),
        ],
    )
    conn.commit()
    conn.close()
    assert sources.read_headroom_wire_saved(home) == 300


def test_caveman_output_saved_names_missing_ledger(tmp_path: Path) -> None:
    home = tmp_path / "home"
    skill = home / CAVEMAN_SKILL_RELPATH
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: caveman\n---\n", encoding="utf-8")
    assert sources.read_caveman_output_saved(home) == "output-savings-ledger-missing"


def test_caveman_output_saved_names_unreadable_ledger(tmp_path: Path) -> None:
    home = tmp_path / "home"
    skill = home / CAVEMAN_SKILL_RELPATH
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: caveman\n---\n", encoding="utf-8")
    ledger = home / CCR_STORE_RELPATH / "output_savings.json"
    ledger.parent.mkdir(parents=True)
    ledger.write_text("not valid json", encoding="utf-8")
    assert sources.read_caveman_output_saved(home) == "output-savings-ledger-unreadable"


def test_caveman_output_saved_reads_top_level_tokens_saved(tmp_path: Path) -> None:
    home = tmp_path / "home"
    skill = home / CAVEMAN_SKILL_RELPATH
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: caveman\n---\n", encoding="utf-8")
    ledger = home / CCR_STORE_RELPATH / "output_savings.json"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(json.dumps({"tokens_saved": 250}), encoding="utf-8")
    assert sources.read_caveman_output_saved(home) == 250


def test_caveman_output_saved_names_not_recorded(tmp_path: Path) -> None:
    home = tmp_path / "home"
    skill = home / CAVEMAN_SKILL_RELPATH
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: caveman\n---\n", encoding="utf-8")
    ledger = home / CCR_STORE_RELPATH / "output_savings.json"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(json.dumps({"unrelated": True}), encoding="utf-8")
    assert sources.read_caveman_output_saved(home) == "output-savings-not-recorded"


def test_codegraph_stats_names_unreadable_sidecar(tmp_path: Path) -> None:
    home = tmp_path / "home"
    stats = home / sources.CODEGRAPH_STATS_RELPATH
    stats.parent.mkdir(parents=True)
    stats.write_text("not valid json", encoding="utf-8")
    assert sources.read_codegraph_hits_vs_reads(home) == "codegraph-stats-unreadable"


def test_codegraph_stats_names_shape_unrecognized(tmp_path: Path) -> None:
    home = tmp_path / "home"
    stats = home / sources.CODEGRAPH_STATS_RELPATH
    stats.parent.mkdir(parents=True)
    stats.write_text(json.dumps({"unrelated": True}), encoding="utf-8")
    assert sources.read_codegraph_hits_vs_reads(home) == "codegraph-stats-shape-unrecognized"


def test_codegraph_stats_names_not_recorded_when_index_present(tmp_path: Path) -> None:
    home = tmp_path / "home"
    index = home / CODEGRAPH_INDEX_RELPATH
    index.parent.mkdir(parents=True)
    index.write_text("{}", encoding="utf-8")
    assert sources.read_codegraph_hits_vs_reads(home) == "codegraph-stats-not-recorded"


def test_cocoindex_cache_hits_names_unreadable_index(tmp_path: Path) -> None:
    home = tmp_path / "home"
    index = home / sources.COCOINDEX_INDEX_RELPATH
    index.parent.mkdir(parents=True)
    index.write_text("not valid json", encoding="utf-8")
    assert sources.read_cocoindex_cache_hits(home) == "cocoindex-index-unreadable"


def test_cocoindex_cache_hits_falls_back_to_skipped_artifacts_length(tmp_path: Path) -> None:
    home = tmp_path / "home"
    index = home / sources.COCOINDEX_INDEX_RELPATH
    index.parent.mkdir(parents=True)
    index.write_text(json.dumps({"skipped_artifacts": ["a", "b", "c"]}), encoding="utf-8")
    assert sources.read_cocoindex_cache_hits(home) == 3


def test_cocoindex_cache_hits_names_not_recorded(tmp_path: Path) -> None:
    home = tmp_path / "home"
    index = home / sources.COCOINDEX_INDEX_RELPATH
    index.parent.mkdir(parents=True)
    index.write_text(json.dumps({"unrelated": True}), encoding="utf-8")
    assert sources.read_cocoindex_cache_hits(home) == "cocoindex-cache-hits-not-recorded"


def test_planning_graph_tokens_saved_names_retrieval_not_recorded(tmp_path: Path) -> None:
    home = tmp_path / "home"
    graph_path = home / sources.GRAPH_STORE_RELPATH
    graph_path.parent.mkdir(parents=True)
    graph_path.write_text("{}", encoding="utf-8")
    assert sources.read_planning_graph_tokens_saved(home) == "planning-graph-retrieval-not-recorded"


def test_planning_graph_tokens_saved_names_unreadable_telemetry(tmp_path: Path) -> None:
    home = tmp_path / "home"
    telemetry = home / sources.PLANNING_GRAPH_TELEMETRY_RELPATH
    telemetry.parent.mkdir(parents=True)
    telemetry.write_text("not valid json", encoding="utf-8")
    assert sources.read_planning_graph_tokens_saved(home) == "planning-graph-telemetry-unreadable"


def test_planning_graph_tokens_saved_zero_when_grounded_without_tokens(tmp_path: Path) -> None:
    home = tmp_path / "home"
    telemetry = home / sources.PLANNING_GRAPH_TELEMETRY_RELPATH
    telemetry.parent.mkdir(parents=True)
    telemetry.write_text(json.dumps({"grounded": True}), encoding="utf-8")
    assert sources.read_planning_graph_tokens_saved(home) == 0


def test_planning_graph_tokens_saved_names_not_recorded(tmp_path: Path) -> None:
    home = tmp_path / "home"
    telemetry = home / sources.PLANNING_GRAPH_TELEMETRY_RELPATH
    telemetry.parent.mkdir(parents=True)
    telemetry.write_text(json.dumps({"grounded": False}), encoding="utf-8")
    assert sources.read_planning_graph_tokens_saved(home) == "planning-graph-tokens-not-recorded"


def test_dispatch_idle_timing_no_runs_dir(tmp_path: Path) -> None:
    report = sources.read_dispatch_idle_timing(tmp_path)
    assert report["status"] == "no-dispatch-journals"
    assert report["sessions"] == []


def test_dispatch_idle_timing_skips_blank_malformed_and_non_numeric_lines(
    tmp_path: Path,
) -> None:
    runs = tmp_path / "_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs/run-a"
    runs.mkdir(parents=True)
    journal = runs / "journal.jsonl"
    journal.write_text(
        "\n".join(
            [
                "",
                "not valid json",
                json.dumps({"payload": "not-a-dict"}),
                json.dumps({"payload": {"idle_seconds": "not-a-number"}}),
                json.dumps({"payload": {"idle_seconds": 600}}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    report = sources.read_dispatch_idle_timing(tmp_path)
    assert report["status"] == "ok"
    assert report["sessions"][0]["idle_samples"] == 1


def test_dispatch_idle_timing_names_no_idle_samples(tmp_path: Path) -> None:
    runs = tmp_path / "_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs/run-a"
    runs.mkdir(parents=True)
    (runs / "journal.jsonl").write_text(
        json.dumps({"payload": {"no_idle_seconds_here": True}}) + "\n", encoding="utf-8"
    )
    report = sources.read_dispatch_idle_timing(tmp_path)
    assert report["status"] == "no-idle-samples"
    assert report["sessions"] == []


def test_read_rollup_by_harness_skips_glob_permission_error(tmp_path: Path, monkeypatch) -> None:
    runs_dir = tmp_path / "_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs"
    runs_dir.mkdir(parents=True)

    def _raises(self, _pattern):
        raise PermissionError("simulated unreadable dispatch-runs directory")

    monkeypatch.setattr(type(runs_dir), "glob", _raises, raising=False)
    report = sources.read_rollup_by_harness(tmp_path)
    assert report == {"status": "no-dispatch-journals", "harnesses": {}}


def test_read_rollup_by_harness_tolerates_blank_lines_and_non_dict_json(
    tmp_path: Path,
) -> None:
    runs_dir = tmp_path / "_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs"
    run_dir = runs_dir / "run-odd-shapes"
    run_dir.mkdir(parents=True)
    (run_dir / "journal.jsonl").write_text(
        "\n".join(
            [
                "",
                json.dumps(["not", "a", "dict"]),
                json.dumps(
                    {
                        "kind": "dispatch-launch",
                        "phase": "outcome",
                        "payload": {"ok": True, "harness_profile": "claude"},
                    }
                ),
                json.dumps({"kind": "some-other-kind", "phase": "observation", "payload": {}}),
                json.dumps(
                    {
                        "kind": "budget-usage",
                        "phase": "observation",
                        "payload": {"layer_savings": {"output_compression_saved": 500}},
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    report = sources.read_rollup_by_harness(tmp_path)
    assert report["status"] == "ok"
    assert report["harnesses"]["claude"]["silent"] == {"output_compression_saved": [500]}


def test_read_rollup_by_harness_skips_non_dict_payload(tmp_path: Path) -> None:
    runs_dir = tmp_path / "_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs"
    run_dir = runs_dir / "run-non-dict-payload"
    run_dir.mkdir(parents=True)
    (run_dir / "journal.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"kind": "dispatch-launch", "phase": "outcome", "payload": "oops"}),
                json.dumps({"kind": "budget-usage", "phase": "observation", "payload": "oops"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    report = sources.read_rollup_by_harness(tmp_path)
    assert report == {"status": "no-savings-samples", "harnesses": {}}


def test_dispatch_idle_timing_reads_journal_samples(tmp_path: Path) -> None:
    runs = tmp_path / "_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs/run-a"
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
