"""CAP-3 / steward 16.2: stage-1 required-settings refusals.

Every case drives the public ``refuse_required_settings`` / ``run_stage_one``
APIs. Fixture coverage is one case per required key (absence + invalid where
applicable). Distinguishing substrings are the setting name and its remedy so
no two keys can pass each other's test.

``COMPONENT_RUNTIME`` is deleted rather than set to a deployed value because
locality fails closed (absent == deployed).
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

import pytest
from django.core.exceptions import ImproperlyConfigured

from config.locality import LOCAL
from config.locality import RUNTIME_ENV_VAR
from config.startup import refuse_required_settings
from config.startup import run_stage_one
from config.startup.stage_one import REQUIRED_SETTINGS
from config.startup.stage_one import RequiredSetting


@pytest.fixture(autouse=True)
def _deployed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(RUNTIME_ENV_VAR, raising=False)


@pytest.fixture
def required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """A fully valid deployed env for the required-settings contract."""
    monkeypatch.setenv(
        "DJANGO_SECRET_KEY",
        "unit-test-secret-key-not-for-production-use",
    )
    monkeypatch.setenv("DJANGO_ADMIN_URL", "secret-admin/")
    monkeypatch.setenv("MCP_HOST_SIDECAR_BASE_URL", "http://platform-mcp-host:8090")
    monkeypatch.setenv("COMPONENT_OIDC_ISSUER", "https://idp.example/realms/platform")
    monkeypatch.setenv(
        "COMPONENT_OIDC_JWKS_URL",
        "https://idp.example/realms/platform/protocol/openid-connect/certs",
    )
    monkeypatch.setenv("COMPONENT_OIDC_AUDIENCE", "platform-web")


def _refusal_message() -> str:
    with pytest.raises(ImproperlyConfigured) as refused:
        refuse_required_settings()
    return str(refused.value)


@pytest.mark.parametrize(
    "setting",
    list(REQUIRED_SETTINGS),
    ids=[s.name for s in REQUIRED_SETTINGS],
)
def test_each_required_key_absent_refuses_naming_setting_and_remedy(
    monkeypatch: pytest.MonkeyPatch,
    required_env: None,
    setting: RequiredSetting,
) -> None:
    monkeypatch.delenv(setting.name, raising=False)

    message = _refusal_message()

    assert setting.name in message
    assert setting.remedy in message


@pytest.mark.parametrize(
    "setting",
    list(REQUIRED_SETTINGS),
    ids=[s.name for s in REQUIRED_SETTINGS],
)
def test_each_required_key_empty_refuses_naming_setting_and_remedy(
    monkeypatch: pytest.MonkeyPatch,
    required_env: None,
    setting: RequiredSetting,
) -> None:
    monkeypatch.setenv(setting.name, "   ")

    message = _refusal_message()

    assert setting.name in message
    assert setting.remedy in message


@pytest.mark.parametrize(
    "invalid_admin",
    ["admin", "admin/", "/", "/admin", "/admin/", "Admin/", "ADMIN"],
    ids=[
        "admin",
        "admin-slash",
        "root",
        "slash-admin",
        "slash-admin-slash",
        "Admin-slash",
        "ADMIN",
    ],
)
def test_django_admin_url_invalid_values_refuse(
    monkeypatch: pytest.MonkeyPatch,
    required_env: None,
    invalid_admin: str,
) -> None:
    monkeypatch.setenv("DJANGO_ADMIN_URL", invalid_admin)

    message = _refusal_message()

    assert "DJANGO_ADMIN_URL" in message
    assert "invalid" in message
    admin = next(s for s in REQUIRED_SETTINGS if s.name == "DJANGO_ADMIN_URL")
    assert admin.remedy in message


def test_happy_path_accepts_valid_required_env(required_env: None) -> None:
    refuse_required_settings()
    run_stage_one(ModuleType("config.settings.production"))


def test_stage_one_skips_when_locality_is_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(RUNTIME_ENV_VAR, LOCAL)
    for name in (
        "DJANGO_SECRET_KEY",
        "DJANGO_ADMIN_URL",
        "MCP_HOST_SIDECAR_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)

    refuse_required_settings()
    run_stage_one(ModuleType("config.settings.production"))


def test_required_settings_registry_covers_production_keys() -> None:
    names = {s.name for s in REQUIRED_SETTINGS}
    assert names >= {
        "DJANGO_SECRET_KEY",
        "DJANGO_ADMIN_URL",
        "MCP_HOST_SIDECAR_BASE_URL",
        "COMPONENT_OIDC_ISSUER",
        "COMPONENT_OIDC_JWKS_URL",
        "COMPONENT_OIDC_AUDIENCE",
    }


def test_production_leaf_source_wires_stage_one() -> None:
    """Regression: production.py must call both CAP-3 stage-1 entry points."""
    source = Path(__file__).resolve().parents[1].joinpath(
        "config/settings/production.py",
    ).read_text(encoding="utf-8")
    assert "refuse_required_settings()" in source
    assert "run_stage_one(" in source
