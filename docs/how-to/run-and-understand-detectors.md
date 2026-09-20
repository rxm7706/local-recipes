---
sources:
  - scripts/detectors.py
  - pixi.toml
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/verdict.py
  - docs/reference/judgement-vocabulary.md
verified: 2026-09-20
---

# How to run and understand Detectors

PyForge's detectors form the core of our CI pipeline (`detectors-ci`) and continuous governance. They are small, offline, deterministic checks that enforce invariants across the codebase.

This guide explains how to run the detector suite locally and how to interpret the results. For architecture rationale, see [The Detector Framework](../explanation/the-detector-framework.md).

## Running the Detectors

The detector registry is `scripts/detectors.py`. Run it through its pixi tasks in the `pyforge-guild` environment (the session default), which carries the `pyforge.doctor` sources the registry threads in:

```bash
pixi run -e pyforge-guild detectors          # every detector, repo + runtime scope
pixi run -e pyforge-guild detectors-ci       # the CI-safe subset (--scope repo)
pixi run -e pyforge-guild detectors -- --list   # what the registry discovered
pixi run -e pyforge-guild detectors -- --json   # machine-readable rows
```

### Filtering by Scope

Detectors are divided into two scopes:
1. `repo`: Runs anywhere, checks only tracked files. These are CI-safe.
2. `runtime`: Checks host state (e.g. `~/.bmad-loops`, `tmux` sessions, the gitignored Tier-3 sprint feeds). These cannot run in CI.

To run one scope explicitly:
```bash
pixi run -e pyforge-guild detectors -- --scope repo
pixi run -e pyforge-guild detectors -- --scope runtime
```

Each detector also has its own pixi task (`pixi task list -e pyforge-guild`, every `*-check` entry) — for example `pixi run -e pyforge-guild spec-surface-check` or `docs-map-hygiene-check`.

## Interpreting the Exit Codes

The detector registry adheres strictly to a three-tier exit code system:

| Exit Code | Status | Meaning |
|-----------|--------|---------|
| `0` | **Pass** | Every selected detector ran and passed. |
| `1` | **FINDINGS** | At least one detector reported a violation of an invariant. |
| `2` | **UNKNOWN** | At least one detector **could not run** (e.g., timed out, threw an exception, or a dependency like `pyforge.doctor` was unimportable), and no detector reported findings. |

> [!WARNING]
> **Exit code 2 is not a softer 0.** A detector that cannot run reports `unknown`, which is never green. The dashboard status strip will not claim "green" if it could not measure the metric.

> [!WARNING]
> **A single Doctor-sourced task uses a different exit domain.** `spec-surface-check`, `story-status-check`, `docs-map-hygiene-check` and the other `python -m pyforge.doctor.sources <name>` tasks project through `pyforge.doctor.verdict.exit_code_for`: any `fail` finding exits `2`, and a `warn` finding never changes the exit code (`0`). So `2` from the registry means "could not run" while `2` from one source means "failed" — read the finding rows, and always read the exit code directly, never through a pipe (a pipe reports the last command's status). The full domain table is in [`judgement-vocabulary.md`](../reference/judgement-vocabulary.md) § *Severity and exit codes*.

## Remediating Common Findings

If the suite exits with `1` (FINDINGS), read the output block at the end of the script's execution.

### Registry Gaps
A registry gap occurs if a script looks like a detector (`scripts/*_check.py` or `docs/dashboard/check_*.py`) but is not wired properly.
- **Fix:** Declare its scope at module level — `DETECTOR = {"scope": "repo"}` or `{"scope": "runtime"}` (`DETECTOR = None` opts a residual mutation-only script out) — and map the script to a pixi task in `pixi.toml` (e.g. `[feature.guild-tasks.tasks.my-detector-check]`).

### Spec Surface Drift (`spec-surface-check`)
This occurs when a governed file is added or modified, but the owning Spec's `.memlog.md` did not record the event.
- **Fix:** See [How to reconcile spec surface drift](reconcile-spec-surface.md).

### Chain Sprawl (`chain-sprawl-check`)
This occurs if you create a standalone Dream/Spec pair that violates the 1:1 "one chain per station" rule, without an explicit `fold-exemption`.
- **Fix:** Either fold the capability into an existing station's Spec, or add an exemption if it is truly cross-cutting (e.g., the testing kit). See [One-Chain Station Ops](one-chain-station-ops.md).

### Docs map hygiene (`docs-map-hygiene-check`)
A page under `docs/tutorials`, `docs/how-to`, `docs/reference` or `docs/explanation` is not linked from `docs/MAP.md` (warn), or the map links a page under `docs/` that does not exist (fail).
- **Fix:** Add the page to the right quadrant table in `docs/MAP.md`, or repoint/remove the dead link.
