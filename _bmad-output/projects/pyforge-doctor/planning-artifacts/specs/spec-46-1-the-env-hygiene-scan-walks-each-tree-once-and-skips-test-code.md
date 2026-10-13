---
title: "46.1: The env-hygiene scan walks each tree once and skips test code"
type: 'fix'
created: '2026-10-12'
status: 'in-progress'
baseline_revision: '7b6caaae2434c529ab2cf49e0e2749713c30ab81'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-44-1-the-doctor-check-speed-budget-is-judged-on-the-cpu-the-check-spends.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/checks/env_hygiene.py
  - src/shared/packages/pyforge-doctor/tests/unit/test_checks_env_hygiene.py
  - src/shared/packages/pyforge-doctor/tests/unit/test_check_speed_budget.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** this is `DW-doctor-44-1`. Story 44.1 made `doctor check`'s five-second budget (NFR-4) judge the CPU a run
spends. One run on the repo root spends 2.75 s at `c447946b3f`: about 1.8x headroom idle, and about 1.25x under load,
because CPU time also rises when cores are shared. The scan grew 19% in eight days (2.31 s on the 2026-10-04 tree).

**The evidence:** measured at `09fd904b02` with `process_time` around each phase of the real `_scan_file`
(`checks/env_hygiene.py:810`), one scan of 2721 discovered files costs 1.99 s of CPU:

| Phase | CPU |
|---|---|
| `ast.parse` of the 178 files that pass both prefilters (`:819`-`:823`) | 0.67 s |
| the `_CredentialInjectionVisitor` walk | 0.69 s |
| `_resolve_os_aliases` (`:298`), a second full `ast.walk` of every parsed tree | 0.34 s |
| reading and prefiltering | 0.29 s |
| discovery (`_discover_python_files`, `:240`) | 0.14-0.33 s |

Of the 178 parsed files, 72 are test code, and they cost 0.71 s. Today the scan reports four findings:

| Finding | After this story |
|---|---|
| `.claude/skills/conda-forge-expert/scripts/github_version_checker.py:68` (`GITHUB_TOKEN`) | kept |
| `.claude/skills/conda-forge-expert/scripts/scan_project.py:1898` (`OCI_REGISTRY_TOKEN`) | kept |
| `src/shared/packages/pyforge-steward/tests/fixtures/ungated_jfrog_auth.py:21` (`JFROG_API_KEY`), a fixture that is ungated on purpose | dropped (test code) |
| `src/platform/langflow_integration/tests.py:183` (`LANGFLOW_SUPERUSER`) | dropped (test code) |

Nothing depends on the dropped findings: steward's keys audit uses its own `pyforge.steward.keys.scan_file`.

**Approach:**
1. The visitor records the `os`, `environ` and `getenv` aliases from `Import` and `ImportFrom` as it walks. That
   replaces the separate `_resolve_os_aliases` walk, and no verdict changes.
2. Discovery skips test code:
   - files named `test_*.py`, `*_test.py`, `conftest.py` or `tests.py`;
   - anything under a `tests` or `test` directory segment.

   The rule is judged on the path relative to the scan target, so a scan pointed straight at a fixtures directory
   still scans it. The saving is about 1.0 s of CPU, 36%.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-doctor` CAP-1 (the fast `doctor check` pre-flight, with its env-hygiene
  detector) and NFR-4 (the five-second budget). No CAP is minted, and no `SPEC.md` text changes.
- **No flag.** This is a `fix` (`spec-feature-flag-governance` Q1): it restores NFR-4's margin. The scope change is the
  operator's ruling.
- **Origin.** `DW-doctor-44-1` (Story 44.1). `docs/dreams/pyforge-doctor.md` Realization log, 2026-10-12 (the
  env-hygiene scan stops growing with the test suite). Operator ruling 2026-10-12: "Single pass + skip tests
  (Recommended)".

## Acceptance Criteria

- **AC1 — One walk per tree.** `_scan_file` walks each parsed tree once. No second `ast.walk` and no separate
  alias-resolution pass remain on the scan path. Every existing test in `tests/unit/test_checks_env_hygiene.py` passes
  unchanged, aliased imports included (`import os as o`, `from os import environ as e`, `from os import getenv`).
- **AC2 — Same verdicts on code.** On the live repo root, the findings outside test code equal today's: the two
  conda-forge-expert findings, same file, line and variable.
- **AC3 — Test code is not scanned.** A fixture tree holds a planted unconditional injection in each of `test_x.py`,
  `x_test.py`, `conftest.py`, `tests.py`, `tests/helper.py`, `test/helper.py` and `app/main.py`. The scan reports only
  `app/main.py`. The same planted file scanned with the `tests/` directory itself as the target is reported, because the
  rule is relative to the target.
- **AC4 — The time drops.** Before and after, the median CPU of five `doctor check` runs on the repo root (Story 44.1's
  measure) falls by at least 25% on the same machine. Record both numbers in the Spec Change Log.
  `test_check_speed_budget.py` passes unchanged.
- **AC5 — The deferral closes.** `DW-doctor-44-1` is marked resolved with this story's commit and the before and after
  numbers.
- **AC6 — Mutation.** Each change below makes a named test fail:
  - restore the separate `_resolve_os_aliases` walk: a test that counts walks, or times them against a fixture;
  - drop the test-code rule: AC3's test;
  - judge the rule on the absolute path rather than the path relative to the target: AC3's direct-target case;
  - lose an alias form: the existing alias tests.

## Boundaries & Constraints

**Always:**
- Keep the prefilters (`_HEADER_PREFILTER_MARKERS`, `environ`/`getenv`) and their order.
- Keep the degrade-never-crash discipline: a file that fails to parse or analyze is skipped, never raised.
- Read every verdict from the exit code, never through a pipe.
- Reconcile every governed path on the memlogs of the Specs that govern it, then stamp scoped (AGENTS.md pre-PR item 5).

**Never:**
- Never change the five-second budget or Story 44.1's CPU measure.
- Never add a cache, a write or a subprocess to the scan (NFR-1: `doctor check` is read-only and offline).
- Never change a finding's message, status, check name or evidence shape.

**Residual risk:**
- Credential injection written inside test code is no longer flagged. That is the operator's ruling; the spec names it,
  and so does the PR.

## I/O & Edge-Case Matrix

| Path, relative to the scan target | Scanned |
|---|---|
| `app/main.py` | yes |
| `test_x.py`, `pkg/x_test.py`, `conftest.py`, `pkg/tests.py` | no |
| `pkg/tests/helper.py`, `pkg/test/helper.py` | no |
| `tests/fixtures/f.py`, scanned with `tests/fixtures/` as the target | yes (relative path `f.py`) |
| `testing/x.py`, `contest.py`, `latest.py` | yes (not a test name or segment) |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-doctor` CAP-1 and NFR-4. No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-12 (the env-hygiene scan stops growing with the
  test suite) entry.
- Deferral closed: `DW-doctor-44-1`.
- Epic: Epic 46 (new), minted with this story. Epic 45 stays reserved by the CI-pause plan.
- Ledger key: `46-1-the-env-hygiene-scan-walks-each-tree-once-and-skips-test-code`.
- Ledger status at mint: `backlog`.
- Deps: none. Story 44.1 is done.
- Surface: `marshal-policy.toml` `[epic_surfaces]."46"`, added with this mint.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass, with AC1-AC3's tests (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- AC4's before and after measure: the median CPU of five `doctor check` runs on the repo root (`os.times`, self plus children) — expected: at least 25% lower.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlogs and scoped stamps.
- The four mutations of AC6 — expected: each fails its named test. Restore each.

## Named, not fixed here

- **Discovery's own walk** (0.14-0.33 s) and **reading every file for the prefilter** (0.29 s) stay as they are.

## Spec Change Log

- 2026-10-12: minted at the operator's ruling "Single pass + skip tests (Recommended)". The evidence is the per-phase
  timing at `09fd904b02` above.

## Review Triage Log

- No review has run yet.
