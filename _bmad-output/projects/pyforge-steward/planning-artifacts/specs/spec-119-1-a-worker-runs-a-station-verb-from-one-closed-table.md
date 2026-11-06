---
title: "119.1: A worker runs a station verb from one closed table"
type: 'feature'
created: '2026-11-06'
status: 'in-progress'
baseline_revision: 'a1a2c2a3aa'
review_loop_iteration: 0
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

