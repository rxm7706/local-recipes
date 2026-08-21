"""Story 11.4 -- isolation and statelessness proven (CAP-2/CAP-3, AD-16).

Epic 11 claims two guarantees for both AD-17 integration patterns --
cross-engine schema isolation (each engine's tables live only in its own
schema) and statelessness (killing/replacing an engine's compute unit loses
no flow, session, or state) -- but until this file, nothing proved either
claim. Story 9.6's own discipline applies here too: "an isolation/
statelessness suite that cannot fail is a failing suite" -- so every real
proof below has a "guard removed" companion (a small, LOCALLY-defined
reproduction of what the guard's absence would do, never a monkeypatch of
real production code, mirroring `test_dashboard_isolation_proof.py`'s
established convention) that proves the real proof's own assertion logic
would actually catch a regression.

Three claims, six tests:

1. Cross-engine schema isolation (real Postgres, no container -- AD-16
   Tier 1): drives Langflow's real Alembic bootstrap via the shared
   `_LifespanManager` (`langflow_integration.asgi`), then inspects
   `public`/`langflow_schema`/`dbgpt_schema` together via `pg_tables`.

2. Pattern-A container-replacement statelessness, simulated in-process (real
   Postgres, no container -- AD-16 Tier 1, matches "in-process" story
   wording): two independent `_LifespanManager` cycles against Langflow's
   real ASGI app -- a flow created+run in the first, re-fetched in a second,
   fully independent one.

3. Pattern-B sidecar container-replacement statelessness: a real
   `docker compose kill`+`start` of the actual `dbgpt` service (AD-16 Tier
   2, container engine required) proving a marker row in the shared
   `dbgpt_schema` survives -- deliberately opt-in gated
   (`PLATFORM_DOCKER_COMPOSE_TESTS=1` + `docker` on PATH), matching this
   project's own precedent (spec-11-2's "Manual checks") of live
   docker-compose round trips being verified once, not wired into the
   pip-only CI `test` job. Its guard-removed companion is NOT gated -- it
   needs no docker/postgres and must always run.

Requires the `langflow` package (`python-agent-platform`/`platform-dev`
pixi env) for claim 1's real Alembic bootstrap and claim 2's ASGI cycles;
gated the same way `test_asgi_seam.py`/`test_langflow_mount.py` gate their
whole module.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import time
from http import HTTPStatus
from pathlib import Path

import pytest

pytest.importorskip("langflow")

import psycopg
from django.conf import settings

# Same base-DSN-without-query-string rationale as langflow_integration/
# tests.py's `_TEST_DSN` and dbgpt_integration/tests.py's own copy: both
# connections below are already schema-qualified, so `search_path` isn't
# needed, and psycopg's own stricter URI parser rejects the unescaped `=`
# inside the `?options=` suffix that SQLAlchemy's parser (what Langflow/
# DB-GPT's own engines use) accepts fine.
_LANGFLOW_TEST_DSN = settings.LANGFLOW_DATABASE_URL.split("?", 1)[0]
_DBGPT_TEST_DSN = settings.DBGPT_DATABASE_URL.split("?", 1)[0]

# src/platform/tests/../compose/compose.yml == src/platform/compose/compose.yml
_COMPOSE_FILE = Path(__file__).resolve().parents[1] / "compose" / "compose.yml"


# ---------------------------------------------------------------------------
# Shared "guard removed" fixture -- state tied to one compute unit's lifetime
# ---------------------------------------------------------------------------


def _assert_state_survived_kill_and_restart(value: object, what: str) -> None:
    """Shared statelessness assertion: `value` must be non-`None`, where the
    caller is responsible for making `value` itself `None` whenever `what`
    did NOT survive the kill+restart cycle it is checking.
    """
    assert value is not None, f"{what} did not survive the kill+restart cycle"


class _InProcessOnlyStore:
    """Local reproduction of state tied to one compute unit's lifetime --
    what EITHER AD-17 pattern's statelessness guarantee would degrade to if
    engine state lived in the compute unit's own process memory instead of
    externally-shared storage (Postgres). What both patterns' guarantee
    actually rests on is identical (Design Notes), so this one class stands
    in for a killed-and-replaced in-process worker (Pattern A) exactly as
    well as a killed-and-replaced sidecar container (Pattern B). Never a
    monkeypatch of real production code.
    """

    def __init__(self) -> None:
        self._data: dict[str, object] = {}

    def write(self, key: str, value: object) -> None:
        self._data[key] = value

    def read(self, key: str) -> object | None:
        return self._data.get(key)

    def simulate_process_kill_and_fresh_start(self) -> None:
        """What happens to in-process-only memory when the compute unit
        holding it (a worker process, or a sidecar container) is killed
        and replaced: it's simply gone.
        """
        self._data = {}


# ---------------------------------------------------------------------------
# 1. Cross-engine schema isolation (AC1/AC2)
# ---------------------------------------------------------------------------


def _assert_each_engines_tables_are_confined_to_their_own_schema(
    rows: list[tuple[str, str]],
) -> None:
    """`rows`: `(schema, table)` tuples spanning `public`/`langflow_schema`/
    `dbgpt_schema`. No table name may appear in more than one schema, and
    `langflow_schema` must be demonstrably non-empty (not a vacuous pass).
    """
    by_schema: dict[str, set[str]] = {}
    for schema, table in rows:
        by_schema.setdefault(schema, set()).add(table)

    assert by_schema.get("langflow_schema"), (
        "langflow_schema has no tables -- this isolation check would pass vacuously"
    )

    owner_schema: dict[str, str] = {}
    leaked: list[tuple[str, str, str]] = []
    for schema, tables in by_schema.items():
        for table in tables:
            if table in owner_schema and owner_schema[table] != schema:
                leaked.append((table, owner_schema[table], schema))
            else:
                owner_schema[table] = schema
    assert not leaked, (
        f"tables leaked across schemas (table, first-schema, also-in): {leaked}"
    )


def _ensure_langflow_schema() -> None:
    with psycopg.connect(_LANGFLOW_TEST_DSN) as conn, conn.cursor() as cursor:
        cursor.execute("CREATE SCHEMA IF NOT EXISTS langflow_schema;")


def _ensure_dbgpt_schema() -> None:
    with psycopg.connect(_DBGPT_TEST_DSN) as conn, conn.cursor() as cursor:
        cursor.execute("CREATE SCHEMA IF NOT EXISTS dbgpt_schema;")


def _fetch_all_three_schemas_tables() -> list[tuple[str, str]]:
    with psycopg.connect(_LANGFLOW_TEST_DSN) as conn, conn.cursor() as cursor:
        cursor.execute(
            "SELECT schemaname, tablename FROM pg_tables "
            "WHERE schemaname IN ('public', 'langflow_schema', 'dbgpt_schema')",
        )
        return cursor.fetchall()


async def _drive_langflow_alembic_bootstrap() -> None:
    from langflow_integration.asgi import _LifespanManager  # noqa: PLC0415
    from langflow_integration.asgi import langflow_application  # noqa: PLC0415

    async with _LifespanManager(langflow_application):
        pass


def test_each_engines_tables_are_confined_to_their_own_schema():
    """AC1: with Langflow's real Alembic bootstrap driven once and
    `dbgpt_schema` present, `public`/`langflow_schema`/`dbgpt_schema`
    inspected together show no table name in more than one schema.
    """
    _ensure_langflow_schema()
    _ensure_dbgpt_schema()
    asyncio.run(_drive_langflow_alembic_bootstrap())

    rows = _fetch_all_three_schemas_tables()

    _assert_each_engines_tables_are_confined_to_their_own_schema(rows)


def test_schema_isolation_check_fails_if_a_table_leaks_into_another_schema():
    """AC2 (9.6 discipline): synthetic rows with a deliberate `public`/
    `langflow_schema` name collision, fed to the same assertion helper the
    real test above uses, must raise.
    """
    contaminated_rows = [
        ("public", "flow"),
        ("langflow_schema", "flow"),
        ("langflow_schema", "vertex_build"),
    ]

    with pytest.raises(AssertionError):
        _assert_each_engines_tables_are_confined_to_their_own_schema(contaminated_rows)


# ---------------------------------------------------------------------------
# 2. Pattern-A container-replacement statelessness, in-process (AC3/AC4)
# ---------------------------------------------------------------------------


def _build_text_only_flow_data(seed_text: str) -> dict:
    """A deterministic, zero-external-dependency flow -- duplicated locally
    from langflow_integration/tests.py's helper of the same name (this
    package's established no-shared-conftest convention).
    """
    from lfx.components.input_output.text import TextInputComponent  # noqa: PLC0415
    from lfx.components.input_output.text_output import (  # noqa: PLC0415
        TextOutputComponent,
    )
    from lfx.graph import Graph  # noqa: PLC0415

    text_input = TextInputComponent()
    text_input.set(input_value=seed_text)
    text_output = TextOutputComponent()
    text_output.set(input_value=text_input.text_response)

    graph = Graph(start=text_input, end=text_output)
    return graph.dump(name="s11-4-pattern-a-probe")["data"]


async def _cycle_one_create_and_run_flow() -> str:
    """Cycle 1: enter a FRESH `_LifespanManager`, log in, create+run a flow,
    return its id. This `async with` block exits before this coroutine
    returns, genuinely tearing down Langflow's DB/cache services -- this IS
    "kill the process/worker" (see `langflow_integration/asgi.py`'s module
    docstring).
    """
    from httpx import ASGITransport  # noqa: PLC0415
    from httpx import AsyncClient  # noqa: PLC0415

    from langflow_integration.asgi import _LifespanManager  # noqa: PLC0415
    from langflow_integration.asgi import langflow_application  # noqa: PLC0415

    seed_text = "s11-4 pattern-a kill+restart probe"
    base_url = "http://testserver"
    async with _LifespanManager(langflow_application):
        transport = ASGITransport(app=langflow_application)
        async with AsyncClient(transport=transport, base_url=base_url) as client:
            login = await client.get("/api/v1/auto_login")
            assert login.status_code == HTTPStatus.OK, login.text
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

            flow_data = _build_text_only_flow_data(seed_text)
            created = await client.post(
                "/api/v1/flows/",
                json={"name": "s11-4-pattern-a-probe", "data": flow_data},
                headers=headers,
            )
            assert created.status_code == HTTPStatus.CREATED, created.text
            flow_id = created.json()["id"]

            key_resp = await client.post(
                "/api/v1/api_key/",
                json={"name": "s11-4-pattern-a-probe-key"},
                headers=headers,
            )
            assert key_resp.status_code == HTTPStatus.OK, key_resp.text
            api_key = key_resp.json()["api_key"]

            run_payload = {
                "input_value": seed_text,
                "input_type": "text",
                "output_type": "text",
            }
            run_resp = await client.post(
                f"/api/v1/run/{flow_id}",
                json=run_payload,
                headers={"x-api-key": api_key},
            )
            assert run_resp.status_code == HTTPStatus.OK, run_resp.text

    return flow_id


async def _cycle_two_refetch_flow(flow_id: str) -> str | None:
    """Cycle 2: a SECOND, fully independent `_LifespanManager` instance, a
    fresh `auto_login`, and a `GET` for the same flow id. Returns the id if
    the flow record survived cycle 1's teardown, `None` otherwise.
    """
    from httpx import ASGITransport  # noqa: PLC0415
    from httpx import AsyncClient  # noqa: PLC0415

    from langflow_integration.asgi import _LifespanManager  # noqa: PLC0415
    from langflow_integration.asgi import langflow_application  # noqa: PLC0415

    base_url = "http://testserver"
    async with _LifespanManager(langflow_application):
        transport = ASGITransport(app=langflow_application)
        async with AsyncClient(transport=transport, base_url=base_url) as client:
            login = await client.get("/api/v1/auto_login")
            assert login.status_code == HTTPStatus.OK, login.text
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

            fetched = await client.get(f"/api/v1/flows/{flow_id}", headers=headers)
            if fetched.status_code != HTTPStatus.OK:
                return None
            return fetched.json().get("id")


def _fetch_flow_write_path_rows(flow_id: str) -> dict[str, int]:
    """Duplicated locally from langflow_integration/tests.py's helper of the
    same name, trimmed to the two write-path tables this claim cares about.
    """
    queries = {
        "vertex_build": (
            "SELECT count(*) FROM langflow_schema.vertex_build WHERE flow_id = %s"
        ),
        "transaction": (
            "SELECT count(*) FROM langflow_schema.transaction WHERE flow_id = %s"
        ),
    }
    with psycopg.connect(_LANGFLOW_TEST_DSN) as conn, conn.cursor() as cursor:
        counts = {}
        for table, query in queries.items():
            cursor.execute(query, (flow_id,))
            counts[table] = cursor.fetchone()[0]
        return counts


def test_pattern_a_kill_and_fresh_start_loses_no_flow_state():
    """AC3: a flow created+run inside one `_LifespanManager` cycle survives
    that cycle exiting (simulating the process/pod being killed) -- a
    second, independent cycle still sees the flow record and its unchanged
    write-path row counts.
    """
    flow_id = asyncio.run(_cycle_one_create_and_run_flow())

    counts_after_cycle_one = _fetch_flow_write_path_rows(flow_id)
    assert counts_after_cycle_one["vertex_build"] >= 1, (
        "no vertex_build rows after cycle 1 -- the flow never actually ran, "
        "so this test would prove nothing"
    )
    assert counts_after_cycle_one["transaction"] >= 1, (
        "no transaction rows after cycle 1 -- the flow never actually ran, "
        "so this test would prove nothing"
    )

    fetched_flow_id = asyncio.run(_cycle_two_refetch_flow(flow_id))
    counts_after_cycle_two = _fetch_flow_write_path_rows(flow_id)

    counts_unchanged = counts_after_cycle_two == counts_after_cycle_one
    counts_survived = counts_after_cycle_two if counts_unchanged else None
    _assert_state_survived_kill_and_restart(fetched_flow_id, "the flow record")
    _assert_state_survived_kill_and_restart(
        counts_survived,
        "the flow's write-path row counts (vertex_build/transaction)",
    )


def test_pattern_a_statelessness_check_fails_if_state_were_held_in_process_memory_only():  # noqa: E501
    """AC4 (9.6 discipline): the Pattern-A real test's own assertion helper,
    fed a local in-process-only store that a "kill+restart" simulation
    wipes, must raise -- proving that assertion would actually catch a
    regression where Langflow's state secretly lived in process memory
    instead of PostgreSQL.
    """
    store = _InProcessOnlyStore()
    store.write("flow-id", "s11-4-pattern-a-in-process-only-probe")

    store.simulate_process_kill_and_fresh_start()

    with pytest.raises(AssertionError):
        _assert_state_survived_kill_and_restart(
            store.read("flow-id"), "the in-process-only store's value",
        )


# ---------------------------------------------------------------------------
# 3. Pattern-B sidecar container-replacement statelessness (AC5/AC6)
# ---------------------------------------------------------------------------

_DOCKER_AVAILABLE = shutil.which("docker") is not None
_DOCKER_COMPOSE_OPT_IN = os.environ.get("PLATFORM_DOCKER_COMPOSE_TESTS") == "1"

requires_docker_compose = pytest.mark.skipif(
    not (_DOCKER_AVAILABLE and _DOCKER_COMPOSE_OPT_IN),
    reason=(
        "opt-in only (AD-16 Tier 2): set PLATFORM_DOCKER_COMPOSE_TESTS=1 with "
        "docker on PATH to run the real docker-compose kill+start round trip "
        "against the dbgpt sidecar"
    ),
)


def _compose(*args: str, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 -- fixed argv, no shell, no untrusted input
        ["docker", "compose", "-f", str(_COMPOSE_FILE), *args],  # noqa: S607
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _dbgpt_container_id() -> str | None:
    result = _compose("ps", "-aq", "dbgpt")
    container_id = result.stdout.strip()
    return container_id or None


def _dbgpt_health_status() -> str | None:
    container_id = _dbgpt_container_id()
    if not container_id:
        return None
    result = subprocess.run(  # noqa: S603 -- fixed argv, no shell, no untrusted input
        ["docker", "inspect", "--format", "{{.State.Health.Status}}", container_id],  # noqa: S607
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _wait_for_dbgpt_healthy(timeout: float = 120) -> None:
    """Bounded wait (spec's own "Block If" bound). A failure to reach
    healthy in time is treated as an environment problem, not a spec
    ambiguity -- `pytest.fail` names exactly that.
    """
    deadline = time.monotonic() + timeout
    status = None
    while time.monotonic() < deadline:
        status = _dbgpt_health_status()
        if status == "healthy":
            return
        time.sleep(2)
    pytest.fail(
        f"dbgpt did not reach healthy within {timeout}s (last status: {status!r}) "
        f"-- environment problem, not a spec ambiguity (this story's spec, 'Block If')",
    )


def _ensure_dbgpt_probe_table() -> None:
    with psycopg.connect(_DBGPT_TEST_DSN) as conn, conn.cursor() as cursor:
        cursor.execute("CREATE SCHEMA IF NOT EXISTS dbgpt_schema;")
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS dbgpt_schema._container_replacement_probe "
            "(marker text primary key);",
        )


def _write_dbgpt_marker(marker: str) -> None:
    with psycopg.connect(_DBGPT_TEST_DSN) as conn, conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO dbgpt_schema._container_replacement_probe (marker) "
            "VALUES (%s) ON CONFLICT (marker) DO NOTHING;",
            (marker,),
        )


def _dbgpt_marker_exists(marker: str) -> bool:
    with psycopg.connect(_DBGPT_TEST_DSN) as conn, conn.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM dbgpt_schema._container_replacement_probe WHERE marker = %s",
            (marker,),
        )
        return cursor.fetchone() is not None


def _drop_dbgpt_probe_table() -> None:
    """Drops the probe table outright (not just the marker row): leaving an
    empty `_container_replacement_probe` table behind would itself violate
    `dbgpt_integration/tests.py::test_dbgpt_schema_exists_with_zero_django_
    orm_tables`'s own "zero tables in dbgpt_schema" invariant -- confirmed
    live, this is exactly what happened before this helper existed.
    """
    with psycopg.connect(_DBGPT_TEST_DSN) as conn, conn.cursor() as cursor:
        cursor.execute(
            "DROP TABLE IF EXISTS dbgpt_schema._container_replacement_probe;",
        )


@requires_docker_compose
def test_pattern_b_sidecar_kill_and_restart_preserves_shared_dbgpt_schema_state():
    """AC5 (opt-in, AD-16 Tier 2): a marker row written into the real,
    shared `dbgpt_schema` survives a real `docker compose kill`+`start` of
    the actual `dbgpt` service (same container id, not recreated -- `kill`+
    `start` reuses the container, unlike `up` again). Always cleans up
    (removes the container, drops the probe table) regardless of outcome.
    """
    marker = "s11-4-pattern-b-container-replacement-probe"
    _ensure_dbgpt_probe_table()
    _write_dbgpt_marker(marker)

    try:
        up = _compose("up", "-d", "dbgpt")
        assert up.returncode == 0, f"docker compose up -d dbgpt failed:\n{up.stderr}"
        _wait_for_dbgpt_healthy()

        container_before = _dbgpt_container_id()

        kill = _compose("kill", "dbgpt")
        assert kill.returncode == 0, f"docker compose kill dbgpt failed:\n{kill.stderr}"

        start = _compose("start", "dbgpt")
        assert start.returncode == 0, (
            f"docker compose start dbgpt failed:\n{start.stderr}"
        )
        _wait_for_dbgpt_healthy()

        container_after = _dbgpt_container_id()
        assert container_after == container_before, (
            "kill+start recreated the dbgpt container (different id) instead "
            "of reusing it -- this test's own premise no longer holds"
        )

        _assert_state_survived_kill_and_restart(
            marker if _dbgpt_marker_exists(marker) else None,
            "the dbgpt_schema marker row",
        )
    finally:
        # `kill` alone stops the container but leaves it in `docker compose
        # ps -a` as "Exited" -- `rm -f` removes it outright, so a real run
        # never leaves anything lingering (this story's spec, Manual checks).
        _compose("kill", "dbgpt")
        _compose("rm", "-f", "dbgpt")
        _drop_dbgpt_probe_table()


def test_pattern_b_statelessness_check_fails_if_state_were_tied_to_the_sidecar_containers_own_storage():  # noqa: E501
    """AC6 (9.6 discipline, always-on -- NOT gated behind docker/opt-in, so
    it still runs in the pip-only CI `test` job where Tier 2 is
    unavailable): reuses `_InProcessOnlyStore` -- it already correctly
    models "state tied to one compute unit's lifetime, wiped when that unit
    is replaced", which applies to a sidecar container being replaced
    exactly as well as an in-process worker being killed (Design Notes).
    """
    store = _InProcessOnlyStore()
    store.write("dbgpt-marker", "s11-4-pattern-b-in-process-only-probe")

    store.simulate_process_kill_and_fresh_start()

    with pytest.raises(AssertionError):
        _assert_state_survived_kill_and_restart(
            store.read("dbgpt-marker"), "the sidecar-local-only store's value",
        )
