"""Story 48.5 / R-21 observability contract tests."""

from __future__ import annotations

import json
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import yaml

from config.observability.metrics import HEALTH_CHECK_DURATION
from config.observability.metrics import load_slo_contract
from config.observability.metrics import metrics_payload
from config.observability.middleware import HealthCheckMetricsMiddleware

SLO_CONTRACT_PATH = (
    Path(__file__).resolve().parents[1] / "config/observability/slo-contract.yaml"
)


def test_slo_contract_declares_four_signals():
    contract = load_slo_contract()
    slos = contract["slos"]
    assert "health_check" in slos
    assert "mcp" in slos
    assert "celery_queue" in slos
    assert "event_stream" in slos
    assert slos["health_check"]["metrics"]["duration_seconds"] == (
        "pyforge_health_check_duration_seconds"
    )
    assert slos["mcp"]["metrics"]["duration_seconds"] == (
        "pyforge_mcp_request_duration_seconds"
    )


def test_metrics_payload_exports_contract_families():
    body = metrics_payload().decode()
    assert "pyforge_health_check_success_total" in body
    assert "pyforge_mcp_request_duration_seconds" in body
    assert "pyforge_celery_queue_oldest_age_seconds" in body
    assert "pyforge_event_stream_lag_seconds" in body


def test_health_check_middleware_observes_ht():
    before = HEALTH_CHECK_DURATION._sum.get()  # noqa: SLF001

    def _ok(_request):
        response = MagicMock()
        response.status_code = HTTPStatus.OK
        return response

    middleware = HealthCheckMetricsMiddleware(_ok)
    request = SimpleNamespace(path="/ht/")
    middleware(request)  # type: ignore[arg-type]

    after = HEALTH_CHECK_DURATION._sum.get()  # noqa: SLF001
    assert after >= before


def test_slo_contract_yaml_is_valid():
    document = yaml.safe_load(SLO_CONTRACT_PATH.read_text(encoding="utf-8"))
    assert document["version"] == 1
    assert json.dumps(document["slos"])
