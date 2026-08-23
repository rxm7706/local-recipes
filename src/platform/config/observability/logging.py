# Copyright (c) 2026 Kevin Mills
# Portions adapted from millsks/django-15-factor-base (MIT License).
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
"""structlog configuration for the application and for third-party logs.

Django, allauth and Celery log through the standard library. Routing those
records through `structlog.stdlib.ProcessorFormatter` means they pass the same
processor chain as our own calls, so every line -- ours or not -- comes out
structured and carries the same context.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

import structlog
from opentelemetry import trace

if TYPE_CHECKING:
    from structlog.typing import EventDict
    from structlog.typing import Processor
    from structlog.typing import WrappedLogger

JSON = "json"
CONSOLE = "console"
LOG_FORMATS = (JSON, CONSOLE)

DEFAULT_LOG_LEVEL = "INFO"


def add_otel_context(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Add the active OpenTelemetry trace and span ids to the event."""
    span_context = trace.get_current_span().get_span_context()
    if span_context.is_valid:
        event_dict["trace_id"] = format(span_context.trace_id, "032x")
        event_dict["span_id"] = format(span_context.span_id, "016x")
    return event_dict


def shared_processors() -> list[Processor]:
    """Build the processor chain applied to structlog and stdlib records alike."""
    return [
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        add_otel_context,
    ]


def configure_structlog() -> None:
    """Point structlog at the standard library logging pipeline."""
    structlog.configure(
        processors=[
            *shared_processors(),
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def resolve_log_format(*, debug: bool, log_format: str | None = None) -> str:
    """Decide between JSON and console rendering."""
    if log_format in LOG_FORMATS:
        return log_format
    return CONSOLE if debug else JSON


def _renderer(log_format: str) -> list[Processor]:
    if log_format == JSON:
        return [
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    return [
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        structlog.dev.ConsoleRenderer(),
    ]


def build_logging_config(
    *,
    debug: bool,
    log_level: str | None = None,
    log_format: str | None = None,
    extra_handlers: dict[str, Any] | None = None,
    extra_loggers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the Django LOGGING dictConfig around structlog."""
    level = (log_level or DEFAULT_LOG_LEVEL).upper()
    resolved_format = resolve_log_format(debug=debug, log_format=log_format)

    handlers: dict[str, Any] = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
        },
    }
    handlers.update(extra_handlers or {})

    loggers: dict[str, Any] = {
        "django_structlog": {"level": level},
        "platformapp": {"level": level},
    }
    loggers.update(extra_loggers or {})

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processors": _renderer(resolved_format),
                "foreign_pre_chain": shared_processors(),
            },
        },
        "handlers": handlers,
        "root": {"level": level, "handlers": ["console"]},
        "loggers": loggers,
    }
