---
title: 'Implement Progress Data Model & Local Storage'
type: 'feature'
created: '2026-08-08'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: true
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** `epics-with-stories.md`'s Epic 8 (lines 359-568) specs a `Progress` record schema
backed by PostgreSQL/SQLite via SQLAlchemy + Alembic migrations, with composite indexes and
database-level transactional writes. Nothing else in this repo's Herald architecture (a stateless
CLI plus a static web dashboard talking to Claude Design) has ever hosted a persistent database or
run migrations -- inventing one here, silently, would have been exactly the kind of unrequested
infrastructure this repo's "Simplicity First" principle rules out.

**Approach (scaled-down, 2026-08-08 scope decision):** the user was asked directly how to handle
the live-database/webhook mismatch and chose a scaled-down first pass: local JSON storage, no
server, every record created by hand via a CLI command (Story 8.3). This story is that storage
layer -- a new `progress.py` module holding a `Progress` dataclass (`id`, `station`, `date`,
`shipped_capabilities`, `compute_hours`, `token_spend`, `wall_clock_hours`, `unblock_narrative`,
`created_at`, `updated_at`) persisted as a single JSON array file, `.herald/progress.json`,
mirroring `state.py`'s established local-file convention exactly: explicit-`Path`-argument
functions (never assume a cwd), atomic writes (temp file + `os.replace`), and structural-
corruption-fails-loud reads (`errors.HeraldError` on malformed JSON, a non-array top level, or a
record missing/mistyping/carrying an unknown field). The full live-database shape is preserved as
a Dream at `docs/dreams/herald-moments-2-4-live-backend.md` for later, separate work; this
module's explicit-path, dataclass-in/dataclass-out shape is designed as the seam that Dream's
future database-backed implementation should be able to slot behind without changing Story 8.3's
CLI surface or Story 8.4's web-tab contract.

**Explicit scope boundary:** no SQLAlchemy, no Alembic, no Postgres/SQLite engine, no database-
level transactions, no composite index or `EXPLAIN PLAN` verification (there is no database to
index). "Concurrent writes" is addressed the same way `state.py` already addresses it for
`.herald/bridge-state.json`: atomic replacement is crash-safety, not concurrency-safety -- two
concurrent writers each load-then-replace the whole document, and the loser's update is silently
lost. No current caller writes concurrently.

## Boundaries & Constraints

**Always:**
- `progress.Progress` -- a frozen dataclass with exactly the ten fields named above,
  `shipped_capabilities` defaulting to `[]`, numeric fields defaulting to `0`/`0.0`,
  `unblock_narrative`/`created_at`/`updated_at` defaulting to `""`.
- `DEFAULT_PROGRESS_PATH = Path(".herald/progress.json")` -- relative, resolved against a real
  repo root by the caller (Story 8.3's `cli._progress_path`), exactly mirroring
  `state.DEFAULT_STATE_PATH`'s own convention.
- `read_all(progress_path) -> list[Progress]` -- every stored record, or `[]` when the file does
  not exist yet (missing file is "no data yet", never an error, matching `state._load_document`).
  Raises `errors.HeraldError` naming `progress_path` on malformed JSON, a non-array top level, a
  duplicated key within one record's object, or any record failing field validation (wrong type,
  a missing field, or an unrecognized field -- a hand-edit typo must fail loud, not be silently
  dropped on the next write).
- `write_all(progress_path, records)` -- atomic (temp file in the same directory, then
  `os.replace`), creates the parent directory if needed, sorts records by `(station, date)` before
  writing so the on-disk file is deterministic regardless of insertion order.
- `upsert(progress_path, *, station, date, shipped_capabilities, compute_hours, token_spend,
  wall_clock_hours, unblock_narrative) -> Progress` -- the `(station, date)` uniqueness key: a
  second call for the same station/day replaces the existing record in place (new `id` never
  minted, `created_at` preserved, `updated_at` bumped) rather than accumulating duplicates. This is
  Story 8.2's "Creates new Progress record for today (if not exists)" AC, reinterpreted for a
  keyless-database world -- `(station, date)` *is* the key.
- `latest_for_station(progress_path, station) -> Progress | None` -- the most recent record (by
  `date`) for one station, or `None` when there is none.
- `list_records(progress_path, *, station=None, date_range=None) -> list[Progress]` -- every
  record matching the optional filters, sorted newest-first by `(date, station)`.
- `progress.STATIONS` -- the same eight-station tuple `web/src/components/Sidebar.jsx` already
  hard-codes (`warden, atlas, marshal, mason, doctor, scribe, steward, herald`), used only to
  produce the CLI's "did you mean" error message (Story 8.3); this module itself never refuses an
  unrecognized station name.

**Block If:** N/A -- no spike, no live gate (this module never makes a network call).

**Never:**
- No SQLAlchemy/Alembic/database engine import anywhere in this module.
- No NDJSON on disk -- the file is one JSON array (documented choice: the whole file is small, one
  record per station per day across a handful of stations, so there is no streaming/append-only
  need NDJSON would justify, and a plain array round-trips through `json.load`/`json.dump` exactly
  like `state.py`'s single JSON object already does). Story 8.3's `--list --json` output is NDJSON
  on stdout -- that is a CLI *output* format decision, unrelated to this module's on-disk shape.
- No database-level transaction claim anywhere in code or docs -- "atomic" in this module means
  "crash-safe via `os.replace`," never "concurrency-safe."

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Missing file | `progress_path` does not exist | `read_all` returns `[]` | No error |
| Fresh `upsert` | no existing `(station, date)` entry | new record appended, `created_at == updated_at` | No error |
| Repeat `upsert`, same `(station, date)` | an entry already exists | record replaced in place; `id`/`created_at` preserved, `updated_at` bumped | No error |
| `upsert`, different date | same station, new date | a second record appended (not a replace) | No error |
| `latest_for_station`, no records | station has no entries | returns `None` | No error |
| `latest_for_station`, several dates | multiple entries for one station | the max-`date` entry returned | No error |
| `list_records`, station filter | `station="warden"` | only that station's records | No error |
| `list_records`, date-range filter | `(start, end)` tuple | only records with `start <= date <= end` | No error |
| Malformed JSON | hand-edited invalid JSON | -- | `HeraldError` naming `progress_path` |
| Non-array top level | `{"a": 1}` | -- | `HeraldError` |
| Record missing a field | a hand-edited entry short a key | -- | `HeraldError` naming the missing field |
| Record with an unknown field | a hand-edited entry with an extra key | -- | `HeraldError` naming the unknown field |
| `write_all`, no parent dir | nested path under `progress_path` | parent directory created | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/progress.py` -- create -- `Progress`
  dataclass, `DEFAULT_PROGRESS_PATH`, `STATIONS`, `read_all`, `write_all`, `upsert`,
  `latest_for_station`, `list_records`, `new_id`, `now_iso`.
- `src/shared/packages/pyforge-herald/tests/test_progress.py` -- create -- the I/O matrix above
  (20 tests).
- `src/shared/packages/pyforge-herald/tests/test_bridge.py` -- edit -- `progress` added to the
  bridge-core determinism-boundary sweep (`_BRIDGE_CORE_MODULES`): it is a plain local-JSON
  persistence module with no transport or argv-parsing concerns, same rationale already applied to
  `auth.py`/`evidence.py`/`watch.py`.

## Design Notes

**Why a JSON array, not NDJSON, on disk.** See the "Never" bullet above -- the choice is
documented there rather than duplicated here; the short version is scale (small file, no streaming
need) plus consistency with `state.py`'s existing single-document convention.

**Why `(station, date)` rather than a caller-supplied id is the uniqueness key.** The original
Epic 8 AC's "Creates new Progress record for today (if not exists)" only makes sense against some
notion of "today's record for this station" -- in a real database that would be a unique
constraint or an upsert-on-conflict clause; here it is `upsert`'s own linear scan-and-replace. This
keeps Story 8.3's `--update` command idempotent per day without the CLI having to track or pass an
id itself.

**Why this module joins the bridge-core determinism sweep.** `test_bridge.py`'s own static check
(`test_bridge_core_sweep_covers_every_non_excluded_package_module`) asserts every non-`cli`/
non-`transport` package module is accounted for in `_BRIDGE_CORE_MODULES` or explicitly excluded
with cause -- `progress.py` has no transport or argv-parsing concerns, so it joins the sweep
exactly like `auth.py`/`evidence.py`/`watch.py` did before it.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- full suite green (baseline **551
  passed, 2 skipped**; **571 passed, 2 skipped** after this story, +20 net new tests).
- `ruff format --check` / `ruff check` from the package root -- `progress.py`, `test_progress.py`,
  and the edited lines of `test_bridge.py` are clean (three pre-existing findings in
  `test_cli_watch.py`/`test_watch.py` remain, untouched by this story).

## Spec Change Log

## Review Triage Log
