---
title: '73.1: A follow-up review run is judged and landed by its own branch'
type: 'fix'
created: '2026-09-28'
status: 'in-review'
baseline_revision: '26028262eb1275a516c451b3362d48616e96bd44'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-66-1-finalize-carries-a-recommended-follow-up-review-into-the-deferred-work-ledger.md
  - .claude/skills/bmad-build-auto/step-01-clarify-and-route.md
warnings:
  - oversized
deferred: []
declared_low_risk: false
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

## Code Map

Paths below sit under `src/shared/packages/pyforge-marshal/src/pyforge/marshal/` (`<pkg>/`). The line numbers the contract cites are stale (re-measured 2026-10-01); the anchors here are symbols.

- `<pkg>/core/dispatch_harness_done.py` -- owns `parse_spec_status`, `followup_review_recommended` (explicit truthy) and `blocks_harness_relaunch`; the marker type and its INTENT read/write sit beside them (pure).
- `<pkg>/core/deferred_work.py` -- `followup_review_id`, `_FOLLOWUP_REVIEW_HEADING_RE`, `render_followup_review_entry` (row = `### DW-FRR-<story>:` heading, `  status: open`), `append_ledger_entry`; the open-row read and the closed-row render join them (AD-4).
- `<pkg>/core/dispatch_completion.py` -- `has_git_progress` / `is_spec_only_narration` (Story 51.4: a spec-only diff is no progress); the two follow-up scopes (merge-subject range, narration path) join them as pure helpers.
- `<pkg>/core/supervise.py::resolve_terminal_session_verdict` -- takes `spec_relative_path`; a follow-up run passes `None` through the narration helper.
- `<pkg>/cli/dispatch.py::dispatch_once` -- harness-done gate (`blocks_harness_relaunch`, Story 29.2) then the INTENT `build_entry(..., KIND_DISPATCH_LAUNCH, Phase.INTENT, payload={...})`; `spec_text` is the primary's tracked spec; `fs.read_text` reads the ledger.
- `<pkg>/dispatch_supervisor/__main__.py` -- `gather_dispatch_git_facts` (`commit_subjects(repo_root, ORIGIN_MAIN)` -> `story_merged`; called four times: the loop and `_run_supervisor_finalize_sequence`); `_spec_land_block_reason` and every `spec_relative_path=` use (`run_dispatch_supervisor` loop, `resolve_terminal_session_verdict` calls); `_launch_story_started_ts` is the pattern for reading the launch INTENT from `folded`; `_land_or_journal_block` -> `_run_and_journal_landing` -> `execute_dispatch_land`.
- `<pkg>/dispatch_land.py::execute_dispatch_land` -- ALREADY_LANDED from `promotion.corroborated_merged_story_keys(main_subjects, ...)` against `origin/main`; `subject` and `head_sha` exist by the time it starts the finalize subprocess (`pyforge.marshal.dispatch_land_finalize <slug> <key> <worktree>`).
- `<pkg>/dispatch_land_finalize/__main__.py` -- `_run_deferred_work_intake` (lock via `fs.acquire_advisory_lock`, publish via `vcs.commit_paths_onto_remote_tip`, non-gating `MRS-DISP-047`), `_carry_followup_row`, the resync observation payload (`followup_review_promoted_id`), `main` argv.
- `<pkg>/ports/vcs.py` / `adapters/vcs_git.py` -- `commit_subjects` hands `ref` straight to `git log`, so `<baseline>..<ORIGIN_MAIN>` needs no port change; `merge_base` + `resolve_ref` give exact ancestry (`is_branch_merged` is patch-content equivalence, broader than the contract's "ancestor").
- Read-only: `.claude/skills/bmad-build-auto/`, `scripts/deferred_work_intake.py`, `sprint-status-ledger.yaml`, every `SPEC.md`.

## Tasks & Acceptance

**Execution:**
- `<pkg>/core/dispatch_harness_done.py` -- frozen `FollowupReview(dw_id: str | None)` with one INTENT payload round-trip -- one shape for the writer (`dispatch_once`) and the readers (supervisor, land).
- `<pkg>/core/deferred_work.py` -- `open_followup_review_id(ledger_text, story_key)` (row headed `DW-FRR-<story>` whose `status:` reads `open`, else `None`) and `close_followup_review_row(ledger_text, dw_id, *, resolved_date, landing)` (`status: closed` plus `resolved: <date> (dispatch-land finalize: <landing>)`; `None` when the row is absent or not open, so a re-run is a no-op) -- pure.
- `<pkg>/core/dispatch_completion.py` -- `merge_subject_ref(baseline_head_sha, ref, *, followup_review)` (`<baseline>..<ref>` for a follow-up, else `ref`) and `narration_spec_path(spec_relative_path, *, followup_review)` (`None` for a follow-up) -- the policy lives in the pure core.
- `<pkg>/cli/dispatch.py` -- `dispatch_once` derives the marker from the primary's `spec_text` (`done` + truthy flag) after the harness-done gate, reads the open row id from the tracked ledger, journals `followup_review` on the INTENT only for a follow-up -- a flag-false `done` spec and every normal run journal nothing new.
- `<pkg>/dispatch_supervisor/__main__.py` -- read the marker from the launch INTENT; `gather_dispatch_git_facts(..., followup_review=False)` reads ranged subjects; route every narration check through `narration_spec_path`; thread the marker into `execute_dispatch_land`.
- `<pkg>/dispatch_land.py` -- `execute_dispatch_land(..., followup_review=None)`: a follow-up skips the key-based ALREADY_LANDED and answers it only when `merge_base(head, ORIGIN_MAIN) == head`; when `dw_id` is set, pass it and the rendered merge subject to the finalize subprocess.
- `<pkg>/dispatch_land_finalize/__main__.py` -- two optional argv flags; after the intake step, close the row under the same lock and publish; a failure is an `MRS-DISP-047` WARN naming it; the resync payload gains `followup_review_closed_id`.
- Tests (`src/shared/packages/pyforge-marshal/tests/unit/`): `test_deferred_work.py`, `test_dispatch_completion.py`, `test_dispatch.py`, `test_dispatch_supervisor_main_loop.py`, `test_dispatch_landing.py`, `test_dispatch_land_finalize.py` -- every I/O-matrix row, the baseline-scope mutation fixture, and a normal-run regression for each judged surface.
- Spec memlogs -- name every governed path on `spec-pyforge-marshal`'s `.memlog.md` and on each co-governor `spec-surface` names (`uv run _bmad/scripts/memlog.py append`); never `--write-baseline`.

**Acceptance Criteria:**
- Given a follow-up run that lands, when finalize ends, then the story's ledger key reads `done` in the tracked ledger throughout and no `DW-FRR` row is added
- Given a normal run, when the supervisor gathers facts and `execute_dispatch_land` runs, then `commit_subjects` is asked for `ORIGIN_MAIN` with no range and no marker reaches the landing
- Given the change, when `lint-types` and the station suite run, then both are green and the touched modules keep their coverage floors

## Spec Change Log

## Review Triage Log

## Design Notes

- The follow-up marker travels as data, never as a flag: the INTENT carries it, the supervisor reads it, `execute_dispatch_land` takes it as a keyword, and finalize (a subprocess the landing starts) takes the row id and the merge subject on argv. A normal run passes nothing, so every normal-run path is byte-identical.
- Baseline scope: `git log <baseline>..refs/remotes/origin/main --format=%s` lists only what reached `origin/main` after the run forked. The story's first merge is an ancestor of the baseline, so it drops out; the run's own merge does not.
- Not covered, by contract: the harness-done CAP-4 relaunch of a follow-up worktree (its spec already reads the flag `false`) and a landing retry after the merge but before finalize carry no marker, so neither closes the row.

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
- `pixi run -e pyforge-guild lint-types` — expected: exit 0 (ruff, `ruff format --check`, mypy over the touched package).
- `python scripts/spec_surface_reconcile.py` — expected: exit 0 once every governed path is named on the owning Spec's `.memlog.md` and each co-governor's (never `--write-baseline`).
