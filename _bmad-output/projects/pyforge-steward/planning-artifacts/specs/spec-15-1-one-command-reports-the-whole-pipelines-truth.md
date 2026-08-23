---
title: One command reports the whole pipeline's truth
type: feature
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
baseline_revision: 98cc782aa485a2f52a35bf2ac9ee7098ec2db173
deferred:
  - summary: >-
      Live (non-baseline) probe implementations are only exercised via stubs;
      no temp-repo / urllib-monkeypatch coverage for recipe/installed/HTTP paths.
    evidence: |-
      verification-gap review: default ProbeHooks paths never run in tests;
      operators' live `steward suite pipeline-truth` can diverge while --baseline stays green.
    location: >-
      src/shared/packages/pyforge-steward/src/pyforge/steward/suite.py
    severity: medium
  - summary: >-
      Dashboard wired census uses loose fleet surfaces (docs/dashboard,
      presentations) rather than package-specific wire state.
    evidence: |-
      blind-hunter: both dashboards can read wired whenever those docs exist;
      baseline still encodes the 2026-08-22 research column.
    location: >-
      src/shared/packages/pyforge-steward/src/pyforge/steward/suite.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** The 13 bmad-suite packages have no single truth report across upstream / recipe / channel / installed / wired stages (spec-bmad-suite-channel-product CAP-1); operators still reconstruct the 2026-08-22 research matrix by hand.

**Approach:** Add a steward duty that, for the 13 suite packages, reports upstream latest (npm AND GitHub per package class), recipe version, channel version, installed version, and wired-or-not — drift named per stage, each probe fail-open — consuming existing probes (npm/GitHub queries, recipe.yaml parse, api.anaconda.org listing, pixi list, `.claude/skills` census). Run against the 2026-08-22 baseline reproduces the research matrix.

## Acceptance Criteria

- One command covers all 13 suite packages.
- Per package reports: upstream latest (npm and/or GitHub by class), recipe version, channel version, installed version, wired-or-not.
- Drift named per stage; each probe fail-open (never abort the whole report on one probe fail).
- Fixture or recorded baseline reproduces the 2026-08-22 research matrix shape.

## Boundaries & Constraints

**Never:** Implement 15.2 autotick advance or later CAP stories. Never `scripts/bmad-switch`. Steward 12-7 remains skipped. Finalize steward ledger only.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/suite.py` — SuiteDuty + CAP-1 probes + `BASELINE_2026_08_22`
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — eighth duty `suite` / verb `pipeline-truth`
- `src/shared/packages/pyforge-steward/src/pyforge/steward/interfaces.py` — duty list includes `suite`
- `src/shared/packages/pyforge-steward/tests/unit/test_suite_pipeline_truth.py` — baseline fidelity, fail-open, drifts
- Probes: npm registry, GitHub releases/tags, recipe.yaml, api.anaconda.org, conda-meta installed scan, `.claude/skills` / `_bmad` census

## Verification

- `pixi run --frozen -e pyforge-steward pytest …` green
- Fail-open probe fixture; baseline matrix shape covered
- CI: detectors, linter, package tests

## Review Triage Log

### 2026-08-23 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 10: (high 2, medium 5, low 3)
- defer: 2: (high 0, medium 1, low 1)
- reject: 8
- addressed_findings:
  - `[high]` `[patch]` Fixed `hooks_from_baseline` shared-GitHub twin collision — github probe is package-aware so `mybmad-dashboard` keeps recorded `0.1.0`
  - `[high]` `[patch]` Strengthened baseline test to assert all 13 packages' stage values vs `BASELINE_2026_08_22`
  - `[medium]` `[patch]` Added `name_drifts` coverage for `recipe` / `installed` / wired-fail stages
  - `[medium]` `[patch]` GitHub release body non-dict + empty `tag_name` fail-open
  - `[medium]` `[patch]` Recipe version type-safe (reject YAML float coercion)
  - `[medium]` `[patch]` Wired probe `ok=False` now names `wired` drift
  - `[medium]` `[patch]` User-Agent on urllib probes; `next(..., None)` in baseline loops
  - `[low]` `[patch]` `--baseline` help clarifies live vs offline matrix replay
  - `[low]` `[patch]` Softened stale "seventh duty" wording in CLI tests/help

## Auto Run Result

Status: done

Summary: Added steward `suite pipeline-truth` duty reporting all 13 bmad-suite packages across upstream (npm/GitHub), recipe, channel, installed, and wired stages with per-stage drift and fail-open probes. `--baseline` replays the 2026-08-22 research matrix (including the bmad-method channel 6.3.0 relic). Review patches fixed the shared-GitHub baseline twin bug and hardened probes/tests.

Files changed:
- `src/shared/packages/pyforge-steward/src/pyforge/steward/suite.py` — new SuiteDuty + baseline matrix
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — suite duty + pipeline-truth verb
- `src/shared/packages/pyforge-steward/src/pyforge/steward/interfaces.py` — register suite
- `src/shared/packages/pyforge-steward/tests/unit/test_suite_pipeline_truth.py` — new tests
- `src/shared/packages/pyforge-steward/tests/unit/test_cli.py` — eight-duty expectations
- planning-artifacts spec — status/triage/auto-run result

Review findings: 10 patches applied; 2 deferred (live-probe coverage, dashboard wire heuristics); 8 rejected (commit hygiene, ledger finalize timing, pixi-list wording vs AC, .dev0 equality matching baseline, ahead-as-drift redesign, bare drift labels, etc.)

Follow-up review recommendation: true (patched high=2; score 3×5 medium + 1×3 low = 18 ≥ 5)

Verification:
- `pixi run --frozen -e pyforge-steward pytest …test_suite_pipeline_truth.py …test_cli.py …test_duty_protocol.py -q` → 38 passed
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests -q` → 823 passed
- `steward suite pipeline-truth --baseline` → 13 packages, method channel 6.3.0 relic

Residual risks: live network path not smoke-tested end-to-end; installed stage uses conda-meta scan rather than literal `pixi list`; dashboard wired is heuristic.
