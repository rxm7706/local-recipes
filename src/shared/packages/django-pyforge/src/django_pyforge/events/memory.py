"""In-process Redis Streams subset for tests (no live cluster)."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any


class StreamResponseError(Exception):
    """Redis-style stream errors (BUSYGROUP / NOGROUP)."""


def _as_str(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode()
    return str(value)


def _parse_stream_id(stream_id: str) -> tuple[int, int]:
    if stream_id in {"-", "0"}:
        return (0, 0)
    if stream_id in {"+", ">"}:
        return (2**63 - 1, 0)
    ms_s, _, seq_s = stream_id.partition("-")
    return (int(ms_s), int(seq_s or "0"))


@dataclass
class _Entry:
    stream_id: str
    fields: dict[str, str]


@dataclass
class _Pending:
    stream_id: str
    consumer: str
    delivered_at: int
    delivery_count: int = 1


@dataclass
class _Group:
    name: str
    last_id: str
    pending: dict[str, _Pending] = field(default_factory=dict)


class MemoryRedis:
    """Enough Streams + SET/GET for EventFabric tests."""

    def __init__(self) -> None:
        self._kv: dict[str, str] = {}
        self._streams: dict[str, list[_Entry]] = {}
        self._groups: dict[str, dict[str, _Group]] = {}
        self._seq = 0
        self._clock = 0

    def set(self, name: str, value: Any, nx: bool = False) -> bool | None:
        key = _as_str(name)
        if nx and key in self._kv:
            return None
        self._kv[key] = _as_str(value)
        return True

    def delete(self, *names: str) -> int:
        removed = 0
        for name in names:
            if self._kv.pop(_as_str(name), None) is not None:
                removed += 1
        return removed

    def get(self, name: str) -> str | None:
        return self._kv.get(_as_str(name))

    def exists(self, *names: str) -> int:
        return sum(1 for name in names if _as_str(name) in self._kv)

    def xadd(self, name: str, fields: dict[str, Any], **_kwargs: Any) -> str:
        self._seq += 1
        stream_id = f"{self._seq}-0"
        copied = {_as_str(k): _as_str(v) for k, v in fields.items()}
        self._streams.setdefault(name, []).append(_Entry(stream_id, copied))
        return stream_id

    def xgroup_create(
        self,
        name: str,
        groupname: str,
        id: str = "$",  # noqa: A002 -- redis-py argument name
        mkstream: bool = False,
    ) -> bool:
        if name not in self._streams:
            if not mkstream:
                msg = "no such key"
                raise StreamResponseError(msg)
            self._streams[name] = []
        groups = self._groups.setdefault(name, {})
        if groupname in groups:
            msg = "BUSYGROUP Consumer Group name already exists"
            raise StreamResponseError(msg)
        last = id
        entries = self._streams[name]
        if id == "$":
            last = entries[-1].stream_id if entries else "0-0"
        elif id in {"0", "0-0"}:
            last = "0-0"
        groups[groupname] = _Group(name=groupname, last_id=last)
        return True

    def xreadgroup(
        self,
        groupname: str,
        consumername: str,
        streams: dict[str, str],
        count: int | None = None,
        **_kwargs: Any,
    ) -> list[list[Any]]:
        out: list[list[Any]] = []
        for stream_name, start in streams.items():
            group = self._require_group(stream_name, groupname)
            if start == ">":
                messages = self._deliver_new(stream_name, group, consumername, count)
            else:
                messages = self._pending_for(stream_name, group, consumername, start, count)
            if messages:
                out.append([stream_name, messages])
        return out

    def xack(self, name: str, groupname: str, *ids: str) -> int:
        group = self._require_group(name, groupname)
        acked = 0
        for stream_id in ids:
            if group.pending.pop(_as_str(stream_id), None) is not None:
                acked += 1
        return acked

    def xautoclaim(
        self,
        name: str,
        groupname: str,
        consumername: str,
        min_idle_time: int,
        start_id: str = "0-0",
        count: int | None = None,
        **_kwargs: Any,
    ) -> tuple[str, list[tuple[str, dict[str, str]]]]:
        group = self._require_group(name, groupname)
        start = _parse_stream_id(start_id)
        claimed: list[tuple[str, dict[str, str]]] = []
        for pending in sorted(group.pending.values(), key=lambda item: _parse_stream_id(item.stream_id)):
            if _parse_stream_id(pending.stream_id) < start:
                continue
            idle = max(0, self._clock - pending.delivered_at)
            if idle < min_idle_time:
                continue
            pending.consumer = consumername
            pending.delivered_at = self._clock
            pending.delivery_count += 1
            fields = self._fields(name, pending.stream_id)
            if fields is not None:
                claimed.append((pending.stream_id, fields))
            if count is not None and len(claimed) >= count:
                break
        next_id = claimed[-1][0] if claimed else "0-0"
        return (next_id, claimed)

    def xpending_range(
        self,
        name: str,
        groupname: str,
        min: str = "-",  # noqa: A002 -- redis-py argument name
        max: str = "+",  # noqa: A002 -- redis-py argument name
        count: int = 100,
        **_kwargs: Any,
    ) -> list[dict[str, str | int]]:
        group = self._require_group(name, groupname)
        lo = _parse_stream_id(min)
        hi = _parse_stream_id(max)
        cap = count
        out: list[dict[str, str | int]] = []
        for pending in sorted(
            group.pending.values(),
            key=lambda item: _parse_stream_id(item.stream_id),
        ):
            parsed = _parse_stream_id(pending.stream_id)
            if parsed < lo or parsed > hi:
                continue
            idle = self._clock - pending.delivered_at
            if idle < 0:
                idle = 0
            out.append(
                {
                    "message_id": pending.stream_id,
                    "consumer": pending.consumer,
                    "time_since_delivered": idle,
                    "times_delivered": pending.delivery_count,
                },
            )
            if len(out) >= cap:
                break
        return out

    def xclaim(
        self,
        name: str,
        groupname: str,
        consumername: str,
        min_idle_time: int,
        *ids: str,
        **_kwargs: Any,
    ) -> list[tuple[str, dict[str, str]]]:
        group = self._require_group(name, groupname)
        claimed: list[tuple[str, dict[str, str]]] = []
        for stream_id in ids:
            pending = group.pending.get(_as_str(stream_id))
            if pending is None:
                continue
            idle = max(0, self._clock - pending.delivered_at)
            if idle < min_idle_time:
                continue
            pending.consumer = consumername
            pending.delivered_at = self._clock
            pending.delivery_count += 1
            fields = self._fields(name, pending.stream_id)
            if fields is not None:
                claimed.append((pending.stream_id, fields))
        return claimed

    def xrange(
        self,
        name: str,
        min: str = "-",  # noqa: A002 -- redis-py argument name
        max: str = "+",  # noqa: A002 -- redis-py argument name
        count: int | None = None,
    ) -> list[tuple[str, dict[str, str]]]:
        entries = self._streams.get(name, [])
        lo = _parse_stream_id(min)
        hi = _parse_stream_id(max)
        out: list[tuple[str, dict[str, str]]] = []
        for entry in entries:
            parsed = _parse_stream_id(entry.stream_id)
            if lo <= parsed <= hi:
                out.append((entry.stream_id, dict(entry.fields)))
            if count is not None and len(out) >= count:
                break
        return out

    def _require_group(self, stream_name: str, groupname: str) -> _Group:
        groups = self._groups.get(stream_name)
        if not groups or groupname not in groups:
            msg = "NOGROUP No such key or consumer group"
            raise StreamResponseError(msg)
        return groups[groupname]

    def _deliver_new(
        self,
        stream_name: str,
        group: _Group,
        consumername: str,
        count: int | None,
    ) -> list[tuple[str, dict[str, str]]]:
        self._clock += 1
        last = _parse_stream_id(group.last_id)
        messages: list[tuple[str, dict[str, str]]] = []
        for entry in self._streams.get(stream_name, []):
            if _parse_stream_id(entry.stream_id) <= last:
                continue
            if entry.stream_id in group.pending:
                continue
            group.pending[entry.stream_id] = _Pending(
                stream_id=entry.stream_id,
                consumer=consumername,
                delivered_at=self._clock,
            )
            group.last_id = entry.stream_id
            messages.append((entry.stream_id, dict(entry.fields)))
            if count is not None and len(messages) >= count:
                break
        return messages

    def _pending_for(
        self,
        stream_name: str,
        group: _Group,
        consumername: str,
        start: str,
        count: int | None,
    ) -> list[tuple[str, dict[str, str]]]:
        self._clock += 1
        floor = _parse_stream_id(start)
        messages: list[tuple[str, dict[str, str]]] = []
        for pending in sorted(group.pending.values(), key=lambda item: _parse_stream_id(item.stream_id)):
            if pending.consumer != consumername:
                continue
            if _parse_stream_id(pending.stream_id) < floor:
                continue
            fields = self._fields(stream_name, pending.stream_id)
            if fields is None:
                continue
            pending.delivered_at = self._clock
            pending.delivery_count += 1
            messages.append((pending.stream_id, fields))
            if count is not None and len(messages) >= count:
                break
        return messages

    def _fields(self, stream_name: str, stream_id: str) -> dict[str, str] | None:
        for entry in self._streams.get(stream_name, []):
            if entry.stream_id == stream_id:
                return dict(entry.fields)
        return None
