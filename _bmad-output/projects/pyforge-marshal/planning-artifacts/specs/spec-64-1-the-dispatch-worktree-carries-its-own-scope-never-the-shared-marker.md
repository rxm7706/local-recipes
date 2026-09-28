---
title: '64.1: The dispatch worktree carries its own scope, never the shared marker'
type: 'fix'
created: '2026-09-27'
status: 'done'
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
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py` -- read-only reuse point: `_ensure_dispatch_worktree` already returns early when `worktree.exists()`, before calling `vcs.add_worktree` -- the mechanism new tests use to pre-seed a worktree-side triangle with no `FakeVcs` registration needed. (Tests import this module `as dispatch_core`; there is no separate `dispatch_core.py` file.)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` -- review pass: corrected the `MRS-DISP-041` catalog comment, which cited only Story 33.9's retired primary-checkout check, to also name Story 64.1's worktree-triangle / parent-environment check.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch.py` -- `FakeFs.write_text_atomic` and `.read_text` made real-disk-backed (the latter falls back to disk when absent from the in-memory dict, needed because `scope_triangle.py`'s seeding helper writes straight to disk, bypassing `FakeFs`); added `read_symlink_target`/`repoint_symlink_atomic`/`exists`, and (review pass) a `repointed` write-log on `FakeFs` for write-scope assertions. Retired `test_dispatch_refuses_triangle_drift_before_launch` (AC #7), replaced with `test_dispatch_launches_despite_primary_triangle_naming_another_station`. Added the four worktree-triangle tests (AC #1, #2, #5, #6). Review pass: strengthened the AC #1/#2 launch test and the AC #5 foreign-marker test with explicit write-scope and byte-identity assertions, and added `test_dispatch_worktree_with_marker_but_missing_link_seeds_only_that_corner` (a mixed-triangle seeding case).
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_completion.py` -- same `FakeFs` real-disk-backing fix (write + read + symlink methods), no behavioral test changes; needed so its `dispatch_once` exercises don't regress once the worktree-seeding step runs. Review pass: corrected a stale comment attributing the `verify_scope` monkeypatch to the retired primary-checkout check instead of `_seed_dispatch_worktree_scope`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_station_guard.py` -- same `FakeFs` symlink-method additions (`read_text` was already disk-fallback-correct).
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_fleet.py` -- same `FakeFs` symlink-method additions (`write_text_atomic`/`read_text` were already real-disk-backed). Review pass: added `test_execute_fleet_cycle_dispatches_despite_primary_triangle_naming_another_station`, closing the AC #3 verification gap the Design Notes below originally argued was untestable, and corrected the `_cycle` helper's docstring accordingly.
- `tests/unit/scope_triangle.py` -- read-only reuse: `point_scope_triangle(root, slug)`, the shared helper used directly to seed worktree-side (and, in the untouched env-disagreement test, would-be primary-side) triangles.

## Tasks & Acceptance

**Execution:**
- `cli/dispatch.py` -- narrow `_dispatch_scope_refusal` to the env-only check; add `_seed_dispatch_worktree_scope` and wire it into `dispatch_once` after worktree resolution -- retires the primary-checkout `verify_scope` refusal (CAP-273) while keeping the worktree its own triangle, per-write-boundary (AD-11).
- `tests/unit/test_dispatch.py` -- fix `FakeFs.read_text`/`write_text_atomic` real-disk backing, add symlink methods, replace the retired-behavior test, add four worktree-triangle tests -- covers AC #1, #2, #5, #6, #7.
- `tests/unit/test_dispatch_completion.py`, `test_dispatch_station_guard.py`, `test_dispatch_fleet.py` -- same `FakeFs` real-disk-backing / symlink-method fixes -- keeps every existing `dispatch_once` exercise in these files correct once worktree-triangle seeding runs for real writes/reads, with no behavioral assertion changes.

**Acceptance Criteria:**
- Given the primary checkout's marker and both links name `pyforge-steward`, when `dispatch_once(slug="pyforge-marshal", …)` runs, then it launches with no `MRS-DISP-041` and the primary's marker/links are unchanged (AC #1; `test_dispatch_launches_despite_primary_triangle_naming_another_station`).
- Given the same run, when its fake-filesystem writes are inspected, then every write lands under the dispatch worktree and `verify_scope(worktree, "pyforge-marshal")` returns `None` (AC #2; same test).
- Given a non-steward station with a backlog story, when `execute_fleet_cycle` runs one cycle, then the story reaches launch with no `MRS-DISP-041` -- guaranteed structurally, since `execute_fleet_cycle` calls `dispatch_once` and the module has exactly one `verify_scope`/`_dispatch_scope_refusal` call site, and now also covered directly by `test_execute_fleet_cycle_dispatches_despite_primary_triangle_naming_another_station` (AC #3; see Design Notes).
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

**AC #3 (fleet-cycle) originally shipped with no dedicated integration test; the review pass added one.** `execute_fleet_cycle` has exactly one call path into the scope check: it calls `dispatch_once` per cycle, and `dispatch_once` is the *only* call site of `_dispatch_scope_refusal` / `_seed_dispatch_worktree_scope` in `cli/dispatch.py` (confirmed by grep before and after this change). AC #1/#2's `dispatch_once`-level tests already exhaustively cover the invariant AC #3 restates at the fleet layer -- there is no additional *code path* for a fleet-level test to exercise. That structural argument is still true, but it is an argument about the code, not a substitute for a test of the scenario AC #3 literally describes: `test_dispatch_fleet.py`'s own `_cycle` helper always calls `point_scope_triangle(tmp_path, slug)` and sets `BMAD_ACTIVE_PROJECT=slug` before every dispatch, so every pre-existing fleet-cycle test structurally cannot exercise "the primary names another station." The review pass (below) added `test_execute_fleet_cycle_dispatches_despite_primary_triangle_naming_another_station`, which drives `execute_fleet_cycle` directly (bypassing `_cycle`) against a primary triangle pointed at a different station, closing that gap without touching the retired-refusal harness-fabrication concern this note originally raised.

**Why `FakeFs.read_text` needed a real-disk fallback.** `scope_triangle.py`'s `point_scope_triangle` writes the marker and symlinks directly via `pathlib`, bypassing `FsPort` entirely (it seeds `verify_scope`'s ground truth, which itself reads real disk). A `FakeFs` whose `read_text` only checked its in-memory dict would see a pre-seeded foreign marker as absent and overwrite it -- not a production bug, but a test-fixture gap that inverts the very corner-preservation behavior AC #5/#6 assert. The fix makes `read_text`/`write_text_atomic`/the two symlink methods real-disk-backed (in-memory-first, disk-fallback), matching `test_dispatch_fleet.py`'s pre-existing pattern.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Manual checks (operator, after landing — never run from inside a dispatched session, which would launch a second one):**
- With the primary checkout's marker on another station, the next real `marshal factory dispatch` on a non-marker station launches with no `MRS-DISP-041`, and `cat _bmad/custom/.active-project` and `readlink _bmad-output/planning-artifacts` on the primary read the same before and after.

## Review Triage Log

### 2026-09-28 — Review pass
- verdicts: 12 findings — high 0, medium 6, low 3, false 3, maybe-false 0
- findings:
  - `[false]` `[reject]` Edge Case Hunter: a corner write that fails partway through `_seed_dispatch_worktree_scope` could leave the worktree triangle inconsistent on retry — refuted: each corner is written and checked independently and idempotently (a corner already agreeing with the slug is never rewritten), so a partial failure self-heals on the next attempt; no state a retry cannot recover.
  - `[false]` `[reject]` Blind Hunter #1: a compatibility symlink seeded under the dispatch worktree could resolve to a different path than the physical `_bmad-output/projects/<slug>/` helpers use, risking a Tier-3-style backlink/dangling-symlink split — refuted: `dispatch_core.planning_specs_dir`/`dispatch_runs_dir` and the seeded `projects/<slug>/{planning,implementation}-artifacts` link targets resolve to the identical physical path; read both side by side.
  - `[false]` `[reject]` Blind Hunter #5: the new/changed tests don't assert `verify_scope`'s drift-detection precisely enough (exact marker shape, link-target shape) to trust the launch tests' `MRS-DISP-041` absence — refuted: `verify_scope` (`scope.py`) is the pre-existing, spec-mandated oracle this story is explicitly barred from changing ("Never: do not change scope.py"), and it already carries its own dedicated strict coverage in `test_scope.py`/`test_verify_scope.py`, independent of this story's diff.
  - `[low]` `[patch]` Blind Hunter #2: the `MRS-DISP-041` catalog comment in `core/findings.py` still cited only Story 33.9's retired primary-checkout check, and implied the primary checkout's marker is still read — fix applied: comment now names both the worktree-triangle check and the parent-environment check, and drops the stale claim.
  - `[low]` `[patch]` Blind Hunter #3: `test_dispatch_completion.py`'s comment above its `verify_scope` monkeypatch still attributed the check to the retired `_dispatch_scope_refusal` primary-checkout call — fix applied: comment now attributes it to `_seed_dispatch_worktree_scope`.
  - `[low]` `[patch]` Blind Hunter #4: no test exercised a "mixed" worktree triangle (marker and one link already agreeing with the slug, the other link entirely absent) to confirm `_seed_dispatch_worktree_scope` seeds only the truly-missing corner and leaves the agreeing corners untouched — fix applied: added `test_dispatch_worktree_with_marker_but_missing_link_seeds_only_that_corner`, asserting the pre-existing marker bytes and link target are unchanged and the missing link is seeded correctly.
  - `[medium]` `[patch]` Blind Hunter #6: no test drives `execute_fleet_cycle` (the fleet-drain entry point) against a primary triangle naming another station, so AC #3's literal scenario rested on a structural argument alone — fix applied (shared with the next two rows): added `test_execute_fleet_cycle_dispatches_despite_primary_triangle_naming_another_station`.
  - `[medium]` `[patch]` Verification Gap Reviewer (other finding), same root cause: `test_dispatch_fleet.py`'s shared `_cycle` helper always repoints the primary triangle to agree via `point_scope_triangle`/`BMAD_ACTIVE_PROJECT` before every dispatch, so every pre-existing fleet-cycle test structurally cannot produce a disagreeing primary — fix applied (shared): the new test drives `execute_fleet_cycle` directly, bypassing `_cycle`.
  - `[medium]` `[patch]` Intent Alignment Auditor, AC #3 divergence, same root cause: the spec requires the fleet-cycle scenario be demonstrated and nothing did — fix applied (shared): same new test; also corrected `_cycle`'s stale docstring, which still cited the retired Story 33.9 primary-checkout guard.
  - `[medium]` `[patch]` Intent Alignment Auditor, AC #1 under-asserted: `test_dispatch_launches_despite_primary_triangle_naming_another_station` didn't confirm the fake harness recorded exactly one launch whose `project_slug` is `pyforge-marshal` — fix applied (shared with the next row): added a `FakeBuildHarness.calls` assertion plus primary marker-bytes/readlink-target identity checks.
  - `[medium]` `[patch]` Intent Alignment Auditor, AC #2 under-asserted: the same test didn't confirm every write landed under the dispatch worktree or `_bmad-output/projects/pyforge-marshal/` — fix applied (shared with the row above): added a `FakeFs.repointed` write log and asserted `fake_fs.files`/`fake_fs.repointed` write-scope, plus a `verify_scope(worktree, slug) is None` check.
  - `[medium]` `[patch]` Intent Alignment Auditor, AC #5 under-asserted: `test_dispatch_refuses_worktree_side_foreign_marker` didn't assert the worktree marker stayed byte-identical or that no run directory was created — fix applied: added a `dispatch_core.dispatch_runs_dir` non-existence check and a marker byte-identity assertion.

## Auto Run Result

**Summary:** Story 64.1 (`spec-pyforge-marshal` CAP-273, FR-219) moved the dispatch scope check from the primary checkout to the dispatch worktree itself. `_dispatch_scope_refusal` now checks only `BMAD_ACTIVE_PROJECT` parent-environment agreement; a new `_seed_dispatch_worktree_scope` writes each missing corner of the worktree's own triangle through `FsPort` (never an existing corner, however shaped) and then calls the unmodified `verify_scope(worktree, slug)`. The primary checkout's marker and links are never read or written by dispatch. This review pass verified all four reviewer layers' findings against the code, found no `intent_gap` or `bad_spec` root cause, and applied six `patch`-routed fixes (three `low`, three grouped `medium` entries) directly; three findings were refuted (`false`) and rejected.

**Files changed (this story, cumulative through review):**
- `src/pyforge/marshal/cli/dispatch.py` — narrowed `_dispatch_scope_refusal` to the env-only check; added `_seed_dispatch_worktree_scope`, wired into `dispatch_once` after worktree resolution.
- `src/pyforge/marshal/core/findings.py` — review pass: corrected the stale `MRS-DISP-041` catalog comment.
- `tests/unit/test_dispatch.py` — real-disk-backed `FakeFs`, retired/replaced the Story 33.9 refusal test, added the worktree-triangle test suite; review pass: strengthened the AC #1/#2 and AC #5 tests, added the mixed-triangle test, added `FakeFs.repointed`.
- `tests/unit/test_dispatch_completion.py` — real-disk-backed `FakeFs`; review pass: corrected a stale comment.
- `tests/unit/test_dispatch_station_guard.py` — real-disk-backed `FakeFs` symlink methods.
- `tests/unit/test_dispatch_fleet.py` — real-disk-backed `FakeFs` symlink methods; review pass: added the `execute_fleet_cycle` primary-disagreement test, corrected `_cycle`'s docstring.

**Review findings breakdown:**
- Patches applied: 6 (3 `low`, 3 `medium`) — see Review Triage Log above for each fix.
- Deferred: 0.
- Rejected (`false`): 3 — Edge Case Hunter's partial-write-failure concern (self-healing, per-corner idempotent); Blind Hunter #1's Tier-3 backlink/dangling-symlink concern (physical helper and seeded link resolve identically); Blind Hunter #5's assertion-strength concern (`verify_scope` is the unchanged, independently-tested oracle).

**Follow-up review recommendation:** `false`. Three `medium` entries were patched this pass, which meets the mechanical "two or more medium entries patched" trigger, but each of the three is a verification-gap finding (a real scenario the diff already handled correctly but no test exercised) closed by a new or strengthened test that now passes and directly exercises exactly the previously-unverified scenario (AC #3's fleet-cycle path, AC #1/#2's launch write-scope, AC #5's foreign-marker preservation). No specific unverified risk remains to name, so the recommendation is `false` per the rule's naming requirement.

**Verification performed:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 8836 passed, 1 skipped, 12 deselected.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — 130 passed, 3 skipped.
- Each new/changed test run in isolation immediately after being written, all passing on first attempt.

**Residual risks:** None specific to this story's diff. The Verification Gap Reviewer noted 2 pre-existing, unrelated slow-test failures elsewhere in the suite (excluded by `pyforge-marshal-test`'s own deselection) — not caused by or related to this change, and out of this story's scope to fix.
