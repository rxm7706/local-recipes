"""Stories 45.1–45.3: generated Cursor .mdc files stay mechanical and honest."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import bmad_cursor_mdc_check as m  # noqa: E402


def test_generate_matches_check_on_a_tmp_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    skill_root = tmp_path / ".claude" / "skills"
    for name, desc in (
        ("bmad-build", "Turns work into code"),
        ("bmad-build-auto", "One unattended iteration"),
    ):
        d = skill_root / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: '{desc}'\n---\n\n"
            "Run render_skill.py then follow workflow.md.\n",
            encoding="utf-8",
        )
    monkeypatch.setattr(m, "ROOT", tmp_path)
    assert m.main(["--write"]) == 0
    assert m.main([]) == 0
    auto = (tmp_path / ".cursor" / "rules" / "bmad-build-auto.mdc").read_text(encoding="utf-8")
    assert "HALT" in auto
    assert "`blocked`/`no subagents`" in auto
    assert "cursor-agent -p" in auto
    assert "Do not shell out" in auto
    assert "@path" in auto
    assert "alwaysApply: false" in auto


def test_check_fails_when_mdc_is_stale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    skill_root = tmp_path / ".claude" / "skills" / "bmad-build"
    skill_root.mkdir(parents=True)
    (skill_root / "SKILL.md").write_text(
        "---\nname: bmad-build\ndescription: 'old'\n---\n\nbody\n",
        encoding="utf-8",
    )
    auto = tmp_path / ".claude" / "skills" / "bmad-build-auto"
    auto.mkdir(parents=True)
    (auto / "SKILL.md").write_text(
        "---\nname: bmad-build-auto\ndescription: 'old'\n---\n\nbody\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(m, "ROOT", tmp_path)
    assert m.main(["--write"]) == 0
    (tmp_path / ".cursor" / "rules" / "bmad-build.mdc").write_text("stale\n", encoding="utf-8")
    assert m.main([]) == 1


def test_check_fails_when_mdc_is_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("bmad-build", "bmad-build-auto"):
        d = tmp_path / ".claude" / "skills" / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: 'd'\n---\n\nbody\n",
            encoding="utf-8",
        )
    monkeypatch.setattr(m, "ROOT", tmp_path)
    assert m.main([]) == 1


def test_render_copies_skill_trigger_body() -> None:
    out = m.render("bmad-build", "Turns work into code", "Run render_skill.py.\n")
    assert "Run render_skill.py." in out
    assert "HALT" in out
    assert "Task tool" in out
