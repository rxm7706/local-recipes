"""W3C ``traceparent`` across the bus (Story 42.3, red-team A-5).

The request that publishes an event has a trace (DjangoInstrumentor continues
the inbound ``traceparent``); the consumer that reacts runs in another process
with none. This module carries the header on the CloudEvents envelope
(``EXT_TRACEPARENT``), re-activates it around the handler, and hands it to
Celery so a chain Warden -> Doctor -> Mason shares one trace id.

OpenTelemetry and structlog are optional here: django-pyforge depends on
neither, so every integration is a guarded import and the header itself is
carried by a plain :class:`contextvars.ContextVar` that always works.
"""

from __future__ import annotations

import re
from contextlib import ExitStack
from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from collections.abc import Iterator

TRACEPARENT_HEADER = "traceparent"
# version-traceid-spanid-flags, lowercase hex; an all-zero trace or span id
# is invalid per the W3C Trace Context spec, and so is version ``ff``.
_TRACEPARENT_RE = re.compile(
    r"^([0-9a-f]{2})-([0-9a-f]{32})-([0-9a-f]{16})-[0-9a-f]{2}$",
)
_FORBIDDEN_VERSION = "ff"

_current_traceparent: ContextVar[str | None] = ContextVar(
    "django_pyforge_traceparent",
    default=None,
)


class TraceparentFormatError(ValueError):
    """``traceparent`` must be a W3C Trace Context header."""


def parse_traceparent(value: Any) -> tuple[str, str] | None:
    """``(trace_id, span_id)`` for a valid header, else ``None``."""
    if not isinstance(value, str):
        return None
    match = _TRACEPARENT_RE.match(value)
    if match is None:
        return None
    version, trace_id, span_id = match.group(1), match.group(2), match.group(3)
    if version == _FORBIDDEN_VERSION:
        return None
    if set(trace_id) == {"0"} or set(span_id) == {"0"}:
        return None
    return trace_id, span_id


def trace_id_of(traceparent: Any) -> str | None:
    parsed = parse_traceparent(traceparent)
    return parsed[0] if parsed else None


def _otel_traceparent() -> str | None:
    try:
        from opentelemetry import propagate  # noqa: PLC0415 -- optional
    except ImportError:
        return None
    carrier: dict[str, str] = {}
    propagate.inject(carrier)
    value = carrier.get(TRACEPARENT_HEADER)
    return value if parse_traceparent(value) else None


def current_traceparent() -> str | None:
    """The header for the trace this code runs under, if any.

    The active OpenTelemetry span wins (that is the request's trace under
    DjangoInstrumentor, or the task's under CeleryInstrumentor); the
    contextvar bound by :func:`bound_trace` is the fallback.
    """
    return _otel_traceparent() or _current_traceparent.get()


def trace_headers() -> dict[str, str]:
    """Celery message headers carrying the current trace (empty if none)."""
    traceparent = current_traceparent()
    if traceparent is None:
        return {}
    return {TRACEPARENT_HEADER: traceparent}


def traceparent_from_task_request(request: Any) -> str | None:
    """Read the header a task was published with.

    A worker exposes custom message headers as request attributes; the eager
    path keeps them under ``request.headers``.
    """
    direct = getattr(request, TRACEPARENT_HEADER, None)
    if parse_traceparent(direct):
        return str(direct)
    headers = getattr(request, "headers", None) or {}
    value = headers.get(TRACEPARENT_HEADER) if isinstance(headers, dict) else None
    return str(value) if parse_traceparent(value) else None


def bind_structlog_trace(traceparent: str) -> list[str]:
    """Bind ``traceparent`` + ``trace_id`` into structlog's contextvars.

    For the Celery task receiver, where django-structlog has just rebuilt
    the context and there is nothing outer to restore. Returns the keys
    bound. No-op without structlog.
    """
    try:
        from structlog.contextvars import bind_contextvars  # noqa: PLC0415
    except ImportError:
        return []
    trace_id = trace_id_of(traceparent)
    if trace_id is None:
        return []
    bind_contextvars(traceparent=traceparent, trace_id=trace_id)
    return ["traceparent", "trace_id"]


def _structlog_scope(traceparent: str, trace_id: str) -> Any:
    """``structlog.contextvars.bound_contextvars`` (restores outer values on
    exit), or ``None`` without structlog."""
    try:
        from structlog.contextvars import bound_contextvars  # noqa: PLC0415
    except ImportError:
        return None
    return bound_contextvars(traceparent=traceparent, trace_id=trace_id)


@contextmanager
def bound_trace(traceparent: str | None) -> Iterator[None]:
    """Run the body under ``traceparent``: contextvar, OTel context, structlog.

    A missing or malformed header binds nothing (the body still runs); a
    consumer must never refuse an event for lack of a trace. On exit every
    layer is restored to what it was, whatever raised.
    """
    parsed = parse_traceparent(traceparent)
    if parsed is None:
        yield
        return
    assert traceparent is not None
    trace_id = parsed[0]
    token = _current_traceparent.set(traceparent)
    try:
        with ExitStack() as stack:
            try:
                from opentelemetry import context as otel_context  # noqa: PLC0415
                from opentelemetry import propagate  # noqa: PLC0415
            except ImportError:
                pass
            else:
                extracted = propagate.extract({TRACEPARENT_HEADER: traceparent})
                stack.callback(otel_context.detach, otel_context.attach(extracted))
            scope = _structlog_scope(traceparent, trace_id)
            if scope is not None:
                stack.enter_context(scope)
            yield
    finally:
        _current_traceparent.reset(token)
