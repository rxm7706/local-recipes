---
title: 'Same URL, different rows'
type: feature
created: '2026-08-25'
status: done
baseline_commit: 541f9b0404159ce69e8ed9f0cbc8abf1a0fdec36
baseline_revision: 541f9b0404159ce69e8ed9f0cbc8abf1a0fdec36
review_loop_iteration: 0
followup_review_recommended: true
context:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/filtering.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/declarations.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/cache.py
  - src/shared/packages/django-atlas/src/django_atlas_portal/views.py
  - src/shared/packages/django-pyforge/src/django_pyforge/roles.py
  - src/platform/tests/test_station_portal_shells.py
  - src/platform/tests/meta/test_no_pyforge_import.py
warnings:
  - oversized
deferred:
  - summary: >-
      Canopy AD-20 also names audit write and role-built navigation; this
      story's board is JSON filter-then-search only.
    evidence: |-
      Story 23.1 ACs and FR-16 name same-URL row isolation via
      filter_by_role / AccessDeclaration. Audit and build_navigation are
      already in pyforge.steward.dashboard from Epic 9 and were not wired
      onto /stations/atlas/board/.
    location: >-
      src/shared/packages/django-atlas/src/django_atlas_portal/board.py
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Analytical boards behind the host are not row-isolated. Two authenticated roles can share a URL and still see the same slice, or a second stack (Vizro) would re-filter. FR-16 / canopy AD-20.

**Approach:** Serve one board URL on the atlas portal. Load the unfiltered master via `get_master_dataset`, then `filter_by_role` / `AccessDeclaration` and `search`. Identity is this request's IdP token roles (18.2), not trusted headers (FR-15).

## Boundaries & Constraints

**Always:** Isolation is only `pyforge.steward.dashboard` filter-then-search. Server-side. Same path for every role. Portal may import `pyforge.steward.dashboard` (not `pyforge.atlas`). `src/platform/` and `src/platform/tests/` never import `pyforge.*`. Cache stores the master only. `Cache-Control: no-store`. Cite canopy AD-20. Specs under `_bmad-output/projects/pyforge-steward/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-steward`.

**Block If:** Implementation would require Vizro/Dash/Flask as the isolation mechanism, trusted-header identity on the host, CloudEvents/Epic 24, Epic 30 console deletion, MinIO, or Liquibase 27-1.

**Never:** Start 24-1. `pyforge.*` under `src/platform/`. Atlas Vizro CLI pages inside the host. A second row-filter stack. `DashboardIdentityMiddleware` as the host identity path. `scripts/bmad-switch`. `bmad-loop`. Other stations' ledgers.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Two roles, same URL | Users A=`atlas`+`east`, B=`atlas`+`west`; GET `/stations/atlas/board/` | Same path; JSON rows disjoint as `east` vs `west` dictate | 200; `no-store` |
| Filter-then-search only | Board view production path | Calls `get_master_dataset` then `filter_by_role` then `search`; never `search` on master | TypeError if `search` got master |
| No row role | Token has `atlas` only | Zero rows, fail-closed | 200 empty list, not 500 |
| Client-side cannot widen | Attacker crafts query/body | Response rows still role-sliced | Extra params ignored |
| Second stack banned | Host, chrome, all `django-*` portal trees | No `vizro`/`dash` import that filters rows; no `pyforge.atlas.dashboard` import | Test fails on offenders |
| Platform boundary | `src/platform/` | No `pyforge` import; lint-imports 0 broken | Gate fails |
| Atlas CLI stays out | `pyforge.atlas` Vizro CLI | Unchanged; not mounted on host URLconf | Non-goal |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/filtering.py` -- reuse `filter_by_role`, `search`, `RoleFilteredRows` (do not fork)
- `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/declarations.py` -- reuse `AccessDeclaration` (`access_column` + closed `roles`)
- `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/cache.py` -- reuse `get_master_dataset`; fetch returns the full master
- `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/middleware.py` -- read-only; do not wire trusted headers on the host
- `src/shared/packages/django-pyforge/src/django_pyforge/roles.py` -- `roles_from_request` / session `idp_token_roles`
- `src/shared/packages/django-pyforge/src/django_pyforge/access.py` -- keep `@require_station_role("atlas")` on the board URL
- `src/shared/packages/django-atlas/src/django_atlas_portal/board.py` -- NEW: declaration, master fetch, unique row-role from `roles ∩ declaration.roles` (0 or >1 → `role=None`), view JSON
- `src/shared/packages/django-atlas/src/django_atlas_portal/urls.py` -- `board/` on the existing atlas prefix
- `src/shared/packages/django-atlas/src/django_atlas_portal/views.py` -- chrome_home unchanged
- `src/platform/tests/test_station_portal_shells.py` -- allowlist only `pyforge.steward.dashboard*` on atlas; still forbid `pyforge.atlas` and other stations
- `src/platform/tests/test_host_board_row_isolation.py` -- NEW: HTTP Client matrix; AST second-stack ban; no `import pyforge` in this file
- `src/platform/pyproject.toml` -- pythonpath `../shared/packages/pyforge-steward/src`
- `src/platform/Containerfile` -- COPY `pyforge-steward/src/pyforge` to `/app/pyforge` so the portal import resolves in the image
- `src/platform/tests/meta/test_no_pyforge_import.py` -- must stay green
- Read-only: `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/` (CLI Vizro stays outside the host)

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/django-atlas/src/django_atlas_portal/board.py` -- host board using steward dashboard primitives only
- [x] `src/shared/packages/django-atlas/src/django_atlas_portal/urls.py` -- same URL for every role
- [x] `src/platform/tests/test_station_portal_shells.py` -- atlas allowlist for steward dashboard
- [x] `src/platform/tests/test_host_board_row_isolation.py` -- I/O matrix + Vizro/second-stack AST
- [x] `src/platform/pyproject.toml` + `src/platform/Containerfile` -- import path at test and image time

**Acceptance Criteria:**
- Given two authenticated users with different row roles, when they request the same board URL, then returned rows differ as their roles dictate.
- Given the board view, when it serves rows, then isolation is server-side filter-then-search via `filter_by_role` / `AccessDeclaration`.
- Given host/chrome/portal source, when a second isolation stack (including Vizro that filters its own rows) appears, then that is a review-blocking / test-failing finding.
- Given atlas's own Vizro CLI pages, when the host URLconf is inspected, then they stay outside the host.

## Spec Change Log

## Review Triage Log

### 2026-08-25 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 3, low 2)
- defer: 1: (high 0, medium 1, low 0)
- reject: 18
- addressed_findings:
  - `[medium]` `[patch]` `fetch_master_dataset` deep-copies rows so LocMemCache cannot alias mutable master dicts
  - `[medium]` `[patch]` POST JSON body to the board URL cannot widen rows (405, no west labels)
  - `[medium]` `[patch]` GET `/stations/atlas/board/` without station role `atlas` is 403 with no rows payload
  - `[low]` `[patch]` isolation tests assert the other tenant's labels are absent from response bytes
  - `[low]` `[patch]` urlconf test requires `filter_by_role` / `AccessDeclaration` imports on `board.py`

## Design Notes

Row vocabulary is `east` / `west` on access column `tenant`. Station role `atlas` is reachability (18.2), not a row tag. Pick the unique intersection of token roles with `AccessDeclaration.roles`; zero or multiple intersections fail closed to `role=None` (empty `RoleFilteredRows`). Fixture master is in-process (skewed: more `east` than `west`) so isolation is not vacuous. JSON body `{"rows":[...]}`. Do not mount Vizro ASGI.

## Verification

**Commands:**
- `pixi run -e platform-ci-test -- pytest src/platform/tests/test_host_board_row_isolation.py src/platform/tests/test_station_portal_shells.py src/platform/tests/meta/test_no_pyforge_import.py -q` -- expected: all pass (needs Django test settings DB like sibling platform tests)
- Confirm atlas Vizro CLI modules are not referenced from `src/platform/config/urls.py`

## Auto Run Result

Status: done
Summary: Atlas portal serves one board URL; steward `get_master_dataset` → `filter_by_role` / `AccessDeclaration` → `search` slices JSON rows by IdP token role. Vizro CLI stays unmounted.
Files:
- `django_atlas_portal/board.py` — host board view
- `django_atlas_portal/urls.py` — `board/` on the atlas prefix
- `tests/test_host_board_row_isolation.py` — HTTP + AST matrix
- `tests/test_station_portal_shells.py` — atlas allowlist for steward dashboard
- `src/platform/pyproject.toml` + `Containerfile` — test/image import path
Review: 5 patches applied (3 medium, 2 low; follow-up score 11); 1 deferred (AD-20 audit/navigation); 18 rejected.
Verification: 18 passed under platform-ci-test (`DATABASE_URL=postgres://postgres:platform@127.0.0.1:5432/platform`); ruff clean on touched Python.
Residual: image COPY of `pyforge-steward` not rebuilt in this run; fixture master not live atlas analytics.
