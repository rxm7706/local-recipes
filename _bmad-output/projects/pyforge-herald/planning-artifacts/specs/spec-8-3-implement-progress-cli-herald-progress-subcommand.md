---
title: 'Implement Progress CLI (`herald progress` subcommand)'
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

**Problem:** Epic 6 (Story 6.1) wired `herald progress` as a placeholder subcommand that always
prints "not yet implemented" -- real behavior was deferred to Epic 8. `epics-with-stories.md`'s
Story 8.3 (lines 452-490) specs three call shapes (`herald progress <station>`, `herald progress
<station> --update`, `herald progress --list [--station <name> --week recent|<N>]`) backed by
SQLAlchemy queries against the live database Epic 8's other stories assumed.

**Approach:** Replace `_run_progress`'s placeholder body with real routing over spec-8-1's
`progress.py` storage layer, reusing Epic 6's existing `--json`/`--date-range`/`--station` global
flags (`_global_flags_parent()`) rather than inventing new ones. A new optional positional
`station` argument (`station_arg`, to avoid colliding with the existing `--station`/`-s` global
filter flag's own `dest="station"`) selects between three modes: given with `--update`, it's
spec-8-2's write path; given alone, it's a single-station "latest record" read; absent, it
defaults to list mode (the AC's own "Default: all stations" framing) using the same
`--station`/`--date-range` flags `--list` explicitly also accepts. `--list` itself is accepted as
an explicit synonym for "no station given" per the AC's own `--list` flag, though the bare form
(no station, no `--list`) already does the same thing.

**Scoped-down deviation from the AC text:** the AC's `--week recent|<N>` flag is dropped --
`--date-range` (already shared, already validated, already tested) covers the same "which records"
filtering need without a second, overlapping time-window vocabulary; adding both would mean two
ways to ask the same question. "Available: warden, atlas, marshal, ..." (the unknown-station error)
reads its list from `progress.STATIONS` (spec-8-1), the same eight-station list the web dashboard's
`Sidebar.jsx` already hard-codes.

## Boundaries & Constraints

**Always:**
- `herald progress <station>` -- prints the latest record for `<station>` (table-ish plain text by
  default, one JSON object with `--json`); "no record yet" is a friendly message + exit 0, not an
  error (a known station with no data is a normal state, not a usage problem).
- `herald progress <station> --update` -- spec-8-2's write path (operator role required); prints
  `Progress updated for <station>` (or the full record as JSON with `--json`).
- `herald progress` (bare) or `herald progress --list` -- every record matching the optional
  `--station`/`--date-range` filters, newest-first; NDJSON (one JSON object per line) with
  `--json`, a one-line-per-record plain-text summary otherwise; "no records" is a friendly message
  + exit 0.
- Unknown station (in either the positional-argument show/update path, or the `--list --station`
  filter path) -- `errors.HeraldError`: `"Station '<x>' not found. Available: <list>. Use --list to
  see recorded stations."`, exit 1 (falls through `errors.exit_code_for`'s default map entry, same
  as every other bare `HeraldError` in this CLI).
- `--date-range` is validated (via the existing `_parse_date_range`) in list mode exactly like
  every other Moment subcommand's global flag -- an invalid range still raises
  `InvalidDateRangeError` before any listing happens.
- `herald progress --help` documents every flag (`--update`, `--list`, `--shipped`,
  `--compute-hours`, `--token-spend`, `--wall-clock-hours`, `--unblock-narrative`, plus the shared
  `--json`/`--date-range`/`--station`) with copy-paste examples in the epilog.
- Reads (show/list) never check auth (AD-16); only `--update` does (spec-8-2's own contract).

**Block If:** N/A -- no spike, no live gate.

**Never:**
- No `--week recent|<N>` flag -- dropped per the scoped-down deviation above.
- No change to `success`/`notice`'s own placeholder behavior -- both remain Epic 9/10's scope,
  untouched by this story.
- No new global flag -- `--update`/`--list`/`--shipped`/`--compute-hours`/`--token-spend`/
  `--wall-clock-hours`/`--unblock-narrative` are `progress`-specific arguments on its own
  subparser, not additions to `_global_flags_parent()`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `herald progress <station>`, no record | known station, nothing recorded | `No progress recorded for <station>.`, exit 0 | No error |
| `herald progress <station>`, no record, `--json` | -- | `{"station": "<x>", "record": null}`, exit 0 | No error |
| `herald progress <station>`, record exists | -- | full record as text or JSON, exit 0 | No error |
| `herald progress <station>`, unknown station | -- | -- | `HeraldError`, exit 1 |
| `herald progress <station> --update`, no operator role | -- | -- | `OperatorAuthorizationError`, exit 1 |
| `herald progress --list`, no records | -- | `No progress records found.`, exit 0 | No error |
| `herald progress --list --station <x>`, unknown station | -- | -- | `HeraldError`, exit 1 |
| `herald progress --list --json`, several records | -- | one JSON object per line (NDJSON), exit 0 | No error |
| `herald progress` (bare) | no station, no `--list` | same as `--list` with no filters | No error |
| `herald progress --date-range <bad>` | any mode reaching list | -- | `InvalidDateRangeError`, exit 1 |
| `herald progress --help` | -- | usage + all flags documented, exit 0 | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` -- edit -- the `progress`
  subparser gains the `station_arg` positional and `--update`/`--list`/`--shipped`/
  `--compute-hours`/`--token-spend`/`--wall-clock-hours`/`--unblock-narrative` flags;
  `_run_progress` rewritten to route across `_run_progress_show`/`_run_progress_update`/
  `_run_progress_list`; new helpers `_progress_path`, `_validate_station`,
  `_prompt_unblock_narrative`, `_format_progress_record`.
- `src/shared/packages/pyforge-herald/tests/test_cli_progress.py` -- create -- the full I/O matrix
  above, 27 tests (show/update/list × happy path, unknown station, empty state, JSON vs. plain
  text, auth gate, same-day replace, the interactive-prompt seam).
- `src/shared/packages/pyforge-herald/tests/test_cli_epic6.py` -- edit -- six tests that exercised
  the *shared* `--json`/`--date-range`/`--station` plumbing via the old `progress` placeholder
  (whose output shape no longer exists) moved onto `success` (still a genuine placeholder) so
  they keep testing the global-flag mechanics rather than progress's now-real domain behavior;
  `test_progress_with_no_flags_routes_and_exits_0` and `test_progress_read_only_never_checks_auth`
  updated in place for the new bare-list-mode output, both `chdir`-isolated to `tmp_path` so they
  never touch a real repo's `.herald/progress.json`.

## Design Notes

**Why the positional argument is `station_arg`, not `station`.** `_global_flags_parent()` already
defines `--station`/`-s` with `dest="station"` for the shared list-filter flag, reused by
`success`/`notice` too. A positional argument sharing that same `dest` would silently overwrite or
be overwritten depending on parse order -- an ambiguous, confusing shape. `station_arg` (surfaced
to the operator as `metavar="station"`, so `--help` still reads naturally) keeps the two
unambiguous: the positional selects single-station show/update mode; `--station` filters list mode.

**Why bare `herald progress` defaults to list mode rather than erroring.** The original placeholder
(Story 6.1) already made bare `herald progress` a valid, exit-0 call -- changing that to a usage
error would have been a silent regression for anyone who had already learned that invocation.
Defaulting to list mode (now genuinely listing, instead of printing a stub) preserves that
contract while making it real.

**Why `--list` exists at all, given bare `herald progress` already lists.** The AC names `--list`
explicitly as part of the CLI surface (`herald progress --list [--station <name> --week
recent|<N>]`), and an operator scripting against this CLI may prefer to state list-mode
unambiguously rather than rely on "no station given" being interpreted as list mode. Both forms are
tested identically in `test_cli_progress.py`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- full suite green (baseline (after
  spec-8-1) 571 passed, 2 skipped; **593 passed, 2 skipped** after spec-8-2 + spec-8-3's shared
  commit, +22 net new tests: 27 new in `test_cli_progress.py` minus 5 tests removed/consolidated
  from `test_cli_epic6.py`'s conversion).
- `ruff format --check` / `ruff check` from the package root -- `cli.py`, `test_cli_progress.py`,
  and the edited lines of `test_cli_epic6.py` are clean.
- `herald progress --help` / `herald progress warden --help`... -- exit 0, documents every flag.

## Spec Change Log

## Review Triage Log
