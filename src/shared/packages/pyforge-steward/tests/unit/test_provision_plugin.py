"""Story 46.5 — the plugin-path install class's first real wiring:
`steward provision --plugin labs --skill <name>` copies exactly ONE named
skill at a time from `bmad-labs-skills`'s own pinned conda share tree into
`.claude/skills/<name>`, refuses any name outside the operator's fixed
2026-09-06 consent list of four (`mcp-builder`, `slides-generator`,
`multi-repo-git-ops`, `release-please`), and accumulates every installed
skill into a `[modules.labs]` roster in `_bmad/custom/config.toml` --
never wiping a previously-installed sibling skill.

Mirrors `test_provision_module_installers.py`'s own fixture-staging
conventions (a fresh-clone `.pixi/envs/pyforge-guild/share/<package>/...`
tree), but the mechanism under test is a plain `shutil` copy
(`_copy_setup_skill_dirs`, reused verbatim) rather than a subprocess
installer -- there is nothing to monkeypatch `subprocess.run` for.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest
import tomllib
from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main
from pyforge.steward.provision import (
    _LABS_CONSENT_SKILLS,
    _SUPPORTED_PLUGINS,
    ProvisionDuty,
    provision_plugin_skill,
)

LABS_PACKAGE = "bmad-labs-skills"
NOT_CONSENTED_SKILL = "software-research"  # a real labs skill, not on the consent list


def _full_namespace(**overrides):
    base = {
        "module": None,
        "plugin": None,
        "skill": None,
        "prove_class_path": False,
        "env": None,
        "runner": None,
        "list": False,
        "verify": False,
        "list_modules": False,
        "json": False,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def _stage_labs_share(root: Path, skill_names: tuple[str, ...]) -> Path:
    """Stage `.pixi/envs/pyforge-guild/share/bmad-labs-skills/skills/<name>/`
    for each of `skill_names`, mirroring
    `test_provision_module_installers.py::_stage_share_skills`'s own
    fresh-clone convention."""
    share = root / ".pixi/envs/pyforge-guild/share" / LABS_PACKAGE / "skills"
    for name in skill_names:
        (share / name).mkdir(parents=True)
        (share / name / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
    return share


@pytest.fixture
def labs_fixture(tmp_path):
    """All four consented skills PLUS one real, non-consented labs skill
    (`software-research`) -- the fixture the consent-list-refusal AC needs
    a genuinely share-tree-present name for."""
    _stage_labs_share(tmp_path, (*_LABS_CONSENT_SKILLS, NOT_CONSENTED_SKILL))
    return tmp_path


# ── provision_plugin_skill (primitive) ───────────────────────────────────


def test_fresh_install_lands_skill_and_writes_labs_roster(labs_fixture):
    result = provision_plugin_skill("labs", "mcp-builder", cwd=labs_fixture)

    assert result["skill_installed"] == "mcp-builder"
    assert result["skills_on_roster"] == ["mcp-builder"]
    assert (labs_fixture / ".claude/skills/mcp-builder/SKILL.md").read_text(
        encoding="utf-8"
    ) == "# mcp-builder\n"

    config = tomllib.loads(
        (labs_fixture / "_bmad/custom/config.toml").read_text(encoding="utf-8")
    )
    labs = config["modules"]["labs"]
    assert labs["skills"] == ["mcp-builder"]
    assert labs["provisioned_by"] == "steward"
    assert labs["installer"] == "steward provision --plugin labs --skill <name>"


def test_second_call_accumulates_without_disturbing_the_first_skill(labs_fixture):
    provision_plugin_skill("labs", "mcp-builder", cwd=labs_fixture)
    first_dir = labs_fixture / ".claude/skills/mcp-builder"
    first_mtime = first_dir.stat().st_mtime

    result = provision_plugin_skill("labs", "release-please", cwd=labs_fixture)

    assert result["skills_on_roster"] == ["mcp-builder", "release-please"]
    assert (labs_fixture / ".claude/skills/release-please").is_dir()
    # mcp-builder's own directory content is untouched by the second call.
    assert first_dir.is_dir()
    assert first_dir.stat().st_mtime == first_mtime
    assert (first_dir / "SKILL.md").read_text(encoding="utf-8") == "# mcp-builder\n"

    config = tomllib.loads(
        (labs_fixture / "_bmad/custom/config.toml").read_text(encoding="utf-8")
    )
    assert config["modules"]["labs"]["skills"] == ["mcp-builder", "release-please"]


def test_reprovision_is_idempotent_overwrite_without_roster_duplication(labs_fixture):
    provision_plugin_skill("labs", "mcp-builder", cwd=labs_fixture)

    result = provision_plugin_skill("labs", "mcp-builder", cwd=labs_fixture)

    assert result["skills_on_roster"] == ["mcp-builder"]
    config = tomllib.loads(
        (labs_fixture / "_bmad/custom/config.toml").read_text(encoding="utf-8")
    )
    assert config["modules"]["labs"]["skills"] == ["mcp-builder"]


def test_all_four_consented_skills_accumulate_in_sorted_order(labs_fixture):
    for name in ("release-please", "mcp-builder", "slides-generator", "multi-repo-git-ops"):
        provision_plugin_skill("labs", name, cwd=labs_fixture)

    for name in _LABS_CONSENT_SKILLS:
        assert (labs_fixture / ".claude/skills" / name).is_dir(), name

    config = tomllib.loads(
        (labs_fixture / "_bmad/custom/config.toml").read_text(encoding="utf-8")
    )
    assert config["modules"]["labs"]["skills"] == sorted(_LABS_CONSENT_SKILLS)


def test_consent_list_refusal_names_the_four_allowed_skills(labs_fixture):
    """A real, share-tree-present labs skill NOT on the consent list is
    refused -- nothing copied, nothing written to the roster."""
    with pytest.raises(RuntimeError, match="not on the .labs. consent list") as exc_info:
        provision_plugin_skill("labs", NOT_CONSENTED_SKILL, cwd=labs_fixture)

    for name in _LABS_CONSENT_SKILLS:
        assert name in str(exc_info.value)
    assert not (labs_fixture / ".claude/skills" / NOT_CONSENTED_SKILL).exists()
    assert not (labs_fixture / "_bmad/custom/config.toml").exists()


def test_foreign_directory_collision_refuses_and_leaves_it_untouched(labs_fixture):
    foreign = labs_fixture / ".claude/skills/mcp-builder"
    foreign.mkdir(parents=True)
    (foreign / "NOTES.md").write_text("unrelated foreign content\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="skill-name collision"):
        provision_plugin_skill("labs", "mcp-builder", cwd=labs_fixture)

    assert (foreign / "NOTES.md").read_text(encoding="utf-8") == "unrelated foreign content\n"
    assert not (foreign / "SKILL.md").exists()
    assert not (labs_fixture / "_bmad/custom/config.toml").exists()


def test_collision_check_is_per_skill_not_per_module(labs_fixture):
    """Once `mcp-builder` is legitimately installed (on the labs roster),
    installing `release-please` for the first time must still refuse a
    genuine FOREIGN collision on release-please's own directory -- it must
    not be waved through just because `labs` already has a roster."""
    provision_plugin_skill("labs", "mcp-builder", cwd=labs_fixture)
    foreign = labs_fixture / ".claude/skills/release-please"
    foreign.mkdir(parents=True)
    (foreign / "NOTES.md").write_text("unrelated foreign content\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="skill-name collision"):
        provision_plugin_skill("labs", "release-please", cwd=labs_fixture)

    config = tomllib.loads(
        (labs_fixture / "_bmad/custom/config.toml").read_text(encoding="utf-8")
    )
    assert config["modules"]["labs"]["skills"] == ["mcp-builder"]
    assert (foreign / "NOTES.md").read_text(encoding="utf-8") == "unrelated foreign content\n"


def test_unregistered_plugin_raises_file_not_found_naming_labs(labs_fixture):
    with pytest.raises(FileNotFoundError, match="labs"):
        provision_plugin_skill("bogus", "mcp-builder", cwd=labs_fixture)


def test_collision_error_names_plugin_not_module(labs_fixture):
    """Review finding: the reused-verbatim collision-check message must say
    'plugin' for the plugin-path class, never 'module' -- `labs` is
    explicitly never a `--module` target, and the old wording pointed an
    operator at `--list-modules`/`--module labs`, neither of which shows
    it."""
    foreign = labs_fixture / ".claude/skills/mcp-builder"
    foreign.mkdir(parents=True)

    with pytest.raises(RuntimeError, match=r"plugin 'labs': skill-name collision"):
        provision_plugin_skill("labs", "mcp-builder", cwd=labs_fixture)


def test_manifest_write_before_copy_makes_a_copy_failure_retry_self_healing(
    labs_fixture, monkeypatch
):
    """Review finding, empirically reproduced: an earlier draft copied the
    skill directory BEFORE recording the roster, so a write failure AFTER a
    successful copy left the directory behind with the roster never gaining
    the skill -- a retry's `already_installed` read `False` and treated the
    prior attempt's own leftover directory as a foreign collision,
    permanently refusing. Recording the roster first means a failure in the
    COPY step instead leaves `already_installed` reading `True` on retry,
    so the collision check is skipped and the retry just re-runs the
    (idempotent) copy -- self-healing, not self-locking."""
    import pyforge.steward.provision as provision_module

    real_copy = provision_module._copy_setup_skill_dirs
    calls = {"n": 0}

    def _fails_once(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("simulated copy failure")
        return real_copy(*args, **kwargs)

    monkeypatch.setattr(provision_module, "_copy_setup_skill_dirs", _fails_once)

    with pytest.raises(OSError, match="simulated copy failure"):
        provision_plugin_skill("labs", "mcp-builder", cwd=labs_fixture)

    # The roster already gained the skill; the directory does not exist yet.
    config = tomllib.loads(
        (labs_fixture / "_bmad/custom/config.toml").read_text(encoding="utf-8")
    )
    assert config["modules"]["labs"]["skills"] == ["mcp-builder"]
    assert not (labs_fixture / ".claude/skills/mcp-builder").exists()

    # Retry: self-healing (no foreign-collision refusal), not self-locking.
    result = provision_plugin_skill("labs", "mcp-builder", cwd=labs_fixture)
    assert result["skill_installed"] == "mcp-builder"
    assert (labs_fixture / ".claude/skills/mcp-builder/SKILL.md").is_file()


def test_missing_share_package_raises_before_any_write(tmp_path, monkeypatch):
    # Pin the ambient prefix to an empty env so the share package is missing
    # regardless of which pixi env runs the suite (pyforge-guild ships it).
    monkeypatch.setenv("CONDA_PREFIX", str(tmp_path / "lean-env"))
    with pytest.raises(FileNotFoundError):
        provision_plugin_skill("labs", "mcp-builder", cwd=tmp_path)
    assert not (tmp_path / "_bmad/custom/config.toml").exists()


def test_marketplace_json_sibling_is_never_touched(labs_fixture):
    """I/O Matrix: `.claude-plugin/marketplace.json` alongside
    `share/bmad-labs-skills/skills/` is never read or copied -- only the
    named subdirectory under `skills/` is."""
    marketplace = (
        labs_fixture
        / ".pixi/envs/pyforge-guild/share"
        / LABS_PACKAGE
        / ".claude-plugin"
        / "marketplace.json"
    )
    marketplace.parent.mkdir(parents=True)
    marketplace.write_text("{}", encoding="utf-8")

    provision_plugin_skill("labs", "mcp-builder", cwd=labs_fixture)

    assert marketplace.read_text(encoding="utf-8") == "{}"
    assert not (labs_fixture / ".claude/skills/.claude-plugin").exists()
    assert not (labs_fixture / ".claude/skills/marketplace.json").exists()


# ── _run_plugin / ProvisionDuty / CLI dispatch ───────────────────────────


def test_run_plugin_missing_skill_flag_is_a_duty_error(labs_fixture, monkeypatch):
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: labs_fixture)

    result = ProvisionDuty().run(_full_namespace(plugin="labs"))

    assert result.ok is False
    assert "--skill" in result.summary
    assert not (labs_fixture / "_bmad/custom/config.toml").exists()


def test_run_plugin_unregistered_plugin_is_reported_even_without_skill(labs_fixture, monkeypatch):
    """Review finding: --plugin bogus with no --skill must name 'bogus' as
    unsupported, not report the unrelated '--skill is required' message --
    plugin registration is checked before --skill's presence."""
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: labs_fixture)

    result = ProvisionDuty().run(_full_namespace(plugin="bogus"))

    assert result.ok is False
    assert "bogus" in result.summary
    assert "--skill is required" not in result.summary


def test_run_plugin_unregistered_plugin_names_labs_as_supported(labs_fixture, monkeypatch):
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: labs_fixture)

    result = ProvisionDuty().run(_full_namespace(plugin="bogus", skill="mcp-builder"))

    assert result.ok is False
    assert "labs" in result.summary
    assert not (labs_fixture / ".claude/skills/mcp-builder").exists()


def test_skill_without_plugin_falls_through_to_bare_provision_help(labs_fixture, monkeypatch):
    """AD-7: `--skill` alone (no `--plugin`) is not a recognized top-level
    action -- it falls through to the existing bare-`provision` help
    behavior, never crashing."""
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: labs_fixture)

    result = ProvisionDuty().run(_full_namespace(skill="mcp-builder"))

    assert result.ok is True
    assert "available flags" in result.summary


def test_run_plugin_json_success_is_valid_json(labs_fixture, monkeypatch):
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: labs_fixture)

    result = ProvisionDuty().run(
        _full_namespace(plugin="labs", skill="mcp-builder", json=True)
    )

    assert result.ok is True
    payload = json.loads(result.summary)
    assert payload["skill_installed"] == "mcp-builder"
    assert payload["skills_on_roster"] == ["mcp-builder"]


def test_run_plugin_json_failure_is_valid_json(labs_fixture, monkeypatch):
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: labs_fixture)

    result = ProvisionDuty().run(
        _full_namespace(plugin="labs", skill=NOT_CONSENTED_SKILL, json=True)
    )

    assert result.ok is False
    payload = json.loads(result.summary)
    assert "error" in payload


def test_cli_provision_plugin_labs_mcp_builder_round_trips(labs_fixture, monkeypatch, capsys):
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: labs_fixture)

    rc = main(["provision", "--plugin", "labs", "--skill", "mcp-builder"])

    assert rc == EXIT_OK
    out = capsys.readouterr().out
    assert "mcp-builder" in out
    assert (labs_fixture / ".claude/skills/mcp-builder").is_dir()


def test_cli_provision_plugin_consent_refusal_exits_failed(labs_fixture, monkeypatch, capsys):
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: labs_fixture)

    rc = main(["provision", "--plugin", "labs", "--skill", NOT_CONSENTED_SKILL])

    assert rc == EXIT_FAILED
    err = capsys.readouterr().err
    for name in _LABS_CONSENT_SKILLS:
        assert name in err


def test_labs_is_the_only_registered_plugin():
    assert set(_SUPPORTED_PLUGINS) == {"labs"}


def test_labs_backend_share_package_and_consent_list():
    backend = _SUPPORTED_PLUGINS["labs"]
    assert backend.share_package == "bmad-labs-skills"
    assert backend.allowed_skills == (
        "mcp-builder",
        "slides-generator",
        "multi-repo-git-ops",
        "release-please",
    )
