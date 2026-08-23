---
title: steward setup/initrepo take the machine to green
type: feature
created: '2026-08-23'
status: in-progress
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: d1c30b5286
---

<intent-contract>

## Intent

**Problem:** After `init`/`shell-init` (17.1), no steward verbs take a fresh machine to validate-fast green — setup/initrepo still improvised (spec-developer-machine-bootstrap CAP-1, 17.2 scope).

**Approach:** Add `steward setup` (clone + pixi install + hooks) and `steward initrepo` (onboard a repo). Given passing `init`, flow ends at validate-fast passing. Prove in clean container; zero improvised steps. Deps: 17.1 done. Skip 12-7.

## Acceptance Criteria

- `steward setup` clones, pixi-installs, wires hooks.
- `steward initrepo` onboards a repo to green.
- Clean-container run: nothing → validate-fast passing, zero improvised steps.
- Does not duplicate provision/cluster bring-up or multi-repo workspaces (Epic 13).

## Boundaries & Constraints

**Never:** Cluster bring-up (12.4). Finalize steward ledger only. Do not touch marshal 20-10 (#698). Skip 12-7.

</intent-contract>

## Code Map

- Parent: `spec-developer-machine-bootstrap/SPEC.md` (CAP-1, 17.2 scope)
- `src/shared/packages/pyforge-steward/` CLI: `setup`, `initrepo`
- Container/integration proof for validate-fast path
- Tests: setup + initrepo flows, `--json` if applicable

## Verification

- validate-fast passes after documented bootstrap sequence
- Container or documented clean-env reproduction
