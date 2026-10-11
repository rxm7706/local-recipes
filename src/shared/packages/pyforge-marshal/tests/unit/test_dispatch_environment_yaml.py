"""Story 91.1: pre-verify ``environment.yaml`` regeneration and cross-surface gate."""

from __future__ import annotations

from pathlib import Path

import pytest
from pyforge.core.process import ProcessResult

from pyforge.marshal.core import gate
from pyforge.marshal.core.dispatch_environment_yaml import (
    DispatchEnvironmentYamlResult,
    apply_dispatch_environment_yaml_before_verify,
    changed_files_trigger_environment_yaml_regeneration,
    export_stdout_differs_from_file,
)
from pyforge.marshal.core.identity import normalize
from pyforge.marshal.core.policy import compose
from pyforge.marshal.dispatch_supervisor import __main__ as supervisor_main
from pyforge.marshal.dispatch_verify import evaluate_dispatch_verification
from pyforge.marshal.dispatch_verification import (
    DispatchVerificationInput,
    DispatchVerificationVerdict,
    judge_dispatch_verification,
)

_ENV_PATH = "environment.yaml"
_PIXI_PATH = "pixi.toml"
_CLEAN_EXPORT = "name: build\ndependencies:\n  - python\n"
_WARN = (
    "\x1b[33m WARN\x1b[0m Using local manifest /wt/pixi.toml rather than "
    "/primary/pixi.toml from environment variable `PIXI_PROJECT_MANIFEST`\n"
)


def test_changed_files_trigger_environment_yaml_regeneration() -> None:
    assert changed_files_trigger_environment_yaml_regeneration((_ENV_PATH,))
    assert changed_files_trigger_environment_yaml_regeneration((_PIXI_PATH,))
    assert not changed_files_trigger_environment_yaml_regeneration(("README.md",))


def test_export_stdout_differs_from_file_uses_rstrip() -> None:
    assert not export_stdout_differs_from_file(export_stdout="a\n", file_text="a\n\n")
    assert export_stdout_differs_from_file(export_stdout="a\n", file_text="b\n")


class _EnvYamlVcs:
    def __init__(self, *, scope: tuple[str, ...]) -> None:
        self._scope = scope
        self.commits: list[tuple[Path, tuple[Path, ...], object]] = []

    def changed_files(self, repo_root: Path, worktree_path: Path, *, base: str) -> tuple[str, ...]:
        del repo_root, worktree_path, base
        return self._scope

    def commit_paths(self, repo_root: Path, paths: tuple[Path, ...], message: object) -> str:
        self.commits.append((repo_root, paths, message))
        return "abc123"


class _EnvYamlProcess:
    def __init__(self, *, stdout: str = _CLEAN_EXPORT, stderr: str = "", exit_code: int = 0) -> None:
        self._stdout = stdout
        self._stderr = stderr
        self._exit_code = exit_code
        self.calls: list[tuple[list[str], Path]] = []

    def run(self, tokens: list[str], *, cwd: Path) -> ProcessResult:
        self.calls.append((tokens, cwd))
        return ProcessResult(self._exit_code, self._stdout, self._stderr)


def test_apply_repairs_corrupt_environment_yaml_from_stdout_only(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    env_file = worktree / _ENV_PATH
    env_file.write_text(_WARN + _CLEAN_EXPORT, encoding="utf-8")

    vcs = _EnvYamlVcs(scope=(_ENV_PATH,))
    process = _EnvYamlProcess(stderr=_WARN)

    result = apply_dispatch_environment_yaml_before_verify(
        worktree=worktree,
        repo_root=tmp_path,
        vcs=vcs,
        process=process,
    )

    assert result == DispatchEnvironmentYamlResult((_ENV_PATH,), True, 0)
    assert env_file.read_text(encoding="utf-8") == _CLEAN_EXPORT
    assert _WARN not in env_file.read_text(encoding="utf-8")
    assert vcs.commits
    assert process.calls[0][0][:3] == ["pixi", "project", "export"]


def test_apply_regenerates_when_only_pixi_toml_changed(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    env_file = worktree / _ENV_PATH
    env_file.write_text(_WARN + _CLEAN_EXPORT, encoding="utf-8")

    vcs = _EnvYamlVcs(scope=(_PIXI_PATH,))
    process = _EnvYamlProcess()

    result = apply_dispatch_environment_yaml_before_verify(
        worktree=worktree,
        repo_root=tmp_path,
        vcs=vcs,
        process=process,
    )

    assert result.committed is True
    assert env_file.read_text(encoding="utf-8") == _CLEAN_EXPORT


def test_apply_skips_when_already_in_sync(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    (worktree / _ENV_PATH).write_text(_CLEAN_EXPORT, encoding="utf-8")

    vcs = _EnvYamlVcs(scope=(_ENV_PATH,))
    process = _EnvYamlProcess()

    result = apply_dispatch_environment_yaml_before_verify(
        worktree=worktree,
        repo_root=tmp_path,
        vcs=vcs,
        process=process,
    )

    assert result == DispatchEnvironmentYamlResult((), False, 0)
    assert not vcs.commits


def test_apply_skips_when_diff_touches_neither_path(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = _EnvYamlVcs(scope=("docs/readme.md",))
    process = _EnvYamlProcess()

    result = apply_dispatch_environment_yaml_before_verify(
        worktree=worktree,
        repo_root=tmp_path,
        vcs=vcs,
        process=process,
    )

    assert result == DispatchEnvironmentYamlResult((), False, None)
    assert not process.calls


def test_apply_export_failure_writes_nothing(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    env_file = worktree / _ENV_PATH
    corrupt = _WARN + _CLEAN_EXPORT
    env_file.write_text(corrupt, encoding="utf-8")

    vcs = _EnvYamlVcs(scope=(_ENV_PATH,))
    process = _EnvYamlProcess(exit_code=1)

    result = apply_dispatch_environment_yaml_before_verify(
        worktree=worktree,
        repo_root=tmp_path,
        vcs=vcs,
        process=process,
    )

    assert result.committed is False
    assert env_file.read_text(encoding="utf-8") == corrupt
    assert not vcs.commits


def test_cross_surface_rule_pins_environment_yaml_command() -> None:
    rule = gate.CROSS_SURFACE_RULES[-1]
    assert rule.rule_id == "environment-yaml"
    assert rule.command == "pixi run -e pyforge-guild steward provision --verify"
    assert gate.changed_files_touch_cross_surface_rule((_ENV_PATH,), rule)
    assert gate.changed_files_touch_cross_surface_rule((_PIXI_PATH,), rule)
    assert not gate.changed_files_touch_cross_surface_rule(("README.md",), rule)


class _FakeVcs:
    def __init__(self, *, changed: tuple[str, ...]) -> None:
        self._changed = changed

    def changed_files(self, repo_root: Path, worktree_path: Path, *, base: str) -> tuple[str, ...]:
        del repo_root, worktree_path, base
        return self._changed


class _CrossSurfaceEnvProcess:
    def __init__(self, *, provision_exit: int = 0, provision_stdout: str = "", provision_stderr: str = "") -> None:
        self._provision_exit = provision_exit
        self._provision_stdout = provision_stdout
        self._provision_stderr = provision_stderr
        self.provision_invocations = 0

    def run(self, tokens, *, cwd: Path):
        joined = " ".join(tokens)
        if "steward" in joined and "provision" in joined:
            self.provision_invocations += 1
            return ProcessResult(
                self._provision_exit,
                self._provision_stdout,
                self._provision_stderr,
            )
        if tokens and tokens[0] == "true":
            return ProcessResult(0, "ok", "")
        return ProcessResult(0, "ok", "")


_REPO_ROOT = Path("/repo")


def test_evaluate_dispatch_verification_environment_yaml_refusal_message(
    tmp_path: Path,
) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    story_key = normalize("91-1-a-corrupt-environment-yaml-never-lands")
    effective, _ = compose(
        project_slug="pyforge-marshal",
        project={"verify_commands": ["true"]},
        flags={},
    )
    stderr = "environment.yaml drift detected"
    process = _CrossSurfaceEnvProcess(provision_exit=1, provision_stderr=stderr)
    envelope = evaluate_dispatch_verification(
        project_slug="pyforge-marshal",
        story_key=story_key,
        worktree=worktree,
        repo_root=_REPO_ROOT,
        effective=effective,
        spec_text=None,
        process=process,
        vcs=_FakeVcs(changed=(_ENV_PATH,)),
    )
    assert process.provision_invocations == 1
    gate015 = [f for f in envelope.findings if f.code == gate.CROSS_SURFACE_GATE_CODE]
    assert len(gate015) == 1
    assert "environment.yaml" in gate015[0].message
    assert gate.ENVIRONMENT_YAML_FIX_COMMAND in gate015[0].message
    checks = envelope.data["cross_surface_checks"]
    assert any(entry["rule_id"] == "environment-yaml" for entry in checks)
    assert (
        judge_dispatch_verification(DispatchVerificationInput(findings=envelope.findings))
        == DispatchVerificationVerdict.REFUSED
    )


def test_evaluate_dispatch_verification_pixi_toml_triggers_environment_yaml_rule(
    tmp_path: Path,
) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    story_key = normalize("91-1-a-corrupt-environment-yaml-never-lands")
    effective, _ = compose(
        project_slug="pyforge-marshal",
        project={"verify_commands": ["true"]},
        flags={},
    )
    process = _CrossSurfaceEnvProcess()
    envelope = evaluate_dispatch_verification(
        project_slug="pyforge-marshal",
        story_key=story_key,
        worktree=worktree,
        repo_root=_REPO_ROOT,
        effective=effective,
        spec_text=None,
        process=process,
        vcs=_FakeVcs(changed=(_PIXI_PATH,)),
    )
    assert process.provision_invocations == 1
    assert envelope.data["cross_surface_check"]["checked"] is True


def test_verification_journals_environment_yaml_when_committed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib

    from pyforge.marshal.core.dispatch_ruff_format import DispatchRuffFormatResult

    loop_tests = importlib.import_module("test_dispatch_supervisor_main_loop")

    repo_root = loop_tests._repo(tmp_path)
    worktree = loop_tests._worktree(repo_root)
    loop_tests._seed_spec(repo_root, worktree, primary=loop_tests._READY_SPEC_TEXT)
    loop_tests._patch_verification(monkeypatch, loop_tests._clean_envelope)
    monkeypatch.setattr(
        supervisor_main,
        "run_dispatch_ruff_format_before_verify",
        lambda **_: DispatchRuffFormatResult((), False),
    )
    monkeypatch.setattr(
        supervisor_main,
        "run_dispatch_environment_yaml_before_verify",
        lambda **_: DispatchEnvironmentYamlResult((_ENV_PATH,), True, 0),
    )
    fs = loop_tests.FakeFs()

    counter = loop_tests._verify(fs, repo_root, worktree)

    assert counter == 4
    assert any("dispatch-environment-yaml" in line for _, line, _ in fs.appended)


def test_matrix_neither_path_skips_exporter_and_rule(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = _EnvYamlVcs(scope=("src/shared/packages/pyforge-marshal/foo.py",))
    process = _EnvYamlProcess()
    assert apply_dispatch_environment_yaml_before_verify(
        worktree=worktree,
        repo_root=tmp_path,
        vcs=vcs,
        process=process,
    ).export_exit_code is None

    story_key = normalize("91-1-a-corrupt-environment-yaml-never-lands")
    effective, _ = compose(
        project_slug="pyforge-marshal",
        project={"verify_commands": ["true"]},
        flags={},
    )
    proc = _CrossSurfaceEnvProcess()
    envelope = evaluate_dispatch_verification(
        project_slug="pyforge-marshal",
        story_key=story_key,
        worktree=worktree,
        repo_root=_REPO_ROOT,
        effective=effective,
        spec_text=None,
        process=proc,
        vcs=_FakeVcs(changed=("src/shared/packages/pyforge-marshal/foo.py",)),
    )
    assert proc.provision_invocations == 0
    assert envelope.data["cross_surface_check"]["checked"] is False
