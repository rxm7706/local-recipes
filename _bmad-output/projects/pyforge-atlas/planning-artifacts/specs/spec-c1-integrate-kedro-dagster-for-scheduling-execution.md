---
title: 'Story C1 (4.1): Integrate `kedro-dagster` for scheduling + execution'
type: 'feature'
status: 'regenerated'
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'
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

### Story C1 (4.1): Integrate `kedro-dagster` for scheduling + execution

As the operator,
I want the Kedro DAG compiled into a Dagster repository with schedules, retries, profiles, and per-node timeouts,
So that I watch runs in the Dagster UI and the 1800 s silent-phase-drop defect is structurally retired.

**Acceptance Criteria:** (spec § 9 Story C1, binding)

**Given** the migrated Kedro DAG
**When** `kedro-dagster` compiles it
**Then** schedules exist as Dagster Schedules encoding the `guides/atlas-operations.md` cadence table (bootstrap weekly; F/H/K/L/E.5 + G-after-vdb daily; E/J/M every 6 h; N hourly per maintainer; refresh assets weekly)
**And** the three bootstrap profiles (maintainer / admin / consumer) exist as named Dagster job configurations with the guide's override precedence (explicit run-config/env beats profile defaults)
**And** retries + phase state are observable in the Dagster UI
**And** timeouts are per-node: a cold-run Phase R overrun can no longer abort Phase F/K/N — the legacy 1800 s `cf_atlas_core` defect is demonstrably retired
**And** a `dagster-dryrun` verify task exists (definitions load, schedules enumerate — no live execution); the schedule bring-up itself is an attended event (Q2)
**And** Phase P stays `PHASE_P_ENABLED=1`, admin-config-only, never a default schedule.

- **FRs:** FR-6.
- **Invariants:** AD-6, AD-1 (`kedro-dagster` is replaceable glue; no upward imports), AD-23 (one execution plane; run admission serializes per dataset set).
- **Mode:** ATTENDED (bring-up boundary event — one of the five § 2.5 attended events; the `dagster-dryrun` gate it builds is loop-consumable thereafter).
- **Gating question:** **Q2** — default adopted (above); re-verify the Dagster bet at wave start (release cadence under Prefect, `kedro-dagster` compatibility, Components/Prefect-deployer ramps).
- **Verify gate:** **builds `dagster-dryrun`**.
- **Depends on:** Epic 3 complete (nodes + refresh assets to schedule).

### Story C2 (4.2): Integrate `kedro-viz` + expose a pixi task

As the operator,
I want the topological DAG rendered by `kedro-viz` behind a dedicated pixi task,
So that I inspect dataset schemas and lineage in the browser instead of reading orchestrator source.

**Acceptance Criteria:** (spec § 9 Story C2, binding)

**Given** the compiled DAG
**When** `pixi run viz` executes
**Then** it launches the Kedro-Viz server
**And** operators can inspect dataset schemas + data lineage in the browser.

- **FRs:** FR-6 (structural observability), whole-migration AC-3.
- **Invariants:** AD-1, AD-6.
- **Mode:** LOOP-E.
- **Gating question:** none (Q2 drained at C1).
- **Verify gate:** `dagster-dryrun` + `kedro-test` (existing gates; viz task smoke lands in the pixi task inventory).
- **Depends on:** C1.

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
