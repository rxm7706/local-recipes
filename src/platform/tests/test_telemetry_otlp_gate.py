"""CAP-2 / steward 16.3 — OTLP export gate and exporter resolution."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from config.observability.telemetry import CONSOLE
from config.observability.telemetry import NONE
from config.observability.telemetry import OTLP
from config.observability.telemetry import configure_telemetry
from config.observability.telemetry import has_span_processor
from config.observability.telemetry import reset_telemetry_for_testing
from config.observability.telemetry import resolve_traces_exporter

_MOCK = MagicMock()
_TEL = "config.observability.telemetry"


@pytest.fixture(autouse=True)
def _reset_telemetry():
    reset_telemetry_for_testing()
    yield
    reset_telemetry_for_testing()


def _instrumentor_patches():
    """Avoid double-instrumenting when calling configure_telemetry."""
    return (
        patch(f"{_TEL}.DjangoInstrumentor", return_value=_MOCK),
        patch(f"{_TEL}.CeleryInstrumentor", return_value=_MOCK),
        patch(f"{_TEL}.PsycopgInstrumentor", return_value=_MOCK),
        patch(f"{_TEL}.RedisInstrumentor", return_value=_MOCK),
        patch(f"{_TEL}.trace.set_tracer_provider"),
    )


class TestResolveTracesExporter:
    def test_none_when_no_endpoint_is_configured(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", raising=False)
        monkeypatch.delenv("OTEL_TRACES_EXPORTER", raising=False)
        assert resolve_traces_exporter() == NONE

    def test_otlp_when_endpoint_is_configured(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")
        monkeypatch.delenv("OTEL_TRACES_EXPORTER", raising=False)
        assert resolve_traces_exporter() == OTLP

    def test_otlp_when_only_traces_endpoint_is_configured(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
        monkeypatch.setenv(
            "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
            "http://collector:4318/v1/traces",
        )
        monkeypatch.delenv("OTEL_TRACES_EXPORTER", raising=False)
        assert resolve_traces_exporter() == OTLP

    @pytest.mark.parametrize("value", [CONSOLE, NONE, OTLP])
    def test_explicit_exporter_is_honoured(
        self,
        monkeypatch: pytest.MonkeyPatch,
        value: str,
    ):
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
        monkeypatch.setenv("OTEL_TRACES_EXPORTER", value)
        assert resolve_traces_exporter() == value


class TestConfigureTelemetryGate:
    def test_configure_attaches_no_processor_without_endpoint(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", raising=False)
        monkeypatch.delenv("OTEL_TRACES_EXPORTER", raising=False)
        monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
        assert resolve_traces_exporter() == NONE

        captured: list[Any] = []

        def _capture(provider: Any) -> None:
            captured.append(provider)

        patches = _instrumentor_patches()
        with patches[0], patches[1], patches[2], patches[3], patches[4] as set_provider:
            set_provider.side_effect = _capture
            assert configure_telemetry() is True

        assert len(captured) == 1
        assert has_span_processor(captured[0]) is False

    def test_configure_attaches_processor_when_otlp_endpoint_set(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4318")
        monkeypatch.delenv("OTEL_TRACES_EXPORTER", raising=False)
        monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
        assert resolve_traces_exporter() == OTLP

        captured: list[Any] = []

        def _capture(provider: Any) -> None:
            captured.append(provider)

        patches = _instrumentor_patches()
        with patches[0], patches[1], patches[2], patches[3], patches[4] as set_provider:
            set_provider.side_effect = _capture
            assert configure_telemetry() is True

        assert len(captured) == 1
        assert has_span_processor(captured[0]) is True

    def test_sdk_disabled_skips_configure(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
        assert configure_telemetry() is False
