"""Story 83.2 (DW-10-3-3): session and CSRF cookies on the plain-HTTP local stack.

`config/settings/production.py` composed `SESSION_COOKIE_SECURE`,
`CSRF_COOKIE_SECURE` and the `__Secure-` cookie names as literals, but the compose
stack serves plain HTTP and a browser drops a `Secure` cookie (and any `__Secure-`
cookie) over HTTP -- so login, the admin and every CSRF-protected POST failed on the
documented stack while `/ht/` answered 200. The fix is one local-only switch,
`DJANGO_INSECURE_LOCAL_COOKIES`, honoured only when `COMPONENT_RUNTIME=local` (the
`config.broker_tls` precedent: a weaker posture needs an explicit local process and a
request by name). A deployed process composes `Secure` cookies and the `__Secure-`
names whatever its environment says.

Settings are loaded for real in a child process (the only way to observe a decision
taken at settings-load), the same technique as `test_langflow_auth_posture.py`; the
compose file is parsed. Removing the `is_local()` guard in `production.py` turns the
deployed-process rows red -- that is the mutation check this story's contract names.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

PLATFORM_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = PLATFORM_ROOT / "compose" / "compose.yml"

_SWITCH = "DJANGO_INSECURE_LOCAL_COOKIES"

_PRODUCTION_ENV = {
    "DJANGO_SETTINGS_MODULE": "config.settings.production",
    "DJANGO_SECRET_KEY": "story-83-2-test-secret-key-not-for-production-use",
    "DJANGO_ADMIN_URL": "secret-admin/",
    "MCP_HOST_SIDECAR_BASE_URL": "http://platform-mcp-host:8090",
    "COMPONENT_OIDC_ISSUER": "https://idp.invalid/realms/platform",
    "COMPONENT_OIDC_JWKS_URL": "https://idp.invalid/realms/platform/certs",
    "COMPONENT_OIDC_AUDIENCE": "platform-web",
    # Stage 1 refuses a deployed boot without it (Story 78.1); a test value.
    "LANGFLOW_SUPERUSER_PASSWORD": "story-83-2-test-langflow-password",
}

_COOKIES = (
    "(settings.SESSION_COOKIE_SECURE, settings.CSRF_COOKIE_SECURE, "
    "settings.SESSION_COOKIE_NAME, settings.CSRF_COOKIE_NAME)"
)


def _cookie_settings(**env: str) -> tuple[bool, bool, str, str]:
    """Load production settings FRESH in a child and return the four cookie values.

    The child inherits nothing that could hand it the posture under test: the
    locality marker and the switch are dropped unless ``env`` gives them (the pytest
    harness exports ``COMPONENT_RUNTIME=local`` for the whole run -- see
    ``conftest.py``).
    """
    child_env = dict(os.environ)
    for key in (
        "DJANGO_READ_DOT_ENV_FILE",
        "COMPONENT_RUNTIME",
        "COMPONENT_PROCESS",
        _SWITCH,
    ):
        child_env.pop(key, None)
    child_env["PYTHONPATH"] = os.pathsep.join(
        [str(PLATFORM_ROOT), *(entry for entry in sys.path if entry)],
    )
    child_env.update(_PRODUCTION_ENV)
    child_env.update(env)
    proc = subprocess.run(  # noqa: S603 -- fixed argv, no shell, no untrusted input
        [
            sys.executable,
            "-c",
            f"from django.conf import settings; print({_COOKIES})",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
        cwd=PLATFORM_ROOT,
        env=child_env,
    )
    assert proc.returncode == 0, proc.stderr
    return ast.literal_eval(proc.stdout.strip().splitlines()[-1])


def test_local_process_with_the_switch_on_serves_plain_http_cookies() -> None:
    """The documented stack: login and CSRF POSTs work over http."""
    session_secure, csrf_secure, session_name, csrf_name = _cookie_settings(
        COMPONENT_RUNTIME="local",
        **{_SWITCH: "True"},
    )

    assert session_secure is False
    assert csrf_secure is False
    assert not session_name.startswith("__Secure-")
    assert not csrf_name.startswith("__Secure-")
    assert (session_name, csrf_name) == ("sessionid", "csrftoken")


@pytest.mark.parametrize("switch", [{}, {_SWITCH: "False"}])
def test_local_process_asks_for_the_weaker_posture_by_name(
    switch: dict[str, str],
) -> None:
    """`COMPONENT_RUNTIME=local` alone is not a request: Secure stays the default."""
    assert _cookie_settings(COMPONENT_RUNTIME="local", **switch) == (
        True,
        True,
        "__Secure-sessionid",
        "__Secure-csrftoken",
    )


@pytest.mark.parametrize(
    "runtime",
    [
        pytest.param({}, id="runtime-unset"),
        pytest.param({"COMPONENT_RUNTIME": "production"}, id="runtime-production"),
        pytest.param({"COMPONENT_RUNTIME": "staging"}, id="runtime-unrecognised"),
        pytest.param({"COMPONENT_RUNTIME": "Local"}, id="runtime-not-exactly-local"),
    ],
)
def test_deployed_process_composes_secure_cookies_whatever_its_environment_says(
    runtime: dict[str, str],
) -> None:
    """The deployed-process row (mutation target): the switch cannot weaken a deploy.

    Fail-closed locality -- unset or unrecognised is deployed (`config.locality`).
    Remove the `is_local()` guard from `production.py` and this goes red.
    """
    assert _cookie_settings(**runtime, **{_SWITCH: "True"}) == (
        True,
        True,
        "__Secure-sessionid",
        "__Secure-csrftoken",
    )


def _compose_environments() -> dict[str, dict[str, str]]:
    yaml = pytest.importorskip("yaml")
    compose = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
    environments: dict[str, dict[str, str]] = {}
    for name, service in compose["services"].items():
        env = service.get("environment") or {}
        if isinstance(env, list):  # the `KEY=value` list form
            env = dict(item.split("=", 1) for item in env if "=" in item)
        environments[name] = {key: str(value) for key, value in env.items()}
    return environments


@pytest.mark.parametrize("service", ["platform", "worker"])
def test_compose_sets_the_switch_beside_the_plain_http_ssl_redirect_off(
    service: str,
) -> None:
    env = _compose_environments()[service]

    assert env["COMPONENT_RUNTIME"] == "local", "the switch is honoured only locally"
    assert env["DJANGO_SECURE_SSL_REDIRECT"] == "False"
    assert env[_SWITCH] == "True"
