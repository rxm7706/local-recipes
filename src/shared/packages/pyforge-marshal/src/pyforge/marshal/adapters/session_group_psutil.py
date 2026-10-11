"""POSIX session process-group observation via psutil (Story 90.1/92.1)."""

from __future__ import annotations

import os
from collections.abc import Iterator

import psutil

from ..ports.session_group import SessionGroupMember, SessionGroupReadError


class PsutilSessionGroup:
    """``SessionGroupPort`` backed by psutil — real host reads only."""

    def iter_session_group_members(self, session_leader_pid: int) -> Iterator[SessionGroupMember]:
        # ``start_new_session=True`` makes the launched child the session leader; its pgid is its pid.
        pgid = session_leader_pid
        try:
            for proc in psutil.process_iter(["pid", "create_time", "status"]):
                info = proc.info
                pid = int(info["pid"])
                try:
                    if os.getpgid(pid) != pgid:
                        continue
                except ProcessLookupError:
                    continue
                status = info.get("status")
                yield SessionGroupMember(
                    pid=pid,
                    started_at=info.get("create_time"),
                    is_zombie=status == psutil.STATUS_ZOMBIE,
                )
        except (psutil.Error, OSError, ValueError) as exc:
            raise SessionGroupReadError(str(exc)) from exc
