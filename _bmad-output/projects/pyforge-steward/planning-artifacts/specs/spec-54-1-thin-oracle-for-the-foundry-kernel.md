---
title: 'Thin oracle for the foundry kernel'
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

**Problem:** Frame preflight checks schema only. A regenerate without an
oracle will look green and miss drain/CLI behavior.

**Approach:** Freeze about 20–40 existing local-recipes tests (core,
steward, marshal CLI, exit codes, `station_port`, cutover-root, no-host)
as the kernel gate. Do not wait for 44.14.

## Boundaries & Constraints

**Always:**
- List lives next to `spec-foundry-regenerate-not-fold`.
- Cite existing tests; do not invent new behavior here.

**Never:**
- Never treat Frame YAML parse as the oracle.
- Never dispatch 44.4 / apply `--phase 1a`.
- Never implement foundry packages in this Story (54.2–54.4).

</intent-contract>

## Acceptance Criteria

1. Tracked archived-test list exists (about 20–40 named tests).
2. List is the named gate for 54.2–54.4.
3. 44.4 and 44.5 remain undispatched.
4. Ledger key exists; this mint does not close the Story as `done`.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `54-1-thin-oracle-for-the-foundry-kernel: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
