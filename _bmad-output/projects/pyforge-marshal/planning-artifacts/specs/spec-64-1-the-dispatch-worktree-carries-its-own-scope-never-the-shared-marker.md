---
title: '64.1: The dispatch worktree carries its own scope, never the shared marker'
type: 'fix'
created: '2026-09-27'
status: 'in-progress'
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

## Source

Contract authored from `docs/dreams/pyforge-marshal.md`'s 2026-09-25 (seed) Realization-log entry under the bmad-switch-scope-enforcement fold (and its 2026-09-27 "Specced" line), and `spec-pyforge-marshal` CAP-273 with its 2026-09-27 direction entry in the Spec's `.memlog.md`, decomposed the same session as Epic 64's mint.

## Binding

Parent Spec capability: `spec-pyforge-marshal` CAP-273 (FR-219).
Dream: `docs/dreams/pyforge-marshal.md` § 2026-09-16 — A BMAD write can never land in the wrong project's artifacts → Realization log → *2026-09-25 (seed)*.
Ledger key: `64-1-the-dispatch-worktree-carries-its-own-scope-never-the-shared-marker`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Manual checks (operator, after landing — never run from inside a dispatched session, which would launch a second one):**
- With the primary checkout's marker on another station, the next real `marshal factory dispatch` on a non-marker station launches with no `MRS-DISP-041`, and `cat _bmad/custom/.active-project` and `readlink _bmad-output/planning-artifacts` on the primary read the same before and after.
