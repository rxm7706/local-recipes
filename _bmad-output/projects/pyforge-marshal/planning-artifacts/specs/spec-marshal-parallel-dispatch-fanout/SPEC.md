---
id: SPEC-marshal-parallel-dispatch-fanout
spec: marshal-parallel-dispatch-fanout
status: shipped
updated: "2026-09-09"
owner-dream: docs/dreams/marshal-parallel-dispatch-fanout.md
covers-dreams:
  - docs/dreams/marshal-parallel-dispatch-fanout.md
companions:
  - wave-scheduler.md
surface:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_fleet.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_fleet_supervisor/**
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py
  - _bmad-output/projects/*/planning-artifacts/marshal-policy.toml
sources:
  - ../../../../../../docs/dreams/marshal-parallel-dispatch-fanout.md
related:
  - ../spec-marshal-single-story-dispatch/SPEC.md
  - ../spec-marshal-token-economy/SPEC.md
  - ../spec-28-12-dependency-derived-dispatch-ordering.md
open_questions: []
  # ANSWERED 2026-09-09, both retired (operator, fleet-readiness batch rows mars-B-B5 / mars-B-B6):
  # oq1 token-budget-aware cap vs fixed integer -> the cap STAYS A FIXED INTEGER. Budget
  #   awareness needs a measured baseline that does not exist (Stories 28.10/28.11 shipped a cost
  #   CATALOG, not a live meter); revisit only once Epic 33's benchmark artifact exists. Rejected:
  #   make it budget-aware now -- a second unfed dial.
  # oq2 precomputed surface index vs live intersection -> keep the LIVE effective-surface
  #   INTERSECTION each tick. The bottleneck is DECLARATION, not cost: `core/dispatch_fleet.py:770-790`
  #   refuses on unknown-surface, and under CAP-16 auto-derivation (`core/gate.py:348-423`) two
  #   same-station stories share a surface by construction, so no index helps until story specs
  #   declare their own `surface:`. Rejected as premature: it optimises a step that always refuses.
---

> **Canonical contract.** This SPEC and `wave-scheduler.md` are the complete,
> preservation-validated contract for parallel factory-dispatch fan-out. Story
> **28.12** (token-economy CAP-14) owns *ordering*; this spec owns *width*.
> Default behavior when `max_parallel` is unset remains serial (byte-identical to
> today).

# Wave scheduling when dependencies and surfaces are disjoint

## Why

Cross-station parallelism already works — Story **22.5** allows `pyforge-marshal`
and `pyforge-atlas` concurrently. Within one station, **22.5** refuses any
second dispatch while *any* journal row is `LIVE` (`MRS-DISP-021`), even when the
two stories share no `Deps:` edge and their effective frozen surfaces (AD-27)
are pairwise disjoint. Epic drains therefore queue unrelated stories behind a
zombie or slow head-of-line story whose WIP cannot collide with them — correct
per-story **22.2** semantics, unnecessarily coarse at the station mutex.

The 2026-09-01 Epic 28 + atlas campaign made this concrete: killing Claude
mid-28.7 left git-fact LIVE on 28.7 while atlas 23.1 ran fine cross-station;
within marshal, unrelated backlog stories still waited on the station slot.
Story **28.12** fixes order (topological sort from `Deps:`); this spec fixes
width (parallel-safe waves among the ready set).

## Capabilities

- **CAP-1**
  - **intent:** A **wave scheduler** on `factory drain` / fleet-supervisor ticks:
    among backlog stories whose dependencies are satisfied on the tracked ledger
    (same ready-set hook as 28.12), launch up to `dispatch.max_parallel` members
    per wave when every pair in the batch has **pairwise disjoint effective
    frozen surfaces** (AD-27 intersection machinery). Between waves, wait until
    every launched member reaches a **terminal dispatch outcome** before computing
    the next batch. Dependents never start in the same wave as an unfinished
    dependency.
  - **success:** With `max_parallel=2` and two ready stories whose surfaces are
    provably disjoint, both dispatch in one wave on separate worktrees/branches;
    with `max_parallel` unset or `1`, behavior is byte-identical to today's
    serial drain. A fixture pins two disjoint pyforge-marshal stories landing in
    one wave while a third overlapping story is refused with `surface-overlap`.

- **CAP-2**
  - **intent:** **Narrow `station_in_flight_conflict()`** (22.5 refinement): refuse
    story Y on station S only when an in-flight story X satisfies **any** of:
    (a) Y depends on X (transitive over declared `Deps:`), (b) effective surfaces
    of X and Y intersect, (c) same story key redispatch (`MRS-DISP-011`). Refuse
    **not** merely because X is `LIVE`. **`judge_dispatch_completion()` unchanged:**
    `LIVE := session_alive OR has_git_progress` per story worktree.
  - **success:** Story A with git-fact LIVE blocks story B only when B depends on
    A or surfaces overlap; unrelated story C with disjoint surface dispatches
    while A remains LIVE. Same-key redispatch and dependency edges still refuse.
    Regression tests cover the 2026-09-01 zombie shape (A live by git facts, C
    unrelated and disjoint → C allowed).

- **CAP-3**
  - **intent:** **`dispatch-wave` journal observability**: each wave records wave
    id, member story keys, applied cap, pairwise disjointness evidence (effective
    surface path sets or stable hashes), and refused candidates with reason
    (`dep-unmet`, `surface-overlap`, `cap`, `unknown-surface`). `marshal status`
    and `fleet-picture` show in-flight count per station and active wave id —
    not a flat single story key hiding concurrency.
  - **success:** A two-member wave produces one journal intent with both keys;
    status output names both in-flight stories and the wave id; a refused
    candidate names `surface-overlap` with the intersecting paths.

- **CAP-4**
  - **intent:** **Explicit cap, default serial:** `dispatch.max_parallel` in
    `marshal-policy.toml` (per station, default `1`) and optional CLI override
    (`--max-in-flight`, exact flag name at implementation). No silent raise;
    `fleet-picture` calls out when a station runs `>1`. `--stories` with parallel
    mode re-validates surfaces and refuses overlapping pairs even when the
    operator listed them — list is intent, not a safety waiver.
  - **success:** Absent policy key and flag → serial. Policy `max_parallel=3`
    with only two disjoint ready stories launches two. Attempt to set cap without
    journaling the effective value fails review — cap must be visible in wave
    journal and status.

- **CAP-5**
  - **intent:** **Compose with 28.12, do not duplicate:** ready-set and
    ledger-order tie-break come from the shared dependency-graph helper introduced
    for Story 28.12 (CAP-14). This spec adds batch selection and parallel launch
    only; it does not introduce a second topo-sort or reorder in-flight campaigns
    retroactively.
  - **success:** Ready-set computation is imported/shared with 28.12 tests; no
    second ordering module. Stories with **empty or unknown** effective surface
    never fan out with others (conservative default — serial until surface is
    declared).

- **CAP-6**
  - **intent:** Factory fan-out gets its **own `dispatch.max_parallel` policy key**, resolved
    by `cli/dispatch.py:893-902` independently of bmad-loop's `scm.max_parallel`
    (`core/policy.py:513`), which it falls back to today. One knob stops governing two
    unrelated concurrency models, and raising the dispatch cap stops firing
    `_max_parallel_clamp_finding` (`core/policy.py:1537-1551`) — whose message names
    `bmad_loop 0.9.0`, a false-context warn on the dispatch path.
  - **success:** A station declaring `dispatch.max_parallel = N` forms waves of up to N with no
    bmad-loop clamp advisory; a station declaring nothing behaves exactly as today (`1`); the
    bmad-loop knob continues to govern the spin engine alone.

## Partial wave failure (v1 default)

When wave members terminalize **asymmetrically** (one verify-fails, one lands):
each member is judged independently per existing gate ladder; survivors may land
without waiting for the failed member. The failed member blocks **only** stories
that declare a dependency on it — not unrelated ready stories in a subsequent
wave. Wave journal records per-member terminal outcome before the wave id closes.

## Explicit non-goals (v1)

- No shared worktree / multi-story branch
- No automatic retry of parallel wave members (28.13 stays separate)
- No cross-station batching
- No weakening verify-before-land (22.3) or per-story preserve (22.2)
- No bmad-loop Phase 5 `max_parallel` — factory dispatch owns this scheduler

## Decomposition

| Capability | Epic 28 story | Story spec |
|---|---|---|
| CAP-1..CAP-5 | **28.16** Parallel dispatch fan-out when deps and surfaces are disjoint | `spec-28-16-parallel-dispatch-fanout-when-deps-and-surfaces-are-disjoint.md` |
| CAP-6 | **33.8** `dispatch.max_parallel` + the first live fan-out wave | minted 2026-09-09 (Epic 33) |

Story **28.12** remains ordering-only (CAP-14). **28.16** deps: **28.12** (ready-set hook).

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — wave batch,
  narrowed conflict, journal, default-serial regression
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — no undeclared deps

## Assumptions

- `status: shipped` is **mechanism only.** CAP-1..CAP-5 shipped in Story 28.16 (wave scheduler
  `core/dispatch_fleet.py:750-790`; narrowed conflict guard `cli/dispatch.py:935`
  `station_in_flight_conflict(..., parallel_dispatch=False)`; wave journal
  `cli/dispatch.py:2775`), all `done`. `docs/dreams/marshal-parallel-dispatch-fanout.md`
  deliberately keeps `status: specified`: its own gate is a live proof, and none exists.

## Residual (carried into Story 33.8)

- `max_parallel` is `1` on all eight rendered loop homes and **no live wave has ever run** — the
  shipped scheduler has never formed a wave in the running estate.
- The cap reuses bmad-loop's `scm.max_parallel` rather than the `dispatch.max_parallel` key the
  Dream asked for. Now CAP-6.
- **Within-station fan-out cannot form a wave at all.** CAP-16 (Story 28.14) auto-derives
  `policy_surface` to the station's whole package tree, so two same-station stories overlap by
  construction and `core/dispatch_fleet.py:786` refuses. Fan-out requires story specs to declare
  their own `surface:` first. Two capabilities shipped a week apart in the same epic compose into
  a no-op; neither Spec recorded it until 2026-09-09.
- The `[epic_surfaces]` entries this Spec's `marshal-policy.toml` glob governs grew on 2026-09-09
  (marshal `"33"`; steward `"48"` and `"49"`). No fan-out semantics changed — those entries are
  the declaration `dispatch_fleet` reads.
