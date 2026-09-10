"""Websocket URL patterns for the steward dashboard extra (Story 48.6 / R-22)."""

from __future__ import annotations

from django.urls import re_path

from pyforge.steward.dashboard.consumers import EventsStreamConsumer

websocket_urlpatterns = [
    re_path(r"^ws/events/$", EventsStreamConsumer.as_asgi()),
]
