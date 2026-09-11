---
title: "Mason's own env satisfies the CFE import floor"
type: 'fix'
created: '2026-09-10'
status: 'done'
baseline_revision: 'e16443693d844e87fc473a90096ab6fac7a7258e'
review_loop_iteration: 0
followup_review_recommended: false
updated: '2026-09-11'
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `mason doctor` reports `unavailable_verbs: ('recipe',)` and
`cfe_import_floor_missing: ('truststore', 'conda-forge-metadata')` when run in the `pyforge-mason`
pixi env, because `[feature.pyforge-mason.dependencies]` (`pixi.toml:281-283`/`:469-476`) declares
neither floor dependency while `cfe.py`'s `CFE_IMPORT_FLOOR` (six distribution-name -> import-name
pairs: `pyyaml`, `requests`, `packaging`, `truststore`, `ruamel.yaml`, `conda-forge-metadata`)
requires both to be importable before the `recipe` verb family is reported available. This is one
of the twelve `done`-but-not-in-effect capabilities the 2026-09-09 fleet-readiness pass found
(steward Epic 49, C6, evidence row mason-B5): the code exists and is correct, but mason's own
environment cannot exercise it.

**Approach:** Add `truststore` and `conda-forge-metadata` to `[feature.pyforge-mason.dependencies]`
at floors matching what `cfe.py`'s `CFE_IMPORT_FLOOR` actually requires, re-solve the lock, and
regenerate `environment.yaml`. Add a regression test pinning the floor so a future dependency edit
that drops either package reds instead of silently re-disabling the verb family. Re-verify CAP-5's
graceful-degradation path still holds (a deliberately broken floor must still exit 0 with the verb
reported unavailable, never a hard failure).

## Boundaries & Constraints

**Always:**
- This is CFE-floor work — driven directly by `cfe.py`'s `CFE_IMPORT_FLOOR` — so the story runs
  through `conda-forge-expert` (CLAUDE.md Rule 1) and ends with the Rule-2 retro.
- Add dependency floors that actually match what `CFE_IMPORT_FLOOR` requires, not an arbitrary
  version.
- Regenerate `environment.yaml` after any `pixi.toml` dependency change (CLAUDE.md's ungated
  `environment.yaml` sync-check rule) — `pixi project export conda-environment -e build >
  environment.yaml`.
- Add a test that pins the floor so a future edit dropping `truststore` or `conda-forge-metadata`
  fails the suite rather than silently re-disabling `recipe`.
- Re-verify the CAP-5 degradation contract: a deliberately broken floor must still exit 0 with the
  verb reported unavailable, not a hard crash.

**Never:**
- Do not touch verbs or code paths unrelated to the import-floor probe — this is a dependency-floor
  fix, not a `recipe` feature change.
- Do not weaken or remove CAP-5's graceful-degradation behavior while fixing the floor gap.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Floor satisfied after fix | `truststore` + `conda-forge-metadata` added to `[feature.pyforge-mason.dependencies]`, lock re-solved | `pixi run -e pyforge-mason mason doctor` reports `cfe_import_floor_satisfied: True`, empty `cfe_import_floor_missing` | N/A |
| `recipe` verb becomes available | Same as above | `unavailable_verbs` no longer contains `"recipe"` | N/A |
| Regression pin | A future edit removes `truststore` or `conda-forge-metadata` from the env | The new pinning test fails | Test failure, not a silent doctor-report change |
| Degradation still holds | Floor deliberately broken (e.g. simulated missing import) | Process still exits 0; verb reported unavailable via `unavailable_verbs` | No hard failure/crash — CAP-5 contract preserved |
| `environment.yaml` sync | `pixi.toml` dependency table changes | `environment.yaml` regenerated to match | Sync check (ungated by `maintenance` label) reds if stale |

</intent-contract>

## Code Map

- `pixi.toml` — `[feature.pyforge-mason.dependencies]` (~line 469-476) gains `truststore` and
  `conda-forge-metadata` entries at floors matching `cfe.py`'s `CFE_IMPORT_FLOOR`.
- `environment.yaml` — regenerated via `pixi project export conda-environment -e build >
  environment.yaml` after the `pixi.toml` change.
- `src/shared/packages/pyforge-mason/src/pyforge/mason/cfe.py` (read-only reference,
  `CFE_IMPORT_FLOOR` ~line 180-187) — the six-entry floor this fix must satisfy exactly; no code
  change expected here.
- `src/shared/packages/pyforge-mason/src/pyforge/mason/doctor.py` (read-only reference,
  `unavailable_verbs`/`cfe_import_floor_satisfied`/`cfe_import_floor_missing` ~lines 130-183) —
  the report fields this fix must flip; no code change expected here.
- `src/shared/packages/pyforge-mason/tests/unit/test_doctor.py` — add the regression assertion
  pinning the floor (real-env probe, or a fixture-driven equivalent matching this file's existing
  conventions).
- `src/shared/packages/pyforge-mason/tests/**` — re-verify (and extend if needed) CAP-5's
  degradation-path coverage: a broken floor still exits 0 with `recipe` reported unavailable.

## Tasks & Acceptance

**Execution:**
- `[fix]` Add `truststore` and `conda-forge-metadata` to
  `[feature.pyforge-mason.dependencies]` in `pixi.toml`, at floors matching `CFE_IMPORT_FLOOR`.
- `[chore]` Re-solve the `pyforge-mason` lock and regenerate `environment.yaml`.
- `[fix]` Add a regression test in `src/shared/packages/pyforge-mason/tests/**` pinning the import
  floor so dropping either dependency fails the suite.
- `[fix]` Re-verify CAP-5's graceful-degradation path (deliberately broken floor still exits 0,
  verb reported unavailable) and add/extend coverage if the existing test does not already prove
  this post-fix.

**Acceptance Criteria:**
- Given `mason doctor` reports `unavailable_verbs: ('recipe',)` and `cfe_import_floor_missing:
  ('truststore', 'conda-forge-metadata')` in the `pyforge-mason` env.
- When `truststore` and `conda-forge-metadata` are added to `[feature.pyforge-mason.dependencies]`
  at floors matching what `cfe.py`'s `CFE_IMPORT_FLOOR` actually requires, the lock is re-solved
  and `environment.yaml` regenerated.
- Then `pixi run -e pyforge-mason mason doctor` reports `cfe_import_floor_satisfied: True`, an
  empty `cfe_import_floor_missing`, and no `recipe` entry in `unavailable_verbs`; a test pins the
  floor so a future dependency edit that drops either package reds instead of silently
  re-disabling the verb family; and CAP-5's degradation path is re-verified (a deliberately broken
  floor still exits 0 with the verb reported unavailable — the graceful-degradation contract must
  not regress into a hard failure).
- Rule 1/2: this is CFE-floor work — the change is driven by `cfe.py`'s import floor, so the story
  runs through `conda-forge-expert` and ends with the Rule-2 retro.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: full suite green

## Spec Change Log

- 2026-09-10: added the missing `## Verification` -> `**Commands:**` section before dispatch. Its absence makes `core.gate.check_spec_binding` (marshal Story 2.7, MRS-GATE-010) unconditionally refuse dispatch verification for any spec authored this way -- confirmed live across doctor's own Epic 21 backlog this session.

## Review Triage Log

### 2026-09-11 — Review pass
- verdicts: 18 findings — high 0, medium 1, low 2, false 8, maybe-false 0, reject 7
- findings:
  - `[false]` `[reject]` environment.yaml not regenerated — `pixi project export conda-environment -e build > environment.yaml` produced zero diff; pyforge-mason deps do not alter the build env export surface.
  - `[low]` `[reject]` Code Map names test_doctor.py but test landed in tests/meta — Tasks say `tests/**`; meta tier is valid for pixi.toml/env-sync guards.
  - `[false]` `[reject]` CAP-5 degradation lacks new coverage — pre-existing test_doctor.py mocked and unmocked never-raises tests plus test_cli doctor exit-0 tests already prove the contract.
  - `[medium]` `[defer]` No end-to-end mason doctor assertion at repo root — probe-level test plus mocked doctor unit tests cover the likely regression; hermetic repo-root doctor test deferred as higher setup cost.
  - `[medium]` `[patch]` Meta test hardcoded floor strings instead of reading sibling pixi feature tables — extended test_cfe_import_floor_env_sync.py to compare against [feature.python.dependencies] and [feature.vuln-db.dependencies] live.
  - `[low]` `[patch]` Floor pin range test only checked SpecifierSet non-empty — now requires >= or > operator per NFR-C1 convention.
  - `[false]` `[reject]` Other four CFE_IMPORT_FLOOR entries lack direct pixi pins — intent scoped to the two packages that were actually missing from pyforge-mason deps.
  - `[low]` `[reject]` Spec frontmatter missing updated date / sprint ledger sync — planning hygiene outside this story's code contract.
  - `[false]` `[reject]` Rule 2 retro missing — closed in same run (CFE v8.90.2 PATCH entry, no skill guidance changes).
  - `[false]` `[reject]` Story still in-progress with open tasks — all execution tasks completed before finalize.
  - `[false]` `[reject]` KeyError if pyforge-mason feature missing — would fail loudly in meta test; not a reachable runtime defect.
  - `[low]` `[patch]` String equality for floor pins fragile to formatting — switched to SpecifierSet comparison in pin test.
  - `[false]` `[reject]` Meta test could pass outside pyforge-mason pixi env — suite runs via pyforge-mason-test task in the correct env.
  - `[false]` `[reject]` environment.yaml CI sync would fail — export verified clean after pixi.toml change.

## Auto Run Result

Status: done

**Summary:** Added `truststore` and `conda-forge-metadata` to `[feature.pyforge-mason.dependencies]` at repo-canonical floors, re-solved `pixi.lock`, and added meta regression tests that pin both the pixi declarations and a live `probe_import_floor(sys.executable)` check. Mason doctor now reports `cfe_import_floor_satisfied: True`, empty `cfe_import_floor_missing`, and no `recipe` in `unavailable_verbs`.

**Files changed:**
- `pixi.toml` — declare CFE import-floor deps for pyforge-mason env
- `pixi.lock` — re-solve after dependency additions
- `src/shared/packages/pyforge-mason/tests/meta/test_cfe_import_floor_env_sync.py` — regression pin (pixi pins + live import probe + cross-feature floor parity)
- `.claude/skills/conda-forge-expert/{SKILL.md,CHANGELOG.md,MANIFEST.yaml,config/skill-config.yaml}` — Rule-2 retro (v8.90.2, no guidance changes)

**Review findings:** 3 patches applied (cross-feature floor sync, SpecifierSet pin comparison, minimum-floor operator check). 1 deferred (repo-root doctor e2e). 14 rejected/false.

**Follow-up review recommended:** false (1 medium patch, 2 low patches — below threshold)

**Verification:**
- `pixi run --frozen -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/meta/test_cfe_import_floor_env_sync.py` — 3 passed
- `pixi run --frozen -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/meta/test_cfe_import_floor_env_sync.py src/shared/packages/pyforge-mason/tests/unit/test_doctor.py` — 35 passed
- Live doctor probe: `cfe_import_floor_satisfied: True`, `unavailable_verbs: ()`
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — 1581 passed, 1 pre-existing failure (`test_portal_last_diagnose.py::test_django_mason_has_no_raw_http_pyforge_or_minio`, also fails at baseline)
- `pixi project export conda-environment -e build > environment.yaml` — no diff (build env unaffected)

**Residual risks:** Full suite has one pre-existing portal import-boundary failure unrelated to this story. Doctor CLI outcome at repo root with a resolved CFE installation is inferred from probe + mocked unit tests, not a dedicated integration test.
