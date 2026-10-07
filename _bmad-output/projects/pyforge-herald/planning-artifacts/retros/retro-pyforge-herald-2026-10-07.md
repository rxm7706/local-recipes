---
title: 'pyforge-herald — Retrospective (2026-10-07: the deck exports move toward the object store)'
project: pyforge-herald
created: '2026-10-07'
updated: '2026-10-07'
scope: 'Two dispatched stories on one day. Story 28.1 (CAP-53) pruned the superseded dated exports and made deck_versions the one rule; Story 29.1 (CAP-54) added the deck store and `herald deck publish` behind the flag pyforge.herald.deck_publish, and added boto3 to the package. The boto3 line moved pyforge-herald/pyproject.toml, so the `code→retro` currency edge fired; this is the retrospective that follows it.'
evidence:
  - 'Story 28.1: PR #1892, merge 6b3a1c4c30, ledger promotion 966b166f76'
  - 'Story 28.1 dispatch run pyforge-herald-20261007T055516715Z-20c28cc4 (verification refused at MRS-GATE-002)'
  - 'Story 29.1 dispatch run pyforge-herald-20261007T072057214Z-deab4f99 (verification refused at MRS-GATE-001, then the verify-fix turn)'
  - 'src/shared/packages/pyforge-herald/pyproject.toml and pixi.toml [feature.pyforge-herald]: boto3 >=1.43.75'
---

## What happened

- **Story 28.1 was finished by its session but refused by the verifier.** The dispatch was launched with the env's
  `marshal` binary instead of `pixi run`, so `python` was not on the supervisor's PATH and the surface-reconcile guard
  could not run. An operator re-ran every check on the branch, and the story then landed through the land-only path with
  all 19 CI checks green.
- **The re-verify found a contract gap in 28.1.** The story's Surface line says
  `deck_versions [--root presentations]`, but the module took a positional path. A `--root` argument was read as a
  directory named `--root` and the check passed on any tree. `main()` now parses `--root` and exits 2 when there is no
  `presentations/` directory.
- **28.1's memlog entries made the herald and doctor Specs stale.** The chain-currency detector dates the Spec stage by
  its memlog, so the required surface-reconcile entries moved both Specs more than 2 days past their PRDs. The landing
  carried the runbook cascade for both stations. Doctor is minting a fix for the detector rule.
- **Story 29.1's first verification failed in the core suite.** `DeckStoreConfigurationError` was not a `PyforgeError`
  (core's CAP-5 error-root guard), and the flag's per-environment values were not yet in `flag-overlays.json`. The
  verify-fix turn fixed both and extended the deck-store tests. The fix turn added an import after the pre-verify ruff
  pass, so `lint-types` failed on import order until an operator sorted it.

## What to carry forward

- Launch every dispatch with `pixi run -e pyforge-guild marshal factory dispatch …`. Marshal is minting a launch-time
  refusal for a missing interpreter.
- A flag story registers its key in four places before verification: `flags.json`, `flag-overlays.json`, core's
  `test_flags.py` and the platform's `_SHIPPED_BOOLEANS` (`docs/reference/story-spec-flag-block.md`).
- An error class a station defines derives from `pyforge.core.errors.PyforgeError`; core's suite enforces it.
- A dependency added to the package's `pyproject.toml` moves the `code` stage. Plan a short retrospective like this one
  in the same landing.
- `docs-site/src/lib/site-url.mjs` is ignored by the root `.gitignore` rule `lib/` and was never tracked, so the
  Starlight docs site cannot build from a clean checkout (FR-8.1, AD-21). It needs its own fix story.
