---
title: '27.1: A PR is judged at its merge-base, and a merge subject names its station'
type: 'fix'
created: '2026-09-18'
status: 'in-progress'
baseline_revision: 'ed367a47d8fb4e2da2275f1f0504e5084840d7c2'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `ledger-regression` on a PR compares the tracked ledgers at the tip of `origin/main` against `HEAD`, so once `marshal factory dispatch` merges a story unattended and promotes its row on `main` before the PR's checks run, the stale PR head "un-finishes" a row it never touched (herald PR #1465, 18:17Z: `done-key-regressed: pyforge-herald: 1 story key(s) moved out of done`). Separately `sources/marshal.py:87` hardcodes `Merge {key} into main`, so a sibling station's `Merge 13-5 into main` reads as atlas's 13.5 landed (`ledger-direction`: atlas 13-5/14-4/15-3 `landed-but-unpromoted` all day).

**Approach:** When `base` ≠ `head`, compare the ledgers at `merge-base(base, head)` vs `head` and carry `merge_base` / `base_requested` in evidence (the push-to-main first-parent fallback stays). Attribute a templated merge subject to a station only when it renders from that station's own `merge_subject_template`, read from `_bmad-output/projects/<slug>/planning-artifacts/marshal-policy.toml` as TOML (legacy default only when the policy declares none).

## Boundaries & Constraints

**Always:**
- The PR #1465 fixture reports `ok`; a branch that genuinely flips a `done` row still FAILs; the sibling-merge fixture reports no atlas `landed-but-unpromoted` row while `Merge pyforge-atlas/13-5 into main` still counts; the eight tracked ledgers' `done` rows keep their evidence under each station's current template.
- Evidence names `merge_base` and `base_requested` whenever a substitution happened; the exit-code domain `{0, 2, 130}` is untouched.

**Never:**
- Do not soften the 2026-09-14 ruling — `ledger-regression` stays the one blocking Doctor step in CI.
- Do not import `pyforge.marshal`; the policy file is read as TOML.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| stale PR head after unattended merge | branch `backlog`, `origin/main` promoted `done` | `ok` | n/a |
| genuine regression | branch flips `done` → `backlog` | FAIL `done-key-regressed` | n/a |
| sibling's templated merge | `main` carries `Merge 13-5 into main` from another station | no atlas finding | n/a |
| station's own scoped merge | `Merge pyforge-atlas/13-5 into main` | counts as landed | n/a |
| policy declares no template | station without `merge_subject_template` | legacy default honoured | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-doctor CAP-78`.
Surface: `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/ledger.py`; `.../sources/marshal.py`; `scripts/ledger_regression_check.py`; tests.
Ledger key: `27-1-a-pr-is-judged-at-its-merge-base-and-a-merge-subject-names-its-station`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-27-1-a-pr-is-judged-at-its-merge-base-and-a-merge-subject-names-its-station.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).

**Manual checks:**
- `pixi run -e pyforge-guild ledger-regression-check` on a checkout whose `HEAD` is a stale story branch and whose `origin/main` carries the promoted row reports `ok` with `merge_base` in evidence; `pixi run -e pyforge-guild ledger-direction-check` on today's `main` no longer lists atlas 13-5 / 14-4 / 15-3.
