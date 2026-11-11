"""The capability ledger's check (Story 121.6; spec-foundry-capability-ledger fcl:CAP-1 and fcl:CAP-2).

``check(root, ledger)`` judges ``docs/foundry/capability-ledger.yaml`` against the live Specs and the written rules of
``modes.md`` (the companion of ``spec-foundry-capability-ledger``: section *Schema v1*, *Expiry*, *Marker tokens* and
*The rules of 2026-11-10*) and writes nothing. It returns ``.findings``, each of which refuses the ledger, and
``.warnings``, each reported and never refused; every one is a ``(code, id, message)`` triple. The inventory is the
generator's (``cutover_ledger.live_caps``, Story 121.1), so the generator and the check read one extract.

* ``rebuild-never-built`` is ruling 3 as ``modes.md`` rule 7 writes it: a ``rebuild`` row whose Spec heading reads
  ``(ready`` and none of whose citing stories reads ``done``. A citing story is a ``### Story E.S`` block of the row
  station's ``epics.md`` whose FR/AD or Parent line names the capability; its status is the ``E-S-`` key of that
  station's ``sprint-status-ledger.yaml``. The message names how the second addendum settles the row.
* An expiry is judged by its form only (``"<station>:<E>.<S>"``, ``"YYYY-MM-DD"`` or ``"flip"``): dates and Story keys
  are doctor's clock (``spec-pyforge-doctor:CAP-95``). A ``flip`` expiry lapses when
  ``pyforge.core.cutover_root.root_of_record()`` answers ``foundry``.
* Case ids are the first column of ``case-list.md`` (``fnr:CAP-1``), read with the rule doctor's
  ``capability-ledger`` source uses.

The module imports no other station; ``steward cutover plan --check`` (Story 121.2) is its caller.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from pyforge.core.cutover_root import root_of_record
from pyforge.core.roster import STATIONS

from .cutover_ledger import (
    CUTOVER_PREFIXES,
    DEFAULT_LEDGER,
    EXTRACT_PATH,
    FROZEN_STATES,
    GENERATED_BY,
    HEADER_KEYS,
    MODES,
    SCHEMA,
    STATES,
    CutoverLedgerError,
    LiveCap,
    cap_id,
    live_caps,
)

# Each finding refuses the ledger; each warning is reported every run and refuses nothing.
FINDING_CODES: tuple[str, ...] = (
    "rebuild-never-built",
    "unclassified",
    "orphan-row",
    "archived-spec-row",
    "heading-drift",
    "duplicate-cap-id",
    "bad-header",
    "bad-mode",
    "bad-state",
    "a-only-without-expiry",
    "bad-expiry-form",
    "flip-expiry-lapsed",
    "rebuild-without-state",
    "verified-without-case",
    "unknown-case",
    "rebuilding-without-frozen-paths",
    "unresolved-dependency",
    "dependency-cycle",
    "launch-not-rebuild",
    "pending-without-question",
    "retire-without-marker",
    "marker-contradicts-mode",
    "unknown-marker",
    "cell-without-expiry",
)
WARNING_CODES: tuple[str, ...] = (
    "mode-pending",
    "defaulted-row",
    "no-marker",
)

__all__ = (
    "CASE_LIST",
    "FINDING_CODES",
    "FLIP",
    "WARNING_CODES",
    "CheckReport",
    "Issue",
    "case_ids",
    "check",
    "citing_stories",
    "expiry_form_problem",
)

Issue = tuple[str, str, str]

CASE_LIST = Path(
    "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/case-list.md"
)
FLIP = "flip"
_FOUNDRY = "foundry"
_HEADER_ID = "header"
_PROJECTS = Path("_bmad-output/projects")
_EPICS = Path("planning-artifacts/epics.md")
_SPRINT_LEDGER = Path("planning-artifacts/sprint-status-ledger.yaml")
_STATION_PREFIX = "pyforge-"
_DONE = "done"
_LIVE_STORY = frozenset({"blocked", "backlog"})
_RETIRED = "retired"
_READY = "ready"
_UNKNOWN = "unknown"
_ARCHIVE_PART = "archive"

# modes.md § Header: the values every v1 header carries.
_HEADER_VALUES: Mapping[str, Any] = {
    "schema": SCHEMA,
    "generated_by": GENERATED_BY,
    "extract": EXTRACT_PATH,
    "modes": list(MODES),
    "states": list(STATES),
    "frozen_states": list(FROZEN_STATES),
}

# Doctor's first-column rule for case-list.md (its capability-ledger source).
_CASE_ID_RE = re.compile(r"^\|\s*(k-[a-z0-9-]+)\s*\|", re.MULTILINE)

# modes.md § Expiry: the three forms; the station is the short key.
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_STORY_EXPIRY_RE = re.compile(r"^(?P<station>[a-z]+):\d+\.\d+$")

# A citing story: a `### Story E.S` block whose FR/AD or Parent line names the capability.
_STORY_RE = re.compile(r"^###[ \t]+Story[ \t]+(?P<epic>\d+)\.(?P<story>\d+)\b")
_BLOCK_END_RE = re.compile(r"^#{1,3}[ \t]")
_LABEL_RE = re.compile(r"\*\*(?:FR/AD|Parent):\*\*|^[ \t]*Parent:")
# A label runs to the next bold label: a bullet separates the items inside it as well as the fields around it.
_NEXT_LABEL_RE = re.compile(r"\*\*[A-Za-z][^*\n]{0,40}:\*\*")
_RANGE = r"(?:[ \t]*(?:\.\.|–|—|\bto\b)[ \t]*(?:[a-z][a-z0-9-]*:)?(?:CAP-)?(?P<{0}>\d+))?"
_REF_RE = re.compile(
    r"\bspec-(?P<spec>[a-z0-9]+(?:-[a-z0-9]+)*)(?::CAP-(?P<sn>\d+)" + _RANGE.format("sto") + r")?"
    r"|\b(?P<pfx>[a-z][a-z0-9]*(?:-[a-z0-9]+)*):CAP-(?P<pn>\d+)" + _RANGE.format("pto") + r"|\bCAP-(?P<n>\d+)"
    r"" + _RANGE.format("to")
)
_MAX_RANGE = 100
_LEDGER_KEY_RE = re.compile(r"^(?P<epic>\d+)-(?P<story>\d+)-")
# A short prefix that names a Spec of its own (extract.md § Id rule); `pap` names a heading, not a Spec context.
_SHORT_PREFIX_SPEC: Mapping[str, str] = {prefix: spec for spec, prefix in CUTOVER_PREFIXES.items()}
_HEADING_PREFIX = "pap"


@dataclass(frozen=True)
class CheckReport:
    """What ``check`` found: findings refuse the ledger, warnings never do."""

    findings: tuple[Issue, ...] = ()
    warnings: tuple[Issue, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.findings


class _Out:
    def __init__(self) -> None:
        self.findings: list[Issue] = []
        self.warnings: list[Issue] = []

    def find(self, code: str, item: str, message: str) -> None:
        self.findings.append((code, item, message))

    def warn(self, code: str, item: str, message: str) -> None:
        self.warnings.append((code, item, message))

    def report(self) -> CheckReport:
        return CheckReport(findings=tuple(sorted(self.findings)), warnings=tuple(sorted(self.warnings)))


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


def case_ids(root: Path) -> frozenset[str]:
    """The case-list ids under ``root``: the first column of ``case-list.md``; empty when the file is absent."""
    path = root / CASE_LIST
    if not path.is_file():
        return frozenset()
    return frozenset(_CASE_ID_RE.findall(path.read_text(encoding="utf-8", errors="replace")))


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise CutoverLedgerError(f"{path}: no capability ledger to check")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise CutoverLedgerError(f"{path}: not YAML ({exc})") from exc
    if not isinstance(data, dict):
        raise CutoverLedgerError(f"{path}: the ledger is not a mapping")
    return data


def _segments(lines: list[str]) -> Iterator[str]:
    """The text of every FR/AD or Parent label in a story block, up to the next label; a wrapped line continues it."""
    for idx, line in enumerate(lines):
        for label in _LABEL_RE.finditer(line):
            text = line[label.end() :]
            nxt = idx + 1
            while _NEXT_LABEL_RE.search(text) is None and nxt < len(lines):
                follow = lines[nxt].strip()
                if not follow or follow.startswith(("**", "#")):
                    break
                text = f"{text} {follow}"
                nxt += 1
            end = _NEXT_LABEL_RE.search(text)
            yield text[: end.start()] if end else text


def _span(start: int, to: str | None) -> range:
    stop = int(to) if to else start
    if stop < start or stop - start > _MAX_RANGE:
        stop = start
    return range(start, stop + 1)


def _named_caps(segment: str, default_spec: str | None) -> set[str]:
    """The ledger ids a FR/AD or Parent segment names; a bare ``CAP-n`` takes the last Spec named before it."""
    named: set[str] = set()
    context = default_spec
    for hit in _REF_RE.finditer(segment):
        if hit.group("spec") is not None:
            context = hit.group("spec")
            if hit.group("sn") is not None:
                named.update(cap_id(context, n) for n in _span(int(hit.group("sn")), hit.group("sto")))
        elif hit.group("pfx") is not None:
            prefix = hit.group("pfx")
            numbers = _span(int(hit.group("pn")), hit.group("pto"))
            if prefix == _HEADING_PREFIX:
                named.update(f"{prefix}:CAP-{n}" for n in numbers)
                continue
            context = _SHORT_PREFIX_SPEC.get(prefix, prefix)
            named.update(cap_id(context, n) for n in numbers)
        elif context is not None:
            named.update(cap_id(context, n) for n in _span(int(hit.group("n")), hit.group("to")))
    return named


def citing_stories(epics_text: str, station: str) -> dict[str, tuple[str, ...]]:
    """Each ledger id the stories of a station's ``epics.md`` name, mapped to the citing ``E.S`` keys in file order.

    A bare ``CAP-n`` with no Spec named before it on its line is the station's own Spec (``spec-<station>``).
    """
    default_spec = station if station.startswith(_STATION_PREFIX) else None
    cites: dict[str, list[str]] = {}
    lines = epics_text.splitlines()
    idx = 0
    while idx < len(lines):
        head = _STORY_RE.match(lines[idx])
        if head is None:
            idx += 1
            continue
        key = f"{head.group('epic')}.{head.group('story')}"
        end = idx + 1
        while end < len(lines) and not _BLOCK_END_RE.match(lines[end]):
            end += 1
        for segment in _segments(lines[idx + 1 : end]):
            for row_id in _named_caps(segment, default_spec):
                keys = cites.setdefault(row_id, [])
                if key not in keys:
                    keys.append(key)
        idx = end
    return {row_id: tuple(keys) for row_id, keys in cites.items()}


class _Stations:
    """Each station's citing stories and story statuses, read once per check."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._cites: dict[str, dict[str, tuple[str, ...]]] = {}
        self._statuses: dict[str, dict[str, list[str]]] = {}

    def citing(self, station: str, row_id: str) -> tuple[str, ...]:
        if station not in self._cites:
            path = self._root / _PROJECTS / station / _EPICS
            text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
            self._cites[station] = citing_stories(text, station)
        return self._cites[station].get(row_id, ())

    def status(self, station: str, story: str) -> str:
        if station not in self._statuses:
            self._statuses[station] = self._read_statuses(station)
        found = self._statuses[station].get(story, [])
        if _DONE in found:
            return _DONE
        return found[0] if found else "no ledger key"

    def _read_statuses(self, station: str) -> dict[str, list[str]]:
        path = self._root / _PROJECTS / station / _SPRINT_LEDGER
        if not path.is_file():
            return {}
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise CutoverLedgerError(f"{path}: not YAML ({exc})") from exc
        entries = data.get("development_status") if isinstance(data, dict) else None
        statuses: dict[str, list[str]] = {}
        for key, value in (entries or {}).items():
            hit = _LEDGER_KEY_RE.match(str(key))
            if hit:
                statuses.setdefault(f"{hit.group('epic')}.{hit.group('story')}", []).append(str(value))
        return statuses


# ---------------------------------------------------------------------------
# The rules
# ---------------------------------------------------------------------------


def expiry_form_problem(value: Any) -> str | None:
    """Why an expiry is not one of modes.md § Expiry's three quoted forms, or ``None`` when it is one of them."""
    if not isinstance(value, str):
        return f"expiry {value!r} is not a quoted string"
    if value == FLIP:
        return None
    if _DATE_RE.match(value):
        try:
            date.fromisoformat(value)
        except ValueError:
            return f"expiry {value!r} is not a calendar date"
        return None
    story = _STORY_EXPIRY_RE.match(value)
    if story is not None and story.group("station") in STATIONS:
        return None
    return f'expiry {value!r} is none of "<station>:<E>.<S>" (a short station key), "YYYY-MM-DD" or "flip"'


def _judge_header(data: Mapping[str, Any], out: _Out) -> None:
    for key in data:
        if key not in HEADER_KEYS:
            out.find("bad-header", _HEADER_ID, f"key {key!r} is not in schema v1")
    for key in HEADER_KEYS:
        if key not in data:
            out.find("bad-header", _HEADER_ID, f"key {key!r} is missing")
    present = [key for key in data if key in HEADER_KEYS]
    if present != [key for key in HEADER_KEYS if key in data]:
        out.find("bad-header", _HEADER_ID, f"keys out of the schema v1 order: {present}")
    for key, want in _HEADER_VALUES.items():
        if key in data and data[key] != want:
            out.find("bad-header", _HEADER_ID, f"{key} is {data[key]!r}, schema v1 has {want!r}")
    updated = data.get("updated")
    if "updated" in data and not (isinstance(updated, str) and _DATE_RE.match(updated)):
        out.find("bad-header", _HEADER_ID, f"updated {updated!r} is not a quoted YYYY-MM-DD")
    if "source_sha" in data and not isinstance(data["source_sha"], str):
        out.find("bad-header", _HEADER_ID, f"source_sha {data['source_sha']!r} is not a quoted string")


def _items(data: Mapping[str, Any], key: str, out: _Out) -> list[dict[str, Any]]:
    raw = data.get(key)
    if raw is None:
        return []
    if not isinstance(raw, list):
        out.find("bad-header", _HEADER_ID, f"{key} is not a list")
        return []
    items: list[dict[str, Any]] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
            out.find("bad-header", f"{key}[{idx}]", "not a mapping with an id")
            continue
        items.append(item)
    return items


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _judge_expiry(item_id: str, mode: Any, item: Mapping[str, Any], out: _Out, flips: list[str]) -> None:
    if "expiry" not in item or item["expiry"] in (None, ""):
        if mode == "A-only":
            out.find("a-only-without-expiry", item_id, "an A-only row carries an expiry (modes.md § Expiry)")
        return
    expiry = item["expiry"]
    problem = expiry_form_problem(expiry)
    if problem is not None:
        out.find("bad-expiry-form", item_id, problem)
    elif mode != "A-only":
        out.find("bad-expiry-form", item_id, f"expiry {expiry!r} on a {mode!r} row: an expiry is for A-only rows only")
    if expiry == FLIP:
        flips.append(item_id)


def _judge_decided(row: Mapping[str, Any], case_list: frozenset[str], out: _Out, flips: list[str]) -> None:
    row_id = row["id"]
    mode = row.get("mode")
    if mode not in MODES:
        out.find("bad-mode", row_id, f"mode {mode!r} is not one of {list(MODES)}")
    state = row.get("state")
    if state is None:
        if mode == "rebuild":
            out.find("rebuild-without-state", row_id, "a rebuild row carries a state (planned until B starts)")
    elif state not in STATES:
        out.find("bad-state", row_id, f"state {state!r} is not one of {list(STATES)}")
    elif mode != "rebuild":
        out.find("bad-state", row_id, f"state {state!r} on a {mode!r} row: a state is for rebuild rows only")
    case = row.get("case_id")
    if state == "verified-in-foundry" and not _text(case):
        out.find("verified-without-case", row_id, "verified-in-foundry names no case_id (fcl:CAP-3)")
    elif case is not None and (not _text(case) or str(case).strip() not in case_list):
        out.find("unknown-case", row_id, f"case_id {case!r} is not a case-list.md id")
    if state in FROZEN_STATES:
        frozen = row.get("frozen_paths")
        if not (isinstance(frozen, list) and frozen and all(_text(path) for path in frozen)):
            out.find("rebuilding-without-frozen-paths", row_id, f"state {state!r} names no frozen_paths")
    _judge_expiry(row_id, mode, row, out, flips)
    if row.get("launch") and mode != "rebuild":
        out.find("launch-not-rebuild", row_id, f"launch on a {mode!r} row: the Launch slice rebuilds")
    if mode == "pending":
        if _text(row.get("pending_on")):
            out.warn("mode-pending", row_id, f"waits on the operator question {row['pending_on']!r}")
        else:
            out.find("pending-without-question", row_id, "a pending row names its operator question (pending_on)")
    if row.get("defaulted") is not None:
        out.warn("defaulted-row", row_id, f"added without a decision on {row['defaulted']}; decide its mode")


def _judge_cells(cells: list[dict[str, Any]], out: _Out, flips: list[str]) -> None:
    for cell in cells:
        cell_id = cell["id"]
        mode = cell.get("mode")
        if mode != "A-only":
            out.find("bad-mode", cell_id, f"cell mode {mode!r}: a cell is A-only")
        if cell.get("expiry") in (None, ""):
            out.find("cell-without-expiry", cell_id, "a cell carries an expiry (modes.md § Rows)")
            continue
        _judge_expiry(cell_id, "A-only", cell, out, flips)


def _judge_markers(caps: Mapping[str, LiveCap], out: _Out) -> None:
    for cap in caps.values():
        if cap.marker is None:
            out.warn("no-marker", cap.id, f"{cap.path}: the heading carries no status marker")
        elif cap.marker[0] == _UNKNOWN:
            out.find("unknown-marker", cap.id, f"{cap.path}: {cap.marker[1]} is not a pinned marker form")


def _never_built(row_id: str, cap: LiveCap, stations: _Stations, out: _Out) -> None:
    cites = stations.citing(cap.station, row_id)
    statuses = [(story, stations.status(cap.station, story)) for story in cites]
    if any(status == _DONE for _, status in statuses):
        return
    live = [story for story, status in statuses if status in _LIVE_STORY]
    settles = f"B-only (carried by {', '.join(live)})" if live else "retire, marker (retired <date>: never built)"
    named = ", ".join(f"{story} ({status})" for story, status in statuses) or "none"
    out.find(
        "rebuild-never-built",
        row_id,
        f"reads (ready and no citing story of {cap.station} is done (citing: {named}); rule 7 settles it {settles}",
    )


def _judge_spec_rows(
    rows: list[dict[str, Any]],
    caps: Mapping[str, LiveCap],
    stations: _Stations,
    out: _Out,
) -> None:
    for row in rows:
        row_id = row["id"]
        mode = row.get("mode")
        cap = caps.get(row_id)
        if _ARCHIVE_PART in Path(str(row.get("path") or "")).parts:
            out.find(
                "archived-spec-row", row_id, f"{row.get('path')} is archived: the folded station row is the record"
            )
            continue
        if cap is None:
            out.find("orphan-row", row_id, "no live capability holds this id")
            continue
        if row.get("heading") != cap.heading:
            out.find("heading-drift", row_id, f"heading {row.get('heading')!r}, the Spec reads {cap.heading!r}")
        retired = cap.marker is not None and cap.marker[0] == _RETIRED
        if mode == "retire" and not retired:
            out.find("retire-without-marker", row_id, f"{cap.path}: a retire row's heading carries (retired <date>)")
        if mode != "retire" and retired:
            out.find("marker-contradicts-mode", row_id, f"{cap.path}: the heading reads retired, the row {mode!r}")
        if mode == "rebuild" and cap.marker is not None and cap.marker[0] == _READY:
            _never_built(row_id, cap, stations, out)


def _cycles(graph: Mapping[str, list[str]]) -> list[tuple[str, ...]]:
    seen: dict[str, int] = {}
    found: dict[tuple[str, ...], None] = {}
    for start in sorted(graph):
        if seen.get(start):
            continue
        seen[start] = 1
        path = [start]
        stack = [iter(graph.get(start, []))]
        while stack:
            nxt = next(stack[-1], None)
            if nxt is None:
                stack.pop()
                seen[path.pop()] = 2
                continue
            mark = seen.get(nxt, 0)
            if mark == 1:
                cycle = path[path.index(nxt) :]
                first = cycle.index(min(cycle))
                found.setdefault(tuple(cycle[first:] + cycle[:first]))
            elif mark == 0:
                seen[nxt] = 1
                path.append(nxt)
                stack.append(iter(graph.get(nxt, [])))
    return list(found)


def _judge_dependencies(rows: list[dict[str, Any]], known: set[str], out: _Out) -> None:
    graph: dict[str, list[str]] = {}
    for row in rows:
        deps = row.get("depends_on")
        if deps is None:
            continue
        if not isinstance(deps, list):
            out.find("unresolved-dependency", row["id"], f"depends_on {deps!r} is not a list of ledger ids")
            continue
        resolved: list[str] = []
        for dep in deps:
            if isinstance(dep, str) and dep in known:
                resolved.append(dep)
            else:
                out.find("unresolved-dependency", row["id"], f"depends_on {dep!r} names no ledger id")
        graph[row["id"]] = resolved
    for cycle in _cycles(graph):
        out.find("dependency-cycle", cycle[0], " -> ".join((*cycle, cycle[0])))


def check(root: Path, ledger: Path = DEFAULT_LEDGER, *, flags_path: Path | str | None = None) -> CheckReport:
    """Judge the capability ledger under ``root`` against the live Specs and ``modes.md``'s rules; write nothing.

    ``flags_path`` is the flag tree ``root_of_record`` reads, only when a row's expiry is ``flip``; ``None`` resolves
    it the way the core reader does. A ledger that is missing, not YAML or not a mapping is a
    :class:`~pyforge.steward.cutover_ledger.CutoverLedgerError`, never a report.
    """
    path = ledger if ledger.is_absolute() else root / ledger
    data = _load(path)
    out = _Out()
    _judge_header(data, out)
    rows = _items(data, "capabilities", out)
    cells = _items(data, "cells", out)
    counts = Counter(item["id"] for item in (*rows, *cells))
    for item_id, count in counts.items():
        if count > 1:
            out.find("duplicate-cap-id", item_id, f"{count} ledger entries hold this id")
    caps = {cap.id: cap for cap in live_caps(root)}
    for cap_id_ in caps:
        if cap_id_ not in counts:
            out.find("unclassified", cap_id_, f"{caps[cap_id_].path}: a live capability with no ledger row")
    _judge_markers(caps, out)
    _judge_spec_rows(rows, caps, _Stations(root), out)
    flips: list[str] = []
    case_list = case_ids(root)
    for row in rows:
        _judge_decided(row, case_list, out, flips)
    _judge_cells(cells, out, flips)
    _judge_dependencies(rows, set(counts), out)
    if flips and root_of_record(flags_path).root == _FOUNDRY:
        for item_id in flips:
            out.find("flip-expiry-lapsed", item_id, "the root of record is foundry: a flip expiry has lapsed")
    return out.report()
