---
title: 'Story 26.2: Manifests carry secret references only'
type: feature
created: '2026-08-25'
status: done
baseline_revision: 'f3507a79d63'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-unifying-strategy-2026-08-24/prd.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-unifying-strategy-2026-08-24/ARCHITECTURE-SPINE.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** FR-32 / canopy AD-19 require that rendered Helm (and the OCP overlay) carry Secret *names and keys*, never secret *values*. Chart templates already wire `secretKeyRef` (parent AD-12), but nothing fails a render when a value is injected — a git-diff of the chart could still leak credentials.

**Approach:** Add a check over `helm template` YAML that fails if a secret value appears (canary `--set-string` plus secret-named env `value:`). Pods keep env / secret mounts. The app must not call a secrets HTTP API. Vault injector, secrets CSI, and an extra secrets sidecar stay out of this chain.

## Boundaries & Constraints

**Always:** Success test is rendered Helm/Kustomize contains names and keys, never values. Cite FR-32, canopy AD-19, parent AD-12. Spec lives at `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/` literally. `BMAD_ACTIVE_PROJECT=pyforge-steward`. Guard-removed companions (Story 9.6) for every assertion helper.

**Block If:** Implementation would add Vault-in-app, Vault injector, secrets CSI, or an extra secrets sidecar (parent AD-14 / fourth kind — needs a dated Dream first).

**Never:** Start 26.3, 26.4, 27-x, or 28-1. Author OpenFeature or Liquibase recipes. Cluster secret-manager wiring (External Secrets) inside the platform image. `import pyforge` under `src/platform/`. `scripts/bmad-switch`. Other stations' ledgers.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clean render | Default `helm template` of core chart | Secret-named env uses `secretKeyRef`; no `kind: Secret`; canary absent | No error |
| Canary values | `--set-string` injects a unique secret string into unused chart-value paths (`postgres.auth.password`, `django.secretKey`, `sidecar.llm.apiKey`) | Rendered YAML does not contain the canary | Assertion fails if it appears |
| Inline env value | Synthetic pod: `DJANGO_SECRET_KEY` has `value:` not `valueFrom` | Same helper as the real proof raises | AssertionError |
| Rendered Secret | Synthetic docs include `kind: Secret` with `stringData` | Helper raises | AssertionError |
| Vault / CSI / sidecar | Synthetic pod: vault annotation, CSI secrets-store volume, or `vault-agent` container | Helper raises | AssertionError |
| Secrets HTTP API | Platform app `.py` (not tests) imports `hvac` / secret-manager client | Helper raises | AssertionError |

</intent-contract>

## Code Map

- `src/platform/deploy/charts/platform/` -- AD-12 chart: `existingSecret` name only; `platform.djangoEnv` / postgres / redis / sidecar `secretKeyRef`; chart must not grow `kind: Secret` or credential defaults
- `src/platform/deploy/charts/platform/templates/_helpers.tpl` -- `platform.existingSecretName`, `platform.djangoEnv` (DJANGO_SECRET_KEY, DATABASE_URL, REDIS_PASSWORD via `secretKeyRef`; REDIS_*_URL uses `$(REDIS_PASSWORD)` expansion)
- `src/platform/deploy/overlays/ocp/` -- thin Route overlay; same secret contract via core chart
- `src/platform/tests/test_chart_invariants.py` -- reuse `_render`, `_pod_specs_by_component`, `requires_helm`; add 26.2 helpers + helm proof + ungated guard-removed companions
- `src/platform/config/`, `src/platform/platformapp/` -- read-only: no secrets HTTP client; consume env only

## Tasks & Acceptance

**Execution:**
- `src/platform/tests/test_chart_invariants.py` -- helpers + helm/canary proof + guard-removed companions + app-source HTTP-API scan
- `src/platform/deploy/charts/platform/values.yaml` -- comment that values hold names/keys only (canopy AD-19); no credential defaults

**Acceptance Criteria:**
- Given `helm template` (or overlay) output, when the secret check runs, then it fails if a secret *value* appears.
- Given pods, when they start, then they consume env or secret file mounts; the app does not call a secrets HTTP API.
- Given this chain, when charts are reviewed, then Vault injector / CSI / extra secrets sidecar is absent.

## Spec Change Log

## Review Triage Log

### 2026-08-25 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 0, low 2)
- defer: 1: (high 0, medium 0, low 1)
- reject: 4: (high 0, medium 1, low 3)
- addressed_findings:
  - `[low]` `[patch]` ruff S105/PT018/PLC0207/B007 on the canary constant and helpers
  - `[low]` `[patch]` split secretKeyRef name vs key assertions so a missing key is not masked
  - `[low]` `[defer]` no Secret volume file-mount in the chart today — delivery is env `secretKeyRef`; adding unused volumes is speculative (parent AD-12 allows either)
  - `[reject]` Kustomize render — this chain ships Helm (+ OCP Helm overlay), not Kustomize
  - `[reject]` wire External Secrets / cluster manager — canopy AD-19, out of chain
  - `[reject]` scan compose.yml placeholders — not a pod spec
  - `[medium]` `[reject]` "must add Vault to prove the helper" — guard-removed companions already inject vault/CSI/sidecar synthetics

## Design Notes

Canary paths are values the templates must *not* interpolate. `redis.password` is not a canary path — `--set redis.password` would smash the `redis:` map. Secret-named env vars (`DJANGO_SECRET_KEY`, `DATABASE_URL`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `DBGPT_LLM_API_KEY`, plus names matching PASSWORD/SECRET/TOKEN/API_KEY) must use `valueFrom.secretKeyRef` and must not set `value`. `REDIS_BROKER_URL` with `$(REDIS_PASSWORD)` is a reference expansion, not a value. Cluster managers may materialize Kubernetes Secrets outside the image; this story does not wire them.

## Verification

**Commands:**
- `export BMAD_ACTIVE_PROJECT=pyforge-steward`
- `pixi run -e platform-dev pytest src/platform/tests/test_chart_invariants.py -q --override-ini 'addopts=--import-mode=importlib' -k 'secret_ref or secret_value or secrets_http or vault_csi or chart_values_check'` -- expected: 10 passed

## Auto Run Result

Status: done

Summary: Helm-render check fails if a secret value (canary or inline env) appears; pods keep secretKeyRef; no secrets HTTP API; no Vault/CSI/sidecar.

Files changed:
- `src/platform/tests/test_chart_invariants.py` -- 26.2 helpers, helm/canary proof, guard-removed companions
- `src/platform/deploy/charts/platform/values.yaml` -- AD-19 comment
- this spec

Review: 2 low patches, 1 deferred (unused secret volumes), 4 rejected.

Verification: 10 passed under platform-dev (including `test_rendered_manifests_carry_secret_refs_never_secret_values`).
