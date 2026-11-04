"""Story 113.1 (CAP-298): the challenge session's argv comes from the packaged claude profile.

Story 113.10 (CAP-299): the session carries no house context, checked at runtime -- hooks off,
Read denies on the instruction files, memlogs and team memory (the target excepted), no
``instructionFiles`` plugin config, ``egm@egm`` enabled in the session's own settings, and a cwd
outside the repo.

Story 113.14 (CAP-298, CAP-299): the session's ceiling is the stage's ``[challenge].timeout_s``, else
its per-stage default; a session past it is killed and raised, never waited on."""

from __future__ import annotations

import dataclasses
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path, PurePosixPath

import pytest
from pyforge.core.process import ProcessError, ProcessResult

from pyforge.marshal.adapters import challenge_harness as harness
from pyforge.marshal.cli import challenge as cli
from pyforge.marshal.core import challenge as core
from pyforge.marshal.core.harness_profile import load_packaged_profiles


def _settings(argv: list[str]) -> dict:
    return json.loads(argv[argv.index("--settings") + 1])


def _render(tmp_path: Path, *, target: Path | None = None, profile=None) -> tuple[list[str], dict]:
    root = tmp_path / "repo"
    argv = harness.render_argv(
        profile or load_packaged_profiles()["claude"],
        prompt="PROMPT",
        model="claude-fable-5-1",
        session_id="sid",
        read_rules=harness.plugin_cache_read_rules(tmp_path / "plugins"),
        run_dir=tmp_path / "run",
        deny_rules=harness.forbidden_read_rules(root, target),
    )
    return argv, _settings(argv)


def test_argv_widens_the_profile_settings_with_plugin_cache_read_rules(tmp_path: Path) -> None:
    profile = load_packaged_profiles()["claude"]
    rules = harness.plugin_cache_read_rules(tmp_path / "plugins")
    run_dir = tmp_path / "run"
    argv = harness.render_argv(
        profile, prompt="PROMPT", model="claude-fable-5-1", session_id="sid", read_rules=rules, run_dir=run_dir
    )
    settings = _settings(argv)
    allow = settings["permissions"]["allow"]
    assert set(rules) <= set(allow) and set(harness.ORCHESTRATOR_TOOLS) <= set(allow)
    assert f"Write(/{run_dir}/**)" in allow and "Write" not in allow and "Bash" not in allow
    assert set(harness.DENIED_TOOLS) <= set(settings["permissions"]["deny"])
    assert argv[argv.index("--permission-mode") + 1] == "default" and "bypassPermissions" not in argv
    assert all(rule.startswith("Read(//") and "/cache/egm/egm/*/" in rule for rule in rules)
    assert argv[-1] == "PROMPT" and "sid" in argv
    assert "--model" in argv and "{model_args}" not in argv


def test_an_unrenderable_settings_value_is_an_error() -> None:
    with pytest.raises(harness.ChallengeHarnessError):
        harness.widen_settings("{not json", [])


# --- 113.10: no house context, checked at runtime ------------------------------------------------


def test_the_session_runs_with_every_hook_off(tmp_path: Path) -> None:
    """AC1: user-, project- and plugin-scope hooks never run in the challenge session."""
    _argv, settings = _render(tmp_path)
    assert settings["disableAllHooks"] is True
    assert json.loads(harness.widen_settings('{"disableAllHooks":false}', []))["disableAllHooks"] is True


def test_the_session_denies_reading_the_house_context(tmp_path: Path) -> None:
    """AC2: Read denies on the instruction files, memlogs and team memory; no instructionFiles config."""
    root = tmp_path / "repo"
    argv, settings = _render(tmp_path, target=root / "docs" / "dreams" / "x.md")
    assert harness.FORBIDDEN_READ_GLOBS == (
        "AGENTS.md",
        "*/**/AGENTS.md",
        "CLAUDE.md",
        "*/**/CLAUDE.md",
        "**/.memlog.md",
        ".claude/memory/**",
    )
    expected = [
        f"Read(/{root}/AGENTS.md)",
        f"Read(/{root}/*/**/AGENTS.md)",
        f"Read(/{root}/CLAUDE.md)",
        f"Read(/{root}/*/**/CLAUDE.md)",
        f"Read(/{root}/**/.memlog.md)",
        f"Read(/{root}/.claude/memory/**)",
    ]
    assert harness.forbidden_read_rules(root, root / "docs" / "dreams" / "x.md") == expected
    assert settings["permissions"]["deny"][-len(expected) :] == expected
    assert all(rule.startswith("Read(//") for rule in expected)
    assert "pluginConfigs" not in settings and "instructionFiles" not in argv[argv.index("--settings") + 1]


def test_only_the_instruction_files_plugin_config_is_dropped() -> None:
    profile_settings = {
        "pluginConfigs": {
            "agents-md@builtin": {"options": {"instructionFiles": "claude-md-and-agents-md"}},
            "other@market": {"options": {"level": 2}},
        }
    }
    widened = json.loads(harness.widen_settings(json.dumps(profile_settings), []))
    assert widened["pluginConfigs"] == {"other@market": {"options": {"level": 2}}}


@pytest.mark.parametrize(
    ("target", "excepted"),
    [
        ("AGENTS.md", "AGENTS.md"),
        ("CLAUDE.md", "CLAUDE.md"),
        ("src/shared/packages/pyforge-atlas/AGENTS.md", "*/**/AGENTS.md"),
        ("docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md", None),
    ],
)
def test_the_target_is_excepted_from_the_read_denies(target: str, excepted: str | None, tmp_path: Path) -> None:
    """AC2: a rules-stage target that is an instruction file stays readable; its siblings stay denied."""
    root = tmp_path / "repo"
    rules = harness.forbidden_read_rules(root, root / target)
    every = [f"Read(/{root / glob})" for glob in harness.FORBIDDEN_READ_GLOBS]
    assert rules == [rule for rule in every if excepted is None or rule != f"Read(/{root / excepted})"]
    _argv, settings = _render(tmp_path, target=root / target)
    # after the tools comes the run folder's slices/ Write deny (Story 113.14), then the read denies
    assert settings["permissions"]["deny"][len(harness.DENIED_TOOLS) + 1 :] == rules


def test_a_target_outside_the_repo_keeps_every_read_deny(tmp_path: Path) -> None:
    rules = harness.forbidden_read_rules(tmp_path / "repo", tmp_path / "elsewhere" / "AGENTS.md")
    assert len(rules) == len(harness.FORBIDDEN_READ_GLOBS)


@pytest.mark.parametrize(
    ("path", "forbidden"),
    [
        ("AGENTS.md", True),
        ("CLAUDE.md", True),
        ("src/shared/packages/pyforge-atlas/AGENTS.md", True),
        ("archive/x/CLAUDE.md", True),
        ("_bmad-output/projects/p/planning-artifacts/specs/spec-p/.memlog.md", True),
        (".claude/memory/MEMORY.md", True),
        (".claude/memory/feedback/x.md", True),
        ("_bmad-output/projects/p/planning-artifacts/specs/spec-p/SPEC.md", False),
        ("docs/dreams/pyforge-marshal.md", False),
        ("docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md", False),
        (".claude/skills/bmad-build-auto/spec-template.md", False),
    ],
)
def test_the_globs_cover_the_house_context_and_not_the_context(path: str, forbidden: bool) -> None:
    """The deny globs read as gitignore-style patterns: ``*/**/`` is one directory deep or more."""
    assert any(PurePosixPath(path).full_match(glob) for glob in harness.FORBIDDEN_READ_GLOBS) is forbidden


def test_the_guards_stay_with_hooks_off(tmp_path: Path) -> None:
    """AC3: Bash, Edit and Write stay denied except the one run-folder Write rule."""
    argv, settings = _render(tmp_path)
    assert harness.DENIED_TOOLS == ("Bash", "Edit", "MultiEdit", "NotebookEdit", "WebFetch", "WebSearch")
    deny, allow = settings["permissions"]["deny"], settings["permissions"]["allow"]
    assert deny[: len(harness.DENIED_TOOLS)] == list(harness.DENIED_TOOLS)
    assert [rule for rule in allow if rule.startswith(("Write", "Edit", "Bash"))] == [f"Write(/{tmp_path / 'run'}/**)"]
    assert [rule for rule in allow if "(" not in rule] == list(harness.ORCHESTRATOR_TOOLS)
    assert argv[argv.index("--permission-mode") + 1] == "default" and settings["disableAllHooks"] is True


def test_the_session_settings_enable_the_plugin_in_their_own_scope(tmp_path: Path) -> None:
    """AC4: ``egm@egm`` is enabled in the challenge --settings, the scope a session outside the repo uses."""
    _argv, settings = _render(tmp_path)
    assert settings["enabledPlugins"] == {core.EGM_PLUGIN_ID: True}
    assert harness.session_settings(tmp_path / "plugins")["enabledPlugins"] == {core.EGM_PLUGIN_ID: True}


def test_a_profile_without_settings_still_gets_the_guards(tmp_path: Path) -> None:
    profile = load_packaged_profiles()["claude"]
    bare = dataclasses.replace(profile, argv=tuple(t for t in profile.argv if not t.startswith(("--settings", '{"'))))
    argv, settings = _render(tmp_path, profile=bare)
    assert argv.count("--settings") == 1 and argv[-1] == "PROMPT"
    assert settings["disableAllHooks"] is True and settings["enabledPlugins"] == {core.EGM_PLUGIN_ID: True}
    assert set(harness.DENIED_TOOLS) <= set(settings["permissions"]["deny"])


class _FakeProcess:
    calls: list[dict] = []
    error: Exception | None = None

    def run(self, argv, *, cwd, timeout_s=None, env=None):
        _FakeProcess.calls.append({"argv": argv, "cwd": cwd, "timeout_s": timeout_s, "env": env})
        if _FakeProcess.error is not None:
            raise _FakeProcess.error
        return ProcessResult(returncode=3, stdout="out\n", stderr="err\n")


@pytest.fixture
def fake_process(monkeypatch: pytest.MonkeyPatch):
    _FakeProcess.calls = []
    _FakeProcess.error = None
    monkeypatch.setattr(harness, "PosixProcess", _FakeProcess)
    monkeypatch.setattr(harness.shutil, "which", lambda binary: f"/usr/bin/{binary}")
    return _FakeProcess


def test_runner_launches_the_claude_binary_and_logs_its_output(fake_process, tmp_path: Path) -> None:
    runner = harness.ClaudeChallengeRunner(plugins_root=tmp_path / "plugins")
    log = tmp_path / "run" / "session.log"
    code = runner.run(prompt="P", model="claude-fable-5-1", root=tmp_path, target=None, log_path=log, timeout_s=12)
    assert code == 3 and log.read_text(encoding="utf-8") == "out\nerr\n"
    (call,) = fake_process.calls
    assert call["argv"][0] == "/usr/bin/claude" and call["argv"][-1] == "P" and call["timeout_s"] == 12
    settings = json.loads(call["argv"][call["argv"].index("--settings") + 1])
    assert f"Write(/{log.parent}/**)" in settings["permissions"]["allow"]


def test_runner_launches_from_a_directory_outside_the_repo(
    fake_process, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC4: the session's cwd is a fresh temp dir outside the repo (no CLAUDE.md, AGENTS.md or git
    status is discovered from it), the Read denies are anchored at the repo, and the env never asks
    Claude Code to load CLAUDE.md from additional directories."""
    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.setenv(harness.ADDITIONAL_DIRS_CLAUDE_MD_ENV, "1")
    runner = harness.ClaudeChallengeRunner(plugins_root=tmp_path / "plugins")
    runner.run(
        prompt="P", model=None, root=root, target=root / "AGENTS.md", log_path=tmp_path / "run" / "log", timeout_s=60
    )
    (call,) = fake_process.calls
    cwd = Path(call["cwd"])
    assert not cwd.resolve().is_relative_to(root.resolve()) and cwd.name.startswith("marshal-egm-")
    assert not cwd.exists()  # removed once the session ends
    assert harness.ADDITIONAL_DIRS_CLAUDE_MD_ENV not in call["env"]
    deny = json.loads(call["argv"][call["argv"].index("--settings") + 1])["permissions"]["deny"]
    assert f"Read(/{root}/AGENTS.md)" not in deny and f"Read(/{root}/CLAUDE.md)" in deny


def test_runner_refuses_a_session_directory_inside_the_repo(
    fake_process, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repo"
    (root / "tmp").mkdir(parents=True)
    monkeypatch.setattr(tempfile, "tempdir", str(root / "tmp"))
    runner = harness.ClaudeChallengeRunner(plugins_root=tmp_path / "plugins")
    with pytest.raises(harness.ChallengeHarnessError, match="inside"):
        runner.run(prompt="P", model=None, root=root, target=None, log_path=tmp_path / "run" / "log", timeout_s=60)
    assert fake_process.calls == []


def test_runner_reports_a_session_that_does_not_complete(fake_process, tmp_path: Path) -> None:
    fake_process.error = ProcessError("timed out")
    runner = harness.ClaudeChallengeRunner(plugins_root=tmp_path)
    log = tmp_path / "session.log"
    with pytest.raises(harness.ChallengeHarnessError):
        runner.run(prompt="P", model=None, root=tmp_path, target=None, log_path=log, timeout_s=60)
    assert "did not complete" in log.read_text(encoding="utf-8")


def test_runner_refuses_a_missing_binary_or_profile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    runner = harness.ClaudeChallengeRunner(plugins_root=tmp_path)
    monkeypatch.setattr(harness.shutil, "which", lambda binary: None)
    monkeypatch.setattr(harness, "_resolve_binary", lambda profile: None)
    with pytest.raises(harness.ChallengeHarnessError, match="not on PATH"):
        runner.run(prompt="P", model=None, root=tmp_path, target=None, log_path=tmp_path / "log", timeout_s=60)
    monkeypatch.setattr(harness, "load_packaged_profiles", lambda: {})
    with pytest.raises(harness.ChallengeHarnessError, match="no packaged"):
        runner.run(prompt="P", model=None, root=tmp_path, target=None, log_path=tmp_path / "log", timeout_s=60)


def test_binary_resolution_falls_back_to_the_profile_dirs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    profile = load_packaged_profiles()["claude"]
    binary = tmp_path / profile.binary
    binary.write_text("#!/bin/sh\n", encoding="utf-8")
    binary.chmod(0o755)
    monkeypatch.setattr(harness.shutil, "which", lambda name: None)
    patched = dataclasses.replace(profile, fallback_bin_dirs=(str(tmp_path),))
    assert harness._resolve_binary(patched) == str(binary)
    assert harness._resolve_binary(dataclasses.replace(profile, fallback_bin_dirs=())) is None


def test_claude_version_reads_the_profile_binary_through_the_process_seam(monkeypatch: pytest.MonkeyPatch) -> None:
    """Story 113.11 (CAP-298): ``claude --version`` runs through ``PosixProcess`` (stubbed here, never the real
    binary); a non-zero exit, a launch failure, a missing binary or a missing profile read as ``None``."""
    calls: list[list[str]] = []
    outcome: list[object] = [ProcessResult(returncode=0, stdout="2.1.271 (Claude Code)\n", stderr="")]

    class _Version:
        def run(self, argv, *, cwd, timeout_s=None, env=None):
            calls.append(list(argv))
            if isinstance(outcome[0], Exception):
                raise outcome[0]
            return outcome[0]

    monkeypatch.setattr(harness, "PosixProcess", _Version)
    monkeypatch.setattr(harness, "_resolve_binary", lambda profile: "/opt/bin/claude")
    assert harness.claude_version() == "2.1.271 (Claude Code)\n"
    assert calls == [["/opt/bin/claude", "--version"]]
    outcome[0] = ProcessResult(returncode=1, stdout="2.1.271 (Claude Code)\n", stderr="")
    assert harness.claude_version() is None
    outcome[0] = ProcessError("timed out")
    assert harness.claude_version() is None
    monkeypatch.setattr(harness, "_resolve_binary", lambda profile: None)
    assert harness.claude_version() is None
    monkeypatch.setattr(harness, "load_packaged_profiles", lambda: {})
    assert harness.claude_version() is None
    assert len(calls) == 3


# --- 113.10: plugin_refusal checks the session's own scope; run_one hands the runner the target -----


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _plugins(tmp_path: Path, version: str = "0.1.0") -> Path:
    plugins = tmp_path / "plugins"
    _write(plugins / "installed_plugins.json", json.dumps({"plugins": {core.EGM_PLUGIN_ID: [{"version": version}]}}))
    cache = plugins / "cache" / core.EGM_MARKETPLACE / "egm" / version / ".claude-plugin"
    _write(cache / "plugin.json", json.dumps({"version": version}))
    for persona, filename in core.ADAPTER_FILES.items():
        adapter = f"---\nname: egm-{persona}\ntools: [Read, Grep, Glob]\nomitClaudeMd: true\n---\n"
        _write(cache / "agents" / filename, adapter)
    return plugins


def test_plugin_refusal_checks_the_session_settings_scope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AC4: the plugin must be enabled in the scope the session uses -- its own --settings."""
    plugins = _plugins(tmp_path)
    personas = tuple(core.ADAPTER_FILES)
    monkeypatch.setattr(harness, "claude_version", lambda: "2.1.271 (Claude Code)\n")  # Story 113.11: no shell-out
    assert cli.plugin_refusal(plugins, "0.1.0", personas) is None
    monkeypatch.setattr(harness, "session_settings", lambda root: {"enabledPlugins": {}})
    assert "not enabled in the challenge session's --settings" in (cli.plugin_refusal(plugins, "0.1.0") or "")

    def _boom(root: Path) -> dict:
        raise harness.ChallengeHarnessError("no packaged 'claude' harness profile")

    monkeypatch.setattr(harness, "session_settings", _boom)
    assert "cannot render" in (cli.plugin_refusal(plugins, "0.1.0") or "")


class _RecordingRunner:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.timeouts: list[float] = []

    def run(
        self, *, prompt: str, model: str | None, root: Path, target: Path | None, log_path: Path, timeout_s: float
    ) -> int:
        self.calls.append({"root": root, "target": target})
        self.timeouts.append(timeout_s)
        return 1


def test_run_one_hands_the_runner_the_repo_and_the_target(tmp_path: Path) -> None:
    """A rules-stage review of AGENTS.md reaches the runner as its target, so its Read deny is left out."""
    root = tmp_path / "repo"
    for relpath in ("AGENTS.md", cli.CHAIN_STANDARD_RELPATH, "docs/dreams/d.md"):
        _write(root / relpath, "x\n")
    runner = _RecordingRunner()
    outcome = cli.run_one(
        root=root,
        slug="pyforge-marshal",
        stage="rules",
        target=root / "AGENTS.md",
        config=core.ChallengeConfig(enabled=True, stages=("rules",)),
        runner=runner,
        out_dir=tmp_path / "out",
        dream=root / "docs/dreams/d.md",
    )
    assert outcome.report is None and "exited 1" in outcome.error
    (call,) = runner.calls
    assert call == {"root": root, "target": root / "AGENTS.md"}
    assert f"Read(/{root}/AGENTS.md)" not in harness.forbidden_read_rules(call["root"], call["target"])


# --- 113.14: every session has a ceiling, and the ceiling is configuration ------------------------------


def test_no_literal_ceiling_remains_in_the_harness() -> None:
    """AC1: the session's ceiling comes from the stage, never a constant in the adapter."""
    assert "3600" not in Path(harness.__file__).read_text(encoding="utf-8")
    assert core.DEFAULT_TIMEOUT_S == {
        "mint": 3600.0,
        "decompose": 3600.0,
        "readiness": 600.0,
        "drift": 3600.0,
        "rules": 3600.0,
    }
    assert set(core.DEFAULT_TIMEOUT_S) == set(core.STAGES)


@pytest.mark.parametrize(
    ("block_timeouts", "expected"),
    [
        ({}, {stage: core.DEFAULT_TIMEOUT_S[stage] for stage in core.STAGES}),
        ({"mint": 42, "readiness": 7.5}, {**core.DEFAULT_TIMEOUT_S, "mint": 42.0, "readiness": 7.5}),
    ],
    ids=["the-stage-defaults", "the-block-values"],
)
def test_run_one_hands_the_runner_the_stage_s_ceiling(block_timeouts: dict, expected: dict, tmp_path: Path) -> None:
    """AC1: the runner's timeout for a stage is the block's ``timeout_s`` value, else the per-stage default."""
    root = tmp_path / "repo"
    for relpath in (
        "AGENTS.md",
        cli.CHAIN_STANDARD_RELPATH,
        cli.SPEC_TEMPLATE_RELPATH,
        cli.STORY_SPEC_TEMPLATE_RELPATH,
        "docs/dreams/d.md",
    ):
        _write(root / relpath, "x\n")
    _write(cli.spec_path(root, "pyforge-marshal"), "x\n")
    block = core.valid_challenge_block({"enabled": True, "stages": list(core.STAGES), "timeout_s": block_timeouts})
    config = core.config_from_block(block)
    runner = _RecordingRunner()
    for stage in core.STAGES:
        cli.run_one(
            root=root,
            slug="pyforge-marshal",
            stage=stage,
            target=root / "AGENTS.md",
            config=config,
            runner=runner,
            out_dir=tmp_path / "out" / stage,
            dream=root / "docs/dreams/d.md",
        )
    assert dict(zip(core.STAGES, runner.timeouts, strict=True)) == expected
    (run_dir,) = (tmp_path / "out" / "readiness").iterdir()
    intent = json.loads((run_dir / cli.JOURNAL_FILENAME).read_text(encoding="utf-8").splitlines()[0])
    assert intent["payload"]["timeout_s"] == expected["readiness"]


def test_a_session_past_its_ceiling_is_a_timeout(fake_process, tmp_path: Path) -> None:
    """AC2: a timed-out session raises ``ChallengeTimeout`` naming the ceiling; another failure stays generic."""
    fake_process.error = ProcessError("command timed out")
    fake_process.error.__cause__ = subprocess.TimeoutExpired(["claude"], 5)
    runner = harness.ClaudeChallengeRunner(plugins_root=tmp_path)
    log = tmp_path / "session.log"
    with pytest.raises(harness.ChallengeTimeout, match="outlived its 5 s ceiling"):
        runner.run(prompt="P", model=None, root=tmp_path / "repo", target=None, log_path=log, timeout_s=5)
    assert "outlived its 5 s ceiling and was killed" in log.read_text(encoding="utf-8")
    assert fake_process.calls[0]["timeout_s"] == 5
    fake_process.error = ProcessError("cannot launch")
    with pytest.raises(harness.ChallengeHarnessError) as raised:
        runner.run(prompt="P", model=None, root=tmp_path / "repo", target=None, log_path=log, timeout_s=5)
    assert not isinstance(raised.value, harness.ChallengeTimeout)


def test_a_real_session_past_its_ceiling_is_killed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AC2: a session binary that would run for 30 s is killed at its 1.5 s ceiling, not waited on."""
    pidfile = tmp_path / "claude.pid"
    binary = tmp_path / "bin" / "claude"
    _write(binary, f"#!/bin/sh\necho $$ > {pidfile}\nexec sleep 30\n")
    binary.chmod(0o755)
    monkeypatch.setattr(harness, "_resolve_binary", lambda profile: str(binary))
    runner = harness.ClaudeChallengeRunner(plugins_root=tmp_path / "plugins")
    started = time.monotonic()
    with pytest.raises(harness.ChallengeTimeout):
        runner.run(
            prompt="P",
            model=None,
            root=tmp_path / "repo",
            target=None,
            log_path=tmp_path / "run" / "log",
            timeout_s=1.5,
        )
    assert time.monotonic() - started < 20
    with pytest.raises(ProcessLookupError):
        os.kill(int(pidfile.read_text(encoding="utf-8")), 0)


def test_the_session_may_not_rewrite_its_slices(fake_process, tmp_path: Path) -> None:
    """Story 113.14 review A: the run folder's ``slices/`` holds the target and Dream the reviewers read; the session's
    one ``Write`` allow covers the run folder, and a ``Write`` deny on ``slices/`` (deny wins over allow in Claude
    Code's permission rules) keeps the reviewed slice out of the session's reach."""
    run_dir = tmp_path / "run"
    _argv, settings = _render(tmp_path)
    deny, allow = settings["permissions"]["deny"], settings["permissions"]["allow"]
    assert f"Write(/{run_dir}/**)" in allow
    assert (
        deny[len(harness.DENIED_TOOLS)]
        == f"Write(/{run_dir}/{core.SLICES_DIRNAME}/**)"
        == f"Write(/{run_dir}/slices/**)"
    )
    bare = json.loads(harness.widen_settings("", []))  # no run folder: no Write allow, no slices deny
    assert not [rule for rule in bare["permissions"]["deny"] if rule.startswith("Write(")]
    runner = harness.ClaudeChallengeRunner(plugins_root=tmp_path / "plugins")
    log = tmp_path / "adhoc-run" / "session.log"
    runner.run(prompt="P", model=None, root=tmp_path / "repo", target=None, log_path=log, timeout_s=60)
    (call,) = fake_process.calls
    rendered = json.loads(call["argv"][call["argv"].index("--settings") + 1])["permissions"]
    assert f"Write(/{log.parent}/slices/**)" in rendered["deny"] and f"Write(/{log.parent}/**)" in rendered["allow"]
