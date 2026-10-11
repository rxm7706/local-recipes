"""Unit coverage for ``PsutilSessionGroup`` (Story 90.1)."""

from __future__ import annotations

from collections.abc import Iterator

import psutil
import pytest

from pyforge.marshal.adapters.session_group_psutil import PsutilSessionGroup
from pyforge.marshal.ports.session_group import SessionGroupMember, SessionGroupReadError


class _FakeProcess:
    def __init__(self, info: dict[str, object]) -> None:
        self.info = info


def test_iter_session_group_members_filters_by_pgid_and_maps_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        _FakeProcess({"pid": 100, "pgid": 42, "create_time": 1.5, "status": psutil.STATUS_RUNNING}),
        _FakeProcess({"pid": 200, "pgid": 99, "create_time": 2.0, "status": psutil.STATUS_RUNNING}),
        _FakeProcess({"pid": 101, "pgid": 42, "create_time": None, "status": psutil.STATUS_ZOMBIE}),
    ]

    def _process_iter(_attrs: list[str]) -> Iterator[_FakeProcess]:
        yield from rows

    monkeypatch.setattr(psutil, "process_iter", _process_iter)

    members = list(PsutilSessionGroup().iter_session_group_members(42))

    assert members == [
        SessionGroupMember(pid=100, started_at=1.5, is_zombie=False),
        SessionGroupMember(pid=101, started_at=None, is_zombie=True),
    ]


@pytest.mark.parametrize("exc_type", [OSError, ValueError])
def test_iter_session_group_members_wraps_host_read_failures(
    monkeypatch: pytest.MonkeyPatch, exc_type: type[BaseException]
) -> None:
    def _broken_iter(_attrs: list[str]) -> Iterator[_FakeProcess]:
        raise exc_type("host unreadable")
        yield  # pragma: no cover

    monkeypatch.setattr(psutil, "process_iter", _broken_iter)

    with pytest.raises(SessionGroupReadError, match="host unreadable") as raised:
        list(PsutilSessionGroup().iter_session_group_members(7))

    assert isinstance(raised.value.__cause__, exc_type)


def test_iter_session_group_members_wraps_psutil_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _broken_iter(_attrs: list[str]) -> Iterator[_FakeProcess]:
        raise psutil.NoSuchProcess(1)
        yield  # pragma: no cover

    monkeypatch.setattr(psutil, "process_iter", _broken_iter)

    with pytest.raises(SessionGroupReadError, match="process no longer exists"):
        list(PsutilSessionGroup().iter_session_group_members(7))
