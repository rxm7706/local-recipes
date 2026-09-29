---
title: 'The context policy block, rendered once for both engines (Story 28.1, Epic 28)'
type: 'feature'
created: '2026-08-30'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: medium
baseline_revision: 'e38f269cc5f642e86b3a379a720a191b94fb0129'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/integration-layers.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** Nothing in `EffectivePolicy` can declare a context pipeline: which
token-economy layers are on, how aggressive, where stores live. Any wiring today would be
per-loop-home hand-configuration, which marshal's policy discipline exists to forbid.

**Approach:** Add a `[context]` block to `EffectivePolicy` (composition, provenance,
validation — the existing layered-policy machinery, one composition site) and render it into
every launch surface identically for both engines (bmad-loop spin's `policy.toml` render and
factory dispatch's launch env/profile resolution). Absent block = every layer off.

## Acceptance Criteria

- Given a policy with no `[context]` block, when a run launches, then every layer is off and
  rendered output/behavior is byte-identical to today.
- Given a `[context]` block, when bmad-loop spin renders `policy.toml` and when factory
  dispatch resolves its launch, then both resolve the same declaration from one composition
  site (no second parser, no engine-specific fork).
- Given `schemas/policy.json`, when the block is present, then it validates, and policy
  provenance reporting covers its keys like any other policy key.
- Given an invalid block (unknown layer name, malformed aggressiveness), when policy
  composes, then the existing loud policy-validation failure path reports it — never a
  silent default.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-marshal/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`. Ledger
key `28-1-the-context-policy-block-rendered-once-for-both-engines`.

**Block If:** A change would make the two engines resolve the block differently, introduce a
second composition site, or change any behavior when the block is absent.

**Never:** Compress anything in this story — this is declaration plumbing only. No new gate
verdicts. No `conda-forge-expert` replacement.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py` — `EffectivePolicy`, `render_policy_toml`, DEFAULT_POLICY
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/schemas/policy.json`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py` + `cli/dispatch.py` (render/launch consumers)

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated
(including the byte-identical-when-absent regression). Land this spec in
`planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 28.1 and spec-marshal-token-economy CAP-1. Follow the existing
layered-policy composition/provenance idiom (Story 1.3/1.10 precedent) — the block is policy
like any other, not a side channel. Layer names should match the companion's layer matrix
(wire, output, structure-graph, derived-context, planning-graph).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, including regression coverage for the `context` policy block: byte-identical rendered TOML when the block is absent, and an identical `context` payload surfaced by both `render_policy_toml` (`adapters/harness_bmadloop.py`) and `dispatch_once`'s returned/journaled data (`cli/dispatch.py`).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (no new dependency surface introduced by this story).

## Spec Change Log

- 2026-08-30: drafted from epics.md Epic 28 for fleet-drain preflight (Dream/Spec chain: docs/dreams/marshal-token-economy.md → spec-marshal-token-economy)

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `92043c0a29` (2026-09-01, "Merge pull request #1002 from rxm7706/dispatch/pyforge-marshal/28.19"); also `eb1dbd6632` (2026-09-01, "Merge pull request #1000 from rxm7706/dispatch/pyforge-marshal/28.18"); also `7b919d63c3` (2026-08-31, "Merge pull request #971 from rxm7706/dispatch/pyforge-marshal/28.15"). Ledger row `28-1-the-context-policy-block-rendered-once-for-both-engines: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-28-19-missing-spec-escalates-never-idle-with-backlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml`, `scripts/fleet_picture.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_fleet.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py`, `src/shared/packages/pyforge-marshal/tests/meta/test_fleet_picture_missing_spec.py`, `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_hotfix.py`, `src/shared/packages/pyforge-marshal/tests/unit/test_status.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
