---
title: "Mason's own env satisfies the CFE import floor"
type: 'fix'
created: '2026-09-10'
status: 'in-progress'
baseline_revision: '57c001c9d7c8864ec235b871c8e3dc024845e414'
review_loop_iteration: 0
followup_review_recommended: false
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

## Spec Change Log

- **Implemented as specced, no deviations.** Added `truststore = ">=0.10.4"` (mirroring
  `[feature.python.dependencies]`'s identical pin) and `conda-forge-metadata = ">=2026.9.5"`
  (mirroring `[feature.vuln-db.dependencies]`'s identical pin) to
  `[feature.pyforge-mason.dependencies]` in `pixi.toml`; re-solved with `pixi install -e
  pyforge-mason`; regenerated `environment.yaml` via `pixi project export conda-environment -e
  build`.
- Added `test_real_environment_satisfies_the_cfe_import_floor` to
  `src/shared/packages/pyforge-mason/tests/unit/test_doctor.py` — runs the real, unmocked
  `cfe.probe_import_floor(sys.executable)` probe against mason's own pixi env and asserts
  `.missing == ()`. This is the regression pin the acceptance criteria calls for.
- **CAP-5 degradation re-verified live**, not just via the existing mocked unit tests (which
  were unaffected by this fix and continued to pass throughout): `pixi run -e pyforge-mason
  mason doctor --cfe-python /usr/bin/python3` (a system interpreter genuinely missing the
  floor) still exits 0 and reports `unavailable_verbs: ('recipe',)` — no crash, no regression
  in the graceful-degradation contract.
- Live-verified the acceptance criteria's exact wording:
  `pixi run -e pyforge-mason mason doctor` now reports `cfe_import_floor_satisfied: True`, an
  empty `cfe_import_floor_missing`, and no `recipe` entry in `unavailable_verbs`.
- Rule 1/2 honored: invoked the `conda-forge-expert` skill before starting (this is CFE-floor
  work per `cfe.py`'s `CFE_IMPORT_FLOOR`), and closed with a Rule-2 retro — CFE skill v8.90.2
  → v8.90.3 (PATCH), CHANGELOG entry stating "no skill changes; verified existing guidance held"
  (the finding is entirely in mason's own environment configuration, not in any CFE
  script/gotcha/pattern).
- **Side effect, reconciled in the same pass**: the `pixi.toml` edit tripped
  `pyforge-marshal/spec-pyforge-core`'s spec-surface drift gate (that spec's `surface:` claims
  the whole `pixi.toml` file). Reconciled per the repo's established foreign-spec-surface
  procedure — a `(note by claude)` entry recording the unrelated touch in that spec's own
  `.memlog.md`, then `python scripts/spec_surface_check.py --write-baseline --spec
  pyforge-marshal/spec-pyforge-core` (scoped, not a bare `--write-baseline`).
- **Left alone, pre-existing and out of scope**: `test_conda_forge_expert_not_replaced_or_skf_
  nested` and `test_cfe_not_replaced_and_claude_agents_untouched`
  (`tests/meta/test_persona_consults_cfe.py` / `test_portal_last_diagnose.py`) fail because the
  branch's own merge commit `57c001c9d7` (landing the prior story 15.2's Rule-2 retro) has a
  subject that doesn't match the sanctioned `retro:`/`retro(<scope>):` pattern the
  `unsanctioned_commits` guard expects — confirmed via `git stash` that this failure predates
  every change in this story. Also pre-existing/unrelated: 5 `test_script_responds_to_help[...]`
  failures (a `ModuleNotFoundError: No module named '_sbom'` import bug in
  `add_handoff.py`/`inventory_match.py`/`library_futures.py`/`recommend_2027.py`/
  `universe_sbom.py`) and `test_bmad_artifacts_integrity` (unrelated `uncovered` spec-surface
  findings against other in-flight specs). None of these touch the import-floor probe or verbs
  this story's Never boundary protects.

## Review Triage Log
