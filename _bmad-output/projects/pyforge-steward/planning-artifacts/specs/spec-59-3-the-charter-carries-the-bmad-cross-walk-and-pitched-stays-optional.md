---
title: '59.3: The Charter carries the BMAD cross-walk and pitched stays optional'
type: 'docs'
created: '2026-09-16'
status: 'in-review'
baseline_revision: '9bdabafaa0966bf6d2ae78b0888c4e913f6418de'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
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

