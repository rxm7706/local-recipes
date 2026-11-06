---
title: "119.3: start_build builds a tracked recipe on the builds pool"
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
---

<intent-contract>

## Intent

**Problem:** `start_build` does nothing. `queues.TOOL_ROUTES` names mason's `build` and `rebuild`, while the face runs `run_build`, so a wired build would land on the 300-second pool and die there.

**Approach:** Operator ruling 2026-11-06: "Accept list". A row runs `mason recipe build` for a flat slug tracked under `recipes/`, and the router names `run_build`.

Ledger key: `119-3-start-build-builds-a-tracked-recipe-on-the-builds-pool`. Type / Effort / Deps: feature / S / 119.1.

### Living CAP citations

- **`spec-pyforge-unifying-strategy` CAP-20** — a start tool does the work it names (canopy:FR-51, canopy:AD-24).

## Acceptance Criteria

- **AC1 — The row.** `mason recipe build recipes/<slug> --format json`, timeout below the builds time limit.
- **AC2 — The target.** A flat slug with no `/`, backslash, `..` or control byte, tracked under `recipes/` in the checkout. Anything else ends with nothing run.
- **AC3 — The queue.** `queue_for("mason", "run_build")` returns `builds`.
- **AC3a — The verdict.** `mason recipe build` exits 0 whatever the build did, so the row reads `data.returncode`: anything but 0 ends the run `FAILED` with the tail of the build log, which mason forwards to stderr.
- **AC4 — The proof.** On a laptop checkout one tracked recipe builds through the worker task, and the result reaches `get_build`.
- **AC5 — Once.** A run whose worker is lost is not started again: it ends `FAILED` and says so, because a second build would share `build_artifacts/` with a first that may still be running.

## Boundaries & Constraints

- Mason's own build timeout (3600 s) is the real bound, below the row's.

**Never:**
- Never add `submit`, `ship`, `update` or `--docker` to the row.
- Never run a recipe path a caller builds by hand; the slug is the whole input.

</intent-contract>

## Binding

Parent: `spec-pyforge-unifying-strategy` CAP-20

- Epic: Epic 119.

## Verification

**Commands:**

- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: exit 0.
- `src/platform/tests/test_station_cli.py` — runs `pyforge.steward.start_tool_cli` in both states.
- `STATION_CLI_LIVE_RECIPE=runs` with `src/platform/tests/test_station_cli_live.py` — one real build.

## Run record (2026-11-06)

Built, reviewed and proved with Story 119.1; see its run record.
