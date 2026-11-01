"""Story 113.1 (CAP-298): the challenge session's argv comes from the packaged claude profile."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest
from pyforge.core.process import ProcessError, ProcessResult

from pyforge.marshal.adapters import challenge_harness as harness
from pyforge.marshal.core.harness_profile import load_packaged_profiles


def test_argv_widens_the_profile_settings_with_plugin_cache_read_rules(tmp_path: Path) -> None:
    profile = load_packaged_profiles()["claude"]
    rules = harness.plugin_cache_read_rules(tmp_path / "plugins")
    run_dir = tmp_path / "run"
    argv = harness.render_argv(
        profile, prompt="PROMPT", model="claude-fable-5-1", session_id="sid", read_rules=rules, run_dir=run_dir
    )
    settings = json.loads(argv[argv.index("--settings") + 1])
    assert settings["pluginConfigs"]  # the profile's own settings survive
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


class _FakeProcess:
    calls: list[dict] = []
    error: Exception | None = None

    def run(self, argv, *, cwd, timeout_s=None, env=None):
        _FakeProcess.calls.append({"argv": argv, "cwd": cwd, "timeout_s": timeout_s})
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
    runner = harness.ClaudeChallengeRunner(plugins_root=tmp_path / "plugins", timeout_s=12)
    log = tmp_path / "run" / "session.log"
    code = runner.run(prompt="P", model="claude-fable-5-1", cwd=tmp_path, log_path=log)
    assert code == 3 and log.read_text(encoding="utf-8") == "out\nerr\n"
    (call,) = fake_process.calls
    assert call["argv"][0] == "/usr/bin/claude" and call["argv"][-1] == "P" and call["timeout_s"] == 12
    settings = json.loads(call["argv"][call["argv"].index("--settings") + 1])
    assert f"Write(/{log.parent}/**)" in settings["permissions"]["allow"]


def test_runner_reports_a_session_that_does_not_complete(fake_process, tmp_path: Path) -> None:
    fake_process.error = ProcessError("timed out")
    runner = harness.ClaudeChallengeRunner(plugins_root=tmp_path)
    log = tmp_path / "session.log"
    with pytest.raises(harness.ChallengeHarnessError):
        runner.run(prompt="P", model=None, cwd=tmp_path, log_path=log)
    assert "did not complete" in log.read_text(encoding="utf-8")


def test_runner_refuses_a_missing_binary_or_profile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    runner = harness.ClaudeChallengeRunner(plugins_root=tmp_path)
    monkeypatch.setattr(harness.shutil, "which", lambda binary: None)
    monkeypatch.setattr(harness, "_resolve_binary", lambda profile: None)
    with pytest.raises(harness.ChallengeHarnessError, match="not on PATH"):
        runner.run(prompt="P", model=None, cwd=tmp_path, log_path=tmp_path / "log")
    monkeypatch.setattr(harness, "load_packaged_profiles", lambda: {})
    with pytest.raises(harness.ChallengeHarnessError, match="no packaged"):
        runner.run(prompt="P", model=None, cwd=tmp_path, log_path=tmp_path / "log")


def test_binary_resolution_falls_back_to_the_profile_dirs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    profile = load_packaged_profiles()["claude"]
    binary = tmp_path / profile.binary
    binary.write_text("#!/bin/sh\n", encoding="utf-8")
    binary.chmod(0o755)
    monkeypatch.setattr(harness.shutil, "which", lambda name: None)
    patched = dataclasses.replace(profile, fallback_bin_dirs=(str(tmp_path),))
    assert harness._resolve_binary(patched) == str(binary)
    assert harness._resolve_binary(dataclasses.replace(profile, fallback_bin_dirs=())) is None
