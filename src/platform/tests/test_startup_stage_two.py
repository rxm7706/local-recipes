"""CAP-3 / steward 16.2: stage-2 owner wiring and deployed post-setup checks."""

from __future__ import annotations

import inspect

import pytest
from django.apps import apps
from django.core.exceptions import ImproperlyConfigured

from config.locality import LOCAL
from config.locality import RUNTIME_ENV_VAR
from config.startup import run_stage_two
from config.startup import stage_two
from config.startup.stage_two import STAGE_TWO_OWNER_APP_LABEL
from config.startup.stage_two import stage_two_has_run
from platformapp.users.apps import UsersConfig


def test_stage_two_owner_app_is_users() -> None:
    assert STAGE_TWO_OWNER_APP_LABEL == "users"
    assert apps.get_app_config(STAGE_TWO_OWNER_APP_LABEL).name == "platformapp.users"


def test_users_config_ready_calls_run_stage_two() -> None:
    source = inspect.getsource(UsersConfig.ready)
    assert "run_stage_two" in source


def test_users_config_ready_sets_stage_two_sentinel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Runtime wiring: ready() must enter stage 2 (not only mention it in source)."""
    monkeypatch.setenv(RUNTIME_ENV_VAR, LOCAL)
    monkeypatch.setattr(stage_two, "_STAGE_TWO_RAN", {"entered": False})

    apps.get_app_config(STAGE_TWO_OWNER_APP_LABEL).ready()

    assert stage_two_has_run() is True


def test_stage_two_sentinel_is_set_even_when_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(RUNTIME_ENV_VAR, LOCAL)
    monkeypatch.setattr(stage_two, "_STAGE_TWO_RAN", {"entered": False})

    assert stage_two_has_run() is False
    run_stage_two()
    assert stage_two_has_run() is True


def test_stage_two_skips_refusals_when_local(
    monkeypatch: pytest.MonkeyPatch,
    settings,
) -> None:
    monkeypatch.setenv(RUNTIME_ENV_VAR, LOCAL)
    settings.DEBUG = True
    settings.SETTINGS_MODULE = "config.settings.local"

    run_stage_two()


def test_stage_two_refuses_debug_true_when_deployed(
    monkeypatch: pytest.MonkeyPatch,
    settings,
) -> None:
    monkeypatch.delenv(RUNTIME_ENV_VAR, raising=False)
    settings.DEBUG = True
    settings.SETTINGS_MODULE = "config.settings.production"

    with pytest.raises(ImproperlyConfigured) as refused:
        run_stage_two()

    message = str(refused.value)
    assert "DEBUG" in message
    assert "DJANGO_DEBUG" in message


def test_stage_two_refuses_local_settings_module_when_deployed(
    monkeypatch: pytest.MonkeyPatch,
    settings,
) -> None:
    monkeypatch.delenv(RUNTIME_ENV_VAR, raising=False)
    settings.DEBUG = False
    settings.SETTINGS_MODULE = "config.settings.local"

    with pytest.raises(ImproperlyConfigured) as refused:
        run_stage_two()

    message = str(refused.value)
    assert "config.settings.local" in message
    assert "config.settings.production" in message
    assert f"{RUNTIME_ENV_VAR}={LOCAL}" in message


def test_stage_two_accepts_production_like_namespace_when_deployed(
    monkeypatch: pytest.MonkeyPatch,
    settings,
) -> None:
    monkeypatch.delenv(RUNTIME_ENV_VAR, raising=False)
    settings.DEBUG = False
    settings.SETTINGS_MODULE = "config.settings.production"

    run_stage_two()
