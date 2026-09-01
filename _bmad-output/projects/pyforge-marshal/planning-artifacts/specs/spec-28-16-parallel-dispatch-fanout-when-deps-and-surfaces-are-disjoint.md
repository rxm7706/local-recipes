---
title: 'Parallel dispatch fan-out when deps and surfaces are disjoint (Story 28.16, Epic 28)'
type: 'feature'
created: '2026-09-01'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: 'NO_VCS'
difficulty: medium
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-parallel-dispatch-fanout/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-parallel-dispatch-fanout/wave-scheduler.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-28-12-dependency-derived-dispatch-ordering.md
  - docs/dreams/marshal-parallel-dispatch-fanout.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** On a single station, Story **22.5** refuses any second dispatch while
*any* story is `LIVE`, even when candidates share no dependency edge and their
AD-27 effective frozen surfaces are pairwise disjoint. Unrelated backlog stories
queue behind slow or zombie head-of-line stories whose WIP cannot collide with
them. Cross-station parallelism works; within-station width does not.

**Approach:** Add opt-in **wave scheduling** (default `max_parallel=1`, serial
unchanged): among deps-ready backlog stories (shared ready-set with Story
**28.12**), launch up to policy cap when surfaces are provably disjoint; narrow
`station_in_flight_conflict()` to refuse only on dependency, surface overlap, or
same-key redispatch — not merely any LIVE story; journal `dispatch-wave` for
observability. Preserve **22.2** per-story LIVE semantics unchanged.

## Acceptance Criteria

- Given `dispatch.max_parallel=2` and two backlog stories whose dependencies are
  satisfied and effective surfaces are pairwise disjoint, when `factory drain`
  runs, then both stories dispatch in one wave on separate worktrees and
  branches.
- Given `max_parallel` unset or `1`, when drain runs, then behavior is
  byte-identical to today's serial within-station drain.
- Given story A `LIVE` by git facts on station S and story B ready with disjoint
  surface and no dependency on A, when dispatch considers B, then B is not
  refused by `MRS-DISP-021` solely because A is live.
- Given story A `LIVE` and story B whose effective surface intersects A's, when
  dispatch considers B, then B is refused with `surface-overlap` evidence.
- Given a wave where one member verify-fails and another succeeds, when outcomes
  are recorded, then the survivor may land independently; the failed member
  blocks only its declared dependents in subsequent waves.
- Given `marshal status` or `fleet-picture` during a two-member wave, when
  rendered, then both in-flight story keys and the wave id are visible.

## Boundaries & Constraints

**Always:** Write artifacts under
`_bmad-output/projects/pyforge-marshal/planning-artifacts/` literally.
`BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`.
Ledger key `28-16-parallel-dispatch-fanout-when-deps-and-surfaces-are-disjoint`.

**Block If:** A change weakens `judge_dispatch_completion()` LIVE semantics,
allows fan-out without declared cap, or fan-outs stories with unknown/empty
surface together.

**Never:** Replace Story 28.12 ordering; duplicate topo-sort; shared worktree;
weaken 22.3 verify-before-land.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_fleet.py` — wave batch builder, ready-set composition with 28.12 helper
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` — narrowed `station_in_flight_conflict`, `--max-in-flight` / policy cap
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_fleet_supervisor/__main__.py` — wave wait loop between ticks
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py` — surface overlap helper reuse (`MRS-DISP-022` path sets)

## Tasks & Acceptance

**Execution:** Implement CAP-1..CAP-5 from
`spec-marshal-parallel-dispatch-fanout/SPEC.md`. Add regression tests for
default-serial, two-member disjoint wave, surface-overlap refusal, zombie-A /
unrelated-B allowed, asymmetric wave terminalization.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 28.16 and spec-marshal-parallel-dispatch-fanout CAP-1..5.
**Deps:** 28.12 (ready-set / topo hook — ship first or land shared library in
same PR tranche). Motivating incident: `docs/dreams/marshal-parallel-dispatch-fanout.md`
(2026-09-01 Epic 28 + atlas drain). Sibling to 28.12 — not scope creep on
ordering.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, including wave + conflict tests.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass.

## Spec Change Log

- 2026-09-01: drafted via `bmad-spec` from `docs/dreams/marshal-parallel-dispatch-fanout.md` (decomposition: Story 28.16, sibling to 28.12)
- 2026-09-01: implemented via `bmad-build-auto` — wave scheduler, narrowed in-flight guard (parallel mode only), dispatch-wave journal, status overlay, `--max-in-flight` CLI + supervisor threading
- 2026-09-01: verification pass — AD-23 guard fix in `spec_deps.py`, AD-27-aware overlap test fix, CAP-3 status tests (`test_dispatch_wave_status.py`)

## Review Triage Log

### 2026-09-01 — Review pass (verification)
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 1, low 2)
- defer: 0
- reject: 0
- addressed_findings:
  - `[medium]` `[patch]` AD-23 meta guard flagged inline `{epic}.{num}` f-strings in `core/spec_deps.py` — replaced with concatenation before `normalize()`.
  - `[low]` `[patch]` `test_surface_overlap_refuses_second_dispatch` used a candidate spec glob that AD-27 intersection emptied; aligned candidate surface with policy default so effective-surface overlap is exercised.
  - `[low]` `[patch]` Added `test_dispatch_wave_status.py` for `latest_dispatch_wave_id` and fleet-row `dispatch_wave_id` / `dispatch_in_flight_stories` (CAP-3).

### 2026-09-01 — Review pass (initial)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none

## Auto Run Result

**Summary:** Story 28.16 adds opt-in parallel dispatch fan-out for factory drain when
`max_parallel > 1` (policy or `--max-in-flight`). Serial mode (`max_parallel=1`, default)
preserves byte-identical blanket `MRS-DISP-021` refusal. Parallel mode narrows
`station_in_flight_conflict()` to same-key, dep-edge, and surface-overlap only; builds
wave batches from deps-ready backlog with pairwise-disjoint effective surfaces; journals
`dispatch-wave`; exposes wave id and all in-flight story keys in status/fleet-picture.

**Files changed:**
- `core/spec_deps.py` — shared deps graph + ready-backlog helpers (28.12 hook); AD-23-safe key assembly
- `core/dispatch_fleet.py` — `WaveBatch`, `build_wave_batch()`, `ordered_ready_backlog()`
- `core/dispatch.py` — `KIND_DISPATCH_WAVE`
- `cli/dispatch.py` — narrowed guard (parallel only), wave dispatch in `execute_fleet_cycle`, wave journal, `--max-in-flight`, supervisor threading
- `cli/status.py` — multi-story in-flight + wave id overlay
- `core/status.py` — `dispatch_wave_id`, `dispatch_in_flight_stories` fields
- `core/findings.py`, `core/verdict.py` — `MRS-DISP-034/035`, `MRS-DRAIN-016`
- `dispatch_fleet_supervisor/__main__.py` — `--max-in-flight` on supervised ticks
- `tests/unit/test_spec_deps.py`, `test_wave_scheduler.py`, `test_dispatch_wave_status.py` — regression tests
- `tests/unit/test_dispatch_station_guard.py`, `test_dispatch_fleet.py`, `test_findings.py` — updated/extended

**Review:** Self-review + verification pass; 3 patch findings fixed (see triage log).

**Verification:** PASS
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 7290 passed (fast suite, excludes `@pytest.mark.slow`)
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — 118 passed

**Residual risks:** End-to-end two-member wave fixture against real harness not added;
asymmetric wave terminalization relies on existing per-story gate ladder (unchanged by design).
