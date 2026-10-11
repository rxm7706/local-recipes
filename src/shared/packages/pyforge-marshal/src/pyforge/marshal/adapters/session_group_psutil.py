"""POSIX session process-group observation via psutil (Story 90.1/92.1)."""

from __future__ import annotations

import os
from collections.abc import Iterator

import psutil

from ..ports.session_group import SessionGroupMember, SessionGroupReadError


class PsutilSessionGroup:
    """``SessionGroupPort`` backed by psutil — real host reads only, never a signal.

    Membership is read per process with ``os.getpgid`` over ``psutil.pids()`` (Story 92.1): psutil has no
    ``pgid`` attribute, and asking ``process_iter`` for one raises ``ValueError`` on every call (the 90.1
    outage). A process that exits during the scan, or one this user may not inspect, is skipped -- it is
    not a read error, and one unreadable process never fails the whole group read."""

    def iter_session_group_members(self, session_leader_pid: int) -> Iterator[SessionGroupMember]:
        # ``start_new_session=True`` makes the launched child the session leader; its pgid is its pid.
        pgid = session_leader_pid
        try:
            pids = psutil.pids()
        except (psutil.Error, OSError) as exc:
            raise SessionGroupReadError(str(exc)) from exc
        for pid in pids:
            try:
                if os.getpgid(pid) != pgid:
                    continue
            except ProcessLookupError, PermissionError:
                continue
            except OSError as exc:
                raise SessionGroupReadError(f"getpgid({pid}) failed: {exc}") from exc
            try:
                proc = psutil.Process(pid)
                with proc.oneshot():
                    started_at: float | None = proc.create_time()
                    status: str | None = proc.status()
            except psutil.NoSuchProcess:
                continue
            except psutil.AccessDenied:
                started_at, status = None, None
            except psutil.Error as exc:
                raise SessionGroupReadError(f"cannot read process {pid}: {exc}") from exc
            yield SessionGroupMember(
                pid=pid,
                started_at=started_at,
                is_zombie=status == psutil.STATUS_ZOMBIE,
            )


def process_cmdline(pid: int) -> str | None:
    """``pid``'s command line, space-joined, or ``None`` when it cannot be read (Story 92.1's identity
    fallback). psutil reads it on every host marshal supports, including those with no ``/proc``."""
    try:
        argv = psutil.Process(pid).cmdline()
    except psutil.Error, OSError:
        return None
    return " ".join(argv) if argv else None
