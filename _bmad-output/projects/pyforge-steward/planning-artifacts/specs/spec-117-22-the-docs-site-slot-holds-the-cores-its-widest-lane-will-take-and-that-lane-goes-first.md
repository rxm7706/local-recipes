---
title: '117.22: The docs-site slot holds the cores its widest lane will take, and that lane goes first'
type: 'fix'
created: '2026-11-26'
status: 'done'
story: 117-22-the-docs-site-slot-holds-the-cores-its-widest-lane-will-take-and-that-lane-goes-first
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py'
  - 'src/shared/packages/pyforge-steward/tests/unit/test_preflight_critical_path.py'
  - 'docs/governance/preflight-budgets.toml'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Measured after herald Story 59.1, a full preflight of all 50 lanes took 421 s cold and 439 s warm, and `pyforge-herald-live-test` still ended it: it started 55 to 78 s in, behind the install and herald's package half, and ran 347 to 352 s on 2 workers, the cores the docs-site slot holds (Story 117.15), though its builds now run side by side and it takes 58 s alone on 16.

**Approach:** Hold, for the docs-site slot, the share its widest xdist lane is planned to take (its expected work over the target seconds of Story 117.15, at most half the machine), so the cores are free when the install before it ends. Rank the docs-site lanes after the install by expected seconds, so herald's live half goes before its package half.

Ledger key: `117-22-the-docs-site-slot-holds-the-cores-its-widest-lane-will-take-and-that-lane-goes-first`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 (the preflight and a PR's CI answer within a measured budget; realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Measure before and after with the harness that measured the baseline (same machine, same tree shape).
- Keep the install first in the chain, and the docs-site mutex as it is (Story 105.1).

**Never:**
- Never delete, skip or re-mark a test, lower a coverage floor, or weaken a lint, type or detector gate to gain time.
- Never hold more than half the machine for the slot.

## Acceptance Criteria

**Given** a full preflight whose docs-site slot holds 2 cores
**When** the slot holds the planned share of its widest xdist lane and the longest docs-site lane goes after the install
**Then** herald's live half starts on that share when the install ends and no longer ends the run

- **AC1 — The scheduler tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_preflight_critical_path.py -q
  ```

- **AC2 — A full preflight of all 50 lanes is faster than 421 s cold.** Expected: exit 0; `total_seconds` in the journal.

  ```bash
  PYFORGE_PREFLIGHT_SCOPE=full pixi run --frozen -e pyforge-guild pr-preflight
  ```

</intent-contract>

## Evidence (2026-11-26)

Cold run after Stories 117.19 to 117.21, 59.1 and 67.1: 421.3 s, `pyforge-herald-live-test` start 55 s, 352 s on 2 workers, 789 CPU-seconds; warm run 438.8 s, start 78 s (behind `pyforge-herald-test`, 20 to 78 s), 347 s on 2 workers.

## Review round (2026-11-26)

The first ordering put the longest docs-site lane ahead of the 'needed' rule, and `test_preflight_docs_site_mutex.py::test_the_install_starts_before_herald_s_suite` went red once in a full run: two 0.1 s lanes, and the shorter-by-noise one a pending lane needs went second. The 'needed' rule now comes first and the expected seconds break its ties (herald's gate needs both its halves, so the live half still goes first). The tracked budgets are measured again from the final runs (a governance act, made on the operator's "Approved").

## Result (2026-11-26)

A full preflight of all 50 lanes, measured with the harness that measured the baseline on the same machine: 312.5 s cold and 319.1 s warm, against 543.2 s and 532.1 s after PR #2405 (42% and 40% less); about 3,900 CPU-seconds against 6,100. `pyforge-herald-live-test` starts 13 to 17 s in on 6 workers and takes 105 to 118 s; the run is bound by the machine. The only red lanes are `detectors-ci` and `test-ci-meta`, reading the measurement's own uncommitted probe lines, as in the baseline.
