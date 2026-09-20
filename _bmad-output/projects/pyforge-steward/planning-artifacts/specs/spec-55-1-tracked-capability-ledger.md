---
title: 'Tracked capability ledger'
type: 'docs'
created: '2026-09-13'
status: 'done'
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** PIN plus policy does not classify capabilities. A new
`CAP-N` can sit forever with no rebuild / retire / A-only row.

**Approach:** Track `docs/foundry/capability-ledger.yaml` with modes
from `modes.md`. Inventory from CAP extracts, not SPEC novels.

## Boundaries & Constraints

**Always:**
- Modes: `rebuild` | `retire` | `A-only` (expiry) | `B-only`.
- Classify from heading extract (`extract.md`).

**Never:**
- Never add a `move` mode.
- Never flip 44.1.

</intent-contract>

## Acceptance Criteria

1. Tracked `docs/foundry/capability-ledger.yaml` exists.
2. Every extracted live `CAP-N` has a mode row.
3. `A-only` rows have an expiry.
4. 44.1 remains `blocked`.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `25c3f7be20` (2026-09-13, "Merge pull request #1346 from rxm7706/steward-55-1-ledger"). Ledger row `55-1-tracked-capability-ledger: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-55-1-tracked-capability-ledger.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `docs/foundry/capability-ledger.yaml`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
