"""Unit tests for ``scripts/docs_skills_catalog.py`` (Story 30.3,
spec-pyforge-doctor CAP-84): docs/reference/skills-catalog.md generated
from every ``.claude/skills/*/`` directory's own frontmatter, across the
three real on-disk layouts (plain SKILL.md, SKF-exported active/<name>/
SKILL.md, skill-brief.yaml fallback) plus a non-skill support directory.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import _docs_gen_common as common  # noqa: E402
import docs_skills_catalog as m  # noqa: E402

_STAMP = {"derived_at": "2026-01-01T00:00:00", "tree": "deadbeef"}


def _write_plain_skill(root: Path, name: str, description: str) -> None:
    skill_dir = root / ".claude" / "skills" / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\nbody\n", encoding="utf-8"
    )


def _write_skf_exported_skill(root: Path, name: str, version: str, description: str) -> None:
    skill_dir = root / ".claude" / "skills" / name
    nested = skill_dir / version / name
    nested.mkdir(parents=True)
    (nested / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\nbody\n", encoding="utf-8"
    )
    (skill_dir / "active").symlink_to(version, target_is_directory=True)


def _write_skill_brief_only(root: Path, name: str, description: str) -> None:
    skill_dir = root / ".claude" / "skills" / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "skill-brief.yaml").write_text(
        yaml.safe_dump({"name": name, "description": description}), encoding="utf-8"
    )


def _write_non_skill_dir(root: Path, name: str) -> None:
    support_dir = root / ".claude" / "skills" / name
    support_dir.mkdir(parents=True)
    (support_dir / "notes.md").write_text("not a skill\n", encoding="utf-8")


def test_discover_skills_reads_all_three_layouts_and_skips_support_dirs(tmp_path: Path):
    _write_plain_skill(tmp_path, "bmad-example", "a bmad skill")
    _write_skf_exported_skill(tmp_path, "pyforge-example", "0.1.0", "a pyforge station skill")
    _write_skill_brief_only(tmp_path, "pyforge-brief-only", "brief-only fallback")
    _write_non_skill_dir(tmp_path, "shared")

    skills = m.discover_skills(tmp_path)

    names = {s["name"] for s in skills}
    assert names == {"bmad-example", "pyforge-example", "pyforge-brief-only"}


def test_discover_skills_categorizes_by_prefix(tmp_path: Path):
    _write_plain_skill(tmp_path, "bmad-example", "d")
    _write_plain_skill(tmp_path, "skf-example", "d")
    _write_plain_skill(tmp_path, "curated-example", "d")
    _write_skf_exported_skill(tmp_path, "pyforge-example", "0.1.0", "d")

    skills = {s["name"]: s["category"] for s in m.discover_skills(tmp_path)}

    assert skills == {
        "bmad-example": "bmad",
        "skf-example": "skf",
        "curated-example": "project",
        "pyforge-example": "pyforge station",
    }


def test_discover_skills_collapses_folded_yaml_description_to_one_line(tmp_path: Path):
    skill_dir = tmp_path / ".claude" / "skills" / "bmad-example"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: bmad-example\ndescription: >\n  line one\n  line two\n---\n\nbody\n",
        encoding="utf-8",
    )

    skills = m.discover_skills(tmp_path)

    assert skills[0]["description"] == "line one line two"


def test_render_is_deterministic(tmp_path: Path):
    _write_plain_skill(tmp_path, "bmad-example", "d")

    assert m.render(tmp_path, _STAMP) == m.render(tmp_path, dict(_STAMP))


def test_main_write_then_check_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _write_plain_skill(tmp_path, "bmad-example", "d")
    monkeypatch.setattr(common, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(common, "head_stamp", lambda root: dict(_STAMP))

    monkeypatch.setattr(sys, "argv", ["docs_skills_catalog.py"])
    assert m.main() == 0

    monkeypatch.setattr(sys, "argv", ["docs_skills_catalog.py", "--check"])
    assert m.main() == 0

    # A new skill, not yet regenerated -> --check reds it.
    _write_plain_skill(tmp_path, "bmad-second", "d")
    assert m.main() == 1
