---
title: "One interpreter story"
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
  - "pixi.toml"
  - "docs/dreams/pyforge-unifying-strategy.md"
  - "src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py"
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The platform image runs Python 3.12 (langflow/dbgpt); Atlas and Doctor
declare `>=3.14`; the `mcp-host` sidecar exists because of that gap. The
Dream's "3.12/3.13/3.14 100 % SUCCESS, byte-for-byte" table is not what the
repo does and cannot be true across ABIs. Red-team **S-5**, **D-1**, directive
**R-16**.

**Approach:** Decide and write it down: either (a) raise langflow/dbgpt to 3.14 (feedstock
work, owned by Mason), (b) lower Atlas/Doctor floors to 3.12, or (c) formalize
the two-interpreter topology (host 3.12 + `mcp-host` 3.14) as the design with
the sidecar sized and policed. This story records the decision as a Dream
Grounding bullet + AD, replaces the multi-Python table with the measured
per-env solve matrix, and opens the follow-on story for the chosen option.

## Acceptance Criteria

- Given the Dream, when read, then the "Multi-Python Resolution" table is gone and a measured per-environment matrix (env, python, record count, platforms) generated from `pixi.lock` stands in its place.
- Given the architecture spine, when read, then one AD names the interpreter topology and its consequence for MCP faces.
- Given the decision, when recorded, then a follow-on story exists in the owning project (mason for (a), atlas+doctor for (b), steward for (c)).

## Boundaries & Constraints

**Always:** Write under `_bmad-output/projects/pyforge-steward/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`.
Ledger key `43-5-one-interpreter-story`. Host never imports `pyforge.*`. No silent floor raise (Grounding "Python floor"). Fleet policy before code.

**Block If:** Implementation would change any package's python floor in this story.

**Never:** A "byte-for-byte" claim across Python minors.

</intent-contract>

## Tasks

- [ ] Matrix generator (script) + Dream table
- [ ] AD in the spine
- [ ] Decision + follow-on story
- [ ] Ledger `43-5-one-interpreter-story` → `review` then `done` via `sprint-ledger-sync`.

## Verification

`bmad-drift` + `dreams-hygiene` clean; generator has a test.

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 43.5). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.
