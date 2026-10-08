---
title: 'pyforge-marshal — Retrospective (2026-10-08: an eight-station drain through the landing path)'
project: pyforge-marshal
date: '2026-10-08'
created: '2026-10-08'
updated: '2026-10-08'
scope: 'Story 46.9 tightened pyforge-marshal/pyproject.toml (the mypy override that hid its Severity.HARD bug is removed), which moves the chain''s code stage (the code→retro currency edge; the last marshal retro is 2026-10-07). This note covers what a day of parallel dispatches across all eight stations taught the landing path.'
evidence:
  - 'Run pyforge-marshal-20261008T161751108Z-7a096d32 (Story 46.9: MRS-GATE-001 coverage gate, then MRS-DISP-059 fix-turn timeout)'
  - 'PRs #1928 (marshal 22.21), #1930/#1931 (steward 60.3/60.4), #1939 (herald 27.4), #1946 (steward 62.2), #1948 (herald 23.6), #1949 (steward 67.2): MRS-DISP-020/038 at merge time'
  - 'PR #1940 (herald fastapi/asgiref run-deps) cleared an MRS-GATE-014 pre-existing gate that refused 22.21'
  - 'PR #1941 (environment.yaml): a dispatch auto-checkpoint captured a pixi WARN line into the file'
---

## What happened

- **The one-story-per-station guard only counts the coding session.** MRS-DISP-021 is checked against a live
  session, so the next story on a station dispatches while the previous one is still verifying or landing. Two
  stories on one station then race to merge into the same files (steward `catalog.py`, `cli.py`, the duty-count
  tests; herald `sidebar_from_map.py`).
- **Merge-time conflicts are not healed.** A landing waits about twenty minutes for CI; when main moves in that
  window the PR becomes unmergeable and the landing refuses with MRS-DISP-020 (or MRS-DISP-038 for a path the heal
  does not know). Every one of these needed an operator merge of `origin/main`, a main-first union of memlogs and the
  team-memory index, and main's spec-surface baseline. The steward and herald conflicts were additive; nothing was lost.
- **A refused re-land verifies the stale branch.** Marshal 22.21's re-land kept failing `pyforge-deps-test` as a
  pre-existing gate (MRS-GATE-014) after the fix (#1940) was on main, because verification ran before main was merged
  into the branch.
- **A story added to a done epic rolled the epic back.** The chain that added 22.20 and 22.21 left `epic-22: done`;
  22.21's supervisor finalize rolled it to `in-progress` and `ledger-regression` refused. It cleared once 22.20 landed
  and the merge brought both stories to `done`.
- **A per-module mypy override hid a crash.** `pyforge.marshal.cli.benchmark` carried `disable_error_code =
  ["attr-defined"]`; every refusal path used `Severity.HARD`, which does not exist, so each refusal raised
  `AttributeError` instead of reporting its finding. Story 46.9's coverage gate surfaced it (78%), and the fix turn
  timed out (MRS-DISP-059) before finishing.
- **A landing merged without promoting** (herald 27.3), leaving `ledger-direction` red on main until
  `dispatch_land_finalize` was run by hand.

## What we changed today

- 46.9: `Severity.HARD` → `Severity.ERROR`; malformed leg JSON reports MRS-BENCH-002; 32 behavioural tests take
  `cli.benchmark` to 100%; the `attr-defined` override is removed (mypy is clean without it).
- Operator practice: dispatch queues wait for each story to land before dispatching the next on the same station.

## Candidate fix stories (not minted here)

1. Re-run the heal (merge `origin/main`, union, re-verify) when a merge is refused for mergeability, instead of
   MRS-DISP-020.
2. Merge `origin/main` into the branch before a land-only re-verification, so a pre-existing gate fixed on main does
   not refuse it.
3. Count a story that is verifying or landing as in flight for MRS-DISP-021/034.
4. A chain that adds a story to a `done` epic rolls the epic key in the same change (doctor 41.5's escape), so the
   first landing does not regress it.
5. Reject a mypy `disable_error_code` override on a module the story touches unless it is still needed.
