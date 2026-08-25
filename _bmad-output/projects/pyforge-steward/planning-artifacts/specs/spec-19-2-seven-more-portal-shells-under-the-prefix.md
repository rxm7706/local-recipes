---
title: 'Seven more portal shells under the prefix'
type: feature
created: '2026-08-24'
status: done
baseline_revision: 61b8874fa8d06119f916e11a1922825a9dbd80bf
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings:
  - oversized
deferred: []
---

<intent-contract>

## Intent

**Problem:** Only Warden is a real station portal under `/stations/<name>/`. Operators still cannot stay in one session and open atlas, doctor, herald, marshal, mason, scribe, and steward on the same origin as Lane 1.

**Approach:** Add seven reusable `django-<station>` shells that register via existing `PortalConfig` discovery, share chrome and the assertion client, and stay projection-only. Do not rebuild Warden.

## Boundaries & Constraints

**Always:** Eight stations in one session: `atlas`, `doctor`, `herald`, `marshal`, `mason`, `scribe`, `steward`, `warden`. Naming triple for each new shell: distribution `django-<station>` at `src/shared/packages/django-<station>/`, module `django_<station>_portal`, label `<station>_portal`. Warden stays `django-warden` / `django_warden_fabric` / `warden_fabric`. Host `INSTALLED_APPS` lists each module; host URLconf keeps a single `stations/` include. Portals call stations only through `django_pyforge.assertion.client.PortalClient`. Switcher tiles omit `work_class` `01` and `02`. Parent AD-2: no `pyforge.*` under `src/platform/`. Rebase onto `origin/main` before merge if Warden 9-3 landed.

**Block If:** Implementation would move existing Django models between apps, start Epic 20 Wagtail, absorb spec-wagtail-corporate-brain, or rewrite `src/shared/packages/pyforge-warden` plugin/scanner layers.

**Never:** Epic 20. MinIO. `pyforge.*` under `src/platform/`. Portal imports of `pyforge.<station>` internals. Raw HTTP from a portal to a service (`httpx`, `requests`, `urllib.request`, `http.client`). Second write path on portal models. Host station roster in `config/urls.py`. Tiling 01/02 as first-class switcher stations. Conda-forge feedstocks for these first-party apps.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| One session, eight GETs | Authenticated client with all eight station roles; `GET /stations/<name>/` for each | All 200; no login redirect; paths same-origin under `/stations/` | 403 only if that station role is missing |
| Naming triple | Each remaining station package on disk + `INSTALLED_APPS` | Dist `django-<station>`, module `django_<station>_portal`, label `<station>_portal`; Warden triple unchanged | Test fails on mismatch |
| Client-only reach | Portal Python trees | No `pyforge.<station>` import; no raw HTTP client to a service; any emit uses `PortalClient` | Test fails on offenders |
| Projection | New portal apps | No Django models / migrations that write domain state; Warden fabric models stay in `warden_fabric` | Fail if models appear on a new shell |
| Switcher 01/02 | Portal with `work_class` `01` or `02` and matching IdP role | Absent from `pyforge_portals` / switcher HTML; still discoverable | Direct URL still station-enforced |

</intent-contract>

## Code Map

- `src/shared/packages/django-warden/src/django_warden_fabric/apps.py` -- clone PortalConfig shape (`station_name`, `mount_token`, `mcp_token`, `work_class="03"`, `urlconf`); do not move models
- `src/shared/packages/django-pyforge/src/django_pyforge/portals.py` -- registration protocol; do not add SLA fields
- `src/shared/packages/django-pyforge/src/django_pyforge/urls.py` -- discovery include; new shells mount here once installed
- `src/shared/packages/django-pyforge/src/django_pyforge/context_processors.py:chrome` -- today filters by role only; must also drop `work_class` in `{"01","02"}`
- `src/shared/packages/django-pyforge/src/django_pyforge/assertion/client.py` -- `PortalClient.emit`; portals must not open HTTP
- `src/shared/packages/django-pyforge/src/django_pyforge/probe_portal/` -- chrome-only fixture to copy (views + template extending `django_pyforge/base.html` + `require_station_role`)
- `src/shared/packages/django-pyforge/src/django_pyforge/access.py` -- station 403, not switcher
- `src/platform/config/settings/base.py:23-31` / `:131-147` -- sys.path inserts + `LOCAL_APPS`; generalize for seven `django-*_portal` modules
- `src/platform/config/settings/test.py:52-53` -- keep probe portal; add a `work_class` `01` fixture app for the switcher matrix row
- `src/platform/config/urls.py:25-32` -- read-only except if a new include would create a roster (forbidden)
- `src/platform/pyproject.toml:12-14` -- pythonpath for each new `django-<station>/src`
- `src/platform/Containerfile:355-357` -- COPY each new module beside chrome/warden
- `.github/workflows/platform-ci.yml:90-91` / `:108-109` -- path filters for `django-*`
- `src/platform/tests/test_django_pyforge_chrome.py` -- `EXPECTED_PORTALS` currently `{warden, chrome-probe}`; extend eight stations + probe; chrome-copy scan over all portal trees
- `src/platform/tests/test_django_pyforge_assertion.py:61-77` -- extend `PORTAL_TREES` to every new portal module
- `src/platform/tests/meta/test_no_pyforge_import.py` -- must stay green
- Read-only: `src/shared/packages/pyforge-warden/**` (Warden 9-3); `src/shared/packages/django-warden/**` models/migrations; Epic 20 / Wagtail

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/django-{atlas,doctor,herald,marshal,mason,scribe,steward}/**` -- hatchling dist; PortalConfig; chrome_home; no models
- `src/shared/packages/django-pyforge/src/django_pyforge/context_processors.py` -- hide work_class 01/02 from switcher
- `src/shared/packages/django-pyforge/src/django_pyforge/workclass_probe/` -- test-only PortalConfig `work_class="01"` (not a production station)
- `src/platform/config/settings/base.py` + `test.py` -- path + INSTALLED_APPS
- `src/platform/pyproject.toml` + `src/platform/Containerfile` + `.github/workflows/platform-ci.yml` -- install/copy/CI
- `src/platform/tests/test_station_portal_shells.py` -- matrix: session, triples, client-only, projection, 01/02
- `src/platform/tests/test_django_pyforge_chrome.py` + `test_django_pyforge_assertion.py` -- expected names + PORTAL_TREES

**Acceptance Criteria:**
- Given chrome and the assertion client, when each of the eight portals is requested in one session, then none re-authenticate and all are same-origin with Lane 1
- Given each remaining station, when packaged, then it has `django-<station>/` with the naming triple, and existing models do not move between apps
- Given a portal, when it reaches a station, then it uses django-pyforge's client only — no station internals, no raw HTTP to a service
- Given portal Django models, when inspected, then they are projections, not a second write path
- Given a `work_class` 01 or 02 registration, when the switcher renders, then it is not tiled as a first-class station

## Spec Change Log

## Review Triage Log

### 2026-08-24 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 9: (high 0, medium 6, low 3)
- defer: 0
- reject: 8
- addressed_findings:
  - `[medium]` `[patch]` work_class 02 had no fixture/test — added `is_switcher_tile` unit coverage for 01 and 02
  - `[medium]` `[patch]` 01 switcher test did not render HTML — now uses `switcher.html`
  - `[medium]` `[patch]` `PORTAL_TREES` omitted `workclass_probe`
  - `[medium]` `[patch]` new shell `chrome_home` never asserted 403 without the station role
  - `[medium]` `[patch]` AST hunt only flagged `pyforge.<own station>` — now any `pyforge.*` package import
  - `[medium]` `[patch]` no check that probe fixtures stay out of production `LOCAL_APPS`
  - `[low]` `[patch]` `chrome()` used bare `.work_class` — now `getattr`
  - `[low]` `[patch]` `_raw_http_imports` missed `from http import client`
  - `[low]` `[patch]` `NEW_STATIONS = EIGHT_STATIONS[:-1]` depended on tuple order

## Design Notes

New shells use app suffix `portal` (not a bare station label) so a later sibling app does not collide. Warden keeps `fabric`. Empty shells ship no `models.py` / migrations — that is the projection rule for apps that do not yet project rows. Warden's existing `ComplianceJob` writer stays until a later cutover; this story must not relocate it.

`chrome()` lists portals with `work_class` not in `{"01","02"}` and `station_name in roles`. Discovery and URLconf stay unfiltered so a 01/02 app can still mount; it is just not a switcher tile.

Wire sys.path like 19.1: if `find_spec` is None, insert `src/shared/packages/django-<station>/src`.

## Verification

**Commands:**
- `pixi run -e platform-ci-test python -m pytest tests/test_station_portal_shells.py tests/test_django_pyforge_chrome.py tests/test_django_pyforge_assertion.py tests/meta/test_no_pyforge_import.py tests/policy -q` (cwd `src/platform`) -- expected: all passed

## Auto Run Result

Status: done
Summary: Seven chrome-only `django-<station>` shells mount under `/stations/<name>/` beside Warden; switcher hides work_class 01/02; portals stay projection-empty and client-only (AST).
Files:
- `src/shared/packages/django-{atlas,doctor,herald,marshal,mason,scribe,steward}/` — hatchling PortalConfig shells
- `django_pyforge/context_processors.py` — `is_switcher_tile`
- `django_pyforge/workclass_probe/` — test-only work_class 01
- host settings, pythonpath, Containerfile, `platform-ci.yml` `django-*/**`
- `tests/test_station_portal_shells.py` plus chrome/assertion updates
Review: 9 patches applied (6 medium, 3 low; follow-up score 21); 8 rejected (19.1 packaging patterns, positive PortalClient emit, OIDC round-trip); 0 deferred.
Verification: 68 passed under platform-ci-test with local PostgreSQL 17 + Redis 7 (`DATABASE_URL=postgres://postgres:platform@127.0.0.1:5432/platform`).
Residual: shells do not call `PortalClient.emit` yet (no service face until Epic 21); rebase onto origin/main (Warden 9-3) before merge.
