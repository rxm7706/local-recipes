---
title: 'Reliability of the CLI-Triggered Equivalents (Scaled Down From Automation Reliability)'
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

**Problem:** Epic 11's original Story 11.2 (`epics-with-stories.md` lines 949-959) specs
"webhook retries (exponential backoff, max 3), cron scheduling verified (Thursday 2300 UTC
fires), gate checks enforced (no claim for failed builds), operator alerts for failures" --
entirely infrastructure (a webhook receiver, a cron scheduler, an alerting channel) this
architecture does not have (see `docs/dreams/herald-moments-2-4-live-backend.md`). Building
tests for any of those four bullets would be testing fictional code paths.

**Approach:** Test the reliability properties that DO apply to a stateless, CLI-triggered
architecture, cross-cutting across the three Moments rather than duplicating any single
module's own tests:
1. The operator-role write gate (AD-16) enforced *consistently* across all SIX write
   commands that exist now that all three Moments are real (`progress --update`, `success
   publish`, `notice author`, `notice publish`, `notice close`, `notice archive`) -- one
   parametrized cross-cutting test, plus a structural source-count guard so a future write
   command cannot silently skip the gate.
2. Graceful (non-raising, non-crashing) CLI-level behavior when a Moment's local storage is
   completely absent (no `.herald/` directory at all) for the two read paths the story names
   explicitly: `herald success validate --all` and `herald notice list`.
3. Explicitly does NOT re-test Progress's own write-idempotency (upsert-not-duplicate on a
   second same-day `--update`) -- already covered end to end by Story 8.1's storage-level
   tests and Story 8.3's CLI-level test; duplicating it here would add no new coverage.

## Boundaries & Constraints

**Always:**
- The write-gate cross-cutting test enumerates the SIX known write commands by name (not
  derived from cli.py's source) as a fixed table (`_WRITE_COMMANDS`), each given the minimal
  `argv` needed to reach its handler's own gate check (every handler calls
  `auth.require_operator_role` before touching storage or its other args, confirmed by
  reading every handler in `cli.py` -- so a nonexistent claim id / component name in the
  argv never matters, the refusal happens first).
- A second, purely structural test counts `"auth.require_operator_role("` occurrences in
  `cli.py`'s source text and asserts it equals exactly 6 -- catching the case where a future
  Moment 5 write command is wired without the gate (the count wouldn't match, forcing a
  conscious update to this test in the same change).
- Both the "wrong role" (`HERALD_TOKEN=viewer:tok`) and "no auth context at all"
  (`HERALD_TOKEN` unset, no `~/.herald/config`) refusal shapes are tested for every one of
  the six commands, not just one.
- Before writing new tests, the module-level (`test_claims.py`/`test_notices.py`) coverage
  of "missing storage file" was actually checked, not assumed: `claims.revalidate_all` and
  `notices.list_notices` had no existing test for a *completely absent* file/index (only
  `read_all`/`_load_index_document`'s own missing-file cases were covered) -- gaps closed at
  the storage-module level too, not only the CLI level.

**Block If:** N/A -- purely local file-system + in-process CLI dispatch, no network
involved.

**Never:**
- No webhook retry/backoff test, no cron-scheduling test, no "gate checks enforced" test
  (there is no CI-integration concept of "a failed build" to gate on in this architecture --
  an operator who runs `herald success create` has implicitly already decided the ship
  qualifies, same boundary Story 9.2's own spec already drew), no operator-alert-delivery
  test -- all deferred to `docs/dreams/herald-moments-2-4-live-backend.md` in full.
- Does not modify `auth.py`, `progress.py`'s upsert logic, or any existing gate call site --
  this story is test-only, proving existing behavior, not changing it.

## I/O & Edge-Case Matrix

| Scenario | Input | Expected | Notes |
|---|---|---|---|
| Each of 6 write commands, wrong role | `HERALD_TOKEN=viewer:tok` | exit 1, `"unauthorized"` in stderr | parametrized over all six |
| Each of 6 write commands, no auth context | `HERALD_TOKEN` unset | exit 1, `"auth context missing"` in stderr | parametrized over all six |
| Gate call-site count | `cli.py` source | exactly 6 occurrences of `auth.require_operator_role(` | structural guard |
| `notice list` on empty repo | no `.herald/` at all | exit 0, `"no notices found"` / `[]` for `--json` | CLI-level; storage-level already covered by `test_list_notices_on_a_completely_empty_repo_is_empty` |
| `success validate --all` on empty repo | no `.herald/claims.json` at all | exit 0, `"revalidated evidence for 0 claim(s)"` | CLI-level; storage-level already covered by `test_revalidate_all_on_a_completely_missing_file_is_a_noop` |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/tests/test_reliability_epic11.py` -- create -- the
  cross-cutting write-gate table test, the structural gate-count guard, and the two
  empty-repo CLI-level tests.
- `src/shared/packages/pyforge-herald/tests/test_claims.py` -- edit --
  `test_revalidate_all_on_a_completely_missing_file_is_a_noop` (storage-level gap closed).
- `src/shared/packages/pyforge-herald/tests/test_notices.py` -- edit --
  `test_list_notices_on_a_completely_empty_repo_is_empty` and
  `test_get_notice_on_a_completely_empty_repo_raises_herald_error` (storage-level gaps
  closed).

## Design Notes

**Judgment call: a fixed table of six commands, not a source-derived list.** Deriving the
list of write commands automatically (e.g. by parsing `cli.py`'s AST for every function that
calls `auth.require_operator_role`) would make the behavioral test self-updating but also
self-blinding -- if a future write command's gate call were accidentally removed, an
auto-derived list would simply stop testing that command rather than flagging the gap. The
fixed table plus the separate structural count guard together give both properties: the
table proves each *named* command still behaves correctly, and the count guard proves
nothing was silently added or removed without a matching test update.

**Judgment call: "gate checks enforced (no claim for failed builds)" is out of scope, not
reinterpreted.** Unlike Stories 11.1/11.3/11.4, this AC bullet has no honest scaled-down
form at all -- there is no CI-reported "build failed" signal anywhere this CLI can observe.
Story 9.2's own spec already drew this exact boundary ("an operator who runs `herald success
create` has implicitly already decided the ship qualifies") when it dropped the original
`gates_passed` webhook-payload field entirely; this story does not re-litigate that,
only reaffirms it.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 736 passed, 2 skipped
  (whole-package total, immediately after this story landed).
- `ruff format --check` / `ruff check` -- clean.

**Manual checks:**
- `pytest tests/test_reliability_epic11.py tests/test_claims.py tests/test_notices.py -q`
  in isolation -- 84 passed.

## Spec Change Log

## Review Triage Log
