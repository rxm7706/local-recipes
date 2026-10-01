---
title: '73.1: A follow-up review run is judged and landed by its own branch'
type: 'fix'
created: '2026-09-28'
status: 'blocked'
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

### 2026-10-01 — Review pass
- verdicts: 31 findings — high 2, medium 8, low 20, false 1, maybe-false 0
- layers: Blind Hunter (12), Edge Case Hunter (7), Verification Gap (3), Intent Alignment (9 divergences). Blind Hunter and Intent Alignment reports reached triage wire-compressed; their full text was recovered from the subagent transcripts before triage, so every row below is from the uncompressed report.
- routing: one `intent_gap` group (G1: BH-8, EC-7), so every other entry is moot for this run. Their routes are recorded as they would have run. The attempted change is saved at `_bmad-output/implementation-artifacts/73-1-intent-gap-attempt-2026-10-01.patch` (16 files, 2,582 lines; resolves to `_bmad-output/projects/pyforge-marshal/implementation-artifacts/`, gitignored) and the code, tests and both spec memlogs were reverted to `baseline_revision`. The `defer` rows are not appended to `deferred:` because they are moot; the Auto Run Result carries them for the re-run.
- findings:
  - `[low]` `[reject]` BH-1 Closing the row suppresses a genuine re-recommendation (the row id has no iteration and the carry skips a story whose heading exists) — by design: Epic 73's hard boundary is that a follow-up never chains another, and step 04 forces the flag false on a follow-up pass, so the cited state is not produced; iterated row ids would add complexity for a state the design excludes.
  - `[low]` `[reject]` BH-2 A spec-only diff counts as progress for a follow-up run, so a session that dies right after step 01's flag flip lands and closes the row — the contract requires this behavior (Approach bullet 2 and the acceptance criterion that a follow-up whose only change is its own spec proceeds to land); the harm needs a session death in that exact window.
  - `[medium]` `[defer]` BH-3 The CAP-4 land-only retry (`_attempt_harness_done_cap4`) and a landing retry after the merge but before finalize carry no marker, so a follow-up still gets the key-based ALREADY_LANDED and its row stays open, with nothing deferred — verified real: that path calls `execute_dispatch_land` without `followup_review`; the contract's Always bullet limits the build to the Surface named in `epics.md`, which does not include it. Entry R1 with EC-5 and IA-9.
  - `[low]` `[reject]` BH-4 The follow-up ALREADY_LANDED check has no head-equals-baseline guard, and ALREADY_LANDED never starts finalize — a run with head equal to baseline and no changes has no git progress, so `supervisor_should_finalize_harness_work` never lets it reach verification or landing; skipping finalize on ALREADY_LANDED is the existing behavior for every run.
  - `[low]` `[reject]` BH-5 The marker reads the primary's spec while the gate reads the worktree-preferred spec, the open-row id comes from a possibly lagging primary ledger, and the ledger path is built twice — the contract says to read the primary's spec, and a worktree spec at done/true while the primary is not done is an unlanded story, which a normal run judges correctly; ledger lag only nulls `dw_id`, which the contract allows; the duplicate path is cosmetic.
  - `[low]` `[patch]` BH-6 The `close_followup_review_row` docstring says `resolved:` above `status: closed` is the order the ledger's closed rows already use — verified wrong: none of the live ledger's `status: closed` rows carries `resolved:` directly before it (they put `status:` first and use `resolution:`), while `status: resolved` rows put `resolved:` before `status:`. The contract prescribes both fields but not their order, so the docstring needs rewording. Moot: the code is reverted.
  - `[low]` `[reject]` BH-7 The review's `resolved:` line names the rendered merge subject, which equals the first landing's subject — the contract says "merge sha or subject", so the subject is a permitted value.
  - `[high]` `[intent_gap]` BH-8 Three claims about the baseline scope: (a) the spec's mutation test was not written — false: I ran the criterion's mutation (a pytest plugin replacing the supervisor's `merge_subject_ref` with a version that ignores the marker) and `test_gather_git_facts_for_a_follow_up_ignores_the_stories_first_merge` fails, as required; (b) a blank baseline yields `..origin/main` — unreachable, the baseline is a `rev-parse` result; (c) the scope assumes the baseline already contains the story's first merge — verified real, the same defect as EC-7. Row grade is the highest member's. Entry G1.
  - `[low]` `[reject]` BH-9 Two tests are vacuous or contradict the spec — the real-git closure test stubs promotion, which narrows what it proves but not what it asserts; the carry-and-close test exercises the real `carried` branch of `_close_followup_row` and does not contradict the criterion, which `test_a_landed_follow_up_review_closes_its_row_and_adds_no_new_one` covers.
  - `[low]` `[reject]` BH-10 `followup_review` is a bool in some supervisor functions and `FollowupReview | None` in others, and no meta test checks every site threads it — a naming inconsistency, not a defect; threading is pinned by `test_every_terminal_verdict_read_of_a_follow_up_run_takes_no_narration_path` and the landing pass-through tests, and the two unpinned sites are VG-1 and VG-2.
  - `[low]` `[reject]` BH-11 The finalize CLI accepts `--landing-subject` without `--followup-review-id`, a subject starting with `-` could misparse, and the no-flag branch of `main` is untested — `execute_dispatch_land` is the only caller and always passes both flags together, the marshal-native merge subject is `Merge <slug>/<key> into main`, and the no-flag branch is one call to the unchanged function.
  - `[low]` `[reject]` BH-12 Documentation and housekeeping gaps (no durable doc for the new journal keys and finalize flags, spec frontmatter, empty logs, "AC 8" numbering, no `pr-preflight` in Verification) — the journal keys are documented in docstrings and the memlog entries; the frontmatter and logs are the harness's own fields at this point in the run; `pr-preflight` is the supervisor path's gate for dispatch branches, not a build-auto verification command.
  - `[medium]` `[defer]` EC-1 The status, zombie and fleet-block readers (`resolve_dispatch_session_verdict`, `station_story_block_facts` and `cli/status.py`) re-gather git facts without the marker and read a live follow-up run as completed — verified by reading: they call `gather_dispatch_git_facts` without `followup_review` over the whole `origin/main`; the contract's Always bullet restricts the build to the named Surface (`dispatch_once`, the supervisor, landing, finalize), which excludes them. Entry R2 with VG-3 and IA-1.
  - `[low]` `[reject]` EC-2 The open-row id is read from the primary's working-tree ledger, which can lag `origin/main`, so `dw_id` journals null and the row is never closed — real but narrow: the lag exists only between a carry's publish and the primary's next resync; the contract's acceptance criteria allow `dw_id: null`, Story 73.2 names stale rows, and the fix adds a git read with a fallback.
  - `[low]` `[reject]` EC-3 A spec-only diff may be only step 01's flag flip — same claim and evidence as BH-2.
  - `[low]` `[reject]` EC-4 A follow-up head equal to the baseline is trivially an ancestor of `origin/main` — same claim and evidence as BH-4.
  - `[medium]` `[defer]` EC-5 A relaunch after step 01 flipped the flag takes the land-only path with no marker — same root as BH-3. Entry R1.
  - `[low]` `[reject]` EC-6 A bulleted `- status:` line gets `resolved:` placed before the bullet — only a hand-bulleted status field is affected; the carry renders `  status: open` with a two-space indent, which closes correctly, and no row leads with its status field.
  - `[high]` `[intent_gap]` EC-7 The baseline can predate the story's first merge, because `_ensure_dispatch_worktree` reuses the story's surviving dispatch worktree, so `<baseline>..origin/main` still contains the first merge and the run reads COMPLETED on its first tick — verified with the code under review against real git: with the surviving 66.1 worktree as the launch baseline (`a0025fff64`, a pre-merge tip that the first merge `e28ee0a260` is not an ancestor of), `gather_dispatch_git_facts(..., followup_review=True)` returns `story_merged_on_main=True`, and eight landed dispatch worktrees exist now. The contract's rule ("not ancestors of the run's `baseline_head_sha`") cannot satisfy its own fourth acceptance criterion in that state. Entry G1.
  - `[medium]` `[patch]` VG-1 The LIVE-branch land site passes `followup_review` to `_land_or_journal_block` with no test, so dropping the keyword leaves the suite green — pre-verified by the layer's mutation and passing probe. Moot: the code is reverted; the re-run should carry the probe.
  - `[medium]` `[patch]` VG-2 A refused or failed land of a follow-up run is never exercised after the terminal-site re-gather, so changing `followup_review=followup_run` to `False` there leaves the suite green — pre-verified by the layer's mutation and probe. Moot, as VG-1.
  - `[medium]` `[defer]` VG-3 The launcher, fleet and status readers judge a live follow-up run by the story's first merge — same root as EC-1. Entry R2.
  - `[medium]` `[defer]` IA-1 Other consumers of the same facts are unchanged (`cli/dispatch.py` readers, `cli/status.py`, `_attempt_harness_done_cap4`), and the Design Notes call this "by contract" — the contract's Always bullet ("Implement only the Surface named in `epics.md` Story 73.1") is what excludes them; the Design Notes wording is the planner's and overstates it. Entries R1 and R2.
  - `[low]` `[reject]` IA-2 The `dw_id` ledger read is the primary's working tree, not `origin/main` (readings C1 and C2) — same claim and evidence as EC-2.
  - `[low]` `[reject]` IA-3 `resolved:` names a subject equal to the first landing's — same claim and evidence as BH-7.
  - `[low]` `[reject]` IA-4 The row closes only on the real-merge path, so an ALREADY_LANDED follow-up never closes it — same claim and evidence as BH-4's second claim.
  - `[low]` `[reject]` IA-5 A tested carry-and-close case goes beyond the intent — same claim and evidence as BH-9.
  - `[low]` `[reject]` IA-6 Ranged subjects and ancestry are modelled by fakes and the mutation criterion is met by fixture — I ran the criterion's mutation and the fixture fails as required; the fake-only ancestry is why EC-7 went unseen, and that defect is carried by entry G1, not by this row.
  - `[low]` `[reject]` IA-7 The chain is tested in pieces, not joined — each seam has its own test (INTENT read, supervisor-to-landing keyword, landing-to-finalize argv, finalize-to-ledger); a joined real-git run is out of proportion for the unit tier.
  - `[false]` `[reject]` IA-8 "No CLI flag": the diff adds two flags to the finalize module's argv — the contract's "No CLI flag" is about how the marker is declared at launch (`dispatch_once`); finalize's argv is an internal subprocess protocol that only `execute_dispatch_land` invokes, so no operator-facing flag exists.
  - `[medium]` `[defer]` IA-9 The 29.2 gate reads the worktree-preferred spec while the marker reads the primary's, and they differ once a prior review attempt rewrote the flag false, so the gate routes to the land-only path with no marker — same root as BH-3 and EC-5. Entry R1.

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

## Auto Run Result

Status: blocked
Blocking condition: intent gap

**What happened.** The story was implemented in full and the attempted tree was green, but review found a hole in the intent contract's own baseline rule. A follow-up run launched into a surviving dispatch worktree still reads COMPLETED on its first supervisor tick, which is the bug this story exists to fix. The hole is inside the `<intent-contract>`, which the build may not edit, so the attempted change was saved as a patch and the code was reverted to `baseline_revision` (`26028262eb1275a516c451b3362d48616e96bd44`). Only this story spec differs from baseline now.

**Saved patch.** `_bmad-output/implementation-artifacts/73-1-intent-gap-attempt-2026-10-01.patch` (16 files, 2,582 lines; the path resolves to `_bmad-output/projects/pyforge-marshal/implementation-artifacts/`, which is gitignored). It is the whole attempted change except this spec: the seven source modules, the six test files in `tests/unit/`, and the `.memlog.md` entries on `spec-pyforge-marshal` and `spec-pyforge-core`. Re-apply it to a baseline tree with `git apply`.

**Unresolved questions** (for the owner of `spec-pyforge-marshal` CAP-281):
1. *Scope of "judged by its own branch" (entry G1).* `_ensure_dispatch_worktree` reuses a surviving branch and worktree, and landed dispatch worktrees survive routinely (eight exist today, including 66.1's). Then `baseline_head_sha` is a pre-merge tip, the story's first merge commit is not an ancestor of it, and "merge subjects that are not ancestors of `baseline_head_sha`" still counts that merge. Reproduced with the attempted code against real git: with 66.1's worktree as the baseline (`a0025fff64`), `gather_dispatch_git_facts(..., followup_review=True)` returns `story_merged_on_main=True`. The contract's rule therefore cannot satisfy its own fourth acceptance criterion in that state. What must the supervisor scope merge subjects to? Option (a): journal `origin/main`'s tip on the launch INTENT and count only subjects that reach `origin/main` after it; every one of the eleven acceptance criteria still holds. Option (b): give a follow-up run a fresh branch and worktree from current `origin/main` and refuse or retire the stale one, which touches an existing worktree and so needs an operator ruling.
2. *Surface (entries R1 and R2).* The same story-first-merge misjudgement remains in readers and callers outside the named Surface: `_attempt_harness_done_cap4` (the CAP-4 land-only retry, which passes no marker to `execute_dispatch_land`), `resolve_dispatch_session_verdict` and `station_story_block_facts` in `cli/dispatch.py`, and `cli/status.py`. Should they join Story 73.1, or belong to a new story that lands before Story 73.2 schedules follow-ups into them? The Always bullet ("Implement only the Surface named in `epics.md` Story 73.1") excludes them today; this spec's Design Notes say "not covered, by contract" for the CAP-4 path, which overstates it, because the Always bullet is the only basis.
3. *Where `dw_id` is read at launch (EC-2).* The contract says "the station's tracked deferred-work ledger". The attempted code read the primary checkout's working copy, which can lag `origin/main` between a carry's publish and the primary's next resync. Both readings are defensible; the cost of a wrong pick is a row left open, not a wrong landing.

**Review findings breakdown.** Patches applied: 0. Three entries routed `patch` and are moot under the cascade: BH-6 (reword a wrong docstring claim about the ledger's closed-row field order), VG-1 and VG-2 (two untested supervisor call sites, each with a passing probe from the Verification Gap layer). Deferred: 0 appended to `deferred:`, because the entries are moot; six `defer` rows are carried here for the re-run as two root causes: R1 (a land path with no marker: BH-3, EC-5, IA-9) and R2 (readers that re-gather without the marker: EC-1, VG-3, IA-1). Intent gap: G1 (BH-8, EC-7), the one root cause that halted the run. Rejected: 20 low and 1 false, each with its recorded reason in the Review Triage Log.

**Verification performed.** On the attempted tree, before review: `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` passed (9597 passed, 1 skipped); `pixi run --frozen -e pyforge-ci pyforge-deps-test` passed (130 passed, 3 skipped); `pixi run -e pyforge-guild lint-types` exit 0; `python scripts/spec_surface_reconcile.py` exit 0. During triage: the criterion's baseline-scope mutation made `test_gather_git_facts_for_a_follow_up_ignores_the_stories_first_merge` fail, as required, and G1 was reproduced against real git as described above. After the revert: `python scripts/spec_surface_reconcile.py` exit 0. No `--write-baseline` was run, the sprint-status ledger and every `SPEC.md` are untouched, and nothing under `implementation-artifacts/` is tracked.

**Residual risks.** Until question 1 is answered, any follow-up run for a story whose dispatch worktree survives would read COMPLETED on its first tick without landing, and Story 73.2's drain would schedule exactly those runs. The attempted design is otherwise sound; the review's other findings were low or moot.
