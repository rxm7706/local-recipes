---
title: Upstream discovery — package it before it's asked for
type: dream
owner: atlas
status: seeded
---

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
