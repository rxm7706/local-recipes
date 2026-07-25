---
title: 'Story E2 (6.2): Integrate OpenLineage + OpenTelemetry'
type: 'feature'
status: 'regenerated'
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'NEVER AUTHORED as a file — wave B9-H4 ran through the in-session agent loop, not bmad-create-story (which wrote files only for waves 0/A/B1-B8), confirmed by the migration session itself. Nothing was lost; there is no original to recover. Intent+ACs below are the real epics.md contract.'
enriched: '2026-07-25 (merged PR #91 body + main commit log; dev narrative recovered, review-triage partial)'
---

> **Contract-spec — no original ever existed (corrected 2026-07-25).** This story
> (wave B9–H4) was built by the atlas migration's **in-session agent loop**, which —
> unlike `bmad-create-story` (used only for waves 0/A/B1–B8) — never emitted a per-story
> spec file. The atlas migration session (`01FYyQvBJuXwySiaMUUYCqBZ`) confirmed this
> exhaustively: no such file exists in `implementation-artifacts/`, `.bmad-loop/runs/`
> (which never existed for atlas), any git worktree, git history, or anywhere on disk.
> **Nothing was lost — there is no original to recover.** This file carries the
> load-bearing contract (Intent + Acceptance Criteria **verbatim** from the tracked
> `planning-artifacts/epics.md`) plus a dev narrative reconstructed from the merged record
> (the "Dev narrative" section below). A fuller BMAD-story-format reconstruction (Dev
> Agent Record + File List + Review Triage Log, built from the agent-loop transcripts) is
> at `../../spec-archive/retro-story-files/6-2-e2.md` — the operator's web-session archive.

## Contract (from epics.md — verbatim, authoritative)

### Story E2 (6.2): Integrate OpenLineage + OpenTelemetry

As the operator,
I want Kedro nodes, Dagster runs, and DuckDB queries instrumented with OpenLineage and OTel,
So that lineage, per-node metrics, and end-to-end traces are observable down to specific API calls.

**Acceptance Criteria:** (spec § 9 Story E2, binding)

**Given** the compiled DAG and hooks layer
**When** instrumentation lands
**Then** lineage + per-node metrics (rows, latency, cache hits) are captured via OpenLineage
**And** end-to-end distributed traces are visible via OTel down to specific API calls
**And** emitted-event/span fixtures are this story's gate assets (AD-20 — fixture-verified, since Wave E has no new named gate).

- **FRs:** FR-12.
- **Invariants:** AD-20, AD-6 (hooks declared in run config — every entry point inherits them, AD-23).
- **Mode:** LOOP-E.
- **Gating question:** none.
- **Verify gate:** existing gates + emitted-event/span fixtures in `kedro-test`.
- **Depends on:** C1 (Dagster runs to instrument).

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

## Dev narrative — recovered from the merged record (2026-07-25)

> The original spec's `## Dev Notes` / `## Review Triage Log` were lost with the Tier-3
> worktree teardown (this story was built in claude.ai/code web session
> `01FYyQvBJuXwySiaMUUYCqBZ`; see `README.md`). The narrative below is reconstructed from
> the **authoritative merged record** — the story's PR body and its commits on `main` —
> **not** a regeneration. If the verbatim original is recovered from the web session, it
> supersedes this section.

### Dev summary — merged PR #91: story(E2): OpenLineage + OpenTelemetry instrumentation via the hook layer (FR-12)

## Summary

**Closes Wave E.** Adds `observability.py` (`AtlasObservabilityHooks`) — registered in `settings.HOOKS` beside `ProjectHooks`, so **every entry point inherits it** (AD-6/AD-23: a `kedro run` and the C1 Dagster plane, which runs nodes through `KedroSession`, are both instrumented from one declaration). Nodes stay pure DataFrame→DataFrame — all instrumentation lives in the hook layer.

- **OpenLineage** — each node run emits a RunEvent START + terminal (COMPLETE/FAIL) with input/output **lineage** and the FR-12 metric facets: standard `outputStatistics.rowCount` per output + a custom `atlasNodeMetrics` run facet carrying **rows / latency_ms / cache_hits**.
- **OpenTelemetry** — a parent pipeline span + nested per-node child spans + per-input dataset-IO ("API call") child spans; one trace per run.
- **Offline + injectable (AD-20)** — both backends default to no-op (no span processor / OL skipped), so the in-container default emits nowhere with no network; the gate injects an `InMemorySpanExporter` + a capturing OL client and asserts the emitted events/spans (the fixture-verified gate — Wave E has no new named gate). Live collector/OTLP wiring is env-driven and **deferred** (DW-E2-1).
- **AD-6/AD-23 import-ban** — only `observability.py` imports openlineage/opentelemetry.

## Review fixes (both in-loop reviewers)

- **rowCount** now gates on a 2-D `.shape` (was bare `len()`, which reported a bogus count for a dict/list/str output — the atlas has dict-returning nodes).
- A node still open when the **pipeline errors** now gets an OL **FAIL** terminal (was a dangling START with no COMPLETE/FAIL for OL consumers).
- **`__deepcopy__`** shares the injected OTel provider *and* OL client by reference, so C1's per-run hook deepcopy can't silently drop the provider while keeping the OL client (an OTel-drops/OL-survives asymmetry that would make the Dagster plane emit events but no spans once a real exporter lands).

Dagster-plane inheritance verification + the facet provenance stamp are recorded DW-E2-2/-3.

## Tests

`620 passed` (+19 new); `dagster definitions validate` passes (deepcopy path intact).

### Commits on `main`

- `bfb195e235` story(E2): OpenLineage + OpenTelemetry instrumentation via the hook layer (FR-12)  _(dev-landing)_

_This PR also carried an automated Gemini review; not reproduced here per repo policy ([[feedback_no_gemini_reviews]])._

