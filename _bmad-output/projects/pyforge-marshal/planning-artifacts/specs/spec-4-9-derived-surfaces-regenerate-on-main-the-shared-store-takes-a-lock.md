---
title: 'Derived surfaces regenerate on main; the shared store takes a lock'
type: 'feature'
created: '2026-08-06'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md']
warnings: []
baseline_revision: 'c0c0736eaf113db22468a70a6bb3a9f90c0b9076'
---

<intent-contract>

## Intent

**Problem:** AD-42 (the PRD Q-10 decomposition, resolved 2026-07-31 against `deferred-work-ledger.md`'s DW-1-4-4 scope note) settled a wider question raised by concurrent loop lines sharing state: "nothing serializes concurrent writes to the SHARED artifacts every loop line writes." The resolution had two halves. Half one — regenerated/derived reporting surfaces (the sprint feed, the console report `marshal deploy refresh-feed` prints) must be RE-DERIVED on the integration branch after a landing, never merged in from a loop home's own copy — is **already structurally true** of this package's shipped code (`cli/land.py`'s resync step calls `cli/deploy.py::reconcile_feed` against `root = repo_root()`, the checked-out `main`; `_run_resync_commands` runs every configured command with `cwd=root`, never `home`) but has never been PROVEN by a test, and nothing stops a future edit from silently regressing it (e.g. a careless refactor threading `home` in instead of `root`). Half two — "an advisory file lock serializes concurrent appends to the canonical Tier-3 store" — has no implementation at all: `cli/deploy.py::run_promote` is the one place in this surface that performs a genuine read-then-write-then-commit sequence against the canonical, git-tracked `planning-artifacts/specs/` directory every loop-home worktree of a project shares (Story 1.5's single-sourced-via-backlink store) — two concurrent `marshal deploy promote` invocations for the SAME project (plausible: an operator's manual run overlapping a scheduler-triggered one, or two concurrent loop-home lines both landing around the same time) can each independently scan "already promoted," compute overlapping `plan.to_promote`, and race through `copy_file`+`commit_paths` with no coordination.

**Approach:** (1) a regression test locking in the ALREADY-CORRECT "regenerate on main, never merge from a home" invariant for `land`'s resync path — no production code change for this half, since the invariant already holds; a test is the deliverable. (2) a new `FsPort.acquire_advisory_lock`/`release_advisory_lock` pair (`adapters/fs_local.py::LocalFs`, POSIX `fcntl.flock` on a sibling `.lock` file, bounded blocking wait), applied around `run_promote`'s write-then-commit critical section (the copy_file loop + the `commit_paths` call) — the ONE concrete "concurrent append to the canonical Tier-3 store" scenario this package's own surface contains. (3) the journal's own two-writer case (Story 3.1/3.2's per-run-directory + `append_line`'s single-`os.write()` `O_APPEND` protocol, AD-25/AD-28/AD-30) is EXPLICITLY excluded from the new lock — it already has its own, different, already-shipped concurrency answer (F-6's own domain) — proven by a boundary test rather than left as an unstated assumption.

## Boundaries & Constraints

**Always:**
- **`FsPort.acquire_advisory_lock(path: Path, *, timeout_s: float) -> AdvisoryLock`** (NEW): acquires a POSIX advisory lock (`fcntl.flock(fd, LOCK_EX)`) on a sibling lock file at `path.with_suffix(path.suffix + ".lock")`, creating it if absent. Blocks up to `timeout_s` (a bounded retry loop with a short sleep between attempts, since `fcntl.flock` itself has no timeout parameter — mirrors this package's own "never an unbounded block" convention, e.g. every `ProcessPort.run` call already carries an explicit timeout). Raises `FsError` if the lock cannot be acquired within `timeout_s`, or on any other I/O failure (unwritable parent directory, permission error). Returns an opaque `AdvisoryLock` handle (holds the open file descriptor) for `release_advisory_lock`.
- **`FsPort.release_advisory_lock(lock: AdvisoryLock) -> None`** (NEW): releases the lock (`fcntl.flock(fd, LOCK_UN)`) and closes the descriptor. Idempotent-safe to call once per successful `acquire_advisory_lock` — never raises on a lock this process itself holds (mirrors `remove_worktree`'s own "the caller already knows this is safe" precondition shape); a caller MUST release via `try`/`finally` around the guarded section, matching this codebase's established explicit-pair convention (no `contextlib` context managers anywhere else in `ports/`/`adapters/`, so this story does not introduce the first one).
- **The lock is ADVISORY, not mandatory** — it only serializes two processes that both CALL `acquire_advisory_lock` on the same path; it provides no protection against a writer that bypasses the primitive entirely (matches `fcntl.flock`'s own real-world semantics, and this package's own "advisory" wording in the AC itself).
- **`run_promote` acquires the lock on `specs_dir` (the canonical, git-tracked `planning-artifacts/specs` directory itself, not a file inside it) BEFORE the `copy_file` loop begins, and releases it in a `finally` AFTER `commit_paths` returns (success or failure)** — the smallest section that actually needs serialization: from "decide what to promote" is already scoped by `scan` (computed before the lock, cheap and re-checked-fresh on every invocation per Story 4.6's own idempotence precedent) through "the promotion is durably committed." A lock-acquisition failure (`FsError`, e.g. another process is already promoting and `timeout_s` elapsed) is a registered WARN finding (never blocks re-running `promote` later — re-entrant, matching every other command in this family) and the run reports `data.promoted: []`, `data.promoted_count: 0` with `data.lock_contended: true` — no copy/commit attempted.
- **`land`'s resync ("regenerate on main, never merge from a home") is proven, not merely assumed**: a new test asserts `reconcile_feed`'s own I/O (`_run_resync_commands`'s `process.run(..., cwd=root, ...)`, `_gather_claimed_commits`'s read of `home` — read-only, feeding the pure `reconcile_feed_domains` core, never written back to `home`) never WRITES anywhere under `home`'s own path, using a fake `ProcessPort`/`FsPort` that would fail the test if `cwd` or any write target ever resolved under `home`.
- **The journal's own two-writer case is explicitly out of scope** — `_DeployRun.write`/`append_line`'s existing per-run-directory + single-`os.write()`-on-`O_APPEND` protocol (AD-25/AD-28/AD-30, Stories 3.1/3.2) is UNTOUCHED by this story's new lock; a boundary test documents this explicitly (asserts `_DeployRun`'s own journal-write call sites never call `acquire_advisory_lock`), so a future reader does not mistake the new lock as covering journal writes too.

**Never:**
- No lock around `_DeployRun`'s journal writes — F-6's own domain, already solved differently (per-run isolation, not mutual exclusion on one shared file).
- No lock around `run_land_story`'s direct merge (`merge_branch`'s own detached-worktree + compare-and-swap `git update-ref`, Story 4.3) or `run_land`'s PR-based merge (`merge_pr`'s own `--match-head-commit`, Story 4.8) — both already have their OWN, git-native concurrency-safety mechanisms; this story's lock is for a plain filesystem write+commit sequence that has none.
- No change to `_run_resync_commands`/`reconcile_feed`'s existing behavior — both are already correct; this story adds proof, not new logic, for that half of the AC.
- Do not build a general-purpose distributed lock, a lock registry, or lock-file cleanup/staleness detection beyond `fcntl.flock`'s own OS-level guarantee (a lock held by a dead process is automatically released by the kernel when its last fd closes) — out of scope; `timeout_s` bounding the wait is the only robustness measure this story adds.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Single `marshal deploy promote` invocation, no contention | Lock free | Acquires immediately, promotes, releases | No finding |
| Two concurrent `promote` invocations for the SAME project | Second run's `acquire_advisory_lock` blocks | First completes and releases; second then acquires and proceeds (re-scans fresh, no duplicate promotion since the first run's `commit_paths` already changed the git-tracked "already promoted" state) | No finding, sequential success |
| Lock cannot be acquired within `timeout_s` | Genuinely stuck/very slow holder | Refused cleanly, `data.lock_contended: true`, `data.promoted: []` | Registered WARN, re-entrant (re-run `promote` later) |
| Lock file's parent directory is unwritable | Permission error | `FsError` from `acquire_advisory_lock` | Registered WARN, same handling as timeout |
| `run_promote` with nothing to promote (`plan.to_promote` empty) | No candidates | Lock is never acquired at all (nothing to serialize) | No finding |
| `land`'s resync with `landing_resync_commands` configured | A command runs | `process.run` invoked with `cwd=root` (never `home`) — asserted by the new proof test | No finding |
| Two concurrent `land`/`promote` runs for DIFFERENT projects | Different `specs_dir` per slug | No contention (lock path is per-project, scoped to `specs_dir`) | No finding |
| A crashed process leaves the lock file present but unlocked | OS releases the `flock` on process exit (kernel-level, not file-existence-based) | The NEXT `acquire_advisory_lock` succeeds immediately (the file's mere EXISTENCE never blocks; only a live `flock` hold does) | No finding |

</intent-contract>

## Code Map

- `src/pyforge/marshal/ports/fs.py` — EDIT. `AdvisoryLock` frozen dataclass (holds the lock file `Path` and an opaque OS-level handle); `FsPort.acquire_advisory_lock`/`release_advisory_lock` Protocol methods.
- `src/pyforge/marshal/adapters/fs_local.py` — EDIT. `LocalFs.acquire_advisory_lock`/`release_advisory_lock`: `fcntl.flock` on a sibling `.lock` file, bounded retry loop for `timeout_s`, `FsError` translation.
- `src/pyforge/marshal/cli/deploy.py` — EDIT. `run_promote` acquires the lock on `specs_dir` before the `copy_file` loop, releases in `finally`; a lock-acquisition failure is a new registered WARN finding (`MRS-DEPLOY-023`) and a clean, re-entrant refusal.
- `src/pyforge/marshal/core/findings.py` / `core/verdict.py` — EDIT. Register + classify `MRS-DEPLOY-023` (`Verdict.WARN`).
- `tests/unit/test_fs_local.py` — EDIT. `acquire_advisory_lock`/`release_advisory_lock` matrix: single acquire/release, a second acquire blocking behind a held lock (via a subprocess or thread holding it, released after a short delay, proving the second acquire eventually succeeds), timeout, permission failure.
- `tests/unit/test_deploy.py` — EDIT. `run_promote` lock-acquisition-failure path (a fake `FsPort` whose `acquire_advisory_lock` raises `FsError`) reports `lock_contended: true` and promotes nothing; a real two-process-style test (fake `FsPort` tracking acquire/release call order across two sequential `run_promote` calls sharing one fake lock state) proving the second run's copy/commit never overlaps the first's.
- `tests/unit/test_land.py` — EDIT (or a NEW small test module). The "regenerate on main, never a loop home" proof test for `reconcile_feed`/`_run_resync_commands`, and the journal-out-of-scope boundary test.

## Design Notes

- **Why `specs_dir` itself is the lock path, not a dedicated lock file inside it:** `acquire_advisory_lock` derives the sibling lock file from the path it's given (`path.with_suffix(...)`) — passing the directory itself keeps the call site simple (`fs.acquire_advisory_lock(specs_dir, ...)`) and the lock file (`specs/.lock` conceptually, or a sibling named path) lives alongside the store it protects, discoverable by an operator investigating a stuck lock.
- **Why the lock is acquired around copy+commit, not around the whole `run_promote` invocation (including the pre-lock `scan`):** `_scan_promotions` is a read-only git/filesystem scan, already cheap and safe to run unlocked and concurrently (two processes reading the same git history is not a race) — locking only the WRITE section minimizes how long a slow promote blocks a concurrent one, and matches this package's own "lock the smallest section that needs it" default (no precedent elsewhere in this codebase for locking reads).
- **Why `land`'s "regenerate on main" half needed no code change:** verified by direct inspection during this spec's own research — `reconcile_feed`'s `root = repo_root()` and `_run_resync_commands`'s `process.run(tokens, cwd=root, ...)` already never reference `home` at all in this call path (the ONLY place `home` appears in `run_land`'s own resync is `_gather_claimed_commits`'s READ of the harness's journal/snapshot state, unchanged output, never written back). This story's contribution to that half is a regression test, not a fix.

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`

## Spec Change Log

**1. `tests/unit/test_findings.py`'s exact-contents meta-test needed updating — not named in the original Code Map.** `REGISTERED_CODES`'s completeness meta-test enumerates every registered finding code explicitly; adding `MRS-DEPLOY-023` without updating that test's own expected set fails it immediately. A gap in this spec's own Code Map (worth naming in future specs touching `REGISTERED_CODES`), fixed as part of normal implementation, not a review finding.

## Review Triage Log

### 2026-08-06 — Review pass 1 (Blind Hunter + Edge Case Hunter, parallel)

- intent_gap: 0
- bad_spec: 0
- patch: 3 (medium 1, moderate 2)
- defer: 2
- reject: 0
- addressed_findings:
  - `[medium]` `[patch]` **`AdvisoryLock.release_advisory_lock` is not actually idempotent despite its own docstring claiming "idempotent-safe" — a second call operates on an fd number the OS may have already reassigned to an unrelated open file elsewhere in the process, silently unlocking/closing the WRONG resource instead of raising.** Found by the Blind Hunter. Not currently triggered (the sole call site, `run_promote`'s single `try`/`finally`, never double-releases), but the primitive's own contract was misleading for a future caller. Fixed: both `ports/fs.py`'s Protocol docstring and `adapters/fs_local.py`'s implementation docstring now say "call AT MOST ONCE," name the fd-reuse hazard explicitly, and no longer claim idempotence.
  - `[moderate]` `[patch]` **The `.lock` sidecar file (`planning-artifacts/specs.lock`) was never removed and had no `.gitignore` entry — it lives inside a TRACKED `planning-artifacts/` directory, so after the first-ever promotion every project permanently grows an untracked file one `git add -A`/`git add .` away from being committed upstream.** Found by the Edge Case Hunter. Fixed: `release_advisory_lock` now best-effort `os.remove()`s the lock file after unlock+close (safe even against a concurrent acquirer already holding an open fd — POSIX unlink only detaches the directory entry); `.gitignore` gained an explicit `_bmad-output/projects/*/planning-artifacts/specs.lock` pattern as defense in depth for a lock a crashed holder left behind (harmless either way — the file's mere existence never blocks a later acquire).
  - `[moderate]` `[patch]` **The test suite proved the lock primitive under contention (`test_second_acquire_times_out_behind_a_held_lock`, bare `LocalFs`) and proved `run_promote`'s WARN-reporting path under SIMULATED contention (a mock `FsPort` that raises immediately), but nothing exercised `run_promote`'s real try/except/else/finally wiring against GENUINE, concurrent `fcntl.flock` contention.** Found by the Edge Case Hunter. Fixed: new test `test_promote_hits_the_real_contention_path_when_another_holder_has_the_lock` -- a background thread acquires the REAL lock via its own independent `LocalFs`/file descriptor (a second, genuinely distinct holder, exactly as `fcntl.flock` treats two separate opens even within one process) and holds it past a monkeypatched-short `_PROMOTE_LOCK_TIMEOUT_S`, proving the foreground `run_promote` call takes the real `MRS-DEPLOY-023` path against actual contention.
- deferred (not fixed in this pass, appended to `deferred-work.md` as NEW entries):
  - `[low]` D1: `adapters/fs_local.py`'s new module-level `import fcntl` makes the whole module unimportable on Windows (no stdlib equivalent) -- very likely consistent with this package's already-established POSIX-only precedent (`adapters/process_posix.py`'s own name/shape), but not independently confirmed as a documented decision in this pass.
  - `[low]` D2: `acquire_advisory_lock`'s `timeout_s` accepts a negative value without validation, producing a confusing (but not unsafe) error message; unreachable via the one shipped call site's hardcoded positive constant.
- rejected: none this pass.

## Suggested Review Order

**The two real correctness/hygiene fixes — start here**

- `LocalFs.release_advisory_lock`'s lock-file cleanup + the corrected double-release docstring.
  [`fs_local.py`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/fs_local.py) — search `def release_advisory_lock`
  [`ports/fs.py`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/fs.py) — search `def release_advisory_lock`

- `.gitignore`'s new `specs.lock` pattern.

**The lock primitive + its wiring**

- `acquire_advisory_lock`'s bounded polling loop.
  [`fs_local.py`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/fs_local.py) — search `def acquire_advisory_lock`

- `run_promote`'s lock acquire/release around the copy+commit section.
  [`deploy.py`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py) — search `_PROMOTE_LOCK_TIMEOUT_S`

**Tests (peripherals)**

- The real-contention thread test, plus the "regenerate on main, never a loop home" and journal-out-of-scope proof tests.
</intent-contract>
