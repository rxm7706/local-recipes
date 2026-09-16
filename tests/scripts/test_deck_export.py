"""Story 21.5 — deck-export stamps exec/marp from facts.yaml (CAP-3)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import deck_export as de  # noqa: E402


def _facts_yaml() -> str:
    return (
        "deck: demo\n"
        "facts:\n"
        "  - id: tree_commit_date\n"
        "    value: \"2026-09-01\"\n"
        "  - id: cfe_skill_version\n"
        "    value: \"8.90.5\"\n"
        "  - id: bmad_core_version\n"
        "    value: \"6.12.0\"\n"
        "  - id: fleet_epics_done_total\n"
        "    value: \"1/2\"\n"
        "  - id: fleet_stories_done_total\n"
        "    value: \"3/4\"\n"
    )


def _exec_html() -> str:
    return (
        "<!DOCTYPE html><html><body><x-dc>"
        "<p>Catch risky dependencies before they ship.</p>"
        "</x-dc></body></html>\n"
    )


def _marp_md() -> str:
    return "---\nmarp: true\n---\n\n# Demo\n\nHello.\n"


def test_load_fact_values(tmp_path: Path) -> None:
    p = tmp_path / "facts.yaml"
    p.write_text(_facts_yaml(), encoding="utf-8")
    got = de.load_fact_values(p)
    assert got["tree_commit_date"] == "2026-09-01"
    assert got["cfe_skill_version"] == "8.90.5"


def test_stamp_exec_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "Demo - Executive Summary.dc.html"
    path.write_text(_exec_html(), encoding="utf-8")
    facts = de.load_fact_values(tmp_path / "x")  # empty
    facts = {
        "tree_commit_date": "2026-09-01",
        "cfe_skill_version": "8.90.5",
        "bmad_core_version": "6.12.0",
        "fleet_epics_done_total": "1/2",
        "fleet_stories_done_total": "3/4",
    }
    de.stamp_exec_summary(path, facts)
    first = path.read_text(encoding="utf-8")
    assert 'data-fact="tree_commit_date"' in first
    assert ">2026-09-01<" in first
    de.stamp_exec_summary(path, facts)
    assert path.read_text(encoding="utf-8") == first
    facts["cfe_skill_version"] = "9.0.0"
    de.stamp_exec_summary(path, facts)
    second = path.read_text(encoding="utf-8")
    assert ">9.0.0<" in second
    assert first != second
    assert first.count(de.BAND_ATTR) == second.count(de.BAND_ATTR) == 1


def test_stamp_marp_then_fact_change(tmp_path: Path) -> None:
    src = tmp_path / "demo-infographic-2026-07-15.md"
    dest = tmp_path / "demo-infographic-2026-09-15.md"
    src.write_text(_marp_md(), encoding="utf-8")
    facts = {"tree_commit_date": "2026-09-01", "cfe_skill_version": "8.90.5"}
    de.stamp_marp_source(src, dest, facts)
    text = dest.read_text(encoding="utf-8")
    assert de.MARP_BAND in text
    assert 'data-fact="cfe_skill_version"' in text
    de.stamp_marp_source(dest, dest, {**facts, "cfe_skill_version": "9.0.0"})
    again = dest.read_text(encoding="utf-8")
    assert again.count(de.MARP_BAND) == 1
    assert ">9.0.0<" in again
    assert ">8.90.5<" not in again


def test_find_source_ignores_narration_suffix(tmp_path: Path) -> None:
    (tmp_path / "demo-infographic-2026-07-24.md").write_text("# old\n", encoding="utf-8")
    (tmp_path / "demo-infographic-2026-09-15.md").write_text("# new\n", encoding="utf-8")
    (tmp_path / "demo-infographic-deck-narration-2026-07-31.md").write_text(
        "# narration\n", encoding="utf-8"
    )
    src, day = de.find_source(str(tmp_path), "demo", "infographic")
    assert day == "2026-09-15"
    assert src.endswith("demo-infographic-2026-09-15.md")


def test_format_to_targets() -> None:
    assert de.format_to_targets("summary", []) == set()
    assert de.format_to_targets("pptx", []) == {"deck-pptx", "infographic-pptx"}
    assert de.format_to_targets("html", []) == {"html"}
    assert de.format_to_targets("all", []) == de.VALID_TARGETS
    assert de.format_to_targets(None, []) == de.VALID_TARGETS
    assert de.format_to_targets(None, ["html"]) == {"html"}


def test_cli_summary_updates_exec_and_skips_marp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "repo"
    deck = root / "presentations" / "demo"
    project = deck / "project"
    marp = deck / "src" / "marp"
    project.mkdir(parents=True)
    marp.mkdir(parents=True)
    (deck / "facts.yaml").write_text(_facts_yaml(), encoding="utf-8")
    exec_path = project / "Demo - Executive Summary.dc.html"
    exec_path.write_text(_exec_html(), encoding="utf-8")
    (marp / "demo-infographic-2026-07-15.md").write_text(_marp_md(), encoding="utf-8")
    monkeypatch.setattr(de, "ROOT", str(root))
    monkeypatch.setattr(sys, "argv", ["deck_export.py", "demo", "--format", "summary"])
    de.main()
    body = exec_path.read_text(encoding="utf-8")
    assert 'data-fact="fleet_stories_done_total"' in body
    assert ">3/4<" in body
    # summary does not date-stamp marp
    assert not list(marp.glob("demo-infographic-2026-09-15.md"))
