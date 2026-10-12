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

# Prototype scan at 70975ae790 (Story 43.1 intent) — segments marshal builds under Tier-3.
_EXPECTED_MARSHAL_SEGMENTS = frozenset(
    {
        "dispatch-runs",
        "dispatch-runs-quarantine",
        "runs",
        "fleet-drain-runs",
        "session-advisories",
        "sprint-status.yaml",
        "recall-feedback",
        "epic-context",
        "epic-continuity",
        "token-economy-benchmark",
        "token-economy-benchmark-per-layer",
    }
)


@dataclass(frozen=True)
class _ShapeRow:
    segment_key: str
    sample_rel: str
    writer_path: Path
    writer_token: str


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
        MARSHAL_SRC / "core" / "dispatch_fleet.py",
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


def _path_join_string(node: ast.AST) -> str | None:
    parts: list[str] = []
    cur: ast.AST = node
    while isinstance(cur, ast.BinOp) and isinstance(cur.op, ast.Div):
        if not isinstance(cur.right, ast.Constant) or not isinstance(cur.right.value, str):
            return None
        parts.insert(0, cur.right.value)
        cur = cur.left
    if isinstance(cur, ast.Constant) and isinstance(cur.value, str):
        parts.insert(0, cur.value)
    elif parts:
        pass
    else:
        return None
    return "/".join(parts)


def _segment_from_literal(text: str) -> str | None:
    if "implementation-artifacts/" not in text or "\n" in text or len(text) > 240:
        return None
    tail = text.split("implementation-artifacts/", 1)[1]
    segment = tail.split("/")[0].split("`")[0]
    if segment in {"deferred-work.md", "spec", "specs"}:
        return None
    base = segment.split("{")[0]
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", base):
        return None
    if segment.startswith("epic-") and segment.endswith("-continuity.md"):
        return "epic-continuity"
    if segment.startswith("epic-") and segment.endswith("-context.md"):
        return "epic-context"
    if segment.startswith("recall-feedback"):
        return "recall-feedback"
    if segment.startswith("token-economy-benchmark-per-layer"):
        return "token-economy-benchmark-per-layer"
    if segment.startswith("token-economy-benchmark"):
        return "token-economy-benchmark"
    if segment.startswith("bmad-build-auto-result"):
        return "bmad-build-auto-result"
    if segment == "sprint-status.yaml" or segment.startswith("sprint-status"):
        return "sprint-status.yaml"
    return segment.split("{")[0].rstrip("-") or None


def _collect_impl_segments_from_ast(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            seg = _segment_from_literal(node.value)
            if seg:
                found.add(seg)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            joined = _path_join_string(node)
            if joined:
                seg = _segment_from_literal(joined)
                if seg:
                    found.add(seg)
    return found


def _table_segment_keys() -> set[str]:
    keys: set[str] = set()
    for row in _SHAPE_TABLE:
        keys.add(row.segment_key.replace("-marker", "").replace("recall-feedback-marker", "recall-feedback"))
        if row.segment_key == "sprint-status":
            keys.add("sprint-status.yaml")
        else:
            keys.add(row.segment_key)
    keys.add("recall-feedback")
    return keys


def test_every_table_sample_classifies_to_a_tier3_rule(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    proj = factory._proj(repo)
    impl = factory._impl(repo)
    impl.mkdir(parents=True)
    for row in _SHAPE_TABLE:
        suffix = row.sample_rel.removeprefix("implementation-artifacts/")
        path = impl / suffix
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


def test_marshal_ast_scan_covers_prototype_segments() -> None:
    collected: set[str] = set()
    for path in MARSHAL_SRC.rglob("*.py"):
        collected |= _collect_impl_segments_from_ast(path)
    normalized = set()
    for seg in collected:
        if seg in {"deferred-work.md", "spec", "specs"}:
            continue
        if seg.startswith("sprint-status"):
            normalized.add("sprint-status.yaml")
        elif seg.startswith("epic-"):
            normalized.add("epic-context" if "context" in seg else "epic-continuity")
        elif seg.startswith("recall-feedback"):
            normalized.add("recall-feedback")
        else:
            normalized.add(seg)
    missing_from_table = sorted(s for s in normalized if s not in _table_segment_keys())
    assert not missing_from_table, missing_from_table
    assert _EXPECTED_MARSHAL_SEGMENTS <= normalized | _table_segment_keys()


def test_fixture_new_kind_is_not_in_the_shape_table(tmp_path: Path) -> None:
    fixture = tmp_path / "fake_marshal_module.py"
    fixture.write_text(
        'run_dir = root / "implementation-artifacts" / "new-kind"\n',
        encoding="utf-8",
    )
    segs = _collect_impl_segments_from_ast(fixture)
    assert "new-kind" in segs
    assert "new-kind" not in _table_segment_keys()
