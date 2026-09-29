---
title: 'Index freshness is an advisory finding (Story 28.7, Epic 28)'
type: 'feature'
created: '2026-08-30'
status: 'done'
baseline_revision: 'de24e3961e7464d8f0019db4e28e1a46439e90cd'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: easy
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/integration-layers.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
deferred:
  - summary: >-
      Index freshness is not wired into spin/preflight admission verbs; only
      `marshal check` surfaces it today.
    evidence: |-
      Problem statement says "at admission time"; spec approach limits to
      marshal check. No hook in spin.py or preflight path.
    severity: medium
---

<intent-contract>

## Intent

**Problem:** A stale codegraph/cocoindex index silently degrades Layers 2–3 mid-run: the
agent answers structure questions from yesterday's graph or recompiles context it didn't
need to. Nothing surfaces staleness at admission time.

**Approach:** `marshal check` (the existing detector front door routing to the detector
registry) gains advisory codegraph/cocoindex staleness findings, evaluated against the
loop-home worktree state.

## Acceptance Criteria

- Given a stale or missing index in a home whose `[context]` block declares the layer, when
  `marshal check` runs, then a named advisory finding reports which index and why.
- Given the finding, when verdicts compute, then the exit-code domain `{0, 1, 2, 3, 4, 130}`
  is unchanged and the finding alone never blocks a run.
- Given a home with the layer declared off, when checked, then no staleness finding is
  raised.
- Given the detector registry, when this lands, then the new findings are registered like
  every other detector output — no second engine.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-marshal/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`. Ledger
key `28-7-index-freshness-is-an-advisory-finding`.

**Block If:** A change would turn the finding into a run-blocking gate or fork a second
detector engine.

**Never:** A competing PR verdict. Rebuilding indexes from inside the check (report, don't
mutate).

</intent-contract>

## Code Map

- `scripts/index_freshness_check.py` (runtime detector; emits `MRS-IDXF-*` via `_findings` JSON)
- `scripts/detectors.py` (`run_one` passes `--json`, parses `structured_findings`)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/check.py` (front door; surfaces structured findings as WARN)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` (registers `MRS-IDXF-001`..`004`)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py` (classifies all four as `Verdict.WARN`)
- `src/shared/packages/pyforge-marshal/tests/unit/test_index_freshness.py` (detector + advisory exit-domain tests)
- `src/shared/packages/pyforge-marshal/tests/unit/test_check.py` (marshal-check structured-findings integration)

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated
(finding raised / not raised, exit-domain unchanged, read-only). Land this spec in
`planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 28.7 and spec-marshal-token-economy CAP-10. Depends on Story 28.3's
seeded kit (there must be an index to judge). Advisory doctrine: findings inform, the
existing gates decide.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, including this story's own new/updated test coverage.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (no undeclared dependency surface).

## Spec Change Log

- 2026-08-30: drafted from epics.md Epic 28 for fleet-drain preflight (Dream/Spec chain: docs/dreams/marshal-token-economy.md → spec-marshal-token-economy)
- 2026-09-01: bmad-build-auto — wired structured `MRS-IDXF-*` findings through detectors.py → marshal check; added verdict classifications and station tests.
- 2026-09-01: review pass 2 — corrected index paths to match Story 28.3 kit (`.codegraph/codegraph.db`) and Scribe seam (`.claude/data/pyforge-scribe/cocoindex-index.json`); added canonical-path guard test.
- 2026-09-01: review pass 3 — fixed cocoindex layer gate to use closed vocabulary `derived-context` (not `incremental-derived-context`); forward loop-home identity in structured findings; added cocoindex + git-degradation test coverage.
- 2026-09-01: review pass 4 — malformed structured_findings no longer silently pass; fall back to MRS-CHECK-002 when parse yields zero valid entries.

- 2026-09-01: review pass 5 — added run_one subprocess integration test, layer-off JSON silence, MRS-IDXF-004 JSON, partial-malformed structured_findings regression; verification green.

## Review Triage Log

### 2026-09-01 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 0, medium 3, low 1)
- defer: 0
- reject: 0
- addressed_findings:
  - `[medium]` `[patch]` MRS-IDXF codes registered but missing from `_CLASSIFY_TABLE` — added WARN entries in verdict.py
  - `[medium]` `[patch]` marshal check emitted generic MRS-CHECK-002 instead of named MRS-IDXF findings — parse `structured_findings` in check.py
  - `[medium]` `[patch]` detectors.py stripped detector output before marshal check could see `_findings` — run index_freshness_check with `--json`, parse and forward structured findings
  - `[low]` `[patch]` no story-owned tests for AC coverage — added test_index_freshness.py and extended test_check.py

### 2026-09-01 — Review pass 2
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 1, medium 0, low 0)
- defer: 0
- reject: 0
- addressed_findings:
  - `[high]` `[patch]` detector checked wrong index paths (`.codegraph/index`, `.cocoindex/index`) — aligned to kit/scribe canonical locations so findings fire on real indices

### 2026-09-01 — Review pass 3
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 1, medium 1, low 1)
- defer: 2: (high 0, medium 1, low 1)
- reject: 0
- addressed_findings:
  - `[high]` `[patch]` cocoindex layer gate used `incremental-derived-context` instead of closed vocabulary `derived-context` — MRS-IDXF-003/004 never fired on real policy; fixed layer key and tests
  - `[medium]` `[patch]` structured findings dropped loop-home identity at marshal boundary — prefix message with `[home]` in detectors.py `_structured_findings_from_output`
  - `[low]` `[patch]` cocoindex MRS-IDXF-003/004 and git-degradation paths lacked detector-level tests — added coverage in test_index_freshness.py

### 2026-09-01 — Review pass 4
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 1, low 0)
- defer: 2: (high 0, medium 0, low 2)
- reject: 8
- addressed_findings:
  - `[medium]` `[patch]` malformed structured_findings silently skipped FINDINGS branch — only continue when at least one valid MRS-IDXF entry parsed; added regression tests in test_check.py

### 2026-09-01 — Review pass 5
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 0, medium 0, low 4)
- defer: 1: (high 0, medium 1, low 0)
- reject: 6
- addressed_findings:
  - `[low]` `[patch]` no run_one subprocess integration test — added test_run_one_index_freshness_check_wires_json_and_structured_findings
  - `[low]` `[patch]` layer-off not tested at main()/JSON level — added test_layer_off_main_emits_no_findings_json
  - `[low]` `[patch]` MRS-IDXF-004 missing JSON assertion — added test_json_output_stale_cocoindex_emits_mrs_idxf_004
  - `[low]` `[patch]` partial malformed structured_findings path untested — added test_partial_malformed_structured_findings_emits_valid_only

## Auto Run Result

Status: done

**Summary:** Story 28.7 (CAP-10) surfaces codegraph/cocoindex staleness as named advisory `MRS-IDXF-001`..`004` findings through the existing detector registry and `marshal check` front door. Stale/missing indices classify WARN (exit 0); layer-off homes raise no finding. Review pass 5 closed test gaps: run_one `--json` wiring, layer-off JSON silence, MRS-IDXF-004 JSON, partial-malformed structured_findings.

**Files changed:**
- `scripts/index_freshness_check.py` — runtime detector; canonical index paths; `derived-context` layer gate; emits `MRS-IDXF-*` via `_findings` JSON
- `scripts/detectors.py` — parse and forward `structured_findings` (with home prefix) from index_freshness_check JSON output
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/check.py` — emit MRS-IDXF WARN findings; fall back to MRS-CHECK-002 when structured parse yields zero valid entries
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` — register MRS-IDXF-001..004
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py` — classify MRS-IDXF-001..004 as Verdict.WARN
- `src/shared/packages/pyforge-marshal/tests/unit/test_index_freshness.py` — AC tests + run_one integration + layer-off/MRS-IDXF-004 JSON coverage
- `src/shared/packages/pyforge-marshal/tests/unit/test_check.py` — integration tests for structured findings path, malformed/empty fallback, partial-malformed
- `pixi.toml` — index-freshness-check task description (derived-context layer name)
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-28-7-index-freshness-is-an-advisory-finding.md` — status done, review log
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml` — ledger key `28-7-index-freshness-is-an-advisory-finding` → done

**Review findings:** pass 1: 4 patches; pass 2: 1 patch; pass 3: 3 patches; pass 4: 1 patch; pass 5: 4 patches (all low); 1 deferred; 6 rejected.

**Follow-up review recommendation:** false

**Verification:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test -- -k "index_freshness or malformed_structured or empty_structured or partial_malformed"` — 21 passed
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — 118 passed, 1 skipped

**Residual risks:** Runtime detector reads `~/.bmad-loops` loop homes (scope=runtime); CI excludes it via detectors-ci. Staleness is advisory-only at `marshal check` — not auto-wired into spin/preflight (deferred: admission-path hook). End-to-end `marshal check` → real detectors subprocess not covered in tests (marshal side uses _FakeProcess; detector side now has run_one integration).

## Status reconcile 2026-09-20

- frontmatter `status` `in-review` → `done` (ledger row `28-7-index-freshness-is-an-advisory-finding: done`).
