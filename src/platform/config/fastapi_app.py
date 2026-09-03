"""FastAPI sub-app mounted at ``/api/`` by :mod:`config.asgi`.

Story 10.1 scope: only the seam itself, exposing a bare ``GET /api/health``
probe. :mod:`config.asgi` routes every ``/api/*`` HTTP path here except
versioned station APIs (Story 43.2: ``/stations/<name>/api/v<N>/`` on
:mod:`config.station_api` sub-apps). Websocket connections are not
path-routed at all yet -- every one reaches the stock ``websocket_application``
stub regardless of path, since nothing under this seam handles websockets today.

Story 11.1 attached Langflow at bare ``/health``/``/health_check`` and
prefix-stripped ``/langflow/*`` directly in :mod:`config.asgi` -- ahead of
this seam in the dispatch order (AD-4) -- rather than through this module,
since Langflow builds and owns its own FastAPI app
(:mod:`langflow_integration.asgi`). Story 43.2 removed bare ``/api/v1/*``
from Langflow's mount; ``/langflow/api/v1/...`` still reaches Langflow.
DB-GPT's ``/api/dbgpt/`` mount (spec-python-agent-platform CAP-3, Story 11.2)
is not yet attached -- not assumed here.

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
