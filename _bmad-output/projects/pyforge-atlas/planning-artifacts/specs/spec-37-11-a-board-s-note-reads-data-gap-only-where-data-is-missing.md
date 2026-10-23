---
title: "37.11: A board's note reads \"Data gap\" only where data is missing"
type: 'fix'
created: '2026-10-22'
status: 'done'
baseline_revision: 'ab50b079a8c8d68d364570b96e01cdd788885ac6'
review_loop_iteration: 2
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - docs/dreams/pyforge-atlas.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/app.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/static_export.py
deferred: []
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** after Story 37.4, the Pages export shows 21 of 34 boards with data. `dashboard/app.py` labels every
`PageDef.note` "**Data gap:**", both in `_legibility_card` and in the identity-workbook page. So behind-upstream's 95
rows sit under "**Data gap:** Wired to `build_behind_upstream_model` over `derived_behind_upstream`…". Most notes now
describe how a board's data is wired. Only three cases are gaps:
- a shell page, which has no data function;
- the identity workbook's `gap_message`;
- a page whose own dataset is unavailable, as its AD-17 stamp line already says.

**Approach:**
1. `app.NOTE_LABEL = "About this board"` and `app.GAP_LABEL = "Data gap"`. `_note_label(has_data, provenance)` returns
   the gap label when the page has no data function or its provenance is `unavailable`, else the note label.
2. `_legibility_card` gains `has_data` (default `True`); `_shell_page` passes `False`. The identity workbook keeps the
   gap label for `gap_message` and labels its note by provenance.
3. `static_export` drops a live-scan note under either label.

Ledger key: `37-11-a-board-s-note-reads-data-gap-only-where-data-is-missing`.
Type / Effort / Deps: fix / XS / —.

### Living CAP citations

- `spec-pyforge-atlas` CAP-63 (FR-71, the boards and their Pages export) and CAP-69 (FR-77, the boards no pipeline fed):
  the label is part of each board's legibility card. A defect, so no new CAP; a fix needs no flag
  (`spec-feature-flag-governance` Q1). AD-17's stamp line is unchanged and stays the authority on availability.

## Acceptance Criteria

- **AC1 — Data.** A note on a page with a data function and an available dataset reads "**About this board:**".
- **AC2 — Gaps.** A shell page's note, the identity workbook's `gap_message`, and a note on a page whose provenance is
  unavailable read "**Data gap:**".
- **AC3 — Export.** The static export drops a live-scan note under either label.
- **AC4 — Unchanged.** No board's data, note text or stamp changes; the atlas unit tests and the dashboard
  integration tests pass.

## Boundaries & Constraints

**Never:** Rename a `PageDef`, change a note's text, or decide availability anywhere but AD-17 provenance and the
page's kind.

**Residual risk:**
- A dataset that exists but holds zero rows still reads "About this board": availability is the file, not its row
  count. The board's grid then shows no rows, and its stamp is a real one.

## I/O & Edge-Case Matrix

| Page | Provenance | Label |
|------|------------|-------|
| data page (grid fed by a loader) | stamped | About this board |
| data page | unavailable | Data gap |
| shell page (no data function) | any | Data gap |
| identity workbook with `gap_message` | any | Data gap (the message) |
| identity workbook, no `gap_message` | stamped | About this board |
| live-scan page, static export | any | note dropped |

</intent-contract>

## Binding

- Parent Spec capabilities: `spec-pyforge-atlas` CAP-63, CAP-69. No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-22 entry (filled boards still read "Data gap").
- Epic: Epic 37 (in progress). Story 37.11 is minted `done`.
- Ledger key: `37-11-a-board-s-note-reads-data-gap-only-where-data-is-missing`; status at mint `done`.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas pyforge-atlas-test` — expected: pass.
- From the repo root, the dashboard unit and integration files:
  `tests/unit/test_dashboard_app.py`, `tests/unit/test_dashboard_static_export.py`,
  `tests/integration/dashboard/test_dashboard_dryrun.py` under `src/shared/packages/pyforge-atlas/` — expected: pass.

## Run results

Run 2026-10-22 in the landing worktree on `ab50b079a8`, every verdict read from its exit code.

- **AC1–AC4, tests:** `test_dashboard_app.py`, `test_dashboard_static_export.py` and
  `integration/dashboard/test_dashboard_dryrun.py`: 122 passed (exit 0). Three tests are new: a note on a page with
  available data, a shell page's note, and a live-scan note under the new label in the export.
- **Mutations**, each restored, each failing a named test:
  - `_note_label` always returns the gap label: `test_note_on_a_page_with_available_data_is_not_a_gap`;
  - always the note label: `test_note_on_a_page_with_no_data_function_is_a_gap`,
    `test_legibility_card_includes_note_when_present` and the dryrun's `test_no_bsl_shell_pages_state_the_gap_without_data`;
  - provenance ignored: `test_legibility_card_includes_note_when_present`;
  - the export strips only the gap label: `test_a_live_scan_note_is_dropped_under_either_label`;
  - after the review, the identity workbook's gap message labelled with the note label:
    `test_identity_workbook_gap_message_reads_data_gap`;
  - after the review, its note hardcoded back to "Data gap":
    `test_identity_workbook_page_falls_back_to_page_note_when_both_files_present`.
- **After the review fixes** (`63cb853a8a`, main `9fc4cb1c2b` merged in): the three files and `tests/integration/dashboard/` give 288 passed (exit 0);
  `pixi run -e pyforge-atlas pyforge-atlas-test` gives 3,113 passed and 20 skipped, then 103 passed (exit 0).
- **A real build:** `build_dashboard(board_projections=True)` over Story 37.2's public-run data root (it predates Story
  37.4's projections). 15 boards read "About this board", each with a stamped dataset; 15 read "Data gap", each with
  an unavailable stamp (among them behind-upstream, universe-sbom and live-catalog-coverage, whose projections that root
  lacks); 4 boards carry no note. On Pages, whose data includes 37.4's projections, those three read "About this
  board".

## Spec Change Log

- 2026-10-22, independent review (FAIL, 1 blocker), fixed on the same branch:
  - B1: the identity workbook's two label rows (AC2; matrix rows 4 and 5) were not pinned. Under either mutation all
    287 dashboard tests passed. The both-files test now asserts the note label, and
    `test_identity_workbook_gap_message_reads_data_gap` asserts the gap label; each fails under its mutation.
  - Nits: the Run results now report `pyforge-atlas-test`; the static-export fixture's default label reads
    `app.GAP_LABEL`. The `37-11` row joins the shared Tier-3 feed at landing, not before (a feed key ahead of the
    merge leaks to main).
  - Found by the full `pr-preflight`, not the review: the `ad-citation` detector flagged a bare `AD-17` in the
    unifying-strategy memlog line this story added, and the core memlog line had the same text (marshal defines its
    own AD-17, so the detector could not see it). Both now cite `pyforge-atlas:AD-17`.
- 2026-10-22: minted `done`, implemented and verified in the same change.

## Review Triage Log

- 2026-10-22, review 1 (independent subagent, read the diff against this spec): FAIL. 1 blocker (B1, the identity
  workbook's label rows unpinned), 0 should-fix, 3 nits. The reviewer ran its mutations in a scratch plugin, so no
  repo file changed. B1 and two nits fixed on the branch (Spec Change Log); the feed-row nit is closed at landing.
- 2026-10-22, review 2 (independent subagent): PASS, 0 blockers, 0 should-fix. Both B1 mutations, two more variants
  and every round-1 mutation fail a named test; the counts above re-run as stated; both memlog lines cite
  `pyforge-atlas:AD-17`. Nit applied: the after-review bullet names its commit. Nit left: the core memlog's
  `updated:` stays at its last append, since the line fix was an edit, not an append; spec-surface passes.
