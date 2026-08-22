---
title: The platform host earns its 15 factors — OIDC-delegated auth, telemetry, startup refusals, policy-as-tests, pixi-sourced deps
type: dream
owner: steward
status: specified   # 2026-08-22 — spec-platform-fifteen-factors, decomposed into the station backlog same day
---

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
