---
title: 'The graduated compression ladder (Story 28.6, Epic 28)'
type: 'feature'
created: '2026-08-30'
status: 'blocked'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: heavy
baseline_revision: 'f5858beff8b277a37ef38ad72bfca749072b8b3d'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/integration-layers.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** A story approaching its token ceiling today has exactly one future: the
stop-retry-defer ladder kills it. There is no softer intervention between "spending
normally" and "dead".

**Approach:** The supervisor gains a compression rung below the existing idle/kill ladder:
as a story's weighted spend approaches its ceiling (threshold from the `[context]` block),
compression aggressiveness is raised. The ladder is **compression-only**: it never changes
the model. Model selection stays where it already lives — statically with the declared
`difficulty:` (FR-51 tiering), dynamically only as Story 3.12's struggle-triggered
floor-*raise* (`spec-adaptive-model-tiering` constraint: escalation is a floor-raise only,
never a downgrade). Escalation is journaled like every other supervisor act.

## Acceptance Criteria

- Given a story crossing the escalation threshold, when the supervisor evaluates the ladder,
  then compression escalation strictly precedes stop-retry-defer — proven by a test on
  ladder ordering.
- Given an escalation, when it applies, then the launched model is unchanged — escalation
  raises compression aggressiveness only; no model-selection change of any direction occurs
  outside the existing FR-51 declared-difficulty and Story 3.12 floor-raise seams.
- Given any escalation level, when the story proceeds, then no gate or reviewer is skipped
  and the contract artifacts (spec/ACs/verdicts) remain uncompressed.
- Given an escalation event, when it happens, then it is journaled with the threshold facts
  that triggered it.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-marshal/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`. Ledger
key `28-6-the-graduated-compression-ladder`.

**Block If:** A change would reproduce the `DW-AD23-3` shape (a cap/escalation silently
dropping real reviewer-recommended work), skip review, or bypass the FR-51 seam.

**Never:** Escalation as a kill substitute — the existing ceilings stay the final backstop.
A second model-selection mechanism. A model *downgrade* under budget pressure — it would
violate `spec-adaptive-model-tiering`'s shipped floor-raise-only constraint.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/supervise.py` — `evaluate_compression_ladder`, `ACTION_PRECEDENCE`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/supervisor/__main__.py` — tick integration, sidecar load, journaling
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py` — `escalation_threshold` in `[context]`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py` — writes `compression-ladder.json` at supervisor spawn
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_profile.py` — wire aggressiveness env mapping

## Tasks & Acceptance

- [x] Pure compression ladder decision in `core/supervise.py`
- [x] Supervisor tick evaluates compression before budget-stop / idle ladder (`ACTION_PRECEDENCE`)
- [x] Policy `escalation_threshold` (default 0.8) in `[context]`
- [x] Spin/resume writes `compression-ladder.json` sidecar when wire enabled
- [x] Unit + integration tests for ladder ordering, threshold facts, sidecar, seam guard
- [x] Meta test: compression functions never reference model/gate seams

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 28.6 and spec-marshal-token-economy CAP-8. Sibling to the idle-strand
ladder (Story 3.5) — same graduated-response idiom, new rung. Model movement is deliberately
out of this story: declared difficulty (FR-51) covers the static tier, Story 3.12 covers the
dynamic (upward-only) case, and `spec-adaptive-model-tiering` forbids downgrades.

Runtime aggressiveness is written to `.marshal/wire/aggressiveness` for the headroom wrapper;
output-compression (CAP-3) and contract artifacts are untouched.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, including this story's own new/updated test coverage.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (no undeclared dependency surface).

## Spec Change Log

- 2026-08-30: drafted from epics.md Epic 28 for fleet-drain preflight (Dream/Spec chain: docs/dreams/marshal-token-economy.md → spec-marshal-token-economy)
- 2026-08-30: ladder made compression-only — the original "may lower the model floor" clause conflicted with spec-adaptive-model-tiering's floor-raise-only constraint (found in the tiering/strategy fold-in analysis)
- 2026-09-01: implemented CAP-8 — compression ladder in supervise/supervisor/policy/spin; added meta seam guard + sidecar test; status blocked pending verification commands (agent shell unavailable)
- 2026-09-01: bmad-build-auto re-run — static review confirms AC coverage; verification still blocked (shell rejected in session)

## Review Triage Log

### 2026-09-01 — Review pass (initial)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none

### 2026-09-01 — Review pass (bmad-build-auto re-run)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none

Manual review (no diff subagents — shell/render_skill blocked): all four ACs have dedicated tests — `ACTION_PRECEDENCE` + `test_compression_escalation_journals_before_story_budget_stop_on_same_tick` (ordering); `CompressionEscalationDecision` field set + `test_cap8_compression_ladder_seam` (model/gate seam isolation); supervisor journals `observed`/`limit`/`threshold`/`declared_aggressiveness`/`target_aggressiveness`; tick loop calls `_maybe_escalate_compression` before `_act_on_budget_transition` for story tokens and before the idle-ladder block.

## Auto Run Result

Status: blocked

Blocking condition: implementation verification could not run — agent session rejected all shell invocations (`render_skill.py`, `pixi run`, `git`); verification commands in § Verification were not executed.

Summary of implemented change: Story 28.6 (CAP-8) adds a graduated wire-compression ladder below the idle/budget kill ladders. As per-story weighted spend crosses `escalation_threshold` (default 0.8 from `[context]`), the supervisor journals `compression-escalation` with threshold facts and raises wire aggressiveness via `.marshal/wire/aggressiveness` before any `budget-stop` or idle-ladder action on the same tick. Model selection is untouched (FR-51 / Story 3.12 seams only).

Files changed (since `baseline_revision`):
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/supervise.py` — `evaluate_compression_ladder`, `CompressionEscalationDecision`, `ACTION_PRECEDENCE`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/supervisor/__main__.py` — sidecar load, `_maybe_escalate_compression`, tick ordering
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py` — `resolve_compression_escalation_threshold`, schema docs
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py` — `compression-ladder.json` sidecar at supervisor spawn
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/schemas/policy.json` — `escalation_threshold` documented
- `src/shared/packages/pyforge-marshal/tests/unit/test_supervise.py` — pure ladder + ordering tests
- `src/shared/packages/pyforge-marshal/tests/unit/test_supervisor.py` — same-tick compression-before-budget-stop integration test
- `src/shared/packages/pyforge-marshal/tests/unit/test_policy.py` — threshold resolution tests
- `src/shared/packages/pyforge-marshal/tests/unit/test_spin.py` — sidecar write test
- `src/shared/packages/pyforge-marshal/tests/meta/test_cap8_compression_ladder_seam.py` — static FR-51/gate seam guard
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-28-6-the-graduated-compression-ladder.md` — this spec (tasks checked, auto-run record)
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml` — ledger key `28-6-the-graduated-compression-ladder: blocked`

Review findings breakdown: 0 patches, 0 deferred, 0 rejected (manual static review only).

Follow-up review recommendation: false (0 patched findings).

Verification performed: not run. Unblock by executing § Verification locally; on green, set `status: done`, stamp `baseline_revision` from `git rev-parse HEAD`, and set ledger `28-6-the-graduated-compression-ladder: done`.

Residual risks: none identified in static review; runtime confirmation depends on the verification commands above.
