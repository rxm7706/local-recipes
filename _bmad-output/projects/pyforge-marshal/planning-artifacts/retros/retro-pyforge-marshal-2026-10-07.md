---
title: 'pyforge-marshal — Retrospective (2026-10-07: the landing path met concurrent landings)'
project: pyforge-marshal
date: '2026-10-07'
created: '2026-10-07'
updated: '2026-10-07'
scope: 'Story 22.17 landed on 2026-10-07 and added pyforge.marshal.dispatch_verification_journal to pyforge-marshal/pyproject.toml, which moves the chain''s code stage (the code→retro currency edge; the last marshal retro is 2026-10-04). This note covers what the day''s dispatches taught the landing path: nine landings across five stations, and the four marshal fix stories they produced (22.15–22.19).'
evidence:
  - 'Story 22.17: PR #1899, merge 609fad9d18 (hand-landed after an operator merge of origin/main and a test fix)'
  - 'Chains: PR #1895 (Stories 22.15–22.17); the 22.18/22.19 chain on branch chain-marshal-baseline-heal-2026-10-07'
  - 'Runs pyforge-herald-20261007T055516715Z-20c28cc4, pyforge-steward-20261007T055444723Z-4d4c948e, pyforge-warden-20261007T055413377Z-abbfa51f (MRS-GATE-002, python not on PATH)'
  - 'Run pyforge-warden-20261007T093623012Z-77c754d3 (MRS-DISP-038 on the baseline and the flag registry)'
---

## What happened

- **Three dispatches lost their verification to the launch environment.** They were launched with the env's `marshal`
  binary instead of `pixi run`. Each session finished, then the supervisor could not find `python` for the surface
  guard and refused at MRS-GATE-002. Story 22.16 makes that a launch-time refusal, or runs the guard under the
  supervisor's own interpreter.
- **A land-only refusal said nothing about why.** Warden 14.2 and steward 74.2 came back `skipped-unverified` with
  no finding naming the gate. A hand replay showed the verification passing; the likely cause was two
  `platform-ci-local` runs sharing fixed ports. Story 22.17 (landed) surfaces every verification finding and journals
  it. Steward Story 63.7 gives `platform-ci-local` a lock.
- **Landings conflicted with each other on shared files.** Every landing that stamps
  `scripts/.spec-surface-baseline.json` conflicts with any landing that stamped it since, and every flag story appends
  to the same four registry files. The heal refused both as unknown paths (MRS-DISP-038), so each needed an operator
  merge. Stories 22.18 (baseline) and 22.19 (flag registry) make both mechanical.
- **A landed story kept its epics line at `backlog`.** When the session sets the spec to `done`, the landing's early
  return skips Story 22.13's epics flip. Doctor's epics meta-test then failed on main after doctor 34.6 landed, until a
  hygiene PR (#1905) set the lines. Story 22.15 fixes the cause.
- **22.17's new tests passed locally and failed in CI.** They reached the real session-harness probe, and the runner
  has no `cursor-agent`. They now pass `FakeBuildHarness`, as the other land-only tests do. A marshal test that calls
  `dispatch_once` should never depend on a harness binary.

## What to carry forward

- Launch every dispatch with `pixi run -e pyforge-guild marshal …` until 22.16 lands.
- Land one story at a time while 22.18 and 22.19 are open; merge `origin/main` into a refused branch, union the
  memlogs and the flag registry main-first, take main's baseline, and re-land.
- Run a new marshal test module with `cursor-agent` off `PATH` before pushing.
- A hand landing (`gh pr merge --merge --subject "Merge <slug>/<key> into main"`) still needs its ledger promotion and
  any `code→retro` retrospective in the same pass.
