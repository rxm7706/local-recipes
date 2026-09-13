---
title: 'Tracked capability ledger'
type: 'docs'
created: '2026-09-13'
status: 'backlog'
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
