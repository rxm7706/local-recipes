---
title: 'CLI-Triggered Progress Creation (scaled down from On-Ship Webhook & Weekly Cron)'
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

**Problem:** `epics-with-stories.md`'s Story 8.2 (lines 407-450) specs a Flask/FastAPI webhook
endpoint at `/api/herald/webhooks/on-ship` that CI calls on every merge to `main`, an async
extraction of `shipped_capabilities`/cost metrics from a bmad-loop journal, HMAC signature
verification, exponential-backoff retry, and an APScheduler/Celery weekly cron fallback that
aggregates the past 7 days of on-ship events per station. None of that infrastructure exists
anywhere in this repo -- there is no running Herald server for CI to call, no scheduler process,
and no bmad-loop journal format this module could parse today.

**Approach (scaled-down, 2026-08-08 scope decision, same decision as spec-8-1):** the webhook and
cron are replaced entirely by a CLI trigger an operator runs by hand after a ship: `herald
progress <station> --update` (Story 8.3's own subcommand implements the actual command surface;
this story is the *design decision and scope boundary* that shape rests on). The "extracted from
CI webhook payload / bmad-loop journal" idea survives in scaled-down form as explicit CLI flags an
operator fills in themselves: `--shipped <capability>` (repeatable), `--compute-hours`,
`--token-spend`, `--wall-clock-hours`. The "operator prompted to author the unblock narrative" AC
survives as a plain interactive text prompt (`cli._prompt_unblock_narrative`, reusing
`auth.confirm`'s injectable-`reader` seam) when `--unblock-narrative` is omitted, rather than the
original's draft-then-later-fill-in webhook flow. The one piece of the original AC this scaled-down
pass keeps *exactly*: AD-16 already named `herald progress --update` by name as a future
operator-gated write in `auth.py`'s own docstring, so `--update` calls
`auth.require_operator_role` before anything else runs, identically to `success publish`/`notice
author`.

**Explicit scope boundary:** no HTTP server, no webhook route, no HMAC signature verification, no
retry/backoff, no cron/scheduler of any kind, no async journal lookup. The live-webhook/cron shape
is preserved as a Dream at `docs/dreams/herald-moments-2-4-live-backend.md` for later, separate
work -- realizing it should only need to swap what *triggers* `progress.upsert` (a webhook handler
calling it instead of a CLI handler), not reshape the storage layer (spec-8-1) or the CLI/web-tab
contract (spec-8-3/8-4) an operator already learned.

## Boundaries & Constraints

**Always:**
- The sole path to creating or updating a `Progress` record is `herald progress <station>
  --update` (Story 8.3). There is no other entry point -- no HTTP route, no scheduled job, no
  second CLI command.
- `--update` requires the `operator` role (AD-16): `auth.require_operator_role(
  auth.resolve_auth_context(), action="herald progress --update")` runs before any other logic in
  `_run_progress_update`, mirroring `_run_success_publish`/`_run_notice_author`'s existing
  gate-first pattern exactly.
- Every field the original webhook payload would have carried is instead an explicit CLI flag:
  `--shipped` (repeatable; omitted means `[]`), `--compute-hours`/`--token-spend`/
  `--wall-clock-hours` (each optional; omitted means `0`/`0`/`0.0`), `--unblock-narrative`
  (optional; omitted triggers the interactive prompt).
- The record's `date` is always "today" (`datetime.now(UTC).date().isoformat()`) -- there is no
  `merged_at` payload field to read a date from; an operator running `--update` after a ship is
  recording that ship's date as today by construction.
- An unrecognized station name (checked against `progress.STATIONS`) is refused *after* the
  operator-role check but *before* any write, naming the problem and every known station -- the
  same "Station 'unknown' not found. Available: ..." shape Story 8.3's read path also uses.

**Block If:** N/A -- no spike, no live gate (this is local-only CLI behavior).

**Never:**
- No webhook route, no signature verification, no retry/backoff logic, no scheduler dependency
  (APScheduler, Celery, or the stdlib `schedule` package) anywhere in this package.
- No silent bypass of the operator-role gate for `--update` -- there is no "draft, unauthenticated,
  published later" path the way the original webhook AC's DRAFT-then-operator-fills-narrative flow
  implied; this scaled-down pass requires the operator to already be authenticated at the moment
  they run `--update`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| No operator role | `HERALD_TOKEN` unset or non-operator role | -- | `OperatorAuthorizationError`, exit 1 |
| Operator role, unknown station | `--update` on a station outside `progress.STATIONS` | -- | `HeraldError` naming the station + available list, exit 1 |
| Operator role, known station, all flags given | `--shipped`/`--compute-hours`/`--token-spend`/`--wall-clock-hours`/`--unblock-narrative` all supplied | record created/replaced for today with exactly those values | No error |
| Operator role, no optional flags | bare `--update` | record created with `[]`/`0`/`0`/`0.0`, narrative from the interactive prompt | No error |
| `--unblock-narrative` omitted | -- | `cli._prompt_unblock_narrative` called; a blank answer or `EOFError` records `""`, never aborts | No error |
| Second `--update`, same day | station/date already has a record | existing record replaced (spec-8-1's `upsert` semantics), not duplicated | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` -- edit -- `_run_progress_update`,
  `_prompt_unblock_narrative`, the `--update`/`--shipped`/`--compute-hours`/`--token-spend`/
  `--wall-clock-hours`/`--unblock-narrative` argparse flags on the `progress` subparser. (Landed in
  the same commit as spec-8-3's CLI dispatch/routing/show/list logic -- see that spec's own Code
  Map for the full file list; this story's own contribution is the `--update` write path and its
  auth gate specifically.)
- `src/shared/packages/pyforge-herald/tests/test_cli_progress.py` -- create -- the `--update`-
  specific rows of the I/O matrix above (operator-role refusal, unknown-station refusal, flag
  defaults, the interactive-prompt seam, same-day replace-not-append).

## Design Notes

**Why the interactive-narrative prompt reuses `auth.confirm`'s seam rather than inventing a new
one.** `auth.confirm(prompt, *, reader=input)` already established the "injectable reader so a
test never blocks on real stdin" pattern for exactly this kind of interactive CLI moment.
`_prompt_unblock_narrative` is free text, not a yes/no gate, so it cannot reuse `confirm` itself --
but it copies the same `reader=input` seam shape, tested the same way (`test_cli_progress.py`'s
`test_prompt_unblock_narrative_*` tests mirror `test_auth.py`'s `test_confirm_*` tests directly).

**Why `--update`'s auth check runs before the unknown-station check, not after.** Matches
`_run_success_publish`/`_run_notice_author`'s existing convention (auth is "literally the first
line of `operation`," per spec-6-3's own Intent) -- a non-operator caller learns they're
unauthorized before learning anything about which stations exist, which is the more conservative
information-disclosure order and costs nothing to keep consistent with the two write paths that
already existed.

**What was deliberately not attempted.** No attempt was made to simulate "async extraction" by,
say, shelling out to `git log` or parsing a PR title -- the epics doc's own "TBD by implementation"
language on the extraction source, combined with there being no bmad-loop journal format
documented anywhere in this repo, made an explicit-flags interface the only interpretation that
does not invent an undocumented parsing contract.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- full suite green (**593 passed, 2
  skipped** after spec-8-2 + spec-8-3 landed together; see spec-8-3 for the story-by-story test
  count).
- `herald progress warden --update --shipped 'Harness Policy' --compute-hours 3.5 --token-spend
  42000 --wall-clock-hours 6 --unblock-narrative none` with `HERALD_TOKEN=operator:tok` set --
  exit 0, `Progress updated for warden` printed, `.herald/progress.json` created.
- Same command with `HERALD_TOKEN=viewer:tok` -- exit 1, `unauthorized: operator role required`.

## Spec Change Log

## Review Triage Log
