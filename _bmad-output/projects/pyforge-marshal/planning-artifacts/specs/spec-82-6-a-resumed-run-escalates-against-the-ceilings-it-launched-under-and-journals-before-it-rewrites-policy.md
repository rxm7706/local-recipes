---
title: '82.6: A resumed run escalates against the ceilings it launched under and journals before it rewrites policy'
type: 'fix'
created: '2026-10-02'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
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

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

## Review Triage Log

- No review has run yet.
