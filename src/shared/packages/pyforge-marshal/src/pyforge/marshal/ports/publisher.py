"""``RunPublisherPort`` — CAP-18 / Story 33.4 run-state publish seam.

A Protocol definition only (AD-11): implemented solely by
``adapters.publisher_host.py::HostPublisher`` (AD-4). Supervisors call the
port on attach, heartbeat, and detach/completion; publish failures are
best-effort and never stop the supervision loop.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class PublishRecord:
    """Neutral publish payload shaped in ``core.publish`` (AD-4, no I/O)."""

    station: str
    run_id: str
    story_key: str | None = None
    phase: str | None = None
    commit_sha: str | None = None
    harness_run_id: str | None = None
    run_kind: str = "loop"
    layer_savings: Mapping[str, object] = field(default_factory=dict)


class RunPublisherPort(Protocol):
    def publish(self, record: PublishRecord) -> str | None:
        """Publish run start; return a host run handle or ``None`` on skip/failure."""
        ...

    def heartbeat(self, handle: str) -> None:
        """Best-effort heartbeat for an existing handle."""
        ...

    def complete(
        self,
        handle: str,
        *,
        status: str,
        result: Mapping[str, object],
    ) -> None:
        """Best-effort terminal completion for an existing handle."""
        ...
