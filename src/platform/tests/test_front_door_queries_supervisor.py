"""Steward 21.5 — front door queries the supervisor (FR-40, FR-41, FR-42)."""

from __future__ import annotations

import ast
import time
from datetime import timedelta
from http import HTTPStatus
from pathlib import Path

import pytest
from django.core.cache import cache
from django.db import connection
from django.db import connections
from django.db.utils import OperationalError
from django.utils import timezone
from django_pyforge.models import RunState
from django_pyforge.supervisor import LAST_OK_CACHE_KEY
from django_pyforge.supervisor import QUERY_BUDGET_SECONDS
from django_pyforge.supervisor import SupervisorUnavailableError
from django_pyforge.supervisor import complete_run
from django_pyforge.supervisor import query_board

from platformapp.front_door.views import age_label

PLATFORM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLATFORM_ROOT.parents[1]
CHROME_ROOT = (
    REPO_ROOT
    / "src"
    / "shared"
    / "packages"
    / "django-pyforge"
    / "src"
    / "django_pyforge"
)
FRONT_DOOR_ROOT = PLATFORM_ROOT / "platformapp" / "front_door"
SUPERVISOR_PATH = CHROME_ROOT / "supervisor.py"
VIEWS_PATH = FRONT_DOOR_ROOT / "views.py"


def _scrape_literals(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            lowered = node.value.lower()
            if "bmad-loops" in lowered:
                hits.append(node.value)
            pathish = "/" in node.value or "~" in node.value
            if pathish and ("tmux" in lowered or "journal" in lowered):
                hits.append(node.value)
    return hits


@pytest.mark.django_db
def test_runs_board_lists_supervisor_rows(client) -> None:
    live = RunState.objects.create(
        station="atlas",
        status=RunState.Status.RUNNING,
        started_at=timezone.now(),
        heartbeat_at=timezone.now(),
    )
    response = client.get("/runs/")
    assert response.status_code == HTTPStatus.OK
    body = response.content.decode()
    assert 'data-board="current"' in body
    assert str(live.id) in body
    assert "unavailable" not in body


@pytest.mark.django_db(transaction=True)
def test_run_from_other_connection_is_visible_on_runs(client) -> None:
    replica = connections.create_connection("default")
    try:
        runs = replica.ops.quote_name("run_state")
        run = RunState.objects.create(
            station="herald",
            status=RunState.Status.RUNNING,
            started_at=timezone.now(),
            heartbeat_at=timezone.now(),
        )
        with replica.cursor() as cursor:
            cursor.execute(
                f"SELECT id FROM {runs} WHERE id = %s",  # noqa: S608
                [run.id],
            )
            assert cursor.fetchone() is not None
    finally:
        replica.close()
    body = client.get("/runs/").content.decode()
    assert str(run.id) in body
    assert 'data-board="current"' in body


@pytest.mark.django_db
def test_timing_ingested_at_complete_is_queryable_across_runs(client) -> None:
    first = RunState.objects.create(
        station="atlas",
        status=RunState.Status.RUNNING,
        started_at=timezone.now() - timedelta(seconds=2),
    )
    second = RunState.objects.create(
        station="warden",
        status=RunState.Status.RUNNING,
        started_at=timezone.now() - timedelta(seconds=1),
    )
    complete_run(str(first.id), status=RunState.Status.SUCCEEDED, result={"a": 1})
    complete_run(str(second.id), status=RunState.Status.FAILED, result={"b": 2})
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.completed_at is not None
    assert second.completed_at is not None
    assert first.duration_ms is not None
    assert second.duration_ms is not None
    body = client.get("/runs/").content.decode()
    assert str(first.id) in body
    assert str(second.id) in body
    assert f'data-duration-ms="{first.duration_ms}"' in body
    assert f'data-duration-ms="{second.duration_ms}"' in body


@pytest.mark.django_db
def test_empty_success_is_current_not_unavailable(client) -> None:
    RunState.objects.all().delete()
    body = client.get("/runs/").content.decode()
    assert 'data-board="current"' in body
    assert "unavailable" not in body
    assert 'class="empty"' in body


@pytest.mark.django_db
def test_unreachable_renders_unavailable_plus_age_not_empty_current(
    monkeypatch,
    client,
) -> None:
    cache.set(LAST_OK_CACHE_KEY, timezone.now() - timedelta(seconds=12))

    def boom() -> tuple:
        raise OperationalError

    monkeypatch.setattr("django_pyforge.supervisor.load_board_rows", boom)
    started = time.monotonic()
    response = client.get("/runs/")
    elapsed = time.monotonic() - started
    assert elapsed < QUERY_BUDGET_SECONDS + 1
    body = response.content.decode()
    assert 'data-board="unavailable"' in body
    assert "unavailable" in body
    assert 'data-age="12s"' in body or 'data-age="13s"' in body
    assert 'data-board="current"' not in body
    assert "Live runs" not in body


@pytest.mark.django_db
def test_unreachable_without_last_ok_age_is_never(monkeypatch, client) -> None:
    cache.delete(LAST_OK_CACHE_KEY)

    def boom() -> tuple:
        raise OperationalError

    monkeypatch.setattr("django_pyforge.supervisor.load_board_rows", boom)
    body = client.get("/runs/").content.decode()
    assert 'data-age="never"' in body
    assert "unavailable" in body


@pytest.mark.django_db
def test_query_board_timeout_is_unavailable(monkeypatch) -> None:
    def boom() -> tuple:
        raise TimeoutError

    monkeypatch.setattr("django_pyforge.supervisor.load_board_rows", boom)
    started = time.monotonic()
    with pytest.raises(SupervisorUnavailableError):
        query_board()
    elapsed = time.monotonic() - started
    assert elapsed < QUERY_BUDGET_SECONDS + 1


@pytest.mark.django_db
def test_successful_board_then_unavailable_uses_written_last_ok(
    monkeypatch,
    client,
) -> None:
    cache.delete(LAST_OK_CACHE_KEY)
    ok = client.get("/runs/")
    assert 'data-board="current"' in ok.content.decode()

    def boom() -> tuple:
        raise OperationalError

    monkeypatch.setattr("django_pyforge.supervisor.load_board_rows", boom)
    body = client.get("/runs/").content.decode()
    assert 'data-board="unavailable"' in body
    assert 'data-age="never"' not in body


@pytest.mark.django_db
def test_query_board_sets_statement_timeout() -> None:
    if connection.vendor != "postgresql":
        pytest.skip("statement_timeout is PostgreSQL")
    seen: list[str] = []

    def wrapper(execute, sql, params, many, context):
        seen.append(sql)
        return execute(sql, params, many, context)

    with connection.execute_wrapper(wrapper):
        query_board()
    assert any("statement_timeout" in sql for sql in seen)


@pytest.mark.django_db
def test_iso_last_ok_from_cache_is_usable(monkeypatch, client) -> None:
    stamped = timezone.now() - timedelta(seconds=4)
    cache.set(LAST_OK_CACHE_KEY, stamped.isoformat(), timeout=None)

    def boom() -> tuple:
        raise OperationalError

    monkeypatch.setattr("django_pyforge.supervisor.load_board_rows", boom)
    body = client.get("/runs/").content.decode()
    assert 'data-board="unavailable"' in body
    assert 'data-age="never"' not in body


def test_age_label_never_and_seconds() -> None:
    now = timezone.now()
    assert age_label(None, now=now) == "never"
    earlier = now - timedelta(seconds=7)
    assert age_label(earlier, now=now) == "7s"


def test_front_door_and_supervisor_do_not_scrape_laptop_state() -> None:
    hits: list[str] = []
    for path in (VIEWS_PATH, SUPERVISOR_PATH):
        hits.extend(_scrape_literals(path))
    assert hits == []
    views = VIEWS_PATH.read_text(encoding="utf-8")
    assert "query_board" in views
    assert "RunState.objects" not in views
    assert "Path.home" not in views
