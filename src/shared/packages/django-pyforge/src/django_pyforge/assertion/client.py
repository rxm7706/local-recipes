"""Portal emitter: in-process RS256 sign. Portals must not open HTTP to services."""

from __future__ import annotations

from typing import Any

from django_pyforge.assertion.crypto import sign_assertion


class PortalClient:
    """Sign a service assertion for ``station`` with the host's RS256 key."""

    def emit(
        self,
        sub: str,
        roles: list[str],
        station: str,
        *,
        private_pem: str | None = None,
    ) -> str:
        return sign_assertion(
            sub=sub,
            roles=roles,
            station=station,
            private_pem=private_pem,
        )

    def start(
        self,
        *,
        station: str,
        sub: str,
        roles: list[str],
        tool: str,
        payload: dict[str, Any] | None = None,
        private_pem: str | None = None,
    ) -> str:
        """Emit an assertion, then publish through the supervisor. No HTTP."""
        from django_pyforge.supervisor import publish_start  # noqa: PLC0415

        assertion = self.emit(sub, roles, station, private_pem=private_pem)
        return publish_start(
            station=station,
            assertion=assertion,
            tool=tool,
            payload=payload,
        )

    def get(
        self,
        *,
        station: str,
        handle: str,
        sub: str,
        roles: list[str],
        private_pem: str | None = None,
    ) -> dict[str, Any]:
        """Emit a fresh assertion, then read the same supervisor run. No HTTP."""
        from django_pyforge.supervisor import get_run as supervisor_get_run  # noqa: PLC0415

        assertion = self.emit(sub, roles, station, private_pem=private_pem)
        return supervisor_get_run(station=station, handle=handle, assertion=assertion)
