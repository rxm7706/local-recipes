"""Minimal Django settings for cross-package contract tests (Story 43.2)."""

from __future__ import annotations

import sys
from pathlib import Path

import django
from django.conf import settings

_REPO_ROOT = Path(__file__).resolve().parents[5]
for rel in (
    "src/shared/packages/pyforge-core/src",
    "src/shared/packages/django-pyforge/src",
):
    path = str(_REPO_ROOT / rel)
    if path not in sys.path:
        sys.path.insert(0, path)


def pytest_configure() -> None:
    if settings.configured:
        return
    from django_pyforge.assertion.golden import GOLDEN_PRIVATE_PEM, GOLDEN_PUBLIC_PEM

    settings.configure(
        SECRET_KEY="testing-kit-contract-test",
        USE_TZ=True,
        INSTALLED_APPS=[],
        PYFORGE_ASSERTION_PRIVATE_KEY=GOLDEN_PRIVATE_PEM,
        PYFORGE_ASSERTION_PUBLIC_KEY=GOLDEN_PUBLIC_PEM,
    )
    django.setup()
