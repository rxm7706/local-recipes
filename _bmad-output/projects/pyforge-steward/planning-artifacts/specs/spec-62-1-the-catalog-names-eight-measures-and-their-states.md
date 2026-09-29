---
title: '62.1: The catalog names eight measures and their states'
type: 'docs'
created: '2026-09-19'
status: 'done'
baseline_revision: '0c11f7f4205d492ae8ce91e99405d943ec835ffe'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred:
  - summary: >-
      The "First cut (all `on`, 2026-09-15)" section heading in measure-catalog.md
      duplicates the new per-row `State` values with nothing forcing the heading to
      update once Story 62.2's add/switch/archive config flips an individual row.
    evidence: |-
      Real future-maintenance risk once a row's state diverges from "all on", but the
      heading text is untouched pre-existing content (outside this diff's hunk) and
      the update mechanism belongs to Story 62.2, which is explicitly out of scope
      for 62.1's Boundaries & Constraints.
    location: >-
      _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-build-league-scorecard/measure-catalog.md:7
    severity: medium
  - summary: >-
      `spec-pyforge-steward/SPEC.md` CAP-44/45/46 already read "(shipped 2026-09-15)"
      ahead of Epic 62's actual landing, and their `success` bullets are truncated
      mid-sentence.
    evidence: |-
      Confirmed by direct read: CAP-44/45/46 all carry a premature "(shipped
      2026-09-15)" annotation and each `success` bullet ends mid-sentence (e.g. CAP-44:
      "the eight first-cut ids are in `measure-catalog.md` and"). Pre-existing defect in
      a different file, not caused by this diff; not this story's surface to fix.
    location: >-
      _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md:253-261
    severity: medium
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** Q5 (the operating-model measure question) named the human/agent/team
dimensions but published no numbers: the companion catalog already lists all eight
already-counted signals with a dimension and a source, but each row's `on`/`off`/
`archived` state is only implied by a section heading, never a per-row field a
consumer or a later story can read.

**Approach:** Add an explicit `State` column to the Registry/First-cut table in the
Spec companion `measure-catalog.md`, valued `on` for all eight rows, so the catalog
publishes dimension, source, and state per id rather than state-by-heading.

## Boundaries & Constraints

**Always:**
- Eight ids published with dimension, source, and state, one row each.
- First cut is all `on`.
- Cite `spec-build-league-scorecard CAP-1`; do not flip any Epic 44 `blocked` ledger key.

**Never:**
- Do not invent a ninth measure, a weight, a composite, or a league total.
- Do not build the add/switch/archive config mechanics (Story 62.2) or the
  consumer refuse path (Story 62.3) here.
- Do not touch Hub Outcome Guards — they read this catalog later, not in this epic.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| catalog published | `measure-catalog.md` registry table | eight rows, each with id, Dimension, Source, and State = `on` | n/a |

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-build-league-scorecard/measure-catalog.md` -- companion catalog; already has `id` / `Dimension` / `Source (already counted)` / `Notes` columns and all eight measures under "First cut (all `on`, 2026-09-15)", but state is only asserted by that heading, not a per-row column -- add an explicit `State` column, `on` for every row.
- `docs/dreams/pyforge-unifying-strategy.md:79-83` -- Q5 entry already cites this catalog path (published 2026-09-15) -- no change needed.
- `docs/dreams/build-league-scorecard.md` -- archived/folded Dream; already documents the three states and the all-`on` first cut in prose -- no change needed.

## Tasks & Acceptance

**Execution:**
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-build-league-scorecard/measure-catalog.md` -- add a `State` column to the Registry/First-cut table, `on` for all eight rows -- makes "published with dimension, source, and state" literally true per row instead of only implied by the section heading, and gives Story 62.2's later config flip a concrete field to act on.

**Acceptance Criteria:**
- Given the catalog before this story, when read, then state is asserted only by a section heading, never a per-row field.
- Given this story lands, when `measure-catalog.md` is read, then all eight rows publish `id`, `Dimension`, `Source`, and an explicit `State` column valued `on`.
- Given the published catalog, when a consumer looks up any of the eight ids, then dimension, source, and state are all present on that row without inventing or reading a substitute field.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- expected: pass (docs-only change; station `verify_commands` regression check, MRS-GATE-010).

**Manual checks (if no CLI):**
- `measure-catalog.md`'s registry table has 8 data rows, each with non-empty `id` / `Dimension` / `Source` / `State` columns, and `State` = `on` for all eight.

## Review Triage Log

### 2026-09-19 — Review pass
- verdicts: 8 findings — high 0, medium 2, low 0, false 6, maybe-false 0
- findings:
  - `[false]` `[reject]` blind-hunter: ledger key `62-1-the-catalog-names-eight-measures-and-their-states` and epics.md Story 62.1's `**Status:**` line both stay `backlog`, not flipped to `done` in this commit — refuted: ledger promotion is a separate, tool-driven `sprint-ledger-sync` commit authored by marshal, never bundled into the implementation commit itself (git history precedent: Story 60.1's landing commit is followed by its own later `marshal: promote sprint-status ledger` commit); epics.md's inline `**Status:**` field is not kept in sync either — Stories 63.1/63.2 are already `done` in the ledger yet still read `**Status:** backlog` in epics.md.
  - `[false]` `[reject]` intent-alignment: same claim, framed as a divergence between the ledger surface and the content surface — same refutation as the row above.
  - `[false]` `[reject]` blind-hunter: no memlog entry was appended to `spec-build-league-scorecard/.memlog.md` for this edit — refuted: `pixi run -e pyforge-guild spec-surface-check` exits 0 ("no drift"); the baseline's `files` set for `pyforge-steward/spec-build-league-scorecard` is empty (no file hashes tracked for this Spec), and the Spec's own `SPEC.md` declares `status: absorbed` with companion documents kept only "as record" — no active surface-reconcile obligation attaches to this file under a disposed Spec.
  - `[false]` `[reject]` intent-alignment: same claim, framed as a divergence between the memlog/spec-surface reconcile expectation and the content edit — same refutation as the row above.
  - `[medium]` `[defer]` blind-hunter: the section heading `## First cut (all \`on\`, 2026-09-15)` duplicates the new per-row `State` values and has no mechanism forcing it to update once Story 62.2's add/switch/archive config lets an operator flip an individual row — real future-maintenance risk, recorded in frontmatter `deferred`; the heading is untouched pre-existing text and its update mechanism is explicitly Story 62.2's scope, out of scope for 62.1.
  - `[medium]` `[defer]` blind-hunter: `spec-pyforge-steward/SPEC.md` CAP-44/45/46 already read "(shipped 2026-09-15)" ahead of Epic 62's actual landing, and CAP-44/45/46's `success` bullets are truncated mid-sentence — real pre-existing accuracy/governance defect in a different file, not caused by this diff, recorded in frontmatter `deferred`.
  - `[false]` `[reject]` blind-hunter: the new `State` values aren't tied to a documented closed vocabulary — refuted: the file's own "Registry" section, immediately above the edited table and untouched by this diff, already documents the exact three-state vocabulary (`on`/`off`/`archived`) governing the whole file.
  - `[false]` `[reject]` intent-alignment: the verification command (`pyforge-steward-test`) would pass regardless of this table's content, diverging from a hypothetical "Reading C" where publication is machine-checked — refuted: Story 62.1 is `Type: docs`; both the pre-existing Tier-2 planning spec and this run's own implementation spec deliberately scope Verification to the station regression suite plus a manual inspection (already performed and passing), matching the Matrix Test Audit's acceptance of a manual check for a non-code-consumed doc row — nothing in the intent selects "Reading C" over that documented, deliberate design.

## Binding

Parent Spec capability: `spec-build-league-scorecard CAP-1`.
Surface: _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-build-league-scorecard/measure-catalog.md; docs/dreams/pyforge-unifying-strategy.md Q5 cite..
Ledger key: `62-1-the-catalog-names-eight-measures-and-their-states`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-62-1-the-catalog-names-eight-measures-and-their-states.md`.

## Auto Run Result

**Summary of implemented change:** Added an explicit `State` column to the Registry/First-cut table in the Spec companion `measure-catalog.md`, valued `on` for all eight already-counted measures (`warden-verdict`, `owner-work-class`, `gate-record-outcomes`, `journal-timing`, `run-cost-usd`, `ledger-throughput`, `detector-pass-fail`, `five-tier-completeness`), so the catalog publishes dimension, source, and state per row rather than state-by-heading.

**Files changed:**
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-build-league-scorecard/measure-catalog.md` -- added a `State` column to the First-cut table, `on` for all eight rows.

**Review findings breakdown:**
- Patched: 0 (high 0, medium 0, low 0).
- Deferred: 2 medium (stale "all `on`" heading once Story 62.2 lands; premature "(shipped 2026-09-15)" + truncated success bullets on `spec-pyforge-steward/SPEC.md` CAP-44/45/46) — both pre-existing, not caused by this diff; recorded in frontmatter `deferred`.
- Rejected (false): 6 — ledger/status-flip expectation (×2, blind-hunter + intent-alignment), memlog-entry expectation (×2, blind-hunter + intent-alignment), undocumented state-vocabulary claim, and non-binding-verification claim. Reasons recorded per-row in the Review Triage Log above.

**Follow-up review recommendation:** `false` (default; no entry was patched this pass, so the patch-volume trigger never applies).

**Verification performed:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- exit 0, 1443 passed, 4 skipped (read directly, not through a pipe).
- Manual check: `measure-catalog.md`'s First-cut table re-read after the edit — 8 data rows, each with non-empty `id` / `Dimension` / `Source` / `State`, `State` = `on` for all eight.
- Diff staged against `baseline_revision` and read directly (`git diff 0c11f7f4205d492ae8ce91e99405d943ec835ffe`): exactly one file, one hunk, matches the Tasks & Acceptance section verbatim.

**Residual risks:** The two deferred findings above (stale heading; premature Spec-status annotations) are real but pre-existing and out of this story's scope — worth a future pass (naturally Story 62.2, or a Spec-hygiene pass on `spec-pyforge-steward/SPEC.md`) but not blocking for 62.1.
