---
title: 'Story G3 (8.3): Implement Dagster Sensors for near-real-time ingestion'
type: 'feature'
status: shipped
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'NEVER AUTHORED as a file — wave B9-H4 ran through the in-session agent loop, not bmad-create-story (which wrote files only for waves 0/A/B1-B8), confirmed by the migration session itself. Nothing was lost; there is no original to recover. Intent+ACs below are the real epics.md contract.'
enriched: '2026-07-25 (merged PR #98 body + main commit log; dev narrative recovered, review-triage partial)'
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
> at `../../spec-archive/retro-story-files/8-3-g3.md` — the operator's web-session archive.

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

## Tasks / Subtasks

*(Derived from the ACs — no original task breakdown was authored for this loop-run story.)*

- [x] it triggers the relevant pipeline incrementally via a Dagster Sensor
- [x] the event-source choice (webhooks vs RSS) and the persistent-daemon question it drags in (Q2 revisit condition) are resolved and recorded in this story's spec (Spine Deferred).

## Dev Notes

**Planning metadata (from `epics.md`):**

- **FRs:** FR-6, spec § 5.9.
- **Invariants:** AD-6, AD-23 (sensor-triggered runs ride the same job machinery), AD-5 (incremental via the dataset class).
- **Mode:** LOOP-E.
- **Gating question:** Q2 revisit condition only (daemon footprint — resolves here if sensors require it; not a blocking Q-gate).
- **Verify gate:** `dagster-dryrun` (sensors enumerate) + simulated-event fixture in `kedro-test`.
- **Depends on:** C1, G2 (per § 14 wave order).
- **DELIVERED (2026-07-18 — closes Wave G):** two sensors (`pypi_release_sensor` → Phase H, `vcs_release_sensor` → Phase K) added to C1's `defs` via `orchestration/event_source.py` (dagster-free logic) + `build_upstream_sensor` in `orchestration/definitions.py`; a simulated event → one `RunRequest` for the existing incremental job (AD-23/AD-5), no-event → `SkipReason`. Event source = RSS/poll cursor (not webhooks); live daemon deferred (DW-G3). Gate `test_definitions_dryrun.py` +12; AD-1 import-ban + `dagster definitions validate` green. See spec § 5.9 / Q2.

### Implementation notes

<!-- DERIVED 2026-07-27 by reading the shipped code (PR #98). No original dev-session
     notes existed for this story; this is what the merged implementation actually does. -->

**RSS/poll cursor, not webhooks — and the reasoning generalizes.** A webhook needs an
always-on bound public ingress: a listener, networking, and exactly the daemon footprint the
project set out to avoid. It also **cannot be exercised offline**, so it could never have a
fixture gate. An RSS/poll snapshot (PyPI `updates.xml`, a repo's `releases.atom`) is a
stateless *outbound* pull, deduped by a Dagster-native cursor, and injectable as a fixture
with zero network. The offline-testability requirement chose the architecture.

**The sensor triggers; it does not fetch (AD-5).** Each sensor yields **one `RunRequest` for
an existing C1 job** — never a second execution plane (AD-23). Incrementality remains the
dataset's job: the run re-fetches only TTL-stale rows via `IncrementalParquetDataset`. A
sensor that re-fetched everything on each event would have undone Wave A.

**The two targets are not arbitrary.** `pypi_release_sensor` → Phase H,
`vcs_release_sensor` → Phase K — exactly the two upstream job surfaces whose catalog entries
A3 flipped to the incremental dataset (`pypi_version_fetched_at`,
`github_version_fetched_at`). The sensors point at the only two places where an event can
actually shorten the path to fresh data.

**Everything degrades to `SkipReason`.** No-event, duplicate, malformed, **and a raising
source** all produce a skip with a stated reason. A flaky upstream feed must never crash the
sensor daemon — availability of the orchestrator does not depend on the politeness of an RSS
endpoint.

**`event_source.py` is deliberately dagster-free.** The event and cursor logic lives outside
the glue module so AD-1's single-dagster-file rule still holds, and so the decision logic is
unit-testable from a simulated event with no orchestrator present.

**Sensors ship `default_status=STOPPED`.** Loading `defs` therefore adds **no always-on
process** — mirroring the schedules' no-auto-start stance. Turning them RUNNING against a
live feed is the attended daemon bring-up (DW-G3, mirroring DW-C1-1). This is how Q2's
daemon-footprint concern was answered without giving up the capability: the sensors exist and
are proven; starting them is the operator's explicit choice.

**Gate:** `test_definitions_dryrun.py` gained 12 assertions — sensors enumerate and target
real jobs; an injected offline source plus `build_sensor_context` turns a simulated event
into one `RunRequest` for the right job with the cursor advancing; the four degrade paths
yield `SkipReason`. `dagster definitions validate` and the AD-1 import-ban pass.

### References

- [Source: _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md#Story-G3]
- [Source: docs/specs/cfe-atlas-datapipeline-kedro-migration.md#§9-Story-G3]
- [Architecture: _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md]

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Delivery Record

<!-- DERIVED from the merged PR via `gh` on 2026-07-27. Exact, not reconstructed. -->

| | |
|---|---|
| Pull request | **#98** — G3: Dagster sensors for near-real-time upstream ingestion (FR-6) |
| Merged | 2026-07-18 |
| Diff | 5 files, +607 / -1 |
| Test files touched | 1 |

**Commits**

- `af28ea9` G3: Dagster sensors for near-real-time upstream ingestion (FR-6)

**File list** *(exact, from the merged diff)*

```
  307 +     0 -  src/shared/packages/pyforge-atlas/tests/orchestration/test_definitions_dryrun.py
  166 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/orchestration/event_source.py
  128 +     1 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/orchestration/definitions.py
    5 +     0 -  docs/specs/cfe-atlas-datapipeline-kedro-migration.md
    1 +     0 -  _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
```

## Dev Agent Record

### Agent Model Used

In-session BMAD agent loop (draft → 2× adversarial review → 1× independent fresh-eyes review → real-gate verify), not a `bmad-dev-story` story-file run.

### Completion Notes List

- **Impl commit `40b9eae`** — G3: Dagster sensors for near-real-time upstream ingestion (FR-6) (#98)
  - Add two Dagster sensors that trigger existing incremental ingestion jobs
  - when an upstream event source reports a new release, closing the gap
  - between scheduled runs (near-real-time, FR-6).
  - - orchestration/event_source.py (NEW, dagster-free): UpstreamEvent /
  - SensorDecision / EventSource protocol + offline_event_source fixture.
  - evaluate_events() dedupes by monotonic seq via cursor, so a sensor
  - tick never re-requests an already-seen release. Zero dagster imports
  - keeps AD-1 import-confinement intact (event modelling lives outside
  - the orchestration glue plane).
  - - orchestration/definitions.py: UPSTREAM_SENSORS table + build_upstream_sensor()
  - factory yielding dg.RunRequest(job=...) for the existing incremental jobs
  - (phase_h_pypi_versions, phase_k_vcs_upstream) or dg.SkipReason when the
  - source is quiet. On event-source error it yields dg.SkipReason (degrade,
  - never crash the daemon). Sensors default STOPPED (SENSOR_DEFAULT_STATUS)
  - and are injectable via event_sources for dry-run tests. No second
  - execution plane: sensors re-request the SAME jobs the schedules run
  - (AD-23, AD-5 incremental datasets do the TTL gating).
  - - tests/orchestration/test_definitions_dryrun.py: sensor dry-run coverage
  - (RunRequest on new event, SkipReason when quiet, dedupe across ticks,
  - degrade-on-error), 33 -> 50 tests.
  - Live sensor daemon bring-up (dagster-daemon process, real RSS/webhook
  - source) is attended/credentialed -> deferred DW-G3.
  - Both in-loop reviewers + independent fresh-eyes review collected;
  - all SHOULD-FIX/NIT applied.
  - Claude-Session: https://claude.ai/code/session_01FYyQvBJuXwySiaMUUYCqBZ
  - Co-authored-by: Claude <noreply@anthropic.com>

## Review Triage Log

No separate review-fix commit; findings (if any) folded into the impl commit. Full review threads on PR `#98`.

## Dev narrative — recovered from the merged record

> The original spec's `## Dev Notes` / `## Review Triage Log` were lost with the Tier-3
> worktree teardown (this story was built in claude.ai/code web session
> `01FYyQvBJuXwySiaMUUYCqBZ`; see `README.md`). The narrative below is reconstructed from
> the **authoritative merged record** — the story's PR body and its commits on `main` —
> **not** a regeneration. If the verbatim original is recovered from the web session, it
> supersedes this section.

### Dev summary — merged PR #98: G3: Dagster sensors for near-real-time upstream ingestion (FR-6)

## Deferred Work (DW ledger)

### DW-G3 — the live Dagster sensor DAEMON bring-up (ATTENDED, Q2) — DEFERRED to the wave-boundary event
- source_spec: `cfe-atlas-datapipeline-kedro-migration.md` (Story G3, § 5.9, FR-6)
  summary: G3 shipped the BUILDABLE half of event-driven ingestion — the sensor DEFINITIONS +
    their eval logic, wired into C1's `defs`, all verified with NO live execution and NO network.
    `orchestration/event_source.py` (dagster-free event parse + monotonic-`seq` cursor dedupe +
    run/skip DECISION, so AD-1's "only definitions.py imports dagster" rule holds) + `UPSTREAM_SENSORS`
    / `build_upstream_sensor` in `orchestration/definitions.py` add two sensors to
    `dg.Definitions(..., sensors=[...])`: `pypi_release_sensor` → the existing `phase_h_pypi_versions`
    job, `vcs_release_sensor` → the existing `phase_k_vcs_upstream` job (AD-23 — each yields a
    `RunRequest` for a job C1 already built; NO second execution plane), both targeting the two
    upstream surfaces A3 flipped to `IncrementalParquetDataset` (AD-5 — the sensor only TRIGGERS;
    the run re-fetches only TTL-stale rows). Event source = **RSS/poll cursor (resolved over webhooks
    — a webhook needs an always-on bound public ingress, the Q2 daemon-footprint cost, and can't be
    exercised offline); the source is INJECTABLE and defaults to an offline no-op (`offline_event_source`
    → `[]`)**, so a built `defs` carries NO network dependency. Sensors ship `default_status=STOPPED` —
    nothing auto-starts. The ACTUAL bring-up is the attended Q2 boundary: standing up a
    `dagster-daemon`, turning the sensors RUNNING, injecting the LIVE RSS/poll feed readers
    (PyPI `updates.xml`, per-repo `releases.atom`) in place of the offline no-op, and observing real
    incremental runs fire. Do NOT weaken the dryrun gate to unattended-execute a live daemon or bind a
    socket (NFR-12). Mirrors DW-C1-1 (live schedule bring-up) and DW-D3-1 (live LLM backend).
  evidence: `dagster definitions validate -m pyforge.atlas.orchestration.definitions` passes offline;
    `tests/orchestration/test_definitions_dryrun.py` (+12: sensors enumerate + target real jobs, a
    simulated event via `build_sensor_context` + an injected fixture source → one `RunRequest` for the
    right incremental job with the cursor advancing, no-event/duplicate/malformed/raising → `SkipReason`,
    `default_status=STOPPED`, offline-default-is-no-op) + the AD-1 import-ban (`tests/catalog/test_no_inline_io.py`,
    now covering `orchestration/event_source.py` via rglob — it imports no dagster). The live feed
    readers do not exist in-package (injected, mirroring the B5/B7/B8 injected-fetcher deferrals).
