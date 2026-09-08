---
title: 'marshal land refuses while a run is in flight'
type: 'feature'
created: '2026-08-09'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
final_revision: '20ad57a62f'
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md']
warnings: ['oversized']
baseline_revision: 'c09088a6e6'
---

<intent-contract>

## Intent

**Problem:** `cli/land.py::run_land` resolves its head branch to the loop-home STATION branch
(`loop/<slug>`) and, when `landing_branch_retirement` policy defaults `True`, folds merge+delete
into one atomic `forge.merge_pr(..., delete_branch=delete_branch)` call (lines ~409, ~812) with no
check for whether a bmad-loop supervisor/engine run is still using that exact branch. Invoked
during a live run it would delete the branch bmad-loop is actively merging stories into —
confirmed 2026-08-09 against a live 9-story run, avoided only because a human read the source
first.

**Approach:** before honoring a policy-true `delete_branch`, gather the SAME liveness facts
`marshal status` already gathers (`cli/status.py::_gather_home_facts` → `core/status.py::
FleetHomeFacts`, reused verbatim) and add one new pure predicate, `core/status.py::is_run_live`,
that a live run downgrades `delete_branch` to `False` for this invocation only (never mutates
policy), refuses by naming the slug/branch, and is overridable by one new explicit CLI flag whose
help text states exactly what it overrides.

## Boundaries & Constraints

**Always:**
- The liveness gather runs ONLY when policy-resolved `delete_branch` is already `True` — a project
  whose `landing_branch_retirement` is `False` triggers no new I/O and no new finding; nothing
  behavioral changes for it.
- New pure predicate `core/status.py::is_run_live(facts: FleetHomeFacts) -> bool` (AD-4: no I/O),
  unit-tested independently: `True` when `facts.has_run` and either `facts.journal_unreadable` (the
  fact CANNOT be proven either way — conservatively treated as live, mirroring Story 4.10's own
  "an unproven branch is refused, never defaulted to delete") or (`not facts.finished and
  facts.supervisor_alive is True`). Every other combination (`has_run=False`; or `has_run=True`,
  readable, and either `finished` or `supervisor_alive is False`) is `False` — safe to retire.
  `derive_home_state`'s own 5-value string is NOT the input here: its `"idle"` state collapses
  "no run ever" and "run exists, supervisor alive, nothing in flight right now" into one string,
  and the second case is exactly the live-between-stories case this story must still catch — the
  raw `FleetHomeFacts` fields are read directly instead.
- `cli/land.py::run_land` gathers facts via a LOCAL import of `cli/status.py::_gather_home_facts`
  and `cli/spin.py::_latest_run_dir`/`_resolve_harness_run_id_for_resume` (the identical
  already-established read sequence `_run_resync_if_enabled` and `cli/retire.py` both already use;
  local import for the same documented load-order-cycle reason every other cross-module `land.py`
  import already uses), passing `home`/`slug`/`head_branch` it already has in scope.
- `run_land` gains three new optional DI params — `harness: HarnessPort | None = None`,
  `process: ProcessPort | None = None`, `clock: ClockPort | None = None` — defaulting to
  `BmadLoopHarness()`/`PosixProcess()`/`SystemClock()` (the first two already imported at module
  level for `_run_resync_if_enabled`; `SystemClock`/`ClockPort` newly imported, matching
  `cli/status.py`'s own identical default-construction convention).
- When `is_run_live(facts)` is `True` and the new override flag is absent: `delete_branch` is
  forced `False` for the `merge_pr` call and journal payloads (the merge itself, PR open/update,
  and resync are entirely unaffected); a new WARN-tier finding `MRS-LAND-008` names the slug and
  `head_branch`, states retirement was skipped because the run is live, and names the override flag.
- New CLI flag `--retire-live-branch` (`action="store_true"`, default `False`) on `add_land_subparser`
  — action-named, not a generic `--force` (this story's single override case doesn't need
  `--force`'s multi-reason breadth): help text states plainly that it retires the branch even while
  this slug's run is live, and that the merge proceeds either way regardless of this flag.
  When passed AND `is_run_live(facts)` is `True`, `delete_branch` keeps its policy value (retirement
  proceeds) and no `MRS-LAND-008` finding fires (nothing was refused).
- `MRS-LAND-008` registered in `core/findings.py` (`REGISTERED_CODES` + docstring prose + the
  compact bullet-comment summary, all three, per that module's own established three-part pattern)
  and `core/verdict.py` (`_CLASSIFY_TABLE["MRS-LAND-008"] = Verdict.WARN`).

**Never:**
- Never blocks the merge itself — a live run changes only whether the branch is retired, never
  whether the wave lands. `landing_branch_retirement=False` landing mid-run was already unaffected
  before this story and stays unaffected.
- Never a `--force` flag on this command (mirrors `marshal retire`'s Story 4.10 precedent, itself
  mirroring `marshal land`'s own Story 4.8 precedent) — `--retire-live-branch` is the one, narrowly
  named override this story adds.
- Never mutates `landing_branch_retirement` policy or any on-disk policy file — the downgrade is
  scoped to this single invocation's `merge_pr` call and journal payload only.
- Never re-derives liveness independently of `cli/status.py::_gather_home_facts` — one gather
  function, one predicate, both reused/added in `core/status.py`/`cli/status.py`, never a second,
  potentially-diverging liveness read inside `land.py` itself.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| No run ever for this slug | `has_run=False` | `is_run_live` false; retirement proceeds exactly as before | No finding |
| Run finished (`state` would read `"stopped"`) | `finished=True` | `is_run_live` false; retirement proceeds | No finding |
| Supervisor confirmed dead, run unfinished (`"unsupervised"`) | `supervisor_alive=False` | `is_run_live` false; retirement proceeds | No finding |
| Supervisor alive, a task in flight (`"running"`) | live | `is_run_live` true; retirement refused, merge proceeds | `MRS-LAND-008` WARN |
| Supervisor alive, no task in flight right now (`"idle"` with `has_run=True`) | live-between-stories | `is_run_live` true; retirement refused, merge proceeds | `MRS-LAND-008` WARN |
| Supervisor alive, paused on escalation | live | `is_run_live` true; retirement refused, merge proceeds | `MRS-LAND-008` WARN |
| Journal/run-state unreadable | `journal_unreadable=True` | `is_run_live` true (unproven, conservative); retirement refused | `MRS-LAND-008` WARN |
| Live run, `--retire-live-branch` passed | explicit override | Retirement proceeds per policy; no refusal finding | No finding |
| Live run, `landing_branch_retirement=False` already | policy already skips retirement | No liveness gather at all; unchanged `False` | No finding |

</intent-contract>

## Code Map

- `src/pyforge/marshal/core/status.py` -- NEW `is_run_live(facts: FleetHomeFacts) -> bool` (pure, AD-4), placed near `derive_home_state`.
- `src/pyforge/marshal/cli/land.py` -- EDIT `run_land`: new `harness`/`process`/`clock` DI params + defaults; local import + call of `_gather_home_facts`/`_latest_run_dir`/`_resolve_harness_run_id_for_resume`; liveness gate before the `merge_pr` call forcing `delete_branch=False` + `MRS-LAND-008` when live and unoverridden; new `--retire-live-branch` flag on `add_land_subparser`; new `_MRS_LAND_008` constant.
- `src/pyforge/marshal/core/findings.py` -- EDIT. Register `MRS-LAND-008` (frozenset + docstring prose + bullet summary).
- `src/pyforge/marshal/core/verdict.py` -- EDIT. Classify `MRS-LAND-008` as `Verdict.WARN`.
- `tests/unit/test_status.py` -- EDIT. `is_run_live`'s full boolean matrix (no I/O).
- `tests/unit/test_land.py` -- EDIT. Live-run refusal (retirement skipped, merge unaffected, finding fires), override flag (retirement proceeds, no finding), and the "no live run → unchanged" directions, using this file's own fake-port style plus `test_status.py`'s `_FakeHarness`/`_FakeProcess` shape for the new `harness`/`process` params.

## Tasks & Acceptance

**Execution:**
- [x] `core/status.py` -- add `is_run_live` -- pure predicate per the Boundaries definition above
- [x] `cli/land.py` -- add DI params, liveness gate, `--retire-live-branch` flag, `MRS-LAND-008` -- implements the refusal
- [x] `core/findings.py` / `core/verdict.py` -- register `MRS-LAND-008` as `Verdict.WARN` -- makes the finding classify and exit correctly
- [x] `tests/unit/test_status.py` -- unit-test `is_run_live`'s full matrix -- proves the pure predicate in isolation
- [x] `tests/unit/test_land.py` -- prove both directions (live → refusal + finding, no live run → unchanged) plus the override flag and the policy-already-off short-circuit

**Acceptance Criteria:**
- Given a slug whose supervisor is alive and run unfinished, when `marshal land <slug>` runs with `landing_branch_retirement` true and no override flag, then the PR still merges, the branch is NOT deleted, and `MRS-LAND-008` names the slug and branch.
- Given the same live slug, when `--retire-live-branch` is passed, then the branch IS deleted per policy and no `MRS-LAND-008` finding fires.
- Given a slug with no live run (finished, unsupervised, or never run), when `marshal land <slug>` runs, then behavior is byte-for-byte identical to before this story (retirement proceeds per policy, no new finding, no new I/O when policy already disables retirement).

## Spec Change Log

## Review Triage Log

### 2026-08-09 — Review pass 1 (Blind Hunter + Edge Case Hunter, parallel)

- intent_gap: 0
- bad_spec: 0
- patch: 6 (high 0, medium 0, low 6)
- defer: 1 (medium 1)
- reject: 5 (low 5)
- addressed_findings:
  - `[low]` `[patch]` **No re-verification of liveness immediately before `forge.merge_pr`'s own delete.** Independently found by both reviewers. The actual window is one local `deploy_run.write` journal call (no network, no polling) -- already as tight as this function's own intent-before/outcome-after ordering (AD-6) allows, and there is no forge-side atomic primitive for "this branch's run is still live" the way `expected_head_sha` has for the merge race. Documented in place rather than adding a second gather: a comment beside the gate now explains why the window is intentionally left open and what would be needed to fully close it (a cross-process lock, out of this story's scope).
  - `[low]` `[patch]` **`_run_resync_if_enabled` ignored `run_land`'s own new `harness`/`process` DI params**, still hardcoding its own `PosixProcess()`/`BmadLoopHarness()` -- a half-wired DI refactor with two different instantiation strategies for the same port types inside one function. Fixed: threaded `harness`/`process` through to both call sites and `reconcile_feed`'s own call.
  - `[low]` `[patch]` **`getattr(args, "retire_live_branch", False)` silently defaults instead of failing loud**, contradicting this codebase's own stated fail-loud-on-wiring-gaps convention. Verified every real caller (the CLI parser via `add_land_subparser`, and every test's `_args()` helper) always sets this attribute. Fixed: direct `args.retire_live_branch` access.
  - `[low]` `[patch]` **Module docstring never mentions the Story 4.11 liveness gate**, the codebase's own established per-story orientation convention. Fixed: added a docstring paragraph.
  - `[low]` `[patch]` **No test proved `--retire-live-branch` is inert when the run is not live** -- the arguably most common real-world usage (an operator passing it defensively). Fixed: new test using `_ExplosiveHarness`/`_ExplosiveProcess`, proving the liveness gate is never even consulted once the flag is set (not merely that the outcome happens to match).
  - `[low]` `[patch]` **Flag help text said a live run "raises" `MRS-LAND-008`**, conflating Finding emission with a Python exception. Fixed: reworded to "reports."
- deferred (not fixed in this pass, appended to `deferred-work.md` as a NEW entry):
  - `[medium]` **`FleetHomeFacts.supervisor_alive` is keyed on the supervisor sidecar's pid, never `launch_pid`** (the actual detached harness process) -- a sidecar crash/not-yet-attached window while the harness itself is still alive would misreport "not live." Pre-existing Story 5.1 semantics, reused verbatim and unmodified by this diff; this story raises the stakes of an existing gap (display-only before, now gates a destructive action) without introducing it.
- rejected: none of substance dropped without review, but 5 findings were assessed and NOT actioned as not real / not in scope, for the record:
  - **"No defensive error handling around the liveness gather call"** — `_gather_home_facts` and its callees are documented and verified as never-raising (returns a degraded `journal_unreadable=True` result instead); the Edge Case Hunter's own pass independently reached the same conclusion and discarded this lead.
  - **"No positive finding when the override flag actually fires"** — the standard envelope's existing `data.branch_retired` field already communicates the outcome precisely; a dedicated Finding here would also contradict this spec's own AC #2 ("no `MRS-LAND-008` finding fires" when overridden).
  - **"`finished=True` trusted unconditionally regardless of `supervisor_alive`"** — matches `derive_home_state`'s own established, reviewed Story 5.1 precedence (a finished run's supervisor naturally exits, so trusting `finished` first is deliberate, not an oversight).
  - **"`--retire-live-branch`'s help text is disproportionately long"** — matches this spec's own explicit instruction to mirror `run_teardown --force`'s help depth, which is equally long for the same reason (a serious safety override deserves full self-documentation).
  - **"`marshal retire` (Story 4.10) is not covered by the same fix"** — out of scope (not part of this diff; Story 4.11's own Deps is S-4.8 only) and not actually the same bug: `core/retire.py` structurally excludes `loop/*` branches already, and gates its own worktree-isolated task branches on `worktree_path_for_branch(...) is None`, a different but equally-reviewed (Story 4.10) liveness proxy suited to its own domain.

### 2026-08-09 — Deterministic verification repair (not a Blind Hunter/Edge Case Hunter pass)

Review pass 1's patches landed clean, but the deterministic gate
`pixi run --frozen -e pyforge-ci pyforge-deps-test` still failed on 3 tests in
`tests/packaging/test_dependency_completeness.py`, all scoped to
`pyforge-steward`/`pyforge-doctor` -- packages this story's diff never
touches. Confirmed pre-existing by git history: `age` (steward) landed
2026-07-31 (`83294a6198`), the missing `mcp` run-dep (doctor) landed
2026-08-07 (`758b5757bc`), both predate this story's `baseline_revision`
(`c09088a6e6`). Fixed directly (not deferred, per repair instructions) using
this repo's own established escape hatches -- `<intent-contract>` untouched:
- `pyforge-steward`: `age` is a subprocess-invoked ENGINE (keys.py's
  encrypt/decrypt), not an importable distribution -- added to
  `CONDA_ONLY_RUN_DEPS`, mirroring `pyforge-warden`'s identical
  deptry/osv-scanner precedent.
- `pyforge-steward`: `_http` (keys.py's sys.path-injected delegate-target
  import of `.claude/skills/conda-forge-expert/scripts/_http.py`) has no
  distributable name to declare -- added to `BASELINE_UNDECLARED_IMPORTS`
  with an OPEN rationale, mirroring atlas's `boring_semantic_layer` entry.
- `pyforge-doctor`: Story 2.1 added `mcp>=1.28.1` to `pyproject.toml` but
  never mirrored it into the package's own `pixi.toml
  [package.run-dependencies]` -- added at the same floor (root pixi.toml's
  `[feature.pyforge-doctor.dependencies]` intentionally pins the dev env
  tighter at `>=2.0.0`, mirroring `pyforge-herald`'s identical split).
- intent_gap: 0
- bad_spec: 0
- patch: 0 (this story's diff was untouched)
- defer: 0 (fixed directly instead, per explicit repair instructions)
- reject: 0
- addressed_findings:
  - `[low]` **3 pre-existing `pyforge-deps-test` failures in unrelated
    packages (steward/doctor) blocked the deterministic verification gate.**
    All three were mechanical, precedent-matched manifest completions; fixed
    directly rather than filed to `deferred-work.md`.

All three spec `## Verification` commands now pass: `pyforge-marshal-test`
(3073 passed, 9 deselected), `pyforge-deps-test` (60 passed), `lint-imports`
(3 contracts kept, 0 broken).

## Design Notes

**Why `journal_unreadable` counts as live.** This mirrors Story 4.10's own `core/retire.py`
philosophy verbatim: a branch is proposed for deletion only when every fact needed to prove safety
was independently established; anything unprovable is refused, never defaulted to delete. An
unreadable journal means liveness genuinely cannot be established either way — the safe direction
is the same one `retire.py` already chose for its own analogous "can't prove it" case.

**Why the predicate reads raw `FleetHomeFacts` fields instead of `derive_home_state`'s state
string.** `build_fleet_row`/`derive_home_state` intentionally report `"idle"` for two different
underlying situations (no run ever vs. a live supervisor between stories) because `marshal status`
only needs to display ONE state per row either way. `land` needs the distinction those two cases
collapse away, so `is_run_live` is a new, narrower predicate over the same already-gathered facts
rather than a second use of the display-oriented enum.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: `done`

**Summary.** `marshal land` now gathers the same liveness facts `marshal status`
already gathers and refuses to retire (delete) the head branch when a
bmad-loop supervisor run is still live for that slug, unless the new
`--retire-live-branch` flag is passed. The merge itself is never blocked.
Implementation + review (Blind Hunter + Edge Case Hunter) completed in a
prior session -- see `## Review Triage Log` pass 1 (6 patch fixes applied,
1 deferred, 5 rejected as not real/out of scope). This session's only work
was a deterministic-verification repair: `pixi run --frozen -e pyforge-ci
pyforge-deps-test` was failing on 3 tests in unrelated packages
(`pyforge-steward`, `pyforge-doctor`), confirmed pre-existing via git
history and unrelated to this story's diff. Fixed directly using this
repo's own established escape hatches -- see the 2026-08-09 "Deterministic
verification repair" entry in `## Review Triage Log` for detail. No code
inside `<intent-contract>` was touched in either session.

**Files changed (this story, prior session, `b78bcdb746`):**
- `src/pyforge/marshal/core/status.py` -- new `is_run_live` pure predicate
- `src/pyforge/marshal/cli/land.py` -- DI params, liveness gate, `--retire-live-branch` flag, `MRS-LAND-008`
- `src/pyforge/marshal/core/findings.py` / `core/verdict.py` -- register `MRS-LAND-008` as WARN
- `tests/unit/test_status.py` / `tests/unit/test_land.py` -- full coverage of the new behavior

**Files changed (this session, verification repair, `20ad57a62f`):**
- `src/shared/packages/pyforge-doctor/pixi.toml` -- mirror the already-declared `mcp>=1.28.1` pyproject dependency into `[package.run-dependencies]`
- `tests/packaging/test_dependency_completeness.py` -- `CONDA_ONLY_RUN_DEPS["pyforge-steward"] = {"age"}` (subprocess engine, not importable) and `BASELINE_UNDECLARED_IMPORTS["pyforge-steward"]["_http"]` (sys.path-injected delegate import, no distributable name)

**Verification performed:** all three spec commands pass --
`pyforge-marshal-test` (3073 passed, 9 deselected), `pyforge-deps-test`
(60 passed), `lint-imports` (3 contracts kept, 0 broken).

**Residual risks:** none new. The pre-existing `defer` finding from review
pass 1 (`FleetHomeFacts.supervisor_alive` keyed on the sidecar pid, not
`launch_pid`) remains filed in `deferred-work.md`, unchanged by this story.

