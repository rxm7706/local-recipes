---
title: 'pyforge-marshal — Retrospective (Epic 85: a verification refusal goes back to the session that wrote the change)'
project: pyforge-marshal
epic: 85
date: '2026-10-04'
created: '2026-10-04'
updated: '2026-10-04'
verdict: accepted-with-open-items
criteria: declared
headless: true
scope: 'Epic 85, Stories 85.1-85.5 (all done at retro time), landed 2026-10-03 to 2026-10-04, plus the first day of the fix turn running ON in dev (spec-pyforge-marshal CAP-286). Written as the reconciler half of the chain-currency sweep: marshal''s code stage moved on 2026-10-04 (Story 83.19''s branch added and reverted a pyproject.toml dependency) and the last retro was 2026-09-26.'
evidence:
  - 'git log --first-parent origin/main: a0f56650c2 (85.1), 9292a611e6 (85.2), ac992095d7 (85.3, PR #1812), ccf87829dc (85.4), 816ee9734d (85.5, PR #1861)'
  - '_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-85-{1..5}-*.md (intent, ACs, Review Triage Log)'
  - '_bmad-output/projects/pyforge-*/implementation-artifacts/dispatch-runs/*2026100[345]*/journal.jsonl (every dispatch-verify-fix and dispatch-verification record, read with a parser)'
  - 'scripts/chain_currency_sweep_check.py --project pyforge-marshal --json on origin/main f35e2c47ab (one edge: feeds code -> retro, 2026-10-04 vs 2026-09-26)'
---

# pyforge-marshal — Retrospective (Epic 85)

## Epic summary

**Epic.** Epic 85, *A verification refusal goes back to the session that wrote the change* (`epics.md` § Epic 85,
`spec-pyforge-marshal` CAP-286). Before it, a dispatch whose verification refused parked for the operator, who
read the refusal and re-dispatched by hand. Epic 85 sends the refusal back to the same session for one bounded fix
turn, behind `pyforge.marshal.verify_fix_loop`.

**Stories.** All five are `done` in the tracked ledger.

| Story | Landed | Path to `main` | Review on record |
|---|---|---|---|
| 85.1 the fix-turn machinery, dormant | `a0f56650c2` | dispatch, sent back, split, rebuilt landing branch | independent review sent back; landing review fixed by the operator's fixer |
| 85.2 a green fix turn lands and survives a restart | `9292a611e6` | dispatch | three independent landing reviews, lows fixed, verdict LAND |
| 85.3 safe to switch on in dev and staging | `ac992095d7` (#1812) | dispatch | landing review sent back and fixed; the post-landing delta review found new defects, fixed forward as 85.4 |
| 85.4 the redaction never hangs the supervisor | `ccf87829dc` | hand-built in `land/pyforge-marshal-85-4` | independent review sent back, fixed |
| 85.5 the fix turn's edits get the spec-surface reconcile | `816ee9734d` (#1861) | dispatch; its own refusal was cleared by a fix turn; landing refused twice on main moving, re-merged by hand, held as a draft at the operator's request, then merged | the build's review passes |

Every dispatch ran on Cursor (`composer-2.5-fast`), per the 2026-10-03 operator ruling in `marshal-policy.toml`.

## The fix turn's first day (ON in dev since 85.3)

Seven dispatch runs refused at verification and launched a fix turn between 2026-10-04 13:38Z and 2026-10-05 00:48Z:

| Run | Story | First refusal | Fix turn | Outcome |
|---|---|---|---|---|
| `pyforge-atlas-…T133823891Z` | atlas 27.2 | MRS-GATE-001 (a verify command failed) | 589 s | **verified** |
| `pyforge-marshal-…T153742426Z` | marshal 86.3 | MRS-GATE-001 | 75 s | **verified** |
| `pyforge-marshal-…T224319783Z` | marshal 85.5 | MRS-GATE-001 | 60 s | **verified** |
| `pyforge-atlas-…T144308982Z` | atlas 27.3 | MRS-GATE-001 (spec-surface drift) | 243 s | parked (MRS-DISP-060) |
| `pyforge-marshal-…T134059690Z` | marshal 86.8 | MRS-GATE-001, then MRS-GATE-011 | 477 s | parked (MRS-DISP-060) |
| `pyforge-mason-…T003648443Z` | mason 27.2 | MRS-GATE-020 (CFE outside a retro), then MRS-GATE-019 | 121 s | parked (MRS-DISP-060) |
| `pyforge-marshal-…T212831927Z` | marshal 83.19 | MRS-GATE-001 (a coverage floor) | — | MRS-DISP-059 (the 900 s budget ran out) |

**Three of seven** refusals became landings with no operator turn. Of the four that parked, three have a cause that
a story now removes, and the fourth was a spec error:

- **atlas 27.3:** the fix turn's own edits failed re-verification on spec-surface drift. Story 85.5 now runs the
  reconcile before re-verifying.
- **mason 27.2:** the fix turn cleared MRS-GATE-020 by moving the CFE edits into retro commits, then re-verification
  refused a `Co-authored-by: Cursor` trailer from the session's own earlier commit. Story 83.25 turns Cursor's
  attribution off at launch.
- **marshal 83.19:** a coverage floor needed more than one 900 s turn; the story was reworked by hand.
- **marshal 86.8:** its spec listed a manual check under `**Commands:**`, outside the station's `verify_commands`.
  MRS-GATE-011 fired only at verification, after the whole build. A fix turn cannot edit the spec, so it could only
  park (finding 4).

## Findings

1. **The fix turn works where the cause is in the code** (three of three such refusals cleared, in 60-589 s), and
   parks honestly where it is not. Keep it ON in dev and staging; the parks above are the input for the next
   tightening, not a reason to switch it off.
2. **A landing finalize promotes the twin's epic roll-up but leaves the Tier-3 feed's epic row stale.** After 41.6
   and 85.5 landed, the feed still read `epic-41: in-progress` (doctor) and `epic-85: in-progress` (marshal) while
   the twins read `done`. The next `sprint-ledger-sync` for each station refused ("feed would un-finish 1 twin key")
   until the feed row was reconciled by hand. Story 83.21 made finalize write the sync's roll-ups to the twin; the
   feed half is missing. → `DW-marshal-retro-2026-10-04-1`.
3. **An operator pause is not a first-class hold.** The operator paused #1861 (85.5) as a draft. The fleet campaign
   still re-dispatched 85.5 (a new Cursor session); only the draft stopped the merge (MRS-DISP-020, "Pull Request is
   still a draft"). → `DW-marshal-retro-2026-10-04-2`.
4. **MRS-GATE-011 is judged only at verification.** A spec whose `**Commands:**` names a command outside the
   station's `verify_commands` is knowable at dispatch time, before any session starts. 86.8 spent a build and a
   fix turn to learn it. → `DW-marshal-retro-2026-10-04-3`.
5. **Chain-currency reads history, not the net change.** 83.19's branch added a `pyforge-testing-kit` dependency to
   marshal's `pyproject.toml` and removed it again; the bytes on `main` did not change, but `fleet_scan` dates the
   code stage from the last commit touching the file, so the merge moved marshal's code stage and turned
   `detectors-ci` red until this retro. → `DW-marshal-retro-2026-10-04-4`.
6. **A land-only re-dispatch blocks its caller until CI finishes.** `marshal factory dispatch` for a `done` story
   (mason 27.2) runs the spec-surface reconcile, opens the PR and then waits on checks in the foreground; an outer
   `timeout 300` killed it mid-wait. Nothing was lost (the PR stayed open and landed by hand), but the CLI gives no
   sign that it will wait. Recorded here only; no row.

## What went well

- The dormant-then-ON rollout (85.1 dormant, 85.3 the safety review, then ON in dev) let three reviews find the
  redaction ReDoS (85.4) before the fix turn ran on real refusals.
- Fixing review findings forward into their own epic (85.4 after 85.3, then 85.5) kept Epic 85 one story line, the
  operator's 2026-10-04 ruling in practice; doctor Story 41.5 made the reopen pass `ledger-regression`.

## Action items

| Item | Owner | Where |
|---|---|---|
| Finalize also writes the feed's epic rows it writes to the twin | marshal | `DW-marshal-retro-2026-10-04-1` |
| An operator hold that dispatch and drain campaigns read before launching | marshal | `DW-marshal-retro-2026-10-04-2` |
| MRS-GATE-011 refuses at dispatch launch, before the session | marshal | `DW-marshal-retro-2026-10-04-3` |
| The chain code stage dates a content change, not a touched-then-restored file | doctor (`fleet_scan`) | `DW-marshal-retro-2026-10-04-4` |
| Cursor sessions never attribute commits | marshal | Story 83.25 (chained in #1865) |
| The 83.19 review's fixes | marshal | Story 83.24 (chained in #1865) |
| The dead mypy override for the deleted `pyforge.marshal.cli.chain` | marshal | closed in this retro (`DW-marshal-86-8-1`) |
