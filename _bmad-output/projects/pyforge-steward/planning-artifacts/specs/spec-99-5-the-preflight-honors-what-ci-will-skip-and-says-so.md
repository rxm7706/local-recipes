---
title: '99.5: The preflight honors what CI will skip, and says so'
type: 'feature'
created: '2026-10-13'
status: 'done'
baseline_revision: '6587b1d7aa69be2794a44853646def731b56d856'
flag:
  key: pyforge.steward.ci_pause_control       # Story 99.3's (one flag per CAP)
  provider: openfeature-file                  # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # Story 99.3's values
  scope: global                               # v1 is global only
  fallback: lane selection uses Story 99.2's declared-state resolver with no snapshot and no banner
  cleanup: with Story 99.3's flag, 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-99-2-every-ci-job-carries-its-pause-switch.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-99-3-the-operator-sees-the-pause-state-of-every-ci-surface-in-one-command.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_ci.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py
  - scripts/pre_push_preflight.sh
  - scripts/platform-ci-local.sh
  - scripts/guild_image_ci.sh
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The local pre-push gate cannot see which CI jobs are paused. Before Story 99.2 it ran every lane with a
`vars.*` term; after 99.2 it resolves `vars.*` from the registry's declared state, which goes stale the moment the
operator flips a variable in the UI. Nothing tells an author, before the run, that a lane will be skipped in CI, and
the manual twins (`platform-ci-local`, the guild image build) run their paused CI twin with no word.

**Approach:**

- **Resolution order in `preflight_ci`.** With the flag on: a `.steward/ci-vars.json` snapshot (Story 99.3's `ci vars
  --refresh`) no older than 24 h wins; a stale or absent snapshot falls back to Story 99.2's declared state. The
  source used (`snapshot <age>` or `declared`) is journaled once per run and printed in the banner.
- **Banner and journal.** Before any lane runs, `pr-preflight` prints one banner line per paused lane:
  `paused in CI: <lane> (<SWITCH> since <date>, review_by <date>)`. Each such lane is journaled
  `skipped: paused in CI (<SWITCH> since <date>, review_by <date>)` in `.steward/preflight-runs.jsonl` and is not run.
  `--ignore-ci-pauses` runs them and journals that it did (ruling Q3).
- **Pre-push hook.** `scripts/pre_push_preflight.sh` prints the same banner (it calls the preflight, so the banner
  comes from one place).
- **Manual twins.** `scripts/platform-ci-local.sh` and `scripts/guild_image_ci.sh` print the banner for their paused
  CI twin and still run every stage the caller asked for (they are the way to exercise a paused surface on purpose).
  They read the banner from one steward entry point, never from a copy of the registry logic.
- **Flag off.** Selection is Story 99.2's declared-state resolution with no snapshot and no banner.

Ledger key: `99-5-the-preflight-honors-what-ci-will-skip-and-says-so`.
Type / Effort / Deps: feature / M / S-99.2, S-99.3.

### Living CAP citations

- **`spec-pyforge-steward` CAP-166** (FR-39): preflight parity; **CAP-159** (lanes read from the workflows);
  **CAP-154** (the pre-push hook).
- **AD-1**, **AD-8**.
- **Flag:** Story 99.3's `pyforge.steward.ci_pause_control`.
- **Origin.** The 2026-10-12 Dream entry; ruling Q3.

## Acceptance Criteria

- **AC1 — Snapshot wins when fresh.** With a snapshot 1 h old setting `PAUSE_CONTAINER_BUILDS=true`, the lanes the
  `guild-container` job selects are skipped; the banner names `snapshot 1h`.
- **AC2 — Stale falls back.** With a 25 h snapshot that says otherwise, the declared state decides and the banner
  names `declared`.
- **AC3 — Journal and override.** A skipped lane journals the exact `skipped: paused in CI (…)` line;
  `--ignore-ci-pauses` runs it and journals the override.
- **AC4 — Hook and twins.** The pre-push hook output contains the banner; `platform-ci-local.sh` and
  `guild_image_ci.sh` print it and still run their requested stages (fake-subprocess tests).
- **AC5 — Flag off.** Selection equals Story 99.2's; no banner; no snapshot read.

## Boundaries & Constraints

- No lane outside the paused set changes selection.
- The snapshot is read-only here; Story 99.3 writes it.
- The twins never skip a stage the caller asked for.

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| snapshot unreadable JSON | treated as absent, banner says so, declared state decides |
| a lane selected by two jobs, one paused | the lane runs (one unpaused job still needs it) |
| `PAUSE_ALL_CI=true` in the snapshot | every push/PR lane journaled paused; `--ignore-ci-pauses` runs all |
| `PYFORGE_PREFLIGHT_SKIP=1` | unchanged: the whole preflight skips and journals, as today |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-166 (FR-39), minted 2026-10-12.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-12 (ci pause control plane) entry.
- Epic: Epic 99, Stories 99.1–99.7.
- Ledger key: `99-5-the-preflight-honors-what-ci-will-skip-and-says-so`.
- Ledger status at mint: `backlog`.
- Deps: S-99.2, S-99.3. `marshal factory dispatch` stamps `baseline_revision` with the launch commit.
- Surface: `marshal-policy.toml` `[epic_surfaces]."99"`.
- Specced 2026-10-13 from the epic's text ahead of its dependencies' landing; the implementing session reads the
  landed resolver and `ci` duty first.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_preflight_ci.py src/shared/packages/pyforge-steward/tests/unit/test_preflight.py -q` — expected: pass (AC1–AC3, AC5).
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts -q -k "pre_push or platform_ci_local or guild_image"` — expected: pass (AC4).
- `pixi run --frozen -e pyforge-guild detectors-ci` and `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0, with the banner naming the two live pauses.

## Auto Run Result

Status: done
Verification: pyforge-steward-test (2568 passed), test_preflight_ci + test_preflight, tests/scripts (pre_push/platform_ci_local/guild_image/ci_pause_twin), spec_surface_reconcile OK; pr-preflight prints declared-source banner for live PAUSE_CONTAINER_BUILDS and PAUSE_PLATFORM_CONTAINER_BUILDS.

## Spec Change Log

- 2026-10-13: specced from Epic 99's Story 99.5 text ahead of its dependencies' landing so the steward chain runs
  unattended (operator direction 2026-10-13).
