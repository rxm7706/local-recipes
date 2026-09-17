---
title: First portal slice — deck status for one slug
type: feature
created: '2026-08-25'
status: done
updated: '2026-08-26'
baseline_revision: c3f75232a15bb3c28730c546e8f955cda59054df
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/change-history/sprint-change-proposal-2026-08-25-station-skill-portal.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-1-skf-domain-skills-from-station-packages.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-2-personas-act-only-through-grammar-and-mcp.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Empty /stations/herald/ does not show deck status.

**Approach:** Show herald deck status for one slug via PortalClient only.

## Acceptance Criteria

- Given an authenticated herald-role session, when the operator opens /stations/herald/, then one slug's status renders via PortalClient only.
- Given src/platform/, when scanned, then no raw HTTP, no pyforge.* import, no chrome copy.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-herald/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-herald` only — never `scripts/bmad-switch`. Ledger key `17-2-first-portal-slice-deck-status-for-one-slug`.

**Block If:** A change would replace `conda-forge-expert`, add `pyforge.*` under `src/platform/`, or start the paired Wave story this spec does not own.

**Never:** Lane 1 CMS takeover. Raw HTTP. Chrome copy.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | Herald-role session GET `/stations/herald/` | Page includes `#herald-deck-status` and slug `pyforge-herald`; view called `PortalClient.invoke` with argv `deck status pyforge-herald` | No error expected |
| FORBIDDEN | Session without herald role GET `/stations/herald/` | HTTP 403; no deck-status body required | Forbidden |
| CLIENT_ONLY | django-herald Python tree | No `pyforge.*` import; no raw HTTP client | Test fails on offenders |

</intent-contract>

## Code Map

- `src/shared/packages/django-herald/src/django_herald_portal/views.py` -- `chrome_home` emits via `PortalClient.invoke`; slug `pyforge-herald`
- `src/shared/packages/django-herald/src/django_herald_portal/templates/herald_portal/home.html` -- extends `django_pyforge/base.html`; `#herald-deck-status`
- `src/shared/packages/django-pyforge/src/django_pyforge/assertion/client.py` -- `PortalClient.emit` + `invoke` (sign, verify, in-process projection; no HTTP)
- `src/shared/packages/django-herald/src/django_herald_portal/urls.py` -- `""` → `chrome_home` at `/stations/herald/`
- Read-only: `src/platform/tests/meta/test_no_pyforge_import.py`; `src/platform/tests/test_station_portal_shells.py`

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/django-pyforge/src/django_pyforge/assertion/client.py` -- add in-process `invoke` -- portals stay client-only
- `src/shared/packages/django-herald/src/django_herald_portal/views.py` -- render one slug through `PortalClient` -- FR-10
- `src/shared/packages/django-herald/src/django_herald_portal/templates/herald_portal/home.html` -- status projection, no chrome copy
- `src/shared/packages/pyforge-herald/tests/meta/test_portal_deck_status.py` -- station AST/chrome gates
- `src/platform/tests/test_herald_portal_deck_status.py` -- GET + invoke argv + 403

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

One slug is `pyforge-herald`. `invoke` signs and verifies the RS256 assertion in-process, then projects `deck status <slug>` — it does not open HTTP and does not import `pyforge.herald` from the portal package. Bind to epics.md Story 17.2 and the 2026-08-25 station-skill-portal SCP.

## Spec Change Log

- 2026-08-25: drafted from epics.md for fleet drain preflight
- 2026-08-26: planned Code Map, I/O matrix, and verification commands for 17.2

## Review Triage Log

### 2026-08-26 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 0, low 1)
- defer: 0
- reject: 6
- addressed_findings:
  - `[low]` `[patch]` ruff I001/TC002/E501 on portal views, PortalClient, and platform tests

## Auto Run Result

Status: done

Summary: `/stations/herald/` renders one slug (`pyforge-herald`) through `PortalClient.invoke` only. Invoke signs and verifies the RS256 assertion in-process and projects `deck status <slug>` — no raw HTTP, no `pyforge.*` in django-herald or new platform code, chrome still extends `django_pyforge/base.html`.

Files:
- `django_herald_portal/views.py` — PortalClient.invoke for chrome_home
- `herald_portal/home.html` — `#herald-deck-status` projection
- `django_pyforge/assertion/client.py` — `invoke` (emit + verify + argv projection)
- `tests/meta/test_portal_deck_status.py` — station AST/chrome gates
- `src/platform/tests/test_herald_portal_deck_status.py` — happy path, argv, 403, invoke
- `planning-artifacts/specs/spec-17-2-….md` — tracked story spec

Review: 1 low patch applied; follow-up score 1 → false.
Rejected: live Design/MCP HTTP from the portal; Lane 1 CMS; chrome copy; CFE replace; django_db Client GET (no local Postgres); pairing 17.1.

Verification: 3 passed (`test_portal_deck_status`); 4 passed (`test_herald_portal_deck_status`); 29 passed (assertion + shells minus DB Client); ruff clean.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
