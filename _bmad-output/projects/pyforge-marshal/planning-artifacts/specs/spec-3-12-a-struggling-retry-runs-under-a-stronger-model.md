---
title: 'A struggling retry runs under a stronger model'
type: 'feature'
created: '2026-08-12'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-adaptive-model-tiering/SPEC.md']
warnings: ['oversized']
baseline_revision: 'f6b3e8f2b32efdedb498c47fa2352f5e17bb4594'
final_revision: 'c0e7ca38a03ba7e52368aad1d0396553df90a25d'
---

<intent-contract>

## Intent

**Problem:** A story that keeps failing dev attempts or exhausting review cycles runs its last, most expensive attempt on the exact same model as its first. `run_resume` — the only path that redispatches an already-deferred story — never touches `.bmad-loop/policy.toml`, and the running `bmad_loop` engine caches its `Policy` object once per process, so nothing short of a fresh-process re-read (i.e. a resume) can ever change the model.

**Approach:** When `run_resume` resumes a run carrying one or more deferred stories whose `attempt`/`review_cycle` reached their own configured ceiling, floor-raise the resumed run's dev-stage model to at least its own review-stage model before the fresh `bmad-loop resume` process reads `policy.toml`, journaled on the same intent/outcome pair `run_resume` already writes.

## Boundaries & Constraints

**Always:**
- Build only on facts confirmed by direct source reading: (a) `bmad_loop` 0.9.0's `Engine.__init__` assigns `self.policy` exactly once per process; no code path re-reads `policy.toml` mid-run, so escalation can only take effect at a fresh process boundary (`bmad-loop resume`), never mid-run; (b) `run_resume` (`cli/spin.py:1728-2089`) today performs zero tiering resolution or `policy.toml` write. **This corrects epics.md's own AC parenthetical**, which claims `run_resume` "already re-resolves and re-renders model tiering before relaunching" — verified false. This story adds that step; it is not reusing something that already exists.
- The trigger reads straight off `RunStatusSnapshot.deferred` (`DeferredStory`). `attempt` already exists there; add `review_cycle: int = 0` (trailing-defaulted, mirroring Story 3.8's own additive-field precedent on the same type family), sourced from `state.tasks[key].review_cycle` at the same construction site that already populates `attempt`. Never a new hand-maintained flag (AD-26): the ceilings compared against (`max_dev_attempts`/`max_review_cycles`) are read straight off the on-disk `policy.toml` this resume is about to reload — no new policy key.
- Escalation is run-level, matching the existing "one difficulty governs a whole launch, never per-story mid-run granularity" constraint this Spec's own Non-goals restate: if any currently-deferred story in the resumed run crosses its ceiling, `[adapter].model` (the dev-stage baseline) is raised to equal `[adapter.review].model` for the whole resumed run — never a per-story override.
- Floor-raise only, never a downgrade: read the current on-disk `[adapter].model` vs `[adapter.review].model` before writing (mirrors `_resolve_model_tiering`'s own read-back pattern); if they already match, no write occurs. This is what makes the mechanism bounded (AC's "does not re-fire") without inventing escalation-history bookkeeping — the floor-raise is naturally idempotent once applied.
- Journal on the same `_RESUME_KIND` intent/outcome pair `run_resume` already builds (AD-28): extend the existing payload with `escalated: bool` and, when true, `escalated_stories`/`from_model`/`to_model`. Register `MRS-SPIN-016` (`Verdict.WARN`, mirroring `MRS-SPIN-015`'s tier) for a write failure at this step — degrades to "resumed on the un-escalated model," never blocks the resume.

**Never:**
- No new model-strength ladder, ranked model list, or new policy key — reuses the review-stage model that already exists as this codebase's own documented "strongest configured" value (`_POLICY_TEMPLATE`'s own comment on `[adapter.review].model = "opus"`: "strongest model where it pays").
- No kill/relaunch of an in-flight `bmad-loop run` process and no new process-lifecycle mechanism — escalation only fires at the already-existing resume boundary.
- No change to the vendored `bmad_loop` package.
- No per-story mid-run model selection (`bmad_loop` supports run-level selection only, unchanged).
- Not blocked on Story 3.11: 3.11 populates `model_tier_map` with real values and a declared-difficulty convention, but this story's baseline-escalation path (undeclared story, unpopulated map) is self-sufficient against the already-shipped Story 6.1 chain and the template's own baseline `sonnet`/`opus` pair — verified no code from 3.11 is a prerequisite (3.11's own sibling worktree is untouched as of this writing).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Struggling story resumed | A deferred story's `attempt >= max_dev_attempts` (or `review_cycle >= max_review_cycles`); on-disk `[adapter].model != [adapter.review].model` | `[adapter].model` rewritten to match `[adapter.review].model`; `run-resume` outcome payload carries `escalated: true`, the crossing story key(s), `from_model`/`to_model` | Write failure -> `MRS-SPIN-016` WARN, resume proceeds un-escalated |
| Already escalated | Same trigger, but on-disk `[adapter].model == [adapter.review].model` already | No write; outcome payload carries `escalated: false` | No error |
| No deferred story crosses its ceiling | `deferred` non-empty but every `attempt`/`review_cycle` below its ceiling | No write; ordinary resume, unchanged from today | No error |
| Undeclared story, unpopulated tier map (today's majority case) | No `model_tier_map` entries anywhere; template baseline `sonnet`/`opus` on disk | Escalation still computable and applies -- the baseline IS a floor to escalate from | No error |
| `status_snapshot` unreadable | `harness.run_status_snapshot` returns `None` | Existing `MRS-SPIN-012` WARN; escalation skipped, resume proceeds | Unchanged existing behavior |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/harness.py` -- EDIT. `DeferredStory` gains `review_cycle: int = 0` (trailing default).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py` -- EDIT. Populate `review_cycle` at the existing `DeferredStory(...)` construction site from `state.tasks[key].review_cycle`, mirroring the existing `attempt` population one line above it.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/supervise.py` -- EDIT. New pure classifier `evaluate_retry_escalation(deferred: Sequence[DeferredStory], max_dev_attempts: int, max_review_cycles: int) -> bool` -- no I/O, mirrors `evaluate_ceiling`/`evaluate_escalation`'s shape. `True` iff any story's `attempt >= max_dev_attempts or review_cycle >= max_review_cycles`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py` -- EDIT. `run_resume`: after `status_snapshot` is fetched and the existing escalation-refusal gate passes, read the on-disk `.bmad-loop/policy.toml` (`tomllib.loads`, mirroring `_resolve_model_tiering`'s own read-back), call `evaluate_retry_escalation`, and when true and `[adapter].model != [adapter.review].model`, rewrite `[adapter].model` via `tomlkit` (comment-preserving, AD-16) and persist through the same atomic-write mechanism `write_policy_toml`/`_resolve_model_tiering` already use. Extend the existing `_RESUME_KIND` intent/outcome payloads with `escalated`/`escalated_stories`/`from_model`/`to_model`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` / `core/verdict.py` -- EDIT. Register `MRS-SPIN-016` (WARN), mirroring `MRS-SPIN-015`'s "a best-effort policy-toml persistence step failed" precedent.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/tests/unit/test_supervise.py` -- EDIT. `evaluate_retry_escalation` transition matrix: no deferred stories, one below ceiling, one at/over `max_dev_attempts`, one at/over `max_review_cycles`, mixed.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/tests/unit/test_harness_bmadloop.py` (or nearest existing harness-adapter test module) -- EDIT. `review_cycle` populates correctly on `DeferredStory`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/tests/unit/test_spin.py` -- EDIT. `run_resume` tests: a synthetic struggling deferred story (attempt/review_cycle over threshold) resolves to an escalated `[adapter].model`, journaled with `escalated: true`; a fresh (non-struggling) deferred story resumes with `escalated: false` and no write; an already-escalated on-disk policy resumes idempotently (no second write, no re-fire); a policy-write failure at this step registers `MRS-SPIN-016` and resume still proceeds.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- log any scope narrowed during implementation (e.g. a fallback needed when `.bmad-loop/policy.toml` is missing/malformed at resume time).

## Tasks & Acceptance

**Execution:**
- [x] `ports/harness.py` -- add `DeferredStory.review_cycle: int = 0`.
- [x] `adapters/harness_bmadloop.py` -- populate `review_cycle` from `state.tasks[key].review_cycle`.
- [x] `core/supervise.py` -- `evaluate_retry_escalation`, pure, no I/O.
- [x] `cli/spin.py::run_resume` -- read on-disk policy, evaluate escalation, floor-raise `[adapter].model` to `[adapter.review].model` when triggered and not already equal, persist atomically, extend `_RESUME_KIND` payloads.
- [x] `core/findings.py`/`core/verdict.py` -- register `MRS-SPIN-016` (WARN).
- [x] Unit tests for every new/edited module, including the full I/O matrix above.
- [x] `deferred-work.md` -- log any narrowed scope. (No entry added -- nothing was narrowed; see Spec Change Log for the one disclosed implementation-detail deviation.)

**Acceptance Criteria:**
*(Story 3.12's ACs from `epics.md`, preserved as the contract of record -- resolved against this codebase's actual, verified behavior rather than the epics.md AC's now-corrected `run_resume` premise.)*
- Given a story whose attempt or review-cycle count reaches its own configured `max_dev_attempts`/`max_review_cycles` ceiling (read from `RunStatusSnapshot.deferred`, never a new hand-maintained flag), when that run is next resumed via `run_resume`, then the resumed run's dev-stage model is at least as strong as its own review-stage model -- a floor-raise only, never a downgrade
- And the escalation is journaled on the same `run-resume` intent/outcome entries every other `run_resume` invocation already writes (AD-28), naming the trigger (which story/ies crossed which ceiling) and the resulting model
- And the escalation is bounded: an already-escalated (`[adapter].model == [adapter.review].model`) on-disk policy produces no further write and no re-fire on a subsequent resume of a still-struggling story
- And a story with no declared difficulty and no populated `model_tier_map` (today's majority case) still has a baseline (the template's own `sonnet`/`opus` default) to escalate from -- not a no-op
- And a regression test proves a synthetic struggling deferred story (attempt/review_cycle at or over its ceiling) resolves to an escalated `[adapter].model` on resume, and a fresh (non-struggling) deferred story does not

## Spec Change Log

- **Read mechanism for the on-disk `policy.toml`.** The Code Map bullet names `tomllib.loads` for the read-back (mirroring `_resolve_model_tiering`), with `tomlkit` separately for the rewrite. Implemented as ONE `tomlkit.parse()` covering both the read and the (conditional) write instead of two separate parses: `tomlkit`'s parsed values (`Table`/`Integer`/`String`) satisfy the exact same `isinstance(x, Mapping|int|str)` checks and equality comparisons a `tomllib`-parsed plain dict would, so nothing about the read logic differs, and a caller that may need to mutate-and-write the SAME document it just read has no reason to parse it twice. The orchestrating task message explicitly offered this as an accepted alternative ("mirror it, or use `tomlkit.parse` since you need a comment-preserving *write* afterward"); this is a pure implementation-detail simplification, not a behavior change -- `tests/unit/test_harness_policy_render.py::test_write_policy_document_writes_a_mutated_doc_and_preserves_comments` proves the resulting document is byte-for-byte identical to a `tomllib`-read baseline with only `[adapter].model` patched.
- **`write_policy_toml`'s atomic-write body was refactored, not duplicated.** The Code Map anticipated "add a small sibling write helper" for the single-key patch case; implemented as `write_policy_document` (new) plus a private `_atomic_write_policy_text` helper both it and `write_policy_toml` now call, rather than a second copy of the temp-file-then-`os.replace` sequence -- so the two writers cannot drift out of agreement over write mechanics. `write_policy_toml`'s own public signature, docstring contract, and every existing test are unchanged (proven by the full green suite).

## Review Triage Log

### 2026-08-12 — Review pass 1 (Blind Hunter + Edge Case Hunter, parallel, blind)
- intent_gap: 0
- bad_spec: 0
- patch: 5 (medium 2, low-medium 1, low 2)
- defer: 4 (low-medium 2, low 2)
- reject: 5 (low 5)
- addressed_findings:
  - `[medium]` `[patch]` `[limits]` ceilings read off the on-disk `policy.toml` were only checked via `isinstance(..., int)` -- no `>= 1` floor (bypassing `render_policy_toml`'s own load-time enforcement) and `bool` (an `int` subclass in Python) could silently become ceiling `1`. Both reviewers converged on the `>= 1` gap independently. Fixed: `cli/spin.py::_apply_retry_escalation` now rejects non-`int`, `bool`, and non-positive values for both ceilings; added `test_resume_rejects_a_non_positive_max_dev_attempts_ceiling` and `test_resume_rejects_a_boolean_max_dev_attempts_ceiling`.
  - `[medium]` `[patch]` `_render_text` (the default, non-JSON CLI output) had no line for `escalated`/`escalated_stories`/`from_model`/`to_model` -- every sibling `run_resume`-only field (`story_key`, `resolution_reference`) has one, but these were missed, leaving the floor-raise decision invisible in the surface an unattended operator actually reads. Fixed: added the missing conditional lines in `cli/spin.py::_render_text`; extended `test_resume_escalates_a_struggling_deferred_story_to_the_review_model` to assert on `capsys` text output.
  - `[low-medium]` `[patch]` `ADAPTER_REVIEW_MODEL_STOCK_DEFAULT = "opus"` hand-duplicated `_POLICY_TEMPLATE`'s own `[adapter.review].model` baseline instead of deriving it -- that baseline has already changed once in this project's history per the template's own comment, and nothing kept the two in sync. Fixed: `adapters/harness_bmadloop.py` now derives it via `tomlkit.parse(_POLICY_TEMPLATE)["adapter"]["review"]["model"]` at import time.
  - `[low]` `[patch]` No test exercised more than one deferred story with only some crossing their ceiling. Fixed: added `test_resume_escalates_only_the_crossing_stories_among_several_deferred`.
  - `[low]` `[patch]` No test exercised a `review_cycle`-triggered escalation through the full `run_resume` pipeline (only `evaluate_retry_escalation`'s own unit tests covered that branch, in isolation). Fixed: added `test_resume_escalates_on_a_review_cycle_ceiling_through_the_full_pipeline`.
  - `[low-medium]` `[defer]` Ceilings are read off *whatever `policy.toml` is currently on disk* at resume time, not necessarily the policy that governed the story while it accumulated its `attempt`/`review_cycle` count -- an intervening re-render (e.g. `marshal config --write-harness-policy`) between deferral and resume could silently change the qualifying threshold. Logged to `deferred-work.md` for a follow-up story; the current on-disk read remains the most faithful available source per this spec's own Design Notes and is not a regression against any existing guarantee.
  - `[low-medium]` `[defer]` The `from_model == to_model` idempotence short-circuit returns before recomputing which stories are currently crossing their ceiling, so a story that *newly* crosses on a resume where the model is already floor-raised is never named in `escalated_stories`/the journal for that resume. The mechanism still runs the correct (already-escalated) model -- only the "credit" for a later trigger is unattributed. Changing this touches the established "populate detail fields only when `escalated: true`" return-contract shape (mirrors `story_key`/`resolution_reference`'s own precedent) and is a deliberate design call better made in a follow-up than rushed here. Logged to `deferred-work.md`.
  - `[low]` `[defer]` The `policy.toml` floor-raise write happens before this resume's own `run-resume` intent is journaled (AD-6-style write-before-act ordering); a crash between the write and the journal append would leave an unrecorded state change. Pre-existing pattern (mirrors `_resolve_model_tiering`'s identical ordering in `run_spin`, unchanged by this story) -- not a novel defect, and a coordinated fix belongs to both call sites at once. Logged to `deferred-work.md`.
  - `[low]` `[defer]` `write_policy_document`'s `tomlkit.dumps(doc)` call runs outside `_atomic_write_policy_text`'s own try/except, so a `dumps` failure would propagate raw rather than as `HarnessPolicyWriteError`. Faithfully mirrors `write_policy_toml`'s own pre-existing identical shape (`render_policy_toml`'s call is equally unwrapped) -- not introduced by this story. Logged to `deferred-work.md`.
  - `[low]` `[reject]` A story with no declared difficulty AND a loop home deliberately left at the harness's stock `[adapter].model = ""` (CLI-default) never qualifies for escalation, with no diagnostic beyond `escalated: false`. Not a gap: this is an intentional, already-documented degrade in `_apply_retry_escalation`'s own docstring (there is no real baseline model string to floor-raise FROM), working as designed.
  - `[low]` `[reject]` A misconfigured `marshal-policy.toml`/`model_tier_map` whose `[adapter.review].model` resolves *weaker* than `[adapter].model` for some difficulty would let this mechanism "floor-raise" to a weaker model. No model-strength ordering exists anywhere in this codebase (confirmed by direct search) and inventing one is an explicit Non-goal of the parent Spec (`spec-adaptive-model-tiering`'s own Constraints: "no new model-strength ladder... reuses the review-stage model that already exists as this codebase's own documented 'strongest configured' value"). Re-litigating an already-made, spec-documented architectural choice, not a new finding.
  - `[low]` `[reject]` Remaining untested degrade branches in `_apply_retry_escalation` (an unreadable `policy.toml` via `FsError`, a `tomlkit.exceptions.ParseError`, a non-mapping `[limits]`/`[adapter]` table) -- generic "more coverage would be nice" with no concrete failure scenario named; the existing `isinstance`/`Mapping` guards are structurally sound for every case tomlkit's own parser can produce.
  - `[low]` `[reject]` A claim that malformed tomlkit-parsed values (e.g. `[limits]` as an array-of-tables) could defeat the `isinstance`/`Mapping` guards was not substantiated against tomlkit's actual wrapper-type behavior; the existing defensive checks are structurally correct for every TOML shape the format itself allows.
  - `[low]` `[reject]` A claimed TOCTOU risk ("a concurrent write by the running harness itself") is factually incorrect: direct investigation of the vendored `bmad_loop` 0.9.0 engine (this story's own Design Notes) already established the harness process never writes `policy.toml` at all -- only Marshal's own code does, at three enumerated call sites, none of which overlap this one during a resume.

## Design Notes

**Why the resume boundary, not a live mid-run kill+relaunch.** Direct reading of the installed `bmad_loop==0.9.0` engine confirms `Engine.__init__` assigns `self.policy` exactly once per process, and no code path inside `engine.py`/`stories_engine.py` ever re-reads `policy.toml`; every session spawn resolves its model from that single frozen snapshot (`self.policy.adapter.resolved(role).model`, `engine.py:2527`). A live mid-run `policy.toml` rewrite therefore has zero effect on an already-running process -- the only place a rewritten `policy.toml` is ever actually read is a fresh `bmad-loop` process, i.e. `bmad-loop resume`. This resolves the parent Spec's Open Question #2 definitively (in favor of the resume-time option) and corrects epics.md's AC parenthetical, which asserted the opposite as already-true.

**Why floor-raise dev to review's own model, not a new ladder.** No model-strength ordering exists anywhere in this codebase (confirmed by direct search) -- inventing one is an explicit Non-goal. But the codebase's own rendering template already encodes a two-rung convention in its own comments: `[adapter].model = "sonnet"` ("dev stays sonnet") paired with `[adapter.review].model = "opus"` ("strongest model where it pays"). Reusing review's own already-resolved model as the escalation ceiling needs no new data and no new policy key, and generalizes correctly once Story 3.11 populates `model_tier_map`: whatever review resolves to for a difficulty is, by this project's own stated convention, already at least as strong as dev.

**Why read the on-disk `policy.toml` rather than re-run `policy.compose()`.** `run_resume` resumes an EXISTING harness run whose story scope and tiering were already decided at its original `run_spin`; re-composing from current project policy risks silently diverging from what that run was actually launched under if project policy changed in between. Reading `.bmad-loop/policy.toml` -- already-rendered, on disk, exactly what `bmad-loop resume` is about to reload -- is the faithful source of "what this run's dev/review models currently are."

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

**Manual checks (if no CLI):**
- Against a throwaway loop home, hand-craft a `state.json` with a deferred story at `attempt == max_dev_attempts`, invoke `run_resume`, and confirm `.bmad-loop/policy.toml`'s `[adapter].model` reads `"opus"` afterward and the run's journal shows `escalated: true` with the story key named.

## Auto Run Result

**Summary.** `run_resume` now floor-raises a resumed run's dev-stage model to its own review-stage model whenever a currently-deferred story's `attempt`/`review_cycle` count has reached its run's configured `max_dev_attempts`/`max_review_cycles` ceiling -- read straight off the on-disk `.bmad-loop/policy.toml` (the only file a fresh `bmad-loop resume` process actually reloads, since the running engine caches its `Policy` object once per process and never re-reads it mid-run), applied idempotently (no write, no re-fire once already escalated), and journaled on the same `run-resume` intent/outcome entries every other resume already writes.

**Files changed:**
- `ports/harness.py` -- `DeferredStory` gains `review_cycle: int = 0`.
- `adapters/harness_bmadloop.py` -- populates `review_cycle`; adds `write_policy_document` (a narrow single-key-patch writer sharing `write_policy_toml`'s atomic-write mechanics via a new `_atomic_write_policy_text` helper); `ADAPTER_REVIEW_MODEL_STOCK_DEFAULT` derived from `_POLICY_TEMPLATE` at import time (review fix -- was a hand-duplicated literal).
- `cli/spin.py` -- `run_resume` gains the retry-escalation read/evaluate/floor-raise/journal step; `[limits]` ceiling validation hardened to reject non-`int`, `bool`, and non-positive values (review fix); `_render_text` gains the missing `escalated`/`escalated_stories`/`from_model`/`to_model` lines (review fix -- the decision was invisible in the default CLI output).
- `core/supervise.py` -- new pure `evaluate_retry_escalation`.
- `core/findings.py` / `core/verdict.py` -- register `MRS-SPIN-016` (WARN, escalation write failure).
- Tests extended across `test_supervise.py`, `test_spin.py` (11 escalation-specific tests, including 4 added during review), `test_harness_bmadloop_run_status_snapshot.py`, `test_harness_policy_render.py`, `test_findings.py`.

**Review findings breakdown (pass 1, Blind Hunter + Edge Case Hunter, blind/parallel):** 5 patched (ceiling `>=1`/bool validation, `_render_text` visibility, derived `ADAPTER_REVIEW_MODEL_STOCK_DEFAULT`, 2 new tests), 4 deferred to the ledger (`DW-FU-3-12` through `DW-FU-3-12-4`: cross-resume ceiling staleness, escalated-story naming on an already-escalated resume, write-before-journal ordering shared with `run_spin`'s pre-existing `_resolve_model_tiering`, an unwrapped `tomlkit.dumps` shared with `write_policy_toml`'s pre-existing shape), 5 rejected (an intentional empty-`[adapter].model` degrade, a re-litigation of the parent Spec's own no-new-ladder Non-goal, generic untested-branch noise, an unsubstantiated malformed-tomlkit claim, and a factually-incorrect TOCTOU claim -- the harness itself never writes `policy.toml`, verified by direct investigation of the vendored engine).

**Verification performed:** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- 3510 passed, 0 failures, 0 regressions (up from 3506 pre-review; 4 new tests added during triage). `lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` -- 3 contracts kept, 0 broken. `ruff check` on all 6 touched source files -- pre-existing findings only, confirmed unchanged via `git stash` diff against the base commit.

**Residual risks:** the 4 deferred items above are real but narrow (cross-resume policy staleness, journal completeness on repeat resumes, a shared write-ordering/error-wrapping pattern this story extended rather than introduced) -- none affects the core guarantee (a struggling story's next attempt runs under a floor-raised model, bounded, never a downgrade). Story 3.11 (declared-difficulty population) remains unstarted in this run's fleet as of this writing; this story's baseline-escalation path is verified self-sufficient against it (see Boundaries & Constraints).
