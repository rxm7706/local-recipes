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
  architecture: planning-artifacts/architecture.md
  epics: planning-artifacts/epics.md
  ux: null (N/A by design — non-interactive CI CLI)
assessmentScope: full go/no-go (PRD + architecture + epics; re-run of the 2026-07-11 PRD-only pass)
priorReport: planning-artifacts/implementation-readiness-report-2026-07-11.md (preserved)
date: 2026-07-12
---

# Implementation Readiness Assessment Report

**Date:** 2026-07-12
**Project:** python-deptry-osv-scanner

## Document Inventory

| Type | Status | File |
|---|---|---|
| **PRD** | ✅ present (whole, no duplicates) | `planning-artifacts/prd.md` (92.5 KB, 2026-07-12 — post-architecture + Phase-0-review reconciliation callouts) |
| **Architecture** | ✅ present (whole, no duplicates) | `planning-artifacts/architecture.md` (36.4 KB, 2026-07-12 — status: complete; 7→4 exit projection) |
| **Epics & Stories** | ✅ present (whole, no duplicates) | `planning-artifacts/epics.md` (39.8 KB, 2026-07-12 — 5 vertical-slice epics / 20 stories, post-Tier-1 corrections) |
| UX Design | ⏭ N/A by design (non-interactive CI CLI; confirmed by the 2026-07-11 report) | — |

**Supplementary context:** the prior PRD-only report (`implementation-readiness-report-2026-07-11.md`, preserved) and the Tier-1-reconciled intake spec (`docs/specs/python-deptry-osv-scanner.md`, 2026-07-12) are used as cross-artifact alignment references. Phase-0 deep-review context: gist `326be5f25e702e0fcce343046c70a6b2`; Tier-1 fixes landed as `33010ac0af`.

**Duplicates/conflicts:** none. **Missing documents:** none (UX absence is by-design).

## PRD Analysis

*Extracted from the canonical FR1–FR31 contract + the 22-NFR set, as amended by the two reconciliation callouts (post-architecture 2026-07-11; Phase-0 review 2026-07-12). The Requirement-ID crosswalk supersedes all spec-era `FRn` labels used in the PRD narrative.*

### Functional Requirements (31)

**A. Manifest Discovery, Ingestion & Extraction**
- FR1 — discover + classify candidate manifests under a path; deterministic selection/precedence (architecture: **union coverage**); report the resolved scan set (the coverage denominator).
- FR2 — classify each dependency **source section** (pixi `[dependencies]` vs `[pypi-dependencies]`; env.yml conda vs `- pip:`) → correct extractor.
- FR3 — extract deps from conda/pixi **source** manifests without a resolved environment.
- FR4 — delegate to engines' native parsers for PyPI inputs (no bespoke parsing).
- FR5 — best-effort templating/selector eval; degrade to name-only+marked, never fail.
- FR6 — per manifest, distinguish "no deps present" vs "deps present but unresolved."
- FR7 — keep per-ecosystem attribution; no silent cross-ecosystem merge.

**B. Dependency-Hygiene** — FR8 hygiene findings (unused/missing/transitive/misplaced), PyPI+conda · FR9 honor `[tool.deptry]` ignores.

**C. Vulnerability** — FR10 vuln findings (advisory/affected-fixed/severity), actionable · FR11 offline/air-gapped DB, offline-by-default, records source+timestamp · FR12 stale DB → degrade verdict, never confident-clean · FR13 unresolved version → **vulnerability-indeterminate** + the name-level CVE tier (mapped-but-unversioned → "carries known critical CVEs across any version"); guardrail: coverage improves only by resolving or name-level flagging, never by assuming a version.

**D. Honest Coverage & Reporting** — FR14 schema-validated report (status/severity/schema_version/coverage/error_kind) · FR15 **split hygiene vs vuln coverage** · FR16 qualified verdict — coverage qualifier always stated, governing status follows the FR20 lattice (partial vuln coverage ⇒ `indeterminate`, non-zero; *corrected 2026-07-12*), never unqualified "clean" · FR17 human + machine report, every blocking finding actionable.

**E. Policy Gate & Verdict** — FR18 gate on content+severity (vuln axis default critical; hygiene axis separate — DEP001 blocks by default, mapping-confidence-gated; DEP002/3/4 warn) · FR19 coverage-floor gate, default OFF (*repurposed 2026-07-12*: the warn-only guardrail + waived-indeterminate ceiling) · FR20 verdict composition — lattice `error > policy-violation > indeterminate > warn > bypassed > clean > not-applicable`; exit derived separately: error→2, un-waived policy-violation→1, **indeterminate→1 (pinned 2026-07-12)**, else 0 · FR21 engine presence/version detection + typed error_kinds routed to owner, never silent PASS · FR22 no-meaningful-scan → non-passing, never clean · FR23 warn-only mode.

**F. Waivers & Bypass** — FR24 auditable expiring waiver (reason/authorizer/expiry), read-not-written · FR25 re-block on expiry + flag for review · FR26 validate waiver schema, reject malformed/malicious.

**G. SBOM & Machine Contract** — FR27 CycloneDX 1.6 SBOM (source-registry purls, self-declared partiality) · FR28 stable exit-code contract (frozen `{0,1,2,130}`).

**H. CLI Operation & Configuration** — FR29 one non-interactive command → one exit code · FR30 dual `[tool.python-deptry-osv-scanner]` config (pyproject+pixi, per-key precedence, owns the hygiene→status + CVSS-threshold policy tables) · FR31 `--version`/`--help` stable contract.

**Total FRs: 31.**

### Non-Functional Requirements (22)

- **C0 — Gate-Integrity invariant** (cross-cutting acceptance property): never false-green; N adversarial fixtures → 0 exit-0.
- **Reliability (5):** NFR-R1 corpus 0 uncaught exceptions (~1,950 files) · R2 ratcheted unparseable-rate baseline · R3a no repo/host mutation · R3b two-tier determinism (decision-deterministic default; byte-identical `--deterministic`) · R5 bounded engine timeout.
- **Security (8):** S1 no execution of untrusted input (AST denylist, no jinja-render, safe_load only) · S2 no silent egress (socket guard) · S3 waiver untrusted + least-privilege · S4 no repo writes + secure temp · S5 ReDoS/resource bound · S6 engine-input purity · S7 output neutralization (schema-aware encoder) · S8 trusted-input integrity (fresh+authentic DB → fail-loud).
- **Performance (3):** P-warm (overhead ≤ ~2s p95, engines-stubbed) · P-cold (cacheable first-run DB; air-gap pre-provisioned fail-loud) · P-concurrency (engines parallel, no shared state, O(project)).
- **Interoperability (3):** I1 schema conformance (report schema, CycloneDX 1.6, purl) · I2 schema-version field + frozen exit enum `{0,1,2,130}` · I3 machine-output purity (stdout = one doc or empty).
- **Usability (2):** U1 actionable diagnostics (fail-with-a-fix) · U2 safe-by-default + warn-only on-ramp.
- **Portability (1):** C1 Python ≥ 3.12; engines on PATH in a tested version range, fail-loud out-of-range; pixi ≥ 0.72.2 (dev-env floor).

**Total NFRs: 22** (accessibility deliberately excluded — non-interactive CLI).

### Additional Requirements

- **Personas:** P1–P4, P6, P7, **P8 (local developer / workstation mode — added 2026-07-12; secondary consumer)**, M1. Journeys J1–J9 + **J10 (workstation mode)**.
- **Constraints:** lean-lib policy (PyYAML safe-APIs, packaging, cyclonedx-python-lib, jsonschema-at-runtime); never-writes-repo; offline-first vuln data; single-release v1; the false-green triad (indeterminate state + 7→4 projection + Gap-C withhold) is non-negotiable.
- **Cross-spec obligations (2026-07-12):** exit-code convergence with `inventory-match --policy` (FR-18 seam — this tool's enum wins); ComplianceReport is a **two-producer schema** (Kedro FR-16/FR-18 = the second producer); source-less hygiene = `not-applicable`; `cfe:*`/G98 SBOM conventions; the bundled map preserves `match_source`/`match_confidence`.

### PRD Completeness Assessment

**Strong and current.** The traceability chain (Vision → Success → 10 Journeys → FR1–31 → 22 NFRs) is intact; the two reconciliation callouts are internally consistent with the inline text they amend (verified during the 2026-07-12 Tier-1 pass — the three triad-contradicting prose sites were corrected). The exit projection is now total (indeterminate→1). No orphaned or contradictory requirements detected at extraction time.

## Epic Coverage Validation

*Method: mechanical per-story FR-tag extraction from `epics.md` (regex over the 20 story bodies — not the file-wide inventory sections, which mask story-level gaps).*

### Coverage Matrix (FR → owning story, by explicit AC tag)

| FR | Story tag(s) | | FR | Story tag(s) |
|---|---|---|---|---|
| FR1 | 1.6 | | FR17 | 1.5b |
| FR2 | 1.6 | | FR18 | 1.4, 3.1 |
| FR3 | ⚠️ untagged (substance: **2.2a**) | | FR19 | 3.1 |
| FR4 | 1.2 | | FR20 | 1.4 |
| FR5 | 2.2b | | FR21 | 1.5a, 5.1 |
| FR6 | 2.3 | | FR22 | 1.5a |
| FR7 | 2.4 | | FR23 | 3.3 |
| FR8 | 1.2 | | FR24 | 3.2 |
| FR9 | 1.2 | | FR25 | 3.3 |
| FR10 | 1.3b | | FR26 | 3.2 |
| FR11 | 1.3b, 2.4 | | FR27 | 4.1 |
| FR12 | 1.3a, 2.4 | | FR28 | ⚠️ untagged (substance: **1.1a**) |
| FR13 | 2.3, 2.4 | | FR29 | 1.5b |
| FR14 | 1.5b | | FR30 | 3.1 |
| FR15 | 2.3 | | FR31 | 1.5b |
| FR16 | 2.3 | | | |

### Missing Requirements

**None substantively missing.** Two **tag-level traceability defects** (LOW severity — one-line fixes):

1. **FR3** (extract deps from conda/pixi source manifests without a resolved environment) — Story 2.2a's *entire subject* ("parse-as-data, never rendered … deps land in the inventory") but the AC never cites `(FR3)`. → Add the tag to 2.2a's first AC.
2. **FR28** (stable exit-code contract) — realized by Story 1.1a's frozen-enum AC ("exit enum is the frozen closed set `{0,1,2,130}`") but tagged only as NFR-I1/I2. → Add `(FR28)` to that AC.

*(Root cause noted for process learning: the prior "all 31 FRs tagged" verification grepped the whole file — the Requirements Inventory section masked the two story-level omissions. This pass scoped the scan to story bodies.)*

**Stories with no FR tag (all legitimate):** 1.1a + 1.1b (the contract-first walking skeleton — schema/lattice/harness infrastructure; 1.1a gains FR28 per above), 2.1 (Gap-C identity machinery feeding FR13 — optionally tag FR13), 5.2 (NFR-driven by design: P-*, R1/R2/R3b, C1).

### Coverage Statistics

- Total PRD FRs: **31**
- FRs substantively covered in stories: **31 (100%)**
- FRs with explicit story-level AC tags: **29 (94%)** → 31 after the two one-line tag fixes
- FRs in epics but not in the PRD: none (no phantom requirements)
- Epic-level FR Coverage Map ↔ story-level tags: consistent (the map's post-roundtable corrections footnote correctly defers to story-level tags)

## UX Alignment Assessment

### UX Document Status

**Not Found — and still correctly so.** The 2026-07-11 report established that no UX artifact is implied (non-interactive `cli_tool`, consumer = pipeline, accessibility excluded). This pass re-examined the one material change since then: **persona P8 (local developer / workstation mode) + Journey 10 were added 2026-07-12** — a human at a terminal is now a *named* consumer. Verdict: **P8 does not create a UX-artifact requirement.** The PRD keeps interactivity at zero by design ("no prompts ever"; `--bypass` takes `--reason` inline), and every human-facing affordance remains owned at requirement level, now including the workstation additions:

- **FR17** human summary (default `--format text`) · **FR31** `--version`/`--help` · **NFR-U1** fail-with-a-fix diagnostics · **NFR-U2** safe-by-default + warn-only on-ramp
- **New, P8-specific (all requirement-owned, not UX artifacts):** cold-start actionable nudge + online-opt-in decision (Story 1.3a AC), workstation install docs + recommended first contact `scan . --warn-only` (Story 5.1 AC), `doctor` disposition v1-if-cheap (5.1 AC), TTY color auto-detection (PRD CLI section).

### Alignment Issues

None. The PRD ↔ architecture ↔ epics agree on the human-facing surface: text output unstable/non-contract, machine output pure (NFR-I3), local mode explicitly "softens nothing" (same lattice, exit codes, no prompts) in all three documents.

### Warnings

None. Absence of a UX document remains a correct non-finding for this product type.

## Epic Quality Review

*Standards: the create-epics-and-stories best practices (user value, epic independence, no forward dependencies, single-agent sizing, testable ACs). Special audit per the run instructions: verify the Phase-0 review's Tier-2–4 obligations were actually captured in story ACs — flagged below where they were not.*

### Epic Structure Validation

| Epic | User value | Independence | Verdict |
|---|---|---|---|
| E1 Spine + PyPI engine | "A maintainer gates a PyPI project end-to-end" — real value; contains two contract-first stories (1.1a/1.1b) that are technical by the letter of the rule | Fully standalone | ✅ — the 1.1a "technical story" is a **documented, roundtable-mandated deviation** (freeze-the-contract-whole to prevent schema-break retrofits), each story ends runnable |
| E2 conda/pixi wedge | The beachhead — differentiated value | Uses only E1 interfaces; "ships red-by-design `indeterminate` exits **without needing E3's waivers**" (explicit) | ✅ |
| E3 Policy + waivers | Team tunes the gate, files auditable exceptions | Functions on E1 output alone (conda-mapping-confidence knob gains full effect only once E2 exists — a data dependency, not a build dependency) | ✅ |
| E4 SBOM | Machine consumer gets an honest CycloneDX BOM | Reads the frozen inventory (E1); conda purls enrich when E2 lands | ✅ |
| E5 Fleet-readiness | 5.1 = adoption/diagnostics value; 5.2 = NFR hardening (persona P7/J8-owned, so it has a user) | Terminal; consumes E1–E2 | ✅ (5.2 accepted as the corpus gate J8 demands) |

Dependencies are strictly backward: E1 → E2 → E3/E4 → E5. **No epic requires a later epic.**

### Dependency Analysis (all 20 stories)

- **No forward dependencies found.** The three historic risks are all defused *in the text*: the 1.3a spike explicitly gates 1.3b + 2.4 **and not 1.2**; 1.4's synthetic-`indeterminate` fixture proves the highest-risk composition path in E1 without 2.3's producer; 2.2a's differential oracle is skip-if-renderer-unavailable (matured in 5.2, no infra forward-dep).
- `_engine_env()` is introduced by the first engine story (1.2) and reused by 1.3b — correct ordering.
- **Sequencing note (minor):** Story 1.6 (discovery) is numbered last in E1 but runs 4th in the recommended build order — and stories 1.1b–1.5 implicitly need a *minimal* discovery stub to run `scan <dir>` at all. The stub's ownership is unstated. → One-line fix: note in 1.1b's AC that it includes a trivial single-manifest discovery stub, completed/replaced by 1.6.
- Starter-template check: architecture says "NONE — complete the existing scaffold"; 1.1a/1.1b are exactly complete-the-scaffold ✅. Asset timing correct (map *stub* in 1.1b, real map when first needed in 2.1) ✅. No DB/entity-upfront violations (no database) ✅.

### Story Sizing & AC Quality

- Sizing: the four Phase-0 splits (1.1a/1.1b, 1.3a/1.3b, 1.5a/1.5b, 2.2a/2.2b) resolved every oversized story; all 20 are single-dev-agent scoped. ✅
- ACs: Given/When/Then throughout; error paths owned (1.5a typed errors, 1.3b exit-code semantics, 1.6's error-vs-indeterminate split); cross-cutting gates (C0a/C0b/C0c, sole-ownership guard, NFR-S\*) threaded per-story rather than as a "do security" story. ✅

### 🔴 Critical Violations

**None.** No technical epics without value rationale, no forward dependencies, no un-completable stories.

### 🟠 Major Issues (3) — Phase-0 obligations NOT yet captured in ACs

*The run instructions asked to flag exactly these. Tier-1 + the 1.3a spike scope landed in ACs; the following did not:*

1. **`pixi.lock` / `conda-lock.yml` extraction is still unowned** (Phase-0 A3). Story 2.1 *consumes* pixi.lock `pypi:` entries; the PRD's MVP text requires synthesizing version-pinned osv input "from `pixi.lock`/conda"; the positioning calls pixi.lock "the vuln hero path" — yet **no story AC builds the lockfile extractor** and the architecture module tree has no `extract/lockfiles.py`. → Add ACs to 2.1 or 2.3 (locked-closure inventory, exact versions, manager-aware conda-vs-pip routing, the URL-basename fixture) before E2 starts.
2. **Story 1.1a's freeze ACs miss three Tier-2 contract items** — the schema will be frozen *without* them unless added first: **(a)** the stable **finding-ID scheme** + waiver-scope decision for all three finding families (vuln/hygiene/indeterminate) — waiver matching (E3) silently depends on it; **(b)** the **producer-agnostic security section** (generic vuln-provenance, optional KEV/EPSS slots, tier + raw severity) — the Kedro FR-16/FR-18 second producer forces a schema bump otherwise; **(c)** the **open `axis` mechanism**. → Blocking **for Story 1.1a specifically** (not for the plan overall); add before implementing 1.1a.
3. **Source-less hygiene semantics (X4/A9-h) absent from 2.2a/2.3 ACs.** The fleet's majority repo shape (feedstocks, no Python source) must yield hygiene `not-applicable` — the semantic Kedro FR-16 already specs for the schema's second producer. Currently no AC owns it (risk: 100%-DEP002 noise on every feedstock scan).

### 🟡 Minor Concerns (6)

1. FR3/FR28 story-level tag omissions (from Step 3) — two one-line tag additions (2.2a, 1.1a).
2. 1.1b minimal-discovery stub unstated (sequencing note above).
3. `run_constraints` handling (X3) not in 2.2a/2.2b ACs — exclude or flag-as-constraint, matching the shipped `scan_project` semantics.
4. Story 4.1 lacks the estate SBOM-convention ACs (X7): `cfe:*` property namespace, G98 purl normalization, `scan-project --sbom-in` round-trip.
5. Story 5.2 lacks: the dogfood gate (spec DoD — run clean on this repo's own manifests), the adversarial out-of-repo corpus additions, and the named reference hardware for P-warm.
6. Story 1.2: DEP005 semantics verification + its policy-table row (default `warn`); Story 2.2a routing AC should name `[feature.*]`/`[target.*]` pixi tables.

### Remediation Guidance

All findings are **AC-text additions to `epics.md`** (+ one architecture module-tree line for the lockfile extractor) — roughly 10 surgical edits, no restructuring. Majors 1–3 should land **before their owning stories are implemented** (Major 2 before Story 1.1a — i.e., first); minors can ride along in the same edit pass.

## Summary and Recommendations

### Overall Readiness Status

**✅ READY — with one pre-1.1a conditions list.** The full artifact set (PRD + architecture + 20-story epics) is complete, mutually consistent after the 2026-07-12 Tier-1 reconciliation, and structurally sound: 31/31 FRs substantively covered, zero forward dependencies, all stories single-agent-sized, cross-cutting invariants threaded as per-story gates, UX correctly N/A. Nothing blocks *starting* implementation. The verdict is conditioned only in one place: **Story 1.1a freezes the ecosystem-wide contract, and three known freeze-scope items (finding-ID scheme, producer-agnostic security section, open axis) are not yet in its ACs** — freezing without them re-creates the exact schema-break risk the walking-skeleton design exists to prevent.

### Critical Issues Requiring Immediate Action

**None at the critical tier.** Three MAJOR issues, all AC-text gaps (not design defects), sequenced by when they bite:

1. **Before Story 1.1a** (first story — therefore the only near-term gate): add the three Tier-2 contract items to 1.1a's ACs — finding-ID scheme + waiver scope, producer-agnostic security section (generic provenance, optional KEV/EPSS, tier + raw severity), open `axis` mechanism.
2. **Before Epic 2**: give `pixi.lock`/`conda-lock.yml` extraction an owning AC + `extract/lockfiles.py` in the architecture tree (the vuln hero path is currently unbuilt-by-omission).
3. **Before Epic 2**: source-less hygiene → `not-applicable` semantics in 2.2a/2.3 (the fleet's majority mode; must match Kedro FR-16's already-specced behavior).

### Recommended Next Steps

1. **One surgical `epics.md` edit pass (~10 edits)** landing the 3 majors + 6 minors (FR3/FR28 tags, 1.1b discovery-stub note, run_constraints, 4.1 SBOM conventions, 5.2 dogfood/adversarial-corpus/hardware, 1.2 DEP005 + 2.2a pixi tables) + one architecture module-tree line. Commit as the Tier-2/4 completion of the Phase-0 review.
2. **Begin implementation at Story 1.1a** (`bmad-quick-dev`), following the recorded wedge-first build order.
3. At the E1→E2 boundary, re-verify majors 2–3 landed before starting 2.1/2.2a.

### Final Note

This assessment identified **11 issues across 3 categories** (3 major AC-gaps, 6 minor AC/tag concerns, 2 traceability tag defects — zero critical, zero structural). The prior PRD-only report's 7 forward-looking items are all discharged or superseded: the 3 architecture-blocking gaps were resolved (Gaps A/B/C), FR30's stability owner was assigned (the ConfigLoader), and all 3 epic-decomposition flags were heeded (vertical slices, seams-first, per-story cross-cutting gates). The plan is cleared for implementation; address Major 1 before the first story rather than before the first commit.

---
**Assessor:** `bmad-check-implementation-readiness` (full go/no-go scope: PRD + architecture + epics; UX N/A) · **Date:** 2026-07-12 · **Verdict:** READY — implementation may begin at Story 1.1a once its freeze-scope ACs are completed (Major 1).
