"""Story 33.12 CAP-5 — ``pyforge login`` local-profile bearer writer."""

from __future__ import annotations

import argparse
import stat
from pathlib import Path

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
