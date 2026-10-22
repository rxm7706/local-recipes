---
title: '45.3: The fleet-picture meta-test names every probe `main()` calls'
type: 'fix'
created: '2026-10-22'
status: 'done'
baseline_revision: 'a81732d0a313de02aefc68d1b573bcd6a405a707'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-45-1-doctor-names-every-ci-surface-that-drifted-stuck-or-outlived-its-review-date.md
  - docs/dreams/pyforge-doctor.md
  - scripts/fleet_picture.py
  - .claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_main_attention.py
  - tests/scripts/test_fleet_picture_ci_pauses.py
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/marshal-policy.toml
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `.claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_main_attention.py` runs
`fleet_picture.main()` end to end with every probe in its `_PROBES` tuple stubbed. Nothing compares `_PROBES` with the
probes `main()` actually calls. A probe added to `main()` and not to `_PROBES` reads the faked `subprocess.run`,
degrades to its own "could not check" line, and breaks the file's three exact-list tests, which then fail without
naming the probe. That happened twice:
- Story 45.1 added `ci_pause_drift_findings`; mason Story 31.1 stubbed it (CFE v8.100.4).
- Story 48.2 added `pages_liveness_findings`; herald Story 45.1 stubbed it (CFE v8.101.1).

The guard that names the gap was written on the 2026-10-14 branch `doctor-45-2-fleet-picture-probe-list` (Story 45.2
there), which never landed. Its stub fix landed separately as Story 31.1, so only the guard is left (team memory,
2026-10-18 addendum to the 2026-10-17 session close).

**Approach:**
1. A new test, `test_probes_tuple_names_every_probe_main_calls`, reads `scripts/fleet_picture.py` with `ast`. It
   collects every module-level function whose name ends in `_findings` or `_staleness` and that `main()` calls by name,
   and asserts that set equals `set(_PROBES)`. Its failure message names each missing probe ("stub them here") and each
   extra one ("main() no longer calls them").
2. The module docstring says the guard exists, after the two incidents it already records.
3. `[epic_surfaces]."45"` declares the meta-test and the CFE version carriers, so a later fix under Epic 45 runs the CFE
   lane.

At `a81732d0a3`, `main()` calls eleven probes and `_PROBES` lists the same eleven, so the guard passes on the tree it
lands on.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-doctor` CAP-89 (Story 45.1, the ci-pause-drift source and its `fleet-picture`
  probe, the first one this test missed). No CAP is minted, and no `SPEC.md`, PRD or spine text changes.
- **No flag.** This is a `fix` (`spec-feature-flag-governance` Q1).
- **conda-forge-expert Rule 2.** The test sits under `.claude/skills/conda-forge-expert/`, so the CFE retro lands with
  it: v8.101.2 to v8.101.3, in its own `retro(cfe):` commit.
- **Origin.** `docs/dreams/pyforge-doctor.md` Realization log, 2026-10-22 (the fleet-picture probe guard). Operator
  ruling 2026-09-29 (`.claude/memory/project/2026-09-29-operator-ruling-a-test-only-cfe-fix-that-was-alre.md`): a
  test-only CFE fix still takes the full chain. Operator rule 2026-10-04: a fix story goes into its done epic.

## Acceptance Criteria

- **AC1 — The guard.** `test_probes_tuple_names_every_probe_main_calls` parses `scripts/fleet_picture.py` with `ast`
  and asserts that the module-level `*_findings` / `*_staleness` functions `main()` calls equal `set(_PROBES)`. Its
  failure message names each missing and each extra probe.
- **AC2 — Green.** The meta-test file passes (4 tests), and `tests/scripts/test_fleet_picture_ci_pauses.py` still
  passes.
- **AC3 — Mutation.** Each change below makes the guard fail with the probe's name. Restore each.
  - remove `pages_liveness_findings` from `_PROBES`;
  - add a name `main()` does not call to `_PROBES`;
  - add a call to a new, unstubbed `*_findings` function inside `main()`.
- **AC4 — Surface.** `[epic_surfaces]."45"` lists the meta-test and the CFE retro carriers (`CHANGELOG.md`, `SKILL.md`,
  `MANIFEST.yaml`, `config/skill-config.yaml`).

## Boundaries & Constraints

**Always:**
- Keep each existing test's intent; no test in the file is deleted or skipped.
- Read every verdict from the exit code, never through a pipe.
- Land the CFE files in their own `retro(cfe):` commit with `CHANGELOG.md` (`pyforge.testing_kit.branch_diff_guard`).
- Reconcile every governed path on the memlogs of the Specs that govern it, then stamp scoped (AGENTS.md pre-PR item 5).

**Never:**
- Never change `scripts/fleet_picture.py`; the probes and their output belong to the stories that added them.
- Never widen the guard's rule to hide a mismatch; a probe whose name fits neither suffix changes the rule, not the
  list.

**Residual risk:**
- A probe named with neither suffix, or one called through a helper rather than directly in `main()`, escapes the
  guard. Today every probe uses one of the two suffixes and is called directly in `main()`.

## I/O & Edge-Case Matrix

| `_PROBES` against `main()` | Guard |
|---|---|
| the eleven probes `main()` calls | pass |
| `pages_liveness_findings` missing | fail: `missing ['pages_liveness_findings']` |
| a name `main()` does not call | fail: `extra ['retired_probe_findings']` |
| `main()` calls a new unstubbed `*_findings` | fail: `missing ['new_probe_findings']` |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-doctor` CAP-89 (Story 45.1). No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-22 (the fleet-picture probe guard) entry.
- Epic: Epic 45 (done). Story 45.3 is minted `done`, so `epic-45` stays `done`. 45.2 was the unlanded branch's number.
- Ledger key: `45-3-the-fleet-picture-meta-test-names-every-probe-main-calls`.
- Ledger status at mint: `done` (implemented and verified in the same change, as the 2026-09-29 ruling's Story 24.1 was).
- Deps: none.
- Surface: `marshal-policy.toml` `[epic_surfaces]."45"`, extended with this mint.

## Verification

**Commands:**
- `pixi run --frozen -e local-recipes python -m pytest .claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_main_attention.py tests/scripts/test_fleet_picture_ci_pauses.py -q -p no:cacheprovider` — expected: 9 passed (AC1, AC2).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e local-recipes test-ci` — expected: the meta-test file passes.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlogs and scoped stamps.
- The three mutations of AC3 — expected: each fails the guard by name. Restore each.

## Spec Change Log

- 2026-10-22: minted `done`. The meta-test file and `tests/scripts/test_fleet_picture_ci_pauses.py` run 9 passed.
- 2026-10-22, AC3: each mutation failed the guard by name, and the restored tree passed.
  - `pages_liveness_findings` removed from `_PROBES`: `missing ['pages_liveness_findings']`.
  - `retired_probe_findings` added to `_PROBES`: `extra ['retired_probe_findings']`.
  - a `new_probe_findings()` call added to `main()`: `missing ['new_probe_findings']`.

## Review Triage Log

- 2026-10-22: the independent review runs as a separate pass and records its findings here.
