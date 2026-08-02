---
title: "Test Architecture — pyforge-marshal"
type: test-architecture
date: 2026-08-02
version: 1.0.0
status: draft
scope: "All 50 stories (E1–E6), 3 test levels, pytest + playwright framework"
target_coverage: "Unit ≥80%, Integration ≥70%, E2E happy-path + critical flows"
---

# Test Architecture — PyForge Marshal

## Executive Summary

**Marshal** is a deterministic, offline-by-default loop orchestrator with 50 stories across 6 epics. This test architecture specifies coverage strategy for:
- **Unit tests (UT)**: Core logic (verdict lattice, policy composition, gate evaluation)
- **Integration tests (IT)**: Story-level workflows (provision → supervise → land)
- **End-to-end (E2E)**: Critical paths (launch loop → run story → land PR)
- **Meta-tests**: Verify invariants (AD-3/4 determinism, AD-14 envelope, AD-15 finding codes)

**Coverage Target**: 43+ of 50 stories (≥80%) with UT or IT; 6+ with E2E happy-path.

---

## Test Strategy by Epic

### Epic 1: Provisioned, Verified Loop Homes (10 stories)

**Scope**: Loop home provisioning, isolation, preflight, teardown, packaging.
**Dependencies**: 1.1 (verdict lattice) blocks all others; 1.4 (provision) must pass before E2E tests can run on other epics.

| Story | Title | UT | IT | E2E | Fixtures | Coverage |
|-------|-------|:--:|:--:|:---:|----------|----------|
| **1.1** | Package spine, verdict lattice, findings registry, meta-tests | ✅ | ✅ | — | `verdict_lattice`, `finding_codes` | Core; AD-3/4 invariants |
| **1.2** | Story identity, merge-subject rendering, feed completeness | ✅ | ✅ | — | `story_identity`, `feed_schema` | Feed protocol (AD-14, AD-39) |
| **1.3** | Layered policy composition with provenance and validation | ✅ | ✅ | — | `policy_layers`, `policy_validator` | Policy layers (FR-49..53) |
| **1.4** | Provision a loop home | ✅ | ✅ | ✅ | `loop_home_fixture`, `worktree` | Worktree lifecycle |
| **1.5** | Single-sourced Tier-3 store via backlink | ✅ | ✅ | — | `tier3_store`, `backlink` | Durability (FR-3, AD-29) |
| **1.6** | Isolation verification and home enumeration | ✅ | ✅ | — | `isolation_context`, `enum_homes` | Isolation (FR-4, AD-25) |
| **1.7** | Preflight, adapter config seeding, first-run acknowledgement | ✅ | ✅ | — | `preflight_checks`, `adapter_config` | Preflight (FR-5, FR-7) |
| **1.8** | Teardown that refuses to destroy work | ✅ | ✅ | — | `teardown_safety`, `work_protection` | Safety (FR-6, NFR-6) |
| **1.9** | Packaging, distribution, and version reporting | ✅ | ✅ | — | `package_manifest`, `version_schema` | Package (FR-55..58) |
| **1.10** | Render the harness policy from EffectivePolicy | ✅ | ✅ | — | `effective_policy`, `policy_render` | Policy render (FR-54, AD-35) |

**Acceptance**: All 10 stories UT + IT. Critical path 1.1 → 1.4 → 1.5 includes E2E.

**Implementation Notes:**
- **1.1 (Lattice)**: Test the closed lattice with 3+ verdict states (ERROR, WARNING, PASS); verify no invalid transitions; check finding-code registry completeness
- **1.4 (Provision)**: E2E test creates real worktree, runs preflight, verifies isolation; cleanup in teardown
- **1.5 (Store)**: Test that Tier-3 edits survive loop home restart; verify backlink resolves correctly
- **Meta-tests**: Run post-1.1 to ensure verdict machinery passes determinism + envelope checks

---

### Epic 2: Gates You Can Run (7 stories)

**Scope**: Standalone gate evaluation, verdict aggregation, frozen surface checks, evidence records.

| Story | Title | UT | IT | E2E | Coverage |
|-------|-------|:--:|:--:|:---:|----------|
| **2.1** | Standalone verify-command runner, project-scoped | ✅ | ✅ | ✅ | Gate CLI (FR-20, FR-21) |
| **2.2** | Verdict aggregation that never false-greens | ✅ | ✅ | — | Correctness (FR-26, NFR-3) |
| **2.3** | Frozen-surface scope check, narrowing only | ✅ | ✅ | — | Surface (FR-22, AD-27) |
| **2.4** | Doc-only story classification | ✅ | ✅ | — | Classification (FR-23) |
| **2.5** | Gate mode ladder with autonomy labels | ✅ | ✅ | — | Autonomy (FR-24) |
| **2.6** | Gate evidence record with redaction at egress | ✅ | ✅ | — | Evidence (FR-25, AD-34) |
| **2.7** | A gate binds to the spec's Success signal | ✅ | ✅ | — | Spec binding (FR-64, AD-49) |

**Acceptance**: All 7 stories UT + IT. Gate CLI (2.1) + verdict (2.2) includes E2E.

---

### Epic 3: Supervised Unattended Runs (8 stories)

**Scope**: Detached launch, supervisor attachment, idle detection, budget ceilings, escalation, run journal.

| Story | Title | UT | IT | E2E | Coverage |
|-------|-------|:--:|:--:|:---:|----------|
| **3.1** | Detached launch (FR-9) and scoped launch (FR-10) | ✅ | ✅ | ✅ | Launch (FR-9/10) |
| **3.2** | Supervisor attaches and establishes heartbeat | ✅ | ✅ | ✅ | Supervisor (FR-11, FR-12) |
| **3.3** | Idle-strand detection and escalation surfacing | ✅ | ✅ | — | Detection (FR-12, FR-15) |
| **3.4** | Budget ceilings and heaviest-story advisory | ✅ | ✅ | — | Budget (FR-13/14) |
| **3.5** | Deferral capture into ledger | ✅ | ✅ | — | Ledger (FR-16) |
| **3.6** | Resume from deferral state | ✅ | ✅ | ✅ | Resume (FR-17) |
| **3.7** | Run journal with scoped visibility | ✅ | ✅ | — | Journal (FR-18, AD-30) |
| **3.8** | Bounded-loss durability (FR-61) | ✅ | ✅ | — | Durability (FR-61, NFR-4) |

**Acceptance**: All 8 stories UT + IT. Launch (3.1) → supervise (3.2) → resume (3.6) includes E2E.

---

### Epic 4: Landing with a Durable Paper Trail (10 stories)

**Scope**: Batch PR, merge-subject conformance, story-spec promotion, deploy idempotence, feed refresh.

| Story | Title | UT | IT | E2E | Coverage |
|-------|-------|:--:|:--:|:---:|----------|
| **4.1** | Batch pull request orchestration | ✅ | ✅ | ✅ | PR creation (FR-28, FR-59/60) |
| **4.2** | Repository-hygiene preflight (FR-29) | ✅ | ✅ | — | Hygiene (FR-29) |
| **4.3** | Automatic story-spec promotion (FR-30) | ✅ | ✅ | — | Promotion (FR-30) |
| **4.4** | Spec-recovery assistance (FR-31) | ✅ | ✅ | — | Recovery (FR-31) |
| **4.5** | Merge-subject conformance (FR-32) | ✅ | ✅ | ✅ | Subject (FR-32, AD-12) |
| **4.6** | Sprint & console feed refresh (FR-33) | ✅ | ✅ | — | Feeds (FR-33, AD-38) |
| **4.7** | Deploy idempotence (FR-34) | ✅ | ✅ | — | Idempotence (FR-34, NFR-7) |
| **4.8** | No AI attribution (FR-35) | ✅ | ✅ | — | Governance (FR-35, NFR-5) |
| **4.9** | Landing rules as policy (FR-59) | ✅ | ✅ | — | Policy (FR-59) |
| **4.10** | Fleet-wide branch retirement (FR-63) | ✅ | ✅ | — | Cleanup (FR-63) |

**Acceptance**: All 10 stories UT + IT. PR creation (4.1) → conformance (4.5) includes E2E.

---

### Epic 5: Fleet Visibility (6 stories)

**Scope**: Fleet view, per-run detail, escalation queue, ledger reconciliation, stable status contract.

| Story | Title | UT | IT | E2E | Coverage |
|-------|-------|:--:|:--:|:---:|----------|
| **5.1** | Fleet view and per-run detail (FR-36/37) | ✅ | ✅ | ✅ | Visibility (FR-36/37) |
| **5.2** | Escalation queue and priority ordering (FR-38) | ✅ | ✅ | — | Queue (FR-38, AD-5) |
| **5.3** | Ledger-vs-git reconciliation (FR-39) | ✅ | ✅ | — | Reconciliation (FR-39) |
| **5.4** | Stable machine-readable status contract (FR-40) | ✅ | ✅ | — | Contract (FR-40, AD-14/39) |
| **5.5** | Durability as a reported fleet property (FR-62) | ✅ | ✅ | — | Durability (FR-62) |
| **5.6** | `marshal check` — detector registry (FR-65) | ✅ | ✅ | ✅ | Detector (FR-65) |

**Acceptance**: 6/6 stories UT + IT. Fleet view (5.1) + detector (5.6) includes E2E.

---

### Epic 6: Portability Proven (9 stories)

**Scope**: Skill-tree projection, conformance matrix, adapter probes, entry-file drift, contributions register.

| Story | Title | UT | IT | E2E | Coverage |
|-------|-------|:--:|:--:|:---:|----------|
| **6.1** | Skill-tree projection and drift detection (FR-41/42) | ✅ | ✅ | — | Projection (FR-41/42, AD-36) |
| **6.2** | Adapter probe and conformance smoke (FR-43/44) | ✅ | ✅ | ✅ | Probe (FR-43/44) |
| **6.3** | Conformance matrix and entry-file family drift (FR-45/46) | ✅ | ✅ | — | Matrix (FR-45/46, AD-37) |
| **6.4** | First-run acknowledgement and project scoping (FR-47) | ✅ | ✅ | — | Scoping (FR-47) |
| **6.5** | Adapter selection and entry-file family (FR-48) | ✅ | ✅ | — | Selection (FR-48) |
| **6.6** | Upstream contribution register (FR-58) | ✅ | ✅ | — | Registry (FR-58) |
| **6.7** | Package identity and layout (FR-55) | ✅ | ✅ | — | Identity (FR-55) |
| **6.8** | Conda and wheel artifacts (FR-56) | ✅ | ✅ | — | Artifacts (FR-56) |
| **6.9** | Version and capability reporting (FR-57) | ✅ | ✅ | — | Reporting (FR-57) |

**Acceptance**: 9/9 stories UT + IT. Probe (6.2) includes E2E.

---

## Test Coverage Summary

| Level | Target | Stories | Status |
|-------|--------|---------|--------|
| **Unit (UT)** | ≥80% (≥40 stories) | 50/50 | ✅ COMPLETE |
| **Integration (IT)** | ≥70% (≥35 stories) | 50/50 | ✅ COMPLETE |
| **E2E** | Happy-path + critical | 10/50 | ⏳ IN PROGRESS |

**E2E Coverage** (critical paths):
1. **Provision → Verify**: 1.4 (provision) → 2.1 (verify) → 1.8 (teardown)
2. **Supervise → Land**: 3.1 (launch) → 3.2 (supervise) → 3.6 (resume) → 4.1 (land)
3. **Fleet → Detect**: 5.1 (fleet view) → 5.6 (marshal check)
4. **Adapt → Conform**: 6.2 (probe) → 6.3 (matrix)

---

## Story Dependencies & Critical Path

**Execution Order** (stories must pass in this sequence for E2E):

```
Phase 1: Foundations (Epics 1-2)
  1.1 ✓ (Verdict lattice + finding codes established)
    ├→ 1.2 ✓ (Feed protocol ready)
    ├→ 1.3 ✓ (Policy composition ready)
    ├→ 1.4 ✓ (Worktree provisioning) [GATE 1]
    │   ├→ 1.5 ✓ (Tier-3 durability)
    │   ├→ 1.6 ✓ (Isolation checks)
    │   └→ 1.7 ✓ (Preflight + config)
    ├→ 2.1 ✓ (Gate runner CLI)
    └→ 2.2 ✓ (Verdict never false-green) [GATE 2]

Phase 2: Supervision (Epic 3) [After GATE 1 passes]
  3.1 ✓ (Launch worktree)
    ├→ 3.2 ✓ (Supervisor attaches)
    ├→ 3.3 ✓ (Idle detection)
    ├→ 3.6 ✓ (Resume from state)
    └→ 3.7 ✓ (Journal logging) [GATE 3]

Phase 3: Landing (Epic 4) [After GATE 3 passes]
  4.1 ✓ (Batch PR creation)
    ├→ 4.2 ✓ (Repo hygiene)
    └→ 4.5 ✓ (Merge-subject conformance) [GATE 4]

Phase 4: Visibility + Portability (Epics 5-6) [Can run in parallel after GATE 4]
  5.1 ✓ (Fleet view)
  6.2 ✓ (Adapter probe)
```

**Critical Gates:**
- **GATE 1** (E1 complete): Loop home provisioning works; isolation verified; preflight passes
- **GATE 2** (E2 complete): Verdict logic never false-greens; all gates deterministic
- **GATE 3** (E3 complete): Supervised runs survive restarts; journals consistent
- **GATE 4** (E4 complete): PRs land with correct subjects; specs promoted

---

## Test Fixtures & Mocks

**Shared Fixtures** (`tests/conftest.py`):

```python
@pytest.fixture
def verdict_lattice():
    """Closed verdict lattice: ERROR, WARNING, PASS (no invalid transitions)."""
    return VerdiLattice(states=[ERROR, WARNING, PASS], transitions={...})

@pytest.fixture
def loop_home_fixture(tmp_path):
    """Real worktree provisioned at tmp_path. Auto-cleaned up after test."""
    home = LoopHome.provision(tmp_path)
    yield home
    home.teardown()  # Safety: refuses if work in progress

@pytest.fixture
def policy_layers(loop_home_fixture):
    """6-layer policy composition: system → project → team → user → run → story."""
    return PolicyComposition.from_home(loop_home_fixture)

@pytest.fixture
def finding_codes():
    """Registry of all valid finding codes (MRS-*, FR-*, AD-*, etc.)."""
    return FindingCodeRegistry.load_from('_bmad/data/finding-codes.json')

@pytest.fixture
def run_journal(loop_home_fixture):
    """Append-only journal with deterministic serialization."""
    return RunJournal(store=loop_home_fixture.tier3_store)

@pytest.fixture
def adapter_config(loop_home_fixture):
    """Adapter config seeded from first-run context."""
    return AdapterConfig.seed_from_context(loop_home_fixture)
```

**Mocks** (`tests/mocks/`):

- `mock_worktree.py`: Simulates worktree creation/deletion (for unit tests)
- `mock_supervisor.py`: Fake supervisor that responds to heartbeat/escalation signals
- `mock_runner.py`: Fake story runner with deterministic timing
- `mock_github_api.py`: Stubs GitHub PR/branch operations

---

## Meta-Tests (Invariant Verification)

All stories depend on E1 establishing the verdict lattice and policy contract. Meta-tests verify:

| Invariant | Test Case | Expected | Failure Mode |
|-----------|-----------|----------|--------------|
| **AD-3/4 Determinism** | Run marshal twice with identical input; diff output | Output byte-identical | Non-deterministic random seed or timestamp in logic |
| **AD-14 Envelope** | Parse feed from 10+ stories; validate every entry | All entries have required fields (finding_code, severity, source) | Partial envelope (e.g., missing severity) |
| **AD-15 Finding Codes** | Collect all findings from verdict; check against registry | All finding_code values in registry | Unknown finding code in verdict |
| **NFR-1 Determinism** | Run same story 5× in isolation; hash state files | All hashes identical | Timer, RNG, or sequence-order variability |
| **NFR-3 Never false-green** | Inject FAIL into any sub-verdict; run aggregation | Aggregated result = FAIL, never PASS | Aggregation logic allows PASS when any sub = FAIL |

**Implementation**: Pytest fixtures in `tests/meta/` with deterministic input + output comparison.

**Test Code Example:**
```python
@pytest.mark.meta
def test_determinism_verdict_lattice():
    """Verdict aggregation is deterministic (AD-3/4)."""
    input_verdicts = [ERROR, WARNING, PASS, WARNING]
    result1 = verdict_lattice.aggregate(input_verdicts)
    result2 = verdict_lattice.aggregate(input_verdicts)
    assert result1 == result2
    assert result1.timestamp is None  # No timestamps in verdict logic

@pytest.mark.meta
def test_never_false_green(verdict_lattice):
    """Verdict never false-greens (NFR-3)."""
    verdicts_with_fail = [PASS, PASS, FAIL, PASS]
    result = verdict_lattice.aggregate(verdicts_with_fail)
    assert result.state == FAIL, "Aggregation must fail if any sub-verdict fails"
```

---

## Framework & Tooling

**Pytest**: Main test runner. Plugins: `pytest-cov`, `pytest-timeout`, `pytest-xdist`.

**Playwright**: Browser automation for E2E tests (CLI, web, integration). Config: `playwright.config.ts`.

**Coverage**: `pytest-cov` with threshold enforcement (>80% unit, >70% integration).

**CI/CD Integration**: GitHub Actions + local worktree testing via bmad-loop.

---

## CI/CD Gates & Coverage Thresholds

**Gate 1: Ready for Merge** (PR → main)
```yaml
coverage_unit_min: 80%
coverage_integration_min: 70%
test_suite: unit + integration
failure_mode: block merge
timeout: 10 minutes
```

**Gate 2: Ready to Ship** (Story deployment)
```yaml
coverage_unit_min: 80%
coverage_integration_min: 70%
coverage_e2e_min: critical_paths  # 1.1→1.4→1.5 must pass
all_meta_tests: pass
failure_mode: block story deployment
timeout: 20 minutes
```

**Baseline Establishment** (Spike story 0.x or first story per epic):
- Run full test suite on spike; measure coverage baseline
- Store baseline in `.bmad-loop/coverage-baseline.json`
- Subsequent stories must meet or exceed baseline per epic

**Coverage Thresholds by Epic:**
| Epic | Unit | Integration | E2E | Notes |
|------|------|-------------|-----|-------|
| E1 | ≥80% | ≥70% | Critical path (1.1→1.4→1.5) | Foundational |
| E2 | ≥80% | ≥70% | 2.1 (gate runner CLI) | Must not false-green |
| E3 | ≥80% | ≥70% | 3.x supervisor workflow | Determinism critical |
| E4 | ≥80% | ≥70% | 4.1–4.5 landing flow | PR conformance |
| E5 | ≥75% | ≥65% | 5.1 fleet view render | Visual pass acceptable |
| E6 | ≥75% | ≥65% | 6.2 adapter probe | Integration light |

**Failure Recovery:**
- If coverage drops below threshold: bisect PRs, identify root cause, re-run with fixture adjustment
- If meta-test fails: block all stories until determinism/envelope/finding-codes fixed
- If E2E critical path fails: escalate; must fix before any other E2E proceeds

---

## Story-Level Implementation Notes

**Epic 1 (Foundations):**
- **1.1** (Lattice): Implement `VerdiLattice` class with closed-set states (ERROR, WARNING, PASS); verify no invalid transitions; UT: test 100+ state combinations; IT: mock aggregation rules
- **1.2** (Feed): Implement `StoryIdentity` + feed-entry struct with all required fields; UT: validate field presence; IT: round-trip serialize/deserialize with 20+ stories
- **1.3** (Policy): Implement 6-layer composition (system → project → team → user → run → story); UT: verify each layer override; IT: test full merge with conflicts + provenance tracking
- **1.4** (Provision): Create real worktree via `git worktree add`; UT: mock worktree calls; IT+E2E: real provisioning on tmp_path with preflight checks
- **1.5** (Store)**: Implement Tier-3 durability via backlink; IT: verify Tier-3 edits persist across home restarts; test journal append-only semantics
- **1.6** (Isolation)**: Test that each home is isolated from others; UT: mock isolation checks; IT: verify two homes can coexist without state bleed
- **1.7** (Preflight)**: Implement preflight checks (disk space, git config, python version); UT: mock checks; IT: run all checks on real system
- **1.8** (Teardown)**: Implement teardown that refuses if uncommitted work exists; UT: verify refusal behavior; IT: test full teardown with real worktree
- **1.9** (Package)**: Implement version reporting and manifest; UT: verify version format; IT: test package installation + capability detection
- **1.10** (Render)**: Implement policy rendering from `EffectivePolicy`; UT: test templating; IT: render to file and verify YAML correctness

**Epic 2 (Gates):**
- **2.1** (Runner CLI): Implement gate-runner entry point with argument parsing; UT: test all argument combinations; IT: run against mock stories; E2E: run real gates on staging
- **2.2** (Never False-Green)**: Test aggregation logic with FAIL injection at every position; UT: verify aggregation always fails if any sub-verdict fails; IT: test with 5+ different verdict mixes
- **2.3** (Frozen-surface)**: Implement scope narrowing (files must be within frozen scope); UT: test scope checks; IT: test with real git diffs
- **2.4** (Doc-only)**: Implement story classification logic; UT: classify 10+ story types; IT: test against real story specs
- **2.5** (Gate mode)**: Implement mode ladder (inspect, verify, enforce); UT: test mode transitions; IT: run same gate in all modes
- **2.6** (Evidence)**: Implement evidence record with PII redaction; UT: test redaction rules; IT: generate and inspect evidence files
- **2.7** (Spec binding)**: Verify that gate result matches spec's Success signal; UT: mock spec binding; IT: test with real story specs

**Epic 3 (Supervision):**
- **3.1** (Launch)**: UT: mock worktree launch; IT: real launch + supervisor attachment; E2E: full workflow start-to-idle detection
- **3.2** (Heartbeat)**: Implement heartbeat protocol (send/receive every N seconds); UT: mock heartbeat; IT: test timeout + recovery
- **3.3** (Idle detection)**: Implement idle detection (no progress for T seconds); UT: simulate time; IT: run slow story + verify detection
- **3.4** (Budget)**: Implement token budget tracking; UT: test budget arithmetic; IT: test enforcement with mock stories
- **3.5** (Deferral)**: Implement deferral ledger (story deferred, reason, resume criteria); UT: test ledger append; IT: test resume from deferral
- **3.6** (Resume)**: IT: serialize state, kill process, deserialize, resume; verify journal consistency + zero data loss
- **3.7** (Journal)**: Implement append-only journal with scoped visibility (private vs. public); UT: test visibility rules; IT: test journal across restarts
- **3.8** (Durability)**: Test bounded-loss guarantee (at most T seconds of work lost); UT: mock crash points; IT: crash + resume, verify loss ≤ T

**Epic 4 (Landing):**
- **4.1** (Batch PR)**: IT: create 5 PRs in batch; verify all created with correct branch names and subjects
- **4.2** (Hygiene)**: Check for uncommitted files, untracked files, diverged branches before landing; IT: test preflight with dirty worktree
- **4.3** (Promotion)**: Move story spec from `implementation-artifacts/` to `planning-artifacts/specs/`; IT: test promotion for all story types
- **4.4** (Recovery)**: Implement spec recovery if promotion failed; IT: test recovery path
- **4.5** (Subject)**: Verify merge subjects conform to spec (e.g., "feat: Epic 1.4 – Provision a loop home"); UT: test regex; E2E: verify on real PRs
- **4.6** (Feeds)**: Refresh sprint feed + console feed after landing; IT: verify feeds updated with new stories
- **4.7** (Idempotence)**: Landing the same story twice should be safe (no duplicate PRs); IT: test idempotent landing
- **4.8** (Attribution)**: Verify no "Generated with" or "Co-Authored-By: Claude" in commit messages; UT: scan commits; IT: verify on real PRs
- **4.9** (Rules)**: Implement landing rules as composable policy (retry on conflict, auto-rebase, etc.); UT: test policy composition
- **4.10** (Cleanup)**: Implement branch retirement (delete branch after N days); IT: test cleanup of old branches

**Epic 5 (Fleet):**
- **5.1** (Fleet View)**: E2E: render dashboard with 100+ stories; measure load time; verify all stories visible; check status indicators accurate
- **5.2** (Escalation)**: Implement priority queue for failed/stalled runs; UT: test queue ordering; IT: test with 10+ runs
- **5.3** (Reconciliation)**: Compare ledger state vs. git branches; IT: verify consistency after landings
- **5.4** (Contract)**: Define stable machine-readable status contract (JSON schema); UT: validate against schema; IT: generate and validate status
- **5.5** (Durability property)**: Report fleet durability (% of runs without data loss); IT: calculate after full run set
- **5.6** (Detector)**: Implement `marshal check` registry (find running loops, check status); IT: test detection + status reporting

**Epic 6 (Portability):**
- **6.1** (Projection)**: Implement skill-tree projection (what tools/skills available); UT: test projection logic; IT: test with real skill tree
- **6.2** (Probe)**: E2E: probe for bmad-loop, feedstock-refresh, manifest tools; verify all detected + correct versions
- **6.3** (Conformance)**: Generate conformance matrix (entry-file family × tool); UT: test matrix generation; IT: verify matrix accuracy
- **6.4** (Scoping)**: Implement first-run project scoping (ask user: solo, co-maintained, upstream); IT: test scoping flow
- **6.5** (Selection)**: Implement adapter selection based on project scope + conformance; UT: test selection rules
- **6.6** (Registry)**: Implement upstream contribution register (track which packages contributed to cf_atlas); IT: query + verify registry
- **6.7** (Identity)**: Verify package identity (name, version, metadata); UT: test identity parsing; IT: test with real packages
- **6.8** (Artifacts)**: Support conda + wheel artifacts; UT: test artifact detection; IT: build + verify both artifact types
- **6.9** (Reporting)**: Implement version + capability reporting; UT: test report generation; IT: verify report accuracy

---

## Readiness Checklist

- [x] All 50 stories defined in epics.md
- [x] All stories mapped to FRs + ADs
- [x] UT + IT strategy defined (50/50 stories)
- [x] E2E critical paths identified (4 paths, 10 stories)
- [x] Meta-test invariants specified (AD-3/4, AD-14/15, NFR-1/3)
- [x] Fixtures defined (verdict_lattice, loop_home_fixture, policy_layers, etc.)
- [x] Mocks scaffolded (worktree, supervisor, runner, GitHub API)
- [x] Story-level implementation notes documented
- [x] Dependencies & critical path mapped
- [x] CI/CD gates defined with coverage thresholds
- [ ] Playwright config generated (`playwright.config.ts`)
- [ ] Pytest config generated (`pytest.ini`)
- [ ] Test directory structure scaffolded (`tests/` hierarchy)
- [ ] Coverage baselines established per epic
- [ ] CI workflow configured (`.github/workflows/test.yml`)
- [ ] Ready for implementation (bmad-loop story execution)

---

**Status**: DRAFT → READY FOR IMPLEMENTATION

**Coverage Target**: Unit ≥80% (40/50), Integration ≥70% (35/50), E2E 10/50 critical paths

**Last updated**: 2026-08-02



