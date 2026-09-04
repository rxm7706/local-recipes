"""Idempotent Lane 1 HomePage + default Wagtail Site (CAP-2)."""

from __future__ import annotations

import os

from django.conf import settings
from django.db.utils import ProgrammingError
from wagtail.coreutils import get_supported_content_language_variant
from wagtail.models import Collection
from wagtail.models import Locale
from wagtail.models import Page
from wagtail.models import Site

from platformapp.front_door.models import HomePage

LANE1_SLUG = "home"
LANE1_TITLE = "PyForge"
LANE1_BODY = "<p>PyForge Lane 1 — published from PostgreSQL.</p>"


def _hostname_port() -> tuple[str, int]:
    raw_port = os.environ.get("WAGTAIL_PORT", "80")
    try:
        port = int(raw_port)
    except ValueError:
        port = 80
    return os.environ.get("WAGTAIL_HOSTNAME", "localhost"), port


def _move_aside_default_page(root: Page) -> Page | None:
    """Rename wagtailcore's seeded plain Page at the Lane 1 slug, if present.

    ``0002_initial_data`` puts "Welcome to your new Wagtail site!" at slug
    ``home`` under root. Liquibase-applied schemas never carry it, but every
    Django-migrated database does -- the test database above all -- and
    ``add_child()`` refuses the duplicate slug, so ``post_migrate`` died and took
    every DB-marked test with it. The page is dropped again by
    ``_drop_default_page`` once nothing points at it.
    """
    placeholder = root.get_children().filter(slug=LANE1_SLUG).first()
    if placeholder is not None:
        placeholder.slug = f"{LANE1_SLUG}-wagtail-default"
        placeholder.save()
    return placeholder


def _drop_default_page(placeholder: Page | None) -> None:
    if placeholder is None:
        return
    if Site.objects.filter(root_page=placeholder).exists():
        return
    placeholder.delete()


def seed_lane1_homepage(**_kwargs: object) -> HomePage | None:
    """Create root + published HomePage + default Site when they are missing.

    Swallow ``ProgrammingError`` so ``migrate --fake`` can still emit
    ``post_migrate`` before Liquibase :16/:19 exist (same as detector seed).
    """
    try:
        # The Locale must be the one Wagtail resolves for new pages (the content
        # variant of LANGUAGE_CODE, "en" for "en-us"), or add_root() below dies with
        # Locale.DoesNotExist on every flushed database -- a transactional test's
        # teardown re-fires post_migrate into an empty wagtailcore_locale table.
        language = get_supported_content_language_variant(
            getattr(settings, "LANGUAGE_CODE", "en") or "en",
        )
        Locale.objects.get_or_create(language_code=language)
        # Same baseline as the Locale: the image/document root Collection is
        # wagtailcore initial data too, so a Liquibase-applied schema or a flushed
        # test database has none and every Image.save() dies on it.
        if Collection.get_first_root_node() is None:
            Collection.add_root(name="Root")
        root = Page.get_first_root_node()
        if root is None:
            root = Page.add_root(title="Root", slug="root")
        home = HomePage.objects.filter(slug=LANE1_SLUG).first()
        placeholder: Page | None = None
        if home is None:
            placeholder = _move_aside_default_page(root)
            home = HomePage(title=LANE1_TITLE, slug=LANE1_SLUG, body=LANE1_BODY)
            root.add_child(instance=home)
            home.save_revision().publish()
        elif not home.live:
            home.save_revision().publish()
        site = Site.objects.filter(is_default_site=True).first()
        hostname, port = _hostname_port()
        if site is None:
            Site.objects.create(
                hostname=hostname,
                port=port,
                site_name=getattr(settings, "WAGTAIL_SITE_NAME", LANE1_TITLE),
                root_page=home,
                is_default_site=True,
            )
        else:
            current = site.root_page.specific
            if not (isinstance(current, HomePage) and current.live):
                site.root_page = home
                if not site.site_name:
                    site.site_name = getattr(settings, "WAGTAIL_SITE_NAME", LANE1_TITLE)
                site.save()
        _drop_default_page(placeholder)
    except ProgrammingError:
        return None
    return home
