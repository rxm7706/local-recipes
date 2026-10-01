"""Story 78.1 / CAP-99 (DW-FU-11-1): the mounted Langflow's auth posture.

`config/asgi.py` forwards every `/langflow/...` request into Langflow with no
platform-side gate, and Langflow's own default (`AUTO_LOGIN=True`) hands any
caller a bearer token for the bootstrap superuser. Settings therefore FORCE
auto-login off and take the superuser password from the environment only; a
deployed boot without it refuses by name. These tests prove each seam without
needing the `langflow` package: settings are loaded for real in a child process
(the only way to observe a decision taken at settings-load), and the compose file
is parsed. The live refusal through `config.asgi` is
`test_langflow_mount.py::test_auto_login_hands_out_no_token_through_the_platform`
(needs `langflow`); the chart's secret reference is in `test_chart_invariants.py`.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

PLATFORM_ROOT = Path(__file__).resolve().parents[1]
BASE_SETTINGS = PLATFORM_ROOT / "config" / "settings" / "base.py"
COMPOSE_FILE = PLATFORM_ROOT / "compose" / "compose.yml"

_DEPLOYED_ENV = {
    "DJANGO_SETTINGS_MODULE": "config.settings.production",
    "DJANGO_SECRET_KEY": "story-78-1-test-secret-key-not-for-production-use",
    "DJANGO_ADMIN_URL": "secret-admin/",
    "MCP_HOST_SIDECAR_BASE_URL": "http://platform-mcp-host:8090",
    "COMPONENT_OIDC_ISSUER": "https://idp.invalid/realms/platform",
    "COMPONENT_OIDC_JWKS_URL": "https://idp.invalid/realms/platform/certs",
    "COMPONENT_OIDC_AUDIENCE": "platform-web",
}
_PASSWORD = "story-78-1-test-langflow-password"  # noqa: S105 -- a test value


def _load_settings(
    expression: str,
    **env: str,
) -> subprocess.CompletedProcess[str]:
    """Evaluate ``expression`` against a FRESHLY loaded settings module.

    The child inherits nothing that could hand it the value under test: no
    ``.env`` reader, no locality keys, and no Langflow keys unless ``env`` gives
    them (the pytest harness exports a throwaway password for the lanes that
    boot Langflow -- see ``conftest.py``).
    """
    child_env = dict(os.environ)
    for key in (
        "DJANGO_READ_DOT_ENV_FILE",
        "COMPONENT_RUNTIME",
        "COMPONENT_PROCESS",
        "LANGFLOW_AUTO_LOGIN",
        "LANGFLOW_SUPERUSER",
        "LANGFLOW_SUPERUSER_PASSWORD",
    ):
        child_env.pop(key, None)
    child_env["PYTHONPATH"] = os.pathsep.join(
        [str(PLATFORM_ROOT), *(entry for entry in sys.path if entry)],
    )
    child_env.update(env)
    return subprocess.run(  # noqa: S603 -- fixed argv, no shell, no untrusted input
        [
            sys.executable,
            "-c",
            f"import os; from django.conf import settings; print({expression})",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
        cwd=PLATFORM_ROOT,
        env=child_env,
    )


_FORCED = 'settings.LANGFLOW_AUTO_LOGIN, os.environ["LANGFLOW_AUTO_LOGIN"]'


@pytest.mark.parametrize("deployer_value", ["true", "True", "1", "yes", "on"])
def test_langflow_auto_login_is_forced_off_whatever_the_environment_says(
    deployer_value: str,
) -> None:
    """A `.env` line, a chart env or a shell export cannot revive auto-login."""
    proc = _load_settings(
        _FORCED,
        DJANGO_SETTINGS_MODULE="config.settings.test",
        LANGFLOW_AUTO_LOGIN=deployer_value,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "False False"


def test_langflow_auto_login_is_forced_off_on_the_deployed_leaf_too() -> None:
    proc = _load_settings(
        _FORCED,
        **_DEPLOYED_ENV,
        LANGFLOW_SUPERUSER_PASSWORD=_PASSWORD,
        LANGFLOW_AUTO_LOGIN="true",
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "False False"


def test_langflow_superuser_password_is_the_environment_value_or_unset() -> None:
    """No default password: unset is `None` -- never a credential."""
    unset = _load_settings(
        "settings.LANGFLOW_SUPERUSER_PASSWORD",
        DJANGO_SETTINGS_MODULE="config.settings.test",
    )
    given = _load_settings(
        "settings.LANGFLOW_SUPERUSER_PASSWORD",
        DJANGO_SETTINGS_MODULE="config.settings.test",
        LANGFLOW_SUPERUSER_PASSWORD=_PASSWORD,
    )

    assert unset.returncode == 0, unset.stderr
    assert unset.stdout.strip() == "None"
    assert given.returncode == 0, given.stderr
    assert given.stdout.strip() == _PASSWORD


def _env_call(node: ast.Assign) -> ast.Call | None:
    value = node.value
    if (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id == "env"
    ):
        return value
    return None


def test_settings_source_gives_the_langflow_password_no_default() -> None:
    """Reads the source, so a literal default cannot hide behind an unset env."""
    tree = ast.parse(BASE_SETTINGS.read_text(encoding="utf-8"))
    found = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        targets = {t.id for t in node.targets if isinstance(t, ast.Name)}
        if "LANGFLOW_SUPERUSER_PASSWORD" in targets and (call := _env_call(node)):
            found["call"] = call
    assert "call" in found, "LANGFLOW_SUPERUSER_PASSWORD must be read via env(...)"
    call = found["call"]
    assert [a.value for a in call.args if isinstance(a, ast.Constant)] == [
        "LANGFLOW_SUPERUSER_PASSWORD",
    ], "no positional default"
    defaults = {k.arg: k.value for k in call.keywords}
    assert set(defaults) == {"default"}
    default = defaults["default"]
    assert isinstance(default, ast.Constant), "the default must be a plain None"
    assert default.value is None, "no baked-in Langflow password"


def test_a_deployed_boot_without_the_langflow_password_refuses_by_name() -> None:
    proc = _load_settings("settings.SECRET_KEY", **_DEPLOYED_ENV)

    assert proc.returncode != 0
    assert "LANGFLOW_SUPERUSER_PASSWORD" in proc.stderr
    assert "ImproperlyConfigured" in proc.stderr


def test_a_deployed_boot_with_the_langflow_password_starts() -> None:
    proc = _load_settings(
        "settings.LANGFLOW_SUPERUSER_PASSWORD",
        **_DEPLOYED_ENV,
        LANGFLOW_SUPERUSER_PASSWORD=_PASSWORD,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == _PASSWORD


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


def test_compose_takes_the_langflow_password_by_reference_never_a_literal() -> None:
    environments = _compose_environments()

    platform = environments["platform"]["LANGFLOW_SUPERUSER_PASSWORD"]
    assert platform.startswith("${LANGFLOW_SUPERUSER_PASSWORD:?"), platform
    for service, env in environments.items():
        for key, value in env.items():
            if key.startswith("LANGFLOW_") and "PASSWORD" in key:
                assert value.startswith("${"), (
                    f"{service}: {key} must be an env reference, got a literal"
                )
        assert env.get("LANGFLOW_AUTO_LOGIN", "false").lower() not in {
            "true",
            "1",
            "yes",
            "on",
        }, f"{service}: compose must not switch Langflow auto-login back on"
