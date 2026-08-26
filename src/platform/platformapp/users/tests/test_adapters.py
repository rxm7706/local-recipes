"""Account adapter coverage (steward 16.4 floor on platformapp/**)."""

from __future__ import annotations

from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.models import SocialLogin
from django.core.checks import run_checks
from django.test import RequestFactory
from django.test import override_settings

from platformapp.users.adapters import AccountAdapter
from platformapp.users.adapters import SocialAccountAdapter
from platformapp.users.models import User


def test_oidc_only_allauth_settings_do_not_raise_w001() -> None:
    assert not any(message.id == "account.W001" for message in run_checks())


def test_account_adapter_honours_registration_flag() -> None:
    request = RequestFactory().get("/")
    with override_settings(ACCOUNT_ALLOW_REGISTRATION=False):
        assert AccountAdapter().is_open_for_signup(request) is False
    with override_settings(ACCOUNT_ALLOW_REGISTRATION=True):
        assert AccountAdapter().is_open_for_signup(request) is True


def test_social_adapter_honours_registration_flag() -> None:
    request = RequestFactory().get("/")
    with override_settings(ACCOUNT_ALLOW_REGISTRATION=False):
        assert SocialAccountAdapter().is_open_for_signup(
            request,
            sociallogin=None,
        ) is False


def test_social_adapter_populate_user_name_from_full_and_parts() -> None:
    adapter = SocialAccountAdapter()
    request = RequestFactory().get("/")
    account = SocialAccount(provider="openid_connect", uid="n")
    sociallogin = SocialLogin(account=account, user=User())

    named = adapter.populate_user(request, sociallogin, {"name": "Full Name"})
    assert named.name == "Full Name"

    sociallogin.user = User()
    first_only = adapter.populate_user(request, sociallogin, {"first_name": "Ada"})
    assert first_only.name == "Ada"

    sociallogin.user = User()
    both = adapter.populate_user(
        request,
        sociallogin,
        {"first_name": "Ada", "last_name": "Lovelace"},
    )
    assert both.name == "Ada Lovelace"

    sociallogin.user = User(name="Kept")
    kept = adapter.populate_user(request, sociallogin, {"name": "Ignored"})
    assert kept.name == "Kept"
