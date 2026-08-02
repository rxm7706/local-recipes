---
title: Upstream discovery — package it before it's asked for
type: dream
owner: atlas
status: archived
archived-reason: absorbed
---

> **Superseded (narrative only).** This Dream's narrative now lives in
> [`docs/dreams/pyforge-atlas.md`](pyforge-atlas.md) § *The estate Atlas
> hosts*, which names Upstream Discovery as a separate initiative that
> Atlas's project tree hosts — **not** a capability of Atlas's own `cf_atlas`
> pipeline (`spec-pyforge-atlas`'s Capabilities are untouched) and **not** a
> duplicate of anything Atlas already builds (it is a candidate-sourcing
> layer that would feed [[packaging-factory]], distinct from Atlas's
> intelligence signals). This is a dream-level consolidation only: the
> project's own contract — 5 capabilities, re-grounded in Atlas's shipped
> Kedro dataflow after the legacy phase-based design was superseded by the
> migration — still lives at `spec-upstream-discovery/SPEC.md`; it is not
> touched by this consolidation. It is honestly the earliest-stage of
> Atlas's three satellites and **not** "the work is done": the Spec itself is
> `status: draft`, with no PRD, no Architecture, and zero implementation —
> six open questions remain, including which of Atlas's 7 closed pipelines
> should host it. Archived 2026-08-02 as the narrative entry point only; its
> Spec continues independently.

# Upstream discovery — sense what the world is building

## The Dream

The factory should not wait for requests. It should **sense** what the
ecosystem is adopting — GitHub trending, org releases, momentum signals — and
carry the worthy candidates into conda-forge *before* anyone files an issue.
Discovery becomes a pipeline phase, not a hobby: signals in, tiered candidates
out, recipes drafted while the hype is still warm.

## What it looks like when real

- **cf_atlas Phase T**: the GitHub-trending discovery engine (schema v29→v30),
  a tiered packaging classifier, and the `trending-candidates` CLI/MCP tool.
- **Org audit track**: systematic sweeps of high-yield orgs (the June 2026
  `github.com/microsoft/*` audit: ~10–14 recipes across 3 waves).
- Candidates flow straight into [[packaging-factory]] campaign machinery, with
  [[pyforge-doctor]]-grade health screens (abandonment, license) up front.

## What is real

- The spec is authored, validated, and committed:
  `docs/specs/trendshift-conda-forge.md` (ready — resume at Wave A; first batch
  seeded by `cli-anything-hub`). Zero implementation yet.

## Realization log

- **2026-06-20** — trendshift spec authored (Track B absorbed the microsoft
  audit).
- **2026-07-23** — Dream retro-seeded. Post-migration note: Phase T should be
  born as a **Kedro node** in the new [[pyforge-atlas]] dataflow, not a legacy
  phase.
