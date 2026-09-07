---
workflowStatus: 'completed'
totalSteps: 5
stepsCompleted: ['step-01-detect-mode', 'step-02-load-context', 'step-03-risk-and-testability', 'step-04-coverage-plan', 'step-05-generate-output']
lastStep: 'step-05-generate-output'
nextStep: ''
lastSaved: '2026-09-07'
workflowType: 'testarch-test-design'
inputDocuments:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/prds/prd-pyforge-doctor-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/test-design-architecture.md
---

# Test Design for QA: pyforge-doctor (Doctor)

**Purpose:** Test execution recipe for the fleet's QA/dev discipline. Defines what to
test, how, and what's needed from other teams — scoped to Epic 20, Doctor's only
undelivered surface (Epics 1–19, 108 stories, already ship their own tests).

**Date:** 2026-09-07
**Author:** rxm7706 (via `bmad-testarch-test-design` / TEA, autonomous run)
**Status:** Draft
**Project:** pyforge-doctor

**Related:** See `test-design-architecture.md` for the full risk register and
testability review this coverage plan is derived from.

---

## Executive Summary

**Scope:** P0–P3 test coverage for Epic 20's 5 stories (20.1–20.5) plus 3 carried-debt
regression items named in the architecture doc (R-2, R-3's smoke assertion, and one
low-cost boundary test). Epics 1–19's 108 stories are explicitly **not** re-tested here
— see "Not in Scope" below for why, and "Interworking & Regression" for what keeps them
covered.

**Risk Summary:**

- Total Risks: 9 (1 high-priority score ≥6, 6 medium, 2 low)
- Critical Categories: TECH (4 of 9) and OPS (2 of 9) dominate — consistent with Epic 20
  being detector/config-drift work, not a user-facing feature.

**Coverage Summary:**

- P0 tests: ~3 (structural non-import guards + fail-open proofs — the two properties
  Epic 20's own text names as join conditions for `detectors`/`detectors-ci`)
- P1 tests: ~5 (per-story fixture proofs named directly in `epics.md`'s Given/When/Then)
- P2 tests: ~3 (cross-station sequencing + carried-debt regression)
- P3 tests: ~2 (documented follow-ups, non-blocking)
- **Total**: ~13 tests (~0.5–1.5 weeks, 1 engineer, alongside Epic 20's own implementation
  — this is a small epic: Effort S/S/M/XS/XS per `epics.md`)

---

## Not in Scope

**Components or systems explicitly excluded from this test plan:**

| Item | Reasoning | Mitigation |
| --- | --- | --- |
| **Epics 1–19 (108 stories)** | Already `done`, already covered by 61 files under `tests/{unit,meta}/` in the shipped package; re-designing their test plan here would duplicate work with no new information | Existing suite runs on every commit via `pixi run -e pyforge-doctor pyforge-doctor-test`; regression obligations tracked in "Interworking & Regression" below |
| **Doctor's web portal (Epic 18, `django_doctor_portal`) and MCP service face** | Canopy-tier UI/service concerns are owned by steward's platform-host conventions (`src/platform/`), not doctor's own CLI verbs; already has its own boundary meta-test (`test_portal_fleet_pulse.py`) | Verified as a passing pre-existing meta-test; not re-scoped here |
| **A persistent load/throughput test suite (k6, etc.)** | Doctor is a single-operator internal CLI with a *latency ceiling* (NFR-4, ~5s), not a service under concurrent load — there is no "scale" NFR to load-test | The existing speed-budget benchmark (`test_check_speed_budget.py`) is the correct tool and is reused, not replaced |
| **Browser/UI regression (Playwright)** | Confirmed by stack detection: zero `page.goto`/`page.locator` anywhere in the package; PRD §UX Design Requirements states "N/A — non-interactive CLI" | N/A |

**Note:** Items listed here have been reviewed against the real package layout (pyproject.toml, `sources/` module list, test directory contents) — not assumed from the template's web-app defaults.

---

## Dependencies & Test Blockers

**CRITICAL:** QA cannot proceed on two of Epic 20's five stories without items from
other teams or an architecture decision.

### Architecture Dependencies (Pre-Implementation)

**Source:** See Architecture doc "Quick Guide" § Blockers for full rationale.

1. **R-4's conformance-test requirement (Story 20.2)** — Architecture/Dev
   - QA needs the render-HALT detector's merge-simulation logic finalized and its
     conformance test landed before writing the `warn`/`ok` fixture-pair test.
   - Blocks: without it, a QA-written fixture test could pass against a detector that
     is quietly wrong (the exact class of bug the 2026-09-06 live HALT session hit).
2. **R-9's schema-version decision (any Epic 20 story that emits a new finding shape)** — architecture
   - QA needs to know whether `schema_version` stays `1` (additive) or bumps, before
     writing the consumer-compat assertion (P1-005 below).
   - Blocks: a `schema_version` bump without a QA-written round-trip check risks
     silently breaking Marshal's existing JSON parse of Doctor's output.

### Cross-Station Dependency (Pre-Implementation, Story 20.4 only)

1. **Steward Story 46.2** (SKF skill install providing `bmad-os-root-cause-analysis`) — currently `blocked` in the shared ledger.
   - QA needs steward 46.2's actual landed `SKILL.md` path/shape before writing the
     routing-line meta-test's real assertion (P2-001 below) — do not pre-author against
     an assumed shape (R-8).

### QA Infrastructure Setup (Pre-Implementation)

1. **Test fixtures** — all three Epic 20 fixtures are already named concretely in
   `epics.md`'s own Given/When/Then clauses (the 2026-08-21 `bmad-loop 0.9.0` lag; a
   planted `[core] user_skill_level` collision; a planted frozen-path edit) — no new
   fixture design is required, only construction.
2. **Test Environments** — no new environment needed. `pixi run -e pyforge-doctor
   pyforge-doctor-test` (local + landing protocol) is the existing, sufficient harness;
   network-touching sources are tested via mocked failure/success, never live network
   calls in the automated suite (mirrors the existing convention for Stories
   10.2/14.1/15.1/15.2/16.1/19.1 — none of their tests hit the real GitHub/npm/anaconda
   APIs).

**Example fixture pattern (this repo's real convention, not Playwright's):**

```python
# tests/unit/test_sources_bmad_config.py  (illustrative — Story 20.2)
from pyforge.doctor.sources.bmad_config import check_render_config_collision

def test_reports_ok_on_todays_single_path_pins(tmp_bmad_config_tree):
    """Today's tree has communication_language/user_skill_level pinned at one
    path each — no collision, detector reports ok."""
    finding = check_render_config_collision(tmp_bmad_config_tree)
    assert finding.status == "ok"

def test_reports_warn_on_planted_two_path_collision(tmp_bmad_config_tree):
    """Given [core] user_skill_level planted beside [modules.bmm]
    user_skill_level (the exact 2026-09-06 live shape) -> warn, naming both paths."""
    tmp_bmad_config_tree.plant_collision("user_skill_level", ["core", "modules.bmm"])
    finding = check_render_config_collision(tmp_bmad_config_tree)
    assert finding.status == "warn"
    assert "user_skill_level" in finding.message
    assert "core" in finding.evidence["paths"] and "modules.bmm" in finding.evidence["paths"]
```

---

## Risk Assessment

**Note:** Full risk details in the Architecture doc. This section maps risks to QA
test coverage.

### High-Priority Risks (Score ≥6)

| Risk ID | Category | Description | Score | QA Test Coverage |
| --- | --- | --- | --- | --- |
| **R-4** | TECH | Render-HALT detector may drift from the real config resolver it simulates | **6** | P0-001 (conformance test) + P1-002 (fixture pair) |

### Medium/Low-Priority Risks

| Risk ID | Category | Description | Score | QA Test Coverage |
| --- | --- | --- | --- | --- |
| R-1 | TECH | AD-13 conformance test cannot run in CI | 4 | Not new coverage — already-accepted, monitored at each `bmad-loop` bump (no QA action this pass) |
| R-2 | TECH | Duplicated AST alias-resolution helper across 3 meta-tests | 4 | P2-003 (refactor regression: 3 existing meta-tests still pass unchanged) |
| R-3 | TECH | Atlas label/JSON-shape coupling by convention only | 4 | P3-001 (smoke assertion, follow-up) |
| R-5 | OPS/PERF | Epic 20's 3 new sources threaten the 5s check budget | 4 | P0-002 (re-profile existing benchmark) |
| R-6 | OPS | Fail-open must distinguish absent vs. malformed ledger | 4 | P0-003 + P1-003 |
| R-9 | DATA | Schema-version bump policy open while 3 new shapes ship | 4 | P1-005 (consumer round-trip) |
| R-7 | SEC | Credential-hygiene generalization residual (already shipped) | 2 | No new coverage this pass — monitor only |
| R-8 | BUS | Story 20.4 blocked on steward 46.2 | 2 | P2-001 (deferred until unblocked) |

---

## NFR Test Coverage Plan

**Purpose:** Map NFR requirements to planned validation work for Epic 20 — this section
defines evidence QA creates; it does not assign final PASS/CONCERNS/FAIL (that's
`nfr-assess`, after Epic 20 ships).

| NFR Category | Requirement / Threshold | Planned Validation | Tool / Level | Evidence Artifact | Priority |
| --- | --- | --- | --- | --- | --- |
| Charter §6 non-self-judgment | Stories 20.2/20.3's new sources import nothing from the subsystem they judge | AST-based static assertion, mirroring `test_no_warden_import.py`/`test_source_independence.py` | Unit/meta | `tests/meta/test_sources_bmad_config_no_render_skill_import.py`, `tests/meta/test_sources_foundry_ledger_independence.py` (new) | P0 |
| Pre-flight speed budget (NFR-4) | `doctor check` stays within its existing budget after Epic 20 | Re-run existing benchmark with Epic 20's sources wired in | Unit (pytest-benchmark style, mirrors `test_check_speed_budget.py`) | Updated benchmark result in the same test file | P0 |
| Fail-open network/config-read discipline | Every Epic 20 source degrades to no-Finding/`ok` on unreachable/absent input, never raises | Fixture-based unit tests per source (mocked failure injection) | Unit | New test cases in `tests/unit/test_sources_bmad_method.py` (extended) and new source test files | P0 |
| Schema-versioned machine contract (NFR-5 / R-9) | New finding shapes stay additive under `schema_version=1`, or a bump ships with a compat test | Round-trip an old-shape and a new-shape `DoctorReport` through the same JSON-Schema validator | Unit | `tests/unit/test_models.py` (extended) or a new schema round-trip test | P1 |

**Missing thresholds or evidence sources:** None — R-9 is a decision, not a missing
threshold; once decided, the validation above is fully specified.

---

## Entry Criteria

**QA testing on Epic 20 cannot begin until:**

- [x] PRD + Architecture Spine are `final`/reviewed (already true — Epics 1–19 shipped
      against them)
- [ ] R-4's conformance-test approach agreed (blocks Story 20.2 fixture work)
- [ ] R-9's schema-version policy decided (blocks any new-shape consumer-compat test)
- [ ] R-6's absent-vs-malformed-ledger distinction agreed (blocks Story 20.3 fixture work)
- [x] Test environment ready — no new environment needed, existing `pixi run -e
      pyforge-doctor pyforge-doctor-test` harness is sufficient
- [x] Fixtures identified — all three Epic 20 fixtures are already named in `epics.md`'s
      own Given/When/Then text (2026-08-21 lag; planted config collision; planted
      frozen-path edit)

## Exit Criteria

**Epic 20's testing phase is complete when:**

- [ ] All P0 tests passing (structural non-import guards + fail-open proofs)
- [ ] All P1 tests passing or explicitly triaged (per-story fixture proofs)
- [ ] No new source joins `detectors`/`detectors-ci` before its fail-open behavior is
      fixture-proven (Epic 20's own stated boundary — this is this repo's actual gate,
      not a generic "no open high-severity bugs" placeholder)
- [ ] `test_check_speed_budget.py` re-profiled and green after Epic 20's sources land
- [ ] Every Doctor finding Epic 20 introduces remains `warn`-at-most / advisory — no
      exit code widens into warden's policy-gate `1` (verified by extending
      `test_verdict_narrows_warden.py`'s coverage, not a new mechanism)

---

## Project Team (Optional)

Roles are not individually named in the PRD/architecture beyond "doctor dev" and
"architecture" (this is a single-operator internal tool with agent-driven
implementation via `marshal factory spin pyforge-doctor` or direct `bmad-build`/
`bmad-build-auto`, not a named human team) — omitted per template guidance rather than
invented.

---

## Test Coverage Plan

**IMPORTANT:** P0/P1/P2/P3 = priority and risk level, not execution timing. See
"Execution Strategy" below for when tests run.

### P0 (Critical)

**Criteria:** Blocks Epic 20's own stated join-condition for `detectors`/`detectors-ci`
+ high risk (≥6) + no workaround.

| Test ID | Requirement | Test Level | Risk Link | Notes |
| --- | --- | --- | --- | --- |
| **P0-001** | Story 20.2's render-HALT detector conformance test (simulation ≡ `render_skill.py`'s real merge, AD-13-style AST/behavior equality) | Unit/meta | R-4 | Must land before Story 20.2's feature code is considered done, not after |
| **P0-002** | `doctor check` speed budget re-profiled with Epic 20's 3 new sources wired in; minimum-findings-count assertion preserved | Unit (benchmark) | R-5 | Reuses `test_check_speed_budget.py`'s existing pattern |
| **P0-003** | Fail-open proof for all 3 new Epic 20 sources: unreachable/absent/malformed input → no Finding or `ok`, never an unhandled exception; absent-ledger and malformed-ledger cases tested separately (Story 20.3) | Unit | R-6 | This is the epic's own explicit join condition for `detectors`/`detectors-ci` |

**Total P0:** 3 tests

---

### P1 (High)

**Criteria:** Per-story fixture proofs named directly in `epics.md`'s own text; medium risk (3-5); no workaround yet but well-specified.

| Test ID | Requirement | Test Level | Risk Link | Notes |
| --- | --- | --- | --- | --- |
| **P1-001** | Story 20.1: 13/13 `packages_checked`, each naming its probe class (tag/commit-pinned/npm); 2026-08-21 `bmad-loop 0.9.0 vs 0.11.0` fixture fires `warn` | Unit | — | Fixture already named in `epics.md` |
| **P1-002** | Story 20.2: planted `[core] user_skill_level` beside `[modules.bmm] user_skill_level` fires `warn` naming both paths; today's tree reports `ok`; a missing config layer file is fail-open | Unit | R-4 | Depends on P0-001 landing first |
| **P1-003** | Story 20.3: planted frozen-path edit under a `rebuilding`/`moving` capability fails, naming the capability and path; an edit outside any frozen path passes; absent ledger is `ok` (pre-cutover) | Unit | R-6 | Distinguish from P0-003's malformed-ledger case explicitly |
| **P1-004** | Story 20.1: fail-open — an unreachable registry (GitHub/npm/anaconda) query yields no Finding, no error, `packages_checked` still accurate for the reachable subset | Unit | — | Mirrors Story 10.2's already-shipped precedent exactly |
| **P1-005** | Schema round-trip: an Epic-20-era `DoctorReport` (with the 3 new finding shapes) still validates against the committed JSON Schema at `schema_version=1`, and an existing consumer (Marshal's JSON parse path) round-trips it without error | Unit | R-9 | Blocked on the R-9 decision |

**Total P1:** 5 tests

---

### P2 (Medium)

**Criteria:** Secondary flows, low/medium risk, cross-station or refactor-adjacent.

| Test ID | Requirement | Test Level | Risk Link | Notes |
| --- | --- | --- | --- | --- |
| **P2-001** | Story 20.4: routing-line meta-test — `bmad-agent-doctor/SKILL.md` names `bmad-os-root-cause-analysis` "to find a cause, never to change a verdict"; register row present; AD-2/AD-11 meta-test passes; CLAUDE.md untouched | Unit/meta | R-8 | Deferred until steward 46.2 unblocks |
| **P2-002** | Story 20.5: `bmad-spec` re-derive leaves `dream-chain-check`/`spec-surface-check` green, `status: shipped` intact, § Open Questions empty | Doc/process check | — | Docs-only story (Effort XS) |
| **P2-003** | Carried-debt regression (R-2): after extracting the shared AST alias-resolution helper, the 3 existing meta-tests it replaces (`test_no_warden_import.py`, `test_sources_warden_no_subprocess.py`, `test_cli_bridge_sole_subprocess.py`) still pass unchanged | Unit/meta | R-2 | Opportunistic, alongside Epic 20's `sources/` work |

**Total P2:** 3 tests

---

### P3 (Low)

**Criteria:** Nice-to-have, documented follow-ups, non-blocking.

| Test ID | Requirement | Test Level | Notes |
| --- | --- | --- | --- |
| **P3-001** | Atlas label/JSON-shape smoke assertion (R-3) added for existing + Epic 20 gather filters | Unit | Follow-up, not blocking Epic 20 |
| **P3-002** | `_default_repo_root`'s `parents[8]` fallback gets an explicit boundary test | Unit | Cheap, opportunistic since Epic 20 touches adjacent `sources/` code |

**Total P3:** 2 tests

---

## Execution Strategy

**Philosophy:** This repo has no PR-gated CI pipeline the way a hosted web app does;
its actual tiers are local-first, pixi-driven, and read-side-conformance-driven.
Playwright/k6 tiering from the template does not apply — replaced with this repo's real
tiers below.

### Every commit: `pytest` via pixi (~seconds, this is a small package)

**All new Epic 20 unit + meta tests** (P0/P1/P2/P3 above):

- `pixi run -e pyforge-doctor pyforge-doctor-test` runs the full `tests/{unit,meta}`
  suite (61 existing files + ~13 new for Epic 20).
- No sharding needed at this scale.

**Why run every commit:** Fast feedback, matches how Epics 1–19 were verified.

### After fail-open is fixture-proven: `detectors` / `detectors-ci` membership

**Epic 20's new sources** (Story 20.2's render-HALT class, Story 20.3's
frozen-path-changed) join `pixi run -e local-recipes detectors` / `detectors-ci` only
once P0-003's fail-open proof is green — this is the epic's own explicit, stated
sequencing, not a generic staging convention.

**Why deferred:** A detector joining the fleet-wide gate before its fail-open path is
proven risks a false-fail taking down the ambient report for everyone, per this repo's
own documented incident history (unauthenticated GitHub probes failing open being a
recurring theme — R-1/R-5's class of concern).

### Ambient / landing-time: `platform-ci-local`, full workflow replay

- Not a new tier for Epic 20 — this already runs the whole `src/platform` suite; Epic
  20 adds no `src/platform` surface (Doctor's CLI chain, not the Canopy portal).

**Manual/out-of-automation:**

- Cross-station verification of steward 46.2's landed shape (Story 20.4, P2-001) —
  inherently manual since it depends on another station's own release timing.

---

## QA Effort Estimate

**QA test development effort only:**

| Priority | Count | Effort Range | Notes |
| --- | --- | --- | --- |
| P0 | 3 | ~1-2 days | Conformance test (P0-001) is the most involved — requires reading `render_skill.py` closely |
| P1 | 5 | ~2-3 days | All 5 fixtures are already named concretely in `epics.md`; construction, not design |
| P2 | 3 | ~1 day | P2-001 blocked on steward 46.2; P2-002/P2-003 are small |
| P3 | 2 | ~0.5 day | Both opportunistic, low cost |
| **Total** | **13** | **~0.5-1.5 weeks** | **Alongside Epic 20's own S/S/M/XS/XS-sized implementation, not a separate QA phase** |

**Assumptions:**

- Includes test design (already mostly done, in this document), implementation,
  debugging.
- Excludes ongoing maintenance of the existing 61-file suite (already maintained as
  part of each shipped story's own definition of done).
- No dedicated QA role exists on this project — implementation and test authorship are
  the same `doctor dev` actor (bmad-build/bmad-build-auto or a `marshal factory spin`
  dispatch), consistent with every prior epic's own pattern.

**Dependencies from other teams:**

- See "Dependencies & Test Blockers" — R-4/R-9/R-6 (architecture decisions) and R-8
  (steward 46.2).

---

## Tooling & Access

No non-standard tools or access requests are required — everything needed
(`pixi`, `pytest`, the existing `pyforge-doctor` pixi environment) is already
provisioned and in daily use by this station.

---

## Interworking & Regression

**Services and components impacted by Epic 20:**

| Service/Component | Impact | Regression Scope | Validation Steps |
| --- | --- | --- | --- |
| **`doctor.verdict` (exit-code module)** | Epic 20's new sources must not widen the exit-code domain | `test_verdict_narrows_warden.py`, `test_verdict_sole_ownership.py` must still pass unchanged | Run full meta suite; assert no new exit code value appears |
| **`fleet-picture` ATTENTION block** | Epic 20 stories 20.1/20.2/20.3 all surface on this ambient report | Existing `fleet-picture` rendering tests (outside this package) | Confirm the report still renders with 3 new finding classes present, doesn't crash on the new evidence shape |
| **Marshal's JSON parse of `DoctorReport`** | R-9's schema-version question directly affects this consumer | P1-005 above | Round-trip an Epic-20-era report through Marshal's actual parse path if accessible, or its documented schema contract otherwise |
| **`detectors` / `detectors-ci` pixi tasks** | Gain 2 new members (Story 20.2, 20.3) once fail-open proven | Existing detector suite membership list | Confirm existing 13+ dispatcher entries still resolve unchanged after the 2 additions |
| **Existing 61-file `tests/{unit,meta}` suite (Epics 1–19)** | Must remain green — Epic 20 touches shared modules (`sources/bmad_method.py`, possibly `models.py` for schema) | Full existing suite | `pixi run -e pyforge-doctor pyforge-doctor-test` — zero regressions permitted |

**Regression test strategy:**

- The existing 61-file suite is the regression backstop for Epics 1–19; Epic 20 adds
  to it, never replaces or skips it.
- No cross-team coordination is needed for regression validation beyond the two named
  dependencies (architecture decisions; steward 46.2) — this is a single-package,
  single-station change set.

---

## Appendix A: Real Code Conventions (not Playwright — this is a pytest/CLI project)

**Structural meta-test pattern** (mirrors the existing 14 meta-test files):

```python
# tests/meta/test_sources_bmad_config_no_render_skill_import.py  (illustrative — Story 20.2)
import ast
from pathlib import Path

SOURCE = Path("src/pyforge/doctor/sources/bmad_config.py")

def test_does_not_import_render_skill_module():
    """Charter §6: a detector judging render_skill.py's merge behavior must not
    import render_skill.py itself -- it re-simulates the merge, structurally
    independent, per AD-13's precedent (restate + conformance-test, never import)."""
    tree = ast.parse(SOURCE.read_text())
    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert "render_skill" not in imported_names
```

**Fail-open pattern** (mirrors Story 10.2's shipped convention):

```python
# tests/unit/test_sources_bmad_method.py  (extended for Story 20.1)
def test_unreachable_registry_yields_no_finding_not_exception(monkeypatch):
    monkeypatch.setattr(
        "pyforge.doctor.sources.bmad_method._fetch_github_release",
        lambda *_: (_ for _ in ()).throw(ConnectionError("unreachable")),
    )
    findings = gather_bmad_suite_drift()
    assert findings == []  # or: whatever findings ARE producible from the reachable subset
```

**Run the suite:**

```bash
pixi run -e pyforge-doctor pyforge-doctor-test
```

---

## Appendix B: Knowledge Base References

- **Risk Governance**: `risk-governance.md` — Risk scoring methodology
- **Test Priorities Matrix**: `test-priorities-matrix.md` — P0-P3 criteria
- **Test Levels Framework**: `test-levels-framework.md` — unit vs. integration selection (adapted: no E2E level applies to this backend CLI)
- **NFR Criteria**: `nfr-criteria.md` — adapted to backend/CLI NFR categories (Security/Reliability/Maintainability applied; Performance reframed as a latency-ceiling budget, not throughput SLO)
- **ADR Quality Readiness Checklist**: `adr-quality-readiness-checklist.md` — Testability & Automation and Security categories applied; Scalability/DR/Deployability/QoE categories N/A for a console-script CLI

---

## Validation Notes (against `checklist.md`)

- [x] Risk assessment matrix present, scored, categorized
- [x] NFR planning summary present with thresholds, gaps, planned evidence
- [x] Coverage matrix and priorities present (P0-P3)
- [x] Execution strategy present, adapted to this repo's real tooling (no fabricated
      Playwright/k6 tiers)
- [x] Resource estimates given as ranges, not false precision
- [x] Quality gate criteria present (Entry/Exit Criteria)
- [x] "Not in Scope" section names why Epics 1-19 are excluded, with mitigation
- [x] No CLI browser sessions were opened during this run (N/A — backend stack); no
      temp artifacts written outside `{test_artifacts}/`
- [x] No story-by-story ID matrix of all 113 stories was produced — coverage is
      organized by risk/P0-P3 tier over the actionable delta (Epic 20) plus named
      carried debts, per this workflow's own template shape (distinct from the
      mechanically-generated `test-architecture.md`'s per-story matrix)

**Generated by:** BMad TEA Agent (`bmad-testarch-test-design`, Create mode, System-Level)
**Workflow:** `bmad-testarch-test-design`
**Version:** 5.0 (Step-File Architecture)
