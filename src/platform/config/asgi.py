"""
ASGI config for Python Agent Platform project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/dev/howto/deployment/asgi/

"""

import os
import sys
from pathlib import Path

from django.core.asgi import get_asgi_application

# This allows easy placement of apps within the interior
# platformapp directory.
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent
sys.path.append(str(BASE_DIR / "platformapp"))

# If DJANGO_SETTINGS_MODULE is unset, default to the local settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

# This application object is used by any ASGI server configured to use this file.
django_application = get_asgi_application()

# Import websocket application here, so apps from django_application are loaded first
# FastAPI seam (Story 10.1): owns the whole /api/ namespace. Epic 11 extends
# it with the real Langflow/DB-GPT mounts; this module never builds those.
from config.fastapi_app import fastapi_application  # noqa: E402
from config.websocket import websocket_application  # noqa: E402


async def application(scope, receive, send):
    if scope["type"] == "http" and scope["path"].startswith("/api/"):
        await fastapi_application(scope, receive, send)
    elif scope["type"] == "http":
        await django_application(scope, receive, send)
    elif scope["type"] == "websocket":
        await websocket_application(scope, receive, send)
    elif scope["type"] == "lifespan":
        # Neither django_application nor websocket_application implements the
        # ASGI lifespan protocol; an ASGI server that sends startup/shutdown
        # messages here would otherwise hit the NotImplementedError below.
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
    else:
        msg = f"Unknown scope type {scope['type']}"
        raise NotImplementedError(msg)
