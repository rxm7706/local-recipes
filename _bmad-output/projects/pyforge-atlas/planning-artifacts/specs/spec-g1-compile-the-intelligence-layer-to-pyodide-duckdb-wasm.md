---
title: 'Story G1 (8.1): Compile the intelligence layer to Pyodide / DuckDB-WASM'
type: 'feature'
status: 'regenerated'
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'NEVER AUTHORED as a file — wave B9-H4 ran through the in-session agent loop, not bmad-create-story (which wrote files only for waves 0/A/B1-B8), confirmed by the migration session itself. Nothing was lost; there is no original to recover. Intent+ACs below are the real epics.md contract.'
enriched: '2026-07-25 (merged PR #96 body + main commit log; dev narrative recovered, review-triage partial)'
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
> at `../../spec-archive/retro-story-files/8-1-g1.md` — the operator's web-session archive.

## Contract (from epics.md — verbatim, authoritative)

### Story G1 (8.1): Compile the intelligence layer to Pyodide / DuckDB-WASM

As a dashboard consumer,
I want the Vizro-AI dashboard + BSL layer running in-browser via Pyodide / DuckDB-WASM,
So that the intelligence surface needs no backend at all.

**Acceptance Criteria:** (spec § 9 Story G1, binding)

**Given** the D-wave dashboard + BSL layer
**When** the WASM build runs
**Then** the dashboard loads and queries run client-side in the browser with no backend
**And** a `wasm-smoke` verify task exists (Playwright headless load-and-query against the built artifact — Chromium pre-provisioned).

- **FRs:** FR-14.
- **Invariants:** AD-21, AD-11 (gate is the wave's first deliverable).
- **Mode:** LOOP-E.
- **Gating question:** none.
- **Verify gate:** **builds `wasm-smoke`**.
- **Depends on:** Epic 5 (dashboard + BSL), F1 (canonical store).

### Story G2 (8.2): Emit Parquet artifacts to a static web host

As a dashboard consumer,
I want Parquet artifacts published to a static host and pulled via HTTP Range,
So that the WASM runtime reads live data with zero backend.

**Acceptance Criteria:** (spec § 9 Story G2, binding)

**Given** the G1 WASM runtime
**When** the emitter publishes
**Then** Parquet artifacts are published to the static host (Q4 default: GitHub Pages) and consumed by the WASM runtime via HTTP Range
**And** the emitter is host-agnostic so an enterprise mirror can substitute (Q4)
**And** the published artifact layout (chunking, manifest) has a single owner: this emitter (Spine convention).

- **FRs:** FR-14.
- **Invariants:** AD-21, AD-2 (mirror substitution).
- **Mode:** ATTENDED (publish boundary event — one of the five § 2.5 attended events).
- **Gating question:** **Q4** (WASM artifact host) — § 11 default adopted: GitHub Pages public path; emitter host-agnostic.
- **Verify gate:** **consumes `wasm-smoke`** (against the published artifact at the attended event; fixture-hosted in-loop).
- **Depends on:** G1.

### Story G3 (8.3): Implement Dagster Sensors for near-real-time ingestion

As the operator,
I want the pipeline event-driven via Dagster Sensors on upstream events (PyPI/GitHub webhooks or RSS),
So that ingestion is near-real-time and incremental instead of purely scheduled.

**Acceptance Criteria:** (spec § 9 Story G3, binding)

**Given** the C1 Dagster repository
**When** a simulated upstream event fires
**Then** it triggers the relevant pipeline incrementally via a Dagster Sensor
**And** the event-source choice (webhooks vs RSS) and the persistent-daemon question it drags in (Q2 revisit condition) are resolved and recorded in this story's spec (Spine Deferred).

- **FRs:** FR-6, spec § 5.9.
- **Invariants:** AD-6, AD-23 (sensor-triggered runs ride the same job machinery), AD-5 (incremental via the dataset class).
- **Mode:** LOOP-E.
- **Gating question:** Q2 revisit condition only (daemon footprint — resolves here if sensors require it; not a blocking Q-gate).
- **Verify gate:** `dagster-dryrun` (sensors enumerate) + simulated-event fixture in `kedro-test`.
- **Depends on:** C1, G2 (per § 14 wave order).
- **DELIVERED (2026-07-18 — closes Wave G):** two sensors (`pypi_release_sensor` → Phase H, `vcs_release_sensor` → Phase K) added to C1's `defs` via `orchestration/event_source.py` (dagster-free logic) + `build_upstream_sensor` in `orchestration/definitions.py`; a simulated event → one `RunRequest` for the existing incremental job (AD-23/AD-5), no-event → `SkipReason`. Event source = RSS/poll cursor (not webhooks); live daemon deferred (DW-G3). Gate `test_definitions_dryrun.py` +12; AD-1 import-ban + `dagster definitions validate` green. See spec § 5.9 / Q2.

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

### Dev summary — merged PR #96: story(G1): DuckDB-WASM in-browser read surface + wasm-smoke gate (FR-14)

## Summary

Opens Wave G. The D-wave read surface's client-side **query runs in-browser with zero backend via genuine DuckDB-WASM** (AD-21). The `wasm/` artifact is a static page that fetches a Parquet file as bytes, registers it, and runs `read_parquet(...)` inside the WASM engine — no server-side query, no API.

- **`wasm-smoke` gate** (`tests/wasm`, AD-11 wave-first deliverable): launches the pre-provisioned **headless Chromium**, loads the built artifact from a loopback static file host, and **proves the no-backend/offline claim** by blocking + asserting **zero non-loopback requests** — the offline proof genuinely covers Web-Worker traffic (both the `.wasm` module and the vendored parquet extension fetch are intercepted). It asserts the exact client-side query result, and is **non-hollow**: removing/malforming/emptying the Parquet flips `#status` to error and **fails** the gate.
- The parquet extension is **vendored locally** so the runtime never reaches `extensions.duckdb.org`. `wasm-build` + `wasm-smoke` pixi tasks; `build/` + `node_modules/` (a ~41 MB `.wasm`) are gitignored + reproducible from `build.py`.

## Review fixes (both in-loop reviewers)

- **Skip-to-green closed:** under `WASM_SMOKE_REQUIRED`/`CI` a missing browser or unbuilt artifact **fails** instead of skipping (a misconfigured CI cannot pass having verified nothing).
- The loopback allowlist parses the URL **host** (`127.0.0.1`/`localhost`/`::1`) instead of a substring match (`http://127.0.0.1.evil.example` no longer slips the offline guard).

## Deferred

The full Vizro/Pyodide dashboard **render** in-browser (**DW-G1-1** — the page renders a plain HTML table, not the Vizro UI) and the CI `wasm-build` step for the gitignored heavy assets (**DW-G1-2**).

## Tests

`683 passed` (+1 real headless-browser gate).

### Commits on `main`

- `d79d483618` story(G1): DuckDB-WASM in-browser read surface + wasm-smoke gate (FR-14)  _(dev-landing)_

_This PR also carried an automated Gemini review; not reproduced here per repo policy ([[feedback_no_gemini_reviews]])._

