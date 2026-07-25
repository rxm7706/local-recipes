---
title: Wasm-first analytical data stack (OCP-ready)
type: dream
owner: crew
status: in-spec
---

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
