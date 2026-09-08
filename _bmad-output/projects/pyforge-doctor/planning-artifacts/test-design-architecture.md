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
---

# Test Design for Architecture: pyforge-doctor (Doctor)

**Purpose:** Architectural concerns, testability gaps, and NFR requirements for review by
the PyForge Guild's Architecture/Dev discipline. Contract between QA and Engineering on
what must be addressed — for Epic 20, Doctor's only undelivered surface — before that
epic's stories are dispatched.

**Date:** 2026-09-07
**Author:** rxm7706 (via `bmad-testarch-test-design` / TEA, autonomous run)
**Status:** Architecture Review Pending (Epic 20 scope only — Epics 1–19 already shipped and reviewed)
**Project:** pyforge-doctor
**PRD Reference:** `_bmad-output/projects/pyforge-doctor/planning-artifacts/prds/prd-pyforge-doctor-2026-07-25/prd.md`
**ADR Reference:** `_bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md`

---

## Executive Summary

**Scope:** This is a **retrospective + forward-looking** system-level test design for an
already-largely-shipped station. `pyforge-doctor` tracks 113 stories across 20 epics;
**108 are `done`** (Epics 1–19). The only undelivered surface is **Epic 20** ("Doctor reads
the whole suite and guards the estate's two blind spots" — 5 stories, 4 `backlog`,
1 `blocked` on a cross-station dependency). This document therefore does two
things: (1) names the testability strengths and residual carried debts of the shipped
94%, so Architecture/Dev knows what not to re-litigate, and (2) treats Epic 20 as the
actionable target of a real testability/risk review, since it is the one place a
pre-implementation gate still has leverage.

**Business Context** (from PRD §1 Vision): Doctor gives the PyForge factory one bedside
manner over health signal already scattered across `pyforge-warden` and `cf_atlas` — a
single `doctor` CLI (`check` / `monitor` / `diagnose`) that replaces "run five tools and
reconcile by hand" with one habit. It is an internal, single-operator/single-agent-consumer
tool (Marshal is the primary machine caller) — there is no external revenue or customer
surface; the "business impact" category (BUS) below concerns fleet-operator trust and
cross-station sequencing, not revenue.

**Architecture** (from the Spine): **Facade over existing instruments**, pipes-and-filters
(gather → normalize → partition/rank), with exactly one narrow, typed subprocess exception
(`doctor.cli_bridge`, AD-5/AD-12). Doctor's own code is coordination and ranking — it never
spawns a scan engine or database query that warden or cf_atlas doesn't already own. Its
`sources/` package has grown into the fleet's conformance-verdict home (15 modules,
14+ addressable dispatcher entries) under Charter §6's rule: **the station that owns an
artifact never grades it** — enforced structurally (AST-based non-import meta-tests), not
by policy alone.

**Expected Scale:** Single-operator internal tool; `doctor check`'s pre-flight path has an
explicit ~5-second speed budget (NFR-4/SM-C1) as its only real "scale" constraint — this is
a latency ceiling, not a throughput target.

**Risk Summary:**

- **Total risks**: 9 (grounded in the architecture spine's own named carried debts, PRD open
  questions, and Epic 20's not-yet-built stories — none invented)
- **High-priority (≥6)**: 1 risk requiring a decision before Epic 20's Story 20.2 ships
- **Test effort**: ~13 new test items (~0.5–1.5 weeks, 1 engineer) — scoped to Epic 20 plus
  3 carried-debt regression items; Epics 1–19's 108 stories keep their own already-shipped
  61-file `tests/{unit,meta}` suite unchanged

---

## Quick Guide

### 🚨 BLOCKERS - Team Must Decide (Can't Proceed Without)

**Pre-Implementation Critical Path** for Epic 20 only (Epics 1–19 have no open blockers):

1. **R-4: Story 20.2's render-HALT detector needs a conformance test, not just logic parity** —
   the detector must re-simulate `render_skill.py`'s `load_central_config()` layer-merge
   to find a key sitting at two different paths; without an AD-13-style AST-literal
   equality test pinning the simulation against the real resolver's behavior, the detector
   can drift silently and under-report the exact HALT class that stalled a live session on
   2026-09-06 (recommended owner: doctor dev, before Story 20.2 lands).
2. **R-9: The `DoctorReport.schema_version` bump policy is still an open question (PRD §8 Q4)
   while Epic 20 is about to add three new finding/evidence shapes into `schema_version=1`** —
   architecture must decide whether these are additive-compatible or require a bump before
   any of Epic 20's stories ship (recommended owner: doctor dev/architecture, one-time
   decision, blocks nothing else).
3. **R-6: Story 20.3's fail-open rule ("no ledger → ok") must not also cover "ledger present
   but malformed"** — the two cases need distinguishable test fixtures before the detector
   joins `detectors-ci` (recommended owner: doctor dev).

**What we need from team:** Resolve these 3 items before Epic 20 stories 20.2/20.3 are
dispatched to a build loop; 20.1/20.4/20.5 are unaffected and can proceed independently.

---

### ⚠️ HIGH PRIORITY - Team Should Validate (We Provide Recommendation, You Approve)

1. **R-1: AD-13's conformance test (`ACTIONABLE_STATUSES` vs. installed `bmad_loop`) cannot
   run in CI** — it runs only under `pixi run -e local-recipes test`, a known, already-accepted
   "missing observation plane" (spine's own words). Recommendation: keep re-running it at
   every `bmad-loop` version bump rather than treating the gap as closed; no new AD needed.
2. **R-5: Epic 20 adds three new network-touching sources on top of an already-tight 5-second
   check budget (NFR-4/SM-C1)** — recommend re-profiling (mirrors Story 6.1's precedent)
   once Epic 20 lands, the same discipline that caught the last budget regression.
3. **R-2/R-3: Two named carried debts from the architecture spine's own "Carried debts"
   section** (a duplicated AST alias-resolution helper across 3 meta-tests; atlas's
   label/JSON-shape coupling guarded by convention, not an assertion) — recommend folding
   the fix into Epic 20's own PR since it touches `sources/` anyway, not a new epic.

**What we need from team:** Review and approve (or defer with a recorded reason) — none of
these block Epic 20's dispatch on their own.

---

### 📋 INFO ONLY - Solutions Provided (Review, No Decisions Needed)

1. **Test strategy**: Unit + structural meta-tests (pytest), zero browser/contract-testing
   surface — Doctor is a non-interactive backend CLI (PRD §UX Design Requirements: "N/A").
   Every architectural invariant (AD-1..AD-13) already has a dedicated meta-test; Epic 20's
   3 new sources should each get one before joining `detectors`/`detectors-ci`, matching the
   epic's own stated boundary ("detectors join `detectors` only after their fixtures prove
   fail-open").
2. **Tooling**: `pytest` via `pixi run -e pyforge-doctor pyforge-doctor-test`; no k6, no
   Playwright, no Pact — none apply to this stack (confirmed by scan, not assumed).
3. **Tiered CI/CD**: local `pixi run … test` (every commit) → `detectors`/`detectors-ci`
   (read-side conformance, after fail-open is fixture-proven) → `platform-ci-local` (full
   workflow replay, ambient).
4. **Coverage**: ~13 new test items across P0–P3, scoped to Epic 20 + 3 carried-debt items —
   not a re-test of the 108 already-shipped, already-covered stories.
5. **Quality gates**: see QA doc; the fleet-wide constraint that supersedes all of them —
   **every Doctor finding stays advisory or a Warden input, never a second PR-gate verdict**
   (Charter §6; Unifying Strategy; repeated verbatim across Epics 5, 6, 17, 20).

**What we need from team:** Review and acknowledge.

---

## For Architects and Devs - Open Topics 👷

### Risk Assessment

**Total risks identified**: 9 (1 high-priority score ≥6, 6 medium, 2 low)

#### High-Priority Risks (Score ≥6) - IMMEDIATE ATTENTION

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner | Timeline |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **R-4** | **TECH** | Story 20.2's render-HALT detector re-simulates `render_skill.py`'s multi-layer config merge to find a key sitting at two paths; without a conformance test tying the simulation to the real resolver, it can silently drift and miss the exact HALT class that stalled a live 2026-09-06 session | 2 | 3 | **6** | Ship an AD-13-style AST-based equality/behavior-parity test asserting the detector's merge simulation matches `load_central_config()`'s real output on both the clean fixture and a planted two-path-key fixture | doctor dev | Before Story 20.2 lands |

#### Medium-Priority Risks (Score 3-5)

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-1 | TECH | AD-13's `ACTIONABLE_STATUSES` conformance test cannot run in CI (no `bmad_loop` installed there) — divergence is caught only at `pixi run … test` time, not push time | 2 | 2 | 4 | Already accepted/documented as a named "missing observation plane"; re-run the check at every `bmad-loop` version bump, don't let the gap silently widen | doctor dev |
| R-2 | TECH | Carried debt: the AST alias-resolution helper used by non-import meta-tests (`test_no_warden_import.py`, `test_sources_warden_no_subprocess.py`, `test_cli_bridge_sole_subprocess.py`) is duplicated rather than shared — a fix to alias-detection logic must land 3 times | 2 | 2 | 4 | Extract a shared helper into `pyforge-testing-kit` (already the home for shared mock families per the spine's own note) while Epic 20 is touching `sources/` anyway | doctor dev |
| R-3 | TECH | Carried debt: `doctor.sources.atlas`'s coupling to cf_atlas's MCP tool label/JSON shape is guarded by convention, not a label-subset smoke assertion — a renamed atlas label fails at call time, not at review time | 1 | 2 | **2→4*** | Add one label-subset smoke assertion per gather filter (existing + Epic 20's new ones). *Raised past the raw 1×2 product because Epic 20 adds 3 more remote-shape-coupled sources, raising recurrence probability. | doctor dev |
| R-5 | OPS/PERF | Epic 20 adds 3 new network-touching sources (suite-drift roster resolution, render-HALT config read, frozen-path ledger read) on top of NFR-4's already-tight 5-second `doctor check` budget; no Epic 20 story explicitly re-profiles it | 2 | 2 | 4 | Re-run the Story 6.1 speed-budget benchmark (`tests/unit/test_check_speed_budget.py`) after Epic 20 lands; the benchmark's own minimum-findings-count assertion already guards against "broken-and-therefore-fast" | doctor dev |
| R-6 | OPS | Story 20.3's fail-open rule ("absent ledger → ok, pre-cutover") risks over-generalizing to "any unreadable ledger → ok", masking a genuinely malformed `docs/foundry/manifest.*` | 2 | 2 | 4 | Fixture both cases separately: absent path (ok) vs. present-but-unparseable path (warn, names the parse error) — never conflate the two | doctor dev |
| R-9 | DATA | `DoctorReport.schema_version` bump policy is still an open question (PRD §8 Q4) while Epic 20 is about to add 3 new finding/evidence shapes under the existing `schema_version=1` | 2 | 2 | 4 | Decide once, in Epic 20's first story: additive shapes stay under `1` (documented precedent — every `sources/` addition since Epic 6 has done this); a breaking shape change bumps to `2` with a consumer-compat test | doctor dev / architecture |

#### Low-Priority Risks (Score 1-2)

| Risk ID | Category | Description | Probability | Impact | Score | Action |
| --- | --- | --- | --- | --- | --- | --- |
| R-7 | SEC | FR-3's credential-hygiene generalization boundary (PRD §8 Q2) — already shipped as the general unconditional-injection scanner per the PRD's 2026-08-26 currency reconciliation; residual risk is only "a genuinely new credential-env-var shape the current AST scan doesn't recognize yet" | 1 | 2 | 2 | Monitor: add a fixture whenever a new credential-injection pattern is found in practice, same discipline `JFROG_API_KEY` set |
| R-8 | BUS | Story 20.4 (routing `bmad-os-root-cause-analysis` into the doctor persona) depends on steward Story 46.2, which is itself `blocked` in that station's ledger — a cross-station sequencing risk, not a doctor-internal one | 1 | 2 | 2 | Re-verify steward 46.2's landed `SKILL.md` shape before editing `bmad-agent-doctor/SKILL.md`'s routing line; do not pre-author against an assumed shape |

#### Risk Category Legend

- **TECH**: Technical/Architecture (flaws, integration, scalability)
- **SEC**: Security (access controls, auth, data exposure)
- **PERF**: Performance (SLA violations, degradation, resource limits)
- **DATA**: Data Integrity (loss, corruption, inconsistency)
- **BUS**: Business Impact (here: fleet-operator trust / cross-station sequencing, not revenue)
- **OPS**: Operations (deployment, config, monitoring)

---

### NFR Testability Requirements

**Purpose:** Capture what architecture must provide so NFR validation can be automated —
planning guidance, not final evidence assessment (that's `nfr-assess`, after Epic 20 ships).
Doctor is a backend CLI; the categories below are adapted from the 8-category ADR Quality
Readiness Checklist to the categories that actually apply to a facade/CLI over subprocess +
MCP + AST-scan sources (Scalability/DR/Deployability/QoE are N/A — no service to scale,
fail over, or deploy with zero downtime; it's a console script).

| NFR Category | Threshold / Requirement | Current Design Support | Gap / Decision Needed | Planned Evidence |
| --- | --- | --- | --- | --- |
| Read-only / non-mutating (NFR-1) | No module under `pyforge.doctor` writes outside a `tempfile`-scoped path or mutates a scanned tree | **Supported** — `tests/meta/test_read_only_guard.py` already enforces this fleet-wide | None — Epic 20's 3 new sources must be added to this guard's scope, not a new mechanism | Existing meta-test, extended |
| Operability exit-code contract (NFR-2) | `check`/`monitor` exit codes ∈ `{0,2,130}`, never warden's policy-gate `1` | **Supported** — `tests/meta/test_verdict_narrows_warden.py`, `test_verdict_sole_ownership.py` | None | Existing meta-tests |
| Bounded, typed subprocess safety (NFR-3) | The one narrow `cli_bridge` subprocess site: argv-as-list, bounded timeout, typed `Finding(status=fail)` never a raw traceback | **Supported** — `tests/meta/test_cli_bridge_sole_subprocess.py` | Carried debt (R-2): the guard's alias-resolution logic is duplicated, not shared | Existing meta-test + R-2's refactor |
| Pre-flight speed budget (NFR-4 / SM-C1, ~5s) | `doctor check`'s default run stays fast enough to be habitual | **Supported today** — `tests/unit/test_check_speed_budget.py`, previously re-profiled once (Story 6.1) | **Gap (R-5)**: not yet re-profiled against Epic 20's 3 new network-touching sources | Re-run the existing benchmark post-Epic-20 |
| Schema-versioned machine contract (NFR-5) | `DoctorReport.schema_version` starts at 1, versioned on breaking change | **Supported** — shipped at `1` since Epic 1 | **Decision needed (R-9)**: does Epic 20's 3 new shapes stay additive under `1`? | A one-time architecture decision + a consumer-compat fixture if bumped |
| Fail-open network discipline (cross-cutting, not a numbered NFR but load-bearing since Story 10.2) | Every network-touching source (registry/GitHub/npm lookups) degrades to *no Finding, no exception* when unreachable | **Supported per-source** (Stories 10.2, 14.1, 15.1/15.2, 16.1, 19.1 each implement it) but **no single meta-test generalizes the pattern** the way AD-5's sole-subprocess-site guard does | **Gap**: a new Epic 20 source could accidentally omit the try/except and no structural test would catch it | Recommend a new meta-test enumerating every "network-touching" source module and asserting each has a bounded, exception-swallowing wrapper — same shape as the sole-subprocess-site guard |
| Charter §6 non-self-judgment (FR-14/FR-15, structural) | No Doctor source imports the station/subsystem it judges | **Supported** — AD-11 (`sources/marshal.py`), AD-13 (`sources/deps.py`), plus per-source meta-tests (`test_no_warden_import.py`, `test_source_independence.py`) | **Actionable for Epic 20**: Stories 20.2 (render-HALT) and 20.3 (frozen-path) are two brand-new judging sources — each needs its own non-import/no-execution meta-test before joining `detectors`/`detectors-ci`, exactly as the epic's own text already requires | Two new meta-tests, one per new source |

**Unknown thresholds:** None outstanding for the shipped surface. Epic 20 carries one
open decision (R-9, schema-version policy) that is a decision, not an unknown threshold.

**Assessment boundary:** Final PASS/CONCERNS/FAIL status belongs in `nfr-assess` after
Epic 20's implementation evidence exists — this document plans validation, it does not
render a verdict.

---

### Testability Concerns and Architectural Gaps

**No critical (blocking) testability concerns identified.** Doctor is an unusually
testability-mature system for its size: 61 test files (`tests/unit/` + `tests/meta/`)
against a 15-module `sources/` package, with a dedicated structural meta-test for every
one of AD-1 through AD-13. The gaps below are real but non-blocking improvements, not
"architecture must fix this before QA can proceed" items.

#### 1. Blockers to Fast Feedback (WHAT WE NEED FROM ARCHITECTURE)

| Concern | Impact | What Architecture Must Provide | Owner | Timeline |
| --- | --- | --- | --- | --- |
| **No generalized fail-open meta-test** (see NFR table) | A future network-touching source could ship without the fail-open guard and no structural test would catch it until it breaks in the field | One meta-test enumerating every source module tagged as network-touching and asserting a bounded try/except wrapper exists | doctor dev | Alongside Epic 20 |
| **Schema-version bump policy undecided (R-9)** | Epic 20's 3 new finding shapes ship into `schema_version=1` without an explicit compatibility ruling | A one-paragraph architecture decision (additive-only vs. bump threshold) | doctor dev / architecture | Before Epic 20's first story lands |

#### 2. Architectural Improvements Needed (WHAT SHOULD BE CHANGED)

1. **Shared AST alias-resolution helper (R-2)**
   - **Current problem**: three separate meta-tests (`test_no_warden_import.py`,
     `test_sources_warden_no_subprocess.py`, `test_cli_bridge_sole_subprocess.py`)
     each carry their own copy of alias-aware import/call detection.
   - **Required change**: extract one shared helper, most naturally into
     `pyforge-testing-kit` (already the fleet's home for shared mock families per the
     spine's own "Carried debts" note).
   - **Impact if not fixed**: a fix to alias-detection semantics (e.g. a new import
     style Python adds) must be applied and re-verified three times independently.
   - **Owner**: doctor dev. **Timeline**: opportunistic, alongside Epic 20's `sources/`
     changes.

2. **Atlas label/JSON-shape coupling by convention only (R-3)**
   - **Current problem**: `doctor.sources.atlas` assumes cf_atlas's MCP tool response
     labels/shapes are stable; nothing asserts it.
   - **Required change**: one label-subset smoke assertion per gather filter (existing
     `staleness`/`cve`/`abandonment`/`adoption` axes, plus Epic 20's new suite-roster
     probe).
   - **Impact if not fixed**: a cf_atlas-side rename surfaces as a runtime `KeyError`/
     silent misparse instead of a reviewable test failure.
   - **Owner**: doctor dev. **Timeline**: opportunistic.

---

### Testability Assessment Summary

**📊 CURRENT STATE - FYI**

#### What Works Well

- ✅ **Every architectural invariant has a structural, not policy-only, test.** AD-1
  (`test_sources_warden_no_subprocess.py`), AD-2 (`test_verdict_narrows_warden.py`,
  `test_verdict_sole_ownership.py`), AD-4 (`test_prescribe_pure_function.py`), AD-5/AD-12
  (`test_cli_bridge_sole_subprocess.py`), AD-6 (`test_atlas_sole_mcp_import.py`), AD-7
  (`test_score_pure_function.py`), AD-11/AD-13 (`test_source_independence.py`,
  `test_sources_deps_forward_dependency.py`) — 14 meta-test files, one class of invariant
  each. This is precisely the "check the invariant, don't just declare it" discipline
  the ADR checklist's §1 Testability & Automation category asks for.
- ✅ **The speed-budget precedent is proven, not aspirational.** Story 6.1 already
  re-profiled `doctor check` once, after Epic 6's source additions threatened NFR-4 —
  and the benchmark asserts a *minimum* findings count so "broken and therefore fast"
  cannot pass. Epic 20 has a working precedent to repeat (R-5's mitigation).
- ✅ **Fail-open discipline is consistent across every network-touching source shipped
  so far** (Stories 10.2, 14.1, 15.1/15.2, 16.1, 19.1) — the gap named above (no
  generalized meta-test) is about making an already-consistent pattern structurally
  enforced, not about inconsistent behavior today.
- ✅ **108 of 113 stories (Epics 1–19) are `done`** with their own tests already in the
  repo — this test design correctly does not re-litigate that surface.

#### Accepted Trade-offs (No Action Required)

- **AD-13's conformance test cannot run in CI (R-1)** — accepted, documented, and
  understood as the same "missing observation plane" class as `dashboard_drift`/
  `loop_stall`/`unpushed_work`. Not revisited here; re-verify at each `bmad-loop` bump.
- **Per-call MCP session spawn (deliberate, unmeasured)** and **`_default_repo_root`'s
  `parents[8]` fallback** — both named in the spine's own "Carried debts" as accepted-for-now,
  neither reopened by Epic 20's scope. `_default_repo_root`'s fallback gets one boundary
  test in the coverage plan (P3) since it's cheap and Epic 20 touches adjacent code, not
  because it is newly risky.

---

### Risk Mitigation Plans (High-Priority Risks ≥6)

**Purpose**: Detailed mitigation strategy for the one score-6 risk. This risk MUST be
addressed before Story 20.2 ships.

#### R-4: Story 20.2's render-HALT detector needs a conformance test (Score: 6) - HIGH

**Mitigation Strategy:**

1. Before writing `sources/bmad_method.py`'s (or a sibling `bmad_config.py`'s)
   layer-merge simulation, read `render_skill.py`'s `load_central_config()` and
   `_find_config_values()` end to end — the detector must reproduce the *same* merge
   order (base → team → user, deep-merge tables) the real resolver uses, not an
   approximation.
2. Write the fixture pair first: (a) today's tree, single-path pins (`[core]
   communication_language`, `[modules.bmm] user_skill_level`) → detector reports `ok`;
   (b) a planted `[core] user_skill_level` beside `[modules.bmm] user_skill_level` →
   detector reports `warn`, naming the key and both paths (mirrors the epic's own
   Given/When/Then verbatim).
3. Add the AD-13-style conformance assertion: parse the detector's merge simulation
   logic (or its output on a shared fixture set) and assert it matches
   `render_skill.py`'s actual `load_central_config()` output — set/dict equality, not
   membership, per AD-13's own three preserved properties (fail don't skip; equality
   not subset; literal not computed).
4. Confirm a missing layer file is fail-open (`ok`, per the epic's own text), tested
   separately from the two-path-key case.

**Owner:** doctor dev
**Timeline:** Before Story 20.2 is dispatched to a build loop
**Status:** Planned
**Verification:** The conformance test itself is the verification artifact — it fails
loudly if the simulation and the real resolver ever diverge, the same guarantee AD-13
already gives `ACTIONABLE_STATUSES`.

---

### Assumptions and Dependencies

#### Assumptions

1. Epic 20's 5 stories (20.1–20.5) are the complete remaining scope for pyforge-doctor
   as of this run — no epic beyond 20 exists in `epics.md` at this stamp (2026-09-06
   `currency_review`).
2. The `_bmad/tea/config.yaml` substitution used for this run (`{output_folder}` →
   `_bmad-output/projects/pyforge-doctor`) is a known, disclosed workaround, not a
   silent guess — a sibling story already documented the same gap fleet-wide.
3. `user_name` resolved to `rxm7706` via git config, since no `_bmad/config.user.toml`
   exists in this worktree to resolve TEA's own `{config_source}:user_name` key.

#### Dependencies

1. Steward Story 46.2 (SKF skill install for `bmad-os-root-cause-analysis`) — required
   by doctor Story 20.4; currently `blocked` in the shared ledger convention (R-8).
2. `docs/foundry/manifest.*` capability ledger's real shape — required by Story 20.3;
   not yet observed live in this repo (pre-cutover), so its fixture must be
   hand-constructed from the cutover spine's own documented shape (`fnd:AD-11`/`fnd:AD-22`).

#### Risks to Plan

- **Risk**: This document's risk register may miss a risk the actual Epic 20
  implementation surfaces (e.g. a GitHub/npm rate-limit interaction none of the
  Given/When/Then clauses name explicitly).
  - **Impact**: A real risk ships untested.
  - **Contingency**: Epic 20's own stated boundary — "detectors join `detectors` only
    after their fixtures prove fail-open" — is itself a backstop gate independent of
    this document's completeness.

---

**End of Architecture Document**

**Next Steps for Architecture Team:**

1. Review Quick Guide (🚨/⚠️/📋) and decide the 3 blockers (R-4, R-9, R-6) before
   Story 20.2/20.3 dispatch.
2. Confirm R-1/R-2/R-3/R-5 recommendations (no new AD required for any of them).
3. Validate the Dependencies section (steward 46.2's real landed shape; the foundry
   manifest's real schema once it exists).

**Next Steps for QA Team:**

1. Refer to the companion QA doc (`test-design-qa.md`) for the P0–P3 coverage plan.
2. Begin fixture construction for Story 20.1/20.2/20.3 (all three fixtures are already
   named concretely in `epics.md`'s own Given/When/Then clauses — no invention needed).
3. No test infrastructure setup is required beyond the existing `pixi run -e
   pyforge-doctor pyforge-doctor-test` harness — this is a backend CLI with an
   established pytest suite, not a new environment.
