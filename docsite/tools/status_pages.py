"""The fleet board and the guild status page -- stdlib-only (herald Story 42.1, spec-pyforge-herald CAP-60).

Two build-time pages under herald's ``/status/`` prefix, mounted beside ``/herald/`` by
``assemble_pages.py`` and rendered by ``docsite/build.py``:

* ``/status/`` -- the fleet board, read from ``docsite/content/fleet-status.json``, a gitignored build
  input a Guild step of steward's Pages workflow writes from ``sprint-ledger-query --format json``.
* ``/status/ci/`` -- the guild status page, every row of CAP-59's committed snapshot
  ``docsite/content/ci-status.json``, validated and ordered by ``ci_surfaces_tile.py`` (one reading).

Both are snapshots: each names its snapshot time and, when ``site.yml``'s ``lane1.href`` is an absolute
``http(s)://`` URL, links the live view on Lane 1 (:func:`lane1_link`). Lane 1 is served by the
platform, never by Pages, so a root-absolute (``/console/``) or relative href would resolve on the
Pages origin and 404 there: the link is then left out. Herald reads steward's output as data and
re-derives nothing; nothing here imports a station or calls ``gh``.

**The input** (``fleet-status.json``). Required: ``stations``, a list; per station ``done`` and
``total`` (non-negative integers, ``done`` no more than ``total``). Every other field is read under the name steward's JSON gives it
(``sprint-ledger-query --format json``: ``StationProgress`` and ``WorkPassportItem``) and is optional;
extra keys are ignored::

    {
      "generated_at": "2026-10-14T03:11:38+00:00",          # the snapshot time
      "stations": [
        {"station": "pyforge-atlas", "epics": 31, "total": 108, "done": 107,
         "in_progress": 0, "backlog": 1, "blocked": 0},
        ...
      ],
      "stories": [                                           # steward's `stories` rows
        {"story_id": "30.2", "station": "pyforge-atlas", "status": "backlog", "title": "..."},
        ...
      ]
    }

``stations`` is steward's ``summary.stations`` as a list (``total`` is ``total_stories``; ``epics``
counts steward's ``epics`` rows for the station); ``stories`` is steward's ``stories`` list, of which
the board's attention block shows the ``blocked`` and ``backlog`` rows.

**The flag** ``pyforge.herald.status_pages`` reaches the ``site`` build as ``PYFORGE_STATUS_PAGES``
(``export_status_pages_env.py``, run in the Guild env). Off: no ``/status/`` page renders, the input
is never opened, and a ``site.yml`` menu entry carrying ``flag: pyforge.herald.status_pages`` is left
out of every menu, so no other page of the artifact changes.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ENV_STATUS_PAGES = "PYFORGE_STATUS_PAGES"
FLAG_KEY = "pyforge.herald.status_pages"
#: The fleet board's build input, under ``docsite/content/`` (gitignored).
INPUT_NAME = "fleet-status.json"
INPUT_REL = f"docsite/content/{INPUT_NAME}"
#: Herald's prefix in the Pages artifact, beside ``/herald/``.
STATUS_PREFIX = "status"
BOARD_PAGE = f"{STATUS_PREFIX}/index.html"
GUILD_PAGE = f"{STATUS_PREFIX}/ci/index.html"
#: A ``site.yml`` menu entry carrying ``flag: <key>`` shows only with that flag on.
MENU_FLAG_KEY = "flag"
#: The attention block's statuses, in the order the block lists them.
ATTENTION_STATUSES: tuple[str, ...] = ("blocked", "backlog")
#: Optional per-station counts, read under steward's names.
COUNT_KEYS: tuple[str, ...] = ("epics", "in_progress", "backlog", "blocked")


class FleetStatusShapeError(ValueError):
    """The fleet-status input is missing, not JSON, or lacks a key the board needs."""


def enabled_from_env() -> bool:
    return os.environ.get(ENV_STATUS_PAGES, "").strip().lower() in ("1", "true", "yes")


def export_env_for_ci() -> dict[str, str]:
    from pyforge.herald.status_pages import status_pages_enabled

    return {ENV_STATUS_PAGES: "1" if status_pages_enabled() else "0"}


def input_path(content_dir: Path) -> Path:
    return content_dir / INPUT_NAME


def lane1_link(lane1: Any) -> dict[str, str] | None:
    """``site.yml``'s ``lane1`` entry when its ``href`` is an absolute ``http(s)://`` URL, else ``None``.

    Lane 1 is the platform's host, not Pages: a root-absolute href (``/console/``, the default until
    the operator names Lane 1's URL) or a relative one resolves on the Pages origin, where it 404s,
    so the status pages carry no Lane 1 link until ``lane1.href`` names another host (herald 42.1's
    re-review, orchestrator ruling 2026-10-15)."""
    if not isinstance(lane1, dict):
        return None
    href = lane1.get("href")
    if not isinstance(href, str) or not href.strip().lower().startswith(("http://", "https://")):
        return None
    return {"href": href.strip(), "label": str(lane1.get("label") or "")}


def menu_entries(entries: Iterable[dict[str, Any]], *, enabled: bool) -> list[dict[str, Any]]:
    """``entries`` without the ones gated on this flag, when it is off.

    An entry naming any other flag is refused: one gated entry this module does not know would
    otherwise show whatever its flag reads."""
    kept: list[dict[str, Any]] = []
    for item in entries:
        gate = item.get(MENU_FLAG_KEY)
        if gate is None:
            kept.append(dict(item))
            continue
        if gate != FLAG_KEY:
            raise ValueError(f"site.yml menu entry gated on an unknown flag {gate!r}: {item!r}")
        if enabled:
            kept.append(dict(item))
    return kept


def _is_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _station_label(index: int, station: dict[str, Any]) -> str:
    name = station.get("station")
    return f"station {index} ({name})" if isinstance(name, str) and name else f"station {index}"


def validate_fleet_status(data: Any, *, path: str) -> None:
    if not isinstance(data, dict):
        raise FleetStatusShapeError(f"{path}: envelope is not a JSON object")
    if "stations" not in data:
        raise FleetStatusShapeError(f"{path}: missing stations")
    stations = data["stations"]
    if not isinstance(stations, list):
        raise FleetStatusShapeError(f"{path}: stations is not a list")
    for index, station in enumerate(stations):
        if not isinstance(station, dict):
            raise FleetStatusShapeError(f"{path}: station {index} is not an object")
        label = _station_label(index, station)
        for key in ("done", "total"):
            if key not in station:
                raise FleetStatusShapeError(f"{path}: {label} missing {key}")
            if not _is_count(station[key]):
                raise FleetStatusShapeError(f"{path}: {label} {key} is not a non-negative integer")
        if station["done"] > station["total"]:
            raise FleetStatusShapeError(f"{path}: {label} done {station['done']} is more than total {station['total']}")
    stories = data.get("stories")
    if stories is None:
        return
    # Optional, but never read loosely: a malformed list would render a false "nothing needs attention".
    if not isinstance(stories, list):
        raise FleetStatusShapeError(f"{path}: stories is not a list")
    for index, story in enumerate(stories):
        if not isinstance(story, dict):
            raise FleetStatusShapeError(f"{path}: story {index} is not an object")
        for key in ("story_id", "status"):
            if key not in story:
                raise FleetStatusShapeError(f"{path}: story {index} missing {key}")


def load_fleet_status(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FleetStatusShapeError(f"{path}: fleet-status input missing")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        raise FleetStatusShapeError(f"{path}: unreadable ({exc})") from exc
    except json.JSONDecodeError as exc:
        raise FleetStatusShapeError(f"{path}: not valid JSON ({exc.msg})") from exc
    validate_fleet_status(data, path=str(path))
    return data


def bar_width(done: int, total: int) -> int:
    """The integer percentage of ``done`` over ``total`` (floored); 0 when ``total`` is 0. The shape
    check refuses ``done`` above ``total``; the clamp only keeps a direct caller's bar inside 100."""
    if total <= 0:
        return 0
    return min(100, done * 100 // total)


def _count(value: Any) -> str:
    return str(value) if _is_count(value) else "—"


def station_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, station in enumerate(data["stations"]):
        name = station.get("station")
        rows.append(
            {
                "name": name if isinstance(name, str) and name else f"station {index}",
                "done": station["done"],
                "total": station["total"],
                "width": bar_width(station["done"], station["total"]),
                **{key: _count(station.get(key)) for key in COUNT_KEYS},
            }
        )
    return rows


def attention_items(data: dict[str, Any]) -> list[dict[str, str]]:
    """Every ``blocked`` then every ``backlog`` story the input carries, each once, in input order."""
    stories = data.get("stories") or []
    seen: set[tuple[str, str]] = set()
    items: list[dict[str, str]] = []
    for status in ATTENTION_STATUSES:
        for story in stories:
            if story.get("status") != status:
                continue
            station = str(story.get("station") or "")
            story_id = str(story["story_id"])
            if (station, story_id) in seen:
                continue
            seen.add((station, story_id))
            title = story.get("title")
            items.append(
                {
                    "station": station,
                    "story_id": story_id,
                    "status": status,
                    "title": title if isinstance(title, str) else "",
                }
            )
    return items


def _counted(data: dict[str, Any], key: str) -> tuple[int, bool]:
    """The stations' summed ``key`` count, and whether every station gave one."""
    values = [station.get(key) for station in data["stations"]]
    return sum(value for value in values if _is_count(value)), all(_is_count(value) for value in values)


def _station_key(station: dict[str, Any]) -> str:
    """The name a story row's ``station`` is matched against (``""`` for a station without one)."""
    name = station.get("station")
    return name if isinstance(name, str) else ""


def _disagreements(data: dict[str, Any], items: list[dict[str, str]]) -> list[str]:
    """Per station, each attention status whose listed rows differ from that station's own count.

    Compared station by station, never as fleet-wide sums: one station's surplus must not hide
    another's missing rows (herald 42.1 re-review). A count the input does not give is not compared;
    a listed story whose station no ``stations`` row names is a disagreement of its own."""
    counts: dict[str, dict[str, int | None]] = {}
    for station in data["stations"]:
        merged = counts.setdefault(_station_key(station), dict.fromkeys(ATTENTION_STATUSES, 0))
        for status in ATTENTION_STATUSES:
            value = station.get(status)
            previous = merged[status]
            merged[status] = previous + value if previous is not None and _is_count(value) else None
    listed: dict[str, dict[str, int]] = {}
    for item in items:
        per = listed.setdefault(item["station"], dict.fromkeys(ATTENTION_STATUSES, 0))
        per[item["status"]] += 1
    lines: list[str] = []
    for name, per_status in counts.items():
        shown = listed.get(name, dict.fromkeys(ATTENTION_STATUSES, 0))
        parts = [
            f"{shown[status]} {status} listed, {count} counted"
            for status, count in per_status.items()
            if count is not None and shown[status] != count
        ]
        if parts:
            lines.append(f"{name or 'a station without a name'}: {', '.join(parts)}")
    for name, shown in listed.items():
        if name not in counts:
            parts = [f"{shown[status]} {status}" for status in ATTENTION_STATUSES if shown[status]]
            lines.append(f"{name or 'no station'}: {', '.join(parts)} listed, no station row counts them")
    return lines


def attention_note(data: dict[str, Any], items: list[dict[str, str]]) -> str | None:
    """What the attention block says beside (or instead of) its list, from the station counts.

    The all-clear is said only when every station counts 0 blocked and 0 backlog: an input whose
    ``stories`` lists fewer rows than its counts show (omitted, or filtered) says so instead of
    claiming nothing needs attention (herald 42.1 review). A list that disagrees with the counts
    names each station where it does, compared per station (herald 42.1 re-review)."""
    blocked, blocked_known = _counted(data, "blocked")
    backlog, backlog_known = _counted(data, "backlog")
    if not items:
        if blocked or backlog:
            return f"The input lists none of the {blocked} blocked / {backlog} backlog stories the station counts show."
        if blocked_known and backlog_known:
            return "Nothing needs attention: no story is blocked or in the backlog."
        return "The input lists no blocked or backlog story, and its station counts do not say whether any exist."
    lines = _disagreements(data, items)
    if lines:
        return "The input's story list and its station counts disagree. " + "; ".join(lines) + "."
    return None


def board(data: dict[str, Any]) -> dict[str, Any]:
    """The fleet board's view of a validated input."""
    generated_at = data.get("generated_at")
    items = attention_items(data)
    return {
        "generated_at": generated_at if isinstance(generated_at, str) and generated_at.strip() else None,
        "stations": station_rows(data),
        "attention": items,
        "attention_note": attention_note(data, items),
    }


#: The guild status page's columns, in order.
GUILD_FIELDS: tuple[str, ...] = ("id", "verdict", "switch", "paused_since", "review_by", "owner", "detail")


def built_from_html(env: dict[str, str] | None = None) -> str:
    """Story 43.5 (CAP-61): the line saying what built the page, for the status pages while ``build.py`` renders
    them (until Story 43.7) -- ``docs-site/src/lib/built-from.ts``'s ``builtFromHtml``, element for element (a test
    holds the two equal): ``GITHUB_SHA``'s first seven, ``PAGES_BUILT_AT`` (else now) to the minute in UTC and
    ``GITHUB_RUN_ID``; ``local build`` with no ``GITHUB_SHA``. Steward's ``tree_hash`` reads it without its text."""
    from datetime import UTC, datetime
    from html import escape

    env = dict(os.environ) if env is None else env
    sha = env.get("GITHUB_SHA", "").strip()
    if sha:
        raw = env.get("PAGES_BUILT_AT", "").strip()
        if raw and not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", raw):
            raise ValueError(f"PAGES_BUILT_AT is not an ISO 8601 time with an offset: {raw!r}")
        at = datetime.fromisoformat(raw) if raw else datetime.now(tz=UTC)
        run = env.get("GITHUB_RUN_ID", "").strip()
        parts = [f"Built from {sha[:7]}", at.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC"), *([f"run {run}"] if run else [])]
        text = " · ".join(parts)
    else:
        text = "local build"
    return f'<p class="built-from" data-pages-built-from data-pagefind-ignore>{escape(text, quote=False)}</p>'


def guild_rows(ordered_rows: Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    """The guild status page's rows: ``ci-status.json``'s rows as ``ci_surfaces_tile.order_rows``
    validated and ordered them (the tile's verdict order, ``live`` last), each field as text."""
    return [
        {field: "—" if row.get(field) is None else str(row.get(field)) for field in GUILD_FIELDS}
        for row in ordered_rows
    ]


def collect_shape_problems(path: Path, *, enabled: bool | None = None) -> list[str]:
    """``pages-check``'s shape check: with the flag on, the input must load; off, it is not opened."""
    if not (enabled_from_env() if enabled is None else enabled):
        return []
    try:
        load_fleet_status(path)
    except FleetStatusShapeError as exc:
        return [str(exc)]
    return []
