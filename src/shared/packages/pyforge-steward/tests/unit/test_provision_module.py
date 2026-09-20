"""`provision_module` + `provision --module` CLI dispatch — Story 6.1.

Covers the I/O matrix's happy-path (two-script success sequence), unknown-
name, missing-backend-dir, script-failure, and `--json` rows, both at the
primitive level (`provision_module`) and through the duty/CLI
(`ProvisionDuty().run()` / `main(["provision", "--module", ...])`). The real
`uv run merge-config.py`/`merge-help-csv.py` invocations are never
exercised here — `subprocess.run` and `pyforge.steward.provision.repo_root`
are monkeypatched, mirroring `test_provision_env.py`'s own rationale.

The dedicated AC-5 regression guard
(`test_provision_module_never_invokes_cleanup_legacy_or_passes_legacy_dir`)
asserts no call's argv ever contains `cleanup-legacy.py` or `--legacy-dir`
— the collateral-deletion risk the story spec's Design Notes identify
against this repo's real `_bmad/core/config.yaml` (a different, already
governance-owned module's legacy config).
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import pytest
from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main
from pyforge.steward.provision import ProvisionDuty, provision_module

_MODULE_YAML = """\
code: bmb
name: "BMad Builder"
description: "Standard Skill Compliant Factory for BMad Agents, Workflows and Modules"
module_version: 1.0.0
default_selected: false
module_greeting: >
  Enjoy making your dream creations with the BMad Builder Module!

bmad_builder_output_folder:
  prompt: "Where should your custom output (agent, workflow, module config) be saved?"
  default: "{project-root}/skills"
  result: "{project-root}/{value}"

bmad_builder_reports:
  prompt: "Output for Evals, Test, Quality and Planning Reports?"
  default: "{project-root}/skills/reports"
  result: "{project-root}/{value}"
"""

_MODULE_HELP_CSV = (
    "module,skill,display-name,menu-code,description,action,args,phase,"
    "after,before,required,output-location,outputs\n"
    'BMad Builder,bmad-bmb-setup,Setup Builder Module,SB,"Install or update.",'
    "configure,,anytime,,,false,{project-root}/_bmad,config.yaml\n"
)

_SKILL_RELATIVE_PATH = Path(".pixi/envs/pyforge-guild/share/bmad-builder/skills/bmad-bmb-setup")


def _write_bmb_skill(root: Path) -> Path:
    skill_dir = root / _SKILL_RELATIVE_PATH
    (skill_dir / "assets").mkdir(parents=True)
    (skill_dir / "assets" / "module.yaml").write_text(_MODULE_YAML, encoding="utf-8")
    (skill_dir / "assets" / "module-help.csv").write_text(_MODULE_HELP_CSV, encoding="utf-8")
    (skill_dir / "scripts").mkdir()
    return skill_dir


# ── Story 46.4: the five real bmad-builder skills under `skills_source_dir`
# (`.pixi/envs/pyforge-guild/share/bmad-builder/skills/`) ───────────────────

_SKILLS_SOURCE_RELATIVE_PATH = Path(".pixi/envs/pyforge-guild/share/bmad-builder/skills")

_SIBLING_BUILDER_SKILL_NAMES = (
    "bmad-agent-builder",
    "bmad-workflow-builder",
    "bmad-module-builder",
    "bmad-eval-runner",
)

_ALL_BUILDER_SKILL_NAMES = frozenset({"bmad-bmb-setup", *_SIBLING_BUILDER_SKILL_NAMES})


def _write_bmb_skill_with_siblings(root: Path) -> Path:
    """`_write_bmb_skill` plus the four sibling builder skills and the two
    files (`module.yaml`, `module-help.csv`) confirmed live to sit alongside
    all five skill dirs at `skills_source_dir` -- distinct from
    `bmad-bmb-setup`'s own `assets/module.yaml` the merge scripts read.
    Gives the directory-only discovery filter real files to skip, not just
    directories to find."""
    skill_dir = _write_bmb_skill(root)
    skills_source = root / _SKILLS_SOURCE_RELATIVE_PATH
    (skills_source / "module.yaml").write_text("code: bmad-builder\n", encoding="utf-8")
    (skills_source / "module-help.csv").write_text("module,skill\n", encoding="utf-8")
    for sibling in _SIBLING_BUILDER_SKILL_NAMES:
        sibling_dir = skills_source / sibling
        sibling_dir.mkdir()
        (sibling_dir / "SKILL.md").write_text(f"# {sibling}\n", encoding="utf-8")
    return skill_dir


def _fake_module_scripts_run(cmd, **kwargs):  # noqa: ARG001
    """Stand in for the real `uv run merge-config.py`/`merge-help-csv.py`
    subprocesses. Returns each script's own documented JSON success
    envelope AND performs the same minimal, realistic file write the real
    script performs -- a `bmb:` section landing in `_bmad/config.yaml`, a
    header + one data row landing in `module-help.csv` -- so
    `module_install_states` (Story 6.2's oracle, reused by Story 6.3's
    post-success verification gate) sees a real, consistent filesystem
    state in every happy-path test that uses this fixture, rather than an
    empty one the new gate would (correctly) reject."""
    if any("merge-config.py" in str(part) for part in cmd):
        config_path = Path(cmd[cmd.index("--config-path") + 1])
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("bmb:\n  bmad_builder_output_folder: skills\n", encoding="utf-8")
        stdout = json.dumps(
            {
                "status": "success",
                "module_code": "bmb",
                "module_keys": ["bmad_builder_output_folder", "bmad_builder_reports"],
                "legacy_configs_found": [],
                "legacy_configs_deleted": [],
            }
        )
    else:
        target_path = Path(cmd[cmd.index("--target") + 1])
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(_MODULE_HELP_CSV, encoding="utf-8")
        stdout = json.dumps(
            {
                "status": "success",
                "module_codes": ["bmb"],
                "rows_added": 9,
                "legacy_csvs_deleted": [],
            }
        )
    return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")


def _fake_module_scripts_run_without_writing_config(cmd, **kwargs):  # noqa: ARG001
    """Simulates a backend inconsistency (story spec Design Notes: not
    reachable via the real `bmb` backend today, but a defensive contract
    for FR-21's literal wording): both scripts exit 0 and emit a
    `"status": "success"` envelope, but neither ever writes `<name>` into
    `_bmad/config.yaml` -- exercising `_run_module`'s post-success
    verification gate."""
    if any("merge-config.py" in str(part) for part in cmd):
        stdout = json.dumps(
            {
                "status": "success",
                "module_code": "bmb",
                "module_keys": [],
                "legacy_configs_found": [],
                "legacy_configs_deleted": [],
            }
        )
    else:
        stdout = json.dumps(
            {
                "status": "success",
                "module_codes": ["bmb"],
                "rows_added": 0,
                "legacy_csvs_deleted": [],
            }
        )
    return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")


def _full_namespace(**overrides):
    base = {"module": None, "env": None, "runner": None, "list": False, "verify": False, "json": False}
    base.update(overrides)
    return argparse.Namespace(**base)


# ── provision_module (primitive) ─────────────────────────────────────────


def test_provision_module_happy_path_invokes_both_scripts_with_no_legacy_dir(tmp_path, monkeypatch):
    skill_dir = _write_bmb_skill(tmp_path)
    calls = []
    answers_seen = []

    def _fake_run(cmd, **kwargs):  # noqa: ARG001
        calls.append(cmd)
        if "--answers" in cmd:
            answers_path = cmd[cmd.index("--answers") + 1]
            answers_seen.append(json.loads(Path(answers_path).read_text(encoding="utf-8")))
        return _fake_module_scripts_run(cmd)

    monkeypatch.setattr(subprocess, "run", _fake_run)

    result = provision_module("bmb", cwd=tmp_path)

    assert len(calls) == 2
    merge_config_cmd, merge_help_cmd = calls

    expected_merge_config_prefix = [
        "uv",
        "run",
        str(skill_dir / "scripts" / "merge-config.py"),
        "--config-path",
        str(tmp_path / "_bmad" / "config.yaml"),
        "--user-config-path",
        str(tmp_path / "_bmad" / "config.user.yaml"),
        "--module-yaml",
        str(skill_dir / "assets" / "module.yaml"),
        "--answers",
    ]
    assert merge_config_cmd[:-1] == expected_merge_config_prefix
    assert merge_config_cmd[-1].endswith(".json")

    assert merge_help_cmd == [
        "uv",
        "run",
        str(skill_dir / "scripts" / "merge-help-csv.py"),
        "--target",
        str(tmp_path / "_bmad" / "module-help.csv"),
        "--source",
        str(skill_dir / "assets" / "module-help.csv"),
    ]

    # The answers JSON assembled from module.yaml's own declared defaults.
    assert answers_seen == [
        {
            "module": {
                "bmad_builder_output_folder": "{project-root}/skills",
                "bmad_builder_reports": "{project-root}/skills/reports",
            }
        }
    ]

    # {project-root}-prefixed output dirs are mkdir -p'd.
    assert (tmp_path / "skills").is_dir()
    assert (tmp_path / "skills" / "reports").is_dir()

    assert result["merge_config"]["status"] == "success"
    assert result["merge_help_csv"]["status"] == "success"
    assert result["output_dirs_created"] == ["skills", "skills/reports"]


def test_provision_module_never_invokes_cleanup_legacy_or_passes_legacy_dir(tmp_path, monkeypatch):
    """AC 5 regression guard: no call's argv may ever contain
    `cleanup-legacy.py` or `--legacy-dir` — passing `--legacy-dir` would pull
    this repo's real `_bmad/core/config.yaml` in as fallback defaults, and
    `cleanup-legacy.py --module-code bmb` would `shutil.rmtree` that
    governance-owned directory (story spec Design Notes)."""
    _write_bmb_skill(tmp_path)
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kwargs: calls.append(cmd) or _fake_module_scripts_run(cmd))

    provision_module("bmb", cwd=tmp_path)

    assert len(calls) == 2
    for call in calls:
        assert not any("cleanup-legacy.py" in str(part) for part in call), call
        assert "--legacy-dir" not in call, call


def test_provision_module_leaves_pre_existing_bmad_core_config_untouched(tmp_path, monkeypatch):
    """Regression guard for the collateral-deletion risk: `_bmad/core/
    config.yaml` (a different, already-governance-owned module's legacy
    config, genuinely present in this repo) must be left byte-for-byte
    untouched by a `--module bmb` run."""
    _write_bmb_skill(tmp_path)
    core_config = tmp_path / "_bmad" / "core" / "config.yaml"
    core_config.parent.mkdir(parents=True)
    core_config.write_text("output_folder: something\n", encoding="utf-8")
    before = core_config.read_text(encoding="utf-8")

    monkeypatch.setattr(subprocess, "run", _fake_module_scripts_run)

    provision_module("bmb", cwd=tmp_path)

    assert core_config.read_text(encoding="utf-8") == before


def test_provision_module_missing_backend_dir_raises_file_not_found_before_any_subprocess(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kwargs: calls.append(cmd))  # noqa: ARG005

    with pytest.raises(FileNotFoundError):
        provision_module("bmb", cwd=tmp_path)

    assert calls == []


def test_provision_module_unregistered_name_raises_file_not_found_not_key_error(tmp_path):
    """A direct caller bypassing `_run_module`'s membership check (Story 6.2/
    6.3 code, or any future caller) must see the same documented
    `FileNotFoundError` the missing-backend-dir case raises, never a bare
    `KeyError` from `_SUPPORTED_MODULES[name]`."""
    with pytest.raises(FileNotFoundError):
        provision_module("not-a-registered-module", cwd=tmp_path)


def test_provision_module_malformed_module_yaml_is_a_clean_runtime_error(tmp_path):
    skill_dir = tmp_path / _SKILL_RELATIVE_PATH
    (skill_dir / "assets").mkdir(parents=True)
    (skill_dir / "assets" / "module.yaml").write_text("- just\n- a\n- list\n", encoding="utf-8")
    (skill_dir / "scripts").mkdir()

    with pytest.raises(RuntimeError, match="did not parse to a mapping"):
        provision_module("bmb", cwd=tmp_path)


def test_provision_module_code_mismatch_is_a_clean_runtime_error(tmp_path):
    """Guards against a registered `_SUPPORTED_MODULES` key silently drifting
    from the module's own declared `code:` field."""
    skill_dir = tmp_path / _SKILL_RELATIVE_PATH
    (skill_dir / "assets").mkdir(parents=True)
    (skill_dir / "assets" / "module.yaml").write_text("code: not-bmb\n", encoding="utf-8")
    (skill_dir / "scripts").mkdir()

    with pytest.raises(RuntimeError, match="does not match the registered name"):
        provision_module("bmb", cwd=tmp_path)


def test_provision_module_script_emits_unparseable_stdout_is_a_clean_runtime_error(tmp_path, monkeypatch):
    _write_bmb_skill(tmp_path)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0, stdout="not json", stderr=""),  # noqa: ARG005
    )

    with pytest.raises(RuntimeError, match="did not emit valid JSON"):
        provision_module("bmb", cwd=tmp_path)


def test_materialize_module_output_dirs_applies_the_value_substitution_branch(tmp_path):
    """`_materialize_module_output_dirs`'s `{value}`-substitution branch (a
    `default` that does NOT already contain `{project-root}`, combined with a
    `result` template that does) is dead for the real `bmb` module.yaml today
    but is a real, reachable code path — covered here directly rather than
    only through `bmb`'s own fixture."""
    from pyforge.steward.provision import _materialize_module_output_dirs

    module_yaml = {
        "code": "example",
        "custom_output": {
            "prompt": "Where?",
            "default": "reports",
            "result": "{project-root}/{value}",
        },
    }

    created = _materialize_module_output_dirs(module_yaml, cwd=tmp_path)

    assert created == ("reports",)
    assert (tmp_path / "reports").is_dir()


def test_provision_module_output_dir_path_occupied_by_a_file_is_a_clean_runtime_error(tmp_path):
    from pyforge.steward.provision import _materialize_module_output_dirs

    (tmp_path / "skills").write_text("not a directory", encoding="utf-8")
    module_yaml = {
        "code": "bmb",
        "bmad_builder_output_folder": {
            "prompt": "Where?",
            "default": "{project-root}/skills",
        },
    }

    with pytest.raises(RuntimeError, match="already exists and is not a directory"):
        _materialize_module_output_dirs(module_yaml, cwd=tmp_path)


def test_provision_module_second_script_failure_propagates_after_the_first_ran(tmp_path, monkeypatch):
    _write_bmb_skill(tmp_path)
    calls = []

    def _fake_run(cmd, **kwargs):  # noqa: ARG001
        calls.append(cmd)
        if any("merge-help-csv.py" in str(part) for part in cmd):
            raise subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr="No data rows found in source")
        return _fake_module_scripts_run(cmd)

    monkeypatch.setattr(subprocess, "run", _fake_run)

    with pytest.raises(subprocess.CalledProcessError):
        provision_module("bmb", cwd=tmp_path)

    assert len(calls) == 2  # merge-config.py ran to completion before merge-help-csv.py failed


def test_provision_module_can_run_twice_without_error(tmp_path, monkeypatch):
    """I/O matrix: re-running against an already-provisioned module is
    idempotent — the anti-zombie merge lives in the wrapped scripts
    themselves; this only asserts the wrap itself never errors on a second
    call."""
    _write_bmb_skill(tmp_path)
    monkeypatch.setattr(subprocess, "run", _fake_module_scripts_run)

    first = provision_module("bmb", cwd=tmp_path)
    second = provision_module("bmb", cwd=tmp_path)

    assert first["merge_config"]["status"] == "success"
    assert second["merge_config"]["status"] == "success"


# ── Story 46.4: bmb's five skills land beside skf ────────────────────────


def test_provision_module_bmb_copies_all_five_builder_skills_fresh(tmp_path, monkeypatch):
    """I/O Matrix 'Fresh bmb provision': all five skill dirs land under
    `.claude/skills/`, the two sibling files at `skills_source_dir` are
    excluded, and `_bmad/config.yaml` still gains `bmb` via the unchanged
    merge-config.py mechanism."""
    _write_bmb_skill_with_siblings(tmp_path)
    monkeypatch.setattr(subprocess, "run", _fake_module_scripts_run)

    result = provision_module("bmb", cwd=tmp_path)

    skills_dir = tmp_path / ".claude" / "skills"
    for skill_name in _ALL_BUILDER_SKILL_NAMES:
        assert (skills_dir / skill_name).is_dir(), skill_name
    assert not (skills_dir / "module.yaml").exists()
    assert not (skills_dir / "module-help.csv").exists()
    assert set(result["skills_copied"]) == _ALL_BUILDER_SKILL_NAMES
    assert (tmp_path / "_bmad" / "config.yaml").is_file()


def test_provision_module_bmb_reprovision_overwrites_skills_in_place(tmp_path, monkeypatch):
    """I/O Matrix 'Re-provision': the five dirs already exist from a prior,
    bmb-recorded run -- overwritten in place (idempotent), no error, no
    duplication. A stray leftover file inside a landed skill proves the
    second run actually replaces the directory rather than merging into
    whatever the first run left behind."""
    _write_bmb_skill_with_siblings(tmp_path)
    monkeypatch.setattr(subprocess, "run", _fake_module_scripts_run)

    provision_module("bmb", cwd=tmp_path)
    stray = tmp_path / ".claude" / "skills" / "bmad-agent-builder" / "STALE.md"
    stray.write_text("leftover from a previous version\n", encoding="utf-8")

    second = provision_module("bmb", cwd=tmp_path)

    assert not stray.exists()
    assert (tmp_path / ".claude" / "skills" / "bmad-agent-builder" / "SKILL.md").is_file()
    assert set(second["skills_copied"]) == _ALL_BUILDER_SKILL_NAMES


def test_provision_module_bmb_foreign_collision_refuses_and_writes_nothing(tmp_path, monkeypatch):
    """I/O Matrix 'Foreign collision': `.claude/skills/bmad-agent-builder`
    already exists but is NOT recorded as bmb-installed -- refuses with a
    named collision error before any subprocess call, copies nothing, and
    writes nothing to `_bmad/config.yaml`."""
    _write_bmb_skill_with_siblings(tmp_path)
    foreign = tmp_path / ".claude" / "skills" / "bmad-agent-builder"
    foreign.mkdir(parents=True)
    (foreign / "SKILL.md").write_text("not the real one\n", encoding="utf-8")
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kwargs: calls.append(cmd))  # noqa: ARG005

    with pytest.raises(RuntimeError, match="skill-name collision"):
        provision_module("bmb", cwd=tmp_path)

    assert calls == [], "collision refusal must happen before any subprocess call"
    assert not (tmp_path / "_bmad" / "config.yaml").exists()
    assert (foreign / "SKILL.md").read_text(encoding="utf-8") == "not the real one\n"
    assert not (tmp_path / ".claude" / "skills" / "bmad-bmb-setup").exists()


def test_provision_module_bmb_via_cli_reports_skills_copied_count(tmp_path, monkeypatch):
    """The `--json` output surfaces `skills_copied` alongside the unchanged
    `merge_config`/`merge_help_csv` keys, and the text summary names the
    skill count -- both mirror the `CondaInstallBackend` path's own
    `skills_installed` reporting rather than staying silent about the new
    copy step."""
    _write_bmb_skill_with_siblings(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)
    monkeypatch.setattr(subprocess, "run", _fake_module_scripts_run)

    duty = ProvisionDuty()
    json_result = duty.run(_full_namespace(module="bmb", json=True))
    text_result = duty.run(_full_namespace(module="bmb"))

    assert json_result.ok is True
    payload = json.loads(json_result.summary)
    assert set(payload["skills_copied"]) == _ALL_BUILDER_SKILL_NAMES
    assert text_result.ok is True
    assert "5 skill(s)" in text_result.summary


# ── ProvisionDuty / CLI dispatch ─────────────────────────────────────────


def test_provision_module_unknown_name_never_reaches_subprocess(tmp_path, monkeypatch):
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kwargs: calls.append(cmd))  # noqa: ARG005

    duty = ProvisionDuty()
    result = duty.run(_full_namespace(module="nope"))

    assert result.ok is False
    assert "nope" in result.summary
    assert "bmb" in result.summary
    assert calls == [], "an unknown module name must never reach a subprocess"


def test_provision_module_unknown_name_via_cli_exits_failed(tmp_path, monkeypatch):
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)

    rc = main(["provision", "--module", "nope"])

    assert rc == EXIT_FAILED


def test_provision_module_unknown_name_with_json_emits_a_parseable_error(tmp_path, monkeypatch):
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)

    duty = ProvisionDuty()
    result = duty.run(_full_namespace(module="nope", json=True))

    assert result.ok is False
    payload = json.loads(result.summary)
    assert "nope" in payload["error"]
    assert "bmb" in payload["error"]


def test_provision_module_missing_backend_dir_names_the_path_and_the_pixi_fix(tmp_path, monkeypatch):
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)

    duty = ProvisionDuty()
    result = duty.run(_full_namespace(module="bmb"))

    assert result.ok is False
    assert "bmad-bmb-setup" in result.summary
    assert "pixi install -e pyforge-guild" in result.summary


def test_provision_module_missing_backend_dir_via_cli_is_a_duty_failure_not_a_crash(tmp_path, monkeypatch):
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)

    rc = main(["provision", "--module", "bmb"])

    assert rc == EXIT_FAILED


def test_provision_module_bmb_via_cli_round_trips(tmp_path, monkeypatch):
    _write_bmb_skill(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)
    monkeypatch.setattr(subprocess, "run", _fake_module_scripts_run)

    rc = main(["provision", "--module", "bmb"])

    assert rc == EXIT_OK


def test_provision_module_bmb_json_emits_parseable_result_keyed_by_step(tmp_path, monkeypatch):
    _write_bmb_skill(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)
    monkeypatch.setattr(subprocess, "run", _fake_module_scripts_run)

    duty = ProvisionDuty()
    result = duty.run(_full_namespace(module="bmb", json=True))

    assert result.ok is True
    payload = json.loads(result.summary)
    assert payload["merge_config"]["status"] == "success"
    assert payload["merge_help_csv"]["status"] == "success"


def test_provision_module_script_failure_surfaces_stderr_verbatim_and_honors_json(tmp_path, monkeypatch):
    _write_bmb_skill(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)

    def _fake_run(cmd, **kwargs):  # noqa: ARG001
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr="Error: Could not load module.yaml")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    duty = ProvisionDuty()
    result = duty.run(_full_namespace(module="bmb", json=True))

    assert result.ok is False
    payload = json.loads(result.summary)
    assert "Could not load module.yaml" in payload["error"]
    assert "nothing was written to _bmad/config.yaml" in payload["error"]


def test_provision_module_script_failure_via_cli_exits_failed(tmp_path, monkeypatch):
    _write_bmb_skill(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)

    def _fake_run(cmd, **kwargs):  # noqa: ARG001
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr="boom")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    rc = main(["provision", "--module", "bmb"])

    assert rc == EXIT_FAILED


def test_provision_module_empty_string_is_treated_as_an_unsupported_name(tmp_path, monkeypatch):
    """`--module ""` must be reported as an unsupported name, not silently
    fall through to the bare-`provision` success summary — empty string is
    falsy, so the dispatch check must use `is not None`, not a truthiness
    check on `ns.module` itself."""
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kwargs: calls.append(cmd))  # noqa: ARG005

    duty = ProvisionDuty()
    result = duty.run(_full_namespace(module=""))

    assert result.ok is False
    assert "bmb" in result.summary  # names the supported set, not the bare-provision help
    assert calls == []


def test_provision_module_takes_precedence_over_verify_and_list():
    """`--module` is the new first precedence check, ahead of `--verify` and
    `--list` (mirrors each new story's flag landing at the top of the
    if-chain)."""
    duty = ProvisionDuty()

    result = duty.run(
        _full_namespace(module="nope", list=True, verify=True)
    )

    assert result.ok is False
    assert "nope" in result.summary  # --module's own handling ran, not --verify's/--list's


# ── Story 6.3: partial-install failure naming + post-success verification ──


def test_provision_module_mid_chain_failure_names_already_wrote_config_section(tmp_path, monkeypatch):
    """I/O Matrix row 1: `merge-config.py` exits 0 (writes `bmb:` into
    `_bmad/config.yaml`), `merge-help-csv.py` exits 1 -- the `DutyResult`
    must carry both the failing script's stderr AND a note that
    `_bmad/config.yaml` already gained a `bmb` section."""
    _write_bmb_skill(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)

    def _fake_run(cmd, **kwargs):  # noqa: ARG001
        if any("merge-help-csv.py" in str(part) for part in cmd):
            raise subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr="No data rows found in source")
        return _fake_module_scripts_run(cmd)

    monkeypatch.setattr(subprocess, "run", _fake_run)

    duty = ProvisionDuty()
    result = duty.run(_full_namespace(module="bmb"))

    assert result.ok is False
    assert "No data rows found in source" in result.summary
    assert "already wrote a 'bmb' section to _bmad/config.yaml during this run before the failure above" in result.summary
    assert "INCOMPLETE" in result.summary


def test_provision_module_mid_chain_failure_with_json_names_already_wrote_config_section(tmp_path, monkeypatch):
    """Same scenario as above, with `--json`: the note must be parseable
    inside the existing `{"error": ...}` shape, matching every other
    error path's JSON contract."""
    _write_bmb_skill(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)

    def _fake_run(cmd, **kwargs):  # noqa: ARG001
        if any("merge-help-csv.py" in str(part) for part in cmd):
            raise subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr="No data rows found in source")
        return _fake_module_scripts_run(cmd)

    monkeypatch.setattr(subprocess, "run", _fake_run)

    duty = ProvisionDuty()
    result = duty.run(_full_namespace(module="bmb", json=True))

    assert result.ok is False
    payload = json.loads(result.summary)
    assert "No data rows found in source" in payload["error"]
    assert "already wrote a 'bmb' section to _bmad/config.yaml during this run before the failure above" in payload["error"]


def test_provision_module_first_script_failure_names_nothing_written(tmp_path, monkeypatch):
    """I/O Matrix row 2: `merge-config.py` itself exits 1 before writing
    anything -- the summary must state nothing was written to
    `_bmad/config.yaml`, not the "already wrote" note."""
    _write_bmb_skill(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)

    def _fake_run(cmd, **kwargs):  # noqa: ARG001
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr="Error: Could not load module.yaml")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    duty = ProvisionDuty()
    result = duty.run(_full_namespace(module="bmb"))

    assert result.ok is False
    assert "Could not load module.yaml" in result.summary
    assert "nothing was written to _bmad/config.yaml" in result.summary
    assert "already wrote" not in result.summary


def test_provision_module_bmb_retry_after_first_script_failure_does_not_self_collide(
    tmp_path, monkeypatch
):
    """Review finding: an earlier draft copied bmb's five skill directories
    BEFORE the merge-config.py/merge-help-csv.py subprocess calls. If those
    calls then failed, the freshly-copied skill dirs were left behind with
    _bmad/config.yaml never gaining the `bmb` key -- so a retry's own
    `already_installed` check still read False and treated the module's own
    leftover directories from the failed attempt as a foreign collision,
    permanently self-locking every retry. The copy now runs only after both
    scripts succeed, so a failed first attempt leaves nothing new behind to
    collide with, and a fixed-and-retried run succeeds cleanly."""
    _write_bmb_skill_with_siblings(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)

    def _failing_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr="transient uv error")

    monkeypatch.setattr(subprocess, "run", _failing_run)
    first = ProvisionDuty().run(_full_namespace(module="bmb"))
    assert first.ok is False
    assert not (tmp_path / ".claude/skills/bmad-bmb-setup").exists(), (
        "the failed first attempt must not have copied anything"
    )

    monkeypatch.setattr(subprocess, "run", _fake_module_scripts_run)
    second = ProvisionDuty().run(_full_namespace(module="bmb"))

    assert second.ok is True, second.summary
    for skill in _ALL_BUILDER_SKILL_NAMES:
        assert (tmp_path / ".claude/skills" / skill).is_dir(), skill


def test_provision_module_bmb_target_exists_as_file_raises_named_error(tmp_path, monkeypatch):
    """Review finding: a foreign plain file (not a directory) sitting at a
    predicted skill path must fail with a clear, named RuntimeError, not an
    unclear shutil.copytree FileExistsError. Uses an already-installed `bmb`
    (the collision check is skipped once installed, per its own documented
    idempotent-re-provision contract) so the scenario reaches
    `_copy_setup_skill_dirs`'s own guard rather than the earlier collision
    check, which would otherwise catch this exact path first via its
    broader `.exists()` test."""
    _write_bmb_skill_with_siblings(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)
    monkeypatch.setattr(subprocess, "run", _fake_module_scripts_run)
    bmad_dir = tmp_path / "_bmad"
    bmad_dir.mkdir(parents=True)
    (bmad_dir / "config.yaml").write_text("bmb: {}\n", encoding="utf-8")
    claude_skills = tmp_path / ".claude/skills"
    claude_skills.mkdir(parents=True)
    (claude_skills / "bmad-bmb-setup").write_text("not a directory", encoding="utf-8")

    result = ProvisionDuty().run(_full_namespace(module="bmb"))

    assert result.ok is False
    assert "exists and is not a directory" in result.summary


def test_provision_module_output_dir_runtime_error_after_both_scripts_land_names_already_wrote_config(
    tmp_path, monkeypatch
):
    """I/O Matrix row 3: both scripts exit 0 (landing `_bmad/config.yaml`
    and `module-help.csv`), then `_materialize_module_output_dirs` raises
    `RuntimeError` because its target path is occupied by a file -- the
    summary must carry the `RuntimeError` text AND the same "already
    wrote" note, since the config/CSV writes happened before the output-dir
    step runs."""
    _write_bmb_skill(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)
    monkeypatch.setattr(subprocess, "run", _fake_module_scripts_run)
    (tmp_path / "skills").write_text("not a directory", encoding="utf-8")

    duty = ProvisionDuty()
    result = duty.run(_full_namespace(module="bmb"))

    assert result.ok is False
    assert "already exists and is not a directory" in result.summary
    assert "already wrote a 'bmb' section to _bmad/config.yaml during this run before the failure above" in result.summary
    assert "INCOMPLETE" in result.summary


def test_provision_module_post_success_verification_gate_rejects_when_name_not_actually_installed(
    tmp_path, monkeypatch
):
    """I/O Matrix row 4: both scripts exit 0 and report `"status":
    "success"`, but a simulated backend inconsistency means `bmb` never
    lands in `_bmad/config.yaml` -- `_run_module`'s post-success
    verification gate must refuse to report `ok=True` on the strength of
    the exit code alone."""
    _write_bmb_skill(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)
    monkeypatch.setattr(subprocess, "run", _fake_module_scripts_run_without_writing_config)

    duty = ProvisionDuty()
    result = duty.run(_full_namespace(module="bmb"))

    assert result.ok is False
    assert "exited 0" in result.summary
    assert "not counted as provisioned" in result.summary


def test_provision_module_post_success_verification_gate_via_cli_exits_failed(tmp_path, monkeypatch):
    _write_bmb_skill(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)
    monkeypatch.setattr(subprocess, "run", _fake_module_scripts_run_without_writing_config)

    rc = main(["provision", "--module", "bmb"])

    assert rc == EXIT_FAILED


def test_provision_module_post_success_verification_gate_with_json(tmp_path, monkeypatch):
    """I/O Matrix row 5: `--json` honored on the post-success verification
    gate's failure path too, matching every other error path's shape."""
    _write_bmb_skill(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)
    monkeypatch.setattr(subprocess, "run", _fake_module_scripts_run_without_writing_config)

    duty = ProvisionDuty()
    result = duty.run(_full_namespace(module="bmb", json=True))

    assert result.ok is False
    payload = json.loads(result.summary)
    assert "not counted as provisioned" in payload["error"]


def test_provision_module_full_success_verification_gate_passes_with_realistic_fixture(tmp_path, monkeypatch):
    """I/O Matrix row 5 (full success, unchanged happy path): with the
    updated `_fake_module_scripts_run` actually landing `bmb` in
    `_bmad/config.yaml`, the post-success verification gate must not
    regress the true happy path -- `ok=True` exactly as Story 6.1
    established."""
    _write_bmb_skill(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)
    monkeypatch.setattr(subprocess, "run", _fake_module_scripts_run)

    duty = ProvisionDuty()
    result = duty.run(_full_namespace(module="bmb"))

    assert result.ok is True
    assert (tmp_path / "_bmad" / "config.yaml").is_file()


def test_provision_module_failure_against_an_already_installed_module_does_not_claim_incomplete(
    tmp_path, monkeypatch
):
    """Review-pass regression: `bmb` was already fully provisioned by an
    earlier, successful run (`_bmad/config.yaml` already has a `bmb:`
    section BEFORE this run starts). This run's own `merge-config.py` call
    fails for a reason that never touches the filesystem (e.g. a transient
    `uv` invocation error). Since `module_install_states` only sees the
    file's PRESENT state, comparing it alone (with no before-snapshot)
    would wrongly conclude this run "already wrote a section ... INCOMPLETE"
    -- the state present is leftover from the PRIOR run, not new. The
    landed-state note must be omitted entirely: nothing about this run's
    own outcome is newly incomplete."""
    _write_bmb_skill(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)
    config_path = tmp_path / "_bmad" / "config.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("bmb:\n  name: BMad Builder\n", encoding="utf-8")

    def _fake_run(cmd, **kwargs):  # noqa: ARG001
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr="transient uv error")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    duty = ProvisionDuty()
    result = duty.run(_full_namespace(module="bmb"))

    assert result.ok is False
    assert "transient uv error" in result.summary
    assert "INCOMPLETE" not in result.summary
    assert "already wrote" not in result.summary
    # the pre-existing install itself is untouched by this failed run
    assert config_path.read_text(encoding="utf-8") == "bmb:\n  name: BMad Builder\n"


def test_provision_module_malformed_config_during_failure_recovery_read_preserves_original_stderr(
    tmp_path, monkeypatch
):
    """Review-pass regression: if `_bmad/config.yaml` is malformed YAML at
    the moment `_run_module`'s except handler tries to check landed state,
    `module_install_states` itself raises `yaml.YAMLError` -- that read
    failure must degrade to "unknown" (no landed-state note), never
    replace the original, more diagnostic subprocess stderr with an
    unrelated YAML-parse error, and never crash past a clean
    `DutyResult(ok=False, ...)`."""
    _write_bmb_skill(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)
    config_path = tmp_path / "_bmad" / "config.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(": not: valid: yaml: [", encoding="utf-8")

    def _fake_run(cmd, **kwargs):  # noqa: ARG001
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr="Error: Could not load module.yaml")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    duty = ProvisionDuty()
    result = duty.run(_full_namespace(module="bmb"))

    assert result.ok is False
    assert "Could not load module.yaml" in result.summary
    assert "already wrote" not in result.summary
    assert "nothing was written" not in result.summary


def test_provision_module_post_success_gate_survives_an_unreadable_config_yaml(tmp_path, monkeypatch):
    """Review-pass regression: if the post-success verification read
    itself raises (e.g. `OSError`/malformed YAML), `_run_module` must
    still return a clean `DutyResult(ok=False, ...)` -- never let a second
    exception from the verification step itself propagate past this
    story's own boundary as an internal crash."""
    _write_bmb_skill(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)
    monkeypatch.setattr(subprocess, "run", _fake_module_scripts_run)

    def _raise_os_error(**kwargs):  # noqa: ARG001
        raise OSError("permission denied")

    monkeypatch.setattr(
        "pyforge.steward.provision.module_install_states",
        lambda *, cwd: _raise_os_error(),
    )

    duty = ProvisionDuty()
    result = duty.run(_full_namespace(module="bmb"))

    assert result.ok is False
    assert "not counted as provisioned" in result.summary
