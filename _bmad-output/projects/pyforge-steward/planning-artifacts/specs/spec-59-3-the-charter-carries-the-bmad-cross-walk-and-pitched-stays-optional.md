---
title: '59.3: The Charter carries the BMAD cross-walk and pitched stays optional'
type: 'docs'
created: '2026-09-16'
status: 'done'
baseline_revision: '9bdabafaa0966bf6d2ae78b0888c4e913f6418de'
review_loop_iteration: 1
followup_review_recommended: false
context: []
deferred:
  - finding: >-
      Charter frontmatter's `status:` comment still says "five amendments have
      executed against it" (dated 2026-09-09); the file now carries well more
      than five dated amendment markers / Realization-log entries.
    location: 'docs/dreams/pyforge-charter.md'
    reason: >-
      Pre-existing staleness predating this diff, not caused by Story 59.3;
      fixing the exact count needs its own pass rather than a side-effect of
      this story's cross-walk addition.
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Hub has a Charter walk and BMAD's daily nouns do not.

**Approach:** The Charter maps Epic / Story / Sprint / PRD / Retrospective (never join) and records Spec shipped != story done != Dream realized. pitched remains declared and optional; no Dream is backfilled.

## Boundaries & Constraints

**Always:**
- Charter maps Epic, Story, Sprint, PRD, Retrospective.
- Spec shipped, story done, and Dream realized stay three different facts.
- pitched stays declared and optional.

**Never:**
- Do not join those BMAD nouns into one row.
- Do not backfill pitched onto existing Dreams.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Dream without pitched | frontmatter lacks pitched | unchanged; pitched optional | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-vocabulary-one-name-one-job CAP-3`.
Surface: docs/dreams/pyforge-charter.md; docs/governance/guild-roster.json..
Ledger key: `59-3-the-charter-carries-the-bmad-cross-walk-and-pitched-stays-optional`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-59-3-the-charter-carries-the-bmad-cross-walk-and-pitched-stays-optional.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

## Review Triage Log

### 2026-09-24 — Review pass
- verdicts: 8 findings — high 0, medium 3, low 3, false 2, maybe-false 0
- findings:
  - `[false]` `[reject]` Blind Hunter: ledger key `59-3-...` still `backlog` while spec status advances and no `sprint-ledger-sync` accompanies the diff — refuted: `step-04-review.md`'s own Finalize section never syncs `sprint-status-ledger.yaml`; ledger promotion is a separate, later operation (`sprint-ledger-sync`), documented in AGENTS.md as happening before landing, not before this workflow's HALT. Not a contradiction this diff created.
  - `[medium]` `[reject]` Blind Hunter: spec's `## Verification` section binds only `pixi run --frozen -e pyforge-steward pyforge-steward-test`, which never runs the new `tests/scripts/test_bmad_cross_walk_is_declared.py` (only `pyforge-doctor-scripts-test` in `-e pyforge-ci` does, confirmed passing) — real gap, but its only fix is editing this build's spec's Verification section, which is explicitly rejected by the Classify rules, and doing so would also break the MRS-GATE-010 verbatim binding to `marshal-policy.toml`'s `verify_commands`. Broader coverage is enforced at the PR-gate layer (`pr-preflight`/`detectors-ci`), not per-story spec Verification.
  - `[low]` `[defer]` Blind Hunter: Charter frontmatter's `status:` comment still says "five amendments have executed against it" (dated 2026-09-09); the file now carries well more than five dated amendment markers/Realization-log entries — real staleness, but pre-existing (the comment predates this diff and was not touched by it); not caused by this story.
  - `[medium]` `[patch]` Blind Hunter: new BMAD-vocabulary table's Story row said "tracked as a row in **the Guild's** `sprint-status-ledger.yaml`," implying one shared ledger, inconsistent with the Epic row's correct "**that station's** `epics.md`" and with the real per-station-ledger layout — fixed: reworded to "that station's `sprint-status-ledger.yaml`".
  - `[medium]` `[patch]` Blind Hunter: every new citation pointed only to `spec-vocabulary-one-name-one-job` CAP-3, which is `status: absorbed-into: spec-pyforge-steward` (folded 2026-09-17) with the capability renumbered `CAP-133` in `spec-pyforge-steward/SPEC.md` — the diff's own new citations never named the live id — fixed: added a "(folded 2026-09-17 into `spec-pyforge-steward` CAP-133)" pointer alongside the CAP-3 citation in the Charter subsection's amendment note, the Realization-log entry, and the new test's module docstring.
  - `[low]` `[patch]` Blind Hunter: `test_the_reverse_walk_names_the_untouched_lexicon_nouns` only asserted the heading phrase, never that Charter/Guild/Smiths/Stations/Guildhall are actually listed, unlike its sibling `test_all_five_bmad_terms_are_mapped` — fixed: added a per-noun assertion loop.
  - `[low]` `[patch]` Edge Case Hunter: `_bmad_subsection()`'s `text.index(...)` calls raised a bare `ValueError` (not a clear assertion failure) if the heading or its closing `### ` heading went missing — fixed: added explicit `assert` guards with descriptive messages before each `.index()` call.
  - Verification Gap Reviewer: no findings (ran the new test directly, confirmed CI wiring via `pyforge-doctor-scripts-test`/`detectors.yml`, spot-checked cited facts).
  - Intent Alignment Auditor: descriptive only, no discrete findings — confirmed the diff implements the one well-grounded reading of the intent (documentation-only, per the sourced operator ruling text), so no `intent_gap`.

### 2026-09-24 — Review pass (follow-up, entered from a `done` spec)
- verdicts: 4 findings — high 0, medium 3, low 1, false 0, maybe-false 0
- findings:
  - `[medium]` `[patch]` self-review: the new subsection's reverse-walk sentence listed `Smiths` as having "no BMAD counterpart," contradicting Charter § The Smiths, which already states "Smith (brand) = agent (category) = persona (technical, what a BMAD config says)" — a real, already-shipped self-contradiction inside the Charter. Fixed: removed `Smiths` from the bare reverse-walk list and added an explanatory clause pointing to the existing Charter § The Smiths equivalence, so it reads as the deliberate non-entry it should have been (matching how `Spec` is already handled) rather than a false negative claim.
  - `[medium]` `[patch]` self-review: `Skills` — its own numbered Charter subsection ("the armory... wielded, never worn") — was completely absent from the cross-walk: no forward-mapping row, no reverse-walk entry, no exception sentence. This breaks the completeness pattern the sibling `### Intelligence Hub vocabulary` cross-walk established and that Story 59.3's own Tasks require mirroring. Fixed: added `Skills` to the reverse-walk list of Lexicon nouns with no BMAD counterpart.
  - `[medium]` `[patch]` self-review: the Sprint table row read "a BMAD planning-lane concept, with no Lexicon noun of its own," directly contradicting the subsection's own opening claim that all five BMAD terms "map onto this Lexicon." Fixed: reworded the row to map Sprint onto its real Lexicon/estate surface — a batch of Stories tracked implicitly through that pass's own rows in the station's `sprint-status-ledger.yaml` — consistent with how Epic/Story/PRD/Retrospective are each mapped.
  - `[low]` `[patch]` self-review: the subsection heading carried an inline `*(amended 2026-09-24)*` tag not used by the sibling Hub cross-walk heading (which states its amendment date only in the fuller parenthetical below, not on the heading itself) — inconsistent styling within the same file. Fixed: removed the inline tag from the heading.
  - Regression test updated to pin all four fixes: `_REVERSE_WALK_NOUNS` now reads `("Charter", "Guild", "Stations", "Guildhall", "Skills")` (dropping `Smiths`, adding `Skills`), and a new `test_smiths_is_explained_not_silently_reverse_walked` pins the explanatory clause. Verified: `pixi run -e pyforge-ci python -m pytest tests/scripts/test_bmad_cross_walk_is_declared.py -q` → 13 passed; `pixi run --frozen -e pyforge-steward pyforge-steward-test` → 1680 passed, 2 skipped; `pixi run -e pyforge-ci pyforge-doctor-scripts-test` → 710 passed, 5 skipped.
- Per this workflow's rule for a review entered against an already-`done` spec, `followup_review_recommended` is forced to `false` at HALT regardless of the patched-medium-count threshold.

## Auto Run Result

**Summary:** Added the `### BMAD vocabulary — cross-walk, never a shared noun` subsection to
`docs/dreams/pyforge-charter.md` (Epic/Story/Sprint/PRD/Retrospective mapped onto the nearest
Lexicon/estate surface, `Spec` explained as the deliberate non-row, three named divergences, a
reverse-walk list), a matching 2026-09-24 Realization-log entry, and companion prose in
`docs/governance/guild-roster.json`'s `$comment_dream_statuses` declaring `pitched` optional and
never backfilled (Ruling 6). Pinned by the new `tests/scripts/test_bmad_cross_walk_is_declared.py`.

**Files changed:**
- `docs/dreams/pyforge-charter.md` — new subsection + Realization-log entry; three first-pass
  review wording fixes (Story-row ledger phrasing; CAP-3→CAP-133 fold pointer added in two spots);
  four follow-up-pass fixes (Smiths/persona reverse-walk contradiction resolved; `Skills` added to
  the reverse-walk; Sprint row's self-contradiction resolved; duplicate amendment-date heading tag
  removed).
- `docs/governance/guild-roster.json` — `$comment_dream_statuses` prose extended (Ruling 6);
  `dream_statuses` array itself untouched (regression-guarded by the new test).
- `tests/scripts/test_bmad_cross_walk_is_declared.py` — new pinning test (13 tests); first-pass
  review hardened `_bmad_subsection()`'s two `.index()` calls with descriptive `assert` guards and
  added a per-noun assertion loop to `test_the_reverse_walk_names_the_untouched_lexicon_nouns`;
  follow-up pass updated `_REVERSE_WALK_NOUNS` (dropped `Smiths`, added `Skills`) and added
  `test_smiths_is_explained_not_silently_reverse_walked`.

**Review findings:** 12 total across two passes (8 first pass: 7 Blind Hunter, 1 Edge Case Hunter,
0 from Verification Gap/Intent Alignment; 4 follow-up self-review) — high 0, medium 6, low 4,
false 2.
- Patched (8): first pass — Story-row ledger wording; missing CAP-3→CAP-133 fold pointers (3
  sites); missing per-noun assertions in the reverse-walk test; bare `ValueError` in
  `_bmad_subsection()`. Follow-up pass — Smiths/persona reverse-walk contradiction; missing
  `Skills` reverse-walk entry; Sprint row's self-contradiction; duplicate amendment-date heading
  styling.
- Deferred (1): Charter frontmatter's stale "five amendments" count — pre-existing, predates this
  diff, not caused by this story. Recorded in `deferred:` below.
- Rejected (3, first pass only): ledger-key-still-`backlog` (expected — ledger sync is a separate,
  later operation, not part of this workflow's Finalize); spec Verification-section coverage gap
  for the new test file (fix is editing this build's own spec, explicitly out of scope, and would
  also break the MRS-GATE-010 verbatim binding to `marshal-policy.toml`); a fabricated "already
  flagged in review pass 1" citation on two findings that no prior triage log for this story
  supports (evaluated each substantively on its own merits regardless of the false provenance
  claim).

**Follow-up review recommended: false (forced).** This pass was entered against an already-`done`
spec (the one allowed follow-up); per this workflow's rule, `followup_review_recommended` is
forced to `false` at HALT regardless of the patched-medium-count threshold. All four follow-up
findings were patched directly with no open questions.

**Verification performed:**
- `python3 -m pytest tests/scripts/test_bmad_cross_walk_is_declared.py -q` → 13 passed (first
  pass: 12 passed).
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` (spec's bound Verification command)
  → 1680 passed, 2 skipped (re-verified after the follow-up pass's edits).
- `pixi run -e pyforge-ci pyforge-doctor-scripts-test` → 710 passed, 5 skipped (re-verified after
  the follow-up pass's edits; this is the suite that actually runs the new pinning test).
- `python scripts/spec_surface_reconcile.py` → `OK: every tracked file governed or allowlisted; no
  drift.` The one governed path this story touches, `docs/dreams/pyforge-charter.md`, is owned by
  `docs/governance/spec-pyforge-charter` (the Charter's own constitutive kernel spec — not
  `spec-vocabulary-one-name-one-job`/`spec-pyforge-steward`, which govern no part of this surface);
  reconciled with a `.memlog.md` event entry naming the change before this Finalize. The other two
  changed files (`docs/governance/guild-roster.json`, `tests/scripts/test_bmad_cross_walk_is_declared.py`)
  are allowlisted (`docs/governance/**`, `tests/**`) and ungoverned by any spec surface.
- Grepped the repo for other consumers of every changed string/constant; found none.

**Residual risks:** the deferred stale-amendment-count finding (tracked below, pre-existing). The
first pass's named risk (full `detectors-ci`/`bmad-drift-check`/`chain-completeness-check` not run
locally) is superseded by this follow-up pass forcing `followup_review_recommended: false`, but
that broader suite still has not been run locally against this diff; it remains a residual risk to
surface at the PR-gate layer (`pr-preflight`/`detectors-ci`) rather than a blocking one for this
story's own Finalize.

