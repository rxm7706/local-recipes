"""Story 9.1 — AD-13's reusable-Django-app scaffold.

This story ships no model, but the `AppConfig` follows AD-13 now so Story
9.3's audit model inherits a compliant scaffold instead of retrofitting one:
an explicit label, unique in `INSTALLED_APPS` and never colliding with a
contrib label (`auth`, `admin`, `messages`), and `default_auto_field` set —
load-bearing once a model with migrations exists, since without it those
migrations would shift under the adopter's own `DEFAULT_AUTO_FIELD` setting.

Requires `django`, so this module (unlike `declarations.py`) only imports
cleanly with the `pyforge-steward[dashboard]` extra installed.
"""

from __future__ import annotations

from django.apps import AppConfig


class DashboardConfig(AppConfig):
    """AD-13 scaffold for `pyforge.steward.dashboard`."""

    name = "pyforge.steward.dashboard"
    label = "pyforge_steward_dashboard"
    default_auto_field = "django.db.models.BigAutoField"
