"""Warden fleet-inventory poll cursor for the dependency-history sensor (Story 25.2, CAP-61).

Compares each inventoried repo's default-branch head SHA against a JSON cursor map
(``repo full name → last processed head``). Moved or newly seen heads coalesce into
one run/skip decision for the Story 25.1 job — dagster-free so AD-1 holds (only
``orchestration/definitions.py`` imports Dagster and wraps this module).

The inventory snapshot is injectable; the default production source returns an empty
export with no filesystem or network read (mirrors ``offline_event_source``).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

# Zero-arg callable returning the current fleet inventory export (a mapping).
InventorySource = Callable[[], Mapping[str, Any] | None]

FLAG_KEY = "pyforge.atlas.dependency_history_sensor"


@dataclass(frozen=True)
class FleetRepoHead:
    """One repo row from Warden's fleet inventory export (``spec-pyforge-warden:CAP-26``)."""

    full_name: str
    head_sha: str


@dataclass(frozen=True)
class FleetInventoryDecision:
    """Run/skip verdict for one sensor tick (mirrors G3's ``SensorDecision``)."""

    run: bool
    run_key: str | None
    new_cursor: str | None
    skip_reason: str | None
    moved_repos: tuple[str, ...]


def offline_fleet_inventory_source() -> dict[str, Any]:
    """Default production source: empty export, no path read, no network (Story 25.2)."""
    return {"repos": []}


def parse_fleet_inventory(raw: Mapping[str, Any] | None) -> tuple[FleetRepoHead, ...] | None:
    """Coerce Warden's export into repo head rows; ``None`` means malformed."""
    if raw is None:
        return ()
    if not isinstance(raw, Mapping):
        return None
    repos = raw.get("repos")
    if not isinstance(repos, list):
        return None
    parsed: list[FleetRepoHead] = []
    for item in repos:
        if not isinstance(item, Mapping):
            return None
        full_name = item.get("full_name")
        head_sha = item.get("head_sha")
        if not full_name or not head_sha:
            return None
        parsed.append(FleetRepoHead(full_name=str(full_name), head_sha=str(head_sha)))
    return tuple(parsed)


def _decode_cursor(cursor: str | None) -> dict[str, str]:
    if not cursor:
        return {}
    try:
        data = json.loads(cursor)
    except (TypeError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, str] = {}
    for key, value in data.items():
        if isinstance(key, str) and value is not None:
            out[key] = str(value)
    return out


def _encode_cursor(cursor_map: dict[str, str]) -> str:
    return json.dumps(dict(sorted(cursor_map.items())), sort_keys=True)


def _stable_run_key(prefix: str, moved: Mapping[str, str]) -> str:
    payload = json.dumps(sorted(moved.items()), sort_keys=True)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}:{digest}"


def evaluate_fleet_inventory(
    heads: Sequence[FleetRepoHead],
    cursor: str | None,
    *,
    run_key_prefix: str,
) -> FleetInventoryDecision:
    """Pure decision over an inventory snapshot and the persisted cursor."""
    prior = _decode_cursor(cursor)
    current = {h.full_name: h.head_sha for h in heads}
    moved = {name: current[name] for name in sorted(current) if prior.get(name) != current[name]}
    new_map = dict(current)

    if moved:
        return FleetInventoryDecision(
            run=True,
            run_key=_stable_run_key(run_key_prefix, moved),
            new_cursor=_encode_cursor(new_map),
            skip_reason=None,
            moved_repos=tuple(sorted(moved)),
        )

    removed = set(prior) - set(current)
    if removed:
        return FleetInventoryDecision(
            run=False,
            run_key=None,
            new_cursor=_encode_cursor(new_map),
            skip_reason="fleet inventory unchanged; dropped repos removed from cursor",
            moved_repos=(),
        )

    return FleetInventoryDecision(
        run=False,
        run_key=None,
        new_cursor=cursor,
        skip_reason="no fleet inventory head changes",
        moved_repos=(),
    )


def evaluate_fleet_inventory_from_raw(
    raw: Mapping[str, Any] | None,
    cursor: str | None,
    *,
    run_key_prefix: str,
) -> FleetInventoryDecision:
    """Parse + decide; malformed export skips with cursor untouched."""
    parsed = parse_fleet_inventory(raw)
    if parsed is None:
        return FleetInventoryDecision(
            run=False,
            run_key=None,
            new_cursor=cursor,
            skip_reason="malformed fleet inventory export",
            moved_repos=(),
        )
    return evaluate_fleet_inventory(parsed, cursor, run_key_prefix=run_key_prefix)
