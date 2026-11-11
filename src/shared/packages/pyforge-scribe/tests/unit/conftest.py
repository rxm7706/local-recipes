"""Shared fixtures for GraphStore tests (Story 28.1), and the one repository-root finder (Story 33.1).

Story 33.1 (spec-pyforge-scribe CAP-31): a test that reads the repository outside this package asks
``find_repo_root()`` (or the ``live_repo_root`` fixture) and its module carries ``pytestmark = pytest.mark.live_tree``;
nothing counts parents. The finder is called lazily, so with the package copied alone every module still imports
and the package half (``-m "not live_tree and not postgres"``) runs; a live-tree test run there fails, never skips.
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from pathlib import Path

import pytest

from pyforge.scribe.graph_store import FlatFileGraphStore, GraphStore

_DEFAULT_PG_DSN = "postgres://postgres:scribe@127.0.0.1:5433/scribe_graph"
# Story 41.3 / CAP-9: the driver no longer creates its own relations, so the
# test database is provisioned the way production is -- from the governed
# Liquibase changesets, which are the one source of this DDL.
_SCRIBE_CHANGESETS = "pyforge-scribe-*.sql"
# The header may carry Liquibase attributes after the id -- db/README.md's
# `runInTransaction:false` exception process mandates exactly that -- so the
# seq must not be anchored to end-of-line.
_CHANGESET_SEQ = re.compile(r"^--changeset\s+\S+?:([1-9][0-9]*)(?:\s|$)", re.MULTILINE)
_provisioned: set[str] = set()


def find_repo_root() -> Path:
    """The repository root: the nearest ancestor holding ``pixi.toml`` and ``.claude/skills``."""
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / ".claude" / "skills").is_dir():
            return candidate
    pytest.fail(
        f"{here} is not inside the repository (no ancestor holds pixi.toml and .claude/skills); "
        "a test that reads the live tree is marked live_tree and runs in the live-tree half"
    )


@pytest.fixture
def live_repo_root() -> Path:
    return find_repo_root()


def _changelog_dir() -> Path:
    return find_repo_root() / "src" / "platform" / "db" / "changelog" / "changes"


def _seq(path: Path) -> int:
    """The changeset's own seq — filename order is lexicographic (`10` < `2`)."""
    match = _CHANGESET_SEQ.search(path.read_text(encoding="utf-8"))
    if match is None:
        pytest.fail(f"{path.name} has no `--changeset <distribution>:<seq>` header")
    return int(match.group(1))


def _statements_in(path: Path) -> list[str]:
    """Forward SQL of one formatted-SQL changeset (``--rollback`` is a comment)."""
    body = "\n".join(
        line for line in path.read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("--")
    )
    return [statement.strip() for statement in body.split(";") if statement.strip()]


def scribe_changeset_paths() -> list[Path]:
    """Scribe's changeset files in changeset order, guarded ones excluded.

    Guarded changesets (``--preconditions``) are the operator's app-role
    grants: ``platform_app`` does not exist in a test database, and Liquibase
    itself skips them there (``onFail:CONTINUE``).
    """
    changelog_dir = _changelog_dir()
    paths = sorted(changelog_dir.glob(_SCRIBE_CHANGESETS), key=_seq)
    if not paths:
        pytest.fail(
            f"scribe's Liquibase changesets are missing from {changelog_dir}; "
            "the durable GraphStore has no other source of DDL (Story 41.3)"
        )
    return [path for path in paths if "--preconditions" not in path.read_text(encoding="utf-8")]


def apply_scribe_changesets(dsn: str) -> None:
    """Apply scribe's changesets to ``dsn`` — idempotent, like Liquibase."""
    import psycopg

    with psycopg.connect(dsn) as conn:
        for path in scribe_changeset_paths():
            for statement in _statements_in(path):
                conn.execute(statement)
        conn.commit()


def _provision(dsn: str) -> None:
    if dsn in _provisioned:
        return
    apply_scribe_changesets(dsn)
    _provisioned.add(dsn)


def require_pg_dsn() -> str:
    dsn = (os.environ.get("SCRIBE_GRAPH_DSN") or _DEFAULT_PG_DSN).split("?", 1)[0]
    try:
        import psycopg

        with psycopg.connect(dsn) as conn:
            conn.execute("SELECT 1")
            row = conn.execute("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'").fetchone()
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"durable GraphStore requires PostgreSQL with pgvector at {dsn}: {exc}")
    if row is None:
        pytest.fail(f"durable GraphStore requires CREATE EXTENSION vector at {dsn}")
    _provision(dsn)
    return dsn


@pytest.fixture
def pg_dsn() -> str:
    return require_pg_dsn()


@pytest.fixture
def apply_changesets() -> Callable[[str], None]:
    """Re-apply the governed changesets — for tests that mutate the shape."""
    return apply_scribe_changesets


StoreFactory = Callable[[], GraphStore]


#: Story 33.1: the postgres param needs the server and reads the host's changesets, so it carries both marks and the
#: flat-file param stays in the package half.
@pytest.fixture(params=["flatfile", pytest.param("postgres", marks=[pytest.mark.live_tree, pytest.mark.postgres])])
def graph_store_factory(request: pytest.FixtureRequest, tmp_path: Path) -> StoreFactory:
    kind = request.param
    if kind == "flatfile":
        path = tmp_path / "graph.json"

        def _flat() -> GraphStore:
            return FlatFileGraphStore(path)

        return _flat

    from pyforge.scribe.graph_store_pg import PostgresGraphStore

    dsn = require_pg_dsn()
    path = tmp_path / "durable-must-not-be-json"

    def _pg() -> GraphStore:
        return PostgresGraphStore(dsn, path)

    return _pg
