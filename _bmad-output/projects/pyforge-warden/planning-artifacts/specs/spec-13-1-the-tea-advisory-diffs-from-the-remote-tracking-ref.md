---
title: "13.1: The TEA advisory diffs from the remote-tracking ref"
type: 'fix'
created: '2026-09-27'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - docs/dreams/pyforge-warden.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `pyforge.warden.tea_advisory`'s default runner passes `--base origin/main` to TEA's `tea-test-review`, whose CLI diffs `<base>...HEAD` (`cli/lib/changed-tests.js`, `cli/lib/diff-evidence.js` in the installed package). Git resolves a short name to a local branch or tag of that name before `refs/remotes/<n>`, so a stray `origin/main` at HEAD empties the changed-test set and the advisory reviews nothing. Found by doctor Story 31.1's review (`DW-warden-tea-advisory-short-base-2026-09-27`).

**Approach:** `_DEFAULT_BASE_REF = "refs/remotes/origin/main"`, and the comment that mirrors steward's `tea-test-review` pixi task names the new base (steward Story 70.1 changes the task in the same change). A unit test captures the argv the default runner builds, with `subprocess.run` replaced, and asserts `--base refs/remotes/origin/main`. TEA's own default is upstream's; it is not changed here.

Ledger key: `13-1-the-tea-advisory-diffs-from-the-remote-tracking-ref`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-warden` CAP-23; `pyforge-steward:CAP-158` (the pixi task's half).

## Acceptance Criteria

- Given the default runner When it builds the `tea-test-review` command line Then it passes `--base refs/remotes/origin/main`
- Given TEA absent, erroring, or the roster lacking `tea` When the advisory runs Then its fail-open and fail-closed behaviour is unchanged
- Given any run When the advisory reports Then it is a note, never a finding, a rung or the exit code

## Boundaries & Constraints

**Always:** advisory only.

**Never:** change TEA's upstream default; run a real agent-backed review in the suite.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| default runner | any target | argv carries `--base refs/remotes/origin/main` | — |
| binary absent | roster has `tea` | fail-open, no note | unchanged |
| roster lacks `tea` | — | `TeaRosterMissingError` | unchanged |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-warden` CAP-23.
Dream: `docs/dreams/pyforge-warden.md` § Realization log → *2026-09-27 (night) — Proposed: the TEA advisory reviews the diff from the remote-tracking ref*.
Deferred-work: closes `DW-warden-tea-advisory-short-base-2026-09-27` (with steward Story 70.1's task half).
Ledger key: `13-1-the-tea-advisory-diffs-from-the-remote-tracking-ref`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass.

## Review Triage Log

- **Review 1 (2026-09-27, independent agent) — FAIL (on 70.1), then fixed:**
  - [fixed] nit: `_default_runner`'s docstring said it is never exercised in the suite -- the real binary never is;
    the new test calls the function with `subprocess.run` replaced. Verified: TEA 1.27.2 rejects only an empty
    base or one starting with `-`, so the full ref is accepted.
- **Review 2 (2026-09-27, same agent, delta) — PASS.**
