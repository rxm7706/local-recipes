"""The one genuinely-live-socket proof for Story 13.6: a real ``daphne``
subprocess, started against ``pyforge.herald.webhook_host:application``,
answering a real signed HTTP POST over a real loopback socket.

Every other webhook/webhook_host test (``test_webhook.py``,
``test_webhook_host.py``) hand-constructs an ASGI ``scope``/``receive``/
``send`` triple -- deliberately, per Boundaries & Constraints ("mirror
13.4's hand-built scope/receive/send pattern for non-socket tests") -- so
none of them prove the ASGI callable actually answers a REAL socket, behind
a REAL ASGI server, the way ``.github/workflows/herald-live-demo.yml``'s
three jobs do for real. This test is that proof, and the only one: opt-in
only (``live_webhook`` marker + ``HERALD_LIVE_WEBHOOK`` skipif, mirroring
``test_live_design_spike.py``'s existing ``live``/``HERALD_LIVE_DESIGN``
precedent), so it never runs in the default ``pyforge-herald-test`` gate --
starting a real subprocess and binding a real port is exactly what that
gate's autouse ``deny_network`` fixture exists to keep out.

Run it deliberately:

    HERALD_LIVE_WEBHOOK=1 pixi run -e pyforge-herald pytest \\
        src/shared/packages/pyforge-herald/tests/test_webhook_live_smoke.py -v

Uses ``httpx2`` (already a Herald dependency -- Boundaries & Constraints
names it explicitly) to make the real HTTP call; no new test dependency.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx2
import pytest

LIVE_ENV = "HERALD_LIVE_WEBHOOK"

pytestmark = [
    pytest.mark.live_webhook,
    pytest.mark.skipif(
        not os.environ.get(LIVE_ENV),
        reason=f"live daphne subprocess smoke test -- set {LIVE_ENV}=1 to run it",
    ),
]

_STARTUP_TIMEOUT_SECONDS = 10.0
_SECRET = b"herald-live-smoke-secret"


def _free_loopback_port() -> int:
    """A port nothing is listening on right now. Small, unavoidable race
    (another process could claim it between this close and daphne's own
    bind) -- the standard "ask the OS for an ephemeral port, then reuse the
    number" pattern every port-picking test harness accepts."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _sign(secret: bytes, timestamp: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret, timestamp.encode("ascii") + b"." + body, hashlib.sha256).hexdigest()


def _wait_for_port(host: str, port: int, *, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_error: OSError | None = None
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError as exc:
            last_error = exc
            time.sleep(0.1)
    raise TimeoutError(f"daphne never started listening on {host}:{port} within {timeout}s") from last_error


@pytest.fixture
def live_daphne(tmp_path: Path):
    """Start a real ``daphne`` subprocess against
    ``pyforge.herald.webhook_host:application``, pointed at a scratch,
    job-local repo root -- never a persistent deployment (this story's own
    first AC). Yields ``(base_url, repo_root)``; always terminates the
    subprocess, even on failure."""
    port = _free_loopback_port()
    env = dict(os.environ)
    env["HERALD_REPO_ROOT"] = str(tmp_path)
    env["HERALD_WEBHOOK_SECRET"] = _SECRET.decode("utf-8")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "daphne",
            "-b",
            "127.0.0.1",
            "-p",
            str(port),
            "pyforge.herald.webhook_host:application",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        _wait_for_port("127.0.0.1", port, timeout=_STARTUP_TIMEOUT_SECONDS)
        yield f"http://127.0.0.1:{port}", tmp_path
    finally:
        process.terminate()
        try:
            output = process.communicate(timeout=5)[0]
        except subprocess.TimeoutExpired:
            process.kill()
            output = process.communicate()[0]
        if process.returncode not in (0, None, -15):  # -15 == SIGTERM, expected
            print(output)  # surfaced by pytest on failure via captured stdout


def test_daphne_answers_a_real_signed_on_ship_post(live_daphne):
    base_url, repo_root = live_daphne
    body = json.dumps({"station": "warden", "compute_hours": 1.5}).encode("utf-8")
    ts = str(int(time.time()))
    response = httpx2.post(
        f"{base_url}/stations/herald/api/v1/webhooks/on-ship",
        content=body,
        headers={
            "X-Hub-Signature-256": _sign(_SECRET, ts, body),
            "X-Hub-Timestamp": ts,
            "Content-Type": "application/json",
        },
        timeout=10.0,
    )
    assert response.status_code == 201
    assert response.json()["station"] == "warden"

    from pyforge.herald import progress

    records = progress.read_all(repo_root / progress.DEFAULT_PROGRESS_PATH)
    assert len(records) == 1
    assert records[0].compute_hours == 1.5


def test_daphne_rejects_an_unsigned_request(live_daphne):
    base_url, repo_root = live_daphne
    body = json.dumps({"station": "warden"}).encode("utf-8")
    response = httpx2.post(
        f"{base_url}/stations/herald/api/v1/webhooks/on-ship",
        content=body,
        headers={"Content-Type": "application/json"},
        timeout=10.0,
    )
    assert response.status_code == 401

    from pyforge.herald import progress

    assert progress.read_all(repo_root / progress.DEFAULT_PROGRESS_PATH) == []
