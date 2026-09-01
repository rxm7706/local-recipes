---
title: 'The graduated compression ladder (Story 28.6, Epic 28)'
type: 'feature'
created: '2026-08-30'
status: 'in-review'
baseline_revision: 'pending-operator-verify'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: heavy
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

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/supervise.py` (idle/budget ladder precedent)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/supervisor/` (tick)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py` (threshold key in the `[context]` block)

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated
(ladder ordering, FR-51-seam-only, no-skip guarantee, journaled escalation). Land this spec
in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 28.6 and spec-marshal-token-economy CAP-8. Sibling to the idle-strand
ladder (Story 3.5) — same graduated-response idiom, new rung. Model movement is deliberately
out of this story: declared difficulty (FR-51) covers the static tier, Story 3.12 covers the
dynamic (upward-only) case, and `spec-adaptive-model-tiering` forbids downgrades.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, including this story's own new/updated test coverage.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (no undeclared dependency surface).

## Spec Change Log

- 2026-08-30: drafted from epics.md Epic 28 for fleet-drain preflight (Dream/Spec chain: docs/dreams/marshal-token-economy.md → spec-marshal-token-economy)
- 2026-08-30: ladder made compression-only — the original "may lower the model floor" clause conflicted with spec-adaptive-model-tiering's floor-raise-only constraint (found in the tiering/strategy fold-in analysis)
- 2026-09-01: implemented CAP-8 — pure compression ladder in `core/supervise.py`, supervisor tick integration, policy `escalation_threshold`, spin sidecar `compression-ladder.json`, harness aggressiveness env mapping; status → in-review pending verification commands.

## Auto Run Result

### Summary

Story 28.6 adds a graduated **compression-only** ladder: as per-story weighted token spend crosses
`escalation_threshold` (default 0.8, from `[context]`), the supervisor journals
`compression-escalation` and writes the target wire aggressiveness to
`<home>/.marshal/wire/aggressiveness` **before** `budget-stop` or idle-ladder actions on the same
tick. Model selection is untouched (FR-51 / Story 3.12 seams preserved).

### Files changed

- `src/.../core/supervise.py` — `CompressionEscalationDecision`, `evaluate_compression_ladder`,
  `ACTION_PRECEDENCE`.
- `src/.../core/policy.py` — `escalation_threshold` in `[context]`, `resolve_compression_escalation_threshold`.
- `src/.../core/harness_profile.py` — `wire_env_for_aggressiveness`, `HEADROOM_TARGET_RATIO` mapping.
- `src/.../supervisor/__main__.py` — sidecar load, `_maybe_escalate_compression`, journal + sidecar write.
- `src/.../cli/spin.py` — writes `compression-ladder.json` at supervisor spawn when wire enabled.
- `src/.../schemas/policy.json` — context field description updated for CAP-8.
- `tests/unit/{test_supervise,test_policy,test_harness_profile,test_supervisor}.py` — ladder ordering,
  threshold validation, supervisor I/O ordering test.

### Verification performed

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` → **7198 passed**, 12 deselected,
  **1 failed**: `test_skf_domain_skill::test_conda_forge_expert_not_replaced` (unrelated worktree
  drift vs `origin/main` under `.claude/skills/conda-forge-expert` — not introduced by this story).
  All Story 28.6 unit tests green, including supervisor ordering
  (`test_compression_escalation_journals_before_story_budget_stop_on_same_tick`) and pure ladder
  tests in `test_supervise.py`.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` → **118 passed**, 1 skipped.

Stamp `baseline_revision` / `final_revision` from `git rev-parse HEAD` at merge and move status to
`done`.

### Residual risks

- Mid-run aggressiveness sidecar is written by the supervisor; live headroom proxy hot-reload is
  best-effort only (deferred — escalation still journaled with threshold facts).
- Compression ladder stays off when wire layer is disabled or sidecar absent (today's behavior).
