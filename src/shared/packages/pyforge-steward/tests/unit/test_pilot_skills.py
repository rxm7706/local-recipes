"""Story 109.2 — the three pilot skills do not depend on the estate environment."""

from __future__ import annotations

from pathlib import Path

from pyforge.steward.bootstrap import repo_root

_SKILLS = Path("docs/foundry/marketplace/skills")
_PILOTS = ("mason/environment", "mason/package", "warden/scan")


def _texts() -> list[tuple[str, str]]:
    root = repo_root() / _SKILLS
    found: list[tuple[str, str]] = []
    for relative in _PILOTS:
        folder = root / relative
        for name in ("SKILL.md", "steps.md"):
            found.append((f"{relative}/{name}", (folder / name).read_text(encoding="utf-8")))
    return found


def test_each_pilot_has_a_skill_and_steps() -> None:
    names = [path for path, _text in _texts()]
    assert names == [
        "mason/environment/SKILL.md",
        "mason/environment/steps.md",
        "mason/package/SKILL.md",
        "mason/package/steps.md",
        "warden/scan/SKILL.md",
        "warden/scan/steps.md",
    ]


def test_pilot_skills_do_not_invoke_the_estate_environment() -> None:
    for path, text in _texts():
        assert "pixi run -e" not in text, path
        assert "pixi run --frozen -e" not in text, path


def test_pilot_skills_name_the_commands_that_were_verified() -> None:
    by_path = dict(_texts())
    environment = by_path["mason/environment/steps.md"]
    assert "conda-lock lock -f pyproject.toml --lockfile conda-lock.yml" in environment
    assert "env.lock" not in environment
    assert "--conda environment.yml" not in environment
    assert "conda-lock, version 4.0.2" in environment or "conda-lock` 4.0.2" in environment
    package = by_path["mason/package/steps.md"]
    assert "pyproject-build --no-isolation" in package
    assert "pixi build --output-dir dist" in package
    assert "Do not run them" in package or "Do not upload" in package
    warden = by_path["warden/scan/steps.md"]
    assert "warden scan ." in warden
    assert "deptry" in warden
    assert "osv-scanner" in warden
    for path, text in _texts():
        assert "404" in text or "Unpublished" in text, path
