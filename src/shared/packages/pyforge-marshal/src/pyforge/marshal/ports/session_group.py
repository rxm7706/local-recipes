"""Injectable read of a dispatch session's process group (Story 90.1, AD-4)."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol

from pyforge.core.errors import PyforgeError


class SessionGroupReadError(PyforgeError, Exception):
    """The host could not enumerate the session's process group."""


@dataclass(frozen=True)
class SessionGroupMember:
    """One process belonging to the session's group at observation time."""

    pid: int
    started_at: float | None
    is_zombie: bool


class SessionGroupPort(Protocol):
    def iter_session_group_members(self, session_leader_pid: int) -> Iterator[SessionGroupMember]:
        """Yield every process in the session group the launch created.

        The group id is the leader pid from ``start_new_session=True`` (Story 90.1).
        Implementations never signal processes; they only observe.
        """
        ...
