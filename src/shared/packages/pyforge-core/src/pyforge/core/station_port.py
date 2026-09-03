"""In-process station API port (Story 43.3, red-team R-6).

Co-located portals reach ``/stations/<name>/api/v<N>/`` through a registered
in-process invoker instead of HTTP loopback to the host. ``STATION_REMOTE=1``
selects the HTTP path in ``django_pyforge.station_port`` / ``PyForgeStationClient``.

The host registers the invoker at startup (``config.station_port.wire_station_port``)
without importing ``pyforge.<station>`` — only this registry surface crosses the
factory/platform boundary from ``django-pyforge``.
"""

from __future__ import annotations

import os
from collections.abc import Callable

from pyforge.core.errors import PyforgeError

STATION_REMOTE_ENV = "STATION_REMOTE"

InProcessInvoker = Callable[[str, str, dict[str, str], bytes | None], bytes]

_invoker: InProcessInvoker | None = None


class StationPortError(PyforgeError):
    """Missing invoker or misuse of the in-process port."""


def is_station_remote() -> bool:
    """True when portals must use HTTP (``pyforge.core.client``) for station APIs."""
    raw = os.environ.get(STATION_REMOTE_ENV, "").strip().lower()
    return raw in {"1", "true", "yes"}


def register_in_process_invoker(fn: InProcessInvoker) -> None:
    """Register the host's ASGI invoker. Idempotent for the same callable."""
    global _invoker
    if _invoker is not None and _invoker is not fn:
        msg = "in-process station port already registered"
        raise StationPortError(msg)
    _invoker = fn


def replace_in_process_invoker(fn: InProcessInvoker) -> InProcessInvoker | None:
    """Test seam: swap the invoker and return the previous one."""
    global _invoker
    previous = _invoker
    _invoker = fn
    return previous


def reset_in_process_invoker() -> None:
    """Test seam: drop the registered invoker."""
    global _invoker
    _invoker = None


def invoke_in_process(
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes | None,
) -> bytes:
    """Call the registered invoker. Never opens a loopback socket."""
    if is_station_remote():
        msg = "invoke_in_process called while STATION_REMOTE is enabled"
        raise StationPortError(msg)
    if _invoker is None:
        msg = "no in-process station port registered"
        raise StationPortError(msg)
    return _invoker(method, url, headers, body)
