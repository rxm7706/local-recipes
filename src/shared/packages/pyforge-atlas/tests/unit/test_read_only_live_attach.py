"""Steward 34.1: read-only live Postgres attach on the plane (FR-46, AD-22)."""

from __future__ import annotations

import ast
import os
import shutil
import socket
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import duckdb
import pytest

from pyforge.atlas.duckdb_writer import ATLAS_DUCKDB_NAME, connect_writer
from pyforge.atlas.live_attach import PostgresNotProvisionedError, attach_postgres_readonly, load_postgres_offline

ATLAS_ROOT = Path(__file__).resolve().parents[2]
LIVE_ATTACH_MODULE = ATLAS_ROOT / "src" / "pyforge" / "atlas" / "live_attach.py"
WRITER_MODULE = ATLAS_ROOT / "src" / "pyforge" / "atlas" / "duckdb_writer.py"
REPO_ROOT = Path(__file__).resolve().parents[6]


def _has_postgres_extension() -> bool:
    try:
        con = duckdb.connect(
            config={
                "autoinstall_known_extensions": False,
                "autoload_known_extensions": False,
            }
        )
        try:
            load_postgres_offline(con)
            return True
        finally:
            con.close()
    except Exception:
        return False


requires_postgres_ext = pytest.mark.skipif(
    not _has_postgres_extension(),
    reason="postgres DuckDB extension is not provisioned in local cache",
)


def _pg_bindir() -> Path | None:
    env_override = os.environ.get("PYFORGE_PG_BINDIR")
    candidates: list[Path] = []
    if env_override:
        candidates.append(Path(env_override))
    which = shutil.which("pg_ctl")
    if which:
        candidates.append(Path(which).resolve().parent)
    prefix = os.environ.get("CONDA_PREFIX")
    if prefix:
        candidates.append(Path(prefix) / "bin")
    for env_name in ("platform-dev", "local-recipes", "pyforge-atlas"):
        candidates.append(REPO_ROOT / ".pixi" / "envs" / env_name / "bin")
    for bindir in candidates:
        needed = ("pg_ctl", "initdb", "psql", "pg_isready")
        if all((bindir / name).is_file() for name in needed):
            return bindir
    return None


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _run_pg(bindir: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
    return subprocess.run(  # noqa: S603 — fixed argv, no shell
        [str(bindir / args[0]), *args[1:]],
        check=check,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


@pytest.fixture
def fixture_postgres(tmp_path: Path) -> Iterator[str]:
    """Two-schema vanilla Postgres. Does not CREATE EXTENSION vector."""
    bindir = _pg_bindir()
    if bindir is None:
        pytest.skip(
            "fixture Postgres needs initdb/pg_ctl (set PYFORGE_PG_BINDIR or "
            "install pixi env platform-dev) -- absent in a fresh worktree's isolated env"
        )
    data_dir = tmp_path / "pgdata"
    sock_dir = tmp_path / "pgsock"
    sock_dir.mkdir()
    log_path = tmp_path / "pg.log"
    _run_pg(
        bindir,
        "initdb",
        "-D",
        str(data_dir),
        "-U",
        "postgres",
        "--auth-local=trust",
        "--auth-host=trust",
        "--no-sync",
    )
    port = _free_port()
    options = f"-p {port} -h 127.0.0.1 -k '{sock_dir}' -c fsync=off -c synchronous_commit=off -c full_page_writes=off"
    try:
        _run_pg(
            bindir,
            "pg_ctl",
            "-D",
            str(data_dir),
            "-l",
            str(log_path),
            "-o",
            options,
            "start",
        )
    except Exception:
        _run_pg(
            bindir,
            "pg_ctl",
            "-D",
            str(data_dir),
            "-m",
            "immediate",
            "stop",
            check=False,
        )
        raise
    try:
        ready = False
        for _ in range(50):
            ping = _run_pg(
                bindir,
                "pg_isready",
                "-h",
                "127.0.0.1",
                "-p",
                str(port),
                "-U",
                "postgres",
                check=False,
            )
            if ping.returncode == 0:
                ready = True
                break
            time.sleep(0.1)
        if not ready:
            pytest.fail(f"postgres did not become ready: {log_path.read_text(encoding='utf-8')}")
        sql = """
        CREATE SCHEMA ops;
        CREATE SCHEMA inventory;
        CREATE TABLE ops.orders (id INTEGER PRIMARY KEY, sku TEXT NOT NULL);
        CREATE TABLE inventory.items (sku TEXT PRIMARY KEY, qty INTEGER NOT NULL);
        INSERT INTO ops.orders (id, sku) VALUES (1, 'bolt');
        INSERT INTO inventory.items (sku, qty) VALUES ('bolt', 42);
        """
        _run_pg(
            bindir,
            "psql",
            "-h",
            "127.0.0.1",
            "-p",
            str(port),
            "-U",
            "postgres",
            "-d",
            "postgres",
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            sql,
        )
        installed = _run_pg(
            bindir,
            "psql",
            "-h",
            "127.0.0.1",
            "-p",
            str(port),
            "-U",
            "postgres",
            "-d",
            "postgres",
            "-At",
            "-c",
            "SELECT extname FROM pg_extension",
        )
        assert "vector" not in installed.stdout.split(), installed.stdout
        yield f"dbname=postgres user=postgres host=127.0.0.1 port={port}"
    finally:
        _run_pg(
            bindir,
            "pg_ctl",
            "-D",
            str(data_dir),
            "-m",
            "immediate",
            "stop",
            check=False,
        )


def _execute_calls_install(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = ""
        if isinstance(func, ast.Attribute):
            name = func.attr
        elif isinstance(func, ast.Name):
            name = func.id
        if name != "execute" or not node.args:
            continue
        arg0 = node.args[0]
        if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
            if arg0.value.lstrip().upper().startswith("INSTALL"):
                found.append(arg0.value)
        if isinstance(arg0, ast.JoinedStr):
            raw = ast.unparse(arg0)
            if "INSTALL" in raw.upper():
                found.append(raw)
    return found


def _imported_or_named(tree: ast.AST, *names: str) -> set[str]:
    found: set[str] = set()
    wanted = set(names)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root in wanted:
                    found.add(root)
        elif isinstance(node, ast.ImportFrom):
            mod = (node.module or "").split(".", 1)[0]
            if mod in wanted:
                found.add(mod)
            for alias in node.names:
                if alias.name in wanted:
                    found.add(alias.name)
        elif isinstance(node, ast.Name) and node.id in wanted:
            found.add(node.id)
        elif isinstance(node, ast.Attribute) and node.attr in wanted:
            found.add(node.attr)
    return found


def test_consumer_path_does_not_install_extensions() -> None:
    assert LIVE_ATTACH_MODULE.is_file()
    installs = _execute_calls_install(LIVE_ATTACH_MODULE)
    assert installs == [], installs
    src = LIVE_ATTACH_MODULE.read_text(encoding="utf-8")
    assert "LOAD postgres" in src
    assert "READ_ONLY" in src
    assert "TYPE POSTGRES" in src


class _RecordingConnection:
    def __init__(self) -> None:
        self.statements: list[str] = []

    def execute(self, sql: str) -> None:
        self.statements.append(sql)
        if sql.lstrip().upper().startswith("LOAD"):
            raise RuntimeError("offline cache empty")


def test_consumer_boot_issues_only_set_and_load() -> None:
    con = _RecordingConnection()
    with pytest.raises(PostgresNotProvisionedError):
        load_postgres_offline(con)
    assert con.statements == [
        "SET autoinstall_known_extensions = false",
        "SET autoload_known_extensions = false",
        "LOAD postgres",
    ]
    assert not any(s.lstrip().upper().startswith("INSTALL") for s in con.statements)


def test_attach_path_is_not_pandas_sqlquerydataset() -> None:
    banned = ("SQLQueryDataSet", "pandas")
    for path in (LIVE_ATTACH_MODULE, WRITER_MODULE):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        hit = _imported_or_named(tree, *banned)
        assert not hit, f"{path.name} must not import or name {sorted(hit)}"


def test_missing_postgres_extension_fails_loud(tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty-duckdb-ext"
    empty_dir.mkdir()
    con = duckdb.connect(
        config={
            "extension_directory": str(empty_dir),
            "autoinstall_known_extensions": False,
            "autoload_known_extensions": False,
        }
    )
    try:
        with pytest.raises(PostgresNotProvisionedError, match="LOAD"):
            load_postgres_offline(con)
    finally:
        con.close()


def test_attach_strips_dsn_whitespace() -> None:
    captured: list[str] = []

    class _AttachCon:
        def execute(self, sql: str) -> None:
            captured.append(sql)

    attach_postgres_readonly(_AttachCon(), "  dbname=postgres  ", alias="oltp")
    assert captured[-1].startswith("ATTACH 'dbname=postgres' AS oltp")
    assert "READ_ONLY" in captured[-1]


@requires_postgres_ext
def test_federated_read_across_two_schemas(tmp_path: Path, fixture_postgres: str) -> None:
    plane = connect_writer(tmp_path / ATLAS_DUCKDB_NAME)
    try:
        attach_postgres_readonly(plane, fixture_postgres, alias="oltp")
        row = plane.execute(
            "SELECT o.id, i.qty FROM oltp.ops.orders AS o JOIN oltp.inventory.items AS i ON o.sku = i.sku"
        ).fetchone()
        assert row == (1, 42)
    finally:
        plane.close()


@requires_postgres_ext
def test_write_through_attach_is_refused(tmp_path: Path, fixture_postgres: str) -> None:
    plane = connect_writer(tmp_path / ATLAS_DUCKDB_NAME)
    try:
        attach_postgres_readonly(plane, fixture_postgres, alias="oltp")
        with pytest.raises(duckdb.Error):
            plane.execute("INSERT INTO oltp.ops.orders VALUES (2, 'nut')")
        count = plane.execute("SELECT COUNT(*) FROM oltp.ops.orders").fetchone()
        assert count == (1,)
    finally:
        plane.close()
