"""The capability-ledger source: every ledger row against its Spec, its mode and its clock.

``docs/foundry/capability-ledger.yaml`` (schema ``pyforge.capability-ledger/v1``; the one definition is
``modes.md`` § Schema v1, a companion of ``spec-foundry-capability-ledger``, written by steward Story 120.2) is
judged against the extract of its live Specs (``extract.md``, the same companion; ``spec-foundry-capability-ledger:CAP-2``,
Story 55.2). Two rules run side by side in this one source:

* **Row truth and time** (``spec-pyforge-doctor:CAP-95``, Story 56.2; the mechanism of
  ``spec-foundry-capability-ledger:CAP-2`` and ``spec-foundry-capability-ledger:CAP-4``). Each row of
  ``capabilities``: an id no live capability holds is FAIL ``orphan-row``; a ``heading`` other than the one
  ``extract_caps`` reads is FAIL ``heading-drift``; a ``path`` under ``archive/`` is FAIL ``archived-spec-row``; a
  ``mode`` of ``pending`` is one WARN (``mode-pending``) and one outside rebuild, retire, A-only and B-only
  (``spec-foundry-capability-ledger:CAP-1``) FAIL ``bad-mode``. Every ``A-only`` row and ``A-only`` ``cells:``
  entry is judged by its expiry, with an injected clock: a date 30 days ahead or less WARNs ``a-only-expiring``
  and one already past FAILs ``a-only-expired``; a Story expiry, the quoted, qualified ``"<station>:<E>.<S>"``,
  resolves against that station's ``sprint-status-ledger.yaml`` key prefix ``<E>-<S>-`` and FAILs when the key is
  ``done`` (``a-only-expiry-lapsed``) or absent (``a-only-expiry-unresolved``), as does a string of no known form,
  a bare ``<E>.<S>`` included; ``"flip"`` FAILs once ``pyforge.core.cutover_root.root_of_record`` reads the root
  of record as ``foundry`` (``a-only-expiry-flipped``) -- this source only reports after the flag reads foundry,
  it never decides when the flag flips -- and a flag tree that raises ``CutoverRootError`` is one cannot-evaluate
  WARN for the ``flip`` rows only; a value that is not a quoted string FAILs ``a-only-expiry-unquoted`` (YAML reads
  an unquoted ``44.10`` as the number ``44.1``). A row's form (``bad-expiry-form``, ``bad-state``,
  ``rebuilding-without-frozen-paths``) is steward's control-plane validator's to judge, so this source never
  judges a row's ``state`` and never reads the header's ``states:``.
* **The post-PIN rule and the verified claims** (``spec-pyforge-doctor:CAP-87``, Story 35.1, unchanged): an
  unclassified live ``CAP-N`` and ``A-only`` without an expiry are HARD, as is a ``verified-in-foundry`` claim
  without a 54.1 case-list id; ``--append`` (WARN) names a live capability, or a live Spec with no ledger row,
  added after the ledger ``source_sha``. For heading, Spec, mode and expiry the HARD findings point at
  ``spec-pyforge-doctor:CAP-95``.

A missing ledger, or one with no ``capabilities`` list, is one cannot-evaluate WARN (``capability-ledger-unevaluable``,
evidence ``unevaluable: true``), never an OK (``spec-pyforge-doctor:AD-15``).

The inventory is an extract, not a document: each capability heading plus its first intent and success lines.
Do not inventory through Scribe's text-file node helper or a truncated SPEC prefix.

Read-only and independent (``spec-pyforge-doctor:AD-1``, ``spec-pyforge-doctor:AD-11``): the ledger, the Specs, the
case list, each station's ``sprint-status-ledger.yaml`` and the flag tree are read as data; the one git read goes
through ``cli_bridge.run_git``; no station package is imported and ``steward cutover plan`` is never invoked.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any, NamedTuple

import yaml
from pyforge.core.cutover_root import LOCAL_DEV_RELATIVE, CutoverRootError, root_of_record

from ..cli_bridge import CliBridgeError, run_git
from ..models import UNEVALUABLE_EVIDENCE_KEY, DoctorStatus, Finding, Source
from . import degrade_on_exception

__all__ = (
    "UNIQUE_WHY_FIXTURE_SENTENCE",
    "CapHeading",
    "extract_caps",
    "gather",
    "iter_live_specs",
    "load_case_list_ids",
    "parse_case_list_ids",
)

_CHECK = "capability-ledger"
#: ``spec-pyforge-doctor:AD-15``'s ``<source>-unevaluable`` check for a cannot-evaluate WARN.
_CHECK_UNEVALUABLE = f"{_CHECK}-unevaluable"
_LIVE_STATUSES = frozenset({"ready", "in-progress"})
_LEDGER = Path("docs") / "foundry" / "capability-ledger.yaml"
_LEDGER_SHOWN = "docs/foundry/capability-ledger.yaml"
# extract.md § Scope: the station Specs and the governance Specs; nothing under archive/ is read.
_SPEC_GLOBS: tuple[str, ...] = (
    "_bmad-output/projects/*/planning-artifacts/specs/spec-*/SPEC.md",
    "docs/governance/spec-*/SPEC.md",
)
_ARCHIVE = "archive"
_CASE_LIST = (
    Path("_bmad-output")
    / "projects"
    / "pyforge-steward"
    / "planning-artifacts"
    / "specs"
    / "spec-foundry-regenerate-not-fold"
    / "case-list.md"
)
_CASE_ID_RE = re.compile(r"^\|\s*(k-[a-z0-9-]+)\s*\|", re.MULTILINE)
_FRAME_CLAIM_RE = re.compile(r"(?:docs/foundry/frames/|\.frame\.md)", re.IGNORECASE)

# Story 55.2 AC-1: fixture Why text the extract must drop.
UNIQUE_WHY_FIXTURE_SENTENCE = "UNIQUE_WHY_55_2_the-capability-section-must-survive-this-sentence"

# extract.md § Heading forms: after optional indentation and one `-` or `*` bullet, a bold capability number --
# `**CAP-n — title**` and `**pap:CAP-n — title**` (title inside the bold) or `**CAP-n**` (title after the dash).
_HEADING_RE = re.compile(
    r"^[ \t]*(?:[-*][ \t]+)?\*\*(?:(?P<prefix>pap):)?CAP-(?P<n>\d+)"
    r"(?:[ \t]+[—–-][ \t]*(?P<title>.+?)\*\*(?P<tail>.*)|\*\*(?P<rest>.*))$"
)
_PLAIN_DASH_RE = re.compile(r"^[ \t]*[—–-][ \t]*(?P<title>.*)$")
# The marker and anything after the bold are not part of the heading: a plain title ends at `←` or at a
# parenthesised status word (modes.md § Marker tokens).
_STATUS_WORDS: tuple[str, ...] = ("ready", "shipped", "retired", "minted", "unbuilt", "deleted", "never built")
_PLAIN_TITLE_END_RE = re.compile(
    r"←|\(\s*(?:" + "|".join(re.escape(word) for word in _STATUS_WORDS) + r")\b",
    re.IGNORECASE,
)
_SECTION_RE = re.compile(r"^#{1,6}[ \t]")
_INTENT_RE = re.compile(r"^\s*[-*]?\s*\*\*intent:\*\*\s*(.+)$", re.IGNORECASE)
_SUCCESS_RE = re.compile(r"^\s*[-*]?\s*\*\*success:\*\*\s*(.+)$", re.IGNORECASE)
# extract.md § Id rule: the three cutover Specs carry a short prefix; `pap:` only for a heading written with it.
_CUTOVER_PREFIXES: dict[str, str] = {
    "python-foundry-cutover": "fnd",
    "foundry-regenerate-not-fold": "fnr",
    "foundry-capability-ledger": "fcl",
}

# spec-foundry-capability-ledger:CAP-1: the four destinations; `pending` is a placeholder, one WARN.
_MODES = frozenset({"rebuild", "retire", "A-only", "B-only"})
_PENDING = "pending"
_A_ONLY = "A-only"

# modes.md § Expiry: three forms, each a quoted string.
_FLIP = "flip"
_FOUNDRY = "foundry"
_DONE = "done"
_EXPIRING_DAYS = 30
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_STORY_EXPIRY_RE = re.compile(r"^(?P<station>[a-z]+):(?P<epic>\d+)\.(?P<story>\d+)$")
_SPRINT_LEDGER = Path("planning-artifacts") / "sprint-status-ledger.yaml"


class CapHeading(NamedTuple):
    """One capability heading of a Spec (extract.md § What is taken): never the Why or the body."""

    n: int
    heading: str
    intent: str
    success: str
    prefix: str = ""


@dataclass(frozen=True)
class CapExtract:
    spec: str
    cap_n: int
    heading: str
    intent: str
    success: str
    path: str
    cite_id: str


class _Unevaluable(Exception):
    """The ledger cannot be read as a ledger -- one cannot-evaluate WARN, never an OK."""


def _normalise(title: str) -> str:
    # extract.md § Heading forms: strip whitespace, then a trailing `.`, then a trailing `*`, then whitespace.
    return title.strip().rstrip(".").rstrip("*").strip()


def _plain_title(rest: str) -> str:
    dash = _PLAIN_DASH_RE.match(rest)
    if dash is None:
        return ""
    title = dash.group("title")
    end = _PLAIN_TITLE_END_RE.search(title)
    return _normalise(title[: end.start()] if end else title)


def _first(rx: re.Pattern[str], lines: list[str]) -> str:
    for line in lines:
        hit = rx.match(line)
        if hit:
            return hit.group(1).strip()
    return ""


def extract_caps(text: str) -> list[CapHeading]:
    """The capability headings of ``text`` in file order, each with its first intent and success line.

    Stores heading + the following intent/success lines only, before the next heading or section. Why,
    Non-goals, and Assumptions are not kept. The first heading of a number (and prefix) wins.
    """
    lines = text.splitlines()
    hits = [(idx, hit) for idx, line in enumerate(lines) if (hit := _HEADING_RE.match(line))]
    rows: list[CapHeading] = []
    seen: set[tuple[str, int]] = set()
    for pos, (idx, hit) in enumerate(hits):
        prefix = hit.group("prefix") or ""
        n = int(hit.group("n"))
        if (prefix, n) in seen:
            continue
        seen.add((prefix, n))
        end = hits[pos + 1][0] if pos + 1 < len(hits) else len(lines)
        block = lines[idx + 1 : end]
        for offset, line in enumerate(block):
            if _SECTION_RE.match(line):
                block = block[:offset]
                break
        if hit.group("title") is not None:
            heading = _normalise(hit.group("title"))
        else:
            heading = _plain_title(hit.group("rest"))
        rows.append(CapHeading(n, heading, _first(_INTENT_RE, block), _first(_SUCCESS_RE, block), prefix))
    return rows


def _frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.rstrip() == "---":
            return fields
        if ":" not in line or line[:1] in {" ", "-", "#"}:
            continue
        key, _, value = line.partition(":")
        # extract.md § Scope: a trailing `# comment` is ignored, so `status: ready   # note` is `ready`.
        value = re.sub(r"\s+#.*$", "", value).strip().strip("'\"")
        if value and not value.startswith(("[", "|", "{")):
            fields[key.strip()] = value
    return {}


def _cite_id(spec: str, cap_n: int, prefix: str = "") -> str:
    """extract.md § Id rule: ``fnd``/``fnr``/``fcl`` for the cutover Specs, ``pap`` only for a prefixed heading,
    else ``<spec>:CAP-n`` with ``<spec>`` the Spec folder name without ``spec-``."""
    if spec in _CUTOVER_PREFIXES:
        return f"{_CUTOVER_PREFIXES[spec]}:CAP-{cap_n}"
    if prefix:
        return f"{prefix}:CAP-{cap_n}"
    return f"{spec}:CAP-{cap_n}"


def iter_live_specs(target: Path) -> list[CapExtract]:
    """Walk the ready/in-progress ``SPEC.md`` files of extract.md § Scope, by path, and extract their CAPs."""
    found: dict[str, Path] = {}
    for pattern in _SPEC_GLOBS:
        for hit in target.glob(pattern):
            if _ARCHIVE in hit.relative_to(target).parts or not hit.is_file():
                continue
            found[hit.relative_to(target).as_posix()] = hit
    rows: list[CapExtract] = []
    for rel, path in sorted(found.items()):
        text = path.read_text(encoding="utf-8", errors="replace")
        if _frontmatter(text).get("status") not in _LIVE_STATUSES:
            continue
        spec = path.parent.name.removeprefix("spec-")
        for cap in extract_caps(text):
            rows.append(
                CapExtract(
                    spec=spec,
                    cap_n=cap.n,
                    heading=cap.heading,
                    intent=cap.intent,
                    success=cap.success,
                    path=rel,
                    cite_id=_cite_id(spec, cap.n, cap.prefix),
                )
            )
    return rows


def _load_ledger(target: Path) -> dict[str, Any]:
    path = target / _LEDGER
    if not path.is_file():
        raise _Unevaluable("is missing")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise _Unevaluable(f"cannot be read ({type(exc).__name__})") from exc
    if not isinstance(data, dict):
        raise _Unevaluable(f"is not a mapping (got {type(data).__name__})")
    return data


def parse_case_list_ids(text: str) -> frozenset[str]:
    """54.1 case-list ids — first column of the thin-oracle table."""
    return frozenset(_CASE_ID_RE.findall(text))


def load_case_list_ids(target: Path) -> frozenset[str]:
    path = target / _CASE_LIST
    if not path.is_file():
        return frozenset()
    return parse_case_list_ids(path.read_text(encoding="utf-8", errors="replace"))


def _claim_verified(row: dict) -> bool:
    state = str(row.get("state") or "").strip()
    if state == "verified-in-foundry":
        return True
    flag = row.get("verified_in_foundry")
    if flag is True:
        return True
    if isinstance(flag, str) and flag.strip():
        return True
    return False


def _claim_case_id(row: dict) -> str:
    for key in ("case_id", "case-list", "case_list_id"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    flag = row.get("verified_in_foundry")
    if isinstance(flag, str) and flag.strip():
        return flag.strip()
    return ""


def _added_after_pin(target: Path, pin_sha: str) -> set[str]:
    if not pin_sha:
        return set()
    try:
        out = run_git(
            target,
            ["diff", "--name-only", "--diff-filter=A", f"{pin_sha}..HEAD"],
        )
    except CliBridgeError, UnicodeDecodeError:
        return set()
    return {line.strip().replace("\\", "/") for line in out.splitlines() if line.strip()}


def _finding(
    status: DoctorStatus,
    message: str,
    evidence: dict,
) -> Finding:
    return Finding(
        source=Source.CAPABILITY_LEDGER,
        check=_CHECK,
        status=status,
        message=message,
        evidence=evidence,
    )


def _unevaluable(message: str, **evidence: object) -> Finding:
    return Finding(
        source=Source.CAPABILITY_LEDGER,
        check=_CHECK_UNEVALUABLE,
        status=DoctorStatus.WARN,
        message=f"{message} -- the capability ledger cannot be evaluated",
        evidence={"ledger": _LEDGER_SHOWN, **evidence, UNEVALUABLE_EVIDENCE_KEY: True},
    )


def _item_id(item: dict) -> str:
    # `or`, not a `.get` default: an `id: null` row would stringify to the text "None".
    return str(item.get("id") or "<no id>")


class _StationLedgers:
    """Each station's ``sprint-status-ledger.yaml`` ``development_status``, read once, as data."""

    def __init__(self, target: Path) -> None:
        self._target = target
        self._keys: dict[str, dict[str, str]] = {}

    def _load(self, station: str) -> dict[str, str]:
        if station not in self._keys:
            path = self._target / "_bmad-output" / "projects" / f"pyforge-{station}" / _SPRINT_LEDGER
            keys: dict[str, str] = {}
            if path.is_file():
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
                status = data.get("development_status") if isinstance(data, dict) else None
                if isinstance(status, dict):
                    keys = {str(key): str(value).strip() for key, value in status.items()}
            self._keys[station] = keys
        return self._keys[station]

    def status(self, station: str, epic: str, story: str) -> str | None:
        """The status of the key with prefix ``<E>-<S>-`` in ``station``'s ledger; ``None`` when there is none."""
        prefix = f"{epic}-{story}-"
        for key, value in self._load(station).items():
            if key.startswith(prefix):
                return value
        return None


def _expiry_findings(
    item_id: str,
    item: dict,
    today: date,
    stations: _StationLedgers,
    flips: list[str],
) -> list[Finding]:
    """Judge one ``A-only`` row's or cell's expiry by its form (modes.md § Expiry) against ``today``."""
    expiry = item.get("expiry")
    base = {"id": item_id, "expiry": expiry}
    if expiry is None or (isinstance(expiry, str) and not expiry.strip()):
        return [
            _finding(DoctorStatus.FAIL, f"{item_id}: A-only without expiry", {"kind": "undated-a-only", "id": item_id})
        ]
    if not isinstance(expiry, str):
        return [
            _finding(
                DoctorStatus.FAIL,
                f"{item_id}: expiry {expiry!r} is not a quoted string (YAML read it as {type(expiry).__name__})",
                {**base, "kind": "a-only-expiry-unquoted"},
            )
        ]
    text = expiry
    if text == _FLIP:
        flips.append(item_id)
        return []
    if _DATE_RE.match(text):
        due: date | None
        try:
            due = date.fromisoformat(text)
        except ValueError:
            due = None
        if due is not None:
            days = (due - today).days
            if days < 0:
                return [
                    _finding(
                        DoctorStatus.FAIL,
                        f"{item_id}: A-only expiry {text} passed {-days} day(s) ago",
                        {**base, "kind": "a-only-expired", "days": days},
                    )
                ]
            if days <= _EXPIRING_DAYS:
                return [
                    _finding(
                        DoctorStatus.WARN,
                        f"{item_id}: A-only expiry {text} is {days} day(s) away",
                        {**base, "kind": "a-only-expiring", "days": days},
                    )
                ]
            return []
    story = _STORY_EXPIRY_RE.match(text)
    if story is not None:
        status = stations.status(story.group("station"), story.group("epic"), story.group("story"))
        if status == _DONE:
            return [
                _finding(
                    DoctorStatus.FAIL,
                    f"{item_id}: A-only expiry {text} has lapsed -- that Story is done",
                    {**base, "kind": "a-only-expiry-lapsed", "status": status},
                )
            ]
        if status is not None:
            return []
        reason = f"no key {story.group('epic')}-{story.group('story')}- in pyforge-{story.group('station')}'s ledger"
    else:
        reason = 'not "<station>:<E>.<S>", "YYYY-MM-DD" or "flip"'
    return [
        _finding(
            DoctorStatus.FAIL,
            f"{item_id}: A-only expiry {text!r} does not resolve ({reason})",
            {**base, "kind": "a-only-expiry-unresolved"},
        )
    ]


def _row_findings(row: dict, row_id: str, caps: dict[str, CapExtract]) -> list[Finding]:
    """``spec-pyforge-doctor:CAP-95``'s truth checks for one ``capabilities`` row: Spec, heading, path, mode."""
    found: list[Finding] = []
    path = str(row.get("path") or "").replace("\\", "/")
    if _ARCHIVE in PurePosixPath(path).parts:
        found.append(
            _finding(
                DoctorStatus.FAIL,
                f"{row_id}: {path} is under archive/ -- the folded station row is the record",
                {"kind": "archived-spec-row", "id": row_id, "path": path},
            )
        )
    else:
        cap = caps.get(row_id)
        if cap is None:
            found.append(
                _finding(
                    DoctorStatus.FAIL,
                    f"{row_id}: no capability of a live Spec holds this id",
                    {"kind": "orphan-row", "id": row_id, "path": path},
                )
            )
        elif row.get("heading") != cap.heading:
            found.append(
                _finding(
                    DoctorStatus.FAIL,
                    f"{row_id}: heading {row.get('heading')!r}, the Spec reads {cap.heading!r}",
                    {
                        "kind": "heading-drift",
                        "id": row_id,
                        "heading": row.get("heading"),
                        "spec_heading": cap.heading,
                        "path": cap.path,
                    },
                )
            )
    mode = row.get("mode")
    if mode == _PENDING:
        found.append(
            _finding(
                DoctorStatus.WARN,
                f"{row_id}: mode pending -- the row waits on an operator question",
                {"kind": "mode-pending", "id": row_id, "pending_on": row.get("pending_on")},
            )
        )
    elif not (isinstance(mode, str) and mode in _MODES):
        found.append(
            _finding(
                DoctorStatus.FAIL,
                f"{row_id}: mode {mode!r} is not one of rebuild, retire, A-only, B-only",
                {"kind": "bad-mode", "id": row_id, "mode": mode},
            )
        )
    return found


def _verified_findings(row: dict, row_id: str, case_ids: frozenset[str]) -> list[Finding]:
    if not _claim_verified(row):
        return []
    case_id = _claim_case_id(row)
    if not case_id:
        return [
            _finding(
                DoctorStatus.FAIL,
                f"{row_id}: verified-in-foundry without a case-list id",
                {"kind": "verified-missing-case", "id": row_id},
            )
        ]
    if _FRAME_CLAIM_RE.search(case_id) or case_id not in case_ids:
        return [
            _finding(
                DoctorStatus.FAIL,
                f"{row_id}: verified-in-foundry {case_id!r} is not a 54.1 case-list id",
                {"kind": "verified-unknown-case", "id": row_id, "case_id": case_id},
            )
        ]
    return []


def _flip_findings(target: Path, flips: list[str]) -> list[Finding]:
    """A ``flip`` expiry lapses once the root of record reads ``foundry``; read only when a ``flip`` row exists."""
    if not flips:
        return []
    try:
        root = root_of_record(target / LOCAL_DEV_RELATIVE).root
    except CutoverRootError as exc:
        return [
            _unevaluable(f"the root of record cannot be read for {len(flips)} flip expiry row(s): {exc}", ids=flips)
        ]
    if root != _FOUNDRY:
        return []
    return [
        _finding(
            DoctorStatus.FAIL,
            f"{item_id}: A-only expiry 'flip' has lapsed -- the root of record is foundry",
            {"kind": "a-only-expiry-flipped", "id": item_id, "expiry": _FLIP, "root": root},
        )
        for item_id in flips
    ]


def _gather(target: Path, today: date) -> tuple[Finding, ...]:
    try:
        ledger = _load_ledger(target)
    except _Unevaluable as exc:
        return (_unevaluable(f"{_LEDGER_SHOWN} {exc}"),)

    rows = ledger.get("capabilities")
    if not isinstance(rows, list):
        return (_unevaluable(f"{_LEDGER_SHOWN} has no `capabilities` list"),)

    pin = str(ledger.get("source_sha") or "")
    added = _added_after_pin(target, pin)
    extracted = iter_live_specs(target)
    caps: dict[str, CapExtract] = {}
    for cap in extracted:
        caps.setdefault(cap.cite_id, cap)  # extract.md: the first holder of an id wins (Specs by path)
    findings: list[Finding] = []
    case_ids = load_case_list_ids(target)
    stations = _StationLedgers(target)
    flips: list[str] = []

    for row in rows:
        if not isinstance(row, dict):
            continue
        row_id = _item_id(row)
        findings.extend(_row_findings(row, row_id, caps))
        if row.get("mode") == _A_ONLY:
            findings.extend(_expiry_findings(row_id, row, today, stations, flips))
        findings.extend(_verified_findings(row, row_id, case_ids))

    cells = ledger.get("cells")
    for cell in cells if isinstance(cells, list) else []:
        if isinstance(cell, dict) and cell.get("mode") == _A_ONLY:
            findings.extend(_expiry_findings(_item_id(cell), cell, today, stations, flips))
    findings.extend(_flip_findings(target, flips))

    row_ids = {str(row.get("id")) for row in rows if isinstance(row, dict) and row.get("id")}
    classified_paths: set[str] = set()
    for row in rows:
        if isinstance(row, dict) and row.get("path"):
            classified_paths.add(str(row["path"]).replace("\\", "/"))

    for cap in caps.values():
        if cap.cite_id in row_ids:
            continue
        evidence = {
            "kind": "unclassified",
            "id": cap.cite_id,
            "spec": cap.spec,
            "path": cap.path,
            "heading": cap.heading,
            "intent": cap.intent,
            "success": cap.success,
        }
        if cap.path in added:
            findings.append(
                _finding(
                    DoctorStatus.WARN,
                    f"{cap.cite_id}: post-PIN unclassified --append",
                    {**evidence, "kind": "append"},
                )
            )
        else:
            findings.append(
                _finding(
                    DoctorStatus.FAIL,
                    f"{cap.cite_id}: unclassified CAP-N",
                    evidence,
                )
            )

    for path in sorted(added):
        if not path.endswith("/SPEC.md"):
            continue
        if "/planning-artifacts/specs/" not in path:
            continue
        # A non-live Spec (absorbed, draft, shipped, no status) has no extract to
        # classify, so its warning could never be cleared. Same test as
        # ``iter_live_specs``; a path gone from the working tree is not live. Any
        # other read error is not "gone", so it reaches ``degrade_on_exception``.
        try:
            text = (target / path).read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError, NotADirectoryError:
            continue
        if _frontmatter(text).get("status") not in _LIVE_STATUSES:
            continue
        if path in classified_paths:
            continue
        if any(cap.path == path for cap in extracted):
            continue
        findings.append(
            _finding(
                DoctorStatus.WARN,
                f"{path}: post-PIN Spec without a ledger row --append",
                {"kind": "append", "path": path},
            )
        )

    if findings:
        return tuple(findings)

    stored = [f"{cap.cite_id}:{cap.intent}:{cap.success}" for cap in extracted]
    return (
        _finding(
            DoctorStatus.OK,
            f"{len(caps)} live CAP extract(s) match the ledger's {len(rows)} row(s)",
            {"checked": len(caps), "rows": len(rows), "stored": stored},
        ),
    )


def gather(target: Path, *, today: date | None = None) -> tuple[Finding, ...]:
    """Judge ``docs/foundry/capability-ledger.yaml`` under ``target`` against its live Specs, its modes and its
    expiry clock (``spec-pyforge-doctor:CAP-95`` beside ``spec-pyforge-doctor:CAP-87``).

    ``today`` is the injected clock the date expiries are judged against (``date.today()`` when omitted). The outer
    ``degrade_on_exception`` net folds anything raised into one WARN.
    """
    clock = today if today is not None else date.today()
    return degrade_on_exception(Source.CAPABILITY_LEDGER, _CHECK, lambda: _gather(target, clock))
