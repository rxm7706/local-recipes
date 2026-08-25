---
title: Warden moves and is renamed
type: feature
created: '2026-08-24'
status: done
baseline_revision: a4738f942fd0d45ac454c4918ca58139b29a6ed7
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings:
  - oversized
deferred: []
---

<intent-contract>

## Intent

**Problem:** The shipped Warden portal still lives as `compliance_face` at `/compliance/`, so the estate cannot enforce one `/stations/<name>/` prefix and cannot rename the app while the application role still has DDL.

**Approach:** Repackage that portal as reusable app `django-warden` / `django_warden_fabric` / `warden_fabric`, mount it at `/stations/warden/` via existing PortalConfig discovery, and leave `/compliance/` as a permanent redirect that preserves path and query.

## Boundaries & Constraints

**Always:** Distribution `django-warden` at `src/shared/packages/django-warden/`; module `django_warden_fabric`; label `warden_fabric`. Host `INSTALLED_APPS` lists the module. JSON + HTML routes live under `/stations/warden/`. `/compliance/` is a supported permanent redirect (308, method-preserving) to `/stations/warden/` with path and query kept. Existing `ComplianceJob` rows, `django_migrations` rows, and `django_content_type` rows survive the label change. Warden planning artifacts that name the old app still resolve via an explicit map (do not rewrite Epic 8 contracts). Parent AD-2: no `pyforge.*` under `src/platform/`. Rebase onto `origin/main` before merge if Warden 9-2 landed.

**Block If:** An Epic 27 story that revokes app-role DDL has started, or the rename would require moving models into a second app.

**Never:** Epic 19.2 seven station shells. Extracting scanners from `src/shared/packages/pyforge-warden`. MinIO. `pyforge.*` imports under `src/platform/`. A temporary redirect scheduled for removal. Label `warden` (bare). A conda-forge feedstock for this first-party app.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Prefix GET | `GET /compliance/upload/?kind=sbom` | `308` `Location: /stations/warden/upload/?kind=sbom` | No error expected |
| Prefix POST | `POST /compliance/upload/` | `308` with same method target `/stations/warden/upload/` | Client reissues POST; no 301→GET conversion |
| Chrome mount | `GET /stations/warden/` | Existing chrome_home still resolves | No error expected |
| JSON mount | `GET /stations/warden/jobs/<id>/` | Same JSON face as the old `/compliance/` include | 404 only if job missing |
| Identifier sweep | `src/` tree | No `\bcompliance_face\b` match | Test fails on leftover identifier |
| Populated relabel | Old table + job row + old content type + old `django_migrations` row; apply 0001 | Job PK remains; table is `warden_fabric_compliancejob`; content type `app_label=warden_fabric`; old migrations row still present plus new app’s 0001 | Forwards is idempotent if new table already exists |
| Fresh install | Empty DB `migrate` | Creates `warden_fabric_compliancejob` only | No error expected |
| Warden artifacts | `spec-8-1` / `spec-8-2` still name the old app | Files exist; README map points to the new triple | No dangling path with no successor |

</intent-contract>

## Code Map

- `src/platform/compliance_face/` -- shipped app to move (apps.py PortalConfig already `mount_token=/stations/warden/`; `portal_urls.py` chrome only; `urls.py` JSON face still included from host at `compliance/`)
- `src/shared/packages/django-pyforge/` -- copy packaging/sys.path/Containerfile COPY pattern; do not change chrome protocol
- `src/shared/packages/django-pyforge/src/django_pyforge/urls.py` -- discovery include; warden mounts here once INSTALLED_APPS uses the new module
- `src/platform/config/settings/base.py:23` / `:140` -- add django-warden `sys.path` insert; replace `compliance_face` in LOCAL_APPS
- `src/platform/config/urls.py:23` -- replace JSON include with prefix redirect; keep `stations/` include
- `src/platform/config/settings/test.py:50` -- probe portal stays; no Epic 19 shells
- `src/platform/pyproject.toml:12` -- pythonpath includes django-warden src
- `src/platform/Containerfile:355` -- COPY django_warden_fabric beside django_pyforge
- `.github/workflows/platform-ci.yml:90` / `:107` -- path filter `django-warden/**`
- `src/platform/tests/test_django_pyforge_chrome.py` -- template/path/urlconf strings
- `src/platform/tests/test_compliance_face_phases.py` -- rename; import `django_warden_fabric`
- `src/platform/tests/meta/test_no_pyforge_import.py` -- must stay green (host still must not import `pyforge.*`)
- `_bmad-output/projects/pyforge-warden/planning-artifacts/specs/README.md` -- name map so 8-1/8-2 still resolve
- `_bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md` -- DW-CANOPY close_when
- Read-only: `src/shared/packages/pyforge-warden/**` (Warden 9-2 overlap)

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/django-warden/**` -- move portal; hatchling dist `django-warden`; AppConfig name/label/urlconf; Celery task name `warden_fabric.run_job`; merge JSON routes into portal urlconf
- `src/shared/packages/django-warden/src/django_warden_fabric/migrations/0001_initial.py` -- SeparateDatabaseAndState: CreateModel in state; DB creates or renames table; relabel content types; leave old `django_migrations` rows
- `src/platform/config/**` -- INSTALLED_APPS, sys.path, 308 redirect
- `src/platform/Containerfile` + `src/platform/pyproject.toml` + `.github/workflows/platform-ci.yml` -- install/copy/CI paths
- `src/platform/tests/test_warden_fabric_rename.py` -- matrix: redirect, identifier sweep, relabel survival, fresh table name
- `src/platform/tests/test_django_pyforge_chrome.py` + phase tests -- follow the move
- `_bmad-output/projects/pyforge-warden/planning-artifacts/specs/README.md` -- old-name map
- delete `src/platform/compliance_face/` after the move

**Acceptance Criteria:**
- Given the shipped portal, when this story merges, then distribution is `django-warden`, module `django_warden_fabric`, label `warden_fabric`
- Given `/compliance/` plus a subpath and query, when requested, then the response is a permanent redirect to `/stations/warden/` preserving path and query
- Given `src/`, when searched for identifier `compliance_face`, then there are no matches
- Given existing job rows, `django_migrations`, and content types, when the app-label migration applies, then those rows survive
- Given this story, when sequencing Epic 27, then 19.1 is complete first and no Epic 27 work starts here
- Given pyforge-warden planning artifacts that named the old app, when followed, then they still resolve

## Spec Change Log

## Review Triage Log

### 2026-08-24 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 1, medium 2, low 1)
- defer: 0
- reject: 2
- addressed_findings:
  - `[high]` `[patch]` Fresh migrate used historical `apps.get_model("warden_fabric")` inside SeparateDatabaseAndState; switched to CreateModel + rename/drop of the legacy table
  - `[medium]` `[patch]` Redirect is 308 (method-preserving), not Django RedirectView 301
  - `[medium]` `[patch]` Identifier sweep uses `\b` + joined token so the old table name may remain
  - `[low]` `[patch]` Golden PEM header assertion in 18.3 tests no longer spells a private-key BEGIN line (credential-surface policy)

## Design Notes

Use HTTP **308** so POST upload clients do not get converted to GET (Django `RedirectView.permanent` is 301). Query string is appended (`RedirectView.query_string` equivalent).

Do not `UPDATE django_migrations` from `compliance_face` to `warden_fabric` for `0001_initial` inside that same migration — the recorder would unique-conflict. Leave the old row (history survives) and let Django insert `(warden_fabric, 0001_initial)`.

Identifier sweep uses `\bcompliance_face\b` so the physical old table name `compliance_face_compliancejob` in the migration is allowed.

## Verification

**Commands:**
- `pixi run -e platform-ci-test python -m pytest tests/test_warden_fabric_rename.py tests/test_django_pyforge_chrome.py tests/test_warden_fabric_phases.py tests/meta/test_no_pyforge_import.py tests/policy -q` (cwd `src/platform`) -- expected: all passed
- `rg -n --pcre2 '\\bcompliance_face\\b' src` -- expected: no matches

## Auto Run Result

Status: done
Summary: Repackaged the shipped Warden portal as django-warden / django_warden_fabric / warden_fabric at /stations/warden/; /compliance/ is a 308 prefix redirect; app-label migration preserves jobs and history; warden specs README maps the old name.
Tests: 71 passed (rename + chrome + phases + assertion + import-linter + policy) under platform-ci-test with local PostgreSQL 17 + Redis 7.

