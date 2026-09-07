"""Story 27.1: SKF domain skill compiled from the marshal station package."""

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

STATION = "marshal"
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


def test_compiled_skill_exists_with_provenance():
    root = _repo_root()
    assert (root / "src" / "shared" / "packages" / f"pyforge-{STATION}").is_dir()
    pkg = _skill_package(root)
    assert pkg.is_dir()
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


def test_compiled_skill_is_agentskills_compliant():
    root = _repo_root()
    pkg = _skill_package(root)
    skill_md = pkg / "SKILL.md"

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
    assert "marshal status" in body
    assert "marshal homes" in body
    assert "marshal check" in body


def test_context_files_not_hand_edited():
    root = _repo_root()
    for name in ("CLAUDE.md", "AGENTS.md"):
        # skf-export-skill (3d745c2c31, 2026-08-26) made the SKF:BEGIN/END managed
        # section the legitimate, tool-generated content of these files — a flat
        # ban on the marker is stale. The invariant is "not hand-edited", checked
        # via the exporter's own well-formedness gate, not marker absence.
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
        # A second managed marker, `bmad:context`, is the sanctioned surface for
        # content moved by `bmad-project-context adopt`/`audit` (Story 30.2,
        # 2026-09-06, D1 -- the project-context surface migration off the retired
        # per-station rulebooks). A well-formed bmad:context block is legitimate,
        # tool-mediated content the same way an SKF managed section is; the
        # zero-diff assertion this test used to carry unconditionally is retired
        # in favor of checking both markers stay well-formed, matching the
        # docstring's own stated invariant ("not hand-edited", not "never
        # touched"). CLAUDE.md carries no bmad:context marker (only AGENTS.md
        # does) and has no other managed-block mechanism, so this second check
        # applies to AGENTS.md only -- checking it against CLAUDE.md would be a
        # vacuous 0==0 pass, not a real assertion.
        if name == "AGENTS.md":
            text = (root / name).read_text(encoding="utf-8")
            opens = text.count("<!-- bmad:context -->")
            closes = text.count("<!-- /bmad:context -->")
            assert opens == closes, f"{name}: unbalanced bmad:context markers"
            assert opens <= 1, f"{name}: more than one bmad:context block"


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
        "conda-forge-expert changed vs origin/main outside a sanctioned `retro:` "
        f"commit that moves its CHANGELOG: {bad}"
    )


def test_does_not_add_loop_supervisor_ingest():
    root = _repo_root()
    changed = changed_paths_since(root)
    ingest_markers = ("supervisor ingest", "bmad-loop ingest", "loop-home list")
    offenders: list[str] = []
    for rel in changed:
        if rel.endswith(".py") and "supervisor" in rel and "src/platform" in rel:
            offenders.append(rel)
        path = root / rel
        if not path.is_file() or path.suffix not in {".py", ".md"}:
            continue
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        prohibits = (
            "do not implement" in lowered
            or "do not wire" in lowered
            or "never" in lowered
            or "no bmad-loop ingest" in lowered
            or "no supervisor ingest" in lowered
        )
        if any(marker in text for marker in ingest_markers) and not prohibits:
            if "test_" in rel:
                continue
            offenders.append(rel)
    assert not offenders, f"bmad-loop ingest wire appeared: {offenders}"


def test_story_does_not_add_pyforge_under_src_platform():
    # NOTE (retro-2026-09-04 action item 11 follow-up): unlike doctor's copy of
    # this guard (test_portal_fleet_pulse.py), this one flags any `pyforge`
    # import currently present in a changed src/platform file, not only ones
    # ADDED by this diff -- bringing it up to doctor's ADDED-only correctness
    # is a policy change, deliberately left as a separate, still-open finding
    # rather than folded into this mechanism-only consolidation.
    root = _repo_root()
    changed = changed_paths_since(root, pathspec="src/platform")
    offenders = pyforge_import_offenders(changed, root)
    assert not offenders, f"src/platform pyforge imports in this diff: {changed} {offenders}"
