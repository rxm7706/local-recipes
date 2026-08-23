---
title: The DB-GPT sidecar joins the chart
type: feature
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-12-1-the-vanilla-chart-with-an-ocp-overlay.md'
warnings: []
baseline_revision: 88be2d2e07c8dec2df4501b0c95256a18a331e29
final_revision: a16e8686f0687f946be2f319d5ca09e5eaf48af6
---

<intent-contract>

## Intent

**Problem:** Story 12.1 deliberately excluded the DB-GPT sidecar from the Helm chart; compose (10.5/11.2) proves the sidecar image locally, but Kubernetes deploy has no sidecar path (spec-local-ocp-hybrid-environment CAP-2).

**Approach:** Extend `src/platform/deploy/charts/platform/` with a DB-GPT sidecar Deployment (replicas 1, Recreate strategy), dedicated SQLite PVC at the resolved metadata path, internal-only Service, and `DBGPT_SIDECAR_BASE_URL` wired for platform pods — all under restricted-v2. Update `test_chart_invariants.py` so the AD-1 inventory expectation includes the sidecar image (replacing the guard that rejects a fourth image).

## Acceptance Criteria

- Given the platform sidecar image values, when `helm template` renders the core chart, then a sidecar Deployment (replicas 1, Recreate) + SQLite PVC + internal Service appear with restricted-v2 pod security on all containers.
- Given platform web/worker pods, then `DBGPT_SIDECAR_BASE_URL` resolves to the internal Service (not localhost).
- Given the chart invariant suite, then the inventory test expects postgres + redis + platform + sidecar images (exact reference matching, not substring) and the suite is green.
- Sidecar templates stay in the core chart (plain K8s); no OCP-specific kinds added.

## Boundaries & Constraints

**Always:** Reuse compose/10.5 sidecar image reference patterns. Chart never renders Secrets with credential defaults (AD-12).

**Never:** Live-cluster deploy claims (AD-16 Tier-3 attended-only). No Redis hardening (12.6) or OCP Route changes in this story.

</intent-contract>

## Code Map

- `src/platform/deploy/charts/platform/templates/` — sidecar Deployment, PVC, Service, value wiring
- `src/platform/deploy/charts/platform/values.yaml` — sidecar image + metadata path knobs
- `src/platform/tests/test_chart_invariants.py` — inventory expectation includes sidecar; update guard companions
- `src/platform/deploy/README.md` — document sidecar values (if new keys)

## Verification

- `pixi run --frozen -e platform-dev pytest src/platform/tests/test_chart_invariants.py`
- `helm template` smoke (when helm on PATH in platform-dev env)

## Auto Run Result

**Summary:** Extended the platform core Helm chart with a DB-GPT sidecar Deployment (replicas 1, Recreate strategy), dedicated SQLite PVC at the compose-resolved metadata path, internal ClusterIP Service, and `DBGPT_SIDECAR_BASE_URL` wired into web/worker pods. Updated `test_chart_invariants.py` for the four-image AD-1 inventory with sidecar/PVC/URL proofs and refreshed guard companions.

**Files changed:**
- `src/platform/deploy/charts/platform/templates/sidecar-deployment.yaml` — singleton dbgpt Deployment with restricted-v2 + `/api/health` probes
- `src/platform/deploy/charts/platform/templates/sidecar-pvc.yaml` — ReadWriteOnce SQLite PVC
- `src/platform/deploy/charts/platform/templates/sidecar-service.yaml` — internal ClusterIP Service on port 5670
- `src/platform/deploy/charts/platform/templates/_helpers.tpl` — dbgpt naming helpers + `DBGPT_SIDECAR_BASE_URL` in `platform.djangoEnv`
- `src/platform/deploy/charts/platform/values.yaml` — `sidecar.*` image/metadata/persistence/LLM passthrough knobs
- `src/platform/tests/test_chart_invariants.py` — four-image inventory, sidecar restricted-v2/PVC/Service/URL tests, guard updates
- `src/platform/deploy/README.md` — documents sidecar values (replaces 12.1 deferral note)

**Verification performed:**
- `pytest src/platform/tests/test_chart_invariants.py` — 23 passed (helm-gated proofs + ungated guard companions)
- `helm lint` on core + overlay charts — pass
- CI platform-ci on PR #640 — test, linter, detectors, container, container-dbgpt all green

**PR:** [#640](https://github.com/rxm7706/local-recipes/pull/640) — merge `a16e8686f0687f946be2f319d5ca09e5eaf48af6`
