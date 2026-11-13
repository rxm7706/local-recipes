"""The capability ledger's generator (Story 121.1; spec-python-foundry-cutover fnd:CAP-9, spec-foundry-capability-ledger
fcl:CAP-1).

Derives the rows of ``docs/foundry/capability-ledger.yaml`` from the live Specs and keeps every decided field. The
inventory is ``extract.md`` and the shape is ``modes.md`` section *Schema v1*, both companions of
``spec-foundry-capability-ledger``; this module restates neither, it follows them:

* ``live_specs(root)`` reads ``_bmad-output/projects/*/planning-artifacts/specs/spec-*/SPEC.md`` and
  ``docs/governance/spec-*/SPEC.md``, parses each frontmatter as YAML (so ``status: ready   # note`` is ``ready``) and
  keeps status ``ready`` or ``in-progress``. Nothing under ``archive/`` is read.
* ``extract_caps(text)`` takes the capability heading lines (``**CAP-n — title**``, ``**CAP-n** — title``,
  ``**pap:CAP-n — title**``), normalises each heading the way doctor's ``extract_caps`` does, and keeps the line's
  tail for ``marker``.
* ``cap_id(spec, n, prefix)`` is the id rule; ``marker(line)`` reads the status token on a heading line.
* ``regenerate(root, ledger)`` rewrites the derived fields and keeps the decided ones, re-modes a row to ``retire``
  where its Spec's marker reads retired, drops a row with no live capability, adds a missing row as ``rebuild``,
  ``planned``, ``defaulted: <today>``, and keeps ``cells:``. ``append(root, ledger)`` only adds missing rows, the same
  way. Both write deterministic YAML and leave the file byte-identical when nothing changed.

The functions take no flag: ``steward cutover plan`` (Story 121.2) reads the kill switch
``pyforge.steward.cutover_ledger_write`` before it calls either write mode. The written rules and ``check()`` are Story
121.6's module (``cutover_ledger_check.py``).
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from pyforge.core.atomic_write import atomic_write_text

__all__ = (
    "CUTOVER_PREFIXES",
    "DEFAULTED_ROW",
    "DEFAULT_LEDGER",
    "EXTRACT_PATH",
    "FROZEN_STATES",
    "GENERATED_BY",
    "HEADER_KEYS",
    "LIVE_STATUSES",
    "MODES",
    "ORPHAN_DROPPED",
    "REMODED_BY_MARKER",
    "ROW_KEYS",
    "SCHEMA",
    "SPEC_GLOBS",
    "STATES",
    "STATUS_WORDS",
    "CapHeading",
    "CutoverLedgerError",
    "LedgerReport",
    "LiveCap",
    "LiveSpec",
    "append",
    "cap_id",
    "extract_caps",
    "live_caps",
    "live_specs",
    "marker",
    "regenerate",
)

SCHEMA = "pyforge.capability-ledger/v1"
GENERATED_BY = "pyforge steward cutover plan"
DEFAULT_LEDGER = Path("docs/foundry/capability-ledger.yaml")
EXTRACT_PATH = (
    "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/extract.md"
)
MODES: tuple[str, ...] = ("rebuild", "retire", "A-only", "B-only", "pending")
STATES: tuple[str, ...] = ("planned", "rebuilding", "verified-in-foundry", "cut")
FROZEN_STATES: tuple[str, ...] = ("rebuilding",)

# modes.md § Schema v1: the header, the row and the cell keys, in this order.
HEADER_KEYS: tuple[str, ...] = (
    "schema",
    "generated_by",
    "updated",
    "source_sha",
    "extract",
    "modes",
    "states",
    "frozen_states",
    "capabilities",
    "cells",
)
ROW_KEYS: tuple[str, ...] = (
    "id",
    "spec",
    "station",
    "heading",
    "path",
    "mode",
    "expiry",
    "state",
    "launch",
    "depends_on",
    "frozen_paths",
    "case_id",
    "pending_on",
    "defaulted",
    "note",
)
DERIVED_KEYS: tuple[str, ...] = ("id", "spec", "station", "heading", "path")
CELL_KEYS: tuple[str, ...] = ("id", "path", "mode", "expiry", "note")
# Decided keys bound to a mode other than retire, or to a state: a row the marker re-modes to retire loses them.
_NOT_RETIRE_KEYS: tuple[str, ...] = ("expiry", "state", "pending_on", "frozen_paths", "case_id")
# Written as double-quoted strings (an unquoted 44.10 would read back as the number 44.1, a bare date as a date).
_QUOTED_KEYS: frozenset[str] = frozenset({"updated", "source_sha", "expiry", "defaulted"})

# extract.md § Scope.
SPEC_GLOBS: tuple[str, ...] = (
    "_bmad-output/projects/*/planning-artifacts/specs/spec-*/SPEC.md",
    "docs/governance/spec-*/SPEC.md",
)
LIVE_STATUSES: frozenset[str] = frozenset({"ready", "in-progress"})
_ARCHIVE = "archive"
_GOVERNANCE_STATION = "governance"

# extract.md § Id rule: the three cutover Specs carry a short prefix; `pap` only for a prefixed heading.
CUTOVER_PREFIXES: Mapping[str, str] = {
    "python-foundry-cutover": "fnd",
    "foundry-regenerate-not-fold": "fnr",
    "foundry-capability-ledger": "fcl",
}
_HEADING_PREFIX = "pap"

# Report codes (fcl:CAP-1): what the generator did to a row.
DEFAULTED_ROW = "defaulted-row"
ORPHAN_DROPPED = "orphan-dropped"
REMODED_BY_MARKER = "remoded-by-marker"

# extract.md § Heading forms. One `-` or `*` bullet after optional indentation, then the bold capability number:
# `**CAP-n — title**` / `**pap:CAP-n — title**` (title inside the bold) or `**CAP-n**` (title after the dash).
_HEADING_RE = re.compile(
    r"^[ \t]*(?:[-*][ \t]+)?\*\*(?:(?P<prefix>pap):)?CAP-(?P<n>\d+)"
    r"(?:[ \t]+[—–-][ \t]*(?P<title>.+?)\*\*(?P<tail>.*)|\*\*(?P<rest>.*))$"
)
_PLAIN_DASH_RE = re.compile(r"^[ \t]*[—–-][ \t]*(?P<title>.*)$")
_SECTION_RE = re.compile(r"^#{1,6}[ \t]")
_INTENT_RE = re.compile(r"^\s*[-*]?\s*\*\*intent:\*\*\s*(.+)$", re.IGNORECASE)
_SUCCESS_RE = re.compile(r"^\s*[-*]?\s*\*\*success:\*\*\s*(.+)$", re.IGNORECASE)

# modes.md § Marker tokens: the pinned forms, and the legacy retired form inside the bold title (fnd:CAP-7).
_PINNED_RE = re.compile(r"\((?P<word>ready|shipped|retired) (?P<date>\d{4}-\d{2}-\d{2})(?!\d)")
_LEGACY_RETIRED_RE = re.compile(r"\bRETIRED (?P<date>\d{4}-\d{2}-\d{2})(?!\d)")
# Any other parenthesised status word on a heading line is unknown (Story 121.6's `unknown-marker`).
STATUS_WORDS: tuple[str, ...] = ("ready", "shipped", "retired", "minted", "unbuilt", "deleted", "never built")
_STATUS_PAREN_RE = re.compile(
    r"\(\s*(?:" + "|".join(re.escape(word) for word in STATUS_WORDS) + r")\b[^)]*\)?",
    re.IGNORECASE,
)
_PLAIN_TITLE_END_RE = re.compile(r"←|" + _STATUS_PAREN_RE.pattern, re.IGNORECASE)
_ID_NUMBER_RE = re.compile(r"CAP-(\d+)$")


class CutoverLedgerError(ValueError):
    """A Spec frontmatter or the ledger cannot be read as the generator needs it; nothing was written."""


@dataclass(frozen=True)
class CapHeading:
    """One capability heading of a Spec (extract.md § What is taken): never the Why or the body."""

    n: int
    prefix: str
    heading: str
    line: str
    tail: str
    intent: str
    success: str


@dataclass(frozen=True)
class LiveSpec:
    """A live Spec: its repository-relative ``SPEC.md`` path, its slug, its station and its text."""

    path: str
    slug: str
    station: str
    status: str
    text: str


@dataclass(frozen=True)
class LiveCap:
    """A live capability: the derived fields of its ledger row and the marker on its heading line."""

    id: str
    spec: str
    station: str
    heading: str
    path: str
    n: int
    prefix: str
    marker: tuple[str, str] | None

    def derived(self) -> dict[str, Any]:
        return {"id": self.id, "spec": self.spec, "station": self.station, "heading": self.heading, "path": self.path}


@dataclass(frozen=True)
class LedgerReport:
    """What a write mode did. ``dropped`` holds the rows with no live capability of their own: orphans, and the second
    and later row of a repeated id."""

    changed: bool
    added: tuple[str, ...] = ()
    dropped: tuple[str, ...] = ()
    remoded: tuple[str, ...] = ()

    @property
    def events(self) -> tuple[tuple[str, str], ...]:
        return (
            tuple((DEFAULTED_ROW, row_id) for row_id in self.added)
            + tuple((ORPHAN_DROPPED, row_id) for row_id in self.dropped)
            + tuple((REMODED_BY_MARKER, row_id) for row_id in self.remoded)
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "changed": self.changed,
            "added": list(self.added),
            "dropped": list(self.dropped),
            "remoded": list(self.remoded),
        }


# ---------------------------------------------------------------------------
# The extract
# ---------------------------------------------------------------------------


def _normalise(title: str) -> str:
    # extract.md § Heading forms: doctor's normalisation, byte for byte.
    return title.strip().rstrip(".").rstrip("*").strip()


def _plain_title(rest: str) -> str:
    dash = _PLAIN_DASH_RE.match(rest)
    if dash is None:
        return ""
    title = dash.group("title")
    end = _PLAIN_TITLE_END_RE.search(title)
    return _normalise(title[: end.start()] if end else title)


def _first(rx: re.Pattern[str], lines: Iterable[str]) -> str:
    for line in lines:
        hit = rx.match(line)
        if hit:
            return hit.group(1).strip()
    return ""


def extract_caps(text: str) -> tuple[CapHeading, ...]:
    """The capability headings of a Spec's text, in file order; the first heading of a number wins."""
    lines = text.splitlines()
    hits: list[tuple[int, re.Match[str]]] = []
    for idx, line in enumerate(lines):
        hit = _HEADING_RE.match(line)
        if hit:
            hits.append((idx, hit))
    caps: list[CapHeading] = []
    seen: set[tuple[str, int]] = set()
    for pos, (idx, hit) in enumerate(hits):
        prefix = hit.group("prefix") or ""
        n = int(hit.group("n"))
        end = hits[pos + 1][0] if pos + 1 < len(hits) else len(lines)
        block = lines[idx + 1 : end]
        for offset, line in enumerate(block):
            if _SECTION_RE.match(line):
                block = block[:offset]
                break
        if (prefix, n) in seen:
            continue
        seen.add((prefix, n))
        if hit.group("title") is not None:
            heading = _normalise(hit.group("title"))
            tail = hit.group("tail")
        else:
            heading = _plain_title(hit.group("rest"))
            tail = hit.group("rest")
        caps.append(
            CapHeading(
                n=n,
                prefix=prefix,
                heading=heading,
                line=lines[idx],
                tail=tail,
                intent=_first(_INTENT_RE, block),
                success=_first(_SUCCESS_RE, block),
            )
        )
    return tuple(caps)


def cap_id(spec: str, n: int, prefix: str = "") -> str:
    """extract.md § Id rule: ``fnd``/``fnr``/``fcl`` for the cutover Specs, ``pap`` only for a prefixed heading, else
    ``<spec>:CAP-n``."""
    if prefix not in ("", _HEADING_PREFIX):
        raise ValueError(f"no short prefix {prefix!r}: only a {_HEADING_PREFIX}: heading carries one")
    if spec in CUTOVER_PREFIXES:
        return f"{CUTOVER_PREFIXES[spec]}:CAP-{n}"
    if prefix:
        return f"{prefix}:CAP-{n}"
    return f"{spec}:CAP-{n}"


def marker(line: str) -> tuple[str, str] | None:
    """The status a heading line carries (modes.md § Marker tokens).

    ``('ready'|'shipped'|'retired', date)`` for a pinned form after the bold title (or the legacy ``RETIRED date``
    inside it); ``('unknown', text)`` for any other parenthesised status word; ``None`` when the line carries none.
    A pinned form anywhere on the line wins over an unknown one before it.
    """
    hit = _HEADING_RE.match(line)
    tail = line if hit is None else (hit.group("tail") if hit.group("title") is not None else hit.group("rest"))
    found: list[tuple[int, str, str]] = []
    pinned = _PINNED_RE.search(tail)
    if pinned:
        found.append((line.find(pinned.group(0)), pinned.group("word"), pinned.group("date")))
    legacy = _LEGACY_RETIRED_RE.search(line)
    if legacy:
        found.append((legacy.start(), "retired", legacy.group("date")))
    if found:
        _, word, when = min(found)
        return (word, when)
    unknown = _STATUS_PAREN_RE.search(tail)
    if unknown:
        return ("unknown", _parenthesised(tail, unknown.start()))
    return None


def _parenthesised(text: str, start: int) -> str:
    """The parenthesised group opening at ``text[start]``, nested groups included; to the end when it never closes."""
    depth = 0
    for idx in range(start, len(text)):
        if text[idx] == "(":
            depth += 1
        elif text[idx] == ")":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]
    return text[start:].strip()


def _frontmatter(text: str, rel: str) -> dict[str, Any]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    for idx in range(1, len(lines)):
        if lines[idx].rstrip() == "---":
            block = "\n".join(lines[1:idx])
            break
    else:
        return {}
    try:
        meta = yaml.safe_load(block)
    except yaml.YAMLError as exc:
        raise CutoverLedgerError(f"{rel}: frontmatter is not YAML ({exc})") from exc
    return meta if isinstance(meta, dict) else {}


def live_specs(root: Path) -> tuple[LiveSpec, ...]:
    """The live Specs under ``root`` (extract.md § Scope), ordered by path; never one under ``archive/``."""
    found: dict[str, LiveSpec] = {}
    for pattern in SPEC_GLOBS:
        for path in root.glob(pattern):
            rel = path.relative_to(root)
            if _ARCHIVE in rel.parts or not path.is_file():
                continue
            key = rel.as_posix()
            text = path.read_text(encoding="utf-8")
            status = _frontmatter(text, key).get("status")
            if not isinstance(status, str) or status.strip() not in LIVE_STATUSES:
                continue
            station = rel.parts[2] if rel.parts[0] == "_bmad-output" else _GOVERNANCE_STATION
            found[key] = LiveSpec(
                path=key,
                slug=rel.parent.name.removeprefix("spec-"),
                station=station,
                status=status.strip(),
                text=text,
            )
    return tuple(found[key] for key in sorted(found))


def live_caps(root: Path) -> tuple[LiveCap, ...]:
    """Every live capability under ``root``: Specs by path, then CAPs numeric; the first holder of an id wins."""
    caps: dict[str, LiveCap] = {}
    for spec in live_specs(root):
        for cap in extract_caps(spec.text):
            row_id = cap_id(spec.slug, cap.n, cap.prefix)
            if row_id in caps:
                continue
            caps[row_id] = LiveCap(
                id=row_id,
                spec=spec.slug,
                station=spec.station,
                heading=cap.heading,
                path=spec.path,
                n=cap.n,
                prefix=cap.prefix,
                marker=marker(cap.line),
            )
    return tuple(sorted(caps.values(), key=lambda cap: (cap.path, cap.prefix, cap.n, cap.id)))


# ---------------------------------------------------------------------------
# The ledger file
# ---------------------------------------------------------------------------


class _Quoted(str):
    pass


class _Flow(list[str]):
    pass


class _Dumper(yaml.SafeDumper):
    """Block style with indented sequences, quoted scalars where the schema asks for strings."""

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        super().increase_indent(flow, False)


def _represent_quoted(dumper: yaml.SafeDumper, value: _Quoted) -> yaml.ScalarNode:
    return dumper.represent_scalar("tag:yaml.org,2002:str", str(value), style='"')


def _represent_flow(dumper: yaml.SafeDumper, value: _Flow) -> yaml.SequenceNode:
    return dumper.represent_sequence("tag:yaml.org,2002:seq", list(value), flow_style=True)


_Dumper.add_representer(_Quoted, _represent_quoted)
_Dumper.add_representer(_Flow, _represent_flow)


def _as_text(value: Any) -> str:
    return value.isoformat() if isinstance(value, date) else str(value)


def _ordered(item: Mapping[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in (*keys, *sorted(k for k in item if k not in keys)):
        if key not in item or item[key] is None:
            continue
        value = item[key]
        out[key] = _Quoted(_as_text(value)) if key in _QUOTED_KEYS else value
    return out


def _row_sort_key(row: Mapping[str, Any]) -> tuple[str, str, int, str]:
    row_id = str(row.get("id", ""))
    number = _ID_NUMBER_RE.search(row_id)
    prefix = _HEADING_PREFIX if row_id.startswith(f"{_HEADING_PREFIX}:") else ""
    return (str(row.get("path", "")), prefix, int(number.group(1)) if number else -1, row_id)


def _comment_block(text: str | None) -> str:
    if not text:
        return ""
    kept: list[str] = []
    for line in text.splitlines(keepends=True):
        if not line.startswith("#"):
            break
        kept.append(line if line.endswith("\n") else line + "\n")
    return "".join(kept)


def _render(
    comments: str,
    rows: list[dict[str, Any]],
    cells: list[dict[str, Any]],
    *,
    updated: str,
    source_sha: str,
) -> str:
    doc = {
        "schema": SCHEMA,
        "generated_by": GENERATED_BY,
        "updated": updated,
        "source_sha": source_sha,
        "extract": EXTRACT_PATH,
        "modes": _Flow(MODES),
        "states": _Flow(STATES),
        "frozen_states": _Flow(FROZEN_STATES),
        "capabilities": [_ordered(row, ROW_KEYS) for row in sorted(rows, key=_row_sort_key)],
        "cells": [_ordered(cell, CELL_KEYS) for cell in cells],
    }
    body = yaml.dump(
        _ordered(doc, HEADER_KEYS),
        Dumper=_Dumper,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=1_000_000,
    )
    return comments + body


def _load(ledger: Path) -> tuple[str | None, dict[str, Any]]:
    if not ledger.is_file():
        return None, {}
    text = ledger.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise CutoverLedgerError(f"{ledger}: not YAML ({exc})") from exc
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise CutoverLedgerError(f"{ledger}: the ledger is not a mapping")
    for key in ("capabilities", "cells"):
        items = data.get(key) or []
        if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
            raise CutoverLedgerError(f"{ledger}: {key} is not a list of mappings")
        data[key] = items
    for row in data["capabilities"]:
        if not isinstance(row.get("id"), str) or not row["id"]:
            raise CutoverLedgerError(f"{ledger}: a capabilities row has no id")
    return text, data


def _head_sha(root: Path) -> str:
    """The HEAD the Specs were read at, or ``""`` where ``root`` is not a git checkout."""
    try:
        result = subprocess.run(  # noqa: S603
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _new_row(cap: LiveCap, today: date) -> dict[str, Any]:
    return {**cap.derived(), "mode": "rebuild", "state": "planned", "defaulted": today.isoformat()}


def _remode(row: dict[str, Any], cap: LiveCap) -> bool:
    if cap.marker is None or cap.marker[0] != "retired" or row.get("mode") == "retire":
        return False
    row["mode"] = "retire"
    for key in _NOT_RETIRE_KEYS:
        row.pop(key, None)
    return True


def _write(
    root: Path,
    ledger: Path,
    old_text: str | None,
    data: Mapping[str, Any],
    rows: list[dict[str, Any]],
    *,
    today: date | None,
    source_sha: str | None,
) -> bool:
    comments = _comment_block(old_text)
    cells = [dict(cell) for cell in data.get("cells") or []]
    if old_text is not None:
        same = _render(
            comments,
            rows,
            cells,
            updated=_as_text(data.get("updated", "")),
            source_sha=_as_text(data.get("source_sha", "")),
        )
        if same == old_text:
            return False
    text = _render(
        comments,
        rows,
        cells,
        updated=(today or date.today()).isoformat(),
        source_sha=_head_sha(root) if source_sha is None else source_sha,
    )
    ledger.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(ledger, text)
    return True


def _resolve(root: Path, ledger: Path) -> Path:
    return ledger if ledger.is_absolute() else root / ledger


def regenerate(
    root: Path,
    ledger: Path = DEFAULT_LEDGER,
    *,
    today: date | None = None,
    source_sha: str | None = None,
) -> LedgerReport:
    """Rewrite the ledger from the live Specs under ``root`` (fnd:CAP-9).

    Derived fields come from the Specs; decided fields are kept. A row whose Spec marker reads retired becomes
    ``retire`` (``remoded-by-marker``), a row with no live capability leaves (``orphan-dropped``), a missing row joins
    as ``rebuild``/``planned``/``defaulted`` (``defaulted-row``), and ``cells:`` stays as it is.
    """
    path = _resolve(root, ledger)
    old_text, data = _load(path)
    day = today or date.today()
    caps = {cap.id: cap for cap in live_caps(root)}
    existing: dict[str, dict[str, Any]] = {}
    dropped: list[str] = []
    for row in data.get("capabilities") or []:
        row_id = row["id"]
        if row_id not in caps or row_id in existing:
            dropped.append(row_id)
            continue
        existing[row_id] = dict(row)
    rows: list[dict[str, Any]] = []
    added: list[str] = []
    remoded: list[str] = []
    for row_id, cap in caps.items():
        if row_id in existing:
            row = {**existing[row_id], **cap.derived()}
        else:
            row = _new_row(cap, day)
            added.append(row_id)
        if _remode(row, cap):
            remoded.append(row_id)
        rows.append(row)
    changed = _write(root, path, old_text, data, rows, today=day, source_sha=source_sha)
    return LedgerReport(changed=changed, added=tuple(added), dropped=tuple(dropped), remoded=tuple(remoded))


def append(
    root: Path,
    ledger: Path = DEFAULT_LEDGER,
    *,
    today: date | None = None,
    source_sha: str | None = None,
) -> LedgerReport:
    """Add the ledger rows the live Specs under ``root`` have and the ledger lacks; no other row changes.

    A new row joins as ``regenerate`` adds one; with nothing to add the file is not written.
    """
    path = _resolve(root, ledger)
    old_text, data = _load(path)
    day = today or date.today()
    rows = [dict(row) for row in data.get("capabilities") or []]
    held = {row["id"] for row in rows}
    added: list[str] = []
    remoded: list[str] = []
    for cap in live_caps(root):
        if cap.id in held:
            continue
        row = _new_row(cap, day)
        if _remode(row, cap):
            remoded.append(cap.id)
        rows.append(row)
        added.append(cap.id)
    if not added:
        return LedgerReport(changed=False)
    changed = _write(root, path, old_text, data, rows, today=day, source_sha=source_sha)
    return LedgerReport(changed=changed, added=tuple(added), remoded=tuple(remoded))
