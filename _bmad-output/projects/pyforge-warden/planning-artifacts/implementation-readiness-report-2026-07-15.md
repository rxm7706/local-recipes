---
stepsCompleted:
  - step-01-document-discovery
  - step-02-prd-analysis
  - step-03-epic-coverage-validation
  - step-04-ux-alignment
  - step-05-epic-quality-review
  - step-06-final-assessment
documentsIncluded:
  spec: docs/specs/pyforge-warden.md (upstream source of truth — spec-first since 2026-07-15)
  prd: planning-artifacts/prd.md
  architecture: planning-artifacts/architecture.md
  epics: planning-artifacts/epics.md
  ux: null (N/A by design — non-interactive CI CLI)
assessmentScope: full go/no-go re-run after the story-0.1 spec-first replan (multi-axis v1; FR32–FR38 + NFR-S9 + Epic 6)
priorReport: planning-artifacts/implementation-readiness-report-2026-07-12.md (preserved; assessed the pre-replan two-engine shape)
date: 2026-07-15
---

# Implementation Readiness Assessment Report

**Date:** 2026-07-15
**Project:** pyforge-warden

## Document Inventory

| Type | Status | File |
|---|---|---|
| **Spec (upstream)** | ✅ present — the sole source of truth since the 2026-07-15 spec-first replan | `docs/specs/pyforge-warden.md` (v1 / v1.x / vision tiering; § Reconciliation + § Release map + § Vision catalog) |
| **PRD** | ✅ present (whole, no duplicates) | `planning-artifacts/prd.md` (2026-07-15 — story-0.1 replan banner; canonical FRs grown to **FR1–FR38**, sections I–K; NFR-S9) |
| **Architecture** | ✅ present (whole, no duplicates) | `planning-artifacts/architecture.md` (2026-07-15 — § Multi-axis reconciliation; axisDataContracts; four-axis pipeline) |
| **Epics & Stories** | ✅ present (whole, no duplicates) | `planning-artifacts/epics.md` (2026-07-15 — 6 epics / **26 stories**; Epic 6 = multi-axis expansion 6.1–6.6) |
| UX Design | ⏭ N/A by design (non-interactive CI CLI; confirmed 2026-07-11) | — |

**Supplementary context:** the adversarial review
(`planning-artifacts/adversarial-review-pyforge-warden-spec-2026-07-15.md`) is this replan's
evidence base — its T1/T2/T4/T-a/T-b never-false-green trades are each closed by a named FR +
story below. The two prior readiness reports are preserved; both assessed the **pre-replan
two-engine product** and are historical.

**Duplicates/conflicts:** none. **Missing documents:** none (UX absence is by-design).

## PRD Analysis

*Extracted from the canonical FR1–FR38 contract + the 23-NFR set (22 + NFR-S9), as amended by
the 2026-07-15 story-0.1 replan banner (which supersedes the two 2026-07-11/12 reconciliation
callouts where they conflict). The Requirement-ID crosswalk now also maps the spec's
FR-K1/FR-L1/FR-L2/FR-C1/FR-C2 working labels → FR36/FR32/FR33/FR34/FR35.*

### Functional Requirements (38)

FR1–FR31 carry forward with three targeted amendments: **FR15** (coverage is per-axis, one
dimension per registered axis), **FR18** (default gate = critical CVE **or** CISA-KEV-listed,
DEP001-blocks confirmed), and section retitles (B = Axis 1, C = Axis 2). New: **FR32/FR33**
(license axis + v1.x gate), **FR34/FR35** (currency axis + v1.x gate), **FR36** (KEV
enrichment + gate + feed-absence semantics), **FR37** (non-gating-axis `warn` visibility),
**FR38** (the one versioned schema amendment). FR33/FR35 are v1.x capabilities listed for
contract completeness and explicitly marked non-v1.

### Non-Functional Requirements (23)

The 22 carried NFRs plus **NFR-S9** (bundled-data max-age). Amended: NFR-P-concurrency (all v1
axes parallel), NFR-C1 (engine version-range doubles as the distribution gate), NFR-S2
(KEV/endoflife feeds under the same no-silent-egress posture).

### Additional Requirements

Unchanged from 2026-07-12 (scaffold-exists, targeted runtime deps + `license-expression`,
single spine, `_engine_env()` seam, bundled map, non-rendering extraction, cross-cutting
acceptance gates) — plus the four replan-assigned ownerships: engine version-range (6.6), KEV
feed lifecycle (6.4), the 6.1 amendment scope, baseline ratchet (v1.x, not scheduled).

### PRD Completeness Assessment

✅ Complete for the multi-axis v1. The former completeness gap — the spec promising axes the
PRD never owned — is closed: every spec v1 feature now has a canonical FR, and every v1.x/vision
feature is named in Growth/Vision with its tier.

## Epic Coverage Validation

### Coverage Matrix (FR → owning story, by AC tag)

| FRs | Owning stories |
|---|---|
| FR1 | 1.9 · FR2 → 1.2/2.2 · FR3 → 2.2 · FR4 → 1.3/1.5 · FR5 → 2.2/2.3 · FR6 → 2.2 · FR7 → 2.1/2.5 |
| FR8, FR9 | 1.3 · FR10 → 1.5 · FR11 → 1.4/1.5 · FR12 → 2.5 · FR13 → 2.1/2.5 |
| FR14 | 1.1 · FR15 → 2.4 (per-axis form widened by 6.1) · FR16 → 2.4 · FR17 → 1.8/5.1 |
| FR18 | 1.6 (KEV tier joined by 6.4) · FR19 → 3.1 · FR20 → 1.1/1.6 · FR21 → 1.7 · FR22 → 1.7 · FR23 → 3.3 |
| FR24–FR26 | 3.2/3.3 · FR27 → 4.1 · FR28 → 1.1/1.6 · FR29 → 1.2+ · FR30 → 3.1 · FR31 → 1.1 |
| **FR32** | **6.2** · **FR33** → 6.2 *(v1.x prep: verdict vocabulary only)* · **FR34** → **6.3** · **FR35** → 6.3 *(v1.x prep)* |
| **FR36** | **6.4** · **FR37** → **6.5** · **FR38** → **6.1** |
| NFR-S9 | 6.3 · NFR-C1 distribution gate → **6.6** |

### Missing Requirements

None blocking. FR33/FR35 activation (the actual v1.x gates) is deliberately unscheduled — they
activate by a policy-table flip (6.5 AC) in a v1.x effort.

### Stats

6 epics · 26 stories (4 already implemented: 1.1–1.4 per `sprint-status.yaml`/code) · 38 FRs +
23 NFRs, all covered · delivery order E1 → E2 → E3/E4 → E6 → E5 (strictly backward deps
preserved; E6 consumes only frozen E1/E2 surfaces and owns the one sanctioned amendment).

## UX Alignment Assessment

### Alignment Status

⏭ N/A by design (unchanged): non-interactive CI CLI; human affordances owned as
FR17/FR23/FR31 + NFR-U1/U2. `scan --doctor` (now committed to v1 in story 5.1) stays inside the
one-verb, no-prompts contract.

### Issues / Warnings

None.

## Epic Quality Review

### Structure Validation

✅ Epic 6 follows the house shape: value-narrative intro, `Stories (6)`, `FRs covered`,
G/W/T ACs with FR tags, pure-numeric `N.M` IDs (bmad-loop parser constraint verified: 6.1–6.6).
Cross-cutting gates (C0/C0c/sole-ownership/NFR-S*) apply per-story, restated in the epic intro.

### Dependency Analysis

✅ Strictly backward: 6.1 → (1.1 frozen contract, deliberate amendment); 6.2/6.3 → (6.1, 1.2
Engine seam, 2.x inventory); 6.4 → (1.4 provisioning template, 1.5, 6.1); 6.5 → (1.2
DefaultPolicy, 1.6 verdict, 6.2/6.3); 6.6 → (1.3/1.5 engine contracts). E5 (5.2) now validates
all four axes — its widened AC references E6 producers, which is why E6 precedes E5 in delivery.

### Sizing & AC Quality

✅ Each 6.x story is single-agent-sized with a deterministic verify path (the scanner's own
test suite). 6.1 is the largest (5 coordinated files) but is a single schema change with an
enumerated update set.

### 🔴 Critical Violations

None.

### 🟠 Major Issues (2)

1. **`sprint-status.yaml` is stale** — it encodes the 20-story plan. `bmad-sprint-planning`
   must re-run before any bmad-loop execution of E6+; until then the loop's feed disagrees with
   epics.md. *(Remediation: run sprint planning as the first post-merge action.)*
2. **Architecture reconciled targetedly, not regenerated** — § Multi-axis reconciliation +
   amended sections are authoritative, but deep sections (e.g. § Starter Template, validation
   narrative) still narrate the two-engine era in places. Acceptable for E6 execution (the
   reconciliation section wins); a full `bmad-document-project`-style regen is deliberately
   deferred.

### 🟡 Minor Issues (3)

1. FR33/FR35 live in the canonical block as marked-non-v1 rows — a contract-completeness
   convention worth revisiting if it confuses a dev agent.
2. The architecture's capability E-numbers ≠ epics.md delivery epic numbers (its new "E5 —
   multi-axis" row = epics.md Epic 6); a clarifying note is in place, but the double numbering
   is a standing wading tax.
3. The deck/infographic status-column defects catalogued in the adversarial review (§4 items
   9–15) remain unfixed — presentation artifacts, not contract, but they will mislead until
   corrected.

### Remediation

Ordered: (1) merge this replan; (2) re-run `bmad-sprint-planning`; (3) execute E6 loop-driven
starting at 6.1; (4) fix the deck/infographic status columns in a follow-on docs pass.

## Summary and Recommendations

### Overall Readiness Status

**READY-WITH-CONDITIONS** — the planning set (spec → PRD → architecture → epics) is internally
consistent for the multi-axis v1 for the first time since the 2026-07-14 scope change. The two
conditions are the 🟠 items: regenerate the sprint feed before loop execution, and treat
architecture's reconciliation section as authoritative over its unregenerated tail.

### Critical Issues Requiring Immediate Attention

None. The five adversarial-review never-false-green trades all have closing owners: T1 → FR36 +
6.4 · T2 → FR37 + 6.5 · T4 → NFR-S9 + 6.3 · T-a → NFR-C1 + 6.6 · T-b → recorded on the v1.x
channel-provenance axis (must read pixi config layers).

### Recommended Next Steps

1. Merge PR #63 (review report + spec re-tier + this replan).
2. `bmad-sprint-planning` → refresh `sprint-status.yaml` for 26 stories.
3. Resume loop-driven implementation at the remaining E1 tail (1.5–1.9) per the wedge-first
   order; E6 unlocks after E4.
4. At effort closeout: the CFE Rules 1 & 2 retro (owed — recorded in the spec's DoD).

### Final Note

This report supersedes the 2026-07-11 and 2026-07-12 reports, both of which assessed the
pre-replan two-engine product and remain preserved as history. The spec is upstream: any future
conflict between these artifacts resolves through `docs/specs/pyforge-warden.md`, and contract
changes land there first.
