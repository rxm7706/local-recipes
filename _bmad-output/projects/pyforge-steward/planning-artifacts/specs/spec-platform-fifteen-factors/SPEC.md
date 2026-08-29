---
spec: platform-fifteen-factors
status: ready
owner-dream: docs/dreams/platform-fifteen-factors.md
surface:
  # Story 16.1 (CAP-5): pixi becomes the sole dependency authority, retiring
  # src/platform/requirements/*.txt. This CI gate is that story's own governed file.
  - scripts/platform_ci_test_requirements_check.py
companions: []
sources:
  - ../../../../../../docs/dreams/platform-fifteen-factors.md
  - ../../../../../../docs/intake/external-repos-analysis-2026-08-22/report.md
open_questions:
  - "OIDC provider for real deployments (Keycloak is the local substrate) — decide before CAP-1's production story."
---

# SPEC — The platform host earns its 15 factors

## Why
src/platform leads on deployment, lags on hygiene: local-password auth, no
telemetry, pip requirements inside a conda-forge factory, no startup
refusals, no policy-as-tests. MIT reference implementations exist
(django-15-factor-base; devinfra as the local backing-services substrate).

## Capabilities
- **CAP-1 — OIDC-delegated identity.** Identity keyed on `idp_subject`;
  is_staff/superuser derived per-authentication from IdP group claims;
  no local passwords; Keycloak realm-as-code locally (devinfra pattern).
  *Success:* login flows through the IdP end-to-end locally; createsuperuser
  retired from the docs path.
- **CAP-2 — telemetry.** structlog + OTel in every process; request_id/
  user_id/trace_id on every line; OTLP export only when endpoint set.
  *Success:* one request traces web→Celery with correlated ids.
- **CAP-3 — startup refusals.** Two-stage fail-fast misconfiguration
  contract. *Success:* each required setting's absence names itself at boot.
- **CAP-4 — policy-as-tests.** Dependency/credential-surface/typing/coverage
  policies as tests. *Success:* the suite reds on policy drift.
- **CAP-5 — pixi-sourced deps.** requirements/*.txt retired; pixi.toml the
  single authority. *Success:* CI + images build from pixi alone.

## Constraints
AD-4/AD-17 topology untouched; chart contract (12.1) preserved — factors
land as values/env seams, not chart rewrites; MIT notices retained on
borrowed code.

## Non-goals
The template pipeline (mason's django-accelerator-framework); the OCP
bring-up (12.4); multi-tenant anything.

## Success signal
A fresh local stack (devinfra-pattern services) boots the platform with
OIDC login, traced requests, and the policy suite green — no pip step
anywhere.
