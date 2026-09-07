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
  - "_bmad-output/projects/pyforge-mason/planning-artifacts/test-design-architecture.md"
  - "src/shared/packages/pyforge-mason/tests/"
  - "src/shared/packages/pyforge-mason/pyproject.toml"
  - "pixi.toml"
---

# Test Design for QA: pyforge-mason (Mason CLI)

**Purpose:** Test execution recipe. Defines what to test, how to test it, and what closing the
12 identified risks needs from the Mason maintainer(s). This is a **hardening plan against an
existing 50-file test suite**, not a from-scratch coverage plan — 60 of 61 stories are already
`done`.

**Date:** 2026-09-07
**Author:** Rxm7706 (via TEA)
**Status:** Draft
**Project:** pyforge-mason

**Related:** see `test-design-architecture.md` for the full risk register, ADR-checklist
testability review, and mitigation plans.

**Stack note:** pyforge-mason is a pure Python CLI (argparse) with no browser, HTTP-service, or
UI surface of its own. `tea_use_playwright_utils`/`tea_use_pactjs_utils` are configured `true`
repo-wide, but neither's relevance gate is met here (no `page.goto`/browser tests exist; the one
integration boundary, `cfe.py`, is a subprocess/argv contract, not a broker-tracked HTTP
contract) — code examples below are pytest, matching the codebase's actual convention, not
Playwright/TypeScript.

---

## Not in Scope

| Item | Reasoning | Mitigation |
|---|---|---|
| **django-mason HTMX portal** (`/stations/mason/`, Story 11.2) | Owned by a separate Django app with its own test surface; consumes Mason only via `PortalClient` | Covered by that package's own test design |
| **`conda-forge-expert`'s own internal correctness** | Rule 1 makes CFE authoritative; Mason may not edit or re-validate CFE's own recipe logic (AD-15) | Covered by CFE's own suite + Rule-2 retrospectives |
| **Wrapped-engine performance** (rattler-build, twine, pixi, conda-lock) | External tools Mason invokes, not logic Mason owns (AD-12) | Engine absence/timeout is Mason's concern (covered); engine internal performance is not |
| **Epic 14 / Story `14-1` recipe content** | Pure CFE-recipe work (win-64 variant), no `pyforge.mason` code path | Covered by CFE's own recipe-build gate once implemented |

**Note:** items above have been reviewed and accepted as out-of-scope for this station's own suite.

---

## Dependencies & Test Blockers

**CRITICAL:** two closures gate trusting specific automation surfaces (not the whole suite).

### Backend/Architecture Dependencies (Pre-Adoption)

**Source:** see Architecture doc "Quick Guide" 🚨 for full mitigation plans.

1. **R-004 fix (CFE-rebuild guard hardening)** — Dev/Architect — before Story 12.8's slice-3 decision
   - QA needs `cfe_rebuild_guard_check.py`'s clauses (a)/(b) to be content-validating, not string-equality, before trusting its green as ground truth for the parallel-run rebuild.
2. **R-003 fix (`environment check` failure surfacing)** — Dev — before any CI gate adoption
   - QA needs a real `conda-lock` failure to produce a non-`ok` JSON status before recommending `mason environment check` as a blocking CI step.

### QA Infrastructure Setup (Already in Place)

1. **Test Data / Fixtures** — `tests/fixtures/fake_cfe_root/` (stub CFE scripts emitting canned
   stdout, AD-16) and `tests/fixtures/delegation_fidelity_recipe/` for the one real-CFE test.
   Auto-cleanup via pytest `tmp_path`; no multi-tenant or PII concerns (local CLI, no DB).
2. **Test Environments** — Local and CI both run inside the `pyforge-mason` pixi environment; no
   staging environment exists or is needed for a local CLI.

**Illustrative fixture pattern** (matches the codebase's real convention — a fake CFE root, not a
browser fixture):

```python
# tests/unit/test_environment.py (illustrative shape)
import pytest

def test_environment_check_surfaces_condalock_failure(fake_cfe_root, monkeypatch):
    # Arrange: conda-lock subprocess exits non-zero with stderr content
    monkeypatch.setattr(
        "pyforge.mason.engines.condalock.subprocess.run",
        lambda *a, **k: _FakeCompletedProcess(returncode=1, stderr=b"lock hash mismatch"),
    )

    report = check_environment(manifest_path=fake_cfe_root / "pyproject.toml")

    assert report.status != "ok"
    assert report.errors  # DW-4-4-3: must not be empty on a real failure
```

---

## Risk Assessment

**Note:** full risk details live in the Architecture doc. This section maps risks to QA validation.

### High-Priority Risks (Score ≥6)

| Risk ID | Category | Description | Score | QA Test Coverage |
|---|---|---|---|---|
| **R-001** | TECH | Seam erosion (recipe knowledge leaking into Mason) | **6** | P0-001: seam meta-tests stay green (existing) |
| **R-002** | SEC | Credential leak via logs/receipts/errors | **6** | P0-002: credential-isolation matrix (existing + extend) |
| **R-003** | OPS/DATA | `environment check` swallows a real failure as "ok" | **6** | P0-003: new regression test (recommended) |
| **R-004** | TECH | CFE-rebuild guard clauses (a)/(b) are gameable | **6** | P0-004/P0-005: new guard-hardening tests (recommended) |

### Medium/Low-Priority Risks

| Risk ID | Category | Description | Score | QA Test Coverage |
|---|---|---|---|---|
| R-005 | BUS | conda-forge PR later rejected reports pending, not success | 4 | P1-001: `ShipReceipt` pending-state test (existing) |
| R-006 | TECH | CFE stdout de-facto contract break | 4 | P1-002: delegation-fidelity test, `slow` lane (existing) |
| R-007 | DATA | Concurrent-ship race misreports FAILED vs TERMINAL | 4 | P1-003: race-window regression test (recommended) |
| R-008 | TECH | `~`-prefixed `--cfe-root` not expanded | 4 | P1-004: path-expansion regression test (recommended) |
| R-009 | SEC | Missing `--` argv separator (2 sites) | 2 | P2-001: argv-separator regression test (recommended) |
| R-010 | TECH | `pixi build` preview-software instability | 2 | P2-002: dual-artifact build smoke (existing) |
| R-011 | TECH | Lean-env interpreter mismatch | 2 | P1-005: interpreter-selection + doctor tests (existing) |
| R-012 | OPS | Epic 14 backlog item, no Mason code path | 1 | Not applicable to this suite |

---

## NFR Test Coverage Plan

| NFR Category | Requirement / Threshold | Planned Validation | Tool / Level | Evidence Artifact | Priority |
|---|---|---|---|---|---|
| Security | No credential in logs/receipts/errors at any verbosity (NFR-2, NFR-6, NFR-16) | Assert zero leakage across `--verbose`/default/`--quiet` | pytest unit/meta | `test_credential_isolation.py` output | P0 |
| Performance | Every CFE call bounded by a mandatory timeout (NFR-1) | Assert `CfeTimeoutError` raised, no orphaned process | pytest unit | `test_engines*.py` timeout-path result | P1 |
| Reliability | Deterministic JSON, idempotent ship, dry-run-by-default (NFR-3/4/8/9) | Simulate `conda-lock`/upload failure and race window | pytest unit | `test_engines_condalock.py`, `test_package_ship.py` | P0/P1 |
| Maintainability | Lean deps (NFR-10); semver discipline (NFR-15) | Round-trip pickle/deepcopy for every `MasonError` subclass | pytest unit | `test_errors.py` | P2 |

**Missing thresholds:** no numeric build-time SLO for `mason recipe/package build` — correctly
deferred to the wrapped engine (AD-6); not a gap requiring `nfr-assess` follow-up.

---

## Entry Criteria

- [x] Fixture CFE root available (`tests/fixtures/fake_cfe_root/`) — already ships with the suite
- [x] pixi `pyforge-mason` environment installable — already exists
- [ ] R-003 and R-004 mitigations landed, for anyone about to treat their surfaces as a CI gate

## Exit Criteria

- [ ] All P0 tests passing (100%)
- [ ] All P1 tests passing, or failures triaged with an owner (≥95%)
- [ ] No open P0/P1 finding in `deferred-work-ledger.md` corresponding to R-001–R-004
- [ ] R-001/R-002 meta-tests remain in the default (non-`slow`) `pyforge-mason-test` task
- [ ] R-006's delegation-fidelity test (`slow`) has run at least once since the last CFE MINOR bump

---

## Test Coverage Plan

**Note:** P0/P1/P2/P3 = **priority and risk level**, not execution timing — see Execution Strategy below.

### P0 (Critical)

**Criteria:** blocks the seam guarantee or a trust-bearing automation surface, no workaround.

| Test ID | Requirement | Test Level | Risk Link | Notes |
|---|---|---|---|---|
| **P0-001** | Seam-guard invariants stay enforced | Meta | R-001 | **Existing** — `test_no_recipe_knowledge.py`, `test_adapter_sole_caller.py`, `test_dependency_direction.py` |
| **P0-002** | Credentials never leak at any verbosity | Unit/Meta | R-002 | **Existing** `test_credential_isolation.py`; **extend** to full `--verbose`/`--quiet` matrix |
| **P0-003** | `environment check` surfaces real `conda-lock` failures | Unit | R-003 | **Recommended new** — closes DW-4-4-3 |
| **P0-004** | Guard clause (b) validates brief content, not just YAML equality | Unit/Meta | R-004 | **Recommended new** — closes DW-12-1-1 |
| **P0-005** | Guard flags CFE-version staleness against slice-1's `equivalence: green` | Unit | R-004 | **Recommended new** — closes DW-12-1-2 |

**Total P0:** 5 (2 existing + regression-lock, 3 recommended new)

### P1 (High)

**Criteria:** important behavior, medium/high risk, workaround exists but is costly.

| Test ID | Requirement | Test Level | Risk Link | Notes |
|---|---|---|---|---|
| **P1-001** | `ShipReceipt` pending-state discipline for conda-forge target | Unit | R-005 | **Existing** `test_package_ship.py` |
| **P1-002** | Delegation-fidelity against a real CFE install | Integration, `slow` | R-006 | **Existing** `test_delegation_fidelity.py` |
| **P1-003** | Concurrent-ship race reclassifies the loser as TERMINAL | Unit | R-007 | **Recommended new** — closes DW-3-7-1 |
| **P1-004** | `~`-prefixed `--cfe-root` expands; `expanduser()` errors caught | Unit | R-008 | **Recommended new** — closes DW-3-6-2/3 |
| **P1-005** | Interpreter selection chain + import-floor probe + doctor report | Unit | R-011 | **Existing** `test_engines.py`, `test_doctor.py`, `test_cli.py` |
| **P1-006** | Exit-code single-ownership (`exit_codes.py`) | Meta | supports R-001 class | **Existing** `test_exit_code_ownership.py` |

**Total P1:** 6 (4 existing, 2 recommended new)

### P2 (Medium)

**Criteria:** secondary hardening, low/medium risk, edge cases.

| Test ID | Requirement | Test Level | Risk Link | Notes |
|---|---|---|---|---|
| **P2-001** | `--` argv separator present in `cfe.validate_recipe()` and `engines.pixi.upload()` | Unit | R-009 | **Recommended new** — closes DW-2-5-4, DW-3-5-1 |
| **P2-002** | Dual-artifact build (conda + wheel/sdist) succeeds from one manifest | Integration | R-010 | **Existing** `test_package_build.py` |
| **P2-003** | Malformed `MASON_CFE_TIMEOUT` warns instead of silently ignoring | Unit | (OPS, DW-2-7-1) | **Recommended new** |

**Total P2:** 3 (1 existing, 2 recommended new)

### P3 (Low)

**Criteria:** documentation/cosmetic, minimal impact.

| Test ID | Requirement | Test Level | Notes |
|---|---|---|---|
| **P3-001** | `pyforge-mason-test-slow` task description text matches what it actually runs | N/A (docs) | Closes DW-3-8-1; not a test, a `pixi.toml` comment fix |

**Total P3:** 1 (documentation fix, no test)

---

## Execution Strategy

**Philosophy:** run everything in the PR lane unless it needs a real CFE install; the fixture-CFE
suite is fast enough that there is no reason to defer any of it.

### Every PR: `pyforge-mason-test` (fast, offline)

- `pixi run -e pyforge-mason pyforge-mason-test` → `pytest src/shared/packages/pyforge-mason/tests -q -m "not slow"`
- All P0/P1/P2 unit, meta, and non-`slow` integration tests (includes every recommended-new test above except P1-002)
- Deterministic, offline, no real CFE install required (AD-16)

### Nightly/Weekly: `pyforge-mason-test-slow` + the CFE-rebuild equivalence lane

- `pixi run -e pyforge-mason pyforge-mason-test-slow` → the one real-CFE delegation-fidelity test (P1-002, FR-46)
- Separately (owned by the CFE-rebuild effort, not this pixi task): the equivalence-harness checks
  noted in DW-12-2-1 make a live GitHub API call under only `@pytest.mark.slow` — recommend also
  marking it `@pytest.mark.network` so a `-m "not network"` CI selection actually excludes it, per
  that finding.

**Manual tests:** none — Mason has no UI/exploratory surface of its own.

---

## QA Effort Estimate

**Hardening effort only** — the suite and architecture already exist; this closes 12 identified gaps.

| Priority | Count | Effort Range | Notes |
|---|---|---|---|
| P0 | 5 | ~8–14 hours | 3 new tests + 2 production fixes (R-003, R-004) |
| P1 | 6 | ~6–12 hours | 2 new tests + 2 production fixes (R-007, R-008); 4 already pass |
| P2 | 3 | ~4–8 hours | 2 new tests + 1 production fix (R-009); 1 already passes |
| P3 | 1 | ~0.5–1 hour | doc-only fix |
| **Total** | **15** | **~19–35 hours** | **~0.5–1 week, single maintainer** |

**Assumptions:** includes test authorship, the paired production fix, and CI verification;
excludes ongoing maintenance. No dedicated QA role exists on this station — Dev (Rxm7706) owns
both the fix and its test.

---

## Interworking & Regression

| Service/Component | Impact | Regression Scope | Validation Steps |
|---|---|---|---|
| **`conda-forge-expert`** (skill + MCP server) | Mason's sole recipe-domain dependency; a stdout/behavior change can break an adapter parse (R-006) | FR-46 delegation-fidelity test + CFE's own suite | Run `pyforge-mason-test-slow` after any CFE MINOR bump; cross-check via `mason doctor` |
| **`django-mason` portal** (`/stations/mason/`) | Consumes Mason only via `PortalClient` (Story 11.2) | django-mason's own test suite | Out of this document's scope; coordinate at the Canopy layer |
| **`pyforge-core`** (`PyforgeError` base) | `MasonError` re-parents to it | `test_errors.py` + pyforge-core's own suite | Re-run `pyforge-mason-test` after any `pyforge-core` change |

**Regression strategy:** the default `pyforge-mason-test` task is the regression suite; no
separate regression pass is needed because it already runs on every PR.

---

## Appendix A: Illustrative Test Shapes

These are shape recommendations for the "recommended new" rows above, matching the codebase's own
pytest + fixture-CFE-root convention — **not** Playwright, since Mason has no browser surface.

```python
# tests/unit/test_package.py (P1-003, illustrative shape)
def test_ship_pypi_race_loser_reports_terminal_not_failed(fake_cfe_root, monkeypatch):
    """DW-3-7-1: a concurrent upload of the same name+version should classify
    the losing invocation as TERMINAL (already shipped by the winner), not FAILED."""
    monkeypatch.setattr(
        "pyforge.mason.pypi_index.version_exists", lambda *a, **k: False,  # check ran before winner uploaded
    )
    monkeypatch.setattr(
        "pyforge.mason.engines.twine.upload",
        lambda *a, **k: _AlreadyExistsUploadError("File already exists"),
    )

    result = ship_pypi(dist_dir=fake_cfe_root / "dist", dry_run=False)

    assert result.state == ShipState.terminal  # not ShipState.failed
```

```python
# tests/unit/test_resolve.py (P1-004, illustrative shape)
@pytest.mark.parametrize("raw_root", ["~/repos/local-recipes", "~"])
def test_cfe_root_expands_user_path(raw_root, monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    resolved = resolve_cfe_root(explicit_arg=raw_root, environment_mapping={}, start_directory=tmp_path)
    assert "~" not in str(resolved.path)
```

**Selective execution by marker (pytest, not Playwright grep tags):**

```bash
# Fast default loop (PR)
pytest src/shared/packages/pyforge-mason/tests -q -m "not slow"

# Slow / real-CFE lane (nightly)
pytest src/shared/packages/pyforge-mason/tests -q -m slow
```

---

## Appendix B: Knowledge Base References

- **Risk Governance**: `risk-governance.md` — scoring methodology used for R-001–R-012
- **Probability/Impact Scale**: `probability-impact.md` — the 1–3 × 1–3 matrix applied above
- **Test Priorities Matrix**: `test-priorities-matrix.md` — P0–P3 criteria
- **Test Levels Framework**: `test-levels-framework.md` — unit vs. integration vs. meta selection
- **Test Quality**: `test-quality.md` — Definition of Done applied to the recommended new tests
- **ADR Quality Readiness Checklist**: `adr-quality-readiness-checklist.md` — basis for the
  Architecture doc's testability review (Scalability/DR marked N/A per its own category list)
- **NFR Criteria**: `nfr-criteria.md` — basis for the NFR Test Coverage Plan above

---

**Generated by:** TEA Master Test Architect (`bmad-testarch-test-design`, system-level, Create mode)
**Version:** 4.0 (BMad v6)
