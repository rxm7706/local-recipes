---
title: A local OpenShift hybrid environment runs the agentic SDLC end to end — visual lifecycle, wired BMAD suite, multiplexed apps, synced tracker
type: dream
owner: steward
status: dreamt
---

# A local OpenShift hybrid environment runs the agentic SDLC end to end

## The Dream

The operator develops against a real, local Red Hat OpenShift cluster
(OpenShift Local under Podman Desktop) with the full agentic SDLC around it:
visual lifecycle management (Podman Desktop) bridged to infrastructure-as-code
(`oc` CLI); the complete BMAD suite wired and orchestrated; a
cookiecutter-django application co-hosted with Langflow (1.11.x) and DB-GPT
behind Traefik/ASGI multiplexing; PostgreSQL and Redis on PVCs with
schema-isolated tenants (`cookiecutter_schema`, `langflow_schema`,
`dbgpt_schema`, `github_metrics`); **Pixi** as the foundational package
manager throughout; **GitHub Projects V2** as the authoritative issue
tracker, synced locally via **dlt** into the cluster's PostgreSQL; and TEA
validating deployments. The full operator-authored technical specification
(six phases, architecture diagram, wiring plan) is filed verbatim at
`docs/intake/local-ocp-hybrid-environment/technical-spec.md` — it is this
Dream's source input and the spec pass's primary source.

## What the fleet already has (convergence map — read before scoping)

The spec's phases land on a fleet that has already built much of this; the
spec pass must reconcile "scaffold fresh" against "deploy what exists":

- **The application layer largely EXISTS as steward's platform**
  (`src/platform/`, Epics 10–13): a cookiecutter-django-derived host with
  Langflow AND DB-GPT integrated as pluggable apps (Pattern-A/B, AD-17),
  schema/PVC isolation decisions already made (AD-6 + the dated SQLite
  exception), Celery + Redis wiring, compose profiles, and — decisive for
  this Dream — **Story 12.1's vanilla Helm chart + thin OCP Route overlay,
  restricted-v2 hardcoded**, whose Tier-3 (live Route admission/SCC) was
  honestly left unverified because *no cluster existed*. This Dream's
  cluster IS the missing verification environment for 12.1 — and 12.2 (GKE
  profile) / 12.3 (air-gap parity) are its siblings in the same epic.
- **ASGI multiplexing has a prior Dream**: [[asgi-multiplexer-monolith]]
  (Django+Langflow+DB-GPT in one ASGI process, no Spec yet). The OCP spec's
  Traefik-routed multiplexer is the cluster-shaped form of the same
  aspiration — the spec pass DECIDES absorb-vs-kin rather than minting a
  duplicate chain.
- **BMAD wiring is already chartered**: the spec's "BMAD Suite Wiring Plan"
  table is `spec-bmad-suite-channel-product` CAP-3's target state verbatim
  (steward Epic 15.3 wires TEA/BMB/CIS/utility-skills/manticore; WDS skip).
  This Dream CONSUMES that chain; it does not re-own it. One spec command,
  `bmad-marshal-detectors-init`, does not exist anywhere — flag for the
  spec pass (the nearest real machinery is marshal's detector registry +
  one-front-door's mc-* triage).
- **Tracker sync has a prior spec**: steward's `spec-jira-github-projects-sync`
  (planning-artifacts/specs). The dlt→`github_metrics` bridge is kin —
  reconcile at spec time.
- **Versions**: the spec names Langflow 1.11.2; the factory's langflow-suite
  recipes are at 1.10.1 (`docs/specs/langflow-conda-forge.md`, suite PR
  #33972 in flight) — a bump decision, not a given. DB-GPT is
  consume-not-submit (G58, external PR #33883).
- **Pixi-as-foundation and dlt** are native here: dlt ships in the pixi
  estate (`library-llms-full.md`), and the workspace conventions
  (environments, lock discipline, the 16-site pixi version registry) apply
  to the new workspace the spec scaffolds.

## What it looks like when real

- One documented bring-up takes a fresh workstation to: cluster Running in
  Podman Desktop, `oc` authenticated, BMAD suite fully wired (via the
  channel-product chain), the platform deployed from the 12.1 chart with
  Routes admitted under restricted-v2 (12.1's Tier-3 finally verified
  live), PVC-backed Postgres/Redis with the four isolated schemas, and
  Langflow + DB-GPT served behind the multiplexed ingress.
- GitHub Projects V2 is the tracker of record, and its items/fields/status
  land in `github_metrics` via a dlt pipeline run from the Pixi workspace —
  no third-party SaaS middleware.
- TEA validates the deployment as part of the flow (its wiring arrives via
  Epic 15.3; `tea-test-review` gates exist today).
- The whole thing is IaC-reproducible: manifests/values tracked, secrets
  never committed (the `.dlt/secrets.toml` and pull-secret handling follow
  steward's key discipline).

## What is real

The intake spec (verbatim, filed); steward's platform + chart (Epics 10–12.1
shipped); the channel-product chain (Epic 15, backlog) that will wire the
suite; dlt installed; the prior asgi-multiplexer and jira-github-projects
Dreams/specs; no cluster, no Podman Desktop integration, no dlt pipeline, no
GitHub Projects V2 board, nothing deployed to OCP.

## Constraints

- Reuse-first: the spec pass must justify any fresh scaffold over deploying
  `src/platform/` + the 12.1 chart (the spec's cookiecutter-django scaffold
  and the platform are the same lineage — divergence is debt).
- Secrets (GitHub PAT, pull secret, DB credentials) follow steward's key
  discipline — never committed, never host-unscoped; the spec's inline
  `debug_password` is a local-dev placeholder, not a pattern.
- BMAD wiring flows through `provision --module` (Epic 15.3), never ad-hoc
  installer runs that leave no manifest record.
- The multiplexer decision (in-process ASGI vs Traefik-routed pods) is made
  once, reconciling [[asgi-multiplexer-monolith]] — not implemented both
  ways.

## Non-goals

- Owning suite wiring or channel currency ([[bmad-suite-channel-product]]).
- The core upgrade ([[bmad-method-core-upgrade]]) and era alignment
  ([[bmad-611-era-alignment]]).
- Production/cloud OCP — this is OpenShift LOCAL; GKE/air-gap stay stories
  12.2/12.3 in the platform epic.
- Replacing the fleet's sprint-ledger machinery with GitHub Projects V2 —
  the board tracks THIS effort's work; any deeper tracker integration is
  `spec-jira-github-projects-sync`'s question.

## Kinships

steward Epics 10–13 (`spec-python-agent-platform` — the app layer + 12.1
chart this deploys and finally live-verifies) · [[asgi-multiplexer-monolith]]
(absorb-vs-kin at spec time) · [[bmad-suite-channel-product]] (CAP-3 wiring
consumed) · `spec-jira-github-projects-sync` (tracker kin) ·
`docs/specs/langflow-conda-forge.md` (1.10.1 suite; the 1.11.x bump
question) · DB-GPT G58 consume-not-submit lineage.
