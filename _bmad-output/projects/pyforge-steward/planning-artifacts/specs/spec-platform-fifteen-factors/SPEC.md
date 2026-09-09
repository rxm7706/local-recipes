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
updated: "2026-09-09"
open_questions: []
  # ANSWERED 2026-09-09 (batch rows stB-B1 / C7): the OIDC provider for real deployments is
  # **Keycloak in-cluster, deployed by the Foundry chart**, as the DEFAULT profile; the
  # `COMPONENT_OIDC_*` seam (`base.py:564-580`, all defaulting to "") stays the BYO-IdP escape
  # hatch. The seam exists and is entirely unpopulated — `production.py` overrides none of it and
  # `base.py:214-215` reads `IDP_CLAIMS_SNAPSHOT = None` / `IDP_USERINFO = None`, the same fact
  # Story 49.6 exists to fix — so this is ONE deployment decision co-decided with 49.6, not two.
  # Infra-kinds check: NOT a breach of the lock — Keycloak is a chart Deployment storing its state
  # in the existing PostgreSQL, and the lock is on backing services (PostgreSQL + Redis +
  # Kubernetes). Vessel: new steward **Story 48.9** on Epic 48, beside 48.4's secrets profile —
  # never the `blocked` Epic 44.
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
  *Production profile decided 2026-09-09:* **Keycloak in-cluster, deployed by the Foundry chart**,
  is the default; the `COMPONENT_OIDC_*` seam is the BYO-IdP escape hatch. Landed as **Story
  48.9**, co-decided with Story 49.6 (which populates `IDP_CLAIMS_SNAPSHOT` / `IDP_USERINFO`,
  both `None` today at `base.py:214-215`).
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
AD-4/pap:AD-17 topology untouched; chart contract (12.1) preserved — factors
land as values/env seams, not chart rewrites; MIT notices retained on
borrowed code.

## Non-goals
The template pipeline (mason's django-accelerator-framework); the OCP
bring-up (12.4); multi-tenant anything.

## Success signal
A fresh local stack (devinfra-pattern services) boots the platform with
OIDC login, traced requests, and the policy suite green — no pip step
anywhere.
