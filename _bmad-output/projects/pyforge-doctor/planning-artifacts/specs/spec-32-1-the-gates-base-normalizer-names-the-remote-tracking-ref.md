---
title: "32.1: The gate's base normalizer names the remote-tracking ref"
type: 'fix'
created: '2026-09-27'
status: 'in-progress'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/governance/spec-coverage-gate-independence/SPEC.md
  - docs/dreams/coverage-gate-independence.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `scripts/coverage_gates_ci.py` picks the touched modules the 80% floor judges from a diff of `<base>...HEAD`. Its `_normalize_base` turns a bare branch name (what `GITHUB_BASE_REF` holds) into the short `origin/<name>` and passes an `origin/<name>` (what the eight `pyforge-<station>-coverage-gate` pixi tasks pass) through. Git resolves a short name to a local branch or tag of that name before `refs/remotes/<name>`, so a local `origin/main` at HEAD empties the diff and the gate passes having judged nothing. Found by doctor Story 31.1's sweep (`DW-doctor-coverage-gates-ci-short-base-2026-09-27`).

**Approach:** `_normalize_base` names `refs/remotes/origin/<name>` for a bare branch name and for `origin/<name>`; a sha, a full ref (`refs/...`) and any revision expression (containing `~`, `^` or `@`) pass through. The default and the pixi tasks go through it, so no task argument changes. `coverage-gates.yml`'s `changes` job diffs `$BASE` itself to pick stations -- outside the driver -- so its pull_request `BASE` (both jobs, kept alike) names `refs/remotes/origin/${GITHUB_BASE_REF}`. Doctor is the mechanism Smith (Epic 24's relay shape); the gate stays outside every station.

Ledger key: `32-1-the-gates-base-normalizer-names-the-remote-tracking-ref`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-coverage-gate-independence` CAP-4 (the governance Spec's own; doctor's epics enumerate its stories); `pyforge-doctor:CAP-85`, `marshal:CAP-270`.

## Acceptance Criteria

- Given `refs/remotes/origin/main` at the fork point and a local branch or tag named `origin/main` at HEAD When the driver diffs on the default base, on `--base origin/main`, or on a bare `main` Then its path list is the one the remote-tracking ref gives
- Given a sha (a push event's `HEAD~1`), a full ref, or a revision expression When normalized Then it is returned unchanged
- Given no shadow When the driver runs Then every touched-module list is unchanged

## Boundaries & Constraints

**Always:** the gate stays outside every station (CAP-1); the push-event sha path keeps working.

**Never:** change a pixi task argument; move the driver.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| PR (`GITHUB_BASE_REF=main`) | bare name | `refs/remotes/origin/main` | a missing ref fails as before |
| pixi task | `origin/main` | `refs/remotes/origin/main` | — |
| push event | 40-hex sha | unchanged | — |
| explicit full ref / `HEAD~1` | any | unchanged | — |
| local branch or tag `origin/main` at HEAD | default | the remote-tracking ref's diff | — |

</intent-contract>

## Binding

Parent Spec capability: `docs/governance/spec-coverage-gate-independence/SPEC.md` CAP-4.
Dream: `docs/dreams/coverage-gate-independence.md` § Realization log → *2026-09-27 (late) — Proposed: the gate diffs against the remote-tracking ref*.
Deferred-work: closes `DW-doctor-coverage-gates-ci-short-base-2026-09-27`.
Ledger key: `32-1-the-gates-base-normalizer-names-the-remote-tracking-ref`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run -e pyforge-guild python -m pytest tests/scripts/test_coverage_gates_ci_driver.py -q` — expected: pass.
- `pixi run -e pyforge-doctor pyforge-doctor-coverage-gate` — expected: runs (the driver on its own base).

## Review Triage Log
