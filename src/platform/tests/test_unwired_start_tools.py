"""Story 21.6: a start tool with no work behind it fails the run and says so."""

from __future__ import annotations

import importlib
import inspect
import re
from typing import Any
from typing import NamedTuple

import pytest
from django_pyforge.assertion.crypto import mint_assertion
from django_pyforge.discovery import iter_portal_configs
from django_pyforge.models import McpHandle
from django_pyforge.models import RunState
from django_pyforge.supervisor import RunnerNotWiredError
from django_pyforge.supervisor import get_run
from django_pyforge.supervisor import lookup_runner
from django_pyforge.supervisor import start_bounded
from django_pyforge.tasks import execute_supervised_run

COMPLETED_CLAIM = re.compile(r"""["']completed["']\s*:\s*True""")


class Face(NamedTuple):
    station: str
    module: str
    run_tool: str
    start_tool: str


FACES: tuple[Face, ...] = (
    Face("doctor", "django_doctor_portal.mcp_asgi", "run_scan", "start_scan"),
    Face("herald", "django_herald_portal.mcp_asgi", "run_notice", "start_notice"),
    Face("marshal", "django_marshal_portal.mcp_asgi", "run_loop", "start_loop"),
    Face("mason", "django_mason_portal.mcp_asgi", "run_build", "start_build"),
    Face("scribe", "django_scribe_portal.mcp_asgi", "run_recall", "start_recall"),
    Face("steward", "django_steward_portal.mcp_asgi", "run_duty", "start_duty"),
    Face("warden", "django_warden_fabric.mcp_asgi", "run_audit", "start_audit"),
)


def _message(face: Face) -> str:
    return f"{face.station} {face.start_tool} ran nothing"


def _registered_runner(face: Face) -> Any:
    """The runner the portal's own registration path installs."""
    module = importlib.import_module(face.module)
    getattr(module, f"ensure_{face.station}_runner")()
    runner = lookup_runner(face.station, face.run_tool)
    assert runner is getattr(module, face.run_tool)
    return runner


def _assertion(face: Face) -> str:
    return mint_assertion(
        sub="agent-21-6",
        roles=[f"pyforge:station:{face.station}"],
        station=face.station,
    )


def _start(face: Face, assertion: str) -> str:
    return start_bounded(
        station=face.station,
        assertion=assertion,
        tool=face.run_tool,
        payload={"target": "."},
    )


def _assert_failed_in_words(face: Face, handle: str, assertion: str) -> None:
    run = get_run(station=face.station, handle=handle, assertion=assertion)
    assert run["status"] == RunState.Status.FAILED
    assert _message(face) in run["result"]["error"]
    row = McpHandle.objects.select_related("run").get(handle=handle)
    assert row.run.status == RunState.Status.FAILED


def test_every_station_face_is_listed_here() -> None:
    """Atlas's runner does its work; any other new face must join ``FACES``."""
    stations = {
        portal.station_name
        for portal in iter_portal_configs()
        if not portal.station_name.endswith("-probe")  # test settings' own portals
    }
    assert stations == {face.station for face in FACES} | {"atlas"}


@pytest.mark.parametrize("face", FACES, ids=lambda face: face.station)
def test_runner_refuses_and_names_the_start_tool(face: Face) -> None:
    with pytest.raises(RunnerNotWiredError) as caught:
        _registered_runner(face)({"target": "."})
    message = str(caught.value)
    assert _message(face) in message
    assert f"pyforge {face.station}" in message


@pytest.mark.django_db
@pytest.mark.parametrize("face", FACES, ids=lambda face: face.station)
def test_worker_ends_the_run_failed_and_get_says_so(
    face: Face,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A real broker's path: the task runs later, on a worker."""
    delayed: list[dict[str, Any]] = []

    def capture_delay(*_args: object, **kwargs: Any) -> None:
        delayed.append(kwargs)

    monkeypatch.setattr(execute_supervised_run, "apply_async", capture_delay)
    _registered_runner(face)
    assertion = _assertion(face)
    handle = _start(face, assertion)
    assert delayed

    execute_supervised_run(*delayed[0]["args"])

    _assert_failed_in_words(face, handle, assertion)


@pytest.mark.django_db
@pytest.mark.parametrize("face", FACES, ids=lambda face: face.station)
def test_eager_start_keeps_the_handle(face: Face) -> None:
    """Test and local settings run the task inside ``start``: it still returns."""
    _registered_runner(face)
    assertion = _assertion(face)

    handle = _start(face, assertion)

    _assert_failed_in_words(face, handle, assertion)


@pytest.mark.parametrize("face", FACES, ids=lambda face: face.station)
def test_no_station_face_claims_a_completed_run(face: Face) -> None:
    source = inspect.getsource(importlib.import_module(face.module))
    assert COMPLETED_CLAIM.search(source) is None
