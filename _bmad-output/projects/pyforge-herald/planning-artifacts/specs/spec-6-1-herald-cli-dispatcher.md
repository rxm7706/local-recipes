---
title: 'Implement Herald CLI Dispatcher'
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

**Problem:** Epic 6 (renumbered today from a satellite "Herald Moments 2-4" chain into this
tracked ledger, per today's reconciliation) needs a single `herald` entry point that routes to
`progress`/`success`/`notice` subcommands, matching AD-11's "one CLI, subcommand routing" rule.
`cli.py` (Epic 1's `deck seed` skeleton) has no such subcommands yet, and its top-level
`command` subparsers group is `required=True` -- a bare `herald` currently exits 2 via argparse's
own usage error, not the 1 this story's AC calls for.

**Approach:** Extend the existing argparse skeleton (not a Click/Typer rewrite -- the epics
doc's own implementation notes suggested Click/Typer, but this repo's actual `cli.py` already
uses argparse, and Story 6.1's task explicitly directs following what's already there) with three
new subparsers (placeholder handlers only), a custom `_HeraldArgumentParser` subclass that
reworks argparse's own usage-error text to this CLI's wording, and a `main()` change: the
top-level `command` group becomes `required=False` so a bare invocation can be caught and
answered with exit 1 (Story 6.1's AC) instead of argparse's automatic exit 2. `deck`'s own nested
`deck_command` group stays `required=True`, unchanged -- Epic 1's contract there is untouched.

## Boundaries & Constraints

**Always:**
- `progress`/`success`/`notice` subcommands exist and route through `dispatch` (AD-6, unchanged
  from Epic 1) with a placeholder body ("not yet implemented") -- their real Moment logic is
  Epics 8/9/10.
- A bare `herald` (empty argv) exits 1, prints a usage message naming every subcommand.
- `herald --help`/`herald -h` exits 0 via argparse's own help action, unchanged.
- `herald unknown-command` exits 2, names the bad value, and lists valid subcommands -- via
  `_HeraldArgumentParser.error`'s reword of argparse's own `invalid choice` message, not a
  hand-rolled pre-check (argparse remains the sole source of truth for "is this a known
  subcommand").
- `dispatch`'s existing AD-6 contract (one stderr line, `errors.exit_code_for`'s mapped code) is
  reused unchanged for every new subcommand -- no parallel error-reporting path.
- `KeyboardInterrupt` during a subcommand's operation exits 130 (implementation notes'
  convention) -- `errors.py`'s map is untouched; 130 is not a `HeraldError` code.

**Block If:** N/A -- no spike, no live gate.

**Never:**
- No rewrite to Click/Typer -- the epics doc's implementation notes are advisory, not binding
  over the package's actual existing convention.
- No change to `deck`'s own nested subparsers' `required=True` contract.
- No real Moment logic (progress/claim/notice persistence, listing, filtering against a backend)
  -- out of scope for Epic 6 entirely (Epics 8/9/10).

## I/O & Edge-Case Matrix

| Scenario | Input | Expected | Exit |
|---|---|---|---|
| Bare invocation | `herald` | usage message naming every subcommand | 1 |
| Top-level help | `herald --help` | argparse-generated help | 0 |
| Known subcommand | `herald progress` | placeholder text | 0 |
| Unknown subcommand | `herald unknown-command` | "unknown command 'unknown-command'; valid subcommands: ..." | 2 |
| Nested unknown | `herald deck bogus` | "unknown command 'bogus'; valid subcommands: 'seed'" (not the top-level list) | 2 |
| Interrupt mid-operation | `KeyboardInterrupt` inside `operation` | none (process exits) | 130 |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` -- edit -- `_HeraldArgumentParser`
  (custom `error()` reword), `_reword_usage_error`, `TOP_LEVEL_COMMANDS`, `progress`/`success`/
  `notice` subparsers (bare form only; `success publish`/`notice author` land with Story 6.3),
  `main`'s `args.command is None` branch (exit 1), `_route`, `KeyboardInterrupt` handling (130).
- `src/shared/packages/pyforge-herald/tests/test_smoke.py` -- edit -- `test_bare_invocation_is_a_usage_error`
  updated from exit 2 to exit 1 (the contract this story changes).
- `src/shared/packages/pyforge-herald/tests/test_bridge.py` -- edit -- `_BRIDGE_CORE_MODULES` gains
  `auth`/`evidence` (Stories 6.3/6.4's new modules; noted here since the sweep-coverage test is
  shared infrastructure, not story-specific).
- `src/shared/packages/pyforge-herald/tests/test_cli_epic6.py` -- create -- the I/O matrix above,
  plus the nested-unknown-choice regression (see Review Triage Log).

## Design Notes

**Judgment call: `required=False` on the top-level group only, not `deck`'s nested group.** The
AC draws a real distinction ("no arguments" -> 1 vs. "invalid subcommand" -> 2) that only
`required=False` + a manual post-parse check can produce; argparse's own `required=True` usage
error is always exit 2, never 1. `deck`'s own nested group keeps `required=True` because no AC
asks for `herald deck`'s own bare-group behavior to change, and Story 1.6's docstring already
names that contract explicitly.

**Judgment call: argparse (not Click/Typer).** The epics doc's implementation notes suggest
"Python Click or Typer" and "reuse existing Herald v0.1.0 structure" in the same sentence --
those two are in tension, since the existing structure is argparse. Per this task's own
instruction to follow what `cli.py` already uses, argparse wins; the epics doc's tooling
suggestion is treated as stale/non-binding.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 424 passed, 2 skipped (whole-package
  total after all five Epic 6 stories land in this same pass; see each story's own count delta
  in its spec).
- `ruff format --check` / `ruff check` on every file this story touches -- clean.

**Manual checks:**
- `herald` (no args) -> exit 1, `python -c "from pyforge.herald.cli import main; print(main([]))"`.
- `herald deck bogus` -> exit 2, message names `'seed'` only, not `progress`/`success`/`notice`.

## Spec Change Log

## Review Triage Log

### 2026-08-07 -- Self-review pass (single agent, no independent second reviewer)

Implemented and reviewed by one session across all five Epic 6 stories in one continuous pass,
not a two-pass independent-reviewer loop. Findings below are from a deliberate adversarial re-read
after the whole-package suite was green, looking specifically at: exit-code consistency with
`errors.py`'s existing map, and whether any new usage-error text was subtly wrong.

- `[medium]` `[patch]` **The invalid-choice reword hardcoded the top-level `TOP_LEVEL_COMMANDS`
  list**, so `herald deck bogus` (a typo under `deck`'s own nested subparsers, which only ever has
  `seed`) would have reported "valid subcommands: deck, progress, success, notice" -- wrong at
  that nesting level and actively misleading (none of those four are valid there). Found while
  manually exercising `herald deck bogus` during this review pass, not by a pre-written test.
  Fixed: `_INVALID_CHOICE_RE` now captures argparse's own `(choose from ...)` clause and echoes it
  verbatim, so the message is correct at every nesting level this CLI has (today: top-level and
  `deck`) with no per-level wiring. New regression test:
  `test_unknown_deck_subcommand_exits_2_and_names_deck_choices_not_top_level`.
- `addressed_findings`: 1 (medium). No `intent_gap`, no `bad_spec`, no `defer`, no `reject`.

**Re-verification (2026-08-07, after the patch):** `pixi run --frozen -e pyforge-herald
pyforge-herald-test` -- 424 passed, 2 skipped; `ruff format --check`/`ruff check` clean on every
file this story (and the rest of Epic 6, landed in the same pass) touches.

### 2026-08-07 -- Adversarial review pass (Blind Hunter + Edge Case Hunter, no shared context)

- `[medium]` `[patch]` **`dispatch` never honored `--json` on its `HeraldError` catch branch.**
  `progress`/`success`/`notice`'s read-only handlers parse `--json` and render their success
  output as JSON, but a `HeraldError` raised inside those same `operation` closures (e.g. an
  invalid `--date-range`) always fell through to `dispatch`'s plain-text
  `"{TOOL_NAME}: {type}: {message}"` line -- a `--json` caller parsing stderr as structured output
  on failure would get a parse error instead of the real one. This exact bug class (an error path
  forgetting `--json`) had already been found and fixed twice this session in other stations
  (Steward's `ProvisionDuty`/`BudgetDuty`), so it was flagged as a demonstrated repeat-risk before
  this review started -- and a third instance turned up here. Fixed: `dispatch` gained a
  keyword-only `json_output: bool = False` parameter; the three read-only call sites
  (`_run_progress`/`_run_success_list`/`_run_notice_list`) now pass `json_output=args.json`, and
  the `HeraldError` branch renders `{"tool", "error", "message"}` as one JSON line on stderr when
  set. `deck seed`/`success publish`/`notice author` have no `--json` flag and never pass it, so
  their error rendering is unchanged. New regression test:
  `test_json_flag_renders_error_as_json_on_stderr` (`test_cli_epic6.py`).
- `addressed_findings`: 1 (medium). No `intent_gap`, no `bad_spec`, no `defer`, no `reject`.

**Re-verification (2026-08-07, after this patch):** `pixi run --frozen -e pyforge-herald
pyforge-herald-test` -- 427 passed, 2 skipped.

**Follow-up review recommendation:** none outstanding for this story; the dispatcher's error
rendering is now symmetric with its success-path JSON handling on every subcommand that offers
`--json`.
