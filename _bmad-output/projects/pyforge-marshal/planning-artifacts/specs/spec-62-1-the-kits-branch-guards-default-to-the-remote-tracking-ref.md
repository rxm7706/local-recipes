---
title: "62.1: The kit's branch guards default to the remote-tracking ref"
type: 'fix'
created: '2026-09-27'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/SPEC.md
  - docs/dreams/pyforge-marshal.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `pyforge-testing-kit`'s `branch_diff_guard` — seeded by marshal, imported by every station's "this branch does not add X" meta tests — defaults its base to the short name `origin/main` in `diff_text_since`, `changed_paths_since`, `existed_at_ref`, `commits_since` and `unsanctioned_commits`. Git resolves a short name to a local branch or tag of that name before `refs/remotes/<name>`, so a local `origin/main` at HEAD makes each guard's diff empty and the guard passes having checked nothing. Found by doctor Story 31.1's review (`DW-marshal-testing-kit-short-origin-main-2026-09-27`).

**Approach:** the kit gains `ORIGIN_MAIN = "refs/remotes/origin/main"`, the five functions default to it, and one private normalizer reads an explicit `origin/<branch>` as `refs/remotes/origin/<branch>` (any other ref — a full ref, `HEAD`, a sha, a local branch name — passes through). The base-absent skip names the ref it looked for. No caller changes. The kit's surface is co-governed by `spec-pyforge-testing-charter` (its memlog records the reconcile); the capability is marshal's (the kit's seed station; the charter's Dream is archived).

Ledger key: `62-1-the-kits-branch-guards-default-to-the-remote-tracking-ref`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-272 (FR-218); CAP-270 (60.1), CAP-271 (61.1); `pyforge-doctor:CAP-85`.

## Acceptance Criteria

- Given `refs/remotes/origin/main` at the fork point and a local branch or tag named `origin/main` at HEAD When a guard runs on its default base Then it sees what the remote-tracking ref gives (the changed paths, the diff, the commits, whether a path existed at the base)
- Given the same shadow When a caller passes `base="origin/main"` explicitly Then the guard reads the remote-tracking ref as well
- Given no shadow When any guard runs Then its result is unchanged, and a caller's full ref, `HEAD`, sha or local branch name passes through
- Given no `refs/remotes/origin/main` When a guard runs Then it skips, naming what it looked for

## Boundaries & Constraints

**Always:** the kit stays a leaf (no station import); `pytest` is imported only on the skip path.

**Never:** change a caller; change what a guard returns when no shadow exists -- one carve-out: a local branch literally named `origin/<x>` is no longer reachable by that short name (the guard reads `refs/remotes/origin/<x>`); a caller that means it passes `refs/heads/origin/<x>`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| no shadow | ordinary checkout | identical results | — |
| local branch or tag `origin/main` at HEAD | default base | the remote-tracking ref's results | — |
| explicit `base="origin/main"` | same shadow | the remote-tracking ref's results | — |
| explicit full ref / `HEAD` / sha / local branch | any | passed through | — |
| no `refs/remotes/origin/main` | shallow or remote-less checkout | skip | the skip names the ref |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal` CAP-272 (FR-218).
Dream: `docs/dreams/pyforge-marshal.md` § Realization log → *2026-09-27 (late, cont.) — Proposed: the shared test kit's branch guards diff against the remote*.
Deferred-work: closes `DW-marshal-testing-kit-short-origin-main-2026-09-27`.
Ledger key: `62-1-the-kits-branch-guards-default-to-the-remote-tracking-ref`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run -e pyforge-testing-kit pyforge-testing-kit-test` — expected: pass.
- `pixi run -e pyforge-guild pyforge-station-tests` — expected: pass (every station suite imports the kit).

## Review Triage Log

- **Review 1 (2026-09-27, independent agent) — FAIL, then fixed:**
  - [fixed] MEDIUM: the charter memlog never recorded the kit's surface reconcile the Approach names -- appended; scoped stamp at landing.
  - [fixed] LOW: a local branch literally named `origin/<x>` stops being reachable by that short name -- stated as the one carve-out under **Never**.
  - [fixed] nit: the shadow test's `existed_at_ref(...) is False` also held for an unresolvable ref -- it now asserts `base.py` existed first.
  - [fixed] nit: the Verification command ran the kit suite in `pyforge-guild`, which lacks the kit's test deps -- now `pyforge-testing-kit-test`.
  - [deferred] LOW: the platform's deliberate copy of the guard reads the short `origin/main` -- steward's surface: `DW-steward-platform-diff-guard-short-origin-main-2026-09-27`.
- **Review 2 (2026-09-27, same agent, delta) — PASS:** every review-1 fix verified; no 62.1 finding remains.

