"""Portal emitter: in-process RS256 sign. Portals must not open HTTP to services."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from typing import Any

from django_pyforge.assertion.crypto import sign_assertion, verify_assertion
from django_pyforge.assertion.schema import audience_for

StationJob = Callable[..., dict[str, Any]]


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


def _default_station_job(
    *,
    station: str,
    job: str,
    payload: dict[str, Any],
    assertion: str,
) -> dict[str, Any]:
    verify_assertion(assertion, audience=audience_for(station))
    if station == "scribe" and job == "recall":
        return _grammar_recall(payload)
    msg = f"unsupported portal job {station}:{job}"
    raise ValueError(msg)


class PortalClient:
    """Sign a service assertion for ``station`` with the host's RS256 key.

    ``call`` is the only station-compute path portals may use: emit, verify,
    then run the public grammar. Portals must not open HTTP to services.
    """

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
