---title: The platform host earns its 15 factors — OIDC-delegated auth, telemetry, startup refusals, policy-as-tests, pixi-sourced deps
type: dream
owner: steward
status: archived   # 2026-08-22 — spec-platform-fifteen-factors, decomposed into the station backlog same day
archived-reason: folded-into-station-dream
---

> **Consolidated into [[pyforge-steward]]** on 2026-09-17 (one-chain-per-station steward fold; folded from `platform-fifteen-factors`).


# The platform host earns its 15 factors

## The Dream

`src/platform` is ahead on deployment (chart + OCP overlay + restricted-v2)
and engine integration, but behind on platform hygiene: no telemetry
(structlog/OTel), local-password auth (allauth signup + createsuperuser)
instead of OIDC-delegated identity, pip requirements files inside a
conda-forge factory, no startup refusal contract, no policy-as-tests. The
dream: the host earns the 15-factor bar — identity keyed on `idp_subject`
with roles derived per-authentication from IdP group claims; request_id/
trace_id on every log line with OTLP export when configured; two-stage
fail-fast misconfiguration refusals; dependency/credential/typing policy as
tests; pixi.toml as the sole dependency authority.

## Grounding

Reference implementation: millsks/django-15-factor-base (MIT — patterns and
code borrowable with notice), same cookiecutter-django lineage, verified
2026-08-22 (intake report). Local backing-services substrate: millsks/
devinfra (MIT) folds in — Keycloak realm-as-code (aud+roles claims,
reimport round-trip), the LGTM observability stack, smoke-test.sh, the
documented Redis `noeviction` rationale (LRU silently drops Celery tasks).

## Constraints / Non-goals

Convergence-checked: `spec-django-accelerator-framework` (mason) is the
TEMPLATE pipeline — different scope; this hardens the live host. Not a
re-platforming: AD-4/AD-17 topology untouched; OIDC lands beside the OCP
chain (Keycloak locally via devinfra patterns, real IdP later). Kin:
`local-ocp-hybrid-environment` (12.4's workstation substrate),
`developer-machine-bootstrap`.

## Realization log

- **2026-08-22** — Seeded from the seven-repo external analysis (`f0c695758c`);
  `spec-platform-fifteen-factors` derived under pyforge-steward and decomposed into the station
  backlog the same day (`a20192dd84`). Spec status `ready`.
- **2026-09-09 (fleet readiness pass)** — Log resumed; it had stopped at 2026-08-22 while Epic 16 finished 5/5 `done` (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`, Class B row stB / § 2.3 **C7**). Keycloak realm-as-code is real (`src/platform/compose/keycloak/realms/platform-realm.json`), but **CAP-1's production half is empty**: `production.py` carries zero OIDC/IDP overrides, `base.py:214-215` has `IDP_CLAIMS_SNAPSHOT = None` / `IDP_USERINFO = None`, and `COMPONENT_OIDC_ISSUER` / `_CLIENT_ID` / `_JWKS_URL` / `_AUDIENCE` all default to `""` at `base.py:564-580`. **The Spec's open question is answered this pass: Keycloak in-cluster, deployed by the Foundry chart, as the default profile, with the `COMPONENT_OIDC_*` seam kept as the BYO-IdP escape hatch — minted as steward Story 48.9 and co-decided with Story 49.6.** Infra-kinds check: no breach — Keycloak is a chart `Deployment` storing state in the existing PostgreSQL. Correction to § *Grounding*: the devinfra "13-service" figure is unfounded — `src/platform/compose/compose.yml` runs **7** services (postgres, redis, platform, keycloak, worker, dbgpt, mcp-host) and there is no LGTM stack anywhere; the chart's 28 templates carry no observability backing service, which is why the flagged infra-kinds collision is LOW and not live. Status unchanged.
