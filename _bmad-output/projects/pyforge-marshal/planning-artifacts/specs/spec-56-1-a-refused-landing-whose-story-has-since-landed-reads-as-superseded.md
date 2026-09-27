---
title: '56.1: A refused landing whose story has since landed reads as superseded'
type: 'fix'
created: '2026-09-27'
status: 'in-review'
review_loop_iteration: 0
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

**Approach:** keep the refusal and report the git fact beside it (AD-5 / AD-33: the journal owns process facts, git owns repository facts, a disagreement is reported, never silently reconciled). A pure `core/dispatch_landing.landing_refusal_superseded(findings, story_merged_on_main=…)` is true only when a finding is ERROR-severity and the story is on `main`. The status fleet sweep answers `story_merged_on_main` from `core.promotion.corroborated_merged_story_keys` — the check `dispatch land` already uses for ALREADY_LANDED — over `main`'s subjects, read at most once per sweep and shared with the failed-patch check, with the station's own `merge_subject_template` and the `origin/main` spec-status reader. The JSON row gains `dispatch_landing_superseded: true` beside the unchanged `dispatch_landing_findings`. `fleet-picture` renders a superseded refusal in its not-blocking list, naming the story as landed since.

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
- Given a superseded refusal in `fleet-picture`'s live row When `fleet-picture` runs Then ATTENTION carries no `landing refused` line for it and the not-blocking list names the story as landed since; an un-superseded refusal still renders `landing refused` in ATTENTION exactly as before
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
| refusal, story landed since | ERROR finding; key corroborated on `main` | `dispatch_landing_superseded: true`; findings unchanged; fleet-picture not-blocking line | none |
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
