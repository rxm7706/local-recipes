---
title: '117.32: CI environments carry the headless Chromium they launch, not the full one'
type: 'chore'
created: '2026-11-27'
status: 'done'
story: 117-32-ci-environments-carry-the-headless-chromium-they-launch-not-the-full-one
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'pixi.toml'
  - 'pixi.lock'
  - 'docs/governance/pin-policy.yaml'
  - 'docs/governance/realization-register.yaml'
  - 'docs/how-to/run-and-read-pr-preflight.md'
  - 'docs/reference/environments.md'
  - 'docs/how-to/pixi-tasks.md'
  - 'docs/map.yaml'
  - 'docs/dreams/pyforge-unifying-strategy.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** A CI job's pixi setup is mostly its cache restore, which grows with the environment: 286 MB restores
in 3 s, 962 MB in 17 s. Four CI environments carry Playwright's full Chromium (403 MB) beside its headless shell
(273 MB) and ffmpeg, the set steward Story 131.1 locked:

| Environment | Size |
|---|---|
| `pyforge-atlas` | 2.5 GB |
| `platform-ci-test` | 2.2 GB |
| `pyforge-herald` | 1.5 GB |
| `detectors` | 1.1 GB |

Every Chromium launch in the code is headless, and a headless launch runs the shell. Deck QA and the deck trio ask
for the system's Chrome first, then fall back to the same headless launch. No detector launches a browser:
check-layout retired with the Guildhall console and now only refuses its blob's return.

**Approach:**

- `platform-ci-test`, `pyforge-atlas` and `pyforge-herald` keep `playwright-chromium-headless-shell` and
  `playwright-ffmpeg`, and drop `playwright-chromium`.
- `detectors` drops all three browser packages. It keeps `playwright-python`.
- A `playwright-full-chromium` feature carries `playwright-chromium` into `pyforge-foundry-full`,
  `pyforge-foundry-full-stack` and `pyforge-container`. These are the environments that had it and where a person
  may drive a headed browser.
- The lock is rewritten by `pixi lock` with the pinned pixi 0.85.0, never `pixi update`, and only loses records.
- `steward estate reconcile` regenerates what follows from `pixi.toml`.
- The pin policy names the feature that now holds each browser package.

Ledger key: `117-32-ci-environments-carry-the-headless-chromium-they-launch-not-the-full-one`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 (realized, no text change).
- Steward Story 131.1's browser set (spec-131-1), narrowed for these environments by the operator's ruling of
  2026-11-27.
- No AD moves.

## Boundaries & Constraints

**Always:**
- Every Chromium launch passes in the environments that keep the shell.
- The laptop and container environments keep the set they had.

**Never:**
- Never move a package other than the removed browsers.
- Never change a test, job or lane.

## Acceptance Criteria

**Given** the four environments installed from the new lock
**When** each launches Chromium as the code does
**Then** it launches from the headless shell, and each environment is smaller.

- **AC1 — The lock only loses records.** Expected: `0`.

  ```bash
  git diff origin/main -- pixi.lock | grep '^+' | grep -vc '^+++'
  ```

- **AC2 — Chromium launches from the shell.** In `platform-ci-test`, `pyforge-atlas` and `pyforge-herald`, this
  prints `launched 156.0.8078.4`, and `share/ms-playwright` holds `chromium_headless_shell-1248` and `ffmpeg-1013`
  only.

  ```bash
  pixi run --frozen -e <env> python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); b = p.chromium.launch(); print('launched', b.version); b.close(); p.stop()"
  ```

- **AC3 — The full preflight passes,** the station suites included: `pixi.toml` is a shared surface.

</intent-contract>

## Result (2026-11-27)

- **AC1:** `0`. The lock loses `playwright-chromium` from the four environments on every platform they lock, and
  `playwright-chromium-headless-shell`, `playwright-ffmpeg` and `playwright-browsers-base` from `detectors`.
- **AC2:** all three environments printed `launched 156.0.8078.4`. Sizes after the change:

  | Environment | Before | After |
  |---|---|---|
  | `platform-ci-test` | 2,198 MB | 1,753 MB |
  | `pyforge-atlas` | 2,530 MB | 2,046 MB |
  | `pyforge-herald` | 1,537 MB | 1,124 MB |
  | `detectors` | 1,087 MB | 407 MB |
- **`llms-full-check`:** clean.
