"""CAP-53: live ``presentations/`` tree holds at most one dated export per kind."""

from __future__ import annotations

from pathlib import Path

from pyforge.herald import deck_versions

_REPO_ROOT = Path(__file__).resolve().parents[6]


def test_live_presentations_tree_has_no_superseded_exports():
    pairs = deck_versions.superseded(_REPO_ROOT)
    assert not pairs, "\n".join(f"{old} (keep {cur})" for old, cur in pairs)


def test_two_dates_one_kind_reports_older(tmp_path: Path):
    pptx_dir = tmp_path / "presentations" / "demo" / "src" / "pptx"
    pptx_dir.mkdir(parents=True)
    older = pptx_dir / "x-deck-2026-07-24.pptx"
    current = pptx_dir / "x-deck-2026-09-15.pptx"
    older.write_bytes(b"old")
    current.write_bytes(b"new")
    pairs = deck_versions.superseded(tmp_path)
    assert pairs == [(older, current)]


def test_look_alike_stems_are_two_kinds(tmp_path: Path):
    marp_dir = tmp_path / "presentations" / "demo" / "src" / "marp"
    marp_dir.mkdir(parents=True)
    (marp_dir / "x-infographic-2026-07-24.md").write_text("a", encoding="utf-8")
    (marp_dir / "x-infographic-deck-narration-2026-07-31.md").write_text("b", encoding="utf-8")
    assert deck_versions.superseded(tmp_path) == []


def test_single_date_older_than_sibling_kinds_kept(tmp_path: Path):
    marp_dir = tmp_path / "presentations" / "demo" / "src" / "marp"
    marp_dir.mkdir(parents=True)
    (marp_dir / "x-narration-2026-07-31.md").write_text("n", encoding="utf-8")
    pptx_dir = tmp_path / "presentations" / "demo" / "src" / "pptx"
    pptx_dir.mkdir(parents=True)
    (pptx_dir / "x-deck-2026-09-15.pptx").write_bytes(b"d")
    assert deck_versions.superseded(tmp_path) == []


def test_sidecar_listed_with_superseded_export(tmp_path: Path):
    pptx_dir = tmp_path / "presentations" / "demo" / "src" / "pptx"
    pptx_dir.mkdir(parents=True)
    older = pptx_dir / "x-deck-2026-07-24.pptx"
    current = pptx_dir / "x-deck-2026-09-15.pptx"
    older.write_bytes(b"old")
    current.write_bytes(b"new")
    sidecar = pptx_dir / "x-deck-2026-07-24.pptx.stamp.json"
    sidecar.write_text("{}", encoding="utf-8")
    assert deck_versions.superseded(tmp_path) == [(older, current)]
    assert sidecar.is_file()


def test_undated_files_never_grouped(tmp_path: Path):
    topic = tmp_path / "presentations" / "demo"
    topic.mkdir(parents=True)
    (topic / "facts.yaml").write_text("{}", encoding="utf-8")
    marp = topic / "src" / "marp"
    marp.mkdir(parents=True)
    (marp / "notes.md").write_text("undated", encoding="utf-8")
    assert deck_versions.superseded(tmp_path) == []


def test_module_main_exit_code(tmp_path: Path, capsys):
    pptx_dir = tmp_path / "presentations" / "demo" / "src" / "pptx"
    pptx_dir.mkdir(parents=True)
    (pptx_dir / "x-deck-2026-07-24.pptx").write_bytes(b"1")
    (pptx_dir / "x-deck-2026-09-15.pptx").write_bytes(b"2")
    assert deck_versions.main(["--root", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "x-deck-2026-07-24.pptx" in out
    assert "x-deck-2026-09-15.pptx" in out


def test_module_main_clean_tree(tmp_path: Path):
    marp_dir = tmp_path / "presentations" / "demo" / "src" / "marp"
    marp_dir.mkdir(parents=True)
    (marp_dir / "x-deck-2026-09-15.md").write_text("only", encoding="utf-8")
    assert deck_versions.main(["--root", str(tmp_path)]) == 0


def test_module_main_root_names_the_presentations_dir(tmp_path: Path):
    pptx_dir = tmp_path / "presentations" / "demo" / "src" / "pptx"
    pptx_dir.mkdir(parents=True)
    (pptx_dir / "x-deck-2026-07-24.pptx").write_bytes(b"1")
    (pptx_dir / "x-deck-2026-09-15.pptx").write_bytes(b"2")
    assert deck_versions.main(["--root", str(tmp_path / "presentations")]) == 1


def test_module_main_refuses_a_root_without_presentations(tmp_path: Path, capsys):
    assert deck_versions.main(["--root", str(tmp_path / "missing")]) == 2
    assert "no presentations/ directory" in capsys.readouterr().err
