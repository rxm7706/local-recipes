---
title: 'Local-dev object storage — Silo default, Garage alternative, pixi-provisioned'
type: 'feature'
created: '2026-09-10'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - scripts/scribe_pg.py
  - scripts/scribe_install_nightly_trigger.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Nobody develops or tests against production StorageGRID. The AD-1 exception permits
object-storage *consumption*, but nothing pixi-installable exists locally to consume yet.

**Approach:** A new, separate pixi feature (not folded into `platform-dev`) carrying `silo`
(default, once Story 50.1 lands) and `garage` (alternative, already on conda-forge today) as
dependencies. A script mirroring `scripts/scribe_pg.py`'s exact shape — a real local server,
never a mock, `up`/`down`/`status` pixi tasks, idempotent, data under gitignored `var/` —
combined with the pluggable-backend pattern already built this session for
`scribe_install_nightly_trigger.py` (`PYFORGE_SCRIBE_TRIGGER_BACKEND`): here,
`PYFORGE_OBJECT_STORAGE_BACKEND`, default `silo`.

## Boundaries & Constraints

**Always:**
- A real local server for each backend — never a mock — matching the `scribe-pg` precedent
  ("an absent database can never read as a green suite").
- Data lives under gitignored `var/platform-object-storage/`, never committed.
- The new pixi feature is separate from `platform-dev`, matching the `scribe-pg`/pgvector win-64
  precedent — Garage has no win-64 build, so folding this into a feature that inherits the full
  workspace platform list would break that solve outright.
- `up`/`down`/`status` are idempotent — re-running `up` against an already-running instance
  re-asserts state rather than failing.

**Never:**
- Never require Silo's recipe (Story 50.1) to exist before this story's own Garage path can be
  developed and tested — Garage works today; Silo becomes real once 50.1 lands, both are built
  in the same story since the pluggable-selection logic is one piece of work.
- Never silently no-op on a platform a backend doesn't support (Garage on Windows) — refuse
  cleanly, name the gap, point at the alternative backend.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Default backend up | `PYFORGE_OBJECT_STORAGE_BACKEND` unset | Silo starts locally, `var/`-scoped data dir | N/A |
| Alternative backend up | `PYFORGE_OBJECT_STORAGE_BACKEND=garage` | Garage starts locally instead | N/A |
| Garage on Windows | `PYFORGE_OBJECT_STORAGE_BACKEND=garage`, win-64 | Refuses cleanly, names the gap, points at Silo | Typed refusal, not silent no-op |
| Idempotent `up` | Already running | Re-asserts state, does not fail or duplicate | N/A |
| `status` | Either backend | Reports whether the local server is listening | N/A |
| `down` | Either backend | Stops the local server; data directory survives | N/A |

</intent-contract>

## Code Map

- `pixi.toml` — new `[feature.platform-object-storage]` (dependencies + tasks)
- `scripts/platform_object_storage.py` — new, mirrors `scripts/scribe_pg.py`'s shape
- `var/platform-object-storage/` — gitignored, per-backend data dirs

## Tasks & Acceptance

**Execution:**
- `feature` — add the `platform-object-storage` pixi feature with `silo` + `garage` dependencies.
- `feature` — `scripts/platform_object_storage.py` with `up`/`down`/`status` subcommands,
  backend selection via `PYFORGE_OBJECT_STORAGE_BACKEND` (default `silo`).
- `feature` — Garage's win-64 gap refuses cleanly with a pointer to Silo.
- `feature` — pixi tasks `platform-object-storage-up`/`-down`/`-status` wiring the script.

**Acceptance Criteria:**
- Given neither Silo nor Garage is provisioned anywhere in this repo, when the new pixi feature
  and script are added, then `platform-object-storage-up`/`-down`/`-status` idempotently
  start/stop/report a real local S3-compatible server, defaulting to Silo.
- And `PYFORGE_OBJECT_STORAGE_BACKEND=garage` runs the identical lifecycle against Garage, with
  an honest, clean refusal (not a silent no-op) on win-64.
- And a fresh `pixi install -e platform-object-storage` resolves cleanly.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: full suite green

## Spec Change Log

## Review Triage Log
