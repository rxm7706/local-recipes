---
title: 'The layers are enabled on `factory spin`, or spin is declared a two-layer engine'
type: 'decision+feature'
created: '2026-09-09'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: 'b29ef400190bcfb1b3abb83ac05085ae7f278798'
context: []
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** On `factory spin` marshal launches `bmad-loop run`, so there is no argv to
prefix (`DW-FU-28-2`). Separately, `cli/dispatch.py:318` folds `read_repo_policy_defaults()`
while `cli/spin.py` does not (`DW-FU-28-2-3`), so a repo-wide `[context]` block acts on one
engine and vanishes silently on the other.

**Approach:** Fold `read_repo_policy_defaults()` into `cli/spin.py` unconditionally, then
attempt the loop-home launcher shim through bmad-loop's own `adapters/profile.py` seam
(`binary`/`launch_args`/`env`) and the `.bmad-loop/profiles/*.toml` overlay marshal already
writes to all eight loop homes.

## Boundaries & Constraints

**Always:** `read_repo_policy_defaults()` is folded on both engines regardless of which
branch below is taken. The decision is recorded as a dated ruling in
`docs/dreams/marshal-token-economy.md`'s Realization log and in this Spec's memlog, not
left implicit.

**Never:** This story does not leave the fold one-sided. It does not invent a second
wrapping mechanism outside the named `adapters/profile.py` seam.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Wire-layer shim succeeds | bmad-loop's profile seam accepts a wrapped launch | Wire layer acts on spin; the Dream's five-layer matrix is corrected | No error expected |
| Wire-layer shim fails | seam cannot carry the wrap | Attempt recorded as unavailable with its reason; spin declared a two-layer engine (output, structure-graph) | Recorded, not silent |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py` -- gains the `read_repo_policy_defaults()` fold
- `core/harness_profile.py` -- composition site shared with dispatch
- `adapters/harness_bmadloop.py` -- spin's engine adapter
- `~/.bmad-loops/*/.bmad-loop/profiles/*.toml` (x8) -- the overlay marshal already writes; shim target
- `docs/dreams/marshal-token-economy.md` § Addendum matrix -- where the dated ruling is recorded

## Tasks & Acceptance

**Execution:**
- `cli/spin.py` -- add the repo-policy-defaults fold, unconditional of which branch below lands
- Attempt the loop-home launcher shim via `adapters/profile.py`'s `binary`/`launch_args`/`env`
- `docs/dreams/marshal-token-economy.md` -- record the dated ruling in the Realization log either way
- This spec's memlog -- record the same ruling

**Acceptance Criteria:**
- Given the fold is missing on spin today, when this story lands, then `read_repo_policy_defaults()` is folded on both `cli/dispatch.py` and `cli/spin.py`
- Given the shim attempt, when it succeeds, then the wire layer acts on spin and the five-layer matrix is corrected in the Dream; when it fails, then spin is declared a two-layer engine on the record, with cost-sensitive work routed to `factory dispatch`
- Given either outcome, when the story closes, then a dated ruling exists in both the Dream's Realization log and this Spec's memlog

## Spec Change Log

## Review Triage Log

### 2026-09-09 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: none — full suite green after Story 33.3 implementation

## Auto Run Result

**Summary:** Folded `read_repo_policy_defaults()` into `factory spin` via `_compose_spin_policy`
(closing DW-FU-28-2-3). Implemented the bmad-loop profile-overlay wire shim
(`attempt_spin_wire_layer`): when the wire layer is enabled and headroom resolves, spin writes
`.bmad-loop/profiles/<adapter>.toml` before launch and reports `wire.applied=True`. Recorded the
dated ruling in the Dream realization log and this spec's memlog — wire acts on spin; spin is not
declared a two-layer-only engine.

**Files changed:**
- `cli/spin.py` — `_compose_spin_policy`, wire overlay attempt, supervisor wire reporting
- `adapters/harness_bmadloop.py` — `attempt_spin_wire_layer`, overlay render/write helpers
- `core/harness_profile.py` — `PROFILE_BY_BMADLOOP_ADAPTER`
- `tests/unit/test_spin.py` — wire apply/degrade/resume tests updated for 33.3
- `docs/dreams/marshal-token-economy.md` — matrix + realization log ruling
- `planning-artifacts/specs/spec-33-3-*.memlog.md` — memlog entry

**Review:** 0 patches. 0 deferred.

**followup_review_recommended:** false

**Verification:**
- `pixi run -e pyforge-marshal pyforge-marshal-test` — PASS (7564 tests)

**Residual risks:** Wire overlay applies only for bmad-loop adapters with a marshal `[wrapper]`
(today: claude). derived-context and planning-graph remain dispatch-only.

## Verification

**Commands:**
- `pixi run -e pyforge-marshal pyforge-marshal-test` -- expect green

**Manual checks (if no CLI):**
- Confirm a repo-wide `[context]` block now acts identically (or is identically declared two-layer) on both `factory dispatch` and `factory spin`
