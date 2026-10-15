---
title: "31.1: The fleet-picture ATTENTION test stubs the CI-pause probe"
type: 'fix'
created: '2026-10-14'
status: 'done'
baseline_revision: '22e5c19c285e722bcf7d58203689d57e9cc4dd55'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - .claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_main_attention.py
  - scripts/fleet_picture.py
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-45-1-doctor-names-every-ci-surface-that-drifted-stuck-or-outlived-its-review-date.md
  - .github/workflows/cfe-regression-net.yml
deferred: []
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** on clean `main` (`22e5c19c28`, measured 2026-10-14),
`pixi run --frozen -e local-recipes python -m pytest .claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_main_attention.py -q`
fails all three tests:

- `test_every_probe_result_reaches_needs_or_watch`
- `test_bmad_core_fail_finding_reaches_watch`
- `test_every_failing_probe_degrades_to_its_own_watch_line`

In each, the expected `watch` list is short one line, `could not check CI pauses`.

- Doctor Story 45.1 (`pyforge-doctor:CAP-89`, merge `7c6dac8c07`) added `ci_pause_drift_findings()` to
  `scripts/fleet_picture.py`. `main()` calls it between `dream_chain_gap_findings` and
  `sibling_dreams_drift_findings`, appends `<check>: <message>` per WARN finding, and appends
  `could not check CI pauses` when it raises.
- The test stubs each probe named in its `_PROBES` tuple (doctor Story 41.4), and the tuple does not name the new one.
  So the probe runs for real against the test's fake `subprocess.run`. In the sentinel test the fake returns
  `#7 an open pr`; in the bmad-core test it returns an empty string; in the raising test it raises. Each time the
  probe raises, and `main()` adds its degrade line.
- `cfe-regression-net` (`pixi run --frozen -e local-recipes test-ci`) runs only on changes under the CFE tree and the
  pixi files. Story 45.1 changed `scripts/fleet_picture.py` and doctor's package, so the lane never ran on its PR.
  It is red on every PR that touches its paths since then.

**Approach:** fix the test, not the script. `main()`'s behaviour is what Story 45.1 specified (its AC8), so
`scripts/fleet_picture.py` stays unchanged.

1. List `ci_pause_drift_findings` in `_PROBES`, in `main()`'s call order. The bmad-core test then stubs it to `[]`
   and the raising test makes it raise, as for every other probe.
2. In the sentinel test, stub it with one `ci-pause-drift` finding and expect its `watch` line between
   `dream chain: gap` and the sibling-dreams line.
3. In the raising test, expect `could not check CI pauses` between `could not check dream-chain gaps` and
   `could not check sibling-dreams drift`.
4. The module docstring says why `_PROBES` must list every probe `main()` calls.

Ledger key: `31-1-the-fleet-picture-attention-test-stubs-the-ci-pause-probe`.
Type / Effort / Deps: fix / XS / —.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-mason` CAP-23 (recipe lifecycle machinery): its success line is "the skill's
  own meta-test suite is green". No CAP is minted, no FR moves, and no `SPEC.md` text changes.
- **Cross-station.** `pyforge-doctor:CAP-89` (Story 45.1) built the probe this test now stubs. No doctor file changes;
  a one-line follow-up note sits on `spec-pyforge-doctor`'s memlog.
- **No flag.** This is a `fix` (`spec-feature-flag-governance` CAP-1, Q1).
- **Chain at done.** The fix was implemented before the chain was written, so the story is minted at `done`, as
  Story 24.1 was (operator ruling 2026-09-29).
- **Origin.** `docs/dreams/pyforge-mason.md` Realization log, the 2026-10-14 entry.

## Acceptance Criteria

- **AC1 — Green.** The three tests in `test_fleet_picture_main_attention.py` pass, and
  `pytest .claude/skills/conda-forge-expert/tests/meta -q` exits 0.
- **AC2 — Intent kept.** No test is skipped or marked `xfail`. Every assertion that stood before still stands. Both
  `watch` lists carry the CI-pause line at `main()`'s position, so a missing or misplaced CI-pause line fails.
- **AC3 — Mutations.** Each change below to a scratch copy of `scripts/fleet_picture.py` fails a named test:
  - drop the CI-pause `watch.append` for findings: `test_every_probe_result_reaches_needs_or_watch`;
  - rename the degrade line `could not check CI pauses`: `test_every_failing_probe_degrades_to_its_own_watch_line`.
- **AC4 — Rule 2.** The test change, a CFE `CHANGELOG.md` PATCH entry (v8.100.4) and the version carriers
  (`SKILL.md`, `MANIFEST.yaml`, `config/skill-config.yaml`) land in one `retro(cfe):` commit.
- **AC5 — Nothing else moves.** `scripts/fleet_picture.py`, every CFE script and every doctor file are unchanged.

## Boundaries & Constraints

**Always:**
- Go through `conda-forge-expert` (Rule 1). Read every verdict from the exit code, never through a pipe.
- Reconcile every governed path on the memlogs of the Specs that govern it: `spec-conda-forge-expert-rebuild` and
  `spec-packaging-factory` (the CFE surface) and `spec-pyforge-marshal` (co-governs the test).

**Never:**
- Change `scripts/fleet_picture.py` to make the test pass.
- Skip, `xfail` or loosen an assertion.
- Touch `src/shared/packages/pyforge-mason/`, `pixi.toml`, `pixi.lock` or `recipes/**`.

## I/O & Edge-Case Matrix

| Case | Expected |
|---|---|
| the CI-pause probe returns one WARN finding | one `watch` line `ci-pause-drift: <message>`, after the dream-chain line |
| the CI-pause probe returns `[]` | no CI-pause line; the bmad-core FAIL line stands alone |
| the CI-pause probe raises | `could not check CI pauses`, after `could not check dream-chain gaps` |
| a probe `main()` calls is missing from `_PROBES` | it reads the fake `subprocess.run` and adds a degrade line, so the tests fail |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-mason` CAP-23. No CAP is minted.
- Dream: `docs/dreams/pyforge-mason.md` § *Realization log*, the 2026-10-14 entry.
- Epic: Epic 31 (new), minted with this story. A fix on a done epic breaks the ledger detectors, so it gets its own.
- Ledger key: `31-1-the-fleet-picture-attention-test-stubs-the-ci-pause-probe`.
- Ledger status at mint: `done` (minted at done; the fix ships in the same change).
- Deps: —.
- Surface: `marshal-policy.toml` `[epic_surfaces]."31"`, added with this mint.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e local-recipes python -m pytest .claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_main_attention.py -q` — expected: 3 passed.
- `pixi run --frozen -e local-recipes python -m pytest .claude/skills/conda-forge-expert/tests/meta -q` — expected: pass.

**Run before the push (not dispatch gates):**
- The two mutations of AC3, against a scratch copy of `scripts/fleet_picture.py` — expected: each fails its named
  test.
- `pixi run --frozen -e pyforge-guild chain-completeness-check`, `story-status-check`, `chain-currency-sweep-check`,
  `dream-chain-check`, `dreams-hygiene-check`, `ledger-regression-check`, `deferred-work-check` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped
  stamps.

## Run results

Run 2026-10-14 in the landing worktree on `22e5c19c28`, every verdict read from its exit code.

- **Before the fix:** the three tests in `test_fleet_picture_main_attention.py` fail (exit 1). Each expected `watch`
  list is short one line, `could not check CI pauses`.
- **AC1:** the file passes, 3 passed (exit 0). The CFE meta suite passes, 7787 passed and 6 skipped (exit 0), both
  before and after the version bump.
- **AC2:** no skip or `xfail` is added, and no assertion is removed. Both `watch` lists gain the CI-pause line at
  `main()`'s position.
- **AC3:** run against a scratch copy of `scripts/fleet_picture.py`, with `src/` linked, the unchanged copy passes
  3 of 3.
  - Dropping the CI-pause `watch.append` fails `test_every_probe_result_reaches_needs_or_watch`.
  - Renaming the degrade line fails `test_every_failing_probe_degrades_to_its_own_watch_line`.
- **AC4:** CFE v8.100.4, a PATCH entry in `CHANGELOG.md`. The version moves in `SKILL.md`, `MANIFEST.yaml` and
  `config/skill-config.yaml`. These five files make up the `retro(cfe):` commit.
- **AC5:** `scripts/fleet_picture.py`, the CFE scripts and every doctor file are unchanged.
- **`pyforge-mason-test`:** 1619 passed, 3 failed, 3 deselected (exit 1) with the CFE edits still uncommitted.
  - The three failures are mason's guard against editing CFE outside a sanctioned retro commit:
    `test_persona_consults_cfe.py::test_conda_forge_expert_not_replaced_or_skf_nested`,
    `test_portal_last_diagnose.py::test_cfe_not_replaced_and_claude_agents_untouched` and
    `test_skf_mason_skill.py::test_conda_forge_expert_not_replaced`.
  - Each lists only `uncommitted:` plus the five CFE files above.
  - `pyforge.testing_kit.branch_diff_guard.unsanctioned_commits` accepts a commit whose subject starts `retro(cfe):`
    and that moves `CHANGELOG.md`. Re-run the suite after that commit; expected: pass.
- **Planning checks** (`pyforge-guild`), each exit 0: `chain-completeness-check`, `story-status-check`,
  `chain-currency-sweep-check`, `dream-chain-check`, `dreams-hygiene-check`, `ledger-regression-check`,
  `deferred-work-check` and `ad-citation-check`. `chain_currency_sweep_check.py --json` reports 0 findings for mason,
  marshal and doctor.
- **`spec-surface-check`:** exit 0. Every CFE path is named on the memlogs of `spec-conda-forge-expert-rebuild`,
  `spec-packaging-factory` and `spec-pyforge-marshal`. Those three Specs still need their scoped stamps.
- **Ledger:** a worktree-local feed was seeded from the tracked ledger with
  `31-1-the-fleet-picture-attention-test-stubs-the-ci-pause-probe: done`, `epic-31: done` and
  `epic-31-retrospective: optional`. `sprint-ledger-sync -- --project mason` wrote mason (175 keys), and the feed was
  then deleted.

## Spec Change Log

- 2026-10-14: minted at `done` from the station Dream's 2026-10-14 entry, with the fix (CFE v8.100.4). Fix under
  CAP-23; no CAP, no FR, no flag.
