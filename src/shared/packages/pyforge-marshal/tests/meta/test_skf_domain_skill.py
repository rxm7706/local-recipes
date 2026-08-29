"""Story 27.1: SKF domain skill compiled from the marshal station package."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

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
        diff = subprocess.check_output(
            ["git", "diff", "origin/main", "--", name],
            cwd=root,
            text=True,
        )
        assert not diff.strip(), f"{name} changed vs origin/main"


def test_conda_forge_expert_not_replaced():
    root = _repo_root()
    cfe = root / ".claude" / "skills" / "conda-forge-expert"
    assert (cfe / "SKILL.md").is_file()
    assert not (cfe / "metadata.json").exists()
    assert not (cfe / "active").exists()
    skill = (cfe / "SKILL.md").read_text(encoding="utf-8")
    assert "conda-forge" in skill.lower()
    diff = subprocess.check_output(
        ["git", "diff", "origin/main", "--", ".claude/skills/conda-forge-expert"],
        cwd=root,
        text=True,
    )
    assert not diff.strip(), "conda-forge-expert changed vs origin/main"


def test_does_not_add_loop_supervisor_ingest():
    root = _repo_root()
    named = subprocess.check_output(
        ["git", "diff", "--name-only", "origin/main"],
        cwd=root,
        text=True,
    )
    changed = [line for line in named.splitlines() if line.strip()]
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
