---
spec: ocp-as-a-portability-profile
status: ready
owner-dream: docs/dreams/ocp-as-a-portability-profile.md
surface: []   # populated as Story 12.9 lands (platform-ci.yml ocp-portability-smoke, deploy/README.md honesty line)
companions:
  - ../spec-local-ocp-hybrid-environment/cluster-bringup-facts.md
  - ../spec-12-2-gke-as-a-portability-profile.md
sources:
  - ../../../../../../docs/dreams/ocp-as-a-portability-profile.md
assumptions:
  - "CRC 2.63.0 / OpenShift 4.22.7 and the internal-registry push commands
    in cluster-bringup-facts.md are the baseline this job copies."
updated: "2026-09-09"
open_questions:
  # The RUNNER-CLASS half is ANSWERED BY IMPLEMENTATION (batch row stB-B2(a)): `ubuntu-latest`
  # with the CRC action (`.github/workflows/platform-ci.yml:1251`), a 90-minute budget and a CRC
  # internal-registry push. The residual is not the class but the PROOF:
  - "No `ocp-portability-smoke` run has ever started a cluster. `gh variable list` returns only
    `ACTIONS_ENABLED=false` and `gh secret list` has no `CRC_PULL_SECRET`, so the job hard-fails at
    `platform-ci.yml:1265-1272` — CAP-2 ('a green run records those assertions') and CAP-3 ('the
    first implementation proves the chosen runner class') are unmet. FUNDED 2026-09-09 (batch rows
    stB-B2(b) / C14): the operator sets `CRC_PULL_SECRET` plus
    `PLATFORM_CI_OCP_PORTABILITY_SMOKE` and dispatches once, BEFORE Story 44.10. What remains open
    is only the timing of that dispatch."
---

# SPEC — OpenShift runs as a CI portability profile

## Why

The platform's first deployment target is Red Hat OpenShift. Story 12.1
shipped the vanilla Kubernetes core chart and a thin OCP Route overlay;
Story 12.2 proved the vanilla Ingress path on a GKE-shaped `kind` profile;
Story 12.3 proved air-gap parity. pap:AD-11's OCP half remains honestly open:
`deploy/README.md` still names "No OCP live-cluster verification in this
repo," and Platform CI has no `ocp-portability-smoke` job. This Spec
closes that gap the same way 12.2 closed GKE: an optional CI profile on
a real OpenShift API, overlay-only. Owner: **steward**. Vehicle: existing
**Story 12.9** (Epic 12 extension — no new epic).

## Capabilities

- **CAP-1 — Optional OCP smoke job.** *Intent:* Platform CI gains
  `ocp-portability-smoke`, default **off** (repo variable
  `PLATFORM_CI_OCP_PORTABILITY_SMOKE=true` or `workflow_dispatch`),
  reusing `build-platform-image`'s artifact (P1 fan-in), helm/kubectl
  from `platform-dev` (pap:AD-16), CRC / OpenShift Local as a named
  system-level exception — never `kind`. *Success:* the job exists and
  is skippable; a dispatch with the variable set reaches cluster-up or
  fails naming why the cluster never started.
- **CAP-2 — Route and SCC proof.** *Intent:* the smoke asserts Route
  admission, edge-terminated HTTPS to `/ht/` and `/admin/login/`,
  migrate-hook completion, and that postgres/redis pods run without
  fixed `runAsUser` under SCC-assigned UIDs — never a `port-forward` or
  a direct Service curl. *Success:* a green run records those
  assertions; a dated note in the 12.1 orbit names any postgres/redis
  image contingency (official vs RH/bitnami).
- **CAP-3 — Runner honesty.** *Intent:* the first implementation proves
  the chosen runner class (GitHub-hosted Ubuntu via
  `crc-org/crc-github-action`, or a labeled self-hosted RHEL/Fedora
  runner) before claiming OCP verification. *Success:* the job never
  reports green on a cluster that never started; an unsupported OS is a
  named skip or a documented self-hosted runner, not a silent pass.

## Constraints

- pap:AD-11: core chart unchanged; OCP kinds only via the existing overlay
  (`overlays/ocp/core-overrides.yaml` + `platform-ocp` Route chart).
- pap:AD-16: helm/kubectl from pixi; CRC/`oc` are explicit named system
  exceptions alongside `kind`.
- pap:AD-15: paths-filtered Platform CI; non-`recipes/` PRs carry the
  `maintenance` label.
- Default off on PR push — CRC is slow (~30–90 min), disk-heavy
  (~35 GiB), and needs `CRC_PULL_SECRET`.
- One engine (Docker) for CRC — same rationale as 12.2; do not
  duplicate the `container` job's docker+podman matrix.

## Non-goals

- Replacing Story 12.7's attended Tier-3 record (PVC edge cases, sidecar
  inventory after 12.5, Redis hardening after 12.6). This job proves the
  portability profile, not every hybrid-environment CAP.
- Production/cluster-specific networking, external DNS, or corporate
  mirror posture.
- Making every PR pay CRC cost. Nightly-only scheduling is an acceptable
  follow-up if PR-default remains off.

## Success signal

An operator (or `workflow_dispatch`) can flip
`PLATFORM_CI_OCP_PORTABILITY_SMOKE=true` and watch Platform CI prove
Route admission + SCC-assigned UIDs through the cluster router on a
cluster that actually started — or see a named skip/failure if it did
not. `deploy/README.md`'s honesty line is replaced by a dated
verification note. Story 12.7 remains the attended closeout.

## First green run is funded — 2026-09-09

**Decision (operator, batch rows stB-B2(b) / C14): fund ONE green `ocp-portability-smoke` run
BEFORE Story 44.10.** Set `CRC_PULL_SECRET` plus `PLATFORM_CI_OCP_PORTABILITY_SMOKE` and dispatch
once.

Why it cannot wait: **44.10 disables this repo's CI.** Without that run, CAP-2 and CAP-3 are never
provable in *either* repo and `deploy/README.md:134` stays permanently conditional. The rejected
alternative was to rewrite CAP-2/CAP-3 as template-only — the "criterion says fixture" shape the
realization gate exists to catch.

This run is also the gate on any Intelligence-Hub NIC-profile story: two unproven profiles side by
side would double the claim with zero evidence (`spec-intelligence-hub` § Constraints).
