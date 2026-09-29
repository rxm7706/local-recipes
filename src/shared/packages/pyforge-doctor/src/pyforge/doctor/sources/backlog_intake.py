"""The backlog-intake gather filter -- Doctor's verdict on which tracked
deferred-work-ledger entries, fleet wide, precisely name a given epic or
story (Story 13.1, Epic 13/CAP-1).

**Why this module exists.** Tracked ``deferred-work-ledger.md`` entries
across the fleet often name an epic/story in prose (e.g. "closes once Story
13.1 lands"), but nothing surfaced that link at story-drafting time -- a
human had to remember to grep the ledger by hand. The fleet has already
shipped a real bug from a related failure class
(``DW-CHAIN-COMPLETENESS-1``, see ``sources/board.py``): a bare substring
test over concatenated prose, which reported false-clean while missing most
of what it claimed to check. This module's entire reason for existing is to
not repeat that mistake -- every match is a parsed, ``\\b``-word-boundary-
anchored ``Epic N`` / ``Story N.M`` / ``Story N-M`` token, never a bare
substring check, so querying epic ``"1"`` can never match text naming
``Epic 11``, and querying story ``"13.1"`` can never match text naming
``Story 13.10``.

**How this relates to ``sources/chain.py``'s ``gather_deferred_work``/
``gather_due_for_verification``.** Both read the SAME tracked artifact
(``planning-artifacts/deferred-work-ledger.md``, fleet wide) and split it
into per-entry blocks anchored on a ``## DW-<id>`` heading -- the same
anchor pattern ``chain.py``'s own ``_ENTRY_RE`` uses
(``^#{2,4}\\s+DW-[A-Za-z0-9][A-Za-z0-9-]*``). Per this story's own Design
Notes, that anchor is mirrored HERE, written locally, rather than importing
``chain.py``'s private helpers -- matching this package's existing
convention of each ``sources/*.py`` module owning its own tiny ledger regex
rather than sharing a heavy parser (see ``ledger.py``'s own independence
discipline for the same rationale applied to a different artifact).

**Read-only, no subprocess.** Pure ``pathlib``/``re`` text scanning over the
tracked ledgers directly -- mirrors ``sources/ledger.py``'s own
independence discipline. Never auto-writes anything into any story/spec
file; the ``Finding`` itself is the entire output (Non-goal).

**Degrades, never crashes** -- the house rule for every Doctor source. An
unparseable ``identifier`` yields one WARN ``Finding`` naming it (never
raises); an unreadable ledger is skipped, the scan continues over the rest.
Every ``Finding`` this module emits is WARN (a match) or OK (no match),
never FAIL -- this source INFORMS, it never gates, mirroring
``gather_due_for_verification``'s own discipline exactly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..models import DoctorStatus, Finding, Source

__all__ = ("ParsedIdentifier", "parse_identifier", "gather")

#: The fleet-wide glob every station's tracked ledger is found under --
#: relative to `target`, mirroring `chain.py`'s own `TRACKED_REL` tail
#: (`planning-artifacts/deferred-work-ledger.md`) composed with the
#: `_bmad-output/projects/*/` prefix every project lives under.
LEDGER_GLOB = "_bmad-output/projects/*/planning-artifacts/deferred-work-ledger.md"

# Mirrors chain.py's own `_ENTRY_RE` anchor
# (`^#{2,4}\s+DW-[A-Za-z0-9][A-Za-z0-9-]*`), written locally rather than
# imported (Design Notes: do not import chain.py's private helpers) --
# extended with two capture groups (the id, and the rest of the heading
# line) this module's own summary-extraction needs that chain.py's sibling
# has no use for.
_ENTRY_RE = re.compile(r"^#{2,4}\s+(DW-[A-Za-z0-9][A-Za-z0-9-]*)(.*)$", re.M)

#: An entry's own (possibly absent) `status:` field value -- the first such
#: line within the entry's span, verbatim (whitespace-trimmed). Mirrors
#: `chain.py`'s own `_VERIFIED_RE` shape, applied to a different field.
_STATUS_LINE_RE = re.compile(r"^\s*status:\s*(.+)$", re.M)

# A story query: an optional case-insensitive "Story " prefix, then
# <epic>.<story> or <epic>-<story>, with an optional trailing lowercase
# letter (a lettered sub-story, e.g. "13.1a") the identifier is allowed to
# carry -- the letter is accepted here for parsing purposes only; it plays
# no further role in _pattern_for's own match (Design Notes: Simplicity
# First -- nothing speculative).
_STORY_RE = re.compile(r"^(?:story\s+)?(\d+)[.\-](\d+)[a-z]?$", re.IGNORECASE)

# An epic-only query: an optional case-insensitive "Epic " prefix, then a
# bare number.
_EPIC_RE = re.compile(r"^(?:epic\s+)?(\d+)$", re.IGNORECASE)

# The leading separator between a heading's id and its own title text --
# ": ", " -- " (em dash), a bare "-", or plain whitespace, in any
# combination -- stripped so `_entries`' own `title` is just the prose.
_TITLE_STRIP_RE = re.compile(r"^[\s:\u2014-]+")


@dataclass(frozen=True)
class ParsedIdentifier:
    """A parsed epic/story query.

    ``story is None`` means an epic-only query -- matches the bare parent
    ``Epic N`` AND any ``Story N.<digits>`` under it. A non-``None``
    ``story`` means an exact-story query -- matches that one story (dotted
    ``N.M`` or kebab ``N-M`` prose form) AND the bare parent ``Epic N``.
    """

    epic: int
    story: int | None


def parse_identifier(raw: str) -> ParsedIdentifier | None:
    """Parse a caller-supplied epic/story identifier -- never raises.

    Accepts a bare epic number (``"13"``), a dotted or kebab story id
    (``"13.1"``/``"13-1"``, optional trailing single lowercase letter), or
    either prefixed with ``"Epic "``/``"Story "`` (case-insensitive).
    Returns ``None`` on anything else, including a non-``str`` ``raw`` or a
    bare unlabeled number this module refuses to treat as an id (Never
    clause: a bare number with no ``Epic``/``Story`` keyword anchor is
    still accepted here as an EPIC id, matching the documented "13" ->
    epic-only form -- what is refused is matching a bare number inside
    ledger PROSE with no keyword anchor, which is `_pattern_for`'s own
    concern, not this function's).
    """
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    story_match = _STORY_RE.match(text)
    if story_match:
        return ParsedIdentifier(epic=int(story_match.group(1)), story=int(story_match.group(2)))
    epic_match = _EPIC_RE.match(text)
    if epic_match:
        return ParsedIdentifier(epic=int(epic_match.group(1)), story=None)
    return None


def _pattern_for(parsed: ParsedIdentifier) -> re.Pattern[str]:
    """The combined, ``\\b``-anchored search pattern for ``parsed`` --
    THE CORE of this story: every alternative anchors the number with
    Python ``\\b`` word boundaries on both sides, so ``Epic 1`` can never
    match inside ``Epic 11``'s prose and ``Story 13.1`` can never match
    inside ``Story 13.10``'s (adjacent digits share no word boundary).

    An epic-only query (``story is None``) matches the bare parent
    ``Epic N`` OR any ``Story N.<digits>``/``Story N-<digits>`` under it,
    dotted or kebab -- symmetric with the story-query branch below (review
    finding: the dotted-only form here used to admit a kebab sub-story
    reference at the exact-story granularity but silently miss the same
    prose shape at the epic-only granularity). A story query matches the
    bare parent ``Epic N`` OR that exact story, dotted or kebab (``Story
    N.M``/``Story N-M``) -- each allowing an optional trailing lowercase
    letter in the LEDGER TEXT (a lettered sub-story), regardless of whether
    the query identifier itself carried one.
    """
    epic_token = rf"\bEpic\s+{parsed.epic}\b"
    if parsed.story is None:
        story_token = rf"\bStory\s+{parsed.epic}[.\-]\d+[a-z]?\b"
        return re.compile(f"(?:{epic_token}|{story_token})", re.IGNORECASE)
    dotted = rf"\bStory\s+{parsed.epic}\.{parsed.story}[a-z]?\b"
    kebab = rf"\bStory\s+{parsed.epic}-{parsed.story}[a-z]?\b"
    return re.compile(f"(?:{epic_token}|{dotted}|{kebab})", re.IGNORECASE)


def _clean_title(raw: str) -> str:
    return _TITLE_STRIP_RE.sub("", raw).strip()


def _status_of(body: str) -> str:
    match = _STATUS_LINE_RE.search(body)
    return match.group(1).strip() if match else ""


def _entries(text: str) -> list[tuple[str, str, str]]:
    """``(entry_id, title, body)`` for every ``## DW-<id>`` heading in
    ``text`` -- this module's own local equivalent of ``chain.py``'s
    entry-splitting idiom (Design Notes: do not import ``chain.py``'s
    private helpers). ``body`` spans from the heading through the next
    heading (or end of text), same convention as ``chain.py``'s
    ``_entries``/``_verification``/``_entry_named_paths``."""
    marks = list(_ENTRY_RE.finditer(text))
    out: list[tuple[str, str, str]] = []
    for i, match in enumerate(marks):
        start = match.start()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out.append((match.group(1), _clean_title(match.group(2)), text[start:end]))
    return out


def gather(target: Path, *, identifier: str) -> tuple[Finding, ...]:
    """Scan every station's tracked ``deferred-work-ledger.md`` under
    ``target`` for entries whose text precisely names ``identifier``'s
    epic or story -- never raises.

    An unparseable ``identifier`` yields one WARN ``Finding`` naming it,
    checked BEFORE any ledger is read. Each matching entry yields one WARN
    ``Finding`` carrying the ledger path, entry id, a one-line summary (the
    entry heading's own title text), the entry's own ``status:`` value (or
    ``""`` when absent -- deliberately no status filtering, Design Notes:
    every textual match is surfaced regardless of ``status:``, letting the
    drafting session judge relevance from the visible evidence), and the
    literal matched token. No matches anywhere -- including when the
    fleet-wide glob finds zero tracked ledgers at all -- degrades to one OK
    ``Finding``, zero matches, rather than an empty tuple.
    """
    parsed = parse_identifier(identifier)
    if parsed is None:
        return (
            Finding(
                source=Source.BACKLOG_INTAKE,
                check="backlog-intake",
                status=DoctorStatus.WARN,
                message=(
                    f"identifier {identifier!r} is not a parseable epic/story "
                    "id (expected e.g. '13', '13.1', '13-1', 'Epic 13', "
                    "'Story 13.1')"
                ),
                evidence={"identifier": identifier},
            ),
        )

    pattern = _pattern_for(parsed)
    findings: list[Finding] = []
    for ledger_path in sorted(target.glob(LEDGER_GLOB)):
        try:
            text = ledger_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            # Tracked ledger path exists but read fails (e.g. permission
            # denied, or it resolved to a directory) -- skip it, the scan
            # continues over the rest (I/O matrix: "ledger unreadable").
            continue
        try:
            ledger_ref = str(ledger_path.relative_to(target))
        except ValueError:
            ledger_ref = str(ledger_path)
        for entry_id, title, body in _entries(text):
            match = pattern.search(body)
            if match is None:
                continue
            findings.append(
                Finding(
                    source=Source.BACKLOG_INTAKE,
                    check="backlog-intake",
                    status=DoctorStatus.WARN,
                    message=f"{entry_id} in {ledger_ref} names {match.group(0)}",
                    evidence={
                        "ledger": ledger_ref,
                        "entry_id": entry_id,
                        "summary": title,
                        "status": _status_of(body),
                        "matched": match.group(0),
                    },
                )
            )

    if not findings:
        return (
            Finding(
                source=Source.BACKLOG_INTAKE,
                check="backlog-intake",
                status=DoctorStatus.OK,
                message=(f"no tracked deferred-work-ledger entry names {identifier}"),
                evidence={"identifier": identifier, "matches": 0},
            ),
        )
    return tuple(findings)
