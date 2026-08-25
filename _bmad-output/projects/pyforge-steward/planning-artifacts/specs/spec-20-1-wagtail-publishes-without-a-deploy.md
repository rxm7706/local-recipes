---
title: Wagtail publishes without a deploy
type: feature
created: '2026-08-24'
status: done
updated: '2026-08-24'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-unifying-strategy-2026-08-24/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/stack.md
warnings:
  - oversized
baseline_revision: d8f0a702bf4d9bcf91d05d85bcbb8ffbdec0350a
review_loop_iteration: 0
followup_review_recommended: true
deferred:
  - summary: >-
      WAGTAILADMIN_BASE_URL still defaults to http://localhost:8000; production
      origin belongs on the Helm/env overlay, not this story's app contract.
    evidence: |-
      Review noted no chart override. Lane 1 HTTP ACs do not require a live
      ingress host in this story; 20.2/deploy overlay can set the env var.
    location: >-
      src/platform/config/settings/base.py
    severity: low
  - summary: >-
      migrate does not seed a HomePage as Site.root_page; `/` is Wagtail's
      default welcome Page until an editor publishes.
    evidence: |-
      AC is publish-then-see, not empty-cluster first GET. Welcome remains
      DB-backed. Seeding is optional operator content.
    location: >-
      src/platform/platformapp/front_door/migrations/0001_homepage.py
    severity: low
  - summary: >-
      wagtail.documents / wagtail.images serving URLconfs are not mounted.
    evidence: |-
      Story 20.2 owns RWX media and renditions; 20.1 forbids starting that split.
    location: >-
      src/platform/config/urls.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** Estate `/` is a cookiecutter `TemplateView`. Editors cannot publish a runbook without a new image and a Deployment rollout (canopy FR-4 / CAP-2).

**Approach:** Mount Wagtail on the existing Django host at `/`. Page rows live in PostgreSQL. Admin login is `WAGTAILADMIN_LOGIN_URL` through the existing allauth OIDC path. IdP group `wagtail-admin` maps to `wagtailadmin.access_admin`.

## Acceptance Criteria

- Given an authenticated editor with the Wagtail-admin IdP group, when they publish a page, then an estate request sees it with no new image and no Deployment rollout.
- Given published page rows in PostgreSQL, when a process restarts or a second client (replica stand-in) reads `/`, then the body is identical; Lane 1 page state is not on ephemeral disk.
- Given an unauthenticated request to Wagtail admin, when it hits the admin URL, then it redirects to the IdP; no local password or email-management surface is reachable.
- Given an authenticated user with no admin group, when they request Wagtail admin, then they are refused with a comprehensible error.
- Given host settings, when loaded, then `WAGTAILADMIN_LOGIN_URL` is the allauth OIDC login.

## Boundaries & Constraints

**Always:** Lane 1 at `/`. Physical writes under `_bmad-output/projects/pyforge-steward/`. `BMAD_ACTIVE_PROJECT=pyforge-steward`. Pages are Django/Wagtail ORM on the existing `DATABASES["default"]`. `WAGTAILADMIN_LOGIN_URL` = existing `openid_connect_login`. `WAGTAILUSERS_PASSWORD_ENABLED = False`. `WAGTAIL_EMAIL_MANAGEMENT_ENABLED = False`. Search backend is PostgreSQL FTS (`django.contrib.postgres`), not Elasticsearch. Cite canopy AD-13 vs parent AD-n.

**Block If:** Adding Wagtail requires MinIO/S3, Elasticsearch, or a second public ASGI process; or platform-ci-test cannot import `wagtail` after the pin.

**Never:** MinIO/S3; Elasticsearch; Story 20.2 (RWX PVC, redis-cache vs redis-broker split, Celery `BaseTaskBackend`); Epic 30 console deletion; absorb `spec-wagtail-corporate-brain` or invent Atlas La Suite REST compatibility; close `lane1-serves-dw-h3`; `import pyforge.*` under `src/platform/`; CodeRed CMS.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Publish live | Editor with `wagtail-admin` group publishes HomePage body | Anonymous GET `/` returns that body; source is Page ORM, not `pages/home.html` | No error |
| Replica/restart | Same published row; new Client after cache clear | Identical HTML; no file under MEDIA_ROOT holds the page body | No error |
| Unauth admin | Anonymous GET Wagtail admin | 302 to allauth `openid_connect_login` | No password form |
| No admin group | Authenticated user without `wagtail-admin` GET admin | 403 with explicit missing-group copy | Not a blank bounce |
| Password/email off | Settings + URL reverse of password/email management | Flags false; those surfaces 404 or redirect away from a local password form | No usable password UI |
| Login URL | Settings | `WAGTAILADMIN_LOGIN_URL` resolves to OIDC login name | Mis-set URL fails test |

</intent-contract>

## Code Map

- `src/platform/config/urls.py` — replace root `TemplateView` with Wagtail catch-all **last**; keep `stations/`, `accounts/`, `ht/`, `compliance/`, `assertion/`
- `src/platform/config/settings/base.py` — Wagtail + `modelcluster`/`taggit`/`django.contrib.postgres` apps; `WAGTAILADMIN_LOGIN_URL`; password/email flags; database search backend
- `src/platform/config/settings/test.py` — `CLAIMS_CONTRACT` unchanged; add `WAGTAIL_ADMIN_IDP_GROUP` if not on contract
- `src/platform/platformapp/front_door/` — **new** app: `HomePage` (title + body in DB), migrations, admin 403 template/copy
- `src/platform/platformapp/users/provisioning.py` — provision `wagtail-admin` group with `wagtailadmin.access_admin`
- `src/platform/config/local_dev/personas.py` — editor persona (or group token) holding the Wagtail-admin IdP group
- `pixi.toml` `[feature.platform-ci-test.pypi-dependencies]` — `wagtail==7.4.3` (CI pytest)
- `pixi.toml` `[feature.python-agent-platform.dependencies]` — `wagtail >=7.4.3,<8.0` (image/runtime)
- `src/platform/tests/test_front_door_publish.py` — **new** matrix tests
- `src/platform/pyproject.toml` — coverage include stays `platformapp/**` (100%); new app must be fully covered
- Helm `deploy/charts/platform/` — **read-only** this story (no RWX, no Redis split)
- `src/atlas/` La Suite client — **read-only**; do not add REST shims

## Tasks & Acceptance

**Execution:**
- `pixi.toml` — pin Wagtail on platform-ci-test (PyPI) and python-agent-platform (conda); lock as required
- `src/platform/platformapp/front_door/` — HomePage + Wagtail apps.py + 403 copy
- `src/platform/config/settings/base.py` — Wagtail settings and INSTALLED_APPS
- `src/platform/config/urls.py` — `/cms/` admin + root `wagtail_urls`
- `src/platform/platformapp/users/provisioning.py` — attach `wagtailadmin.access_admin` to designated Wagtail-admin group
- `src/platform/tests/test_front_door_publish.py` — cover every matrix row
- If `pixi.toml` changes, `pixi project export conda-environment -e build > environment.yaml` and commit if it drifts

**Acceptance Criteria:**
- Given an editor with the Wagtail-admin IdP group, when they publish, then GET `/` shows the new body without a template-file or chart change.
- Given two clients after publish, when both GET `/`, then bodies match and the page row is in PostgreSQL.
- Given anonymous GET `/cms/`, when followed, then location is the OIDC login.
- Given a signed-in user without the group, when they GET `/cms/`, then the response explains they lack Wagtail admin.
- Given settings, when inspected, then `WAGTAILADMIN_LOGIN_URL` is the allauth OIDC URL.

## Design Notes

Admin mount: `/cms/` so Django `ADMIN_URL` and Wagtail do not collide. Catch-all `include(wagtail_urls)` is last **after** DEBUG preview routes. Admin 403 uses `front_door/cms_forbidden.html` (do not override Wagtail's `permission_denied.html`). Gate on IdP group membership, not `has_perm` (superuser bypass). `post_migrate` provisions the designated group.

Default `COMPONENT_WAGTAIL_ADMIN_GROUP=wagtail-admin`.

## Spec Change Log

## Review Triage Log

### 2026-08-24 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 8: (high 0, medium 5, low 3)
- defer: 3: (high 0, medium 0, low 3)
- reject: 14
- addressed_findings:
  - `[medium]` `[patch]` refuse `/cms/` on IdP group membership, including superusers without the group
  - `[medium]` `[patch]` dedicated `cms_forbidden.html` instead of overriding Wagtail `permission_denied.html`
  - `[medium]` `[patch]` OIDC login redirect keeps `next`; authenticated editors leaving `/cms/login/` go to admin home
  - `[medium]` `[patch]` DEBUG `/400/`…`/500/` and staticfiles registered before the Wagtail catch-all
  - `[medium]` `[patch]` `post_migrate` provisions the Wagtail-admin Django group
  - `[low]` `[patch]` admin path matching uses `path_info`
  - `[low]` `[patch]` skip blank `WAGTAIL_ADMIN_IDP_GROUP` names
  - `[low]` `[patch]` MEDIA_ROOT leak assertion always runs

## Verification

**Commands:**
- `pixi run -e platform-ci-test pytest src/platform/tests/test_front_door_publish.py src/platform/tests/test_oidc_identity.py src/platform/tests/test_health_endpoint.py -q` -- expected: pass
- `pixi run -e platform-ci-test pytest src/platform -q --ignore=src/platform/ingest` -- expected: pass (coverage 100% on `platformapp/**`)

## Auto Run Result

Status: done

Summary: Wagtail 7.4.3 is Lane 1 at `/` on the Django host. HomePage body is PostgreSQL-backed. `/cms/` is IdP-only via `WAGTAILADMIN_LOGIN_URL`. The `wagtail-admin` group maps to `wagtailadmin.access_admin`. Did not start 20.2, MinIO, Elasticsearch, console deletion, or Atlas REST.

Files changed:
- `pixi.toml` / `pixi.lock` — Wagtail on platform-ci-test and python-agent-platform; Django 5.2.15 for CI (Wagtail 7.4 requires ≥5.2)
- `src/platform/config/settings/base.py` — Wagtail apps, OIDC login URL, FTS backend, middleware
- `src/platform/config/urls.py` — `/cms/` + catch-all `/`
- `src/platform/platformapp/front_door/` — HomePage, 403 copy, group middleware
- `src/platform/platformapp/users/provisioning.py` — provision Wagtail-admin group
- `src/platform/tests/test_front_door_publish.py` — matrix tests
- this spec

Review: 8 patches (5 medium, 3 low; follow-up score 18). 3 deferred. Rejected cluster-image assertions, document/image serving (20.2), HomePage seed, and corporate-brain REST.

Verification: `pytest src/platform --ignore=src/platform/ingest` — 194 passed, 20 skipped.

Residual: first GET `/` before an editor publishes is Wagtail's welcome Page; media/RWX is 20.2.
