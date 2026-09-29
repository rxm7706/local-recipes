---
title: 'Portal and Marshal inherit default recall'
type: 'feature'
created: '2026-09-13'
status: 'done'
---

<intent-contract>

## Intent

Lock portal and Marshal recall argv to inherit CAP-4. Add a Cursor rule
that points at the AGENTS session path.

## Boundaries & Constraints

**Always:** no `--kind` on those argv builders.

**Never:** portal redesign; `pyforge.scribe` import from django-scribe.

</intent-contract>

## Spec Change Log

- **2026-09-13:** implemented — argv locks + `.cursor/rules/scribe-recall.mdc`.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `2bf100082f` (2026-09-10, "Add regression tests for deploy promotion clean-only gate (Story 12.1)."); also `e329c9424d` (2026-08-21, "steward: Story 12.1 done (PR #605) — vanilla chart + OCP overlay landed"); also `473281c344` (2026-08-21, "steward: Story 12.1 spec finalize - status done, triage log, auto run result"). Ledger row `12-1-portal-and-marshal-inherit-default-recall: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-12-1-regression-test-the-promotion-verifier-s-clean-only-refusal-cannot-be-removed-silently.md`, `_bmad-output/projects/pyforge-warden/planning-artifacts/sprint-status-ledger.yaml`, `src/platform/tests/test_deploy_verify_promotion_clean_only.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `ready-for-dev` → `done` (ledger row `12-1-portal-and-marshal-inherit-default-recall: done`).
- `## Auto Run Result` reconstructed from git (none survived).
