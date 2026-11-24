---
title: '131.1: Playwright''s browsers install from pixi on linux-64, osx-arm64 and win-64'
type: 'feature'
created: '2026-11-21'
status: 'done'
story: 131-1-playwright-s-browsers-install-from-pixi-on-linux-64-osx-arm64-and-win-64
spec: spec-pyforge-steward
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # tests, a gate's own module and the scripts a gate runs; a gated gate is a silent green (roster list)
surface:
  - 'recipes/playwright-*/**'
  - 'pixi.toml'
  - 'pixi.lock'
  - 'environment.yaml'
  - '.claude/skills/conda-forge-expert/**'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Pixi resolves the `playwright` driver to 1.63 in some environments and 1.64 in others, and the six browser recipes build for linux-64 only, at the 1.63 driver's revisions, so every browser-driving environment downloads its browser at run time.

**Approach:** Pin one driver across the estate; give each recipe a download and a sha256 per platform at that driver's revisions; build locally; name the packages in the browser-driving environments from a channel. The operator publishes to `SelfExplainML`.

Ledger key: `131-1-playwright-s-browsers-install-from-pixi-on-linux-64-osx-arm64-and-win-64`.

### Living CAP citations

- spec-pyforge-steward CAP-5 (realized, no text change); no AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Write `pixi.lock` only with the pixi version the workspace pins.

**Never:**
- Never upload a package, never submit a recipe to conda-forge, never name an unpublished package in the lock.

## Acceptance Criteria

**Given** pixi resolves the `playwright` driver to 1.63 in some environments and 1.64 in others, and the six browser recipes build for linux-64 only, at the 1.63 driver's revisions
**When** one driver is pinned across the estate, each recipe carries a download and a sha256 per platform at that driver's revisions and builds locally, and the browser-driving environments name the packages from a channel
**Then** every environment resolves one `playwright` version, each recipe builds for linux-64 and osx-arm64 (win-64 built or its blocker named), and a browser check runs on macOS with no `playwright install`
**And** the lock names the packages only once the operator has published them to `SelfExplainML`; until then the PR is a draft

- **AC1 — The recipes build.** Expected: exit 0 for each recipe on osx-arm64 and linux-64.

  ```bash
  pixi run -e local-recipes rattler-build build --recipe recipes/playwright-chromium --target-platform osx-arm64
  ```

- **AC2 — One driver across the lock.** Expected: one version.

  ```bash
  grep -oE 'conda-forge/[a-z0-9-]+/playwright-1\.[0-9.]+-' pixi.lock | sed -E 's|.*/playwright-([0-9.]+)-|\1|' | sort -u
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-5 (realized, no text change); no AD moves.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-11-21 entry; operator ruling of 2026-11-21.
- Epic: Epic 131, minted with this story.
- Ledger key: `131-1-playwright-s-browsers-install-from-pixi-on-linux-64-osx-arm64-and-win-64`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."131"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-21: minted from the station Dream's 2026-11-21 entry and the operator's ruling of the same date.
- 2026-11-23: closed. The 15 packages are on `SelfExplainML` (operator upload 2026-11-23; every sha256 matches `pixi.lock`), PR #2376's CI is green on every workflow, and the full `pr-preflight` passed all 48 lanes. Renumbered from 129.1, then 130.1, as main landed its own Epics 129 and 130.
