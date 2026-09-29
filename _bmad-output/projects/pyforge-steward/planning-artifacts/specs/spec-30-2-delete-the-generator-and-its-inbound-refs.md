---
title: 'Story 30.2: Delete the generator and its inbound refs'
type: chore
created: '2026-08-25'
status: done
updated: '2026-08-25'
baseline_revision: f5f0bccf3b5dc0f9a4ebd1ebd142ab5f7d595540
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-30-1-remaining-console-surfaces-have-a-home.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/console-parity-inventory.md
warnings:
  - oversized
deferred: []
---

<intent-contract>

## Intent

**Problem:** After 30.1 named Canopy homes, the Guildhall generator, four pixi tasks, scheduled Pages regen, and committed `data.js` still exist. Two consoles would become permanent if the old path is only unlinked.

**Approach:** Migrate parsers first (sprint-ledger + fleet/chain audit), then delete the generator, four pixi tasks, scheduled trigger, and `data.js`. Rewrite inbound refs to `/console/` or surviving Kedro-Viz. Keep `steward deploy dashboard` as the Kedro-Viz reconcile push.

## Boundaries & Constraints

**Always:**
- Delete `docs/dashboard/generate.py`, `docs/dashboard/data.js`, the four pixi tasks `dashboard-gen` / `dashboard-watch` / `dashboard-check` / `dashboard-drift-check`, and the `schedule:` cron on `.github/workflows/dashboard.yml`.
- Kedro-Viz under `docs/dashboard/kedro-viz/` and `.github/workflows/kedro-viz-publish.yml` survive.
- Lane 1 homes from 30.1 under `src/platform/` stay. No `pyforge.*` imports under `src/platform/`.
- `spec-factory-console` stays `superseded` and records 30.2 deletion (Marshal Phase 5 already superseded the spec).
- Tests fail if `generate.py`, `data.js`, or any of the four pixi task tables return.
- Write under `_bmad-output/projects/pyforge-steward/` (physical path). `BMAD_ACTIVE_PROJECT=pyforge-steward`. Do not run `scripts/bmad-switch`.

**Block If:** A change would delete Kedro-Viz or its workflow, or would start Story 31.1.

**Never:** Delete 30.1 console homes. Leave operator docs/workflows pointing at deleted generator paths. Squash-merge.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Generator gone | Tree after merge | `generate.py` and `data.js` absent | Test fails if either file returns |
| Four tasks gone | `pixi.toml` | No `dashboard-gen/watch/check/dashboard-drift-check` task tables | Test fails if a table returns |
| Schedule gone | `dashboard.yml` | No `schedule:` cron; Pages still uploads `docs/dashboard` (Kedro-Viz) | No error |
| Kedro-Viz kept | Same tree | `docs/dashboard/kedro-viz/` and `kedro-viz-publish.yml` present | Test fails if either vanished |
| Parser migrate | `sprint-ledger-sync` / chain-layers | No import of `docs/dashboard/generate.py` | Fail if the retired path is loaded |
| Reintroduce | File or pixi task comes back | Doctor `dashboard-drift` FAIL | Finding, not crash |
| Host boundary | `src/platform/` | No `import pyforge` | Existing meta test stays green |

</intent-contract>

## Code Map

- `docs/dashboard/generate.py`, `data.js`, `check_render.js`, `scripts/dashboard_watch.py` — delete
- `docs/dashboard/kedro-viz/**`, `.github/workflows/kedro-viz-publish.yml` — keep
- `.github/workflows/dashboard.yml` — drop cron + `generate.py` step; keep Pages upload
- `pixi.toml` — drop four tasks; rewrite descriptions that name them
- `scripts/fleet_scan.py` — parsers extracted from generate.py (chain/fleet/sprint)
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py` — chain-layers uses fleet_scan; dashboard-drift/check-layout become reintroduction gates
- `scripts/promote_sprint_status.py` — stop loading generate.py
- `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy.py` — repo marker + no-op build (Kedro-Viz staged by atlas)
- `src/shared/packages/pyforge-atlas/tools/normalize_viz_build.py` — same marker change
- `src/platform/tests/test_console_parity_homes.py` — invert generator-kept; add reintroduction gate
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-factory-console/SPEC.md` — 30.2 completed
- Inbound refs: AGENTS/CLAUDE/Charter/presentations/specs/workflows/scripts/tests — rewrite, no 404s

## Tasks & Acceptance

**Execution:**
- Extract fleet/sprint parsers to `fleet_scan.py`; retarget promote + chain-layers + marshal loaders
- Invert doctor dashboard-drift / check-layout to reintroduction gates; add `retired-console-check` pixi task
- Delete generator files + four pixi tasks + schedule; keep Kedro-Viz + Pages upload
- Rewrite inbound refs; mark factory-console retirement complete
- Tests: gone / kept / reintroduction / no pyforge in src/platform

**Acceptance Criteria:**
- Given proven parity, when this story merges, then the generator, its four pixi tasks, scheduled workflow trigger, and committed data blob are gone
- Given inbound refs, when followed, then they do not 404 or point at the retired generator path
- Given Kedro-Viz, when this story merges, then the tree and its workflow survive
- Given `spec-factory-console`, when this story merges, then it remains superseded and records the deletion
- Given a reintroduced generator or four-task table, when tests/doctor run, then they fail

## Design Notes

`steward deploy dashboard` stays: kedro-viz-publish stages `docs/dashboard/kedro-viz/` then reconciles. Build no longer wraps `dashboard-gen`. Pages workflow remains the publisher of that tree (no daily regen). Fleet/chain audit is not a console; it moves with the parsers.

## Spec Change Log

- 2026-08-25 — drafted from epics.md Story 30.2; implementation on `steward/30-2-delete-the-generator-and-its-inbound-refs`.

## Review Triage Log

- Self-review: generator/data.js/four pixi tasks/schedule gone; Kedro-Viz + kedro-viz-publish.yml kept; parsers in `scripts/fleet_scan.py`; `retired-console-check` is the reintroduction gate; `spec-factory-console` remains superseded.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `a3784c33ed` (2026-08-25, "Merge pull request #804 from rxm7706/steward/30-2-ledger-finalize"); also `c3ac2f3ec2` (2026-08-25, "Merge pull request #803 from rxm7706/steward/30-2-delete-the-generator-and-its-inbound-ref"). Ledger row `30-2-delete-the-generator-and-its-inbound-refs: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `.cursor/pyforge-fleet-drain/queues.yaml`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `ready` → `done` (ledger row `30-2-delete-the-generator-and-its-inbound-refs: done`).
- `## Auto Run Result` reconstructed from git (none survived).
