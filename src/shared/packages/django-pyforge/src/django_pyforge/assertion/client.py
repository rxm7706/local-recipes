"""Portal emitter: in-process RS256 sign. Portals must not open HTTP to services."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from django_pyforge.assertion.crypto import sign_assertion, verify_assertion
from django_pyforge.assertion.schema import audience_for

InvokeRunner = Callable[..., dict[str, Any]]

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
