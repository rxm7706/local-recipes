"""One-generator dossier path — stdlib-only for the ``site`` build (Story 43.1, CAP-61)."""

from __future__ import annotations

import os

ENV_PAGES_ONE_GENERATOR = "PYFORGE_PAGES_ONE_GENERATOR"
DOSSIER_ARTIFACT_REL = "herald/dossier/index.html"


def enabled_from_env() -> bool:
    return os.environ.get(ENV_PAGES_ONE_GENERATOR, "").strip().lower() in ("1", "true", "yes")


def export_env_for_ci() -> dict[str, str]:
    from pyforge.herald.pages_one_generator import pages_one_generator_enabled

    enabled = pages_one_generator_enabled()
    return {ENV_PAGES_ONE_GENERATOR: "1" if enabled else "0"}


def select_dossier_generator(*, flag_enabled: bool | None = None) -> str:
    """Return ``astro`` or ``jinja`` for ``/herald/dossier/``."""
    if flag_enabled is None:
        flag_enabled = enabled_from_env()
    return "astro" if flag_enabled else "jinja"
