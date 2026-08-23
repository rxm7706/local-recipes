---
title: The DB-GPT sidecar joins the chart
type: feature
created: '2026-08-23'
status: ready
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-12-1-the-vanilla-chart-with-an-ocp-overlay.md'
warnings: []
baseline_revision: f8c8df5469
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
