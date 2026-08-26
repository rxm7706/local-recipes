"""Portal emitter: in-process RS256 sign. Portals must not open HTTP to services."""

from __future__ import annotations

from pathlib import Path


class PortalClient:
    """Sign a service assertion for ``station`` with the host's RS256 key.

    Station jobs that are not an MCP hop (read-only inventory) also go
    through this client — never raw HTTP and never a portal import of
    ``pyforge.*`` in ``src/platform/``.
    """

    def emit(
        self,
        sub: str,
        roles: list[str],
        station: str,
        *,
        private_pem: str | None = None,
    ) -> str:
        from django_pyforge.assertion.crypto import sign_assertion

        return sign_assertion(
            sub=sub,
            roles=roles,
            station=station,
            private_pem=private_pem,
        )

    def provision_list(
        self,
        *,
        cwd: str | Path | None = None,
    ) -> dict[str, tuple[str, ...]]:
        """Named pixi environments as ``steward provision --list`` (in-process)."""
        from pyforge.steward.provision import load_pixi_environments
        from pyforge.steward.provision import repo_root

        return load_pixi_environments(cwd=cwd if cwd is not None else repo_root())
