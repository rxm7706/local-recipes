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

Transport note (Story 27.3, DW-FU-20-2-2): the comparison rides the face's
ARROW transport (``type: "arrow"``), not its JSON one. The fixture now carries
NULL, DATE, TIMESTAMP, DECIMAL and BLOB values, and ``pkg/query.py``'s JSON
transport is lossy for exactly those: it goes through
``DataFrame.to_json(orient="records")``, which renders DATE/TIMESTAMP as epoch
milliseconds, DECIMAL as a float, and — the disqualifying one — every BLOB as
``{}``, so a seeded BLOB divergence would be invisible. Arrow IPC round-trips
all five to the same Python objects DuckDB's own cursor yields, so the gate
compares typed values rather than two different serializers' opinions of them.

Port note (Story 27.3, DW-FU-20-2-3): the gate binds an ephemeral free port and
passes it to ``boot_query_plane``. The installed ``duckdb-server`` hard-codes
``app.listen(3000, …)`` and ships no port flag, so the port is honoured by the
injected launcher (``_launcher_on_port``), which runs the shipped
``pkg.server.server`` with ``socketify.App.listen`` bound to that port. Nothing
about the server's query handling is faked. The previous gate probed the
hard-coded 3000 and skipped when it was taken — a race, and a silent hole in CI.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyarrow as pa
import pytest

from pyforge.atlas.duckdb_writer import ATLAS_DUCKDB_NAME, connect_reader, connect_writer
from pyforge.atlas.query_plane_boot import PlaneBoot, boot_query_plane

# --- fixture: ONE seed, read by both faces (never two independently-seeded
# stores per the story's Boundaries & Constraints) ---------------------------

FIXTURE_TABLE = "face_parity_fixture"


def _plane(tmp_path: Path) -> Path:
    return tmp_path / ATLAS_DUCKDB_NAME


def _seed_fixture(path: Path) -> None:
    """Seed the one fixture table: a scalar triple plus one column per type the
    parity gate must cover (DATE, TIMESTAMP, DECIMAL, BLOB), and an all-NULL row
    so NULL is compared as a value, not as an absent column."""
    writer = connect_writer(path)
    try:
        writer.execute(
            f"""
            CREATE TABLE {FIXTURE_TABLE} (
                id INTEGER,
                label VARCHAR,
                amount DOUBLE,
                released DATE,
                observed TIMESTAMP,
                price DECIMAL(12, 3),
                digest BLOB
            )
            """
        )
        writer.execute(
            f"""
            INSERT INTO {FIXTURE_TABLE} VALUES
              (1, 'alpha', 1.5, DATE '2026-01-02', TIMESTAMP '2026-01-02 03:04:05',
               10.125, '\\x00\\x01\\xfe'::BLOB),
              (2, 'beta', 2.5, DATE '2026-02-03', TIMESTAMP '2026-02-03 04:05:06',
               20.250, 'ascii-bytes'::BLOB),
              (3, NULL, NULL, NULL, NULL, NULL, NULL)
            """
        )
    finally:
        writer.close()


# The IDENTICAL query set run against both faces (AC: "an identical query
# set"). "empty" is I/O row EMPTY_RESULT: 0 rows on both faces. The five typed
# queries each read ONE of the widened columns, so a divergence in that column
# names its own query rather than only the catch-all "rows".
QUERIES: tuple[tuple[str, str], ...] = (
    (
        "rows",
        f"SELECT id, label, amount, released, observed, price, digest FROM {FIXTURE_TABLE} ORDER BY id",
    ),
    ("single_row", f"SELECT amount FROM {FIXTURE_TABLE} WHERE id = 2"),
    ("empty", f"SELECT id FROM {FIXTURE_TABLE} WHERE id > 1000"),
    ("nulls", f"SELECT id FROM {FIXTURE_TABLE} WHERE label IS NULL ORDER BY id"),
    ("dates", f"SELECT id, released FROM {FIXTURE_TABLE} ORDER BY id"),
    ("timestamps", f"SELECT id, observed FROM {FIXTURE_TABLE} ORDER BY id"),
    ("decimals", f"SELECT id, price FROM {FIXTURE_TABLE} ORDER BY id"),
    ("blobs", f"SELECT id, digest FROM {FIXTURE_TABLE} ORDER BY id"),
)

# Each widened column, the UPDATE that diverges it, and the queries that must
# flip to "mismatch" when it does. `label` stands in for NULL-ness: filling the
# all-NULL row's label changes both the row dump and the IS NULL query.
TYPED_DIVERGENCES: tuple[tuple[str, str, frozenset[str]], ...] = (
    ("null", f"UPDATE {FIXTURE_TABLE} SET label = 'delta' WHERE id = 3", frozenset({"rows", "nulls"})),
    ("date", f"UPDATE {FIXTURE_TABLE} SET released = DATE '2099-12-31' WHERE id = 1", frozenset({"rows", "dates"})),
    (
        "timestamp",
        f"UPDATE {FIXTURE_TABLE} SET observed = TIMESTAMP '2099-12-31 23:59:59' WHERE id = 2",
        frozenset({"rows", "timestamps"}),
    ),
    ("decimal", f"UPDATE {FIXTURE_TABLE} SET price = 99.999 WHERE id = 1", frozenset({"rows", "decimals"})),
    (
        "blob",
        f"UPDATE {FIXTURE_TABLE} SET digest = '\\xde\\xad'::BLOB WHERE id = 2",
        frozenset({"rows", "blobs"}),
    ),
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
# same protocol test_query_plane_boot.py verified: POST JSON, body is either a
# JSON array of row-objects or an Arrow IPC stream, per `type`). Kept local
# rather than imported cross-module -- this gate is a single self-contained
# file per the story's Never clause (no shared comparison framework). ---------


def _post_query(endpoint: str, sql: str, *, result_type: str = "json") -> bytes:
    request = urllib.request.Request(
        endpoint,
        data=json.dumps({"sql": sql, "type": result_type, "uuid": "face-parity"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310 — 127.0.0.1
        return response.read()


def _http_rows(endpoint: str, sql: str) -> list[dict[str, Any]]:
    """Read one query off the Arrow transport, decoded to the same Python
    objects DuckDB's own cursor yields (see the module docstring's transport
    note on why JSON cannot carry this fixture)."""
    with pa.ipc.open_stream(io.BytesIO(_post_query(endpoint, sql, result_type="arrow"))) as reader:
        return reader.read_all().to_pylist()


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
    importlib.util.find_spec("pkg") is None or importlib.util.find_spec("socketify") is None,
    reason="duckdb-server is not provisioned (the linux-64 pyforge-atlas pixi env carries it)",
)


# The shipped server, on a port of our choosing. `pkg/server.py` hard-codes
# `app.listen(3000, …)` and `pkg/__main__.py` takes only the DB path, so the
# port has to be bound at the socketify seam; everything that answers a query
# below is the installed server's own code.
_SERVER_ON_PORT = """\
import sys

import duckdb
from diskcache import Cache
from socketify import App

port = int(sys.argv[1])
db_path = sys.argv[2]

_listen = App.listen
App.listen = lambda self, _hardcoded, handler=None: _listen(self, port, handler)

from pkg.server import server

server(duckdb.connect(db_path), Cache())
"""


def _ephemeral_port() -> int:
    """Bind port 0, read back what the kernel gave us, release it."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _launcher_on_port(port: int) -> Callable[[Sequence[str]], subprocess.Popen[bytes]]:
    def launch(argv: Sequence[str]) -> subprocess.Popen[bytes]:
        db_path = list(argv)[1]
        return subprocess.Popen(  # noqa: S603 — fixed argv, no shell
            [sys.executable, "-c", _SERVER_ON_PORT, str(port), db_path]
        )

    return launch


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
    port = _ephemeral_port()
    boot = boot_query_plane(path, stack_up=stack_up, port=port, launcher=_launcher_on_port(port))
    try:
        if boot.http is None:
            notice = next(n for n in boot.notices if n["event"] == "http-face-not-raised")
            return {name: _compare(rows, None, reason=notice["reason"]) for name, rows in library_results.items()}
        _wait_until_ready(boot.http.process, boot.http.endpoint)
        return {
            name: _compare(library_results[name], _http_rows(boot.http.endpoint, sql)) for name, sql in queries
        }
    finally:
        _shutdown_boot(boot)


# --- I/O row: HAPPY_PATH + EMPTY_RESULT (one real boot; both faces up) -------


@requires_duckdb_server
def test_happy_path_rows_agree_row_for_row_including_empty_result(tmp_path: Path) -> None:
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
    # The widened fixture really did carry each type across the wire -- a gate
    # that agreed because both faces returned nothing would prove nothing.
    typed_row = report["rows"].library_rows[0]
    assert typed_row["released"] is not None
    assert typed_row["observed"] is not None
    assert typed_row["price"] is not None
    assert isinstance(typed_row["digest"], bytes)
    assert report["rows"].library_rows[2]["label"] is None


@requires_duckdb_server
def test_the_gate_runs_on_an_ephemeral_port_never_the_hard_coded_default(tmp_path: Path) -> None:
    """DW-FU-20-2-3: the port the boot reports is the one this test bound, so a
    machine already serving on 3000 cannot turn the gate into an opaque
    startup failure (nor, before, into a silent skip)."""
    from pyforge.atlas.query_plane_boot import DEFAULT_PORT

    path = _plane(tmp_path)
    _seed_fixture(path)
    port = _ephemeral_port()
    assert port != DEFAULT_PORT

    boot = boot_query_plane(path, stack_up=True, port=port, launcher=_launcher_on_port(port))
    try:
        assert boot.http is not None
        assert boot.http.endpoint == f"http://127.0.0.1:{port}/"
        _wait_until_ready(boot.http.process, boot.http.endpoint)
        assert _http_rows(boot.http.endpoint, f"SELECT id FROM {FIXTURE_TABLE} ORDER BY id") == [
            {"id": 1},
            {"id": 2},
            {"id": 3},
        ]
    finally:
        _shutdown_boot(boot)


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
@pytest.mark.parametrize(("kind", "mutation", "affected"), TYPED_DIVERGENCES, ids=[d[0] for d in TYPED_DIVERGENCES])
def test_seeded_divergence_in_each_typed_column_fails_and_names_it(
    tmp_path: Path, kind: str, mutation: str, affected: frozenset[str]
) -> None:
    """One divergence per widened type (NULL, DATE, TIMESTAMP, DECIMAL, BLOB):
    the gate must fail, and name exactly the queries that read that column."""
    path = _plane(tmp_path)
    _seed_fixture(path)

    # Capture the library face's snapshot BEFORE mutating the fixture.
    library_results = {name: _library_rows(path, sql) for name, sql in QUERIES}

    # Mutate one fixture column between the two captures -- a real divergence
    # between two snapshots of the plane (the single-writer-per-file
    # constraint rules out a literal simultaneous divergence; see the module
    # docstring), proving the comparator is not vacuous for this type.
    writer = connect_writer(path)
    try:
        writer.execute(mutation)
    finally:
        writer.close()

    port = _ephemeral_port()
    boot = boot_query_plane(path, stack_up=True, port=port, launcher=_launcher_on_port(port))
    try:
        assert boot.http is not None
        _wait_until_ready(boot.http.process, boot.http.endpoint)
        http_results = {name: _http_rows(boot.http.endpoint, sql) for name, sql in QUERIES}
    finally:
        _shutdown_boot(boot)

    report = {name: _compare(library_results[name], http_results[name]) for name, _ in QUERIES}

    # Exactly the queries reading the mutated column diverge; the unrelated
    # ones do not -- the gate names the affected queries, not everything.
    mismatches = {name for name, qp in report.items() if qp.status == "mismatch"}
    assert mismatches == set(affected), f"{kind} divergence flagged {sorted(mismatches)}, expected {sorted(affected)}"
    assert report["empty"].status == "match"

    with pytest.raises(AssertionError) as excinfo:
        _assert_parity(report)
    for name in sorted(affected):
        assert name in str(excinfo.value)
