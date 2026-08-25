"""Portal emitter: in-process RS256 sign. Portals must not open HTTP to services."""

from __future__ import annotations

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
