---
title: '59.5: One mint-time slugify and two DW families'
type: 'feature'
created: '2026-09-16'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred:
  - summary: >-
      `mint_sweep_id` (the sweep-scoped `DW-{station}-{slug}-{date}[-n]` family)
      and `slugify_title`/`StoryIdentity`/`mint_story_identity` (one mint-time
      slugify deriving a new story's heading, ledger key, and spec filename)
      have no caller yet: `scripts/deferred_work_promote.py` only imports the
      story-scoped `mint_id_for_entry`, and no script mints a new story's three
      spellings today (that still happens by hand, mirroring `epics.md`'s own
      established numbering convention per `AGENTS.md` § *Spec → Story before
      code*). This story's own scope is the derivation functions themselves
      (I/O matrix: "new story mint" / "existing DW- id"), not their wiring.
    evidence: >-
      `grep -rn "mint_sweep_id\|mint_story_identity\|slugify_title\|StoryIdentity"
      --include="*.py" .` outside `sources/chain.py` and its tests returns
      nothing. Closure: wire `mint_sweep_id` into a future sweep-promotion
      entrypoint (natural home: `scripts/deferred_work_promote.py`, alongside
      `mint_id_for_entry`) and `mint_story_identity` into whichever script
      first automates `bmad-create-epics-and-stories`' hand-mirrored numbering
      convention — both outside this story's surface.
    location: >-
      src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py
    severity: low
declared_low_risk: false
baseline_revision: '685667273e3f5d680464de653d4bcdc26c01bcea'
---

<intent-contract>

## Intent

**Problem:** One story is spelled three non-derivable ways and DW- has eleven grammars.

**Approach:** A new story's heading, ledger key, and spec-<ledger-key>.md derive from one function. A new DW- id is story-scoped or sweep-scoped and includes the short station token. The 53 divergent slugs and 1338 existing DW- ids are untouched.

## Boundaries & Constraints

**Always:**
- New heading, ledger key, and spec-<ledger-key>.md share one slugify.
- New DW- ids are story-scoped or sweep-scoped and carry the short station token.

**Never:**
- Do not retro-rename the 53 divergent slugs.
- Do not rewrite the 1338 existing DW- ids.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| new story mint | one title | heading, ledger key, spec filename all derive | n/a |
| existing DW- id | any of the 1338 | byte-identical | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-vocabulary-one-name-one-job CAP-6`.
Surface: scripts/deferred_work_promote.py.
Ledger key: `59-5-one-mint-time-slugify-and-two-dw-families`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-59-5-one-mint-time-slugify-and-two-dw-families.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

