"""Portal emitter: in-process RS256 sign. Portals must not open HTTP to services."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django_pyforge.assertion.crypto import sign_assertion
from django_pyforge.assertion.crypto import verify_assertion
from django_pyforge.assertion.schema import audience_for

LAST_DIAGNOSE_TOOL = "last_diagnose"

_portal_jobs: dict[tuple[str, str], Callable[..., dict[str, Any]]] = {}


def register_portal_job(station: str, tool: str, fn: Callable[..., dict[str, Any]]) -> None:
    """Bind an in-process portal job. Portals must not open HTTP to reach it."""
    _portal_jobs[(station, tool)] = fn


def lookup_portal_job(station: str, tool: str) -> Callable[..., dict[str, Any]]:
    try:
        return _portal_jobs[(station, tool)]
    except KeyError as exc:
        msg = f"no portal job for {station}/{tool}"
        raise KeyError(msg) from exc


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

    def last_diagnose(
        self,
        sub: str,
        roles: list[str],
        station: str = "mason",
        *,
        private_pem: str | None = None,
    ) -> dict[str, Any]:
        """Return one last diagnose (or equivalent) via in-process emit + job."""
        assertion = self.emit(sub, roles, station, private_pem=private_pem)
        verify_assertion(assertion, audience=audience_for(station))
        job = lookup_portal_job(station, LAST_DIAGNOSE_TOOL)
        return job(assertion=assertion)
