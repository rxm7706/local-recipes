---
title: '82.6: A resumed run escalates against the ceilings it launched under and journals before it rewrites policy'
type: 'fix'
created: '2026-10-02'
status: 'done'
baseline_revision: '1a2ef172558d19a460e24731cc1eed9856444c0c'
review_loop_iteration: 0
followup_review_recommended: false
warnings: ['oversized']
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
deferred:
  - summary: >-
      A chained resume judges a story deferred during an earlier resume against the launch run's recorded ceilings, not the ceilings that resume ran under.
    evidence: |-
      Only the run-launch intent records `limits` (read back by `_launch_limits_for_resume`); the run-resume intent records none. If policy.toml is re-rendered between the launch and the first resume, a story that defers during that resume has counters accrued under the re-rendered ceilings but is judged against the launch's. Unverified: whether `bmad-loop resume` re-reads `.bmad-loop/policy.toml` or reuses the run's own policy snapshot. Settle by reading bmad_loop's resume path, or by a live two-resume run with a ceiling re-rendered between the resumes.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py:2240
    severity: medium (unverified)
  - summary: >-
      `run_spin` still writes the wire-layer profile overlay inside `_resolve_model_tiering`, before the launch intent and the in-flight guard.
    evidence: |-
      `attempt_spin_wire_layer` runs at the end of `_resolve_model_tiering`, ahead of `mint_run_id`, run-directory creation and the intent append. A failed intent append or a refused spin guard leaves that overlay rewritten with no journal record: the DW-3-12-3 pattern for a different file. Pre-existing, and outside this story's policy.toml scope; moving it after the intent changes when `data["wire"]` is set for the outcome payload, which the wire-layer capability's own contract owns.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py:875
    severity: low
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

### 2026-10-02 — Review pass
- verdicts: 34 findings — high 0, medium 1, low 25, false 7, maybe-false 1
- findings:
  - `[low]` `[reject]` BH1 launch ceilings can be recorded for a policy.toml that was never written (MRS-SPIN-015) — needs a failed write after a durable intent AND ceilings that differ from the file on disk; an unwritable loop home also defeats the later resume's own write (MRS-SPIN-016); the fix adds a journal field and a branch; accepted in Design Notes and carried to Auto Run Result as a residual risk.
  - `[maybe-false]` `[defer]` BH2 a chained resume judges counters against the launch's ceilings, not those the earlier resume ran under — would settle on whether `bmad-loop resume` re-reads policy.toml or keeps the run's snapshot; if true, medium (unverified); recorded under `deferred`.
  - `[low]` `[reject]` BH3 the resume intent's `escalated` now means "planned" — the intent mandated by this story is write-ahead by definition and `escalation_applied` on the outcome carries the fact; no consumer reads the field (dispatch.py's `escalated` is its own entry); a rename is public surface.
  - `[low]` `[reject]` BH4 spin has no `escalation_applied` equivalent — before this story the spin write left no journal record at all; the finding stays in the report as MRS-SPIN-015; a new outcome field is public surface for an unlikely failure.
  - `[low]` `[reject]` BH5 `policy_change` appears when nothing changes and names only the dev stage — a from==to record is accurate, and the outcome entry already journals `resolved_models` for every stage; the contract asks for "from and to model".
  - `[false]` `[reject]` BH6 no recorded evidence for AC6 or the verification commands in the spec — the Triage Log and Auto Run Result are written by this step; the evidence is recorded below.
  - `[low]` `[patch]` BH7 stale references to `_apply_retry_escalation` — the only live one was the docstring at test_spin.py:3239, fixed; the ledger rows, epics.md story sections, change-history and the dream are dated history and stay.
  - `[low]` `[reject]` BH8 `_launch_limits_for_resume` reads journals before the cheap short-circuits and repeats an existing scan — resumes are rare and journals small; no named harm.
  - `[low]` `[patch]` BH9 test gaps on the journal-reading path — the spawn-failure outcome assertion was real and is fixed with VG1's test; the run_id filter, an unmatched or unreadable journal falling back, and splitting one test are rejected: defensive branches that fall back to today's on-disk read.
  - `[false]` `[reject]` BH10 spec-surface stamp left pending — `scripts/spec_surface_reconcile.py` and `spec-surface-check` both exit 0; the run forbids `--write-baseline`; both memlogs name every governed path changed.
  - `[low]` `[reject]` BH11 API-shape nits (tuple return, frozen dataclass holding dicts, a second policy read, a redundant `int()`) — cosmetic; no caller can diverge.
  - `[false]` `[reject]` EC1 `tier_plan.limits` None falls back to the on-disk file while a rewrite is pending — `render_policy_toml` seeds both `[limits]` keys unconditionally and refuses a value below 1, so `limits` is non-None whenever a plan exists.
  - `[low]` `[reject]` EC2 a failed `_write_tier_policy` leaves limits and `policy_change` journaled with no spin outcome field — same root cause as BH1 and BH4.
  - `[low]` `[reject]` EC3 policy.toml edited between the plan read and the write — a read-modify-write race that existed before; the window grew by one directory creation and one append; the fix re-reads and compares.
  - `[low]` `[reject]` EC4 `from_model` is read at plan time, not at the write — same root cause as EC3.
  - `[low]` `[reject]` EC5 a crash between the resume intent and the write leaves `escalated: true` unapplied — inherent in a write-ahead intent; same root cause as BH3.
  - `[low]` `[defer]` EC6 `attempt_spin_wire_layer` still writes the wire overlay before the intent — pre-existing, a different file from policy.toml; recorded under `deferred`.
  - `[low]` `[reject]` EC7 a non-`HarnessPolicyWriteError` raised by the writer escapes after a durable intent — already tracked as open DW-3-12-4; `_resolve_model_tiering` rendered the same inputs moments earlier, so the unwrapped path is not reachable in practice.
  - `[false]` `[reject]` EC8 `policy_change` is journaled even when no model moved — the record is accurate and no consumer reads it; the contract requires the record when the model changes, not only then.
  - `[low]` `[reject]` EC9 `policy_change` names only the dev stage — same root cause as BH5.
  - `[low]` `[reject]` EC10 `_launch_limits_for_resume` reads every sidecar newest-first — same root cause as BH8.
  - `[low]` `[patch]` EC11 stale references after deleting `_apply_retry_escalation` — same root cause as BH7; the test docstring was fixed.
  - `[low]` `[reject]` EC12 the intent records the render's ceilings though the write may fail — same root cause as BH1.
  - `[low]` `[reject]` EC13 the Design Notes sentence "the same loop home could not run it either way" is imprecise — the fix is editing this build's spec; the underlying mismatch is BH1.
  - `[low]` `[reject]` EC14 "no model change exists without a record" overstates, since `policy_change` is dev-only — the outcome's `resolved_models` records every stage; same root cause as BH5.
  - `[low]` `[patch]` VG1 the resume launch-failure outcome's `escalation_applied` is unpinned (removing it left test_spin.py green, mutation-demonstrated by the layer) — fixed: `test_resume_launch_failure_outcome_carries_escalation_applied` (write took effect, write failed); mutation D (the field removed from that branch) fails both cases on two runs.
  - `[medium]` `[patch]` VG2 nothing pins that the policy.toml write lands before `harness.spin` / `harness.resume` (deferring both writes past the spawn left the suite green, mutation-demonstrated by the layer) — fixed: the two ordering tests log the write to the shared `events` list and assert it precedes "spin" / "resume".
  - `[low]` `[reject]` IA1 `escalated` means "attempted" in the intent and spin has no applied flag — same root cause as BH3 and BH4.
  - `[false]` `[reject]` IA2 `policy_change` attaches whenever a plan exists, not only when the model changes — same as EC8.
  - `[low]` `[reject]` IA3 spin's from/to model is dev-stage only and `stories` is the whole preview — same root cause as BH5; the story spec's "stories that triggered it" are the selected stories the render was resolved for.
  - `[low]` `[reject]` IA4 recorded ceilings may not be what the harness ran under after a degraded write — same root cause as BH1.
  - `[low]` `[reject]` IA5 other policy.toml writers (config, refresh, adapters) stay unjournaled — pre-existing, operator-initiated re-renders; the Approach scopes the journaling to the two launching commands.
  - `[false]` `[reject]` IA6 AC6 mutation evidence is prose only — re-verified this pass: mutations A (ceilings from the on-disk file only), B (resume writes at plan time) and C (spin writes inside the tiering decision) fail 4, 5 and 3 tests in test_spin.py; D fails the 2 new cases.
  - `[false]` `[reject]` IA7 AC1 and AC2 are tested at `run_resume`, not through argparse — `test_resume_cli_accepts_slug_and_format` asserts `args.handler is run_resume` (test_spin.py:3124), a one-hop mapping.

## Auto Run Result

Status: done
Blocking condition: none

### Summary of implemented change

A resumed run now escalates against the ceilings its own launch recorded, and neither `policy.toml` rewrite precedes its own journaled intent. The launch intent records `limits` (`max_dev_attempts`, `max_review_cycles`) and, when tiering would rewrite the file, `policy_change`. `_plan_retry_escalation` judges deferred stories against the ceilings of the `run-launch` entry whose outcome carries the resumed `harness_run_id`, and reads the on-disk file only for a launch that recorded none or a malformed record. `_resolve_model_tiering` and `_plan_retry_escalation` now return plans; `run_spin` and `run_resume` apply them (`_write_tier_policy`, `_write_retry_escalation`) only after the intent is durable. The resume outcomes gain `escalation_applied`. DW-3-12-1 and DW-3-12-3 are closed.

### Files changed

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py` -- plan/write split for both rewrites, launch-ceiling recording and read-back, `policy_change`, `escalation_applied`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/supervise.py` -- two comments naming where the ceilings now come from (no behaviour change).
- `src/shared/packages/pyforge-marshal/tests/unit/test_spin.py` -- one test per acceptance criterion plus the review-pass tests (launch-failure outcome, write-before-spawn ordering); the MRS-SPIN-016 test amended.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` -- DW-3-12-1 and DW-3-12-3 `status: closed` with `resolved:` lines.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` and `spec-pyforge-core/.memlog.md` -- surface-reconcile events naming `cli/spin.py`, `core/supervise.py` and `tests/unit/test_spin.py`; no baseline stamped.

### Review findings

34 findings from four layers. Patched (3 entries): VG2 (medium, write-before-spawn ordering now pinned), VG1 with BH9's spawn-failure part (low, launch-failure outcome now pinned), BH7 with EC11 (low, stale docstring). Deferred (2): BH2 (maybe-false, medium unverified) and EC6 (low), both under `deferred` in the frontmatter, with ledger twins `DW-marshal-82-6` and `DW-marshal-82-6-2` in `deferred-work-ledger.md` (ingested by `scripts/deferred_work_intake.py --fix --project marshal`, which the `deferred-work` detector requires). Rejected: every other finding, each with its recorded reason in the Review Triage Log.

### Follow-up review recommendation

`followup_review_recommended: false`. Patched entries by verdict: medium 1, low 2. No high, and fewer than two medium; the patches are test-only and mutation-verified, so no unverified risk is named.

### Verification performed

All exit codes read directly, never through a pipe, on the patched tree:

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- exit 0, 10033 passed, 1 skipped, 12 deselected.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- exit 0, 130 passed, 3 skipped.
- `pixi run --frozen -e pyforge-guild lint-types`, `spec-surface-check`, `story-status-check`, `deferred-work-check` -- exit 0 each; `python scripts/spec_surface_reconcile.py` -- exit 0 ("every tracked file governed or allowlisted; no drift").
- Mutation checks (AC6), each applied to `cli/spin.py`, `test_spin.py` run, source restored and byte-compared: A (ceilings from the on-disk file only) 4 failed; B (resume writes at plan time) 5 failed; C (spin writes inside the tiering decision) 3 failed; D (`escalation_applied` dropped from the launch-failure outcome) 2 failed on two runs.

### Residual risks

- **Degraded spin write.** If `_write_tier_policy` fails (MRS-SPIN-015) after the durable intent, the journaled `limits` and `policy_change` describe a render that never landed, the harness runs on the prior file, and no spin outcome field says so. Rejected as low (BH1, BH4, EC2, EC12, IA4): it needs a failed write plus differing ceilings, and a loop home too broken to write is too broken for the later resume's own write. The Design Notes sentence "the same loop home could not run it either way" overstates this; it does not hold when the failure is transient.
- **Wire overlay and chained-resume ceilings** are the two deferred items above.
- **Review-pass history.** An auto-checkpoint commit (`b0673f5108`) captured mutation A while it was applied; the next checkpoint (`144c224471`) holds the restored file. `HEAD` has no tree difference against the last pre-mutation commit (`af06ac1750`).
