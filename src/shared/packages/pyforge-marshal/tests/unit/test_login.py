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
    args = argparse.Namespace(persona="marshal-operator", bearer_file=str(bearer))
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
    )
    assert login_mod.run_login(args) == login_mod.EXIT_USAGE
    assert not bearer.exists()
