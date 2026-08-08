---
title: 'Story C2 (4.2): Integrate `kedro-viz` + expose a pixi task'
type: 'feature'
status: shipped
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'NEVER AUTHORED as a file — wave B9-H4 ran through the in-session agent loop, not bmad-create-story (which wrote files only for waves 0/A/B1-B8), confirmed by the migration session itself. Nothing was lost; there is no original to recover. Intent+ACs below are the real epics.md contract.'
enriched: '2026-07-25 (merged PR #85 body + main commit log; dev narrative recovered, review-triage partial)'
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
> at `../../spec-archive/retro-story-files/4-2-c2.md` — the operator's web-session archive.

## Contract (from epics.md — verbatim, authoritative)

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

## Tasks / Subtasks

*(Derived from the ACs — no original task breakdown was authored for this loop-run story.)*

- [x] it launches the Kedro-Viz server
- [x] operators can inspect dataset schemas + data lineage in the browser.

## Dev Notes

**Planning metadata (from `epics.md`):**

- **FRs:** FR-6 (structural observability), whole-migration AC-3.
- **Invariants:** AD-1, AD-6.
- **Mode:** LOOP-E.
- **Gating question:** none (Q2 drained at C1).
- **Verify gate:** `dagster-dryrun` + `kedro-test` (existing gates; viz task smoke lands in the pixi task inventory).
- **Depends on:** C1.

### Implementation notes

<!-- DERIVED 2026-07-27 by reading the shipped code (PR #85). No original dev-session
     notes existed for this story; this is what the merged implementation actually does. -->

**The smallest story in the migration, and the shape is the point.** Two files, +66 lines:
a `viz` pixi task and `tests/orchestration/test_viz_loadable.py`. No source code was
written — Kedro-Viz consumes the existing DAG as-is. That it required no code is the
evidence that the declarative-DAG bet paid off: lineage visualization is a *consequence*
of the catalog, not a feature someone had to build.

**The gate asserts loadability, not rendering.** `test_kedro_viz_load_data_builds_the_atlas_dag_offline`
proves Viz can construct the atlas DAG **offline**; `test_viz_pixi_task_is_registered`
proves the task reached the operator's pixi inventory. Neither launches a browser or a
server — same posture as C1's `dagster-dryrun` and the other structural gates.

**One detail that matters more than it looks.** The task sets
`cwd = "src/shared/packages/pyforge-atlas"`, and the test resolves the project root from
`__file__` (`parents[2]`). The Kedro CLI needs the project cwd, so without the pin, `viz`
would render whatever stray project the operator happened to be standing in. `--no-browser`
keeps it headless-safe.

### References

- [Source: _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md#Story-C2]
- [Source: docs/specs/cfe-atlas-datapipeline-kedro-migration.md#§9-Story-C2]
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
| Pull request | **#85** — story(C2): integrate kedro-viz behind a pixi `viz` task (FR-6 / AC-3) |
| Merged | 2026-07-18 |
| Diff | 2 files, +66 / -0 |
| Test files touched | 1 |

**Commits**

- `d4d7372` story(C2): integrate kedro-viz behind a pixi 'viz' task (FR-6 / AC-3)

**File list** *(exact, from the merged diff)*

```
   61 +     0 -  src/shared/packages/pyforge-atlas/tests/orchestration/test_viz_loadable.py
    5 +     0 -  pixi.toml
```

## Dev Agent Record

### Agent Model Used

In-session BMAD agent loop (draft → 2× adversarial review → 1× independent fresh-eyes review → real-gate verify), not a `bmad-dev-story` story-file run.

### Completion Notes List

- **Impl commit `d4d7372`** — story(C2): integrate kedro-viz behind a pixi 'viz' task (FR-6 / AC-3)
  - Adds 'pixi run viz' (kedro viz run --no-browser, cwd = the atlas project) so an
  - operator inspects dataset schemas + data lineage in the browser instead of
  - reading orchestrator source.
  - Offline smoke (tests/orchestration/test_viz_loadable.py): asserts Kedro-Viz's
  - own load_data builds the migrated atlas DAG (8 pipelines / 40 nodes / 114
  - datasets) with no server + no network, and that the viz pixi task is registered
  - with the atlas cwd. AD-1/AD-6: kedro_viz is visualization glue imported ONLY in
  - this test, never in package code (the src-tree import-ban is untouched).
  - 514 passed (+2).

## Review Triage Log

No separate review-fix commit; findings (if any) folded into the impl commit. Full review threads on PR `#85`.

<!-- end retro story -->

## Dev narrative — recovered from the merged record

> The original spec's `## Dev Notes` / `## Review Triage Log` were lost with the Tier-3
> worktree teardown (this story was built in claude.ai/code web session
> `01FYyQvBJuXwySiaMUUYCqBZ`; see `README.md`). The narrative below is reconstructed from
> the **authoritative merged record** — the story's PR body and its commits on `main` —
> **not** a regeneration. If the verbatim original is recovered from the web session, it
> supersedes this section.

### Dev summary — merged PR #85: story(C2): integrate kedro-viz behind a pixi `viz` task (FR-6 / AC-3)
