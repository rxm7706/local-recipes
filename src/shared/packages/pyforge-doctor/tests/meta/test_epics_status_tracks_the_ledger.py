"""Doctor's ``epics.md`` ``**Status:**`` lines read the tracked ledger, not stale prose (Story 41.2, DW-FU-23-6).

The tracked ``sprint-status-ledger.yaml`` is the source of truth for a story's status; ``epics.md`` carries a
``**Status:**`` line on some stories and those lines lagged it (19 mismatches at the 2026-10-01 triage,
Stories 23.5 and 23.6 among them). A story's ledger key starts with its number (``34.3`` -> ``34-3-``), so the
join needs no title matching. A story with no ``**Status:**`` line asserts nothing and is not checked; the first
word of the line is its status (``done - verified against ...`` reads ``done``).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# tests/meta/test_x.py -> parents[3] is src/shared/packages/ (same arithmetic as the sibling meta-tests).
PACKAGES_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = PACKAGES_ROOT.parents[2]
PLANNING = REPO_ROOT / "_bmad-output" / "projects" / "pyforge-doctor" / "planning-artifacts"

_STORY_HEADING_RE = re.compile(r"^### Story (\d+)\.(\d+[a-z]?):", re.MULTILINE)
_STATUS_LINE_RE = re.compile(r"^\*\*Status:\*\*[ \t]*(.*)$", re.MULTILINE)
_LEDGER_ROW_RE = re.compile(r"^  ([0-9]+-[0-9]+[a-z]?-[^:\s]+):\s*([A-Za-z-]+)\s*(?:#.*)?$", re.MULTILINE)


def ledger_statuses(ledger_text: str) -> dict[str, str]:
    """Story key -> status for every ``development_status`` row."""
    return {m.group(1): m.group(2) for m in _LEDGER_ROW_RE.finditer(ledger_text)}


def epics_status_mismatches(epics_text: str, ledger: dict[str, str]) -> list[str]:
    """One line per story whose epics ``**Status:**`` differs from the ledger (or has no ledger key)."""
    headings = list(_STORY_HEADING_RE.finditer(epics_text))
    problems: list[str] = []
    for idx, heading in enumerate(headings):
        end = headings[idx + 1].start() if idx + 1 < len(headings) else len(epics_text)
        statuses = _STATUS_LINE_RE.findall(epics_text[heading.start() : end])
        if not statuses:
            continue
        number = f"{heading.group(1)}.{heading.group(2)}"
        prefix = f"{heading.group(1)}-{heading.group(2)}-"
        keys = [key for key in ledger if key.startswith(prefix)]
        if not keys:
            problems.append(f"Story {number}: epics Status {statuses[-1]!r} but no ledger key starts {prefix!r}")
            continue
        words = statuses[-1].split()
        epics_status = words[0] if words else ""
        if epics_status != ledger[keys[0]]:
            problems.append(f"Story {number}: epics Status {epics_status!r} != ledger {ledger[keys[0]]!r} ({keys[0]})")
    return problems


def test_status_line_matching_the_ledger_is_clean() -> None:
    epics = "### Story 1.1: a\n\n**Status:** done - verified against X\n\n### Story 1.2: b\n\nno status line\n"
    ledger = {"1-1-a": "done", "1-2-b": "backlog"}

    assert epics_status_mismatches(epics, ledger) == []


def test_lagging_blocked_and_unkeyed_status_lines_are_each_named() -> None:
    epics = (
        "### Story 2.1: a\n**Status:** backlog\n\n"
        "### Story 2.2: b\n**Status:** blocked\n\n"
        "### Story 2.3: c\n**Status:** done\n"
    )
    ledger = {"2-1-a": "done", "2-2-b": "backlog"}

    problems = epics_status_mismatches(epics, ledger)

    assert len(problems) == 3
    assert "Story 2.1" in problems[0] and "'done'" in problems[0]
    assert "Story 2.2" in problems[1] and "'backlog'" in problems[1]
    assert "Story 2.3" in problems[2] and "no ledger key" in problems[2]


def test_ledger_statuses_reads_comments_and_ignores_header_rows() -> None:
    text = "# stories: 2\ndevelopment_status:\n  1-1-a: done  # note\n  epic-1: done\n  1-2b-c: in-progress\n"

    assert ledger_statuses(text) == {"1-1-a": "done", "1-2b-c": "in-progress"}


@pytest.mark.skipif(not PLANNING.is_dir(), reason="the pyforge-doctor planning tree is not in this checkout")
def test_live_tree_every_doctor_epics_status_matches_the_ledger() -> None:
    epics = (PLANNING / "epics.md").read_text(encoding="utf-8")
    ledger = ledger_statuses((PLANNING / "sprint-status-ledger.yaml").read_text(encoding="utf-8"))

    assert ledger, "the tracked ledger parsed to no story rows"
    assert epics_status_mismatches(epics, ledger) == []
