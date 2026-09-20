---
title: 'Recall withholds sources committed after compile'
type: 'feature'
created: '2026-09-13'
status: 'done'
---

<intent-contract>

## Intent

Persist `compiled_at` on the flat-file store. Recall treats a post-compile
source commit as stale without rebuilding the graph.

## Boundaries & Constraints

**Always:** selection-time git compare; commit/transcript exempt.

**Never:** Protocol change; recompile-on-recall; PG/plane schema this story.

</intent-contract>

## Spec Change Log

- **2026-09-13:** implemented — `compiled_at` on the flat-file store;
  recall-time `source_committed_after` at selection.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `ee5316e216` (2026-09-07, "feat(warden): Story 11.1 -- bmad-os-review-pr and findings-triage are warden-wielded advisory lenses"); also `d570630ed3` (2026-08-21, "marshal: mark Story 11.1 done, promote its spec"); also `d630deb2f4` (2026-08-21, "marshal: Story 11.1 - neutral contract and agent-adapter fan-out"). Ledger row `11-1-recall-withholds-sources-committed-after-compile: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `.claude/skills/bmad-agent-warden/SKILL.md`, `_bmad-output/projects/pyforge-warden/planning-artifacts/sprint-status-ledger.yaml`, `src/shared/packages/pyforge-warden/tests/unit/test_advisory_lenses.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `ready-for-dev` → `done` (ledger row `11-1-recall-withholds-sources-committed-after-compile: done`).
- `## Auto Run Result` reconstructed from git (none survived).
