"""Story 21.6: a start tool with no work behind it fails the run and says so."""

from __future__ import annotations

import importlib
import inspect
import re
from typing import Any
from typing import NamedTuple

import pytest
from django_pyforge import supervisor
from django_pyforge.assertion.crypto import mint_assertion
from django_pyforge.models import McpHandle
from django_pyforge.models import RunState
from django_pyforge.supervisor import RunnerNotWiredError
from django_pyforge.supervisor import get_run
from django_pyforge.supervisor import start_bounded
from django_pyforge.tasks import execute_supervised_run

COMPLETED_CLAIM = re.compile(r"""["']completed["']\s*:\s*True""")


class Face(NamedTuple):
    station: str
    module: str
    tool: str


FACES: tuple[Face, ...] = (
    Face("doctor", "django_doctor_portal.mcp_asgi", "run_scan"),
    Face("herald", "django_herald_portal.mcp_asgi", "run_notice"),
    Face("marshal", "django_marshal_portal.mcp_asgi", "run_loop"),
    Face("mason", "django_mason_portal.mcp_asgi", "run_build"),
    Face("scribe", "django_scribe_portal.mcp_asgi", "run_recall"),
    Face("steward", "django_steward_portal.mcp_asgi", "run_duty"),
    Face("warden", "django_warden_fabric.mcp_asgi", "run_audit"),
)


def _runner(face: Face) -> Any:
    return getattr(importlib.import_module(face.module), face.tool)


@pytest.mark.parametrize("face", FACES, ids=lambda face: face.station)
def test_runner_refuses_and_names_itself(face: Face) -> None:
    with pytest.raises(RunnerNotWiredError) as caught:
        _runner(face)({"target": "."})
    message = str(caught.value)
    assert f"{face.station}.{face.tool} ran nothing" in message
    assert f"pyforge {face.station}" in message


@pytest.mark.django_db
@pytest.mark.parametrize("face", FACES, ids=lambda face: face.station)
def test_run_ends_failed_and_get_says_so(
    face: Face,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The real runner, through the real worker task: never ``SUCCEEDED``."""
    delayed: list[dict[str, Any]] = []

    def capture_delay(*_args: object, **kwargs: Any) -> None:
        delayed.append(kwargs)

    monkeypatch.setattr(execute_supervised_run, "apply_async", capture_delay)
    monkeypatch.setitem(
        supervisor._runners,  # noqa: SLF001
        (face.station, face.tool),
        _runner(face),
    )
    assertion = mint_assertion(
        sub="agent-21-6",
        roles=[f"pyforge:station:{face.station}"],
        station=face.station,
    )
    handle = start_bounded(
        station=face.station,
        assertion=assertion,
        tool=face.tool,
        payload={"target": "."},
    )
    assert delayed

    with pytest.raises(RunnerNotWiredError):
        execute_supervised_run(*delayed[0]["args"])

    run = get_run(station=face.station, handle=handle, assertion=assertion)
    assert run["status"] == RunState.Status.FAILED
    assert f"{face.station}.{face.tool} ran nothing" in run["result"]["error"]
    row = McpHandle.objects.select_related("run").get(handle=handle)
    assert row.run.status == RunState.Status.FAILED


@pytest.mark.parametrize("face", FACES, ids=lambda face: face.station)
def test_no_station_face_claims_a_completed_run(face: Face) -> None:
    source = inspect.getsource(importlib.import_module(face.module))
    assert COMPLETED_CLAIM.search(source) is None
