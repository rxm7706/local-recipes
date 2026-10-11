---
title: 'pyforge-marshal — Retrospective (2026-10-11: held landings, review loops and a reverted liveness change)'
project: pyforge-marshal
date: '2026-10-11'
created: '2026-10-11'
updated: '2026-10-11'
scope: 'Story 93.1 changed pyforge-marshal/pyproject.toml (the wheel force-includes data/bmad_loop_plugins; the import contract lists pyforge.marshal.data), which moves the chain''s code stage past the last marshal retro (2026-10-08) on the code→retro currency edge. This note covers what 2026-10-10..11 taught the dispatch and landing path: independent landing reviews, a reverted liveness change, and three landing-path defects that each needed an operator hand.'
evidence:
  - 'PR #2106 (revert of Story 90.1: psutil process_iter(["pgid"]) raised on psutil 7.2.2 and the error counted as alive)'
  - 'Story 92.1 (PR #2114, held): independent review iterations 1 and 2 sent back (tests did not catch the reverted 90.1 bug; MRS-DISP-064 collided with Story 93.1)'
  - 'Steward 87.5 (PR #2111, held): MRS-DISP-063 refused a passed review (blame time 0), then MRS-DISP-020 on a still-draft PR'
  - 'Marshal 86.2 (PR #2110): landing refused on a red head before it re-merged main (MRS-DISP-056)'
  - 'PR #2113: doctor live-tree Dream count re-pinned after PR #2112 archived a row-less Dream without triggering doctor-test'
---

## What happened

- **A liveness change broke every dispatch and was reverted.** Story 90.1 read the session's process group with
  `psutil.process_iter(["pid", "pgid", ...])`; `pgid` is not an attribute on psutil 7.2.2, the read raised, and the
  error was treated as "alive", so every run whose session had exited read as live. A stale run whose worktree had
  been swept also crashed `marshal factory dispatch` (`VcsCommandError` from `gather_dispatch_git_facts` on a
  missing worktree). The code was reverted (PR #2106) and Story 92.1 re-does it.
- **A green in-session review is not a landing review.** 92.1's own review pass recorded 0 findings; the first
  independent review found the tests passed with the reverted 90.1 bug put back, a pid-reuse hole, and three ACs
  never wired into production callers. The second found its new finding code already taken on main.
- **Finding codes are minted on a branch and collide on main.** 92.1 and 93.1 both took `MRS-DISP-064` within hours;
  nothing checked the registry against `origin/main` until a reviewer merged it by hand.
- **The land-only review gate misread its own log.** Story 89.1 orders Review Triage Log headings by blame time, but
  `_parse_blame_porcelain` reads `git blame --porcelain`, which prints `committer-time` only on a commit's first
  line; later lines of the same commit read 0. A passing entry committed with a frontmatter edit read older than
  the earlier "sent back" entry, and MRS-DISP-063 refused it. Story 94.1 fixed the parser.
- **A held PR is never released.** Story 83.18 turns a held PR into a draft; nothing turns it back when
  `landing_review: passed`, so `gh pr merge` fails (MRS-DISP-020). Story 94.2 is minted for it; until it lands the
  operator runs `gh pr ready`.
- **A refused landing re-checks the stale head.** With main fixed, 86.2's land-only re-dispatch still refused on the
  branch's last red head (MRS-DISP-056) instead of merging main first and letting CI re-run; main had to be merged
  by hand (the 2026-10-08 retro's candidate 2, again).
- **A planning-only PR turned main latently red.** PR #2112 archived a Dream with no README row; doctor's live-tree
  count test pins that number, and #2112's paths did not trigger doctor-test, so the next PR that did (86.2's
  landing) failed on it.

## What we changed

- 90.1 reverted (#2106); 92.1 in review with real-process liveness tests and the AC11 mutation table.
- 94.1 landed: per-line committer time (`--line-porcelain`), with a regression test that commits a frontmatter edit
  and a later heading together.
- 94.2 minted (this chain): land-only marks the PR ready when `landing_review: passed`, then merges.
- Operator practice: every security- or liveness-sensitive story dispatches with `--hold-landing` and gets an
  independent review before it lands; a send-back records the findings in the story spec, the fixes land on the
  branch from a separate implementer, and a fresh reviewer gates the next iteration.

## Candidate fix stories (not minted here)

1. Refuse a branch whose finding-code registry collides with `origin/main`'s at verify time (a merge-tree check over
   `core/findings.py`), not at merge time.
2. On a land-only re-dispatch, merge `origin/main` into the branch and let CI re-run before reading the head's checks
   (carried from the 2026-10-08 retro, candidate 2).
3. A PR that moves or adds a Dream runs doctor's dreams-hygiene tests in its own lanes, or the live-tree count is
   derived rather than pinned.
4. Treat a dispatch run whose worktree is missing as not live everywhere (Story 92.1 scope, landing pending).
