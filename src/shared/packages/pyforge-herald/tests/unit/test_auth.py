"""``auth.py``'s role resolution + write-gate (Story 6.3, AD-16).

Every test passes an explicit ``config_path`` under ``tmp_path`` -- never
the real ``~/.herald/config`` -- mirroring the package's existing
``credentials_file`` fixture convention (``tests/conftest.py``); the
``deny_network`` autouse fixture is not the mechanism here (this module
reaches no network at all), but the "never touch the developer's real
files" discipline is the same one.
"""

from __future__ import annotations

import json

import pytest

from pyforge.herald import auth
from pyforge.herald.errors import OperatorAuthorizationError


def test_no_env_var_and_no_config_file_resolves_to_no_auth_context(
    tmp_path, monkeypatch
):
    monkeypatch.delenv(auth.TOKEN_ENV_VAR, raising=False)
    assert auth.resolve_auth_context(config_path=tmp_path / "config") is None


def test_env_var_with_operator_role_resolves(monkeypatch, tmp_path):
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "operator:tok-123")
    context = auth.resolve_auth_context(config_path=tmp_path / "config")
    assert context is not None
    assert context.role == "operator"
    assert context.source == f"env:{auth.TOKEN_ENV_VAR}"


def test_env_var_with_a_different_role_resolves_to_that_role_not_operator(
    monkeypatch, tmp_path
):
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "viewer:tok-123")
    context = auth.resolve_auth_context(config_path=tmp_path / "config")
    assert context is not None
    assert context.role == "viewer"


def test_env_var_present_but_not_colon_delimited_is_ignored_not_treated_as_operator(
    monkeypatch, tmp_path
):
    """A trivial bypass this module's own docstring calls out: merely
    setting ``HERALD_TOKEN`` to any non-empty string must not grant the
    operator role -- the role has to be explicitly encoded."""
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "just-a-bare-token-no-role")
    assert auth.resolve_auth_context(config_path=tmp_path / "config") is None


def test_config_file_with_operator_role_resolves(monkeypatch, tmp_path):
    monkeypatch.delenv(auth.TOKEN_ENV_VAR, raising=False)
    config_path = tmp_path / "config"
    config_path.write_text(json.dumps({"role": "operator", "token": "x"}))
    context = auth.resolve_auth_context(config_path=config_path)
    assert context is not None
    assert context.role == "operator"
    assert context.source == f"file:{config_path}"


def test_config_file_with_a_non_operator_role_resolves_to_that_role(
    monkeypatch, tmp_path
):
    monkeypatch.delenv(auth.TOKEN_ENV_VAR, raising=False)
    config_path = tmp_path / "config"
    config_path.write_text(json.dumps({"role": "viewer"}))
    context = auth.resolve_auth_context(config_path=config_path)
    assert context is not None
    assert context.role == "viewer"


def test_missing_config_file_resolves_to_no_auth_context(monkeypatch, tmp_path):
    monkeypatch.delenv(auth.TOKEN_ENV_VAR, raising=False)
    assert auth.resolve_auth_context(config_path=tmp_path / "does-not-exist") is None


def test_malformed_json_config_file_resolves_to_no_auth_context_not_a_crash(
    monkeypatch, tmp_path
):
    monkeypatch.delenv(auth.TOKEN_ENV_VAR, raising=False)
    config_path = tmp_path / "config"
    config_path.write_text("{not json")
    assert auth.resolve_auth_context(config_path=config_path) is None


def test_config_file_with_no_role_field_resolves_to_no_auth_context(
    monkeypatch, tmp_path
):
    monkeypatch.delenv(auth.TOKEN_ENV_VAR, raising=False)
    config_path = tmp_path / "config"
    config_path.write_text(json.dumps({"token": "x"}))
    assert auth.resolve_auth_context(config_path=config_path) is None


def test_env_var_takes_precedence_over_config_file(monkeypatch, tmp_path):
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "operator:tok-123")
    config_path = tmp_path / "config"
    config_path.write_text(json.dumps({"role": "viewer"}))
    context = auth.resolve_auth_context(config_path=config_path)
    assert context is not None
    assert context.source == f"env:{auth.TOKEN_ENV_VAR}"


def test_require_operator_role_passes_through_an_operator_context():
    context = auth.AuthContext(role="operator", source="env:HERALD_TOKEN")
    assert (
        auth.require_operator_role(context, action="herald success publish") is context
    )


def test_require_operator_role_raises_for_a_non_operator_role():
    context = auth.AuthContext(role="viewer", source="env:HERALD_TOKEN")
    with pytest.raises(OperatorAuthorizationError, match="unauthorized"):
        auth.require_operator_role(context, action="herald success publish")


def test_require_operator_role_raises_for_no_auth_context():
    with pytest.raises(OperatorAuthorizationError, match="auth context missing"):
        auth.require_operator_role(None, action="herald success publish")


def test_require_operator_role_error_names_herald_token_and_auth_login():
    """The AC's own wording: 'Configure with herald auth login or set
    HERALD_TOKEN env var'."""
    with pytest.raises(OperatorAuthorizationError) as excinfo:
        auth.require_operator_role(None, action="herald notice author")
    assert "herald auth login" in str(excinfo.value)
    assert "HERALD_TOKEN" in str(excinfo.value)


def test_confirm_accepts_blank_y_and_yes_case_insensitive():
    for answer in ("", "y", "Y", "yes", "YES", "  yes  "):
        assert auth.confirm("Continue? [Y/n] ", reader=lambda _p, a=answer: a) is True


def test_confirm_declines_anything_else():
    for answer in ("n", "no", "nope", "x"):
        assert auth.confirm("Continue? [Y/n] ", reader=lambda _p, a=answer: a) is False


def test_confirm_declines_on_eof():
    def _raise_eof(_prompt: str) -> str:
        raise EOFError

    assert auth.confirm("Continue? [Y/n] ", reader=_raise_eof) is False
