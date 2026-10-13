---
title: '100.4: The refreshed estate proves itself in every environment and every station suite'
type: 'feature'
created: '2026-10-13'
status: 'ready-for-dev'
baseline_revision: '233e07909b5f7e89e49744cdeb642cdc0985b177'
flag:
  key: pyforge.steward.estate_refresh          # Story 100.2's (one flag per CAP)
  provider: openfeature-file                   # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # Story 100.2's values
  scope: global                                # v1 is global only
  fallback: the `estate verify` and `estate status` verbs refuse naming the flag; no lane, install or probe runs
  cleanup: with Story 100.2's flag, 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-100-2-one-command-moves-the-library-pins-on-the-policy-and-restores-what-the-upgrade-loses.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-100-5-a-moved-pin-is-realized-not-just-locked.md
  - docs/intake/estate-refresh/PLAN-2026-10-13.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_ci.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py
  - scripts/sbom_laptop_gate.py
  - scripts/ensure-local-recipes-env.sh
  - docs/governance/ci-surfaces.yaml
  - pixi.toml
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Nothing proves a refreshed `pixi.toml` across the estate before the push — 36 environments on three
platforms, ten suites, the platform's own CI, the laptop SBOM gate — and the one signal today is CI after the fact
(`docs/intake/estate-refresh/PLAN-2026-10-13.md` § 4, gap 4). A tree that already has an environment installed
short-circuits `pixi install --frozen` and passes where a clean checkout fails (team memory 2026-07-30), and
container lanes are paused in CI (CAP-166), so "green" needs a definition.

**Approach:** `estate verify`, a verb on Story 100.2's duty, run in a detached worktree, in tiers, with every
realization probe, every row carrying its platform.

- **Worktree.** `git worktree add --detach <path> <branch-tip>` under the repo's scratch area (gitignored),
  removed when done, kept under `--keep`; the working tree is never installed into (fnd:AD-23 — CI evidence is a
  real local run).
- **Environments (ruling Q12).** The default tier: `pyforge-guild`, `pyforge-core`, `pyforge-testing-kit`, the
  eight station envs (`pyforge-atlas`, `-doctor`, `-herald`, `-marshal`, `-mason`, `-scribe`, `-steward`,
  `-warden`), `platform-ci-test`, `pyforge-foundry-full` (fnd:CAP-12's laptop SBOM). `--all` adds every other
  environment in `[environments]` (36 today, read from `pixi.toml` through `provision.py::load_pixi_environments`,
  FR-14 — never a list). For each: `pixi install --frozen -e <env>`, verdict by exit code, wall time, `du -sm`
  delta against the previous journal. A feature whose `platforms` excludes this platform is a `lock-solved` row,
  and `osx-arm64` and `win-64` are `lock-solved` rows for every environment, proven by one `pixi lock --check`
  (ruling Q14).
- **Lanes.** The lanes `preflight_ci` selects for a diff touching `pixi.toml` (CAP-159: read from the workflow
  files, never a copy): `lint-types`, `detectors-ci`, every station suite through `pyforge-station-tests`, the
  coverage gates, `platform-ci-local -- --test`, the `local-recipes` `test-ci`. CAP-166's declared pauses are
  honored: a paused lane is journaled `skipped: paused in CI (<SWITCH> since <date>)` with its switch, never run
  silently, and `--ignore-ci-pauses` runs it (Story 99.5's rule, read from `docs/governance/ci-surfaces.yaml` once
  Story 99.1 has landed; until then every lane runs). Plus the laptop SBOM gate (`sbom-laptop-gate`), the
  recipe-factory import smoke (`verify-env`), `pin_policy_check.py --fan-out`, every realization-register row's
  `probe` and each distinct register `test` once (Story 100.5). The atlas Chromium/DuckDB/WASM gate (`CI=1`),
  herald's browser check and scribe's Postgres lane (`scribe-pg-up` first) are `manual` rows carrying their command
  — never silently green.
- **Verdict.** One red environment, lane, fan-out finding or probe (`stale`, `missing`) reds the run with a
  documented exit code (AD-8); an installed `bmad-method` core below the pinned floor is `stale`. The journal's
  `verify` block: one row per environment, lane and probe with `platform`, verdict, exit, seconds, size delta.
  `estate status` prints, per platform, the lock (`pixi.lock` sha) it last confirmed.
- **Scoping.** `--env <name>`, `--lane <name>`, `--probe <package>` re-run one; `--all`; `--keep`.

Ledger key: `100-4-the-refreshed-estate-proves-itself-in-every-environment-and-every-station-suite`.
Type / Effort / Deps: feature / M / S-100.2, S-100.5.

### Living CAP citations

- **`spec-pyforge-steward` CAP-167** (FR-40): the verify verb and the per-platform confirmation.
- **CAP-5** (the Guild's 2 GB bound): the Guild's cold install is recorded against it. **CAP-159**: lanes are read
  from the workflows. **CAP-162**: the kit probes read `marshal seed check --json`'s envelope. **CAP-166**: pauses
  are honored and named. **FR-14**: environments are read from `[environments]`.
- **AD-1**: `pixi`, `git`, every lane and every probe by subprocess. **AD-8**: child exit codes recorded,
  `main()` projects the duty's. **fnd:AD-23**: a real local run in a fresh tree.
- **Flag:** Story 100.2's `pyforge.steward.estate_refresh`.
- **Origin.** The 2026-10-13 Dream entry; rulings Q12 and Q14 (asked and answered 2026-10-13).

## Acceptance Criteria

- **AC1 — Fresh tree, right tier.** With a fake `git` and `pixi`, `estate verify` records `git worktree add
  --detach` first, then `pixi install --frozen -e <env>` for exactly the default tier (read from a fixture
  `pixi.toml`), and for every environment under `--all`; no argv targets the working tree; a feature whose
  `platforms` excludes the fixture platform yields a `lock-solved` row and no install.
- **AC2 — Lanes from the workflows, pauses honored.** The lanes recorded equal `preflight_ci`'s selection for a
  `pixi.toml` diff on the fixture workflows; with a fixture registry pausing `guild-container`, that lane is
  journaled `skipped: paused in CI (PAUSE_CONTAINER_BUILDS since 2026-10-04)` and not run; `--ignore-ci-pauses`
  runs it; the three manual rows appear with their commands and no verdict.
- **AC3 — Probes and tests.** Every register row's `probe` runs once and each distinct `test` once; a fixture
  manifest at 6.12.0 against a 6.12.2 lock yields `stale` and a red run; `--probe bmad-method` runs only that
  probe.
- **AC4 — Platforms.** Every row carries `platform`; `pixi lock --check` runs once and `osx-arm64` and `win-64`
  rows read `lock-solved`; `estate status` prints, per platform, the lock sha last confirmed, with the two others
  `lock-solved`.
- **AC5 — Verdict and journal.** One faked red lane reds the run with the documented code; the journal validates
  against the schema with the `verify` block; the Guild row carries its `du -sm` against the 2 GB bound; `--keep`
  leaves the worktree and says where.
- **AC6 — Nothing live.** No test installs an environment, runs a lane or touches the network; `git worktree` is
  faked.

## Boundaries & Constraints

- The working tree is never installed into; the detached worktree is the only install target.
- No environment list, lane list or probe list lives in the duty: environments from `[environments]`, lanes from
  the workflows through `preflight_ci`, probes from the register.
- A paused CI lane is skipped and said so, never run silently and never silently green.
- Other platforms are never claimed installed; `lock-solved` is the only verdict a run can give them.

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| `--all` on linux-64 with `dbgpt-sidecar` (`platforms = ["linux-64"]`) and `osx` (`osx-arm64-min`) | sidecar installed; `osx` `lock-solved` |
| `pixi install --frozen -e local-recipes` exceeds a `--budget-minutes` | row `timed-out`, run red, remaining envs still run |
| `scribe-pg-up` not running | scribe lane is the `manual` row; the station suite still runs its non-Postgres tests |
| register row `test` shared by three rows | that test runs once |
| `--env pyforge-guild --lane lint-types` | one install, one lane, no probes |
| `pixi lock --check` red | every other-platform row `unsolved`, run red |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-167 (FR-40), minted 2026-10-13.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-13 (estate refresh) entry.
- Epic: Epic 100, Stories 100.1–100.7.
- Ledger key: `100-4-the-refreshed-estate-proves-itself-in-every-environment-and-every-station-suite`.
- Ledger status at mint: `backlog`.
- Deps: S-100.2, S-100.5. `marshal factory dispatch` stamps `baseline_revision` with the launch commit (Story 100.1's run did), so no
  hand re-base is needed.
- Surface: `marshal-policy.toml` `[epic_surfaces]."100"` (added with the mint).
- Minted 2026-10-13 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_estate_verify.py -q` — expected: pass (AC1–AC5).
- `pixi run --frozen -e pyforge-guild detectors-ci` and `lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild python scripts/spec_surface_reconcile.py` and `spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.
- Operator, once, on the branch (not a test): `pixi run --frozen -e pyforge-steward pyforge steward estate verify --env pyforge-guild --lane lint-types` — expected: exit 0 with a journal row (the first real run; recorded in the Auto Run Result).

## Spec Change Log

- 2026-10-13: minted with CAP-167 / FR-40 and Epic 100. `type: feature`, Story 100.2's flag. Tiers, `--all` and the
  per-platform rows by rulings Q12 and Q14 (asked and answered 2026-10-13); waits on Story 100.5 for the register
  probes.
