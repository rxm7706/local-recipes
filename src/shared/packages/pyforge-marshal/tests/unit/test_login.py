"""Story 33.12 CAP-5 — ``pyforge login`` local-profile bearer writer."""

from __future__ import annotations

import argparse
import stat
import sys
from pathlib import Path

import pytest
from pyforge.core.process import PosixProcess, ProcessError, ProcessResult

from pyforge.marshal.cli import login as login_mod


def test_login_writes_bearer_file_mode_0600(tmp_path, monkeypatch, capsys):
    repo = tmp_path / "repo"
    (repo / "src" / "platform" / "config" / "local_dev").mkdir(parents=True)
    (repo / "src" / "platform" / "config" / "local_dev" / "mint.py").write_text(
        "def main(argv): return 'tok'\n",
        encoding="utf-8",
    )
    bearer = tmp_path / "secret" / "bearer"
    monkeypatch.chdir(repo)

    def _fake_mint(_repo: Path, persona: str) -> str:
        assert persona == "marshal-operator"
        return "local-dev-token"

    monkeypatch.setattr(login_mod, "_mint_local_token", _fake_mint)
    args = argparse.Namespace(
        persona="marshal-operator",
        bearer_file=str(bearer),
        pkce=False,
        issuer=None,
        client_id="pyforge-cli",
    )
    assert login_mod.run_login(args) == login_mod.EXIT_OK
    out = capsys.readouterr().out.strip()
    assert out == str(bearer)
    assert bearer.read_text(encoding="utf-8") == "local-dev-token\n"
    assert stat.S_IMODE(bearer.stat().st_mode) == 0o600
    assert "local-dev-token" not in capsys.readouterr().err


def test_login_unknown_persona_nonzero_without_file(tmp_path, monkeypatch, capsys):
    repo = tmp_path / "repo"
    (repo / "src" / "platform" / "config" / "local_dev").mkdir(parents=True)
    (repo / "src" / "platform" / "config" / "local_dev" / "mint.py").write_text(
        "def main(argv): raise SystemExit('unknown persona')\n",
        encoding="utf-8",
    )
    bearer = tmp_path / "bearer"
    monkeypatch.chdir(repo)
    monkeypatch.setattr(
        login_mod,
        "_mint_local_token",
        lambda *_: (_ for _ in ()).throw(RuntimeError("unknown persona")),
    )
    args = argparse.Namespace(
        persona="missing",
        bearer_file=str(bearer),
        pkce=False,
        issuer=None,
        client_id="pyforge-cli",
    )
    assert login_mod.run_login(args) == login_mod.EXIT_USAGE
    assert not bearer.exists()


class _FakePkceLogin:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs

    def run(self) -> str:
        return "pkce-token"


def test_login_pkce_writes_bearer_without_persona(tmp_path, monkeypatch, capsys):
    bearer = tmp_path / "pkce-bearer"
    monkeypatch.setattr(login_mod, "PkceLogin", _FakePkceLogin)
    args = argparse.Namespace(
        persona=None,
        bearer_file=str(bearer),
        pkce=True,
        issuer="http://127.0.0.1:8080/realms/platform",
        client_id="pyforge-cli",
    )
    assert login_mod.run_login(args) == login_mod.EXIT_OK
    assert bearer.read_text(encoding="utf-8") == "pkce-token\n"
    assert capsys.readouterr().out.strip() == str(bearer)


def test_login_pkce_rejects_persona(capsys):
    args = argparse.Namespace(
        persona="marshal-operator",
        bearer_file=None,
        pkce=True,
        issuer="http://127.0.0.1:8080/realms/platform",
        client_id="pyforge-cli",
    )
    assert login_mod.run_login(args) == login_mod.EXIT_USAGE
    assert "persona cannot be used with --pkce" in capsys.readouterr().err


def test_login_pkce_requires_issuer(capsys):
    args = argparse.Namespace(
        persona=None,
        bearer_file=None,
        pkce=True,
        issuer=None,
        client_id="pyforge-cli",
    )
    assert login_mod.run_login(args) == login_mod.EXIT_USAGE
    assert "--issuer is required with --pkce" in capsys.readouterr().err


# --- _mint_local_token over the ONE sanctioned subprocess seam (Story 52.1,
# SPEC-pyforge-core CAP-6): fakes `PosixProcess.run` (the
# `test_harness_bmadloop_engine_liveness.py` convention), never `subprocess`.


def test_mint_local_token_returns_stdout_token_on_success(tmp_path, monkeypatch):
    calls: list[tuple[list[str], Path, float | None]] = []

    def _fake_run(self, argv, *, cwd, timeout_s=None):
        calls.append((list(argv), cwd, timeout_s))
        return ProcessResult(returncode=0, stdout="tok\n", stderr="")

    monkeypatch.setattr(PosixProcess, "run", _fake_run)
    assert login_mod._mint_local_token(tmp_path, "marshal-operator") == "tok"
    assert len(calls) == 1
    argv, cwd, timeout_s = calls[0]
    # The child is this interpreter running a `-c` script with the persona
    # as its single positional argument, from the repo root, no timeout.
    assert argv[0] == sys.executable
    assert argv[1] == "-c"
    assert argv[3] == "marshal-operator"
    assert cwd == tmp_path
    assert timeout_s is None
    # The former custom `env=` (PYTHONPATH=<repo_root>/src/platform) now
    # lives inside the child's own script as an explicit sys.path insert --
    # `PosixProcess.run` inherits os.environ exactly and takes no `env=`.
    script = argv[2]
    assert "sys.path.insert(0, " in script
    assert repr(str(tmp_path / login_mod._PLATFORM_SRC)) in script
    assert "from config.local_dev.mint import main" in script


def test_mint_local_token_executes_the_child_script_for_real(tmp_path):
    """No fake here: the rewritten `-c` script actually runs in a real child
    interpreter against a stub `src/platform` tree (a `config.local_dev.mint`
    package plus a `django` stub module beside it), proving the
    `sys.path.insert` really puts the platform dir on the child's import
    path -- the substring checks above cannot tell a malformed script from a
    working one."""
    platform = tmp_path / "src" / "platform"
    (platform / "config" / "local_dev").mkdir(parents=True)
    (platform / "config" / "__init__.py").write_text("", encoding="utf-8")
    (platform / "config" / "local_dev" / "__init__.py").write_text("", encoding="utf-8")
    (platform / "config" / "local_dev" / "mint.py").write_text(
        'def main(argv): return "tok-" + argv[0]\n', encoding="utf-8"
    )
    (platform / "django.py").write_text("def setup(): pass\n", encoding="utf-8")
    assert login_mod._mint_local_token(tmp_path, "marshal-operator") == "tok-marshal-operator"


def test_mint_local_token_platform_config_wins_over_inherited_pythonpath(tmp_path, monkeypatch):
    """Same real child, but the parent now carries a `PYTHONPATH` pointing
    at a DECOY tree with its own `config.local_dev.mint` returning
    `"decoy"`. `PosixProcess.run` inherits `os.environ` exactly, so that
    decoy reaches the child -- and the platform dir's `mint` must still win,
    because the script's `sys.path.insert(0, <platform src>)` precedes every
    inherited `PYTHONPATH` entry. This is the precedence guarantee the
    migration comment scopes to `config`."""
    repo = tmp_path / "repo"
    platform = repo / "src" / "platform"
    (platform / "config" / "local_dev").mkdir(parents=True)
    (platform / "config" / "__init__.py").write_text("", encoding="utf-8")
    (platform / "config" / "local_dev" / "__init__.py").write_text("", encoding="utf-8")
    (platform / "config" / "local_dev" / "mint.py").write_text(
        'def main(argv): return "tok-" + argv[0]\n', encoding="utf-8"
    )
    (platform / "django.py").write_text("def setup(): pass\n", encoding="utf-8")

    decoy = tmp_path / "decoy"
    (decoy / "config" / "local_dev").mkdir(parents=True)
    (decoy / "config" / "__init__.py").write_text("", encoding="utf-8")
    (decoy / "config" / "local_dev" / "__init__.py").write_text("", encoding="utf-8")
    (decoy / "config" / "local_dev" / "mint.py").write_text('def main(argv): return "decoy"\n', encoding="utf-8")
    (decoy / "django.py").write_text("def setup(): pass\n", encoding="utf-8")

    monkeypatch.setenv("PYTHONPATH", str(decoy))
    assert login_mod._mint_local_token(repo, "marshal-operator") == "tok-marshal-operator"


def test_mint_local_token_nonzero_exit_raises_runtime_error_with_stderr(tmp_path, monkeypatch):
    def _fake_run(self, argv, *, cwd, timeout_s=None):
        return ProcessResult(returncode=1, stdout="", stderr="boom\n")

    monkeypatch.setattr(PosixProcess, "run", _fake_run)
    with pytest.raises(RuntimeError, match=r"^boom$"):
        login_mod._mint_local_token(tmp_path, "marshal-operator")


def test_mint_local_token_launch_failure_maps_to_runtime_error(tmp_path, monkeypatch):
    """`PosixProcess.run` raising `ProcessError` (the interpreter could not
    be launched at all) surfaces as the same `RuntimeError` shape
    `run_login` already catches -- its message names the launch failure,
    and no raw `OSError` escapes."""

    def _boom(self, argv, *, cwd, timeout_s=None):
        raise ProcessError("cannot launch ['python']: permission denied")

    monkeypatch.setattr(PosixProcess, "run", _boom)
    with pytest.raises(RuntimeError, match="permission denied") as excinfo:
        login_mod._mint_local_token(tmp_path, "marshal-operator")
    assert isinstance(excinfo.value.__cause__, ProcessError)
    assert not isinstance(excinfo.value, OSError)


def test_mint_local_token_empty_stdout_raises_runtime_error(tmp_path, monkeypatch):
    def _fake_run(self, argv, *, cwd, timeout_s=None):
        return ProcessResult(returncode=0, stdout="\n", stderr="")

    monkeypatch.setattr(PosixProcess, "run", _fake_run)
    with pytest.raises(RuntimeError, match="empty bearer"):
        login_mod._mint_local_token(tmp_path, "marshal-operator")


def test_run_login_reports_launch_failure_as_usage_error(tmp_path, monkeypatch, capsys):
    """End to end through `run_login`: a launch failure inside the mint
    child never crashes the CLI -- EXIT_USAGE with the reason on stderr and
    no bearer file written, exactly the failed-mint path."""
    repo = tmp_path / "repo"
    (repo / "src" / "platform" / "config" / "local_dev").mkdir(parents=True)
    (repo / "src" / "platform" / "config" / "local_dev" / "mint.py").write_text(
        "def main(argv): return 'tok'\n", encoding="utf-8"
    )
    bearer = tmp_path / "bearer"
    monkeypatch.chdir(repo)

    def _boom(self, argv, *, cwd, timeout_s=None):
        raise ProcessError("executable not found: 'python'")

    monkeypatch.setattr(PosixProcess, "run", _boom)
    args = argparse.Namespace(
        persona="marshal-operator",
        bearer_file=str(bearer),
        pkce=False,
        issuer=None,
        client_id="pyforge-cli",
    )
    assert login_mod.run_login(args) == login_mod.EXIT_USAGE
    assert "executable not found" in capsys.readouterr().err
    assert not bearer.exists()
