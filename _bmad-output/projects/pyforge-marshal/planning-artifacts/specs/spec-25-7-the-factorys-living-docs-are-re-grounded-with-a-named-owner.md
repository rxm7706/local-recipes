---
title: The factory's living docs are re-grounded with a named owner
type: docs
created: '2026-08-24'
status: ready
updated: '2026-08-24'
context: []
warnings: []
baseline_revision: ea294fb639
---

<intent-contract>

## Intent

**Problem:** After BMAD 6.11 retired `bmad-document-project`, living factory docs (`architecture-bmad-infra.md`, 8× `project-context.md`) drifted with no reconciler; SYNC-RUNBOOK has no named owner/cadence for re-grounding (FR-611 CAP-7; spec-bmad-611-era-alignment open question).

**Approach:** Re-ground `architecture-bmad-infra.md` to describe 6.11 infra (render pipeline, TOML layers, current skill set). Refresh all 8 station `project-context.md` rulebooks via plain agents with bumped `source_pin`s. Update SYNC-RUNBOOK to name recurring owner + cadence. **Open-question decision (2026-08-24):** fold living-doc re-grounding into the SYNC-RUNBOOK cadence as a **marshal** duty (matches parent SPEC "Owner: marshal") — not a per-station relay. Deps: 25.6 done (#721). Completes Epic 25 → marshal DRAINED.

## Acceptance Criteria

- `architecture-bmad-infra.md` describes 6.11 infra accurately (render pipeline, TOML layers, current skills).
- All 8 `projects/<slug>/project-context.md` re-grounded with bumped `source_pin`s.
- SYNC-RUNBOOK names recurring owner (marshal) + cadence; open question closed with dated entry in parent SPEC / memlog.
- HOLD AGENTS.md managed block / project-context ledger (upstream reworking) — re-ground existing rulebooks only.

## Boundaries & Constraints

**Never:** Adopt stories.yaml / folder+id dispatch / v7-removal paths. Never wait on upstream successor. Finalize marshal ledger only — mark `epic-25: done`. **maintenance label** on PR.

</intent-contract>

## Code Map

- Parent: `spec-bmad-611-era-alignment/SPEC.md` (CAP-7)
- Surfaces: `architecture-bmad-infra.md`, `_bmad-output/projects/*/project-context.md` (×8), SYNC-RUNBOOK(s)

## Verification

- Docs review: 6.11 accuracy; source_pins bumped
- Open question resolved in SPEC frontmatter / dated memlog
