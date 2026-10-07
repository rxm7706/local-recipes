"""CAP-53 Story 28.2: ``retire_superseded`` after each dated export write."""

from __future__ import annotations

from pathlib import Path

from pyforge.herald import deck_versions


def _pptx_dir(tmp_path: Path) -> Path:
    return tmp_path / "presentations" / "demo" / "src" / "pptx"


def test_retire_superseded_removes_older_same_kind(tmp_path: Path) -> None:
    pptx_dir = _pptx_dir(tmp_path)
    pptx_dir.mkdir(parents=True)
    older = pptx_dir / "x-deck-2026-09-15.pptx"
    newer = pptx_dir / "x-deck-2026-10-02.pptx"
    older.write_bytes(b"old")
    newer.write_bytes(b"new")

    result = deck_versions.retire_superseded(newer)

    assert result.written_superseded is False
    assert older in result.retired
    assert not older.is_file()
    assert newer.is_file()
    assert deck_versions.superseded(tmp_path) == []


def test_retire_superseded_removes_sidecar_with_export(tmp_path: Path) -> None:
    pptx_dir = _pptx_dir(tmp_path)
    pptx_dir.mkdir(parents=True)
    older = pptx_dir / "x-deck-2026-09-15.pptx"
    newer = pptx_dir / "x-deck-2026-10-02.pptx"
    older.write_bytes(b"old")
    newer.write_bytes(b"new")
    sidecar = pptx_dir / "x-deck-2026-09-15.pptx.stamp.json"
    sidecar.write_text("{}", encoding="utf-8")

    deck_versions.retire_superseded(newer)

    assert not older.is_file()
    assert not sidecar.is_file()


def test_retire_superseded_leaves_other_kinds(tmp_path: Path) -> None:
    marp_dir = tmp_path / "presentations" / "demo" / "src" / "marp"
    marp_dir.mkdir(parents=True)
    other = marp_dir / "x-infographic-deck-narration-2026-07-31.md"
    older = marp_dir / "x-infographic-2026-09-15.md"
    newer = marp_dir / "x-infographic-2026-10-02.md"
    other.write_text("n", encoding="utf-8")
    older.write_text("old", encoding="utf-8")
    newer.write_text("new", encoding="utf-8")

    deck_versions.retire_superseded(newer)

    assert not older.is_file()
    assert other.is_file()
    assert newer.is_file()


def test_retire_superseded_same_day_overwrite_retires_nothing(tmp_path: Path) -> None:
    pptx_dir = _pptx_dir(tmp_path)
    pptx_dir.mkdir(parents=True)
    path = pptx_dir / "x-deck-2026-10-02.pptx"
    path.write_bytes(b"v1")
    path.write_bytes(b"v2")

    result = deck_versions.retire_superseded(path)

    assert result == deck_versions.RetireSupersededResult((), False)
    assert path.read_bytes() == b"v2"


def test_retire_superseded_backdated_write_reports_superseded(tmp_path: Path) -> None:
    pptx_dir = _pptx_dir(tmp_path)
    pptx_dir.mkdir(parents=True)
    current = pptx_dir / "x-deck-2026-09-15.pptx"
    backdated = pptx_dir / "x-deck-2026-09-01.pptx"
    older = pptx_dir / "x-deck-2026-08-01.pptx"
    current.write_bytes(b"current")
    backdated.write_bytes(b"back")
    older.write_bytes(b"older")

    result = deck_versions.retire_superseded(backdated)

    assert result.written_superseded is True
    assert result.retired == ()
    assert current.is_file()
    assert backdated.is_file()
    assert older.is_file()


def test_retire_superseded_ignores_undated_files(tmp_path: Path) -> None:
    topic = tmp_path / "presentations" / "demo"
    marp = topic / "src" / "marp"
    marp.mkdir(parents=True)
    (topic / "facts.yaml").write_text("{}", encoding="utf-8")
    (marp / "notes.md").write_text("undated", encoding="utf-8")
    newer = marp / "x-deck-2026-10-02.md"
    newer.write_text("new", encoding="utf-8")

    deck_versions.retire_superseded(newer)

    assert (marp / "notes.md").is_file()
