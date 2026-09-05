"""Station-owned SKF skill provenance for pyforge-scribe (Story 5.1).

Steward 29.1 already compiled the skill. This suite owns the remaining
gap: the station fails if provenance is not scribe-package-backed.
It does not require a recompile and does not assert generated_at freshness.
"""

from __future__ import annotations

import json
from pathlib import Path

from pyforge.testing_kit import changed_paths_since, pyforge_import_offenders

STATION = "scribe"
SKILL_NAME = f"pyforge-{STATION}"


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / ".claude" / "skills").is_dir():
            return candidate
    raise AssertionError("could not locate repo root (pixi.toml + .claude/skills)")


def _skill_package(root: Path) -> Path:
    active = (root / ".claude" / "skills" / SKILL_NAME / "active").resolve()
    return active / SKILL_NAME


def test_skill_exists_with_scribe_package_provenance():
    root = _repo_root()
    pkg = _skill_package(root)
    assert pkg.is_dir(), f"missing compiled skill package {pkg}"

    provenance = json.loads((pkg / "provenance-map.json").read_text(encoding="utf-8"))
    meta = json.loads((pkg / "metadata.json").read_text(encoding="utf-8"))

    assert meta["generated_by"] == "create-skill"
    assert meta["name"] == SKILL_NAME
    assert meta["source_repo"].endswith(f"pyforge-{STATION}")
    assert provenance["source_commit"]
    assert provenance["entries"], "provenance-map.json must pin at least one export"
    for entry in provenance["entries"]:
        src = entry["source_file"]
        assert f"pyforge-{STATION}" in src
        path = root / src
        assert path.is_file(), src
        line = int(entry["source_line"])
        assert line >= 1
        text = path.read_text(encoding="utf-8").splitlines()
        assert line <= len(text), f"{src}:{line} out of range"

    brief = root / ".claude" / "skills" / SKILL_NAME / "skill-brief.yaml"
    assert brief.is_file()
    brief_text = brief.read_text(encoding="utf-8")
    assert f"src/shared/packages/pyforge-{STATION}" in brief_text
    assert SKILL_NAME in brief_text

    body = (pkg / "SKILL.md").read_text(encoding="utf-8")
    assert "scribe capture" in body
    assert "scribe graph compile" in body
    assert "scribe recall" in body


def test_conda_forge_expert_unchanged_shape():
    root = _repo_root()
    cfe = root / ".claude" / "skills" / "conda-forge-expert"
    assert (cfe / "SKILL.md").is_file()
    assert not (cfe / "metadata.json").exists()
    assert not (cfe / "active").exists()
    skill = (cfe / "SKILL.md").read_text(encoding="utf-8")
    assert "conda-forge" in skill.lower()


def test_story_does_not_edit_claude_or_agents():
    root = _repo_root()
    changed = changed_paths_since(root, pathspec=("CLAUDE.md", "AGENTS.md"))
    assert not changed, f"Wave A must not edit CLAUDE.md/AGENTS.md: {changed}"


def test_story_does_not_add_pyforge_under_src_platform():
    root = _repo_root()
    changed = changed_paths_since(root, pathspec="src/platform")
    offenders = pyforge_import_offenders(changed, root)
    assert not offenders, f"src/platform pyforge imports in this diff: {changed} {offenders}"
