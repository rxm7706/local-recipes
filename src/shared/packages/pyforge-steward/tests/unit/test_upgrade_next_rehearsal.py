"""Story 14.10 — `@next` rehearsal (report-only, fixture-based).

Exercises CAP-6 pixi-bin PATH fallback, CAP-8 single-conflict path, and CAP-7 skf
restore together in the invocation shape documented in
``spec-bmad-suite-lifecycle/release-cadence.md`` § The ``@next`` rehearsal.

No live ``npx bmad-method@next`` call — ``tmp_path`` stands in for the throwaway
worktree.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml

from pyforge.steward.upgrade import (
    TRAP_LOCAL_CUSTOMIZATION,
    apply_bmad_core_upgrade,
    build_preflight_report,
    format_apply,
)

# Verbatim argv shape for Story 46.10 cross-check against release-cadence.md.
# Placeholders stand in for paths resolved at runtime in a live rehearsal.
NEXT_REHEARSAL_ARGV = [
    "upgrade",
    "bmad-core",
    "--target",
    "6.12.1-next.0",
    "--apply",
    "--repo-root",
    "<throwaway-worktree>",
    "--installer",
    "npx bmad-method@next",
    "--installed-package-root",
    "<cached-6.12.0-unpacked>",
    "--package-root",
    "<unpacked-next-tarball>",
    "--catalog-dir",
    "<fixture-or-authored-catalog-dir>",
    "--branch",
    "rehearsal/next-cap6-cap8",
]

_REHEARSAL_TARGET = "6.12.1-next.0"
_SKILL = "bmad-dev-auto"
_SKILL_FILE = "step-02.md"
_SKILL_REL = f".claude/skills/{_SKILL}/{_SKILL_FILE}"

_SKILL_BASE = "ROUTE = old\nMID = x\nTAIL = same\n"
_SKILL_OURS = "ROUTE = old  # kept by repo\nMID = x\nTAIL = same\n"
_SKILL_NEW = "ROUTE = new\nMID = x\nTAIL = same\n"

_SKF_CONFIG_REL = "_bmad/skf/config.yaml"
_SKF_CONFIG_TEXT = (
    "# SKF Module Configuration\nuser_name: Test\nides:\n  - claude-code\nskills_output_folder: .claude/skills\n"
)
_PACKAGED_SOURCE_REL = ".pixi/envs/pyforge-guild/lib/node_modules/bmad-module-skill-forge/src"
_PACKAGED_FILES = {
    "skf-alpha/SKILL.md": "# skf-alpha\n",
    "skf-campaign/SKILL.md": "# skf-campaign\n",
    "module.yaml": "name: skf\n",
}


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _manifest_text() -> str:
    return (
        "installation:\n"
        "  version: 6.12.0\n"
        "modules:\n"
        "  - name: core\n"
        "    version: 6.12.0\n"
        "    source: built-in\n"
        "  - name: bmm\n"
        "    version: 6.12.0\n"
        "    source: built-in\n"
        "  - name: skf\n"
        "    version: 2.1.0\n"
        "    source: custom\n"
    )


def _write_package(root: Path, *, skill_body: str) -> Path:
    skill_dir = root / "src" / "bmm-skills" / _SKILL
    skill_dir.mkdir(parents=True)
    (skill_dir / _SKILL_FILE).write_text(skill_body, encoding="utf-8")
    return root


def _write_rehearsal_repo(root: Path) -> Path:
    (root / "scripts" / "bmad-loop-worktree").parent.mkdir(parents=True)
    (root / "scripts" / "bmad-loop-worktree").write_text("#!/bin/sh\n", encoding="utf-8")

    manifest_dir = root / "_bmad" / "_config"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "manifest.yaml").write_text(_manifest_text(), encoding="utf-8")
    (manifest_dir / "skill-manifest.csv").write_text(f'canonicalId,name\n"{_SKILL}","{_SKILL}"\n', encoding="utf-8")

    for sub in ("bmm", "core", "scripts"):
        (root / "_bmad" / sub).mkdir(parents=True, exist_ok=True)
    (root / "_bmad" / "custom" / "config.toml").parent.mkdir(parents=True, exist_ok=True)
    (root / "_bmad" / "custom" / "config.toml").write_text("team = true\n", encoding="utf-8")
    (root / "_bmad" / "config.toml").write_text(
        '[modules.skf]\nsidecar_path = "{project-root}/_bmad/_memory/forger-sidecar"\n',
        encoding="utf-8",
    )

    packaged = root / _PACKAGED_SOURCE_REL
    for rel, body in _PACKAGED_FILES.items():
        target = packaged / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")

    skills = root / ".claude" / "skills"
    skills.mkdir(parents=True)
    skf = root / "_bmad" / "skf"
    skf.mkdir(parents=True)
    for name in ("skf-alpha", "skf-campaign"):
        shutil.copytree(packaged / name, skf / name)
        shutil.copytree(packaged / name, skills / name)
    (skf / "config.yaml").write_text(_SKF_CONFIG_TEXT, encoding="utf-8")

    skill_dir = root / ".claude" / "skills" / _SKILL
    skill_dir.mkdir(parents=True)
    (skill_dir / _SKILL_FILE).write_text(_SKILL_OURS, encoding="utf-8")

    pixi_bin = root / ".pixi" / "envs" / "pyforge-guild" / "bin"
    pixi_bin.mkdir(parents=True)
    (pixi_bin / "node").write_text("#!/bin/sh\n", encoding="utf-8")
    (pixi_bin / "node").chmod(0o755)

    _git(root, "init", "-q")
    _git(root, "config", "user.email", "fixture@test")
    _git(root, "config", "user.name", "fixture")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "rehearsal fixture")
    return root


def _write_next_catalog(directory: Path, *, own_installer: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{_REHEARSAL_TARGET}.yaml").write_text(
        yaml.safe_dump(
            {
                "version": _REHEARSAL_TARGET,
                "baseline_pair_from": "6.12.0",
                "custom_modules": [
                    {
                        "name": "skf",
                        "own_installer": [str(own_installer), "update"],
                        "config_paths": [_SKF_CONFIG_REL],
                        "packaged_source": _PACKAGED_SOURCE_REL,
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return directory


def _fake_next_installer(path: Path, *, target_pkg: Path) -> Path:
    body = textwrap.dedent(
        f"""\
        #!/usr/bin/env python3
        import pathlib, shutil, sys
        repo = pathlib.Path.cwd()
        assert sys.argv[1:4] == ["install", "--action", "update"], sys.argv
        assert "-y" in sys.argv
        (repo / "_bmad" / "bmm" / "updated.txt").write_text("from-next\\n", encoding="utf-8")
        (repo / "_bmad" / "core" / "updated.txt").write_text("from-next\\n", encoding="utf-8")
        skf = repo / "_bmad" / "skf"
        shutil.rmtree(skf, ignore_errors=True)
        skf.mkdir(parents=True)
        (skf / "config.yaml").write_text(
            "# REGENERATED BY CORE\\n", encoding="utf-8"
        )
        pkg = pathlib.Path({str(target_pkg)!r})
        dest = repo / ".claude" / "skills" / {_SKILL!r}
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy(
            pkg / "src" / "bmm-skills" / {_SKILL!r} / {_SKILL_FILE!r},
            dest / {_SKILL_FILE!r},
        )
        sys.exit(0)
        """
    )
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)
    return path


def _fake_skf_installer(path: Path) -> Path:
    body = textwrap.dedent(
        """\
        #!/usr/bin/env python3
        import pathlib, sys
        repo = pathlib.Path.cwd()
        skf = repo / "_bmad" / "skf"
        skf.mkdir(parents=True, exist_ok=True)
        config = skf / "config.yaml"
        existing = config.read_text(encoding="utf-8") if config.is_file() else ""
        config.write_text(existing + "health_check_repo: example/skf\\n", encoding="utf-8")
        sys.exit(0)
        """
    )
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)
    return path


def _rehearsal_fixture(tmp_path: Path) -> dict[str, Path]:
    repo = _write_rehearsal_repo(tmp_path / "worktree")
    installed_pkg = _write_package(tmp_path / "installed-6.12.0", skill_body=_SKILL_BASE)
    target_pkg = _write_package(tmp_path / "next-unpacked", skill_body=_SKILL_NEW)
    core = _fake_next_installer(tmp_path / "fake-npx-bmad-method-next", target_pkg=target_pkg)
    own = _fake_skf_installer(tmp_path / "fake-skill-forge")
    catalog = _write_next_catalog(tmp_path / "catalog", own_installer=own)
    return {
        "repo": repo,
        "installed_pkg": installed_pkg,
        "target_pkg": target_pkg,
        "core": core,
        "own": own,
        "catalog": catalog,
    }


@pytest.fixture(autouse=True)
def _no_real_home(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "fake-home")


def test_next_rehearsal_cap6_cap8_cap7_report_only(tmp_path, monkeypatch):
    paths = _rehearsal_fixture(tmp_path)
    repo = paths["repo"]
    pixi_bin = repo / ".pixi" / "envs" / "pyforge-guild" / "bin"

    real_which = shutil.which

    def which(name: str, path: str | None = None):
        if name == "node":
            return None
        if name == "bmad-method":
            return str(paths["core"])
        return real_which(name, path=path)

    monkeypatch.setattr(shutil, "which", which)

    preflight = build_preflight_report(
        repo=repo,
        target_version=_REHEARSAL_TARGET,
        catalog_directory=paths["catalog"],
        installed_package_root=paths["installed_pkg"],
    )
    assert TRAP_LOCAL_CUSTOMIZATION in preflight.trap_ids
    assert len(preflight.local_customizations) == 1
    assert preflight.local_customizations[0].path == _SKILL_REL

    report = apply_bmad_core_upgrade(
        repo=repo,
        target_version=_REHEARSAL_TARGET,
        installer_bin=str(paths["core"]),
        catalog_directory=paths["catalog"],
        installed_package_root=paths["installed_pkg"],
        package_root=paths["target_pkg"],
        branch="rehearsal/next-cap6-cap8",
    )

    assert report.installer_exit == 0
    cap6_notes = [n for n in report.notes if "not on PATH" in n and "node" in n]
    assert cap6_notes, report.notes
    assert str(pixi_bin) in cap6_notes[0]

    reapply = report.local_customizations_reapply
    assert reapply is not None
    assert len(reapply.findings) == 1
    finding = reapply.findings[0]
    assert finding.path == _SKILL_REL
    assert finding.action == "conflict_needs_manual_merge"
    conflict_path = repo / f"{_SKILL_REL}.customization-conflict"
    assert conflict_path.is_file()
    assert finding.conflict_path == f"{_SKILL_REL}.customization-conflict"
    assert report.local_customizations_ok is False

    skf = report.custom_modules[0]
    assert skf.name == "skf"
    assert skf.config_paths[0].status == "restored"
    config_text = (repo / _SKF_CONFIG_REL).read_text(encoding="utf-8")
    assert config_text.startswith(_SKF_CONFIG_TEXT)
    assert "health_check_repo: example/skf" in config_text
    assert skf.own_installer_exit == 0
    assert skf.ok is True
    assert report.custom_modules_ok is True

    text = format_apply(report, as_json=False)
    assert "## CAP-8 local customizations re-applied" in text
    assert "[conflict_needs_manual_merge]" in text

    argv_doc = json.dumps(NEXT_REHEARSAL_ARGV)
    assert "npx bmad-method@next" in argv_doc
    assert _REHEARSAL_TARGET in argv_doc
