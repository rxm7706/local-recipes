---
title: 'Story G3 (8.3): Implement Dagster Sensors for near-real-time ingestion'
type: 'feature'
status: 'regenerated'
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'
enriched: '2026-07-25 (merged PR #98 body + main commit log; dev narrative recovered, review-triage partial)'
---

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

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

### Dev summary — merged PR #98: G3: Dagster sensors for near-real-time upstream ingestion (FR-6)

## Story G3 — Dagster sensors for near-real-time ingestion (FR-6)

Adds two Dagster sensors that trigger the **existing** incremental ingestion jobs when an upstream event source reports a new release, closing the latency gap between scheduled runs.

### Changes
- **`orchestration/event_source.py` (NEW, dagster-free)** — `UpstreamEvent` / `SensorDecision` / `EventSource` protocol + `offline_event_source` fixture. `evaluate_events()` dedupes by monotonic `seq` via cursor, so a tick never re-requests an already-seen release. Zero dagster imports preserves **AD-1** import-confinement (event modelling stays outside the orchestration glue plane).
- **`orchestration/definitions.py`** — `UPSTREAM_SENSORS` table + `build_upstream_sensor()` factory yielding `dg.RunRequest(job=...)` for the existing jobs (`phase_h_pypi_versions`, `phase_k_vcs_upstream`) or `dg.SkipReason` when quiet / on event-source error (degrade, never crash the daemon). Sensors default **STOPPED** and are injectable via `event_sources` for dry-run tests. **No second execution plane** — sensors re-request the same jobs the schedules run (**AD-23**); **AD-5** incremental datasets do the TTL gating.
- **`tests/orchestration/test_definitions_dryrun.py`** — sensor dry-run coverage (RunRequest on new event, SkipReason when quiet, dedupe across ticks, degrade-on-error). 33 → 50 tests.

### Deferred
- Live sensor daemon bring-up (`dagster-daemon` process + real RSS/webhook source) is attended/credentialed → **DW-G3**.

### Verification
- Sensor dry-run + AD-1 ban gate: **48 passed**.
- Full atlas suite: **712 passed**.

Both in-loop reviewers + an independent fresh-eyes review collected; all SHOULD-FIX / NIT applied.

### Commits on `main`

- `eff5e1be77` G3: Dagster sensors for near-real-time upstream ingestion (FR-6) (#98)  _(dev-landing)_

_This PR also carried an automated Gemini review; not reproduced here per repo policy ([[feedback_no_gemini_reviews]])._

