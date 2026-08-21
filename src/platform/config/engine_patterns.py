"""AD-17 -- the per-engine integration-pattern registry (spec-python-agent-
platform, Story 11.2).

AD-14 established two named integration patterns for the agentic engines
this platform hosts (`docs/dreams/db-gpt-django-plugin.md`):

- Pattern A -- in-process ASGI mount + schema isolation (Langflow, Story
  11.1: `langflow_integration/asgi.py`, mounted by `config/asgi.py`).
- Pattern B -- the engine's own sidecar container, reached over Celery/REST
  (DB-GPT, Story 10.5's `dbgpt` compose service + Story 11.2's
  `dbgpt_integration/tasks.py`), never an ASGI mount.

AD-17 generalizes the CHOICE between them into this one registry, consulted
by both `config/asgi.py` (to decide whether to build an ASGI sub-app) and
`dbgpt_integration/tasks.py` (to resolve a Pattern-B engine's sidecar URL).
Switching an engine's pattern is meant to be a config change here, never a
code fork: the same dispatcher/routing code paths serve both patterns,
branching only on this registry.

First triggered by DB-GPT's own Pattern-B deviation (dated in
`docs/dreams/db-gpt-django-plugin.md`'s 2026-08-21 AD-14 entry) after the
`dbgpt-app` / `langflow-base` `fastapi` pin conflict -- see that entry for
the full citation, not re-derived here.
"""

from __future__ import annotations

import environ

env = environ.Env()

# "A" = in-process ASGI mount. "B" = sidecar container, Celery/REST dispatch.
ENGINE_PATTERNS: dict[str, str] = {
    "langflow": "A",
    "dbgpt": "B",
}

# Pattern-B engines only: how to reach their sidecar. `dbgpt`'s default
# matches Story 10.5's own compose service name/port (`dbgpt:5670`) --
# reachable by service name from any other container on the same compose
# network (`platform`/Celery workers included). A non-compose local run
# (e.g. `dbgpt start webserver` invoked directly, as this story's own
# verification did) reaches it at `localhost` instead -- both cases are
# env-overridable, matching every other `env()`-sourced value in this
# platform (`config/settings/base.py`'s own convention).
SIDECAR_BASE_URLS: dict[str, str] = {
    "dbgpt": env("DBGPT_SIDECAR_BASE_URL", default="http://dbgpt:5670"),
}


def get_sidecar_base_url(engine: str) -> str:
    """Resolve a Pattern-B engine's sidecar base URL from the registry.

    Raises `ValueError` for a Pattern-A (or unknown) engine -- there is no
    sidecar to reach for those; the caller should be building an ASGI mount
    instead (or, for an unknown engine, has a bug).
    """
    pattern = ENGINE_PATTERNS.get(engine)
    if pattern != "B":
        msg = f"{engine!r} is not a Pattern-B (sidecar) engine (pattern={pattern!r})"
        raise ValueError(msg)
    return SIDECAR_BASE_URLS[engine]
