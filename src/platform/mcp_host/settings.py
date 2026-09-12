"""Minimal Django settings for the mcp-host sidecar (spec-mcp-host-real-station-tools).

Just enough for a station's real in-process MCP app (e.g.
``django_marshal_portal.mcp_asgi``) to reach ``django_pyforge``'s ORM models
(``RunState``/``McpHandle``) against the SAME shared Postgres the web pod
uses. No Langflow, no Redis client: the functions this sidecar calls
(``publish_held_loop_bounded``/``heartbeat_held_run``/``complete_held_run``/
``list_published_story_tasks``) never touch ``django.core.cache`` or the
event broker -- both degrade to a silent no-op when
``REDIS_BROKER_URL``/``REDIS_CACHE_URL`` are absent, by design (see
``django_pyforge.supervisor._publish_run_started_event``).

``INSTALLED_APPS`` lists only ``django_pyforge`` (the ORM models) plus
whichever station portal packages this image's Containerfile actually
copies in -- add a station here only alongside its portal COPY line.
"""

from __future__ import annotations

import environ

env = environ.Env()

SECRET_KEY = env.str("DJANGO_SECRET_KEY")

DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres:///platform"),
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True

INSTALLED_APPS = [
    "django_pyforge",
    "django_marshal_portal",
]

# CAP-18 host assertion verify (django_pyforge.assertion.crypto.verify_assertion,
# reached via supervisor.publish_held_run). Optional like the web image's own
# wiring -- absent means every publish call raises AssertionRefusedError.
PYFORGE_ASSERTION_PUBLIC_KEY = env.str("PYFORGE_ASSERTION_PUBLIC_KEY", default="")
