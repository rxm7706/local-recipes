---
spec: local-ocp-hybrid-environment
status: ready
owner-dream: docs/dreams/local-ocp-hybrid-environment.md
surface: []   # populated as stories land (chart sidecar/Redis templates, bring-up docs, dlt pipeline)
companions:
  - reconciliation-and-corrections.md
  - cluster-bringup-facts.md
sources:
  - ../../../../../../docs/intake/local-ocp-hybrid-environment/technical-spec.md
assumptions:
  - "CRC 2.63.0 / OpenShift 4.22.7 is the bring-up baseline; the Podman
    Desktop extension flow is as documented 2026-08-22 (companion facts)."
  - "steward 15.3 (provision --module) lands before any TEA-in-cluster
    validation is claimed; tea-test-review's standalone CLI suffices until."
open_questions: []   # the four shaping decisions were operator-locked 2026-08-22 (memlog)
---

# SPEC — The local OpenShift hybrid environment runs the agentic SDLC end to end

## Why

The operator wants a real local OpenShift cluster with the full agentic SDLC
around it. Two research passes proved the intake spec lands on a fleet that
already built most of it: `src/platform` IS the app layer (Langflow
in-process ≥1.11.4, DB-GPT sidecar, one front door), and Story 12.1's chart +
OCP overlay exist with exactly four honestly-unverified Tier-3 items that
only a live cluster can prove. So this effort is an **Epic 12 extension**
(operator-locked): bring the cluster up, verify 12.1 live, close the two
owed chart gaps (DB-GPT sidecar, Redis hardening), and add the one genuinely
new build (the dlt Projects V2 bridge). Every intake claim that contradicted
shipped architecture or external reality is struck with citations in
`reconciliation-and-corrections.md` — nothing adopted silently.

## Capabilities

- **CAP-1 — Cluster bring-up + registry posture (→ Story 12.4).** *Intent:*
  a documented, reproducible bring-up: Podman Desktop OpenShift Local
  extension (CRC 2.63.0 / OpenShift 4.22.7; 4 cores / 10.5 GB / 35 GB;
  Linux needs the `crc` binary on PATH) to Running; `oc` authenticated; the
  **internal-registry push** pattern (`podman login/tag/push` to
  `default-route-openshift-image-registry.apps-crc.testing` → ImageStream)
  minted as steward's anticipated OpenShift/registry-posture AD; pull
  secret, kubeadmin credentials, and the GitHub PAT recorded per the keys
  discipline (first inventory entries hand-authored). *Success:* fresh
  workstation reproduces it; the platform image pulls in-cluster from the
  ImageStream.
- **CAP-2 — DB-GPT sidecar joins the chart (→ Story 12.5).** *Intent:* the
  known-owed chart addition — sidecar Deployment (the platform's own image,
  never `eosphorosai/*` raw), dedicated SQLite PVC at the resolved
  metadata path, singleton semantics (replicas 1, Recreate), internal-only
  Service via `DBGPT_SIDECAR_BASE_URL`; 12.1's inventory-test sidecar
  REJECTION flips to expectation. *Success:* renders under restricted-v2;
  invariant tests updated and green.
- **CAP-3 — Redis hardened, ephemeral kept (→ Story 12.6).** *Intent:*
  emptyDir stays (Celery re-queues); AUTH via `existingSecret` key +
  NetworkPolicy restricting Redis to platform pods — closing 12.1's named
  unauthenticated-Redis follow-up. *Success:* rendered NetworkPolicy +
  AUTH-wired `REDIS_URL`; invariant tests cover both.
- **CAP-4 — Tier-3 attended verification (→ Story 12.7).** *Intent:*
  `helm install` core + overlay on the live cluster proves the four
  unverified items — Route admission, SCC enforcement, PVC binding,
  official postgres/redis images under an SCC-assigned arbitrary UID
  (fallback: RH/bitnami images or the `postgres.dataMountPath` seam) — plus
  the fresh-install migration-window observation. *Success:* a dated
  verification record in the 12.1 spec's orbit; failures become findings.
- **CAP-5 — dlt Projects V2 bridge (→ Story 12.8).** *Intent:* a small
  custom dlt **GraphQL** source (no verified source covers Projects V2;
  reuse `steward/sync.py`'s queries) loads the `github_metrics` dataset
  into cluster Postgres via port-forward; classic PAT with `read:project`
  (fine-grained PATs cannot reach user-owned projects); 5,000 points/hr +
  100-item pages budgeted; the board is created and repo-linked via
  `gh project link`. *Success:* board items queryable in `github_metrics`;
  kin-declared to `spec-jira-github-projects-sync` Mode B — never a second
  sync engine.

## Constraints

- Every strike in `reconciliation-and-corrections.md` is binding: no fresh
  scaffold, no Traefik/multiplexer topology, no `DBGPT_DB_URL`, no
  `logspace/langflow`, no public DB-GPT route, no hand-`psql` schema
  creation, no `?options=search_path` for Langflow, no
  `bmad-marshal-detectors-init`.
- BMAD wiring consumes steward 15.3 — never ad-hoc installer runs.
- Secrets: AD-12 `existingSecret` by reference + steward keys discipline;
  the intake's inline `debug` credentials are placeholders only.
- Image flow: internal-registry push is canonical; `--image` not the
  deprecated `--docker-image`; builds stay on the pixi/podman path.
- Langflow runs in-process (no Langflow pod; settings derive its env).

## Non-goals

- GKE and air-gap (Stories 12.2/12.3, unchanged, same epic).
- Jira sync or any bidirectional board semantics (the shipped sync chain).
- Suite wiring ownership (steward Epic 15) and the channel pipeline.
- Production/cloud OCP.

## Success signal

A fresh workstation reaches: cluster Running, platform deployed from the
12.1 chart via the internal registry with Routes admitted under
restricted-v2 and all four Tier-3 items dated-verified, the sidecar and
hardened Redis rendered from the same chart, and `github_metrics` answering
queries about the linked Projects V2 board — with zero steps improvised
outside the documented bring-up.
