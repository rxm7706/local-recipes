"""scripts/scribe_pg.py keeps the server's Unix socket in a short per-user directory (Story 22.1).

A worktree's `var/scribe-pg/.s.PGSQL.5433` runs past the kernel's socket-path limit, so
the socket goes to `SCRIBE_PG_SOCKET_DIR`, else `$XDG_RUNTIME_DIR/scribe-pg`, else
`/tmp/scribe-pg-<uid>`. No test here starts a server.
"""

from __future__ import annotations

import importlib.util
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def _load():
    spec = importlib.util.spec_from_file_location(
        "scribe_pg", REPO / "scripts" / "scribe_pg.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["scribe_pg"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def scribe_pg(tmp_path, monkeypatch):
    module = _load()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "CLUSTER", tmp_path / "var" / "scribe-pg" / "data")
    monkeypatch.setattr(
        module, "LOGFILE", tmp_path / "var" / "scribe-pg" / "server.log"
    )
    monkeypatch.delenv("SCRIBE_PG_SOCKET_DIR", raising=False)
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    return module


def test_the_override_wins(scribe_pg, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "xdg"))
    monkeypatch.setenv("SCRIBE_PG_SOCKET_DIR", str(tmp_path / "sock"))
    assert scribe_pg._socket_dir() == tmp_path / "sock"


def test_xdg_runtime_dir_is_next(scribe_pg, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "xdg"))
    assert scribe_pg._socket_dir() == tmp_path / "xdg" / "scribe-pg"


def test_tmp_per_uid_is_the_fallback(scribe_pg) -> None:
    assert scribe_pg._socket_dir() == Path("/tmp") / f"scribe-pg-{os.getuid()}"


def test_the_socket_dir_is_created_0700(scribe_pg, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("SCRIBE_PG_SOCKET_DIR", str(tmp_path / "sock"))
    sock_dir = scribe_pg._prepare_socket_dir()
    assert sock_dir == tmp_path / "sock"
    assert stat.S_IMODE(sock_dir.stat().st_mode) == 0o700


def test_a_loose_existing_dir_is_tightened(scribe_pg, monkeypatch, tmp_path) -> None:
    loose = tmp_path / "sock"
    loose.mkdir(mode=0o755)
    loose.chmod(0o755)
    monkeypatch.setenv("SCRIBE_PG_SOCKET_DIR", str(loose))
    assert scribe_pg._prepare_socket_dir() == loose
    assert stat.S_IMODE(loose.stat().st_mode) == 0o700


def test_a_socket_path_over_the_limit_fails_loud(
    scribe_pg, monkeypatch, tmp_path, capsys
) -> None:
    too_long = tmp_path / ("x" * (scribe_pg.SOCKET_PATH_MAX + 1))
    monkeypatch.setenv("SCRIBE_PG_SOCKET_DIR", str(too_long))
    assert scribe_pg._prepare_socket_dir() is None
    err = capsys.readouterr().err
    assert (
        "SCRIBE_PG_SOCKET_DIR" in err and f"limit is {scribe_pg.SOCKET_PATH_MAX}" in err
    )
    assert not too_long.exists()


def test_the_limit_counts_the_socket_file_name(
    scribe_pg, monkeypatch, tmp_path
) -> None:
    """A directory that fits only because the `.s.PGSQL.<port>` suffix is ignored still fails."""
    suffix = len(f"/.s.PGSQL.{scribe_pg.PORT}")
    budget = scribe_pg.SOCKET_PATH_MAX - len(os.fsencode(tmp_path)) - 1
    just_over = tmp_path / ("y" * (budget - suffix + 1))
    monkeypatch.setenv("SCRIBE_PG_SOCKET_DIR", str(just_over))
    assert scribe_pg._prepare_socket_dir() is None
    just_fits = tmp_path / ("y" * (budget - suffix))
    monkeypatch.setenv("SCRIBE_PG_SOCKET_DIR", str(just_fits))
    assert scribe_pg._prepare_socket_dir() == just_fits


def test_a_symlinked_socket_dir_is_refused(
    scribe_pg, monkeypatch, tmp_path, capsys
) -> None:
    real = tmp_path / "real"
    real.mkdir(mode=0o700)
    link = tmp_path / "link"
    link.symlink_to(real)
    monkeypatch.setenv("SCRIBE_PG_SOCKET_DIR", str(link))
    assert scribe_pg._prepare_socket_dir() is None
    assert "not a directory you own" in capsys.readouterr().err


def _fake_run(calls: list[list[str]]):
    def run(args, **kw):
        calls.append(list(args))
        if args[:2] == ["pg_ctl", "--version"]:
            return subprocess.CompletedProcess(
                args, 0, "pg_ctl (PostgreSQL) 17.11\n", ""
            )
        if args[0] == "psql" and "-tAc" in args:
            return subprocess.CompletedProcess(args, 0, "1\n", "")
        return subprocess.CompletedProcess(args, 0, "", "")

    return run


def _present_cluster(module) -> None:
    module.CLUSTER.mkdir(parents=True)
    (module.CLUSTER / "PG_VERSION").write_text("17\n")


def test_up_starts_the_server_with_the_short_socket_dir(
    scribe_pg, monkeypatch, tmp_path
) -> None:
    _present_cluster(scribe_pg)
    monkeypatch.setenv("SCRIBE_PG_SOCKET_DIR", str(tmp_path / "sock"))
    monkeypatch.setattr(scribe_pg, "_need", lambda binary: binary)
    answers = iter([False, True])
    monkeypatch.setattr(scribe_pg, "_is_up", lambda: next(answers))
    calls: list[list[str]] = []
    monkeypatch.setattr(scribe_pg, "_run", _fake_run(calls))
    assert scribe_pg.up() == 0
    start = next(c for c in calls if c[0] == "pg_ctl" and "start" in c)
    options = start[start.index("-o") + 1]
    assert f"-k {tmp_path / 'sock'}" in options
    assert str(scribe_pg.CLUSTER.parent) not in options
    assert (scribe_pg.CLUSTER / "PG_VERSION").is_file()


def test_up_reuses_a_listening_cluster(scribe_pg, monkeypatch, tmp_path) -> None:
    _present_cluster(scribe_pg)
    monkeypatch.setenv("SCRIBE_PG_SOCKET_DIR", str(tmp_path / "sock"))
    monkeypatch.setattr(scribe_pg, "_need", lambda binary: binary)
    monkeypatch.setattr(scribe_pg, "_is_up", lambda: True)
    calls: list[list[str]] = []
    monkeypatch.setattr(scribe_pg, "_run", _fake_run(calls))
    assert scribe_pg.up() == 0
    assert not [
        c for c in calls if c[0] in ("initdb",) or (c[0] == "pg_ctl" and "start" in c)
    ]
    assert not (tmp_path / "sock").exists()


def test_status_reports_the_socket_dir_the_server_uses(
    scribe_pg, monkeypatch, capsys
) -> None:
    _present_cluster(scribe_pg)
    (scribe_pg.CLUSTER / "postmaster.pid").write_text(
        "4242\n/data\n1790000000\n5433\n/run/user/1000/scribe-pg\n127.0.0.1\n"
    )
    monkeypatch.setattr(scribe_pg, "_is_up", lambda: True)
    assert scribe_pg.status() == 0
    out = capsys.readouterr().out
    assert (
        "listening on 127.0.0.1:5433" in out
        and "socket dir /run/user/1000/scribe-pg" in out
    )
