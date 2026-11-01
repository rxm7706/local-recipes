"""Story 19.1: SKF domain skill compiled from the mason station package.

Story 19.6 (spec-pyforge-mason CAP-29) adds grammar coverage: every verb
``build_parser()`` registers appears in the station ``SKILL.md``. A miss is
fixed by regenerating the skill with ``skf-update-skill`` from
``.claude/skills/pyforge-mason/skill-brief.yaml``, never by hand (canopy:AD-17).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from pyforge.testing_kit import (
    cfe_surface,
    changed_paths_since,
    pyforge_import_offenders,
    unsanctioned_commits,
)

from pyforge.mason.cli import build_parser

STATION = "mason"
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


def test_skf_compile_path_is_present():
    root = _repo_root()
    required = [
        root / "_bmad" / "skf" / "skf-create-skill" / "SKILL.md",
        root / ".claude" / "skills" / "skf-create-skill" / "SKILL.md",
        root / ".claude" / "skills" / "skf-export-skill" / "SKILL.md",
        root / ".claude" / "skills" / "shared" / "scripts" / "skf-extract-public-api.py",
        root / ".claude" / "skills" / "shared" / "scripts" / "skf-validate-frontmatter.py",
        root / ".claude" / "skills" / "shared" / "scripts" / "skf-validate-output.py",
    ]
    missing = [str(p.relative_to(root)) for p in required if not p.is_file()]
    assert not missing, f"SKF compile path removed: {missing}"


def test_compiled_skill_is_agentskills_compliant_with_provenance():
    root = _repo_root()
    pkg = _skill_package(root)
    skill_md = pkg / "SKILL.md"
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
        line = int(entry["source_line"])
        path = root / src
        assert path.is_file(), src
        assert line >= 1
        text = path.read_text(encoding="utf-8").splitlines()
        assert line <= len(text), f"{src}:{line} out of range"

    brief = root / ".claude" / "skills" / SKILL_NAME / "skill-brief.yaml"
    assert brief.is_file()
    assert f"src/shared/packages/pyforge-{STATION}" in brief.read_text(encoding="utf-8")

    fm = subprocess.run(
        [
            sys.executable,
            str(root / ".claude" / "skills" / "shared" / "scripts" / "skf-validate-frontmatter.py"),
            str(skill_md),
            "--skill-dir-name",
            SKILL_NAME,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert fm.returncode == 0, fm.stdout + fm.stderr
    fm_payload = json.loads(fm.stdout)
    assert fm_payload["status"] in {"pass", "warn"}
    assert fm_payload["summary"]["high"] == 0

    out = subprocess.run(
        [
            sys.executable,
            str(root / ".claude" / "skills" / "shared" / "scripts" / "skf-validate-output.py"),
            str(pkg),
            "--generated-by",
            "create-skill",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    payload = json.loads(out.stdout)
    high = payload["summary"]["by_severity"]["high"]
    assert high == 0, payload
    body = skill_md.read_text(encoding="utf-8")
    assert "pyforge mason recipe" in body
    assert "pyforge mason package" in body
    assert "pyforge mason environment" in body
    assert "pyforge mason doctor" in body
    assert "/stations/mason/mcp" in body
    assert "conda-forge-expert" in body


VERB_NOUNS = ("recipe", "package", "environment")


def _subparsers(parser: argparse.ArgumentParser) -> argparse._SubParsersAction | None:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    return None


def registered_verbs(parser: argparse.ArgumentParser) -> list[tuple[str, str]]:
    """Every ``(noun, verb)`` pair the parser registers, in registration order."""
    nouns = _subparsers(parser)
    assert nouns is not None, "build_parser() registers no nouns"
    pairs: list[tuple[str, str]] = []
    for noun, noun_parser in nouns.choices.items():
        verbs = _subparsers(noun_parser)
        if verbs is not None:
            pairs.extend((noun, verb) for verb in verbs.choices)
    return pairs


def verbs_missing_from(skill_text: str, pairs: list[tuple[str, str]]) -> list[str]:
    return [f"{noun} {verb}" for noun, verb in pairs if f"{noun} {verb}" not in skill_text]


def test_station_skill_documents_every_registered_verb():
    """Story 19.6 (CAP-29): the station skill documents the whole `mason` grammar."""
    pairs = registered_verbs(build_parser())
    assert {noun for noun, _ in pairs} == set(VERB_NOUNS), pairs
    body = (_skill_package(_repo_root()) / "SKILL.md").read_text(encoding="utf-8")
    missing = verbs_missing_from(body, pairs)
    assert not missing, (
        f"{SKILL_NAME} SKILL.md does not document {missing}; regenerate it with skf-update-skill from "
        f".claude/skills/{SKILL_NAME}/skill-brief.yaml (never hand-edit the compiled skill)"
    )


def test_grammar_coverage_check_is_not_vacuous():
    parser = build_parser()
    nouns = _subparsers(parser)
    assert nouns is not None
    recipe_verbs = _subparsers(nouns.choices["recipe"])
    assert recipe_verbs is not None
    recipe_verbs.add_parser("planted-verb")
    body = (_skill_package(_repo_root()) / "SKILL.md").read_text(encoding="utf-8")
    assert verbs_missing_from(body, registered_verbs(parser)) == ["recipe planted-verb"]


def test_context_files_not_hand_edited():
    """AGENTS.md SKF block is written only by skf-export-skill."""
    root = _repo_root()
    for name in ("CLAUDE.md", "AGENTS.md"):
        result = json.loads(
            subprocess.check_output(
                [
                    sys.executable,
                    str(root / ".claude" / "skills" / "shared" / "scripts" / "skf-rebuild-managed-sections.py"),
                    str(root / name),
                    "check",
                ],
                text=True,
            )
        )
        if result["has_managed_section"]:
            assert result["markers_valid"], f"{name}: malformed SKF managed section"


def test_cfe_guard_reads_the_one_cfe_surface_owner():
    """Story 83.24: mason guard uses ``pyforge.testing_kit.cfe_surface``."""
    source = Path(__file__).read_text(encoding="utf-8")
    assert "cfe_surface.CFE_GIT_PATHSPECS" in source
    assert "cfe_surface.CFE_CHANGELOG_PATH" in source


def test_conda_forge_expert_not_replaced():
    root = _repo_root()
    cfe = root / ".claude" / "skills" / "conda-forge-expert"
    assert (cfe / "SKILL.md").is_file()
    assert not (cfe / "metadata.json").exists()
    assert not (cfe / "active").exists()
    skill = (cfe / "SKILL.md").read_text(encoding="utf-8")
    assert "conda-forge" in skill.lower()
    bad = unsanctioned_commits(
        root,
        pathspec=cfe_surface.CFE_GIT_PATHSPECS,
        changelog_path=cfe_surface.CFE_CHANGELOG_PATH,
    )
    assert not bad, (
        "conda-forge-expert must not be replaced in this story -- only a sanctioned "
        f"`retro:` commit that moves its CHANGELOG may touch it: {bad}"
    )


def test_story_does_not_add_pyforge_under_src_platform():
    root = _repo_root()
    changed = changed_paths_since(
        root,
        base="origin/main...HEAD",
        require="origin/main",
        pathspec="src/platform",
        include_untracked=True,
    )
    offenders = pyforge_import_offenders(changed, root)
    assert not offenders, f"src/platform pyforge imports in this diff: {changed} {offenders}"
