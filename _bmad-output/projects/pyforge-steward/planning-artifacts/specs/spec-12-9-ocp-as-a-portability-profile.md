---
title: OCP as a portability profile
type: infra
created: '2026-08-23'
status: ready
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/docs/dreams/ocp-as-a-portability-profile.md'
  - '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-12-1-the-vanilla-chart-with-an-ocp-overlay.md'
warnings: []
baseline_revision: 11069e182e
---

<intent-contract>

## Intent

**Problem:** Story 12.1 OCP overlay exists but Platform CI has no OCP portability proof — AD-11 half open; deploy README still says no live OCP verification.

**Approach:** Add optional `ocp-portability-smoke` job to `.github/workflows/platform-ci.yml` (default off, workflow_dispatch / repo var), mirroring gke-portability-smoke pattern: real OpenShift API (CRC/OpenShift Local), internal-registry push, helm install core+overlay, curl via admitted Route. Update deploy README honesty line.

## Acceptance Criteria

- Optional CI job `ocp-portability-smoke` exists, default off, fan-in from build-platform-image when enabled.
- Job uses OCP overlay + Route; no kind; curl through router not port-forward.
- Consumes cluster-bringup-facts.md registry pattern from Story 12.4.
- Does not claim Story 12.7 attended closeout scope.
- PR carries maintenance label.

## Boundaries & Constraints

**Never:** Replace Story 12.7 live-cluster verification. No chart contract changes beyond CI wiring.

</intent-contract>

## Code Map

- `.github/workflows/platform-ci.yml` — new optional job + inputs/vars
- `src/platform/deploy/README.md` — honesty line update
- `.github/workflows/README` or platform-ci comments if pattern docs live there

## Verification

- Workflow YAML valid (detectors/linter CI)
- Mirror gke-portability-smoke structure; job skipped when var unset
