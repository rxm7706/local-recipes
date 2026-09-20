---
title: 'The compile keeps knowledge layers honest'
type: 'feature'
created: '2026-09-13'
status: 'done'
---

<intent-contract>

## Intent

Fix compile-time stale false positives (mtime vs git), bound retro/memlog/changelog walks, and add named contract surfaces (active Dreams, ready SPECs, fact ledgers).

## Boundaries & Constraints

**Always:** stale iff latest source commit author date > this compile's `compiled_at`. Retros only under `planning-artifacts/retros/`.

**Never:** `*retro*` filename glob; `archive/`; `implementation-artifacts/`; `tests/`; wholesale `docs/`.

</intent-contract>

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `6be39246da` (2026-08-15, "doctor: land Story 8.4 -- sprint ledger, dashboard, epics outcome, spec promotion, Epic 8 done"); also `b70a02bae1` (2026-08-15, "doctor: Story 8.4 -- the baseline re-stamps so a second --fix run is a no-op"); also `35d1b71215` (2026-08-08, "herald: Story 8.4 — Progress web tab (static progress.json snapshot)"). Ledger row `8-4-the-compile-keeps-knowledge-layers-honest: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-8-4-the-baseline-re-stamps-so-a-second-run-is-a-no-op.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml`, `docs/dashboard/data.js`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `ready-for-dev` → `done` (ledger row `8-4-the-compile-keeps-knowledge-layers-honest: done`).
- `## Auto Run Result` reconstructed from git (none survived).
