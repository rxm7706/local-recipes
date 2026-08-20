"""Builds Langflow's FastAPI app once, exported for `config/asgi.py`'s dispatcher.

Story 11.1 (spec-python-agent-platform CAP-2, AD-4/AD-14 Pattern A): Langflow
lives in-process as a mounted ASGI app, not a sidecar. `langflow.main.create_app()`
reads Langflow's own settings (`LANGFLOW_DATABASE_URL`, `LANGFLOW_CACHE_TYPE`,
`LANGFLOW_CONFIG_DIR`, `LANGFLOW_KNOWLEDGE_BASES_DIR`, ...) from the process
environment at call time via its own pydantic-settings service -- so this module
must be imported only AFTER Django's settings have executed and exported those
derived values into `os.environ` (`config/settings/base.py`). `config/asgi.py`
guarantees that ordering the same way it already does for
`config.fastapi_app`/`config.websocket`: it imports this module only after
`django_application = get_asgi_application()` has triggered `django.setup()`.

`create_app()` only constructs the FastAPI app object (routes, middleware, the
`lifespan` context manager) -- it does not open a database connection or run
Langflow's own Alembic migrations. Those happen when the ASGI server actually
sends this app a `lifespan.startup` message, which `config/asgi.py`'s dispatcher
drives explicitly alongside the platform's own FastAPI stub's lifespan (Design
Notes: "Dual-lifespan ASGI startup").
"""

from langflow.main import create_app

langflow_application = create_app()
