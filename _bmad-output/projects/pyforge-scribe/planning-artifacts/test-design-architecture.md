---
workflowStatus: 'completed'
totalSteps: 5
stepsCompleted: ['step-01-detect-mode', 'step-02-load-context', 'step-03-risk-and-testability', 'step-04-coverage-plan', 'step-05-generate-output']
lastStep: 'step-05-generate-output'
nextStep: ''
lastSaved: '2026-09-07'
workflowType: 'testarch-test-design'
inputDocuments:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/prds/prd-pyforge-scribe-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/prds/prd-pyforge-scribe-2026-07-25/addendum.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/architecture/architecture-pyforge-scribe-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/deferred-work-ledger.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/sprint-status-ledger.yaml
  - src/shared/packages/pyforge-scribe/ (pyproject.toml, src/pyforge/scribe/*.py, tests/)
---

# Test Design for Architecture: pyforge-scribe (Scribe)

**Purpose:** Architectural concerns, testability gaps, and NFR requirements for review by the Scribe/steward engineering owners. Serves as a contract between QA/test-architecture and engineering on what must be addressed as Scribe's remaining work (Epic 7) and deferred-work backlog are worked.

**Date:** 2026-09-07
**Author:** BMad Master Test Architect (bmad-testarch-test-design, unattended run)
**Status:** Architecture Review Pending
**Project:** pyforge-scribe
**PRD Reference:** `_bmad-output/projects/pyforge-scribe/planning-artifacts/prds/prd-pyforge-scribe-2026-07-25/prd.md` (+ `addendum.md`)
**ADR Reference:** `_bmad-output/projects/pyforge-scribe/planning-artifacts/architecture/architecture-pyforge-scribe-2026-07-25/ARCHITECTURE-SPINE.md` (AD-1..AD-9)

---

## Executive Summary

**Scope:** Scribe's shipped surface — `scribe capture` / `scribe capture --promote` / `scribe capture --transcripts` (Epics 1, 3), `scribe graph compile --nightly` (Epics 2, 3, 6), `scribe recall` (Epic 2), the `GraphStore` CAP-18 plugin contract with three drivers (Epic 4), and the SKF skill/persona/portal tier (Epic 5). 18 of 19 stories are `done`; Story 7.1 (Epic 7, three docs-skill routing) is `blocked` on a cross-station dependency (steward 46.2) and is out of this design's coverage scope.

**Business Context** (from PRD):

- **Problem:** team knowledge is scattered and lossy across per-machine auto-memory; Scribe is the checked-in, git-native, air-gapped capture → compile → recall loop that fixes it (PRD §1).
- **Revenue/Impact:** not revenue-bearing; the cost of failure is silent knowledge loss (duplicated work, e.g. the `d43899c1cb` incident) and a false "grounded" answer eroding trust in `scribe recall`.
- **GA Launch:** already shipped (Epics 1–6 `done`); this is a post-ship testability/risk review, not a pre-implementation gate.

**Architecture** (from ARCHITECTURE-SPINE.md):

- **Key Decision 1:** Event-sourced capture with a derived, rebuildable read-model (AD-1) — `compile.py` never accepts direct graph edits; the graph is 100% re-derivable from source records.
- **Key Decision 2:** `GraphStore` as a `typing.Protocol` port (AD-5), now fronting three plugins registered on the shared `pyforge.core.hooks` contract — `FlatFileGraphStore` (default), `PostgresGraphStore` (pgvector), `PlaneGraphStore` (CAP-19 DuckDB) — selected by owner/env, never imported directly by callers.
- **Key Decision 3:** Air-gap by construction (AD-6) — zero required network calls in the default configuration; recall's default path is deterministic lexical retrieval, with local, non-network embeddings as an additive semantic layer.

**Expected Scale** (from ARCHITECTURE-SPINE.md / deferred-work-ledger.md):

- Compile surfaces: `.claude/memory/`, `**/.memlog.md` (88 nodes observed), git history (capped at 100 commits), retros, CHANGELOGs, plus raw session transcripts (measured 27 files / 631MB on the owning machine — the only uncapped surface until Story 3.3 bounded it).

**Risk Summary:**

- **Total risks**: 9
- **High-priority (≥6)**: 4 risks requiring immediate mitigation
- **Test effort**: ~35–55 tests across the untested risk surfaces below (~1–2 weeks for 1 QA/dev-in-test-role)

---

## Quick Guide

### 🚨 BLOCKERS - Team Must Decide (Can't Proceed Without)

1. **R-001: `promote.py` has never received an adversarial review** — the sole write path outside `.claude/memory/` (AD-2); a defect here is the one class of bug that could violate the FR-7 write-boundary contract itself (recommended owner: Scribe maintainer / security reviewer).
2. **R-002: `recall.answer()`'s tie-break silently prefers the alphabetically-earlier (usually older) node** on equal token-overlap scores, with no `valid_from` consultation — this is the one path that can make `scribe recall` return a superseded claim as if current, directly touching AD-8's "never fabricates, always grounds correctly" premise (recommended owner: Scribe maintainer).
3. **R-003: no standing CI gate re-verifies AD-6's air-gap guarantee** as new surfaces (embeddings, PG/plane drivers, graphify/cocoindex extras) are added — the only existing offline-conformance test was written against Story 2.1's flat-file adapter (recommended owner: Scribe maintainer / CI owner).
4. **R-006: 87 of 88 memlog graph nodes are titled `---`** (the YAML frontmatter delimiter, because `_node_from_text_file` takes the first non-empty line as title) — recommend `compile.py` prefer a memlog's `topic:` field when present, quoting the ~17 memlogs whose `topic:` is not valid YAML today (implementation phase, Scribe maintainer).

**What we need from team:** Resolve or explicitly risk-accept these 4 items; none currently blocks shipped functionality, but all four are silent-failure modes with no detector.

---

### ⚠️ HIGH PRIORITY - Team Should Validate (We Provide Recommendation, You Approve)

1. **R-004: `.claude/memory/MEMORY.md`'s 200-line cap is convention-only** — recommend a lightweight line-count check (detector or meta-test), not new tooling infrastructure (implementation phase).
2. **R-005: no detector asserts `CLAUDE.md`'s `@.claude/memory/MEMORY.md` import still resolves** — recommend folding into the same check as R-004 (one detector closes both DW-1-2-1 and DW-1-2-4).

**What we need from team:** Review recommendations and approve (or suggest changes) — none require new architecture, all are contained, mechanical fixes.

---

### 📋 INFO ONLY - Solutions Provided (Review, No Decisions Needed)

1. **Test strategy**: pytest unit + `tests/meta/` conformance tests (existing pattern; no Playwright/UI surface — Scribe is a backend CLI/library, confirmed by stack detection: no `playwright.config.*`, no `package.json`, no browser indicators under `src/shared/packages/pyforge-scribe/`).
2. **Tooling**: pytest, `pixi run -e pyforge-scribe pyforge-scribe-test`; PG-backed tests provision schema from the governed Liquibase changesets (`tests/unit/conftest.py`), not ad hoc DDL.
3. **Execution tiers**: PR (all unit/meta tests, <5 min observed), no nightly/weekly tier needed today — see QA doc.
4. **Coverage**: ~35–55 test scenarios prioritized P0–P3 (see companion QA doc).
5. **Quality gates**: P0 100%, P1 ≥95%, existing repo-wide coverage gate (`coverage-gates.yml`) already enforces unit/integration thresholds package-wide.

**What we need from team:** Just review and acknowledge.

---

## For Architects and Devs - Open Topics 👷

### Risk Assessment

**Total risks identified**: 9 (4 high-priority score ≥6, 3 medium, 2 low)

#### High-Priority Risks (Score ≥6) - IMMEDIATE ATTENTION

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner | Timeline |
|---|---|---|---|---|---|---|---|---|
| **R-001** | **DATA** | `promote.py` (sole write path outside `.claude/memory/`, AD-2) has never had an adversarial review; open since the Story 1.3 dangling-commit recovery | 3 | 3 | **9** | Dedicated adversarial-review pass (fuzzed frontmatter, path-traversal attempts in captured `--type`/`--text`, concurrent-invocation races) before the next Epic-7-class change touches `promote.py` | Scribe maintainer | Next promote.py touch |
| **R-002** | **DATA** | `recall.answer()` tie-breaks on ascending node id, never `valid_from`; for date-ordered transcript filenames this usually resolves to the OLDER, since-superseded statement (DW-FU-3-2-4) | 2 | 3 | **6** | Add a recency-aware tie-break (prefer `valid_from` descending, or exclude nodes a live `supersedes:` edge points at) as a scoped `recall.py` change | Scribe maintainer | Before transcript-sourced recall queries are trusted for "why did we..." answers |
| **R-003** | **TECH** | AD-6's air-gap guarantee has one offline-conformance test (Story 2.1, flat-file adapter only); no standing check covers `embeddings.py`, the PG/plane drivers, or the graphify/cocoindex extras added since | 2 | 3 | **6** | Extend the offline-conformance test to run against the full default-config compile+recall path, or add a lint rule forbidding new `socket`/`requests`/`httpx` imports outside the PG/plane driver modules | Scribe maintainer / CI owner | Next NFR/air-gap review |
| **R-006** | **TECH** | 87/88 memlog graph nodes are titled `---` (`compile.py::_node_from_text_file` takes the frontmatter delimiter as title); the graph's primary human-readable field is unusable for browsing (DW-2-1-3) | 3 | 2 | **6** | Prefer a memlog's `topic:` field over the first line; quote the ~17 memlogs whose `topic:` is not valid YAML in the same change | Scribe maintainer | Next compile.py touch |

#### Medium-Priority Risks (Score 3-5)

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner |
|---|---|---|---|---|---|---|---|
| R-004 | OPS | `.claude/memory/MEMORY.md`'s 200-line cap (Claude Code truncation point) is enforced by convention only, no CI check (DW-1-2-1) | 2 | 2 | 4 | One-line-count detector or meta-test | Scribe maintainer |
| R-005 | OPS | No detector asserts the `CLAUDE.md` `@.claude/memory/MEMORY.md` import still exists/resolves; a rename or deletion silently severs team memory (DW-1-2-4) | 2 | 2 | 4 | Fold into the R-004 detector (same fix closes both) | Scribe maintainer |
| R-007 | OPS | In bmad-loop worktree sessions, team memory loads twice from two divergent physical `MEMORY.md` files (loop-home `main` vs. worktree story branch) (DW-1-2-2) | 3 | 1 | 3 | Accept as an inherent bmad-loop-home cost, or gate the import on being inside a loop worktree (bmad-loop-level fix, outside Scribe's own boundary) | bmad-loop maintainers |

#### Low-Priority Risks (Score 1-2)

| Risk ID | Category | Description | Probability | Impact | Score | Action |
|---|---|---|---|---|---|---|
| R-008 | DATA | A transcript node's citation/id derives from basename only, not a path relative to `transcript_root`; two same-named files in different subdirectories would collide (DW-FU-3-2) — currently unreachable since `scan_transcripts()` globs one flat directory | 1 | 2 | 2 | Monitor; only a defect if the scanner is later made recursive |
| R-009 | OPS | `pyforge-scribe/spec-pyforge-scribe` spec-surface baseline is stale for 12 files with no Epic-3 provenance entry (DW-FU-3-2-3) — governance/traceability gap, not a functional defect | 1 | 1 | 1 | Monitor; scoped `--write-baseline --spec` reconcile at next spec touch |

#### Risk Category Legend

- **TECH**: Technical/Architecture (flaws, integration, scalability)
- **SEC**: Security (access controls, auth, data exposure)
- **PERF**: Performance (SLA violations, degradation, resource limits)
- **DATA**: Data Integrity (loss, corruption, inconsistency)
- **BUS**: Business Impact (UX harm, logic errors, revenue)
- **OPS**: Operations (deployment, config, monitoring)

*(No SEC or PERF risks scored: Scribe has no auth surface of its own — the portal's `PortalClient`-only rule is enforced by `tests/meta/test_first_portal_slice.py` — and Story 3.3 already closed the one measured performance risk, the unbounded transcript scan, with a file/byte cap and mtime cache (2.2s cold / 0.3s cached at close).)*

---

### NFR Testability Requirements

**Purpose:** Capture what Scribe's design must provide so NFR validation can be automated later. This is planning guidance, not final evidence assessment.

| NFR Category | Threshold / Requirement | Current Design Support | Gap / Decision Needed | Planned Evidence |
|---|---|---|---|---|
| Data integrity (air-gap, AD-6) | Zero required network calls in default config (PRD SM-5) | Supported for the flat-file default path (Story 2.1 offline-conformance test) | R-003: no standing check covers newer surfaces (embeddings, PG/plane, extras) | Extended offline-conformance test or import-lint rule |
| Data integrity (grounding, AD-8) | Every `scribe recall` response either cites a real record or returns "no grounded answer found" | Supported — `_citation_is_resolvable()` gate exists | R-002: tie-break can surface a superseded record as if current | Unit test asserting recency-correct tie-break once fixed |
| Reliability (unattended compile, FR-11) | Idempotent, unattended nightly compile | Supported — file cap, byte budget, per-file timeout, mtime scan cache (Story 3.3) | None open | `test_transcripts.py` / `test_compile.py` idempotency assertions (already present per baseline inventory) |
| Maintainability (graph readability) | Compiled nodes are human-navigable | Partial — citation paths resolve correctly but titles are broken for memlog nodes | R-006 | A `test_compile.py` assertion that `title != "---"` for any memlog-sourced node |

**Unknown thresholds:** none — Scribe's NFR contract (PRD §4, AD-6/AD-8) states testable pass/fail conditions directly; no numeric SLO (latency/throughput) is declared, consistent with a local, non-networked CLI.

**Assessment boundary:** Final PASS/CONCERNS/FAIL status belongs in `nfr-assess` after implementation evidence exists.

---

### Testability Concerns and Architectural Gaps

**🚨 ACTIONABLE CONCERNS - Architecture Team Must Address**

#### 1. Blockers to Fast Feedback (WHAT WE NEED FROM ARCHITECTURE)

| Concern | Impact | What Architecture Must Provide | Owner | Timeline |
|---|---|---|---|---|
| **No standing air-gap regression test** | A future surface (a fourth `GraphStore` driver, a new extra) could silently add a default network call and nothing would fail | A parametrized offline-conformance test that runs the full default-config `capture → compile → recall` path under a network-blocked harness, not just the Story 2.1 adapter | Scribe maintainer | Before the next `GraphStore` driver or extra ships |
| **No recency signal in `recall`'s tie-break** | Tests asserting "the current answer wins" for genuinely superseded facts cannot be written until the tie-break itself is fixed | Either a `valid_from`-descending tie-break or an explicit "exclude nodes with a live `supersedes:` edge pointing at them" rule in `recall.py` | Scribe maintainer | Before transcript-sourced supersession is test-covered |

#### 2. Architectural Improvements Needed (WHAT SHOULD BE CHANGED)

1. **Memlog node titling**
   - **Current problem**: `_node_from_text_file` takes the first non-empty line as title; for `.memlog.md` files that is the YAML frontmatter delimiter `---`.
   - **Required change**: Prefer the `topic:` frontmatter field when present (and fix the ~17 memlogs whose `topic:` needs quoting in the same change).
   - **Impact if not fixed**: The compiled graph's primary human-readable field stays unusable for 87/88 memlog nodes.
   - **Owner**: Scribe maintainer.
   - **Timeline**: Next `compile.py` touch.

---

### Testability Assessment Summary

**📊 CURRENT STATE - FYI**

#### What Works Well

- ✅ The `GraphStore` port is a `typing.Protocol` (structural typing) with three drivers selected by owner/env (`PYFORGE_GRAPHSTORE_OWNER`, `SCRIBE_GRAPH_DSN`, `QUERY_PLANE_DUCKDB`) — tests can swap backends without touching `compile.py`/`recall.py` call sites (AD-5 holding as designed).
- ✅ Business logic (`classify_and_draft`, `apply_promotion`) is decoupled from the CLI's `typer.confirm()` interactive prompt — tests call the functions directly rather than needing to script stdin, a controllability win.
- ✅ The transcript surface's cost bound (Story 3.3: 256-file cap, 1 GiB budget, 30s per-file timeout, mtime+size scan cache) is itself independently testable and was verified terminating on the live 27-file/631MB surface (2.2s cold / 0.3s cached).
- ✅ The PG driver's test schema is provisioned from the governed Liquibase changesets (`tests/unit/conftest.py`), not ad hoc DDL — the test database matches production DDL by construction.
- ✅ `tests/meta/` conformance tests (`test_first_portal_slice.py`, `test_skf_skill_ownership.py`, `test_station_persona.py`) already enforce the AD-7 consumer-boundary and five-tier-symmetry rules structurally, not by convention.

#### Accepted Trade-offs (No Action Required)

- **Manual-only invocation (no `Stop`/`SessionEnd`/`PreCompact` hooks)** — a deliberate, permanent product stance (PRD §5 Non-Goals), not a testability gap.
- **The bmad-loop double-load of `MEMORY.md` (R-007)** — an inherent cost of the loop-home layout, not fixable inside Scribe's own write boundary; acceptable as documented.

This is technical debt (R-001, R-002, R-003, R-006) that should be addressed opportunistically at the next touch of the affected module, not a signal to open a dedicated remediation epic.

---

### Risk Mitigation Plans (High-Priority Risks ≥6)

#### R-001: `promote.py` has never received an adversarial review (Score: 9) - CRITICAL

**Mitigation Strategy:**

1. Run a dedicated adversarial review pass against `promote.py`: fuzzed/malformed frontmatter in source user-local entries, path-traversal attempts via a crafted `--type`, concurrent `--promote` invocations racing on the same `MEMORY.md`.
2. Add regression tests for every finding directly to `tests/unit/test_promote.py`.
3. Re-verify the FR-7/AD-2 write-boundary invariant holds under the fuzzed inputs (nothing outside `.claude/memory/` and the one pointer-stub exception is ever written).

**Owner:** Scribe maintainer
**Timeline:** Before the next feature touches `promote.py`
**Status:** Planned
**Verification:** New `test_promote.py` cases covering each finding, all green; no write observed outside the FR-7 boundary under fuzzing.

#### R-002: `recall.answer()`'s tie-break can serve a superseded fact as current (Score: 6) - HIGH

**Mitigation Strategy:**

1. Change the tie-break in `recall.py::answer()` from `(-score, node.id)` to consult `valid_from` (descending) or exclude nodes with a live `supersedes:` edge pointing at them.
2. Add a unit test with two equal-overlap nodes where the older one is superseded, asserting the newer/current one is returned.

**Owner:** Scribe maintainer
**Timeline:** Before transcript-sourced supersession is relied on for real "why did we..." queries
**Status:** Planned
**Verification:** New `test_recall.py` case for the tie-break; existing supersession tests (`test_supersession.py`) still pass unchanged.

#### R-003: No standing air-gap regression test beyond Story 2.1 (Score: 6) - HIGH

**Mitigation Strategy:**

1. Parametrize the existing offline-conformance pattern (network-blocked harness) to run the full `capture → compile → recall` default-config path, not only the flat-file adapter in isolation.
2. Add an import-lint check (or a `tests/meta/` conformance test) forbidding new network-client imports (`socket`, `requests`, `httpx`, `urllib.request`) outside `graph_store_pg.py`/`graph_store_plane.py` (the two drivers whose DSN/env-gated activation is the documented exception).

**Owner:** Scribe maintainer / CI owner
**Timeline:** Before the next `GraphStore` driver or `compile_surface` extra ships
**Status:** Planned
**Verification:** The extended offline test and the import-lint check both run in the existing `pyforge-scribe-test` pixi task.

#### R-006: 87/88 memlog graph nodes titled `---` (Score: 6) - HIGH

**Mitigation Strategy:**

1. In `compile.py::_node_from_text_file`, prefer a memlog's `topic:` frontmatter field over the first non-frontmatter line when present.
2. In the same change, quote the ~17 memlogs whose `topic:` value is not valid YAML today (an unquoted `:`), since the fix would otherwise fail on them.
3. Add a `test_compile.py` regression asserting no memlog-sourced node is titled `---`.

**Owner:** Scribe maintainer
**Timeline:** Next `compile.py` touch
**Status:** Planned
**Verification:** `test_compile.py` regression test green against a fixture memlog set including at least one unquoted-`topic:` case.

---

### Assumptions and Dependencies

#### Assumptions

1. Story 7.1 (Epic 7, `blocked` on steward 46.2) is out of this design's coverage scope; it introduces no new testable code path (routing lines + a register row), only cross-station sequencing.
2. Scribe has no HTTP/API surface of its own to test — the portal integration point is `PortalClient`-only and already conformance-tested (`tests/meta/test_first_portal_slice.py`); this design does not duplicate that coverage.
3. `pydantic`/`typer`/`gitpython` version floors are as pinned in the shipped `pyproject.toml`; no re-verification against upstream was performed here (out of scope for a test-design review).

#### Dependencies

1. **CAP-14 durable PG/pgvector driver and semantic recall** — owned by steward Epic 28, not Scribe; this design treats `graph_store_pg.py` as already-shipped and in scope for R-003's air-gap check only insofar as it must stay opt-in.
2. **Epic 7's cross-station unblock** — steward Story 46.2 — required before Story 7.1's routing lines can land; not required for this test design.

#### Risks to Plan

- **Risk**: The four high-priority findings above (R-001..R-003, R-006) are all pre-existing, unaddressed carried debt (per `deferred-work-ledger.md`, most open since 2026-08-23/26) rather than newly discovered defects — there is no guarantee they get prioritized ahead of new feature work.
  - **Impact**: Test coverage for these paths (adversarial `promote.py` inputs, tie-break correctness, air-gap regression, memlog titling) stays absent until the underlying fix lands.
  - **Contingency**: Track via the existing tracked `deferred-work-ledger.md` (already carries DW-FU-3-2-4, DW-2-1-3, DW-1-2-1, DW-1-2-4) rather than opening a duplicate tracking surface.

---

**End of Architecture Document**

**Next Steps for Architecture Team:**

1. Review Quick Guide (🚨/⚠️/📋) and prioritize the 3 blockers.
2. Assign owners and timelines for the 4 high-priority risks (≥6) — all currently default to "Scribe maintainer."
3. Validate assumptions and dependencies above.
4. Provide feedback on testability gaps (R-001..R-003, R-006).

**Next Steps for QA Team:**

1. Refer to the companion QA doc (`test-design-qa.md`) for the P0–P3 test scenario breakdown.
2. Begin with R-001/R-002/R-006 regression-test scaffolding once the corresponding fixes land (tests can be written test-first against the mitigation plans above).
