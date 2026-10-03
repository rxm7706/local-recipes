---
title: '66.2: Every landed follow-up recommendation is backfilled and held by a meta test'
type: 'chore'
created: '2026-09-28'
status: 'ready-for-dev'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-66-1-finalize-carries-a-recommended-follow-up-review-into-the-deferred-work-ledger.md
  - docs/dreams/pyforge-marshal.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Story 66.1 carries a recommended follow-up review from the moment it lands, but every story that already landed `done` with `followup_review_recommended: true` stays uncarried. Measured 2026-09-28 with marshal's own parsers over the 1,583 tracked story specs: 210 read `done` with the flag true. Of those, 28 are carried by a bmad-loop damping row (Story 4.13's `DW-FU-<story>`, whose tracked text names no `origin:`), 51.2 by the hand-filed `DW-FU-51-2-1`, and 181 by nothing. 48 of the 210 landed through the `factory dispatch` era's merge forms on `origin/main`. Without a backfill and a check that holds it, the next hand landing of a flagged spec is lost the same way.

**Approach:**
- One pass renders a `DW-FRR-<story>` row with 66.1's renderer into the story's own project's tracked `deferred-work-ledger.md`, for every `done`-and-flagged tracked spec that no row carries.
- `status: open` when `origin/main` shows the story's landing as `Merge <slug>/<key> into main` or a `dispatch/<slug>/<key>` branch merge (the `factory dispatch` era, hand landings included). Otherwise `status: closed`, with the reason on the row: a bmad-loop wave landing, where the loop's own follow-up budget governed the recommendation. So no row asserts that a review never ran where the repository cannot show it.
- Each of the 28 loop damping carries gains one `origin: review-budget-followup` line, and `core/deferred_work.render_ledger_entry` writes that line from then on, so a future loop carry is recognised too.
- `DW-FU-51-2-1` closes, superseded by `DW-FRR-51-2` (open), which the backfill mints like any other.
- A new meta test holds the invariant over the whole repository: every tracked story spec under `_bmad-output/projects/*/planning-artifacts/specs/` that reads `status: done` with the flag true (parsed with `core/dispatch_harness_done`) has, in its own project's tracked ledger, a row whose `source_spec:` names the spec's filename and whose `origin:` is `dispatch-followup-review` or `review-budget-followup`. A failure names each orphan and its project. A spec whose flag a later follow-up cleared is not in scope: bmad-build-auto writes `false` before its one follow-up pass and forces `false` at that pass's halt.
- The rows land in all eight stations' ledgers. pyforge-atlas's ledger is governed by `spec-pyforge-atlas`, so its path is named on that Spec's memlog (`spec-surface`); the other seven are allowlisted. Epic 66's `[epic_surfaces]` entry admits all eight ledgers and that memlog.

Ledger key: `66-2-every-landed-follow-up-recommendation-is-backfilled-and-held-by-a-meta-test`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: chore / M / S-66.1 (the `DW-FRR-<story>` renderer and id).

### Living CAP citations

- `spec-pyforge-marshal` CAP-275 (FR-221).
- `spec-pyforge-atlas` — co-governor of `_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md` (surface reconcile only; no atlas capability changes).

## Acceptance Criteria

- Given the tree after the backfill When `tests/meta/test_followup_review_carried.py` runs Then it finds no `done`-and-flagged tracked spec, in any of the eight projects, without a carrying row in its own project's ledger
- Given a fixture tree with one `done`-and-flagged spec and no carrying row When the meta test's predicate runs over it Then it reports that spec and its project; with a `dispatch-followup-review` row naming the spec it reports nothing; with a `review-budget-followup` row naming it, nothing; with a row naming it under any other `origin:`, the spec is still reported
- Given each backfilled row When it is read Then it was rendered by 66.1's renderer, names the spec in `source_spec:` and the landing evidence in `evidence:`, and reads `status: open` for a `Merge <slug>/<key> into main` or `dispatch/<slug>/<key>` landing on `origin/main`, `closed` with its reason otherwise
- Given the 28 loop damping carries When the backfill runs Then each gains exactly one `origin: review-budget-followup` line and no other change; `render_ledger_entry`'s output carries that line and `test_deferred_work.py` pins it
- Given `DW-FU-51-2-1` When the backfill lands Then it reads closed, superseded by `DW-FRR-51-2`, and `DW-FRR-51-2` reads open
- Given the backfilled ledgers When `pixi run -e pyforge-guild deferred-work-check` and `pixi run -e pyforge-guild spec-surface-check` run Then both exit 0

## Boundaries & Constraints

**Always:** Implement only the Surface named in `epics.md` Story 66.2. Render every row with Story 66.1's renderer (one row shape, one id). Append rows; the only edits to an existing row are one added `origin:` line (loop carries) and `DW-FU-51-2-1`'s status and story pointer. Reconcile the atlas ledger on `spec-pyforge-atlas`'s memlog before any scoped stamp, and stamp only the Specs the detector names.

**Never:**
- Do not rewrite an existing row's summary, evidence or id.
- Do not mint a row for a spec whose flag is false or absent, or whose status is not `done`.
- Do not mark a backfilled row `open` for a landing the repository cannot show as a `factory dispatch`-era merge.
- Do not change `scripts/deferred_work_intake.py`, doctor's `deferred-work` source, or any station's code other than `core/deferred_work.py`.
- Do not keep a backfill script in the tree; the rows and the meta test are the durable record.
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`; do not run `scripts/bmad-switch`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| dispatch-era landing, uncarried | `Merge <slug>/<key> into main` on `origin/main` | `DW-FRR-<story>` row, `status: open` | none |
| loop-era landing, uncarried | no dispatch-era merge form | `DW-FRR-<story>` row, `status: closed` with its reason | none |
| loop damping carry | `DW-FU-<story>` row promoted by Story 4.13 | gains `origin: review-budget-followup` | none |
| 51.2 | hand-filed `DW-FU-51-2-1` | `DW-FRR-51-2` open; `DW-FU-51-2-1` closed, superseded | none |
| flag later cleared | flag `false` after a follow-up | out of scope; no row | none |
| planted orphan | `done` + flag, no carrying row | meta test fails naming spec and project | none |
| row under another origin | `source_spec` names the spec, `origin:` something else | still an orphan | none |

</intent-contract>

## Source

Contract authored from `docs/dreams/pyforge-marshal.md`'s 2026-09-19 (the third drain, in flight) Realization-log entry, item (5), and `spec-pyforge-marshal` CAP-275 with its 2026-09-28 direction entry in the Spec's `.memlog.md` (the measurements and decision (6)), decomposed the same session as Epic 66's mint.

## Binding

Parent Spec capability: `spec-pyforge-marshal` CAP-275 (FR-221).
Dream: `docs/dreams/pyforge-marshal.md` § Realization log → *2026-09-19 (the third drain, in flight)*, item (5), and its *Decomposed 2026-09-28* note.
Ledger key: `66-2-every-landed-follow-up-recommendation-is-backfilled-and-held-by-a-meta-test`.
Ledger status at mint: `backlog`.
Deferred-work row closed by this story: `DW-FU-51-2-1`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Manual checks:**
- `pixi run -e pyforge-guild deferred-work-check` — exit 0.
- `pixi run -e pyforge-guild spec-surface-check` — exit 0 (the atlas ledger reconciled on `spec-pyforge-atlas`'s memlog).
