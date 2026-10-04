---
title: OpenShift runs as a CI portability profile — the OCP overlay proven on a real cluster
type: dream
owner: steward
status: archived   # 2026-08-24 — spec-ocp-as-a-portability-profile (CAP-1..3); decomposed as steward Story 12.9 (backlog — no ocp-portability-smoke job yet)
archived-reason: folded-into-station-dream
---

> **Consolidated into [[pyforge-steward]]** on 2026-09-17 (one-chain-per-station steward fold; folded from `ocp-as-a-portability-profile`).


# OpenShift runs as a CI portability profile — the OCP overlay proven on a real cluster

## The Dream

The platform's **first deployment target is Red Hat OpenShift** — not merely
as a chart template, but as something Platform CI can prove automatically.
Story 12.1 shipped a vanilla Kubernetes core chart and a thin OCP Route overlay;
Story 12.2 proved the vanilla Ingress path on a GKE-shaped `kind` profile;
Story 12.3 proved air-gap parity. The OCP half of AD-11's portability clause
remains honestly open: `deploy/README.md` still names "No OCP live-cluster
verification in this repo."

This Dream closes that gap the same way 12.2 closed the GKE gap: an optional
Platform CI job spins up a **real OpenShift API** (OpenShift Local / CRC — not
`kind`, which cannot admit Routes or enforce `restricted-v2` SCC), pushes the
shared platform image through the internal-registry pattern, installs the core
chart with `overlays/ocp/core-overrides.yaml` plus the Route overlay, and
curls the app through the cluster router — never a `port-forward` or a direct
Service curl. OCP is a **profile**, not a second implementation: the overlay
Story 12.1 already owns stays the only OCP-specific surface.

## What it looks like when real

- `ocp-portability-smoke` exists in `.github/workflows/platform-ci.yml`, default
  **off** on PRs (same opt-in pattern as `gke-portability-smoke` and
  `air-gap-parity`): repo variable `PLATFORM_CI_OCP_PORTABILITY_SMOKE=true` or
  a `workflow_dispatch` toggle.
- The job reuses `build-platform-image`'s artifact (P1 fan-in), installs helm/kubectl
  from `platform-dev` (AD-16), and treats CRC/OpenShift Local as a named
  system-level exception alongside `kind`.
- Smoke assertions prove: Route admission, edge-terminated HTTPS to `/ht/` and
  `/admin/login/`, migrate hook completion, and that postgres/redis pods run
  without fixed `runAsUser` under SCC-assigned UIDs.
- A dated verification note in the 12.1 orbit records whatever contingency the
  run needed (official postgres/redis images vs. RH/bitnami fallbacks) — kin to
  Story 12.7's attended checklist, but automated and repeatable.

## What is real

- Story 12.1 overlay (`src/platform/deploy/overlays/ocp/`) and invariant tests
  (`test_chart_invariants.py`) — template/lint only, no live cluster.
- Story 12.2 `gke-portability-smoke` — the sibling CI pattern to mirror
  (optional job, shared image artifact, no `--wait` helm install, migrate wait
  before ORM assertion).
- Story 12.3 `air-gap-parity` — orthogonal; does not substitute for OCP Route/SCC proof.
- `spec-local-ocp-hybrid-environment` + Story 12.4 bring-up facts — the internal-registry
  push commands and CRC 2.63.0 / OpenShift 4.22.7 baseline this job copies;
  the full hybrid SDLC (BMAD wiring, dlt, DB-GPT sidecar) stays out of scope.
- No automated OCP job in Platform CI today.

## Constraints

- AD-11: core chart unchanged; OCP specifics only via the existing overlay
  (`core-overrides.yaml` + `platform-ocp` Route chart) — never OCP kinds in the core.
- AD-16: helm/kubectl from pixi; CRC/`oc` as explicit named system exceptions.
- AD-15: paths-filtered Platform CI; non-`recipes/` PRs carry the `maintenance` label.
- Default off on PR push — CRC is slow (~30–90 min job budget), disk-heavy (~35 GiB
  bundle), and needs a Red Hat pull secret (`CRC_PULL_SECRET`).
- **Runner honesty:** OpenShift Local's documented OS support excludes Ubuntu/Debian
  for the Podman Desktop path; GitHub-hosted `ubuntu-latest` may or may not run CRC
  via `crc-org/crc-github-action`. The spec's first implementation must prove the
  chosen runner class or fall back to a labeled self-hosted RHEL/Fedora runner —
  never claim OCP verification on a cluster that never started.

## Non-goals

- Replacing Story 12.7's full attended Tier-3 record (PVC edge cases, sidecar
  inventory after 12.5, Redis hardening after 12.6) — this job proves the
  portability profile, not every hybrid-environment CAP.
- Production/cluster-specific networking, external DNS, or corporate mirror posture.
- Duplicating `container`'s docker+podman matrix — one engine (Docker) for CRC, same
  rationale as 12.2.
- Nightly-only scheduling is acceptable as a follow-up if PR-default remains off;
  making every PR pay CRC cost is explicitly rejected.

## Kinships

- [[python-agent-platform]] — AD-11 (OCP-first, GKE as CI profile); CAP-6 portability.
- `spec-12-2-gke-as-a-portability-profile` — structural sibling; copy job shape,
  diverge at cluster + overlay + assertion path.
- [[local-ocp-hybrid-environment]] — consumes CAP-1 registry/bring-up facts (Story 12.4);
  does not re-own the full hybrid SDLC.
- Story 12.7 — overlapping Tier-3 items; 12.9 automates the subset CI can own;
  12.7 remains the attended closeout after chart extensions 12.5–12.6 land.

## Realization log

- **2026-08-23** — Dreamt and prematurely marked `specified` against
  `spec-12-9-ocp-as-a-portability-profile` (a story-spec name). That folder
  never existed; INV-1 matches the Dream slug, so the chain was still
  `dream-without-spec`.
- **2026-08-24** — Chain Spec `spec-ocp-as-a-portability-profile` landed
  `ready` (CAP-1..3). Bound to existing Story 12.9; ledger flipped
  done→backlog because Platform CI still has no `ocp-portability-smoke`
  job. Runner class remains an open question at story time.
- **2026-09-09 (fleet readiness pass)** — Log resumed; the last entry asserted a job that now exists (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`, Class B row stB / § 2.3 **C14**). Story 12.9 landed: `ocp-portability-smoke` at `.github/workflows/platform-ci.yml:1243`, `runs-on: ubuntu-latest`, 90-minute budget, CRC internal-registry push, double-gated on `PLATFORM_CI_OCP_PORTABILITY_SMOKE` / `workflow_dispatch` plus a fail-fast `CRC_PULL_SECRET` check at `:1265-1272` — so the earlier "Platform CI still has no `ocp-portability-smoke` job" line is **superseded**, and the runner-class open question is answered *by construction* (`ubuntu-latest` + the CRC action). CAP-1 met. **CAP-2 and CAP-3 are not:** `gh variable list` returns only `ACTIONS_ENABLED=false`, `gh secret list` has no `CRC_PULL_SECRET`, and `spec-12-9-…md:54` records "first green ocp-portability-smoke deferred to operator". **Operator decision this pass (batch C14): fund one green run — set `CRC_PULL_SECRET` + `PLATFORM_CI_OCP_PORTABILITY_SMOKE` and dispatch once, before Story 44.10 disables this repo's CI.** Status stays `specified` until that run exists — this Dream's own Constraint says never claim OCP verification on a cluster that never started. It is also the gate on any Intelligence-Hub NIC-profile story.
