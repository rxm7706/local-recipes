---
title: "Broker TLS is verified"
type: "fix"
created: "2026-09-02"
status: "ready-for-dev"
updated: "2026-09-02"
baseline_commit: "58ee07a0"
severity: "HIGH"
context:
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/resilience-invariants.md"
  - "src/platform/config/settings/base.py"
  - "src/platform/config/startup/stage_one.py"
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `CELERY_BROKER_USE_SSL = {"ssl_cert_reqs": ssl.CERT_NONE}` whenever the broker URL
is `rediss://`. Under an enterprise TLS mandate this looks encrypted and is
MITM-able. Red-team **X-2**, directive **R-14**.

**Approach:** `ssl_cert_reqs = CERT_REQUIRED` with `ssl_ca_certs` from the corporate bundle
(`truststore` / `SSL_CERT_FILE`) for both the Celery broker and the result
backend; `CERT_NONE` is permitted only under `COMPONENT_RUNTIME=local` and the
production settings check refuses it.

## Acceptance Criteria

- Given production settings and a `rediss://` broker, when loaded, then `ssl_cert_reqs` is `CERT_REQUIRED` and `ssl_ca_certs` points at the configured bundle.
- Given `COMPONENT_RUNTIME` unset (deployed) and `CERT_NONE` requested via env, when `manage.py check` runs, then stage-1 refuses.
- Given the laptop profile, when loaded, then `CERT_NONE` still works for a self-signed local Redis.

## Boundaries & Constraints

**Always:** Write under `_bmad-output/projects/pyforge-steward/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`.
Ledger key `41-4-broker-tls-is-verified`. Host never imports `pyforge.*`. Truststore first; explicit bundle path second; never `verify=False` semantics in a deployed profile.

**Block If:** Implementation would add a flag that re-enables `CERT_NONE` in production.

**Never:** `CERT_NONE` outside `COMPONENT_RUNTIME=local`.

</intent-contract>

## Tasks

- [ ] Settings change + stage-1 check
- [ ] Tests: production/local matrix
- [ ] Ledger `41-4-broker-tls-is-verified` → `review` then `done` via `sprint-ledger-sync`.

## Verification

`src/platform/tests/test_startup_required_settings.py` + a new settings test; `pixi run -e python-agent-platform`.

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 41.4). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.
