---
title: 'pyforge-marshal — Retrospective (2026-09-26: Epic 46 lands, the harness range moves to bmad-loop 0.12)'
project: pyforge-marshal
created: '2026-09-26'
updated: '2026-09-26'
scope: 'Everything in marshal''s tree since the 2026-09-20 retro: Stories 53.3, 46.1, 46.2, 46.3, 46.6 landed (PRs #1554-#1597 era); Epic 54 / CAP-265 minted; the MRS-DISP-049 verdict-classification crash fixed (PR #1603); and the bmad-loop runtime range widened to <0.13 with the estate build channel-pinned (PR #1607).'
evidence:
  - 'git log --since=2026-09-20 -- src/shared/packages/pyforge-marshal _bmad-output/projects/pyforge-marshal (46.x landings, a1e5f55a5c MRS-DISP-049, 244ac7eb83 the cap)'
  - 'spec-pyforge-marshal/.memlog.md entries 2026-09-20 .. 2026-09-26 (surface reconciles for 53.3, 46.1, 46.2, 46.6; CAP-265 self-validate; the 2026-09-26 cap reconcile)'
  - 'pixi run -e pyforge-marshal pyforge-marshal-test — 8652 passed in an env re-solved onto bmad-loop 0.12.0'
---

## What landed

- **Epic 46 (the substrate and the session path):** 46.1 `marshal context bootstrap` (a bare clone
  fetches-and-verifies the substrate-nightly pair), 46.2 `marshal context bundle --epic N
  [--expect-digest]` (digest-pinned bundles), 46.3 `scribe capture` named as the session-close
  ritual across the instruction surfaces, 46.6 the persistence advisory for a session whose layers
  lapse (CAP-193). 46.9 / 46.10 remain queued.
- **53.3** — 96 ports-driven unit tests for the dispatch supervisor main loop and a coverage floor
  for it (CAP-264); doctor 24.1 then moved the coverage-gate tests marshal was hosting for other
  stations out of marshal's tree (spec-coverage-gate-independence).
- **Epic 54 / CAP-265 minted** (a landing's ledger promotion repairs its own feed drift); the
  2026-09-24 chain reconcile registered FR-211. Story 54.1 is still `backlog`.
- **MRS-DISP-049 registered in `_CLASSIFY_TABLE`** (PR #1603): steward 63.4's new session-precondition
  finding crashed every dispatch launch whenever `steward session check` was non-ok, because the
  verdict table had no entry for it. The fix sat un-PR'd on a branch for most of a session.
- **bmad-loop 0.12.0 admitted** (PR #1607): `>=0.11.0,<0.12` → `<0.13` in pyproject, the package
  manifest and the FR-52 range constants, after verifying the four lazily-imported modules ship and
  the suite is green on 0.12.0.

## What the period found

- **A new finding code is not registered until the verdict table says so.** DISP-049 shipped with
  its emitter and no `_CLASSIFY_TABLE` row; nothing red until a real launch hit the non-ok branch.
  The classification table needs a meta-test that every `MRS-*` code the package can emit has a row
  — file it against the verdict module if none exists.
- **Three spellings of one range.** The pyproject pin, the package manifest pin and the FR-52
  constants moved together only because `test_manifest_sync.py` refuses otherwise; four fixture
  tests also encoded the old ceiling (`0.12.2` as "same major, out of range") and had to move to
  `0.13.2`. When a range moves, grep the tests for the literal too.
- **Upstream now validates what marshal guarded.** bmad-loop 0.12.0's `bmadconfig` raises
  `BmadConfigError("… must contain a top-level mapping")` on a list-shaped `config.yaml`, ahead of
  marshal's "invalid bmad-config shape" guard. The contract (never raise, report) holds; the guard
  is now a second line, not the first.
- **conda-forge ships bmad-loop.** `conda-forge/bmad-loop-feedstock` (2026-09-20, not this repo's)
  gates `__unix` and adds `tmux`/`rich`/`httpx`. Under strict channel priority it shadowed the
  estate's ungated SelfExplainML build and killed every win-64 solve; `pixi.toml` now pins the
  dependency to SelfExplainML in the marshal and local-recipes features. Loop homes take bmad-loop
  from these environments, so the pin decides what every drain runs.
- **Attention items that are not work:** the two `MRS-DISP-020` landing refusals still shown for
  doctor 30.3 / marshal 46.6 after both landed by hand, and the three atlas baseline-drift defers whose
  stories were retired or reminted, are recorded as `DW-marshal-disp020-stale-refusal-2026-09-25`
  and `DW-marshal-baseline-drift-supersession-2026-09-25`. The single-shared-marker launch limit
  (`MRS-DISP-041`) is seeded on the Dream (PR #1601), not yet specced.

## What to carry forward

- Run the harness range check the way the FR states it: module set present, suite green on the
  admitted release — then move all three spellings and the test fixtures in one commit.
- Before assuming a SelfExplainML package is estate-only, `lookup_feedstock` it; the cfe
  `on-conda-forge` fields are hints (G78).
- 46.9 / 46.10, 47.1–47.4, 54.1 stay queued for the next drain; the MRS-DISP-041 marker limit
  still needs its Spec before two stations can dispatch concurrently.
