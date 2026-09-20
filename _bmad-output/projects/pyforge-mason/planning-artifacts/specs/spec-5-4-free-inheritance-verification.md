---
title: 'Free-inheritance verification (SM-4)'
type: 'chore'
created: '2026-08-15'
status: 'blocked'
blocking_condition: 'unmet external dependency -- Mason v1 has not shipped'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-5-context.md'
warnings: []
---

<intent-contract>

## Intent

**Problem:** SM-4 ("free inheritance") claims a CFE improvement reaches Mason with zero
corresponding Mason change. Proving it needs a *real* post-ship CFE MINOR version bump observed
against a shipped Mason `recipe` verb -- not a simulation. Neither precondition holds today: Mason
v1 (Epics 1-5) is not shipped -- this very story and its sibling 5.5 (the closing retrospective) are
themselves the remaining open work in Epic 5 -- so there is no "post-ship" point yet to measure a CFE
change against.

**Approach:** Record the measurement procedure and the current CFE baseline now, so the observation
is a same-day action once both preconditions hold. Do not fabricate, simulate, or backport a CFE
change to manufacture evidence.

## Boundaries & Constraints

**Always:** the eventual observation compares a `mason recipe <verb>` invocation's behavior
before/after a real CFE MINOR release, recorded with the CFE version and date, per the story's AC.

**Block If:** Mason v1 (Epics 1-5, including this story's sibling 5.5) has not been declared done
(true today: 5.4 and 5.5 both remain open per `sprint-status.yaml`) -- HALT blocked. No real CFE
MINOR version has landed since that ship point -- HALT blocked. Either condition alone is sufficient
to block; this run hits both.

**Never:** simulate, mock, or hand-roll a "CFE improvement" to produce a passing observation. Never
edit the CFE surface to manufacture a bump (Rule 1; the Story 5.2 governance test would catch it
regardless). Never mark SM-4 satisfied without a dated, real observation.

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-mason/planning-artifacts/prds/prd-pyforge-mason-2026-07-25/prd.md`
  §7 (SM-4 definition) and §10 D-4 ("Revisit when SM-1 and SM-4 are both demonstrated") -- where
  SM-4's satisfaction gets recorded once observed.
- `src/shared/packages/pyforge-mason/src/pyforge/mason/recipe.py` -- the CFE-dependent verb family
  (AD-6); any `mason recipe <verb>` invocation is the natural subject since it delegates to CFE by
  subprocess with zero Mason-side recipe logic (D-1), so a CFE-side improvement should surface there
  with no Mason code change.
- `.claude/skills/conda-forge-expert/CHANGELOG.md` -- source of the "did a real CFE MINOR bump land"
  signal. Current baseline recorded by this run: **v8.81.0** (2026-07-29), unchanged as of
  2026-08-15.

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

This story is pure observation, not implementation -- there is no code to write today. Its own XS
effort estimate and epics.md assumption A-4 ("depends on an external event... may complete after v1
is declared done") both anticipate exactly this outcome. Re-invoke this spec once both Block If
conditions clear; at that point the "Execution" checklist above is the entire remaining task.

## Verification

**Manual checks (if no CLI):**
- `sprint-status.yaml`: Epics 1-5 all `done` (including 5.5) confirms the ship precondition.
- `.claude/skills/conda-forge-expert/CHANGELOG.md` top entry version > `8.81.0` (this run's recorded
  baseline) with a MINOR bump confirms the CFE-side precondition.

## Auto Run Result

Status: done
Reconciled 2026-09-20: the `blocked` verdict below is the session's own record at halt time; the story was landed afterwards and the ledger row promoted to `done` by `7a05d20034 2026-08-21 mason: Story 5.4 free-inheritance verification — SM-4 recorded, Epic 5 closed` — that promotion is the ruling this record now reflects.
Blocking condition: **unmet external dependency -- Mason v1 has not shipped**

**Summary:** Story 5.4 requires observing a real conda-forge-expert MINOR version bump landing
*after* Mason ships v1, then re-running the affected `mason recipe` verb to show the improved
behaviour with zero Mason repository change. Investigation confirmed neither precondition exists:

- Mason v1 has not shipped. `sprint-status.yaml` (both the Tier-3 feed and the tracked ledger) shows
  Epic 5 stories 5.4 (this story) and 5.5 (the closing Rule-2 retrospective) still open, and Epic 6
  (a separate CFE-rebuild feasibility spike, out of v1 scope per `epics.md`) is irrelevant to this
  precondition. `pyforge-mason`'s `pyproject.toml` is still at `0.1.0` with no `CHANGELOG.md`, and no
  ship-receipt artifact exists anywhere in the repo -- consistent with SM-1 (Mason ships Mason) not
  yet having produced a real PyPI/TestPyPI publish.
- Even once v1 ships, no *real* post-ship CFE MINOR bump has landed to observe: the CFE skill's
  current version is `8.81.0` (`CHANGELOG.md`, dated 2026-07-29), unchanged through this run's date
  (2026-08-15).

Per this story's own effort note ("Depends on an external event; may complete after v1 ships") and
epics.md assumption A-4, this is the expected, designed outcome for an early invocation -- not a
planning defect. No code was written. A spec now exists (`status: blocked`) recording the exact
procedure and the CFE version baseline (`8.81.0`) so the observation is a same-day action once Epic
5 (including 5.5) is done and a subsequent real CFE MINOR release lands. This run performed no
codebase modification.

**Action taken:** none (read-only investigation). `_bmad-output/implementation-artifacts/sprint-
status.yaml` was left unmodified -- 5.4 remains `backlog`, matching reality.

**Recommendation:** re-invoke `bmad-dev-auto 5-4-free-inheritance-verification` after Story 5.5
lands and Mason v1 is declared done, and periodically thereafter until a CFE MINOR bump is observed
in `CHANGELOG.md` above `8.81.0`.

## Status reconcile 2026-09-20

- Auto Run Result `Status: blocked` → `done` (see the reconcile line under it).
