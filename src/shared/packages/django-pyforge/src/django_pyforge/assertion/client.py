"""Portal emitter: in-process RS256 sign. Portals must not open HTTP to services."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
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


_LOOP_HOME_ROOT_ENV = "BMAD_LOOP_HOME_ROOT"
_MARKER = Path("_bmad") / "custom" / ".active-project"


class PortalClient:
    """In-process portal client. Sign assertions; list provisioned loop homes."""

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

    def list_loop_homes(self) -> list[dict[str, str | None]]:
        """Return provisioned loop homes under ``BMAD_LOOP_HOME_ROOT``.

        In-process filesystem read only. No HTTP. A home is a child directory
        that carries Marshal's active-project marker (Story 1.4).
        """
        root = self._loop_home_root()
        try:
            if not root.is_dir():
                return []
            children = list(root.iterdir())
        except OSError:
            return []
        homes: list[dict[str, str | None]] = []
        for child in sorted(children, key=lambda path: path.name):
            if not child.is_dir():
                continue
            marker = child / _MARKER
            try:
                if not marker.is_file():
                    continue
                active = marker.read_text(encoding="utf-8").strip() or None
            except OSError:
                continue
            homes.append(
                {
                    "slug": child.name,
                    "path": str(child.resolve()),
                    "active_project": active,
                }
            )
        return homes

    def _loop_home_root(self) -> Path:
        override = os.environ.get(_LOOP_HOME_ROOT_ENV)
        root = Path(override).expanduser() if override else Path.home() / ".bmad-loops"
        if not root.is_absolute():
            root = Path.cwd() / root
        return root

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
