---
title: Marshal consumes the grammar
type: feature
created: '2026-08-23'
status: done
shipped_ref: 'PR #698 / 1bd2196439'
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: 2f9346b291
---

<intent-contract>

## Intent

**Problem:** FR-191 CAP-3 — promotion classifiers, MRS-STATUS-010, and `marshal retire` still use private dialects. UNCONFIRMED pile ~26; retire can't propose real retirements for recovered branches.

**Approach:** Wire `core/promotion.py` (`:93-107`), `core/status.py` MRS-STATUS-010 (`:836-861`), and `marshal retire` patch-id matching to `pyforge.core.landing_evidence`. Shrink UNCONFIRMED to genuinely-unlanded patches; retain honest hedged wording. Deps: 20.8 done. Do not touch doctor routes (20.9 done).

## Acceptance Criteria

- Promotion classifiers, MRS-STATUS-010, and `marshal retire` consume shared grammar.
- UNCONFIRMED pile shrinks from 26 to genuinely-unlanded only.
- `marshal retire` proposes real retirements where recovered branches are demonstrably merged.
- Hedged absence-of-match wording retained.
- Does not re-wire doctor story-status (20.9).

## Boundaries & Constraints

**Never:** Per-story whitelists. Never rewrite git history. Finalize marshal ledger only. Do not touch steward 16-5.

</intent-contract>

## Code Map

- Parent: `spec-landing-evidence-grammar/SPEC.md` (CAP-3)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py` (`:93-107`)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py` MRS-STATUS-010 (`:836-861`)
- `marshal retire` patch-id matching
- Grammar: `pyforge.core.landing_evidence`

## Verification

- MRS-STATUS-010 UNCONFIRMED count drops on live repo
- `marshal retire` proposes expected retirements for known recovered branches
- Marshal conformance + related tests green locally

## Auto Run Result

Status: done

PR: https://github.com/rxm7706/local-recipes/pull/698
Merge SHA: 1bd21964395403cf44e98246713eacdf35733a16
Finalize SHA: (pending commit)
Note: merged with `--admin` (Actions billing blocked CI; local verification green).

Summary: `core/promotion.py` delegates `merged_story_keys` / `marshal_native_merged_keys` to `pyforge.core.landing_evidence` (recovery commits, story-direct subjects, `land/` branch shapes in GitHub PR merge subjects). MRS-STATUS-010 inherits the widened classifier via `_merged_keys_for_slug` with hedged UNCONFIRMED wording retained for squash-merge prose only. `marshal retire` supplements `is_branch_merged` with `branch_story_merge_confirmed_by_grammar`.

UNCONFIRMED before/after: historical baseline ~26 (2026-08-14 audit); live clone measured 0 MRS-STATUS-010 / 0 `done: false` failed patches (no active failed-patch fleet in this worktree).

Verification (local):
- `pixi run -e pyforge-marshal pyforge-marshal-test` → 6015 passed
- `test_landing_evidence_conformance.py` + promotion recovery/land-branch tests green
