---
title: Startup refuses misconfiguration, two-stage and named
type: feature
created: '2026-08-23'
status: done
shipped_ref: '6e157b892b55f6dd7aa54b48b27f30cb237bbca4'
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: 936b47178a0d62e49e40a87fa8db706ff88921c8
followup_review_recommended: true
deferred:
  - summary: >-
      Operator-facing deploy README / NOTES still omit COMPONENT_RUNTIME and
      the invalid DJANGO_ADMIN_URL set beyond the chart values change.
    evidence: |-
      Blind-hunter noted docs/NOTES still describe required env without CAP-3
      locality or admin-URL validity rules. Chart default was patched; prose
      docs were not fully rewritten this story.
    location: >-
      src/platform/deploy/README.md
    severity: medium
  - summary: >-
      is_serving_process / COMPONENT_PROCESS locality helpers ship without
      dedicated tests (unused by CAP-3 stage-2 conditions yet).
    evidence: |-
      Blind-hunter / verification-gap: PROCESS_ENV_VAR is declared for later
      stage-2 DB conditions; CAP-3 does not depend on it. Low risk until
      those conditions land.
    location: >-
      src/platform/config/locality.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** Platform boot can proceed past missing/invalid required settings into import side effects (CAP-3 / `spec-platform-fifteen-factors`). Operators get opaque mid-boot failures instead of a named setting + remedy.

**Approach:** Add a two-stage fail-fast validation contract before app import side effects: stage names each missing/invalid required setting and its remedy. Fixture-prove every required key. Borrow MIT django-15-factor-base patterns with notices if useful. Do not implement 16.3–16.5 (telemetry, policy-as-tests, OIDC).

## Acceptance Criteria

- Missing/invalid required setting → boot fails in a validation stage that **names the setting and its remedy** before app import side effects.
- Fixture coverage for each required key (absence / invalid cases as appropriate).
- Two-stage shape documented in code/docs (validation vs later boot).
- Related platform / steward tests green.
- Does not implement 16.3–16.5, steward 12-7, or Epic 17.

## Boundaries & Constraints

**Never:** AD-4/pap:AD-17 topology or chart 12.1 rewrites (factors as seams only). Never `scripts/bmad-switch`. Never auto-merge. Finalize steward ledger only. Do not touch marshal. Skip 12-7 forever.

</intent-contract>

## Code Map

- `src/platform/config/settings/` (base/local/production) — required env contract
- `src/platform/config/startup/` — two-stage refusal package (stage_one / stage_two)
- `src/platform/config/locality.py` — `COMPONENT_RUNTIME` fail-closed locality
- Platform boot entrypoints: `manage.py` / ASGI/WSGI / celery / docs conf
- Tests under `src/platform/tests/test_startup_*.py` proving each required key

## Verification

- Per-key fixtures: fail names setting + remedy; happy path boots
- `pixi run --frozen -e pyforge-steward` / platform test env related pytest green
- CI detectors / linter / package tests

## Review Triage Log

### 2026-08-23 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 10: (high 4, medium 6, low 0)
- defer: 2: (high 0, medium 1, low 1)
- reject: 4
- addressed_findings:
  - `[high]` `[patch]` Containerfile collectstatic under production settings + `admin/` — set `COMPONENT_RUNTIME=local` for the build RUN
  - `[high]` `[patch]` compose platform/worker still used `admin/` against production settings — set `COMPONENT_RUNTIME: local`
  - `[high]` `[patch]` Helm `adminUrl: admin/` refused by stage-1 — default to `platform-admin/`
  - `[high]` `[patch]` celery_app local leaf missing locality pairing — mirror manage/ASGI `COMPONENT_RUNTIME=local` setdefault
  - `[medium]` `[patch]` docs/conf.py django.setup under local leaf — setdefault `COMPONENT_RUNTIME=local`
  - `[medium]` `[patch]` expand invalid admin URLs (`/admin`, `/admin/`, casefold)
  - `[medium]` `[patch]` stage-2 DEBUG check uses truthiness, not identity-with-True
  - `[medium]` `[patch]` production.py wiring assertion (source file contains refuse/run_stage_one)
  - `[medium]` `[patch]` UsersConfig.ready runtime sentinel via `apps.get_app_config(...).ready()`
  - `[medium]` `[patch]` stage-2 skips refusals when local (DEBUG + local settings)

## Auto Run Result

Status: done

### Summary
CAP-3 two-stage startup refusals for `src/platform`: stage 1 names missing/invalid required env (`DJANGO_SECRET_KEY`, `DJANGO_ADMIN_URL`) with remedies before django-environ mid-import failures; stage 2 refuses deployed `DEBUG` and local-settings escape from `UsersConfig.ready()`. Fail-closed `COMPONENT_RUNTIME` locality; MIT notices from django-15-factor-base patterns.

### Files changed
- `src/platform/config/locality.py` — fail-closed locality helpers
- `src/platform/config/startup/` — stage_one / stage_two / package docs
- `src/platform/config/settings/production.py` — early refuse + leaf `run_stage_one`
- `src/platform/platformapp/users/apps.py` — stage-2 owner hook
- `src/platform/manage.py`, `config/asgi.py`, `config/celery_app.py`, `docs/conf.py` — local runtime setdefault when local leaf
- `src/platform/conftest.py` — pytest defaults to local
- `src/platform/Containerfile`, `compose/compose.yml`, `deploy/charts/platform/values.yaml` — keep build/compose/chart coherent with refusals
- `src/platform/tests/test_startup_*.py` — fixture coverage

### Review findings
- Patches applied: 10 (4 high, 6 medium) → `followup_review_recommended: true` (any high patch)
- Deferred: 2 (operator docs; unused process-type helper tests)
- Rejected: noise / pre-existing ASGI default-to-local; ledger finalize is a station post-step; dual refuse call sites intentional; WSGI production default correct without local setdefault

### Verification
```
cd src/platform && pixi run -e platform-ci-test -- python -m pytest \
  tests/test_startup_required_settings.py \
  tests/test_startup_stage_two.py \
  tests/test_startup_locality.py -q
# → 27 passed
```

### Residual risks
- Live production-leaf import still not subprocess-tested (source wiring asserted only).
- Real OCP installs must leave `COMPONENT_RUNTIME` unset and set a non-placeholder `DJANGO_ADMIN_URL` (chart default now `platform-admin/`).
