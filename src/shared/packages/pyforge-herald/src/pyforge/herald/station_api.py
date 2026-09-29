"""Herald v1 station API registration (Story 19.1).

The platform host registers herald's FastAPI sub-app in
``config.station_api`` but must not import ``pyforge.*`` directly — it
loads this module by name via ``importlib`` and calls ``attach_webhook_asgi``.
"""

from __future__ import annotations

from typing import Any


class _LazyWebhookASGI:
    """Defer ``webhook_host`` import/build until the first webhook request."""

    def __init__(self) -> None:
        self._inner = None

    async def __call__(self, scope, receive, send) -> None:
        if self._inner is None:
            from pyforge.herald import webhook, webhook_host

            self._inner = webhook_host.build_application(
                webhook_host._resolve_repo_root(),
                webhook.resolve_webhook_secret(),
            )
        await self._inner(scope, receive, send)


def attach_webhook_asgi(app: Any) -> None:
    """Mount the webhook ASGI callable on herald's station sub-app."""
    app.mount("/", _LazyWebhookASGI())
