---
title: 'Story C1 (4.1): Integrate `kedro-dagster` for scheduling + execution'
type: 'feature'
status: shipped
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'NEVER AUTHORED as a file — wave B9-H4 ran through the in-session agent loop, not bmad-create-story (which wrote files only for waves 0/A/B1-B8), confirmed by the migration session itself. Nothing was lost; there is no original to recover. Intent+ACs below are the real epics.md contract.'
enriched: '2026-07-25 (merged PR #84 body + main commit log; dev narrative recovered, review-triage partial)'
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
> at `../../spec-archive/retro-story-files/4-1-c1.md` — the operator's web-session archive.

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
- **Invariants:** AD-6, AD-1 (`kedro-dagster` is replaceable glue; no upward imports), AD-23 (one execution plane; run admission serializes per dataset set — **admission clause RESTORED 2026-07-29: retracted 2026-07-27 as unimplemented (`AUD-ATLAS-046`), built and gated by Story 10.6 (`admission.py` + `settings.HOOKS`), which closes `DW-AD23-1`. C1's `in_process` executor still only serializes ops within a run — and on the Dagster plane it is load-bearing for admission's release path, `DW-AD23-2`**).
- **Mode:** ATTENDED (bring-up boundary event — one of the five § 2.5 attended events; the `dagster-dryrun` gate it builds is loop-consumable thereafter).
- **Gating question:** **Q2** — default adopted (above); re-verify the Dagster bet at wave start (release cadence under Prefect, `kedro-dagster` compatibility, Components/Prefect-deployer ramps).
- **Verify gate:** **builds `dagster-dryrun`**.
- **Depends on:** Epic 3 complete (nodes + refresh assets to schedule).

## Tasks / Subtasks

*(Derived from the ACs — no original task breakdown was authored for this loop-run story.)*

- [x] schedules exist as Dagster Schedules encoding the `guides/atlas-operations.md` cadence table (bootstrap weekly; F/H/K/L/E.5 + G-after-vdb daily; E/J/M every 6 h; N hourly per maintainer; refresh assets weekly)
- [x] the three bootstrap profiles (maintainer / admin / consumer) exist as named Dagster job configurations with the guide's override precedence (explicit run-config/env beats profile defaults)
- [x] retries + phase state are observable in the Dagster UI
- [x] timeouts are per-node: a cold-run Phase R overrun can no longer abort Phase F/K/N — the legacy 1800 s `cf_atlas_core` defect is demonstrably retired
- [x] a `dagster-dryrun` verify task exists (definitions load, schedules enumerate — no live execution); the schedule bring-up itself is an attended event (Q2)
- [x] Phase P stays `PHASE_P_ENABLED=1`, admin-config-only, never a default schedule.

## Dev Notes

**Planning metadata (from `epics.md`):**

- **FRs:** FR-6.
- **Invariants:** AD-6, AD-1 (`kedro-dagster` is replaceable glue; no upward imports), AD-23 (one execution plane; run admission serializes per dataset set — **admission clause RESTORED 2026-07-29: retracted 2026-07-27 as unimplemented (`AUD-ATLAS-046`), built and gated by Story 10.6 (`admission.py` + `settings.HOOKS`), which closes `DW-AD23-1`. C1's `in_process` executor still only serializes ops within a run — and on the Dagster plane it is load-bearing for admission's release path, `DW-AD23-2`**).
- **Mode:** ATTENDED (bring-up boundary event — one of the five § 2.5 attended events; the `dagster-dryrun` gate it builds is loop-consumable thereafter).
- **Gating question:** **Q2** — default adopted (above); re-verify the Dagster bet at wave start (release cadence under Prefect, `kedro-dagster` compatibility, Components/Prefect-deployer ramps).
- **Verify gate:** **builds `dagster-dryrun`**.
- **Depends on:** Epic 3 complete (nodes + refresh assets to schedule).

### Implementation notes

<!-- DERIVED 2026-07-27 by reading the shipped code (PR #84). No original dev-session
     notes existed for this story; this is what the merged implementation actually does. -->

**One module holds the whole binding.** `orchestration/definitions.py` is the
*replaceable-glue* boundary the kernel promises. `dagster` and `kedro_dagster` are imported
**only** here — never by pipeline, node, dataset, or MCP code (AD-1). That single-module
containment is what makes the "the orchestrator is swappable glue" claim structural rather
than aspirational, and `tests/catalog/test_no_inline_io.py` was extended in this PR to
enforce the import-direction ban.

**It wraps the execution plane; it never adds one.** The glue takes
`kedro_dagster.KedroProjectTranslator` output and layers exactly four things on top:
schedules, profiles, tags, and per-node timeouts. Every cadence job is an **op-subset of
the single migrated `__default__` DAG** — which is why cross-pipeline phases (E + J + M)
compose into one job without any procedural driver (FR-2 / AD-3). There is no second
execution path.

**Per-op timeouts retire a real failure class.** Every op carries its own
`dagster/max_runtime` budget from `NODE_TIMEOUTS`. The legacy orchestrator had a single
`1800s` `cf_atlas_core` timeout that could silently drop a phase and still score the run
green. Making the budget per-op means an overrunning node can no longer abort its
siblings — the coarse-cap silent-drop class is retired *structurally*, not by raising the
cap.

**Phase P stays admin-only.** The BigQuery-backed monthly-downloads phase is
admin-config-only and never appears on a default schedule. The dryrun gate asserts this,
so making it a default is a test failure rather than a surprise bill.

**Profiles resolve with explicit-beats-default precedence.** The three bootstrap profiles
(maintainer / admin / consumer) are named run configurations via `resolve_profile_config`;
explicit run-config always beats a profile default.

**Environment choice is deliberate.** Translation runs against the Kedro `local` env, which
layers `conf/local/credentials.yml` placeholder stubs over `base` so credential-scoped
catalog entries resolve **offline**. `KEDRO_ENV` overrides it for real deployments. The
project root is resolved from `__file__`, not the cwd, so the definitions build the same
way regardless of where Dagster is invoked from.

**What this story deliberately did not do.** Building the definitions performs **no network
IO and no live execution**. The `dagster-dryrun` gate imports the module, builds `defs`,
and asserts that schedules enumerate, jobs resolve, and each op has an independent timeout.
The live daemon and any scheduled run are the attended bring-up, deferred as DW-C1 — see
the DW ledger section below. `resolve_profile_config` is consequently exercised only by the
gate; `build_definitions` does not call it, which is structural scope by design for the
attended boundary.

### References

- [Source: _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md#Story-C1]
- [Source: docs/specs/cfe-atlas-datapipeline-kedro-migration.md#§9-Story-C1]
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
| Pull request | **#84** — story(C1): kedro-dagster orchestration glue + dagster-dryrun gate (FR-6) |
| Merged | 2026-07-18 |
| Diff | 7 files, +804 / -7 |
| Test files touched | 3 |

**Commits**

- `166eb42` story(C1): kedro-dagster orchestration glue + dagster-dryrun gate (FR-6)

**File list** *(exact, from the merged diff)*

```
  453 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/orchestration/definitions.py
  249 +     0 -  src/shared/packages/pyforge-atlas/tests/orchestration/test_definitions_dryrun.py
   59 +     7 -  src/shared/packages/pyforge-atlas/tests/catalog/test_no_inline_io.py
   23 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/orchestration/__init__.py
   15 +     0 -  src/shared/packages/pyforge-atlas/conf/base/dagster.yml
    4 +     0 -  pixi.toml
    1 +     0 -  src/shared/packages/pyforge-atlas/tests/orchestration/__init__.py
```

## Dev Agent Record

### Agent Model Used

In-session BMAD agent loop (draft → 2× adversarial review → 1× independent fresh-eyes review → real-gate verify), not a `bmad-dev-story` story-file run.

### Completion Notes List

- **Impl commit `166eb42`** — story(C1): kedro-dagster orchestration glue + dagster-dryrun gate (FR-6)
  - Compiles the migrated Kedro DAG into Dagster Definitions via
  - KedroProjectTranslator (orchestration/definitions.py — the single AD-1 glue
  - seam) with:
  - - Schedules encoding the atlas-operations.md cadence table (bootstrap weekly;
  - F/H/K/L/E.5 + G-after-vdb daily; E/J/M every 6h; N hourly; refresh assets
  - weekly). Phase P deliberately gets NO schedule.
  - - Three bootstrap profiles (maintainer/admin/consumer) as resolve_profile_config
  - with precedence run-config > env > profile default.
  - - Per-op timeouts: each op carries its OWN dagster/max_runtime tag (no single
  - job/run-level timeout) — the structural retirement of the legacy 1800s
  - cf_atlas_core monolith. Operative F/K/N-vs-Phase-R isolation is delivered by
  - job separation (R rides only weekly bootstrap; F/K/N are own scheduled jobs).
  - - Phase P admin-config-only, reachable ONLY via the unscheduled
  - phase_p_pypi_downloads job (AC-6).
  - - dagster-dryrun gate: definitions load + schedules enumerate + jobs resolve +
  - per-op independent timeout + Phase-P-not-scheduled + profile precedence, all
  - offline, NO live execution. Ships as tests/orchestration (19) + a pixi task.
  - Invariants: AD-1/AD-6 — only the glue imports dagster/kedro_dagster, kedro_mcp
  - banned everywhere incl. the glue (two-scan import-ban test); AD-23 — one
  - execution plane via the kedro_run resource.
  - ATTENDED scope: this is the offline-buildable half; the live schedule bring-up
  - (daemon, RUNNING schedules, per-op runtime enforcement, profile run-wiring) is
  - DEFERRED to the attended Q2 event (DW-C1-1/-2), gate never weakened (NFR-12).
  - Reviewer fixes applied: AD-1 exemption scoped so kedro_mcp stays banned in the
  - glue (was whole-denylist exempt); hook-op detection uses a stable name-prefix
  - not the fragile _hook_ infix; timeout docstring no longer overclaims runtime
  - enforcement. 512 passed (+20); dagster definitions validate passes offline.

## Review Triage Log

No separate review-fix commit; findings (if any) folded into the impl commit. Full review threads on PR `#84`.

## Dev narrative — recovered from the merged record

> The original spec's `## Dev Notes` / `## Review Triage Log` were lost with the Tier-3
> worktree teardown (this story was built in claude.ai/code web session
> `01FYyQvBJuXwySiaMUUYCqBZ`; see `README.md`). The narrative below is reconstructed from
> the **authoritative merged record** — the story's PR body and its commits on `main` —
> **not** a regeneration. If the verbatim original is recovered from the web session, it
> supersedes this section.

### Dev summary — merged PR #84: story(C1): kedro-dagster orchestration glue + dagster-dryrun gate (FR-6)

## Deferred Work (DW ledger)

### DW-C1-1 — the live Dagster schedule bring-up (ATTENDED, Q2) — DEFERRED to the wave-boundary event
- source_spec: `c1-integrate-kedro-dagster-for-scheduling-execution.md`
  summary: C1 shipped the offline glue (`orchestration/definitions.py`) + the `dagster-dryrun` gate (definitions load, schedules enumerate, jobs resolve, per-op timeout tags, Phase-P admin-only) — all verified with NO live execution. The actual schedule BRING-UP is the attended Q2 boundary: standing up a Dagster daemon (`dagster dev -m pyforge.atlas.orchestration.definitions`), turning the schedules RUNNING (they ship with no `default_status=RUNNING`, so nothing auto-starts), and observing real retries/phase-state in the UI. Do NOT weaken the dryrun gate to unattended-execute (NFR-12).
  evidence: `dagster definitions validate -m pyforge.atlas.orchestration.definitions` passes offline; `tests/orchestration/test_definitions_dryrun.py` (19) + the AD-1 import-ban (`tests/catalog/test_no_inline_io.py`) are the loop-consumable gate. `defs = build_definitions()` builds under blocked sockets (no network IO at import).

### DW-C1-2 — per-op runtime ENFORCEMENT + profile-config run-wiring are bring-up concerns (structural-only in C1)
- source_spec: `c1-integrate-kedro-dagster-for-scheduling-execution.md`
  summary: Two AC surfaces are STRUCTURAL in C1 and become operative only at the live bring-up (both reviewer-flagged, recorded not faked):
    (a) **Per-op timeout ENFORCEMENT.** Each op carries an independent `dagster/max_runtime` tag (the monolith is gone — no job/run-level timeout anywhere), but `dagster/max_runtime` is Dagster's run-monitoring tag, enforced by the DAEMON at bring-up. Today's operative isolation (a Phase-R overrun can't abort F/K/N) comes from JOB SEPARATION — Phase R rides only the weekly `bootstrap_data` job, F/K/N have their own scheduled jobs — not from the tag. Per-op runtime capping arrives with the daemon.
    (b) **Profile precedence run-wiring.** `resolve_profile_config` (maintainer/admin/consumer, precedence: run-config > env > profile default) is a verified pure function but is NOT yet attached to any job as `RunConfig`/`default_config`; a real run does not yet consume it. Wiring the resolved profile config into the job run-config is a bring-up step.
    Also deferred: the kedro-dagster `before/after_pipeline_run` hook ops exist only on the translated base graph and are filtered out of the derived/scheduled jobs — confirm at bring-up whether per-run session hooks are needed on the scheduled jobs or are intentionally base-only.
  evidence: `test_timeouts_are_not_a_single_monolith` + `test_every_op_has_its_own_timeout` prove the structural side; `resolve_profile_config` is exercised only by the gate, and `build_definitions` does not call it (structural-scope, by design for the attended C1 boundary).
