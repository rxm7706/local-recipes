"""Steward 20.1: Wagtail Lane 1 publishes from PostgreSQL without a deploy."""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.test import Client
from django.test import RequestFactory
from django.urls import reverse
from wagtail.coreutils import get_supported_content_language_variant
from wagtail.models import Collection
from wagtail.models import Locale
from wagtail.models import Page
from wagtail.models import Site

from platformapp.front_door.lane1_seed import LANE1_SLUG
from platformapp.front_door.lane1_seed import seed_lane1_homepage
from platformapp.front_door.middleware import WagtailAdminGroupRequiredMiddleware
from platformapp.front_door.middleware import is_cms_login_path
from platformapp.front_door.middleware import must_refuse_admin
from platformapp.front_door.models import HomePage
from platformapp.users.provisioning import provision_designated_groups
from platformapp.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

PUBLISHED_BODY = "lane-1-body-from-orm-not-pages-home-html"


def _oidc_login_path() -> str:
    return reverse(
        "openid_connect_login",
        kwargs={"provider_id": settings.OIDC_PROVIDER_ID},
    )


def _publish_home(body: str) -> HomePage:
    root = Page.get_first_root_node()
    home = HomePage(title="Estate", slug="estate", body=body)
    root.add_child(instance=home)
    home.save_revision().publish()
    site = Site.objects.get(is_default_site=True)
    site.root_page = home
    site.save()
    return home


def test_seed_lane1_homepage_is_idempotent_and_serves_root(client: Client) -> None:
    first = seed_lane1_homepage()
    second = seed_lane1_homepage()
    assert first is not None
    assert second is not None
    assert first.pk == second.pk
    assert HomePage.objects.filter(slug=LANE1_SLUG).count() == 1
    site = Site.objects.get(is_default_site=True)
    assert site.root_page.specific.pk == first.pk
    response = client.get("/")
    assert response.status_code == HTTPStatus.OK
    assert "Lane 1" in response.content.decode()
    assert LANE1_SLUG in {page.slug for page in HomePage.objects.all()}


def test_seed_lane1_homepage_replaces_wagtail_default_page_at_the_slug() -> None:
    """wagtailcore's initial data seeds a plain Page at slug "home" under root.

    The seeder used to call add_child() straight over it and die on the duplicate
    slug from post_migrate -- i.e. during test-database creation, so every
    DB-marked test errored before running. It must move the placeholder aside,
    seed the HomePage at the slug, and drop the placeholder once no Site uses it.
    """
    root = Page.get_first_root_node()
    HomePage.objects.filter(slug=LANE1_SLUG).delete()
    Site.objects.all().delete()
    default_page = Page(title="Welcome to your new Wagtail site!", slug=LANE1_SLUG)
    root.add_child(instance=default_page)
    placeholder_pk = Page.objects.get(slug=LANE1_SLUG).pk

    home = seed_lane1_homepage()

    assert home is not None
    assert HomePage.objects.filter(slug=LANE1_SLUG, live=True).count() == 1
    assert Page.objects.filter(slug=LANE1_SLUG).count() == 1
    assert not Page.objects.filter(pk=placeholder_pk).exists()
    assert Site.objects.get(is_default_site=True).root_page_id == home.pk


def test_seed_lane1_homepage_restores_wagtail_baseline_rows() -> None:
    """A flushed database (transactional-test teardown) loses wagtailcore's initial
    data; post_migrate re-fires the seeder, which must put back the content-variant
    Locale and the root Collection or every later page/image save fails."""
    # Empty every wagtailcore baseline table the way a flush does (pages first:
    # Page.locale is PROTECT).
    Site.objects.all().delete()
    Page.objects.all().delete()
    Collection.objects.all().delete()
    Locale.objects.all().delete()

    home = seed_lane1_homepage()

    assert home is not None
    assert HomePage.objects.filter(slug=LANE1_SLUG, live=True).count() == 1
    assert Site.objects.get(is_default_site=True).root_page_id == home.pk
    assert Collection.get_first_root_node() is not None
    expected = get_supported_content_language_variant(settings.LANGUAGE_CODE)
    assert Locale.objects.filter(language_code=expected).exists()


def test_publish_homepage_body_comes_from_orm(client: Client) -> None:
    _publish_home(PUBLISHED_BODY)

    response = client.get("/")

    assert response.status_code == HTTPStatus.OK
    assert PUBLISHED_BODY in response.content.decode()
    stored = HomePage.objects.get(slug="estate")
    assert stored.body == PUBLISHED_BODY
    home_template = Path(settings.APPS_DIR) / "templates" / "pages" / "home.html"
    assert PUBLISHED_BODY not in home_template.read_text(encoding="utf-8")
    about = client.get("/about/")
    assert about.status_code == HTTPStatus.OK


def test_two_clients_see_identical_html_and_body_is_not_on_disk(client: Client) -> None:
    _publish_home(PUBLISHED_BODY)
    cache.clear()

    first = client.get("/")
    replica = Client()
    cache.clear()
    second = replica.get("/")

    assert first.content == second.content
    assert PUBLISHED_BODY in first.content.decode()
    media_root = Path(settings.MEDIA_ROOT)
    leaked: list[Path] = []
    if media_root.exists():
        leaked = [
            path
            for path in media_root.rglob("*")
            if path.is_file()
            and PUBLISHED_BODY in path.read_text(encoding="utf-8", errors="ignore")
        ]
    assert leaked == []


def test_anonymous_cms_redirects_to_oidc_login(client: Client) -> None:
    response = client.get("/cms/", follow=False)

    assert response.status_code == HTTPStatus.FOUND
    login_path = _oidc_login_path()
    assert login_path in response.url
    assert "next=" in response.url
    assert "/cms/" in response.url
    assert "password" not in response.url.lower()


def test_cms_without_wagtail_group_is_explicit_403(client: Client) -> None:
    user = UserFactory()
    client.force_login(user)

    response = client.get("/cms/")

    assert response.status_code == HTTPStatus.FORBIDDEN
    body = response.content.decode()
    assert settings.WAGTAIL_ADMIN_IDP_GROUP in body
    assert "Wagtail-admin IdP group" in body

    pages = client.get("/cms/pages/")
    assert pages.status_code == HTTPStatus.FORBIDDEN
    assert settings.WAGTAIL_ADMIN_IDP_GROUP in pages.content.decode()

    superuser = UserFactory(username="su-no-group", is_superuser=True, is_staff=True)
    client.force_login(superuser)
    refused = client.get("/cms/")
    assert refused.status_code == HTTPStatus.FORBIDDEN


def test_editor_with_wagtail_group_reaches_cms_admin(client: Client) -> None:
    provision_designated_groups()
    user = UserFactory()
    user.groups.add(Group.objects.get(name=settings.WAGTAIL_ADMIN_IDP_GROUP))
    client.force_login(user)

    response = client.get("/cms/")

    assert response.status_code == HTTPStatus.OK


def test_password_and_email_management_are_off(client: Client) -> None:
    assert settings.WAGTAILUSERS_PASSWORD_ENABLED is False
    assert settings.WAGTAIL_EMAIL_MANAGEMENT_ENABLED is False
    assert settings.WAGTAIL_PASSWORD_MANAGEMENT_ENABLED is False
    response = client.get(reverse("wagtailadmin_password_reset"))
    assert response.status_code == HTTPStatus.NOT_FOUND
    login_page = client.get(reverse("wagtailadmin_login"), follow=False)
    assert login_page.status_code == HTTPStatus.FOUND
    login_path = reverse(
        "openid_connect_login",
        kwargs={"provider_id": settings.OIDC_PROVIDER_ID},
    )
    assert login_path in login_page.url
    assert b"password" not in login_page.content.lower()


def test_wagtailadmin_login_url_is_oidc() -> None:
    assert settings.WAGTAILADMIN_LOGIN_URL == settings.LOGIN_URL
    login_path = _oidc_login_path()
    assert str(settings.WAGTAILADMIN_LOGIN_URL) == login_path


def test_must_refuse_admin_covers_path_and_auth_branches() -> None:
    factory = RequestFactory()
    user = UserFactory()
    provision_designated_groups()
    editor = UserFactory(username="editor-cms")
    editor.groups.add(Group.objects.get(name=settings.WAGTAIL_ADMIN_IDP_GROUP))

    request_root = factory.get("/")
    request_root.user = user
    assert must_refuse_admin(request_root) is False

    request_cms = factory.get("/cms/")
    request_cms.user = AnonymousUser()
    assert must_refuse_admin(request_cms) is False

    request_bare = factory.get("/cms")
    request_bare.user = user
    assert must_refuse_admin(request_bare) is True

    missing_user = factory.get("/cms/")
    assert must_refuse_admin(missing_user) is False

    allowed = factory.get("/cms/")
    allowed.user = editor
    assert must_refuse_admin(allowed) is False

    assert is_cms_login_path("/cms/login") is True
    assert is_cms_login_path("/cms/login/") is True
    assert is_cms_login_path("/cms/") is False

    authed_login = factory.get("/cms/login/")
    authed_login.user = editor
    response = WagtailAdminGroupRequiredMiddleware(lambda request: None)(authed_login)
    assert response.status_code == HTTPStatus.FOUND
    assert reverse("wagtailadmin_home") in response.url

    anonymous_login = factory.get("/cms/login/")
    login_mw = WagtailAdminGroupRequiredMiddleware(lambda request: None)
    redirected = login_mw(anonymous_login)
    assert redirected.status_code == HTTPStatus.FOUND
    assert "next=" in redirected.url


def test_chrome_signup_link_and_flash_messages(client: Client, settings) -> None:
    settings.ACCOUNT_ALLOW_REGISTRATION = True
    about = client.get("/about/")
    assert b"sign-up-link" in about.content

    user = UserFactory()
    client.force_login(user)
    response = client.post("/users/~update/", {"name": "Shown"}, follow=True)
    assert response.status_code == HTTPStatus.OK
    assert b"alert" in response.content
