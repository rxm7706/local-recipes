"""FR-37 / canopy AD-17: SKF domain skill compiled from a station package."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

PROOF_STATION = "scribe"
SKILL_NAME = f"pyforge-{PROOF_STATION}"


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
    """Removing SKF create-skill / helpers must fail this suite (AD-17)."""
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


def test_proof_station_had_no_skill_is_scribe_not_atlas():
    """FR-37: demonstrate on a station that has no skill today — not atlas's existing one."""
    root = _repo_root()
    assert (_repo_root() / "src" / "shared" / "packages" / f"pyforge-{PROOF_STATION}").is_dir()
    assert _skill_package(root).is_dir()
    atlas_legacy = root / ".claude" / "skills" / "cf-atlas-legacy"
    assert atlas_legacy.is_dir()
    assert SKILL_NAME != "cf-atlas-legacy"
    assert not (root / ".claude" / "skills" / "pyforge-atlas" / "SKILL.md").exists()


def test_compiled_skill_is_agentskills_compliant_with_provenance():
    root = _repo_root()
    pkg = _skill_package(root)
    skill_md = pkg / "SKILL.md"
    provenance = json.loads((pkg / "provenance-map.json").read_text(encoding="utf-8"))
    meta = json.loads((pkg / "metadata.json").read_text(encoding="utf-8"))

    assert meta["generated_by"] == "create-skill"
    assert meta["name"] == SKILL_NAME
    assert meta["source_repo"].endswith(f"pyforge-{PROOF_STATION}")
    assert provenance["source_commit"]
    assert provenance["entries"], "provenance-map.json must pin at least one export"
    for entry in provenance["entries"]:
        src = entry["source_file"]
        assert f"pyforge-{PROOF_STATION}" in src
        line = int(entry["source_line"])
        path = root / src
        assert path.is_file(), src
        assert line >= 1
        text = path.read_text(encoding="utf-8").splitlines()
        assert line <= len(text), f"{src}:{line} out of range"

    brief = root / ".claude" / "skills" / SKILL_NAME / "skill-brief.yaml"
    assert brief.is_file()
    assert f"src/shared/packages/pyforge-{PROOF_STATION}" in brief.read_text(encoding="utf-8")

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
    assert "scribe capture" in body
    assert "scribe graph compile" in body
    assert "scribe recall" in body


def test_context_files_not_hand_edited():
    """skf-export-skill is the only allowed writer; this story skipped export."""
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


def test_conda_forge_expert_not_replaced():
    root = _repo_root()
    cfe = root / ".claude" / "skills" / "conda-forge-expert"
    assert (cfe / "SKILL.md").is_file()
    assert not (cfe / "metadata.json").exists()
    # Not an SKF version-nested station skill.
    assert not (cfe / "active").exists()
    skill = (cfe / "SKILL.md").read_text(encoding="utf-8")
    assert "conda-forge" in skill.lower()


def test_story_does_not_add_pyforge_under_src_platform():
    """Host import boundary: this story must not write pyforge.* into src/platform/.

    Pre-existing ingest modules on main may already import pyforge; they are
    out of this write-set. Any platform path in *this* diff is scanned.
    """
    root = _repo_root()
    named = subprocess.check_output(
        ["git", "diff", "--name-only", "origin/main", "--", "src/platform"],
        cwd=root,
        text=True,
    )
    changed = [line for line in named.splitlines() if line.strip()]
    offenders: list[str] = []
    for rel in changed:
        path = root / rel
        if path.suffix != ".py" or not path.is_file():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".")[0]]
            if "pyforge" in names:
                offenders.append(f"{rel}:{node.lineno}")
    assert not offenders, f"src/platform pyforge imports in this diff: {changed} {offenders}"
