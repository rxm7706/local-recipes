---
title: "Results render with derived progress"
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

**Problem:** Async compliance jobs need operator-visible progress that cannot lie
(no phase picking its own number), and report/SBOM retrieval that reuses the
engine/CLI outputs stored by 8.1.

**Approach:** Keep `phases.PHASES` + `advance()` as the sole phase clock; status
JSON exposes `phase`/`progress` derived from `phase_index`; report endpoint
returns stored report/SBOM JSON. Unit tests prove monotonic phase guard and
keys-not-blobs task signature.

## Boundaries & Constraints

**Always:**
- Progress = phase_index / len(PHASES); never a free-form percent from a phase.
- Reports come from engine output already persisted on the job — no second analyzer.

**Never:**
- Let a phase set its own progress number.
- Reimplement SBOM/vuln renderers in the web face.

## I/O & Edge-Case Matrix

| Scenario | Input | Expected | Error Handling |
|----------|-------|----------|----------------|
| Out-of-order advance | advance(scan) at 0 | RuntimeError phase guard | fail loud |
| Complete job | advance past last | RuntimeError already complete | fail loud |
| Report before success | status != succeeded | 409 | JSON error |

</intent-contract>

## Code Map

- `src/platform/compliance_face/phases.py`
- `src/platform/compliance_face/views.py` (status/report)
- `src/platform/tests/test_compliance_face_phases.py`

## Tasks

- [x] Phase guard + derived progress
- [x] Status/report endpoints
- [x] Unit tests without pytest-django
