---
title: django-pyforge is the only chrome
type: feature
created: '2026-08-24'
status: done
updated: '2026-08-24'
baseline_revision: 5eafc38d8bd30d08ba373b32674976a9ceadb34b
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
deferred:
  - summary: >-
      django-pyforge is not a pixi path dependency of platform-ci-test or the
      image pip layer; the host loads it via sys.path and a Containerfile COPY.
    evidence: |-
      Hatchling pyproject exists. A pixi path dep would rewrite pixi.lock; the
      image pip layer cannot hatchling-build without extra tools.
    location: >-
      pixi.toml / src/platform/Containerfile
    severity: medium
  - summary: >-
      Container secrets-scan still covers only src/platform and shell-hook, not
      the new django_pyforge COPY.
    evidence: |-
      Runtime copies src/shared/packages/django-pyforge into /app/django_pyforge.
    location: >-
      src/platform/Containerfile
    severity: low
  - summary: >-
      Uninstall AC is proven with an isolated template Engine, not by mutating
      INSTALLED_APPS (Client GET needs a live database under ATOMIC_REQUESTS).
    evidence: |-
      test_removing_chrome_breaks_both_portals_identically uses Engine(app_dirs=False).
    location: >-
      src/platform/tests/test_django_pyforge_chrome.py
    severity: low
---

> **2026-08-25:** `[feature.platform-image-pip]` as an *installer* is superseded by
> `spec-platform-image-one-pixi-env`. Acceptance criteria and deferred items above are historical
> (this story shipped).

<intent-contract>

## Intent

**Problem:** Station portals can each ship a switcher, base layout, or theme, and adding a station currently means editing the host URLconf. CAP-1 / canopy:AD-1 and canopy:AD-3 require one installable chrome package.

**Approach:** Ship `django-pyforge` as a reusable Django app. Portals register via AppConfig (station name, mount token, MCP token, chrome hooks, plus owner slug, backup, `work_class`, promotion date). The host discovers them with `apps.get_app_configs()` and mounts `/stations/<name>/` as a pattern. SLA body is not a chrome field. Prove with two portals: existing `compliance_face` plus a test fixture portal (not Epic 19 shells).

## Boundaries & Constraints

**Always:** Chrome templates and theme static live only in `django-pyforge`. Discovery is `apps.get_app_configs()`. Portal mount tokens must be `/stations/<station_name>/`. Parent AD-2: no `pyforge.*` import under `src/platform/`. Keep the existing `/compliance/` include; do not add the S-19.1 redirect.

**Block If:** A change would require renaming `compliance_face` or adding FastAPI ports.

**Never:** Second chrome in a portal. Hardcoded station roster in host URLconf. `django-lasuite` as UI. Steward SLA microservice. S-18.2 role switcher. S-18.3 RS256 client. S-19.1 warden rename. S-32.1 plugin API. MinIO. Eight FastAPI ports.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Two portals render | Both portals in INSTALLED_APPS; GET each chrome page | `#pyforge-chrome` markup byte-identical; templates resolve from django-pyforge | No error expected |
| Portal ships chrome copy | Portal templates/ or static/ contains base/switcher/theme | Enumeration test fails | Assertion failure |
| Bad mount token | AppConfig mount_token not `/stations/<name>/` | Registration check returns Error | Check fails the config |
| Missing chrome app | django-pyforge removed from INSTALLED_APPS | Both portal templates fail the same parent lookup | TemplateDoesNotExist for `django_pyforge/base.html` |
| SLA on chrome | AppConfig defines `sla_body` | Registration check returns Error | Check fails the config |

</intent-contract>

## Code Map

- `src/shared/packages/django-pyforge/` -- new hatchling package; module `django_pyforge` (not `pyforge.*`)
- `src/shared/packages/django-pyforge/src/django_pyforge/apps.py` -- `DjangoPyforgeConfig` plus `PortalConfig` protocol fields
- `src/shared/packages/django-pyforge/src/django_pyforge/discovery.py` -- `iter_portal_configs()` via `apps.get_app_configs()`
- `src/shared/packages/django-pyforge/src/django_pyforge/checks.py` -- prefix + no-`sla_body` system checks
- `src/shared/packages/django-pyforge/src/django_pyforge/urls.py` -- include each portal at `<station_name>/` (host mounts this at `stations/`)
- `src/shared/packages/django-pyforge/src/django_pyforge/templates/django_pyforge/` -- `base.html` + `switcher.html` only chrome templates
- `src/shared/packages/django-pyforge/src/django_pyforge/static/django_pyforge/theme.css` -- theme assets
- `src/shared/packages/django-pyforge/src/django_pyforge/probe_portal/` -- test/fixture portal app (not an Epic 19 shell)
- `src/platform/config/settings/base.py:117` -- add `django_pyforge` to LOCAL_APPS; do not list station names
- `src/platform/config/settings/test.py` -- add probe portal to INSTALLED_APPS
- `src/platform/config/urls.py:23` -- keep `compliance/` include; add `stations/` include of django-pyforge urls only (no roster)
- `src/platform/compliance_face/apps.py` -- subclass `PortalConfig`; OM Q3 fields; no `sla_body`
- `src/platform/compliance_face/views.py` + `urls.py` -- thin HTML chrome page extending django-pyforge base (JSON API unchanged)
- `pixi.toml` -- `[feature.platform-ci-test.pypi-dependencies]` path to django-pyforge; `[feature.platform-image-pip.pypi-dependencies]` path for image layer
- `scripts/platform_image_pip_layer.py` -- emit local path requirements (not only `==` pins)
- `.github/workflows/platform-ci.yml` -- path filter includes `src/shared/packages/django-pyforge/**`
- `src/platform/tests/test_django_pyforge_chrome.py` -- ACs
- Read-only: `src/platform/tests/meta/test_no_pyforge_import.py` (must stay green)

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/django-pyforge/**` -- create installable chrome app + probe portal -- CAP-1 package
- `src/platform/config/settings/base.py` -- install django_pyforge -- host consumes chrome
- `src/platform/config/urls.py` -- `stations/` pattern include -- no station roster
- `src/platform/compliance_face/**` -- register as portal; chrome page extends shared base -- second chrome forbidden
- `pixi.toml` + `scripts/platform_image_pip_layer.py` + `environment.yaml` if lock/export required -- installable in CI and image
- `src/platform/tests/test_django_pyforge_chrome.py` -- cover I/O matrix

**Acceptance Criteria:**
- Given two portal apps in INSTALLED_APPS, when they render a chrome page, then chrome markup is byte-identical and sourced from django-pyforge
- Given a test that enumerates portal template/static dirs, when either ships a base layout, switcher, or theme copy, then the test fails
- Given host URLconf, when inspected, then it has no station roster; discovery is `apps.get_app_configs()`
- Given a portal registering outside `/stations/<name>/`, when checks run, then the registration check fails
- Given AppConfig discovery, when a portal is registered, then owner slug, backup, `work_class`, and promotion date are present and `sla_body` is not a chrome field
- Given django-pyforge removed from INSTALLED_APPS, when both portals resolve their layout parent, then both fail identically

## Spec Change Log

## Review Triage Log

### 2026-08-24 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 10: (high 2, medium 5, low 3)
- defer: 3: (high 0, medium 1, low 2)
- reject: 6
- addressed_findings:
  - `[high]` `[patch]` Moved `PortalConfig` out of `apps.py` (`default=False`) so chrome is the only default AppConfig
  - `[high]` `[patch]` `DjangoPyforgeConfig.ready` imports `django_pyforge.checks`; test runs `run_checks()`
  - `[medium]` `[patch]` Split `portal_urls` from JSON `urls` so GET `/compliance/` stays the JSON face
  - `[medium]` `[patch]` Chrome identity test uses the real `chrome` context processor
  - `[medium]` `[patch]` Switcher links `portal.mount_token`
  - `[medium]` `[patch]` Image `rm -rf` probe_portal after COPY
  - `[medium]` `[patch]` Duplicate `station_name` check E005
  - `[low]` `[patch]` `sys.path` insert only when `find_spec("django_pyforge")` is None
  - `[low]` `[patch]` Empty required chrome fields fail E004
  - `[low]` `[patch]` Probe `chrome_home` is `@require_GET`

## Design Notes

Host keeps `path("compliance/", include("compliance_face.urls"))` as today's JSON face. Story 19.1 owns the permanent redirect and app rename. Discovery mounts `compliance_face.portal_urls` at `/stations/warden/` (HTML chrome only).

`PortalConfig` lives in `django_pyforge.portals`, not `pyforge.*`, so the host may import it.

Probe portal station name `chrome-probe` is a test fixture, not a Guildhall station.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done
Summary: Shipped `django-pyforge` chrome package with AppConfig portal protocol, host `stations/` discovery include (no station roster), Warden + fixture probe portals, and AC tests.
Files: `src/shared/packages/django-pyforge/**` (chrome app); host settings/urls/Containerfile; `compliance_face` PortalConfig + portal_urls; platform tests; spec; platform-ci path filter.
Review: 10 patches applied (2 high); 3 deferred; remaining findings rejected (pixi lock, README, unused mcp_token until S-18.3, lasuite, FastAPI).
Follow-up review recommended: true (2 high patches; score 3×5 medium + 1×3 low = 18).
Tests: 37 passed (`test_django_pyforge_chrome` + policy + import-linter). Full `pytest -v` not run locally (PostgreSQL).
Residual: no pixi.lock install of the wheel; secrets-scan does not yet cover the chrome COPY.
