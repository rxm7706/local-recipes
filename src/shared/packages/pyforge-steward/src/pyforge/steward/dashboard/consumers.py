"""Channels websocket consumer for live CloudEvent relay (Story 48.6 / R-22)."""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
from typing import Any
from urllib.parse import parse_qs

from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from django_pyforge.assertion.exceptions import (
    AssertionRefusedError,
    BadSignatureError,
    ExpiredAssertionError,
    WrongAudienceError,
)
from django_pyforge.assertion.schema import CLAIM_SUB, EVENTS_AUDIENCE
from django_pyforge.assertion.verify import verify_assertion_claims
from django_pyforge.events.browser_relay import cloudevent_from_fields, matches_subject, tail_events

_CLOSE_UNAUTHORIZED = 4401


class EventsStreamConsumer(AsyncWebsocketConsumer):
    """Tail-read ``pyforge.events`` and forward subject-matched CloudEvents."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._subject: str | None = None
        self._relay_task: asyncio.Task[None] | None = None
        self._stop_relay = False

    async def connect(self) -> None:
        token = _token_from_scope(self.scope)
        if not token:
            await self.close(code=_CLOSE_UNAUTHORIZED)
            return
        public_pem = _assertion_public_pem()
        if not public_pem:
            await self.close(code=_CLOSE_UNAUTHORIZED)
            return
        try:
            claims = verify_assertion_claims(
                token,
                audience=EVENTS_AUDIENCE,
                public_pem=public_pem,
            )
        except (
            AssertionRefusedError,
            BadSignatureError,
            ExpiredAssertionError,
            WrongAudienceError,
        ):
            await self.close(code=_CLOSE_UNAUTHORIZED)
            return
        subject = claims.get(CLAIM_SUB)
        if not isinstance(subject, str) or not subject:
            await self.close(code=_CLOSE_UNAUTHORIZED)
            return
        self._subject = subject
        await self.accept()
        self._stop_relay = False
        self._relay_task = asyncio.create_task(self._relay_loop())

    async def disconnect(self, code: int) -> None:
        self._stop_relay = True
        if self._relay_task is not None:
            self._relay_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._relay_task
            self._relay_task = None

    async def _relay_loop(self) -> None:
        assert self._subject is not None
        broker_url = _broker_url()
        if not broker_url:
            return
        try:
            async for _stream_id, fields in tail_events(
                broker_url,
                last_id="$",
                stop=lambda: self._stop_relay,
            ):
                event = cloudevent_from_fields(fields)
                if event is None or not matches_subject(event, self._subject):
                    continue
                await self.send(text_data=json.dumps(event))
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 -- relay dies quietly; client can reconnect
            return


def _token_from_scope(scope: dict[str, Any]) -> str | None:
    raw = scope.get("query_string", b"")
    if isinstance(raw, bytes):
        query = raw.decode("latin-1")
    else:
        query = str(raw)
    values = parse_qs(query, keep_blank_values=False).get("token")
    if not values:
        return None
    token = values[0]
    return token if isinstance(token, str) and token.strip() else None


def _assertion_public_pem() -> str:
    configured = getattr(settings, "PYFORGE_ASSERTION_PUBLIC_KEY", "")
    if isinstance(configured, str) and configured.strip():
        return configured.strip()
    env = os.environ.get("PYFORGE_ASSERTION_PUBLIC_KEY", "")
    return env.strip() if isinstance(env, str) else ""


def _broker_url() -> str:
    configured = getattr(settings, "REDIS_BROKER_URL", "")
    if isinstance(configured, str) and configured.strip():
        return configured.strip()
    env = os.environ.get("REDIS_BROKER_URL", "")
    return env.strip() if isinstance(env, str) else ""
