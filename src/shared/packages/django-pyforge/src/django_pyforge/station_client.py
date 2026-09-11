"""Portal-facing wrapper around ``pyforge.core.client`` (CAP-6 / AD-7).

Portals must not construct raw HTTP requests. They emit an RS256 assertion
through :class:`django_pyforge.assertion.client.PortalClient`, then call station
routes via this wrapper.
"""

from __future__ import annotations

import asyncio
from typing import Any

from django_pyforge.assertion.client import PortalClient
from django_pyforge.circuits import CircuitBreaker
from django_pyforge.circuits import Degraded
from pyforge.core.client import API_VERSION_HEADER
from pyforge.core.client import PyForgeStationClient
from pyforge.core.client import StationClientError
from pyforge.core.client import Transport

__all__ = [
    "API_VERSION_HEADER",
    "PyForgeStationClient",
    "StationClientDegraded",
    "StationHttpClient",
    "Transport",
    "station_outbound_breaker",
]

station_outbound_breaker = CircuitBreaker(name="station_outbound")


class StationClientDegraded(StationClientError):
    """Outbound station call degraded because the circuit is open."""


def _guarded_transport(transport: Transport) -> Transport:
    """Wrap a transport so outbound failures trip the shared async breaker."""

    def wrapped(
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
    ) -> bytes:
        def _call() -> bytes:
            return transport(method, url, headers, body)

        result = asyncio.run(station_outbound_breaker.call_or_degrade(_call))
        if isinstance(result, Degraded):
            raise StationClientDegraded(result.reason)
        return result

    return wrapped


class StationHttpClient:
    """Reach ``/stations/<name>/api/v<N>/`` with a host-minted assertion."""

    def __init__(self, portal_client: PortalClient | None = None) -> None:
        self._portal = portal_client or PortalClient()

    def emit_and_build(
        self,
        *,
        station: str,
        sub: str,
        roles: list[str],
        version: int = 1,
        base_url: str = "",
        private_pem: str | None = None,
        transport: Transport | None = None,
    ) -> PyForgeStationClient:
        assertion = self._portal.emit(sub, roles, station, private_pem=private_pem)
        if transport is None:
            from django_pyforge.station_port import default_transport

            transport = default_transport()
        if transport is not None:
            transport = _guarded_transport(transport)
        return PyForgeStationClient(
            station=station,
            version=version,
            base_url=base_url,
            assertion=assertion,
            transport=transport,
        )

    def post(
        self,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        station: str,
        sub: str,
        roles: list[str],
        version: int = 1,
        base_url: str = "",
        private_pem: str | None = None,
        transport: Transport | None = None,
    ) -> bytes:
        if transport is None:
            from django_pyforge.station_port import default_transport

            transport = default_transport()
        client = self.emit_and_build(
            station=station,
            sub=sub,
            roles=roles,
            version=version,
            base_url=base_url,
            private_pem=private_pem,
            transport=transport,
        )
        return client.post(path, payload=payload)
