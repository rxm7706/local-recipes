---
title: 'A/B protocol and pin on foundry'
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

**Problem:** Foundry README still reads as a cutover replay target. A new
builder cannot start from a clean BMAD tree.

**Approach:** Land `ab-sync.md` protocol on B: greenfield README/AGENTS,
`docs/foundry/PIN.md`, short case-list stub. A stays control. No
`_bmad-output` copy.

## Boundaries & Constraints

**Always:**
- One starting contract: Dream + Frame + Spec five-fields.
- Compare behavior (`pass|A-only|B-only|diverge`).

**Never:**
- Never rsync planning trees or `src/shared/packages`.
- Never dispatch 44.4 / 44.5 / 44.6.

</intent-contract>

## Acceptance Criteria

1. python-foundry has `PIN.md` and a case-list stub.
2. README/AGENTS do not say replay/44.4 fold.
3. local-recipes does not receive B's slim chain as a copy.
4. Ledger key exists; this mint does not close the Story as `done`.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `52c9dbcd4e` (2026-09-13, "Merge pull request #1342 from rxm7706/steward-54-5-agents-pin"). Ledger row `54-5-a-b-protocol-and-pin-on-foundry: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `AGENTS.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `backlog` → `done` (ledger row `54-5-a-b-protocol-and-pin-on-foundry: done`).
- `## Auto Run Result` reconstructed from git (none survived).
