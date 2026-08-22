---
title: 'Story 12.5: The spec surface baseline write race is closed'
type: 'bugfix'
created: '2026-08-21'
status: 'in-progress'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
baseline_revision: '3783e63bc5b70a2806be2e432a6fd1784a219105'
---

<intent-contract>

## Intent

**Problem:** `scripts/spec_surface_check.py --write-baseline` does an unlocked
read-modify-write of `scripts/.spec-surface-baseline.json`: the scoped path reads the
committed file, mutates only the named spec's key(s), and writes the whole file back.
Two concurrent invocations for different `--spec` targets — plausible under this repo's
documented parallel-BMAD-agent pattern — race, and the loser's just-stamped entry is
silently clobbered (both exit 0). Reproduced live pre-fix: 4/20 concurrent-stamp trials
lost a write. This is CAP-5 of `spec-fleet-hygiene-verification-exemplar-program`,
cited there as `DW-13-5-2`; the atlas ledger records the race itself under
`DW-13-5-3` (its `DW-13-5-2` is the adjacent missing-staleness-safeguards entry) —
this story closes the RACE, whichever id names it.

**Approach:** Serialize the whole read-modify-write span under a self-contained,
stdlib-only advisory lock (`fcntl.flock` on a raw fd against a sidecar
`scripts/.spec-surface-baseline.json.lock`, mirroring the herald/marshal fleet
precedent inline), and make the write itself atomic (temp file + `os.replace`) so a
concurrent reader never sees a torn baseline. Refactor the critical section into small
module-level functions so the race is provable with a deterministic, controlled
interleaving in tests.

## Boundaries & Constraints

**Always:**
- Self-contained stdlib-only: never import `pyforge.marshal`, `pyforge.herald`, or any
  fleet package from this script (it must run under plain `python` with no env).
- The lock must bracket the ENTIRE read → merge → write span (locking only the write
  re-opens the race), for both the scoped and the full (`--spec`-less) stamp paths.
- Lock the sidecar file, never the baseline itself — `os.replace` swaps the baseline's
  inode, so a lock held on it would not exclude the next locker.
- No timeout, no staleness detection, no retry machinery: `flock` releases on process
  exit/crash; a second caller blocks until free (herald `locking.py`'s documented
  rationale, adopted verbatim).
- Never unlink the lockfile after use — unlink-while-others-wait recreates the race
  (a waiter holds the old inode while a newcomer locks a fresh file). It stays on disk,
  gitignored.
- Existing CLI contract unchanged: flags, exit codes (0 stamped / 2 usage or unknown
  spec), stderr redirect message, merge-never-rewrite scoped semantics, JSON format
  (`indent=1, sort_keys=True`, trailing newline).
- Concurrency tests are deterministic: prove the race with a controlled interleaving
  (barrier/lock-held gating), never a bare timing race; any waits are safe-direction
  only (long enough to be sure, never "hope both landed in the window").
- Tests live in `.claude/skills/conda-forge-expert/tests/meta/test_spec_surface_check.py`
  (the file that already owns this script's behavior), reusing its
  `_fixture_repo`/`_patched_checker` harness.

**Block If:** none identified — mechanism, location, and precedent are all settled.

**Never:**
- Never widen scope into atlas `DW-13-5-2`'s OTHER safeguards (hash the git blob not
  working-tree bytes, memlog-names-the-files cross-check, multi-owner refresh) — those
  stay open ledger entries; this story is the race only.
- Never touch `src/shared/packages/pyforge-doctor/` — the read-only port never writes,
  so it needs no lock (Charter §6; it benefits from the atomic replace for free).
- Never stamp or "reconcile" foreign baselines (the 63 pre-existing detector FAILs from
  in-flight steward/doctor-package/marshal/mason work are NOT this story's to accept;
  a scoped stamp for the mason specs governing the edited test file would also accept
  their unrelated pending drift).
- Never add Windows (`msvcrt`) support — this is a Linux-side repo tool invoked with
  plain `python`; herald needed the dual path only because it targets win-64.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Concurrent scoped stamps | Two invocations, different `--spec`, forced read-overlap interleaving | Fully serialized: both entries updated, every unrelated entry preserved, both exit 0 | No error |
| Lock already held | Another process holds the sidecar lock | Invocation blocks (no timeout), proceeds after release, stamps correctly | No error |
| Holder crashes | Lock-holding process dies mid-span | OS releases the flock; next caller proceeds | No error |
| Concurrent reader | Doctor's read-only detector reads during a stamp | Sees old or new baseline, never a torn/partial file (atomic `os.replace`) | No error |
| Full stamp vs scoped stamp | `--write-baseline` (all) races `--write-baseline --spec X` | Serialized; whichever runs second operates on the first's completed write | No error |
| Unwritable scripts/ dir | Lockfile cannot be created | OSError propagates (current behavior for an unwritable baseline; no new swallowing) | Traceback, non-zero exit |

</intent-contract>

## Code Map

- `scripts/spec_surface_check.py` -- the defect: `main()`'s merge block
  (`BASELINE.read_text` → mutate → `BASELINE.write_text`, lines ~205-214). Extract
  `_read_baseline()`, `_baseline_lock()` (contextmanager: `os.open` raw fd on
  `BASELINE.with_name(BASELINE.name + ".lock")`, `fcntl.flock LOCK_EX`, close in
  `finally`; resolve the path at call time so tests can monkeypatch `BASELINE`),
  `_write_baseline(merged)` (same-dir `.tmp` + `os.replace`; tmp name is safe because
  it is only ever written under the lock), and `_stamp_baseline(spec_names, current)`
  (the locked critical section returning the scope message). `main()` keeps
  arg-validation and `_live_state()` outside the lock (expensive; reads the working
  tree, not the baseline) and calls `_stamp_baseline`. Docstring gains a short
  DW-13-5-2/DW-13-5-3 concurrency note.
- `.gitignore` -- ignore `scripts/.spec-surface-baseline.json.lock` and
  `scripts/.spec-surface-baseline.json.tmp` (precedent: `planning-artifacts/specs.lock`,
  line ~733).
- `.claude/skills/conda-forge-expert/tests/meta/test_spec_surface_check.py` -- new
  S-12.5 test section; extend `_patched_checker` with an importable-module loader
  (importlib from the patched copy) for the in-process interleaving test.
- READ-ONLY precedent: `src/shared/packages/pyforge-herald/src/pyforge/herald/locking.py`
  (sidecar-lock rationale), `pyforge.marshal.adapters.fs_local::acquire_advisory_lock`
  (raw-fd flock shape, AD-42). Ledger record: atlas `deferred-work-ledger.md`
  `DW-13-5-3` (and `DW-13-5-2` context).

## Tasks & Acceptance

**Execution:**
- [ ] `scripts/spec_surface_check.py` -- extract `_read_baseline` / `_baseline_lock` /
  `_write_baseline` / `_stamp_baseline`; wire `main()` through them -- closes the race
  while keeping the CLI contract byte-compatible on the happy path
- [ ] `.gitignore` -- add the two sidecar entries -- keeps `git status` clean after any
  stamp
- [ ] `test_spec_surface_check.py` -- add: (1) deterministic forced-interleaving test:
  load the patched module in-process, wrap `_read_baseline` with a 2-thread barrier
  (bounded wait, `BrokenBarrierError` tolerated — under the lock the second reader can
  never reach it), run two `_stamp_baseline` calls for different specs in threads,
  assert BOTH entries updated and unrelated entries preserved (fails deterministically
  on the unlocked code: both reads complete pre-write and the last write clobbers);
  (2) cross-process serialization test: test flocks the sidecar, launches the CLI
  subprocess, asserts it has not completed after a safe-direction wait, releases,
  asserts completion + correct stamp; (3) atomicity/no-residue assertions: no `.tmp`
  left behind, baseline parses, lockfile exists and is ignorable
- [ ] Verify the reproduction driver (scratchpad `repro_race.py`, 20 concurrent-stamp
  trials) reports 0 lost writes against the fixed script

**Acceptance Criteria:**
- Given two concurrent `--write-baseline` invocations against
  `scripts/.spec-surface-baseline.json`, when both run, then neither write is silently
  lost (CAP-5; reproduces and fixes the race cited as `DW-13-5-2`, recorded in the
  atlas ledger as `DW-13-5-3`).
- Given the pre-fix script, when the reproduction driver runs 20 concurrent-stamp
  trials, then it demonstrates lost writes (observed: 4/20); given the fixed script,
  the same driver reports 0/20.
- Given the pre-existing test suite for this script (6 tests), when it runs post-fix,
  then all still pass unmodified.
- Given the repo-wide spec-surface detector, when it runs post-fix, then the ONLY new
  findings versus the captured pre-change set are the two documented `drift` findings
  for the edited test file under the mason blanket globs (left for the landing
  session's reconciliation, per the Story 12.4 precedent).

## Spec Change Log

## Review Triage Log

## Design Notes

- **Spec location deviation (recorded):** this spec is authored directly at the
  tracked `planning-artifacts/specs/` path (sibling format) instead of the workflow's
  default Tier-3 `implementation-artifacts/` scratch location — per the dispatching
  instruction, since story specs are durable/tracked by repo convention and this
  worktree's Tier-3 is torn down at landing.
- **Why lock-then-read, not compare-and-swap:** CAS (re-read + verify before replace)
  still needs a serialization point to be correct and complicates the failure story;
  a blocking advisory lock is the fleet's settled pattern and the whole span is
  sub-second.
- **Why the tests can be deterministic:** mutual exclusion is a logical property —
  with the lock, the "both readers read the stale state" interleaving is impossible
  by construction, so a barrier on the read path either breaks (fixed code, bounded
  wait, safe direction) or passes instantly (unlocked code) and the final-state
  assertion then discriminates the two.

## Verification

**Commands:**
- `pixi run --frozen -e local-recipes pytest .claude/skills/conda-forge-expert/tests/meta/test_spec_surface_check.py -q` -- expected: all pass (6 pre-existing + new; the `test_spec_surface_check_green` detector test remains red from the 63 pre-existing foreign findings — run the S-12.5 + S-13.1 selection, and document the green-test status separately)
- `python3 repro_race.py <fixed script> 20` (scratchpad driver) -- expected: `0/20 trials silently lost a write`
- `pixi run --frozen -e local-recipes spec-surface-check` (before/after diff against the captured pre-change set) -- expected: only the two documented mason `drift` findings for the edited test file are new
- `ruff check scripts/spec_surface_check.py .claude/skills/conda-forge-expert/tests/meta/test_spec_surface_check.py` (pixi env) -- expected: no NEW findings vs pre-change
