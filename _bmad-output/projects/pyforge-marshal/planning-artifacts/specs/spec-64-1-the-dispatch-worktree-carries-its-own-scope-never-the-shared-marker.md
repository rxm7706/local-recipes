---
title: '64.1: The dispatch worktree carries its own scope, never the shared marker'
type: 'fix'
created: '2026-09-27'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `dispatch_once` refuses `MRS-DISP-041` unless the PRIMARY checkout's shared active-project marker (`_bmad/custom/.active-project`) and both compatibility links (`_bmad-output/{planning,implementation}-artifacts`) name the dispatch slug: `_dispatch_scope_refusal` in `cli/dispatch.py` calls `verify_scope(repo_root, slug)` before any launch work. On 2026-09-25 `marshal factory dispatch pyforge-marshal 46.9` was refused while pyforge-steward's chain held that marker, and `BMAD_ACTIVE_PROJECT=pyforge-marshal` had no effect; on 2026-09-27 the marker still names pyforge-steward, so every non-steward dispatch and every drain cycle through `dispatch_once` refuses. Nothing the dispatch launches reads that marker: the session runs with `cwd` set to its own fresh dispatch worktree (a `git worktree add`, where the gitignored marker and links do not exist) and `BMAD_ACTIVE_PROJECT=<slug>` in its environment (`adapters/harness_bmadbuild.py`), which `_bmad/scripts/resolve_config.py` ranks above any marker; every launcher read and write is a physical `_bmad-output/projects/<slug>/` path. The check guards a resource no dispatch write resolves through, and it lets only one station dispatch at a time.

**Approach:** move the scope check to the root the session runs in, the way `marshal init` does for a loop home (`cli/init.py`: `verify_scope(home, slug)`, MRS-INIT-003). `_dispatch_scope_refusal` keeps only the parent-environment check: a `BMAD_ACTIVE_PROJECT` naming another slug refuses `MRS-DISP-041` before any worktree work, unchanged. After `_ensure_dispatch_worktree` returns a worktree and before anything launches, a new step writes each MISSING corner of the worktree's own triangle through `FsPort` — the marker (`<slug>` plus a newline, `write_text_atomic`) and both links (relative `projects/<slug>/planning-artifacts` and `projects/<slug>/implementation-artifacts`, `repoint_symlink_atomic`) — and never touches a corner that already exists. It then calls `verify_scope(worktree, slug)`. Any drift (a corner naming another project, an unrecognized link shape, a non-link where a link belongs) refuses `MRS-DISP-041` naming the worktree and all three found values, with no harness launch and no run directory. Dispatch never reads or writes the primary checkout's marker or links. The Dream seed's flip under a lock is rejected: it would repoint every primary-checkout writer that does not take the lock for the length of each launch (the Spec memlog's 2026-09-27 direction entry has the evidence).

Ledger key: `64-1-the-dispatch-worktree-carries-its-own-scope-never-the-shared-marker`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-273 (FR-219).

## Acceptance Criteria

- Given the primary checkout's marker and both links name `pyforge-steward` When `dispatch_once(slug="pyforge-marshal", story=<a backlog story with a tracked spec>)` runs against fakes Then the fake harness records exactly one launch whose `project_slug` is `pyforge-marshal`, no `MRS-DISP-041` finding is returned, and the primary's marker bytes and both `readlink` targets are identical before and after
- Given the same run When its writes are listed (the fake filesystem's write log and the fake VCS's worktree adds) Then every written path is under the dispatch worktree or `_bmad-output/projects/pyforge-marshal/`, and `verify_scope(worktree, "pyforge-marshal")` returns `None` afterwards
- Given the same primary When `execute_fleet_cycle` runs one cycle scoped to a non-steward station with one backlog story Then that story reaches the launch, with no `MRS-DISP-041` refusal
- Given `BMAD_ACTIVE_PROJECT=pyforge-steward` in the parent environment and slug `pyforge-marshal` When `dispatch_once` runs Then it returns `MRS-DISP-041` naming both projects, adds no worktree and launches nothing (`test_dispatch_refuses_bmad_active_project_env_disagreement` stays green unchanged)
- Given an existing dispatch worktree whose own marker names `pyforge-steward` When `dispatch_once(slug="pyforge-marshal", …)` reaches it Then it refuses `MRS-DISP-041` naming the worktree, launches nothing, creates no run directory, and leaves that marker byte-identical
- Given an existing dispatch worktree whose `planning-artifacts` link has an unrecognized target (an absolute path or a foreign shape) When dispatch reaches it Then it refuses `MRS-DISP-041` and leaves the link as found
- Given `test_dispatch_refuses_triangle_drift_before_launch` (Story 33.9: a primary triangle on steward refuses) When this story lands Then it is replaced by the launch test above — the refusal it pinned is the behaviour CAP-273 retires — and no other test in `test_dispatch.py` changes its expectation

## Boundaries & Constraints

**Always:** Implement only the Surface named in `epics.md` Story 64.1. `verify_scope` (`scope.py`) stays the one triangle check and is called unchanged. Writes go through `FsPort` only (AD-11's observable write boundary). A corner is written only when absent, and the seeded shapes are exactly the relative `projects/<slug>/<name>` targets `verify_scope` recognizes. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not read, write, repoint, flip or lock the primary checkout's marker or links; add no advisory lock to the launch.
- Do not repoint or overwrite an existing worktree corner that names another project or has an unrecognized shape — refuse `MRS-DISP-041`.
- Do not change `scope.py`, `scripts/bmad-switch` or `cli/init.py`; do not add a Tier-3 backlink to the dispatch worktree (out of scope).
- Do not weaken or reorder the parent-environment check.
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`; do not run `scripts/bmad-switch`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| primary on another station | primary marker and links name pyforge-steward; slug pyforge-marshal; no env | launch proceeds; worktree triangle written for pyforge-marshal; primary unchanged | none |
| primary triangle absent or unrecognized | no primary marker, or missing links | launch proceeds (the primary is never read) | none |
| env contradiction | `BMAD_ACTIVE_PROJECT=pyforge-steward`, slug pyforge-marshal | `MRS-DISP-041`; no worktree added | refused before any worktree work |
| env agrees | `BMAD_ACTIVE_PROJECT=pyforge-marshal` | launch proceeds | none |
| fresh worktree | no triangle in the worktree | three corners written; `verify_scope` passes | a failed corner write is `MRS-DISP-006` (cannot provision), no launch |
| reused worktree, agreeing triangle | all three corners name the slug | no write; `verify_scope` passes | none |
| reused worktree, foreign marker | worktree marker names pyforge-steward | `MRS-DISP-041`; marker untouched; no launch, no run dir | refused |
| reused worktree, unrecognized link | absolute or foreign-shape link | `MRS-DISP-041`; link untouched | refused |
| drain cycle | primary on pyforge-steward; a non-steward station with a backlog story | the story reaches the launch | none |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` -- `_dispatch_scope_refusal(slug)` narrowed to the parent-environment (`BMAD_ACTIVE_PROJECT`) check only, its primary-checkout `verify_scope(repo_root, slug)` call retired; new `_seed_dispatch_worktree_scope(*, fs, worktree, slug)` writes each missing worktree-triangle corner through `FsPort` then calls `verify_scope(worktree, slug)`, returning `MRS-DISP-006` on a write failure or `MRS-DISP-041` on drift; wired into `dispatch_once` right after the worktree path is resolved and before output-layer seeding.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/scope.py` -- read-only: `verify_scope`, `format_scope_drift`, `UNRECOGNIZED`, the marker/link-shape contract. Unchanged (spec Never rule).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/fs_local.py` -- read-only: `LocalFs`'s `read_symlink_target`/`repoint_symlink_atomic`/`exists` semantics, modeled faithfully in the test doubles below.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_core.py` -- read-only reuse point: `_ensure_dispatch_worktree` already returns early when `worktree.exists()`, before calling `vcs.add_worktree` -- the mechanism new tests use to pre-seed a worktree-side triangle with no `FakeVcs` registration needed.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch.py` -- `FakeFs.write_text_atomic` and `.read_text` made real-disk-backed (the latter falls back to disk when absent from the in-memory dict, needed because `scope_triangle.py`'s seeding helper writes straight to disk, bypassing `FakeFs`); added `read_symlink_target`/`repoint_symlink_atomic`/`exists`. Retired `test_dispatch_refuses_triangle_drift_before_launch` (AC #7), replaced with `test_dispatch_launches_despite_primary_triangle_naming_another_station`. Added the four worktree-triangle tests (AC #1, #2, #5, #6).
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_completion.py` -- same `FakeFs` real-disk-backing fix (write + read + symlink methods), no behavioral test changes; needed so its `dispatch_once` exercises don't regress once the worktree-seeding step runs.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_station_guard.py` -- same `FakeFs` symlink-method additions (`read_text` was already disk-fallback-correct).
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_fleet.py` -- same `FakeFs` symlink-method additions (`write_text_atomic`/`read_text` were already real-disk-backed); no new fleet-cycle test (see Design Notes for the structural-guarantee rationale covering AC #3).
- `tests/unit/scope_triangle.py` -- read-only reuse: `point_scope_triangle(root, slug)`, the shared helper used directly to seed worktree-side (and, in the untouched env-disagreement test, would-be primary-side) triangles.

## Tasks & Acceptance

**Execution:**
- `cli/dispatch.py` -- narrow `_dispatch_scope_refusal` to the env-only check; add `_seed_dispatch_worktree_scope` and wire it into `dispatch_once` after worktree resolution -- retires the primary-checkout `verify_scope` refusal (CAP-273) while keeping the worktree its own triangle, per-write-boundary (AD-11).
- `tests/unit/test_dispatch.py` -- fix `FakeFs.read_text`/`write_text_atomic` real-disk backing, add symlink methods, replace the retired-behavior test, add four worktree-triangle tests -- covers AC #1, #2, #5, #6, #7.
- `tests/unit/test_dispatch_completion.py`, `test_dispatch_station_guard.py`, `test_dispatch_fleet.py` -- same `FakeFs` real-disk-backing / symlink-method fixes -- keeps every existing `dispatch_once` exercise in these files correct once worktree-triangle seeding runs for real writes/reads, with no behavioral assertion changes.

**Acceptance Criteria:**
- Given the primary checkout's marker and both links name `pyforge-steward`, when `dispatch_once(slug="pyforge-marshal", …)` runs, then it launches with no `MRS-DISP-041` and the primary's marker/links are unchanged (AC #1; `test_dispatch_launches_despite_primary_triangle_naming_another_station`).
- Given the same run, when its fake-filesystem writes are inspected, then every write lands under the dispatch worktree and `verify_scope(worktree, "pyforge-marshal")` returns `None` (AC #2; same test).
- Given a non-steward station with a backlog story, when `execute_fleet_cycle` runs one cycle, then the story reaches launch with no `MRS-DISP-041` -- guaranteed structurally, since `execute_fleet_cycle` calls `dispatch_once` and the module has exactly one `verify_scope`/`_dispatch_scope_refusal` call site (AC #3; see Design Notes).
- Given `BMAD_ACTIVE_PROJECT=pyforge-steward` and slug `pyforge-marshal`, when `dispatch_once` runs, then it still refuses `MRS-DISP-041` before any worktree work (AC #4; `test_dispatch_refuses_bmad_active_project_env_disagreement`, unchanged).
- Given an existing dispatch worktree whose own marker names `pyforge-steward`, when `dispatch_once` reaches it, then it refuses `MRS-DISP-041` naming the worktree, launches nothing, and leaves that marker byte-identical (AC #5; `test_dispatch_refuses_worktree_side_foreign_marker`).
- Given an existing dispatch worktree whose `implementation-artifacts` link has an unrecognized shape, when dispatch reaches it, then it refuses `MRS-DISP-041` and leaves the link untouched (AC #6; `test_dispatch_refuses_worktree_side_unrecognized_link`).
- Given a fresh dispatch worktree, when `dispatch_once` seeds its triangle and a corner write fails, then it returns `MRS-DISP-006` and launches nothing (`test_dispatch_worktree_scope_write_failure_is_mrs_disp_006`).
- Given a reused dispatch worktree whose triangle already agrees with the slug, when `dispatch_once` reaches it, then no corner is rewritten and the launch proceeds (`test_dispatch_reused_worktree_with_agreeing_triangle_launches`).
- Given `test_dispatch_refuses_triangle_drift_before_launch` (Story 33.9), when this story lands, then it no longer exists and no other test in `test_dispatch.py` changes its expectation (AC #7; verified: full-file diff touches only the retired test and net-new tests/fixture methods).

## Source

Contract authored from `docs/dreams/pyforge-marshal.md`'s 2026-09-25 (seed) Realization-log entry under the bmad-switch-scope-enforcement fold (and its 2026-09-27 "Specced" line), and `spec-pyforge-marshal` CAP-273 with its 2026-09-27 direction entry in the Spec's `.memlog.md`, decomposed the same session as Epic 64's mint.

## Binding

Parent Spec capability: `spec-pyforge-marshal` CAP-273 (FR-219).
Dream: `docs/dreams/pyforge-marshal.md` § 2026-09-16 — A BMAD write can never land in the wrong project's artifacts → Realization log → *2026-09-25 (seed)*.
Ledger key: `64-1-the-dispatch-worktree-carries-its-own-scope-never-the-shared-marker`.
Ledger status at mint: `backlog`.

## Design Notes

**AC #3 (fleet-cycle) has no dedicated integration test.** `execute_fleet_cycle` has exactly one call path into the scope check: it calls `dispatch_once` per cycle, and `dispatch_once` is the *only* call site of `_dispatch_scope_refusal` / `_seed_dispatch_worktree_scope` in `cli/dispatch.py` (confirmed by grep before and after this change). AC #1/#2's `dispatch_once`-level tests therefore already exhaustively cover the invariant AC #3 restates at the fleet layer -- there is no additional code path for a fleet-level test to exercise. The existing `_cycle` test helper's `_scoped_dispatch_once` monkeypatch shim always seeds a correct primary-checkout triangle before calling through; constructing a fleet-level test of the *retired* refusal would require bypassing that shim to fabricate a scenario the module can no longer produce, which would test the harness, not the production code. AC #3 is satisfied by this structural guarantee, not a new test.

**Why `FakeFs.read_text` needed a real-disk fallback.** `scope_triangle.py`'s `point_scope_triangle` writes the marker and symlinks directly via `pathlib`, bypassing `FsPort` entirely (it seeds `verify_scope`'s ground truth, which itself reads real disk). A `FakeFs` whose `read_text` only checked its in-memory dict would see a pre-seeded foreign marker as absent and overwrite it -- not a production bug, but a test-fixture gap that inverts the very corner-preservation behavior AC #5/#6 assert. The fix makes `read_text`/`write_text_atomic`/the two symlink methods real-disk-backed (in-memory-first, disk-fallback), matching `test_dispatch_fleet.py`'s pre-existing pattern.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Manual checks (operator, after landing — never run from inside a dispatched session, which would launch a second one):**
- With the primary checkout's marker on another station, the next real `marshal factory dispatch` on a non-marker station launches with no `MRS-DISP-041`, and `cat _bmad/custom/.active-project` and `readlink _bmad-output/planning-artifacts` on the primary read the same before and after.
