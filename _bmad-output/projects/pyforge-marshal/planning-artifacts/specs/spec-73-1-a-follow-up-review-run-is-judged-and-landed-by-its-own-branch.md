---
title: '73.1: A follow-up review run is judged and landed by its own branch'
type: 'fix'
created: '2026-09-28'
status: 'backlog'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-66-1-finalize-carries-a-recommended-follow-up-review-into-the-deferred-work-ledger.md
  - .claude/skills/bmad-build-auto/step-01-clarify-and-route.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** CAP-275 (Story 66.1) carries a landed story's `followup_review_recommended: true` into an open `DW-FRR-<story>` row (`origin: dispatch-followup-review`). The review itself can already be launched: `dispatch_once` refuses a `done` spec only when the flag is false (Story 29.2, `blocks_harness_relaunch`, `cli/dispatch.py:2211-2214`), and `bmad-build-auto`'s step 01 (`.claude/skills/bmad-build-auto/step-01-clarify-and-route.md:29-31`) routes a `done` spec whose flag is true to a fresh review, writing the flag `false` first. But marshal then misjudges the run, because the story already landed once:
- `dispatch_supervisor/__main__.py::gather_dispatch_git_facts` sets `story_merged_on_main` from the story key's corroborated merge subject (`:376-398`), which the first landing put on `main`, and `core/dispatch_completion.judge_dispatch_completion` returns COMPLETED on it (`:82-83`) — the review run reads finished on its first tick.
- `dispatch_land.py::execute_dispatch_land` answers ALREADY_LANDED when the key is among the corroborated merged keys (`:687-727`) — the review's branch never merges.
- A review that patches nothing changes only its own spec (the flag, `review_loop_iteration`, its review log), which `has_git_progress` with `spec_relative_path` counts as no progress (Story 51.4).
- Nothing closes the `DW-FRR` row.

**Approach:**
- **The marker is derived, not declared.** `dispatch_once` reads the story's tracked spec (the primary's, as it does today) and, when `parse_spec_status` is `done` and `core/dispatch_harness_done.followup_review_recommended` is true, marks the run a follow-up review run: the launch INTENT payload carries `followup_review: {"dw_id": "<DW-FRR-…>" | null}` (the open row's id read from the station's tracked deferred-work ledger, `null` when none). No CLI flag.
- **Judged by its own branch.** For a follow-up run (read from its own launch INTENT), the supervisor's `story_merged_on_main` counts only merge subjects on `origin/main` that are not ancestors of the run's `baseline_head_sha` (for example `commit_subjects` over `<baseline>..refs/remotes/origin/main`); `branch_merged` already requires divergence from the baseline. A diff limited to the story's own spec counts as progress for a follow-up run (it is the review's record). A normal run is judged exactly as today.
- **Landed by its own head.** For a follow-up run, `execute_dispatch_land` does not answer ALREADY_LANDED from the story key's merge subject; it answers ALREADY_LANDED only when the run's own head is an ancestor of `origin/main`, and otherwise merges the branch through the existing path (merge subject as the template renders it).
- **The row closes when the review lands.** After a follow-up run's landing, finalize renders the row closed — `status: closed` and `resolved: <date> (dispatch-land finalize: <merge sha or subject>)` — through a pure function in `core/deferred_work.py`, inside the same advisory lock and `commit_paths_onto_remote_tip` publish CAP-275's carry uses. The review's own landing leaves the flag `false` on `origin/main`, so CAP-275 adds no new row. A failed close is a non-gating `MRS-DISP-047` WARN in the resync payload, as the carry's failures are.

Ledger key: `73-1-a-follow-up-review-run-is-judged-and-landed-by-its-own-branch`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / M / 66.1, 72.1.

### Living CAP citations

- `spec-pyforge-marshal` CAP-281 (FR-228).
- Kinship: `spec-pyforge-doctor:CAP-86` (Doctor checks on every PR that a done story's recommended follow-up review is carried).
- Kinship: CAP-275 (Stories 66.1, 66.2, the row); CAP-280 (Story 72.1, the supervisor's merge reads, which this story scopes to the run's baseline); CAP-276 (Story 67.1, the journal-first verdict).

## Acceptance Criteria

- Given 51.2's tracked spec (`done`, `followup_review_recommended: true`) and an open `DW-FRR-51-2` row When `dispatch_once` launches 51.2 against fakes Then the launch INTENT carries `followup_review` with `dw_id` `DW-FRR-51-2`, and `bmad-build-auto` is launched on the `done` spec
- Given the same spec and no row When `dispatch_once` launches Then `followup_review.dw_id` is `null` and the launch proceeds
- Given a `done` spec with the flag false When `dispatch_once` runs Then Story 29.2's land-only path is unchanged and no follow-up marker is journaled
- Given a follow-up run whose story's original merge subject is on `origin/main` and whose own branch has not merged When the supervisor ticks with the session alive Then the verdict is LIVE, no exit is allowed, and `story_merged_on_main` reads false
- Given that run's branch merged onto `origin/main` after its baseline When the supervisor ticks Then `story_merged_on_main` reads true and the run completes
- Given a follow-up run whose only change is its own spec When the session ends and verification passes Then the run is not judged no-progress and proceeds to land
- Given a follow-up run When `execute_dispatch_land` runs and the run's head is not on `origin/main` Then it merges the branch (not ALREADY_LANDED); when the head is already an ancestor of `origin/main`, it answers ALREADY_LANDED
- Given a follow-up run that landed When finalize runs Then `DW-FRR-51-2` is published `status: closed` with `resolved:` naming the landing, and no new `DW-FRR` row is added
- Given a publish failure while closing When finalize runs Then an `MRS-DISP-047` WARN names it and finalize's exit code is unchanged
- Given a normal (non-follow-up) run When the supervisor and `dispatch land` run Then both behave exactly as today
- Given the baseline scope removed When the follow-up supervisor fixture runs Then it reads COMPLETED on its first tick and the test fails (mutation)

## Boundaries & Constraints

**Always:** Implement only the Surface named in `epics.md` Story 73.1. Derive the follow-up marker from the tracked spec's frontmatter, through `followup_review_recommended` (explicit truthy only). Read every merge fact from `origin/main` (CAP-280). Keep row parsing and rendering pure in `core/deferred_work.py` (AD-4); close the row only through the lock and publish CAP-275 uses.

**Never:**
- Do not flip, re-add or re-queue the story's ledger key; it stays `done` throughout.
- Do not change `.claude/skills/bmad-build-auto/` (step 01 and step 04 already do the review and leave the flag `false`).
- Do not change how a normal run is judged or landed.
- Do not schedule follow-ups from a drain here (Story 73.2).
- Do not change `scripts/deferred_work_intake.py` (spec-pyforge-doctor governs it).
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`; do not run `scripts/bmad-switch`.

Co-governing Specs: `spec-pyforge-marshal` (owner of `src/shared/packages/pyforge-marshal/**`) and `spec-pyforge-core` (co-governs every station's `src/`) — reconcile each one the spec-surface detector names.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| follow-up launch, row open | spec `done`, flag true, `DW-FRR` open | INTENT `followup_review.dw_id` set; review launched | none |
| follow-up launch, no row | spec `done`, flag true, no row | INTENT `dw_id: null`; launched | none |
| flag false | spec `done`, flag false | Story 29.2 land-only, unchanged | as today |
| first landing on `origin/main` | follow-up branch unmerged | LIVE; no exit | none |
| follow-up merged | own merge after baseline | COMPLETED | none |
| spec-only review | diff = own spec | counted as progress; lands | none |
| land, head not on `origin/main` | follow-up run | merged through the existing path | as today |
| land, head already on `origin/main` | follow-up run | ALREADY_LANDED | none |
| close fails | publish error | row stays open | `MRS-DISP-047` WARN; exit unchanged |
| normal run | not a follow-up | unchanged | as today |

</intent-contract>

## Source

Contract authored from the operator's 2026-09-28 direction, `docs/dreams/pyforge-marshal.md`'s 2026-09-28 entry (*a drain runs the follow-up review a landed story recommended*) and `spec-pyforge-marshal` CAP-281 with its 2026-09-28 direction entry in the Spec's `.memlog.md` (the file:line evidence for the supervisor's and the landing's misjudgement), decomposed the same session as Epic 73's mint.

## Binding

Parent Spec capability: `spec-pyforge-marshal` CAP-281 (FR-228).
Ledger key: `73-1-a-follow-up-review-run-is-judged-and-landed-by-its-own-branch`.
Ledger status at mint: `backlog`.
Deps: Story 66.1 (the `DW-FRR` rows this story closes) and Story 72.1 (the supervisor's merge reads on `origin/main`, which this story scopes to the run's baseline).
Policy: no `[epic_surfaces]` entry; the Surface is inside marshal's default surface.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
