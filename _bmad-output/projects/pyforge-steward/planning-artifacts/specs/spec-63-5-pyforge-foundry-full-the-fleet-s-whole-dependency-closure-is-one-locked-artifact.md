---
title: '63.5: pyforge-foundry-full — the fleet''s whole dependency closure is one locked artifact'
type: 'feature'
created: '2026-09-20'
status: 'done'
baseline_revision: '08c466b8256359386772797845a4f3cd9408b2ed'
final_revision: 'pending — the merge commit of the fleet/agents-md-mod PR (#1551)'
review_loop_iteration: 1
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** no environment ever resolved every station's extras together, so cross-feature pin conflicts stayed invisible until a fresh worktree tripped one (2026-09-20: steward's adoption-register probe found `eval-quality` only because the primary checkout had the 10 GB `local-recipes` env on disk). The fleet had no single artifact that states its real dependency closure.

**Approach:** `pixi.toml` declares `pyforge-foundry-full` = the union of every PyForge feature (`python`, `pyforge-guild`, `guild-tasks`, `pyforge-core`, `pyforge-testing-kit`, the eight stations), `no-default-feature` — never the runtime (`pyforge-guild`), never the recipe factory (`local-recipes`), never installed by default. The lock carries it on all three platforms. A station's own env carries what its code wields: `bmad-eval-quality` pinned in `pyforge-steward`. The first solve's findings are fixed at their owners with the reason written beside each pin.

## Boundaries & Constraints

**Always:**
- The union solves on linux-64, osx-arm64-min and win-64; `pixi lock` is the proof and the artifact
- A conflict the union exposes is fixed at the owning station's pin with a written reason — never by loosening the union
- Never cap without a reason (operator ruling 2026-09-20); a kept ceiling names its reason beside the pin

**Never:**
- Do not make `pyforge-foundry-full` a default or a runtime env; do not install it in CI's station jobs
- Do not move `requires-pixi` ahead of conda-forge's `pixi` package (an in-env pixi below the floor refuses the manifest)

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| first union solve | mason `python-build <1.6` vs four `>=1.6.0` floors | refused; fixed at mason (floors) | the lock's own error names the pair |
| second union solve | warden `py-rattler >=0.26.0` vs conda's rattler-solver (`<0.26`) | refused; warden floor back to 0.25.0 (catalog-sync bump, not an API need) | as above |
| fresh worktree, station envs only | steward suite | `eval-quality` found in `.pixi/envs/pyforge-steward/bin`; suite green | n/a |
| pixi 0.81.0 bump attempt | conda-forge `pixi` at 0.80.0 | `bump-pixi-version` reverted to 0.80.0; retry recorded | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-steward CAP-151`.
Surface: `pixi.toml`, `pixi.lock`, `scripts/pixi_version_registry.py` (+ `docsite-check.yml` site), `src/shared/packages/pyforge-mason/pixi.toml`, `src/shared/packages/pyforge-mason/src/pyforge/mason/engines/__init__.py`, `src/shared/packages/pyforge-mason/tests/meta/test_engine_version_range_sync.py` (mason memlog decision: floors), `[feature.pyforge-warden.dependencies]` (`py-rattler`).
Ledger key: `63-5-pyforge-foundry-full-the-fleet-s-whole-dependency-closure-is-one-locked-artifact`.
Hand-driven 2026-09-20 in PR #1551.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).

**Manual checks:**
- `pixi lock` reports up-to-date; `pixi-version-check` clean (18 sites); `llms-full-check` clean; `pyforge-station-tests` green on the lock.

## Review Triage Log

### 2026-09-20 — hand-driven pass
  - `[high]` `[patch]` `eval-quality` pinned only in `local-recipes` + `pyforge-guild`; `suite.py:714` fell back to the primary checkout's env. Pinned in `pyforge-steward` (the container env inherits it).
  - `[high]` `[patch]` mason `python-build >=1.5.0,<1.6` vs `>=1.6.0` floors — union unsolvable. Floors; the one-minor-window convention amended by ruling (mason memlog; sync tests rewritten).
  - `[medium]` `[patch]` warden `py-rattler >=0.26.0` blocked conda's rattler-solver variant; the bump was a catalog sync. Floor 0.25.0; warden's own env still resolves 0.26.0; 2122 passed.
  - `[medium]` `[patch]` `docsite-check.yml` pinned pixi outside the registry. Registered (18 sites).
  - `[low]` `[defer]` pixi 0.81.0 — blocked on the conda-forge feedstock; command recorded on the Dream.

## Auto Run Result

**Status:** done
**Summary:** the union env is declared and locked (648 packages on linux-64); the steward pin lands; two cross-feature inconsistencies fixed at their owners; one unregistered pixi pin site registered.
**Verification:** steward 1578 passed in a station-envs-only worktree; warden 2122; mason 1589 + 12; `pixi-version-check` clean over 18 sites; `llms-full-check` clean; `pyforge-station-tests` — see the PR body.
**Files changed:** see Binding.
**Residual risks:** the union env is unexercised at runtime by design; install it deliberately when a cross-station integration needs the full closure.
**Follow-up review recommendation:** false
