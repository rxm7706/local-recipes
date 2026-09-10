"""Thin ASGI router for dashboard websocket faces (Story 48.6 / R-22)."""

from __future__ import annotations

from channels.routing import URLRouter

from pyforge.steward.dashboard.routing import websocket_urlpatterns

application = URLRouter(websocket_urlpatterns)
