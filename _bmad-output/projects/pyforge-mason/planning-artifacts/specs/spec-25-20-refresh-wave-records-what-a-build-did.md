---
title: "25.20: refresh-wave records what a build did"
type: 'fix'
created: '2026-11-05'
status: 'done'
baseline_revision: 'c09248dfb6'
review_loop_iteration: 1
followup_review_recommended: false
flag-exempt: recipe-build
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - .claude/skills/conda-forge-expert/scripts/refresh_wave.py
  - .claude/skills/conda-forge-expert/tests/unit/test_refresh_wave.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `refresh-wave` writes a record no build earned, in two directions. `_TEST_BLOCK_RE` never matches rattler-build's
own wording, `failed to setup test environment`, so a clean build with an unsolvable test environment stamps `failed`, not
G95's `build-clean-test-blocked`. And rattler-build exits 0 with `Starting build of 0 outputs` when every variant is skipped,
so a recipe that never built stamps `success`: Story 25.19's review found two `pyobjc-framework-*` recipes in that state.

**Approach:** Match rattler-build's own phrase, and treat 0 outputs as no build: report `skipped` and leave the recipe's record
as it is. The status vocabulary in `SKILL.md` stays; `skipped` is a report value only.

Ledger key: `25-20-refresh-wave-records-what-a-build-did`. Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **CAP-35** — the feedstock refresh campaign; its outcome set names G95 and host-blocked `not-attempted`, and this story makes the driver able to write them truthfully.

## Acceptance Criteria

- **AC1 — The test block.** `_classify_build` returns `build-clean-test-blocked` for output carrying `failed to setup test environment` when an artifact exists, and `failed` when none does.
- **AC2 — The skip.** A build that exits 0 with `Starting build of 0 outputs` reports `build.status: skipped`, writes no `cfe-local-build-*` field, and leaves the run's exit code at 0.
- **AC3 — The tests.** `tests/unit/test_refresh_wave.py` covers both, and each new test fails with its fix reverted.
- **AC4 — The retro.** The change lands in a `retro(cfe):` commit with its `CHANGELOG.md` entry, and `pixi run --frozen -e pyforge-mason pyforge-mason-test` exits 0.

## Boundaries & Constraints

- A CFE script change, so the full chain (operator ruling 2026-09-29).
- A fix: no new CAP, no flag (`spec-feature-flag-governance` Q1).

**Never:**
- Never add a status to the `cfe-local-build-status` vocabulary.
- Never write a `cfe-local-build-*` field by hand.

</intent-contract>

## Binding

Parent: `spec-pyforge-mason` CAP-35

- Found by: Story 25.19's independent review, 2026-11-05.
- Epic: Epic 25.

## Verification

**Commands:**

- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`).
- `pytest .claude/skills/conda-forge-expert/tests/unit/test_refresh_wave.py` in the `local-recipes` env — expected: pass.

## Spec Change Log

- 2026-11-05: minted and landed with Story 25.19, which needs the driver's records to be true.
