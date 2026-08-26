---
title: First portal slice — start/get one audit
type: feature
created: '2026-08-25'
status: done
updated: '2026-08-26'
baseline_revision: c3f75232a15bb3c28730c546e8f955cda59054df
review_loop_iteration: 0
followup_review_recommended: true
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/change-history/sprint-change-proposal-2026-08-25-station-skill-portal.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-1-skf-domain-skills-from-station-packages.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-2-personas-act-only-through-grammar-and-mcp.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Warden portal still only local ORM lists; start/get must go through host MCP.

**Approach:** HTMX start one audit and retrieve after disconnect via PortalClient only.

## Acceptance Criteria

- Given an authenticated warden-role session, when the operator starts an audit from HTMX, then start/get go through PortalClient only.
- Given src/platform/, when scanned, then no raw HTTP, no pyforge.* import, no chrome copy.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-warden/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-warden` only — never `scripts/bmad-switch`. Ledger key `10-2-first-portal-slice-audit-start-get`.

**Block If:** A change would replace `conda-forge-expert`, add `pyforge.*` under `src/platform/`, or start the paired Wave story this spec does not own.

**Never:** Second PR-gate verdict. Raw HTTP. Chrome copy.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Start audit | Warden-role HTMX POST | PortalClient.start; opaque handle; MCP start_audit equivalent | 403 without warden role |
| Get after disconnect | Same handle + new assertion | PortalClient.get; same run; no recompute | Handle without matching sub refused |
| Forbidden transport | Views / platform | No urllib/requests/httpx; no `import pyforge` under src/platform/ | Test fails |

</intent-contract>

## Code Map

- `src/shared/packages/django-pyforge/src/django_pyforge/assertion/client.py` — PortalClient.emit only today; add in-process `start`/`get` (emit + supervisor). Do not open HTTP.
- `src/shared/packages/django-pyforge/src/django_pyforge/supervisor.py` — `publish_start` / `get_run` / `register_runner` (reuse; do not add a second ledger).
- `src/shared/packages/django-pyforge/src/django_pyforge/mcp_start_get.py` — Atlas `start_run_pipeline`/`get_run` pattern; do not reuse tool names. Warden owns `start_audit`/`get_audit`.
- `src/shared/packages/django-atlas/src/django_atlas_portal/mcp_asgi.py` — reuse shape: attach tools + register_runner + `asgi_for_server`.
- `src/shared/packages/django-warden/src/django_warden_fabric/apps.py` — `mcp_asgi_app` currently `asgi_for_station` (identity `station_face` only). Point at warden MCP ASGI.
- `src/shared/packages/django-warden/src/django_warden_fabric/views.py` — `chrome_home` + upload/job ORM faces stay. New HTMX start/get call PortalClient only; `@require_station_role("warden")`.
- `src/shared/packages/django-warden/src/django_warden_fabric/portal_urls.py` — mount start/get next to `chrome_home`; keep `urls.py` job routes.
- `src/shared/packages/django-warden/src/django_warden_fabric/templates/warden_fabric/chrome.html` — content-block HTMX only; still extends `django_pyforge/base.html`. No `base.html`/`switcher.html`/`theme.css` copy (chrome test).
- `src/shared/packages/django-pyforge/src/django_pyforge/roles.py` — `claims_from_request` / `roles_from_request` for emit `sub` + roles.
- `src/platform/tests/test_django_pyforge_chrome.py` — chrome-div identity; do not break.
- `src/platform/tests/test_start_get_survives_disconnect.py` — disconnect/get contract to mirror for warden.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/django-pyforge/src/django_pyforge/assertion/client.py` -- add PortalClient.start/get (emit then supervisor; no HTTP) -- portal path is PortalClient only
- `src/shared/packages/django-warden/src/django_warden_fabric/mcp_asgi.py` -- host MCP `start_audit`/`get_audit` + `run_audit` runner (no second verdict) -- agents use POST /stations/warden/mcp
- `src/shared/packages/django-warden/src/django_warden_fabric/apps.py` -- mcp_asgi_app uses warden MCP ASGI -- identity face is not enough
- `src/shared/packages/django-warden/src/django_warden_fabric/views.py` + `portal_urls.py` + `templates/warden_fabric/chrome.html` -- HTMX start/get; keep lists/upload -- operator slice
- `src/shared/packages/pyforge-warden/tests/meta/test_portal_audit_start_get.py` -- AST: PortalClient-only, no raw HTTP, no platform pyforge.*, no chrome copy, no second verdict -- station AC oracle
- `src/platform/tests/test_warden_portal_audit_start_get.py` -- Django: start then get after disconnect; 403 without role; no pyforge import -- behavioral AC

**Acceptance Criteria:**
- Given an authenticated warden-role session, when the operator starts an audit from HTMX, then start/get go through PortalClient only.
- Given src/platform/, when scanned, then no raw HTTP, no pyforge.* import, no chrome copy.

## Spec Change Log

- 2026-08-25: drafted from epics.md for fleet drain preflight
- 2026-08-26: planned — PortalClient.start/get, warden MCP start_audit/get_audit, HTMX on chrome content block

## Review Triage Log

### 2026-08-26 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 0, medium 4, low 2)
- defer: 0
- reject: 14
- addressed_findings:
  - `[medium]` `[patch]` pyforge scan missed untracked `src/platform` files — now includes `git ls-files --others` plus this story's test path
  - `[medium]` `[patch]` chrome home did not assert the HTMX start form — added `test_chrome_home_exposes_htmx_start_form`
  - `[medium]` `[patch]` unknown-handle GET had no oracle — added `test_get_unknown_handle_is_not_found`
  - `[medium]` `[patch]` host MCP `start_audit` had no `tools/call` — added `test_mcp_start_audit_returns_handle`
  - `[low]` `[patch]` whitespace-only `target` now strips to `.`
  - `[low]` `[patch]` `run_audit` now treats a non-dict payload as `{}`

## Design Notes

PortalClient.start/get emit an RS256 assertion then call supervisor (same writer as MCP tools). Views never POST to `/stations/warden/mcp`. Existing `ComplianceJob` upload/status/report stay ORM. `run_audit` returns a payload dict only — not a Warden PR-gate verdict.

## Verification

**Commands:**
- `pixi run -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/meta/test_portal_audit_start_get.py -q` -- expected: pass
- `cd src/platform && DATABASE_URL=postgres://postgres:platform@localhost:5432/platform pixi run -e platform-ci-test python -m pytest tests/test_warden_portal_audit_start_get.py -q` -- expected: pass
- `git diff origin/main -- src/platform` -- expected: no `import pyforge` / `from pyforge`

## Auto Run Result

Status: done

Summary: `/stations/warden/` HTMX start/get go through `PortalClient.start`/`get` (emit + supervisor). Host MCP exposes `start_audit`/`get_audit`. Existing ComplianceJob lists/upload stay. No raw HTTP, no `pyforge.*` under `src/platform/`, no chrome copy, no second PR-gate verdict.

Files changed:
- `django_pyforge/assertion/client.py` — PortalClient.start/get
- `django_warden_fabric/mcp_asgi.py` — warden MCP start/get + run_audit
- `django_warden_fabric/apps.py` — serve warden MCP ASGI
- `django_warden_fabric/views.py` + `portal_urls.py` + templates — HTMX slice
- station + platform tests — AC oracles

Review findings: 6 patches applied (medium 4, low 2, score 14); 0 deferred; 14 rejected. Follow-up review recommended: true (no high; 3×4 + 1×2 = 14 ≥ 5).

Verification:
- `pixi run -e pyforge-warden pytest …/test_portal_audit_start_get.py -q` — 6 passed
- `platform-ci-test` `tests/test_warden_portal_audit_start_get.py` — 7 passed (plus related chrome/MCP smokes)
- no `import pyforge` / `from pyforge` in `src/platform` story files

Residual risks: `run_audit` is a supervised stub, not a live Warden engine scan. HTMX attributes work without a bundled htmx.js on chrome (plain POST still starts).
