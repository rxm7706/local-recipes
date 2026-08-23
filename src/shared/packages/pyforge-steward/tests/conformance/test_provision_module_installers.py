"""Story 15.3 — conda-installer backends for tea / cis / utility-skills /
manticore.

Each addition drives the package's own `*-install` entry point (AD-1),
records a `_bmad/config.yaml` manifest section, refuses skill-name
collisions before first install, and stays reproducible against a
fresh-clone fixture (share data staged under `.pixi/envs/local-recipes`).
WDS is covered as an explicit skip citation, never as a registered module.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import pytest
import yaml

from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main
from pyforge.steward.provision import (
    CondaInstallBackend,
    ProvisionDuty,
    _SUPPORTED_MODULES,
    _installer_skill_names,
    provision_module,
)


def _full_namespace(**overrides):
    base = {
        "module": None,
        "env": None,
        "runner": None,
        "list": False,
        "verify": False,
        "list_modules": False,
        "json": False,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def _stage_share_skills(
    root: Path,
    *,
    package: str,
    source_dir: str,
    skill_names: tuple[str, ...],
) -> Path:
    """Stage a minimal share/<package>/<source_dir>/<skill>/ tree under the
    fresh-clone pixi-env convention Story 6.1 already uses for bmb."""
    share = root / ".pixi/envs/local-recipes/share" / package / source_dir
    for name in skill_names:
        (share / name).mkdir(parents=True)
        (share / name / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
    return share


def _fake_installer_run(cmd, **kwargs):  # noqa: ARG001
    """Stand in for `bmad-*-install <dest>`: copy staged share skill dirs
    into the destination the real installer would write."""
    installer = Path(cmd[0]).name if cmd else ""
    dest = Path(cmd[1]) if len(cmd) > 1 else Path(".claude/skills")
    dest.mkdir(parents=True, exist_ok=True)

    # Map installer → (package, source dirs or explicit names) from the
    # live `_SUPPORTED_MODULES` registry so the fake stays in sync.
    name = next(
        (
            key
            for key, backend in _SUPPORTED_MODULES.items()
            if isinstance(backend, CondaInstallBackend) and backend.installer == installer
        ),
        None,
    )
    assert name is not None, f"unexpected installer {installer!r}"
    backend = _SUPPORTED_MODULES[name]
    assert isinstance(backend, CondaInstallBackend)

    cwd = Path(kwargs.get("cwd") or ".")
    prefix = Path((kwargs.get("env") or {}).get("CONDA_PREFIX", cwd / ".pixi/envs/local-recipes"))
    share_root = prefix / "share" / backend.share_package
    skill_names = _installer_skill_names(backend, share_root=share_root)
    installed = []
    for skill in skill_names:
        # Prefer the first source dir that contains the skill (tea has two).
        src = None
        if backend.skill_names:
            src = share_root / "skills" / skill
            if not src.is_dir():
                # cis stages under skills/ in fixtures even though the real
                # package uses an allowlist — fall back to any source dir.
                for source in ("skills", *backend.skill_source_dirs):
                    candidate = share_root / source / skill
                    if candidate.is_dir():
                        src = candidate
                        break
        else:
            for source in backend.skill_source_dirs:
                candidate = share_root / source / skill
                if candidate.is_dir():
                    src = candidate
                    break
        assert src is not None and src.is_dir(), f"missing staged skill {skill}"
        target = dest / skill
        if target.exists():
            # Real installers rmtree+copytree; we recreate minimally.
            for child in target.iterdir():
                child.unlink()
            target.rmdir()
        target.mkdir(parents=True)
        (target / "SKILL.md").write_text((src / "SKILL.md").read_text(encoding="utf-8"), encoding="utf-8")
        installed.append(skill)

    stdout = f"Installed {len(installed)} skill(s) to '{dest}':\n" + "".join(
        f"  - {s}\n" for s in installed
    )
    return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")


@pytest.fixture
def tea_fixture(tmp_path):
    _stage_share_skills(
        tmp_path,
        package="bmad-method-test-architecture-enterprise",
        source_dir="agents",
        skill_names=("bmad-tea",),
    )
    _stage_share_skills(
        tmp_path,
        package="bmad-method-test-architecture-enterprise",
        source_dir="workflows",
        skill_names=("testarch",),
    )
    return tmp_path


@pytest.fixture
def cis_fixture(tmp_path):
    backend = _SUPPORTED_MODULES["cis"]
    assert isinstance(backend, CondaInstallBackend)
    _stage_share_skills(
        tmp_path,
        package=backend.share_package,
        source_dir="skills",
        skill_names=backend.skill_names,
    )
    return tmp_path


# ── Cross-module skill-name collision (registry integrity) ───────────────


def test_supported_installer_modules_have_disjoint_skill_names():
    """Skill-name-collision-checked at the registry: no two conda-install
    backends claim the same skill name."""
    claimed: dict[str, str] = {}
    for name, backend in _SUPPORTED_MODULES.items():
        if not isinstance(backend, CondaInstallBackend):
            continue
        names = backend.skill_names
        if not names:
            # Discovery backends (tea/utility/manticore) — use the live share
            # tree when the local-recipes env is present; otherwise skip the
            # dynamic half (explicit cis allowlist still checked above).
            continue
        for skill in names:
            assert skill not in claimed, (
                f"skill {skill!r} claimed by both {claimed[skill]!r} and {name!r}"
            )
            claimed[skill] = name


def test_live_share_skill_names_are_disjoint_across_installer_modules():
    """When the pixi local-recipes env is present, discovered skill names
    across tea/cis/utility-skills/manticore must not collide."""
    root = Path(__file__).resolve()
    repo = None
    for ancestor in root.parents:
        if (ancestor / "scripts/bmad-loop-worktree").is_file():
            repo = ancestor
            break
    assert repo is not None
    share = repo / ".pixi/envs/local-recipes/share"
    if not share.is_dir():
        pytest.skip("local-recipes pixi env share data not present")

    claimed: dict[str, str] = {}
    for name, backend in _SUPPORTED_MODULES.items():
        if not isinstance(backend, CondaInstallBackend):
            continue
        share_root = share / backend.share_package
        if not share_root.is_dir():
            pytest.skip(f"share package {backend.share_package} missing")
        for skill in _installer_skill_names(backend, share_root=share_root):
            assert skill not in claimed, (
                f"skill {skill!r} claimed by both {claimed[skill]!r} and {name!r}"
            )
            claimed[skill] = name
    assert claimed  # sanity: at least one skill discovered


# ── provision_module (installer backends) ────────────────────────────────


def test_provision_tea_via_installer_records_manifest_and_skills(tea_fixture, monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_installer_run)

    result = provision_module("tea", cwd=tea_fixture)

    assert result["installer"] == "bmad-tea-install"
    assert set(result["skills_installed"]) == {"bmad-tea", "testarch"}
    assert (tea_fixture / ".claude/skills/bmad-tea").is_dir()
    assert (tea_fixture / ".claude/skills/testarch").is_dir()
    config = yaml.safe_load((tea_fixture / "_bmad/config.yaml").read_text(encoding="utf-8"))
    assert "tea" in config
    assert config["tea"]["installer"] == "bmad-tea-install"
    assert config["tea"]["provisioned_by"] == "steward"


def test_provision_installer_preserves_sibling_manifest_keys(tea_fixture, monkeypatch):
    """Manifest merge must not drop other module keys already in config.yaml."""
    bmad = tea_fixture / "_bmad"
    bmad.mkdir(parents=True)
    (bmad / "config.yaml").write_text(
        "bmb:\n  output_folder: skills\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(subprocess, "run", _fake_installer_run)

    provision_module("tea", cwd=tea_fixture)

    config = yaml.safe_load((bmad / "config.yaml").read_text(encoding="utf-8"))
    assert "bmb" in config
    assert config["bmb"]["output_folder"] == "skills"
    assert "tea" in config


def test_provision_installer_refuses_non_mapping_config(tea_fixture, monkeypatch):
    bmad = tea_fixture / "_bmad"
    bmad.mkdir(parents=True)
    (bmad / "config.yaml").write_text("- not-a-mapping\n", encoding="utf-8")
    monkeypatch.setattr(subprocess, "run", _fake_installer_run)

    with pytest.raises(RuntimeError, match="must be a mapping"):
        provision_module("tea", cwd=tea_fixture)


def test_provision_prefers_local_share_over_ambient_conda_prefix(tea_fixture, monkeypatch):
    """Fresh-clone fixture share must win over a lean ambient CONDA_PREFIX."""
    lean = tea_fixture / "lean-prefix"
    lean.mkdir()
    monkeypatch.setenv("CONDA_PREFIX", str(lean))
    seen: list[str] = []

    def _tracking_run(cmd, **kwargs):
        seen.append((kwargs.get("env") or {}).get("CONDA_PREFIX", ""))
        return _fake_installer_run(cmd, **kwargs)

    monkeypatch.setattr(subprocess, "run", _tracking_run)

    result = provision_module("tea", cwd=tea_fixture)

    assert result["installer"] == "bmad-tea-install"
    assert seen
    assert Path(seen[0]) == tea_fixture / ".pixi/envs/local-recipes"


def test_provision_installer_exit_0_but_skills_missing_raises(tea_fixture, monkeypatch):
    def _noop_installer(cmd, **kwargs):  # noqa: ARG001
        return subprocess.CompletedProcess(cmd, 0, stdout="Installed 0\n", stderr="")

    monkeypatch.setattr(subprocess, "run", _noop_installer)

    with pytest.raises(RuntimeError, match="skills still missing"):
        provision_module("tea", cwd=tea_fixture)

    assert not (tea_fixture / "_bmad/config.yaml").exists()


def test_discovery_backends_skill_names_are_disjoint_in_fixture(tmp_path):
    """Always-on disjointness for discovery backends (no live pixi env)."""
    tea_pkg = "bmad-method-test-architecture-enterprise"
    util_pkg = "bmad-utility-skills"
    _stage_share_skills(
        tmp_path, package=tea_pkg, source_dir="agents", skill_names=("bmad-tea",)
    )
    _stage_share_skills(
        tmp_path, package=tea_pkg, source_dir="workflows", skill_names=("testarch",)
    )
    _stage_share_skills(
        tmp_path,
        package=util_pkg,
        source_dir="skills",
        skill_names=("bmad-os-gh-triage",),
    )
    share = tmp_path / ".pixi/envs/local-recipes/share"
    claimed: dict[str, str] = {}
    for name, backend in _SUPPORTED_MODULES.items():
        if not isinstance(backend, CondaInstallBackend):
            continue
        share_root = share / backend.share_package
        if not share_root.is_dir():
            continue
        for skill in _installer_skill_names(backend, share_root=share_root):
            assert skill not in claimed, (
                f"skill {skill!r} claimed by both {claimed[skill]!r} and {name!r}"
            )
            claimed[skill] = name
    assert set(claimed) >= {"bmad-tea", "testarch", "bmad-os-gh-triage"}


def test_provision_cis_via_installer_records_manifest(cis_fixture, monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_installer_run)

    result = provision_module("cis", cwd=cis_fixture)

    assert result["installer"] == "bmad-cis-install"
    assert len(result["skills_installed"]) == 10
    config = yaml.safe_load((cis_fixture / "_bmad/config.yaml").read_text(encoding="utf-8"))
    assert config["cis"]["installer"] == "bmad-cis-install"


@pytest.mark.parametrize(
    ("module_name", "package", "source_dir", "skills", "installer"),
    [
        (
            "utility-skills",
            "bmad-utility-skills",
            "skills",
            ("bmad-os-gh-triage", "bmad-os-review-pr"),
            "bmad-utility-skills-install",
        ),
        (
            "manticore",
            "bmad-manticore",
            "skills",
            ("mc-agent", "mc-setup"),
            "bmad-manticore-install",
        ),
    ],
)
def test_provision_utility_and_manticore_via_installer(
    tmp_path, monkeypatch, module_name, package, source_dir, skills, installer
):
    _stage_share_skills(tmp_path, package=package, source_dir=source_dir, skill_names=skills)
    monkeypatch.setattr(subprocess, "run", _fake_installer_run)

    result = provision_module(module_name, cwd=tmp_path)

    assert result["installer"] == installer
    assert set(result["skills_installed"]) == set(skills)
    config = yaml.safe_load((tmp_path / "_bmad/config.yaml").read_text(encoding="utf-8"))
    assert module_name in config


def test_provision_installer_refuses_skill_name_collision(tea_fixture, monkeypatch):
    """Foreign skill already present + module not yet manifest-recorded →
    RuntimeError before any subprocess."""
    collision = tea_fixture / ".claude/skills/bmad-tea"
    collision.mkdir(parents=True)
    (collision / "SKILL.md").write_text("# foreign\n", encoding="utf-8")
    calls: list[object] = []

    def _tracking_run(cmd, **kwargs):
        calls.append(cmd)
        return _fake_installer_run(cmd, **kwargs)

    monkeypatch.setattr(subprocess, "run", _tracking_run)

    with pytest.raises(RuntimeError, match="skill-name collision"):
        provision_module("tea", cwd=tea_fixture)

    assert calls == []


def test_provision_installer_idempotent_reprovision_allows_overwrite(tea_fixture, monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_installer_run)
    provision_module("tea", cwd=tea_fixture)
    # Second run: skills exist but module is manifest-recorded → allowed.
    second = provision_module("tea", cwd=tea_fixture)
    assert second["installer"] == "bmad-tea-install"


def test_provision_installer_missing_share_raises_before_subprocess(tmp_path, monkeypatch):
    calls: list[object] = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kwargs: calls.append(cmd))  # noqa: ARG005

    with pytest.raises(FileNotFoundError, match="share package is missing"):
        provision_module("tea", cwd=tmp_path)

    assert calls == []


def test_provision_wds_is_skip_decided_with_upstream_citation(tmp_path, monkeypatch):
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)
    calls: list[object] = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kwargs: calls.append(cmd))  # noqa: ARG005

    result = ProvisionDuty().run(_full_namespace(module="wds"))

    assert result.ok is False
    assert "skip" in result.summary.lower() or "deprecated" in result.summary.lower()
    assert "bmad-ux" in result.summary or "install-matrix" in result.summary
    assert calls == []
    assert "wds" not in _SUPPORTED_MODULES


def test_provision_module_api_raises_skip_citation_for_wds(tmp_path):
    with pytest.raises(FileNotFoundError, match="deprecated"):
        provision_module("wds", cwd=tmp_path)


def test_provision_tea_via_cli_round_trips(tea_fixture, monkeypatch, capsys):
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tea_fixture)
    monkeypatch.setattr(subprocess, "run", _fake_installer_run)

    rc = main(["provision", "--module", "tea"])

    assert rc == EXIT_OK
    out = capsys.readouterr().out
    assert "tea" in out
    assert "bmad-tea-install" in out


def test_provision_tea_json_emits_installer_steps(tea_fixture, monkeypatch):
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tea_fixture)
    monkeypatch.setattr(subprocess, "run", _fake_installer_run)

    result = ProvisionDuty().run(_full_namespace(module="tea", json=True))

    assert result.ok is True
    payload = json.loads(result.summary)
    assert payload["installer"] == "bmad-tea-install"
    assert "bmad-tea" in payload["skills_installed"]


def test_provision_installer_failure_names_nothing_written(tea_fixture, monkeypatch):
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tea_fixture)

    def _boom(cmd, **kwargs):  # noqa: ARG001
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr="CONDA_PREFIX is not set")

    monkeypatch.setattr(subprocess, "run", _boom)

    result = ProvisionDuty().run(_full_namespace(module="tea"))

    assert result.ok is False
    assert "CONDA_PREFIX is not set" in result.summary
    assert "nothing was written to _bmad/config.yaml" in result.summary
    assert not (tea_fixture / "_bmad/config.yaml").exists()


def test_provision_does_not_register_method_loop_skf_labs_dashboards_template():
    """Story 15.3 boundaries: never absorb core/loop/skf/labs/dashboards/
    template via `--module`."""
    forbidden = {
        "method",
        "bmad-method",
        "loop",
        "bmad-loop",
        "skf",
        "skill-forge",
        "labs",
        "labs-skills",
        "dashboard",
        "dashboards",
        "template",
        "module-template",
        "wds",
    }
    assert forbidden.isdisjoint(_SUPPORTED_MODULES)
