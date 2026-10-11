---
title: 'pyforge-herald — Retrospective (2026-10-11: one real ship lands on the host plus sidecar, and the CI demo retires)'
project: pyforge-herald
created: '2026-10-11'
updated: '2026-10-11'
scope: 'Story 36.1 changed src/shared/packages/pyforge-herald/pyproject.toml after the last herald retro (2026-10-07), which moves the chain''s code stage past it on the code→retro currency edge. This note covers Stories 19.2 and 36.1 landing, and the fix story 37.1 their reviews surfaced.'
evidence:
  - 'Story 19.2: PR #2123 (merge ba613abab3); independent gap review iteration 1 sent back, iteration 2 passed'
  - 'Story 19.2 dispatch run pyforge-herald-20261011T145445292Z-69725fea (reused a pre-sidecar branch; landing refused at MRS-DISP-038)'
  - 'Story 36.1: PR #2128; dispatch refused at launch with MRS-DISP-050 until its Verification Commands were split (PR #2124)'
  - 'Story 37.1 minted (PR #2126) from DW-herald-19-2-1'
---

## What happened

- **A dispatch reused a stale branch.** Story 19.2's 2026-10-11 dispatch found `dispatch/pyforge-herald/19.2` from
  2026-10-10, built before the sidecar re-scope, with its spec reading `done` on the branch only. The run took the
  follow-up review path and tried to land code written for the old topology; the landing was refused only because the
  spec conflicted with main. An independent gap review against the current spec then found the live restart test
  broken and the how-to describing the old topology; an implementer closed eleven items and a second review passed.
- **A story's Verification named commands outside the station's policy.** Story 36.1 listed doctor, scripts,
  registry and docs checks under `**Commands:**`; marshal's spec binding refused the launch (MRS-DISP-050). The fix
  keeps `**Commands:**` to herald's `verify_commands` and moves the rest to a "Run before the push" list.
- **A session ended before its own review.** Story 36.1's session stopped externally after the supervisor verified
  the branch, leaving the spec `in-progress` with no Review Triage Log; land-only refused (MRS-DISP-063). It was
  hand-landed with an independent review running alongside.
- **A review found a defect outside the story.** On a host without herald, the django-herald portal's module-level
  `pyforge.herald` import broke `manage.py migrate` and made the host's Django pages answer 500 (DW-herald-19-2-1).
  Story 37.1 fixes it the way steward 87.1 did for the station API seam.

## What we changed

- 19.2: `herald-ship-local` drives a real landing through the platform host into the mcp-host sidecar on 127.0.0.1;
  the how-to is rewritten for that topology and every command in it was run end to end.
- 36.1: the disabled `herald-live-demo.yml` moved to `archive/.github/workflows/` and its readers followed.
- 37.1 minted (Epic 37): the herald portal loads without herald and says why.

## Candidate fix stories (not minted here)

1. A dispatch that finds an existing branch whose spec reads `done` but predates a later re-scope on main should
   refuse, not run a follow-up review and land.
2. Mint-time binding check: refuse a story spec whose `**Commands:**` names anything outside the station's
   `verify_commands` before the chain merges, not at dispatch.
3. When a session stops before its review step, the supervisor should record the missing review and hold the
   landing for an independent one instead of opening a landable PR.
