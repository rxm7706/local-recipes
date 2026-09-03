"""Platform-root pytest hooks.

CAP-3 / steward 16.2: unit and CI tests are a local runtime. setdefault so a
developer shell that already exported COMPONENT_RUNTIME=local is untouched, and
so deployed-only startup refusals do not fire under ``--ds=config.settings.test``.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("COMPONENT_RUNTIME", "local")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")


@pytest.fixture(autouse=True)
def _isolate_caches():
    """Start every test with an empty cache.

    The test settings use LocMemCache, which lives for the whole pytest
    process — unlike the database, nothing rolls it back between tests. Story
    42.2 put per-subject rate-limit buckets in that cache, so without this a
    subject's spend would accumulate across every test that used it and the
    suite's outcome would depend on collection order. Clearing is the fix that
    keeps the real limiter in the path rather than stubbing it out.
    """
    from django.core.cache import caches  # noqa: PLC0415

    for alias in caches:
        caches[alias].clear()
