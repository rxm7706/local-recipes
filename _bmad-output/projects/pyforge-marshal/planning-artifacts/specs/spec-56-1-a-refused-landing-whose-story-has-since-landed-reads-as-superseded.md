---
title: '56.1: A refused landing whose story has since landed reads as superseded'
type: 'fix'
created: '2026-09-27'
status: 'in-review'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `marshal status` projects the newest dispatch run's last `dispatch-land` OUTCOME findings onto each station's row, and `fleet-picture` turns any ERROR-severity finding into an ATTENTION line (`landing refused … -- MRS-DISP-020`). Nothing written after a landing made by another route reaches that journal, so the line stays until the station's next dispatch replaces the run. On 2026-09-25..27 doctor 30.3 (PR #1585, run `pyforge-doctor-20260924T110838338Z-84c5006a`) and marshal 46.6 (PR #1597, run `pyforge-marshal-20260925T064250213Z-f0621b0b`) both sat in ATTENTION after both PRs had merged, both refused head SHAs were ancestors of `origin/main`, and both keys read `done` in their tracked ledgers. Doctor has no backlog left, so its line would never clear.

**Approach:** keep the refusal and report the git fact beside it (AD-5 / AD-33: the journal owns process facts, git owns repository facts, a disagreement is reported, never silently reconciled). A pure `core/dispatch_landing.landing_refusal_superseded(findings, story_merged_on_main=…)` is true only when a finding is ERROR-severity and the story is on `main`. The status fleet sweep answers `story_merged_on_main` from `core.promotion.corroborated_merged_story_keys` — the check `dispatch land` already uses for ALREADY_LANDED — over `main`'s subjects, read at most once per sweep and shared with the failed-patch check, with the station's own `merge_subject_template` and the `origin/main` spec-status reader. The JSON row gains `dispatch_landing_superseded: true` beside the unchanged `dispatch_landing_findings`, and the dispatch run's own story as `dispatch_story`. The marker is a git fact only: a post-merge promote + ledger failure journals the same `MRS-DISP-020`, so "nothing owed" also needs the tracked ledger's `done`, which the status summary must not read (AD-5). `fleet-picture` — whose counts already come from the tracked ledgers — renders a marked refusal in its not-blocking list, naming `dispatch_story` as landed since, only when that story reads `done` in the station's tracked ledger; otherwise it stays in ATTENTION naming the owed promote + ledger (amended 2026-09-27, review 1).

Ledger key: `56-1-a-refused-landing-whose-story-has-since-landed-reads-as-superseded`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-266 (FR-212).

## Acceptance Criteria

- Given a station row whose newest dispatch run carries an ERROR-severity landing finding and whose story key is among `main`'s corroborated merged keys When `marshal status --format json` runs Then the row carries `dispatch_landing_superseded: true` and `dispatch_landing_findings` is byte-identical to the journal's
- Given the same refusal whose story is not on `main` When status runs Then the row carries no `dispatch_landing_superseded` key
- Given a sweep whose `main` read raises, or whose policy compose yields an ERROR finding When status runs Then no row carries the marker (the refusal stays actionable)
- Given a row whose landing findings are WARN-only When status runs Then no marker is set, whatever `main` says
- Given a marked refusal whose story reads `done` in the station's tracked ledger When `fleet-picture` runs Then ATTENTION carries no `landing refused` line for it and the not-blocking list names the dispatch run's own story (`dispatch_story`) as landed since; an unmarked refusal still renders `landing refused` in ATTENTION exactly as before
- Given a marked refusal whose ledger key is not `done` (a post-merge promote + ledger failure) When `fleet-picture` runs Then it stays in ATTENTION, naming the owed promote + ledger
- Given a run whose completion reads `completed`, so `current_story` is not the dispatch story When status and `fleet-picture` run Then the row carries `dispatch_story` and the line names it, never `current_story`
- Given the live doctor 30.3 and marshal 46.6 rows When `fleet-picture` runs after this lands Then neither appears in ATTENTION

## Boundaries & Constraints

**Always:** Implement only the Surface named in `epics.md` Story 56.1. The marker is set only on a positive, corroborated merge; every read failure leaves it off. `main`'s subjects are read once per sweep. The decision is a pure function in `core/` (AD-4); git and policy reads stay in `cli/`.

**Never:**
- Do not delete, rewrite or re-journal a landing finding; do not change `dispatch_land.py` or the journal format.
- Do not make the marker gate anything (dispatch admission, exit codes, verdicts); it is a reported fact.
- Do not use the uncorroborated `merged_story_keys` for this decision (a mint/fix PR from a station branch is not a landing, Story 51.7 / CAP-255).
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`; do not run `scripts/bmad-switch`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| refusal, story landed since | ERROR finding; key corroborated on `main`; ledger `done` | `dispatch_landing_superseded: true`; findings unchanged; fleet-picture not-blocking line naming `dispatch_story` | none |
| post-merge finalize failure | ERROR `MRS-DISP-020` after the merge; key on `main`; ledger not `done` | marker set (git fact); fleet-picture keeps it in ATTENTION naming the owed promote + ledger | refusal stays actionable |
| refusal, story not landed | ERROR finding; key absent from `main` | no marker; ATTENTION `landing refused` | none |
| `main` unreadable | `VcsCommandError` on `commit_subjects` | no marker on any row | refusal stays in ATTENTION |
| policy ERROR for the slug | `_merged_keys_for_slug` returns an ERROR finding | no marker | refusal stays in ATTENTION |
| WARN-only landing findings | MRS-DISP-047 | no marker | unchanged not-blocking line |
| no landing findings | empty | no marker, no `main` read on their account | none |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal` CAP-266 (FR-212).
Dream: `docs/dreams/pyforge-marshal.md` § Realization log → *2026-09-27 — Proposed: a landing refusal outlives the landing*.
Ledger key: `56-1-a-refused-landing-whose-story-has-since-landed-reads-as-superseded`.
Ledger status at mint: `backlog`.
Deferred-work row closed by this story: `DW-marshal-disp020-stale-refusal-2026-09-25`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Manual checks:**
- `pixi run -e pyforge-guild fleet-picture` — the doctor 30.3 and marshal 46.6 refusals are absent from ATTENTION and named in the not-blocking list.
- `pixi run -e pyforge-marshal -- marshal status --format json` — both rows carry `dispatch_landing_superseded: true` with `dispatch_landing_findings` unchanged.

## Review Triage Log

### Review 1 — 2026-09-27, independent adversarial reviewer, commit `bd9bee9dfc` — FAIL

Read against this spec, CAP-266 and the Spec's Constraints; not against the implementer's summary.

- `[high]` `[patch]` **A post-merge finalize failure reads as "not waiting on you".** `dispatch_land.py` journals a REFUSED outcome with ERROR `MRS-DISP-020` twice over: when `gh pr merge` fails, and when the promote + ledger finalize fails *after* the PR merged. In the second case the story is on `main` under marshal's own trusted subject, so the implemented predicate (ERROR finding + key on `main`) marks it superseded, although the spec and ledger promotion never ran and the operator still owes it (the merged-story-with-`backlog`-row respawn trap). The journal payload carries no `merged` flag and both failures share one code, so `marshal status` cannot tell them apart without reading free text (AD-15). Probe: that finding plus `Merge pyforge-doctor/30-3 into main` → superseded. No test covered it. **Fix:** the completion evidence a finalize failure lacks is the tracked ledger's `done`. `marshal status` must not read story state for the fleet summary (AD-5), so the marker stays a pure git fact ("the story is on `main`") and `fleet-picture` — whose counts already come from the tracked ledgers — moves a refusal out of ATTENTION only when the marker is set AND the station's tracked ledger reads the story `done`. A marked refusal whose key is not `done` stays in ATTENTION, naming the owed finalize. CAP-266 amended through its memlog; SPEC.md re-rendered.
- `[medium]` `[patch]` **The story label names no story, or the wrong one.** `fleet-picture` took the label from `current_story`, which the overlay overwrites with the dispatch story only on a live run or a terminal dead tail. A run whose completion reads `completed` (a live supervisor, or git-recomputed `story_merged_on_main`) keeps the loop home's `current_story` — `None` ("its story"), or an unrelated loop story named as landed. The live cases passed only because both runs were `stopped_externally`. **Fix:** the row carries the dispatch run's own story as `dispatch_story`; `fleet-picture` reads it; a `completed`-verdict test.
- `[low]` `[patch]` `tests/unit/test_status.py` (the sweep-wiring class) sat outside the epics.md Surface. **Fix:** Surface amended to name it.
- `[low]` `[patch]` No test pinned the shared `main` read when a refused row and a patch-carrying home meet in one sweep. **Fix:** a sweep test asserting one `commit_subjects` call and an unchanged `MRS-STATUS-011`.
- `[low]` `[patch]` The `_landing_superseded` docstring claimed "at most one `git show`"; the reader runs once per station-branch merge naming the row's key. **Fix:** wording.
- `[low]` `[defer]` `landing_was_refused` has no guard for a non-mapping item; `core/journal.py::resolve_land_findings_from_payload` already filters to dicts and the declared type holds. No change.
- `[low]` `[patch]` `spec-surface` warned on the new test file. **Fix:** memlog entry + scoped stamp at landing.

Out of this story's Boundaries, recorded rather than fixed here: the two `MRS-DISP-020` meanings deserve distinct codes (`DW-marshal-disp020-two-meanings-2026-09-27`).
