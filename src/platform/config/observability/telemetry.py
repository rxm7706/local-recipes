# Copyright (c) 2026 Kevin Mills
# Portions adapted from millsks/django-15-factor-base (MIT License).
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
"""OpenTelemetry tracing setup.

Tracing is always wired in; only *export* is conditional. The OTLP processor is
attached only when an endpoint is configured (or exporter is explicitly otlp).
"""

from __future__ import annotations

import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from config.locality import is_local

DEFAULT_SERVICE_NAME = "python-agent-platform"

OTLP = "otlp"
CONSOLE = "console"
NONE = "none"

OTEL_SDK_DISABLED_ENV_VAR = "OTEL_SDK_DISABLED"

_DISABLED_VALUES = frozenset({"true", "1", "yes"})

_configured = False


def otel_sdk_is_disabled() -> bool:
    """Report whether this component has opted out of the OpenTelemetry SDK."""
    raw = os.environ.get(OTEL_SDK_DISABLED_ENV_VAR, "")
    return raw.strip().lower() in _DISABLED_VALUES


def _has_otlp_endpoint() -> bool:
    return bool(
        os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        or os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"),
    )


def build_resource(service_version: str | None = None) -> Resource:
    """Describe this service to the tracing backend."""
    attributes: dict[str, str] = {
        "service.name": os.environ.get("OTEL_SERVICE_NAME") or DEFAULT_SERVICE_NAME,
        "deployment.environment": "local" if is_local() else "deployed",
    }
    if service_version:
        attributes["service.version"] = service_version
    return Resource.create(attributes)


def resolve_traces_exporter() -> str:
    """Decide how spans should leave the process."""
    configured = os.environ.get("OTEL_TRACES_EXPORTER", "").strip().lower()
    if configured in {CONSOLE, NONE, OTLP}:
        return configured
    return OTLP if _has_otlp_endpoint() else NONE


def has_span_processor(provider: TracerProvider) -> bool:
    """Report whether any span processor is attached to `provider`."""
    active = getattr(provider, "_active_span_processor", None)
    if active is None:
        return False
    return bool(getattr(active, "_span_processors", None))


def configure_telemetry(service_version: str | None = None) -> bool:
    """Install the tracer provider and instrument the stack."""
    global _configured  # noqa: PLW0603
    if _configured or otel_sdk_is_disabled():
        return False

    provider = TracerProvider(resource=build_resource(service_version))

    exporter = resolve_traces_exporter()
    if exporter == OTLP:
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    elif exporter == CONSOLE:
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)

    DjangoInstrumentor().instrument()
    CeleryInstrumentor().instrument()
    PsycopgInstrumentor().instrument()
    RedisInstrumentor().instrument()

    _configured = True
    return True


def reset_telemetry_for_testing() -> None:
    """Clear the idempotence guard so a test can configure again."""
    global _configured  # noqa: PLW0603
    _configured = False
