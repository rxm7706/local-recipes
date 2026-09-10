---
title: "Story 48.9: OIDC default profile — Keycloak in-cluster, BYO seam kept"
type: story
created: 2026-09-10
baseline_revision: 64ea7659d022c4d2c97938c6ac39e936d65c27c4
status: ready-for-dev
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-platform-fifteen-factors/SPEC.md
  - src/platform/config/settings/base.py
  - src/platform/config/settings/production.py
  - src/platform/config/startup/stage_one.py
  - src/platform/compose/compose.yml
  - src/platform/compose/keycloak/realms/platform-realm.json
  - src/platform/deploy/charts/platform/values.yaml
  - src/platform/deploy/charts/platform/templates/_helpers.tpl
  - src/platform/deploy/README.md
  - docs/reference/enterprise-deployment.md
warnings: []
deferred: []
declared_low_risk: false
---

# Story 48.9: OIDC default profile — Keycloak in-cluster, BYO seam kept

<intent-contract>

## Intent

**Problem:** The `COMPONENT_OIDC_*` seam exists but is entirely unpopulated in production — `base.py:569-590` defaults all four to `""`, `production.py` overrides none, and stage-1 already refuses boot without `COMPONENT_OIDC_ISSUER`, `COMPONENT_OIDC_JWKS_URL`, and `COMPONENT_OIDC_AUDIENCE`. Local dev uses compose Keycloak; deployed clusters have no default IdP.

**Approach:** Promote Keycloak to an in-cluster chart `Deployment` + `Service` (realm-as-code ConfigMap, state in the existing PostgreSQL) as the **default** OIDC profile. Wire `COMPONENT_OIDC_*` through `platform.djangoEnv` for every platform-image pod. Keep an explicit **`oidc.profile: byo`** values path that skips Keycloak and reads issuer/JWKS/client from values — the BYO-IdP escape hatch. Document both profiles in `enterprise-deployment.md`.

## Boundaries & Constraints

**Always:** AD-12 holds — chart never renders `kind: Secret`; `COMPONENT_OIDC_CLIENT_SECRET` and Keycloak admin/DB passwords arrive via `existingSecret` secretKeyRef only. Keycloak is a chart `Deployment`, not a new infra kind — state lives in existing PostgreSQL (separate `keycloak` database). Realm JSON mirrors compose groups/clients/mappers. NetworkPolicy: web/worker egress to keycloak; keycloak ingress from web (+ ingress controller namespace for browser login); keycloak egress to postgres + DNS. Co-decision with Story 49.6 is naming-only here — do **not** set `IDP_CLAIMS_SNAPSHOT` / `IDP_USERINFO` (49.6 owns that). Update AD-1 image inventory test to include Keycloak image (sixth workload image).

**Never:** No SaaS IdP as default. No Vault HTTP clients. No fourth backing-service kind beyond PostgreSQL + Redis + Kubernetes. No hand-edit of `sprint-status-ledger.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| BUNDLED_DEFAULT | `oidc.profile=bundled` (default), secret holds OIDC + Keycloak keys | Keycloak Deployment/Service/Ingress render; platform pods get computed `COMPONENT_OIDC_*` env | Missing secret keys fail render via `required` |
| BYO_PROFILE | `oidc.profile=byo`, explicit `oidc.byo.issuer/jwksUrl/clientId` | No Keycloak workloads; platform pods get BYO env from values | Empty BYO fields fail `helm template` |
| STAGE1_BOOT | Deployed settings module, OIDC env wired | `refuse_required_settings()` passes when chart env present | Existing stage-1 tests unchanged |
| REALM_REDIRECTS | `ingress.host=platform.internal` | Realm client redirect URIs include `https://platform.internal/*` | N/A — configmap content |

</intent-contract>

## Code Map

- `src/platform/deploy/charts/platform/values.yaml` — add `oidc` (profile, byo block, claim env defaults) and `keycloak` (image, ingress host, db name, resources)
- `src/platform/deploy/charts/platform/templates/_helpers.tpl` — `platform.keycloak.fullname`, `platform.oidcEnv`, `platform.networkPolicy.egressToKeycloak`, update `webEgressRules`/`workerEgressRules`
- `src/platform/deploy/charts/platform/templates/keycloak-*.yaml` — Deployment, Service, Ingress (bundled only), realm ConfigMap, optional db-init Job hook
- `src/platform/deploy/charts/platform/templates/networkpolicy-*.yaml` — keycloak ingress/egress policies when bundled
- `src/platform/deploy/charts/platform/templates/NOTES.txt` — OIDC + secret key additions
- `src/platform/deploy/overlays/eso/externalsecret-platform-secrets.example.yaml` — map `COMPONENT_OIDC_CLIENT_SECRET`, `KEYCLOAK_ADMIN_PASSWORD`
- `src/platform/deploy/README.md` — secret keys table + OIDC profile pointer
- `docs/reference/enterprise-deployment.md` — new § OIDC identity profile (bundled Keycloak vs BYO)
- `src/platform/tests/test_chart_invariants.py` — Story 48.9 proofs; extend `_default_image_references`, `_REQUIRED_PLATFORM_SECRET_KEYS`, egress tests

## Tasks & Acceptance

**Execution:**
- `src/platform/deploy/charts/platform/values.yaml` — `oidc` + `keycloak` defaults (bundled profile, Keycloak 26.4.0 image matching compose)
- `src/platform/deploy/charts/platform/templates/_helpers.tpl` — OIDC env fragment wired into `platform.djangoEnv`
- `src/platform/deploy/charts/platform/templates/keycloak-deployment.yaml` — postgres-backed Keycloak with realm import
- `src/platform/deploy/charts/platform/templates/keycloak-service.yaml` — ClusterIP :8080
- `src/platform/deploy/charts/platform/templates/keycloak-ingress.yaml` — TLS host for browser OIDC (bundled)
- `src/platform/deploy/charts/platform/templates/keycloak-realm-configmap.yaml` — realm-as-code with ingress-aware redirect URIs
- `src/platform/deploy/charts/platform/templates/keycloak-db-init-job.yaml` — hook Job creates `keycloak` database (bundled)
- `src/platform/deploy/charts/platform/templates/networkpolicy-keycloak.yaml` — ingress/egress for keycloak component
- `src/platform/deploy/overlays/eso/externalsecret-platform-secrets.example.yaml` — OIDC + Keycloak secret keys
- `docs/reference/enterprise-deployment.md` — OIDC profile section
- `src/platform/deploy/README.md` — document new secret keys and default profile
- `src/platform/tests/test_chart_invariants.py` — Story 48.9 AC tests

**Acceptance Criteria:**
- Given `helm template` with default values, when manifests render, then a Keycloak Deployment and Service exist and every platform-image pod (`web`, `worker`, `beat`, `migrate`, `liquibase`, consume-events) carries non-empty `COMPONENT_OIDC_ISSUER`, `COMPONENT_OIDC_JWKS_URL`, `COMPONENT_OIDC_CLIENT_ID`, `COMPONENT_OIDC_AUDIENCE`, and secretKeyRef `COMPONENT_OIDC_CLIENT_SECRET`
- Given `oidc.profile=byo` with explicit issuer/jwks/clientId, when templates render, then no Keycloak Deployment exists and platform pods still carry the BYO OIDC env
- Given `docs/reference/enterprise-deployment.md`, when an operator reads the OIDC section, then bundled Keycloak-in-cluster is named as default and BYO via `COMPONENT_OIDC_*` / `oidc.profile=byo` is documented
- Given `pixi run -e platform-dev pytest src/platform/tests/test_chart_invariants.py -k story_48_9 -q`, when tests run, then all Story 48.9 tests pass

## Verification

**Commands:**
- `pixi run -e platform-dev pytest src/platform/tests/test_chart_invariants.py -k story_48_9 -q` — expected: all pass
- `pixi run -e platform-dev helm lint src/platform/deploy/charts/platform` — expected: 0 failures
- `pixi run -e platform-dev pytest src/platform/tests/test_startup_required_settings.py -q` — expected: all pass

**Manual checks (if no CLI):**
- Inspect rendered `platform.djangoEnv` for OIDC keys on web pod

## Spec Change Log

## Review Triage Log

## Design Notes

Keycloak uses the migration-role postgres credentials (`POSTGRES_PASSWORD`) against database `keycloak` — same lock, no new secret kind. Browser-facing issuer URL uses `https://{{ keycloak.ingress.host }}/realms/platform`; in-cluster JWKS may use the Service DNS for pod-to-IdP reachability during login callback validation. Realm client secret in cluster must match `COMPONENT_OIDC_CLIENT_SECRET` in `platform-secrets` (operator-generated, never committed).
