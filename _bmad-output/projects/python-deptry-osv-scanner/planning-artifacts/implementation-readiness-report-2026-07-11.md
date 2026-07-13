---
stepsCompleted:
  - step-01-document-discovery
  - step-02-prd-analysis
  - step-03-epic-coverage-validation
  - step-04-ux-alignment
  - step-05-epic-quality-review
  - step-06-final-assessment
documentsIncluded:
  prd: planning-artifacts/prd.md
  architecture: null
  epics: null
  ux: null
assessmentScope: prd-only (pre-architecture)
date: 2026-07-11
---

# Implementation Readiness Assessment Report

**Date:** 2026-07-11
**Project:** python-deptry-osv-scanner

## Document Inventory

| Type | Status | File |
|---|---|---|
| **PRD** | ✅ present (whole, no duplicates) | `planning-artifacts/prd.md` (~601 lines, 83.8 KB) |
| Architecture | ⚠️ not yet created | — |
| Epics & Stories | ⚠️ not yet created | — |
| UX Design | ⏭ N/A (non-interactive CI CLI; UX skipped in PRD) | — |

**Assessment scope:** PRD-only (pre-architecture readiness). Architecture, Epics, and UX are the *expected next-phase outputs*, not defects. Steps 03 (epic coverage), 04 (UX alignment), and 05 (epic quality) have no artifacts to assess and will be reported N/A; Step 02 (PRD analysis) is the substantive validation; Step 06 reframes the verdict as "ready to proceed to architecture?".

**Duplicates/conflicts:** none.

## PRD Analysis

*Extracted from the canonical FR1–FR31 contract + the NFR set. (The PRD's Requirement-ID crosswalk supersedes all spec-era `FRn` labels used in the narrative — noted for the architect.)*

### Functional Requirements (31)

**A. Manifest Discovery, Ingestion & Extraction**
- FR1 — discover + classify candidate manifests under a path; deterministic selection/precedence; report the resolved scan set (coverage denominator).
- FR2 — classify each dependency **source section** (pixi `[dependencies]` vs `[pypi-dependencies]`; env.yml conda vs `- pip:`) → correct extractor.
- FR3 — extract deps from conda/pixi **source** manifests without a resolved environment.
- FR4 — delegate to engines' native parsers for PyPI inputs (no bespoke parsing).
- FR5 — best-effort templating/selector eval; degrade to name-only+marked, never fail.
- FR6 — per manifest, distinguish "no deps present" vs "deps present but unresolved."
- FR7 — keep per-ecosystem attribution; no silent cross-ecosystem merge.

**B. Dependency-Hygiene** — FR8 hygiene findings (unused/missing/transitive/misplaced), PyPI+conda · FR9 honor `[tool.deptry]` ignores.

**C. Vulnerability** — FR10 vuln findings (advisory/affected-fixed/severity), actionable · FR11 offline/air-gapped DB, offline-by-default, records source+timestamp · FR12 detect **stale DB** → degrade verdict, never confident-clean · FR13 unresolved version → **vulnerability-indeterminate** (range-vs-genuinely-unresolved).

**D. Honest Coverage & Reporting** — FR14 schema-validated report (status/severity/schema_version/coverage/error_kind) · FR15 **split hygiene vs vuln coverage** · FR16 partial coverage → qualified verdict, never bare "clean" · FR17 human + machine report, **every blocking finding actionable**.

**E. Policy Gate & Verdict** — FR18 gate on content+severity, default critical · FR19 minimum coverage-floor gate (default OFF) · FR20 verdict-composition (error-dominates lattice + separate exit) · FR21 detect engine presence/version + typed error_kinds routed to owner, never silent PASS · FR22 no-meaningful-scan → non-passing, never clean · FR23 warn-only mode.

**F. Waivers & Bypass** — FR24 auditable expiring waiver (reason/authorizer/expiry), read-not-written · FR25 re-block on expiry + flag for review · FR26 validate waiver schema, reject malformed/malicious.

**G. SBOM & Machine Contract** — FR27 CycloneDX SBOM (source-registry purls, self-declared partiality) · FR28 stable exit-code contract.

**H. CLI Operation & Configuration** — FR29 one non-interactive command → one exit code · FR30 dual `[tool.python-deptry-osv-scanner]` config (pyproject+pixi, per-key precedence) · FR31 `--version`/`--help` stable contract.

**Total FRs: 31.**

### Non-Functional Requirements (22)

- **C0 — Gate-Integrity invariant** (cross-cutting acceptance property): never false-green; N adversarial fixtures → 0 exit-0.
- **Reliability (5):** NFR-R1 corpus 0 uncaught exceptions (~1,950 files) · R2 ratcheted unparseable-rate baseline · R3a no repo/host mutation · R3b two-tier determinism (decision-deterministic default; byte-identical opt-in) · R5 bounded engine timeout.
- **Security (8):** S1 no code execution (AST denylist + no template render) · S2 no silent egress (socket guard) · S3 waiver untrusted + least-privilege · S4 no repo writes + secure temp · S5 ReDoS/resource bound (line-bound + non-nested quantifiers + decompression bound) · S6 engine-input purity (no requirements/argv injection) · S7 output neutralization (schema-aware encoder, purl percent-encode) · S8 trusted-input integrity (fresh+authentic DB, stale→fail-loud).
- **Performance (3):** NFR-P-warm (overhead ≤ ~2s p95 on the corpus, engines-stubbed) · P-cold (cacheable first-run DB, air-gap pre-provisioned) · P-concurrency (engines parallel, no shared state, O(project) not O(fleet)).
- **Interoperability (3):** I1 schema conformance (report JSON schema, CycloneDX 1.6, purl) · I2 schema-version field + frozen exit enum `{0,1,2,130}` · I3 machine-output purity (stdout = one doc or empty).
- **Usability (2):** U1 actionable diagnostics (fail-with-a-fix) · U2 safe-by-default + warn-only on-ramp.
- **Portability (1):** C1 Python ≥ 3.12; engines on PATH in a tested version range (fail-loud out-of-range); pixi ≥ 0.72.2.

**Total NFRs: 22.** (Accessibility deliberately excluded — non-interactive CLI.)

### Additional Requirements & Constraints
- **Hard constraints:** stdlib-only extraction (`tomllib` + `re`, AST-enforced); NFR3 never-writes-repo; offline-first vuln data; single-release v1 (epics E1–E4).
- **Config:** dual TOML `[tool.python-deptry-osv-scanner]`; waiver file `.python-deptry-osv-scanner-waivers.yaml` (read-only by scan; `--bypass` stanza emitted for the human to commit).
- **Deferred backlog (Growth):** KEV gate tier · new-findings-only baseline ratchet · SARIF · cf_atlas promotion · P6/J7 audit retrieval · per-section severity · EPSS.
- **10 consolidated Architecture Open Questions** (in the PRD): 3 blocking — deptry-severity→verdict-lattice mapping (Gap A), ComplianceReport↔CycloneDX shared-inventory model (Gap B), osv name-only-input contract + offline-DB provisioning/trust-anchor (Gap C).

### PRD Completeness Assessment (initial)
**Strong.** The traceability chain (Vision → Success Criteria → 9 Journeys → FR1–31 → NFR set) is intact and was adversarially stress-tested at every major step ([A] elicitation + [P] party-mode). FRs are at capability altitude and testable; NFRs are stated as **enforced, assertable mechanisms** with metrics (not vague quality claims). The safety-critical spine (C0 → FR18/FR21/FR22 → false-green=0) is airtight. **Gaps are not PRD defects but downstream-phase items:** the 3 blocking open questions are correctly deferred to architecture (they *gate design*, not the PRD), and Architecture/Epics/Stories are the expected next outputs. One residual watch item surfaced in traceability review: **FR30 (dual-config) has no owning NFR** for its input-contract stability (flagged in the PRD's open-questions "owners to assign").

## Epic Coverage Validation

**Status: N/A — epics/stories not yet created** (the expected output of the `bmad-create-epics-and-stories` phase, which follows architecture).

### Coverage Statistics
- Total PRD FRs: **31**
- FRs covered in epics: **0** (no epics document exists)
- Coverage percentage: **0% — pending epic decomposition, not a defect**

### Assessment
All 31 FRs are currently **awaiting epic/story decomposition**. This is the correct state for a pre-architecture readiness check — FR→epic traceability cannot exist before epics are authored. The PRD does pre-scope the work into **epics E1–E4** (E1 manifest bridge, E2/E3 dual extraction, E4 honest report + gate) and pre-maps journeys→FRs, so the decomposition has a clear starting structure. When epics are created (post-architecture), re-run this check to validate that every FR1–FR31 maps to at least one story — with particular attention to the connective-tissue FRs added late (FR1 discovery, FR2 routing, FR7 non-merge) and the cross-cutting NFR **C0** guard suite, which must be enforced by acceptance tests across multiple stories rather than owned by a single one.

## UX Alignment Assessment

**UX Document Status: Not Found — and correctly so (UX is NOT implied).**

The PRD classifies this as a non-interactive `cli_tool` whose primary consumer is a CI pipeline: "no public SDK/IDE surface," no web/mobile/interactive components, accessibility explicitly excluded. There is no user-interface to design. UX design was deliberately skipped during PRD authoring for this reason.

### Alignment Issues
None. The only *human-facing* surface is the CLI's text summary + exit code, and that affordance is already owned at the requirement level — **not** as a UX artifact but as functional/quality requirements:
- **NFR-U1 (actionable diagnostics)** — every non-zero exit names the package + finding + manifest location + remediation ("fail with a fix, not just a red X").
- **NFR-U2 (safe-by-default + warn-only on-ramp)** — the day-one adoption experience (the closest thing to "UX" here) is a stated requirement, tied to the anti-metric.
- **FR17** — human-readable summary + machine-readable report; **FR31** — `--version`/`--help`.

### Warnings
None. Absence of a UX document is **not** a gap for this product type; flagging it would be a false positive.

## Epic Quality Review

**Status: N/A — epics/stories not yet created.** Cannot review artifacts that don't exist. Instead, three **forward-looking quality flags** for the `bmad-create-epics-and-stories` phase (derived from the PRD's structure — heed these to avoid the exact violations this step exists to catch):

### 🟠 Flag 1 — E1–E4 as pre-scoped are TECHNICAL layers, not user-value epics
The PRD pre-scopes work as **E1 (manifest bridge) / E2–E3 (dual extraction) / E4 (report + gate)** — these are *horizontal architectural layers*, and this review step flags "technical epics with no user value" as a **critical** violation. When decomposing, **either** reframe to user outcomes **or** organize by **vertical slices** so each epic ships end-to-end value, e.g.:
- "Scan a PyPI project end-to-end (delegate + unified gate)" — J2
- "Scan a conda/pixi source manifest end-to-end (the wedge)" — J1
- "Gate policy + auditable waivers" — J4/J9
- "SBOM + machine contract" — J5
Map E1–E4 *across* those slices rather than shipping E1 as a standalone epic with no user-visible outcome.

### 🟠 Flag 2 — Sequencing / forward-dependency risk on the connective-tissue FRs
**FR1 (discovery) and FR2 (per-section routing)** are foundational — every extraction FR depends on them. Ensure the first vertical slice establishes them (and the `_engine_env()` normalization helper + the pure-JSON stdout seam, which Amelia flagged as "cheap-now, ruinous-to-retrofit") so later stories don't forward-reference un-built infrastructure.

### 🟠 Flag 3 — Cross-cutting invariants can't be owned by one story
**C0 (never false-green)** and the **NFR-S\* security suite** (ReDoS bound, output neutralization, engine-input purity, stale-DB integrity) are properties that must hold across *every* slice. Model them as **acceptance-test gates applied to each story**, not as a single "do security" story — otherwise they'll be deferred and the cardinal rule erodes. The **corpus-conformance ratchet (J8/NFR-R1/R2)** is likewise a standing CI gate, not a one-time story.

### Greenfield setup note
Greenfield project; a scaffold already exists at `src/shared/packages/python-deptry-osv-scanner/` (pixi build member, cli stub, 2 smoke tests green). The first story is *complete-the-scaffold*, not *create-from-template* — lighter than a typical greenfield Story 1.1.

## Summary and Recommendations

### Overall Readiness Status

Two-level verdict (this was a pre-architecture, PRD-only assessment):

- **PRD readiness → ✅ READY** (to proceed to architecture). The PRD is complete, internally reconciled (one canonical FR1–FR31 ID space, no contradictions), traceable end-to-end (Vision → Success → 9 Journeys → 31 FRs → 22 NFRs), and every major section was adversarially stress-tested. The safety-critical spine (C0 → FR18/FR21/FR22 → false-green = 0) is airtight.
- **Full implementation readiness → ⛔ NOT YET** — and *correctly so*: Architecture, Epics, and Stories do not exist. These are the **required next artifacts**, not defects. There is nothing to implement against until they are authored.

### Critical Issues Requiring Action (before implementation — all are next-phase, none are PRD defects)

1. **[BLOCKING for architecture] 3 open questions that gate E4 design** — resolve in `bmad-create-architecture` *before* building the report engine:
   - **Gap A — deptry-severity → verdict-lattice mapping** (the sharpest): whether a hygiene finding can reach `policy-violation`/exit-1 or is capped at `warn`. The two models yield different exit-code state machines; FR20/E4 sit on top of it. *Recommended default to confirm: hygiene = a separate `warn`-axis.*
   - **Gap B — ComplianceReport ↔ CycloneDX shared-inventory model** (the spine of E4; "BOM count == inventory count" implies a shared object never named).
   - **Gap C — osv name-only/range input contract + offline-DB provisioning/trust-anchor** (OD2, the #1 complexity hotspot).
2. **[Assign in architecture] FR30 (dual-config) has no owning NFR** for its input-contract stability (config-key precedence/forward-compat live only as CLI-section prose ACs).
3. **[Heed at epic-decomposition] Reframe E1–E4 from technical layers to vertical slices** so each epic ships end-to-end user value (Epic-Quality Flag 1); establish FR1/FR2 + the engine-env/pure-JSON seams first (Flag 2); model C0 + the NFR-S\* suite as per-story acceptance gates, not a single story (Flag 3).

### Recommended Next Steps

1. **`bmad-create-architecture`** — start from the PRD's **§ Architecture Open Questions (consolidated)**; resolve the 3 blocking gaps (A/B/C) first, and assign FR30's stability owner.
2. **`bmad-create-epics-and-stories`** — vertical-slice framing (per Epic-Quality flags); pre-map FR1–FR31 → stories.
3. **Re-run `bmad-check-implementation-readiness`** once epics exist — then Steps 3 (epic coverage), 4 (UX, will stay N/A), and 5 (epic quality) have artifacts to assess and this becomes a full go/no-go.
4. **Commit** the completed PRD + this readiness report (both are tracked Tier-2 planning artifacts) on branch `claude/python-deptry-osv-scanner`.

### Final Note

This assessment found **0 PRD defects** and **7 forward-looking items** across 3 categories (3 architecture-blocking open questions, 1 requirement-ownership gap, 3 epic-decomposition flags) — none blocking the PRD itself, all owned by the next two phases. **The PRD is cleared to proceed to architecture.**

---
**Assessor:** `bmad-check-implementation-readiness` (PRD-only scope) · **Date:** 2026-07-11 · **Verdict:** PRD READY → architecture; full implementation readiness pending architecture + epics.
