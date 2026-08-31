---
title: 'The state layer survives a second writer'
type: 'bugfix'
created: '2026-08-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
baseline_revision: '98fbdf37f8dbf1abb327ed290fb423b34e65cf00'
final_revision: '3f8be97a6b6c2c83e717cd5972957a4ab01c06de'
---

<intent-contract>

## Intent

**Problem:** `state.py`, `progress.py`, `claims.py`, and `notices.py` each do an unlocked
whole-document read-modify-write (load, mutate one entry, atomically replace via temp-file +
`os.replace`); two concurrent writers can silently drop one update. Tracked as `DW-1-4-2`,
confirmed concretely reachable (two concurrent `herald deck pull` invocations for the same
slug), and about to become routine the moment Epic 13's webhook lands — this story is a hard
prerequisite for every later story in the epic.

**Approach:** Add one small stdlib-only, cross-platform advisory file lock (`fcntl` on POSIX,
`msvcrt` on Windows — this package targets win-64, so POSIX-only `fcntl` alone is not enough)
and hold it across each module's full read-modify-write span. No schema change, no new
dependency, no public-signature change. Record the SQLite-vs-per-file-lock decision in
`DW-1-4-2` as resolved: per-document lock now; SQLite/Postgres stays Story 13.3's separate,
larger-scoped migration.

## Boundaries & Constraints

**Always:**
- Every mutating entry point below acquires an exclusive OS-level advisory lock spanning its
  entire read-modify-write critical section (load through atomic replace) on a sidecar
  `<document>.lock` file, so a second concurrent writer blocks and serializes instead of racing.
- The lock is stdlib-only (`fcntl`/`msvcrt`) and shared by one new module so the fix applies
  uniformly, not spot-fixed per module.
- Lock-acquisition/release failures (e.g. an unwritable lock-file directory) raise
  `errors.HeraldError`, matching every other structural-failure path in these modules (AD-6).
- A concurrency test per module proves the fix: forced deterministic interleaving (a thread
  barrier or monkeypatched delay between load and replace — not a timing-dependent sleep race),
  confirmed to fail against the pre-fix code and pass after.
- `DW-1-4-2` in the deferred-work ledger is closed with the chosen approach recorded.

**Block If:** None — the locking-approach decision is resolved within this spec (Design Notes),
per the epic's own framing of this as the story that resolves it, not a human decision point.

**Never:**
- Migrate storage to SQLite/Postgres or change the on-disk JSON/markdown schema — that is Story
  13.3's explicit, separate scope; doing it here would duplicate that work.
- Add a third-party locking dependency (e.g. `filelock`) — stdlib `fcntl`/`msvcrt` already cover
  every platform this package targets.
- Implement lock-staleness detection or timeouts — OS-level advisory locks release automatically
  when the holding process exits or crashes, so no manual cleanup is needed.
- Change any public function signature or the shape of a stored document.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Two concurrent writers, same document | Two callers invoke the same module's mutating function at ~the same time (e.g. two `state.write()` calls for different slugs in one file) | Second writer blocks until the first releases the lock; both writers' updates are present in the final document | No error expected |
| Single writer, no contention | Normal single-process call, as today | Behavior unchanged from before this story (same schema, same HeraldError contract, no observable perf regression) | No error expected |
| Lock file's parent directory unwritable | Sidecar `.lock` path's directory can't be created/opened | Lock acquisition fails structurally | `errors.HeraldError` naming the path, never a raw `OSError` |
| Process crashes while holding the lock | A writer dies mid-critical-section | Next writer still acquires the lock (OS releases it on process exit) | No error expected; no stale-lock cleanup needed |

</intent-contract>

## Code Map

- `src/pyforge/herald/locking.py` -- NEW: shared cross-platform advisory-lock context manager
- `src/pyforge/herald/state.py` -- `write()` (`:203`) does the read-modify-write to lock
- `src/pyforge/herald/progress.py` -- `upsert()` (`:237`) does the read-modify-write to lock
- `src/pyforge/herald/claims.py` -- `create()` (`:351`) does a lock-the-whole-function
  read-modify-write; `publish()` (`:392`), `revalidate()` (`:493`), `revalidate_all()` (`:529`)
  each call `evidence_mod.validate_link` (real HTTP request) per evidence entry -- validation
  must run before lock acquisition, only the load/apply/write span is locked
- `src/pyforge/herald/notices.py` -- `author_notice()` (`:372`), `publish_notice()` (`:475`),
  `close_notice()` (`:512`), `archive_rename()` (`:638`) each write both the JSON index and a
  markdown file; locking the whole function body serializes both as one critical section
- `_bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md` -- close
  `DW-1-4-2` (currently `status: open`, line 270)

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/herald/locking.py` -- add a `locked(lock_path: Path)` context manager using
  `fcntl.flock` (POSIX) / `msvcrt.locking` (Windows), wrapping `OSError` as `errors.HeraldError`
  -- one shared primitive so the fix is uniform across modules
- [x] `src/pyforge/herald/state.py` -- wrap `write()`'s load+mutate+replace body in
  `locking.locked(state_path.with_name(state_path.name + ".lock"))`
- [x] `src/pyforge/herald/progress.py` -- wrap `upsert()`'s `read_all`+mutate+`write_all` body in
  the same lock convention keyed on `progress_path`
- [x] `src/pyforge/herald/claims.py` -- wrap `create()`'s whole body in the lock keyed on
  `claims_path` (no network I/O, lock the whole function as originally). For `publish()`,
  `revalidate()`, and `revalidate_all()`: run evidence-link validation (`evidence_mod.validate_link`)
  BEFORE acquiring the lock; acquire the lock only around loading the fresh claims state, applying
  the already-computed validation results, and writing -- the lock must never span network I/O.
  If a validated evidence entry no longer matches what the fresh locked read shows (a concurrent
  writer changed it in between), discard that entry's stale validation result rather than
  clobbering the newer data; every other entry's write still lands normally.
  **Carry the pre-lock validation results POSITIONALLY (index-aligned with the evidence tuple they
  were computed from) in ALL THREE of `publish()`, `revalidate()`, and `revalidate_all()` -- never
  in a dict keyed by `Evidence` value, not even within a single claim.** `Evidence` is a frozen,
  value-equal dataclass and `create()` performs no de-duplication (it validates only `type`), so
  ONE claim can legitimately carry two field-identical entries (same url/type/label); an
  `Evidence`-keyed dict collapses them onto one key and stores the last result for both, losing
  the other entry's real outcome. Keep, per claim, the pre-validation evidence tuple `original`
  and an index-aligned results tuple, then inside the lock apply by index: for each index `i` of
  the freshly-read `claim.evidence`, apply `results[i]` only when `i < len(original)` **and**
  `fresh.evidence[i] == original[i]`; otherwise leave that fresh entry untouched (it was changed,
  reordered, or added concurrently). This preserves the discard-stale-result rule above while
  handling duplicates and a concurrently-changed evidence length correctly. **`revalidate_all()`
  additionally:** key that per-claim structure by claim id (e.g. `dict[str, tuple[original,
  results]]`) so a lookup only ever searches within the SAME claim's own results -- never one
  structure shared across every claim's evidence, which would let one claim's validation outcome
  overwrite another's
- [x] `src/pyforge/herald/claims.py` -- `publish()` must never persist `status="published"`
  alongside an evidence entry this call did not itself validate. Inside the lock, after computing
  the final evidence tuple, re-verify that every entry it is about to write carries this call's
  own validation; if a concurrent writer changed an entry during the unlocked validation window
  (so the discard-stale rule passed the fresh, unvalidated entry through), abort with
  `errors.ClaimStateError` naming the claim and telling the operator to re-run publish, rather
  than writing a published claim whose evidence was never validated. The discard-stale rule stays
  as-is for `revalidate()`/`revalidate_all()`, whose whole purpose is to record breakage rather
  than gate on it
- [x] `src/pyforge/herald/notices.py` -- wrap `author_notice()`, `publish_notice()`,
  `close_notice()`, `archive_rename()` bodies in the lock keyed on the resolved `index_path`
- [x] `tests/test_locking.py` -- NEW: two threads/processes serialize rather than race; lock
  releases cleanly on process exit; unwritable lock path raises `HeraldError`
- [x] `tests/test_state.py`, `tests/test_progress.py`, `tests/test_claims.py`,
  `tests/test_notices.py` -- add one forced-interleaving concurrency test per module proving no
  update is lost (verify it fails on pre-fix code, passes after); the `claims.py` test must prove
  no update is lost AND that no network call happens while the lock is held. Add a regression test
  proving that when `revalidate_all` validates two different claims sharing a field-identical
  evidence entry, each claim keeps the outcome of ITS OWN validation call, never a collided one.
  Add an INTRA-claim regression test for all three of `publish`/`revalidate`/`revalidate_all`: one
  claim carrying two field-identical evidence entries whose two validation calls return DIFFERENT
  outcomes (e.g. first `is_valid=True`, second `is_valid=False` -- a transient 429) keeps both
  distinct outcomes index-aligned, never one outcome collapsed onto both entries. Add a test that
  `publish` refuses (raising `ClaimStateError`) rather than publishing when a concurrent writer
  changed an evidence entry during the unlocked validation window
- [x] `_bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md` -- set
  `DW-1-4-2` `status: done 2026-08-10` with a `verified:` line recording the chosen approach
  (per-document advisory lock; SQLite/Postgres deferred to Story 13.3), matching this ledger's
  existing resolution convention (see `DW-1-1-1`)

**Acceptance Criteria:**
- Given two concurrent writers targeting the same document in any of the four modules, when both
  call their mutating function at ~the same time, then no update is silently lost.
- Given the SQLite-vs-per-file-lock question this story owns, when the story completes, then the
  chosen approach is recorded in writing in `DW-1-4-2`, not left open.
- Given a single writer with no contention, when it calls any of the four modules' mutating
  functions, then behavior, schema, and the `HeraldError` contract are unchanged from before this
  story.
- Given the new concurrency tests, when run against the pre-fix code, then they fail (proving the
  race is real); when run against the fixed code, then they pass.
- Given `publish()`, `revalidate()`, or `revalidate_all()` validating evidence links, when the
  lock is held, then no network call (`evidence_mod.validate_link`) executes during that span --
  validation happens before lock acquisition, never inside it.
- Given `revalidate_all` validating two different claims that share a field-identical evidence
  entry (e.g. same url/type/label), when their two independent validation calls return different
  outcomes, then each claim's evidence is stamped with the result of ITS OWN validation call --
  never a sibling claim's.
- Given a SINGLE claim carrying two field-identical evidence entries (same url/type/label --
  `create()` performs no de-duplication), when `publish`, `revalidate`, or `revalidate_all`
  validates it and the two calls return different outcomes, then each entry is stamped with the
  result of the validation call made for THAT entry's position -- never one outcome collapsed onto
  both entries.
- Given `publish` whose unlocked evidence validation is followed by a concurrent writer changing
  one of that claim's evidence entries, when `publish` reaches its locked write, then it raises
  `errors.ClaimStateError` and writes nothing -- a claim is never persisted as `published`
  carrying an evidence entry that `publish` call did not itself validate.

## Spec Change Log

### 2026-08-10 — bad_spec repair (review pass 1)
- Triggering finding: Blind Hunter and Edge Case Hunter independently found that `claims.py`'s
  `publish()`, `revalidate()`, and `revalidate_all()` held the new advisory lock across
  `evidence_mod.validate_link` -- a real HTTP request per evidence entry (`revalidate_all`
  iterating every stored claim's every entry) -- because the original Tasks instruction to "wrap
  ... bodies in the lock" did not carve non-storage network I/O out of the critical section.
- Amended: `## Code Map` and `## Tasks & Acceptance`'s `claims.py` entries, plus a new AC and
  this Design Notes section, to require evidence validation run before lock acquisition, with
  only the load/apply/write span locked.
- Known-bad state avoided: a `claims revalidate-all` (or `publish`/`revalidate`) call blocking
  every other concurrent claims writer -- including this epic's future webhook -- for the
  duration of one or more live HTTP requests. Not a lost-update bug, but a serious new liveness
  regression this story did not have before, and directly undermines the practical concurrency
  the epic needs from this prerequisite.
- KEEP: `locking.py`'s design (the `locked(lock_path)` contextmanager shape, `fcntl`/`msvcrt`
  platform branch, `errors.HeraldError` wrapping on acquisition failure, house-style docstrings)
  is sound -- reproduce essentially as-is. `state.py` and `progress.py`'s wiring (whole-function
  locking, no network calls involved) is correct as-is. `notices.py`'s wiring (locking the whole
  function body so the index write and the markdown write land in one critical section) is
  correct as-is -- no network I/O there either. `claims.create()`'s wiring (no network call) is
  correct as-is. The four modules' concurrency-test technique (`threading.Barrier` plus a
  monkeypatched delay on the read step, forcing deterministic interleaving rather than a
  timing-dependent sleep race) is the right approach and should be reused for `claims.py`'s test
  too. The `DW-1-4-2` ledger-closure convention (matching `DW-1-1-1`'s `verified:` line format)
  is correct -- reproduce it, updated to reflect the `claims.py` restructuring.

### 2026-08-10 — bad_spec repair (review pass 2)
- Triggering finding: Blind Hunter and Edge Case Hunter independently found (and Blind Hunter
  reproduced directly) that `revalidate_all()`'s pre-lock validation map was a single flat
  `dict[Evidence, Evidence]` built across every stored claim's evidence in one comprehension.
  `Evidence` is a frozen, value-equal dataclass, so two different claims citing a field-identical
  entry (same url/type/label) collide as the same dict key -- one claim's validation outcome
  silently overwrites another's stored evidence status on collision. Root cause: the pass-1
  Design Notes sketch illustrated a single-claim, URL-keyed dict (`{e.url: validate(e.url) for e
  in claim.evidence}`) and never addressed `revalidate_all`'s cross-claim batching case; the
  implementer's reasonable extrapolation to one shared dict across all claims introduced the
  collision.
- Amended: `## Tasks & Acceptance`'s `claims.py` entry and its test-coverage entry, plus a new AC,
  to require `revalidate_all()`'s validation map be scoped per claim (never one flat dict across
  every claim's evidence).
- Known-bad state avoided: silent cross-claim data corruption -- a claim's stored evidence
  `validated`/`validated_at` fields overwritten with an unrelated claim's HTTP check outcome, with
  no error and no indication anything was wrong. Exactly the class of "silently wrong, not
  visibly broken" bug this epic (LB-1..LB-3, "an unrecorded ship is indistinguishable from no
  ship") exists to eliminate -- ironically introduced by this story's own fix.
- KEEP: everything pass 1's KEEP list already named (`locking.py`, `state.py`/`progress.py`
  wiring, `notices.py` wiring, `claims.create()`, the concurrency-test technique, the ledger
  convention) remains correct and should be reproduced as before. Additionally KEEP: `publish()`
  and `revalidate()`'s validate-before-lock restructuring and their `Evidence`-keyed maps are
  correct as shipped -- both operate on exactly one claim at a time, so no cross-claim collision
  is possible there; only `revalidate_all()`'s cross-claim batching needs the per-claim-scoped
  fix. KEEP the `_lock_is_currently_free` non-blocking self-check test technique and the
  `publish`/`revalidate_all` "validated before lock" tests -- reproduce them as-is.

### 2026-08-10 — bad_spec repair (review pass 4)
- Triggering finding: Blind Hunter found, and a direct repro confirmed, that the
  `Evidence`-keyed validation map collapses **duplicate field-identical evidence entries within a
  SINGLE claim** — not just across claims. `Evidence` is frozen and value-equal and `create()`
  de-duplicates nothing, so a claim carrying the same entry twice gets two independent validation
  calls but retains only the last result, applied to both entries. Reproduced: a claim with a
  duplicated link whose two checks return `True` then `False` (transient 429) stores
  `[False, False]`; the pre-change code, which built the tuple positionally, stored
  `[True, False]`. Both `revalidate` and `revalidate_all` are affected. Root cause: pass 2's own
  amendment diagnosed the collision as a *cross-claim* problem and explicitly blessed the wrong
  design in Design Notes — "`publish`/`revalidate` operate on one claim at a time, so this risk
  does not apply to them — their existing `Evidence`-keyed, single-claim maps are correct as-is."
  That sentence is false: single-claim scope does not make an `Evidence`-keyed map collision-free.
  The implementation faithfully followed it and even reproduced it as a code comment asserting the
  collision "cannot happen".
  Second finding folded into this repair: `publish`'s `validated_map.get(e, e)` pass-through lets
  a claim be persisted as `published` carrying an evidence entry that call never validated (a
  concurrent `revalidate` writing `validated=False` during the unlocked HTTP window), silently
  bypassing publish's own broken-link gate.
- Amended: `## Tasks & Acceptance`'s `claims.py` entry and its test-coverage entry, two new ACs,
  and the `## Design Notes` validation-map section — replacing the value-keyed-dict design with an
  index-aligned positional carry (`original` tuple + index-aligned `results`, applied under an
  `e == original[i]` check) required in all three of `publish`/`revalidate`/`revalidate_all`, plus
  a new in-lock gate for `publish`. The false "single-claim maps are correct as-is" sentence is
  deleted and replaced with an explicit statement that it is false, so it cannot be re-derived.
- Known-bad state avoided: silent loss of a real validation outcome inside one claim — an evidence
  link that genuinely failed recorded as passing (or vice versa) with no error, plus a claim
  publishable as `published` over evidence never checked. This is the third recurrence of one root
  cause (`Evidence` used as a dict key) and the same "silently wrong, not visibly broken" class the
  epic exists to eliminate (LB-1..LB-3) — again introduced by this story's own fix.
- KEEP: everything passes 1 and 2's KEEP lists already named remains correct and should be
  reproduced. Specifically: `locking.py`'s whole design — the `locked(lock_path)` contextmanager
  shape, the raw `os.open` descriptor with `0o600`, the `fcntl`/`msvcrt` platform branch, the
  `errors.HeraldError` wrapping, the best-effort `_release` under `contextlib.suppress(OSError)`,
  and the docstring notes on per-document granularity and non-reentrancy. `state.py`,
  `progress.py`, and `notices.py`'s wiring (whole-function locking; `notices.py` deliberately
  covering both the index write and the markdown write in one critical section) is correct as-is.
  `claims.create()`'s wiring, including pass 3's move of the cheap local argument checks to before
  lock acquisition, is correct as-is. The validate-before-lock restructuring of
  `publish`/`revalidate`/`revalidate_all` is correct and central — keep it; only the *shape of the
  carried results* changes from a value-keyed dict to an index-aligned tuple. Keep pass 3's
  in-lock `status != "draft"` re-check in `publish` and its concurrent-same-claim-publish
  regression test; keep `revalidate_all`'s "claim created concurrently → leave untouched including
  `updated_at`" rule and its per-claim-id scoping (now carrying an `(original, results)` pair
  instead of a sub-dict). Keep the four modules' concurrency-test technique (`threading.Barrier`
  plus a monkeypatched delay on the read step), the `_lock_is_currently_free` non-blocking
  self-check with its deliberate-duplication docstring, the "validated before lock" tests, the
  cross-claim collision regression test, and the `DW-1-4-2` ledger-closure convention (matching
  `DW-1-1-1`'s `verified:` line format), updated for the positional restructuring. The reverted
  implementation is preserved at tag `herald-13-1-pass4-preserved` (commit `70220e6b4b`) and as a
  patch under the run scratchpad — re-derive from it rather than from scratch.

## Review Triage Log

### 2026-08-10 — Review pass
- intent_gap: 0
- bad_spec: 1: (high 0, medium 1, low 0)
- patch: 9: (high 0, medium 3, low 6)
- defer: 1: (high 0, medium 1, low 0)
- reject: 4: (high 0, medium 0, low 4)
- addressed_findings:
  - `[medium]` `[bad_spec]` The lock in `claims.py`'s `publish()`/`revalidate()`/`revalidate_all()`
    spanned real network I/O (evidence-link HTTP validation) because the original Tasks
    instruction under-specified the critical section's boundary -- amended Code Map, Tasks, and
    Design Notes to require validation before lock acquisition; code reverted for re-derivation.

### 2026-08-10 — Review pass 2
- intent_gap: 0
- bad_spec: 1: (high 1, medium 0, low 0)
- patch: 9: (high 0, medium 4, low 5)
- defer: 0
- reject: 2: (high 0, medium 0, low 2)
- addressed_findings:
  - `[high]` `[bad_spec]` `revalidate_all()`'s pre-lock validation map was keyed by `Evidence`
    value across ALL claims, so two different claims sharing a field-identical evidence entry
    collide -- one claim's validation outcome silently overwrites another's. Amended Tasks and
    added an AC requiring the map be scoped per claim; code reverted for re-derivation.

### 2026-08-10 — Review pass 3
- intent_gap: 0
- bad_spec: 0
- patch: 9: (high 1, medium 1, low 7)
- defer: 1: (high 0, medium 0, low 1)
- reject: 2: (high 0, medium 0, low 2)
- addressed_findings:
  - `[high]` `[patch]` `claims.publish()`'s `status != "draft"` guard was checked only against the
    pre-lock read, never re-verified against the fresh in-lock read -- two concurrent `publish()`
    calls on the SAME claim both pass the guard and the second silently overwrites the first
    (`published_at`/`thesis`/evidence), never raising the documented `ClaimStateError`. Added the
    same status re-check inside the lock, plus a regression test for concurrent same-claim publish.
  - `[low]` `[patch]` `revalidate_all()` stamped `updated_at` on every claim in the fresh read,
    including one created concurrently (absent from the pre-lock `validated_by_claim` scan) whose
    evidence was never actually checked. Now left untouched (both evidence and `updated_at`)
    when absent from the validation map.
  - `[low]` `[patch]` Cheap, purely-local validation (`claims.create`'s `project_name`/evidence-type
    checks, `notices.py`'s `_validate_type`/`_validate_component`/self-redirect checks) ran inside
    the lock across all four touched modules -- moved before lock acquisition so an invalid call
    fails fast without contending on the lock first.
  - `[low]` `[patch]` `locking.py` had no docstring note on two adjacent hazards raised across all
    three review passes: per-document (not per-record) lock granularity, and same-thread
    re-entrant `locked()` calls self-deadlocking. Added one sentence each.
  - `[low]` `[patch]` `test_claims.py`'s `_lock_is_currently_free` hand-reimplemented the
    `fcntl`/`msvcrt` platform dispatch instead of noting why it can't reuse `locking._acquire`
    (that call blocks, defeating the check's purpose) -- added a docstring line making the
    deliberate-duplication reasoning explicit so future drift is a documented trade-off, not silent.
  - `[low]` `[patch]` `locking.locked()` opened the sidecar file with `os.open(..., 0o666)`,
    broader than `tempfile.mkstemp`'s restrictive default used elsewhere in these modules --
    narrowed to `0o600` for consistency (lock files hold no sensitive content, but the
    inconsistency was unexplained).
  - `[medium]` `[patch]` `msvcrt.locking(LK_LOCK)` internally retries only ~10s before raising
    `OSError`, unlike POSIX `fcntl.flock(LOCK_EX)`'s indefinite block -- raised independently in
    all three review passes. Wrapped the Windows acquire in a retry loop so sustained contention
    blocks (matching POSIX semantics and the module's own "no timeout" contract) instead of
    surfacing a spurious `HeraldError`.
  - `[low]` `[defer]` No CI workflow runs the `pyforge-herald` pytest suite on Windows (only
    `test-windows.yml`'s conda-recipe build job targets `windows-2022`), so `locking.py`'s
    `msvcrt` branch -- the one this module was explicitly widened for -- has zero automated
    coverage. Out of this story's file surface (CI workflow changes, not `state.py`/`progress.py`/
    `claims.py`/`notices.py`); deferred to `{implementation_artifacts}/deferred-work.md`.

### 2026-08-10 — Review pass 4
- intent_gap: 0
- bad_spec: 2: (high 1, medium 1, low 0)
- patch: 8: (high 0, medium 2, low 6)
- defer: 1: (high 0, medium 1, low 0)
- reject: 6: (high 0, medium 0, low 6)
- addressed_findings:
  - `[high]` `[bad_spec]` The `Evidence`-keyed pre-lock validation map collapses duplicate
    field-identical evidence entries WITHIN a single claim (`Evidence` is frozen and value-equal;
    `create()` de-duplicates nothing), so two independent validation calls yield one retained
    result applied to both entries -- reproduced as `[False, False]` where the pre-change
    positional code stored `[True, False]`. Affects `revalidate` and `revalidate_all`. Caused by
    pass 2's Design Notes explicitly blessing single-claim `Evidence`-keyed maps as safe. Amended
    Tasks, Design Notes, and added an AC requiring index-aligned positional carry in all three
    functions; code reverted for re-derivation.
  - `[medium]` `[bad_spec]` `publish`'s `validated_map.get(e, e)` pass-through can persist
    `status="published"` alongside an evidence entry that call never validated (a concurrent
    `revalidate` writing `validated=False` during the unlocked HTTP window), bypassing publish's
    documented broken-link gate. Amended Tasks/Design Notes and added an AC requiring an in-lock
    re-verification that raises `ClaimStateError` instead of publishing unvalidated evidence.

### 2026-08-10 — Review pass 5
- intent_gap: 0
- bad_spec: 0
- patch: 11: (high 0, medium 3, low 8)
- defer: 3: (high 1, medium 0, low 2)
- reject: 3: (high 0, medium 0, low 3)
- addressed_findings:
  - `[medium]` `[patch]` All ten lock-path derivations used `path.with_name(path.name + ".lock")`,
    which raises a raw `ValueError` on an empty-name path (`Path("/")`, `Path(".")`) -- an AD-6
    breach and a direct violation of this story's own "the `HeraldError` contract is unchanged" AC
    (verified: pre-story `state.write(Path("/"), ...)` raised `HeraldError`, post-story it raised
    `ValueError`). Added `locking.lock_path_for()` as the single guarded derivation point and
    routed all ten sites through it.
  - `[medium]` `[patch]` `locking._acquire`'s Windows retry loop caught EVERY `OSError` and slept
    forever, so a permanent failure (EACCES/EBADF/EINVAL, or a volume without byte-range locking)
    spun at 10Hz with no output instead of surfacing -- and made `locked()`'s documented
    `OSError`->`HeraldError` wrap unreachable on win32. Now retries only `errno.EDEADLOCK` (the
    LK_LOCK contention timeout) and re-raises everything else.
  - `[medium]` `[patch]` `DW-1-4-2`'s closure note overclaimed: it read as RESOLVED while the
    entry's own `update_2026-08-07` paragraph -- the concurrent `herald deck pull` scenario -- is
    still broken, because `deck_pipeline` builds its etag map from a pre-network `state.read` and
    the lock only spans `state.write`'s own body. Narrowed the `verified:` note to state exactly
    what is and is not closed, and recorded the caller-level spans as a separate ledger entry.
  - `[low]` `[patch]` `revalidate`/`revalidate_all` stamped `updated_at` even when the
    discard-stale rule dropped EVERY one of this run's results (a concurrent writer replaced all
    the evidence), asserting a validation that never happened -- the same defect pass 3 fixed one
    branch over for a concurrently-created claim. Both now leave the claim untouched, with
    regression tests.
  - `[low]` `[patch]` `revalidate_all` keys results by claim id, which silently collapses two
    claims sharing an id (injected `id_factory`, hand-edited/merged `claims.json`) -- one claim's
    HTTP outcome overwriting the other's. Added a structural `HeraldError` guard plus a test.
  - `[low]` `[patch]` `locking.py`'s opening sentence claimed the primitive is "shared by every
    whole-document read-modify-write in this package" -- false: `registry.register` and
    `deck_pipeline._atomic_write_text` are uncovered. Scoped the claim to the four modules and
    named the exclusions.
  - `[low]` `[patch]` `notices.py`'s docstring claimed the markdown race closed unconditionally.
    Two limits added: the lock is keyed on `index_path` while the markdown lands under
    `repo_root` (callers passing different explicit `index_path` values serialize on nothing), and
    `_write_markdown` is a non-atomic `write_text`, so concurrent READERS can still see a
    truncated file.
  - `[low]` `[patch]` Nothing tested that `locked()` releases when the guarded block raises -- the
    module's most load-bearing line, and this story adds several raise-inside-the-lock paths.
    Added `test_locked_releases_when_the_guarded_block_raises`.
  - `[low]` `[patch]` Every concurrency test raced threads in one interpreter, so the suite would
    stay green if `_acquire` were ever replaced by a `threading.Lock` -- silently reopening the
    multi-process race the story exists to close. Added
    `test_locked_excludes_a_second_os_process`.
  - `[low]` `[patch]` `test_locked_releases_when_the_holding_process_is_killed` never synchronized
    on the waiter reaching the blocking acquire, so the child was normally dead first and the test
    degraded into "acquire an already-free lock". Added the waiter handshake plus a positive
    assertion that the lock is genuinely held while the holder lives.
  - `[low]` `[patch]` `proc.stdout.readline()` and two `t.join()` calls had no timeout, so a lock
    regression or a child that never printed would hang pytest until the CI job timeout. Added
    `_readline_or_fail` (bounded read) and bounded joins with explicit `is_alive` assertions.
- Deferred (3, appended as NEW entries to `deferred-work.md`): `deck_pipeline`'s caller-level
  read-network-write spans (the story's motivating `herald deck pull` scenario, reproduced);
  `notices._write_markdown`'s non-atomic write; `registry.register`'s unlocked whole-document RMW.
- Rejected (3): a claimed isort/`I001` regression in `test_state.py`/`test_progress.py` (`ruff
  check` passes on both -- not reproducible); the Windows-CI coverage gap (already recorded in the
  ledger by pass 3, re-raised verbatim); `publish`'s two `ClaimStateError` cases being
  indistinguishable (a real API nicety, but adding an exception subclass exceeds this story's
  no-public-surface-change boundary).

### 2026-08-10 — Review pass 6
- intent_gap: 0
- bad_spec: 0
- patch: 10: (high 0, medium 2, low 8)
- defer: 1: (high 0, medium 0, low 1)
- reject: 6: (high 0, medium 1, low 5)
- addressed_findings:
  - `[medium]` `[patch]` `publish()` resolved its final thesis from the PRE-LOCK read
    (`claim.thesis`), so publishing with no `--thesis` while a concurrent writer set a new one
    republished the stale text AND filed the newer text into `edit_history` as the superseded
    version -- inverting the two. Reproduced: on-disk `thesis-OLD`, concurrent write of
    `thesis-NEW`, published result `thesis-OLD` / `edit_history ['thesis-NEW']`. Exactly the
    lost-update class `DW-1-4-2` exists to close, on the field an operator is most likely to be
    editing, and untouched by the evidence-focused fix. `final_thesis` is now resolved from the
    fresh in-lock read, with the pre-lock check demoted to an explicit fail-fast; a concurrent
    writer clearing the thesis mid-window now refuses with the same message instead of persisting
    an empty one. Three regression tests.
  - `[medium]` `[patch]` `progress.write_all` is a PUBLIC whole-document writer and took no lock,
    so a second process calling it clobbered a concurrent `upsert` exactly as before this story --
    while the module docstring advertised that race as closed. An advisory lock only serializes the
    writers that all take it. Split into a locked public `write_all` plus a private
    `_write_all_unlocked` that `upsert` calls from inside its own critical section (`locked` is
    deliberately non-reentrant, so calling the public one there would self-deadlock); docstring
    corrected. Regression test proven to fail unlocked.
  - `[low]` `[patch]` `revalidate`/`revalidate_all`'s every-result-discarded guard was written as
    `if fresh_claim.evidence and not any(carried)`, keyed on the FRESH read rather than on what the
    run actually validated -- so a concurrent writer emptying the evidence tuple skipped the guard
    and stamped `updated_at` for a validation whose every result was thrown away, the precise case
    the guard exists to catch. Both now key on `original_evidence`. A claim that simply has no
    evidence still gets its ordinary stamp (pre-story behavior, covered by its own test so the fix
    cannot overshoot into a behavior change).
  - `[low]` `[patch]` `revalidate_all`'s duplicate-claim-id guard ran only against the pre-lock
    read, while the loop consuming the id-keyed results iterates the fresh in-lock read -- so a
    duplicate written during the unlocked HTTP window sailed past it and one claim's single
    validation outcome (plus this run's `updated_at`) landed on BOTH same-id claims. Reproduced.
    Extracted as `_require_unique_ids` and now checked against the fresh read too.
  - `[low]` `[patch]` `test_locked_excludes_a_second_os_process` -- the one test nominated as the
    guard against `_acquire` being "simplified" into a `threading.Lock` -- was a false green: its
    worker called `locked(...).__enter__()` bare, so an exception left `acquired` unset and the
    assertion passed. Verified: with `locked` monkeypatched to raise unconditionally, the test
    passed. It also stranded an entered contextmanager (lock + fd) for the session. Rewritten with
    a full `with` block, recorded exceptions, an explicit `assert not failures`, and a bounded join.
  - `[low]` `[patch]` `locking.locked`'s `finally: os.close(fd)` was unsuppressed, so a failing
    close replaced whatever exception the guarded block raised and leaked a raw `OSError` out of a
    module documenting `HeraldError` as its only failure mode (AD-6) -- while the docstring claimed
    teardown never masks the block's exception. Suppressed like `_release`, docstring corrected,
    regression test added.
  - `[low]` `[patch]` `publish_notice`/`close_notice`/`archive_rename` acquired the lock before
    discovering there is no notice index at all, and lock acquisition creates the parent directory
    and the sidecar `.lock` file -- so an operator running one from the wrong directory littered it
    with an empty `.herald/` tree on a pure error path that had no filesystem side effect before
    this story. Added `_require_existing_index`, a pre-lock fail-fast reusing each caller's own
    refusal message (the authoritative in-lock checks stay). `author_notice` deliberately excluded.
  - `[low]` `[patch]` `state.write`'s docstring replaced its caveat pointing at the caller-level
    race with an unqualified "can never silently drop one update", leaving a maintainer reading the
    code no pointer to the surviving `deck_pipeline` read-network-write span -- whose only record
    was a paragraph inside a ledger entry now marked `done`. Caveat restored and made specific.
  - `[low]` `[patch]` `DW-1-4-2`'s closure note said the caller-level spans "are tracked as a new,
    separate ledger entry"; they were recorded in `implementation-artifacts/deferred-work.md`, not
    as a `## DW-` entry in that ledger, so a reader looking there finds nothing. Reworded to name
    the actual file.
  - `[low]` `[patch]` This change introduced `ruff format` violations in `notices.py` and
    `test_notices.py`, both clean at the baseline revision (verified by formatting each baseline
    blob through `--stdin-filename`). Reformatted.
- Deferred (1, appended as a NEW entry to `deferred-work.md`): `claims.create` mints ids without
  checking them against stored ones, so the duplicate-id invariant `revalidate_all` now enforces is
  never established where ids are created -- and the three functions disagree about what a duplicate
  means. Only reachable via an injected `id_factory` or a hand-edited `claims.json`; fixing it means
  a new error contract on public entry points, outside this story's boundary.
- Rejected (6): `updated_at` stamped for a claim with NO evidence (pre-story behavior for the
  single-writer path -- changing it would breach this story's own "behavior unchanged" AC; the
  concurrent-emptying variant WAS real and is patched above); `updated_at` stamped when only SOME
  results were discarded (the claim genuinely was partially updated, so the timestamp is accurate);
  `publish`'s gate not firing when a concurrent writer REMOVES an evidence entry (a fresh tuple that
  is a prefix of the validated one contains only entries this call validated, so the docstring's
  guarantee holds); `state.write`'s docstring "error contract drift" (the documented contract is
  `HeraldError` for that case, which is still what it raises); the Windows-CI coverage gap (already
  recorded in the ledger by pass 3, re-raised verbatim a third time); adding a "waiting for lock"
  notice / non-blocking first attempt to `locked` (the spec's Never-list explicitly forbids timeout
  and staleness machinery, and block-forever is the chosen contract).

### 2026-08-10 — Review pass 7
- intent_gap: 0
- bad_spec: 0
- patch: 8: (high 0, medium 1, low 7)
- defer: 2: (high 0, medium 1, low 1)
- reject: 3: (high 0, medium 0, low 3)
- addressed_findings:
  - `[medium]` `[patch]` `notices._require_existing_index` — the pre-lock fail-fast pass 6 added
    to stop the three notice mutators littering a `.herald/` tree — gated on `index_path.exists()`,
    which returns `False` whenever the *stat* itself fails. An index that exists but cannot be read
    (symlink loop, unsearchable parent, EACCES, EIO) was therefore reported as `no notice found`,
    pointing the operator at a missing notice instead of their permissions fault and silently
    replacing the `could not be read` error these calls raised before this story. `state.read`'s
    own docstring documents this exact anti-pattern as the reason it has no `exists()` pre-check.
    Now stats and treats only `FileNotFoundError`/`NotADirectoryError` as absent; every other
    `OSError` falls through to the lock so the authoritative in-lock `_load_index_document`
    produces its accurate error. Three-way parametrized regression test, proven to fail unpatched.
  - `[low]` `[patch]` `revalidate`/`revalidate_all`'s every-result-discarded guard keyed on
    `original_evidence` alone, so it missed the mirror-image case: a claim carrying NO evidence
    when this run read it, given evidence by a concurrent writer during the unlocked window. Zero
    validation calls were made, yet `updated_at` was stamped as though the newly-appeared entries
    had been checked — the same "assert a validation that never landed" defect passes 3, 5, and 6
    each fixed from a different direction. Both guards now read `(original or fresh) and not
    any(carried)`, which leaves the claim untouched in both concurrent-edit directions while
    preserving the deliberate ordinary stamp for a claim that simply has no evidence (its
    pass-6 test still passes). Two regression tests, proven to fail unpatched.
  - `[low]` `[patch]` `locked()`'s second acquisition-failure wrap — `_acquire` raising, the branch
    pass 5's Windows `EDEADLOCK`-only re-raise exists to make reachable — had zero coverage on any
    platform; both existing failure tests trip on the earlier `mkdir`/`os.open` wrap. Added
    `test_locked_raises_herald_error_when_the_lock_call_itself_fails`, pinning the AD-6 contract
    (`HeraldError` naming the lock path, `OSError` as `__cause__`, guarded block never entered).
  - `[low]` `[patch]` `test_a_failing_teardown_never_masks_the_guarded_block` monkeypatched
    `locking.os.close` — and `locking.os` IS the global `os` module, so every `os.close` in the
    interpreter raised `EIO` for the test's duration. Safe only by accident today; anything later
    added to that test body (a subprocess, a tempfile error path, a capfd read) would fail from
    nowhere near the code under test. Scoped to the descriptors `locked` itself opened.
  - `[low]` `[patch]` Five concurrency tests (`test_state`, `test_progress`, `test_notices`, and
    two in `test_claims`) joined their workers with a timeout but never asserted the threads
    finished, so a genuine deadlock regression would fail with a content mismatch that reads as a
    lost update rather than a hang — and leave two abandoned threads holding the lock for the rest
    of the session. Added the `is_alive` assertion `test_locking.py` and `test_progress.py` already
    set the precedent for.
  - `[low]` `[patch]` `claims.py`'s module docstring said `create` "locks its whole function body",
    contradicting `create`'s own docstring (and the code) since pass 3 moved the argument checks
    before the lock. Given that three of this story's six prior repairs traced to a docstring
    asserting something untrue, corrected to "whole read-modify-write span" with the carve-out named.
  - `[low]` `[patch]` `notices.py`'s module docstring made the same now-false "whole function body"
    claim for all four mutators, while three of them run `_require_existing_index` outside the lock —
    the very pre-check that produced the first finding above. A maintainer reading only the module
    docstring had no reason to suspect any pre-lock I/O existed, let alone that it decided an error
    message. Corrected, with both classes of pre-lock check named.
  - `[low]` `[patch]` `locking.py`'s module docstring narrowed the spec's "lock-acquisition/release
    failures raise `HeraldError`" bullet to *acquisition* only, without recording that the release
    and close suppression (pass 6) is a deliberate deviation or why — leaving the code and the
    spec's Always-list in unexplained contradiction. Stated the asymmetry and its rationale
    explicitly (AD-6's intent is honored, its literal wording is not). Also corrected the
    close-suppression comment, whose "the fd is released by the OS regardless" justification
    reasoned only about Linux, in the one module that exists because this package targets win-64.
- Deferred (2, appended as NEW entries to `deferred-work.md`): `revalidate`/`revalidate_all`'s
  skip branches being invisible in the return value, so `cli.py` reports a completed validation with
  a false valid/broken count for a claim it skipped (fixing it means a return-shape change, which
  this story's Never-list forbids, in a file outside its Code Map); and `revalidate_all`'s
  duplicate-claim-id refusal being a verified behavior change against the baseline (which handled
  duplicates correctly) and so a divergence from this story's own "behavior unchanged" AC — left
  open because the coherent answer spans `create`/`revalidate`/`publish`/`revalidate_all` together,
  the same cross-function policy pass 6 already deferred for `create`.
- Rejected (3): the `.lock` sidecar now left beside `state.py`/`progress.py`/`claims.py`'s document
  on a corrupt-document error path (unlike pass 6's notices case, which littered an unrelated
  directory with a whole `.herald/` tree, this sidecar lands next to a document that already exists,
  is created `0o600`, is gitignored, and would be created by the next successful call anyway — and
  the only available pre-check is the `exists()` anti-pattern this pass just removed);
  `author_notice`'s error path littering (pass 6 deliberately excluded it because creating the index
  is its job, and with the argument checks already pre-lock its remaining in-lock failure modes are
  write failures, which create the sidecar regardless); and `lock_path_for` raising ENAMETOOLONG for
  a document name within 5 bytes of `NAME_MAX` (herald's document names are fixed constants, so this
  needs a hand-passed ~255-character path, and hashing machinery to avoid it fails Simplicity First).

## Design Notes

The lock is a small context manager, not a library: a sidecar file opened (created if missing)
per protected document, with a platform-branched exclusive lock held for the `with` block's
duration.

```python
@contextlib.contextmanager
def locked(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+b") as fh:
        _acquire(fh)  # fcntl.flock(LOCK_EX) or msvcrt.locking(LK_LOCK)
        try:
            yield
        finally:
            _release(fh)
```

For notices.py, lock the whole mutating function (not just `_write_index_document`) so the
index write and the markdown write for one notice happen inside a single critical section --
this closes the markdown-file race as a side effect, without treating it as a separate fix.

**claims.py's `publish`/`revalidate`/`revalidate_all` must not hold the lock during network
I/O.** Each calls `evidence_mod.validate_link` per evidence entry -- a real HTTP request. Locking
the whole function (fine for `create`, which has no network step) would mean one slow validation
call blocks every other claims writer for its duration. Instead: validate first, lock second.

**Carry the results POSITIONALLY, never in an `Evidence`-keyed dict.** The results must be
index-aligned with the exact evidence tuple they were computed from, and applied back by index
after an equality check at that index:

```python
original = claim.evidence                                            # pre-validation snapshot
results = tuple(_revalidated_entry(e, ...) for e in original)        # network, unlocked, index-aligned
with locking.locked(claims_path.with_name(claims_path.name + ".lock")):
    claims = read_all(claims_path)  # fresh state, not the pre-validation read
    fresh = ...the claim, re-found by id...
    applied = tuple(
        results[i] if i < len(original) and e == original[i] else e
        for i, e in enumerate(fresh.evidence)
    )
    _write_all(claims_path, claims)
```

The `e == original[i]` check is what implements the discard-stale rule: if a concurrent writer
changed a specific evidence entry between the unlocked validation and the locked re-read, that
index's now-stale result is dropped rather than overwriting the newer data -- every other entry's
write still lands normally. Comparing at a fixed index (rather than looking the entry up by value)
also survives a concurrently-changed evidence length or ordering. This is a narrow, low-frequency
edge case (single-operator CLI commands racing their own evidence links), not worth a retry loop.

**An `Evidence`-keyed dict is wrong even within a single claim.** `Evidence` is a frozen,
value-equal dataclass and `create()` de-duplicates nothing (it validates only `type`), so ONE
claim can legitimately carry two field-identical entries (same url/type/label). A
`dict[Evidence, Evidence]` collapses them onto a single key: two independent validation calls are
made, but only the last result is retained and it is then applied to BOTH entries. A claim with a
duplicated link where the first check succeeds and the second hits a transient 429 stores
`[False, False]` instead of `[True, False]`. This applies to `publish`, `revalidate`, AND
`revalidate_all` alike -- operating on one claim at a time does **not** make an `Evidence`-keyed
map safe, and any comment or docstring asserting that it does is false and must not be written.

**`revalidate_all` additionally scopes per claim id.** Its per-claim structure is keyed by claim
id first, so a lookup only ever searches within that same claim's own results -- never one
structure shared across every claim's evidence, which would additionally let one claim's HTTP
outcome overwrite a different claim's:

```python
validated_by_claim = {
    c.id: (c.evidence, tuple(_revalidated_entry(e, ...) for e in c.evidence))
    for c in claims
}  # network, unlocked; per claim id, an (original, results) index-aligned pair
with locking.locked(...):
    fresh = read_all(claims_path)
    for claim in fresh:
        if claim.id not in validated_by_claim:
            ...created concurrently: leave untouched, including `updated_at`...
        original, results = validated_by_claim[claim.id]
        ...apply by index with the e == original[i] check, as above...
```

**`publish` must additionally gate on what it actually validated.** The discard-stale rule is
right for `revalidate`/`revalidate_all`, whose purpose is to record breakage rather than reject
it. It is *not* sufficient for `publish`, whose contract is that a broken link blocks the publish
and nothing is written. If the fresh locked read shows an evidence entry that changed during the
unlocked validation window, the discard rule passes that entry through unvalidated -- and `publish`
would then persist `status="published"` alongside evidence it never checked (and which a
concurrent `revalidate` may have just proved broken). So inside the lock, after computing the
final evidence tuple, `publish` re-verifies that every entry it is about to write carries this
call's own validation, and raises `errors.ClaimStateError` naming the claim (write nothing,
tell the operator to re-run) when any does not.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done (follow-up review pass 7 — no code re-derivation; 8 patches applied on top of the
pass-6 implementation).

**Implemented change (unchanged in substance from pass 6):** a stdlib-only, cross-platform advisory
file lock (`locking.py`) held across the full read-modify-write span of `state.write`,
`progress.upsert`/`write_all`, `claims.create`/`publish`/`revalidate`/`revalidate_all`, and
`notices.author_notice`/`publish_notice`/`close_notice`/`archive_rename`, closing `DW-1-4-2`'s
lost-update race. Evidence-link HTTP validation stays outside the lock, with results carried
index-aligned and applied under an `e == original[i]` check.

**Files changed this pass:**
- `src/pyforge/herald/notices.py` — `_require_existing_index` now distinguishes an absent index from
  an unreadable one (no `Path.exists()`); module docstring corrected on where the lock actually starts
- `src/pyforge/herald/claims.py` — both every-result-discarded guards now also catch evidence that
  appeared concurrently on a claim this run had nothing to validate; module docstring corrected
- `src/pyforge/herald/locking.py` — docstring records the acquisition-vs-teardown error-contract
  asymmetry and its rationale; close-suppression comment no longer reasons only about Linux
- `tests/test_notices.py` — new 3-way parametrized unreadable-index regression test; liveness assertion
- `tests/test_claims.py` — two new evidence-appeared-concurrently regression tests; liveness assertions
- `tests/test_locking.py` — new `_acquire`-failure → `HeraldError` test; `os.close` monkeypatch scoped
  to `locked`'s own descriptors
- `tests/test_state.py`, `tests/test_progress.py` — liveness assertions on the concurrency tests

**Review findings breakdown:** 8 patches applied (1 medium, 7 low); 2 deferred as new
`deferred-work.md` entries (CLI misreporting a skipped revalidation; `revalidate_all`'s duplicate-id
refusal as a baseline behavior change); 3 rejected. No intent gaps, no bad_spec repairs — the pass-6
implementation stands.

**Verification:**
- `pixi run -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/` — **784 passed, 2
  skipped** (778 + 6 new tests).
- All 5 new *behavioral* tests proven to fail against the unpatched code (reverted both fixes, ran the
  suite: 5 failed / 779 passed), then pass after — the race and the misrouted error are real, not
  hypothetical. The 6th new test is coverage-only for an untested error branch.
- `ruff format --check` and `ruff check` clean on all 8 touched files. The 24 pre-existing lint errors
  and 2 format-dirty files elsewhere in the package were left alone (untouched by this story, and
  pass 6's precedent is to fix only what the change introduces).

**Residual risks:**
- `locking.py`'s `msvcrt` branch still has no automated coverage — no CI job runs this suite on
  Windows (ledger entry from pass 3).
- The two deferred items above are real and unfixed: a skipped revalidation is still reported to the
  operator as a completed one, and a duplicate-id `claims.json` still blocks `revalidate-all` entirely.
- `DW-1-4-2`'s closure remains deliberately narrow: `deck_pipeline`'s caller-level
  read-network-write spans, `notices._write_markdown`'s non-atomic write, and `registry.register`'s
  unlocked RMW are all still open (pass-5 ledger entries).
