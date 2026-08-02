---
title: WASM Data Stack
type: dream
owner: atlas
status: archived
archived-reason: absorbed
---

> **Superseded and fully consolidated.** This Dream's narrative now lives in
> [`docs/dreams/pyforge-atlas.md`](pyforge-atlas.md) § *The estate Atlas
> hosts*, which names the Wasm Analytics Stack as a separate, substantial
> initiative that Atlas's project tree hosts — **not** a capability of
> Atlas's own `cf_atlas` pipeline (`spec-pyforge-atlas`'s own CAP-1..CAP-17
> are untouched) and **not** a duplicate of anything Atlas already builds
> (Atlas's own G1 Pyodide/DuckDB-WASM compilation is a kinship this project
> reuses for its own out-of-scope v2 dashboard, not the same project). This
> started 2026-08-02 as a dream-level-only consolidation, then was
> **upgraded the same day to a full chain consolidation by explicit user
> decision**, overriding this repo's default dream-level-only convention:
> this project's own contract (5 capabilities, FR-1–17, honestly narrowed
> from its founding gist's broader claim) is no longer a standalone Spec —
> it was folded verbatim into `spec-pyforge-atlas/SPEC.md` as
> `## Satellite: Wasm Analytics Stack`, with its capabilities renumbered
> `CAP-27`..`CAP-31`; its PRD was folded into
> `prds/prd-pyforge-atlas-2026-07-17/prd.md`; its Architecture spine was
> folded into `architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md`
> with its invariants renumbered `AD-47`..`AD-56`. The original standalone
> documents were **not deleted** — they were moved intact to
> `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/{briefs/brief-wasm-analytics-stack-2026-07-25,prds/prd-wasm-analytics-stack-2026-07-25,architecture/architecture-wasm-analytics-stack-2026-07-25,specs/spec-wasm-analytics-stack}/`.
> It is also still **not** "the work is done" — epics/stories are
> deliberately not yet decomposed (planning ran to PRD + Architecture depth
> only) and no code has been written; the project remains planning-complete
> and unscheduled.

# Wasm-first analytics — sandboxed pipelines for the hardened enterprise

## The Dream

A modern analytical data stack whose logic runs as **Python-compiled WASI
components** — sandboxed, portable, high-performance — deployable on Red Hat
OpenShift under **Restricted SCC** (non-root UID 1001, read-only rootfs):
ingestion via **dlt** (Excel → FastAPI in the seed use-case), transformation via
**dbt**, native **OTel tracing + OpenLineage provenance**, one **Pixi** toolchain
bridging local dev, Podman "digital twins," and production OCP.

## Kinships

- [[sentinel]]'s WASM branch (ADR-037/038/039) dreamed the adapters; this stack
  is the analytics-shaped application of them.
- [[pyforge-atlas]] shipped the sibling proof (G1: the intelligence layer
  compiled to Pyodide/DuckDB-WASM).
- [[enterprise-airgap]] + [[presenton-pixi-image]] share the OCP-hardened,
  regulated-enterprise posture; [[unity-data-stack]] is the platform it would
  live on.

## What exists

- The architecture README (`wasm-first-analytical-data-stack-ocp-ready/` gist,
  2026-04-19 — same weekend as Sentinel v2.1).

## Realization log

- **2026-04-19** — architecture authored (gist); never landed.
- **2026-07-23** — Dream seeded from the gist audit.
