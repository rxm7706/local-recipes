---
title: First portal slice — one inventory/run row
type: feature
created: '2026-08-25'
updated: '2026-08-26'
status: done
baseline_revision: c3f75232a15bb3c28730c546e8f955cda59054df
review_loop_iteration: 0
followup_review_recommended: true
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/change-history/sprint-change-proposal-2026-08-25-station-skill-portal.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-1-skf-domain-skills-from-station-packages.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-2-personas-act-only-through-grammar-and-mcp.md
warnings: []
deferred:
  - summary: >-
      Host chrome does not load an HTMX runtime, so hx-* poll attributes are markup-only.
    evidence: |-
      django_pyforge/base.html is read-only for this story and has no htmx script.
      First paint is server-rendered and satisfies the GET AC without JS.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/templates/django_pyforge/base.html
    severity: low
---

<intent-contract>

## Intent

**Problem:** Empty /stations/atlas/ shell does no real job.

**Approach:** HTMX on /stations/atlas/ shows one factory inventory or run-state row via django-pyforge PortalClient only. Not DW-H3. Not Vizro.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-atlas/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-atlas` only — never `scripts/bmad-switch`. Ledger key `19-2-first-portal-slice-inventory-row`. GET `/stations/atlas/` for an authenticated atlas-role session must render exactly one inventory or run-state row. The view must call `django_pyforge.assertion.client.PortalClient` (emit/sign) before reading host supervisor `run_state`; no raw HTTP. Keep existing django-pyforge chrome (`extends "django_pyforge/base.html"`). Tests that fail if ACs are violated live under `src/shared/packages/pyforge-atlas/tests/` and/or `src/shared/packages/django-atlas/` plus platform pytest that already hosts Django.

**Block If:** A change would replace `conda-forge-expert`, add `pyforge.*` under `src/platform/`, or start the paired Wave story this spec does not own (19.1 SKF/persona remint).

**Never:** DW-H3 REST. Vizro on the host. Raw HTTP (`httpx`/`requests`/`urllib.request`). `pyforge.*` under `src/platform/`. Chrome copy (`base.html` / `switcher.html` / `theme.css` in django-atlas). New public port. `pixi.toml` unless a test cannot run without it. Editing `CLAUDE.md` / `AGENTS.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Authenticated atlas GET | Session/token has role `atlas`; zero or more `run_state` rows | 200; HTMX markup; exactly one `#atlas-inventory-row` (latest atlas run if present, else one idle inventory row) | No error expected |
| Wrong role | Role `warden` only | 403; no inventory row required | Forbidden from `require_station_role` |
| PortalClient required | Atlas portal Python tree | Uses `PortalClient`; no httpx/requests/urllib.request | Test fails on offenders |

</intent-contract>

## Code Map

- `src/shared/packages/django-atlas/src/django_atlas_portal/views.py` — `chrome_home` (L9–12) currently `render(..., "atlas_portal/home.html")` only. Emit via `PortalClient`, then load one atlas `RunState` in-process.
- `src/shared/packages/django-atlas/src/django_atlas_portal/templates/atlas_portal/home.html` — extends chrome; body is `<p id="atlas-body">atlas portal</p>`. Add one HTMX row (`hx-*` on the row/partial). Do not copy chrome files.
- `src/shared/packages/django-atlas/src/django_atlas_portal/urls.py` — `path("", views.chrome_home, name="atlas-home")`. Optional fragment path only if first paint still includes the row.
- `src/shared/packages/django-atlas/src/django_atlas_portal/board.py` — existing JSON board; do not turn this story into a dashboard. Leave unless a one-line reuse is required.
- `src/shared/packages/django-pyforge/src/django_pyforge/assertion/client.py` — `PortalClient.emit` only (signer, not HTTP). Read-only: do not add HTTP here (Wave B mutex).
- `src/shared/packages/django-pyforge/src/django_pyforge/supervisor.py` — `get_run` / `RunState` / `_row_payload`. In-process read after emit. Do not write runs from the portal GET.
- `src/shared/packages/django-pyforge/src/django_pyforge/models.py` — `RunState` (`station`, `status`, timestamps).
- `src/shared/packages/django-pyforge/src/django_pyforge/access.py` — keep `@require_station_role("atlas")`.
- `src/shared/packages/django-pyforge/src/django_pyforge/templates/django_pyforge/base.html` — sole chrome. Read-only.
- `src/platform/tests/test_station_portal_shells.py` — existing GET `/stations/atlas/` 200 + 403. New AC tests must not break this.
- `src/shared/packages/pyforge-atlas/tests/meta/test_skf_skill_and_persona.py` — 19.1; do not remint Wave A.
- Station tests to add: `src/shared/packages/pyforge-atlas/tests/meta/test_portal_inventory_row.py` (AST: PortalClient used; no raw HTTP; no chrome copy) and `src/platform/tests/test_atlas_portal_inventory_row.py` (Django GET renders one row).

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/django-atlas/src/django_atlas_portal/views.py` — emit via PortalClient, then pick one in-process run-state or idle inventory row; pass it to the template.
- `src/shared/packages/django-atlas/src/django_atlas_portal/templates/atlas_portal/home.html` — render that single HTMX row under existing chrome.
- `src/platform/tests/test_atlas_portal_inventory_row.py` — authenticated GET shows one `#atlas-inventory-row`; wrong role 403.
- `src/shared/packages/pyforge-atlas/tests/meta/test_portal_inventory_row.py` — PortalClient import present; no raw HTTP; no chrome-copy filenames in django-atlas.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-19-2-first-portal-slice-inventory-row.md` — keep this tracked spec current.

**Acceptance Criteria:**
- Given an authenticated atlas-role session, when the operator opens /stations/atlas/, then one row renders via PortalClient only.
- Given src/platform/ and django-atlas, when reviewed, then no raw HTTP, no pyforge.* under src/platform/, no chrome copy.
- Given DW-H3 / La Suite REST, when this story lands, then it is not implemented here.

## Spec Change Log

- 2026-08-25: drafted from epics.md for fleet drain preflight
- 2026-08-26: planned for ready-for-dev — Code Map + I/O matrix; run-state via supervisor after PortalClient.emit (not HTTP)
- 2026-08-26: implemented chrome_home emit-then-read + one `#atlas-inventory-row`; AC tests landed

## Review Triage Log

### 2026-08-26 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 0, medium 2, low 4)
- defer: 1: (high 0, medium 0, low 1)
- reject: 14
- addressed_findings:
  - `[medium]` `[patch]` Dropped private `supervisor._row_payload`; map public RunState fields in the portal view
  - `[medium]` `[patch]` Order latest run with `started_at` DESC NULLS LAST
  - `[low]` `[patch]` `hx-get` uses `{% url 'atlas-home' %}`
  - `[low]` `[patch]` Meta test requires `PortalClient().emit(`
  - `[low]` `[patch]` AST raw-HTTP scan flags `import urllib`
  - `[low]` `[patch]` Idle GET asserts `data-station="atlas"`

## Design Notes

PortalClient is a signer (steward 18.3): emit the assertion, then read `run_state` in-process. Latest `station="atlas"` row if any; otherwise one idle inventory row so the surface is never empty. HTMX attributes mark the row; first paint is server-rendered so GET alone satisfies the AC without a second chrome or Vizro.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

Summary: GET `/stations/atlas/` emits via PortalClient then renders one HTMX `#atlas-inventory-row` from in-process atlas `run_state` (idle if none). No raw HTTP, no chrome copy, no Wave A remint, no DW-H3/Vizro.

Files:
- `src/shared/packages/django-atlas/src/django_atlas_portal/views.py` — emit then latest/idle row
- `src/shared/packages/django-atlas/src/django_atlas_portal/templates/atlas_portal/home.html` — one HTMX row
- `src/platform/tests/test_atlas_portal_inventory_row.py` — GET 200/403 ACs
- `src/platform/tests/test_station_portal_shells.py` — claims + django_db so atlas GET still 200
- `src/shared/packages/pyforge-atlas/tests/meta/test_portal_inventory_row.py` — PortalClient/HTTP/chrome AST
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-19-2-first-portal-slice-inventory-row.md` — tracked spec

Review: 6 patches applied (2 medium, 4 low; follow-up score 10); 1 deferred (chrome HTMX runtime); 14 rejected (PortalClient-as-HTTP-client, get_run-without-handle, extra matrix rows, emit/DB swallow).

Follow-up review recommended: true (patched medium 2, low 4; score 10).

Verification:
- `pixi run --frozen -e pyforge-atlas pytest …/test_portal_inventory_row.py -q` — 3 passed
- `pixi run --frozen -e platform-ci-test pytest …inventory_row.py …station_portal_shells.py -q` — 11 passed (`DATABASE_URL` to local Postgres)
- `git diff origin/main -- src/platform` — no `import pyforge` / `from pyforge`

Residual: 60s HTMX refresh is markup-only until chrome loads HTMX; emit token is unused after sign (steward 18.3 signer).
