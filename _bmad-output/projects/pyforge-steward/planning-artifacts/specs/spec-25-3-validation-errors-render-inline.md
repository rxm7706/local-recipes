---
title: 'Validation errors render inline'
type: feature
created: '2026-08-25'
status: done
baseline_commit: a76381bf8f8
baseline_revision: a76381bf8f8
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-unifying-strategy-2026-08-24/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-unifying-strategy-2026-08-24/prd.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/resilience-invariants.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** FastAPI HTTP 422 JSON arrays (`loc: ["body", "version"]`) do not map onto Django form fields, so operators see a generic toast instead of the field that failed (FR-28, BS-7, canopy:AD-15).

**Approach:** `PydanticFormErrorBridge` in `django-pyforge` unpacks 422 `detail` arrays into Django `ValidationError` dicts and re-renders the originating HTMX form with inline field errors. Tests fail if the bridge is removed or stubbed.

## Boundaries & Constraints

**Always:** Bridge lives in `django-pyforge` (`django_pyforge.form_errors`). Chrome path `src/shared/packages/django-pyforge/`. Specs under `_bmad-output/projects/pyforge-steward/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-steward`. Parent AD-2: no `pyforge.*` under `src/platform/`. Originating surface is the chrome HTMX form (probe portal POST), not a toast-only path.

**Block If:** Implementation would add pydantic / django-htmx to pixi, put `pyforge.*` under `src/platform/`, or treat `django-lasuite` as form chrome.

**Never:** Start 25.4 or Epic 26. MinIO/S3. `scripts/bmad-switch`. `bmad-loop`. Other stations' ledgers. A second per-station 422 mapper.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Rejected HTMX submit | POST bound form; FastAPI-shaped 422 `detail` with `loc: ["body", "version"]` | HTTP 422; `#id_version` errorlist shows `msg` on the originating form | Field highlighted; not a toast-only dump |
| Bridge to ValidationError | Same JSON array | `ValidationError` dict keyed by `version` | `body`/`query` loc prefixes dropped |
| Opaque toast (mechanism absent) | Same 422 passed to `toast_http_422` | Generic blob; form field has no errorlist | Documents the toast trap; canopy:AD-15 |
| Bridge removed | AST of `form_errors.py` without `PydanticFormErrorBridge` unpacking `detail`/`loc` | Test fails | Canopy canopy:AD-15 |

</intent-contract>

## Code Map

- `src/shared/packages/django-pyforge/src/django_pyforge/form_errors.py` -- NEW: `PydanticFormErrorBridge`, `toast_http_422` (canopy:AD-15 trap)
- `src/shared/packages/django-pyforge/src/django_pyforge/forms.py` -- NEW: originating `VersionForm`
- `src/shared/packages/django-pyforge/src/django_pyforge/templates/django_pyforge/htmx_form.html` -- NEW: inline field errors + `hx-post`
- `src/shared/packages/django-pyforge/src/django_pyforge/static/django_pyforge/theme.css` -- `.errorlist` / invalid field highlight
- `src/shared/packages/django-pyforge/src/django_pyforge/probe_portal/views.py` -- POST originating surface applies the bridge
- `src/shared/packages/django-pyforge/src/django_pyforge/probe_portal/urls.py` -- form route
- `src/platform/tests/test_validation_errors_render_inline.py` -- NEW: matrix + canopy:AD-15; import `django_pyforge` only
- Never: `src/platform/**` importing `pyforge.*`; Epic 25.4 reconcile; pixi.toml; django-lasuite chrome

## Tasks & Acceptance

**Execution:**
- `django_pyforge/form_errors.py` -- unpack 422 arrays into `ValidationError` dicts
- probe form view + chrome fragment -- render errors on the originating surface
- `src/platform/tests/test_validation_errors_render_inline.py` -- ACs including canopy:AD-15 absence

**Acceptance Criteria:**
- Given a rejected submission, when the response renders, then errors appear inline on the originating surface.
- And `PydanticFormErrorBridge` lives in `django-pyforge`.
- And the test fails if the bridge is removed.

## Spec Change Log

## Review Triage Log

### 2026-08-25 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 0, low 1)
- defer: 0
- reject: 0
- addressed_findings:
  - `[low]` `[patch]` canopy:AD-15 AST now requires `apply` to call `add_error`, so a stubbed bridge still fails.

## Design Notes

FastAPI RequestValidationError JSON is `{ "detail": [ { "loc": ["body", "version"], "msg": "...", "type": "..." } ] }`. Django forms want `{ "version": ["..."] }`. Drop leading `body`/`query`/`path`; map the last string loc that matches a form field, else `__all__`. Do not add pydantic — parse the JSON shape only. `toast_http_422` is the naive dump (toast trap): same payload, no field errors.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

Summary: `PydanticFormErrorBridge` in django-pyforge unpacks FastAPI 422 `detail` arrays into Django `ValidationError` dicts. The chrome-probe HTMX form re-renders field errors inline on HTTP 422. `toast_http_422` is the canopy:AD-15 opaque trap. No pixi bump.

Files changed:
- `django_pyforge/form_errors.py` -- bridge + toast trap
- `django_pyforge/forms.py` -- originating `VersionForm`
- `django_pyforge/htmx_form.html` + probe `form.html` / `chrome_form` -- originating surface
- `theme.css` -- `.errorlist` / `input.error`
- `src/platform/tests/test_validation_errors_render_inline.py` -- matrix + canopy:AD-15
- this spec

Review findings: 1 low patch (AST `add_error`). Deferred 0. Rejected 0. Follow-up review: false (score 1).

Verification: `pixi run -e platform-ci-test pytest src/platform/tests/test_validation_errors_render_inline.py src/platform/tests/meta/test_no_pyforge_import.py -q` → 6 passed. Chrome suite still 12 passed.

Residual: probe POST always applies a canned 422 (fixture originating surface, not a live FastAPI hop).
