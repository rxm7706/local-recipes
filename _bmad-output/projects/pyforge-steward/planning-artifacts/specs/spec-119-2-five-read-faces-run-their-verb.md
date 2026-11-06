---
title: "119.2: Five read faces run their verb"
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
---

<intent-contract>

## Intent

**Problem:** `start_scan`, `start_notice`, `start_recall`, `start_duty` and `start_audit` fail honestly and do nothing, and their CLIs can answer read-only. Warden's portal audit, the one product caller, shows a failure for work its CLI can do.

**Approach:** Operator ruling 2026-11-06: "Accept list". Each face gets a row of Story 119.1's table and a validator, and its runner runs that row.

Ledger key: `119-2-five-read-faces-run-their-verb`. Type / Effort / Deps: feature / M / 119.1.

### Living CAP citations

- **`spec-pyforge-unifying-strategy` CAP-20** — a start tool does the work it names (canopy:FR-51, canopy:AD-24).

## Acceptance Criteria

- **AC1 — The rows.** doctor `diagnose --target <name> --json`; herald `notice get <id>`; scribe `recall -- <query>`; steward `ci status --json`, `estate plan --json` and `estate status`, chosen by a closed duty name; warden `scan <path> --format json`, with exit codes 0, 1 and 2 as results.
- **AC2 — The targets.** A doctor or herald target is one token. A scribe query is bounded text with no control characters, and it cannot be read as a flag. A steward target is one of the three duty names. A warden target resolves under the root, and a symlink out of it is refused.
- **AC3 — The proof.** On a laptop checkout each of the five tools, through the worker task, ends with the CLI's real output in `get_*`. Warden's portal page shows the real report.
- **AC4 — The record.** `_grammar_recall` raises when the exit code is not 0, so a failed recall reads as a failure. `DW-scribe-5-2` and `DW-steward-21-6-5` close.

## Boundaries & Constraints

**Never:**
- Never add `--open-fix-prs`, `--bypass`, `--fix-prs-dry-run` or `--write`-shaped options to a row.
- Never give steward a row outside the three read verbs.

</intent-contract>

## Binding

Parent: `spec-pyforge-unifying-strategy` CAP-20

- Closes: `DW-scribe-5-2`, `DW-steward-21-6-5`.
- Epic: Epic 119.

## Verification

**Commands:**

- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: exit 0.
- `src/platform/tests/test_station_cli.py` — runs `pyforge.steward.start_tool_cli` in both states.

