---
title: '45.3: The fleet-picture meta-test names every probe `main()` calls'
type: 'fix'
created: '2026-10-22'
status: 'done'
baseline_revision: 'a81732d0a313de02aefc68d1b573bcd6a405a707'
review_loop_iteration: 1
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
   in call order. It asserts that `_PROBES` names the same probes, each once, in that order (the docstring already said
   `_PROBES` follows the call order). Its failure message names each missing probe ("stub them here") and each extra
   one ("main() no longer calls them"); a missing `main()` fails with its own message.
2. The module docstring says the guard exists and what escapes it, after the two incidents it already records.
3. `[epic_surfaces]."45"` declares the meta-test and the CFE version carriers, so a later Epic-45 dispatch that stubs a
   new probe there is in scope (MRS-GATE-007). It widens the scope check only; no dispatch verify runs the CFE lane
   because of it.

At `a81732d0a3`, `main()` calls eleven probes and `_PROBES` lists the same eleven in the same order, so the guard
passes on the tree it lands on.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-doctor` CAP-89 (Story 45.1, the ci-pause-drift source and its `fleet-picture`
  probe, the first one this test missed) and CAP-91 (Story 48.2, the Pages-liveness probe, the second). No CAP is
  minted, and no `SPEC.md` text changes. The PRD and the architecture spine each gain a dated currency section and no
  FR or AD (the spec-to-PRD edge went stale on this mint).
- **No flag.** This is a `fix` (`spec-feature-flag-governance` Q1).
- **conda-forge-expert Rule 2.** The test sits under `.claude/skills/conda-forge-expert/`, so the CFE retro lands with
  it: v8.101.2 to v8.101.3, in its own `retro(cfe):` commit.
- **Origin.** `docs/dreams/pyforge-doctor.md` Realization log, 2026-10-22 (the fleet-picture probe guard). Operator
  ruling 2026-09-29 (`.claude/memory/project/2026-09-29-operator-ruling-a-test-only-cfe-fix-that-was-alre.md`): a
  test-only CFE fix still takes the full chain. Operator rule 2026-10-04: a fix story goes into its done epic.

## Acceptance Criteria

- **AC1 — The guard.** `test_probes_tuple_names_every_probe_main_calls` parses `scripts/fleet_picture.py` with `ast`
  and asserts that `_PROBES` lists the module-level `*_findings` / `*_staleness` functions `main()` calls, each once
  and in call order. Its failure message names each missing and each extra probe.
- **AC2 — Green.** The meta-test file passes (4 tests), and `tests/scripts/test_fleet_picture_ci_pauses.py` still
  passes.
- **AC3 — Mutation.** Each change below makes the guard fail with the probe's name. Restore each.
  - remove `pages_liveness_findings` from `_PROBES`;
  - add a name `main()` does not call to `_PROBES`;
  - add a call to a new, unstubbed `*_findings` function inside `main()`;
  - swap two entries of `_PROBES` (fails naming the call order);
  - list one entry twice (fails naming it);
  - rename `main()` (fails saying the file defines no `main()`).
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
- The guard sees only module-level `def`s with one of the two suffixes that `main()` calls by bare name. A probe
  named otherwise, called through a helper, `functools.partial` or an attribute, bound with `lambda`, defined under a
  module-level `if`/`try`, or imported from another module escapes it, as do the I/O helpers the fixture stubs
  (`running_stations`, `load_drain_queue_overrides`, `_open_prs_by_head_ref`). Each escape still turns the other tests
  red without naming the probe. Today every probe is a module-level `def` with one of the two suffixes, called by bare
  name.

## I/O & Edge-Case Matrix

| `_PROBES` against `main()` | Guard |
|---|---|
| the eleven probes `main()` calls | pass |
| `pages_liveness_findings` missing | fail: `missing ['pages_liveness_findings']` |
| a name `main()` does not call | fail: `extra ['retired_probe_findings']` |
| `main()` calls a new unstubbed `*_findings` | fail: `missing ['new_probe_findings']` |
| two entries swapped | fail: `not in main()'s call order` |
| an entry listed twice | fail: `lists ['loop_home_staleness'] more than once` |
| `main()` renamed | fail: `defines no module-level main()` |
| `async def main()` | pass |

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

- 2026-10-22, independent review (FAIL), fixed on the same branch:
  - B1: the meta-test and the four CFE carriers are governed by `pyforge-marshal/spec-pyforge-marshal` and
    `pyforge-mason/spec-conda-forge-expert-rebuild` / `spec-packaging-factory`, and none of their memlogs named this
    change; spec-surface-check stayed green only through spec-packaging-factory's `CHANGELOG.md` sentinel. Each now
    carries a reconcile event naming the paths, with a scoped stamp.
  - S1: Approach 3 said the surface makes a later Epic-45 fix run the CFE lane. `epic_surfaces` feeds only the scope
    check (MRS-GATE-007); Approach 3 and the `marshal-policy.toml` comment now say so.
  - S2: "no PRD or spine text changes" was false after the currency sections; the citation now says what moved.
  - Nits: the guard checks call order (the docstring's claim) and duplicates, and fails by message when `main()` is
    missing or renamed; the residual risk names every escape the review reproduced; CAP-91 is cited; ruff PIE807 at the
    two `lambda: {}` / `lambda: []` stubs fixed (`dict`, `list`). Mutations rerun: all seven listed in the I/O matrix
    behave as shown, and the restored tree passes (9 passed).

- 2026-10-22: minted `done`. The meta-test file and `tests/scripts/test_fleet_picture_ci_pauses.py` run 9 passed.
- 2026-10-22, AC3: each mutation failed the guard by name, and the restored tree passed.
  - `pages_liveness_findings` removed from `_PROBES`: `missing ['pages_liveness_findings']`.
  - `retired_probe_findings` added to `_PROBES`: `extra ['retired_probe_findings']`.
  - a `new_probe_findings()` call added to `main()`: `missing ['new_probe_findings']`.

## Review Triage Log

- 2026-10-22, review 1 (independent subagent, read the diff against this spec): FAIL. 1 blocker (B1, spec-surface
  reconcile missing on the co-governing Specs), 2 should-fix (S1, S2), 9 nits. All fixed on the branch (Spec Change
  Log). Not fixed: the Tier-3 doctor feed lacking 45-3, 49-1 and epic-49 is the shared feed, written after the merge;
  the code-before-chain commit order stands (the 2026-09-29 ruling's precedent); the 2026-10-18 addendum's "new epic"
  plan yields to the 2026-10-04 rule (a fix story goes into its done epic).
