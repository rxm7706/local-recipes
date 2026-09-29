"""Unit tests for ``pyforge.marshal.scope.verify_scope`` (Story 20.6 / FR-190 CAP-1).

Matrix: agree→None; A-vs-B→ScopeDrift naming found-vs-expected;
unrecognized symlink shapes→``"unrecognized"`` (never inferred agreement).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from pyforge.marshal.scope import UNRECOGNIZED, ScopeDrift, verify_scope

_SCOPE_SRC = Path(__file__).resolve().parents[2] / "src" / "pyforge" / "marshal" / "scope.py"


def _point_triangle(root: Path, slug: str) -> None:
    """Write marker + both artifact symlinks at the recognized relative shape."""
    marker = root / "_bmad" / "custom" / ".active-project"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(slug + "\n", encoding="utf-8")
    out = root / "_bmad-output"
    out.mkdir(parents=True, exist_ok=True)
    for name in ("planning-artifacts", "implementation-artifacts"):
        target_dir = out / "projects" / slug / name
        target_dir.mkdir(parents=True, exist_ok=True)
        link = out / name
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(Path("projects") / slug / name)


def test_all_agree_on_expected_returns_none(tmp_path: Path) -> None:
    _point_triangle(tmp_path, "pyforge-marshal")
    assert verify_scope(tmp_path, "pyforge-marshal") is None


def test_consistent_wrong_slug_is_drift_naming_found_vs_expected(tmp_path: Path) -> None:
    """DW-1-4-2 blind spot (2): B/B/B vs expected A is drift, not a pass."""
    _point_triangle(tmp_path, "project-b")
    drift = verify_scope(tmp_path, "project-a")
    assert isinstance(drift, ScopeDrift)
    assert drift.expected == "project-a"
    assert drift.marker == "project-b"
    assert drift.planning_artifacts == "project-b"
    assert drift.implementation_artifacts == "project-b"


@pytest.mark.parametrize(
    "bad_target",
    [
        Path("/absolute/projects/foo/planning-artifacts"),
        Path("projects/foo/extra/planning-artifacts"),
        Path("elsewhere/foo/planning-artifacts"),
        Path("projects/foo/wrong-leaf"),
    ],
)
def test_unrecognized_planning_symlink_shape_reports_unrecognized(tmp_path: Path, bad_target: Path) -> None:
    """DW-1-4-2 blind spot (1): foreign shapes are never inferred agreement."""
    _point_triangle(tmp_path, "ok-slug")
    link = tmp_path / "_bmad-output" / "planning-artifacts"
    link.unlink()
    link.symlink_to(bad_target)
    drift = verify_scope(tmp_path, "ok-slug")
    assert isinstance(drift, ScopeDrift)
    assert drift.expected == "ok-slug"
    assert drift.marker == "ok-slug"
    assert drift.planning_artifacts == UNRECOGNIZED
    assert drift.planning_artifacts == "unrecognized"
    assert drift.implementation_artifacts == "ok-slug"


def test_unrecognized_implementation_symlink_shape_reports_unrecognized(
    tmp_path: Path,
) -> None:
    _point_triangle(tmp_path, "ok-slug")
    link = tmp_path / "_bmad-output" / "implementation-artifacts"
    link.unlink()
    link.symlink_to(Path("/tmp/foreign-impl"))
    drift = verify_scope(tmp_path, "ok-slug")
    assert isinstance(drift, ScopeDrift)
    assert drift.implementation_artifacts == UNRECOGNIZED
    assert drift.marker == "ok-slug"
    assert drift.planning_artifacts == "ok-slug"


def test_missing_triangle_corners_are_unrecognized_not_match(tmp_path: Path) -> None:
    """Empty root: fail-closed — never treat absence as agreement with expected."""
    drift = verify_scope(tmp_path, "anything")
    assert isinstance(drift, ScopeDrift)
    assert drift.expected == "anything"
    assert drift.marker == UNRECOGNIZED
    assert drift.planning_artifacts == UNRECOGNIZED
    assert drift.implementation_artifacts == UNRECOGNIZED


def test_expected_slug_unrecognized_token_never_agrees(tmp_path: Path) -> None:
    """Fail-closed token must never be a successful expected_slug (false pass)."""
    drift = verify_scope(tmp_path, UNRECOGNIZED)
    assert isinstance(drift, ScopeDrift)
    assert drift.expected == UNRECOGNIZED
    assert drift.marker == UNRECOGNIZED
    assert drift.planning_artifacts == UNRECOGNIZED
    assert drift.implementation_artifacts == UNRECOGNIZED


def test_empty_marker_with_valid_links_is_unrecognized(tmp_path: Path) -> None:
    _point_triangle(tmp_path, "ok-slug")
    marker = tmp_path / "_bmad" / "custom" / ".active-project"
    marker.write_text("   \n", encoding="utf-8")
    drift = verify_scope(tmp_path, "ok-slug")
    assert isinstance(drift, ScopeDrift)
    assert drift.marker == UNRECOGNIZED
    assert drift.planning_artifacts == "ok-slug"
    assert drift.implementation_artifacts == "ok-slug"


def test_non_symlink_occupant_is_unrecognized(tmp_path: Path) -> None:
    _point_triangle(tmp_path, "ok-slug")
    link = tmp_path / "_bmad-output" / "planning-artifacts"
    link.unlink()
    link.mkdir()
    drift = verify_scope(tmp_path, "ok-slug")
    assert isinstance(drift, ScopeDrift)
    assert drift.planning_artifacts == UNRECOGNIZED


def test_dot_segment_symlink_slug_is_unrecognized(tmp_path: Path) -> None:
    _point_triangle(tmp_path, "ok-slug")
    link = tmp_path / "_bmad-output" / "planning-artifacts"
    link.unlink()
    link.symlink_to(Path("projects") / ".." / "planning-artifacts")
    drift = verify_scope(tmp_path, "ok-slug")
    assert isinstance(drift, ScopeDrift)
    assert drift.planning_artifacts == UNRECOGNIZED


def test_non_utf8_marker_is_unrecognized(tmp_path: Path) -> None:
    _point_triangle(tmp_path, "ok-slug")
    marker = tmp_path / "_bmad" / "custom" / ".active-project"
    marker.write_bytes(b"\xff\xfe not utf-8")
    drift = verify_scope(tmp_path, "ok-slug")
    assert isinstance(drift, ScopeDrift)
    assert drift.marker == UNRECOGNIZED


def test_verify_scope_source_has_no_subprocess() -> None:
    """CAP-1: three file reads + string compares; no subprocess."""
    tree = ast.parse(_SCOPE_SRC.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(alias.name.split(".", 1)[0] != "subprocess" for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".", 1)[0] != "subprocess"
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            assert not (node.value.id == "subprocess")
