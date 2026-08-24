---
title: 'The apply runner — transactional, guarded'
type: 'feature'
created: '2026-08-14'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
last_pass: 'verification-repair + second review (2026-08-14)'
context: []
warnings: ['oversized']
difficulty: 'heavy'
baseline_revision: '64e717d13554938e03ceac5a6a98c2aae407b957'
final_revision: '1e6eb700fd9d98f5c4c42ea5e455b3b93d48a31d'
---

<intent-contract>

## Intent

**Problem:** `seed/apply/` is an empty package. Story 9.6 built a `Plan` carrying a
`RepoFingerprint` explicitly so that "a later `apply` story can refuse a `Plan` whose fingerprint
no longer matches" — and nothing consumes it. There is no code path anywhere in `seed/` that turns
a `Plan` into writes, so AR-5 (a stale plan applied against a changed repo) and NFR-R1 (no partial
state) are both unmitigated, and Stories 10.4/10.6/10.7 have no runner to build on.

**Approach:** Add `seed/apply/run.py` — `run_apply(plan, *, repo_root, never_write, commit)` — the
transactional envelope, and nothing else. It refuses a stale plan before touching disk, executes
the plan's actions in the plan's own order through a caller-supplied per-action `commit` step,
snapshots each action's target immediately before that action runs, and on ANY failure restores
every snapshot in reverse order so the repo is left exactly as it was found. Materializing an
action's content (Copier, region insertion) is the caller's job — the runner never decides WHAT to
write, only that a run either completes or leaves nothing behind.

## Boundaries & Constraints

**Always:**
- `run_apply` consumes **only** `plan`, `repo_root`, `never_write`, and `commit` (P-04). It never
  loads a `Manifest`, never calls `classify`/`build_plan`, never reads `.marshal/seed-state.yml`.
- The stale-plan refusal runs FIRST, before any snapshot and before any `commit` call, and raises
  `PreconditionFailure` (exit 3) whose message contains the literal token `stale-plan` and names
  each way the fingerprint diverged.
- The fingerprint comparison covers all three `RepoFingerprint` fields — `git_head`, `dirty`, and
  every `artifact_hashes` pair — and lives in `plan/build.py`, the fingerprint's sole producer.
  `seed/apply/run.py` imports neither `hashlib` nor `detect.hashes`, in any form (P-07; the
  existing `tests/meta/test_p07_no_hash_comparison_in_apply.py` AST guard stays untouched and
  green). See Design Notes for why the AD-57 freshness check is not a P-07 hash guard.
- Actions execute in `plan.actions` order, unmodified — never re-sorted, never filtered.
- Every byte the runner itself writes (rollback restores) goes through `fs.write` / `fs.remove`
  with the caller's `repo_root`/`never_write` (P-01). The runner calls no other write primitive.
- The transaction covers exactly `repo_root / action.target_path`, one path per action, snapshotted
  as `bytes` (present) or `None` (absent) immediately before that action's `commit` call.
- Rollback restores in REVERSE execution order, so two actions naming the same `target_path` unwind
  correctly.
- Rollback runs for **any** `BaseException`, including `KeyboardInterrupt`, and re-raises the
  original exception unchanged once restoration succeeds.
- An empty `plan.actions` performs zero snapshots, zero `commit` calls, and zero writes, and
  returns normally (the caller's exit 0).
- `commit` is documented as contracted to write only within `repo_root / action.target_path`;
  anything it writes elsewhere is outside the transaction.

**Block If:**
- The stale-plan refusal cannot be implemented without either weakening
  `tests/meta/test_p07_no_hash_comparison_in_apply.py` or dropping a `RepoFingerprint` field from
  the comparison. (Neither is permitted; if both become necessary, this is an architecture
  question, not an implementation choice.)

**Never:**
- No materialization: no `copier` import, no `engine.materialize` call, no `regions.apply` call, no
  per-artifact-class branching. `commit` supplies all of it.
- No staged-output reconciliation and no staging-directory cleanup, despite `engine/copier.py`'s
  docstring assigning both to "Story 10.3's apply runner" — `MaterializeResult` exposes only
  absolute `staged_paths`, never the staging root, so neither is implementable against the shipped
  API. Filed as deferred work, routed to whoever wires materialization (S-10.6).
- No preconditions beyond the fingerprint: not-a-git-repo, dirty-worktree, hand-edit, `--force`,
  and `--skip` are Story 10.4's surface (its own `Surface:` line names this same file).
- No state read or write, no `.marshal/plan.json` read or write, no CLI wiring, no exit-code
  dispatch (`errors.py`: mapping a caught `SeedError` to `sys.exit` is a later CLI story).
- No removal of empty parent directories `atomic_write_bytes` created — `fs` ships no
  directory-removal primitive and P-01 forbids reaching around it. Rollback restores file CONTENT;
  an empty directory may survive (stated bound, filed as deferred work).
- No new import-linter contract (`tests/meta/test_ad3_ad4_import_linter.py` asserts exactly four).
- No edit to any existing meta test, to `detect/hashes.py`, to `plan/types.py`, or to
  `engine/copier.py`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Empty plan | `Plan(actions=(), fingerprint fresh)` | Returns `ApplyResult(applied=())`; `commit` never called; no file created, not even `.marshal/` | No error expected |
| Happy path | 3 actions, fingerprint fresh | `commit` called once per action in `plan.actions` order; returns ids in that order | No error expected |
| Stale — HEAD moved | Plan built, then a new commit lands | Nothing written, `commit` never called | `PreconditionFailure` (exit 3), message contains `stale-plan` and `git_head` |
| Stale — dirty flipped | Plan built clean, worktree now dirty | Nothing written, `commit` never called | `PreconditionFailure` (exit 3), message names `dirty` |
| Stale — actioned file edited | A `present-divergent` artifact hand-edited after plan build | Nothing written, `commit` never called | `PreconditionFailure` (exit 3), message names the artifact id |
| Stale — absent file appeared | An `absent` artifact created on disk after plan build | Nothing written, `commit` never called | `PreconditionFailure` (exit 3), message names the artifact id |
| Stale — empty plan, HEAD moved | `actions=()`, fingerprint stale | Refused, not treated as a no-op | `PreconditionFailure` (exit 3) — deliberate ordering, see Design Notes |
| Plan integrity | `artifact_hashes` names an id no `Action` carries | Refused before any write | `PreconditionFailure` (exit 3), message names the orphan id |
| Fault at index 0 | `commit` raises on the 1st action | Zero net change on disk | Original exception propagates unchanged |
| Fault at index 1 | `commit` raises on the 2nd action | Action 0's target restored byte-identical (or removed if it was absent) | Original exception propagates unchanged |
| Fault at index 2 | `commit` raises on the 3rd action | Actions 0 and 1 both reverted, in reverse order | Original exception propagates unchanged |
| Interrupt mid-run | `commit` raises `KeyboardInterrupt` | Completed writes reverted | `KeyboardInterrupt` propagates unchanged |
| State untouched | `.marshal/seed-state.yml` pre-exists; fault injected | File byte-identical after the failed run | Original exception propagates |
| Rollback itself fails | A restore raises (e.g. `never_write` now matches the target) | Every other restore still attempted | `InternalError` (exit 10) naming the original failure AND every unrestorable path, `raise ... from` the original |
| Snapshot unreadable | Target exists but `read_bytes` raises before its action runs | Prior actions rolled back; that action never runs | The `OSError` propagates unchanged (`fs`'s own "never wraps a generic OSError" line) |
| Never-write target | An action names a never-write path and `commit` honors `fs` | `commit`'s own `NeverWriteViolation` triggers rollback of prior actions | `NeverWriteViolation` (exit 4) propagates unchanged |

</intent-contract>

## Code Map

Paths under `src/shared/packages/pyforge-marshal/` unless noted; module prefix
`src/pyforge/marshal/`.

- `.../seed/apply/run.py` — **NEW.** `ApplyResult`, `CommitAction` alias, `run_apply`. The whole
  story's behavior.
- `.../seed/apply/__init__.py` — currently 0 bytes; re-export `ApplyResult`/`run_apply` with an
  explicit `__all__`, matching `seed/engine/__init__.py`'s front-door convention.
- `.../seed/plan/build.py` — **MODIFIED (additive).** Gains `fingerprint_drift(plan, repo_root) ->
  tuple[str, ...]`. Already owns `_git_head`, `_repo_is_dirty`, `_GIT_TIMEOUT_S`, and the
  `hash_content` import — the verifier sits beside the producer so the two cannot drift.
- `.../seed/plan/types.py` — consumed unmodified: `Plan.actions` (tuple, sorted by `artifact_id`,
  uniqueness enforced on load), `Plan.repo_fingerprint`, `Action.artifact_id`/`target_path`/
  `current_state`, `RepoFingerprint.git_head`/`dirty`/`artifact_hashes`.
- `.../seed/fs.py` — consumed unmodified: `write(path, data, *, repo_root, never_write)`,
  `remove(path, *, repo_root, never_write)`, `NeverWrite`. Imported as the MODULE (`from .. import
  fs`) so tests can monkeypatch `run.fs.write` — `regions/apply.py`'s established idiom.
- `.../seed/errors.py` — consumed unmodified: `PreconditionFailure` (exit 3, first real raise site
  in the package) and `InternalError` (exit 10). Both need a non-blank `remedy=` kwarg.
- `.../seed/detect/hashes.py` — `hash_content` reached ONLY via `plan/build.py`; never imported
  here (P-07 meta test).
- `.../tests/meta/test_p07_no_hash_comparison_in_apply.py` — the guard this story must satisfy, not
  edit. Its `test_apply_package_scan_surface_is_not_empty` now scans `run.py` too.
- `.../tests/meta/test_seed_no_bare_exception.py` — forbids `raise Exception(...)`/`raise
  SystemExit(...)` anywhere under `seed/`; a bare `raise` re-raise is fine.
- `.../tests/unit/test_seed_apply_run.py` — **NEW.**
- `.../tests/unit/test_seed_plan_build.py` — **MODIFIED (additive).** `fingerprint_drift` cases;
  reuse its existing `_git`/`_init_git_repo`/`_manifest`/`_whole_file`/`_hybrid`/`_sample_plan`
  helpers rather than re-inventing them.
- `.../tests/unit/test_seed_plan_types.py` — reference only: `_action`/`_fingerprint`/`_plan`
  override-dict builders for constructing a `Plan` without `build_plan`.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md`
  — **MODIFIED.** Append an entry naming every changed path; `scripts/spec_surface_reconcile.py`
  fails a governed-code change whose owning spec's memlog did not move.
- `pyproject.toml` / `pixi.toml` — **no change.** No new dependency; `run.py` is stdlib + in-package.

## Tasks & Acceptance

**Execution:**
- [x] `.../seed/plan/build.py` — add `fingerprint_drift(plan, repo_root) -> tuple[str, ...]`
  returning one human-readable string per divergence (empty tuple = fresh): `git_head` vs
  `_git_head`, `dirty` vs `_repo_is_dirty`, and per `artifact_hashes` pair the current
  `hash_content` of `repo_root / action.target_path` (read as UTF-8 text, degrading to `""` for an
  absent/non-file/unreadable/non-UTF-8 target — `_current_text`'s own fallback), plus an entry for
  any hashed id no `Action` carries. Reads the path unconditionally rather than gating on
  `current_state`. — the one place hashing happens, beside the fingerprint's only producer.
- [x] `.../seed/apply/run.py` — define frozen `ApplyResult(applied: tuple[str, ...])` and the
  `CommitAction = Callable[[Action], None]` alias, with a module docstring stating the transaction
  boundary, the `commit` contract, and every bound this spec's Never list names. — the shape
  callers bind to.
- [x] `.../seed/apply/run.py` — implement `run_apply`: `fingerprint_drift` refusal →
  `PreconditionFailure` naming `stale-plan` and every divergence; empty-plan short-circuit;
  per-action snapshot-then-`commit` in `plan.actions` order; reverse-order restore on any
  `BaseException` via `fs.write`/`fs.remove`; `InternalError` (chained) when a restore itself
  fails, otherwise a bare re-raise. — NFR-R1, AD-57, P-01, P-04, P-07 in one function.
- [x] `.../seed/apply/__init__.py` — re-export `ApplyResult`, `run_apply`, `CommitAction` with an
  explicit `__all__`. — the package front door.
- [x] `.../tests/unit/test_seed_apply_run.py` — cover every I/O-matrix row above, with fault
  injection at indices 0, 1 and 2 of a three-action plan (the AC's "three different action
  indices"); assert rollback routes through `fs` by monkeypatching `run.fs.write`/`run.fs.remove`
  and counting; assert a pre-seeded `.marshal/seed-state.yml` is byte-identical after a failed run;
  assert `PreconditionFailure.exit_code == 3` / `InternalError.exit_code == 10` and both carry a
  non-blank `remedy`; assert `run.py`'s source imports nothing from `seed.state` (so the guarantee
  survives Story 10.2 merging). — proves the matrix.
- [x] `.../tests/unit/test_seed_plan_build.py` — add `fingerprint_drift` cases against a real
  `tmp_path` git repo: fresh plan → `()`; new commit → names `git_head`; worktree dirtied → names
  `dirty`; actioned file edited → names the artifact id; absent artifact created → names the
  artifact id; orphan hashed id → named. — proves the verifier, including the
  absent-then-appeared case a `current_state`-gated read would have missed.
- [x] `.../planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` — append an entry naming every
  changed path and summarizing the story. — `spec_surface_reconcile.py`'s reconciliation contract.

**Acceptance Criteria:**
- Given `run_apply` is handed a plan and a `commit` that records what it is called with, when the
  run succeeds, then `commit` was called exactly once per action, in `plan.actions` order, and
  `ApplyResult.applied` lists the same ids in the same order.
- Given a repo whose state changed since the plan was built, when `run_apply` runs, then it raises
  `PreconditionFailure` with `exit_code == 3` and a message containing `stale-plan`, and `commit`
  was never called and no file under `repo_root` changed.
- Given `seed/apply/run.py`, when its imports are inspected, then it imports neither `hashlib` nor
  `detect.hashes` (the existing P-07 meta test passes unmodified) and nothing from `seed.state`,
  `seed.engine`, `seed.detect`, or `copier`.
- Given a run interrupted at any action index, when rollback completes, then every file the runner
  snapshotted is byte-identical to its pre-run bytes or absent again if it was absent, and the
  exception the caller sees is the one `commit` raised — not a rollback artifact.
- Given the whole change, when `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` runs,
  then the suite is green with no pre-existing test modified.

## Spec Change Log

### 2026-08-14 — Verification-repair pass (no intent-contract change)

The loop's deterministic verifier failed the run on
`pixi run --frozen -e pyforge-ci pyforge-deps-test` (rc=1). The failing case was
`test_conda_run_deps_add_nothing_undeclared[pyforge-mason]` — the pre-existing `DW-FU-10-2`
this spec had disposed of as "not fixed here". That disposition was wrong for a gate the loop
treats as a hard landing precondition: deferring it does not park the debt, it blocks every
story in Epic 10 behind it indefinitely.

Repaired by adding the `pyforge-mason` entry to `CONDA_ONLY_RUN_DEPS` in
`tests/packaging/test_dependency_completeness.py` — the escape hatch the assertion message
names, on the precedent already recorded there for warden and steward. Rationale, evidence, and
the reason the alternative branch is wrong are in Verification § Disposition.

`<intent-contract>` is **unmodified**. The change touches no file the Never list names, no
`pyproject.toml`, and no `pixi.toml`; `git diff --stat -- src/shared/packages/pyforge-marshal/tests/meta/`
remains empty. Re-verified after the repair: `pyforge-deps-test` 74 passed,
`pyforge-marshal-test` 4237 passed / 9 deselected, `pyforge-mason-test` 1409 passed / 2
deselected, `spec_surface_reconcile.py` unchanged at its 2 pre-existing findings.

## Review Triage Log

### 2026-08-14 — Review pass (second; verification-repair run)

- intent_gap: 0
- bad_spec: 0
- patch: 11: (high 2, medium 4, low 5)
- defer: 3: (high 0, medium 2, low 1)
- reject: 4: (high 0, medium 2, low 2)
- addressed_findings:
  - `[high]` `[patch]` **The containment check did not bind the path it was guarding.** Added by
    the FIRST review pass, it resolved `repo_root / action.target_path` — but the snapshot loop and
    `_restore` both re-derived the RAW path. Both reviewers reached the hole independently and both
    reproduced real data loss. Edge Case Hunter: `target_path="sub/../b.txt"` resolves inside the
    repo (accepted), stats as absent because `sub` does not exist (snapshot `None`), and once
    `commit`'s `mkdir(parents=True)` creates `sub` the same raw path resolves onto the real
    `b.txt`, which rollback then DELETES — a pre-existing, unrelated, in-repo file destroyed by a
    rolled-back run, which is verbatim NFR-R1's prohibition. Blind Hunter: a `commit` that
    materializes an action's missing parent as a SYMLINK to a host directory makes rollback
    `fs.remove` a file OUTSIDE `repo_root` entirely (host file confirmed destroyed); `fs`'s
    never-write guard cannot intervene, which is the very reason the containment check was added.
    Fixed on both sides: non-normalized targets (absolute, or containing `..`) are now refused
    outright before resolution, and `_restore` re-checks containment per path, reporting an escaped
    target as unrestorable rather than touching it. Regression tests for both, each verified to
    fail against the pre-fix code.
  - `[high]` `[patch]` **The verifier was stricter than the producer, bricking apply.** The first
    pass's `or target.is_symlink()` in `fingerprint_drift`'s ABSENT branch disagreed with
    `detect/inventory.py::_classify_entry`, which asks `target.exists()` alone. A DANGLING symlink
    at an absent artifact's path is where they diverge: `exists()` follows the broken link and says
    False, so `build_plan` records `ABSENT`, while `is_symlink()` says True, so `fingerprint_drift`
    refused the plan the instant it was produced — and re-planning yielded the identical plan, so
    apply was permanently unreachable and the remedy string ("re-run the plan") could not work.
    Verified by execution. Predicate restored to `exists()`. Producer/verifier agreement is the
    stated reason this function lives in `plan/build.py` at all, so this was the fix, not a
    loosening; the symlink rollback bound remains separately filed.
  - `[medium]` `[patch]` A `target_path` with an embedded NUL reached `Path.resolve()` and raised a
    raw `ValueError`, escaping the closed six-leaf `SeedError` taxonomy — the identical hole class
    the adjacent `ProcessError` wrap was added to close, on the very line added to guard untrusted
    plans. Now an `unusable-target` `PreconditionFailure` (exit 3), chained.
  - `[medium]` `[patch]` The containment guard read `resolved != resolved_root and resolved_root
    not in resolved.parents`, so a target resolving to the repo root ITSELF (`.`, `""`, `sub/..`)
    short-circuited to accepted and the run returned success with `commit` handed the root
    directory. The escape clause is gone; the root is refused like anything else outside.
  - `[medium]` `[patch]` The escaping-target remedy told the operator the plan "did not come from
    `build_plan`" and to re-plan. Provably false and actively misleading: `_resolve_within_repo`
    returns `None` for an absolute/traversing/symlinked manifest `path`, `_classify_entry` treats
    that as `ABSENT`, and `build_plan` emits an ordinary `Action` carrying the raw escaping path —
    so re-planning reproduces the same plan forever. Remedy now names the manifest entry as the
    thing that must change; the underlying emission is filed as `DW-FU-10-3-9`.
  - `[medium]` `[patch]` The first pass added a duplicate-ACTION-id check on the reasoning that "a
    corrupted plan is refused, never partially verified", but left the mirror case unguarded:
    `artifact_hashes` carrying the same id twice reported `()`. Verified by execution. Symmetric
    check added.
  - `[medium]` `[patch]` **The packaging repair's own escape hatch was unratcheted.** This run added
    a five-name `CONDA_ONLY_RUN_DEPS` entry, and that table — unlike its two siblings in the same
    file — had no staleness guard, despite those siblings' docstrings warning that an unguarded
    table "becomes a permanent excuse". Worse (Edge Case Hunter): the exemption is permanent while
    `_scan_imports`' `deferred` bucket is discarded at both call sites (`hard, _ = …`), so a lazy
    `import twine` inside a function would ship an unusable wheel with no gate firing — and three
    of the five exempted names are real importable distributions. Two guards added
    (`test_conda_only_entries_are_still_conda_run_deps`,
    `test_conda_only_run_deps_are_never_imported`), both mutation-verified.
  - `[low]` `[patch]` The prose justifying the packaging repair claimed none of the five engines is
    "an importable distribution". False for `twine`/`conda-lock`/`python-build`; the true claim is
    that mason never imports them — a property of the code, not the packages. Corrected in all four
    places it had been written (test comment, spec Disposition, ledger entry, memlog) and, more to
    the point, converted from a claim into an assertion.
  - `[low]` `[patch]` `_restore`'s docstring argued that catching `Exception` rather than
    `BaseException` is deliberate so a Ctrl-C is never swallowed — while `run_apply` wraps exactly
    that interrupt in a catchable `InternalError` whenever a restore fails. The contradiction is
    stated rather than left standing; the behavior is a frozen-matrix conflict, filed as
    `DW-FU-10-3-10`.
  - `[low]` `[patch]` The module's four-residue enumeration named only DIRECTORIES for the "not a
    regular file" class, but the predicate is `is_file()`, so a dangling symlink, a symlink to a
    directory, and a FIFO survive rollback identically. Wording widened to the actual predicate.
  - `[low]` `[patch]` Two test-fidelity defects: `_fresh_plan`'s docstring claimed its actions are
    "exactly what `build_plan` would record" while emitting a `PRESENT_DIVERGENT` +
    `COPIED_MANAGED` pair the producer cannot reach (bound now stated, with why it is harmless
    here); and the escaping-target test paired one action with `artifact_hashes=()`, a plan
    `fingerprint_drift` independently refuses — so it passed only because containment runs first
    and would have kept passing with the containment check deleted. Now built through `_fresh_plan`
    so it genuinely isolates containment. Also added a `ProcessError` test that drives the REAL
    `fingerprint_drift` (via a nonexistent `repo_root`) rather than only a monkeypatched stand-in.
  - Deferred (3): `DW-FU-10-3-8` (`fingerprint_drift`'s read is unguarded when called directly —
    the containment check is its caller's, and Story 10.4 owns that file next), `DW-FU-10-3-9`
    (`build_plan` emits escaping-target actions, so one bad manifest entry refuses the whole plan;
    the fix is manifest-load validation, outside this surface), `DW-FU-10-3-10` (interrupt wrapped
    in `InternalError` on a failed rollback — two frozen matrix rows collide, so choosing a winner
    is an intent decision).
  - Rejected (4): the `write_plan`-flips-`dirty` bootstrap failure and the executable-mode loss,
    both already filed by the first pass as `DW-FU-10-3` and `DW-FU-10-3-2` and re-derived here
    independently; a one-shot-iterable `plan.actions` being consumed three times (`Plan.actions` is
    contractually a tuple); and the observation that the P-07 meta test is now non-load-bearing
    because `run.py` reaches hashing transitively through `plan.build` — true, but explicitly
    reasoned through in Design Notes and already stated in the module docstring by the first pass.

### 2026-08-14 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 11: (high 2, medium 5, low 4)
- defer: 7: (high 1, medium 5, low 1)
- reject: 1: (high 0, medium 0, low 1)
- addressed_findings:
  - `[high]` `[patch]` `fingerprint_drift` compared CONTENT only, and every read degrades an
    absent/non-file/unreadable/non-UTF-8 target to `''` — the same value every `ABSENT` artifact's
    hash already encodes. Both reviewers reproduced the consequence by execution: a binary,
    unreadable, or empty file appearing at an absent artifact's path re-hashed identically, the
    plan was accepted as fresh, and apply destroyed the file — verbatim the hole the function's own
    docstring claimed to have closed. Fixed by comparing STATE where content cannot decide: an
    `ABSENT` artifact must still not exist, a present one must still be readable as text, and only
    then does its hash mean anything. `_read_text_or_blank_verbose` carries the readability half;
    `_current_text` keeps `build_plan`'s behavior byte-for-byte. The overclaiming docstring and the
    spec's matching Design Note were corrected rather than left standing.
  - `[high]` `[patch]` `run_apply` performed no containment check on `action.target_path`, and
    `Path(repo_root) / "/etc/passwd"` discards `repo_root` entirely. Since `plan.json` is explicitly
    untrusted, hand-editable input, a plan could direct snapshots and rollback writes anywhere on
    the host — and `fs`'s never-write guard cannot catch it, because a path outside `repo_root`
    falls back to an absolute POSIX string no repo-relative pattern can match. Fixed with an
    `escaping-target` `PreconditionFailure` (exit 3) raised before any snapshot or `commit`,
    mirroring `detect/inventory.py`'s own `_resolve_within_repo` guard.
  - `[medium]` `[patch]` The id→target lookup was a dict comprehension, so two actions sharing an
    `artifact_id` collapsed onto the last one and the first one's target went unverified while
    drift still reported `()`. Now reported as drift.
  - `[medium]` `[patch]` `ProcessError` (missing `git`, nonexistent `repo_root`) escaped the closed
    six-leaf taxonomy untranslated, handing an operator a traceback where `PreconditionFailure`'s
    own docstring promises exit 3. Now wrapped, chained, with a remedy.
  - `[medium]` `[patch]` The module docstring claimed the design made P-04 "literally true" and
    implied P-07 was met. `run_apply` does shell out to git and does cause hashing at apply time;
    keeping the call one module away satisfies the meta test's letter. Rewritten to state plainly
    that both rules are deliberately REINTERPRETED, with the reconciling argument named, so nobody
    reads the green meta test as proof the underlying rule was untouched.
  - `[medium]` `[patch]` A refusal test asserted `set(_tree(...)) == set(before)` — filenames only,
    so a runner that rewrote every pre-existing file's contents before refusing would have passed.
    Now the full content comparison every sibling test uses.
  - `[medium]` `[patch]` `_tree()` was described as a zero-net-change oracle while blind to
    permission bits, leftover directories, and symlink conversion; every fault-injection target was
    also flat. Bounds now stated in its docstring, and a nested-target rollback test added.
  - `[low]` `[patch]` `ApplyResult.applied` was recomputed from `plan.actions` on the way out, so a
    value sold as "proof the runner neither re-sorted nor filtered" was derived from the input.
    Now accumulated inside the loop.
  - `[low]` `[patch]` The banned-import test's docstring claimed a guarantee a direct-import AST
    scan cannot give (`run.py` reaches `detect.hashes`/`hashlib` transitively via `plan.build`).
    Bound stated.
  - `[low]` `[patch]` The runner's "leaves the repo as it found it" claim now enumerates the four
    residues a rolled-back run genuinely leaves (mode, directories, symlinks, never-write targets)
    instead of mentioning only empty parent directories.
  - `[low]` `[patch]` Two "filed as deferred work" claims in the docstring pointed at nothing the
    ledger could see. The entries are now actually filed (`DW-FU-10-3` … `DW-FU-10-3-7`).
  - Fixture fallout of the first patch, worth recording: the new existence check exposed that
    several tests pre-created a target while leaving the action's `current_state` at the `ABSENT`
    default — an internally impossible plan. `_fresh_plan` now corrects each action's state to
    match the repo, making its "exactly what `build_plan` would record" claim true of the actions
    as well as the fingerprint.
  - Rejected (1, low): a proposal to verify that `commit` actually changed the target's bytes. That
    is the `commit` contract's business, and it would break a legitimately idempotent no-op commit.

## Design Notes

**Why the AD-57 freshness check is not the P-07 hash guard, and why it lives in `plan/build.py`.**
P-07 ("hash guards are checked in detect, never in apply; apply trusts the plan") prevents apply
from re-adjudicating, per artifact, whether a managed file was hand-edited — the
`detect/hashes.py::check_managed_file(path, recorded_sha)` question, whose answer decides an
artifact's fate. AD-57 asks a different, whole-plan question: is this `Plan` still a true
description of the repo? It answers once, before anything runs, and its only outcomes are "proceed
with the entire plan" or "refuse the entire plan" — apply never grades an individual artifact. The
two are separable, but the MECHANISM overlaps (both hash file content), and the shipped
`tests/meta/test_p07_no_hash_comparison_in_apply.py` encodes P-07 structurally, as an import ban on
`seed/apply/**`. Putting `fingerprint_drift` in `plan/build.py` satisfies both without touching
either rule: the meta test stays byte-identical and genuinely green (no hashing lives under
`seed/apply/`), and the verifier sits beside `build_plan`, the fingerprint's sole producer, so
producer and verifier cannot drift apart — the failure mode a second, independent reimplementation
inside `apply/` would invite. This is a deliberate reading of a real tension, stated so it can be
disagreed with explicitly rather than discovered later.

**Why verification reads the target unconditionally instead of reusing `_current_text`'s
state gate.** `_current_text` returns `""` for an `ABSENT` artifact WITHOUT touching the
filesystem. Reusing it verbatim would make the most important drift case invisible: an artifact
absent at plan time that has since been created on disk would re-hash to `""`, match, and be
silently clobbered by apply — exactly AR-5. Reading unconditionally (with the same
absent/non-file/unreadable/non-UTF-8 → `""` degradation) catches it. The one divergence from
`build_plan`'s own read is an entry whose path escapes `repo_root` (classified `ABSENT` for that
reason): verification may read a real file there and report drift where `build_plan` recorded
`""`. That direction is fail-closed — it refuses rather than proceeds — and such an entry is
already pathological, so the extra strictness is accepted rather than special-cased.

**Why the stale check precedes the empty-plan short-circuit.** Read in isolation, "apply is a
no-op on an empty plan and exits 0" and "apply refuses a plan whose fingerprint no longer matches"
collide when both hold. Refusing wins: an empty plan asserts "this repo needs nothing", and if the
repo has moved since, that assertion is exactly what is no longer known to be true — a re-plan is
the correct next step, and AD-60 makes re-planning cheap. The empty-plan AC is satisfied on a fresh
plan, which is the only state in which "nothing to do" is a trustworthy answer.

**Why `commit` is a callback rather than the runner materializing artifacts.** The AC requires
fault injection at three different action indices, which is only expressible if the per-action step
is injectable. Beyond that, the epic's own dependency graph puts materialization downstream: 10.6
(`adopt`) depends on 10.3 **and Epic 8** — the region engine — which is where per-class writing is
actually wired. Keeping `run.py` ignorant of `ArtifactClass` is also what makes "consumes only a
`Plan`" (P-04) literally true: the runner never needs the `Manifest` that region bodies, formats,
and model version would drag in. The cost is the stated `commit` contract (write only within
`repo_root / action.target_path`); anything else is outside the transaction, and the runner says so
rather than pretending otherwise.

**Amendment made during implementation verification (stricter than the contract, never weaker).**
The Always bullet enumerates "every `artifact_hashes` pair", and the matrix's Plan-integrity row
covers a hashed id no `Action` carries. Verifying the delivered code surfaced the mirror case as a
live hole: `Plan.from_json_dict` validates that `actions` are unique and sorted but never
cross-checks them against `artifact_hashes`, so a hand-edited `plan.json` that DROPPED a pair would
leave that artifact entirely unverified — precisely the stale content this check exists to catch.
`fingerprint_drift` therefore checks the correspondence in BOTH directions. This only ever refuses
more, never fewer, plans than the contract describes.

**Rollback shape.**

```python
for index, action in enumerate(plan.actions):
    target = repo_root / action.target_path
    snapshots.append((target, target.read_bytes() if target.is_file() else None))
    commit(action)                     # anything raising here unwinds everything before it
# on failure, in reverse:
#   bytes -> fs.write(target, bytes, ...)   |   None -> fs.remove(target, ...) if it exists
```

Reverse order is what makes two actions sharing a `target_path` unwind correctly; a forward restore
would leave the later action's snapshot (itself post-first-write content) as the final state. Every
restore is attempted even after one fails, so a single unrestorable path never abandons the rest;
only then does `InternalError` report the residue — a failed rollback IS the partial state NFR-R1
forbids, so it must be loud rather than swallowed into the original exception.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: green, including the new
  `test_seed_apply_run.py` and the extended `test_seed_plan_build.py`; `test_p07_no_hash_comparison_in_apply.py`
  green with `run.py` now in its scan surface; `test_seed_no_bare_exception.py` and
  `test_ad3_ad4_import_linter.py` unchanged and green.
- `git diff --stat -- src/shared/packages/pyforge-marshal/tests/meta/` — expected: **empty**. No
  meta test is edited by this story.
- `python scripts/spec_surface_reconcile.py` — expected: no NEW finding attributable to
  `pyforge-marshal`. **Pre-existing red at baseline `64e717d`** with 2 findings, both
  `pyforge-mason/spec-django-accelerator-framework` (`drift-blind` + `no-baseline`); its remedy is a
  human-invoked `--write-baseline`, which this script deliberately refuses to expose. Not this
  story's surface — see Disposition below.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: **green, 74 passed**. This gate
  was pre-existing red at baseline on one case
  (`test_conda_run_deps_add_nothing_undeclared[pyforge-mason]`), filed as `DW-FU-10-2` and the
  reason Story 10.2 deferred; because it is a *deterministic verify command every story in this
  loop must pass*, carrying it forward blocked this story from landing. **Closed here** — see
  Disposition below. `DW-FU-10-2` is now `resolved`.

**Disposition of the two pre-existing red gates** (stated, not left as scenery): both are
`pyforge-mason` packaging/governance defects, both verified byte-identical to baseline `64e717d`
before this story's first edit (`git diff 64e717d..HEAD` touches neither `tests/packaging/`, nor
`src/shared/packages/pyforge-mason/`, nor the root `pixi.toml`), and both lie outside this story's
Surface (`seed/apply/run.py`, `seed/plan/build.py`).

- **`DW-FU-10-2` — FIXED (out-of-surface, deliberate).** "Pre-existing" explains why a finding is
  not this story's fault; it never explains why it stays, and this one reddens a gate every
  subsequent story in Epic 10 must pass. The remedy is exactly the one `DW-FU-10-2`'s own evidence
  predicted and the assertion message itself names: `pyforge-mason`'s five engines
  (`pixi`, `twine`, `conda-lock`, `python-build`, `gh`) are justified in
  `tests/packaging/test_dependency_completeness.py`'s `CONDA_ONLY_RUN_DEPS`. Verified by reading
  the code, not assumed: every one is located with `shutil.which` and driven by `subprocess.run`
  from `engines/*.py`, and `grep -rE "^\s*(import|from)\s+(build|twine|conda_lock|pixi|gh)\b" src/`
  over the whole package returns nothing — so mason never IMPORTS any of them. Note the precise
  claim, because the review pass caught an earlier, sloppier one: only `pixi` (Rust) and `gh` (Go)
  are genuinely not Python distributions; `twine`, `conda-lock`, and `python-build` (conda-forge's
  spelling of `build`) are real importable PyPI distributions that mason simply drives as
  subprocesses. That is a property of today's code, not of the packages, so it is now **asserted**
  rather than trusted — see the two new guards below. Declaring them in `[project.dependencies]` (the
  assertion's other branch) would push five CLI tools onto every `pip install pyforge-mason`,
  against FR-41's lean-dependency floor. This is the *sanctioned escape hatch*, not a weakening of
  the gate: it is the same shape already recorded there for `pyforge-warden`'s
  `deptry`/`osv-scanner` and `pyforge-steward`'s `age`, their version ranges stay guarded by
  `pyforge-mason/tests/meta/test_engine_version_range_sync.py` (all five pairs, verified green),
  and `CONDA_ONLY_RUN_DEPS` feeds only `_conda_only`, so nothing else changes behavior. The review
  pass hardened it further, because an exemption table with no ratchet is exactly the "permanent
  excuse" this file's two sibling tables are explicitly guarded against: `test_conda_only_entries_
  are_still_conda_run_deps` fails when an entry stops naming a real run-dep, and
  `test_conda_only_run_deps_are_never_imported` asserts the premise itself over BOTH the `hard` and
  `deferred` import buckets — closing a real hole, since both existing call sites discard
  `_scan_imports`' `deferred` result (`hard, _ = …`), so a lazy `import twine` inside a function
  would otherwise have shipped an unusable wheel with no gate firing. Both are mutation-verified.
  Precedent
  for a marshal story editing this table for a sibling package is established: Story 4.11 landed
  `CONDA_ONLY_RUN_DEPS["pyforge-steward"] = {"age"}` in this same file. No intent-contract term is
  touched — the Never list names meta tests under `seed/` plus `detect/hashes.py`,
  `plan/types.py`, `engine/copier.py`, and the Code Map's "`pyproject.toml` / `pixi.toml` — no
  change" still holds byte-for-byte.
- **The surface-baseline gap — NOT fixed, re-filed.** `spec_surface_reconcile.py` still reports its
  2 findings, both `pyforge-mason/spec-django-accelerator-framework` (`drift-blind` + `no-baseline`),
  byte-identical to baseline. Its remedy is a human-invoked `--write-baseline`, which the script
  deliberately refuses to expose to an unattended agent, so it genuinely cannot be closed here.

**Manual checks:**
- `seed/state/` is still `__init__.py`-only in this worktree (Story 10.2 is `done` but deferred on
  the gate above, so its code is not in this baseline). Confirm nothing in this story imports or
  assumes `seed.state`, so the two merge cleanly and "state is untouched" stays structurally true.


## Auto Run Result

Status: done — resumed after the loop's deterministic verifier failed the previous session's run.

**What this run did.** The failing gate was `pixi run --frozen -e pyforge-ci pyforge-deps-test`
(rc=1), on `test_conda_run_deps_add_nothing_undeclared[pyforge-mason]` — the pre-existing
`DW-FU-10-2` this spec had disposed of as "not fixed here". That disposition was wrong for a gate
the loop treats as a hard landing precondition: deferring it did not park the debt, it blocked
this story and everything behind it. Fixed at the source the assertion message itself names, then
a fresh adversarial review pass over the whole diff caught two high-severity defects in code the
FIRST review pass had added, plus nine more.

**Files changed** (`<intent-contract>` untouched; no `pyproject.toml`, no `pixi.toml`, no meta
test):
- `tests/packaging/test_dependency_completeness.py` — `CONDA_ONLY_RUN_DEPS["pyforge-mason"]` for
  the five subprocess engines, plus the two guards that make that exemption honest
  (`test_conda_only_entries_are_still_conda_run_deps` — the ratchet this table lacked while both
  its siblings had one; `test_conda_only_run_deps_are_never_imported` — asserts the premise over
  the `deferred` import bucket both existing call sites discard).
- `.../seed/apply/run.py` — containment now refuses non-normalized targets before resolution and
  refuses the repo root itself; unresolvable paths become `PreconditionFailure` instead of a raw
  `ValueError`; `_restore` re-checks containment per path; corrected remedy text and three
  docstring overclaims.
- `.../seed/plan/build.py` — ABSENT predicate restored to `exists()` (producer/verifier agreement);
  symmetric duplicate-id check on `artifact_hashes`.
- `.../tests/unit/test_seed_apply_run.py`, `.../tests/unit/test_seed_plan_build.py` — 9 regression
  tests; two fixture-fidelity corrections.
- `.../planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` — two entries naming every path.
- `deferred-work.md` — `DW-FU-10-2` → `resolved`; `DW-FU-10-3-8` … `DW-FU-10-3-10` filed.

**Review findings:** 0 intent_gap, 0 bad_spec, 11 patched (high 2, medium 4, low 5), 3 deferred,
4 rejected. Full detail in the Review Triage Log's second entry.

**Verification** (all re-run on the final tree):
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — **84 passed** (was 1 failed / 73 passed).
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — **4246 passed**, 9 deselected
  (baseline 4237).
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — **1409 passed**, 2 deselected.
- `git diff --stat -- src/shared/packages/pyforge-marshal/tests/meta/` — **empty**.
- `python scripts/spec_surface_reconcile.py` — unchanged at its 2 pre-existing
  `pyforge-mason/spec-django-accelerator-framework` findings; no new finding.
- Mutation-verified rather than assumed: 8 of the 9 new tests were confirmed to FAIL against the
  pre-fix source (the 9th replaces a monkeypatched assertion with a real-path one, so it passes
  both ways by design), and both new packaging guards were confirmed to fail on the mutation each
  exists to catch.

**Residual risks.**
- The surface-baseline red (`spec_surface_reconcile.py`, 2 findings) is NOT fixed. Its remedy is a
  human-invoked `--write-baseline`, which the script deliberately refuses to expose to an
  unattended agent. Byte-identical to baseline; genuinely not closable here.
- Ten bounds remain filed against this story (`DW-FU-10-3` … `DW-FU-10-3-10`). The two that most
  affect a caller: `DW-FU-10-3` — writing `plan.json` to its own canonical path flips the
  fingerprint's `dirty` flag, so the first apply of a freshly built plan refuses itself as stale on
  a clean repo (Story 10.6 owns the write-order fix); and `DW-FU-10-3-9` — `build_plan` can emit an
  escaping-target action, which now correctly refuses the whole plan but needs manifest-load
  validation to prevent.
- Rollback restores CONTENT only. Mode, directories, symlinks, and never-write targets remain
  documented residues with their own ledger entries.
