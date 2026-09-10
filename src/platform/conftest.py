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

    import django_atlas_portal.mcp_asgi as atlas_mcp  # noqa: PLC0415
    import django_doctor_portal.mcp_asgi as doctor_mcp  # noqa: PLC0415
    import django_herald_portal.mcp_asgi as herald_mcp  # noqa: PLC0415
    import django_marshal_portal.mcp_asgi as marshal_mcp  # noqa: PLC0415
    import django_mason_portal.mcp_asgi as mason_mcp  # noqa: PLC0415
    import django_scribe_portal.mcp_asgi as scribe_mcp  # noqa: PLC0415
    import django_steward_portal.mcp_asgi as steward_mcp  # noqa: PLC0415
    import django_warden_fabric.mcp_asgi as warden_mcp  # noqa: PLC0415
    from django_pyforge import supervisor  # noqa: PLC0415

    atlas_mcp._APP = None  # noqa: SLF001
    warden_mcp._SERVER = None  # noqa: SLF001
    _cache_mods = (
        doctor_mcp,
        herald_mcp,
        marshal_mcp,
        mason_mcp,
        scribe_mcp,
        steward_mcp,
    )
    for mod in _cache_mods:
        mod._CACHE.clear()  # noqa: SLF001
    supervisor._runners.clear()  # noqa: SLF001
