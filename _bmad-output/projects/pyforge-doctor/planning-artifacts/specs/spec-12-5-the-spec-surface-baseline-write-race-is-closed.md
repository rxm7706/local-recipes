---
title: 'Story 12.5: The spec surface baseline write race is closed'
type: 'bugfix'
created: '2026-08-21'
status: 'in-review'
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
  DW-13-5-2/DW-13-5-3 concurrency note. [Corrected in review pass 1: the call-time
  lock-path resolution exists so the sidecar tracks `BASELINE` wherever it points —
  the test harness repoints `REPO_ROOT` in a patched copy of the script; no test
  monkeypatches `BASELINE` directly, as this section originally claimed.]
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
- [x] `scripts/spec_surface_check.py` -- extract `_read_baseline` / `_baseline_lock` /
  `_write_baseline` / `_stamp_baseline`; wire `main()` through them -- closes the race
  while keeping the CLI contract byte-compatible on the happy path
- [x] `.gitignore` -- add the two sidecar entries -- keeps `git status` clean after any
  stamp
- [x] `test_spec_surface_check.py` -- add (final shape after review pass 1): (1)
  deterministic forced-interleaving test: load the patched module in-process, wrap
  `_read_baseline` with a 2-thread barrier (2s bounded wait, `BrokenBarrierError`
  tolerated — under the lock the second reader can never reach it), run two
  `_stamp_baseline` calls for different specs in threads with exceptions collected
  (never swallowed), assert BOTH entries updated AND a third never-stamped bystander
  spec's entry survives byte-identical with the key-set intact (fails
  deterministically on the unlocked code: both reads complete pre-write and the last
  write clobbers); (2) cross-process serialization tests for BOTH stamp paths (scoped
  AND full — the lock must bracket both): the test flocks the sidecar, launches the
  CLI, OBSERVES via the child's /proc fd table that it reached and blocked on the
  lock (never inferred from a fixed sleep), holds a short confirmation window
  (alive + baseline byte-stale), releases, asserts completion + correct stamp, with
  fd/child cleanup fully inside try/finally; (3) atomicity/no-residue assertions: no
  `.tmp` left behind, baseline parses, lockfile exists and is ignorable; `fcntl`
  imported function-locally so off-POSIX collection of the rest of the file survives
- [x] Verify the reproduction driver (scratchpad `repro_race.py`, 20 concurrent-stamp
  trials) reports 0 lost writes against the fixed script

**Acceptance Criteria:**
- Given two concurrent `--write-baseline` invocations against
  `scripts/.spec-surface-baseline.json`, when both run, then neither write is silently
  lost (CAP-5; reproduces and fixes the race cited as `DW-13-5-2`, recorded in the
  atlas ledger as `DW-13-5-3`).
- Given the unlocked implementation, when the committed forced-interleaving test (and
  the two lock-held blocking tests) run against it, then they fail deterministically —
  proven by negative control 2026-08-21 (flock line neutralized in place: 3 failed in
  0.44s); given the fixed script they pass. [Durable reproduction. The scratchpad
  stress driver additionally demonstrated the live defect pre-fix — 4/20 concurrent
  20-trial stamps lost a write, 0/20 post-fix, recorded 2026-08-21 — as dated
  historical evidence; the driver itself is session-scratch, not part of this
  contract's re-runnable surface.]
- Given the five pre-existing S-13.1/CLI-contract tests for this script, when they run
  post-fix, then all still pass unmodified. (`test_spec_surface_check_green`, the
  sixth test in the file, is red before AND after this story from 63 pre-existing
  foreign findings — see the detector AC below; this story does not change that.)
- Given the repo-wide spec-surface detector, when it runs post-fix (all story files
  staged), then the ONLY new finding versus the captured pre-change set is the single
  `drift` finding for the edited test file under
  `pyforge-mason/spec-conda-forge-expert-rebuild` (left for the landing session's
  reconciliation, per the Story 12.4 precedent). [Verified reality, amended from the
  draft's projection of "two": `pyforge-mason/spec-packaging-factory`'s memlog already
  names the test file path, so its finding is suppressed as presumed-reconciled — a
  strict subset of the projection, zero unexpected findings. The new spec file itself
  is covered by the `_bmad-output/**` allowlist entry.]

## Spec Change Log

### 2026-08-21 — Review pass 1 patch amendments + one intent-contract precedence note (no loopback)

**No bad_spec loopback ran** — no finding implicated the derived code, so the code was
patched in place and the spec sections outside the contract were amended to match
verified reality. Amendments: AC set corrected (unsatisfiable "all 6 pre-existing tests
pass" split into the honest 5-pass + green-test-red-before-and-after statement;
reproduction ACs re-anchored on the committed deterministic tests with the scratchpad
stress numbers demoted to dated historical evidence), test task rewritten to the final
reviewed shape (bystander spec, exception collection, /proc fd-observation for BOTH
stamp paths, function-local `fcntl`), Code Map's false "tests monkeypatch BASELINE"
claim corrected, Verification updated to real counts.

**Intent-contract precedence note (contract is read-only under this workflow):** the
I/O matrix row "Full stamp vs scoped stamp — whichever runs second operates on the
first's completed write" is imprecise for the full-stamp-second case: the full path
never reads the baseline — it deliberately replaces every entry with its own pre-lock
live snapshot (its documented accept-everything semantics, unchanged by this story).
The governing intent (CAP-5 / the epic AC: neither write silently LOST) has exactly one
reading and is satisfied — the stamps serialize, no entry is dropped by an unread
interleaving; full-stamp-wins-by-design is not a lost write. The module docstring
states this explicitly. Build and review against this reading, not the row's literal
"operates on" clause.

**KEEP (verified, must survive any future re-derivation):** the sidecar-flock +
atomic-replace mechanism exactly as shipped (lock the sidecar not the baseline;
whole-span bracket; no timeout/unlink); `_live_state()` and arg validation outside the
lock; byte-identical CLI output on every path; the negative-control protocol (flock
neutralized → 3 deterministic failures) as the proof the tests can fail.

## Review Triage Log

### 2026-08-21 — Review pass 1

- intent_gap: 0
- bad_spec: 0
- patch: 12: (high 0, medium 5, low 7)
- defer: 2: (high 0, medium 0, low 2)
- reject: 7: (high 0, medium 0, low 7)
- addressed_findings:
  - `[medium]` `[patch]` Blind Hunter: AC "all 6 pre-existing tests pass" self-contradicted
    by the Verification section (the green detector test is red from foreign findings).
    AC rewritten to the honest 5-pass + red-before-and-after statement.
  - `[medium]` `[patch]` Blind Hunter: the "lock brackets BOTH paths" constraint had zero
    test enforcement — a refactor locking only the scoped branch would pass green. Added
    `test_full_stamp_blocks_while_lock_held` (shared `_run_cli_against_held_lock` body).
  - `[medium]` `[patch]` Blind Hunter: load-bearing reproduction evidence lived only in a
    session scratchpad. ACs re-anchored on the committed deterministic tests + negative
    control; stress numbers kept as dated historical evidence.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (dedupe): "unrelated entries
    preserved" was claimed but never asserted (2-spec fixture, both stamped). Concurrency
    test now adds a never-stamped bystander spec and asserts its entry byte-identical +
    exact key-set.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (dedupe): blocking test inferred
    "blocked" from a fixed 2s sleep — false-pass on a loaded machine still inside
    `_live_state`, and the comment overclaimed proof. Replaced with
    `_wait_until_blocked_on_lock`: /proc fd-table observation + a 0.5s alive-and-stale
    confirmation window; an unlocked CLI cannot survive it.
  - `[low]` `[patch]` (x7): intent-contract matrix-row full-stamp-second overclaim →
    docstring sentence + Spec Change Log precedence note (contract read-only); ~7s fixed
    test latency → barrier 5s→2s + sleep replaced by observation (suite 8.4s→4.6s);
    thread exceptions swallowed → collected and asserted; false "tests monkeypatch
    BASELINE" comment → corrected in script + Code Map; `_load_checker_module` docstring
    fiction (sys.modules/id-uniqueness) → corrected; module-level `fcntl` import killed
    off-POSIX collection of the whole file → function-local; fd/Popen setup outside the
    blocking test's try → moved inside with None-guards. (+1 self-inflicted I001 from the
    import-comment placement, fixed in the same pass; ruff back to the 5 pre-existing.)
  - deferred (2, low): corrupt/hand-mangled committed baseline dies with a raw
    JSONDecodeError on scoped stamps (pre-existing expression, both hunters) →
    `DW-FU-12-5`; zero-discoverable-specs full stamp silently wipes the baseline to `{}`
    exit 0 (pre-existing semantics, Edge Case Hunter) → `DW-FU-12-5-2`. Both minted in
    doctor's Tier-3 `implementation-artifacts/deferred-work.md` (worktree-local — relay
    at landing).
  - rejected (7, low; severities re-assigned by consequence): (1) vanished-baseline
    FileNotFoundError guard — the proposed `except → {}` would reintroduce the
    drop-every-other-spec hazard; crashing is the safe behavior; (2) `_stamp_baseline([])`
    falls to the full branch — no real caller, byte-identical to the pre-fix `if args.spec`
    falsy semantics; (3) unknown-spec direct call raises inside the lock — contract keeps
    validation in `main()`; the CLI is the consumer surface; (4) no fsync before
    `os.replace` — crash-durability of a git-tracked artifact; recovery is `git checkout`,
    and the runtime never-torn claim (what the story promises) is delivered by `os.replace`;
    (5) disk-full partial `.tmp` residue — gitignored and overwritten by the next stamp;
    (6) multi-UID 0o644 lockfile PermissionError trap — the contract's own edge-matrix row
    prescribes raw propagation ("no new swallowing"), and this repo's worktrees are
    per-user; (7) environment-pinned 63→64 AC numbers rot — dated-observation convention,
    already bracket-noted in the AC (Story 12.4 precedent).

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
- `pixi run --frozen -e local-recipes pytest .claude/skills/conda-forge-expert/tests/meta/test_spec_surface_check.py -q` -- expected: `1 failed, 9 passed` — the 9 are the 5 pre-existing S-13.1/CLI tests + the 4 S-12.5 tests; the 1 failure is `test_spec_surface_check_green`, red before AND after this story from the pre-existing foreign findings
- Negative control (proves the S-12.5 tests can fail): neutralize the `fcntl.flock` line in a copy (or in place, restoring after) and re-run the 3 lock tests -- expected: 3 deterministic failures (observed 2026-08-21: `3 failed in 0.44s`)
- `pixi run --frozen -e local-recipes spec-surface-check` (before/after diff against the captured pre-change set, story files staged) -- expected: exactly one new finding, the `spec-conda-forge-expert-rebuild` drift for the edited test file (63 -> 64)
- `ruff check scripts/spec_surface_check.py .claude/skills/conda-forge-expert/tests/meta/test_spec_surface_check.py` (pixi env) -- expected: no NEW findings vs pre-change (5 pre-existing: 4x PLW1510 test-file, 1x EXE001 script)

## Auto Run Result

Status: done

**Summary.** `scripts/spec_surface_check.py --write-baseline`'s unlocked read-modify-write
of `scripts/.spec-surface-baseline.json` (CAP-5, cited as `DW-13-5-2`; the race itself is
the atlas ledger's `DW-13-5-3`) is closed: the whole read → merge → write span now runs
under an advisory `fcntl.flock` on a sidecar `.spec-surface-baseline.json.lock`
(herald/marshal fleet precedent mirrored inline, stdlib-only, no timeout/staleness/unlink
machinery), and the write is atomic (`.tmp` + `os.replace`) so the read-only Doctor
detector never sees a torn baseline. The race was REPRODUCED first against the pristine
script (4/20 concurrent 20-trial scoped stamps silently lost a write, both writers exit
0), and the fix re-verified (0/20). CLI contract byte-identical on every path (verified
by the implementation agent against `git show HEAD:` on all 5 paths). Full-stamp
accept-everything semantics deliberately unchanged, now stated in the docstring and
pinned by a Spec Change Log precedence note.

**Files changed:**
- `scripts/spec_surface_check.py` — `_read_baseline` / `_baseline_lock` /
  `_write_baseline` / `_stamp_baseline` extracted; `main()` wires through the locked
  critical section; docstring + comments record the defect ids, precedent, and
  full-stamp semantics.
- `.claude/skills/conda-forge-expert/tests/meta/test_spec_surface_check.py` — S-12.5
  section: deterministic forced-interleaving test (barrier-gated `_read_baseline`,
  bystander-spec preservation, collected thread exceptions), cross-process lock-held
  blocking tests for BOTH stamp paths (/proc fd-table observation, no timing
  inference), atomicity/no-residue test; `fcntl` function-local for off-POSIX
  collection.
- `.gitignore` — sidecar `.lock` + `.tmp` entries beside the `specs.lock` precedent.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-12-5-...md` —
  this spec (authored at the tracked sibling path per dispatch, deviation recorded).
- Doctor Tier-3 `implementation-artifacts/deferred-work.md` (worktree-local,
  ephemeral) — `DW-FU-12-5` (corrupt-baseline raw JSONDecodeError) and `DW-FU-12-5-2`
  (zero-spec full stamp wipes baseline) minted; relay to the shared checkout at landing.

**Review findings breakdown:** one pass, Blind Hunter + Edge Case Hunter in parallel with
no shared context: 0 intent_gap, 0 bad_spec (no loopback — no finding implicated the
derived mechanism), 12 patched (5 medium: unsatisfiable AC, full-path lock untested,
scratchpad-only evidence, bystander preservation unasserted, timing-inferred blocking;
7 low), 2 deferred (both pre-existing, ids above), 7 rejected (reasoning in the triage
log; one rejection defends crashing over a guard that would reintroduce the
drop-everything hazard).

**Verification performed (orchestrator-run, post-patch, real counts):**
- `pixi run --frozen -e local-recipes pytest .../test_spec_surface_check.py -q` —
  `1 failed, 9 passed in 4.58s`; the failure is `test_spec_surface_check_green` only,
  red before AND after this story (63 pre-existing foreign findings on this base).
- Stress reproduction: pre-fix `4/20 trials silently lost a write`; post-fix (run
  twice, incl. after all review patches) `0/20`.
- Negative control on the FINAL tests: flock line neutralized in place → the 3 lock
  tests fail deterministically (`3 failed in 0.44s`); restored, all pass.
- Detector diff vs the captured pre-change set (story files staged): exactly ONE new
  finding — mason `spec-conda-forge-expert-rebuild` drift for the edited test file
  (63 → 64); `spec-packaging-factory` suppressed (its memlog already names the file);
  the new spec file is `_bmad-output/**`-allowlisted.
- `ruff check` both files: 5 findings before and after (4x PLW1510, 1x EXE001 — the
  identical pre-existing set).

**Follow-up review recommendation:** true — the review pass drove a substantive rework
of the concurrency test harness (new /proc fd-observation helper, shared blocking-test
body, bystander fixture): 12 patched findings with 5 mediums is significant by volume
and the reworked deterministic-concurrency logic has not itself been independently
reviewed (its negative control has been re-run, but fresh eyes are warranted).

**Residual risks / landing notes:**
- The single mason `drift` FAIL for the edited test file is the sanctioned in-flight
  signal for this change — reconcile at landing (mason memlog entry naming the file,
  stage, then scoped `--write-baseline --spec pyforge-mason/spec-conda-forge-expert-rebuild`);
  do NOT stamp it from this branch (it would accept mason's unrelated pending drift).
- Relay the two Tier-3 DW entries to the shared checkout at landing (worktree Tier-3 is
  ephemeral).
- `spec-fleet-hygiene-verification-exemplar-program`'s `hygiene-gap-catalog.md` CAP-5
  line reads "specced — backlog, not yet landed"; update to shipped at landing (CAP-1
  keeps the catalog current).
- The baseline sidecar lockfile appears on disk after any stamp; it is gitignored and
  deliberately never unlinked.
