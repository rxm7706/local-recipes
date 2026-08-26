"""Portal emitter: in-process RS256 sign. Portals must not open HTTP to services."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

InvokeRunner = Callable[..., dict[str, Any]]
StationJob = Callable[..., dict[str, Any]]

LAST_DIAGNOSE_TOOL = "last_diagnose"

_portal_jobs: dict[tuple[str, str], Callable[..., dict[str, Any]]] = {}

_LOOP_HOME_ROOT_ENV = "BMAD_LOOP_HOME_ROOT"
_MARKER = Path("_bmad") / "custom" / ".active-project"


def register_portal_job(station: str, tool: str, fn: Callable[..., dict[str, Any]]) -> None:
    """Bind an in-process portal job. Portals must not open HTTP to reach it."""
    _portal_jobs[(station, tool)] = fn


def lookup_portal_job(station: str, tool: str) -> Callable[..., dict[str, Any]]:
    try:
        return _portal_jobs[(station, tool)]
    except KeyError as exc:
        msg = f"no portal job for {station}/{tool}"
        raise KeyError(msg) from exc


def parse_recall_cli(stdout: str) -> dict[str, Any]:
    """Turn ``scribe recall`` stdout into cited portal results."""
    citation: str | None = None
    body: list[str] = []
    for line in stdout.splitlines():
        if line.startswith("[source: ") and line.endswith("]"):
            citation = line[len("[source: ") : -1]
        else:
            body.append(line)
    text = "\n".join(body).strip() or "no grounded answer found"
    grounded = citation is not None and text != "no grounded answer found"
    if text == "no grounded answer found":
        return {"grounded": False, "text": text, "citation": None}
    return {"grounded": grounded, "text": text, "citation": citation}


def _grammar_recall(payload: dict[str, Any]) -> dict[str, Any]:
    query = str(payload.get("query", ""))
    pyforge = shutil.which("pyforge")
    argv = [pyforge, "scribe", "recall", query] if pyforge else ["scribe", "recall", query]
    completed = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        check=False,
    )
    return parse_recall_cli(completed.stdout)


def _scribe_recall_job(
    *,
    assertion: str,
    payload: dict[str, Any] | None = None,
    **_: Any,
) -> dict[str, Any]:
    del assertion
    return _grammar_recall(payload or {})


register_portal_job("scribe", "recall", _scribe_recall_job)


def _default_station_job(
    *,
    station: str,
    job: str,
    payload: dict[str, Any],
    assertion: str,
) -> dict[str, Any]:
    from django_pyforge.assertion.crypto import verify_assertion
    from django_pyforge.assertion.schema import audience_for

    verify_assertion(assertion, audience=audience_for(station))
    registered = lookup_portal_job(station, job)
    return registered(assertion=assertion, payload=payload)


class PortalClient:
    """In-process portal client. Sign assertions; list provisioned loop homes.

    Station jobs that are not an MCP hop (read-only inventory) also go
    through this client — never raw HTTP and never a portal import of
    ``pyforge.*`` in ``src/platform/``. ``call`` is the named-job path:
    emit, verify, then the registered in-process job (or an injectable
    runner). ``start`` / ``get`` are the supervisor handle path.
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
        from django_pyforge.assertion.crypto import verify_assertion
        from django_pyforge.assertion.schema import audience_for

        assertion = self.emit(sub, roles, station, private_pem=private_pem)
        verify_assertion(assertion, audience=audience_for(station))
        job = lookup_portal_job(station, LAST_DIAGNOSE_TOOL)
        return job(assertion=assertion)

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
        from django_pyforge.assertion.crypto import verify_assertion
        from django_pyforge.assertion.schema import audience_for

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

    def provision_list(
        self,
        *,
        cwd: str | Path | None = None,
    ) -> dict[str, tuple[str, ...]]:
        """Named pixi environments as ``steward provision --list`` (in-process)."""
        from pyforge.steward.provision import load_pixi_environments
        from pyforge.steward.provision import repo_root

        return load_pixi_environments(cwd=cwd if cwd is not None else repo_root())

    def call(
        self,
        station: str,
        job: str,
        payload: dict[str, Any],
        *,
        sub: str,
        roles: list[str],
        private_pem: str | None = None,
        runner: StationJob | None = None,
    ) -> dict[str, Any]:
        assertion = self.emit(
            sub,
            roles,
            station,
            private_pem=private_pem,
        )
        run = runner or _default_station_job
        return run(
            station=station,
            job=job,
            payload=payload,
            assertion=assertion,
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
