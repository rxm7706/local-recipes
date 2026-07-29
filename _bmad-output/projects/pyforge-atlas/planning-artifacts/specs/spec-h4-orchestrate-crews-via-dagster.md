---
title: 'Story H4 (9.4): Orchestrate Crews via Dagster'
type: 'feature'
status: shipped
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'NEVER AUTHORED as a file — wave B9-H4 ran through the in-session agent loop, not bmad-create-story (which wrote files only for waves 0/A/B1-B8), confirmed by the migration session itself. Nothing was lost; there is no original to recover. Intent+ACs below are the real epics.md contract.'
enriched: '2026-07-25 (merged PR #102 body + main commit log; dev narrative recovered, review-triage partial)'
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
> at `../../spec-archive/retro-story-files/9-4-h4.md` — the operator's web-session archive.

## Contract (from epics.md — verbatim, authoritative)

### Story H4 (9.4): Orchestrate Crews via Dagster

As the operator,
I want Dagster assets, sensors (new raw files), and schedules (weekly linting) triggering the Agno crews autonomously,
So that the factory layer runs itself.

**Acceptance Criteria:** (spec § 9 Story H4, binding)

**Given** the H2 crews and the C1 Dagster repository
**When** the assets/sensors/schedules land
**Then** an asset dry-run enumerates the crew assets
**And** a simulated new-raw-file event triggers the compile crew via a Sensor.

- **FRs:** FR-22(d), FR-6.
- **Invariants:** AD-22, AD-6, AD-23.
- **Mode:** LOOP-E (spec § 9 explicit).
- **Gating question:** none.
- **Verify gate:** `dagster-dryrun` (crew assets enumerate) + simulated-trigger fixture.
- **Depends on:** H1, H2, H3; C1.
- **DELIVERED (2026-07-18 — closes Wave H + the migration):** the Wave-H crews run on C1's single Dagster plane (AD-6/AD-23). `orchestration/definitions.py` gains crew ASSETS (`compiled_wiki` → CompileCrew, `wiki_lint_report` → LintCrew, `deps=[compiled_wiki]`), their asset-jobs (`wiki_compile_job`/`wiki_lint_job`), a weekly LINT schedule (`wiki_lint_schedule`, `0 6 * * 1`, § 7.2), and the new-raw-file compile SENSOR (`wiki_raw_file_sensor` → `wiki_compile_job`, ships STOPPED). The raw-scan + cursor-dedupe DECISION logic lives in `orchestration/wiki_events.py` (dagster-free — AD-1 holds; only definitions.py imports dagster). `dagster definitions validate` green; a simulated new-raw-file event (injected lister + `build_sensor_context`) → one `RunRequest` for the compile job. Live daemon + wiki-store bring-up DEFERRED (DW-H4). Gate `test_definitions_dryrun.py` H4 section (+12; C1/G3 invariants scoped to kedro op-jobs via `_kedro_jobs`). Independent review found 1 SHOULD-FIX (`_decode_cursor` crashed on a valid-JSON-but-nested cursor, breaking its "never a crash" contract) — fixed (filter to str inside the guard) + regression-tested; the `_kedro_jobs` scoping was verified NOT to weaken any C1/G3 guard.

## Tasks / Subtasks

*(Derived from the ACs — no original task breakdown was authored for this loop-run story.)*

- [x] an asset dry-run enumerates the crew assets
- [x] a simulated new-raw-file event triggers the compile crew via a Sensor.

## Dev Notes

**Planning metadata (from `epics.md`):**

- **FRs:** FR-22(d), FR-6.
- **Invariants:** AD-22, AD-6, AD-23.
- **Mode:** LOOP-E (spec § 9 explicit).
- **Gating question:** none.
- **Verify gate:** `dagster-dryrun` (crew assets enumerate) + simulated-trigger fixture.
- **Depends on:** H1, H2, H3; C1.
- **DELIVERED (2026-07-18 — closes Wave H + the migration):** the Wave-H crews run on C1's single Dagster plane (AD-6/AD-23). `orchestration/definitions.py` gains crew ASSETS (`compiled_wiki` → CompileCrew, `wiki_lint_report` → LintCrew, `deps=[compiled_wiki]`), their asset-jobs (`wiki_compile_job`/`wiki_lint_job`), a weekly LINT schedule (`wiki_lint_schedule`, `0 6 * * 1`, § 7.2), and the new-raw-file compile SENSOR (`wiki_raw_file_sensor` → `wiki_compile_job`, ships STOPPED). The raw-scan + cursor-dedupe DECISION logic lives in `orchestration/wiki_events.py` (dagster-free — AD-1 holds; only definitions.py imports dagster). `dagster definitions validate` green; a simulated new-raw-file event (injected lister + `build_sensor_context`) → one `RunRequest` for the compile job. Live daemon + wiki-store bring-up DEFERRED (DW-H4). Gate `test_definitions_dryrun.py` H4 section (+12; C1/G3 invariants scoped to kedro op-jobs via `_kedro_jobs`). Independent review found 1 SHOULD-FIX (`_decode_cursor` crashed on a valid-JSON-but-nested cursor, breaking its "never a crash" contract) — fixed (filter to str inside the guard) + regression-tested; the `_kedro_jobs` scoping was verified NOT to weaken any C1/G3 guard.

### Implementation notes

<!-- DERIVED 2026-07-27 by reading the shipped code (PR #102). No original dev-session
     notes existed for this story; this is what the merged implementation actually does. -->

**The closing story, and its claim is that there is no second scheduler.** The Wave-H crews
run on **C1's single Dagster plane** (AD-6/AD-23). `orchestration/definitions.py` gains crew
assets — `compiled_wiki` → `CompileCrew`, `wiki_lint_report` → `LintCrew` with
`deps=[compiled_wiki]` — their asset-jobs (`wiki_compile_job`, `wiki_lint_job`), a weekly lint
schedule (`wiki_lint_schedule`, `0 6 * * 1`), and a new-raw-file compile sensor
(`wiki_raw_file_sensor` → `wiki_compile_job`), shipped STOPPED like G3's.

**Decision logic stays dagster-free.** The raw-scan and cursor-dedupe logic lives in
`orchestration/wiki_events.py`, so AD-1's "only `definitions.py` imports dagster" rule holds
even as the orchestration surface grows. Same split as G3's `event_source.py` — the pattern
held across two waves, which is the evidence it was the right seam.

**The write boundary is restated at the asset level (AD-22).** Both asset descriptions say it
explicitly: the crews write **only** the wiki tree, never an atlas dataset. The lint asset is
read-only over the wiki.

**Scaffolding is idempotent so a crew never fails on a missing directory.** `_wiki_layout()`
calls `scaffold_wiki`, which only ever creates under the root and is non-destructive. The
wiki root resolves from `ATLAS_WIKI_ROOT` or defaults beside the project — host-agnostic, no
path baked in (AD-2).

**One scoping change worth understanding.** C1's and G3's invariants — every op carries its
own timeout, sensors target real jobs — were scoped to **kedro op-jobs** via `_kedro_jobs`,
because the new crew asset-jobs are not kedro op-jobs and would otherwise trip guards written
for a different job shape. The review explicitly verified this scoping **did not weaken** any
C1 or G3 guard. That verification is the load-bearing part: narrowing a guard's domain is
exactly how guards silently stop guarding.

**Review finding, and it is a good one.** `_decode_cursor` crashed on a valid-JSON-but-nested
cursor, breaking its own "never a crash" contract — fixed by filtering to `str` inside the
guard, with a regression test. A degrade path that itself has a crash path is not a degrade
path.

**Gate:** `test_definitions_dryrun.py` H4 section (+12); `dagster definitions validate` green;
a simulated new-raw-file event (injected lister + `build_sensor_context`) yields one
`RunRequest` for the compile job. Live daemon and wiki-store bring-up are DW-H4.

### References

- [Source: _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md#Story-H4]
- [Source: docs/specs/cfe-atlas-datapipeline-kedro-migration.md#§9-Story-H4]
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
| Pull request | **#102** — H4: orchestrate the Wave-H wiki crews via Dagster (FR-22(d)/FR-6) |
| Merged | 2026-07-18 |
| Diff | 4 files, +422 / -13 |
| Test files touched | 1 |

**Commits**

- `c8258b1` H4: orchestrate the Wave-H wiki crews via Dagster (FR-22(d)/FR-6)

**File list** *(exact, from the merged diff)*

```
  173 +    12 -  src/shared/packages/pyforge-atlas/tests/orchestration/test_definitions_dryrun.py
  156 +     1 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/orchestration/definitions.py
   92 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/orchestration/wiki_events.py
    1 +     0 -  _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
```

## Dev Agent Record

### Agent Model Used

In-session BMAD agent loop (draft → 2× adversarial review → 1× independent fresh-eyes review → real-gate verify), not a `bmad-dev-story` story-file run.

### Completion Notes List

- **Impl commit `6cc2dbf`** — H4: orchestrate the Wave-H wiki crews via Dagster (FR-22(d)/FR-6) (#102)
  - Wire the agno wiki crews onto C1's SINGLE Dagster plane (Wave H, spec § 7.2
  - / § 9 Story H4) — the final story of the Kedro migration.
  - orchestration/wiki_events.py (NEW, dagster-free — AD-1 holds; only
  - definitions.py imports dagster): the new-raw-file DECISION logic.
  - scan_raw_docs (filesystem read) + evaluate_raw_scan (cursor-dedupe: the
  - cursor stores the seen raw-doc name set; new names -> run with a
  - deterministic run_key, advance the cursor; nothing new -> skip, cursor
  - untouched). Mirrors event_source.py for G3.
  - orchestration/definitions.py (the AD-1 glue module):
  - - Crew ASSETS: compiled_wiki (CompileCrew: raw->compiled, staleness
  - forwarded) + wiki_lint_report (LintCrew over compiled/, deps=[compiled_wiki]).
  - The crews write ONLY the wiki tree (AD-22). resolve_wiki_root is env-driven
  - (ATLAS_WIKI_ROOT; host-agnostic AD-2); _wiki_layout scaffolds idempotently.
  - - Crew asset-jobs: wiki_compile_job / wiki_lint_job (define_asset_job).
  - - Weekly LINT schedule: wiki_lint_schedule (0 6 * * 1, § 7.2).
  - - New-raw-file compile SENSOR: build_wiki_compile_sensor -> wiki_raw_file_sensor
  - targets wiki_compile_job (AD-23 — the SAME plane, an existing job; no second
  - scheduler). Injectable raw_lister (offline scan by default); a simulated new
  - raw doc -> one RunRequest (cursor advances); nothing new / already-seen ->
  - SkipReason; a failing lister degrades to skip (never crashes the daemon).
  - Ships default_status=STOPPED.
  - - All wired into dg.Definitions(assets=..., jobs=... + [compile,lint], ...).
  - Test scoping: the C1/G3 invariants that iterate defs.jobs (per-op timeouts,
  - phase_state tags, retry policy, Phase-P scheduling) are scoped to the KEDRO
  - op-jobs via a new _kedro_jobs() helper — the Wave-H factory ASSET jobs are a
  - different kind of job and legitimately carry neither kedro ops nor those tags.
  - test_schedules_enumerate's expected scheduled-job set adds wiki_lint_job.
  - Verify gate: dagster definitions validate green; test_definitions_dryrun.py
  - H4 section (+12): assets enumerate, crew jobs resolve, weekly lint schedule
  - fires the lint job, sensor targets the compile job, a simulated new-raw-file
  - event -> RunRequest for the compile crew, no-new-file/already-seen ->
  - SkipReason, lister-error degrades to skip, ships STOPPED, + wiki_events unit
  - tests. AD-1 import-ban green over wiki_events.py. Full atlas suite 787 passed.
  - Live daemon + wiki-store bring-up DEFERRED (DW-H4); the crews' agno/LLM
  - synthesis is DW-H2, the wiki store is DW-H1. Also folds in the H4 DELIVERED
  - doc updates (epics + sprint-status; epic-9 retro marked required).
  - Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
  - Claude-Session: https://claude.ai/code/session_01FYyQvBJuXwySiaMUUYCqBZ
  - Review fix (folded in): _decode_cursor filtered to str inside the guard so a
  - valid-JSON-but-nested cursor ([{...}]/[[...]]) degrades to nothing-seen
  - instead of a TypeError that kills the sensor tick; +8 regression cases. Full
  - atlas suite 795 passed.
  - Co-authored-by: Claude <noreply@anthropic.com>

## Review Triage Log

No separate review-fix commit; findings (if any) folded into the impl commit. Full review threads on PR `#102`.

## Dev narrative — recovered from the merged record

> The original spec's `## Dev Notes` / `## Review Triage Log` were lost with the Tier-3
> worktree teardown (this story was built in claude.ai/code web session
> `01FYyQvBJuXwySiaMUUYCqBZ`; see `README.md`). The narrative below is reconstructed from
> the **authoritative merged record** — the story's PR body and its commits on `main` —
> **not** a regeneration. If the verbatim original is recovered from the web session, it
> supersedes this section.

### Dev summary — merged PR #102: H4: orchestrate the Wave-H wiki crews via Dagster (FR-22(d)/FR-6)

## Deferred Work (DW ledger)

### DW-H4 — the live factory-crew daemon bring-up (sensor RUNNING + weekly lint + live wiki store) (ATTENDED) — DEFERRED
- source_spec: `cfe-atlas-datapipeline-kedro-migration.md` (Story H4, § 7.2, FR-22(d)/FR-6)
  summary: H4 shipped the BUILDABLE half of the factory orchestration — the crew ASSETS
    (`compiled_wiki`, `wiki_lint_report`), their asset-jobs (`wiki_compile_job`, `wiki_lint_job`),
    the weekly LINT schedule (`wiki_lint_schedule`, `0 6 * * 1`), and the new-raw-file compile
    SENSOR (`wiki_raw_file_sensor`) — all wired into C1's `defs` on the SAME Dagster plane
    (AD-6/AD-23; no second scheduler) and verified OFFLINE: `dagster definitions validate` passes,
    the assets enumerate, and a simulated new-raw-file event (injected `raw_lister` +
    `build_sensor_context`) yields one `RunRequest` for the compile job (dedupe/degrade covered).
    The raw-scan DECISION logic lives in `orchestration/wiki_events.py` (dagster-free — AD-1 holds;
    only `definitions.py` imports dagster). The ACTUAL bring-up is the attended Q2/daemon event:
    stand up a `dagster-daemon`, turn `wiki_raw_file_sensor` RUNNING against the LIVE wiki store
    (the DW-H1 MinIO/PostgreSQL + `ATLAS_WIKI_ROOT`), let the weekly lint schedule fire, and observe
    real compile/lint crew runs materialize the assets. The sensor ships `default_status=STOPPED`
    (nothing auto-starts). Do NOT weaken the dryrun gate to unattended-execute a live daemon or bind
    a socket (NFR-12). Mirrors DW-C1-1 (live schedule) + DW-G3 (live sensor daemon).
  evidence: `orchestration/wiki_events.py` imports only stdlib (AD-1 import-ban green over it);
    `dagster definitions validate -m pyforge.atlas.orchestration.definitions` passes offline;
    `tests/orchestration/test_definitions_dryrun.py` H4 section (+12: assets enumerate, crew jobs
    resolve, weekly lint schedule, sensor targets the compile job, simulated new-raw-file →
    RunRequest, no-new-file/already-seen → SkipReason, lister-error degrades, ships STOPPED, +
    wiki_events unit tests). The live wiki store is DW-H1; the crews' agno/LLM synthesis is DW-H2.
