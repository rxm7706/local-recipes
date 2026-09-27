---
title: "63.1: The station-tests lane picks suites from the remote-tracking ref"
type: 'fix'
created: '2026-09-27'
status: 'in-progress'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md
  - docs/governance/spec-coverage-gate-independence/SPEC.md
  - docs/dreams/pyforge-marshal.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `.github/workflows/pyforge-station-tests.yml` — the conformance lane `spec-pyforge-core` CAP-8 made a PR gate — chooses which station suites run from `git diff "$BASE"...HEAD` with `BASE="origin/${GITHUB_BASE_REF}"`. Its checkout fetches tags (`fetch-depth: 0`), and git resolves a short name to `refs/tags/<n>` before `refs/remotes/<n>`, so a pushed tag named `origin/main` empties the selection and the PR runs no station suite. Found by doctor Story 32.1's review (`DW-marshal-station-tests-short-base-ref-2026-09-27`); `coverage-gates.yml`, which follows the "same rule, deliberately", already names the full ref.

**Approach:** the lane's pull_request `BASE` names `refs/remotes/origin/${GITHUB_BASE_REF}`. A new scripts-suite test (`tests/scripts/test_workflow_diff_bases_name_full_refs.py`, stdlib only) scans every workflow under `.github/workflows/` and fails on any line that builds a base from a short `origin/${…}` — a GitHub expression or a shell variable — so the shape cannot come back in this lane, the coverage gate or mason's four recipe workflows (`pyforge-mason:CAP-28`, fixed in the same change).

Ledger key: `63-1-the-station-tests-lane-picks-suites-from-the-remote-tracking-ref`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-core` CAP-10 (on CAP-8's lane); `coverage-gate-independence:CAP-4`; `pyforge-mason:CAP-28`.

## Acceptance Criteria

- Given a pull request When the station-tests lane's `changes` job picks suites Then it diffs from `refs/remotes/origin/${GITHUB_BASE_REF}`
- Given any workflow under `.github/workflows/` When the scripts suite runs Then a diff base built from a short `origin/${…}` fails the test, naming the file and line
- Given the pre-fix tree When the test runs Then it fails (on this lane and the four recipe workflows); after the fix it passes
- Given a push event When the lane runs Then its sha base is unchanged

## Boundaries & Constraints

**Always:** the lane runs the pixi tasks (CAP-8), never a hand-enumerated list; the test is stdlib only (it runs in `pyforge-ci`).

**Never:** change which suites a shared-surface change selects; flag a comment line.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| pull request | `GITHUB_BASE_REF=main` | `BASE=refs/remotes/origin/main` | a missing ref fails the diff as before |
| push | `HEAD~1` sha | unchanged | — |
| workflow line `origin/${{ github.base_ref }}` | any workflow | test fails, names file:line | — |
| workflow line `origin/${GITHUB_BASE_REF}` or `origin/$VAR` | any workflow | test fails | — |
| `refs/remotes/origin/${…}` | any workflow | passes | — |
| a commented-out line | any workflow | ignored | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-core` CAP-10.
Dream: `docs/dreams/pyforge-marshal.md` § Realization log → *2026-09-27 (night) — Proposed: the station-tests lane picks suites from the remote-tracking ref*.
Deferred-work: closes `DW-marshal-station-tests-short-base-ref-2026-09-27`.
Ledger key: `63-1-the-station-tests-lane-picks-suites-from-the-remote-tracking-ref`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass.
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0.

## Review Triage Log

- **Review 1 (2026-09-27, independent agent) — FAIL (on 70.1), then fixed:**
  - [fixed] nit: the scan missed a quoted variable (`origin/"$X"`), `format('origin/{0}', ...)` and a literal range
    (`origin/main...HEAD`), and flagged a trailing comment -- all four handled and pinned; the redundant
    `refs/remotes/` lookbehind dropped. It still finds exactly the five pre-fix lines on `origin/main`'s workflows.
