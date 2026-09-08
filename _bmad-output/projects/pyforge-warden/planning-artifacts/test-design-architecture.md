---
workflowStatus: 'completed'
totalSteps: 5
stepsCompleted: ['step-01-detect-mode', 'step-02-load-context', 'step-03-risk-and-testability', 'step-04-coverage-plan', 'step-05-generate-output']
lastStep: 'step-05-generate-output'
nextStep: ''
lastSaved: '2026-09-07'
workflowType: 'testarch-test-design'
inputDocuments:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/prds/prd-pyforge-warden-2026-07-14/prd.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/architecture/architecture-pyforge-warden-2026-07-14/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/sprint-status-ledger.yaml
  - src/shared/packages/pyforge-warden/tests/ (file listing only)
---

# Test Design for Architecture: pyforge-warden Compliance Gate

**Purpose:** Architectural concerns, testability gaps, and NFR requirements for review by Architecture/Dev teams. Serves as a contract between QA and Engineering on what must be addressed to keep the never-false-green invariant provably true as the system evolves.

**Date:** 2026-09-07
**Author:** rxm7706
**Status:** Architecture Review Pending
**Project:** pyforge-warden
**PRD Reference:** `planning-artifacts/prds/prd-pyforge-warden-2026-07-14/prd.md`
**ADR Reference:** `planning-artifacts/architecture/architecture-pyforge-warden-2026-07-14/ARCHITECTURE-SPINE.md`

**Scope note:** pyforge-warden's v1 core (FR1-FR40, 6 epics, 31 stories) plus five post-v1 epics (7-11, 12 more stories) are already `done` in `sprint-status-ledger.yaml` — this is a **retrospective hardening test design** over a shipped, dogfooded system (64 existing test files under `src/shared/packages/pyforge-warden/tests/`), not a pre-implementation gate. "Blockers" below are backlog-worthy CI/process gaps, not build-blocking dependencies. Epic 11 (advisory lenses; stories 11.1/11.2) is the one epic still `blocked`/`backlog`.

---

## Executive Summary

**Scope:** A non-interactive CLI quality gate running four axes (hygiene/deptry, security/osv-scanner+KEV+EPSS, license, currency) over Python projects sourced from PyPI or conda-forge, emitting one schema-validated `ComplianceReport` + CycloneDX SBOM behind one exit code.

**Business Context** (from PRD):

- **Problem:** Dependency hygiene and vulnerability scanning are disjointed tools; conda/pixi projects are second-class because neither `deptry` nor `osv-scanner` parses `pixi.toml`/`environment.yml`/recipe formats natively.
- **Anti-metric:** gate-disabled events → target 0. The acceptance property (C0) is **the gate never emits a false-green.**
- **GA status:** shipped — v1 (Epics 1-6) plus Epics 7-10 are `done`; Epic 11 is `blocked`/`backlog`.

**Architecture** (from `architecture.md`):

- **Key Decision 1:** One `ResolvedInventory` spine — discovery/extraction produce it, both engines and all four axis producers annotate it, report/SBOM/verdict read it (never re-defined).
- **Key Decision 2:** The false-green triad — an `indeterminate` verdict state above `warn`, a locked 7→4 exit projection, and Gap-C's ecosystem-identity withhold — sound only together.
- **Key Decision 3:** Stack — stdlib-lean Python ≥3.12 CLI (`argparse`, `tomllib`, `re`) plus four targeted safe deps (PyYAML `safe_load`, `packaging`, `cyclonedx-python-lib`, `jsonschema`); `deptry` + `osv-scanner` as conda run-deps; no CLI framework, no Jinja rendering.

**Expected Scale:** Single-process, per-invocation cost independent of fleet size (NFR-P-concurrency); designed for a 20,000+ repo fleet via CI-template composition, not in-tool aggregation.

**Risk Summary:**

- **Total risks:** 14
- **High-priority (≥6):** 5 risks requiring attention before the next change to a false-green-triad module
- **Test effort:** the P0-P3 scenarios below are mostly *already implemented* (64 test files exist); estimated **~30-70 hours** to close the identified CI/process gaps (see companion QA doc)

---

## Quick Guide

### 🚨 BLOCKERS - Team Must Decide (Can't Proceed Without)

1. **R-001: Undetected regression against the never-false-green invariant (C0)** - the single highest-scored risk in this document (9/9, CRITICAL) — an engine/DB/extractor change could silently regress the never-false-green invariant unless the adversarial fixture corpus (0 fixtures exit-0) is maintained and PR-gated on every touch of `extract/`, `engines.py`, `verdict.py`, `feeds.py` (recommended owner: Warden maintainer + CI).
2. **R-002: Corpus-oracle / differential-oracle suite has no CI wiring** - No workflow or scheduler ever runs `pyforge-warden-test-corpus-oracle`, and Story 5.2 moved the 4 precision differential-oracle tests (2.2/2.3) out of the default gate with it — the strongest correctness check in the architecture (0-uncaught-exceptions over ~1,950 real recipes, ratcheted unparseable-rate, differential-oracle ⊇ real renderer) is currently unexecuted by CI (recommended owner: Platform/CI, Marshal station).
3. **R-003: 19 baseline entries expire simultaneously on 2027-07-24** - `.warden-baseline.yaml` re-blocks all 19 grandfathered findings on the same calendar date, which an unattended loop would triage as a code regression rather than a scheduled event (recommended owner: Warden maintainer).
4. **R-004: Offline vuln-DB content pre-flight is a single point of truth for "never confident-clean on a corrupt DB"** - confirm this invariant carries its own dedicated regression test so a future `engines.py`/loader refactor cannot silently drop it (recommended owner: Warden maintainer).

**What we need from team:** Close or explicitly accept these 4 items; none require a design change, only CI/process wiring.

---

### ⚠️ HIGH PRIORITY - Team Should Validate (We Provide Recommendation, You Approve)

1. **R-006: osv-scanner 2.5.0 migrated to OSV-Scalibr end-to-end** - Recommend a deliberate conformance re-run against 2.5.x output shape before widening the story-6.6 version-range pin past the currently-pinned range (implementation phase; Warden maintainer proposes, Architecture approves the widened range).
2. **R-007: `.warden-baseline.yaml`'s first entry hardcodes the running interpreter's patch version** (`currency:unknown:!python-runtime@3.14.6`) - a pixi-environment Python bump silently un-matches it, resurfacing as un-grandfathered `warn` noise. Recommend a version-agnostic baseline-ID scheme as a Story 6.8 follow-up (implementation phase).
3. **R-009: NFR-P-warm (≤~2s p95 overhead, engines stubbed) has a test but no tracked trend** - Recommend wiring `test_perf_overhead.py`'s output to a tracked artifact so a regression is a visible diff, not a silent creep (implementation phase).

**What we need from team:** Review recommendations and approve (or suggest changes).

---

### 📋 INFO ONLY - Solutions Provided (Review, No Decisions Needed)

1. **Test strategy**: pytest unit/conformance/meta split, one module per pipeline stage (already shipped, 64 files) — see companion QA doc for the coverage matrix.
2. **Tooling**: pytest + ruff + `jsonschema` (schema self-validation); `-m slow` marker isolates the corpus/differential-oracle/perf suites from the default PR gate.
3. **Tiered CI**: PR = default `pyforge-warden-test` (excludes `-m slow`); Nightly/Weekly = the `-m slow` suites, once R-002 wires them to a schedule.
4. **Coverage**: ~24 test scenarios prioritized P0-P3 in the companion QA doc, cross-referencing the existing 64-file suite rather than proposing net-new tests where coverage already exists.
5. **Quality gates**: P0 100%, P1 ≥95%, corpus regression non-increasing, false-green=0 adversarial fixture gate.

**What we need from team:** Just review and acknowledge (we already have the solution).

---

## For Architects and Devs - Open Topics 👷

### Risk Assessment

**Total risks identified**: 14 (5 high-priority score ≥6, 5 medium, 4 low)

#### High-Priority Risks (Score ≥6) - IMMEDIATE ATTENTION

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner | Timeline |
|---|---|---|---|---|---|---|---|---|
| **R-001** | **SEC** | An engine/DB/extractor change silently regresses the never-false-green invariant (C0) | 3 | 3 | **9** | Maintain + PR-gate the adversarial fixture corpus (0 fixtures exit-0) on every touch of `extract/`, `engines.py`, `verdict.py`, `feeds.py` | Warden maintainer + CI | Before next release touching a triad module |
| **R-002** | **OPS** | Corpus-oracle + differential-oracle suites (DW-5-2-5) have no CI workflow or scheduler entry | 3 | 2 | **6** | Add a nightly/weekly workflow invoking `pyforge-warden-test-corpus-oracle`; alert distinctly from the default suite | Platform/CI (Marshal) | Before next extractor-touching story |
| **R-003** | **DATA** | 19 `.warden-baseline.yaml` entries expire simultaneously 2027-07-24 (DW-5-2-7) | 3 | 2 | **6** | Stagger expiries or re-stamp on a rolling schedule; surface an early-warning via `scan --doctor` | Warden maintainer | Well before 2027-07-24 |
| **R-004** | **SEC** | Offline OSV-DB staleness/poisoning (empty/corrupt `all.zip`) could silently exit clean if the content pre-flight regresses | 2 | 3 | **6** | Dedicated regression test asserting empty/corrupt-zip → non-clean status; keep `snapshot_at=None` → `indeterminate` asserted in the adversarial suite | Warden maintainer | Ongoing (regression-test audit) |
| **R-005** | **TECH** | E1's lossy stdlib extractor (6 Jinja/selector-laden formats) regresses undetected while R-002 is unwired | 2 | 3 | **6** | Depends on R-002; keep the supported-construct matrix current; version-control the ratcheted `unparseable_rate` baseline explicitly | Warden maintainer | Tied to R-002 |

#### Medium-Priority Risks (Score 3-5)

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner |
|---|---|---|---|---|---|---|---|
| R-006 | TECH | osv-scanner 2.5.0's Scalibr migration is a pipeline replacement, not a point release — output-shape drift risk on the next in-range bump | 2 | 2 | 4 | Deliberate conformance re-run against 2.5.x before widening the version-range pin (story 6.6) | Warden maintainer |
| R-007 | DATA | Baseline finding-ID hardcodes interpreter patch version (DW-5-2-6) — a Python bump silently un-matches it | 2 | 2 | 4 | Version-agnostic baseline-ID scheme (Story 6.8 follow-up) | Warden maintainer |
| R-008 | BUS | DEP001 mapping-confidence gate mis-scores an ambiguous conda↔PyPI mapping (false-block or false-pass) | 2 | 2 | 4 | Confirm the exact-map-hit-vs-multi-spelling-guess threshold stays documented and tested per story 2.1 | Warden maintainer |
| R-009 | PERF | NFR-P-warm (≤~2s p95) is asserted once, not trended — a slow regression could go unnoticed | 2 | 2 | 4 | Wire `test_perf_overhead.py` output to a tracked artifact | Platform/CI |
| R-010 | OPS | KEV/EPSS/endoflife cached-feed staleness across a 20k-repo fleet has a documented absence rule but no described refresh cadence job | 2 | 2 | 4 | Document the refresh-job ownership for `feeds.py`'s cache layer | Platform/CI |

#### Low-Priority Risks (Score 1-2)

| Risk ID | Category | Description | Probability | Impact | Score | Action |
|---|---|---|---|---|---|---|
| R-011 | SEC | Waiver/baseline file is untrusted input by design; the tool never verifies authorship | 1 | 3 | 3 | Monitor — accepted v1 assumption (git + CODEOWNERS is the boundary) |
| R-012 | SEC | Fix-PR actuator (`actuator.py`) is the sole forge-egress module; a bug could open unintended PRs | 1 | 3 | 3 | Monitor — mitigated by opt-in flag, env-only credentials, post-verdict invocation, dry-run carve-out |
| R-013 | TECH | A future producer story could widen the report schema outside the sanctioned 6.1 amendment | 1 | 2 | 2 | Monitor — enforced by `_REPORT_AXES` + exact-13 `Component` meta-test |
| R-014 | DATA | Cross-ecosystem `(ecosystem, name, version)` merge could double-count or mis-attribute a component | 1 | 2 | 2 | Monitor — architecture states merge rules explicitly; no evidence of a defect |

#### Risk Category Legend

- **TECH**: Technical/Architecture (flaws, integration, scalability)
- **SEC**: Security (access controls, auth, data exposure)
- **PERF**: Performance (SLA violations, degradation, resource limits)
- **DATA**: Data Integrity (loss, corruption, inconsistency)
- **BUS**: Business Impact (UX harm, logic errors, revenue)
- **OPS**: Operations (deployment, config, monitoring)

---

### NFR Testability Requirements

**Purpose:** Capture what architecture must provide so NFR validation can be automated later. This is planning guidance, not final evidence assessment.

| NFR Category | Threshold / Requirement | Current Design Support | Gap / Decision Needed | Planned Evidence |
|---|---|---|---|---|
| Security | NFR-S1-S9: no-execution extractor, no silent egress, waiver least-privilege, output neutralization, trusted-DB integrity | Supported — AST-denylist + socket-guard are enforced meta-tests, not unprovable negatives | None blocking; R-004's content pre-flight should have an explicit, named regression test | `meta/test_extract_no_execution.py`, `meta/test_socket_deny_alive.py`, adversarial fixture corpus |
| Performance | NFR-P-warm ≤~2s p95 overhead (engines stubbed); NFR-P-cold one-time DB provisioning; NFR-P-concurrency no shared state | Partial — test exists, no trend tracking (R-009) | Exact numeric p95 baseline on the pinned reference corpus/hardware is **UNKNOWN** (not stated as a concrete number in PRD/architecture beyond "~2s") | `conformance/test_perf_overhead.py`, `conformance/test_engine_parallelism.py` |
| Reliability | NFR-R1 (0 uncaught exceptions/~1,950-file corpus), NFR-R2 (ratcheted unparseable-rate), NFR-R3a/b (no-mutation + determinism), NFR-R5 (engine timeout) | Supported in test code, **not executed in CI** (R-002) | CI/scheduler wiring for the `-m slow` corpus + differential-oracle suites | `conformance/test_corpus_regression.py`, `conformance/test_extraction_oracle.py`, `conformance/test_corpus_determinism.py` |
| Maintainability | FR38 single-schema-writer discipline; canonical StrEnum-only vocabulary | Supported — `_REPORT_AXES` + exact-13 `Component` meta-test enforce it | None blocking | `conformance/test_report_schema.py`, ruff lint gate |

**Unknown thresholds:** the concrete NFR-P-warm p95 numeric target (named corpus + reference hardware) and the `--db-max-age` default (currently 7d, flagged by the architecture's own Gap Analysis as needing calibration) — both carried forward as clarification items, not guessed.

**Assessment boundary:** Final PASS/CONCERNS/FAIL status belongs in `nfr-assess` after implementation evidence exists.

---

### Testability Concerns and Architectural Gaps

**🚨 ACTIONABLE CONCERNS - Architecture Team Must Address**

#### 1. Blockers to Fast Feedback (WHAT WE NEED FROM ARCHITECTURE)

| Concern | Impact | What Architecture Must Provide | Owner | Timeline |
|---|---|---|---|---|
| **No CI/scheduler entry for `-m slow` suites** | The corpus-conformance, differential-oracle, and perf-overhead tests exist but never run automatically — regressions surface only on manual runs | A nightly/weekly workflow (or scheduler entry) invoking `pyforge-warden-test-corpus-oracle` | Platform/CI | Pre-next extractor-touching story |
| **Baseline expiry cliff has no early-warning signal** | A future `scan --doctor` run gives no hint that 19 findings will re-block on the same date | A "N baseline entries expire within 90 days" check surfaced by `scan --doctor` | Warden maintainer | Backlog |

#### 2. Architectural Improvements Needed (WHAT SHOULD BE CHANGED)

1. **Baseline finding-ID version-agnosticism**
   - **Current problem**: the currency-axis baseline entry embeds the exact interpreter patch version in its finding ID.
   - **Required change**: a version-agnostic ID grammar for runtime-derived findings (Story 6.8 follow-up).
   - **Impact if not fixed**: every pixi-environment Python bump produces un-grandfathered `warn` noise indistinguishable from a new finding.
   - **Owner**: Warden maintainer.
   - **Timeline**: opportunistic, tied to the next 6.8-touching change.

---

### Testability Assessment Summary

**📊 CURRENT STATE - FYI**

#### What Works Well

- One `ResolvedInventory` + canonical `StrEnum` model (`Status`, `ErrorKind`, `WithholdReason`, `Ecosystem`) gives every test a single seam to assert against — no parallel shapes to reconcile.
- Security invariants are enforced *mechanisms*, not unprovable negatives: `meta/test_extract_no_execution.py` (AST-denylist) and `meta/test_socket_deny_alive.py` (socket-guard) turn "no execution / no egress" into deterministic pass/fail.
- `verdict.py`'s sole-ownership wall is itself under a meta-test (`meta/test_verdict_sole_ownership.py`) — the exit-code seam cannot be silently duplicated by a new module.
- 64 test files already exist across `unit/`, `conformance/`, and `meta/`, mirroring the module structure 1:1 — this is a mature harness, not a green-field testability problem.

#### Accepted Trade-offs (No Action Required)

- **Waiver/baseline authorship is unverified at runtime (NFR-S3)** — the tool enforces schema + expiry only; authenticity is delegated to git + CODEOWNERS. Documented as a resolved v1 assumption; acceptable as-is.
- **cf_atlas fleet-wide aggregation is out of scope (J3)** — satisfied by CI-template composition, not an in-tool capability. Acceptable as-is; not technical debt.

---

### Risk Mitigation Plans (High-Priority Risks ≥6)

#### R-001: Undetected regression against the never-false-green invariant (Score: 9) - CRITICAL

**Mitigation Strategy:**

1. Keep the adversarial fixture corpus (stale/empty/swapped DB, engine crash/timeout/missing/incompatible-version, unparseable-but-nonempty manifest, injection attempt, wildcard waiver) asserting **0 fixtures exit-0**.
2. Gate every PR touching `extract/`, `engines.py`, `verdict.py`, or `feeds.py` on this suite explicitly (confirm it runs in the default `pyforge-warden-test` task, not only `-m slow`).
3. Extend the corpus whenever a new false-green vector is discovered, retro-driven.

**Owner:** Warden maintainer + CI/Platform
**Timeline:** Before next release touching a false-green-triad module
**Status:** In Progress (suite exists; explicit PR-gating on the triad-touching diff not independently confirmed this pass)
**Verification:** CI log showing the adversarial suite executed and green on a PR touching a triad module

#### R-002: Corpus-oracle / differential-oracle CI gap (Score: 6) - HIGH

**Mitigation Strategy:**

1. Add a scheduled (nightly/weekly) workflow invoking `pixi run -e pyforge-warden pyforge-warden-test-corpus-oracle`.
2. Restore the 4 precision differential-oracle tests (stories 2.2/2.3) to a gate that actually executes, even off the PR path.
3. Alert on failure distinctly from the default suite so a regression surfaces within one cadence cycle.

**Owner:** Platform/CI (Marshal station)
**Timeline:** Before the next `extract/*`-touching story
**Status:** Planned (open in `deferred-work-ledger.md` since Story 5.2)
**Verification:** a workflow/scheduler entry referencing the corpus-oracle task, with at least one recorded green run

#### R-003: Baseline simultaneous-expiry cliff (Score: 6) - HIGH

**Mitigation Strategy:**

1. Stagger the 19 `.warden-baseline.yaml` expiry dates ahead of 2027-07-24, or re-stamp on a rolling schedule.
2. Keep the regeneration command (`scripts/dogfood_scan.py --emit-baseline`) documented in the baseline file's own header (already done).
3. Add an early-warning check ("N entries expire within 90 days") to `scan --doctor`.

**Owner:** Warden maintainer
**Timeline:** Well before 2027-07-24
**Status:** Planned (open in `deferred-work-ledger.md`)
**Verification:** staggered `expires_at` values in `.warden-baseline.yaml`, or a dated tracking issue

#### R-004: Offline-DB staleness/poisoning (Score: 6) - HIGH

**Mitigation Strategy:**

1. Keep the DB content pre-flight (advisory-count ≥1, case-sensitive `PyPI` dir-segment check) as a named, independently-tested invariant — not folded silently into a broader loader refactor.
2. Confirm `snapshot_at=None` → `indeterminate` is asserted explicitly in the adversarial suite.
3. Revisit `--db-max-age` (default 7d) calibration against real staleness incidents when data exists.

**Owner:** Warden maintainer
**Timeline:** Ongoing regression-test audit
**Status:** In Progress (mechanism shipped per architecture; explicit named-test audit not independently confirmed this pass)
**Verification:** a named test asserting empty/corrupt-zip `all.zip` → non-clean status

#### R-005: E1 extractor regression undetected (Score: 6) - HIGH

**Mitigation Strategy:**

1. Depends on R-002 — the differential-oracle *is* the detection mechanism; unwired, this risk is unmonitored.
2. Keep the supported-construct matrix (compiler()/pin_subpackage()/selectors/for-loops) current as new recipe constructs appear in the corpus.
3. Version-control the ratcheted `unparseable_rate` baseline number explicitly so a regression is a visible diff.

**Owner:** Warden maintainer
**Timeline:** Tied to R-002's CI-wiring timeline
**Status:** Planned
**Verification:** `unparseable_rate` baseline diff reviewed on every extractor-touching PR; corpus-oracle CI green

---

### Assumptions and Dependencies

#### Assumptions

1. The waiver/baseline integrity boundary is git + CODEOWNERS (architecture's own "Resolved v1 assumptions") — the tool never authenticates authorship at runtime.
2. Coverage-floor gating (`--fail-under-coverage`) defaults OFF in v1; this test design does not treat coverage-floor enforcement as a P0 gate.
3. This is a retrospective/hardening test design over an already-shipped 43-story system (`sprint-status-ledger.yaml`, 2026-09-06) — "blockers" are CI/process gaps, not pre-implementation dependencies.

#### Dependencies

1. CI/scheduler wiring for the corpus-oracle + differential-oracle suites (R-002) - required before the next extractor change ships with confidence.
2. A baseline-expiry staggering decision (R-003) - required well before 2027-07-24.

#### Risks to Plan

- **Risk**: This test design targets a mature, already-shipped system rather than a pre-implementation architecture.
  - **Impact**: the "pre-implementation critical path" framing above is repurposed as "before the next touch of an affected module."
  - **Contingency**: treat blockers as backlog items already tracked in `deferred-work-ledger.md` (DW-5-2-5/6/7) rather than new blocking gates.

---

**End of Architecture Document**

**Next Steps for Architecture Team:**

1. Review Quick Guide (🚨/⚠️/📋) and prioritize the 3 blockers.
2. Assign owners and timelines for the 5 high-priority risks (≥6).
3. Validate assumptions and dependencies.

**Next Steps for QA Team:**

1. Refer to the companion QA doc (`test-design-qa.md`) for the test-scenario coverage plan.
2. Confirm the adversarial and corpus-oracle suites are wired into CI per R-001/R-002 before the next false-green-triad-touching change.
