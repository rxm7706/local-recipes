"""Unit tests for ``pyforge.doctor.sources.backlog_intake`` (Story 13.1) --
covers every row of the spec's I/O & Edge-Case Matrix against REAL tmp
fixture trees, mirroring ``test_sources_chain_deferred_work.py``'s own
real-fixture (no git needed) discipline.

The two adversarial collision cases (epic "1" vs. an entry naming only
"Epic 11"; story "13.1" vs. an entry naming only "Story 13.10") are THE
CORE of this story -- see their own dedicated test functions below, named
so a `pytest -k` selection finds them directly.
"""

from __future__ import annotations

from pathlib import Path

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import backlog_intake

# --- fixture helpers ---------------------------------------------------------


def _write_ledger(target: Path, project: str, text: str) -> Path:
    path = target / "_bmad-output" / "projects" / project / "planning-artifacts" / "deferred-work-ledger.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# --- parse_identifier ---------------------------------------------------------


def test_parse_identifier_accepts_bare_epic_number():
    parsed = backlog_intake.parse_identifier("13")
    assert parsed == backlog_intake.ParsedIdentifier(epic=13, story=None)


def test_parse_identifier_accepts_epic_prefixed_case_insensitive():
    assert backlog_intake.parse_identifier("Epic 13") == backlog_intake.ParsedIdentifier(epic=13, story=None)
    assert backlog_intake.parse_identifier("epic 13") == backlog_intake.ParsedIdentifier(epic=13, story=None)


def test_parse_identifier_accepts_dotted_story_id():
    assert backlog_intake.parse_identifier("13.1") == backlog_intake.ParsedIdentifier(epic=13, story=1)


def test_parse_identifier_accepts_kebab_story_id():
    assert backlog_intake.parse_identifier("13-1") == backlog_intake.ParsedIdentifier(epic=13, story=1)


def test_parse_identifier_accepts_story_prefixed_case_insensitive():
    assert backlog_intake.parse_identifier("Story 13.1") == backlog_intake.ParsedIdentifier(epic=13, story=1)
    assert backlog_intake.parse_identifier("story 13-1") == backlog_intake.ParsedIdentifier(epic=13, story=1)


def test_parse_identifier_accepts_trailing_lowercase_letter():
    assert backlog_intake.parse_identifier("13.1a") == backlog_intake.ParsedIdentifier(epic=13, story=1)


def test_parse_identifier_rejects_unparseable_text():
    assert backlog_intake.parse_identifier("not-an-id") is None


def test_parse_identifier_rejects_empty_and_whitespace_only():
    assert backlog_intake.parse_identifier("") is None
    assert backlog_intake.parse_identifier("   ") is None


def test_parse_identifier_never_raises_on_non_string_input():
    assert backlog_intake.parse_identifier(None) is None  # type: ignore[arg-type]
    assert backlog_intake.parse_identifier(13) is None  # type: ignore[arg-type]


def test_parse_identifier_rejects_mismatched_keyword_and_shape():
    # "Epic " only pairs with a bare number; "Story " only pairs with the
    # dotted/kebab shape -- a mismatch is unparseable, not silently coerced.
    assert backlog_intake.parse_identifier("Epic 13.1") is None
    assert backlog_intake.parse_identifier("Story 13") is None


# --- Epic-level match -----------------------------------------------------


def test_epic_level_query_matches_an_entry_naming_the_bare_epic(tmp_path: Path):
    _write_ledger(
        tmp_path,
        "doctor",
        "## DW-1: some entry\nstatus: open\nsummary: touches Epic 13 directly.\n",
    )

    findings = backlog_intake.gather(tmp_path, identifier="13")

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.BACKLOG_INTAKE
    assert finding.check == "backlog-intake"
    assert finding.status is DoctorStatus.WARN
    assert finding.evidence["entry_id"] == "DW-1"
    assert finding.evidence["matched"] == "Epic 13"
    assert finding.evidence["status"] == "open"


def test_epic_level_query_also_matches_any_story_under_it(tmp_path: Path):
    """An epic-only query matches `Epic N` bare AND any `Story N.<digits>`
    under it -- an entry naming only a story, never the bare epic."""
    _write_ledger(
        tmp_path,
        "doctor",
        "## DW-2: some entry\nsummary: closes once Story 13.5 lands.\n",
    )

    findings = backlog_intake.gather(tmp_path, identifier="13")

    assert len(findings) == 1
    assert findings[0].evidence["matched"] == "Story 13.5"


def test_epic_level_query_also_matches_a_kebab_story_under_it(tmp_path: Path):
    """Review finding: the epic-only branch used to check only the dotted
    `Story N.<digits>` form, missing a kebab `Story N-<digits>` reference --
    an asymmetry with the story-level query below, which has always
    accepted both forms. Symmetric coverage now."""
    _write_ledger(
        tmp_path,
        "doctor",
        "## DW-15: some entry\nsummary: closes once Story 13-5 lands.\n",
    )

    findings = backlog_intake.gather(tmp_path, identifier="13")

    assert len(findings) == 1
    assert findings[0].evidence["matched"] == "Story 13-5"


def test_entry_naming_both_epic_and_story_yields_exactly_one_finding(
    tmp_path: Path,
):
    _write_ledger(
        tmp_path,
        "doctor",
        "## DW-11-8-1: split out of Epic 11\n"
        "summary: the capability re-emerged and Epic 13 / Story 13.1 in "
        "`epics.md`, cleared to dispatch.\n"
        "status: resolved -- closes once Story 13.1 lands.\n",
    )

    findings = backlog_intake.gather(tmp_path, identifier="13.1")

    assert len(findings) == 1
    assert findings[0].evidence["entry_id"] == "DW-11-8-1"


# --- Story-level exact match -----------------------------------------------


def test_story_level_dotted_query_matches_dotted_and_kebab_prose(tmp_path: Path):
    _write_ledger(tmp_path, "doctor", "## DW-3: dotted\nsummary: needs Story 13.1.\n")
    _write_ledger(tmp_path, "warden", "## DW-4: kebab\nsummary: needs Story 13-1.\n")

    findings = backlog_intake.gather(tmp_path, identifier="13.1")

    assert {f.evidence["entry_id"] for f in findings} == {"DW-3", "DW-4"}
    assert {f.evidence["matched"] for f in findings} == {"Story 13.1", "Story 13-1"}


def test_story_level_kebab_query_matches_dotted_and_kebab_prose(tmp_path: Path):
    _write_ledger(tmp_path, "doctor", "## DW-3: dotted\nsummary: needs Story 13.1.\n")
    _write_ledger(tmp_path, "warden", "## DW-4: kebab\nsummary: needs Story 13-1.\n")

    findings = backlog_intake.gather(tmp_path, identifier="13-1")

    assert {f.evidence["entry_id"] for f in findings} == {"DW-3", "DW-4"}


def test_story_level_query_also_matches_the_bare_parent_epic(tmp_path: Path):
    _write_ledger(tmp_path, "doctor", "## DW-5: parent only\nsummary: blocks on Epic 13.\n")

    findings = backlog_intake.gather(tmp_path, identifier="13.1")

    assert len(findings) == 1
    assert findings[0].evidence["matched"] == "Epic 13"


def test_story_level_query_matches_a_lettered_sub_story(tmp_path: Path):
    _write_ledger(
        tmp_path,
        "doctor",
        "## DW-6: lettered\nsummary: needs Story 13.1a specifically.\n",
    )

    findings = backlog_intake.gather(tmp_path, identifier="13.1")

    assert len(findings) == 1
    assert findings[0].evidence["matched"] == "Story 13.1a"


# --- Collision guard: THE CORE of this story -------------------------------


def test_epic_1_query_does_not_match_epic_11_prose(tmp_path: Path):
    """Adversarial check named in the story's own Verification section: a
    synthetic ledger entry whose only epic reference is "Epic 11" must
    produce ZERO matches when queried for epic "1" -- a boundary regex,
    never a bare substring test (DW-CHAIN-COMPLETENESS-1's failure class)."""
    _write_ledger(
        tmp_path,
        "doctor",
        "## DW-7: unrelated\nsummary: split out of Epic 11, nothing else.\n",
    )

    findings = backlog_intake.gather(tmp_path, identifier="1")

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK
    assert findings[0].evidence == {"identifier": "1", "matches": 0}


def test_story_13_1_query_does_not_match_story_13_10_prose(tmp_path: Path):
    """Adversarial check named in the story's own Verification section: a
    synthetic ledger entry whose only story reference is "Story 13.10" must
    produce ZERO matches when queried for story "13.1"."""
    _write_ledger(
        tmp_path,
        "doctor",
        "## DW-8: unrelated\nsummary: depends on Story 13.10, nothing else.\n",
    )

    findings = backlog_intake.gather(tmp_path, identifier="13.1")

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK
    assert findings[0].evidence == {"identifier": "13.1", "matches": 0}


# --- No matches anywhere ----------------------------------------------------


def test_no_matches_anywhere_reports_ok(tmp_path: Path):
    _write_ledger(tmp_path, "doctor", "## DW-9: irrelevant\nsummary: about Epic 5 only.\n")

    findings = backlog_intake.gather(tmp_path, identifier="13")

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK
    assert findings[0].check == "backlog-intake"
    assert findings[0].evidence == {"identifier": "13", "matches": 0}


# --- Unparseable identifier --------------------------------------------------


def test_unparseable_identifier_reports_one_warn_naming_it(tmp_path: Path):
    findings = backlog_intake.gather(tmp_path, identifier="not-an-id")

    assert len(findings) == 1
    finding = findings[0]
    assert finding.status is DoctorStatus.WARN
    assert finding.check == "backlog-intake"
    assert "not-an-id" in finding.message
    assert finding.evidence == {"identifier": "not-an-id"}


# --- Ledger unreadable -------------------------------------------------------


def test_unreadable_ledger_is_skipped_and_scan_continues(tmp_path: Path):
    # "doctor"'s own ledger path exists but is a DIRECTORY, not a file --
    # read_text() raises IsADirectoryError (an OSError), which must be
    # absorbed, not propagated -- and the scan must still find the real
    # match in "warden"'s own (readable) ledger.
    unreadable = tmp_path / "_bmad-output" / "projects" / "doctor" / "planning-artifacts" / "deferred-work-ledger.md"
    unreadable.mkdir(parents=True)
    _write_ledger(tmp_path, "warden", "## DW-10: readable\nsummary: names Epic 13.\n")

    findings = backlog_intake.gather(tmp_path, identifier="13")

    assert len(findings) == 1
    assert findings[0].evidence["entry_id"] == "DW-10"
    assert findings[0].evidence["ledger"] == str(
        Path("_bmad-output/projects/warden/planning-artifacts/deferred-work-ledger.md")
    )


# --- No tracked ledgers exist at all ----------------------------------------


def test_no_tracked_ledgers_at_all_reports_ok(tmp_path: Path):
    findings = backlog_intake.gather(tmp_path, identifier="13")

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK
    assert findings[0].evidence == {"identifier": "13", "matches": 0}


# --- Evidence shape -----------------------------------------------------------


def test_match_evidence_carries_summary_from_em_dash_heading(tmp_path: Path):
    _write_ledger(
        tmp_path,
        "doctor",
        "## DW-1-1-1 — The loop's exact command, unfrozen\nstatus: open\nsummary: names Epic 13 in passing.\n",
    )

    findings = backlog_intake.gather(tmp_path, identifier="13")

    assert findings[0].evidence["summary"] == ("The loop's exact command, unfrozen")


def test_match_evidence_carries_summary_from_colon_heading(tmp_path: Path):
    _write_ledger(
        tmp_path,
        "doctor",
        "### DW-FU-6-4: Follow-up review still recommended\nsummary: names Epic 13 in passing.\n",
    )

    findings = backlog_intake.gather(tmp_path, identifier="13")

    assert findings[0].evidence["summary"] == "Follow-up review still recommended"


def test_match_evidence_status_defaults_to_empty_string_when_absent(
    tmp_path: Path,
):
    _write_ledger(tmp_path, "doctor", "## DW-11: no status line\nsummary: names Epic 13.\n")

    findings = backlog_intake.gather(tmp_path, identifier="13")

    assert findings[0].evidence["status"] == ""


def test_multi_project_matches_are_all_reported_independently(tmp_path: Path):
    _write_ledger(tmp_path, "doctor", "## DW-12: doctor entry\nsummary: names Epic 13.\n")
    _write_ledger(tmp_path, "mason", "## DW-13: mason entry\nsummary: names Epic 13 too.\n")
    _write_ledger(tmp_path, "steward", "## DW-14: unrelated\nsummary: names Epic 5 only.\n")

    findings = backlog_intake.gather(tmp_path, identifier="13")

    assert len(findings) == 2
    assert {f.evidence["entry_id"] for f in findings} == {"DW-12", "DW-13"}
    assert all(f.status is DoctorStatus.WARN for f in findings)


def test_gather_never_raises_on_a_completely_empty_target(tmp_path: Path):
    empty = tmp_path / "definitely-empty"
    empty.mkdir()

    findings = backlog_intake.gather(empty, identifier="13")

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


def test_gather_never_raises_when_target_is_a_file_not_a_directory(tmp_path: Path):
    # Review finding: Path.glob() on a non-directory `self` has a
    # documented history of varying by Python version. Pinned to this
    # package's own interpreter, it degrades to zero matches -- proven
    # here rather than left as an open question, and this test is the
    # guard against a future interpreter bump silently reintroducing a
    # raise (the module's own "degrades, never crashes" house rule).
    a_file = tmp_path / "not-a-directory.txt"
    a_file.write_text("not a directory", encoding="utf-8")

    findings = backlog_intake.gather(a_file, identifier="13")

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


def test_gather_never_raises_when_target_does_not_exist(tmp_path: Path):
    missing = tmp_path / "does-not-exist-at-all"

    findings = backlog_intake.gather(missing, identifier="13")

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK
