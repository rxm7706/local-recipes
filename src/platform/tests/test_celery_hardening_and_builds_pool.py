"""Story 42.4 — Celery hardening and the builds pool.

Red-team S-2 (Celery was at-most-once by configuration: no ``acks_late``, no
``reject_on_worker_lost``, one queue for eight stations, so a SIGKILL'd worker
dropped its task with the RunState row RUNNING forever and a Mason build flood
starved Doctor remedies) and T-6 (a 300 s ceiling on every task, so nothing
hours-scale could run at all). Directive **R-10**.

Four things are proven here, each against the seam that carries it:

* delivery is at-least-once, and a re-delivered task runs exactly once more
  (``django_pyforge.tasks`` + ``supervisor.begin_attempt``);
* the routing table, through Celery's OWN router (``app.amqp.router``) rather
  than the chrome function alone, so the settings wiring is part of the proof;
* the chart's ``worker.queues`` mirrors the chrome's table (ungated, PyYAML
  only) -- the rendered Deployments are proven in ``test_chart_invariants``;
* the worker-lost sweep (``supervisor.sweep_lost_runs``), per-station limit,
  inspect-gated, scheduled, and runnable by hand.
"""

from __future__ import annotations

import ast
import json
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import pytest
from celery import current_app
from django.core.management import call_command
from django.utils import timezone
from django_pyforge import queues
from django_pyforge import supervisor
from django_pyforge.models import RunState
from django_pyforge.queues import ALL_QUEUES
from django_pyforge.queues import BUILDS_QUEUE
from django_pyforge.queues import DEFAULT_QUEUE
from django_pyforge.queues import PRIORITY_QUEUE
from django_pyforge.queues import PRUNE_RUN_STATE_TASK
from django_pyforge.queues import STATION_QUEUES
from django_pyforge.queues import SUPERVISED_RUN_TASK
from django_pyforge.queues import SWEEP_LOST_RUNS_TASK
from django_pyforge.queues import TASK_ROUTES
from django_pyforge.queues import TOOL_ROUTES
from django_pyforge.queues import WORKER_QUEUES
from django_pyforge.queues import station_time_limit
from django_pyforge.supervisor import REDELIVERED_KEY
from django_pyforge.supervisor import WORKER_LOST_REASON
from django_pyforge.supervisor import begin_attempt
from django_pyforge.supervisor import register_runner
from django_pyforge.supervisor import sweep_lost_runs
from django_pyforge.tasks import execute_supervised_run
from django_pyforge.tasks import redelivered

if TYPE_CHECKING:
    from collections.abc import Iterator

PLATFORM_ROOT = Path(__file__).resolve().parents[1]
BASE_SETTINGS_PATH = PLATFORM_ROOT / "config" / "settings" / "base.py"
CORE_CHART_VALUES = PLATFORM_ROOT / "deploy" / "charts" / "platform" / "values.yaml"

STATION = "atlas"
TOOL = "run_pipeline"
AGENT = "agent-42-4"
GENERAL_LIMIT_SECONDS = 5 * 60
ONE_HOUR_SECONDS = 3600


class _WorkerKilled(BaseException):
    """Stands in for SIGKILL: not an ``Exception``, so the task's ``except``
    never runs -- exactly what a killed pool child looks like to the ledger."""


@contextmanager
def _redelivered_message(task: Any) -> Iterator[None]:
    """Run ``task.run`` under the request kombu builds when it restores an
    unacked message (``delivery_info.redelivered`` is what the Redis
    transport sets on the re-delivery)."""
    task.push_request(delivery_info={"redelivered": True})
    try:
        yield
    finally:
        task.pop_request()


def _live_run(
    *,
    station: str = STATION,
    status: str = RunState.Status.RUNNING,
    last_seen_ago: timedelta = timedelta(0),
    started_ago: timedelta | None = None,
) -> RunState:
    now = timezone.now()
    started = now - (started_ago if started_ago is not None else last_seen_ago)
    return RunState.objects.create(
        status=status,
        station=station,
        subject=AGENT,
        celery_task_id=f"task-{station}-{now.timestamp()}-{RunState.objects.count()}",
        started_at=started,
        heartbeat_at=now - last_seen_ago,
    )


class _Inspector:
    """A ``control.inspect()`` double: what each worker reports holding."""

    def __init__(
        self,
        *,
        active: dict[str, list[dict[str, Any]]] | None = None,
        reserved: dict[str, list[dict[str, Any]]] | None = None,
        scheduled: dict[str, list[dict[str, Any]]] | None = None,
        raises: Exception | None = None,
    ) -> None:
        self._active = active
        self._reserved = reserved
        self._scheduled = scheduled
        self._raises = raises
        self.calls: list[str] = []

    def _answer(self, name: str, value: Any) -> Any:
        self.calls.append(name)
        if self._raises is not None:
            raise self._raises
        return value

    def active(self) -> Any:
        return self._answer("active", self._active)

    def reserved(self) -> Any:
        return self._answer("reserved", self._reserved)

    def scheduled(self) -> Any:
        return self._answer("scheduled", self._scheduled)


def _nobody_holds_anything() -> _Inspector:
    return _Inspector(active={}, reserved={}, scheduled={})


def _settings_assignment(name: str) -> ast.expr:
    tree = ast.parse(BASE_SETTINGS_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if name in {t.id for t in node.targets if isinstance(t, ast.Name)}:
            return node.value
    msg = f"config/settings/base.py assigns no {name}"
    raise AssertionError(msg)


def _env_int_settings(text: str) -> set[str]:
    """Settings assigned from ``env.int("<same name>", default=...)`` (the
    42.2 convention: a knob is a self-named, env-overridable setting)."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(text)):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        func = node.value.func
        if not (isinstance(func, ast.Attribute) and func.attr == "int"):
            continue
        args = node.value.args
        if not args or not isinstance(args[0], ast.Constant):
            continue
        targets = {t.id for t in node.targets if isinstance(t, ast.Name)}
        names |= {name for name in targets if name == args[0].value}
    return names


# ---------------------------------------------------------------------------
# AC 1 -- at-least-once delivery; a killed worker's task re-runs exactly once
# ---------------------------------------------------------------------------


def test_delivery_is_at_least_once_by_configuration() -> None:
    """S-2 was "at-most-once by configuration". The three knobs are read off
    Celery's OWN conf (so the ``CELERY_`` namespace wiring is part of the
    proof) and off the settings source as literals -- an env-overridable
    ``acks_late`` would let one deployment silently reopen S-2.
    """
    conf = current_app.conf
    assert conf.task_acks_late is True
    assert conf.task_reject_on_worker_lost is True
    assert conf.worker_prefetch_multiplier == 1
    for name in (
        "CELERY_TASK_ACKS_LATE",
        "CELERY_TASK_REJECT_ON_WORKER_LOST",
        "CELERY_WORKER_PREFETCH_MULTIPLIER",
    ):
        value = _settings_assignment(name)
        assert isinstance(value, ast.Constant), (
            f"{name} must be a literal, got {ast.dump(value)}"
        )
        expected = 1 if name == "CELERY_WORKER_PREFETCH_MULTIPLIER" else True
        assert value.value == expected, (
            f"{name} must be the literal {expected!r}, got {value.value!r}"
        )


@pytest.mark.parametrize(
    ("info", "expected"),
    [
        (None, False),
        ({"is_eager": True}, False),
        ({"redelivered": False}, False),
        ({"redelivered": True}, True),
    ],
)
def test_redelivered_reads_the_transport_flag(*, info: Any, expected: bool) -> None:
    class _Request:
        delivery_info = info

    assert redelivered(_Request()) is expected
    assert redelivered(object()) is False


@pytest.mark.django_db
def test_a_killed_worker_re_runs_the_task_once_and_the_row_ends_terminal() -> None:
    """AC 1. Delivery 1: the pool child is killed mid-runner -- no ``except``
    runs, nothing writes, the row is RUNNING (the S-2 state). Delivery 2 is
    the broker's re-delivery (acks_late + reject_on_worker_lost): the runner
    runs again and the row reaches SUCCEEDED. Delivery 3 -- a duplicate --
    does not run the runner: the row is terminal.
    """
    run = _live_run()
    calls: list[int] = []

    def runner(payload: dict[str, Any]) -> dict[str, Any]:
        calls.append(1)
        if len(calls) == 1:
            raise _WorkerKilled
        return {"ok": True, "attempt": len(calls)}

    register_runner(STATION, TOOL, runner)
    args = (str(run.id), STATION, TOOL, {})

    with pytest.raises(_WorkerKilled):
        execute_supervised_run(*args)
    run.refresh_from_db()
    assert run.status == RunState.Status.RUNNING
    assert run.result is None

    with _redelivered_message(execute_supervised_run):
        execute_supervised_run.run(*args)
    run.refresh_from_db()
    assert run.status == RunState.Status.SUCCEEDED
    assert run.result == {"ok": True, "attempt": 2}
    assert run.completed_at is not None
    assert calls == [1, 1]

    with _redelivered_message(execute_supervised_run):
        execute_supervised_run.run(*args)
    run.refresh_from_db()
    assert run.status == RunState.Status.SUCCEEDED
    assert calls == [1, 1], "a terminal run must not be re-run"


@pytest.mark.django_db
def test_a_task_that_loses_its_worker_twice_is_failed_not_looped() -> None:
    """``reject_on_worker_lost`` is documented to cause message loops; the
    supervisor bounds the re-run to ONE. The second re-delivery does not run
    the runner and terminalises the row as ``worker_lost``.
    """
    run = _live_run()
    calls: list[int] = []

    def runner(_payload: dict[str, Any]) -> None:
        calls.append(1)
        raise _WorkerKilled

    register_runner(STATION, TOOL, runner)
    args = (str(run.id), STATION, TOOL, {})

    with pytest.raises(_WorkerKilled):
        execute_supervised_run(*args)
    with _redelivered_message(execute_supervised_run), pytest.raises(_WorkerKilled):
        execute_supervised_run.run(*args)
    run.refresh_from_db()
    assert run.status == RunState.Status.RUNNING
    assert run.result == {REDELIVERED_KEY: True}

    with _redelivered_message(execute_supervised_run):
        execute_supervised_run.run(*args)
    run.refresh_from_db()
    assert run.status == RunState.Status.FAILED
    assert run.result["reason"] == WORKER_LOST_REASON
    assert run.result["attempts"] == 2  # noqa: PLR2004 -- the original + one re-run
    assert calls == [1, 1]


@pytest.mark.django_db
def test_begin_attempt_refuses_terminal_and_missing_rows_and_bumps_heartbeat() -> None:
    cancelled = _live_run(status=RunState.Status.CANCELLED)
    assert begin_attempt(str(cancelled.id)) is False
    assert begin_attempt(str(cancelled.id), redelivered=True) is False
    cancelled.refresh_from_db()
    assert cancelled.status == RunState.Status.CANCELLED

    import uuid  # noqa: PLC0415

    assert begin_attempt(str(uuid.uuid4())) is False

    stale = _live_run(last_seen_ago=timedelta(minutes=30))
    before = stale.heartbeat_at
    assert begin_attempt(str(stale.id)) is True
    stale.refresh_from_db()
    assert before is not None
    assert stale.heartbeat_at is not None
    assert stale.heartbeat_at > before
    assert stale.result is None, "a first attempt leaves result untouched"


# ---------------------------------------------------------------------------
# AC 3 -- the routing table, through Celery's own router
# ---------------------------------------------------------------------------


def _routed_queue(name: str, args: tuple[Any, ...] = ()) -> str:
    route = current_app.amqp.router.route({}, name, args=args, kwargs={})
    return route["queue"].name


@pytest.mark.parametrize(
    ("station", "tool", "queue"),
    [
        ("mason", "build", BUILDS_QUEUE),
        ("mason", "rebuild", BUILDS_QUEUE),
        ("mason", "last_diagnose", "mason"),
        ("doctor", "remedy", PRIORITY_QUEUE),
        ("doctor", "pulse", "doctor"),
        ("atlas", "run_pipeline", "atlas"),
        ("warden", "run_audit", "warden"),
        ("not-a-station", "anything", DEFAULT_QUEUE),
    ],
)
def test_supervised_runs_route_by_station_and_tool(
    station: str,
    tool: str,
    queue: str,
) -> None:
    """AC 3: a Mason build lands on ``builds``; a Doctor remedy on
    ``priority``; everything else on its station's queue."""
    assert _routed_queue(SUPERVISED_RUN_TASK, ("run-id", station, tool, {})) == queue
    assert queues.queue_for(station, tool) == queue


def test_housekeeping_and_named_tasks_route_by_name() -> None:
    assert _routed_queue(PRUNE_RUN_STATE_TASK) == PRIORITY_QUEUE
    assert _routed_queue(SWEEP_LOST_RUNS_TASK) == PRIORITY_QUEUE
    assert _routed_queue("warden_fabric.run_job") == "warden"
    # No opinion -> Celery's default queue, which is ours, not "celery".
    assert _routed_queue("platformapp.front_door.run_django_task") == DEFAULT_QUEUE
    assert current_app.conf.task_default_queue == DEFAULT_QUEUE
    unnamed = "platformapp.front_door.run_django_task"
    assert queues.route_task(unnamed, (), {}, {}) is None
    # A supervised run whose args are unreadable still lands somewhere sane.
    unreadable = queues.route_task(SUPERVISED_RUN_TASK, (), {}, {})
    assert unreadable == {"queue": DEFAULT_QUEUE}


def test_the_topology_is_one_table() -> None:
    """Every route targets a declared queue; Celery declares exactly the
    chrome's queues; the general pool never lists ``builds`` and drains
    ``priority`` first; every station token has its own queue."""
    declared = [queue.name for queue in current_app.conf.task_queues]
    assert declared == list(ALL_QUEUES)
    assert set(TOOL_ROUTES.values()) <= set(ALL_QUEUES)
    assert set(TASK_ROUTES.values()) <= set(ALL_QUEUES)
    assert BUILDS_QUEUE not in WORKER_QUEUES
    assert WORKER_QUEUES[0] == PRIORITY_QUEUE
    assert set(STATION_QUEUES) == set(queues.STATION_TOKENS)
    assert set(STATION_QUEUES) <= set(WORKER_QUEUES)
    assert len(ALL_QUEUES) == len(set(ALL_QUEUES))


def test_builds_limit_is_hours_scale_and_the_general_limit_is_not(settings) -> None:
    """T-6: hours-scale work has its own limit; Block-If: the default queue's
    limit is NOT raised to hours. Both are documented settings; the broker's
    visibility timeout outlasts the longest of them, or a live build would be
    delivered twice on Redis."""
    assert settings.CELERY_BUILDS_TASK_TIME_LIMIT >= ONE_HOUR_SECONDS
    assert settings.CELERY_TASK_TIME_LIMIT < ONE_HOUR_SECONDS
    assert settings.CELERY_BUILDS_TASK_TIME_LIMIT > settings.CELERY_TASK_TIME_LIMIT
    declared = _env_int_settings(BASE_SETTINGS_PATH.read_text(encoding="utf-8"))
    for name in ("CELERY_BUILDS_TASK_TIME_LIMIT", "RUN_STATE_SWEEP_INTERVAL_SECONDS"):
        assert name in declared, f"{name} is not an env-overridable setting"
        assert getattr(settings, name) > 0
    options = current_app.conf.broker_transport_options
    assert options["visibility_timeout"] > settings.CELERY_BUILDS_TASK_TIME_LIMIT
    assert options["queue_order_strategy"] == "priority"
    assert station_time_limit("mason") == settings.CELERY_BUILDS_TASK_TIME_LIMIT
    assert station_time_limit("atlas") == settings.CELERY_TASK_TIME_LIMIT
    assert station_time_limit("doctor") == settings.CELERY_TASK_TIME_LIMIT


def test_values_worker_queues_mirror_the_chrome() -> None:
    """Ungated (no helm): the chart's ``worker.queues`` is the chrome's
    ``WORKER_QUEUES`` in order, never ``builds``, and its builds limit is the
    chrome's documented default -- a laptop and the cluster agree."""
    yaml = pytest.importorskip("yaml", reason="PyYAML parses values.yaml")
    values = yaml.safe_load(CORE_CHART_VALUES.read_text(encoding="utf-8"))
    assert list(values["worker"]["queues"]) == list(WORKER_QUEUES)
    builds = values["worker"]["builds"]
    limit = int(builds["taskTimeLimitSeconds"])
    assert limit == queues.DEFAULT_BUILDS_TASK_TIME_LIMIT_SECONDS
    assert limit >= ONE_HOUR_SECONDS
    assert 0 < int(builds["softTimeLimitSeconds"]) < int(builds["taskTimeLimitSeconds"])
    base_default = _settings_assignment("_DEFAULT_BUILDS_TASK_TIME_LIMIT")
    assert eval(compile(ast.Expression(base_default), "<settings>", "eval")) == (  # noqa: S307 -- literal product from our own source
        queues.DEFAULT_BUILDS_TASK_TIME_LIMIT_SECONDS
    )


# ---------------------------------------------------------------------------
# AC 4 -- the worker-lost sweep
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_sweep_marks_a_silent_run_failed_with_reason_worker_lost() -> None:
    """AC 4: RUNNING, silent for longer than its pool's limit, no worker holds
    its task -> FAILED with reason ``worker_lost``; a fresh run is untouched."""
    lost = _live_run(last_seen_ago=timedelta(seconds=GENERAL_LIMIT_SECONDS + 1))
    fresh = _live_run(last_seen_ago=timedelta(seconds=GENERAL_LIMIT_SECONDS - 5))

    report = sweep_lost_runs(inspector=_nobody_holds_anything())

    lost.refresh_from_db()
    fresh.refresh_from_db()
    assert lost.status == RunState.Status.FAILED
    assert lost.result["reason"] == WORKER_LOST_REASON
    assert lost.result["task_id"] == lost.celery_task_id
    assert lost.result["limit_seconds"] == GENERAL_LIMIT_SECONDS
    assert lost.completed_at is not None
    assert fresh.status == RunState.Status.RUNNING
    assert report["swept"] == 1
    assert report["run_ids"] == [str(lost.id)]
    assert report["inspected"] is True
    assert report["live"] == 2  # noqa: PLR2004 -- the two rows above


@pytest.mark.django_db
def test_sweep_gives_a_mason_run_the_builds_limit(settings) -> None:
    """A Mason row is measured against the builds limit -- ten minutes of
    silence is a live build, not a lost worker."""
    building = _live_run(station="mason", last_seen_ago=timedelta(minutes=10))
    abandoned = _live_run(
        station="mason",
        last_seen_ago=timedelta(seconds=settings.CELERY_BUILDS_TASK_TIME_LIMIT + 1),
    )

    report = sweep_lost_runs(inspector=_nobody_holds_anything())

    building.refresh_from_db()
    abandoned.refresh_from_db()
    assert building.status == RunState.Status.RUNNING
    assert abandoned.status == RunState.Status.FAILED
    assert abandoned.result["reason"] == WORKER_LOST_REASON
    assert abandoned.result["limit_seconds"] == settings.CELERY_BUILDS_TASK_TIME_LIMIT
    assert report["swept"] == 1


@pytest.mark.django_db
def test_sweep_leaves_a_task_a_worker_still_holds() -> None:
    """Silent past the limit but reported by a worker (a re-delivered task
    legitimately runs past the original start): left alone, counted."""
    held = _live_run(last_seen_ago=timedelta(hours=1))
    inspector = _Inspector(
        active={"worker@a": [{"id": held.celery_task_id, "name": SUPERVISED_RUN_TASK}]},
        reserved={},
        scheduled={"worker@a": [{"eta": None, "request": {"id": "someone-else"}}]},
    )

    report = sweep_lost_runs(inspector=inspector)

    held.refresh_from_db()
    assert held.status == RunState.Status.RUNNING
    assert report["swept"] == 0
    assert report["still_held"] == 1
    assert inspector.calls == ["active", "reserved", "scheduled"]


@pytest.mark.django_db
def test_sweep_measures_from_the_latest_attempt() -> None:
    """``begin_attempt`` bumps ``heartbeat_at``, so a re-run that started
    recently is not failed on the strength of the original start time."""
    run = _live_run(
        last_seen_ago=timedelta(hours=2),
        started_ago=timedelta(hours=2),
    )
    assert begin_attempt(str(run.id), redelivered=True) is True

    report = sweep_lost_runs(inspector=_nobody_holds_anything())

    run.refresh_from_db()
    assert run.status == RunState.Status.RUNNING
    assert report["stale"] == 0


@pytest.mark.django_db
def test_sweep_does_nothing_when_the_workers_cannot_be_asked(caplog) -> None:
    """Silence from an unreachable broker is not proof a task is dead."""
    stale = _live_run(last_seen_ago=timedelta(hours=1))

    down = _Inspector(raises=ConnectionError("broker down"))
    with caplog.at_level("ERROR"):
        report = sweep_lost_runs(inspector=down)

    stale.refresh_from_db()
    assert stale.status == RunState.Status.RUNNING
    assert report["swept"] == 0
    assert report["stale"] == 1
    assert report["inspected"] is False
    assert "broker down" in report["error"]
    messages = [record.message for record in caplog.records]
    assert any("supervisor.sweep_inspect_unavailable" in m for m in messages), messages


@pytest.mark.django_db
def test_sweep_never_inspects_when_nothing_is_stale() -> None:
    _live_run()
    inspector = _Inspector(raises=AssertionError("must not be asked"))

    report = sweep_lost_runs(inspector=inspector)

    assert report["stale"] == 0
    assert inspector.calls == []


@pytest.mark.django_db
def test_the_sweep_is_scheduled_routed_to_priority_and_runnable_by_hand(
    settings,
    capsys,
    monkeypatch,
) -> None:
    """A sweep nothing runs sweeps nothing: beat fires it on
    ``RUN_STATE_SWEEP_INTERVAL_SECONDS`` (the chart deploys ``beat``), it
    rides ``priority`` so a station backlog cannot delay it, and
    ``manage.py sweep_lost_runs`` is the operator's lever."""
    entry = settings.CELERY_BEAT_SCHEDULE["sweep-lost-runs"]
    assert entry["task"] == SWEEP_LOST_RUNS_TASK
    assert entry["schedule"] == settings.RUN_STATE_SWEEP_INTERVAL_SECONDS > 0
    assert _routed_queue(SWEEP_LOST_RUNS_TASK) == PRIORITY_QUEUE

    from django_pyforge.tasks import sweep_lost_runs_task  # noqa: PLC0415

    assert sweep_lost_runs_task.name == SWEEP_LOST_RUNS_TASK
    monkeypatch.setattr(supervisor, "_celery_inspector", _nobody_holds_anything)
    lost = _live_run(last_seen_ago=timedelta(hours=1))
    assert sweep_lost_runs_task()["swept"] == 1
    lost.refresh_from_db()
    assert lost.status == RunState.Status.FAILED

    _live_run(last_seen_ago=timedelta(hours=1))
    call_command("sweep_lost_runs", as_json=True)
    assert json.loads(capsys.readouterr().out)["swept"] == 1

    monkeypatch.setattr(
        supervisor,
        "_celery_inspector",
        lambda: _Inspector(raises=ConnectionError("broker down")),
    )
    _live_run(last_seen_ago=timedelta(hours=1))
    call_command("sweep_lost_runs")
    out = capsys.readouterr().out
    assert "swept 0 of 1" in out
    assert "could not be inspected" in out
