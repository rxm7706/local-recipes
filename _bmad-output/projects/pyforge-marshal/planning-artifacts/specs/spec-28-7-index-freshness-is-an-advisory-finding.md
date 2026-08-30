---
title: 'Index freshness is an advisory finding (Story 28.7, Epic 28)'
type: 'feature'
created: '2026-08-30'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: easy
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/integration-layers.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** A stale codegraph/cocoindex index silently degrades Layers 2–3 mid-run: the
agent answers structure questions from yesterday's graph or recompiles context it didn't
need to. Nothing surfaces staleness at admission time.

**Approach:** `marshal check` (the existing detector front door routing to the detector
registry) gains advisory codegraph/cocoindex staleness findings, evaluated against the
loop-home worktree state.

## Acceptance Criteria

- Given a stale or missing index in a home whose `[context]` block declares the layer, when
  `marshal check` runs, then a named advisory finding reports which index and why.
- Given the finding, when verdicts compute, then the exit-code domain `{0, 1, 2, 3, 4, 130}`
  is unchanged and the finding alone never blocks a run.
- Given a home with the layer declared off, when checked, then no staleness finding is
  raised.
- Given the detector registry, when this lands, then the new findings are registered like
  every other detector output — no second engine.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-marshal/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`. Ledger
key `28-7-index-freshness-is-an-advisory-finding`.

**Block If:** A change would turn the finding into a run-blocking gate or fork a second
detector engine.

**Never:** A competing PR verdict. Rebuilding indexes from inside the check (report, don't
mutate).

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/check.py` (front door)
- `scripts/detectors.py` registry / `pyforge.doctor.sources` dispatcher (where the finding registers)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` (finding codes)

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated
(finding raised / not raised, exit-domain unchanged, read-only). Land this spec in
`planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 28.7 and spec-marshal-token-economy CAP-10. Depends on Story 28.3's
seeded kit (there must be an index to judge). Advisory doctrine: findings inform, the
existing gates decide.

## Spec Change Log

- 2026-08-30: drafted from epics.md Epic 28 for fleet-drain preflight (Dream/Spec chain: docs/dreams/marshal-token-economy.md → spec-marshal-token-economy)
