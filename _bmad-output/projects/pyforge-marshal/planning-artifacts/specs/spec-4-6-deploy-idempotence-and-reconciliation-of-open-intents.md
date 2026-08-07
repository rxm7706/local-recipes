---
title: 'Deploy idempotence and reconciliation of open intents'
type: 'feature'
created: '2026-08-06'
status: 'done'

review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md']
warnings: []
baseline_revision: '565bd99fbe478be01dd435002e11d4124644e669'
---

<intent-contract>

## Intent

**Problem:** `promote` (4.1), `land-story` (4.3), and `batch-pr` (4.4) each perform an irreversible or externally-visible action AD-6's own text names explicitly — "promoting a spec, merging, opening a PR" — yet none of them journals an `intent` entry BEFORE acting (grepped live: zero `Phase.INTENT` writers exist anywhere in `cli/deploy.py` today). AD-6 is violated by every prior deploy action, and nothing reconciles a crash mid-action — a `deploy` killed between `commit_paths`/`merge_branch`/`create_pr` succeeding and the process reporting back has no record of whether the irreversible step happened.

**Approach:** retrofit proper `intent`/`outcome` journal pairs (AD-6, AD-28) around each of the three actions' own irreversible step. Before performing that step, each action first checks `core.journal.fold`'s `open_intents` for a matching, unclosed intent from a prior run of the SAME action against the SAME target (story key / branch / PR) — if found, it attempts reconciliation via EXTERNAL evidence (git-truthful: does the commit/merge/PR actually exist now?) rather than blindly re-performing the action (the AD-6 × AD-21 precedence: observe and close, never re-act without evidence the action didn't occur). An intent with no available evidence stays open, classifies `WARN` (AD-21's own F-17 amendment), and is reported — never blocking, never silently retried.

## Boundaries & Constraints

**Always:**
- **Every irreversible step in `promote`/`land-story`/`batch-pr` gains an `intent`→`outcome` pair**, mirroring AD-6's own literal examples: `promote`'s `VcsPort.commit_paths` call, `land-story`'s `VcsPort.merge_branch` call, `batch-pr`'s `ForgePort.create_pr`/`update_pr` calls (label application is NOT independently irreversible in the same sense — a mis-applied label is trivially reversible, so it does not need its own intent/outcome pair; only the PR create/update itself does). The `intent` entry's payload names enough to reconcile later: the story key(s) involved, and what specifically is about to happen (e.g. `{"action": "commit_paths", "story_keys": [...]}`).
- **Reconciliation precondition, before any of these three actions re-attempts its own irreversible step**: fold the journal, check `open_intents` for an unclosed intent of the SAME kind targeting the SAME story key(s)/branch/PR from an EARLIER run. If found: attempt to close it via external evidence — for `promote`, does `planning-artifacts/specs/spec-<key>*.md` already exist and is it committed (reuse Story 4.1's own `_already_promoted_keys`/`path_has_uncommitted_changes`); for `land-story`, does the story now appear in `merged_story_keys` (reuse Story 4.1's own machinery); for `batch-pr`, does `ForgePort.find_open_pr` now show a PR already reflecting this content. Evidence found → journal a `reconciliation` outcome (AD-28's own literal shape: `intent_id` referencing the open intent, evidence named) and DO NOT re-perform the action — proceed as if it already succeeded. No evidence found → the intent stays open, reported as a `WARN`-classified finding (never `ERROR`, per AD-21's F-17 amendment — an open intent must never make every subsequent `deploy` invocation non-zero), and the action proceeds normally (since there's no proof the prior attempt did anything, it is safe and necessary to attempt it now).
- **Idempotence, the general property (AD-21)**: each of the three actions already has (from Stories 4.1/4.3/4.4) some form of "is this already done" check (`_already_promoted_keys`, the already-merged short-circuit in `land-story`, `find_open_pr`'s existing-PR detection in `batch-pr`) — this story's job is to make sure EVERY step, not just the headline action, reports `done | skipped | failed` per AD-21's own text, and that a re-run against a fully converged system (nothing to promote, nothing to land, PR already reflects the wave) produces zero changes and exit 0 (NFR-7). Audit each of the three commands' full step sequence and confirm every step already has this shape; where one doesn't, add it.
- **`core/journal.py` gains the reconciliation-evidence classification as a pure function** (if one doesn't already exist to build on) — taking the open intent's payload and the caller-gathered external evidence (already fetched via `VcsPort`/`ForgePort` by the CLI layer, never re-fetched inside `core/**` per AD-4) and returning whether it reconciles, so the "what counts as evidence" DECISION is pure/testable even though gathering the evidence itself is impure.

**Never:**
- Reconciliation NEVER re-performs an action whose intent is open without evidence the action did not occur — the exact AD-6 × AD-21 precedence this story's own AC states verbatim. If evidence is ambiguous or unavailable, the intent stays open; the action is retried ONLY because retrying is independently safe (each of the three actions' own existing idempotence checks already make a genuine re-attempt a no-op if the target state is already reached) — reconciliation and "safe to retry anyway" are two different justifications that happen to cooperate here, not the same claim.
- No new blocking behavior from an open intent — it classifies `WARN`, never `ERROR`, per AD-21's F-17 amendment, explicitly exempt from the exit-0 convergence property.
- Do not touch `cli/land.py`/Story 4.8's own surface (this story hardens the THREE EXISTING `cli/deploy.py` actions, not a new command).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clean run, no prior open intents | Normal invocation | Intent written, action performed, outcome written | No error |
| Prior open intent, evidence confirms the action DID happen | e.g. `promote`'s spec file now exists and is committed | Reconciliation outcome closes the old intent; action NOT re-performed; proceeds as already-done | No error |
| Prior open intent, no evidence available | Genuinely ambiguous/unconfirmable | Intent stays open, `WARN` finding; action is attempted now (safe per each command's own idempotence check) | Reported, non-blocking |
| Re-run against a fully converged system | Nothing left to promote/land/PR-update | Every step reports `skipped`; zero changes; exit 0 | No error |
| A step fails partway | e.g. `commit_paths` raises mid-batch | That step reports `failed`; intent for it stays open (no outcome written); re-run picks up from there | Registered finding |
| Multiple open intents from different runs, same target | Two crashed attempts | Reconciliation checks against the SAME external evidence source for both; both close together if evidence confirms, or both stay open if not | No error |

</intent-contract>

## Code Map

- `src/pyforge/marshal/core/journal.py` — EDIT. A pure reconciliation-evidence classification function (only if nothing suitable already exists — check `FoldResult.open_intents`/`orphaned_outcomes` and any existing reconciliation helper first).
- `src/pyforge/marshal/cli/deploy.py` — EDIT. Retrofit `intent`/`outcome` pairs around `run_promote`'s `commit_paths` call, `run_land_story`'s `merge_branch` call, `run_batch_pr`'s `create_pr`/`update_pr` calls; add the pre-action reconciliation check to each; audit and complete `done | skipped | failed` step reporting across all three.
- `src/pyforge/marshal/core/findings.py` / `core/verdict.py` — EDIT. New code for "open intent, no evidence" classified `WARN` (confirm no suitable code already exists before adding one).
- `tests/unit/test_journal.py` — EDIT. Reconciliation-evidence classification matrix.
- `tests/unit/test_deploy.py` — EDIT. Idempotence/reconciliation tests for all three actions, including the NFR-7 zero-changes-on-converged-re-run test for each.

## Tasks & Acceptance

**Execution:**
- [x] `core/journal.py` — reconciliation-evidence classification (if needed beyond what exists).
- [x] `cli/deploy.py` — intent/outcome retrofit for `promote`, `land-story`, `batch-pr`'s irreversible steps.
- [x] `cli/deploy.py` — pre-action reconciliation check for all three.
- [x] `cli/deploy.py` — audit/complete `done|skipped|failed` step reporting for all three.
- [x] `core/findings.py` / `core/verdict.py` — register the open-intent-WARN code if needed.
- [x] Unit tests for every new/edited module, including the full I/O matrix above and an NFR-7 test per action.
- [x] `deferred-work.md` — log any scope narrowed during implementation.

**Acceptance Criteria:**
*(Story 4.6's ACs from `epics.md`, preserved as the contract of record.)*
- Given a deploy that failed partway, when it is re-run, then each step reports `done | skipped | failed` and already-promoted specs are neither re-promoted nor duplicated
- And a re-run against a fully converged system produces zero changes and exit 0 (NFR-7)
- Given a lone `intent` entry from a crash, when reconciliation runs, then it is closed only by a `reconciliation` outcome carrying observed external evidence — commit sha, worktree absence, PR number — plus the reconciling command (AD-28)
- And absent evidence the intent stays open and is reported
- And reconciliation may observe and close; it may never re-perform an action whose intent is open without evidence the action did not occur — the explicit AD-6 × AD-21 precedence

## Design Notes

**Why this story retrofits three already-shipped commands rather than building new ones.** Its own Deps (S-4.1, S-4.4) name the exact commands that need hardening — this is the pattern this whole epic has followed elsewhere (Story 4.1's own live run found and fixed a real bug in itself after merging; Story 4.2 reused rather than duplicated Story 4.1's machinery). AD-6's crash-safety guarantee is only as good as its weakest actual writer, and today none of the three real irreversible-action call sites honor it.

**Why label application in `batch-pr` doesn't get its own intent/outcome pair.** AD-6's own criterion is "irreversible or externally-visible" — a label is trivially reversible (remove it, re-add it) and carries no data-loss risk if mis-applied or double-applied (GitHub's own label API is itself idempotent). The PR create/update is the one genuinely irreversible/hard-to-reverse step in that command.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: all green, new tests included, zero regressions.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` — expected: all import-linter contracts hold.

**Manual checks (if no CLI):**
- Simulate a crashed `promote` (an open intent with no outcome) against a real throwaway Tier-3 fixture and confirm a re-run either reconciles via evidence or reports the open intent as a `WARN`, never re-promoting a spec that's already durably archived.

## Spec Change Log

**1. Journal file layout for the new intent/outcome pairs -- adapted, not specified by the Code Map.** The Code Map names `cli/deploy.py`'s own three commands as the site of the new intent/outcome writes but does not specify a file layout. Implemented by reusing this module's own established `_journal_manual_landing`/`cli/init.py::_journal_abandonments` shape (`_mint_deploy_run`: mint a fresh, dedicated Tier-3 run directory per invocation, `implementation-artifacts/runs/<run_id>/journal.jsonl`) rather than inventing a single persistent per-slug journal file. Since a reconciliation outcome is written by a LATER, independent invocation than the intent it closes, pairing them (AD-28's "pairing is by `intent_id` ONLY") requires a GLOBAL fold across every run directory (`_fold_deploy_journal`), not a per-directory one -- a per-directory fold (this module's own pre-existing `_gather_gate_verdicts` precedent) would show the same intent as perpetually open in its own origin file even after a later run's reconciliation outcome closed it. Logged as a scope note in `deferred-work.md` (unbounded run-directory scan as a Tier-3 store accumulates runs over a project's lifetime) rather than treated as a defect -- no AC bounds performance and this project's current scale (tens of runs per slug) shows no practical concern.

**2. Reconciliation-evidence classification function name and location -- `core.journal.intent_reconciles`, not specified by name in the Code Map.** The Always bullet describes the function's shape ("taking the open intent's payload and the caller-gathered external evidence... returning whether it reconciles") without naming it. Implemented as `intent_reconciles(intent_payload: Mapping, evidence: Mapping) -> bool` in `core/journal.py` (confirmed live, per the story's own instruction, that no suitable reconciliation helper already existed -- `FoldResult.open_intents`/`orphaned_outcomes` are query views, not a classification). All-or-nothing semantics: reconciles only when EVERY story key an intent named appears in the evidence's own `confirmed_story_keys` -- a deliberate reading of "a batched action either fully happened or Marshal cannot positively say it did" from the story's own Always bullet (`promote` commits several specs in ONE commit).

**3. `MRS-DEPLOY-021` registered for the open-intent-WARN code -- confirmed live that none already existed.** Checked `core/verdict.py`'s `_CLASSIFY_TABLE` and `core/findings.py`'s `REGISTERED_CODES` before adding: no existing code names "an open intent with no confirming evidence" specifically (the codebase's OTHER "unclosed intent" precedent this story's Design Notes reference, `MRS-SPIN-006`, names a DIFFERENT condition -- a launch's own outcome entry failing to journal -- not a cross-invocation open-intent reconciliation gap). `MRS-DEPLOY-021` classifies `Verdict.WARN`, per AD-21's own F-17 amendment, and is shared across all three commands (`promote`/`land-story`/`batch-pr`) rather than split per-command, since the shape and severity are identical in every case: an open intent, no evidence, non-blocking.

**4. Two pre-existing Story 4.3 tests asserted the exact AD-6 gap this story closes -- updated, not weakened.** `test_land_story_merge_failure_is_a_hard_stop_with_no_journal_entry` (renamed `..._leaves_an_open_intent_with_no_outcome`) and the journal-line-count assertions in `test_land_story_merges_with_a_rendered_subject_and_journals_on_green`/`test_land_story_redaction_failure_warns_but_still_lands` asserted "no journal entry on merge failure" and "exactly one journal entry" respectively -- both true only because `land-story` wrote NO paper trail before its own `merge_branch` call (the precise gap AD-6 names and this story exists to close). Per this story's own Always bullet ("an `intent` entry BEFORE the action... an `outcome` entry after"), a merge failure now correctly leaves one open intent (not zero), and a successful landing now correctly journals three lines (the merge's own intent+outcome pair, plus the pre-existing manual-landing observation) instead of one. Updated to assert the new, AD-6-compliant behavior; no assertion was removed, only expanded (see the story's own Verification section for the full green run).

**5. `batch-pr`'s reconciliation evidence narrowed to NEVER auto-close on bare PR-existence alone -- code review, 2026-08-06, P2, both reviewers' independent top finding.** The Always bullet names the evidence for `batch-pr` as "does `ForgePort.find_open_pr` now show a PR already reflecting THIS content" -- the initial implementation read `existing is not None` as satisfying that in full, but bare PR-existence on the head branch does not confirm the PR reflects the SPECIFIC crashed intent's own story keys (a stale PR from an earlier, differently-scoped wave, or a manually-opened PR, satisfies `existing is not None` identically). `ports/forge.py::PrInfo` carries no title/body/content field `ForgePort` could query to verify per-key coverage, and adding one is out of this story's own Code Map scope (no new `ForgePort` methods are named). Per the story's own guidance for exactly this shape ("if precise per-key content verification isn't feasible... the more conservative and still-correct fix is to NOT auto-reconcile... via this weak signal at all"), `run_batch_pr` now always passes `confirmed_story_keys=set()` to `_reconcile_open_intents` for the `_BATCH_PR_WRITE_KIND` -- every `batch-pr` open intent stays open and reports `MRS-DEPLOY-021` until a stronger evidence source exists (e.g. a future `ForgePort` method exposing PR body/description content), requiring the operator's own confirmation rather than an automatic close on a signal too weak to trust. This does not change `create_pr`-vs-`update_pr` routing, which remains `existing`'s own, unchanged, established idempotence check.

</intent-contract>

## Review Triage Log

### 2026-08-06 — Review pass 1 (Blind Hunter + Edge Case Hunter, parallel)

- intent_gap: 0
- bad_spec: 0
- patch: 5 (critical 2, high 1, medium 2)
- defer: 3
- reject: 0
- addressed_findings:
  - `[critical]` `[patch]` **`_deploy_writer_id` minted a bare `f"deploy-{action}-{os.getpid()}"`, with the per-invocation counter always restarting at 0 -- and OS process ids are reused over time.** Before this diff, journal reads were scoped to ONE run directory at a time, so a `(writer_id, counter)` collision across two separate process invocations was harmless. This diff's own `_fold_deploy_journal` folds EVERY run directory's journal into ONE GLOBAL `fold()` call and pairs intents/outcomes by `intent_id` alone -- so a crashed invocation's open intent and a LATER, completely unrelated invocation (same action, same project, different actual target) could mint the IDENTICAL `JournalEntryId(writer_id, counter=0)`, letting the global fold mis-pair an outcome from one invocation against an intent from a different, unrelated one, corrupting AD-28's own intent/outcome pairing guarantee -- exactly "wrongly reconciled as already done," the failure mode this whole story exists to prevent. Both reviewers independently found this, top finding both times. Fixed: `_deploy_writer_id` now incorporates a fresh `secrets`-sourced random token (the same uniqueness source `mint_run_id`'s own `random_token` already uses via `_land_random_token`, reused rather than a second scheme) alongside the pid, making a collision practically impossible regardless of pid reuse. New tests: `test_deploy_writer_id_p1_unique_across_pid_reuse`, `test_deploy_writer_id_p1_pid_reuse_does_not_mispair_a_global_fold`.
  - `[critical]` `[patch]` **`run_batch_pr`'s reconciliation evidence treated "SOME PR exists on this head branch" as confirmation that EVERY key in the CURRENT wave was covered by a prior `create_pr`/`update_pr` call.** `confirmed_story_keys=set(wave_keys) if existing is not None else set()` let a stale PR from an earlier, differently-scoped wave, or a manually-opened PR unrelated to a crashed intent, satisfy the check identically to a PR that intent's own action genuinely produced -- despite the surrounding comment/docstring explicitly claiming the evidence is "does `find_open_pr` now show a PR already reflecting THIS content." Both reviewers independently found this. Fixed (the conservative branch the story's own guidance names, since `PrInfo` carries no content field to verify per-key coverage against and adding one is out of this story's `ForgePort` scope): `run_batch_pr` now always passes `confirmed_story_keys=set()` for `_BATCH_PR_WRITE_KIND` -- every `batch-pr` open intent stays open and reports `MRS-DEPLOY-021` until a stronger evidence source exists, never auto-closed on bare PR-existence alone. Documented in Spec Change Log entry 5. Rewrote `test_batch_pr_reconciles_a_prior_open_intent_when_a_pr_now_exists` into `test_batch_pr_never_auto_reconciles_on_bare_pr_existence_alone`, asserting the intent now stays open.
  - `[high]` `[patch]` **`_fold_deploy_journal`'s blanket `except (TypeError, ValueError, KeyError, OSError)` around the merged-fold call discarded the WHOLE folded history on any such exception, returning an empty `FoldResult` with ZERO finding emitted.** Not per-entry quarantine (which `core.journal.fold`'s own `_quarantine` mechanism already provides correctly) -- a blanket fallback that could make EVERY genuinely-open intent across every run directory silently invisible in one shot, with an operator seeing a clean report and no way to know reconciliation never actually ran. Fixed: a new registered `MRS-DEPLOY-022` (`Verdict.WARN`, same tier as `MRS-DEPLOY-021`) is emitted naming that the cross-run fold failed and reconciliation could not be attempted this invocation; the guarded action still proceeds normally (never blocking). New test: `test_fold_deploy_journal_p3_reports_a_finding_on_blanket_fold_failure`.
  - `[medium]` `[patch]` **`run_promote` gated its call to `_reconcile_open_intents` with `if policy._is_valid_project_slug(project_slug):`, but `run_land_story`/`run_batch_pr` called it unconditionally** -- an inconsistent defensive posture across three call sites presented as parallel implementations of the same pattern, and a minor encapsulation break (reaching into a private, `_`-prefixed cross-module function at three sites). Fixed: the guard is now applied ONCE, inside `_reconcile_open_intents` itself, and `run_promote`'s own local guard was removed as redundant -- all three call sites get the same behavior uniformly with no duplicated cross-module reach.
  - `[medium]` `[patch]` **No test constructed TWO OR MORE distinct open intents of the same kind within the same journal fold**, to verify `_reconcile_open_intents`'s loop correctly reconciles ONE while leaving the OTHER open and reporting `MRS-DEPLOY-021` for it independently -- every existing scenario carried exactly one open intent, leaving the loop's multi-intent iteration branch effectively unverified. New test: `test_promote_reconciles_one_open_intent_while_leaving_a_disjoint_one_open` (two crashed-run intents, disjoint story-key subsets; asserts exactly one `reconciliation` outcome and exactly one `MRS-DEPLOY-021` finding, each naming the correct intent).
- deferred (not fixed in this pass, appended to `deferred-work.md` as NEW entries):
  - `[medium]` `_reconcile_open_intents` runs very early in each of the three commands, before later gates/hygiene/preflight checks that could still cause the overall invocation to fail or short-circuit for an unrelated reason -- an invocation that ultimately errors out later can still have already mutated the journal (closing a legitimate crashed intent via confirmed evidence) as a side effect. Likely CORRECT behavior (closing an intent on real, confirmed evidence is valid regardless of what the rest of the invocation does), but an undocumented trade-off worth naming explicitly.
  - `[low]` The `evidence_note` human-readable string embedded in each `reconciliation` outcome's payload is a hardcoded literal per call site, never validated against what `confirmed_story_keys` was actually derived from -- a future edit changing the real evidence source at one call site without updating the matching string could silently mislabel the audit trail.
  - `[low]` `MRS-DEPLOY-021`'s WARN message's blanket reassurance ("its own existing idempotence check may make attempting it again safe regardless") is reasonable for `commit_paths`/`merge_branch` but overstates confidence for `create_pr`/`update_pr`, whose safety depends entirely on `find_open_pr` accuracy -- worth softening the message language in a future pass, not urgent given P2's fix above already tightens the underlying evidence check for that exact case.
- rejected: none this pass.

## Suggested Review Order

**The two critical fixes (P1, P2) — start here**

- `_deploy_writer_id`: the P1 fix adding a random token, closing the PID-reuse collision the new cross-run global fold introduced.
  [`deploy.py:1309`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py#L1309)

- `_reconcile_open_intents`: the P2 fix disabling auto-reconciliation for `batch-pr` entirely (no `ForgePort` primitive exists to verify PR content matches specific keys — always requires operator confirmation instead of a weak bare-existence check), plus the P4 unified slug-validity guard.
  [`deploy.py:1576`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py#L1576)

**Supporting fix**

- `_fold_deploy_journal`: the P3 fix reporting a finding on blanket fold failure instead of silently returning an empty result.
  [`deploy.py:1374`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py#L1374)

- `intent_reconciles`, the pure evidence-classification core all three call sites share.
  [`journal.py:1104`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/journal.py#L1104)

**Tests (peripherals)**

- Writer-ID collision proof, blanket-fold-failure finding, multi-intent reconciliation (P5), and the corrected `batch-pr` never-auto-reconciles test.
  [`test_deploy.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_deploy.py#L1)
