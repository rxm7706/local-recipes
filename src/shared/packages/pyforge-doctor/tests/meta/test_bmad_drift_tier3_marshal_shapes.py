"""Story 43.1: ``TIER3_RUN_ARTIFACTS`` stays aligned with marshal Tier-3 writers (no import)."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

from pyforge.doctor.sources import factory

REPO_ROOT = Path(__file__).resolve().parents[6]
MARSHAL_SRC = REPO_ROOT / "src" / "shared" / "packages" / "pyforge-marshal" / "src" / "pyforge" / "marshal"
BMAD_BUILD_AUTO_WORKFLOW = REPO_ROOT / ".claude" / "skills" / "bmad-build-auto" / "workflow.md"

_IMPL_ARTIFACTS_SEGMENT_RE = re.compile(
    r"implementation-artifacts[/\"]([a-z0-9_{}-]+(?:/\.\.\.)?|[a-z0-9_{}-]+)"
)


@dataclass(frozen=True)
class _ShapeRow:
    segment_key: str
    sample_rel: str
    writer_path: Path
    writer_token: str


# Segments marshal builds directly under implementation-artifacts/ (Story 43.1 table).
_SHAPE_TABLE: tuple[_ShapeRow, ...] = (
    _ShapeRow(
        "dispatch-runs",
        "implementation-artifacts/dispatch-runs/run-a/journal.jsonl",
        MARSHAL_SRC / "core" / "layer_savings_sources.py",
        "dispatch-runs",
    ),
    _ShapeRow(
        "dispatch-runs-quarantine",
        "implementation-artifacts/dispatch-runs-quarantine/run-a/journal.jsonl",
        MARSHAL_SRC / "core" / "dispatch_stale.py",
        "dispatch-runs-quarantine",
    ),
    _ShapeRow(
        "epic-continuity",
        "implementation-artifacts/epic-97-continuity.md",
        MARSHAL_SRC / "core" / "derived_context.py",
        "continuity_output_relpath",
    ),
    _ShapeRow(
        "epic-context",
        "implementation-artifacts/epic-97-context.md",
        MARSHAL_SRC / "core" / "derived_context.py",
        "implementation_artifacts_relpath",
    ),
    _ShapeRow(
        "fleet-drain-runs",
        "implementation-artifacts/fleet-drain-runs/run-a/journal.jsonl",
        MARSHAL_SRC / "cli" / "spin.py",
        "fleet-drain-runs",
    ),
    _ShapeRow(
        "recall-feedback",
        "implementation-artifacts/recall-feedback__97.2__run.md",
        MARSHAL_SRC / "core" / "recall_feedback.py",
        "recall-feedback__",
    ),
    _ShapeRow(
        "recall-feedback-marker",
        "implementation-artifacts/recall-feedback__97.2__run.md.query-ran",
        MARSHAL_SRC / "adapters" / "harness_bmadloop.py",
        ".query-ran",
    ),
    _ShapeRow(
        "runs",
        "implementation-artifacts/runs/run-a/journal.jsonl",
        MARSHAL_SRC / "cli" / "status.py",
        'implementation-artifacts" / "runs"',
    ),
    _ShapeRow(
        "session-advisories",
        "implementation-artifacts/session-advisories/run-a/journal.jsonl",
        MARSHAL_SRC / "cli" / "context.py",
        "session-advisories",
    ),
    _ShapeRow(
        "sprint-status",
        "implementation-artifacts/sprint-status.yaml",
        MARSHAL_SRC / "cli" / "land.py",
        "sprint-status.yaml",
    ),
    _ShapeRow(
        "token-economy-benchmark",
        "implementation-artifacts/token-economy-benchmark-2026-10-12T103206Z.json",
        MARSHAL_SRC / "cli" / "benchmark.py",
        "token-economy-benchmark-",
    ),
    _ShapeRow(
        "token-economy-benchmark-per-layer",
        "implementation-artifacts/token-economy-benchmark-per-layer-2026-10-12T103206Z.json",
        MARSHAL_SRC / "cli" / "benchmark.py",
        "token-economy-benchmark-per-layer-",
    ),
    _ShapeRow(
        "bmad-build-auto-result",
        "implementation-artifacts/bmad-build-auto-result-97-2-some-story.md",
        BMAD_BUILD_AUTO_WORKFLOW,
        "bmad-build-auto-result-",
    ),
)


def _collect_impl_segments_from_source(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    found: set[str] = set()
    for match in _IMPL_ARTIFACTS_SEGMENT_RE.finditer(text):
        seg = match.group(1).split("/")[0].split("{")[0].rstrip("-")
        if seg and seg not in {"..", "."}:
            found.add(seg)
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return found
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            val = node.value
            if "implementation-artifacts/" not in val:
                continue
            tail = val.split("implementation-artifacts/", 1)[1].split("/")[0]
            tail = tail.split("{")[0].rstrip("-")
            if tail:
                found.add(tail)
    return found


def _normalize_segment(name: str) -> str:
    if name.startswith("epic-") and name.endswith("-continuity.md"):
        return "epic-continuity"
    if name.startswith("epic-") and name.endswith("-context.md"):
        return "epic-context"
    if name.startswith("recall-feedback"):
        return "recall-feedback"
    if name.startswith("token-economy-benchmark-per-layer"):
        return "token-economy-benchmark-per-layer"
    if name.startswith("token-economy-benchmark"):
        return "token-economy-benchmark"
    if name.startswith("bmad-build-auto-result"):
        return "bmad-build-auto-result"
    return name


def _table_segment_keys() -> set[str]:
    keys: set[str] = set()
    for row in _SHAPE_TABLE:
        keys.add(row.segment_key)
    return keys


def test_every_table_sample_classifies_to_a_tier3_rule(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    proj = factory._proj(repo)
    proj.mkdir(parents=True)
    for row in _SHAPE_TABLE:
        suffix = row.sample_rel.removeprefix("implementation-artifacts/")
        path = proj / suffix
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n", encoding="utf-8")
        cls = factory.classify(path, repo)
        assert cls != "UNKNOWN", row.sample_rel
        assert any(r.classification == cls for r in factory.TIER3_RUN_ARTIFACTS), (row.sample_rel, cls)


def test_writer_tokens_still_present_in_cited_sources() -> None:
    for row in _SHAPE_TABLE:
        assert row.writer_path.is_file(), row.writer_path
        text = row.writer_path.read_text(encoding="utf-8")
        assert row.writer_token in text, (row.segment_key, row.writer_path, row.writer_token)


def test_marshal_scan_segments_have_table_rows() -> None:
    collected: set[str] = set()
    for path in MARSHAL_SRC.rglob("*.py"):
        for seg in _collect_impl_segments_from_source(path):
            collected.add(_normalize_segment(seg))
    # deferred-work.md and spec shapes use non-TIER3 classify rules — not required here.
    skip = {"deferred-work.md", "spec", "specs", "sprint-status-ledger.yaml"}
    table_keys = _table_segment_keys()
    missing = sorted(s for s in collected if s not in table_keys and s not in skip)
    assert not missing, f"unlisted marshal Tier-3 segments: {missing}"


def test_fixture_new_kind_fails_scan(tmp_path: Path) -> None:
    fixture = tmp_path / "fake_marshal_module.py"
    fixture.write_text(
        'run_dir = root / "implementation-artifacts" / "new-kind"\n',
        encoding="utf-8",
    )
    segs = _collect_impl_segments_from_source(fixture)
    assert "new-kind" in segs
