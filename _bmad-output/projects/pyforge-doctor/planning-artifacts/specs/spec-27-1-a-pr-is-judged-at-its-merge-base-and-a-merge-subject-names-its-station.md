---
title: '27.1: A PR is judged at its merge-base, and a merge subject names its station'
type: 'fix'
created: '2026-09-18'
status: 'done'
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
- `pixi run -e pyforge-guild ledger-regression-check` on a checkout whose `HEAD` is a stale story branch and whose `origin/main` carries the promoted row reports `ok` with `merge_base` in evidence.
- *(Corrected 2026-09-18 after the dispatched session's trace:)* the atlas 13-5 / 14-4 / 15-3 `landed-but-unpromoted` rows are NOT this story's — those merges are atlas's own bmad-loop-scoped subjects read with pre-rekey keys (`rekey-2026-09-17.md`: 13-5→12-5, 14-4→13-4, 15-3→14-3), which `gather_direction` cannot map because only `gather()` got rekey-awareness (Story 25.3). That is Story 27.2 (CAP-79); this story's `blocked` was the session refusing to bundle it, correctly.

## Auto Run Result

Status: done
Reconciled 2026-09-20: the `blocked` verdict below is the session's own record at halt time; the story was landed afterwards and the ledger row promoted to `done` by `5f1625f29c 2026-09-18 marshal: promote sprint-status ledger for 'pyforge-doctor' (1 key(s) -> done)` — that promotion is the ruling this record now reflects.
Blocking condition: implementation verification failed

**Implemented and verified (all pass):**
- `ledger.py::gather()` now compares `merge-base(base, head)` vs `head` when `base` ≠ `head`, carrying `merge_base`/`base_requested` in evidence; the same-commit push fallback is unchanged.
- `_project_merge_subject_template()` (added to both `ledger.py` and `marshal.py`) reads a station's own `merge_subject_template` from its tracked `marshal-policy.toml` as TOML, falling back to the legacy `"Merge {key} into main"` default — used by `marshal.py::gather_story_status` (Routes 2/3) and by `ledger.py::gather_direction`'s new templated-subject matching (scoped to fire only when a project declares its own distinct template, so unscoped stations keep exact pre-fix parity — verified live: `ledger-direction-check` reports the same 3 findings before and after for stations with no override).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`: 1722 passed, 1 skipped.
- `pixi run -e pyforge-guild ledger-regression-check --json`: reports `ok`, evidence carries `base_requested: "origin/main"`, `merge_base: "ed367a47d8fb4e2da2275f1f0504e5084840d7c2"`, `ledgers_compared: 8` — matches this story's first manual check exactly.
- All 5 I/O & Edge-Case Matrix rows are covered by passing fixture tests (12 new unit tests across `test_sources_ledger.py`, `test_sources_ledger_direction.py`, `test_sources_marshal_story_status.py`), including the row-3 fixture ("sibling's templated merge ... no atlas finding").

**Failing check:** the second manual check — `pixi run -e pyforge-guild ledger-direction-check` on today's `main` no longer lists atlas 13-5 / 14-4 / 15-3 — still fails after this fix, independently re-run and confirmed:

```
[ledger-direction] ledger-direction: fail -- pyforge-atlas/13-5: landed-but-unpromoted — merge history names this story, but the tracked ledger is not done
[ledger-direction] ledger-direction: fail -- pyforge-atlas/14-4: landed-but-unpromoted — merge history names this story, but the tracked ledger is not done
[ledger-direction] ledger-direction: fail -- pyforge-atlas/15-3: landed-but-unpromoted — merge history names this story, but the tracked ledger is not done
```

**Reason — this story's Approach does not reach this incident's real cause.** Traced independently in git history: atlas's 13-5/14-4/15-3 merges are `Merge bmad-loop/<run>/<key> into loop/pyforge-atlas (bmad-loop)` subjects, already correctly scoped by the pre-existing `_BMADLOOP_MERGE_SUBJECT_RE` match — not a cross-station templated-subject collision (atlas's own `marshal-policy.toml` declares no `merge_subject_template` at all; confirmed by reading the file). The real cause is `_bmad-output/projects/pyforge-atlas/planning-artifacts/rekey-2026-09-17.md`, which renamed `13-5→12-5`, `14-4→13-4`, `15-3→14-3` the day before: `gather_direction`'s `done_ids` reads the ledger's current (post-rekey) keys, so it can never match the historical merge subjects' pre-rekey keys. `gather()`'s own `_check()` already has rekey-map awareness for this exact continuity concern (Story 25.3 / spec-one-chain-per-station CAP-3(g)); `gather_direction` never received the equivalent treatment — a distinct, pre-existing gap, not something this story's Boundaries, Approach, or Surface name.

**Why not fixed here:** porting rekey-map awareness into `gather_direction` is a new capability, not a fix within this story's declared Approach ("attribute a templated merge subject to a station only when it renders from that station's own template") — and per this repo's Dream-first governance (operator ruling 2026-09-12), gap-closure work still requires its own Dream + Spec before implementation, with no exemption for a mechanically small fix. Bundling it here would also violate Surgical Changes (touch only what the task requires).

**Recommendation:** mint a follow-up Dream/Spec for `gather_direction` rekey-map awareness (mirroring `gather()`'s `_check()` pattern), OR correct this spec's second manual check (it encodes the epic's original — and, per this investigation, mistaken — root-cause attribution for the live atlas incident) before re-dispatching. The commits implementing this story's actual Approach are complete, tested, and left in place on this branch; only the story's `status` and this note are new.

## Status reconcile 2026-09-20

- Auto Run Result `Status: blocked` → `done` (see the reconcile line under it).
