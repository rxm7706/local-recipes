"""FastAPI sub-app mounted at ``/api/`` by :mod:`config.asgi`.

Story 10.1 scope: only the seam itself, exposing a bare ``GET /api/health``
probe. :mod:`config.asgi` routes every ``/api/*`` HTTP path here (websocket
connections are not path-routed at all yet -- every one reaches the stock
``websocket_application`` stub regardless of path, since nothing under this
seam handles websockets today); Epic 11 attaches the real Langflow
(``/api/v1/``) and DB-GPT (``/api/dbgpt/``) mounts under this same namespace
(spec-python-agent-platform CAP-2/CAP-3) -- this module intentionally builds
neither. Langflow's non-``/api/`` route (``/langflow/``) falls outside this
seam's namespace and will need its own dispatch rule in :mod:`config.asgi`
when Epic 11 adds it -- not assumed here.

Routes here declare their own full ``/api/...`` path (see ``/api/health``
below): the composed dispatcher forwards the whole, unmodified ASGI scope
rather than mounting via a path-stripping ``Mount``, so a future route added
here must include its own ``/api/...`` prefix or it 404s silently.

``/api/health`` is an unconditional liveness ping with no DB/Redis check --
it exists to prove the FastAPI seam itself is reachable, not as the platform's
K8s probe target. ``/ht/`` (django-health-check, wired in
``config.settings.base``) is the real liveness/readiness endpoint that
actually checks the database and cache.
"""

from fastapi import FastAPI

fastapi_application = FastAPI(title="Python Agent Platform API")


@fastapi_application.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
