---
spec: reusable-cicd-workflows
status: extension-point
owner-dream: docs/dreams/reusable-cicd-workflows.md
trigger: "conda-forge-tracker (the named candidate second consumer — active, zero CI today) or any second repo adopts CI wanting these workflows"
companions: []
sources:
  - ../../../../../../docs/dreams/reusable-cicd-workflows.md
---

# SPEC — A centrally-maintained CI/CD workflow family (PARKED)

Parked by the Dream's own constraint — it is a parity capture whose premise
is not yet real here. The one transferable idea (parallelizing detector CI steps) found no current bottleneck. Zero stories minted; when the trigger fires, this
spec gets a real pass and decomposition. Parking recorded 2026-08-22 so
INV-1 holds without speculative work.

**Trigger:** a SECOND consuming repo needs this repo's workflows (today: one mono-repo on plain Actions)

## Extension contract (added 2026-08-22)

This repo's workflows become consumable, not centrally familied: a thin
`on: workflow_call` wrapper (mason Story 9.1) with documented inputs/secrets
lets ANY consumer — conda-forge-tracker, an enterprise or air-gapped mirror
that vendors the file — plug in self-service via
`uses: rxm7706/local-recipes/.github/workflows/<name>.yml@<ref>` (or a
vendored copy where egress is blocked). The 63-family shape stays
permanently out of scope; the socket is the deliverable.
