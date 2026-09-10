"""Story 50.3: the S3-client seam proves the pap:AD-1 exception end-to-end.

A real round trip against a real local Silo server -- never a mock. This
test runs its OWN ephemeral Silo instance (own port, own tmp data dir)
rather than reaching for Story 50.2's fixed-contract-port dev instance
(`pixi run -e platform-object-storage platform-object-storage-up`, always
127.0.0.1:9000): a shared, fixed-port dev server is the wrong thing for an
automated, parallel-safe test to depend on, but it is the SAME Silo binary
that instance runs, from the same `platform-object-storage` pixi env.

Skips (does not fail) when that env isn't installed on this machine --
`platform-object-storage` is a separate, standalone pixi environment
(win-64-less workspace member, `scribe-pg` precedent) that the ordinary
`platform-dev` / `platform-ci-test` test run does not provision. A missing
optional local-dev environment is not a defect in `src/platform/` itself.
"""

from __future__ import annotations

import os
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from django.core.exceptions import ImproperlyConfigured

from config.object_storage import object_storage_client

REPO_ROOT = Path(__file__).resolve().parents[3]
_SILO_BINARY = REPO_ROOT / ".pixi" / "envs" / "platform-object-storage" / "bin" / "silo"

_ACCESS_KEY = "roundtriptestaccess"
_SECRET_KEY = "roundtriptestsecret1234567890"  # noqa: S105
_HEALTH_POLL_SECONDS = 30
_HTTP_OK = 200


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _health_ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=1) as resp:  # noqa: S310
            return resp.status == _HTTP_OK
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


@pytest.fixture
def local_silo(tmp_path):
    """Start a real, ephemeral Silo server; yield its endpoint + credentials."""
    if not _SILO_BINARY.is_file():
        pytest.skip(
            "platform-object-storage pixi env not installed -- run "
            "`pixi install -e platform-object-storage` to exercise this "
            "round trip (Story 50.1's Silo recipe)"
        )

    api_port = _free_port()
    console_port = _free_port()
    data_dir = tmp_path / "silo-data"
    data_dir.mkdir()
    env = {
        **os.environ,
        "MINIO_ROOT_USER": _ACCESS_KEY,
        "MINIO_ROOT_PASSWORD": _SECRET_KEY,
    }
    proc = subprocess.Popen(  # noqa: S603
        [
            str(_SILO_BINARY),
            "server",
            str(data_dir),
            "--address",
            f":{api_port}",
            "--console-address",
            f":{console_port}",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    endpoint = f"http://127.0.0.1:{api_port}"
    try:
        for _ in range(_HEALTH_POLL_SECONDS):
            if _health_ok(f"{endpoint}/minio/health/live"):
                break
            time.sleep(1)
        else:
            proc.terminate()
            pytest.fail("ephemeral silo server did not become healthy in time")
        yield endpoint, _ACCESS_KEY, _SECRET_KEY
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_object_storage_client_round_trips_against_local_silo(local_silo, settings):
    """put then get returns the same bytes -- proven, not just declared."""
    endpoint, access_key, secret_key = local_silo
    settings.OBJECT_STORAGE_ENDPOINT_URL = endpoint
    settings.OBJECT_STORAGE_ACCESS_KEY = access_key
    settings.OBJECT_STORAGE_SECRET_KEY = secret_key

    client = object_storage_client()
    bucket = "platform-seam-roundtrip"
    key = "proof.txt"
    payload = b"pap:AD-1 dated exception -- consumed, not self-hosted"

    client.create_bucket(Bucket=bucket)
    client.put_object(Bucket=bucket, Key=key, Body=payload)
    got = client.get_object(Bucket=bucket, Key=key)["Body"].read()

    assert got == payload


def test_object_storage_client_raises_typed_error_when_unconfigured(settings):
    """No endpoint configured -> a typed, named error -- never a silent no-op."""
    settings.OBJECT_STORAGE_ENDPOINT_URL = None
    settings.OBJECT_STORAGE_ACCESS_KEY = None
    settings.OBJECT_STORAGE_SECRET_KEY = None

    with pytest.raises(ImproperlyConfigured, match="OBJECT_STORAGE_ENDPOINT_URL"):
        object_storage_client()
