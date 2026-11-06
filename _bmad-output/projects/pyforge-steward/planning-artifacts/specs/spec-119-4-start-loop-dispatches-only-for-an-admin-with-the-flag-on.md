---
title: "119.4: start_loop dispatches only for an admin with the flag on"
type: 'feature'
created: '2026-11-06'
status: 'in-progress'
baseline_revision: 'a1a2c2a3aa'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag:
  key: pyforge.steward.start_loop_dispatch
  provider: openfeature-file
  default: {production: off, staging: off, dev: off}
  scope: global
  fallback: "start_loop is refused or the run ends FAILED with nothing dispatched; every other start tool is unchanged"
  cleanup: "the operator decides when it turns on; 90 days after ON in every environment (Q4) the owning station files the removal story"
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-21-6-a-start-tool-with-no-work-behind-it-says-so.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md
  - docs/dreams/pyforge-unifying-strategy.md
deferred:
  - id: first-real-dispatch-through-start-loop
    summary: "start_loop has only reached a stand-in CLI: Story 119.4 forbids a real dispatch, because it spends. Before relying on it, the operator turns pyforge.steward.start_loop_dispatch on and runs one real dispatch. Dispatch's own steps can outlast the 270-second verb bound (readiness and git checkout each allow 600 s), and a timeout then ends the run with a worktree provisioned and no harness launched."
    location: _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-119-4-start-loop-dispatches-only-for-an-admin-with-the-flag-on.md:22
    severity: medium
---

<intent-contract>

## Intent

**Problem:** `marshal factory dispatch` launches an unattended agent that spends money and opens PRs. MCP start tools check a signed assertion and no role, and a worker subprocess sits outside the session hook, so a plain row would hand that verb to any caller with an assertion for marshal.

**Approach:** Operator ruling 2026-11-06: "Dispatch, gated". The row names a required role and a flag. `publish_start` refuses a caller without `pyforge:admin` before a run row exists, and refuses while the flag is off. The runner reads the flag again, because it can flip between start and run. The flag ships off in every environment.

Ledger key: `119-4-start-loop-dispatches-only-for-an-admin-with-the-flag-on`. Type / Effort / Deps: feature / M / 119.1.

### Living CAP citations

- **`spec-pyforge-unifying-strategy` CAP-20** — a start tool does the work it names (canopy:FR-51, canopy:AD-24).

## Acceptance Criteria

- **AC1 — The row.** `marshal factory dispatch <project> <story> --format json`, with `<project>/<story>` as the target, each part one token, and the long project form, `pyforge-<station>`.
- **AC2 — The role.** A caller without `pyforge:admin` is refused, no run row exists, and the refusal says the role is required, through the MCP transport as well as in the process.
- **AC3 — The flag.** With the flag off a start is refused the same way; if it flips off after a start, the run ends `FAILED` with nothing dispatched.
- **AC4 — The two states.** A test proves both flag states with a fake `pyforge`, so no real dispatch runs and no money is spent.
- **AC5 — Once.** A run whose worker is lost is not dispatched again: it ends `FAILED` and says so, because the first dispatch may be spending. The refusal to re-run is durable on the run row, not read from the broker.
- **AC6 — The harness.** A dispatch's `PATH` reaches `~/.local/bin`, where `claude` and `cursor-agent` live.

## Boundaries & Constraints

- Turning the flag on is the operator's act. No story here turns it on, and no real dispatch runs from this chain.

**Never:**
- Never add `spin`, `drain` or `challenge` to the table.
- Never check the role only in the worker: by then a run row exists.

</intent-contract>

## Binding

Parent: `spec-pyforge-unifying-strategy` CAP-20

- Epic: Epic 119.

## Verification

**Commands:**

- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: exit 0.
- `src/platform/tests/test_station_cli.py` — runs `pyforge.steward.start_loop_dispatch` in both states.

