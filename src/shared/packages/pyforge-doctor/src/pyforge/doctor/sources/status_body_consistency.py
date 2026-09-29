"""Status/body consistency gather (Stories 21.12–21.16, ``spec-status-body-consistency``).

Story 21.12 (CAP-1): under ``status: realized|shipped|done``, report body lines
that still read incomplete progress — ``N of M stories/capabilities``,
hyphenated ``N-of-M``, or bare ``N/M`` on a line that also names
stories/capabilities — with ``N < M``. Warn-only, read-only, fail-open.

Story 21.13 (CAP-2): reconcile a Spec's declared ``open_questions`` frontmatter
against its companion ``.memlog.md``'s last unclosed ``(open)`` / ``(question)``
entry. Warn-only, read-only, fail-open — reports the contradiction, never
proposes closing text.

Story 21.14 (CAP-3): bounded forward-looking-language patterns measured against
the full live tier before joining ``gather``. Fires on at most the herald
Dream+Spec pair and stays quiet elsewhere; see ``PROMISSORY_LANGUAGE_ACCEPTED``
and ``measure_promissory_language_precision``.

Story 21.15 (CAP-4): reconcile a frontmatter ``status:`` comment naming an epic or
story key against that key's live row in every tracked ``sprint-status-ledger.yaml``.
Warn-only, read-only, fail-open.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from ..models import DoctorStatus, Finding, Source
from . import degrade_on_exception

__all__ = (
    "TERMINAL_STATUSES",
    "OpenQuestionMatch",
    "OpenQuestionsScanStats",
    "PromissoryLanguageMatch",
    "PromissoryLanguageMeasurement",
    "StatusCommentRef",
    "StatusCommentScanStats",
    "TierScanStats",
    "PROMISSORY_LANGUAGE_ACCEPTED",
    "gather",
    "gather_open_questions_reconcile",
    "gather_progress_phrase",
    "gather_promissory_language",
    "gather_status_comment_reconcile",
    "iter_frontmatter_documents",
    "iter_promissory_section_surfaces",
    "iter_spec_documents",
    "iter_terminal_tier_documents",
    "last_unclosed_memlog_question",
    "load_ledger_status_index",
    "measure_promissory_language_precision",
    "open_questions_frontmatter_count",
    "parse_status_comment_references",
    "scan_body_for_incomplete_progress",
    "scan_body_for_promissory_language",
    "status_comment_text",
)

#: FALLBACK (Story 59.2) when `guild-roster.json` is unavailable -- today's
#: value, not a parallel source of truth. Live calls derive the Spec-side
#: member ("shipped") from `guild-roster.json`'s `spec_statuses_terminal` /
#: `spec_statuses_ended_acts` (`terminal - ended_acts` yields exactly
#: `{"shipped"}`) and union it with the literal `"realized"` (Dream
#: vocabulary) / `"done"` (Story vocabulary, dead for this module's own
#: inputs -- it only ever scans Dream `*.md` and `SPEC.md` files, never Story
#: files -- kept for parity with this fallback).
TERMINAL_STATUSES = frozenset({"realized", "shipped", "done"})

_GUILD_ROSTER_REL = "docs/governance/guild-roster.json"


def _load_terminal_statuses(target: Path) -> tuple[frozenset[str], Finding | None]:
    """The live terminal-status set, read fresh from ``guild-roster.json`` at
    ``target`` -- never cached at import time (mirrors
    ``factory.py::_roster`` / ``chain.py::_load_dream_roster``, the house
    pattern for this package).

    ``(spec_statuses_terminal - spec_statuses_ended_acts) | {"realized",
    "done"}`` -- the Spec-only-terminal value (``{"shipped"}``) unioned with
    the two non-CAP-1 literals ``TERMINAL_STATUSES`` always carried.

    On any read/parse/shape failure, degrades to ``TERMINAL_STATUSES`` (never
    a crash) and returns a WARN ``Finding`` for the caller to append to its
    own ``findings`` rather than degrading silently (Story 59.2, mirrors
    ``chain.py::_load_constitutive``).
    """
    try:
        data = json.loads((target / _GUILD_ROSTER_REL).read_text(encoding="utf-8"))
        raw_terminal = data["spec_statuses_terminal"]
        raw_ended_acts = data["spec_statuses_ended_acts"]
        if not isinstance(raw_terminal, list) or not isinstance(raw_ended_acts, list):
            raise TypeError("spec_statuses_terminal/spec_statuses_ended_acts must be lists")
        terminal = frozenset(str(s) for s in raw_terminal)
        ended_acts = frozenset(str(s) for s in raw_ended_acts)
    except Exception as exc:  # noqa: BLE001 -- degrade, never crash (house rule)
        return TERMINAL_STATUSES, Finding(
            source=Source.STATUS_BODY_CONSISTENCY,
            check=_CHECK_ROSTER_DEGRADED,
            status=DoctorStatus.WARN,
            message=(
                f"{_GUILD_ROSTER_REL} could not be read for the Spec-side of "
                f"TERMINAL_STATUSES ({exc.__class__.__name__}: {exc}) — "
                f"falling back to {sorted(TERMINAL_STATUSES)}"
            ),
            evidence={"path": _GUILD_ROSTER_REL},
        )
    return (terminal - ended_acts) | {"realized", "done"}, None


_CHECK_PROGRESS = "status-body-progress-phrase"
_CHECK_OPEN_QUESTIONS = "status-body-open-questions"
_CHECK_PROMISSORY = "status-body-promissory-language"
_CHECK_STATUS_COMMENT = "status-body-status-comment"
_CHECK_STATUS_COMMENT_UNRESOLVABLE = "status-body-status-comment-unresolvable"
_CHECK_UNPARSEABLE = "status-body-unparseable"
_CHECK_ROSTER_DEGRADED = "spec-status-roster-degraded"

_LEDGER_SUFFIX = "planning-artifacts/sprint-status-ledger.yaml"
_LEDGER_STATUS_WORDS = (
    "backlog",
    "done",
    "in-progress",
    "in-review",
    "blocked",
    "ready-for-dev",
    "ready",
    "review",
    "optional",
)
_LEDGER_STATUS_ALT = "|".join(re.escape(word) for word in _LEDGER_STATUS_WORDS)
_EPIC_STATUS_COMMENT_RE = re.compile(rf"(?i)(?:\b|→\s*|\->\s*)epic\s+(\d+)\s+({_LEDGER_STATUS_ALT})\b")
_STORY_STATUS_COMMENT_RE = re.compile(rf"(?i)\bstory\s+(\d+)[.\-](\d+)[a-z]?\s+({_LEDGER_STATUS_ALT})\b")

_HEADING_LINE_RE = re.compile(r"^#{1,6}\s")

# CAP-3 (Story 21.14): bounded phrases measured on the live tier — do not widen
# without re-measuring ``measure_promissory_language_precision``.
_PROMISSORY_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bactive now\b", re.IGNORECASE), "active-now"),
    (re.compile(r"\bactive, in-progress work\b", re.IGNORECASE), "in-progress-work"),
    (
        re.compile(r"\bzero stories are implemented yet\b", re.IGNORECASE),
        "zero-stories-yet",
    ),
    (
        re.compile(r"\bimmediate next build target\b", re.IGNORECASE),
        "immediate-next-build",
    ),
    (re.compile(r"\bdescribed a mid-build\b", re.IGNORECASE), "mid-build-described"),
    (
        re.compile(
            r"\bcontradicted this Spec.*[`']?status:\s*shipped[`']?",
            re.IGNORECASE,
        ),
        "contradicted-shipped-status",
    ),
    (
        re.compile(r"\bnot yet true end to end\b", re.IGNORECASE),
        "not-yet-true-end-to-end",
    ),
)

_HERALD_DREAM_REL = "docs/dreams/pyforge-herald.md"
_HERALD_SPEC_REL_SUFFIX = "pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md"

_MEMLOG_ENTRY_RE = re.compile(r"^-\s+\((\w+)")

# ``3 of 9 stories`` / ``3 of 9 capabilities``
_PROGRESS_OF_RE = re.compile(
    r"\b(\d+)\s+of\s+(\d+)\s+(?:stories|capabilities)\b",
    re.IGNORECASE,
)

# ``3-of-9`` (same semantic family as the spaced form)
_HYPHEN_OF_RE = re.compile(
    r"\b(\d+)-of-(\d+)\b",
    re.IGNORECASE,
)

# ``3/9`` only when the line also names stories or capabilities. Excludes a
# story/epic-ID pair or range glued to it on either side — ``Stories
# 20.4/20.5`` (a "." before the first digit), ``Stories 11-2/11-3`` or
# ``CAP-8/9/10`` (a "-" or a third ``/digit`` member on either side) all read
# as two dotted/hyphenated IDs or a slash-joined ID list, not a fraction,
# even though the bare digits satisfy ``n < m``.
_SLASH_RE = re.compile(r"(?<![.\-/])\b(\d+)/(\d+)\b(?!/\d)")
_SLASH_CONTEXT_RE = re.compile(r"\b(?:stories?|capabilities?)\b", re.IGNORECASE)


@dataclass(frozen=True)
class TierScanStats:
    scanned_terminal: int = 0
    silent: int = 0
    fired: int = 0


@dataclass(frozen=True)
class ProgressMatch:
    line_no: int
    line_text: str
    n: int
    m: int
    matched: str


def _parse_frontmatter(text: str) -> tuple[dict[str, object], bool]:
    """Return ``(fields, unparseable)`` for a ``---``-fenced document."""
    if not text.startswith("---"):
        if "---" in text:
            return {}, True
        return {}, False
    try:
        parts = text.split("---", 2)
        if len(parts) < 3:
            return {}, True
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return {}, True
    if data is None:
        return {}, False
    if not isinstance(data, dict):
        return {}, True
    return data, False


def _body_after_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    marker = "\n---\n"
    idx = text.find(marker, 3)
    if idx == -1:
        return ""
    return text[idx + len(marker) :]


def _normalize_status(raw: object) -> str:
    if not isinstance(raw, str):
        return ""
    status = raw.strip()
    if len(status) >= 2 and status[0] == status[-1] and status[0] in "\"'":
        status = status[1:-1]
    return status.strip()


def _match_incomplete_progress_on_line(line: str) -> list[tuple[int, int, str]]:
    """Return ``(n, m, matched_phrase)`` for every incomplete-progress hit on ``line``."""
    hits: list[tuple[int, int, str]] = []
    for match in _PROGRESS_OF_RE.finditer(line):
        n, m = int(match.group(1)), int(match.group(2))
        if n < m:
            hits.append((n, m, match.group(0)))
    for match in _HYPHEN_OF_RE.finditer(line):
        n, m = int(match.group(1)), int(match.group(2))
        if n < m:
            hits.append((n, m, match.group(0)))
    if _SLASH_CONTEXT_RE.search(line):
        for match in _SLASH_RE.finditer(line):
            n, m = int(match.group(1)), int(match.group(2))
            if n < m:
                hits.append((n, m, match.group(0)))
    return hits


def scan_body_for_incomplete_progress(body: str) -> tuple[ProgressMatch, ...]:
    """Every body line whose text reads incomplete progress with ``N < M``."""
    out: list[ProgressMatch] = []
    for line_no, line in enumerate(body.splitlines(), start=1):
        for n, m, matched in _match_incomplete_progress_on_line(line):
            out.append(
                ProgressMatch(
                    line_no=line_no,
                    line_text=line.rstrip(),
                    n=n,
                    m=m,
                    matched=matched,
                )
            )
    return tuple(out)


@dataclass(frozen=True)
class PromissoryLanguageMatch:
    line_no: int
    surface_kind: str
    pattern_id: str
    line_text: str


def iter_promissory_section_surfaces(body: str) -> tuple[tuple[int, str, str], ...]:
    """Section headings and body lines under each heading (CAP-3 scan surface)."""
    lines = body.splitlines()
    surfaces: list[tuple[int, str, str]] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if _HEADING_LINE_RE.match(line):
            surfaces.append((index + 1, "heading", line.strip()))
            next_index = index + 1
            while next_index < len(lines) and not _HEADING_LINE_RE.match(lines[next_index]):
                if lines[next_index].strip():
                    surfaces.append((next_index + 1, "section", lines[next_index].strip()))
                next_index += 1
            index = next_index
        else:
            index += 1
    return tuple(surfaces)


def scan_body_for_promissory_language(body: str) -> tuple[PromissoryLanguageMatch, ...]:
    """Bounded forward-looking phrases under section headings (Story 21.14 / CAP-3)."""
    out: list[PromissoryLanguageMatch] = []
    for line_no, surface_kind, text in iter_promissory_section_surfaces(body):
        for pattern, pattern_id in _PROMISSORY_PATTERNS:
            if pattern.search(text):
                out.append(
                    PromissoryLanguageMatch(
                        line_no=line_no,
                        surface_kind=surface_kind,
                        pattern_id=pattern_id,
                        line_text=text.rstrip(),
                    )
                )
                break
    return tuple(out)


def _is_herald_pair_path(rel: str) -> bool:
    return rel == _HERALD_DREAM_REL or rel.endswith(_HERALD_SPEC_REL_SUFFIX)


@dataclass(frozen=True)
class PromissoryLanguageMeasurement:
    scanned_terminal: int
    herald_pair_fired: int
    false_positive_documents: int
    precision: float

    @property
    def accepted(self) -> bool:
        """At most the known herald Dream+Spec pair fires, never anything
        else. ``<=`` rather than ``==`` (2026-09-14): the Spec side of the
        pair had its promissory language cleaned up after this was first
        measured (Story 21.14 ship time, both firing), dropping the live
        count to 1 -- a real improvement, not a regression, and an exact
        match would have wrongly rejected it. Precision stays 1.0 either
        way since ``false_positive_documents`` is unaffected."""
        return self.herald_pair_fired <= 2 and self.false_positive_documents == 0


def measure_promissory_language_precision(target: Path) -> PromissoryLanguageMeasurement:
    """Measure CAP-3 precision over every terminal-tier document."""
    scanned_terminal = 0
    herald_fired = 0
    false_positive_documents = 0
    # No `findings` list owned here (this returns a dataclass, not Findings) --
    # a degraded roster falls back silently; the WARN itself surfaces via
    # `gather_promissory_language`'s own top-level load when this is called
    # from its accepted path (Story 59.2).
    terminal_statuses, _roster_warning = _load_terminal_statuses(target)

    for path, status in iter_terminal_tier_documents(target, terminal_statuses):
        fm, unparseable = _parse_frontmatter(path.read_text(encoding="utf-8"))
        if unparseable:
            continue
        resolved_status = status or _normalize_status(fm.get("status"))
        if resolved_status not in terminal_statuses:
            continue

        scanned_terminal += 1
        rel = _rel_path(path, target)
        body = _body_after_frontmatter(path.read_text(encoding="utf-8"))
        if not scan_body_for_promissory_language(body):
            continue

        if _is_herald_pair_path(rel):
            herald_fired += 1
        else:
            false_positive_documents += 1

    fired_total = herald_fired + false_positive_documents
    precision = herald_fired / fired_total if fired_total else 0.0
    return PromissoryLanguageMeasurement(
        scanned_terminal=scanned_terminal,
        herald_pair_fired=herald_fired,
        false_positive_documents=false_positive_documents,
        precision=precision,
    )


# Measured at Story 21.14 ship time against the full live tier: herald Dream+Spec
# both fire, zero false positives elsewhere (document-level precision 1.0).
# Re-measured 2026-09-14: the Spec side was cleaned up and no longer fires,
# leaving only the Dream -- still zero false positives, still precision 1.0.
PROMISSORY_LANGUAGE_ACCEPTED = True


def iter_terminal_tier_documents(
    target: Path, terminal_statuses: frozenset[str] | None = None
) -> tuple[tuple[Path, str], ...]:
    """Dream ``*.md`` and ``SPEC.md`` paths whose frontmatter ``status`` is terminal.

    ``terminal_statuses`` is the live-derived (or fallback) terminal set --
    pass it down from a caller that has already resolved it once per call
    (``measure_promissory_language_precision``, ``gather_progress_phrase``,
    ``gather_promissory_language``); omit it only when calling this function
    directly, which falls back to a fresh per-call roster read (Story 59.2).
    """
    if terminal_statuses is None:
        terminal_statuses, _roster_warning = _load_terminal_statuses(target)
    docs: list[tuple[Path, str]] = []

    dreams_dir = target / "docs" / "dreams"
    if dreams_dir.is_dir():
        for path in sorted(dreams_dir.glob("*.md")):
            if path.name == "README.md":
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            fm, unparseable = _parse_frontmatter(text)
            if unparseable:
                docs.append((path, ""))
                continue
            status = _normalize_status(fm.get("status"))
            if status in terminal_statuses:
                docs.append((path, status))

    spec_roots = (
        target / "_bmad-output" / "projects",
        target / "docs" / "governance",
    )
    for root in spec_roots:
        if not root.is_dir():
            continue
        if root.name == "projects":
            for project_dir in sorted(root.iterdir()):
                specs_dir = project_dir / "planning-artifacts" / "specs"
                if not specs_dir.is_dir():
                    continue
                for spec_dir in sorted(specs_dir.iterdir()):
                    spec_md = spec_dir / "SPEC.md"
                    if not spec_md.is_file():
                        continue
                    _append_spec_if_terminal(spec_md, docs, terminal_statuses)
        else:
            for spec_md in sorted(root.glob("**/SPEC.md")):
                _append_spec_if_terminal(spec_md, docs, terminal_statuses)

    return tuple(docs)


@dataclass(frozen=True)
class OpenQuestionMatch:
    line_no: int
    line_text: str


@dataclass(frozen=True)
class OpenQuestionsScanStats:
    scanned_specs: int = 0
    silent: int = 0
    fired: int = 0


def _memlog_entry_tag(line: str) -> str | None:
    match = _MEMLOG_ENTRY_RE.match(line.strip())
    if not match:
        return None
    return match.group(1).lower()


def last_unclosed_memlog_question(memlog_text: str) -> OpenQuestionMatch | None:
    """The last ``(open)`` / ``(question)`` entry with no later ``(decision)``."""
    last_open: OpenQuestionMatch | None = None
    for line_no, line in enumerate(memlog_text.splitlines(), start=1):
        tag = _memlog_entry_tag(line)
        if tag is None:
            continue
        if tag in {"open", "question"}:
            last_open = OpenQuestionMatch(line_no=line_no, line_text=line.rstrip())
        elif tag == "decision":
            last_open = None
    return last_open


def _strip_yaml_comment(value: str) -> str:
    quote: str | None = None
    for index, char in enumerate(value):
        if quote:
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        elif char == "#" and (index == 0 or value[index - 1].isspace()):
            return value[:index].strip()
    return value.strip()


def open_questions_frontmatter_count(
    text: str,
) -> tuple[int, int | None, bool]:
    """Return ``(count, open_questions_line_no, unparseable)`` for a Spec body."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return 0, None, True
    end = next((index for index in range(1, len(lines)) if lines[index].strip() == "---"), -1)
    if end < 0:
        return 0, None, True

    fm, unparseable = _parse_frontmatter(text)
    if unparseable:
        return 0, None, True

    fm_lines = lines[1:end]
    key_idx = next(
        (index for index, line in enumerate(fm_lines) if line.startswith("open_questions:")),
        -1,
    )
    if key_idx < 0:
        return 0, None, False

    open_questions_line = key_idx + 2  # frontmatter body starts at file line 2
    raw = fm.get("open_questions")
    if raw is None:
        inline = _strip_yaml_comment(fm_lines[key_idx].split(":", 1)[1])
        if inline:
            if inline.startswith("[") and inline.endswith("]"):
                inner = inline[1:-1].strip()
                return (
                    0 if not inner else len([x for x in inner.split(",") if x.strip()]),
                    open_questions_line,
                    False,
                )
            return 0, open_questions_line, True
        count = 0
        indent: int | None = None
        for line in fm_lines[key_idx + 1 :]:
            if line.strip() and not line.startswith((" ", "\t")):
                break
            stripped = line.lstrip()
            if not stripped.startswith("- "):
                continue
            item_indent = len(line) - len(stripped)
            if indent is None:
                indent = item_indent
            if item_indent == indent:
                count += 1
        return count, open_questions_line, False

    if isinstance(raw, list):
        return len(raw), open_questions_line, False
    return 0, open_questions_line, True


def iter_spec_documents(target: Path) -> tuple[Path, ...]:
    """Every ``SPEC.md`` under BMAD specs and governance."""
    docs: list[Path] = []
    spec_roots = (
        target / "_bmad-output" / "projects",
        target / "docs" / "governance",
    )
    for root in spec_roots:
        if not root.is_dir():
            continue
        if root.name == "projects":
            for project_dir in sorted(root.iterdir()):
                specs_dir = project_dir / "planning-artifacts" / "specs"
                if not specs_dir.is_dir():
                    continue
                for spec_dir in sorted(specs_dir.iterdir()):
                    spec_md = spec_dir / "SPEC.md"
                    if spec_md.is_file():
                        docs.append(spec_md)
        else:
            for spec_md in sorted(root.glob("**/SPEC.md")):
                docs.append(spec_md)
    return tuple(docs)


@dataclass(frozen=True)
class StatusCommentRef:
    kind: str  # "epic" | "story"
    ledger_key: str
    claimed_status: str
    matched_text: str


@dataclass(frozen=True)
class StatusCommentScanStats:
    scanned_documents: int = 0
    silent: int = 0
    fired: int = 0
    unresolvable: int = 0


def _parse_ledger_statuses(text: str) -> dict[str, str]:
    """``key: value`` pairs under ``development_status:`` (Story 21.15 / CAP-4)."""
    out: dict[str, str] = {}
    in_block = False
    for raw in text.splitlines():
        if raw.startswith("development_status:"):
            in_block = True
            continue
        if not in_block:
            continue
        if raw and not raw.startswith((" ", "\t")):
            break
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if sep:
            out[key.strip()] = value.strip()
    return out


def load_ledger_status_index(target: Path) -> dict[str, tuple[str, str]]:
    """Map ledger keys to ``(project_slug, live_status)`` across every tracked ledger.

    A ledger key (``epic-14``, a story key) is not fleet-unique — every
    station numbers its own epics/stories from scratch, so two stations can
    both define ``epic-14``. ``setdefault`` here means the first project in
    sort order silently wins any collision. This flat index exists only as a
    fallback for a document whose owning project can't be determined —
    ``gather_status_comment_reconcile`` resolves against the document's own
    project first via ``load_project_ledger_statuses``.
    """
    index: dict[str, tuple[str, str]] = {}
    projects_root = target / "_bmad-output" / "projects"
    if not projects_root.is_dir():
        return index
    for project_dir in sorted(projects_root.iterdir()):
        if not project_dir.is_dir():
            continue
        ledger_path = project_dir / _LEDGER_SUFFIX
        if not ledger_path.is_file():
            continue
        try:
            statuses = _parse_ledger_statuses(ledger_path.read_text(encoding="utf-8"))
        except OSError:
            continue
        project_slug = project_dir.name
        for key, status in statuses.items():
            index.setdefault(key, (project_slug, status))
    return index


def load_project_ledger_statuses(target: Path, project_slug: str) -> dict[str, str]:
    """Ledger key -> live status for exactly one project's own tracked ledger."""
    ledger_path = target / "_bmad-output" / "projects" / project_slug / _LEDGER_SUFFIX
    if not ledger_path.is_file():
        return {}
    try:
        return _parse_ledger_statuses(ledger_path.read_text(encoding="utf-8"))
    except OSError:
        return {}


def owning_project_for_doc(target: Path, path: Path, text: str) -> str | None:
    """The BMAD project slug a status-comment reference should resolve against.

    A story spec or ``SPEC.md`` under ``_bmad-output/projects/<slug>/...``
    names its own project in the path — unambiguous. A Dream under
    ``docs/dreams/`` carries no such path; its ``owner:`` frontmatter field
    (a station name, e.g. ``doctor``) maps to that station's ``pyforge-``
    project by this fleet's own naming convention.
    """
    try:
        rel_parts = path.relative_to(target / "_bmad-output" / "projects").parts
    except ValueError:
        rel_parts = ()
    if rel_parts:
        return rel_parts[0]
    fm, unparseable = _parse_frontmatter(text)
    if unparseable:
        return None
    owner = fm.get("owner")
    if isinstance(owner, str) and owner.strip():
        return f"pyforge-{owner.strip()}"
    return None


def _frontmatter_lines(text: str) -> tuple[list[str], bool]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return [], True
    end = next(
        (index for index in range(1, len(lines)) if lines[index].strip() == "---"),
        -1,
    )
    if end < 0:
        return [], True
    return lines[1:end], False


def status_comment_text(text: str) -> tuple[str | None, int | None]:
    """Concatenated ``status:`` comment text and its 1-based file line number."""
    fm_lines, unparseable = _frontmatter_lines(text)
    if unparseable:
        return None, None
    status_idx = next(
        (index for index, line in enumerate(fm_lines) if line.startswith("status:")),
        -1,
    )
    if status_idx < 0:
        return None, None

    status_line = fm_lines[status_idx]
    comment_parts: list[str] = []
    if "#" in status_line:
        comment_parts.append(status_line.split("#", 1)[1].strip())

    for continuation in fm_lines[status_idx + 1 :]:
        stripped = continuation.strip()
        if stripped.startswith("#"):
            comment_parts.append(stripped.lstrip("#").strip())
            continue
        break

    if not comment_parts:
        return None, None
    return " ".join(comment_parts), status_idx + 2


def parse_status_comment_references(comment: str) -> tuple[StatusCommentRef, ...]:
    """Every epic/story + claimed-status pair named in a status comment."""
    refs: list[StatusCommentRef] = []
    seen: set[tuple[str, str]] = set()
    for match in _EPIC_STATUS_COMMENT_RE.finditer(comment):
        epic = match.group(1)
        claimed = match.group(2).lower()
        ledger_key = f"epic-{epic}"
        token = ("epic", ledger_key)
        if token in seen:
            continue
        seen.add(token)
        refs.append(
            StatusCommentRef(
                kind="epic",
                ledger_key=ledger_key,
                claimed_status=claimed,
                matched_text=match.group(0).strip(),
            )
        )
    for match in _STORY_STATUS_COMMENT_RE.finditer(comment):
        epic, story, claimed = match.group(1), match.group(2), match.group(3).lower()
        ledger_key = f"{epic}-{story}"
        token = ("story", ledger_key)
        if token in seen:
            continue
        seen.add(token)
        refs.append(
            StatusCommentRef(
                kind="story",
                ledger_key=ledger_key,
                claimed_status=claimed,
                matched_text=match.group(0).strip(),
            )
        )
    return tuple(refs)


def iter_frontmatter_documents(target: Path) -> tuple[Path, ...]:
    """Dreams, ``SPEC.md`` files, and tracked story specs with frontmatter."""
    docs: list[Path] = []

    dreams_dir = target / "docs" / "dreams"
    if dreams_dir.is_dir():
        for path in sorted(dreams_dir.glob("*.md")):
            if path.name != "README.md":
                docs.append(path)

    for spec_md in iter_spec_documents(target):
        docs.append(spec_md)

    specs_root = target / "_bmad-output" / "projects"
    if specs_root.is_dir():
        for project_dir in sorted(specs_root.iterdir()):
            story_specs = project_dir / "planning-artifacts" / "specs"
            if not story_specs.is_dir():
                continue
            for path in sorted(story_specs.glob("spec-*.md")):
                docs.append(path)

    return tuple(dict.fromkeys(docs))


def _resolve_story_ledger_key(prefix: str, ledger_index: dict[str, tuple[str, str]]) -> str | None:
    matches = [key for key in ledger_index if key.startswith(f"{prefix}-")]
    if len(matches) == 1:
        return matches[0]
    if prefix in ledger_index:
        return prefix
    return matches[0] if matches else None


def _status_comment_message(
    *,
    rel: str,
    line_no: int,
    ref: StatusCommentRef,
    ledger_key: str,
    ledger_status: str,
    project_slug: str,
) -> str:
    return (
        f"{rel}:{line_no} status comment names {ref.matched_text!r} while "
        f"{project_slug} sprint-status-ledger.yaml row {ledger_key!r} reads "
        f"{ledger_status!r}"
    )


def _status_comment_unresolvable_message(
    *,
    rel: str,
    line_no: int,
    ref: StatusCommentRef,
) -> str:
    return (
        f"{rel}:{line_no} status comment names {ref.matched_text!r} but no "
        f"tracked ledger row matches {ref.ledger_key!r}"
    )


def gather_status_comment_reconcile(target: Path) -> tuple[Finding, ...]:
    """CAP-4: frontmatter status comments vs live sprint ledger rows."""
    ledger_index = load_ledger_status_index(target)
    findings: list[Finding] = []
    scanned_documents = 0
    silent = 0
    fired = 0
    unresolvable = 0

    for path in iter_frontmatter_documents(target):
        rel = _rel_path(path, target)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            findings.append(
                Finding(
                    source=Source.STATUS_BODY_CONSISTENCY,
                    check=_CHECK_UNPARSEABLE,
                    status=DoctorStatus.WARN,
                    message=(f"{rel} could not be read — {exc.__class__.__name__}: {exc}"),
                    evidence={"path": rel},
                )
            )
            continue

        comment, line_no = status_comment_text(text)
        if comment is None:
            continue

        refs = parse_status_comment_references(comment)
        if not refs:
            continue

        scanned_documents += 1
        doc_fired = False
        owning_project = owning_project_for_doc(target, path, text)
        project_ledger = load_project_ledger_statuses(target, owning_project) if owning_project else {}
        for ref in refs:
            # Resolve against the document's OWN project first — a ledger key
            # like "epic-14" is not fleet-unique, every station numbers its
            # own epics from scratch, so falling straight to the flat
            # cross-project index risks checking the comment against a
            # different station's epic 14 entirely.
            project_slug: str | None = None
            ledger_status: str | None = None
            if project_ledger:
                scoped_key = (
                    _resolve_story_ledger_key(ref.ledger_key, project_ledger)
                    if ref.kind == "story"
                    else (ref.ledger_key if ref.ledger_key in project_ledger else None)
                )
                if scoped_key is not None:
                    project_slug = owning_project
                    ledger_status = project_ledger[scoped_key]
                    resolved_key = scoped_key

            if project_slug is None:
                if ref.kind == "story":
                    resolved_key = _resolve_story_ledger_key(ref.ledger_key, ledger_index)
                else:
                    resolved_key = ref.ledger_key
                if resolved_key is not None and resolved_key in ledger_index:
                    project_slug, ledger_status = ledger_index[resolved_key]
                else:
                    resolved_key = None

            if resolved_key is None:
                unresolvable += 1
                doc_fired = True
                findings.append(
                    Finding(
                        source=Source.STATUS_BODY_CONSISTENCY,
                        check=_CHECK_STATUS_COMMENT_UNRESOLVABLE,
                        status=DoctorStatus.WARN,
                        message=_status_comment_unresolvable_message(
                            rel=rel,
                            line_no=line_no or 1,
                            ref=ref,
                        ),
                        evidence={
                            "path": rel,
                            "line": line_no,
                            "comment": comment,
                            "ledger_key": ref.ledger_key,
                            "claimed_status": ref.claimed_status,
                            "matched_text": ref.matched_text,
                        },
                    )
                )
                continue

            if ref.claimed_status != ledger_status:
                fired += 1
                doc_fired = True
                findings.append(
                    Finding(
                        source=Source.STATUS_BODY_CONSISTENCY,
                        check=_CHECK_STATUS_COMMENT,
                        status=DoctorStatus.WARN,
                        message=_status_comment_message(
                            rel=rel,
                            line_no=line_no or 1,
                            ref=ref,
                            ledger_key=resolved_key,
                            ledger_status=ledger_status,
                            project_slug=project_slug,
                        ),
                        evidence={
                            "path": rel,
                            "line": line_no,
                            "comment": comment,
                            "ledger_key": resolved_key,
                            "claimed_status": ref.claimed_status,
                            "ledger_status": ledger_status,
                            "ledger_project": project_slug,
                            "matched_text": ref.matched_text,
                        },
                    )
                )

        if not doc_fired:
            silent += 1

    tier_stats = {
        "scanned_documents": scanned_documents,
        "silent": silent,
        "fired": fired,
        "unresolvable": unresolvable,
    }
    if not findings:
        return (
            Finding(
                source=Source.STATUS_BODY_CONSISTENCY,
                check=_CHECK_STATUS_COMMENT,
                status=DoctorStatus.OK,
                message=(
                    f"no status-comment/ledger contradictions across {scanned_documents} document(s) with named keys"
                ),
                evidence=tier_stats,
            ),
        )

    return tuple(
        Finding(
            source=f.source,
            check=f.check,
            status=f.status,
            message=f.message,
            evidence={**f.evidence, **tier_stats},
        )
        for f in findings
    )


def _append_spec_if_terminal(spec_md: Path, docs: list[tuple[Path, str]], terminal_statuses: frozenset[str]) -> None:
    try:
        text = spec_md.read_text(encoding="utf-8")
    except OSError:
        return
    fm, unparseable = _parse_frontmatter(text)
    if unparseable:
        docs.append((spec_md, ""))
        return
    status = _normalize_status(fm.get("status"))
    if status in terminal_statuses:
        docs.append((spec_md, status))


def _rel_path(path: Path, target: Path) -> str:
    try:
        return path.relative_to(target).as_posix()
    except ValueError:
        return path.as_posix()


def _progress_phrase_message(*, rel: str, line_no: int, status: str, matched: str) -> str:
    return f"{rel}:{line_no} reads {matched!r} under status: {status!r}"


def gather_progress_phrase(target: Path) -> tuple[Finding, ...]:
    """CAP-1: incomplete progress phrases under terminal ``status:``."""
    findings: list[Finding] = []
    scanned_terminal = 0
    silent = 0
    fired = 0

    terminal_statuses, roster_warning = _load_terminal_statuses(target)
    if roster_warning is not None:
        findings.append(roster_warning)

    for path, status in iter_terminal_tier_documents(target, terminal_statuses):
        rel = _rel_path(path, target)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            findings.append(
                Finding(
                    source=Source.STATUS_BODY_CONSISTENCY,
                    check=_CHECK_UNPARSEABLE,
                    status=DoctorStatus.WARN,
                    message=(f"{rel} could not be read — {exc.__class__.__name__}: {exc}"),
                    evidence={"path": rel},
                )
            )
            continue

        fm, unparseable = _parse_frontmatter(text)
        if unparseable:
            findings.append(
                Finding(
                    source=Source.STATUS_BODY_CONSISTENCY,
                    check=_CHECK_UNPARSEABLE,
                    status=DoctorStatus.WARN,
                    message=f"{rel} frontmatter is unparseable",
                    evidence={"path": rel},
                )
            )
            continue

        resolved_status = status or _normalize_status(fm.get("status"))
        if resolved_status not in terminal_statuses:
            continue

        scanned_terminal += 1
        body = _body_after_frontmatter(text)
        matches = scan_body_for_incomplete_progress(body)
        if not matches:
            silent += 1
            continue

        for match in matches:
            fired += 1
            findings.append(
                Finding(
                    source=Source.STATUS_BODY_CONSISTENCY,
                    check=_CHECK_PROGRESS,
                    status=DoctorStatus.WARN,
                    message=_progress_phrase_message(
                        rel=rel,
                        line_no=match.line_no,
                        status=resolved_status,
                        matched=match.matched,
                    ),
                    evidence={
                        "path": rel,
                        "line": match.line_no,
                        "line_text": match.line_text,
                        "status": resolved_status,
                        "n": match.n,
                        "m": match.m,
                        "matched": match.matched,
                    },
                )
            )

    tier_stats = {
        "scanned_terminal": scanned_terminal,
        "silent": silent,
        "fired": fired,
    }
    if not findings:
        return (
            Finding(
                source=Source.STATUS_BODY_CONSISTENCY,
                check="status-body-consistency",
                status=DoctorStatus.OK,
                message=(f"no incomplete progress phrases under terminal status across {scanned_terminal} document(s)"),
                evidence=tier_stats,
            ),
        )

    return tuple(
        Finding(
            source=f.source,
            check=f.check,
            status=f.status,
            message=f.message,
            evidence={**f.evidence, **tier_stats},
        )
        for f in findings
    )


def _open_questions_message(
    *,
    rel: str,
    spec_line: int,
    memlog_line: int,
) -> str:
    return (
        f"{rel}:{spec_line} declares open_questions: [] while "
        f"{rel.rsplit('/', 1)[0]}/.memlog.md:{memlog_line} carries an unclosed "
        f"(open) or (question) entry"
    )


def gather_open_questions_reconcile(target: Path) -> tuple[Finding, ...]:
    """CAP-2: ``open_questions`` frontmatter vs companion memlog."""
    findings: list[Finding] = []
    scanned_specs = 0
    silent = 0
    fired = 0

    for spec_md in iter_spec_documents(target):
        rel = _rel_path(spec_md, target)
        memlog = spec_md.parent / ".memlog.md"
        if not memlog.is_file():
            continue

        scanned_specs += 1
        try:
            spec_text = spec_md.read_text(encoding="utf-8")
            memlog_text = memlog.read_text(encoding="utf-8")
        except OSError as exc:
            findings.append(
                Finding(
                    source=Source.STATUS_BODY_CONSISTENCY,
                    check=_CHECK_UNPARSEABLE,
                    status=DoctorStatus.WARN,
                    message=(f"{rel} or its companion memlog could not be read — {exc.__class__.__name__}: {exc}"),
                    evidence={"path": rel},
                )
            )
            continue

        oq_count, oq_line, oq_unparseable = open_questions_frontmatter_count(spec_text)
        if oq_unparseable:
            findings.append(
                Finding(
                    source=Source.STATUS_BODY_CONSISTENCY,
                    check=_CHECK_UNPARSEABLE,
                    status=DoctorStatus.WARN,
                    message=f"{rel} open_questions frontmatter is unparseable",
                    evidence={"path": rel},
                )
            )
            continue

        unclosed = last_unclosed_memlog_question(memlog_text)
        if unclosed is None:
            silent += 1
            continue

        if oq_count > 0:
            silent += 1
            continue

        fired += 1
        spec_line = oq_line or 1
        memlog_rel = _rel_path(memlog, target)
        findings.append(
            Finding(
                source=Source.STATUS_BODY_CONSISTENCY,
                check=_CHECK_OPEN_QUESTIONS,
                status=DoctorStatus.WARN,
                message=_open_questions_message(
                    rel=rel,
                    spec_line=spec_line,
                    memlog_line=unclosed.line_no,
                ),
                evidence={
                    "path": rel,
                    "spec_line": spec_line,
                    "memlog_path": memlog_rel,
                    "memlog_line": unclosed.line_no,
                    "memlog_line_text": unclosed.line_text,
                    "open_questions_count": oq_count,
                },
            )
        )

    tier_stats = {
        "scanned_specs": scanned_specs,
        "silent": silent,
        "fired": fired,
    }
    if not findings:
        return (
            Finding(
                source=Source.STATUS_BODY_CONSISTENCY,
                check="status-body-open-questions",
                status=DoctorStatus.OK,
                message=(
                    f"no open_questions/memlog contradictions across {scanned_specs} spec(s) with companion memlogs"
                ),
                evidence=tier_stats,
            ),
        )

    return tuple(
        Finding(
            source=f.source,
            check=f.check,
            status=f.status,
            message=f.message,
            evidence={**f.evidence, **tier_stats},
        )
        for f in findings
    )


def _promissory_message(*, rel: str, line_no: int, status: str, pattern_id: str) -> str:
    return f"{rel}:{line_no} reads forward-looking ({pattern_id!r}) under status: {status!r}"


def gather_promissory_language(target: Path) -> tuple[Finding, ...]:
    """CAP-3: forward-looking section language under terminal ``status:``."""
    if not PROMISSORY_LANGUAGE_ACCEPTED:
        measurement = measure_promissory_language_precision(target)
        return (
            Finding(
                source=Source.STATUS_BODY_CONSISTENCY,
                check=_CHECK_PROMISSORY,
                status=DoctorStatus.OK,
                message=(
                    "promissory-language signal measured-and-rejected "
                    f"(precision={measurement.precision:.3f}, "
                    f"herald_pair={measurement.herald_pair_fired}, "
                    f"false_positives={measurement.false_positive_documents})"
                ),
                evidence={
                    "accepted": False,
                    "scanned_terminal": measurement.scanned_terminal,
                    "herald_pair_fired": measurement.herald_pair_fired,
                    "false_positive_documents": measurement.false_positive_documents,
                    "precision": measurement.precision,
                },
            ),
        )

    findings: list[Finding] = []
    scanned_terminal = 0
    silent = 0
    fired = 0

    terminal_statuses, roster_warning = _load_terminal_statuses(target)
    if roster_warning is not None:
        findings.append(roster_warning)

    for path, status in iter_terminal_tier_documents(target, terminal_statuses):
        rel = _rel_path(path, target)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            findings.append(
                Finding(
                    source=Source.STATUS_BODY_CONSISTENCY,
                    check=_CHECK_UNPARSEABLE,
                    status=DoctorStatus.WARN,
                    message=(f"{rel} could not be read — {exc.__class__.__name__}: {exc}"),
                    evidence={"path": rel},
                )
            )
            continue

        fm, unparseable = _parse_frontmatter(text)
        if unparseable:
            findings.append(
                Finding(
                    source=Source.STATUS_BODY_CONSISTENCY,
                    check=_CHECK_UNPARSEABLE,
                    status=DoctorStatus.WARN,
                    message=f"{rel} frontmatter is unparseable",
                    evidence={"path": rel},
                )
            )
            continue

        resolved_status = status or _normalize_status(fm.get("status"))
        if resolved_status not in terminal_statuses:
            continue

        scanned_terminal += 1
        body = _body_after_frontmatter(text)
        matches = scan_body_for_promissory_language(body)
        if not matches:
            silent += 1
            continue

        for match in matches:
            fired += 1
            findings.append(
                Finding(
                    source=Source.STATUS_BODY_CONSISTENCY,
                    check=_CHECK_PROMISSORY,
                    status=DoctorStatus.WARN,
                    message=_promissory_message(
                        rel=rel,
                        line_no=match.line_no,
                        status=resolved_status,
                        pattern_id=match.pattern_id,
                    ),
                    evidence={
                        "path": rel,
                        "line": match.line_no,
                        "line_text": match.line_text,
                        "surface_kind": match.surface_kind,
                        "pattern_id": match.pattern_id,
                        "status": resolved_status,
                    },
                )
            )

    tier_stats = {
        "scanned_terminal": scanned_terminal,
        "silent": silent,
        "fired": fired,
        "accepted": True,
    }
    if not findings:
        return (
            Finding(
                source=Source.STATUS_BODY_CONSISTENCY,
                check=_CHECK_PROMISSORY,
                status=DoctorStatus.OK,
                message=(f"no promissory language under terminal status across {scanned_terminal} document(s)"),
                evidence=tier_stats,
            ),
        )

    return tuple(
        Finding(
            source=f.source,
            check=f.check,
            status=f.status,
            message=f.message,
            evidence={**f.evidence, **tier_stats},
        )
        for f in findings
    )


#: Checks that CAP-1..CAP-4 can each independently emit for the same
#: underlying file/roster problem -- dedupe by (check, path) rather than
#: letting every caller's copy survive into the combined ``gather()`` output.
_DEDUPE_BY_PATH_CHECKS = frozenset({_CHECK_UNPARSEABLE, _CHECK_ROSTER_DEGRADED})


def _dedupe_unparseable_findings(
    findings: tuple[Finding, ...],
) -> tuple[Finding, ...]:
    seen: set[tuple[str, str]] = set()
    out: list[Finding] = []
    for finding in findings:
        if finding.check not in _DEDUPE_BY_PATH_CHECKS:
            out.append(finding)
            continue
        key = (finding.check, str(finding.evidence.get("path", "")))
        if key in seen:
            continue
        seen.add(key)
        out.append(finding)
    return tuple(out)


def _gather_all(target: Path) -> tuple[Finding, ...]:
    cap1 = gather_progress_phrase(target)
    cap2 = gather_open_questions_reconcile(target)
    cap3 = gather_promissory_language(target)
    cap4 = gather_status_comment_reconcile(target)
    cap1_warns = [f for f in cap1 if f.status != DoctorStatus.OK]
    cap2_warns = [f for f in cap2 if f.status != DoctorStatus.OK]
    cap3_warns = [f for f in cap3 if f.status != DoctorStatus.OK]
    cap4_warns = [f for f in cap4 if f.status != DoctorStatus.OK]
    cap3_rejected = [f for f in cap3 if f.status == DoctorStatus.OK and f.evidence.get("accepted") is False]
    if cap1_warns or cap2_warns or cap3_warns or cap4_warns:
        return _dedupe_unparseable_findings(tuple(cap1_warns + cap2_warns + cap3_warns + cap4_warns))
    if cap3_rejected:
        return tuple(cap3_rejected)
    return (
        Finding(
            source=Source.STATUS_BODY_CONSISTENCY,
            check="status-body-consistency",
            status=DoctorStatus.OK,
            message="no status/body consistency findings",
            evidence={
                **cap1[0].evidence,
                **cap2[0].evidence,
                **cap3[0].evidence,
                **cap4[0].evidence,
            },
        ),
    )


def gather(target: Path) -> tuple[Finding, ...]:
    """Status/body consistency gather — CAP-1..CAP-4 (CAP-3 when accepted)."""
    return degrade_on_exception(
        Source.STATUS_BODY_CONSISTENCY,
        "status-body-consistency",
        lambda: _gather_all(target),
    )
