---
title: '56.1: frozen-path-changed reads the ledger''s rebuilding rows, not a manifest that never existed'
type: 'fix'
created: '2026-11-10'
status: 'backlog'
story: 56-1-frozen-path-changed-reads-the-ledger-s-rebuilding-rows-not-a-manifest-that-never-existed
spec: spec-pyforge-doctor
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a check that judges; a gated gate is a silent green (spec-feature-flag-governance Q1; roster list)
surface:
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/frozen_path.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_frozen_path.py'
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/prds/prd-pyforge-doctor-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md
  - docs/dreams/pyforge-doctor.md
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `frozen-path-changed` (`sources/frozen_path.py`) probes `docs/foundry/manifest.{yaml,yml,json}` and freezes `rebuilding`/`moving`; the real file is `docs/foundry/capability-ledger.yaml`, so every run answers OK `no capability ledger found (pre-cutover)`: a guard that cannot fire behind a hollow suite (audit MUST 2). No capability carried it.

**Approach:** Read the v1 ledger (header `schema`, `generated_by`, `updated`, `source_sha`, `extract`, `modes`; rows with `state` and `frozen_paths`) as data, freeze the constant `{rebuilding}`, keep `_changed_paths`, the existing `_is_frozen` match and the `degrade_on_exception` net, and report an absent subject as one cannot-evaluate WARN (AD-15). The schema version is not checked, so today's v0 file reads `0 frozen of <N> rows` until steward Story 121.3 regenerates it.

Ledger key: `56-1-frozen-path-changed-reads-the-ledger-s-rebuilding-rows-not-a-manifest-that-never-existed`.
Type / Effort / Deps: fix / M / —; cross-station: steward:S-120.2.

### Living CAP citations

- **`spec-pyforge-doctor` CAP-94** — a change under a rebuilding capability's frozen paths is named (minted 2026-11-10).
- **`fnd:AD-22`** — a rebuilding capability's paths are frozen (as steward Story 120.3 amends it); **`spec-foundry-capability-ledger:CAP-1`** — the v1 ledger schema.
- **`spec-pyforge-doctor` AD-15** — a source that cannot measure its subject says so in one cannot-evaluate WARN.

## Boundaries & Constraints

**Always:**
- Read the ledger as data; import no station (AD-1, AD-11); every git read through `cli_bridge.run_git` (AD-5).
- Keep the dispatcher's exit domain `{0, 2, 130}` (AD-2); a cannot-evaluate row carries `unevaluable: true` (AD-15).
- Build every test ledger under `tmp_path` with path joins and no tracked-path literal, so the module needs no `live_tree` mark.

**Never:**
- Never read a header key for the frozen set, never keep the `moving` state, never freeze a `cells:` entry.
- Never hand-edit `SPEC.md` (memlog, then `bmad-spec` or the anchored script render with both self-validate passes logged); never append a `Surface reconcile` line to another Spec's memlog or run `spec_surface_check.py --write-baseline` (Story 58.4 stamps every Spec once, last on the branch); never add new behaviour or a kill switch beyond this story's capability text (operator ruling of 2026-11-10: each gap is a deferred-work row).

## Acceptance Criteria

- **AC1 — The rewritten suite runs in the package half and keeps its size.** Expected: pytest exit 0; grep prints 20 or more.

  ```bash
  pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_frozen_path.py -q -m 'not live_tree' -p no:cacheprovider && grep -cE '^\s*(async\s+)?def test_' src/shared/packages/pyforge-doctor/tests/unit/test_sources_frozen_path.py
  ```

- **AC2 — The module runs in the package half (no live_tree mark in any form).** Expected: exit 1 (no match).

  ```bash
  git grep -n live_tree -- src/shared/packages/pyforge-doctor/tests/unit/test_sources_frozen_path.py
  ```

- **AC3 — The source no longer names a manifest or the move state.** Expected: exit 1 (no match).

  ```bash
  git grep -nE 'manifest\.(yaml|yml|json)|_MANIFEST_CANDIDATES|"moving"' -- src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/frozen_path.py
  ```

- **AC4 — Each rule has its case.** Expected: exit 0, 7 selected: one FAIL with evidence holding the row id and the path; one FAIL `guards nothing`; one OK `0 frozen of 1 rows`; three single WARNs with evidence['unevaluable'] is True; the v1 fixture (header schema, generated_by, updated, source_sha, extract, modes) parses with only the OK.

  ```bash
  pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_frozen_path.py -q -p no:cacheprovider -k 'rebuilding_row_with_changed_path or rebuilding_row_without_paths or planned_row_reports_zero_frozen or no_ledger_is_unevaluable or unparseable_ledger_is_unevaluable or origin_main_unresolvable_is_unevaluable or v1_fixture_header'
  ```

- **AC5 — On this tree the source reads the real ledger (story branch, v0 rows carry no state; the same after control-plane Story 121.3 regenerates it to v1).** Expected: exit 0; stdout matches `0 frozen of [0-9]+ rows` and does not contain `no capability ledger found`.

  ```bash
  pixi run --frozen -e pyforge-guild frozen-path-changed-check
  ```

- **AC6 — The flag gate passes this story's spec.** Expected: exit 0; the printed JSON object has "verdict": "pass".

  ```bash
  pixi run --frozen -e pyforge-guild flag-gate-check -- --spec "$(ls _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-56-1-*.md)"
  ```

- **AC7 — Lint, types and the doctor suite halves stay green.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild lint-types && pixi run --frozen -e pyforge-doctor pyforge-doctor-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-doctor CAP-94 (minted 2026-11-10); FR-25 ← CAP-94.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-10 (the cutover readiness audit) entry; the operator's rulings of 2026-11-10 in `docs/dreams/pyforge-unifying-strategy.md` § *Realization log*.
- Epic: Epic 56, minted with this story.
- Ledger key: `56-1-frozen-path-changed-reads-the-ledger-s-rebuilding-rows-not-a-manifest-that-never-existed` (`backlog`).
- Deps: —; cross-station: steward:S-120.2.
- Surface: `marshal-policy.toml` `[epic_surfaces]."56"`.
- Minted 2026-11-10 in the one chain commit of the integration branch `cutover-readiness-2026-11-10`, before any doctor story builds.

## Notes

- Code is wrong (audit defect: a guard that cannot fire, a hollow suite).
- The ledger v1 contract is control-plane's (steward Story 121.1; written into `extract.md` by its shared request 1): rows carry `state` (planned | rebuilding | verified-in-foundry | cut) and `frozen_paths` on rebuilding rows. The header's `frozen_states` equals the constant `{rebuilding}` this source uses.
- Match: equal to, or under `<p>/`, a frozen path (the existing `_is_frozen` semantics). `cells:` entries are never frozen.
- Fix the docstring's dead spine path; qualify bare CAP ids in the module (CHAIN-STANDARD section 6). The pixi task's description still says manifest: steward-station's shared request.
- Co-governor `spec-pyforge-core` (src/**): its reconcile line comes through the core-kit closer (marshal Story 117.8); every stamp runs once in Story 58.4.
- Cross-station deps: steward:S-120.2 (modes.md Schema v1).
- Rulings of 2026-11-10 applied (`docs/dreams/pyforge-unifying-strategy.md` § Realization log, the second addendum, 'Accept all, run mint'): a source that measured nothing reads `unmeasured`, a warning the merge bar does not fail on; `doctor flags kill-switch` stays Doctor's one actuator; doctor's closed one-time campaigns retire; the marker grammar is CHAIN-STANDARD section 4 as steward Story 120.3 amends it (`(retired <date>[: <reason>])` and semicolon qualifiers, no `(unbuilt)` token); the operator flips `pyforge.cutover_root` by hand once the Launch slice is proven, and nothing flips it automatically.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code (never through a pipe).

**Run before the push:**
- `pixi run --frozen -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check` — expected: exit 0 each.

## Spec Change Log

- 2026-11-10: minted from the station Dream's 2026-11-10 entry (the cutover readiness audit) and the operator's rulings of 2026-11-10.
