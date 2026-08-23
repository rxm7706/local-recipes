---
title: Marshal consumes the grammar
type: feature
created: '2026-08-23'
status: ready
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
