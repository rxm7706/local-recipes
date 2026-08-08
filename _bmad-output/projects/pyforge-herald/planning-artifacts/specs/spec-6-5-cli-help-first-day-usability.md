---
title: 'CLI Help & First-Day Usability (Inline)'
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

**Problem:** FR-26 (named in `cli.py`'s own existing docstring, Story 1.1) requires every
subcommand's `--help` to be 100% argparse-generated. Story 6.1-6.4 add real subcommands and
flags, but without deliberate `help=`/`description=`/`epilog=` text on each, argparse's default
output would be terse to the point of not meeting this story's own "learn the CLI on day 1
without external documentation" bar.

**Approach:** Every parser this package now builds (`_build_parser`) carries a `description`, and
every Moment subparser (`progress`/`success`/`notice`) and their write sub-subcommands
(`success publish`, `notice author`) carry `help=` (for the parent's summary line) plus, for the
top-level and Moment parsers, an `epilog` of copy-paste-ready example invocations
(`argparse.RawDescriptionHelpFormatter` so the epilog's line breaks survive). Unclear-flag
handling reuses Story 6.1's `_HeraldArgumentParser.error` reword (already appends "See --help for
available options." to every usage error) rather than adding a second mechanism.

## Boundaries & Constraints

**Always:**
- `herald --help`: program description, usage line, every top-level subcommand with a one-line
  `help=`, an epilog of realistic example invocations. Exit 0.
- `herald progress --help`: subcommand intent (`description=`), usage pattern, every flag
  (`--json`/`-j`, `--date-range`, `--station`/`-s`) documented with its own `help=` text, an
  epilog of examples. Exit 0.
- `herald success --help` / `herald notice --help` / `herald success publish --help` /
  `herald notice author --help`: same standard -- `help=`/`description=`/positional `help=` on
  every parser this package builds, none left with argparse's bare default.
- `herald progress --unknown`: "unrecognized arguments: --unknown" reworded to
  `"unknown flag '--unknown'"`, plus "See --help for available options." on a second stderr
  line. Exit 2.

**Block If:** N/A.

**Never:**
- No hand-written help text bypassing argparse's own generation (FR-26's own constraint, already
  in force since Story 1.1) -- every word an operator sees under `--help` comes from an
  argparse `description=`/`help=`/`epilog=` kwarg, never a bespoke `print()` in a help path.

## I/O & Edge-Case Matrix

| Scenario | Input | Expected | Exit |
|---|---|---|---|
| Top-level help | `herald --help` | description, usage, subcommand list, epilog examples | 0 |
| Moment help | `herald progress --help` | intent, usage, `--json`/`--date-range`/`--station` documented, examples | 0 |
| Write sub-subcommand help | `herald success publish --help` | intent, `claim_id` positional documented | 0 |
| Unclear flag | `herald progress --unknown` | names the flag, suggests `--help` | 2 |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` -- edit -- `description`/
  `epilog`/`formatter_class=argparse.RawDescriptionHelpFormatter` on the top-level parser and on
  `progress`/`success`/`notice`; `help=` on every subparser and every `add_argument` call this
  story's scope touches (shared with Stories 6.1-6.3's own additions, since help text is
  authored alongside each flag/subcommand's own definition, not as a separate pass).
- `src/shared/packages/pyforge-herald/tests/test_cli_epic6.py` -- create (shared with
  6.1/6.2/6.3) -- `--help` exit-0 assertions per subcommand, the unclear-flag row.

## Design Notes

**Judgment call: help text is authored inline with each flag/subcommand's own definition, not as
a separate documentation pass.** Since Stories 6.1-6.4 already had to write `help=` strings to
get argparse to accept the calls at all (argparse does not require `help=`, but every
`add_parser`/`add_argument` call in this story's diff includes one), Story 6.5's actual
incremental work is narrower than the epics doc's stand-alone framing suggests: the epilogs
(example blocks) and the top-level `description`/`RawDescriptionHelpFormatter` wiring are the
concrete delta this story adds on top of what 6.1-6.4 already had to write to be usable at all.

**Judgment call: reuse Story 6.1's error reword rather than a second "unclear flag" mechanism.**
The AC's "names the problem, suggests --help" could have been built as its own check, but
`_HeraldArgumentParser.error` (Story 6.1) already reformats every usage error and already appends
the "See --help for available options." line unconditionally -- adding a second, parallel
mechanism for this one AC would duplicate that machinery for no behavioral gain.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 424 passed, 2 skipped
  (whole-package total after all five Epic 6 stories).
- `ruff format --check` / `ruff check` -- clean.

**Manual checks:**
- `herald --help`, `herald progress --help`, `herald success --help`, `herald notice --help`,
  `herald success publish --help`, `herald notice author --help` -- each exits 0 and prints a
  non-empty `description`/`help=`-derived body (visually spot-checked during this pass).
- `herald progress --unknown` -- exit 2, message contains both `--unknown` and `--help`.

## Spec Change Log

## Review Triage Log

### 2026-08-07 -- Self-review pass (single agent, no independent second reviewer)

- No patch-worthy findings specific to this story. Verified during this pass: every
  `add_parser`/`add_argument` call added across Epic 6 carries a `help=` string (grepped the
  diff for calls missing one -- none found); the top-level and three Moment parsers all set
  `formatter_class=argparse.RawDescriptionHelpFormatter` so their `epilog=` line breaks render as
  written rather than being re-wrapped by argparse's default formatter.
- `addressed_findings`: 0. No `intent_gap`, no `bad_spec`, no `defer`, no `reject`.

**Re-verification (2026-08-07):** `pixi run --frozen -e pyforge-herald pyforge-herald-test` --
424 passed, 2 skipped; `ruff format --check`/`ruff check` clean.
