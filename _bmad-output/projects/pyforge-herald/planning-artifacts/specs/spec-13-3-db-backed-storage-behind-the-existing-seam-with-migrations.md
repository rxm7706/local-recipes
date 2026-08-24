---
title: 'DB-backed storage behind the existing seam, with migrations'
type: 'feature'
created: '2026-08-11'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: ['oversized']
baseline_revision: '257094dcc2cf99a95c8553b6c05ae3cc09fe876f'
final_revision: 'bac539f44a87f01c89c1325de68e4476791d318b'
---

<intent-contract>

## Intent

**Problem:** Herald's three storage modules (`progress.py`, `claims.py`, `notices.py`) each
persist to a local JSON file (`.herald/progress.json`, `.herald/claims.json`,
`.herald/notices-index.json`), serialized only by Story 13.1's per-file `fcntl`/`msvcrt`
advisory lock. Epic 13's Spec (LB-1) and `epics.md`'s own Story 13.3 AC require replacing
these three file stores with a real database carrying the same schemas, with migrations,
behind the existing pure-function seam — unblocked by Story 13.2's recorded decision.

**Approach:** Introduce one stdlib-only `sqlite3` database (`.herald/herald.db`, greenfield —
no DB code exists anywhere in this package today) via a new `db.py` module owning connection
setup, a version-tracked migration runner, and a transaction context manager. Rewrite
`progress.py`/`claims.py`/`notices.py`'s internals to read/write through it instead of JSON
files, replacing `locking.locked()` with SQLite's own transactional locking (WAL + a generous
`busy_timeout`) as the concurrency primitive for these three modules only — every public
function signature, dataclass shape, and error type stays unchanged. The first migration
imports any pre-existing `.herald/*.json` data so operators keep their already-recorded
progress/claims/notices.

## Boundaries & Constraints

**Always:**
- Stdlib `sqlite3` only; one shared `.herald/herald.db` for progress+claims+notices-index
  (state.py's `.herald/bridge-state.json` is untouched — out of Surface, still `locking.py`).
  `WAL` journal mode + a generous `busy_timeout` so concurrent writers block-and-serialize
  (never raise "database is locked") and unlocked reads never block on a writer — preserving
  today's exact blocking/non-blocking behavior.
- Every write op (`upsert`, `create`, `publish`, `revalidate`, `revalidate_all`,
  `author_notice`, `publish_notice`, `close_notice`, `archive_rename`) wraps its
  read-modify-write in one transaction, replacing `locking.locked()`. Preserve `claims.py`'s
  existing pattern exactly: validate evidence UNLOCKED (real HTTP) first, then open the
  transaction only around a fresh re-read/apply/write with its discard-stale-on-conflict rule.
- First migration imports existing `.herald/{progress,claims,notices-index}.json` data (if
  present) into the new tables, once, idempotently; leave the legacy files in place afterward
  (inert, not deleted). A file that fails today's own `read_all`/`_load_index_document`
  validation fails migration the same way (`errors.HeraldError`), never silently dropped.
- Notices' markdown (`notices/YYYY-MM/<type>/<component>.md`) stays the git-tracked durable
  copy; only the JSON index moves to the DB. `_write_markdown` is untouched, including its
  known non-atomicity.
- Add `scripts/export_progress_snapshot.py` (mirrors `export_web_snapshot.py`/
  `export_notices_snapshot.py`'s existing shape) and repoint `web/package.json`'s
  `sync-progress` script to it — `web/scripts/sync-progress.mjs` reads
  `.herald/progress.json` as a raw file, bypassing Python entirely, and would silently start
  writing an empty snapshot once this story stops writing that file (console.warn only, no
  hard failure) — a web-tab contract shape change this story must not cause.
- Every existing test in `test_locking.py`/`test_state.py` stays green, unmodified. Every
  public-behavior assertion in `test_progress.py`/`test_claims.py`/`test_notices.py` (return
  values, dataclass equality, error types, concurrency serialization) keeps passing; only
  raw-JSON-format-dependent fixtures/assertions are rewritten for the DB backing.

**Block If:**
- A `.herald/herald.db` already exists at story start with a `user_version` higher than this
  story's migration set defines — HALT rather than guessing whether to overwrite or ignore it.

**Never:**
- Touch `state.py`, `state.DEFAULT_STATE_PATH`, `.herald/bridge-state.json`, or remove
  `locking.py` (state.py still depends on it).
- Fix `notices._write_markdown`'s non-atomicity or its index-path-vs-repo_root lock-key
  mismatch — both are separately tracked, pre-existing, out of this story's scope.
- Build the full consolidated `herald snapshot` CLI command (Story 13.2's own recorded BUILD
  verdict, already filed as its own `deferred-work.md` entry, explicitly not Epic 13 scope) —
  add only the one minimal `export_progress_snapshot.py` needed to keep the existing npm hook
  working.
- Add a new runtime dependency (sqlalchemy, alembic, apsw, aiosqlite, ...) — stdlib `sqlite3`
  only, no in-repo precedent exists to follow.
- Change any CLI argument, output shape (including `--json`), or exit code. Implement LB-2
  (webhook, Story 13.4) or LB-3 (scheduler, Story 13.5).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fresh install | No `.herald/` dir, no legacy JSON | First write creates `.herald/herald.db`, schema applied | No error |
| Legacy import | `.herald/progress.json`/`claims.json`/`notices-index.json` exist, no `herald.db` yet | First migration imports every record once; legacy files left in place | No error |
| Legacy corrupt | Legacy JSON already fails today's `read_all`/`_load_index_document` | Migration raises `errors.HeraldError` naming the file | Structural failure, nothing partially imported |
| Unknown future schema | `herald.db` exists with `user_version` above this story's latest | HALT — no automatic overwrite or downgrade | Blocking condition, per Boundaries |
| Concurrent writers, same key | Two callers `upsert` the same `(station, date)` / `publish` the same claim id concurrently | Second writer's change lands after the first commits; no update lost | Serialized via SQLite transaction, matches Story 13.1 parity |
| Web build after swap | `npm run build` against a DB seeded via CLI | `export_progress_snapshot.py` (new) + the two existing exporters produce all three `web/public/*.json` snapshots unchanged in shape | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/db.py` -- NEW: `DEFAULT_DB_PATH`,
  connection setup (WAL, busy_timeout), version-tracked migration runner (embedded SQL/Python,
  not separate `.sql` files — avoids a hatchling packaging-data risk with no in-repo
  precedent), `transaction()` context manager, one-time legacy-JSON import.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/progress.py` -- MODIFY: internals of
  `read_all`/`write_all`/`_write_all_unlocked`/`upsert`/`latest_for_station`/`list_records`
  swap JSON I/O for `db.py`; `DEFAULT_PROGRESS_PATH = db.DEFAULT_DB_PATH`. Public signatures
  unchanged.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/claims.py` -- MODIFY: same swap for
  `read_all`/`read_one`/`list_claims`/`create`/`publish`/`revalidate`/`revalidate_all`/
  `snapshot`/`referenced_by_claims`; preserve the unlocked-validate-then-recheck pattern
  exactly (now via `db.transaction`). `DEFAULT_CLAIMS_PATH = db.DEFAULT_DB_PATH`.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/notices.py` -- MODIFY: index-related
  functions (`author_notice`/`publish_notice`/`close_notice`/`get_notice`/`aliases_for`/
  `list_notices`/`archive_rename`) swap the index's JSON I/O for `db.py`; `_write_markdown`
  and the markdown path untouched. `DEFAULT_INDEX_PATH = db.DEFAULT_DB_PATH`.
- `src/shared/packages/pyforge-herald/scripts/export_progress_snapshot.py` -- NEW: mirrors
  `export_web_snapshot.py`'s shape; calls `progress.list_records()`, writes
  `web/public/progress.json`.
- `src/shared/packages/pyforge-herald/web/package.json` -- MODIFY: `"sync-progress"` script
  repointed to `python ../scripts/export_progress_snapshot.py` (or equivalent); remove the
  now-dead `web/scripts/sync-progress.mjs`.
- `src/shared/packages/pyforge-herald/tests/test_db.py` -- NEW: migration idempotency/
  versioning, WAL+busy_timeout config, legacy-JSON import (success + corrupt-file failure),
  unknown-future-`user_version` HALT behavior.
- `src/shared/packages/pyforge-herald/tests/test_progress.py`,
  `tests/test_claims.py`, `tests/test_notices.py` -- MODIFY: rewrite raw-file-format-dependent
  fixtures/assertions (e.g. "invalid JSON raises HeraldError") for the DB backing; every
  public-behavior assertion (including the existing `threading.Barrier` concurrency tests)
  keeps passing.
- `src/shared/packages/pyforge-herald/tests/test_export_progress_snapshot.py` -- NEW: mirrors
  `tests/test_export_web_snapshot.py`'s pattern.
- `src/shared/packages/pyforge-herald/docs/cli-runbooks.md`,
  `docs/automation-troubleshooting.md`, `docs/operator-guide.md`, `docs/web-ux-guide.md` --
  MODIFY: replace the JSON-corruption troubleshooting text and `.herald/{progress,claims,
  notices-index}.json` file-location references with `.herald/herald.db`; update
  `web-ux-guide.md`'s exporter table row for Progress.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py`,
  `scripts/export_web_snapshot.py`, `scripts/export_notices_snapshot.py`, `web/README.md` --
  MODIFY (added by the 2026-08-13 review pass): the same rename sweep, in the four places the
  first pass missed. These carry the JSON filenames in *user-facing* text -- `--repo-root`'s
  `--help` string in both `cli.py` and `export_web_snapshot.py` -- so `herald success --help`
  contradicted the runbooks rewritten above it, and `web/README.md` still pointed readers at the
  deleted `scripts/sync-progress.mjs`. Text only; no behavior.
- (Fourth review pass, 2026-08-13 -- no new files.) `db.py`: `_import_legacy_v1` skips a store
  whose table already holds rows, `connection()` translates the write paths' full exception set,
  `_has_legacy_data` uses `_is_definitely_absent` and takes the names to check. `claims.py`: new
  `_write_transaction` helper, used by all four writers (`create`'s bespoke wrapper folded into
  it). `notices.py`: the stale-markdown `unlink` moved past the commit; `_require_existing_index`
  asks only about the notices legacy store. Stale-reference sweep completed in `locking.py`,
  `errors.py`, `tests/test_bridge.py`, and `web/src/panels/{Progress,Success,Operations}Panel.jsx`
  (text only). `docs/automation-troubleshooting.md`: the two new operator-facing failure modes.
  `tests/test_db.py` + `tests/test_notices.py`: 7 regression tests.
- (Third review pass, 2026-08-13 -- no new files.) `db.py`: `_is_definitely_absent` added,
  `_empty_read_connection` rebuilt from a new `_SCHEMA_MIGRATIONS` (with `_migrate_v1` split
  into `_schema_v1` + the legacy import), schema SQL made `CREATE TABLE IF NOT EXISTS`.
  `notices.py`: `_require_existing_index` consults `db._has_legacy_data`; write-order comment
  corrected; write paths widened to the pre-13.3 exception set (also `progress.py`,
  `claims.py`). `claims.py`: `create` wrapped. `tests/test_db.py`: 6 regression tests added,
  3 legacy-import tests taught to assert "once". `scripts/export_progress_snapshot.py`: mode
  `100644` -> `100755`.

## Tasks & Acceptance

**Execution:** (all paths relative to `src/shared/packages/pyforge-herald/`)
- [x] `src/pyforge/herald/db.py` -- create connection/migration/transaction module -- the new
  storage foundation every other module rewrite depends on
- [x] `src/pyforge/herald/progress.py` -- swap internals to `db.py`, preserve public API --
  first consumer, smallest schema (no nested sub-objects)
- [x] `src/pyforge/herald/claims.py` -- swap internals to `db.py`, preserve the
  unlocked-validate-then-recheck pattern -- most complex consumer (evidence/edit_history JSON
  columns, HTTP-in-the-middle transaction shape)
- [x] `src/pyforge/herald/notices.py` -- swap index internals to `db.py`, leave `_write_markdown`
  untouched -- third consumer, index+redirects JSON columns
- [x] `scripts/export_progress_snapshot.py` -- add, mirroring the two existing exporters --
  closes the web-tab regression this story's swap would otherwise cause
- [x] `web/package.json` + delete `web/scripts/sync-progress.mjs` -- repoint the npm hook --
  completes the exporter swap
- [x] `tests/test_db.py` -- add migration/import/HALT coverage -- proves the new foundation
  before trusting it under the three rewritten modules
- [x] `tests/test_progress.py`, `tests/test_claims.py`, `tests/test_notices.py` -- rewrite
  format-dependent fixtures, keep every public-behavior assertion -- proves behavioral parity
- [x] `tests/test_export_progress_snapshot.py` -- add -- proves the new exporter script
- [x] `docs/cli-runbooks.md`, `docs/automation-troubleshooting.md`, `docs/operator-guide.md`,
  `docs/web-ux-guide.md` -- update storage-location/corruption text -- keeps operator docs
  truthful after the swap

**Acceptance Criteria:**
- [x] Given the full existing `locking`/`state`/`progress`/`claims`/`notices` test suite, when run
  after this story's changes, then every test passes. (**827 passed, 2 pre-existing unrelated
  skips**, after the fourth review pass added 7 tests to the 820 that passed before it. Measured with
  `PYTHONPATH=src python -m pytest tests -q` run **inside this worktree** -- note that
  `pixi run -e pyforge-herald pyforge-herald-test` resolves its `pytest` path against the main
  checkout, so it reports that tree's numbers, not this branch's; the earlier "804" in this AC was
  that mismatch.)
- [x] Given `herald progress <station> --update`, `herald success create/publish/revalidate`, and
  `herald notice author/publish/close`, when run against a fresh `.herald/` directory, then
  their CLI output shape and exit codes are unchanged from before this story. (Verified via the
  unmodified `test_cli_progress.py`/`test_cli_success.py`/`test_cli_notice_epic10.py` suites,
  all green with no assertion changes.)
- [x] Given an operator's pre-existing `.herald/progress.json`/`claims.json`/`notices-index.json`,
  when `herald` next runs (triggering the first migration), then every record is present and
  readable via the module's public read functions afterward, and the legacy files remain on
  disk untouched. (Verified both by `tests/test_db.py`'s legacy-import coverage and by a manual
  scratch-directory run -- see Dev Notes.)
- [x] Given `npm run build`, when run against a DB seeded via the CLI, then `web/public/progress
  .json`, `success.json`, and `notices.json` are all produced correctly with no dependency on
  `sync-progress.mjs`. (Verified manually -- see Dev Notes; `sync-progress.mjs` deleted.)
- [x] Given two concurrent writers hitting the same `(station, date)` / same claim id / same
  notice component, when both write concurrently, then no update is silently lost. (Proven by
  real cross-thread `db.transaction` serialization in `test_db.py`, `test_progress.py`,
  `test_claims.py`, `test_notices.py`'s Story 13.1 concurrency suites.)
- [x] Given notices authored/published/closed after this story, when the markdown files under
  `notices/YYYY-MM/...` are inspected, then their write mechanism (including the known
  non-atomicity) is unchanged from before this story. (`_write_markdown`/`_render_markdown`
  untouched, byte-for-byte the same as before this story.)

**Dev Notes (2026-08-13):**
- `db.py` uses a reentrant, thread-local "ambient transaction" design (`transaction()`/
  `connection()`) so `read_all`/`_write_all`-style functions keep their exact pre-13.3
  single-argument call shape both standalone and from inside a write function's own critical
  section -- this is what let the great majority of the existing `monkeypatch.setattr(claims,
  "read_all", ...)`-based Story 13.1 concurrency tests keep working with only a path-fixture
  rename (`"claims.json"` -> `"herald.db"`, to avoid colliding with the legacy-import filename
  convention). Tests that asserted against the retired `.lock` sidecar file directly were
  rewritten to prove the same guarantee via a real, independent `BEGIN IMMEDIATE` attempt
  against the database instead.
- `claims.id` is deliberately NOT a schema-level PRIMARY KEY/UNIQUE column (unlike
  `progress.id`/`notices_index.component`): duplicate-id detection stays the application-level
  `claims._require_unique_ids` concern Story 13.1 pass-4 already built, matching the
  pre-Story-13.3 JSON array's own semantics. A hard schema constraint would have made that
  guard structurally unreachable and changed a tested error message.
- Manual verification performed: (1) `npm install && npm run build` in `web/` -- clean build,
  `sync-progress` invoked `export_progress_snapshot.py` successfully; all three
  `public/{progress,success,notices}.json` produced (via build + the two manual exporters,
  matching this package's existing "no single sync-everything command" convention). (2) A
  scratch `/tmp` directory hand-seeded with `.herald/{progress,claims,notices-index}.json`
  (one record each) then read via the public module functions -- `.herald/herald.db` created,
  `sqlite3 .herald/herald.db "select count(*) from progress"` etc. all returned `1` (`0` for
  `notices_redirects`, none seeded), `PRAGMA journal_mode` = `wal`, `PRAGMA user_version` = `1`,
  and all three legacy JSON files remained present and byte-identical afterward.
- Repair pass (2026-08-13): the prior session's `20b88dd689` commit left `python
  scripts/spec_surface_reconcile.py` gating-red (22 findings) -- `spec-pyforge-herald` and
  `spec-herald-moments-2-4-live-backend` each govern part of this story's 18-file diff, and
  neither spec's `.memlog.md` had moved to reconcile it. No code changed for this repair;
  reconciled by naming the changed paths in both specs' `.memlog.md` per the established
  convention (see each memlog's own 2026-08-13 "SURFACE DRIFT RECONCILED"/"LB-1 IMPLEMENTED"
  entry). Verified: `python scripts/spec_surface_reconcile.py` now exits 0
  ("OK: every tracked file governed or allowlisted; no drift"), and
  `python -m pyforge.doctor.sources spec-surface` reports zero herald findings (neither FAIL nor
  WARN) -- fully reconciled, not merely downgraded to non-gating drift-presumed.

**Dev Notes -- follow-up review pass (2026-08-13):**
- **Measure inside the worktree.** `pixi run -e pyforge-herald pyforge-herald-test` runs
  `pytest src/shared/packages/pyforge-herald/tests` resolved against the MAIN checkout, so in a
  bmad-loop run worktree it silently reports the *other* tree's result: it returned an identical
  "784 passed" both with this pass's changes applied and with them `git stash`ed, while the
  worktree's own baseline was 803. Every number in this pass comes from
  `PYTHONPATH=src python -m pytest tests -q` run inside the worktree. Final: **814 passed, 2
  skipped** (803 baseline + 11 new tests).
- The read/write asymmetry in error handling was the pass's one high-severity finding, and it was
  fixed at the seam rather than per-call-site: `db.connection()` now translates any `sqlite3.Error`
  raised inside its `with` block into `errors.HeraldError`, covering all six read functions at once
  and keeping future readers correct by construction. The ambient branch deliberately does NOT
  wrap -- inside a transaction the writer's own handler owns the whole critical section.
- `STRICT` was added to all four tables rather than restoring `_fields_problem` on the read path:
  it makes the wrong-typed value impossible to store instead of merely detected on the way back
  out, costs nothing per read, and is what makes the modules' existing "plain, typed SQL column"
  docstrings true. Safe to change v1's schema in place because the story is unlanded and
  `.herald/` is gitignored scratch -- no operator database exists at v1 yet.
- Reads of a not-yet-existing store are served from an in-memory database carrying the schema.
  The legacy-import contract is preserved by checking for the legacy JSON files first: a store
  that does not exist BUT has `progress.json`/`claims.json`/`notices-index.json` beside it still
  goes through the real database, so the "import triggers on any command" requirement holds.
- Each new test was mutation-checked rather than assumed discriminating: stripping `BEGIN
  IMMEDIATE` fails the new notices lost-revision test, dropping `STRICT` fails the type test, and
  restoring the always-retry loop fails the WAL test after exactly 30.09s -- reproducing the
  original stall to the hundredth of a second.
- Re-verified after the pass: full suite 814 passed / 2 skipped; `python
  scripts/spec_surface_reconcile.py` exits 0; `python -m pyforge.doctor.sources spec-surface`
  reports zero herald findings (the four newly-touched paths named in both specs' `.memlog.md`
  per the same convention the first repair pass established); all three exporters produce their
  snapshots from a CLI-seeded database; `npm run build` clean, with `sync-progress` invoking
  `export_progress_snapshot.py` successfully.

**Dev Notes -- follow-up review pass (2026-08-13, third pass):**
- Both high-severity findings were the same mistake in two places: **treating
  `Path.exists()` as "does this store exist"**. It answers "could I stat it", and every
  stat failure collapses into the same `False` as a genuinely absent file. `notices.py`
  already had the right pattern (and a docstring explaining it) from Story 13.1;
  `db.connection` and `notices._require_existing_index`'s *new* `herald.db`-based
  fast-path each got it wrong in a different direction -- one read a locked store as
  empty, the other read a not-yet-migrated store as missing. Fixed by making the
  distinction explicit (`db._is_definitely_absent`) and by giving the fail-fast the
  legacy-awareness `db.connection` already had.
- Both were **operator-upgrade-path** bugs invisible to the suite: they need either a
  permissions fault or a pre-existing legacy JSON store, neither of which any test
  fixture had. The suite was green at 814 before this pass and is green at 820 after.
- **Every new test was mutation-checked, and one failed the check.**
  `test_empty_read_connection_...` originally compared the in-memory and on-disk schemas
  directly -- which, with only one migration registered, compares two identical things
  and can never fail. It now injects a synthetic v2 (the state the next schema change
  puts the module in) and asserts the in-memory path picks it up. The same mutation
  sweep also caught that routing `_empty_read_connection` through `_ensure_schema` made
  a pure read attempt the legacy import, which had silently defused the
  unreadable-store test; that is why the structural half is split out as `_schema_v1`.
  Mutation results: reverting each fix fails its own test (M1 exists()-gate, M2
  legacy-check, M3 `IF NOT EXISTS`, M4 `create` wrapper, M5 exception set, M6 hardcoded
  v1 schema).
- Measurement, again, from **inside the worktree** (`PYTHONPATH=src python -m pytest
  tests -q`) -- `pixi run -e pyforge-herald pyforge-herald-test` still resolves against
  the main checkout and reports that tree's numbers.
- Re-verified after the pass: 820 passed / 2 skipped; `python
  scripts/spec_surface_reconcile.py` exits 0; `python -m pyforge.doctor.sources
  spec-surface` reports zero herald findings; all three exporters emit real data from a
  seeded database (`progress.json` 370 B, `notices.json` 372 B; `success.json` is `[]`
  only because the seeded claim is a draft, which is the exporter's own pre-existing
  published-only filter); legacy import verified end-to-end for all three stores plus a
  redirect, with the legacy files left in place; `npm run build` clean, `sync-progress`
  invoking `export_progress_snapshot.py`.
- One item deferred rather than patched (`DW-FU-13-3`): a single corrupt legacy JSON file
  aborts the shared migration and so blocks all three Moments, where pre-13.3 it blocked
  only its own. Not a spec deviation -- one shared database and fail-on-invalid-legacy
  are both mandated -- so it needs a design decision, not a fix.

**Dev Notes -- follow-up review pass (2026-08-13, fourth pass):**
- **Both high/medium storage findings were a previous pass's fix reasoning being right about
  three cases and wrong about the fourth.** The `IF NOT EXISTS` fix argued a re-run import is
  caught by the tables' `PRIMARY KEY`s -- true for `progress`/`notices_index`/`notices_redirects`,
  false for `claims`, the one table this story deliberately gives no key. The `create` wrapper
  argued the other three claims writers are covered by their pre-transaction read -- true of that
  read, and they each take a second one inside the transaction. Both were found by testing the
  stated premise rather than reading the reasoning, which is the only way this class shows up.
- **The read/write asymmetry recurred twice more and was closed at the seam both times.** The
  third pass widened the WRITE paths' exception set for a lone surrogate; the read seam kept
  `sqlite3.Error` and had the identical hole, reachable through the real CLI. The third pass added
  `_is_definitely_absent` because `Path.exists()` conflates "absent" with "un-stat-able"; the
  helper right beside it still asked `exists()`. Fixing at `db.connection`/`db._has_legacy_data`
  covers every current and future caller rather than the six that exist today.
- `notices.author_notice`'s stale-markdown `unlink` is the one operation whose placement the
  transaction genuinely changed. Pre-13.3 the index write was already durable when it ran, so a
  failure afterwards could not un-write the index; inside a transaction the same failure rolls the
  index back onto a path this call has already deleted. Moving it past the commit restores the old
  ordering semantics exactly, including its "raise if the unlink fails" behavior.
- Measurement, again, from **inside the worktree** (`PYTHONPATH=src python -m pytest tests -q`):
  820 before, 827 after. `pixi run -e pyforge-herald pyforge-herald-test` still resolves against
  the main checkout and reports that tree's numbers.
- Every new test was mutation-checked and one mutation was wrong before it was right: M6 initially
  "passed" because the edit landed on `create` rather than `publish` (both call sites now read
  `_write_transaction`, so a positional sed hits the wrong one). Re-run against `publish`, it
  fails. The other six failed their own tests on the first attempt.
- Re-verified after the pass: 827 passed / 2 skipped; `python scripts/spec_surface_reconcile.py`
  exits 0; all three exporters emit real data from a CLI-seeded database (`progress.json` 381 B,
  `success.json` 632 B with a published claim, `notices.json` 1 notice); `npm run build` clean
  with `sync-progress` invoking `export_progress_snapshot.py`.
- One item deferred rather than patched (`DW-FU-13-3-2`): a read-only `.herald/` now fails every
  command, including reads that worked pre-13.3. The cause is WAL itself -- even a bare
  `PRAGMA journal_mode` raises on such a store -- and WAL is mandated by this story's Boundaries,
  so it needs a design decision, not a fix.
- One stale reference was found and deliberately left: `pixi.toml`'s `pyforge-herald-web-snapshot`
  task description still names `.herald/claims.json`. `pixi.toml` is governed by
  `pyforge-marshal/spec-pyforge-core`, so `spec_surface_reconcile.py` reds on the edit and the fix
  belongs to that Spec's surface, not to a herald story.

## Design Notes

**Schema shape (illustrative, not exhaustive):**
```sql
CREATE TABLE progress (
  id TEXT PRIMARY KEY, station TEXT NOT NULL, date TEXT NOT NULL,
  shipped_capabilities TEXT NOT NULL,  -- JSON array
  compute_hours REAL NOT NULL, token_spend INTEGER NOT NULL,
  wall_clock_hours REAL NOT NULL, unblock_narrative TEXT NOT NULL,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(station, date)
);
-- claims / notices_index / notices_redirects mirror the same shape; nested
-- lists (evidence, edit_history, revisions) stored as JSON TEXT columns --
-- no cross-record query is named by any AC, so 3NF normalization is
-- deliberately out of scope (Simplicity First).
```

**Concurrency:** SQLite's own `BEGIN IMMEDIATE ... COMMIT` transaction is the sole lock
primitive for progress/claims/notices — this is the epic's own named alternative to Story
13.1's fcntl lock ("moving to one real database with native locking/transactions"), not a
second mechanism layered on top. `state.py` keeps `locking.py` unchanged since it is out of
Surface.

**Why one shared `.herald/herald.db`, not three files:** `epics.md`'s own AC says "the
database" (singular) carries all three schemas — matches the epic's Technical Decision framing
("one real database... [vs] per-document lock"). Each module's `DEFAULT_*_PATH` constant is
redefined to `db.DEFAULT_DB_PATH` rather than removed, so every existing call site
(`cli.py`'s `progress.DEFAULT_PROGRESS_PATH`, etc.) needs zero changes.

## Verification

**Commands:**
- `pixi run -e pyforge-herald pyforge-herald-test` -- expected: all tests pass, including new
  `test_db.py` and `test_export_progress_snapshot.py`
- `pixi run -e pyforge-herald pyforge-herald-web-snapshot` -- expected: `success.json` still
  exports correctly (claims path unaffected by the exporter-script changes)
- `cd src/shared/packages/pyforge-herald/web && npm run build` -- expected: builds clean,
  `public/progress.json`/`success.json`/`notices.json` all present

**Manual checks:**
- Seed `.herald/progress.json`/`claims.json`/`notices-index.json` by hand in a scratch repo
  root, run any `herald` command once, then inspect `.herald/herald.db` (`sqlite3 .herald/herald.db
  "select count(*) from progress"`, etc.) to confirm the legacy import landed.

## Review Triage Log

### 2026-08-13 — Review pass (follow-up, fourth pass)
- intent_gap: 0
- bad_spec: 0
- patch: 9 (high 1, medium 3, low 5)
- defer: 1
- reject: 13
- addressed_findings:
  - `[high]` `[patch]` The legacy import silently DUPLICATED every claim on the one path that
    legitimately reruns the v1 migration over populated tables. The third pass made the schema SQL
    `CREATE TABLE IF NOT EXISTS` so a database restored from `sqlite3 .dump` (which emits no
    `PRAGMA user_version`, so it comes back full at version 0) is not permanently bricked, and
    justified leaving the import half alone with: "if legacy JSON is also present the `INSERT`s hit
    the existing rows' `PRIMARY KEY` and raise `IntegrityError`". That premise is false for exactly
    one table -- `claims`, whose `id` is deliberately NOT a key (this story's own Dev Note explains
    why). Reproduced end to end on the documented restore path: a repo carrying only
    `.herald/claims.json` (a station that uses `herald success` and not `herald progress`) went from
    `['c1']` to `['c1', 'c1']` at exit 0, after which `revalidate_all` refused permanently with
    "holds duplicate claim ids" -- and there is no repair tool. `_import_legacy_v1` now skips each
    store whose destination table already holds rows, which is also the more accurate reading of the
    spec's own "imports ... once, idempotently": a re-run is a no-op rather than an `IntegrityError`
    the operator has to interpret.
  - `[medium]` `[patch]` `claims.publish`/`revalidate`/`revalidate_all` leaked a raw `sqlite3.Error`
    past the AD-6 seam -- the same defect the third pass patched in `create`, left in the other three
    on a reasoning that only covered half of each. That pass's comment argues they "each take their
    first `read_all` BEFORE opening the transaction, so that one is standalone and already covered";
    true, and beside the point, because each then takes a SECOND, in-transaction `read_all` that is
    ambient, which `db.connection` deliberately does not translate. Reproduced with the fault
    arriving during the unlocked evidence-validation window -- which for `revalidate_all` is one
    real HTTP request per evidence entry across every claim, i.e. seconds to minutes wide:
    `sqlite3.OperationalError: no such table: claims` reached `cli.dispatch`, which catches only
    `HeraldError`, as a traceback. Fixed once, at a new `claims._write_transaction` helper all four
    writers now use, rather than three more copies of the same `try`.
  - `[medium]` `[patch]` The READ seam translated only `sqlite3.Error`, so the exact failure the
    third pass fixed on the write side escaped on the read side. That pass widened the writers to
    the pre-13.3 set `(OSError, TypeError, ValueError, RecursionError)` citing "a lone surrogate
    (what `argv` yields for a non-UTF-8 byte via `surrogateescape`)"; binding a parameter is where
    SQLite converts Python values, and reads bind parameters too. Reproduced through the real CLI,
    not by inspection: `herald success review $'\xff'` reached `read_one`'s `WHERE id = ?` and
    exited as a raw `UnicodeEncodeError` traceback. `db.connection` now catches the writers' set, so
    all six read functions are covered at the seam.
  - `[medium]` `[patch]` `notices.author_notice` deleted the OLD markdown file INSIDE the
    transaction, so a rollback left the index pointing at a file this call had already removed --
    the phantom entry that function's own write-ordering comment exists to prevent, plus the loss of
    the git-tracked durable record. Reachable via a COMMIT failure (ENOSPC/EIO) or a Ctrl-C in the
    window; verified with an injected commit failure on a re-author under a changed `--type` (which
    is what relocates the path). Under the pre-13.3 JSON store the index write was already durable
    at that point, so there was nothing to roll back to -- the transaction is what created this.
    The unlink now runs after the commit, restoring the pre-13.3 ordering semantics; the stale
    write-order comment claiming the `unlink` is one of the operations a rollback protects was
    corrected with it.
  - `[low]` `[patch]` `db._has_legacy_data` asked `Path.exists()`, one helper over from
    `_is_definitely_absent`, which the third pass added precisely because `exists()` collapses every
    stat failure into "absent". A legacy store behind a stat failure (symlink loop, EIO) therefore
    read as no-legacy-data: the read path was served `[]` from the empty in-memory database while
    the write path on the same store correctly reported the file could not be read.
  - `[low]` `[patch]` `_SCHEMA_MIGRATIONS` and `_MIGRATIONS` are two hand-kept tuples whose
    agreement was asserted only in a docstring ("Every entry here must have a matching version in
    `_MIGRATIONS`"), and the one test that exercises them monkeypatches BOTH plus `SCHEMA_VERSION`
    together, so it structurally cannot catch a one-sided entry. Confirmed by registering a v2 in
    `_MIGRATIONS` alone: the on-disk store gets the column, the in-memory read connection does not,
    and both stamp v2 -- re-arming the exact defect `_empty_read_connection` was rebuilt to fix.
    Pinned with a test rather than a runtime assert (no per-call cost, caught in CI).
  - `[low]` `[patch]` `notices._require_existing_index`'s legacy bypass asked whether ANY of the
    three legacy stores exists, not the notices one, so an unrelated `.herald/progress.json` (a repo
    that used `herald progress` and never `herald notice`) suppressed the fail-fast and put back the
    `.herald/` tree it exists to avoid creating on a pure error path. `db._has_legacy_data` now
    takes the names to check.
  - `[low]` `[patch]` Five more files still named the deleted JSON stores in text a reader hits:
    `locking.py`'s module docstring still claimed scope over `state.py`/`progress.py`/`claims.py`/
    `notices.py` -- which THIS STORY made false, leaving `state.py` its one caller;
    `tests/test_bridge.py` repeated the same sentence in a docstring this diff had already edited;
    `errors.py`'s `ClaimNotFoundError` said "does not exist in `claims.json`"; and all three web
    panels named their old `.herald/*.json` source in their header comments. Text only, no behavior.
  - `[low]` `[patch]` The rewritten troubleshooting doc defined corruption as exactly two things and
    omitted both operator-facing failure modes THIS STORY introduced -- the `user_version` HALT
    (what an accidental herald downgrade looks like) and "legacy data could not be imported", whose
    only stated remedy lived in a source comment. Both added, framed as "not corruption" so the
    restore-from-backup advice above them is not misapplied to either.

  Every new test was mutation-checked, and one mutation was itself wrong before it was right:
  reverting each of the seven fixes fails its own test (M1 import guard, M2 read-seam exception set,
  M3 `_is_definitely_absent`, M4 divergent registries, M5 narrowed notices predicate, M6 `publish`'s
  wrapper, M7 unlink-inside-transaction) -- but M6 first "passed", because the sed targeting the
  first `_write_transaction` call site hit `create`, not `publish`; re-run against the right site it
  fails. Suite: 820 passed before this pass, 827 after (7 new), 2 pre-existing skips, measured with
  `PYTHONPATH=src python -m pytest tests -q` inside the worktree per the second pass's note.

  Deferred (1): a read-only `.herald/` directory now fails every command, including reads that
  worked pre-13.3. Filed rather than patched because the cause is WAL itself -- verified that even a
  bare `PRAGMA journal_mode` raises "attempt to write a readonly database" on such a store, since a
  WAL database opened read-write must write its `-shm` sidecar -- and WAL is mandated by this
  story's own Boundaries, so re-deriving reproduces it. Resolving it is a design decision (a
  `mode=ro` connection, or documenting that `.herald/` must be writable), not a fix.

  Rejected as noise, spec-compliant-by-design, or disproportionate (13). Four prior-pass rejections
  were re-tested rather than inherited; all four survived on verified premises. (1) "The runbooks now
  direct operators to DELETE `herald.db`, so the legacy re-import discards newer work" -- re-read
  both rewritten sections: they say *restore from a backup*, never *delete*. (The `.dump` variant of
  that advice is reachable and IS the high finding above, but by a different mechanism.) (2)
  `web/package.json` invoking `python` rather than `python3` -- re-raised this pass on the new
  premise that a stock Linux box has no `python`; the choice remains correct for the pixi/conda env
  these scripts run in (where `python3` does not exist on Windows), `npm run build` re-verified clean
  this pass, and the sibling exporter this script was modeled on uses the same interpreter name. The
  related claim that "both sibling exporters use `python3`" is false: `export_web_snapshot.py`, the
  one the spec names as the model, is `#!/usr/bin/env python`. (3) `compute_hours=2` round-tripping
  as `2.0` through the `REAL` column -- dataclass equality holds and every JSON consumer reads them
  identically. (4) `progress.write_all` now rejecting a duplicate `(station, date)` the JSON array
  tolerated -- verified still wrapped in `HeraldError`. The rest: `_set_wal_mode` not verifying the
  mode it set (no reachable silent case demonstrated -- SQLite raises here rather than returning a
  different mode, and the obvious "check the current mode first" refactor cannot help, since reading
  `PRAGMA journal_mode` needs the same write access); `_is_busy` matching "locked"/"busy" as
  substrings (unreachable -- `_set_wal_mode` is its only caller and its pragma cannot emit those
  messages); the two "different keys both land" concurrency tests being non-discriminating (the
  second pass deliberately kept them and corrected their docstrings to say so, naming the test that
  does carry the guarantee); one shared database widening lock contention across the three Moments,
  now including `_write_markdown` inside the transaction (the spec mandates one shared database, and
  a local markdown write is milliseconds); "could not be opened" wording on a lock timeout (right
  error type and exit code); `export_progress_snapshot.py`'s cwd-relative `--repo-root` default
  (matches `export_web_snapshot.py`'s precedent exactly); `HERALD_PROGRESS_PATH` no longer honored
  (the variable named a `progress.json` that no longer exists as a concept); `json.dumps` accepting
  `inf` (pre-existing -- the JSON store had the identical behavior -- and reachable only via
  `--compute-hours inf`); and `_has_legacy_data` "making reads return `[]`" as reported (the reported
  mechanism misquotes the code; the real variant of that hazard is the `exists()` finding patched
  above). One further stale reference was found and deliberately NOT patched: `pixi.toml`'s
  `pyforge-herald-web-snapshot` task description still names `.herald/claims.json`, but `pixi.toml`
  is governed by `pyforge-marshal/spec-pyforge-core`, so `scripts/spec_surface_reconcile.py` reds on
  the edit and correcting it belongs to that Spec's surface, not to a herald story.

### 2026-08-13 — Review pass (follow-up, third pass)
- intent_gap: 0
- bad_spec: 0
- patch: 9 (high 2, medium 3, low 4)
- defer: 1
- reject: 9
- addressed_findings:
  - `[high]` `[patch]` Every `notices` MUTATION refused to see a legacy index, so the first
    command an operator ran after upgrading decided the outcome. `publish_notice`/
    `close_notice`/`archive_rename` call `_require_existing_index`, whose fail-fast stats
    `DEFAULT_INDEX_PATH` -- repointed by this story at `.herald/herald.db`, which on an
    un-migrated repo does not exist yet. It therefore refused BEFORE anything could reach
    `_connect`/`_import_legacy_v1`, while the legacy `.herald/notices-index.json` sat right
    there. Reproduced: on a repo carrying only the legacy index, `publish_notice` raised
    `no notice found for component 'auth-api-v1'`; running any read first (which does open a
    connection, and so migrates) made the identical call succeed. Ordering-dependent, silent,
    and on the exact upgrade path AC 3 is about. `db._has_legacy_data` -- already the predicate
    `db.connection` uses for this same distinction -- now gates the fast path.
  - `[high]` `[patch]` `db.connection` gated the side-effect-free read path on
    `db_path.exists()`, and `Path.exists()` returns `False` for ANY stat failure (EACCES,
    symlink loop, EIO), so a store that exists but cannot be read was served from the empty
    in-memory database: `progress.read_all`/`claims.read_all`/`notices.list_notices` returned
    `[]` and `read_one`/`get_notice` raised "not found", with no error, while the write path on
    the identical store raised correctly. All three exporters are pure readers, so this
    silently rewrote healthy `web/public/*.json` snapshots to `[]` at exit 0 -- and
    `automation-troubleshooting.md`'s new "all three exporters raise on read failure" text was
    false for it. This is the hazard `notices._require_existing_index`'s own docstring spends a
    paragraph forbidding, reintroduced two files over. Reproduced with `chmod 000` on
    `.herald/`. Replaced with `_is_definitely_absent`, which discriminates
    `FileNotFoundError`/`NotADirectoryError` from every other `OSError` exactly as that
    docstring prescribes.
  - `[medium]` `[patch]` `claims.create` leaked a raw `sqlite3.Error` past the AD-6 seam. The
    previous pass fixed the read path "once at the seam" in `db.connection`, but that
    translation deliberately does not apply inside a transaction (the writer owns its critical
    section) -- and `create` is the only writer whose sole read is the ambient one AND which
    carried no `except sqlite3.Error` of its own. `publish`/`revalidate`/`revalidate_all` escape
    only incidentally, taking their first `read_all` before the transaction opens. Reproduced:
    after an out-of-band `DROP TABLE claims`, `create` raised
    `sqlite3.OperationalError: no such table: claims` to `cli.dispatch`, which catches only
    `HeraldError`, as an unhandled traceback; `progress.upsert` on the same damaged store
    correctly returned a `HeraldError`.
  - `[medium]` `[patch]` A database restored from a LOGICAL dump was bricked permanently.
    `sqlite3 .dump` does not emit `PRAGMA user_version`, so such a restore -- a plausible
    reading of the "restore `.herald/herald.db` from a backup ... there is no repair tool"
    advice THIS STORY wrote into `cli-runbooks.md` and `automation-troubleshooting.md` -- comes
    back with all four tables populated at version 0. `_ensure_schema` then reran the v1
    migration and died on `table progress already exists`, on that command and every subsequent
    one, with no repair path. Reproduced end to end. Schema SQL is now
    `CREATE TABLE IF NOT EXISTS`, making re-running the migration over present tables a no-op;
    the legacy-import half stays correct on that path, since a duplicate would hit the primary
    key and surface as the accurate "legacy data could not be imported".
  - `[medium]` `[patch]` The write paths narrowed their exception set to `sqlite3.Error`, but
    `_to_params` -- which still `json.dumps` the JSON columns -- runs inside the same `try`. The
    pre-Story-13.3 writers caught `(OSError, TypeError, ValueError, RecursionError)`, so this
    silently regressed the error contract the story promised to keep unchanged. Reproduced
    both arms: a non-serializable capability escaped as a raw `TypeError`, and a lone surrogate
    (what `argv` yields for a non-UTF-8 byte via `surrogateescape`) escaped as a raw
    `UnicodeEncodeError` from SQLite's own TEXT binding -- a case the old
    `json.dumps(ensure_ascii=True)` path round-tripped. Both reached `cli.dispatch` as
    tracebacks. The original set is restored across `progress.py` (2 sites), `claims.py`, and
    `notices.py` (4 sites).
  - `[low]` `[patch]` `_empty_read_connection` was a second, divergent schema source: it applied
    `_SCHEMA_V1_SQL` directly and then stamped `user_version = SCHEMA_VERSION`, claiming to be
    current while pinned to v1. The first migration added after this story would have given an
    on-disk store the v2 shape and this one the v1 shape, both stamped v2 -- and every read of a
    not-yet-existing store (fresh repo, all three exporters, every `--list`-shaped command)
    takes this path. For a story titled "with migrations" that is the invariant most worth
    pinning. Split `_migrate_v1` into `_schema_v1` (structure) plus the import, added
    `_SCHEMA_MIGRATIONS`, and built this connection from it. Deliberately NOT routed through
    `_ensure_schema`: doing so made a pure read attempt the legacy JSON import, which is both
    pointless here and wrong under the very stat failure the finding above covers -- caught
    because it made that finding's own regression test stop discriminating.
  - `[low]` `[patch]` The three `..._is_imported_once` tests never asserted "once" -- each did a
    single read and checked the record count, so the idempotency the name sells and the
    `user_version` gating exists to buy was untested. The one existing idempotency test covers
    the NO-legacy case only, which is not the interaction that matters: the legacy file is
    deliberately left in place, so it is still there on every later open. Each now reads a
    second time with the file present.
  - `[low]` `[patch]` `scripts/export_progress_snapshot.py` shipped non-executable (`100644`)
    while both sibling exporters are `100755`, so `./scripts/export_progress_snapshot.py` failed
    where the other two work. Mode fixed in the index, not just the worktree.
  - `[low]` `[patch]` `notices.py`'s write-order comment became stale under the transaction: it
    argued the ordering's only risk was "an orphaned, harmless markdown file", true when a
    markdown-write failure was the sole trigger. `_write_markdown` is now a filesystem write
    INSIDE `db.transaction`, so the index rolls back on any later failure in the block and the
    orphan is reachable from more paths. Comment rewritten to state that, and why the trade
    still points the same way (an inert file beats a phantom index entry the CLI reports as
    live).

  Deferred (1): the corrupt-legacy-file blast radius -- one bad file now aborts the shared
  migration and blocks all three Moments, where pre-13.3 it blocked only its own. Filed as a new
  ledger entry rather than patched because it is not a spec deviation (the spec mandates one
  shared database AND mandates that an invalid legacy file fail migration), so re-deriving
  reproduces it; resolving it is a design decision, not a fix.

  Rejected as noise, spec-compliant-by-design, or disproportionate (9). Two prior-pass
  rejections were re-tested rather than inherited, since a rejection resting on a false fact
  hides the finding permanently -- both survived on verified premises this time. (1) Deleting
  `herald.db` re-imports the legacy snapshot and discards newer work: re-raised on the claim
  that this story's own runbooks now direct operators to do it. Re-read: they say *restore from
  a backup*, never *delete*, and a physical restore carries `user_version = 1`, so no re-import
  occurs -- the premise is weaker than claimed and the prior rejection stands. (The `.dump`
  variant of that same advice IS reachable, and was patched above.) (2) `web/package.json`
  invoking `python` rather than `python3`: correct for a pixi/conda env, where `python3` does
  not exist on Windows; re-verified `npm run build` clean this pass. The rest: `claims._write_all`
  remaining a `DELETE` + re-`INSERT` full-table rewrite instead of adopting `progress.upsert`'s
  row-level form (the spec says "preserve `claims.py`'s existing pattern exactly" -- compliance,
  not a defect); decorative `PRAGMA foreign_keys = ON` (previously rejected; consistent with the
  spec's explicit no-normalization stance); splitting schema SQL on a bare `;` (what the previous
  pass deliberately changed it TO; no semicolon exists in any statement); `compute_hours=0`
  exporting as `0.0` rather than `0` (a `REAL` column round-trip; dataclass equality holds and
  every JSON consumer reads them identically -- not a shape change); `_empty_read_connection` not
  applying `busy_timeout`/`foreign_keys` (an in-memory single-connection database, where neither
  can matter); a lock timeout surfacing through the "could not be opened" message (misleading
  wording, but the right error type and exit code, and the contention-widening it reflects is the
  spec's own one-shared-database mandate); and `notices.get_notice`'s two sequential reads not
  taking one snapshot (rejected twice before; the premise still holds).

### 2026-08-13 — Review pass (follow-up, second pass)
- intent_gap: 0
- bad_spec: 0
- patch: 11 (high 1, medium 5, low 5)
- defer: 0
- reject: 14
- addressed_findings:
  - `[high]` `[patch]` Every read path leaked raw `sqlite3.Error`. `progress.read_all`,
    `claims.read_all`/`read_one`, and `notices.get_notice`/`aliases_for`/`list_notices` ran their
    SQL with no `except sqlite3.Error`, while every writer wrapped its own -- so a table-level
    fault reached `cli.dispatch`, which catches only `HeraldError`, as an unhandled traceback
    instead of the "message plus exit code 1" the runbooks THIS STORY rewrote now promise.
    Reproduced: `DROP TABLE progress` out of band, then `progress.read_all` →
    `sqlite3.OperationalError: no such table: progress`. Fixed once at the seam --
    `db.connection()` translates `sqlite3.Error` raised inside its `with` block -- so all six
    sites are covered without repeating the guard. `db.transaction()`'s `conn.commit()` is now
    wrapped too, which was the same gap for `claims.create`/`progress.write_all` at COMMIT time.
  - `[medium]` `[patch]` `_set_wal_mode` retried EVERY `sqlite3.OperationalError` until
    `_BUSY_TIMEOUT_MS` expired, but only `SQLITE_BUSY` can ever be resolved by waiting. Measured:
    a read-only `.herald/herald.db` stalled every command a full **30.00s** before failing (its
    journal-mode switch is itself a write, so it fails identically on every attempt); a
    filesystem lacking WAL's shared-memory support behaves the same. Retry now gated on
    `_is_busy`; the same case fails in 0.00s. Regression test asserts the elapsed bound and fails
    (30.09s) against the old loop.
  - `[medium]` `[patch]` Every PURE READ created `.herald/herald.db`, its parent directory, and
    WAL's `-wal`/`-shm` sidecars -- a behavior change from the pre-13.3 modules (`read_all` on a
    missing file returned `[]` and touched nothing) and a visible one: the repo's `.gitignore`
    entry is the root-anchored `/.herald/` (deliberately, per its own comment, so a tracked
    `.herald/` fixture deeper in the tree keeps working), so any read run from a SUBDIRECTORY left
    an untracked `<subdir>/.herald/` in `git status`. Every `--list`-shaped command and all three
    exporters take this path. `connection()` now serves a store that does not exist yet -- and has
    no legacy JSON beside it to migrate -- from an empty in-memory database. The prior pass
    rejected this on a "gitignored, no data impact" premise; re-tested, that premise was false.
  - `[medium]` `[patch]` The tables were not `STRICT`, so SQLite's default type affinity accepted
    anything and the repeated "every other field is a plain, typed SQL column" claim (in
    `progress.read_all`'s docstring and two others) was simply untrue -- and the per-record type
    validation the pre-13.3 JSON reader ran on every read was gone with nothing replacing it.
    Reproduced: `UPDATE progress SET compute_hours='lots'` → `read_all` returned
    `Progress(compute_hours='lots')`, no error, deferring the failure to the first arithmetic
    downstream. All four tables are now `STRICT` (SQLite 3.53.4 here; needs ≥3.37), so that write
    is rejected at the source and the claim is true as written.
  - `[medium]` `[patch]` A caller passing a pre-13.3 DOCUMENTED default path -- e.g.
    `claims.read_all(Path(".herald/claims.json"))`, which every public function still accepts --
    made SQLite create the database at that name, after which the migration tried to `json.load`
    the file it had just created. Reproduced: permanent failure reported as
    `'utf-8' codec can't decode byte 0x95 ... claims file could not be read`, which points nowhere
    near the cause. `_import_legacy_v1` now skips any legacy candidate whose resolved path is the
    database itself. (The test suite had been working around this by renaming its fixtures.)
  - `[medium]` `[patch]` `notices.py` was left with NO real concurrency coverage. Its only such
    test races two authors of DIFFERENT components, but Story 13.3 rewrote the index write into a
    single-row `ON CONFLICT` upsert, so disjoint components cannot clobber each other whatever the
    locking does -- verified: it still passes against a `db.transaction` stripped of its `BEGIN
    IMMEDIATE`. DW-1-4-2's guarantee for this module was therefore unguarded. Added
    `test_two_concurrent_reauthors_of_the_same_component_do_not_lose_a_revision`, which races the
    genuine read-modify-write (the revisions list) with the delay injected into `_write_markdown`
    -- the only point inside the critical section between the read and the write. Verified
    discriminating: 2 revisions (one lost) against the stripped transaction, 3 against the real one.
  - `[low]` `[patch]` Both rewritten "different keys both land" concurrency tests carried
    docstrings claiming they "fail against a version that does not hold the transaction across its
    read-modify-write span". Neither does. Docstrings corrected to state the outcome they actually
    assert, and to name the test that does hold the guarantee in each module.
  - `[low]` `[patch]` `transaction()`'s `finally` did `stack.pop()` -- removing the TOP of the
    ambient stack rather than the entry that frame pushed -- so any out-of-LIFO exit would
    deregister a different path's still-open transaction and leave a closed connection registered
    as ambient for it. Latent (every call site nests with plain `with` today) and free to close:
    now removes its own entry by identity. Its `conn.rollback()` also ran unguarded inside
    `except BaseException`, so a rollback failure would replace the exception that caused the
    abort; now suppressed (closing the connection rolls back anyway).
  - `[low]` `[patch]` Four files still named the deleted JSON stores in USER-FACING text: `cli.py`
    (`--repo-root`'s `--help` said "repo root containing .herald/claims.json", plus three
    docstrings), `export_web_snapshot.py` (module docstring, function docstring, and its own
    `--help`), `export_notices_snapshot.py` (module docstring), and `web/README.md` (described
    `sync-progress` as copying `.herald/progress.json` and pointed at `scripts/sync-progress.mjs`,
    which this story deleted). The incomplete remainder of the sweep the four `docs/*.md` files
    already got -- `herald success --help` was contradicting the runbooks rewritten beside it.
  - `[low]` `[patch]` The `sqlite3.IntegrityError` branch the PREVIOUS review pass added to
    `_connect` (duplicate `(station, date)` in a legacy `progress.json` → "legacy data could not
    be imported" rather than "is not a valid database") shipped with no test. Added one asserting
    both the right message and the absence of the wrong one.
  - `[low]` `[patch]` This spec's own AC claimed "804 passed". The real count is 803 before this
    pass and 814 after. Root cause worth recording: `pixi run -e pyforge-herald
    pyforge-herald-test` resolves against the MAIN checkout, not the run worktree, so it silently
    reports the other tree's numbers -- it returned an identical "784 passed" both with this
    pass's changes applied and with them stashed. Every measurement in this pass was taken with
    `PYTHONPATH=src python -m pytest tests -q` inside the worktree; the AC now says so.

  Rejected as noise, spec-compliant-by-design, or disproportionate to fix for the risk (14).
  Three were re-tested rather than inherited, since a rejection resting on a false fact would hide
  the finding permanently -- one (the read-side database creation above) was overturned that way;
  these two survived on verified premises: the `HERALD_PROGRESS_PATH` override the deleted
  `sync-progress.mjs` really did honor (the prior pass's "no prior behavior to regress from" was
  wrong, but the variable named a `progress.json` that no longer exists as a concept, and a
  repo-wide grep finds zero remaining references, so there is nothing to preserve); and
  `progress.write_all`'s duplicate-`(station, date)` message (claimed to surface raw SQL --
  verified false, `_write_all_unlocked` wraps `sqlite3.Error` in `HeraldError`). The rest:
  `httpx2` reached through `claims` during migration allegedly falsifying "stdlib-only" (`httpx2`
  is a declared package dependency, and `export_web_snapshot.py` already imported it transitively
  pre-13.3 -- it fails only on a bare interpreter that was never a supported configuration);
  `python` vs `python3` in `web/package.json` (`python` is the correct choice for a pixi/conda
  env, where `python3` does not exist on Windows, and the failure is loud -- verified `npm run
  build` clean); `export_progress_snapshot.py`'s cwd-relative `--repo-root` default (matches
  `export_web_snapshot.py:60`'s existing precedent exactly); `author_notice`'s markdown write now
  rolling back the index while the file survives (real, but every fix trades it for the phantom
  index entry the code comment says was deliberately fixed -- narrow trigger, no data loss);
  splitting schema SQL on a bare `;` (what the previous pass deliberately changed it TO; no
  semicolon exists in any statement); `_migrate_v1` coupling the legacy import to schema creation
  (correct as designed -- the import IS a one-time v0→v1 concern); legacy JSON restored after
  migration being ignored (the "once, idempotently" requirement, as written); a hand-stamped
  negative `user_version`, and hardlink/case-differing path aliasing of the ambient key (both
  contrived; `.resolve()` covers symlinks); one shared database widening lock contention across
  the three Moments (the spec mandates one shared database); the inner post-`BEGIN IMMEDIATE`
  HALT re-check being untested (a genuine race, not reasonably testable); and
  `notices.get_notice`'s two sequential reads not taking one snapshot (previously rejected; the
  premise still holds).

### 2026-08-13 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 9 (high 1, medium 4, low 4)
- defer: 0
- reject: 12
- addressed_findings:
  - `[high]` `[patch]` `db.transaction()`'s `BEGIN IMMEDIATE` was unguarded -- a lock-timeout
    leaked the connection and raised a raw `sqlite3.OperationalError` instead of
    `errors.HeraldError`, contradicting the module's own "never raise 'database is locked'"
    design goal. Wrapped in try/except mirroring `_connect`'s own exception style; closes the
    connection and raises `HeraldError` on failure.
  - `[medium]` `[patch]` `notices.py`'s write paths (`author_notice`/`publish_notice`/
    `close_notice`/`archive_rename`) never wrapped `sqlite3.Error` into `HeraldError`, unlike
    `progress.py`/`claims.py`'s equivalent writers. Added the same wrapping for AD-6 parity.
  - `[medium]` `[patch]` Ambient-transaction stack was keyed on raw `str(db_path)` with no
    path normalization -- two spellings of the same physical file could self-deadlock and hit
    the leak above. Both `connection()`/`transaction()` now key on
    `str(Path(db_path).resolve())`.
  - `[medium]` `[patch]` Legacy-JSON validation branches ("non-list top-level document",
    "unknown field on an entry") lost all test coverage once they became reachable only through
    the one-time migration-import path -- a future regression there would go undetected. Added
    two new `test_db.py` cases exercising both branches via migration.
  - `[medium]` `[patch]` Rewritten backup/restore doc guidance (`cli-runbooks.md`,
    `automation-troubleshooting.md`, `operator-guide.md`) told operators to restore
    `.herald/herald.db` from backup with no mention of the WAL `-wal`/`-shm` sidecar files --
    incomplete/risky advice for a real restore. Added a clarifying note to each.
  - `[low]` `[patch]` `claims.read_all`'s docstring claimed "in `id` order"; the query is
    `ORDER BY rowid`. Corrected the docstring (query unchanged).
  - `[low]` `[patch]` `db.py`'s schema-SQL statement splitter depended on the literal `";\n\n"`
    separator, silently breaking if `_SCHEMA_V1_SQL` were ever reformatted. Changed to split on
    bare `";"`, stripping and skipping empty chunks.
  - `[low]` `[patch]` A duplicate `(station, date)` in a legacy `progress.json` being imported
    raised `sqlite3.IntegrityError`, reported as "is not a valid database" (factually wrong --
    it's a duplicate-key violation in imported data, not a corrupt file). Added an
    `except sqlite3.IntegrityError` clause in `_connect`, checked before the generic
    `DatabaseError` clause, with an accurate message.
  - `[low]` `[patch]` `claims._row_to_claim`/`notices._row_to_entry` parsed
    `evidence`/`edit_history`/`revisions` JSON columns without validating list-shape (unlike
    `progress._row_to_progress`), so a non-iterable malformed value could leak a raw `TypeError`
    instead of `HeraldError`. Added `isinstance(..., list)` guards matching `progress.py`'s
    existing pattern (defense-in-depth for `notices.py`, whose downstream `_entry_to_notice`
    already independently validated the same shape).

  Rejected as noise, spec-compliant-by-design, or disproportionate to fix for the risk (12):
  package.json/script cwd-resolution "fragility" (verified safe -- npm guarantees the scripts'
  cwd, and the math matches the deleted script's own precedent); legacy notice-redirect import
  skipping `archive_rename`'s referential-integrity checks (spec-compliant as literally written;
  self-healing "not found" error, no corruption); decorative `PRAGMA foreign_keys = ON`
  (harmless, consistent with the spec's explicit no-3NF-normalization stance); `claims.py` not
  adopting `progress.py`'s row-level `upsert` rewrite (spec explicitly says "preserve
  `claims.py`'s existing pattern exactly" -- this is compliance, not a defect); inconsistent
  "file"/"database" wording across three modules' error messages (cosmetic; fixing risks
  breaking existing string-matching tests for no functional gain); a pure DB read against a
  path with no legacy data eagerly provisions an empty `.herald/herald.db` (real but
  low-consequence -- gitignored, no data impact -- and a "clean" fix risks breaking the
  explicit legacy-import-must-trigger-on-any-command requirement); `notices.get_notice`'s two
  sequential reads aren't wrapped in one snapshot under WAL (a vanishingly narrow race with no
  data-loss consequence; "fixing" it would violate the module's own stated
  reads-never-block-writers invariant); legacy data re-importing if an operator manually
  deletes `herald.db` while leaving the legacy JSON files in place (requires a deliberate,
  unusual manual action; arguably reasonable recovery behavior, consistent with "legacy files
  left in place"); the legacy-import trigger keying on filename alone (contrived trigger,
  loud-error failure mode when it does misfire); `notices.list_notices` "missing" `ORDER BY`
  (verified FALSE -- the function already does `sorted(notices, key=lambda n: n.component)`
  before returning); `progress.write_all` now rejecting a same-`(station, date)` duplicate the
  old JSON array silently tolerated (already safely wrapped in `HeraldError`; arguably an
  improvement, not a regression); `HERALD_PROGRESS_PATH` env var no longer honored by the new
  exporter script (brand-new script, no prior behavior to regress from; docs already
  consistently describe the flag-based contract).


## Auto Run Result

Status: done (fourth follow-up review pass; no intent gaps, no spec repair loopback)

**Implemented change (cumulative, this story):** `progress.py`/`claims.py`/`notices.py` persist to
one shared stdlib-`sqlite3` database `.herald/herald.db` behind an unchanged public API, via a new
`db.py` owning connection setup (WAL + `busy_timeout`), a version-tracked migration runner, a
reentrant ambient-transaction context manager replacing `locking.locked()` for those three modules,
and a one-time import of any pre-existing legacy JSON stores. This pass changed no contract; it
closed four correctness holes in that machinery and finished the story's own rename sweep.

**Files changed in this pass:**
- `src/pyforge/herald/db.py` — legacy import skips a store whose table already holds rows;
  `connection()` translates the write paths' full exception set; `_has_legacy_data` uses
  `_is_definitely_absent` and accepts the names to check.
- `src/pyforge/herald/claims.py` — new `_write_transaction` helper wrapping the whole critical
  section, adopted by all four writers (`create`'s bespoke wrapper folded into it).
- `src/pyforge/herald/notices.py` — stale-markdown `unlink` deferred past the commit;
  `_require_existing_index` asks only about the notices legacy store.
- `src/pyforge/herald/locking.py`, `src/pyforge/herald/errors.py`, `tests/test_bridge.py`,
  `web/src/panels/{Progress,Success,Operations}Panel.jsx` — stale `.herald/*.json` references
  (text only, no behavior).
- `docs/automation-troubleshooting.md` — the `user_version` HALT and the legacy-import failure,
  framed as "not corruption" so the restore-from-backup advice is not misapplied.
- `tests/test_db.py` (+6), `tests/test_notices.py` (+1) — one regression test per fix.
- Both herald specs' `.memlog.md` — surface reconciliation for the newly-touched governed paths.

**Review findings:** 9 patched (high 1, medium 3, low 5), 1 deferred (`DW-FU-13-3-2`), 13 rejected,
0 intent gaps, 0 bad-spec loopbacks. Four prior-pass rejections were re-tested rather than
inherited; all four survived on verified premises.

**Verification:**
- `PYTHONPATH=src python -m pytest tests -q` inside the worktree: **827 passed, 2 skipped**
  (820 before this pass). `pixi run -e pyforge-herald pyforge-herald-test` is NOT used — it resolves
  against the main checkout and reports that tree's numbers.
- Each of the 7 new tests mutation-checked: reverting its fix fails it. M6's first mutation was
  itself faulty (it edited `create`, not `publish`) and was re-run against the right call site.
- Every patched finding reproduced before the fix and confirmed fixed after — including two through
  the real CLI (`herald success review` with a non-UTF-8 argv byte) and one end-to-end on the
  documented `sqlite3 .dump` restore path.
- `python scripts/spec_surface_reconcile.py` exits 0; `python -m pyforge.doctor.sources
  spec-surface` reports zero herald findings.
- All three exporters emit real data from a CLI-seeded database; `npm run build` clean with
  `sync-progress` invoking `export_progress_snapshot.py`.

**Residual risks:**
- `DW-FU-13-3-2` (deferred): a read-only `.herald/` fails every command, including reads that worked
  pre-13.3. Inherent to the spec-mandated WAL mode; needs a design decision.
- `DW-FU-13-3` (deferred by the third pass, still open): one corrupt legacy JSON file aborts the
  shared migration and so blocks all three Moments.
- `pixi.toml`'s `pyforge-herald-web-snapshot` task description still names `.herald/claims.json`.
  Left deliberately: `pixi.toml` is governed by `pyforge-marshal/spec-pyforge-core`, so the fix
  belongs to that Spec's surface.
- This pass changed error-translation breadth on the read seam (`db.connection` now catches
  `TypeError`/`ValueError`/`RecursionError` inside its `with` block). Intentional and matched to the
  write paths, but it means a caller's own programming error inside a read block now surfaces as
  `HeraldError` rather than its native type.
