---
workflowStatus: 'completed'
totalSteps: 5
stepsCompleted: ['step-01-detect-mode', 'step-02-load-context', 'step-03-risk-and-testability', 'step-04-coverage-plan', 'step-05-generate-output']
lastStep: 'step-05-generate-output'
nextStep: ''
lastSaved: '2026-09-07'
workflowType: 'testarch-test-design'
inputDocuments:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/test-design-architecture.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - src/shared/packages/pyforge-warden/tests/ (file listing only)
---

# Test Design for QA: pyforge-warden Compliance Gate

**Purpose:** Test execution recipe for QA/maintainer. Defines what to test, how to test it, and what's needed from other teams.

**Date:** 2026-09-07
**Author:** rxm7706
**Status:** Draft
**Project:** pyforge-warden

**Related:** See Architecture doc (`test-design-architecture.md`) for testability concerns and architectural blockers.

**Stack note:** pyforge-warden is a stdlib-lean, non-interactive Python CLI (no browser, no HTTP API in its core gate path). The test framework is **pytest** (`tests/{unit,conformance,meta}/`), not Playwright — the workflow's default Playwright-utils examples are adapted to pytest throughout this document since there is no `page.goto`/`page.locator`/browser surface to exercise in the CLI core. The one HTTP-API surface in the wider system is the Epic-8 Django portal (`django-warden`); it is called out under Interworking, not folded into this CLI-gate coverage plan.

---

## Executive Summary

**Scope:** Test coverage for the four-axis compliance gate (hygiene, security, license, currency), its verdict/exit-code composition, the manifest-extraction bridge (E1), and the waiver/baseline suppression engine — all as already implemented in `src/shared/packages/pyforge-warden/`.

**Risk Summary:**

- Total Risks: 14 (5 high-priority score ≥6, 5 medium, 4 low)
- Critical Categories: SEC (false-green, DB integrity), OPS (CI wiring gap), DATA (baseline expiry cliff)

**Coverage Summary:**

- P0 tests: 8 (never-false-green invariants, verdict/exit correctness, security meta-tests)
- P1 tests: 8 (feed-absence gating, engine version drift, mapping confidence, determinism, actuator safety)
- P2 tests: 5 (identity merge, waiver schema validation, config precedence, ignore respect, empty-extraction downgrade)
- P3 tests: 3 (perf trend, dogfood self-scan, plugin-registration non-competition)
- **Total**: 24 scenarios (predominantly already covered by the existing 64-file suite — see Notes column); ~30-70 hours to close identified gaps, not to author net-new tests (~1-2 weeks, 1 engineer)

---

## Not in Scope

**Components or systems explicitly excluded from this test plan:**

| Item | Reasoning | Mitigation |
|---|---|---|
| **SARIF output** | Growth/v1.x tier, unbuilt | None needed yet; value-space reserved in the CLI contract |
| **Public PyPI/conda-forge publish + `--engine` swappability** | Growth/v1.x tier, unbuilt | None needed yet |
| **cf_atlas fleet-wide promotion (FR-16/18)** | Post-v1 backlog consumption seam | Report/SBOM `schema_version` stability covers the seam already |
| **Full conda↔PyPI name reconciliation** | Explicitly deferred (FR7) | Per-ecosystem attribution is preserved and reported as a documented, honest limitation |
| **Axes 5-6 (Sigstore/SLSA provenance, OpenSSF Scorecard)** | Vision tier, unbuilt | None needed yet |
| **Django-warden web portal UI/UX (Epic 8)** | Out of the core CLI-gate scope of this design | Covered by its own byte-equality-with-CLI invariant (`_phase_guard`); see Interworking |
| **Epic 11 advisory lenses (stories 11.1/11.2)** | Ledger status `blocked`/`backlog` — not yet implemented | Re-run this test design's epic-level companion once Epic 11 ships |

**Note:** Items listed here have been reviewed and are accepted as out-of-scope for this pass.

---

## Dependencies & Test Blockers

**CRITICAL:** these items, from the companion Architecture doc's Quick Guide, gate confident QA sign-off on the next false-green-triad-touching change.

### Backend/Architecture Dependencies (Pre-Implementation)

**Source:** See Architecture doc "Quick Guide" for detailed mitigation plans

1. **Corpus-oracle + differential-oracle CI wiring (R-002)** - Platform/CI - Before next extractor-touching story
   - QA needs a scheduled workflow actually executing `pyforge-warden-test-corpus-oracle`.
   - Without it, an extractor regression merges green through the default gate.

2. **Baseline expiry staggering decision (R-003)** - Warden maintainer - Before 2027-07-24
   - QA needs to know whether the 19-entry simultaneous expiry will be staggered or intentionally left as a scheduled event.
   - Without a decision, the eventual red run is indistinguishable from a real regression.

### QA Infrastructure Setup (Already in Place)

1. **Test fixtures** - already exist: `tests/fixtures/{recipes,lockfiles,malicious,engine-output,corpus,eligibility_corpus,osv-db,projects}/`.
2. **Test environments** - `pixi run -e pyforge-warden pyforge-warden-test` (default, excludes `-m slow`); no separate CI/staging environment needed (single-process CLI, no service to deploy).

**Example test pattern actually used in this repo** (pytest, not Playwright):

```python
import pytest
from pyforge.warden.verdict import compose_verdict
from pyforge.warden.models import Status

@pytest.mark.parametrize(
    "statuses,expected_exit",
    [
        ([Status.CLEAN], 0),
        ([Status.INDETERMINATE], 1),
        ([Status.ERROR], 2),
    ],
)
def test_exit_projection_pinned(statuses, expected_exit):
    verdict = compose_verdict(statuses)
    assert verdict.exit_code == expected_exit
```

---

## Risk Assessment

**Note:** Full risk details in Architecture doc. This section summarizes risks relevant to QA test planning.

### High-Priority Risks (Score ≥6)

| Risk ID | Category | Description | Score | QA Test Coverage |
|---|---|---|---|---|
| **R-001** | SEC | Undetected false-green regression | **9** | P0-001: adversarial fixture corpus (0 exit-0) |
| **R-002** | OPS | Corpus/differential-oracle has no CI wiring | **6** | P0-003, P0-004: keep the tests green locally; CI wiring is a process fix, not a new test |
| **R-003** | DATA | 19 baseline entries expire simultaneously | **6** | P0-006: baseline/waiver expiry re-block behavior |
| **R-004** | SEC | Offline DB staleness/poisoning | **6** | P0-002: DB content pre-flight |
| **R-005** | TECH | E1 extractor regression undetected | **6** | P0-003, P0-004 |

### Medium/Low-Priority Risks

| Risk ID | Category | Description | Score | QA Test Coverage |
|---|---|---|---|---|
| R-006 | TECH | osv-scanner Scalibr migration output drift | 4 | P1-002: engine version-range pre-flight |
| R-007 | DATA | Baseline ID hardcodes interpreter version | 4 | P0-006 (regression-adjacent; no dedicated test yet) |
| R-008 | BUS | DEP001 mapping-confidence mis-score | 4 | P1-003 |
| R-009 | PERF | Perf overhead has no trend tracking | 4 | P3-001 |
| R-010 | OPS | Feed-cache staleness across fleet, no described refresh job | 4 | P1-001 (feed-absence semantics only; refresh-job ownership is a process gap) |
| R-011 | SEC | Waiver/baseline authorship unverified (accepted) | 3 | P2-002 |
| R-012 | SEC | Fix-PR actuator forge-egress bug | 3 | P1-005 |
| R-013 | TECH | Schema single-writer violation | 2 | P1-007 |
| R-014 | DATA | Cross-ecosystem identity merge ambiguity | 2 | P2-001 |

---

## NFR Test Coverage Plan

**Purpose:** Map NFR requirements to planned validation work. Does not assign final PASS/CONCERNS/FAIL status.

| NFR Category | Requirement / Threshold | Planned Validation | Tool / Level | Evidence Artifact | Priority |
|---|---|---|---|---|---|
| Security | NFR-S1 (no execution), NFR-S2 (no silent egress) | AST-denylist over `extract/`; socket-guard over the orchestrator process | meta/pytest | `meta/test_extract_no_execution.py`, `meta/test_socket_deny_alive.py` | P0 |
| Security | NFR-S8 (trusted DB integrity) | Content pre-flight on `all.zip` (advisory-count ≥1, case-sensitive dir check) | conformance/pytest | `conformance/test_osv_offline_db_spike.py` | P0 |
| Performance | NFR-P-warm (≤~2s p95 overhead, engines stubbed) | Benchmark with engines stubbed; p95/median over N runs | conformance/pytest | `conformance/test_perf_overhead.py` (no trend dashboard yet — R-009) | P3 |
| Reliability | NFR-R1/R2 (0 exceptions, ratcheted unparseable-rate over ~1,950 recipes) | Corpus-conformance sweep | conformance/pytest, `-m slow` | `conformance/test_corpus_regression.py` (not CI-scheduled — R-002) | P0 |
| Reliability | NFR-R3b (determinism) | Twice-run byte-identical in `--deterministic` mode | conformance/pytest | `conformance/test_corpus_determinism.py` | P1 |
| Maintainability | FR38 (single schema-writer) | `_REPORT_AXES` completeness + exact-13 `Component` shape | conformance/pytest | `conformance/test_report_schema.py`, `conformance/test_sbom_schema.py` | P1 |

**Missing thresholds or evidence sources:** the concrete NFR-P-warm p95 numeric target and the `--db-max-age` calibration value are not pinned to a number in the source documents — both need stakeholder clarification before `nfr-assess` can render a final verdict on Performance.

---

## Entry Criteria

**QA testing cannot begin until ALL of the following are met:**

- [x] Requirements agreed (PRD + architecture both `status: complete`/reconciled 2026-08-26)
- [x] Test fixtures ready (`tests/fixtures/*` already committed)
- [ ] Corpus-oracle/differential-oracle CI wiring resolved (R-002) — open
- [ ] Baseline-expiry staggering decision made (R-003) — open

## Exit Criteria

**Testing phase is complete when ALL of the following are met:**

- [ ] All P0 tests passing (already true locally; CI-wiring gap for the `-m slow` subset is the open item)
- [ ] All P1 tests passing or failures triaged
- [ ] No open high-priority (≥6) risk without an assigned mitigation owner
- [ ] `unparseable_rate` baseline diff reviewed on the current HEAD

---

## Project Team (Optional)

| Name | Role | Testing Responsibilities |
|---|---|---|
| rxm7706 | Maintainer / Sole QA+Dev | Test strategy, all test levels, waiver/baseline schema ownership (P7 persona in the PRD) |

---

## Test Coverage Plan

**IMPORTANT:** P0/P1/P2/P3 = **priority and risk level**, NOT execution timing. See "Execution Strategy" for timing.

### P0 (Critical)

**Criteria:** Blocks core functionality + High risk (≥6) + No workaround

| Test ID | Requirement | Test Level | Risk Link | Notes |
|---|---|---|---|---|
| **P0-001** | Adversarial fixture corpus: 0 fixtures exit-0 across false-green vectors | Conformance | R-001 | Existing; confirm PR-gated on triad-module diffs |
| **P0-002** | DB content pre-flight rejects empty/corrupt `all.zip`, never silent-clean | Conformance | R-004 | `test_osv_offline_db_spike.py`; story 1.4 decision record |
| **P0-003** | Corpus-conformance: 0 uncaught exceptions across ~1,950 recipes, ratcheted rate | Conformance (`-m slow`) | R-002, R-005 | `test_corpus_regression.py`; **not CI-scheduled** |
| **P0-004** | Differential-oracle: E1 dep-set ⊇ authoritative renderer's | Conformance (`-m slow`) | R-002, R-005 | `test_extraction_oracle.py`; stories 2.2/2.3 |
| **P0-005** | Verdict/exit projection pinned: `{clean,not-applicable,bypassed}→0`, `policy-violation→1`, `indeterminate→1`, `error→2`, SIGINT→130 | Unit + Meta | (C0) | `test_verdict_sole_ownership.py`; stories 1.1/1.6 |
| **P0-006** | Baseline & waiver suppression: expired → re-block; applied entries echoed; baseline blocks NEW findings only | Conformance | R-003, R-007 | `test_baseline_grandfathering.py`; story 6.8 |
| **P0-007** | Extractor no-execution invariant (AST-denylist) | Meta | (NFR-S1) | `test_extract_no_execution.py` |
| **P0-008** | Socket-deny: orchestrator process opens no socket outside the actuator carve-out | Meta | (NFR-S2) | `test_socket_deny_alive.py` |

**Total P0:** 8 tests (all already exist in code; the gap is CI scheduling for P0-003/P0-004)

---

### P1 (High)

**Criteria:** Important features + Medium/high risk + Common workflows

| Test ID | Requirement | Test Level | Risk Link | Notes |
|---|---|---|---|---|
| **P1-001** | KEV/EPSS feed-absence under an active policy → `indeterminate`, never silent no-op | Conformance | R-010 | `test_kev_enrichment.py`, `test_epss_enrichment.py`; stories 6.4/6.7 |
| **P1-002** | Engine version-range pre-flight fails loud on out-of-range deptry/osv-scanner | Meta/Conformance | R-006 | `test_engine_version_range_sync.py`; story 6.6 |
| **P1-003** | DEP001 mapping-confidence gate: high-confidence blocks, ambiguous warns | Unit | R-008 | story 2.1; `hygiene.py` join logic |
| **P1-004** | Determinism: twice-run byte-identical in `--deterministic` mode | Conformance | (NFR-R3b) | `test_corpus_determinism.py` |
| **P1-005** | Fix-PR actuator: opt-in only, post-verdict, never mutates scanned tree; dry-run opens no sockets | Conformance | R-012 | `test_fix_pr_actuator.py`; story 6.9 |
| **P1-006** | Engine parallelism: all v1 axes run independently, no shared mutable state | Conformance | (NFR-P-concurrency) | `test_engine_parallelism.py` |
| **P1-007** | Report/SBOM schema self-validation + `len(SBOM.components) == inventory_count` | Conformance | R-013 | `test_report_schema.py`, `test_sbom_schema.py`; stories 4.1/6.1 |
| **P1-008** | `scan --doctor`: exit 0 healthy / exit 2 + typed `error_kind` on problem, never exit 1 | Unit | (D8) | `test_doctor.py` |

**Total P1:** 8 tests (all already exist in code)

---

### P2 (Medium)

**Criteria:** Secondary flows + low/medium risk + acceptable workaround exists

| Test ID | Requirement | Test Level | Risk Link | Notes |
|---|---|---|---|---|
| **P2-001** | Cross-ecosystem `(ecosystem, name, version)` merge never double-counts or mis-attributes | Unit | R-014 | `inventory.py` identity/merge rules |
| **P2-002** | Waiver file schema validation rejects malformed/malicious entries | Unit | R-011 | `waiver.py` |
| **P2-003** | `[tool.deptry]` ignore respected end-to-end | Integration | — | FR9 |
| **P2-004** | Config precedence (`pyproject.toml` vs `pixi.toml`, CLI override) resolves deterministically, conflicts surfaced | Unit | — | FR30 `ConfigLoader` |
| **P2-005** | `--allow-empty` downgrades a deliberate empty-extraction monorepo sweep to `coverage: none` | Unit | — | FR22 |

**Total P2:** 5 tests

---

### P3 (Low)

**Criteria:** Nice-to-have + exploratory + benchmarks

| Test ID | Requirement | Test Level | Notes |
|---|---|---|---|
| **P3-001** | NFR-P-warm overhead p95 benchmark (engines stubbed) | Performance | `test_perf_overhead.py`; feeds R-009 |
| **P3-002** | Dogfood: this repo's own scan stays clean/warn, never error | Conformance | `test_dogfood.py`; subject to the R-003 expiry cliff |
| **P3-003** | SKF skill / `bmad-agent-warden` persona never publish a second PR-gate verdict | Meta | `test_pr_gate_plugin_registration.py`; Epic 9 |

**Total P3:** 3 tests

---

## Execution Strategy

**Philosophy:** Run everything in PRs unless it carries real infrastructure overhead. This is a stdlib CLI test suite (pytest), not a browser suite — no parallelization framework beyond pytest's own is assumed.

### Every PR: `pixi run -e pyforge-warden pyforge-warden-test` (default marker excludes `-m slow`)

- Unit, most conformance, and all meta tests (P0-005, P0-007, P0-008, P1-002 through P1-008, all of P2).
- Exact wall-clock runtime was not measured in this pass; the default suite is expected to be well under the PR-fast-feedback threshold given its scope (64 files, no I/O-heavy corpus sweep).

**Why run in PRs:** fast feedback, no expensive infrastructure.

### Nightly/Weekly: `-m slow` marked suites (~unmeasured; currently **not scheduled at all** — R-002)

- Corpus-conformance regression (P0-003), differential-oracle (P0-004), perf-overhead benchmark (P3-001).

**Why defer to nightly/weekly:** these sweep ~1,950 real recipe fixtures and a rendered-oracle comparison — expensive relative to the rest of the suite, per the architecture's own `-m slow` marking decision (story 5.2).

**Manual/dogfood** (not on the default schedule): `test_dogfood.py` (P3-002) runs this repo's own recipes against the shipped baseline; subject to the R-003 expiry cliff.

---

## QA Effort Estimate

**Gap-closure effort only** (the 64-file suite already exists; this estimates closing R-001 through R-014's open items, not authoring net-new tests):

| Priority | Count | Effort Range | Notes |
|---|---|---|---|
| P0 | 8 | ~15-25 hours | Mostly CI/scheduler wiring (R-002) + confirming PR-gating on triad diffs (R-001); tests themselves exist |
| P1 | 8 | ~10-20 hours | Version-range re-conformance (R-006), baseline-ID follow-up design (R-007) |
| P2 | 5 | ~5-15 hours | Spot-check existing coverage; no known gaps |
| P3 | 3 | ~2-8 hours | Perf-trend wiring (R-009) |
| **Total** | 24 | **~30-70 hours** | **~1-2 weeks, 1 engineer** |

**Assumptions:**

- Excludes ongoing maintenance.
- Assumes the existing 64-file suite is the baseline, not a green-field build.

---

## Implementation Planning Handoff (Optional)

| Work Item | Owner | Target Milestone | Dependencies/Notes |
|---|---|---|---|
| Wire corpus-oracle suite to a scheduled CI workflow | Platform/CI | Before next extractor story | R-002 |
| Stagger or accept the 2027-07-24 baseline expiry cliff | Warden maintainer | Before 2027-07-24 | R-003 |
| Track NFR-P-warm p95 trend | Platform/CI | Opportunistic | R-009 |

---

## Tooling & Access

| Tool or Service | Purpose | Access Required | Status |
|---|---|---|---|
| pytest + `-m slow` marker | Test execution and suite partitioning | None (already in pixi env) | Ready |
| ruff | Lint gate | None | Ready |
| CI workflow/scheduler edit rights | Wire the `-m slow` suites to a recurring run (R-002) | Repo write access to `.github/workflows/` or the fleet scheduler | Pending |

---

## Interworking & Regression

| Service/Component | Impact | Regression Scope | Validation Steps |
|---|---|---|---|
| **django-warden portal (Epic 8)** | Calls the same engines via Celery, async | Results must render byte-equal to the CLI (`_phase_guard`-derived progress) | Portal regression suite (out of this CLI-focused design's scope) |
| **`pyforge.core.hooks` plugin registration (Epic 9)** | Commercial scanners register as optional plugins | Default run must stay green with no plugin present | `test_pr_gate_plugin_registration.py` |
| **cf_atlas (post-v1 consumption seam)** | Consumes the report/SBOM contract | `schema_version` must remain additive-only | `test_report_schema.py` |

**Regression test strategy:**

- The default `pyforge-warden-test` suite is the regression gate for every PR; the `-m slow` suites are the deeper regression gate once R-002 schedules them.

---

## Appendix A: Code Examples & Tagging

**pytest markers for selective execution** (this repo's actual convention; no Playwright tags apply — there is no browser surface):

```python
import pytest

@pytest.mark.slow
def test_corpus_zero_uncaught_exceptions(recipe_corpus):
    for recipe_path in recipe_corpus:
        result = extract(recipe_path)  # must never raise
        assert result is not None

def test_verdict_never_false_green(adversarial_fixture):
    report = run_scan(adversarial_fixture)
    assert report.exit_code != 0
```

**Run specific subsets:**

```bash
# Default PR gate (excludes -m slow)
pixi run -e pyforge-warden pyforge-warden-test

# The corpus-oracle + differential-oracle + perf suites (currently unscheduled — R-002)
pixi run -e pyforge-warden pyforge-warden-test-corpus-oracle
```

---

## Appendix B: Knowledge Base References

- **Risk Governance**: `risk-governance.md` - Risk scoring methodology
- **Test Priorities Matrix**: `test-priorities-matrix.md` - P0-P3 criteria
- **Test Levels Framework**: `test-levels-framework.md` - E2E vs API vs Unit selection
- **Test Quality**: `test-quality.md` - Definition of Done

---

**Generated by:** BMad TEA Agent
**Workflow:** `bmad-testarch-test-design`
**Version:** 5.0 (Step-File Architecture)
