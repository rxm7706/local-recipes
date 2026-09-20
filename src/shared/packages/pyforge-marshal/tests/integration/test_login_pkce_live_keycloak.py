"""Story 33.14 — live PKCE login against compose Keycloak."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

pytest.importorskip("jwt")
import jwt
from jwt import PyJWKClient

from pyforge.marshal.adapters.oidc_pkce import PkceLogin, PkceLoginError

REPO_ROOT = Path(__file__).resolve().parents[6]
COMPOSE_FILE = REPO_ROOT / "src/platform/compose/compose.yml"
ISSUER = "http://127.0.0.1:8080/realms/platform"
CLIENT_ID = "pyforge-cli"
USERNAME = "marshal-operator"
PASSWORD = "marshal-operator"


def _compose_cmd() -> list[str]:
    engine = os.environ.get("PLATFORM_CI_LOCAL_ENGINE", "docker")
    return [engine, "compose", "-f", str(COMPOSE_FILE)]


def _docker_available() -> bool:
    engine = os.environ.get("PLATFORM_CI_LOCAL_ENGINE", "docker")
    return shutil.which(engine) is not None


def _keycloak_ready(timeout_s: float = 180.0) -> bool:
    deadline = time.monotonic() + timeout_s
    probe = f"{ISSUER}/.well-known/openid-configuration"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(probe, timeout=5) as response:  # noqa: S310
                if response.status == 200:
                    return True
        except OSError:
            time.sleep(2.0)
    return False


@pytest.fixture(scope="module")
def keycloak_stack():
    if not _docker_available():
        pytest.skip("docker/podman not available")
    up = subprocess.run(
        [*_compose_cmd(), "up", "-d", "keycloak"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if up.returncode != 0:
        pytest.skip(f"could not start keycloak: {up.stderr or up.stdout}")
    if not _keycloak_ready():
        subprocess.run([*_compose_cmd(), "down", "keycloak"], cwd=REPO_ROOT, check=False)
        pytest.skip("keycloak did not become ready in time")
    yield
    subprocess.run([*_compose_cmd(), "down", "keycloak"], cwd=REPO_ROOT, check=False)


def _follow_keycloak_login(auth_url: str) -> None:
    cookie = ""
    url = auth_url
    for _ in range(12):
        request = urllib.request.Request(  # noqa: S310
            url,
            headers={"Cookie": cookie} if cookie else {},
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            body = response.read().decode("utf-8", errors="replace")
            set_cookie = response.headers.get("Set-Cookie")
            if set_cookie:
                cookie = set_cookie.split(";", 1)[0]
            final_url = response.geturl()
        if final_url.startswith("http://127.0.0.1:") and "/callback" in final_url:
            with urllib.request.urlopen(final_url, timeout=10) as response:  # noqa: S310
                response.read()
            return
        match = re.search(r'form[^>]+action="([^"]+)"', body)
        if match is None:
            raise PkceLoginError("keycloak login form not found")
        action = html_unescape(match.group(1))
        if action.startswith("/"):
            parsed = urllib.parse.urlparse(final_url)
            action = f"{parsed.scheme}://{parsed.netloc}{action}"
        form_data = urllib.parse.urlencode({"username": USERNAME, "password": PASSWORD}).encode("utf-8")
        post = urllib.request.Request(  # noqa: S310
            action,
            data=form_data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": cookie,
            },
            method="POST",
        )
        with urllib.request.urlopen(post, timeout=30) as response:  # noqa: S310
            location = response.geturl()
            set_cookie = response.headers.get("Set-Cookie")
            if set_cookie:
                cookie = set_cookie.split(";", 1)[0]
            if location.startswith("http://127.0.0.1:") and "/callback" in location:
                with urllib.request.urlopen(location, timeout=10) as callback:  # noqa: S310
                    callback.read()
                return
            url = location
    raise PkceLoginError("keycloak login redirect chain did not reach callback")


def html_unescape(value: str) -> str:
    return (
        value.replace("&amp;", "&")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
    )


def _decode_bearer(bearer: str) -> dict[str, object]:
    client = PyJWKClient(f"{ISSUER}/protocol/openid-connect/certs")
    signing_key = client.get_signing_key_from_jwt(bearer)
    return jwt.decode(
        bearer,
        signing_key.key,
        algorithms=["RS256"],
        audience="platform-web",
        issuer=ISSUER,
    )


@pytest.mark.slow
def test_pkce_login_mints_for_marshal_role(keycloak_stack) -> None:
    del keycloak_stack
    token_holder: list[str] = []
    errors: list[Exception] = []

    def browser(url: str) -> None:
        _follow_keycloak_login(url)

    def run_login() -> None:
        try:
            token_holder.append(
                PkceLogin(
                    issuer=ISSUER,
                    client_id=CLIENT_ID,
                    timeout_s=120.0,
                    open_browser=browser,
                ).run()
            )
        except Exception as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    thread = threading.Thread(target=run_login, daemon=True)
    thread.start()
    thread.join(timeout=120.0)
    assert not errors, errors[0] if errors else None
    bearer = token_holder[0]
    assert bearer
    claims = _decode_bearer(bearer)
    groups = claims.get("groups")
    assert isinstance(groups, list)
    assert "pyforge:station:marshal" in groups


@pytest.mark.slow
def test_staff_user_bearer_mints_403(keycloak_stack) -> None:
    del keycloak_stack
    token_url = f"{ISSUER}/protocol/openid-connect/token"
    body = urllib.parse.urlencode(
        {
            "grant_type": "password",
            "client_id": "platform-web",
            "client_secret": "local-compose-keycloak-secret-not-real",
            "username": "staff-user",
            "password": "staff-user",
        }
    ).encode("utf-8")
    request = urllib.request.Request(  # noqa: S310
        token_url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        payload = json.loads(response.read().decode("utf-8"))
    bearer = payload["access_token"]
    claims = _decode_bearer(bearer)
    groups = claims.get("groups")
    assert isinstance(groups, list)
    assert "pyforge:station:marshal" not in groups
