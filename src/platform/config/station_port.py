"""Wire the host ASGI seam as the in-process station port (Story 43.3).

``src/platform/`` never imports ``pyforge.*``; this module registers the
invoker through ``django_pyforge.station_port`` only.
"""

from __future__ import annotations

import asyncio
from urllib.parse import urlparse


def asgi_invoke(
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes | None,
) -> bytes:
    """Dispatch a station API request through the host ASGI app without HTTP."""
    from httpx import ASGITransport
    from httpx import AsyncClient

    from config.asgi import application

    parsed = urlparse(url)
    path = parsed.path
    if parsed.query:
        path = f"{path}?{parsed.query}"

    async def _call() -> bytes:
        transport = ASGITransport(app=application)
        async with AsyncClient(
            transport=transport,
            base_url="http://in-process",
        ) as client:
            response = await client.request(
                method,
                path,
                headers=headers,
                content=body,
            )
            response.raise_for_status()
            return response.content

    return asyncio.run(_call())


def wire_station_port() -> None:
    """Register the in-process invoker once Django apps are ready."""
    from django_pyforge.station_port import register_in_process_handler

    register_in_process_handler(asgi_invoke)
