"""Epic 119's proof on a laptop: each start tool runs its real station CLI.

CI has no pixi environments to call, so this skips unless ``STATION_CLI_LIVE_ROOT``
names a checkout that has them::

    STATION_CLI_LIVE_ROOT=<checkout> STATION_CLI_LIVE_RECIPE=python-wget \\
        pixi run -e pyforge-guild platform-ci-local -- --test

No test here turns ``pyforge.steward.start_loop_dispatch`` on, so ``start_loop`` is
refused and nothing is dispatched.
"""

from __future__ import annotations

import importlib
import os
from typing import Any

import pytest
from django_pyforge.assertion.crypto import mint_assertion
from django_pyforge.models import RunState
from django_pyforge.roles import ROLE_ADMIN
from django_pyforge.supervisor import get_run
from django_pyforge.supervisor import register_runner
from django_pyforge.supervisor import start_bounded
from mcp.server.mcpserver.exceptions import ToolError

LIVE_ROOT = os.environ.get("STATION_CLI_LIVE_ROOT", "")
pytestmark = pytest.mark.skipif(
    not LIVE_ROOT, reason="STATION_CLI_LIVE_ROOT names no checkout"
)

MODULES = {
    "doctor": "django_doctor_portal.mcp_asgi",
    "herald": "django_herald_portal.mcp_asgi",
    "marshal": "django_marshal_portal.mcp_asgi",
    "mason": "django_mason_portal.mcp_asgi",
    "scribe": "django_scribe_portal.mcp_asgi",
    "steward": "django_steward_portal.mcp_asgi",
    "warden": "django_warden_fabric.mcp_asgi",
}
#: The smallest tracked recipe that builds without a network-heavy solve.
RECIPE = os.environ.get("STATION_CLI_LIVE_RECIPE", "")


def _run(station: str, run_tool: str, target: str, settings: Any) -> dict[str, Any]:
    settings.STATION_CLI_ROOT = LIVE_ROOT
    register_runner(
        station, run_tool, getattr(importlib.import_module(MODULES[station]), run_tool)
    )
    assertion = mint_assertion(
        sub="live-119", roles=[f"pyforge:station:{station}"], station=station
    )
    handle = start_bounded(
        station=station, assertion=assertion, tool=run_tool, payload={"target": target}
    )
    return get_run(station=station, handle=handle, assertion=assertion)


@pytest.mark.django_db
def test_doctor_scan_returns_a_real_report(settings: Any) -> None:
    run = _run("doctor", "run_scan", "numpy", settings)
    assert run["status"] == RunState.Status.SUCCEEDED
    assert "findings" in run["result"]["report"]


@pytest.mark.django_db
def test_herald_notice_reaches_the_real_cli(settings: Any) -> None:
    """The tree holds no notice, so herald's own refusal is the real answer."""
    run = _run("herald", "run_notice", "no-such-component", settings)
    assert run["status"] == RunState.Status.FAILED
    assert "no notice found" in run["result"]["error"]


@pytest.mark.django_db
def test_scribe_recall_returns_a_real_answer(settings: Any) -> None:
    run = _run("scribe", "run_recall", "what did the operator rule on N1", settings)
    assert run["status"] == RunState.Status.SUCCEEDED
    assert "no grounded answer found" not in run["result"]["stdout"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("duty", "key"),
    [("ci-status", "repo"), ("estate-plan", "kind"), ("estate-status", "journals")],
)
def test_steward_duty_returns_a_real_report(settings: Any, duty: str, key: str) -> None:
    run = _run("steward", "run_duty", duty, settings)
    assert run["status"] == RunState.Status.SUCCEEDED
    assert key in run["result"]["report"]


@pytest.mark.django_db
def test_warden_audit_returns_a_real_report(settings: Any) -> None:
    run = _run("warden", "run_audit", "src/platform", settings)
    assert run["status"] == RunState.Status.SUCCEEDED
    assert run["result"]["report"]["status"]["value"]


@pytest.mark.django_db
def test_mason_build_builds_a_tracked_recipe(settings: Any) -> None:
    if not RECIPE:
        pytest.skip("STATION_CLI_LIVE_RECIPE names no recipe")
    run = _run("mason", "run_build", RECIPE, settings)
    assert run["status"] == RunState.Status.SUCCEEDED, run["result"]
    assert run["result"]["exit_code"] == 0


@pytest.mark.django_db
def test_marshal_loop_stays_refused_with_the_shipped_flag(
    settings: Any,
) -> None:
    settings.STATION_CLI_ROOT = LIVE_ROOT
    assertion = mint_assertion(
        sub="live-119", roles=["pyforge:station:marshal", ROLE_ADMIN], station="marshal"
    )
    with pytest.raises(ToolError):
        start_bounded(
            station="marshal",
            assertion=assertion,
            tool="run_loop",
            payload={"target": "steward/x"},
        )
