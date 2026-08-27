"""Story 20.1: one boot script raises both plane faces (CAP-5, `query-plane-face` 2026-08-26)."""

from __future__ import annotations

import json
import shutil
import socket
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pytest

from pyforge.atlas import query_plane_boot
from pyforge.atlas.duckdb_writer import (
    ATLAS_DUCKDB_NAME,
    SecondWriterRefused,
    connect_writer,
)
from pyforge.atlas.query_plane_boot import (
    DEFAULT_PORT,
    STACK_UP_ENV,
    DuckDBServerNotProvisionedError,
    boot_query_plane,
    stack_is_up,
)


def _plane(tmp_path: Path) -> Path:
    return tmp_path / ATLAS_DUCKDB_NAME


class _FakeProcess:
    pid = 4242

    def poll(self) -> None:
        return None


# --- I/O row 1: STACK_DOWN -------------------------------------------------


def test_stack_down_raises_library_face_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(STACK_UP_ENV, raising=False)
    boot = boot_query_plane(_plane(tmp_path))
    try:
        assert boot.http is None
        # The library face is genuinely usable: a real SELECT.
        assert boot.library.execute("SELECT 42").fetchone() == (42,)
        assert len(boot.notices) == 1
        notice = boot.notices[0]
        assert notice["event"] == "http-face-not-raised"
        assert notice["reason"] == "stack-down"
        # Structured means JSON-serializable, one line (the CLI envelope contract).
        assert "\n" not in json.dumps(notice)
    finally:
        boot.library.close()


# --- I/O row 2: STACK_UP (injected launcher) -------------------------------


def test_stack_up_launches_via_injected_launcher(tmp_path: Path) -> None:
    path = _plane(tmp_path)
    recorded: list[list[str]] = []

    def launcher(argv: Any) -> _FakeProcess:
        recorded.append(list(argv))
        return _FakeProcess()

    boot = boot_query_plane(path, stack_up=True, launcher=launcher)
    try:
        # Both handles are returned.
        assert boot.http is not None
        assert isinstance(boot.http.process, _FakeProcess)
        assert boot.http.endpoint == f"http://127.0.0.1:{DEFAULT_PORT}/"
        # The REAL argv contract (bound from the installed pkg/__main__.py):
        # one positional, the DuckDB path. No port flag exists upstream.
        assert recorded == [["duckdb-server", str(path)]]
        # Chosen handling (spec Design Notes): the plane writer FILELOCK stays
        # held by the boot for its whole lifetime, so a second writer is still
        # refused while the HTTP face lives...
        with pytest.raises(SecondWriterRefused):
            connect_writer(path)
        events = [n["event"] for n in boot.notices]
        assert events == ["library-face-yielded", "http-face-raised"]
    finally:
        boot.library.close()
    # ...and closing the boot's library handle releases the plane again.
    writer = connect_writer(path)
    writer.close()


def test_stack_up_with_custom_port_and_real_launcher_fails_loud(
    tmp_path: Path,
) -> None:
    # The installed duckdb-server hard-codes port 3000; a real launch on any
    # other port would report an endpoint that points nowhere. Fail loud, and
    # release the writer lock on the way out.
    path = _plane(tmp_path)
    with pytest.raises(ValueError, match="3000"):
        boot_query_plane(path, stack_up=True, port=8123, launcher=None)
    writer = connect_writer(path)
    writer.close()


# --- I/O row 3: MISSING_PROVISIONING ---------------------------------------


def test_missing_provisioning_raises_typed_and_releases_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _plane(tmp_path)
    monkeypatch.setattr(query_plane_boot.shutil, "which", lambda _: None)
    with pytest.raises(
        DuckDBServerNotProvisionedError, match="pixi install -e pyforge-atlas"
    ) as excinfo:
        boot_query_plane(path, stack_up=True)
    # The typed error names the provisioning step; the boot never installs.
    assert "INSTALL" not in str(excinfo.value).replace(
        "pixi install -e pyforge-atlas", ""
    )
    # The writer lock was released: a follow-up writer succeeds.
    writer = connect_writer(path)
    writer.close()


# --- I/O row 4: SECOND_BOOT_INVOCATION -------------------------------------


def test_second_boot_invocation_is_refused(tmp_path: Path) -> None:
    path = _plane(tmp_path)
    first = boot_query_plane(path, stack_up=False)
    try:
        # The existing duckdb_writer refusal, not a new error type.
        with pytest.raises(SecondWriterRefused):
            boot_query_plane(path, stack_up=False)
    finally:
        first.library.close()


# --- env-signal parsing -----------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, False),
        ("", False),
        ("0", False),
        ("false", False),
        ("banana", False),
        ("1", True),
        ("true", True),
        ("TRUE", True),
        (" yes ", True),
        ("on", True),
    ],
)
def test_env_signal_parsing(
    monkeypatch: pytest.MonkeyPatch, raw: str | None, expected: bool
) -> None:
    if raw is None:
        monkeypatch.delenv(STACK_UP_ENV, raising=False)
    else:
        monkeypatch.setenv(STACK_UP_ENV, raw)
    assert stack_is_up() is expected


def test_explicit_override_beats_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(STACK_UP_ENV, "1")
    assert stack_is_up(False) is False
    monkeypatch.delenv(STACK_UP_ENV, raising=False)
    assert stack_is_up(True) is True


# --- real-binary smoke (guarded) --------------------------------------------

requires_duckdb_server = pytest.mark.skipif(
    shutil.which("duckdb-server") is None,
    reason=(
        "duckdb-server is not provisioned (the linux-64 pyforge-atlas pixi "
        "env carries it)"
    ),
)


def _port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        # SO_REUSEADDR mirrors what the server's own listener (socketify/uWS)
        # can do — without it a prior run's TIME_WAIT socket false-skips.
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
        return True


def _post_query(endpoint: str, sql: str) -> bytes:
    request = urllib.request.Request(
        endpoint,
        data=json.dumps({"sql": sql, "type": "json", "uuid": "smoke"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310 — 127.0.0.1
        return response.read()


@requires_duckdb_server
def test_real_duckdb_server_launches_from_the_one_site(tmp_path: Path) -> None:
    # The free-port pattern from test_read_only_live_attach.py cannot pick the
    # server's port — the installed duckdb-server hard-codes 3000 with no flag
    # (deviation recorded in the story spec's Design Notes) — so the guard is
    # availability of that fixed port, not a chosen free one.
    if not _port_is_free(DEFAULT_PORT):
        pytest.skip(f"port {DEFAULT_PORT} (hard-coded upstream) is already in use")
    import time

    boot = boot_query_plane(_plane(tmp_path), stack_up=True)
    assert boot.http is not None
    process = boot.http.process
    try:
        body: bytes | None = None
        for _ in range(150):
            if process.poll() is not None:
                pytest.fail(
                    f"duckdb-server exited at startup (rc={process.returncode})"
                )
            try:
                body = _post_query(boot.http.endpoint, "SELECT 42 AS answer")
                break
            except (urllib.error.URLError, ConnectionError, OSError):
                time.sleep(0.2)
        assert body is not None, "endpoint never became reachable"
        assert json.loads(body) == [{"answer": 42}]
        assert process.poll() is None, "server must still be alive after serving"
        assert boot.http.endpoint == f"http://127.0.0.1:{DEFAULT_PORT}/"
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except Exception:
            process.kill()
            process.wait(timeout=10)
        boot.library.close()
