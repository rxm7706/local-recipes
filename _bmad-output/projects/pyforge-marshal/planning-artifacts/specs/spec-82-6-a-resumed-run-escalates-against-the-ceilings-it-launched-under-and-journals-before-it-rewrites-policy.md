---
title: '82.6: A resumed run escalates against the ceilings it launched under and journals before it rewrites policy'
type: 'fix'
created: '2026-10-02'
status: 'in-review'
baseline_revision: '1a2ef172558d19a460e24731cc1eed9856444c0c'
review_loop_iteration: 0
followup_review_recommended: false
warnings: ['oversized']
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Retry escalation and model tiering both rewrite the loop home's `.bmad-loop/policy.toml`, and both do it
loosely. Re-verified at HEAD a7cdb91fe4:

- `cli/spin.py::_apply_retry_escalation` (`:1928`) reads `max_dev_attempts` and `max_review_cycles` from the on-disk
  `policy.toml` at resume time (`fs.read_text(policy_path)`, `:1975`) and compares them with `DeferredStory.attempt` and
  `.review_cycle`, counters accumulated under whatever policy governed the launch. A re-render in between (`marshal config
  --write-harness-policy`, or a later `factory spin` in the same home) that raises a ceiling makes a story that exhausted
  the original ceiling stop qualifying; nothing persists the launch-time ceilings (DW-3-12-1).
- `run_spin` calls `_resolve_model_tiering` (`:1643`, which writes `policy.toml` via `write_policy_toml` at `:744`) before
  `mint_run_id` (`:1673`), `create_dir_exclusive` (`:1679`) and the launch intent; `run_resume` calls
  `_apply_retry_escalation` (`:2283`) before `mint_run_id` (`:2296`) and `create_dir_exclusive` (`:2302`). If run-directory
  creation or the intent append then fails, the policy change is on disk with no journal record (DW-3-12-3).

**Approach:**

- The launch intent records the `[limits]` ceilings the run starts under (`max_dev_attempts`, `max_review_cycles`) as read
  from the rendered `policy.toml`.
- `_apply_retry_escalation` reads those ceilings from the launch entry of the run being resumed (the Marshal run whose
  `run-launch` outcome carries the same `harness_run_id`); only a run whose launch recorded none falls back to the on-disk
  file, as today.
- Both commands decide the policy change first, journal their intent naming it (from and to model, the stories that
  triggered it), and write `policy.toml` only after that intent is durable; a failure before then leaves the file
  untouched and reported.

Ledger key: `82-6-a-resumed-run-escalates-against-the-ceilings-it-launched-under-and-journals-before-it-rewrites-policy`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-20 (a story that exhausts its attempt or cycle threshold next runs under a stronger model) and
  CAP-19 (the model-tiering policy write), with Story 3.12 (FR-183; AD-26, AD-28). Defects of shipped behaviour, so no new
  CAP; no flag.

## Acceptance Criteria

- Given a run whose launch recorded `max_dev_attempts = 2`, a story deferred at attempt 2, and an on-disk `policy.toml` now saying 4 When `marshal factory resume` runs Then escalation fires
- Given a run whose launch entry records no ceilings When resume runs Then escalation reads the on-disk `policy.toml` as today
- Given `run_spin` with model tiering that changes the model When the intent append fails Then `policy.toml` is byte-identical to before and the failure is reported
- Given `run_resume` with an escalation to apply When run-directory creation fails Then `policy.toml` is unchanged
- Given a successful launch or resume that changes the model When the journal is read Then its intent entry names the change and precedes the write
- Given either fix reverted When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** The on-disk `policy.toml` stays the harness's input; the journal records why it changed. Escalation stays
bounded and idempotent. Close DW-3-12-1 and DW-3-12-3 in `deferred-work-ledger.md` when the story lands (status `closed`, a
`resolved:` line naming this story).

**Never:** Do not re-run `policy.compose()` at resume. Do not write bmad-loop's own run state. Do not change the
spin guards (Story 82.7's surface).

</intent-contract>

## Binding

Parent: Story 3.12, `spec-pyforge-marshal` CAP-20 and CAP-19; a defect, no new CAP.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 entry.
Ledger key: `82-6-a-resumed-run-escalates-against-the-ceilings-it-launched-under-and-journals-before-it-rewrites-policy`.
Ledger status at mint: `backlog`.
Deps: —.
Closes: DW-3-12-1, DW-3-12-3.

## Code Map

Anchors re-verified at HEAD `38c0958808` (the spec's `a7cdb91fe4` line numbers are stale: 82.4/82.5 shifted them).
All under `src/shared/packages/pyforge-marshal/`.

- `src/pyforge/marshal/cli/spin.py:647` `_resolve_model_tiering` -- resolves tier, renders, then writes `policy.toml` itself
  (`write_policy_toml` `:771`, MRS-SPIN-015 `:778`); `attempt_spin_wire_layer` follows (`:797`). Only `run_spin` calls it.
- `cli/spin.py:1770` `run_spin` -- tiering call, then the spin guard (`:1773`, 82.7's surface, do not touch), then
  `mint_run_id` `:1800`, `create_dir_exclusive` `:1806`, launch intent `:1819` (`fsync=True`), `harness.spin` `:1854`.
- `cli/spin.py:2058` `_apply_retry_escalation` -- reads on-disk `policy.toml` (`:2105`), takes ceilings from its `[limits]`
  (`:2117-2141`), floor-raises `[adapter].model` and writes via `write_policy_document` (`:2163`, MRS-SPIN-016).
- `cli/spin.py:2412` `run_resume` -- escalation call, then `mint_run_id` `:2426`, `create_dir_exclusive` `:2432`, intent
  `:2444` (already carries `escalated`/`escalated_stories`/`from_model`/`to_model`), outcomes `:2499`, `:2516`.
- `cli/spin.py:1976-2017` `_latest_run_dir` / `_resolve_harness_run_id_for_resume` -- reuse pattern: real-FS `Path.glob`
  over `<tier3>/runs/<slug>-*`, journal read through `fs.read_text` + `core.journal.fold`.
- `src/pyforge/marshal/adapters/harness_bmadloop.py:797,1048` `write_policy_toml` / `write_policy_document` -- unchanged;
  both raise `HarnessPolicyWriteError`. Read-only here.
- `tests/unit/test_spin.py:40` `FakeFs` (`appended_lines`, `fail_create_dir_exclusive`, `fail_append_line`,
  `read_text_contents`), `:2531` `_outcome_line`, `:2562` `_seed_resolvable_prior_run`, `:3130` `_BASELINE_POLICY_TOML`,
  `:3155` `_seed_resume_with_deferred`, `:3175-3425` escalation tests, `:3486-3735` tiering tests. Tests reach both
  functions only through `run_spin` / `run_resume`; `:3397` pins the MRS-SPIN-016 contract this story changes.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md:1429,1459` -- DW-3-12-1 / DW-3-12-3.

## Tasks & Acceptance

**Execution:**
- `src/pyforge/marshal/cli/spin.py` -- `_resolve_model_tiering` stops writing: it returns `(refuse, plan)` where `plan`
  (a frozen `_TierPolicyWrite`: effective policy, difficulty, adapter, tier resolution, rendered `[limits]`, change record)
  is applied by a new `_write_tier_policy` -- the MRS-SPIN-015 degrade moves there unchanged -- RATIONALE: DW-3-12-3.
- `cli/spin.py` `run_spin` -- apply the plan after the intent append succeeds and before `harness.spin`; the intent
  payload gains `limits` (plan ceilings, else the on-disk file's, else absent) and `policy_change`
  (`from_model`, `to_model`, `governing_difficulty`, `stories`) when a plan exists.
- `cli/spin.py` -- split `_apply_retry_escalation` into `_plan_retry_escalation` (decide, no write) and
  `_write_retry_escalation` (the `write_policy_document` call and MRS-SPIN-016 degrade); add `_valid_ceilings` (the int /
  non-bool / >= 1 guard, shared by both ceiling sources) and `_launch_limits_for_resume` (scan the slug's run dirs for the
  `run-launch` outcome carrying `harness_run_id`, return that run's recorded `limits`).
- `cli/spin.py` `run_resume` -- plan, mint, create dir, journal the intent, then write; `data["escalated"]` and its
  detail fields turn true only once the write took effect; the outcome payloads gain `escalation_applied` when a plan existed.
- `tests/unit/test_spin.py` -- one test per acceptance criterion below, each failing when its fix is reverted; amend
  `:3397` (intent names the attempted escalation, `escalation_applied` is false, report says `escalated: False`).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` -- DW-3-12-1 and DW-3-12-3 to
  `status: closed` with a `resolved:` line naming Story 82.6.

**Acceptance Criteria:** the six criteria in the intent contract above, each pinned by a named test in `test_spin.py`.

## Spec Change Log

## Design Notes

- The intent is the write-ahead record (AD-6): it says what Marshal is about to do, the outcome says what happened. A
  failed escalation write after a durable intent is therefore reported, not hidden: MRS-SPIN-016 fires, the report says
  `escalated: False`, and the resume outcome carries `escalation_applied: false`.
- A malformed recorded `limits` counts as "recorded none" and falls back to the on-disk file, like a launch from before this
  story. A failed spin write after a durable intent can leave the recorded ceilings those of the render that never landed;
  MRS-SPIN-015 already says the harness then runs on the prior file, and the same loop home could not run it either way.
- Deferring the tiering write also stops a refused spin guard (82.7) from leaving a rewritten `policy.toml` behind. That is
  a consequence of the reorder, not a change to the guard.
- Out of scope: DW-3-12-2 (naming a newly crossing story once already escalated) and DW-3-12-4 (an unwrapped
  `tomlkit.dumps` ahead of the atomic write) stay open; neither is in this story's `Closes:`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

## Review Triage Log

- No review has run yet.
