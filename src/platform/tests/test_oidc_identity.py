"""OIDC identity and login tests (CAP-1 / steward 16.5)."""

from __future__ import annotations

import pytest
import structlog
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.models import SocialLogin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpRequest

from config.authorization.adapters import OIDCSocialAccountAdapter
from config.authorization.adapters import claims_from
from config.authorization.claims import read_group_claim
from config.authorization.exceptions import ClaimsRejected
from config.authorization.mapper import resolve_user
from config.authorization.mapper import sync_for_interactive
from config.local_dev.personas import build_claims
from config.local_dev.personas import get_persona
from config.local_dev.tokens import mint_token
from config.locality import RUNTIME_ENV_VAR
from django_pyforge.roles import IDP_TOKEN_ROLES_SESSION_KEY
from platformapp.users.provisioning import provision_designated_groups

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(RUNTIME_ENV_VAR, "local")


@pytest.fixture(autouse=True)
def _provision_groups() -> None:
    provision_designated_groups()


def test_idp_subject_is_unique_nullable() -> None:
    user_model = get_user_model()
    field = user_model._meta.get_field("idp_subject")  # noqa: SLF001
    assert field.unique is True
    assert field.null is True


def test_resolve_user_creates_user_with_unusable_password() -> None:
    claims = build_claims(get_persona("reader"))
    user = resolve_user(claims)
    assert user.idp_subject == "local-dev:persona:reader"
    assert not user.has_usable_password()


def test_resolve_user_is_idempotent() -> None:
    claims = build_claims(get_persona("staff"))
    first = resolve_user(claims)
    second = resolve_user(claims)
    assert first.pk == second.pk


def test_sync_sets_staff_from_group_claim() -> None:
    claims = build_claims(get_persona("staff"))
    user = resolve_user(claims)
    outcome = sync_for_interactive(user, claims)
    user.refresh_from_db()
    assert user.is_staff is True
    assert user.is_superuser is False
    assert outcome.ignored == ()


def test_sync_ignores_unmatched_groups_and_logs(caplog: pytest.LogCaptureFixture) -> None:
    structlog.configure(
        processors=[structlog.processors.KeyValueRenderer()],
        wrapper_class=structlog.make_filtering_bound_logger(0),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )
    claims = build_claims(get_persona("reader"))
    claims["groups"] = ["platform-staff", "unknown-group"]
    user = resolve_user(claims)
    outcome = sync_for_interactive(user, claims)
    assert "unknown-group" in outcome.ignored
    user.refresh_from_db()
    assert user.is_staff is True


def test_adapter_pre_social_login_establishes_session() -> None:
    persona = get_persona("staff")
    claims = build_claims(persona)
    account = SocialAccount(provider="openid_connect", uid=persona.subject, extra_data={"userinfo": claims})
    sociallogin = SocialLogin(account=account)
    request = HttpRequest()
    request.session = {}

    OIDCSocialAccountAdapter().pre_social_login(request, sociallogin)

    assert sociallogin.user.idp_subject == persona.subject
    assert sociallogin.user.is_staff is True
    assert request.session[IDP_TOKEN_ROLES_SESSION_KEY] == read_group_claim(
        claims,
        "groups",
    )


def test_adapter_refuses_missing_identity_claim() -> None:
    account = SocialAccount(provider="openid_connect", uid="missing", extra_data={"userinfo": {}})
    sociallogin = SocialLogin(account=account)
    request = HttpRequest()

    with pytest.raises(ImmediateHttpResponse):
        OIDCSocialAccountAdapter().pre_social_login(request, sociallogin)


def test_claims_from_flattens_oidc_envelopes() -> None:
    account = SocialAccount(
        provider="openid_connect",
        uid="x",
        extra_data={"id_token": {"sub": "a"}, "userinfo": {"groups": ["g"]}},
    )
    sociallogin = SocialLogin(account=account)
    assert claims_from(sociallogin)["sub"] == "a"
    assert claims_from(sociallogin)["groups"] == ["g"]


def test_mint_token_produces_jwt_for_persona() -> None:
    token = mint_token("staff")
    assert isinstance(token, str)
    assert len(token.split(".")) == 3


def test_sync_refuses_absent_group_claim() -> None:
    claims = build_claims(get_persona("reader"))
    del claims["groups"]
    user = resolve_user(claims)
    with pytest.raises(ClaimsRejected, match="group claim absent"):
        sync_for_interactive(user, claims)


def test_provision_designated_groups_creates_rows() -> None:
    assert Group.objects.filter(name="platform-staff").exists()
    assert Group.objects.filter(name="platform-superuser").exists()
