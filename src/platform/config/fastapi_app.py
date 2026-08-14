"""FastAPI sub-app mounted at ``/api/`` by :mod:`config.asgi`.

Story 10.1 scope: only the seam itself, exposing a bare ``GET /api/health``
probe. :mod:`config.asgi` routes every ``/api/*`` path here; Epic 11 attaches
the real Langflow (``/api/v1/``) and DB-GPT (``/api/dbgpt/``) mounts under
this same namespace (spec-python-agent-platform CAP-2/CAP-3) -- this module
intentionally builds neither. Langflow's non-``/api/`` route (``/langflow/``)
falls outside this seam's namespace and will need its own dispatch rule in
:mod:`config.asgi` when Epic 11 adds it -- not assumed here.
"""

from fastapi import FastAPI

fastapi_application = FastAPI(title="Python Agent Platform API")


@fastapi_application.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
