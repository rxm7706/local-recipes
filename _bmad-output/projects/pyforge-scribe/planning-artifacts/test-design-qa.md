---
workflowStatus: 'completed'
totalSteps: 5
stepsCompleted: ['step-01-detect-mode', 'step-02-load-context', 'step-03-risk-and-testability', 'step-04-coverage-plan', 'step-05-generate-output']
lastStep: 'step-05-generate-output'
nextStep: ''
lastSaved: '2026-09-07'
workflowType: 'testarch-test-design'
inputDocuments:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/test-design-architecture.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/deferred-work-ledger.md
  - src/shared/packages/pyforge-scribe/tests/
---

# Test Design for QA: pyforge-scribe (Scribe)

**Purpose:** Test execution recipe. Defines what to test, how to test it, and what this pass needs from the Scribe maintainer.

**Date:** 2026-09-07
**Author:** BMad Master Test Architect (bmad-testarch-test-design, unattended run)
**Status:** Draft
**Project:** pyforge-scribe

**Related:** See `test-design-architecture.md` for testability concerns and the 4 high-priority risk mitigation plans (R-001, R-002, R-003, R-006).

---

## Executive Summary

**Scope:** Test scenarios for Scribe's shipped surface (`capture`, `capture --promote`, `capture --transcripts`, `graph compile --nightly`, `recall`, the `GraphStore` plugin contract) — specifically the gaps and risks identified against the 19-story epic breakdown and the tracked deferred-work ledger, not a re-derivation of the ~19 existing test files' full contents.

**Risk Summary:**

- Total Risks: 9 (4 high-priority score ≥6, 3 medium, 2 low)
- Critical Categories: DATA (promote.py write-boundary, recall grounding correctness), TECH (air-gap regression coverage, graph node titling)

**Coverage Summary:**

- P0 tests: ~9 (write-boundary integrity, grounded-citation correctness, air-gap default)
- P1 tests: ~14 (promotion classification edge cases, supersession, compile idempotency, plugin selection)
- P2 tests: ~16 (memlog titling, transcript provenance, extras off-by-default)
- P3 tests: ~3 (spec-surface hygiene, exploratory)
- **Total**: ~42 tests (~1-2 weeks with 1 QA/dev-in-test-role, mostly extending the existing pytest suite rather than building new infrastructure)

---

## Not in Scope

| Item | Reasoning | Mitigation |
|---|---|---|
| **Story 7.1 (three docs-skill routing)** | `blocked` in the sprint ledger on steward 46.2; introduces no testable runtime code, only routing lines + a register row | Covered by whatever test design steward 46.2's own effort produces; re-run this workflow for Epic 7 once unblocked |
| **CAP-14 durable PG/pgvector driver internals, semantic recall ranking quality** | Owned by steward Epic 28, not Scribe; Scribe's own `test_graph_store_pg.py`/`test_recall_semantic.py` already exist | Covered under steward's own test-design pass |
| **Portal HTMX rendering, `PortalClient` wire format** | Owned by the portal/steward chrome; Scribe's obligation (PortalClient-only, no raw HTTP) is already conformance-tested (`tests/meta/test_first_portal_slice.py`) | Validated manually by steward's UI test coverage |
| **Playwright/browser/UI testing** | Scribe is a backend CLI/library — no `playwright.config.*`, no `package.json`, no browser indicators anywhere under `src/shared/packages/pyforge-scribe/` (stack auto-detected as `backend`) | N/A — not applicable to this station |
| **Contract/Pact testing** | No pact artifacts, no consumer/provider HTTP boundary owned by Scribe itself (`tea_use_pactjs_utils` relevance gate does not fire — no `pact/`, no `.pacttest.ts`, no `@pact-foundation/pact` dependency) | N/A |

**Note:** Items listed here have been reviewed and accepted as out-of-scope for this design pass.

---

## Dependencies & Test Blockers

**CRITICAL:** the P0 tests below cannot be written meaningfully until the corresponding architecture-doc mitigation lands.

### Backend Dependencies (Pre-Implementation)

**Source:** See `test-design-architecture.md` Quick Guide for the full mitigation plans.

1. **R-002 tie-break fix** - Scribe maintainer - before transcript-sourced recall is trusted
   - QA needs `recall.py::answer()` to consult `valid_from` (or exclude superseded nodes) before a "supersession wins the tie" test can pass.
   - Blocks: P0-003 below.

2. **R-006 memlog titling fix** - Scribe maintainer - next `compile.py` touch
   - QA needs `_node_from_text_file` to prefer `topic:` before a "no node titled `---`" regression test can be written as a passing assertion rather than a documented failure.
   - Blocks: P2-006 below.

### QA Infrastructure Setup (Already in Place — No New Work Needed)

1. **Test fixtures** - existing `tests/unit/conftest.py` provisions the PG test schema from the governed Liquibase changesets (`platform/db/changelog/changes/pyforge-scribe-*.sql`) — reuse this pattern for any new PG-backed test.
2. **Test environments** - `pixi run -e pyforge-scribe pyforge-scribe-test` runs the full suite locally and in CI (`platform-ci.yml`, `coverage-gates.yml`); no separate staging environment exists or is needed for a local-file/CLI product.

**Example fixture-reuse pattern (this repo's actual pytest style, not a generic template):**

```python
import pytest
from pyforge.scribe.graph_store import FlatFileGraphStore
from pyforge.scribe import recall


@pytest.fixture
def store(tmp_path):
    return FlatFileGraphStore(tmp_path / "graph.json")


def test_recall_prefers_current_over_superseded_on_tie(store):
    """R-002 regression: two nodes tie on token overlap; the superseded
    (older) one must not win just because its id sorts first."""
    # ... seed two equal-overlap nodes, one marked superseded via
    # `supersedes:` edge, per test_supersession.py's existing pattern ...
    result = recall.answer("why did we drop Kuzu?", store, repo_root=tmp_path)
    assert result.citation is not None
    assert not result.is_superseded_node
```

---

## Risk Assessment

**Note:** Full risk details, scoring, and mitigation strategies are in `test-design-architecture.md`. This section maps risks to QA validation approach only.

### High-Priority Risks (Score ≥6)

| Risk ID | Category | Description | Score | QA Test Coverage |
|---|---|---|---|---|
| **R-001** | DATA | `promote.py` untested against adversarial input; sole write path outside `.claude/memory/` | **9** | Fuzz `classify_and_draft`/`apply_promotion` with malformed frontmatter and path-traversal-shaped `--type`/`--text`; assert nothing is ever written outside `.claude/memory/` + the one pointer-stub exception |
| **R-002** | DATA | `recall` tie-break can serve a superseded fact as current | **6** | Unit test: two equal-overlap nodes, one superseded — assert the current one wins (blocked until the fix lands; see Dependencies) |
| **R-003** | TECH | No standing air-gap regression beyond the Story 2.1 flat-file adapter | **6** | Extend the offline-conformance pattern to the full default-config `capture → compile → recall` path; add an import-lint/meta-test forbidding new network-client imports outside the PG/plane drivers |
| **R-006** | TECH | 87/88 memlog graph nodes titled `---` | **6** | Regression test asserting no memlog-sourced node title equals `---` (blocked until the fix lands; see Dependencies) |

### Medium/Low-Priority Risks

| Risk ID | Category | Description | Score | QA Test Coverage |
|---|---|---|---|---|
| R-004 | OPS | `MEMORY.md` 200-line cap is convention-only | 4 | Meta-test asserting `MEMORY.md` line count stays under 200 |
| R-005 | OPS | No detector for a broken `CLAUDE.md` `@import` | 4 | Meta-test asserting the import line exists and its target path resolves |
| R-007 | OPS | bmad-loop double-loads `MEMORY.md` in worktree sessions | 3 | Documented, not automated — outside Scribe's write boundary |
| R-008 | DATA | Transcript node id collision (unreachable today) | 2 | Monitor only; add a test if `scan_transcripts()` ever becomes recursive |
| R-009 | OPS | Spec-surface baseline stale for 12 files | 1 | Not a runtime test; scoped `--write-baseline --spec` reconcile |

---

## NFR Test Coverage Plan

**Purpose:** Map NFR requirements to planned validation work. This section defines what evidence should be created or collected; it does not assign final PASS/CONCERNS/FAIL status.

| NFR Category | Requirement / Threshold | Planned Validation | Tool / Level | Evidence Artifact | Priority |
|---|---|---|---|---|---|
| Data integrity (air-gap) | Zero required network calls, default config (PRD SM-5) | Extend offline-conformance test to full `capture → compile → recall` path; add import-lint for network-client modules | pytest unit + meta | `test_graph_store.py` extension + new `tests/meta/test_air_gap_imports.py` | P0 |
| Data integrity (grounding) | Every `recall` response cites a real record or returns "no grounded answer found" | Unit test for tie-break recency correctness | pytest unit | `test_recall.py` | P0 |
| Reliability (unattended compile) | Idempotent, bounded nightly compile (FR-11, Story 3.3) | Already covered — cap/timeout/cache assertions exist per baseline test inventory | pytest unit | `test_transcripts.py`, `test_compile.py` | P1 (verify, no new work) |
| Maintainability (graph readability) | Compiled nodes are human-navigable (titles meaningful) | Regression test: no memlog node titled `---` | pytest unit | `test_compile.py` extension | P2 |

**Missing thresholds or evidence sources:** none — Scribe declares no numeric SLO (latency/throughput); its NFR contract is pass/fail (air-gap: zero calls; grounding: citation-or-explicit-miss).

---

## Entry Criteria

**Testing for the risk-driven scenarios below cannot begin until ALL of the following are met:**

- [x] Requirements agreed (PRD FR-1..FR-15, ARCHITECTURE-SPINE.md AD-1..AD-9 both `status: final`)
- [x] Test environment provisioned (`pixi run -e pyforge-scribe pyforge-scribe-test` already green in CI)
- [x] Test data factories available (`tests/unit/conftest.py` fixtures)
- [ ] R-002's tie-break fix landed (blocks P0-003)
- [ ] R-006's memlog-titling fix landed (blocks P2-006)

## Exit Criteria

**This test-design pass is complete when ALL of the following are met:**

- [ ] All P0 tests passing (R-001 adversarial suite, R-002 tie-break regression once unblocked, R-003 air-gap extension)
- [ ] All P1 tests passing or explicitly triaged
- [ ] No open high-priority (score ≥6) risk without an owner and timeline (see architecture doc — all 4 currently assigned to "Scribe maintainer")
- [ ] Repo-wide coverage gate (`coverage-gates.yml`) still green after new tests land

---

## Test Coverage Plan

**IMPORTANT:** P0/P1/P2/P3 = **priority and risk level**, NOT execution timing. See "Execution Strategy" for when tests run.

### P0 (Critical)

**Criteria:** Blocks core functionality + High risk (≥6) + No workaround

| Test ID | Requirement | Test Level | Risk Link | Notes |
|---|---|---|---|---|
| **P0-001** | `promote.py` writes nothing outside `.claude/memory/` + the pointer-stub exception under fuzzed/malformed input | Unit | R-001 | Extend `test_promote.py`; fuzz frontmatter and `--type`/`--text` |
| **P0-002** | `promote.py` handles concurrent `--promote` invocations against the same `MEMORY.md` without corrupting the index | Unit/Integration | R-001 | New; matches the existing `capture.py::_locked` flock pattern used elsewhere |
| **P0-003** | `recall` never returns a superseded node ahead of its current replacement on an overlap tie | Unit | R-002 | Blocked on the architecture-doc fix landing |
| **P0-004** | Default-config `capture → compile → recall` performs zero network calls end-to-end | Unit (offline harness) | R-003 | Extends the Story 2.1 offline-conformance pattern beyond the flat-file adapter alone |
| **P0-005** | No non-PG/plane module imports a network-client library (`socket`, `requests`, `httpx`, `urllib.request`) | Meta (static import scan) | R-003 | New `tests/meta/` conformance test |
| **P0-006** | Every `scribe recall` response either resolves a real citation or returns the explicit "no grounded answer found" result | Unit | AD-8 (existing) | Verify `test_recall.py` already covers this; add a case for an ambiguous/empty query if missing |
| **P0-007** | `GraphStore` plugin selection (`open_graph_store`) never falls through to an unintended default when `PYFORGE_GRAPHSTORE_OWNER` is set to a registered owner | Unit | AD-5 | Verify `test_graph_store_plugins.py` covers the flat-file/PG/plane three-way selection explicitly |
| **P0-008** | Fact supersession marks the prior node's validity ended without deleting it (FR-10) | Unit | AD-4 (existing) | Verify `test_supersession.py` coverage is current against the tie-break fix (P0-003) once landed |
| **P0-009** | `scribe capture` writes land only under `.claude/memory/<type>/` matching the `type` field (FR-1/FR-8) | Unit | AD-3 (existing) | Verify `test_capture.py` covers all three types plus an invalid-type rejection |

**Total P0:** ~9 tests

---

### P1 (High)

**Criteria:** Important features + Medium risk (3-4) + Common workflows + Workaround exists but difficult

| Test ID | Requirement | Test Level | Risk Link | Notes |
|---|---|---|---|---|
| **P1-001** | `.claude/memory/MEMORY.md` stays under 200 lines | Meta | R-004 | New line-count meta-test |
| **P1-002** | Root `CLAUDE.md`'s `@.claude/memory/MEMORY.md` import line exists and its target resolves | Meta | R-005 | New meta-test |
| **P1-003** | Idempotent re-invocation of `--promote` skips already-`promoted: true` entries (FR-6) | Unit | AD-2 (existing) | Verify `test_promote.py` covers the no-duplicate-write case |
| **P1-004** | Team-voice rewrite strips first-person/"user prefers" framing without altering paths/commands (FR-4) | Unit | AD-2 (existing) | Verify `test_promote.py` covers the rewrite transform, not just classification |
| **P1-005** | `--transcripts` scan never auto-promotes; every candidate lands in the reviewed proposal flow | Unit | Epic 3 (existing) | Verify `test_transcripts.py` asserts zero direct writes before confirmation |
| **P1-006** | Nightly compile is idempotent — unchanged source yields byte-identical rerun | Unit | FR-11 (existing) | Verify `test_compile.py` covers the no-new-activity case |
| **P1-007** | Transcript scan cost bound (256-file cap, 1 GiB budget, 30s per-file timeout) is enforced, not just documented | Unit | Story 3.3 (existing) | Verify `test_transcripts.py` asserts the cap/timeout paths, not only the happy path |
| **P1-008** | Overlapping `graph compile` invocations skip cleanly via the non-blocking lock (exit 0, "skipped") | Unit/Integration | Story 3.3 (existing) | Verify a concurrent-invocation test exists; add if missing |
| **P1-009** | `PostgresGraphStore` schema isolation (`scribe_schema`) matches the Liquibase-governed DDL exactly | Integration | AD-5 (existing) | Verify `test_graph_store_pg.py` runs against the real changesets via `conftest.py`, not a hand-written schema |
| **P1-010** | `graphify`/`cocoindex` extras are behaviorally inert when absent/off (air-gap default) | Unit | Epic 6 (existing) | Verify `test_extras_graphify.py`/`test_extras_cocoindex_flow.py` assert identical compile output with the extra off |
| **P1-011** | `graphify` extra writes GraphNodes only through the `graph_store` persist port, never a parallel store | Unit | Epic 6 (existing) | Verify `test_extras_graphify.py` coverage |
| **P1-012** | `cocoindex` extra recomputes only changed sources (zero recompute on two unchanged runs) | Unit | Epic 6 (existing) | Verify `test_extras_cocoindex_flow.py` coverage |
| **P1-013** | Graph-node `stale: true` flag fires only when source postdates `valid_from` with no `supersedes:` edge | Unit | Epic 6 (existing) | Verify coverage in `test_compile.py`/`test_graph_store_operations.py` |
| **P1-014** | `PlaneGraphStore` refuses in-memory DuckDB by construction | Unit | AD-5 (existing) | Verify `test_graph_store_plane.py` asserts the refusal, not just the happy path |

**Total P1:** ~14 tests

---

### P2 (Medium)

**Criteria:** Secondary features + Low risk (1-2) + Edge cases + Regression prevention

| Test ID | Requirement | Test Level | Risk Link | Notes |
|---|---|---|---|---|
| **P2-001** | A clearly personal user-local entry is classified `personal` and excluded from the promotion proposal | Unit | AD-2 (existing) | Verify `test_promote.py` covers this classification branch |
| **P2-002** | Frontmatter with a bare `@`-token (npm scope, GitHub handle) is written safely without triggering a nested-import interpretation | Unit | DW-1-2-6 | New — guard belongs in the `scribe capture` writer per the ledger's own recommendation |
| **P2-003** | `scan_transcripts()`'s citation format (`<jsonl filename>:L<line>`) resolves correctly for a transcript node | Unit | AD-8 (existing) | Verify `test_transcripts.py` coverage |
| **P2-004** | Two transcripts sharing a basename under different subdirectories do not collide (currently unreachable — non-recursive glob) | Unit | R-008 | Low priority; add only if the scanner becomes recursive |
| **P2-005** | `move_list` extra output (host `import pyforge.*` sites, `sys.path` inserts) matches a known fixture repo layout | Unit | Epic 6 (existing) | Verify `test_extras_move_list.py` coverage |
| **P2-006** | No memlog-sourced graph node is titled `---` | Unit | R-006 | Blocked on the architecture-doc fix landing |
| **P2-007** | Semantic recall (`embeddings.py`) produces deterministic, reproducible embeddings across two runs with no model download | Unit | AD-6 (existing) | Verify `test_recall_semantic.py` asserts determinism, not just "returns a result" |
| **P2-008** | Pointer-stub rewrite preserves the promoted file's path and an ISO `YYYY-MM-DD` date exactly | Unit | AD-2 (existing) | Verify `test_promote.py` covers the stub format precisely |

**Total P2:** ~8 tests *(remaining ~8 of the ~16 estimated P2 scenarios are already covered by the existing 19-file suite per the baseline test-architecture.md inventory and require no new authoring — verification only)*

---

### P3 (Low)

**Criteria:** Nice-to-have + Exploratory + Documentation validation

| Test ID | Requirement | Test Level | Notes |
|---|---|---|---|
| **P3-001** | `pyforge-scribe/spec-pyforge-scribe` spec-surface baseline reconciles cleanly for the 12 stale files | N/A (governance) | Not a pytest scenario — a scoped `--write-baseline --spec` operation per R-009 |
| **P3-002** | `scribe --help` output documents all three top-level commands with sub-flags | Unit (CLI smoke) | Verify `test_cli.py` covers `--help` text |
| **P3-003** | The `cli-runbooks.md` documented crontab entry is syntactically valid (`flock -n`-wrapped, path-parameterized) | Exploratory / doc lint | Manual spot-check, not automated |

**Total P3:** ~3 tests

---

## Execution Strategy

**Philosophy:** Run everything in PRs — the full `pyforge-scribe-test` pytest suite already runs in well under 15 minutes (no browser/UI tests exist to parallelize).

### Every PR: pytest Suite (existing `pyforge-scribe-test` task)

**All functional tests** (from any priority level):

- All unit, integration, and meta tests via `pixi run -e pyforge-scribe pyforge-scribe-test`
- Total: ~45 tests once the new scenarios above land (existing ~19 test files plus the new/extended cases)

**Why run in PRs:** Fast feedback; no expensive infrastructure — the PG-backed tests provision from committed Liquibase changesets in seconds.

### Nightly/Weekly: none required

No load, chaos, or multi-hour test exists or is warranted for a local-file CLI product; the one previously-expensive surface (unbounded transcript scan) was already bounded to sub-3-second cold-run cost by Story 3.3 and runs in the PR tier.

**Manual tests** (excluded from automation):

- P3-003 (crontab syntax spot-check) — documentation validation, not CI-worthy.

---

## QA Effort Estimate

**QA test-authoring effort only** (excludes any Scribe-maintainer fix implementation for R-001/R-002/R-003/R-006 themselves):

| Priority | Count | Effort Range | Notes |
|---|---|---|---|
| P0 | ~9 | ~15-25 hours | R-001's adversarial fuzzing harness is the heaviest single item; P0-003 blocked pending the tie-break fix |
| P1 | ~14 | ~12-20 hours | Mostly verification-of-existing-coverage against the baseline's 19 test files, plus 2 new meta-tests |
| P2 | ~8 | ~6-10 hours | Mix of new small tests and coverage verification |
| P3 | ~3 | ~1-2 hours | Mostly manual/exploratory |
| **Total** | ~34 | **~34-57 hours (~1-2 weeks)** | **1 QA/dev-in-test-role, part-time alongside other work** |

**Assumptions:**

- Includes test design, implementation, and debugging against the existing pytest suite; excludes the underlying fixes for R-001/R-002/R-003/R-006 (those are Scribe-maintainer implementation work tracked in `test-design-architecture.md`).
- Excludes ongoing maintenance.
- Assumes the existing `tests/unit/conftest.py` fixture infrastructure is reused as-is.

**Dependencies from other teams:**

- R-002 and R-006 fixes (Scribe maintainer) block P0-003 and P2-006 respectively — see Dependencies & Test Blockers above.

---

## Implementation Planning Handoff

| Work Item | Owner | Target Milestone | Dependencies/Notes |
|---|---|---|---|
| R-001 adversarial review + `test_promote.py` extension | Scribe maintainer | Next `promote.py` touch | P0-001, P0-002 |
| R-002 tie-break fix + `test_recall.py` extension | Scribe maintainer | Before transcript recall is trusted | Unblocks P0-003 |
| R-003 air-gap regression extension + import-lint meta-test | Scribe maintainer / CI owner | Next `GraphStore` driver or extra | P0-004, P0-005 |
| R-006 memlog titling fix + `test_compile.py` extension | Scribe maintainer | Next `compile.py` touch | Unblocks P2-006 |

---

## Interworking & Regression

| Service/Component | Impact | Regression Scope | Validation Steps |
|---|---|---|---|
| **steward Epic 28 (`PostgresGraphStore`)** | Shares the `GraphStore` port; any port-shape change ripples here | `test_graph_store_pg.py` must stay green | Re-run `pyforge-scribe-test` after any `graph_store.py` protocol change |
| **steward 34.5 (`PlaneGraphStore`, CAP-19 query plane)** | Same port; also consumes `atlas.duckdb` | `test_graph_store_plane.py` must stay green | Same as above |
| **marshal Epic 28 (planning-graph retrieval, Story 28.9)** | Consumes the `stale: true` flag (Story 6.3) | Marshal's own retrieval tests must fall back correctly on a stale node | Cross-station — verify marshal's test suite, not Scribe's, on any `stale` semantics change |
| **Portal `/stations/scribe/` (steward Epic 19/29)** | Consumes `recall` via `PortalClient` only | `tests/meta/test_first_portal_slice.py` must stay green | No raw HTTP path exists to regress |

**Regression test strategy:** the existing `pyforge-scribe-test` pytest suite is the full regression suite for this station; no cross-team coordination is needed beyond re-running it after any `GraphStore` port or `stale`-flag semantic change (both cross-station-consumed surfaces).

---

## Appendix A: Code Examples & Tagging

Scribe has no Playwright/browser surface — the project's actual test stack is pytest. Priority tagging uses pytest markers, not Playwright `--grep` tags:

```python
# pytest.ini / pyproject.toml [tool.pytest.ini_options]
# markers =
#     p0: critical, no-workaround risk
#     p1: high, common-workflow risk
#     p2: medium, edge-case risk
#     p3: low, exploratory

import pytest
from pyforge.scribe import promote


@pytest.mark.p0
def test_promote_never_writes_outside_memory_boundary(tmp_path, monkeypatch):
    """R-001: fuzzed frontmatter/path input must never escape
    .claude/memory/ + the one pointer-stub exception (AD-2/FR-7)."""
    memory_root = tmp_path / ".claude" / "memory"
    source_root = tmp_path / "user-local"
    before = {p for p in tmp_path.rglob("*") if p.is_file()}

    proposal = promote.classify_and_draft(source_root, memory_root, tmp_path)
    promote.apply_promotion(memory_root, proposal)

    after = {p for p in tmp_path.rglob("*") if p.is_file()}
    new_files = after - before
    assert all(
        memory_root in p.parents or p.parent == source_root
        for p in new_files
    )
```

**Run specific markers:**

```bash
# Run only P0 tests
pixi run -e pyforge-scribe pytest src/shared/packages/pyforge-scribe/tests -q -m p0

# Run P0 + P1
pixi run -e pyforge-scribe pytest src/shared/packages/pyforge-scribe/tests -q -m "p0 or p1"

# Run the full suite (default PR gate)
pixi run -e pyforge-scribe pyforge-scribe-test
```

---

## Appendix B: Knowledge Base References

- **Risk Governance**: `risk-governance.md` - Risk scoring methodology
- **Test Priorities Matrix**: `test-priorities-matrix.md` - P0-P3 criteria
- **Test Levels Framework**: `test-levels-framework.md` - E2E vs API vs Unit selection (Unit-dominant here; no E2E/UI surface)
- **Test Quality**: `test-quality.md` - Definition of Done

---

**Generated by:** BMad TEA Agent
**Workflow:** `bmad-testarch-test-design`
**Version:** 5.0 (Step-File Architecture)
