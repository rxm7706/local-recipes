"""scripts/scribe_pg.py keeps the server's Unix socket in a short per-user directory (Story 22.1).

A worktree's `var/scribe-pg/.s.PGSQL.5433` runs past the kernel's socket-path limit, so
the socket goes to `SCRIBE_PG_SOCKET_DIR`, else `$XDG_RUNTIME_DIR/scribe-pg`, else
`/tmp/scribe-pg-<uid>`. No test here starts a server.

Socket dirs are built under a short base in /tmp, never under pytest's `tmp_path`: that
path alone can pass the limit (macOS resolves it under /private/var/folders/...).
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="scribe-pg is POSIX-only (no win-64 pgvector)"
)

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
def short():
    base = Path(tempfile.mkdtemp(prefix="spg", dir="/tmp"))
    yield base
    shutil.rmtree(base, ignore_errors=True)


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


# --- which directory -------------------------------------------------------------


def test_the_override_wins(scribe_pg, monkeypatch, short) -> None:
    (short / "xdg").mkdir()
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(short / "xdg"))
    monkeypatch.setenv("SCRIBE_PG_SOCKET_DIR", str(short / "sock"))
    assert scribe_pg._socket_dir() == (short / "sock", True)


def test_a_relative_override_is_made_absolute(scribe_pg, monkeypatch, short) -> None:
    """The server resolves a relative -k against its data dir, not the caller's cwd."""
    monkeypatch.chdir(short)
    monkeypatch.setenv("SCRIBE_PG_SOCKET_DIR", "sock")
    assert scribe_pg._socket_dir() == (short / "sock", True)


def test_xdg_runtime_dir_is_next(scribe_pg, monkeypatch, short) -> None:
    (short / "xdg").mkdir()
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(short / "xdg"))
    assert scribe_pg._socket_dir() == (short / "xdg" / "scribe-pg", False)


def test_a_missing_xdg_runtime_dir_falls_back_to_tmp(
    scribe_pg, monkeypatch, short
) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(short / "absent"))
    assert scribe_pg._socket_dir() == (
        Path("/tmp") / f"scribe-pg-{os.getuid()}",
        False,
    )


def test_tmp_per_uid_is_the_fallback(scribe_pg) -> None:
    assert scribe_pg._socket_dir() == (
        Path("/tmp") / f"scribe-pg-{os.getuid()}",
        False,
    )


# --- preparing it ----------------------------------------------------------------


def test_a_default_dir_is_created_0700(scribe_pg, monkeypatch, short) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(short))
    sock_dir = scribe_pg._prepare_socket_dir()
    assert sock_dir == short / "scribe-pg"
    assert stat.S_IMODE(sock_dir.stat().st_mode) == 0o700


def test_a_loose_default_dir_is_tightened(scribe_pg, monkeypatch, short) -> None:
    loose = short / "scribe-pg"
    loose.mkdir()
    loose.chmod(0o755)
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(short))
    assert scribe_pg._prepare_socket_dir() == loose
    assert stat.S_IMODE(loose.stat().st_mode) == 0o700


def test_an_absent_chosen_dir_is_created_0700(scribe_pg, monkeypatch, short) -> None:
    monkeypatch.setenv("SCRIBE_PG_SOCKET_DIR", str(short / "sock"))
    sock_dir = scribe_pg._prepare_socket_dir()
    assert sock_dir == short / "sock"
    assert stat.S_IMODE(sock_dir.stat().st_mode) == 0o700


def test_an_existing_chosen_dir_keeps_its_mode(scribe_pg, monkeypatch, short) -> None:
    """A directory the user chose may be shared on purpose; the script never re-modes it."""
    shared = short / "shared"
    shared.mkdir()
    shared.chmod(0o2775)
    monkeypatch.setenv("SCRIBE_PG_SOCKET_DIR", str(shared))
    assert scribe_pg._prepare_socket_dir() == shared
    assert stat.S_IMODE(shared.stat().st_mode) == 0o2775


def test_a_chosen_path_that_is_a_file_is_refused(
    scribe_pg, monkeypatch, short, capsys
) -> None:
    (short / "afile").write_text("")
    monkeypatch.setenv("SCRIBE_PG_SOCKET_DIR", str(short / "afile"))
    assert scribe_pg._prepare_socket_dir() is None
    assert capsys.readouterr().err


def test_a_socket_path_over_the_limit_fails_loud(
    scribe_pg, monkeypatch, short, capsys
) -> None:
    too_long = short / ("x" * (scribe_pg.SOCKET_PATH_MAX + 1))
    monkeypatch.setenv("SCRIBE_PG_SOCKET_DIR", str(too_long))
    assert scribe_pg._prepare_socket_dir() is None
    err = capsys.readouterr().err
    assert "SCRIBE_PG_SOCKET_DIR" in err
    assert f"limit is {scribe_pg.SOCKET_PATH_MAX}" in err
    assert not too_long.exists()


def test_the_limit_counts_the_socket_file_name(scribe_pg, monkeypatch, short) -> None:
    """The whole `<dir>/.s.PGSQL.<port>` path is measured: exactly the limit fits, one over fails."""
    suffix = len(f"/.s.PGSQL.{scribe_pg.PORT}")
    room = scribe_pg.SOCKET_PATH_MAX - len(os.fsencode(short)) - 1 - suffix
    monkeypatch.setenv("SCRIBE_PG_SOCKET_DIR", str(short / ("y" * (room + 1))))
    assert scribe_pg._prepare_socket_dir() is None
    monkeypatch.setenv("SCRIBE_PG_SOCKET_DIR", str(short / ("y" * room)))
    assert scribe_pg._prepare_socket_dir() == short / ("y" * room)


def test_a_comma_in_the_path_is_refused(scribe_pg, monkeypatch, short, capsys) -> None:
    monkeypatch.setenv("SCRIBE_PG_SOCKET_DIR", str(short / "a,b"))
    assert scribe_pg._prepare_socket_dir() is None
    assert "comma" in capsys.readouterr().err


def test_a_symlinked_default_dir_is_refused(
    scribe_pg, monkeypatch, short, capsys
) -> None:
    (short / "real").mkdir(mode=0o700)
    (short / "scribe-pg").symlink_to(short / "real")
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(short))
    assert scribe_pg._prepare_socket_dir() is None
    assert "not a directory you own" in capsys.readouterr().err


def test_a_default_dir_owned_by_someone_else_is_refused(
    scribe_pg, monkeypatch, short, capsys
) -> None:
    (short / "scribe-pg").mkdir(mode=0o700)
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(short))
    real_uid = os.getuid()
    monkeypatch.setattr(scribe_pg, "_socket_dir", lambda: (short / "scribe-pg", False))
    monkeypatch.setattr(scribe_pg.os, "getuid", lambda: real_uid + 1)
    assert scribe_pg._prepare_socket_dir() is None
    assert "not a directory you own" in capsys.readouterr().err


# --- up and status -----------------------------------------------------------------


def _fake_run(calls: list[list[str]], show_dirs: str = ""):
    def run(args, **kw):
        calls.append(list(args))
        if args[:2] == ["pg_ctl", "--version"]:
            return subprocess.CompletedProcess(
                args, 0, "pg_ctl (PostgreSQL) 17.11\n", ""
            )
        if args[0] == "psql" and "SHOW unix_socket_directories" in args:
            return subprocess.CompletedProcess(args, 0, f"{show_dirs}\n", "")
        if args[0] == "psql" and "-tAc" in args:
            return subprocess.CompletedProcess(args, 0, "1\n", "")
        return subprocess.CompletedProcess(args, 0, "", "")

    return run


def _present_cluster(module) -> None:
    module.CLUSTER.mkdir(parents=True)
    (module.CLUSTER / "PG_VERSION").write_text("17\n")


def _starts(calls):
    return [c for c in calls if c[0] == "pg_ctl" and "start" in c]


def test_up_starts_the_server_with_the_short_socket_dir(
    scribe_pg, monkeypatch, short
) -> None:
    _present_cluster(scribe_pg)
    monkeypatch.setenv("SCRIBE_PG_SOCKET_DIR", str(short / "sock"))
    monkeypatch.setattr(scribe_pg, "_need", lambda binary: binary)
    answers = iter([False, True])
    monkeypatch.setattr(scribe_pg, "_is_up", lambda: next(answers))
    calls: list[list[str]] = []
    monkeypatch.setattr(scribe_pg, "_run", _fake_run(calls))
    assert scribe_pg.up() == 0
    (start,) = _starts(calls)
    options = start[start.index("-o") + 1]
    assert f"-k {short / 'sock'}" in options
    assert str(scribe_pg.CLUSTER.parent) not in options


def test_up_quotes_a_socket_dir_with_a_space(scribe_pg, monkeypatch, short) -> None:
    _present_cluster(scribe_pg)
    monkeypatch.setenv("SCRIBE_PG_SOCKET_DIR", str(short / "a b"))
    monkeypatch.setattr(scribe_pg, "_need", lambda binary: binary)
    answers = iter([False, True])
    monkeypatch.setattr(scribe_pg, "_is_up", lambda: next(answers))
    calls: list[list[str]] = []
    monkeypatch.setattr(scribe_pg, "_run", _fake_run(calls))
    assert scribe_pg.up() == 0
    (start,) = _starts(calls)
    assert f"-k '{short / 'a b'}'" in start[start.index("-o") + 1]


def test_up_stops_before_pg_ctl_when_the_guard_trips(
    scribe_pg, monkeypatch, short
) -> None:
    _present_cluster(scribe_pg)
    monkeypatch.setenv(
        "SCRIBE_PG_SOCKET_DIR", str(short / ("x" * (scribe_pg.SOCKET_PATH_MAX + 1)))
    )
    monkeypatch.setattr(scribe_pg, "_need", lambda binary: binary)
    monkeypatch.setattr(scribe_pg, "_is_up", lambda: False)
    calls: list[list[str]] = []
    monkeypatch.setattr(scribe_pg, "_run", _fake_run(calls))
    assert scribe_pg.up() == 1
    assert not _starts(calls)


def test_up_reuses_a_listening_cluster(scribe_pg, monkeypatch, short) -> None:
    _present_cluster(scribe_pg)
    monkeypatch.setenv("SCRIBE_PG_SOCKET_DIR", str(short / "sock"))
    monkeypatch.setattr(scribe_pg, "_need", lambda binary: binary)
    monkeypatch.setattr(scribe_pg, "_is_up", lambda: True)
    calls: list[list[str]] = []
    monkeypatch.setattr(scribe_pg, "_run", _fake_run(calls))
    assert scribe_pg.up() == 0
    assert not _starts(calls)
    assert not (short / "sock").exists()


def test_up_does_not_initdb_when_another_checkouts_server_listens(
    scribe_pg, monkeypatch
) -> None:
    monkeypatch.setattr(scribe_pg, "_need", lambda binary: binary)
    monkeypatch.setattr(scribe_pg, "_is_up", lambda: True)
    calls: list[list[str]] = []
    monkeypatch.setattr(scribe_pg, "_run", _fake_run(calls))
    assert scribe_pg.up() == 0
    assert not [c for c in calls if c[0] == "initdb"]
    assert not (scribe_pg.CLUSTER / "PG_VERSION").exists()


def test_status_asks_the_listening_server(scribe_pg, monkeypatch, capsys) -> None:
    monkeypatch.setattr(scribe_pg, "_is_up", lambda: True)
    monkeypatch.setattr(scribe_pg.shutil, "which", lambda binary: binary)
    calls: list[list[str]] = []
    monkeypatch.setattr(
        scribe_pg, "_run", _fake_run(calls, show_dirs="/run/user/1000/scribe-pg")
    )
    assert scribe_pg.status() == 0
    out = capsys.readouterr().out
    assert "listening on 127.0.0.1:5433" in out
    assert "socket dir /run/user/1000/scribe-pg" in out


def test_status_labels_a_stale_pid_file(scribe_pg, monkeypatch, capsys) -> None:
    _present_cluster(scribe_pg)
    (scribe_pg.CLUSTER / "postmaster.pid").write_text(
        "4242\n/data\n1790000000\n5433\n/run/user/1000/scribe-pg\n127.0.0.1\n"
    )
    monkeypatch.setattr(scribe_pg, "_is_up", lambda: False)
    assert scribe_pg.status() == 0
    assert (
        "socket dir /run/user/1000/scribe-pg (stale postmaster.pid)"
        in capsys.readouterr().out
    )


def test_status_names_the_configured_dir_when_down(
    scribe_pg, monkeypatch, short, capsys
) -> None:
    monkeypatch.setenv("SCRIBE_PG_SOCKET_DIR", str(short / "sock"))
    monkeypatch.setattr(scribe_pg, "_is_up", lambda: False)
    assert scribe_pg.status() == 0
    assert f"socket dir {short / 'sock'} (configured)" in capsys.readouterr().out
