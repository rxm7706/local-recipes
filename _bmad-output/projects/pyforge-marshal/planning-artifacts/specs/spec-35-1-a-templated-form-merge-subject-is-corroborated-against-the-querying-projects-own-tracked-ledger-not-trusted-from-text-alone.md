---
title: '35.1: A templated-form merge subject is corroborated against the querying project''s own tracked ledger, not trusted from text alone'
type: 'fix'
created: '2026-09-18'
status: 'done'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** A templated-form merge subject is corroborated against the querying project's own tracked ledger, not trusted from text alone (contract recovered from epics.md Intent + ACs).

**Approach:** `core/promotion.py` (`_classify_merge_subject`, `merged_story_keys`, `marshal_native_merged_keys` all gain an optional `known_keys` parameter), `dispatch_supervisor/__main__.py` (`_load_known_story_keys` new helper reads the querying project's own tracked `sprint-status-ledger.yaml`; `gather_dispatch_git_facts` wired to use it — the exact function that produced 2026-09-11's false verdicts), `tests/unit/test_promotion.py`, `tests/unit/test_dispatch.py`

Ledger key: `35-1-a-templated-form-merge-subject-is-corroborated-against-the-querying-projects-own-tracked-ledger-not-trusted-from-text-alone`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- Cited from epics.md: `spec-marshal-templated-merge-subject-cross-project-collision` CAP-1

## Acceptance Criteria

- Given a bare `"Merge 22.5 into main"` subject is accepted as ANY project's own merged key with zero station-scoping, since the templated shape's text carries no station token When the caller supplies `known_keys` (the querying project's own tracked story-key catalog, loaded from its `sprint-status-ledger.yaml`) Then a templated-shape match is trusted only when its key is a member — corroboration the ledger provides that git text cannot; an unrelated project's colliding key number is excluded And with `known_keys` omitted (the default), behavior is unchanged for any not-yet-updated caller — no silent regression And a missing or malformed ledger degrades to `frozenset()` (trust nothing from the templated shape), the SAFE direction, never a crash and never the dangerous direction And re-running the Dream's own live reproduction (`merged_story_keys` templated-shape matches for a `pyforge-doctor` query) drops from 79 to 30 keys, with `22.11`/`22.12`/`23.x`/`28.x`/`39.x`–`49.x` all gone

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| a bare `"Merge 22.5 into main"` subject is accepted as ANY project's own merged  | the caller supplies `known_keys` (the querying project's own | a templated-shape match is trusted only when its key is a member — corroboration | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 35.1 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `35-1-a-templated-form-merge-subject-is-corroborated-against-the-querying-projects-own-tracked-ledger-not-trusted-from-text-alone: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
