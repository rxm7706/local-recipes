---
title: 'Implement Shared Argument Conventions'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** AD-11 promises "shared global flags: `--help`, `--json`, `--date-range
<start>..<end>`, `--station <name>`" across every Moment subcommand, but Story 6.1 lands
`progress`/`success`/`notice` with no flags at all. Without a shared definition, each future
Moment (Epics 8/9/10) would redeclare the same three flags independently, risking drift.

**Approach:** One `argparse.ArgumentParser(add_help=False)` "parent" template
(`_global_flags_parent`) defining `--json`/`-j`, `--date-range`, `--station`/`-s`, attached via
`parents=[...]` to `progress`, `success`, and `notice`. `--date-range` parsing is deliberately
**not** an argparse `type=` validator: the AC calls for exit code 1 on an invalid range, but an
argparse `type=` failure always exits 2. Parsing instead happens post-parse, inside each
handler's `dispatch`-wrapped `operation` -- reusing the exact AD-6 error path Story 1.4 already
built, rather than inventing a second one.

## Boundaries & Constraints

**Always:**
- `--json`/`-j` on `progress`/`success`/`notice`: valid JSON to stdout, no ANSI/color codes,
  exit 0.
- `--date-range <start>..<end>` (`YYYY-MM-DD` each): parses via `date.fromisoformat` (not
  `datetime.strptime`, which would construct a naive `datetime` -- flagged by this package's own
  `ruff` `DTZ007` rule and pointless anyway, since a date range has no time-of-day component).
  Valid range filters (today: only echoed back in the placeholder JSON payload, since no backend
  exists yet); exit 0.
- `--date-range` with an unparseable value: `errors.InvalidDateRangeError` ("Invalid date
  format: ...; expected <start>..<end> as YYYY-MM-DD..YYYY-MM-DD"), routed through `dispatch` ->
  exit 1 (the map's default fallback, no new entry needed).
- `--station`/`-s <name>`: passed through as a filter value.
- An unrecognized flag on any subcommand: argparse's own "unrecognized arguments" usage error,
  reworded by Story 6.1's `_HeraldArgumentParser.error` to `"unknown flag '--x'"`, exit 2.

**Block If:** N/A.

**Never:**
- No `type=` validator for `--date-range` (would exit 2, contradicting the AC's exit 1).
- No new HTTP/network surface -- this story is pure argument plumbing.

## I/O & Edge-Case Matrix

| Scenario | Input | Expected | Exit |
|---|---|---|---|
| JSON flag | `herald progress --json` | valid JSON, no ANSI | 0 |
| JSON short flag | `herald progress -j` | same | 0 |
| Valid date range | `herald progress --json --date-range 2026-08-01..2026-08-31` | `date_range: ["2026-08-01", "2026-08-31"]` | 0 |
| Invalid date range | `herald progress --date-range invalid..dates` | "Invalid date format" on stderr | 1 |
| Station filter | `herald progress --json --station warden` | `station: "warden"` | 0 |
| Station short flag | `herald progress --json -s warden` | same | 0 |
| Unknown flag | `herald progress --unknown-flag` | "unknown flag '--unknown-flag'" | 2 |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` -- edit -- `_global_flags_parent`,
  `_parse_date_range`, `_run_progress`/`_run_success_list`/`_run_notice_list`'s JSON/date-range/
  station handling.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/errors.py` -- edit --
  `InvalidDateRangeError` (falls through the existing exit-code map to 1; no new map entry).
- `src/shared/packages/pyforge-herald/tests/test_errors.py` -- edit -- parametrized coverage for
  the new error type's exit code.
- `src/shared/packages/pyforge-herald/tests/test_cli_epic6.py` -- create (shared with Stories
  6.1/6.3/6.5) -- the I/O matrix's flag rows.

## Design Notes

**Judgment call: flags live after the subcommand name, never before.** `--json` etc. are declared
on the `progress`/`success`/`notice` parsers themselves (via `parents=`), not on the top-level
parser -- so `herald --json progress` is not accepted, only `herald progress --json`. Every
AC example uses the latter form; the former was never asked for, and adding it would mean a
second, redundant flag definition on the top-level parser plus a merge-precedence question this
story has no cause to answer.

**Judgment call: the placeholder JSON payload echoes the parsed filters rather than a canned
constant.** Since no backend exists yet (Epics 8/9/10), `--station`/`--date-range`'s only
observable effect today is appearing in the JSON payload unchanged -- proof the parsing/plumbing
works end to end, without pretending to filter data that does not exist yet.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 424 passed, 2 skipped
  (whole-package total after all five Epic 6 stories).
- `ruff format --check` / `ruff check` -- clean.

**Manual checks:**
- `herald progress --json | python -m json.tool` -- valid JSON.
- `herald progress --date-range 2026-08-01..2026-08-31; echo $?` -- exit 0.
- `herald progress --date-range bogus; echo $?` -- exit 1.

## Spec Change Log

## Review Triage Log

### 2026-08-07 -- Self-review pass (single agent, no independent second reviewer)

- `[low]` `[patch]` The first implementation used `datetime.strptime(...).date()`, which `ruff`'s
  `DTZ007` rule flags (naive datetime construction). Since only a `date` is ever needed, switched
  to `date.fromisoformat` -- no naive-datetime construction at all, and one line shorter per
  field. No behavior change (both reject the same malformed inputs via `ValueError`); caught by
  `ruff check` during this story's own verification pass, not a second reviewer.
- `addressed_findings`: 1 (low). No `intent_gap`, no `bad_spec`, no `defer`, no `reject`.

**Re-verification (2026-08-07):** `pixi run --frozen -e pyforge-herald pyforge-herald-test` --
424 passed, 2 skipped; `ruff format --check`/`ruff check` clean.

### 2026-08-07 -- Adversarial review pass (Blind Hunter + Edge Case Hunter, no shared context)

- `[medium]` `[patch]` **`_parse_date_range` never checked `start <= end`.** Each half of
  `<start>..<end>` was validated independently via `date.fromisoformat`, so an inverted range
  like `2026-08-31..2026-08-01` parsed cleanly and silently returned a nonsensical
  start-after-end pair to every caller. Fixed: raises `InvalidDateRangeError` when `start > end`.
  New regression test: `test_date_range_inverted_start_after_end_exits_1`.
- `[medium]` `[patch]` **The three call sites (`_run_progress`/`_run_success_list`/
  `_run_notice_list`) used `if args.date_range else None`, a truthiness check.** An explicit
  `--date-range ""` (empty string) is falsy, so it silently matched the "no flag given" branch
  and skipped `_parse_date_range` entirely instead of raising on the malformed input. Fixed: all
  three now check `if args.date_range is not None else None`. New regression test:
  `test_date_range_empty_string_is_validated_not_treated_as_absent`.
- `addressed_findings`: 2 (medium). No `intent_gap`, no `bad_spec`, no `defer`, no `reject`.

**Re-verification (2026-08-07, after this patch):** `pixi run --frozen -e pyforge-herald
pyforge-herald-test` -- 427 passed, 2 skipped.

**Follow-up review recommendation:** none outstanding for this story; date-range validation now
covers both the inverted-range and falsy-empty-string edge cases alongside the existing
malformed-format coverage.
