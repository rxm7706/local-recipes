---
title: 'Free-inheritance verification (SM-4) -- recheck 2026-08-20'
type: 'chore'
created: '2026-08-20'
status: 'blocked'
blocking_condition: 'unmet external dependency -- Mason v1 has not shipped; no new CFE MINOR since baseline'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-5-context.md'
warnings: []
baseline_revision: '4397583a7687c989086673c1ac82cea94a531238'
---

<intent-contract>

## Intent

**Problem:** SM-4 ("free inheritance") requires observing a *real* post-ship CFE MINOR version
bump against a shipped Mason `recipe` verb. The prior run (2026-08-15, `spec-5-4-free-inheritance-
verification.md`) found both preconditions unmet and recorded a CFE baseline of `v8.81.0` to make
a future recheck fast. This run re-verifies that baseline five days later.

**Approach:** Re-check both Block-If conditions against current repo state only; do not repeat the
full investigation. If either is still unmet, HALT blocked again with a refreshed baseline. Do not
fabricate, simulate, or backport a CFE change to manufacture evidence.

## Boundaries & Constraints

**Always:** the eventual observation compares a `mason recipe <verb>` invocation's behavior
before/after a real CFE MINOR release, recorded with the CFE version and date, per the story's AC.

**Block If:** Mason v1 (Epics 1-5, including sibling story 5.5) has not been declared done -- HALT
blocked. No real CFE MINOR version has landed since the recorded baseline (`v8.81.0`,
2026-07-29) -- HALT blocked. Either condition alone is sufficient; this run hits both:
- `sprint-status.yaml` (Tier-3 feed, checked 2026-08-20): `epic-5: backlog`; `5-4-free-inheritance-
  verification: backlog` (this story); `5-5-rule-2-conda-forge-expert-retrospective: backlog`.
  Epic 5 is not done.
- `.claude/skills/conda-forge-expert/CHANGELOG.md` top entry (checked 2026-08-20): still
  **v8.81.0** (Jul 29, 2026, current) -- unchanged from the recorded baseline.

**Never:** simulate, mock, or hand-roll a "CFE improvement" to produce a passing observation. Never
edit the CFE surface to manufacture a bump (Rule 1; the Story 5.2 governance test would catch it
regardless). Never mark SM-4 satisfied without a dated, real observation.

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-mason/planning-artifacts/prds/prd-pyforge-mason-2026-07-25/prd.md`
  §7 (SM-4 definition, line 829) and §10 D-4 ("Revisit when SM-1 and SM-4 are both demonstrated",
  line 971) -- unchanged since the prior run; re-read in full this session, content identical.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` -- authoritative live story-status
  feed; confirms Epic 5 / 5.4 / 5.5 are all still `backlog` as of 2026-08-20.
- `.claude/skills/conda-forge-expert/CHANGELOG.md` -- source of the "did a real CFE MINOR bump
  land" signal. Still **v8.81.0** as of 2026-08-20 -- no change since the prior baseline.
- `src/shared/packages/pyforge-mason/src/pyforge/mason/recipe.py` -- the CFE-dependent verb family
  (AD-6); the eventual observation subject once both preconditions clear.

## Tasks & Acceptance

**Execution (deferred until both Block If conditions clear):**
- [ ] Confirm Mason v1 is declared done -- Epics 1-5 all `done` in `sprint-status.yaml`, including
      5.5's closing retrospective.
- [ ] Confirm a CFE MINOR version has shipped after that ship point (`CHANGELOG.md` top entry
      version greater than the baseline recorded at ship time).
- [ ] Identify the specific `mason recipe <verb>` whose behavior the new MINOR release changed; run
      it and compare against a pre-recorded baseline run, with no Mason code change in between.
- [ ] Record the observation -- CFE version, date, verb, and the behavior delta -- as a dated entry
      under PRD §7 SM-4, and mark it satisfied.

**Acceptance Criteria:**
- Given a CFE MINOR version bump landing after Mason ships, when the affected Mason verb is
  re-run, then the improved behaviour is observed and the Mason repository shows no corresponding
  change.
- Given the observation, when it is recorded, then SM-4 is marked satisfied with the CFE version
  and the date.

## Design Notes

This is a periodic recheck, not new implementation -- there is no code to write today, matching the
prior run's own finding. Re-invoke this spec once both Block-If conditions clear; at that point the
"Execution" checklist above is the entire remaining task.

## Verification

**Manual checks (if no CLI):**
- `sprint-status.yaml`: Epics 1-5 all `done` (including 5.5) confirms the ship precondition.
- `.claude/skills/conda-forge-expert/CHANGELOG.md` top entry version > `8.81.0` with a MINOR bump
  confirms the CFE-side precondition.

## Auto Run Result

Status: `blocked`
Blocking condition: **unmet external dependency -- Mason v1 has not shipped; no new CFE MINOR
version has landed since the recorded baseline**

**Summary:** Independently re-verified both Block-If conditions against live repo state on
2026-08-20. Both still hold:

- **Epic 5 not done.** `_bmad-output/implementation-artifacts/sprint-status.yaml` (lines 69-75):
  `epic-5: backlog`; `5-4-free-inheritance-verification: backlog` (this story, not yet closed);
  `5-5-rule-2-conda-forge-expert-retrospective: backlog`. Stories 5.1-5.3 are `done`, but the epic
  itself and its two remaining stories are open.
- **No new CFE MINOR version.** `.claude/skills/conda-forge-expert/CHANGELOG.md` top entry (line 5)
  is still **v8.81.0** (Jul 29, 2026) -- byte-identical to the baseline recorded in the prior run
  (`spec-5-4-free-inheritance-verification.md`, 2026-08-15). No release has shipped in the
  intervening five days.

Per the intent contract, either condition alone is sufficient to block; this recheck hits both, so
the Execution checklist above was NOT performed -- its four items remain unchecked `[ ]`. No CFE
change was fabricated, simulated, or backported, and nothing under `.claude/skills/conda-forge-
expert/` or any recipe surface was touched. This is the expected, designed outcome for this recheck,
not a failure.

**Action taken:** none beyond this spec file's own status/result fields. No other file was created,
edited, or deleted; `sprint-status.yaml` and the PRD were left unmodified.

**Recommendation:** re-invoke this recheck again once Story 5.5 lands and Epic 5 is declared `done`
in `sprint-status.yaml`, and periodically thereafter until `CHANGELOG.md`'s top entry advances past
`8.81.0` with a MINOR bump.
