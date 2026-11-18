---
title: '126.1: The checkout is clean on a case-insensitive filesystem'
type: 'fix'
created: '2026-11-18'
status: 'ready-for-dev'
story: 126-1-the-checkout-is-clean-on-a-case-insensitive-filesystem
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # tests, a gate's own module and the scripts a gate runs; a gated gate is a silent green (roster list)
surface:
  - 'recipes/CTranslate2/**'
  - 'src/shared/packages/pyforge-warden/tests/fixtures/corpus/recipes/CTranslate2/**'
  - 'scripts/.spec-surface-baseline.json'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `recipes/ctranslate2/` (4.8.0) and `recipes/CTranslate2/` (4.6.0) are both tracked, so a macOS checkout always shows one modified, `git rebase` refuses, and a baseline stamped there recorded the wrong file's hash (the `cfe-meta` failure on PR #2373).

**Approach:** The uppercase directory and its warden corpus twin are removed and the warden Spec is reconciled and stamped.

Ledger key: `126-1-the-checkout-is-clean-on-a-case-insensitive-filesystem`.

### Living CAP citations

- spec-pyforge-steward CAP-175 and CAP-5 (realized, no text change); FR-49 ← CAP-175; no AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Close the deferred-work row this story names with the commit that resolves it.

**Never:**
- Never weaken an assertion that holds on Linux, hand-edit a compiled skill, a `SPEC.md`, a generated page or `sprint-status-ledger.yaml`.

## Acceptance Criteria

**Given** `recipes/ctranslate2/` (4.8.0) and `recipes/CTranslate2/` (4.6.0) are both tracked, so a macOS checkout always shows one modified, `git rebase` refuses, and a baseline stamped there recorded the wrong file's hash (the `cfe-meta` failure on PR #2373)
**When** the uppercase directory and its warden corpus twin are removed and the warden Spec is reconciled and stamped
**Then** `git status` is clean after a fresh checkout on macOS, `spec-surface-check` exits 0 on Linux and macOS, and warden's corpus regression still passes
**And** `DW-doctor-59-1-1`'s case-collision half reads resolved in its ledger with the commit that closed it

- **AC1 — The story's own check passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild spec-surface-check && pixi run --frozen -e pyforge-warden pyforge-warden-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-175 and CAP-5 (realized, no text change); FR-49 ← CAP-175; no AD moves.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-11-18 entry; operator ruling of 2026-11-18: "THIS MACHINE WILL BE A FIRST CLASS DEVELOPMENT HOST -- JUST FIX ALL THE DEFERRED ROW ITEMS NOW.. AND NOT LEAVE ANYTHING FOR LATER", "JUST USE ctranslate2 and remove the other one", "we should continue to support manticore and antigravity", "we still want to do everything in this session as one PR".
- Epic: Epic 126, minted with this story.
- Ledger key: `126-1-the-checkout-is-clean-on-a-case-insensitive-filesystem` (`backlog`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."126"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-18: minted from the station Dream's 2026-11-18 entry and the operator's rulings of the same date.
