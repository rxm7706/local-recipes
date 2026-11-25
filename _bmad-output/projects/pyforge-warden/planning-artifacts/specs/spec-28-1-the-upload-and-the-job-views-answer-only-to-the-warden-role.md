---
title: '28.1: The upload and the job views answer only to the warden role'
type: 'fix'
created: '2026-11-24'
status: 'in-review'
story: 28-1-the-upload-and-the-job-views-answer-only-to-the-warden-role
spec: spec-pyforge-warden
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # an access check is a gate; a gated gate is a silent green (roster list)
surface:
  - 'src/shared/packages/django-warden/src/django_warden_fabric/views.py'
  - 'src/platform/tests/test_warden_portal_upload_gate.py'
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - docs/dreams/pyforge-warden.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Three views of the compliance web face carry no role check: `upload_manifest`, `job_status` and `job_report`. Every other view in the module carries `require_station_role("warden")`, and no middleware requires a login in front of `/stations/`. The upload is also `csrf_exempt` and takes a file of any size, so a caller with no token can store a file, create a job row and enqueue a scan, and anyone holding a job id can read its report.

**Approach:** Put `require_station_role("warden")` on the three views, drop the upload's CSRF exemption so it is checked like the module's other POST views, and refuse a file over `COMPLIANCE_FACE_MAX_UPLOAD_BYTES` (default 20 MiB) with 413: a body over the limit by more than the multipart allowance before it is read, any other on the file's counted size, and in both cases before anything reaches the blob root or a job row exists.

Ledger key: `28-1-the-upload-and-the-job-views-answer-only-to-the-warden-role`.

### Living CAP citations

- spec-pyforge-warden CAP-16 (realized, no text change); canopy:AD-15; no warden FR.

## Boundaries & Constraints

**Always:**
- Refuse before anything reaches the blob root, a job row exists or a scan is enqueued.
- Keep the tests free of any `pyforge` import.

**Never:**
- Never put the role check behind a flag.
- Never change a model, a migration or a task in this story.

## Acceptance Criteria

**Given** `upload_manifest`, `job_status` and `job_report` carry no role check, the upload is `csrf_exempt`, and no size is checked
**When** the three views carry the role check, the upload drops its CSRF exemption, and a file over the configured size is refused
**Then** a caller with no token or another station's role gets 403 from all three and nothing is stored or enqueued, a warden-role upload returns 202 with its job id, and an oversized file gets 413 and never reaches the blob root (a body over the limit by more than the multipart allowance is refused before it is read)
**And** a cookie-authenticated POST with no CSRF token is refused when checks are enforced

- **AC1 — The gate tests pass in the platform suite.** Expected: exit 0.

  ```bash
  pixi run -e pyforge-guild platform-ci-local -- --test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-warden CAP-16 (realized, no text change); canopy:AD-15; no warden FR.
- Dream: `docs/dreams/pyforge-warden.md`, the 2026-11-24 entry (the upload answers only to the warden role); operator rulings of 2026-11-24.
- Epic: Epic 28, minted with this story.
- Ledger key: `28-1-the-upload-and-the-job-views-answer-only-to-the-warden-role`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."28"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-24: minted from the station Dream's 2026-11-24 entry and the operator's rulings of the same date; implemented the same day and left `in-review`: implementation and review do not share a session.
