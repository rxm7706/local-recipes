---
title: 'Story G2 (8.2): Emit Parquet artifacts to a static web host'
type: 'feature'
status: 'shipped'
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'NEVER AUTHORED as a file — wave B9-H4 ran through the in-session agent loop, not bmad-create-story (which wrote files only for waves 0/A/B1-B8), confirmed by the migration session itself. Nothing was lost; there is no original to recover. Intent+ACs below are the real epics.md contract.'
enriched: '2026-07-25 (merged PR #97 body + main commit log; dev narrative recovered, review-triage partial)'
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
> at `../../spec-archive/retro-story-files/8-2-g2.md` — the operator's web-session archive.

## Contract (from epics.md — verbatim, authoritative)

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

### Dev summary — merged PR #97: story(G2): host-agnostic static-host Parquet emitter + HTTP-Range gate (FR-14)

## Summary

Adds `publish/` — the **single owner** of the published-artifact layout (chunked Parquet + a `manifest.json` contract, defined once). `emit_static_site` writes the layout to a target **directory** ("the static host filesystem"); **which host** serves it (GitHub Pages public path, or an enterprise/JFrog mirror) is a deploy/config choice — **no host URL / github.io is baked into the emit logic** (AD-2 mirror substitution; a consumer composes chunk URLs from a runtime base via `chunk_url`).

- **`publish-range` gate** (`tests/publish`): emits the layout, serves it over a Range-capable loopback host, points a DuckDB httpfs client at it, and **proves consumption is via HTTP Range** — 206 Partial Content reading strictly **fewer** bytes than the whole file (measured ~2.9%); a whole-file 200 **fails** the gate (non-hollow). Also asserts the chunk path is discovered **from the manifest** + matches checksums, host-agnosticism (same dir, two bases), and the D1 `ci_red` result over the range-served Parquet. httpfs `LOAD`ed **offline** from cache.

## Review fixes

- **MUST-FIX (Reviewer B):** a dataset **name** is joined onto `target_dir` and `rmtree`'d on re-emit — an unsanitized `../x` / `a/b` / leading-slash name would delete a directory **outside** `target_dir`. `_require_safe_name` now rejects any traversal/separator, and **all names+types validate up front** before any filesystem mutation (also fixes the non-atomic partial-emit that destroyed a prior good site on a late failure). Regression tests for both.
- **Reviewer A:** the `publish-range` pixi task sets `PUBLISH_RANGE_REQUIRED=1` so the authoritative gate **fails** (never skips-to-green) if httpfs is unprovisioned; the single-owner docstring corrected — G1's `wasm/` runtime is **not yet** a manifest consumer (it fetches a flat parquet), recorded **DW-G2-2**.

## Deferred

The live GitHub Pages publish (**DW-G2-1**, attended) + migrating G1 to consume the manifest (**DW-G2-2**).

## Tests

`695 passed` (+12 new).

### Commits on `main`

- `fc6f846c9f` story(G2): reject over-long dataset names up front (independent review, LOW)  _(review-fix)_
- `ac63f3e751` story(G2): host-agnostic static-host Parquet emitter + HTTP-Range gate (FR-14)  _(dev-landing)_

_This PR also carried an automated Gemini review; not reproduced here per repo policy ([[feedback_no_gemini_reviews]])._

