---
title: "119.1: A worker runs a station verb from one closed table"
type: 'feature'
created: '2026-11-06'
status: 'done'
baseline_revision: 'a1a2c2a3aa'
review_loop_iteration: 1
followup_review_recommended: false
declared_low_risk: false
flag:
  key: pyforge.steward.start_tool_cli
  provider: openfeature-file
  default: {production: on, staging: on, dev: on}
  scope: global
  fallback: "the run ends FAILED with nothing started and the error says the kill switch is off"
  cleanup: "90 days after ON in every environment (Q4); the owning station files the removal story"
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-21-6-a-start-tool-with-no-work-behind-it-says-so.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md
  - docs/dreams/pyforge-unifying-strategy.md
deferred:
  - id: platform-worker-runs-no-station-cli
    summary: "The platform image runs no station CLI: it has no repo checkout, its Containerfile copies pyforge core, steward, mason and herald source only, and no pixi environment holds both Celery and all seven CLIs. Wired start tools work on a laptop checkout and fail honestly in the image until a worker image carries Celery, the CLIs and a checkout, on a chart Deployment consuming the station queues. Read from the Containerfile, not from a running image: django_warden_fabric.tasks and atlas's runner import pyforge.warden and pyforge.atlas, which that file does not copy, so check both when the image is built."
    location: _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-119-1-a-worker-runs-a-station-verb-from-one-closed-table.md:22
    severity: medium
  - id: revoke-leaves-a-running-verb
    summary: "revoke_subject signals the pool child, whose default SIGTERM ends it with no cleanup, so a revoked or worker-killed run leaves its verb's process group running. A timeout and the soft limit do stop the group. Read from the code, not run."
    location: _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-119-1-a-worker-runs-a-station-verb-from-one-closed-table.md:22
    severity: medium
  - id: a-cli-runs-as-the-worker-user
    summary: "The environment scrub stops inheritance only. A CLI runs as the worker's user, so it can read /proc/<ppid>/environ, HOME and a .env in the checkout, and start_build runs third-party build scripts for any pyforge:station:mason assertion. The worker image should run CLIs as another user, or in a sandbox."
    location: _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-119-1-a-worker-runs-a-station-verb-from-one-closed-table.md:22
    severity: medium
  - id: begin-attempt-races-the-claim
    summary: "begin_attempt's redelivered branch and heartbeat_held_run each read and rewrite RunState.result without a lock, and that blob holds the at-most-once marker. A write between their read and write could drop the marker. Unreachable today, because the visibility timeout exceeds any task; move the marker to its own column or lock those writes."
    location: _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-119-1-a-worker-runs-a-station-verb-from-one-closed-table.md:22
    severity: low
---

<intent-contract>

## Intent

**Problem:** Story 21.6 made seven runners fail honestly, and they still do no work. A worker that shells out to a station CLI sits outside `.claude/hooks/pre-shell.py`, so a caller-chosen verb could reach what an agent is refused at the shell. The worker's environment also holds database and signing secrets that no station CLI needs.

**Approach:** Operator rulings 2026-11-06: "All seven", laptop stack first, "Accept list". One module holds one closed table. A caller passes a target; the row fixes everything else. No shell, an allowlisted environment, a bounded output. `RunnerNotWiredError` stays the shape of an expected failure, so the worker records it and keeps the handle.

Ledger key: `119-1-a-worker-runs-a-station-verb-from-one-closed-table`. Type / Effort / Deps: feature / M / 21.6.

### Living CAP citations

- **`spec-pyforge-unifying-strategy` CAP-20** — a start tool does the work it names (canopy:FR-51, canopy:AD-24).

## Acceptance Criteria

- **AC1 — The table.** `django_pyforge/station_cli.py` holds one row per start tool: station, start tool, argv builder, target validator, result exit codes, pixi environment, the variables it passes, and whether it runs at most once. Its timeout comes from its queue's limit. Nothing else in the chrome or the portals names a CLI verb for a start tool.
- **AC2 — The run.** A row runs `<root>/.pixi/envs/<env>/bin/pyforge <station> ...` with no shell, in its own process group, from `STATION_CLI_ROOT`, under an environment built from an allowlist that excludes the worker's secrets. The result holds the argv, the exit code, a stderr tail, and a JSON report or capped stdout. A report keeps its smallest top-level values up to the cap and names the rest with their size.
- **AC3 — Honest failure.** An unset root, a missing executable, the kill switch off and a refused target each end the run `FAILED` with no subprocess started, and the message says which. An exit code outside the row's list, a non-zero result code with no JSON report, or a timeout ends the run `FAILED` with the code or the bound, and a timeout or the task's soft limit stops the verb's whole process group. Output the run store refuses stays text. Under eager settings `start_*` still returns its handle.
- **AC4 — The pin.** A test pins the whole table, every steward duty included, and fails on any row token in the session hook's reach: `--yes`, `--open-fix-prs`, `--bypass`, `--auto-approve`, `--transitive`, `submit`, `ship`, `publish`, `author`, `close`, `archive`. A second test asks the real hook about every row, with denied verbs as its control.
- **AC5 — The limits.** A row's run is published with its own soft and hard limits, above its verb's timeout, because the 60-second soft limit in the settings would stop `estate plan`.

## Boundaries & Constraints

- Atlas's runner does its work and does not change.
- The image is out of scope; the deferred row carries it.

**Never:**
- Never pass a caller's string through a shell, and never let a caller name a verb or a flag.
- Never hand a CLI the worker's whole environment.
- Never import `pyforge.<station>` from the runner; the CLI is the grammar.

</intent-contract>

## Binding

Parent: `spec-pyforge-unifying-strategy` CAP-20

- Closes: `DW-steward-21-6-2`, with Stories 119.2, 119.3 and 119.4.
- Epic: Epic 119.

## Verification

**Commands:**

- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: exit 0.
- `src/platform/tests/test_station_cli.py` — runs `pyforge.steward.start_tool_cli` in both states.

## Run record (2026-11-06)

Built by hand in `wire-start-tools-2026-11-06`, in one PR with Stories 119.1 to 119.4.

**Independent review.** A fresh reviewer read the diff against the Specs and found 5 high, 9 medium and 8 low. Each was checked against the code before it was acted on.

- High, all fixed: a timeout killed only the `pyforge` wrapper, so the station CLI ran on; a redelivered dispatch or build started a second time; only one steward duty was pinned; doctor's frozen exit 2 lost its report; warden's exit 2, an audit that did not finish, read `SUCCEEDED`, and its portal default could never audit.
- Medium, fixed: a dispatch's `PATH` missed `~/.local/bin`; a refusal reached an MCP caller as a bare error; the scrub dropped `PYFORGE_ENVIRONMENT`, `PYFORGE_FLAGS_PATH`, warden's feed caches and `SCRIBE_GRAPH_DSN`; a per-key cap dropped the substance of a report; live tests that could pass on nothing; limits untested at `apply_async`; the how-to's worker and install lines.
- Medium, deferred: a CLI runs as the worker's user, so the scrub stops inheritance and not a same-user read (`DW-steward-119-1-3`).
- Low, fixed: `recall_cli_argv` had no `--`; the tracked-recipe lookup had no timeout and refused `_libgcc_mutex`; NUL and NaN could strand a run; the long project slug; spec drift. Low, documented: `ci status` writes its snapshot. Low, deferred: `estate plan` ignores pixi's exit (`DW-steward-119-2`), the portal recall's environment (`DW-steward-119-2-2`). Low, no change: a doctor target that names a directory turns on read-only local checks, as its `--help` says.

**Second review.** A narrower pass over those fixes found 1 high and 5 medium. The high: `mason recipe build` exits 0 whatever the build did, so a failed build read `SUCCEEDED`, and the first live proof showed nothing about the build: `python-wget` had in fact failed, on a recipe that declares no `setuptools`. The row now reads `data.returncode`, and the proof builds `runs`. The medium, all fixed: a NUL in a failed verb's stderr, a lone surrogate or an overflowing float could stop the run store's write; the report cap did not count keys; the row's `passthrough`, `at_most_once` and the allowlist were unpinned; the redelivery test never set `redelivered`. Low, deferred: `begin_attempt` can race the at-most-once marker (`DW-steward-119-1-4`). Low, accepted: `communicate` holds a verb's whole output in worker memory before the cap.

**Mutants.** Six ran on a committed tree: no process-group kill, a steward duty reaching `estate refresh --transitive`, the gate removed, the whole environment inherited, the at-most-once check removed, the row's limits dropped. Twelve tests failed, one mutant or more for each. Live mode stayed off for that run, so no mutant verb ran for real. `test_a_soft_limit_stops_the_whole_verb` passed under the first mutant because the kill landed before its child started; it now waits for the child, and both process-group tests fail under that mutant.

**Live proof.** `STATION_CLI_LIVE_ROOT` named the primary checkout, through `platform-ci-local -- --test`: 1501 passed, 14 skipped, exit 0, and all nine tests in `test_station_cli_live.py` ran. Doctor, scribe, three steward duties and warden returned real reports. `mason recipe build` built `runs` to a `.conda` artifact, with `data.returncode` 0. Herald's own refusal came back, because the tree holds no notice. `start_loop` was refused with the shipped flag, and no real dispatch ran.
