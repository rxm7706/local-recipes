"""Django-free recall submit: one PortalClient.call, no HTTP."""

from __future__ import annotations

from typing import Any, Protocol


class RecallClient(Protocol):
    def call(
        self,
        station: str,
        job: str,
        payload: dict[str, Any],
        *,
        sub: str,
        roles: list[str],
    ) -> dict[str, Any]: ...


def submit_recall(
    client: RecallClient,
    query: str,
    *,
    sub: str,
    roles: list[str],
) -> dict[str, Any]:
    """Submit one recall query through ``client.call`` only."""
    return client.call(
        "scribe",
        "recall",
        {"query": query},
        sub=sub,
        roles=roles,
    )
