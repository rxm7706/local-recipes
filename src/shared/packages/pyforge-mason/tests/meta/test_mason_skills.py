"""Story 19.2+ — hand-authored Mason craft skills (mason-package, …)."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

import pytest
import yaml

CFE_LINK_FRAGMENT = ".claude/skills/conda-forge-expert/"
GOTCHA_HEADING_RE = re.compile(r"^### G\d+\.", re.MULTILINE)

# Extend in Story 19.4 (feedstock campaigns).
MASON_HAND_AUTHORED_SKILLS: tuple[dict[str, object], ...] = (
    {
        "skill_dir": "mason-package",
        "expected_name": "mason-package",
        "required_phrases": (
            "pyforge mason package build",
            "pyforge mason package ship",
            "pypi-test",
            "pypi",
            "conda-forge",
            "channel:",
            "--yes",
        ),
        "gate_phrases": (
            "pypi-test",
            "pypi",
            "gate",
        ),
    },
    {
        "skill_dir": "mason-environment",
        "expected_name": "mason-environment",
        "required_phrases": (
            "pyforge mason environment lock",
            "pyforge mason environment check",
            "discover",
            "explicit",
            "--platform",
            "engine_name",
            "engine_version",
            "conda-lock",
        ),
    },
)


class MasonSkillContractError(AssertionError):
    """A hand-authored Mason skill violates the Story 19.2 contract."""


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / ".claude" / "skills").is_dir():
            return candidate
    raise MasonSkillContractError("could not locate repo root (pixi.toml + .claude/skills)")


def _parse_skill_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        raise MasonSkillContractError("SKILL.md must start with YAML frontmatter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise MasonSkillContractError("SKILL.md frontmatter not closed")
    data = yaml.safe_load(parts[1])
    if not isinstance(data, dict):
        raise MasonSkillContractError("SKILL.md frontmatter must be a mapping")
    return {str(k): str(v) if v is not None else "" for k, v in data.items()}


def _validate_skill_file(skill_md: Path, spec: dict[str, object]) -> None:
    if not skill_md.is_file():
        raise MasonSkillContractError(f"missing {skill_md.relative_to(_repo_root())}")
    text = skill_md.read_text(encoding="utf-8")
    frontmatter = _parse_skill_frontmatter(text)
    expected_name = str(spec["expected_name"])
    if frontmatter.get("name") != expected_name:
        raise MasonSkillContractError(
            f"{skill_md}: frontmatter name: expected {expected_name!r}, got {frontmatter.get('name')!r}"
        )
    if not frontmatter.get("description", "").strip():
        raise MasonSkillContractError(f"{skill_md}: description: frontmatter must be non-empty")

    body = text.split("---", 2)[2]
    for phrase in spec["required_phrases"]:
        if phrase not in body:
            raise MasonSkillContractError(f"{skill_md}: body must mention {phrase!r}")

    for phrase in spec.get("gate_phrases", ()):
        if phrase not in body:
            raise MasonSkillContractError(f"{skill_md}: body must document pypi-test gate (missing {phrase!r})")

    if CFE_LINK_FRAGMENT not in text:
        raise MasonSkillContractError(f"{skill_md}: must link {CFE_LINK_FRAGMENT} (conda-forge target defers to CFE)")

    gotcha = GOTCHA_HEADING_RE.search(text)
    if gotcha:
        line_no = text[: gotcha.start()].count("\n") + 1
        raise MasonSkillContractError(
            f"{skill_md}:{line_no}: CFE gotcha heading {gotcha.group(0)!r} is forbidden "
            "(recipe knowledge stays in conda-forge-expert)"
        )


@pytest.mark.parametrize("spec", MASON_HAND_AUTHORED_SKILLS, ids=lambda s: str(s["skill_dir"]))
def test_hand_authored_mason_skill_contract(spec: dict[str, object]) -> None:
    root = _repo_root()
    skill_dir = str(spec["skill_dir"])
    skill_md = root / ".claude" / "skills" / skill_dir / "SKILL.md"
    _validate_skill_file(skill_md, spec)


def test_gotcha_heading_detector_is_not_vacuous() -> None:
    root = _repo_root()
    source = root / ".claude" / "skills" / "mason-package" / "SKILL.md"
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "SKILL.md"
        planted = source.read_text(encoding="utf-8") + "\n### G99. Planted gotcha for meta-test\n"
        copy.write_text(planted, encoding="utf-8")
        spec = MASON_HAND_AUTHORED_SKILLS[0]
        with pytest.raises(MasonSkillContractError, match="G99"):
            _validate_skill_file(copy, spec)
