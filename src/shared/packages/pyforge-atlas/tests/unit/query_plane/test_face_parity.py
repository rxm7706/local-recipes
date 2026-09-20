"""Story 20.2 (CAP-5) — face parity is part of done.

The `query-plane-face` operator ruling (2026-08-26) committed to raising BOTH the
in-process library face and the Mosaic ``duckdb-server`` HTTP/Arrow face from
Story 20.1's one boot script, and said parity between them "is part of the
face's definition of done." This module is that offline-safe parity gate: it
runs an IDENTICAL query set against (a) a ``connect_reader`` handle on
``atlas.duckdb`` and (b) the HTTP/Arrow face raised by
``pyforge.atlas.query_plane_boot.boot_query_plane``, and asserts row-for-row
agreement.

NOT the ``tests/parity/`` package. That directory's "parity" means
legacy-``cf_atlas.db``-vs-migrated-pipeline-output (Story B1/B4/AD-19) — an
unrelated concept. This gate compares CAP-19's two QUERY-PLANE FACES against
each other, on the SAME fixture data, never two independently-seeded stores.

Sequencing note (binding, from Story 20.1's own Design Notes): DuckDB refuses
any second cross-process open — read-only or read-write — while a read-write
connection is held elsewhere, and the real ``duckdb-server`` opens the plane
file read-write at startup. The two faces can therefore never hold LIVE
connections to the same file at once (``boot_query_plane`` itself yields the
library connection before launching the server). This gate compares
SEQUENTIAL snapshots of the identical on-disk fixture — the library face is
read first, then the HTTP face is raised (or found not raised) and read — never
two independently-seeded stores.
"""

from __future__ import annotations

import contextlib
import json
import shutil
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from pyforge.atlas.duckdb_writer import ATLAS_DUCKDB_NAME, connect_reader, connect_writer
from pyforge.atlas.query_plane_boot import DEFAULT_PORT, PlaneBoot, boot_query_plane

# --- fixture: ONE seed, read by both faces (never two independently-seeded
# stores per the story's Boundaries & Constraints) ---------------------------

FIXTURE_TABLE = "face_parity_fixture"


def _plane(tmp_path: Path) -> Path:
    return tmp_path / ATLAS_DUCKDB_NAME


def _seed_fixture(path: Path) -> None:
    writer = connect_writer(path)
    try:
        writer.execute(f"CREATE TABLE {FIXTURE_TABLE} (id INTEGER, label VARCHAR, amount DOUBLE)")
        writer.execute(f"INSERT INTO {FIXTURE_TABLE} VALUES (1, 'alpha', 1.5), (2, 'beta', 2.5), (3, 'gamma', 3.5)")
    finally:
        writer.close()


# The IDENTICAL query set run against both faces (AC: "an identical query
# set"). "empty" is I/O row EMPTY_RESULT: 0 rows on both faces.
QUERIES: tuple[tuple[str, str], ...] = (
    ("rows", f"SELECT id, label, amount FROM {FIXTURE_TABLE} ORDER BY id"),
    ("single_row", f"SELECT amount FROM {FIXTURE_TABLE} WHERE id = 2"),
    ("empty", f"SELECT id FROM {FIXTURE_TABLE} WHERE id > 1000"),
)


def _library_rows(path: Path, sql: str) -> list[dict[str, Any]]:
    reader = connect_reader(path)
    try:
        cursor = reader.execute(sql)
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
    finally:
        reader.close()


# --- HTTP/Arrow face wire contract (bound from the installed duckdb-server,
# same protocol test_query_plane_boot.py verified: POST JSON, body is a JSON
# array of row-objects). Kept local rather than imported cross-module -- this
# gate is a single self-contained file per the story's Never clause (no shared
# comparison framework). ------------------------------------------------------


def _post_query(endpoint: str, sql: str) -> bytes:
    request = urllib.request.Request(
        endpoint,
        data=json.dumps({"sql": sql, "type": "json", "uuid": "face-parity"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310 — 127.0.0.1
        return response.read()


def _wait_until_ready(process: Any, endpoint: str) -> None:
    for _ in range(150):
        if process.poll() is not None:
            pytest.fail(f"duckdb-server exited at startup (rc={process.returncode})")
        try:
            _post_query(endpoint, "SELECT 1")
            return
        except urllib.error.URLError, ConnectionError, OSError:
            time.sleep(0.2)
    pytest.fail("HTTP/Arrow endpoint never became reachable")


def _shutdown_boot(boot: PlaneBoot) -> None:
    """Never let teardown mask an in-flight test failure or skip the library
    close: the kill/wait fallback runs best-effort (the process may already
    be gone, e.g. a mid-test crash left a stale ``returncode``), and
    ``boot.library.close()`` always runs via ``finally``."""
    try:
        if boot.http is not None:
            process = boot.http.process
            process.terminate()
            try:
                process.wait(timeout=10)
            except Exception:
                with contextlib.suppress(Exception):
                    process.kill()
                with contextlib.suppress(Exception):
                    process.wait(timeout=10)
    finally:
        boot.library.close()


requires_duckdb_server = pytest.mark.skipif(
    shutil.which("duckdb-server") is None,
    reason=("duckdb-server is not provisioned (the linux-64 pyforge-atlas pixi env carries it)"),
)


def _port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
        return True


# --- the comparator: the ONE named property this gate proves ----------------


@dataclass(frozen=True)
class QueryParity:
    """Outcome of comparing one query across the two faces.

    ``status`` is one of ``"match"``, ``"mismatch"``, or ``"not_applicable"``
    (the last one is I/O row FACE_DOWN: the HTTP face was never raised, so no
    comparison was attempted — this must never be conflated with ``"match"``).
    """

    status: str
    library_rows: list[dict[str, Any]]
    http_rows: list[dict[str, Any]] | None
    reason: str | None = None


def _compare(
    library_rows: list[dict[str, Any]],
    http_rows: list[dict[str, Any]] | None,
    *,
    reason: str | None = None,
) -> QueryParity:
    if http_rows is None:
        return QueryParity(status="not_applicable", library_rows=library_rows, http_rows=None, reason=reason)
    status = "match" if library_rows == http_rows else "mismatch"
    return QueryParity(status=status, library_rows=library_rows, http_rows=http_rows)


def _assert_parity(report: dict[str, QueryParity]) -> None:
    """The gate's pass/fail contract — names the divergent quer(y/ies)."""
    mismatches = {name: qp for name, qp in report.items() if qp.status == "mismatch"}
    assert not mismatches, "face parity violated for " + "; ".join(
        f"{name} (library={qp.library_rows!r}, http={qp.http_rows!r})" for name, qp in sorted(mismatches.items())
    )


def _run_face_parity(path: Path, queries: tuple[tuple[str, str], ...], *, stack_up: bool) -> dict[str, QueryParity]:
    """Read the library face first, then raise (or not) the HTTP face and read
    it — sequential snapshots of the SAME fixture, per the module docstring's
    sequencing note."""
    library_results = {name: _library_rows(path, sql) for name, sql in queries}
    boot = boot_query_plane(path, stack_up=stack_up)
    try:
        if boot.http is None:
            notice = next(n for n in boot.notices if n["event"] == "http-face-not-raised")
            return {name: _compare(rows, None, reason=notice["reason"]) for name, rows in library_results.items()}
        _wait_until_ready(boot.http.process, boot.http.endpoint)
        return {
            name: _compare(library_results[name], json.loads(_post_query(boot.http.endpoint, sql)))
            for name, sql in queries
        }
    finally:
        _shutdown_boot(boot)


# --- I/O row: HAPPY_PATH + EMPTY_RESULT (one real boot; both faces up) -------


@requires_duckdb_server
def test_happy_path_rows_agree_row_for_row_including_empty_result(tmp_path: Path) -> None:
    if not _port_is_free(DEFAULT_PORT):
        pytest.skip(f"port {DEFAULT_PORT} (hard-coded upstream) is already in use")
    path = _plane(tmp_path)
    _seed_fixture(path)

    report = _run_face_parity(path, QUERIES, stack_up=True)

    _assert_parity(report)
    # Every query was genuinely compared -- never a silent skip when both
    # faces are actually up.
    assert {qp.status for qp in report.values()} == {"match"}
    # EMPTY_RESULT (I/O row 4): 0 rows on both faces still counts as a match,
    # not an accidental "not_applicable" or a false mismatch.
    assert report["empty"].library_rows == []
    assert report["empty"].http_rows == []


# --- I/O row: FACE_DOWN -------------------------------------------------------


def test_face_down_reports_not_applicable_never_a_silent_pass(tmp_path: Path) -> None:
    path = _plane(tmp_path)
    _seed_fixture(path)

    report = _run_face_parity(path, QUERIES, stack_up=False)

    assert {qp.status for qp in report.values()} == {"not_applicable"}
    assert all(qp.reason == "stack-down" for qp in report.values())
    # The empty-result query in particular must not be conflated with a pass:
    # 0 library rows and "not attempted" are different statuses.
    assert report["empty"].library_rows == []
    assert report["empty"].status != "match"
    # A not-applicable report is not a failure either -- the degrade path
    # (Story 20.1) is a legitimate state, not a crash.
    _assert_parity(report)


# --- I/O row: SEEDED_DIVERGENCE ----------------------------------------------


@requires_duckdb_server
def test_seeded_divergence_fails_and_names_the_divergent_query(tmp_path: Path) -> None:
    if not _port_is_free(DEFAULT_PORT):
        pytest.skip(f"port {DEFAULT_PORT} (hard-coded upstream) is already in use")
    path = _plane(tmp_path)
    _seed_fixture(path)

    # Capture the library face's snapshot BEFORE mutating the fixture.
    library_results = {name: _library_rows(path, sql) for name, sql in QUERIES}

    # Mutate one fixture row between the two captures -- a real divergence
    # between two snapshots of the plane (the single-writer-per-file
    # constraint rules out a literal simultaneous divergence; see the module
    # docstring), proving the comparator is not vacuous.
    writer = connect_writer(path)
    try:
        writer.execute(f"UPDATE {FIXTURE_TABLE} SET amount = 999.0 WHERE id = 2")
    finally:
        writer.close()

    boot = boot_query_plane(path, stack_up=True)
    try:
        assert boot.http is not None
        _wait_until_ready(boot.http.process, boot.http.endpoint)
        http_results = {name: json.loads(_post_query(boot.http.endpoint, sql)) for name, sql in QUERIES}
    finally:
        _shutdown_boot(boot)

    report = {name: _compare(library_results[name], http_results[name]) for name, _ in QUERIES}

    # The two queries touching id=2 diverge; the unrelated "empty" query does
    # not -- the gate names exactly the affected queries, not everything.
    mismatches = {name for name, qp in report.items() if qp.status == "mismatch"}
    assert mismatches == {"rows", "single_row"}
    assert report["empty"].status == "match"

    with pytest.raises(AssertionError) as excinfo:
        _assert_parity(report)
    assert "rows" in str(excinfo.value)
    assert "single_row" in str(excinfo.value)
