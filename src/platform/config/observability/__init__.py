# Copyright (c) 2026 Kevin Mills
# Portions adapted from millsks/django-15-factor-base (MIT License).
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
"""Logging and telemetry wiring.

`configure_observability` is the single call each process entrypoint makes --
`manage.py`, `wsgi.py`, `asgi.py` and the Celery app. structlog itself is
configured from the settings module instead, because `LOGGING` has to be built
while settings are being read.
"""

from __future__ import annotations

from pathlib import Path

import environ
from django.conf import settings

from config.observability.logging import add_otel_context
from config.observability.logging import build_logging_config
from config.observability.logging import configure_structlog
from config.observability.logging import resolve_log_format
from config.observability.metrics import configure_metrics
from config.observability.metrics import observe_mcp_duration
from config.observability.metrics import set_celery_queue_oldest_age
from config.observability.metrics import set_event_stream_lag
from config.observability.telemetry import configure_telemetry

__all__ = [
    "add_otel_context",
    "build_logging_config",
    "configure_metrics",
    "configure_observability",
    "configure_structlog",
    "configure_telemetry",
    "load_django_settings",
    "observe_mcp_duration",
    "read_dot_env",
    "resolve_log_format",
]

# Repository root: observability -> config -> src/platform -> (parents).
# Platform layout: src/platform/{config,manage.py}; .env lives next to manage.py.
BASE_DIR = Path(__file__).resolve().parents[2]


def read_dot_env() -> bool:
    """Load `.env` before telemetry reads any `OTEL_*` variable.

    Settings read `.env` too, but that happens when Django loads its settings --
    long after this runs at entrypoint import. Without this, `OTEL_*` entries in
    `.env` would be parsed too late to affect tracing and would appear to be
    ignored.

    Real environment variables still win: `read_env` does not overwrite entries
    already present in `os.environ`.
    """
    env = environ.Env()
    if not env.bool("DJANGO_READ_DOT_ENV_FILE", default=False):
        return False

    dot_env = BASE_DIR / ".env"
    if not dot_env.is_file():
        return False

    env.read_env(str(dot_env))
    return True


def load_django_settings() -> None:
    """Import the settings module before anything can swallow its refusals.

    Story 41.4 / CAP-3. ``DjangoInstrumentor().instrument()`` reads
    ``settings.MIDDLEWARE`` inside a ``try/except ImproperlyConfigured`` and
    answers a failure by calling ``settings.configure()`` -- which replaces the
    real settings module with Django's empty defaults for the rest of the
    process. A stage-1 refusal raised while importing settings was therefore
    demoted to a debug log at every entrypoint (`manage.py`, `wsgi`, `asgi`,
    the Celery app), and the component booted with no apps and no middleware
    instead of failing fast. Found live: `manage.py check` answered "System
    check identified no issues" and exited 0 for a deployed component with no
    `DJANGO_SECRET_KEY`.

    Touching one setting here imports the module first, so the refusal is the
    process's own exception. In a healthy process this is a no-op -- the
    instrumentor would have imported the same module microseconds later.

    Raises:
        ImproperlyConfigured: Propagated from any stage-1 refusal.
    """
    _ = settings.INSTALLED_APPS


def configure_observability(service_version: str | None = None) -> bool:
    """Configure logging-adjacent environment and telemetry for this process.

    ``.env`` is read first (telemetry reads ``OTEL_*`` from the environment),
    then the settings module, then telemetry -- see `load_django_settings` for
    why that middle step is not optional.

    Returns:
        True when telemetry was configured by this call, False when skipped.
    """
    read_dot_env()
    load_django_settings()
    configure_metrics()
    _register_platform_observability_hooks()
    return configure_telemetry(service_version)


def _register_platform_observability_hooks() -> None:
    from django_pyforge.observability_hooks import set_celery_queue_age_writer
    from django_pyforge.observability_hooks import set_event_stream_lag_writer
    from django_pyforge.observability_hooks import set_mcp_duration_observer

    set_mcp_duration_observer(observe_mcp_duration)
    set_celery_queue_age_writer(set_celery_queue_oldest_age)
    set_event_stream_lag_writer(set_event_stream_lag)
