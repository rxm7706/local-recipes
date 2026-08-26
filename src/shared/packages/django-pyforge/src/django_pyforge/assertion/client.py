"""Portal emitter: in-process RS256 sign. Portals must not open HTTP to services."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django_pyforge.assertion.crypto import sign_assertion, verify_assertion
from django_pyforge.assertion.schema import audience_for

InvokeRunner = Callable[..., dict[str, Any]]


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

    def invoke(
        self,
        sub: str,
        roles: list[str],
        station: str,
        argv: list[str],
        *,
        private_pem: str | None = None,
        runner: InvokeRunner | None = None,
    ) -> dict[str, Any]:
        """Emit, verify in-process, then project station argv (no HTTP)."""
        token = self.emit(sub, roles, station, private_pem=private_pem)
        verify_assertion(token, audience=audience_for(station))
        if runner is not None:
            return runner(station=station, argv=argv, token=token)
        return self._argv_projection(station, argv)

    @staticmethod
    def _argv_projection(station: str, argv: list[str]) -> dict[str, Any]:
        slug = ""
        if station == "herald" and len(argv) >= 3 and argv[:2] == ["deck", "status"]:
            slug = argv[2]
        elif argv:
            slug = argv[-1]
        return {
            "slug": slug,
            "linked": False,
            "project_id": None,
            "sync": None,
            "last_pull": None,
            "stale_mirror": False,
        }
