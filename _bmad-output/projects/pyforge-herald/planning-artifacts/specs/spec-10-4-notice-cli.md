---
title: 'Notice CLI'
type: 'feature'
created: '2026-08-08'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** Epic 6 wired only `herald notice` (list placeholder) and `herald notice author
<name>` (write-gated stub) under the `notice` top-level subparser. Epic 10 needs the full
command family -- `author`/`publish`/`list`/`get`/`close`/`archive` -- consistent with the rest
of this CLI's conventions (global `--json`/`--date-range`/`--station` flags, `--help` text,
`dispatch()` as the sole `HeraldError` boundary).

**Approach:** every new subcommand is added under `notice`'s existing `notice_subparsers` group
and routed through `_route`'s existing `if args.command == "notice": ...` branch (extended with
one `if` per new `notice_command` value, `list` remaining the fallback for backward compatibility
with bare `herald notice`). Every handler's `operation` closure is handed to `dispatch()`
unchanged from every other subcommand in this file -- no parallel error-reporting path.

**Judgment call: `--json`/`--date-range`/`--station` stay on the `notice` parser (via
`parents=[global_flags]`), not duplicated on each subparser.** This matches `success`'s existing
pattern (`success --json publish claim-123`, flags before the subcommand token) rather than
inventing a second placement convention Epic 10 alone would use. `--category`/`--status` are new,
`list`-only flags (no other subcommand needs them) and are declared on the `list` subparser
itself, not the shared parent -- they are not part of the "every Moment subcommand gets these"
contract Story 6.2 established.

## Boundaries & Constraints

**Always:**
- `herald notice` (bare, no subcommand) and `herald notice list` are equivalent -- both call
  `_run_notice_list`, preserving Epic 6's `test_notice_list_read_only_never_checks_auth` shape
  (`cli.main(["notice"]) == 0`, no auth check).
- `herald notice list`/`herald notice get` never call `auth` at all -- reads are public per
  AD-16, same boundary every prior read subcommand in this file honors.
- `herald notice author`/`publish`/`close`/`archive` all call `auth.require_operator_role` as the
  first statement of their `operation` closure.
- Every subcommand's `--help` exits 0 and documents its own flags (Story 6.5's inline-help
  convention, unchanged).
- `--json` output is one JSON value per call (an array for `list`, an object for `get`) --
  mirrors `progress --json`'s single-object shape, never partial/streamed output.

**Block If:** N/A -- no spike gate.

**Never:**
- No new error-reporting path outside `dispatch()` -- a `HeraldError` from any notice subcommand
  (e.g. `notices.get_notice`'s "no notice found") surfaces through the exact same
  one-stderr-line/exit-code contract as `deck seed`'s.

## I/O & Edge-Case Matrix

| Command | Auth | Notes |
|---|---|---|
| `herald notice` / `herald notice list` | none | draft notices excluded by default |
| `herald notice list --category eol` | none | filters `type == "eol"` |
| `herald notice list --status draft` | none | shows only drafts (mirrors Success's draft/published split) |
| `herald notice list --status all` | none | every status |
| `herald notice get <component>` | none | follows a rename redirect; unknown component -> exit 1 |
| `herald notice author ...` | operator | Story 10.2 |
| `herald notice publish <component>` | operator | draft -> published |
| `herald notice close <component> [--reason ...]` | operator | published -> closed |
| `herald notice archive --rename OLD NEW` | operator | Story 10.3 |
| `herald notice --help` / any subcommand `--help` | none | exit 0, documents its flags |
| `herald notice bogus-subcommand` | none | argparse usage error, exit 2 |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` -- edit -- `notice`
  subparser tree (`list`/`author`/`publish`/`get`/`close`/`archive`), `_route`'s notice branch,
  `_run_notice_list`/`_run_notice_publish`/`_run_notice_get`/`_run_notice_close`/
  `_run_notice_archive`, `_notice_summary_line`/`_notice_to_json` helpers.
- `src/shared/packages/pyforge-herald/tests/test_cli_epic6.py` -- edit -- notice-author tests
  updated to the new flag shape; `test_notice_list_read_only_never_checks_auth` and the
  `--help`/usage-error tests unchanged (still pass against the extended parser).
- `src/shared/packages/pyforge-herald/tests/test_cli_notice_epic10.py` -- create -- full
  subcommand coverage: write-gate on every write path, the author/publish/close/list/get/archive
  round trip, category/status filtering, redirect-following via `get`.

## Design Notes

**Why keep `list` as a real subcommand *and* keep bare `notice` working, instead of requiring
`list`?** The task's own worked example enumerates `herald notice list` explicitly (parity with
`herald success`/`herald progress`'s own bare-command listing), but Epic 6 already shipped and
tested `herald notice` (no subcommand) as the listing entry point, and `test_cli_epic6.py`'s
`test_notice_list_read_only_never_checks_auth` asserts exactly that shape. Breaking it for no
functional gain would be an unforced regression; both forms routing to the identical handler
costs nothing and preserves both contracts.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 595 passed, 2 skipped.
- `ruff format --check` / `ruff check` -- clean.

## Spec Change Log

## Review Triage Log
