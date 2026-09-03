"""Profile switch for station API reachability (Story 43.3).

Default (co-located): in-process ASGI via ``pyforge.core.station_port``.
``STATION_REMOTE=1``: ``pyforge.core.client`` over HTTP with the assertion.
"""

from __future__ import annotations

from pyforge.core.client import Transport
from pyforge.core.station_port import invoke_in_process
from pyforge.core.station_port import is_station_remote
from pyforge.core.station_port import register_in_process_invoker

__all__ = [
    "default_transport",
    "is_station_remote",
    "make_in_process_transport",
    "register_in_process_handler",
]


def register_in_process_handler(fn: object) -> None:
    """Register the host invoker (called from ``config.station_port`` at startup)."""
    register_in_process_invoker(fn)  # type: ignore[arg-type]


def replace_in_process_handler(fn: object) -> object | None:
    """Test seam: swap the invoker through the django-pyforge bridge."""
    from pyforge.core.station_port import replace_in_process_invoker

    return replace_in_process_invoker(fn)  # type: ignore[arg-type]


def make_in_process_transport() -> Transport:
    """Return a ``PyForgeStationClient`` transport that never loopbacks HTTP."""

    def transport(
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
    ) -> bytes:
        return invoke_in_process(method, url, headers, body)

    return transport


def default_transport() -> Transport | None:
    """In-process transport when co-located; ``None`` selects urllib HTTP."""
    if is_station_remote():
        return None
    return make_in_process_transport()
