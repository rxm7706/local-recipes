"""Idempotent Lane 1 HomePage + default Wagtail Site (CAP-2)."""

from __future__ import annotations

import os

from django.conf import settings
from django.db.utils import ProgrammingError
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


def seed_lane1_homepage(**_kwargs: object) -> HomePage | None:
    """Create root + published HomePage + default Site when they are missing.

    Swallow ``ProgrammingError`` so ``migrate --fake`` can still emit
    ``post_migrate`` before Liquibase :16/:19 exist (same as detector seed).
    """
    try:
        language = (getattr(settings, "LANGUAGE_CODE", "en") or "en")[:7]
        Locale.objects.get_or_create(language_code=language)
        root = Page.get_first_root_node()
        if root is None:
            root = Page.add_root(title="Root", slug="root")
        home = HomePage.objects.filter(slug=LANE1_SLUG).first()
        if home is None:
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
            return home
        current = site.root_page.specific
        if isinstance(current, HomePage) and current.live:
            return home
        site.root_page = home
        if not site.site_name:
            site.site_name = getattr(settings, "WAGTAIL_SITE_NAME", LANE1_TITLE)
        site.save()
    except ProgrammingError:
        return None
    return home
