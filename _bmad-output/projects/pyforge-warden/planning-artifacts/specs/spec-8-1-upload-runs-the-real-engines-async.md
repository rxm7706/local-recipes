---
title: "Upload runs the real engines, async"
type: 'feature'
created: '2026-08-22'
status: 'done'
baseline_revision: ''
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Warden engines are CLI-only; operators need an upload face that runs the
EXISTING engines asynchronously without putting manifest blobs on the Celery broker.

**Approach:** Add Django app `compliance_face` on the platform-app host (decision
2026-08-22): multipart upload stores bytes under a storage_key; Celery task receives
only job_id; task calls `pyforge.warden.cli.main(["scan", ...])`.

## Boundaries & Constraints

**Always:**
- Keys-not-blobs: Celery args are job_id strings only.
- Safe-loader-only storage (no yaml.load/exec on upload).
- Call existing warden engines — never reimplement analyzers.

**Never:**
- Standalone service host (platform-app chosen).
- Put manifest bytes in Redis/broker/DB columns.

## I/O & Edge-Case Matrix

| Scenario | Input | Expected | Error Handling |
|----------|-------|----------|----------------|
| Upload supported file | requirements.txt | 202 + job_id | N/A |
| Unsupported format | .exe | 400 | JSON error |
| Missing blob at key | deleted file | job FAILED | error field set |

</intent-contract>

## Code Map

- `src/platform/compliance_face/` — app
- `src/platform/config/settings/base.py` — LOCAL_APPS
- `src/platform/config/urls.py` — `/compliance/`

## Tasks

- [x] Host decision: platform-app
- [x] Models + migration (storage_key)
- [x] Upload + Celery task
- [x] Wire urls/settings

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `5017a51957` (2026-08-22, "Merge pull request #636 from rxm7706/warden/8-1-upload-runs-real-engines-async"). Ledger row `8-1-upload-runs-the-real-engines-async: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `src/platform/compliance_face/__init__.py`, `src/platform/compliance_face/apps.py`, `src/platform/compliance_face/migrations/0001_initial.py`, `src/platform/compliance_face/migrations/__init__.py`, `src/platform/compliance_face/models.py`, `src/platform/compliance_face/phases.py`, `src/platform/compliance_face/tasks.py`, `src/platform/compliance_face/urls.py`, `src/platform/compliance_face/views.py`, `src/platform/config/settings/base.py`, `src/platform/config/urls.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
