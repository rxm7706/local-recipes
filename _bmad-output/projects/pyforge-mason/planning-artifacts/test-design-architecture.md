---
workflowStatus: 'completed'
totalSteps: 5
stepsCompleted:
  - 'step-01-detect-mode'
  - 'step-02-load-context'
  - 'step-03-risk-and-testability'
  - 'step-04-coverage-plan'
  - 'step-05-generate-output'
lastStep: 'step-05-generate-output'
nextStep: ''
lastSaved: '2026-09-07'
workflowType: 'testarch-test-design'
inputDocuments:
  - "_bmad-output/projects/pyforge-mason/planning-artifacts/prds/prd-pyforge-mason-2026-07-25/prd.md"
  - "_bmad-output/projects/pyforge-mason/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md"
  - "_bmad-output/projects/pyforge-mason/planning-artifacts/epics.md"
  - "_bmad-output/projects/pyforge-mason/planning-artifacts/sprint-status-ledger.yaml"
  - "_bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md"
  - "src/shared/packages/pyforge-mason/tests/"
---

# Test Design for Architecture: pyforge-mason (Mason CLI)

**Purpose:** Architectural concerns, testability gaps, and NFR requirements for review by the
Mason maintainer(s). Serves as a contract on what must be addressed before the CFE-rebuild
guard's next slice (Epic 12/Story 12.8) or before `mason environment check` is adopted as a
blocking CI gate — see companion doc `test-design-qa.md` for the execution recipe.

**Date:** 2026-09-07
**Author:** Rxm7706 (via TEA `bmad-testarch-test-design`, system-level mode)
**Status:** Retrospective + forward review (station is largely `done`; see Scope)
**Project:** pyforge-mason
**PRD Reference:** `planning-artifacts/prds/prd-pyforge-mason-2026-07-25/prd.md`
**ADR Reference:** `planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md`

---

## Executive Summary

**Scope:** `mason` is a Python CLI that **wraps** `conda-forge-expert` by subprocess for all
recipe operations and **builds natively** for `package` (PyPI/conda/conda-forge shipping) and
`environment` (lockfile binding) — the seam is drawn by capability, not by product (D-1). Unlike
a typical Phase-3 test design run before implementation, **60 of 61 stories across 14 epics are
already `done`** (only `14-1`, a recipe-only relay through CFE with no `pyforge.mason` code path,
is `backlog`). This document is therefore a **testability audit of the shipped system plus a
forward risk register**, not a pre-implementation blocker list.

**Business Context:** the product exists to avoid the `pyforge-atlas` precedent — ~29,000 LOC
rebuilt to re-earn 41,410 LOC of conda-forge knowledge, with the 8,902-LOC original still the
live runtime. Mason's central bet (D-1) is that zero-knowledge-duplication plus meta-test
enforcement beats a fork.

**Architecture:** knowledge-free core (AD-1) enforced by named meta-tests, not documentation; the
CFE port is the sole CFE caller (AD-3); subprocess-only, typed, timed invocation (AD-4); no
persisted state — idempotence is achieved by interrogating the target, not a local cache (AD-10).
Stack: Python ≥3.12, argparse only (no CLI framework, FR-41), 50 test files under
`src/shared/packages/pyforge-mason/tests/` running against a fixture CFE root (AD-16).

**Risk Summary:** 12 risks identified — **4 high-priority (score ≥6)**, 4 medium, 4 low.
Hardening effort for the confirmed gaps is small (~1–2 weeks), since the underlying suite and
architecture already exist; this is closing gaps, not building coverage from zero.

---

## Quick Guide

### 🚨 Must Close Before the Next Irreversible Step

1. **R-004: The CFE-rebuild parallel-run guard has two soft spots** (clause (b)'s
   `brief_mirrored_through` check is pure string equality and never opens the brief; slice-1's
   `equivalence: green` has no forcing function to catch staleness against a newer CFE release) —
   close before Story 12.8's slice-3 go/adjust/stop decision. *(Owner: Dev/Architect)*
2. **R-003: `mason environment check --format json` can report `status: "ok"` while swallowing a
   real `conda-lock` subprocess failure** (DW-4-4-3) — close before any CI workflow adopts this
   command as a blocking gate. *(Owner: Dev)*

**What we need from the team:** confirm these two before treating the CFE-rebuild guard or
`environment check` as trustworthy automation surfaces.

---

### ⚠️ High Priority — Team Should Validate

1. **R-001/R-002 (seam guard + credential isolation):** these meta-tests
   (`test_no_recipe_knowledge.py`, `test_adapter_sole_caller.py`, `test_credential_isolation.py`)
   are the product's core safety net. Recommend treating any diff to them as review-blocking
   regardless of size. *(implementation phase: ongoing review policy)*
2. **R-007/R-008 (concurrent-ship race; unexpanded `~` in `--cfe-root`):** both are small, scoped
   fixes (DW-3-7-1, DW-3-6-2/3). Recommend batching into one hardening PR rather than deferring
   indefinitely. *(implementation phase: next hardening pass)*

**What we need from the team:** review the recommendations and approve, or propose changes.

---

### 📋 Info Only — Solutions Already in Place

1. **Test strategy:** unit + meta + integration via pytest against a fixture CFE root (AD-16); no
   browser/E2E layer exists or is needed — Mason has no UI or HTTP surface of its own (see QA doc
   § Not in Scope for the one portal exception).
2. **Tooling:** pytest, pixi tasks `pyforge-mason-test` (fast, `-m "not slow"`) and
   `pyforge-mason-test-slow` (the one real-CFE delegation-fidelity test, FR-46).
3. **Coverage:** ~12–15 recommended new/hardening scenarios on top of the existing 50-file suite,
   prioritized P0–P3 (see QA doc).
4. **Quality gates:** see QA doc § Exit Criteria.

**What we need from the team:** review and acknowledge.

---

## For Architects and Devs — Open Topics 👷

### Risk Assessment

**Total risks identified:** 12 (4 high-priority score ≥6, 4 medium, 4 low)

#### High-Priority Risks (Score ≥6) — IMMEDIATE ATTENTION

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner | Timeline |
|---|---|---|---|---|---|---|---|---|
| **R-001** | **TECH** | Seam erosion — recipe knowledge migrates into Mason over time, repeating the `pyforge-atlas` outcome (PRD R-1, R-9) | 2 | 3 | **6** | FR-42/43 meta-tests already land and pass; keep permanently in the P0 regression set | Dev | Ongoing |
| **R-002** | **SEC** | Credential leak through logs, receipts, or error output (PRD R-8) | 2 | 3 | **6** | AD-14 + `test_credential_isolation.py` cover the read/log paths; widen to every `--verbose`/`--quiet` level | Dev | Next hardening pass |
| **R-003** | **OPS/DATA** | `mason environment check --format json` reports `status: "ok"` with empty `errors[]` while `conda-lock`'s own subprocess failure and stderr are swallowed (DW-4-4-3) | 3 | 2 | **6** | Capture `conda-lock` stderr in `engines/condalock.py::check()`; surface non-`ok` status + populated `errors[]` on non-zero exit; add regression test | Dev | Before CI adopts this as a gate |
| **R-004** | **TECH** | CFE-rebuild guard clause (b) is pure string equality against tracked YAML and never opens the brief (DW-12-1-1); slice-1 `equivalence: green` has no staleness check against newer CFE releases (DW-12-1-2) — this guard is the sole automated defense against repeating R-001 during the in-flight parallel-run rebuild | 2 | 3 | **6** | Hash/re-parse the brief's actual content for clause (b); add a CFE-version staleness check before Story 12.8's slice-3 decision | Dev/Architect | Before slice-3 briefing |

#### Medium-Priority Risks (Score 3-5)

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner |
|---|---|---|---|---|---|---|---|
| R-005 | BUS | `conda-forge` ship target could report success for a PR a human later rejects (PRD R-4) | 2 | 2 | 4 | AD-9's `pending`-state discipline (FR-17) already makes this explicit; keep in P1 regression | Dev |
| R-006 | TECH | CFE stdout is a de-facto, not formal, contract; an upstream change could silently break an adapter parse (PRD R-2) | 2 | 2 | 4 | FR-46 delegation-fidelity test (`slow`) is the one real-CFE check; run it on a Nightly lane, not ad hoc | Dev |
| R-007 | DATA | Concurrent ship of the identical name+version races between the idempotence interrogation and the upload call, reporting the loser as `FAILED` not `TERMINAL` (DW-3-7-1) — undermines AD-10's own guarantee | 2 | 2 | 4 | Detect the target's "already exists" response post-hoc and reclassify as `terminal`; add a race-window regression test | Dev |
| R-008 | TECH | A `~`-prefixed `--cfe-root` is never expanded before reaching child-process argv, and `expanduser()`'s `RuntimeError` is not caught (DW-3-6-2, DW-3-6-3) | 2 | 2 | 4 | Expand user-paths once in `resolve_cfe_root`; widen the except clause; add regression test | Dev |

#### Low-Priority Risks (Score 1-2)

| Risk ID | Category | Description | Probability | Impact | Score | Action |
|---|---|---|---|---|---|---|
| R-009 | SEC | `cfe.validate_recipe()` and `engines.pixi.upload()` omit a `--` argv separator, so a path/channel name starting with `-` could be misparsed by the wrapped tool (DW-2-5-4, DW-3-5-1) | 1 | 2 | 2 | Add the separator at both call sites (low-cost fix) |
| R-010 | TECH | `pixi build` member-package semantics are preview software and shared workspace-wide (PRD R-5) | 1 | 2 | 2 | Monitor; any fix is workspace-wide, not Mason-specific |
| R-011 | TECH | A lean pixi env's `sys.executable` may not import CFE at all (PRD R-6) | 1 | 2 | 2 | D-7 explicit interpreter selection + FR-3 floor probe + FR-34 `doctor` already close this |
| R-012 | OPS | Epic 14 / Story `14-1` (`bmad-eval-quality` win-64 variant) is `backlog` — pure CFE-recipe work, no `pyforge.mason` code path | 1 | 1 | 1 | No Mason test-surface action needed; tracked for fleet completeness |

#### Risk Category Legend

- **TECH**: Technical/Architecture · **SEC**: Security · **PERF**: Performance · **DATA**: Data
  Integrity · **BUS**: Business Impact · **OPS**: Operations

---

### NFR Testability Requirements

| NFR Category | Threshold / Requirement | Current Design Support | Gap / Decision Needed | Planned Evidence |
|---|---|---|---|---|
| Security | No credential in logs/receipts/errors at any verbosity (NFR-2, NFR-6, NFR-16) | Supported (AD-14) | R-002 (widen verbosity coverage); R-009 (argv-separator gap) | `test_credential_isolation.py` + new argv-separator regression tests |
| Performance | Every CFE call bounded by a mandatory timeout; a hang must never hang Mason (NFR-1) | Supported (AD-4, `CfeTimeoutError`) | No numeric wall-clock SLO for `mason recipe/package build` — **UNKNOWN**, correctly inherited from the wrapped engine rather than owned by Mason | `test_engines*.py` timeout-path tests; no load tooling needed (local CLI, not a service) |
| Reliability | Deterministic JSON (NFR-3), single-document stream discipline (NFR-4), idempotent ship (NFR-8), dry-run-by-default (NFR-9) | Supported, with 2 confirmed gaps | R-003 (swallowed `environment check` failure); R-007 (race misreports FAILED vs TERMINAL) | `test_engines_condalock.py` + `test_package_ship.py` regression additions |
| Maintainability | Lean, justified dependency set (NFR-10); CLI/JSON-schema semver discipline (NFR-15) | Supported (meta-tests enforce dependency floors) | DW-4-1-1: ~12 `MasonError` subclasses hand-duplicate `__reduce__` pickle/deepcopy boilerplate | `test_errors.py` covers round-trip today; a shared mixin would reduce future-drift risk, not current correctness |

**Unknown thresholds:** no numeric build-time SLO exists for `mason recipe build`/`package build`
(reasonably deferred to the wrapped engine per AD-6's capability-tier split). Not converted to a
risk — it is a correct architectural non-decision, not a gap.

**Assessment boundary:** final PASS/CONCERNS/FAIL status belongs in `nfr-assess` after evidence exists.

---

### Testability Concerns and Architectural Gaps

**🚨 ACTIONABLE CONCERNS**

#### 1. Blockers to Fast, Trustworthy Feedback

| Concern | Impact | What Must Be Provided | Owner | Timeline |
|---|---|---|---|---|
| CFE-rebuild guard soft spots (R-004) | A silently-defeated guard would let seam erosion recur mid-rebuild with no red CI | Content-checked clause (b); a CFE-version staleness check | Dev/Architect | Before Story 12.8 slice-3 decision |
| `environment check`'s swallowed failure (R-003) | A CI consumer trusts a JSON "ok" that hides a real `conda-lock` failure | Captured stderr, non-`ok` status on failure | Dev | Before CI adoption as a gate |

#### 2. Architectural Improvements Worth Making

1. **Concurrent-ship idempotence (R-007).** AD-10 chose interrogation over local state
   deliberately (D-11) to avoid a stale second source of truth — the tradeoff is sound, but the
   interrogate-then-act window itself was never named as an accepted race in the ADR. Recommend
   documenting the window explicitly alongside D-11, or closing it per the mitigation above.
2. **Path-expansion consistency (R-008).** `resolve.py`'s pure-function contract (AD-5) is a
   strength — its untested edge is simply that `~` expansion happens nowhere in the resolution
   chain today.

**📊 Testability Assessment Summary**

**What Works Well**

- AD-16's fixture-CFE-root discipline means the entire suite runs deterministically offline, with
  the single explicitly `slow`-marked exception (FR-46/NFR-13) — a rare, valuable trait against
  the ADR checklist's "Isolation" and "Headless Interaction" criteria.
- The seam itself (AD-1/AD-2/AD-3) is enforced by meta-tests named for the invariant they check
  (`test_no_recipe_knowledge.py`, `test_adapter_sole_caller.py`, `test_dependency_direction.py`,
  `test_namespace_is_implicit.py`, `test_exit_code_ownership.py`) rather than asserted only in
  prose.
- AD-9's `ShipReceipt`/`ShipTargetResult` shape makes "pending vs. success" a type-level
  distinction a renderer cannot accidentally collapse.

**Accepted Trade-offs (No Action Required)**

- Scalability, Availability, and Disaster-Recovery ADR-checklist categories are architecturally
  **N/A**: Mason is a local, single-process CLI with no persisted state to back up (AD-10) and no
  multi-instance deployment story. Documented here so it is not mistaken for an unassessed gap.

---

### Risk Mitigation Plans (High-Priority Risks ≥6)

#### R-001: Seam erosion (Score: 6) — ONGOING DISCIPLINE

**Mitigation Strategy:**
1. Keep `test_no_recipe_knowledge.py` / `test_adapter_sole_caller.py` / `test_dependency_direction.py` in the always-run (non-`slow`) suite permanently.
2. Treat any diff touching them as review-blocking regardless of size.
3. Route any new conda-forge-specific need discovered mid-Mason-work to a CFE retrospective, never a local patch (AD-15).

**Owner:** Dev · **Timeline:** Ongoing · **Status:** Mitigated, regression-locked · **Verification:** these tests stay green in the default `pyforge-mason-test` task.

#### R-002: Credential leak (Score: 6) — MITIGATED, WIDEN COVERAGE

**Mitigation Strategy:**
1. Confirm `test_credential_isolation.py` covers every `--verbose`/default/`--quiet` level, not just default.
2. Confirm no `JFROG_*` read anywhere in `pyforge/mason/`.

**Owner:** Dev · **Timeline:** Next hardening pass · **Status:** Mitigated / recommend widening · **Verification:** planted-credential fixture asserts zero leakage across verbosity levels.

#### R-003: `environment check` swallows failure (Score: 6) — OPEN

**Mitigation Strategy:**
1. Capture `conda-lock`'s stderr in `engines/condalock.py::check()` instead of inheriting it.
2. Surface a non-`ok` status and populate `errors[]` on non-zero exit.
3. Add a regression test simulating a failing `conda-lock` subprocess.

**Owner:** Dev · **Timeline:** Before CI adopts this command as a gate · **Status:** Open · **Verification:** new test asserts `status != "ok"` and `errors` non-empty on a simulated failure.

#### R-004: CFE-rebuild guard soft spots (Score: 6) — OPEN

**Mitigation Strategy:**
1. Replace clause (b)'s string-equality check with one that opens and hashes/validates the brief's actual amendment content.
2. Add a clause comparing the CFE version recorded at `equivalence: green` time against CFE's current `CHANGELOG.md` head; flag staleness.
3. Land both before Story 12.8's slice-3 go/adjust/stop decision.

**Owner:** Dev/Architect · **Timeline:** Before slice-3 briefing · **Status:** Open · **Verification:** a fixture proves each clause red before the fix, green after (matching Story 6.2's own discipline).

---

### Assumptions and Dependencies

#### Assumptions

1. Mason remains a local, single-operator CLI in v1 — the Scalability/DR/HA ADR categories stay N/A until a service deployment is proposed.
2. The CFE-rebuild's own campaign-state.yaml remains the source of truth for slice sequencing; this document does not re-decide Epic 6/12's re-scope gate.
3. No numeric build-time SLO is owned by Mason (AD-6); this is treated as a correct non-decision, not an open NFR gap.

#### Dependencies

1. `conda-forge-expert`'s own Rule-2 retrospective loop — required before any CFE-side fix for R-006. No fixed date; triggered by the next CFE MINOR bump.
2. Story 12.8's slice-3 decision — blocked on R-004's closure per this document's recommendation.

#### Risks to Plan

- **Risk:** the CFE-rebuild's own timeline could outrun this document's recommended R-004 closure.
  - **Impact:** Slice 3 could brief against an unhardened guard.
  - **Contingency:** Story 12.5's ownership-decision precedent shows the campaign already accepts a recorded, dated human decision in place of an automated gate when needed — the same escape hatch applies here if R-004 is knowingly deferred.

---

**End of Architecture Document**

**Next Steps:**

1. Review Quick Guide (🚨/⚠️/📋) and confirm the two must-close items.
2. Assign owners/timelines for R-001–R-004 per the mitigation plans above.
3. Refer to `test-design-qa.md` for the concrete test scenarios and execution recipe.
