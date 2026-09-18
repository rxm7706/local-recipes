---
title: '27.5: A bare-form merge is attributed by the paths its diff touches'
type: 'fix'
created: '2026-09-18'
status: 'in-review'
baseline_revision: '7536234005af17c5a7d1ec59419de01d5ffd6b64'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 27.3 tried to attribute a bare legacy-form merge (`Merge 34-3 into main`) to a station by whether that station's ledger knows the key. Its own review showed that rule reopens the cross-station collision whenever two stations know the same integer key — the common case under one shared story grammar — so it reverted and landed empty. Marshal `34-3` (`dcda31b8cb`, 2026-09-12, harness run `deferred`) still reads `done` with no merge commit anywhere on `main`.

**Approach:** Attribute a bare-form merge by the station paths its first-parent diff touches (`git diff --name-only <merge>^1 <merge>`, classified by `_bmad-output/projects/<slug>/` and `src/shared/packages/<slug>/` prefixes, cached per sha within a run). A bare-form merge attributes to the querying station iff its paths appear AND the station's ledger knows the key — both conditions, never one. Git is the sole authority for merged facts. One helper serves `marshal.py::gather_story_status` and `ledger.py::gather_direction`; the scoped form and every other shape are unchanged.

## Boundaries & Constraints

**Always:**
- `story-status` on `main` reports no finding for marshal `34-3`; a bare `Merge 34-3 into main` whose diff touches only another station's paths attributes nothing to the querying station even when its ledger knows 34-3; a merge touching no station path attributes nothing; the scoped form still attributes; CAP-78's PR #1465 replay and CAP-79's rekey replay stay green.
- One helper, both sources; git call cached per sha; exit-code domain `{0, 2, 130}` untouched.

**Never:**
- Do not attribute by ledger membership alone (27.3's gap), and do not attribute a fleet-wide mop commit that grazes many packages to every station it touches — the ledger-knows-the-key condition is the second gate.
- Do not import `pyforge.marshal`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| own legacy landing | `Merge 34-3 into main`; diff touches only marshal paths; marshal ledger knows 34-3 | attributed to marshal | n/a |
| sibling's bare merge | same subject; diff touches only steward paths; marshal ledger knows 34-3 | nothing for marshal | n/a |
| no station path | bare subject; diff touches only `docs/` | nothing | n/a |
| scoped form | `Merge pyforge-marshal/50-1 into main` | attributed (unchanged path) | n/a |
| git call fails | `git diff` errors for a sha | WARN naming the sha, subject unattributed | never crash |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-doctor CAP-80` (Approach amended 2026-09-18).
Surface: `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py`; `.../sources/ledger.py`; tests. Prior art: `.worktrees/dispatch-pyforge-doctor-27.3/_bmad-output/implementation-artifacts/spec-27-3-attempted-patch-2026-09-18.patch` (plumbing only — its rule is the one this story replaces).
Ledger key: `27-5-a-bare-form-merge-is-attributed-by-the-paths-its-diff-touches`.
Re-keyed from 27.4 the same evening (27.4 is a reserved hole: the mint PR's branch name `doctor/27-4-mint` parses under the station-branch landing grammar, so its merge subject reads as 27.4 landed and any dispatch of that key short-circuits `story_merged_on_main`). Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-27-5-a-bare-form-merge-is-attributed-by-the-paths-its-diff-touches.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).

**Manual checks:**
- `pixi run -e pyforge-guild story-status-check` on `main` reports no `marshal/34-3` finding; `git diff --name-only dcda31b8cb^1 dcda31b8cb` shows only `pyforge-marshal` paths (the real-case fixture).
