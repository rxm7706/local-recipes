---
title: "Test Architecture — pyforge-doctor"
type: test-architecture
date: 2026-08-02
version: 1.0.0
status: draft
scope: "12 stories (E1–E3); Epic 1 shipped (5/5), Epics 2–3 pending (0/7); pytest, 2 real test levels (unit, meta) — no integration/e2e directories exist"
target_coverage: "Epic 1 (shipped): every AC in every story has a corresponding passing test — verified, not aspirational. Epics 2–3 (pending): unit + meta coverage planned per-story below, at the same density Epic 1 shipped."
---

# Test Architecture — PyForge Doctor

## Executive Summary

This document was authored 2026-08-02 to **replace a fabricated placeholder**. The
prior `test-architecture.md` (78 lines) was generic boilerplate — a template with
`Target Stories: TBD` on every row, no reference to Doctor's real epics, stories, or
test files — created in a bulk commit that also contained a false migration note and
other fabricated content; all of it was found and remediated this session. Everything
below is grounded in the actual repository: real story text from `epics.md`, real test
files under `src/shared/packages/pyforge-doctor/tests/`, and a real, currently-green
test run (confirmed via `pixi run -e pyforge-doctor pyforge-doctor-test`: **193 tests
passed** across the 13 files that exist today).

Doctor is **42% code-complete** (5 of 12 stories shipped — Epic 1 done; Epics 2 and 3
not yet started). This document is therefore a **hybrid**:

- **Retrospective for Epic 1** — documents the coverage that actually exists, citing
  real test files by name. No test file is invented; every mapping below was verified
  by reading the file.
- **Prospective for Epics 2–3** — for each of the 7 pending stories, states the
  **planned test level** (unit and/or meta — Doctor has never used integration or
  e2e levels; see below) and what it should cover once the story ships, per that
  story's stated FR/AD and acceptance criteria in `epics.md`. No file name is invented
  for pending work; where a planned meta-test's shape is already established by an
  Epic-1 precedent (e.g. a new sole-subprocess-site guard), that precedent is named
  explicitly as the pattern to mirror, not as an existing file.

## Test Levels In Use (Grounded, Not Templated)

Doctor's real test suite has **two** levels, not the conventional unit/integration/e2e
three — this is a deliberate consequence of its architecture, not a gap:

- **Unit (`tests/unit/`)** — the workhorse level. Because every AD-1/AD-5/AD-6 boundary
  (warden's engine check, the future atlas MCP/CLI gather) is a **library call or a
  monkeypatched function**, not a real subprocess or network call, "integration-shaped"
  behavior (e.g. `doctor.sources.warden.gather()` calling the *real*
  `pyforge.warden.engines.run_doctor_checks`, or `doctor check --json` invoking `main()`
  in-process end-to-end) is exercised **inside** `tests/unit/`, not a separate
  integration tier. `tests/unit/test_checks_env_hygiene.py` and
  `tests/unit/test_check_speed_budget.py` go further still: they run against the real,
  unmocked repo tree (the `_http.py` golden fixture; a real wall-clock `doctor check`
  invocation) — the closest thing this suite has to an integration or E2E test, done as
  a unit test with a real fixture rather than a separate harness.
- **Meta (`tests/meta/`)** — static AST-scan invariant guards (no execution of the code
  under test). These prove architectural rules that a runtime test can't: "this module
  never imports `subprocess`," "this module never calls `exec`/`eval`," "only
  `verdict.py` may reference the frozen exit-code literals." Every meta-test also
  positively proves its own detector fires on a synthetic violation (not vacuous).
- **No `tests/integration/` or `tests/e2e/` directories exist** in
  `src/shared/packages/pyforge-doctor/tests/` today, and none is planned — Doctor is a
  non-interactive CLI at a scale (13 files, 193 tests, all sub-20-second) where a third
  tier would add process overhead without adding coverage the unit level can't already
  provide via real (unmocked) fixtures. This mirrors `pyforge-warden`'s own test
  architecture, which Doctor's package layout was built to mirror (epics.md
  "Additional Requirements").
- **No `tests/fixtures/conftest.py` exists** — fixtures are two static JSON files
  (`tests/fixtures/minimal_check_report.json`, `minimal_diagnose_report.json`) used
  directly by `test_models.py`'s schema-validation tests, not pytest fixture functions.

---

## Epic 1: Pre-flight Check (walking skeleton) — SHIPPED (5/5)

**Scope**: Stand up the package; freeze the `DoctorStatus`/`Source`/`Partition`/
`Finding`/`DoctorReport` contract and the `verdict` exit-code module; wrap warden's
engine self-check as a library call; add the new credential/env-hygiene detector;
wire `doctor check` with `--json` under a speed budget. **FR-1, FR-2, FR-3, FR-9
(check verb), NFR-1, NFR-2, NFR-4, NFR-5.**

| Story | Title | Status | Test files (real) |
|-------|-------|:------:|--------------------|
| **1.1** | Package scaffold, frozen Finding/DoctorReport contract & exit-code module | done | `unit/test_models.py`, `unit/test_verdict.py`, `unit/test_main_stub.py`, `meta/test_verdict_sole_ownership.py`, `meta/test_read_only_guard.py`, `meta/test_no_warden_import.py` |
| **1.2** | Wrap warden's engine-availability self-check (FR-1, AD-1) | done | `unit/test_sources_warden.py`, `meta/test_sources_warden_no_subprocess.py`, `meta/test_no_warden_import.py` (shared — narrows the 1.1 guard's one exemption) |
| **1.3** | Tri-state, individually addressable checks (FR-2) | done | `unit/test_checks_registry.py` |
| **1.4** | Credential/environment-hygiene check (FR-3) | done | `unit/test_checks_env_hygiene.py`, `meta/test_env_hygiene_no_execution.py` |
| **1.5** | `doctor check` CLI wiring, `--json`, and the speed budget (FR-9, NFR-4) | done | `unit/test_cli_check.py`, `unit/test_check_speed_budget.py`, `unit/test_main_stub.py` (shared — its docstring: "extended by Story 1.5") |

**Verified**: `pixi run -e pyforge-doctor pyforge-doctor-test` → `193 passed` (13
files, no skips, no xfails observed at time of writing).

### Story-level detail (Epic 1)

- **1.1 — Contract & exit code.** `unit/test_models.py` (27 test functions) covers
  every row of the story's I/O & Edge-Case Matrix for `Finding`/`DoctorReport`,
  including schema validation of the packaged `data/report-schema.json` against both
  `tests/fixtures/minimal_check_report.json` and `minimal_diagnose_report.json`, and
  against live `DoctorReport.to_json_dict()` output. `unit/test_verdict.py` (11 tests)
  proves the exit-code domain is exactly `{0, 2, 130}` and that a `warn`-status Finding
  never changes the exit code. `unit/test_main_stub.py` (10 tests) proves `--version`,
  `--help`, and the now-`required=True` subcommand usage error. Three meta-tests prove
  the architectural invariants that can't be caught by a runtime assertion:
  `meta/test_verdict_sole_ownership.py` (AD-2 — only `verdict.py` may reference the
  frozen exit literals), `meta/test_read_only_guard.py` (NFR-1 — no filesystem write
  outside a `tempfile`-scoped path anywhere in the package), and
  `meta/test_no_warden_import.py` (AD-3 — no module besides the sanctioned
  `sources/warden.py` may import `pyforge.warden`, absolute or relative form).
- **1.2 — Warden wrap (AD-1).** `unit/test_sources_warden.py` (11 tests) proves the
  all-healthy/one-missing/warden-absent cases plus a **live equivalence check**
  against `pyforge.warden.engines.run_doctor_checks` called directly — the two paths
  are asserted to never diverge — and several review-hardened failure shapes
  (unimportable warden, malformed result, truthy-non-bool `ok`).
  `meta/test_sources_warden_no_subprocess.py` (17 tests) is the AD-1
  no-reimplementation guard: `sources/warden.py` may only import
  `pyforge.warden.engines.run_doctor_checks` — no `subprocess`, no other warden
  submodule, no other symbol from `engines`, and no import outside a closed
  allowlist.
- **1.3 — Tri-state registry.** `unit/test_checks_registry.py` (13 tests) covers
  list-all/filtered/unknown-category, the no-execution proof for `list_checks`,
  `gather_one` found/not-found/unknown-category-raises, and a live drift-detection
  cross-check against a real, unmocked `sources.warden.gather()` call.
- **1.4 — Env-hygiene detector.** `unit/test_checks_env_hygiene.py` (37 tests, the
  largest file in the suite) covers the direct positive case, the real
  `.claude/skills/conda-forge-expert/scripts/_http.py` golden fixture (the concrete
  `JFROG_API_KEY` worked example the Dream names), the host-scoped negative case (no
  false positive on already-correct code), the no-match empty-tuple case, and
  `gather_one`'s filter-equivalence. `meta/test_env_hygiene_no_execution.py` (7 tests)
  proves the scanner is `ast.parse`-only — it never `exec`s/`eval`s/dynamically
  imports the source it scans.
- **1.5 — CLI wiring, `--json`, speed budget.** `unit/test_cli_check.py` (23 tests)
  covers the default combined run, `--engines`/`--env` filtering (including the
  unknown-name usage error and the degraded-vs-clean asymmetry between categories),
  `--list`, schema-valid `--json` output (via `jsonschema`, asserting no
  `prescriptions` key for `verb: "check"`), `--version`/`--help` parity with warden's
  own CLI, and `path` positional forwarding.
  `unit/test_check_speed_budget.py` (1 test, deliberately real/unmocked — this is a
  wall-clock NFR-4 benchmark, not a code-path unit test) asserts `doctor check`
  completes within the documented speed budget against this monorepo's own root,
  skipped outside a monorepo checkout.

---

## Epic 2: Fleet Pulse (`doctor monitor --fleet`) — PENDING (0/3)

**Scope**: An atlas gather filter proven MCP-first/CLI-fallback on one Watch axis
(staleness), extended to all three named axes (staleness/cve/abandonment), then wired
into the verb with a default axis set and `--json`. **FR-4, FR-5, FR-9 (monitor verb),
AD-5, AD-6.** No code exists yet under `doctor.sources.atlas` or `doctor.cli_bridge`;
no test files exist for this epic.

| Story | Title | Status | Planned level | Planned coverage (from epics.md AC, not invented) |
|-------|-------|:------:|----------------|----------------------------------------------------|
| **2.1** | Atlas gather filter — staleness axis, MCP-first with CLI fallback (FR-5, AD-6) | not started | unit + meta | Unit: MCP-tool path normalizes to `Finding(source=Source.STALENESS_REPORT, ...)`; CLI-fallback path via a new `doctor.cli_bridge` module produces the *same* Finding shape for equivalent data (argv-as-list, bounded timeout, typed fail-Finding on subprocess failure per AD-5 — no raw traceback). Meta: a **new** sole-subprocess-site guard asserting `doctor.cli_bridge` is the only module in the package containing a `subprocess` call — same pattern `meta/test_sources_warden_no_subprocess.py` already established for AD-1, applied to AD-5. |
| **2.2** | cve and abandonment watch axes (FR-4) | not started | unit | Per-axis normalization tests for `--watch cve` (tagged `Source.CVE_WATCHER`) mirroring 2.1's MCP-first/CLI-fallback pattern; `--watch abandonment` composes `Source.FEEDSTOCK_HEALTH` (`stuck`/`bad`) + `Source.RELEASE_CADENCE` (`decelerating`/`silent`) into individually Source-tagged Findings — asserting a composite is never presented as a single instrument's output; a multi-axis invocation test (`--watch staleness,cve`) asserting every requested axis appears in one `DoctorReport`, still individually filterable. |
| **2.3** | `doctor monitor --fleet` CLI wiring, default axis set, `--json` (FR-9) | not started | unit | Mirrors `unit/test_cli_check.py`'s existing structure once it exists for `monitor`: no-`--watch`-flag runs the documented default axis set (staleness + cve, not every axis); `--json` produces a schema-valid `DoctorReport` (`verb: "monitor"`) with the same human/JSON parity guarantee Story 1.5 already proved for `check`; human-readable output supports filtering by `Finding.source`. |

**Acceptance target once built**: same density as Epic 1 — every AC in `epics.md`
Stories 2.1–2.3 gets at least one passing unit test; AD-5's sole-subprocess-site claim
gets a meta-test before any code merges that could violate it (matching how Epic 1
paired every AD/NFR claim with a meta-test at the same story it was introduced, not
retrofitted later).

---

## Epic 3: Diagnose & Prescribe (`doctor diagnose --prescribe`) — PENDING (0/4)

**Scope**: Partition every gathered Finding by actionability, rank the actionable
partition by severity × exploitability × blast-radius, name a root cause per
Prescription, then wire the verb with `--json`. Consumes Epic 1's `check` gather filter
and Epic 2's `atlas` gather filter as already-shipped inputs — adds zero new
subprocess/MCP calls of its own (AD-4: `doctor.prescribe` is a pure function). **FR-6,
FR-7, FR-8, FR-9 (diagnose verb), AD-4.** No code exists yet under `doctor.prescribe`;
no test files exist for this epic. Depends on Epic 2 shipping first for its atlas
inputs to exist, though the partition/rank logic itself only needs `list[Finding]` and
could in principle be built against Epic 1 findings alone.

| Story | Title | Status | Planned level | Planned coverage (from epics.md AC, not invented) |
|-------|-------|:------:|----------------|----------------------------------------------------|
| **3.1** | Partition findings by actionability (FR-6, AD-4) | not started | unit + meta | Unit: a mixed-Finding fixture (some fixable, one unfixed CVE) partitions into exactly one of `Partition.ACTIONABLE`/`BLOCKED`/`ACCEPTED_RISK` per Finding, with `sum(partition counts) == len(findings)` (no silent drop); a `blocked` Finding carries a human-readable reason ("no fix version published"), never omitted from output. Meta: a **new** pure-function guard asserting `doctor.prescribe` contains no `subprocess` import and no MCP-client import — mirrors `meta/test_sources_warden_no_subprocess.py`'s style, applied to AD-4's "zero calls of its own" claim. |
| **3.2** | Rank the actionable partition (FR-7, AD-4) | not started | unit | KEV-flagged Finding ranks above an equal-severity non-KEV Finding; higher-EPSS Finding ranks above a lower-EPSS Finding at equal severity; smaller upgrade-lag classification (patch < minor < major, reusing `behind-upstream`'s existing lag classification) breaks a severity+exploitability tie; every ranked `Prescription` carries a `rank_factors` object naming which signals fired (e.g. `{kev, epss, blast_radius}`) — never a bare integer. |
| **3.3** | Root-cause naming (FR-8) | not started | unit | A Prescription for a CVE Finding traceable to a staleness lag names that lag in `root_cause` ("upstream released a fix N versions ago"), not only the CVE ID; a Prescription for an engine-missing Finding (from Epic 1's `check` gather) has its `root_cause` templated from that Finding's own `evidence` field — no new NLP/inference layer, a pure template over already-structured evidence. |
| **3.4** | `doctor diagnose --target … --prescribe` CLI wiring, `--json` (FR-9) | not started | unit | `doctor diagnose --target <x>` (no `--prescribe`) gathers and reports Findings for the target without partitioning/ranking; `--prescribe` triggers the 3.1→3.2→3.3 pipeline; `--json` produces a schema-valid `DoctorReport` (`verb: "diagnose"`, `prescriptions` populated) with the same parity guarantee as `check`/`monitor`; a target with only `blocked`/`accepted-risk` Findings still lists them under `--prescribe` rather than reporting a misleadingly-clean empty result. |

**Acceptance target once built**: same density as Epic 1. 3.1's AD-4 purity claim gets
a meta-test at the same story it's introduced (not deferred), matching Epic 1's own
convention of pairing every AD/NFR claim with its guard immediately.

---

## Test Coverage Summary

| Level | Epic 1 (shipped) | Epic 2 (pending) | Epic 3 (pending) |
|-------|-------------------|--------------------|--------------------|
| **Unit** | 8 files, 176 `def test_` functions (193 collected — includes parametrization), all passing | 0 files — 3 stories planned | 0 files — 4 stories planned |
| **Meta** | 5 files (`test_verdict_sole_ownership`, `test_read_only_guard`, `test_no_warden_import`, `test_sources_warden_no_subprocess`, `test_env_hygiene_no_execution`), all passing | 0 files — 1 new guard planned (2.1, AD-5) | 0 files — 1 new guard planned (3.1, AD-4) |
| **Integration / E2E** | Not a separate level in this codebase (see "Test Levels In Use" above) — real-fixture cases live inside `tests/unit/` | same | same |

**Story-level test presence**: 5/12 stories (42%) have real, passing tests today.
7/12 (58%) have a stated plan and zero fabricated file names.

---

## Meta-Tests (Invariant Verification) — Real, Shipped

All five meta-tests are static AST scans (no code execution) and each positively
proves its own detector fires on a synthetic violation — none is a vacuous guard.

| File | Invariant | What it scans |
|------|-----------|----------------|
| `meta/test_verdict_sole_ownership.py` | AD-2 — only `verdict.py` owns the frozen exit-code literals `{0, 2, 130}` | Every module except `verdict.py`, for a bare exit-primitive call with a domain int literal, or an import/dereference of a `_`-private `verdict` name |
| `meta/test_read_only_guard.py` | NFR-1 — nothing writes outside a `tempfile`-scoped path | Every module, for `open(..., "w"/"a"/"x")`, `Path.write_text`/`write_bytes`, and `os`/`shutil` mutation calls |
| `meta/test_no_warden_import.py` | AD-3 — Doctor's taxonomy never imports warden's, except the one sanctioned gather filter | Every module except `sources/warden.py`, for an absolute or relative `pyforge.warden` import |
| `meta/test_sources_warden_no_subprocess.py` | AD-1 — the warden wrap is a library call, never a reimplementation | `sources/warden.py` only, for `subprocess`/shell-out calls or any import outside a closed allowlist (`__future__`, `pathlib`, `..models`, `pyforge.warden.engines`) |
| `meta/test_env_hygiene_no_execution.py` | The env-hygiene scanner treats source as untrusted data | `checks/env_hygiene.py` only, for `exec`/`eval`/`__import__` calls |

**Planned additions** (not yet built, named above at their owning story): a
sole-subprocess-site guard for `doctor.cli_bridge` (Story 2.1, AD-5) and a
zero-subprocess/zero-MCP-import guard for `doctor.prescribe` (Story 3.1, AD-4).

---

## Framework & Tooling

**Pytest** is the only test runner in use — no Playwright, no browser automation
(Doctor has no UX surface; `epics.md` states this explicitly: "N/A — non-interactive
CLI, same as `pyforge-warden`; no UI surface"). Run via the pixi task
`pyforge-doctor-test` (`pixi.toml` `[feature.pyforge-doctor.tasks]`):

```
pixi run -e pyforge-doctor pyforge-doctor-test
# -> pytest src/shared/packages/pyforge-doctor/tests -q
```

Confirmed green at time of writing: `193 passed` in ~16s, no `tests/integration/`,
no `tests/e2e/`, no `conftest.py`. Dependencies are lean by design (`pyproject.toml`):
runtime is `jsonschema` only, plus the optional `gate = ["pyforge-warden"]` extra
(AD-1) — no test-only dependency beyond pytest itself is declared.

---

## Readiness Checklist

- [x] All 12 stories defined in `epics.md`, mapped to FRs/ADs
- [x] Epic 1 (5 stories) — real test files exist and pass (193 tests, 13 files)
- [x] Meta-test invariants specified and shipped for every Epic-1 AD/NFR claim (AD-1,
      AD-2, AD-3, NFR-1)
- [x] Fixtures identified — 2 static JSON fixtures (`tests/fixtures/`), no
      `conftest.py`, no mock modules (none needed: warden is called live via
      monkeypatch, not mocked-and-forgotten)
- [x] Test levels documented as they actually exist (unit + meta only — no
      integration/e2e directories, and none planned)
- [ ] Epic 2 (3 stories) — `doctor.sources.atlas`, `doctor.cli_bridge` not yet built;
      no test files yet
- [ ] Epic 3 (4 stories) — `doctor.prescribe` not yet built; no test files yet
- [ ] New meta-test: `doctor.cli_bridge` sole-subprocess-site guard (Story 2.1, AD-5)
- [ ] New meta-test: `doctor.prescribe` zero-subprocess/zero-MCP-import guard
      (Story 3.1, AD-4)
- [ ] Coverage baseline recorded once Epics 2–3 ship (no baseline file exists yet —
      none is fabricated here)

---

**Status**: DRAFT — Epic 1 retrospectively documented and verified green; Epics 2–3
prospectively planned, zero code or tests written yet for either.

**Coverage Target**: Epic 1 — 5/5 stories with real passing tests (achieved). Epics
2–3 — 7/7 stories to reach the same unit+meta density Epic 1 shipped, before each
epic is marked done.

**Last updated**: 2026-08-02
