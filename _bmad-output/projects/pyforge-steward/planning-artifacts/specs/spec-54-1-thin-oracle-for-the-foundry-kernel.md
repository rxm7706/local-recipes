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
