"""Story 33.1: SKF domain skill compiled from the steward station package."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from pyforge.testing_kit import (
    changed_paths_since,
    pyforge_import_offenders,
    unsanctioned_commits,
)

STATION = "steward"
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
    assert "steward keys" in body
    assert "steward provision" in body
    assert "pyforge steward" in body


def test_context_files_not_hand_edited():
    """Wave A prefers skip export; CLAUDE.md/AGENTS.md must not be hand-edited.

    Matches the sibling `test_skf_domain_skills.py`'s already-loosened form: the
    SKF managed-section well-formedness check is the real invariant (a flat
    zero-diff-vs-origin/main ban predates the SKF-export shift and also blocks
    a legitimate `bmad-project-context adopt`/`audit` content migration, e.g.
    Story 30.2, 2026-09-06).
    """
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


_CFE_SURFACE = ".claude/skills/conda-forge-expert"
_CFE_CHANGELOG = f"{_CFE_SURFACE}/CHANGELOG.md"


def test_conda_forge_expert_not_replaced():
    root = _repo_root()
    cfe = root / ".claude" / "skills" / "conda-forge-expert"
    assert (cfe / "SKILL.md").is_file()
    assert not (cfe / "metadata.json").exists()
    assert not (cfe / "active").exists()
    skill = (cfe / "SKILL.md").read_text(encoding="utf-8")
    assert "conda-forge" in skill.lower()
    # Sanctioned Rule-2 retro -- subject starts `retro:` AND the CFE CHANGELOG
    # moves in the same commit, the fleet rule
    # `scripts/mason_cfe_surface_check.py` enforces for mason. A station story
    # never touches the surface; a fleet hygiene branch may carry the one
    # sanctioned retro (2026-09-04, PR #1043).
    bad = unsanctioned_commits(root, pathspec=_CFE_SURFACE, changelog_path=_CFE_CHANGELOG)
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


def test_wave_b_portal_slice_is_owned_by_33_2():
    """33.1 must not own the portal slice; 33.2's suite gates django-steward."""
    root = _repo_root()
    views = root / "src/shared/packages/django-steward/src/django_steward_portal/views.py"
    assert views.is_file()
    text = views.read_text(encoding="utf-8")
    assert "PortalClient" in text
    assert "provision_list" in text
