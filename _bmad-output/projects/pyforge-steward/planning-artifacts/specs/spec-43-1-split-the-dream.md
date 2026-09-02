---
title: "Split the Dream into living and archive"
type: "docs"
created: "2026-09-02"
status: "ready-for-dev"
updated: "2026-09-02"
baseline_commit: "58ee07a0"
severity: "HIGH"
context:
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/resilience-invariants.md"
  - "docs/dreams/pyforge-unifying-strategy.md"
  - "docs/dreams/README.md"
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** 2,092 lines; the authoritative content is a Grounding block that overrides the
diagrams beneath it; five "historical, do not build" sections still read as
instruction. The review prompt itself inherited the wrong topology. Red-team
**B-10**, directive **R-4**.

**Approach:** Move everything Grounding marks historical to
`docs/dreams/archive/pyforge-unifying-strategy-2026-08-23-topology.md`, keep a
living Dream of at most 400 lines whose diagrams are the ones to build, keep the
Realization log intact (in the living file), and add a `dreams-hygiene`
finding: a `specified`/`realized` Dream may not contain a section titled
"historical" longer than 20 lines.

## Acceptance Criteria

- Given the living Dream, when counted, then it is ≤ 400 lines and every mermaid in it is a build target.
- Given the archive file, when read, then it carries a header stating it is historical and points at the living file; inbound links from specs still resolve (no 404 in `dream-chain`).
- Given `dream-chain --dreams`, when run, then the new `historical-section-too-long` finding exists and fires on a fixture, not on the living Dream.
- Given `docs/dreams/README.md`, when read, then the table row still resolves and the status is unchanged (`specified`).

## Boundaries & Constraints

**Always:** Write under `_bmad-output/projects/pyforge-steward/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`.
Ledger key `43-1-split-the-dream`. Host never imports `pyforge.*`. Grounding rulings survive verbatim in the living file. Realization log stays.

**Block If:** Implementation would delete history or rewrite rulings while moving them.

**Never:** Two files both claiming to be the Dream.

</intent-contract>

## Tasks

- [ ] Archive split
- [ ] README + link sweep
- [ ] Detector finding + fixture
- [ ] Realization entry
- [ ] Ledger `43-1-split-the-dream` → `review` then `done` via `sprint-ledger-sync`.

## Verification

`pixi run -e pyforge-doctor python -m pyforge.doctor.sources dream-chain --dreams` and `dream-chain`.

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 43.1). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.
