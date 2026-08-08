---
title: 'End-to-End Integration Test Across All Three Real Moments (Scaled Down)'
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

**Problem:** Epic 11's original Story 11.1 (`epics-with-stories.md` lines 936-947) specs an
end-to-end scenario "PR merge -> progress created -> claim auto-extracted -> claim
published -> success visible in web," implying a live webhook chain that fires
automatically across all three Moments. There is no webhook, no CI integration point, and
no live database anywhere in this repo's Herald architecture (see
`docs/dreams/herald-moments-2-4-live-backend.md`) -- Epics 8/9/10 already scaled every
record-creation path down to an operator-run CLI command.

**Approach:** One integration test (`tests/test_integration_epic11.py`) walking the exact
scaled-down operator workflow the three Moments actually support, end to end, in one test:
`herald progress warden --update` (Story 8.2/8.3) creates a progress record -> `herald
success create` + `herald success publish` (Story 9.2/9.3) creates and publishes a claim ->
`herald notice author --publish` (Story 10.2/10.4) publishes a notice -> each Moment's own
`--json` listing command is asserted to show it -> each Moment's static-snapshot-export
script (`web/scripts/sync-progress.mjs`, `scripts/export_web_snapshot.py`'s
`export_success_snapshot`, `scripts/export_notices_snapshot.py`) is run against the same
local data and asserted to produce correct, non-empty JSON. "CLI + web + automation
coordinated" (the AC's own wording) is satisfied honestly: "automation" here means these
three export scripts, the only automation this architecture actually has -- not a live
pipeline.

## Boundaries & Constraints

**Always:**
- The test exercises real storage end to end -- no CLI subcommand is mocked; only
  `evidence.validate_for_publish`/`validate_link` (HTTP calls the package's `deny_network`
  autouse fixture would otherwise block) and `auth.confirm` (the `Continue? [Y/n]`
  interactive prompt) are stubbed, exactly as every other write-path CLI test in this
  package already stubs them.
- One shared `tmp_path` acts as the repo root for all three Moments (`monkeypatch.chdir`
  for `progress`/`notice`, which resolve against `Path.cwd()`; `--repo-root` explicitly for
  `success`) -- proving the three Moments' local storage genuinely coexists under one
  `.herald/` tree, the same way a real operator's repo checkout would hold it.
- `sync-progress.mjs` is run as a real `node` subprocess (no stub) -- it does no network I/O
  of its own (local `fs` reads/writes only), so nothing here needs `deny_network`'s
  carve-out. `export_web_snapshot.py`'s `export_success_snapshot` and
  `export_notices_snapshot.py`'s `export_snapshot` are called directly as Python functions
  (mirrors `test_export_web_snapshot.py`'s own `importlib`-by-path loader, since these
  scripts live outside the `pyforge.herald` package).
- `sync-progress.mjs`'s write destination (`web/public/progress.json`) is fixed relative to
  its own script location, not overridable -- the test writes there for real (harmless:
  `web/public/*.json` is gitignored generated data per `web/.gitignore`) and cleans the file
  up in an autouse fixture's teardown, rather than leaving a stray artifact for the next
  test run.

**Block If:** N/A -- no live network reachable in this suite; nothing here calls out except
the local `node` subprocess.

**Never:**
- No mocked `cli.main` calls -- every step really writes to and reads from `tmp_path`'s
  local storage; a test that stubbed the storage layer would prove nothing about the three
  Moments actually working together.
- No assertion on web-tab *rendering* -- this story proves the export scripts produce
  correct JSON, not that a browser renders it (no browser in this suite; Story 11.4's spec
  documents that boundary explicitly for the performance AC's parallel claim).

## I/O & Edge-Case Matrix

| Scenario | Input | Expected | Notes |
|---|---|---|---|
| Progress write then list | `progress warden --update` then `progress --json` | one NDJSON record, `station == "warden"` | |
| Success create then publish then list | `success create` -> `success publish --thesis` -> `success --json list` | one NDJSON record, `status == "published"` | |
| Notice author --publish then list | `notice author --publish` -> `notice --json list` | one JSON-array entry, `status == "published"` | |
| sync-progress.mjs against real data | `.herald/progress.json` with one record | `web/public/progress.json` round-trips the same station | real `node` subprocess |
| export_success_snapshot against real data | `.herald/claims.json` with one published claim | `success.json` contains that claim's id | |
| export_notices_snapshot against real data | `.herald/notices-index.json` with one published notice | `notices.json` contains that component, count == 1 | |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/tests/test_integration_epic11.py` -- create -- the one
  end-to-end test (`test_all_three_moments_end_to_end`) plus its fixtures
  (`_operator_and_stubbed_validation`, `_isolate_cwd`, `_cleanup_web_public`).

## Design Notes

**Judgment call: one test function, not a suite of smaller ones.** Splitting each Moment's
"create -> verify" step into its own test would lose the thing this story actually needs to
prove -- that the *sequence* works end to end against one shared repo root, mirroring a real
operator's session. Each individual Moment's own create/publish/list behavior is already
covered exhaustively by its own Epic's test files (`test_cli_progress.py`,
`test_cli_success.py`, `test_cli_notice_epic10.py`); this story is deliberately the
integration layer on top, not a duplicate of any of them.

**Judgment call: real `node` subprocess for `sync-progress.mjs`, not a Python re-
implementation of its logic.** The script's whole value is proving the *actual* build-time
tool works against real CLI-written data -- re-implementing its JSON-copy logic in Python
would test a parallel implementation, not the one operators actually run via `npm run
sync-progress`. `node` is confirmed available in the `pyforge-herald` pixi env (verified
before writing this test: `pixi run --frozen -e pyforge-herald node --version` succeeds).

**Judgment call: no override for `sync-progress.mjs`'s output path.** The script has no
`--out`/env override for its *destination* (only its *source* is overridable, via an
explicit arg or `HERALD_PROGRESS_PATH`) -- extending the script to support one purely to
make this test more hermetic would be scope creep on a script Story 8.4 already shipped and
this effort is not otherwise touching. Writing to the real (but gitignored, generated-data-
only) `web/public/progress.json` and cleaning it up in an autouse fixture is the pragmatic,
scoped choice.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 718 passed, 2 skipped
  (whole-package total, immediately after this story landed).
- `ruff format --check` / `ruff check` -- clean.

**Manual checks:**
- Ran the test in isolation (`pytest tests/test_integration_epic11.py -q`) -- passes; then
  confirmed `web/public/` no longer exists afterward (`git status --short web/` empty),
  proving the cleanup fixture ran.

## Spec Change Log

## Review Triage Log
