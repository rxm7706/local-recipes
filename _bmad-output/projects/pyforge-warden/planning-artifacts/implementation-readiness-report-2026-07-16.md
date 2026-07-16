---
stepsCompleted:
  - step-01-document-discovery
  - step-02-prd-analysis
  - step-03-epic-coverage-validation
  - step-04-ux-alignment
  - step-05-epic-quality-review
  - step-06-final-assessment
documentsIncluded:
  spec: docs/specs/pyforge-warden.md (upstream source of truth)
  prd: planning-artifacts/prd.md
  architecture: planning-artifacts/architecture.md
  epics: planning-artifacts/epics.md
  ux: null (N/A by design — non-interactive CI CLI)
assessmentScope: delta re-run after the D12 re-baseline (2026-07-16) — v1 absorbs the axis gates (flag-activated), EPSS, baseline & grandfathering, and the fix-PR actuator
priorReport: planning-artifacts/implementation-readiness-report-2026-07-15.md (preserved; assessed the pre-D12 26-story shape)
date: 2026-07-16
---

# Implementation Readiness Assessment Report

**Date:** 2026-07-16
**Project:** pyforge-warden

## Document Inventory

| Type | Status | File |
|---|---|---|
| **Spec (upstream)** | ✅ present — re-baselined by **D12** (owner-directed): the former "v1.1 NOW" bucket is now v1 | `docs/specs/pyforge-warden.md` |
| **PRD** | ✅ present | `planning-artifacts/prd.md` (2026-07-16 — canonical **FR1–FR40**; new § L Adoption & Remediation; FR33/FR35/FR36/FR37 re-baselined) |
| **Architecture** | ✅ present | `planning-artifacts/architecture.md` (2026-07-16 — two-mode policy, `first-epss` contract, `baseline.py` + `actuator.py`) |
| **Epics & Stories** | ✅ present | `planning-artifacts/epics.md` (2026-07-16 — 6 epics / **29 stories**; Epic 6 = 6.1–6.9) |
| UX Design | ⏭ N/A by design | — |

**Duplicates/conflicts:** none. **Missing documents:** none.

## PRD Analysis

*Delta against the 2026-07-15 report; unchanged findings are not restated.*

### Functional Requirements (40)

FR1–FR38 carry forward with the D12 re-baseline: **FR33/FR35** are now **v1, flag-activated**
(unconfigured → `warn` per FR37; configured → `policy-violation`/`indeterminate`); **FR36** now
includes EPSS (`epss {score, percentile}` + `--min-epss`, FIRST.org cached feed, mirrored
absence rule); **FR37** is re-framed as the unconfigured-axis default. New: **FR39** baseline &
grandfathering, **FR40** fix-PR actuator (§ L). The crosswalk gains FR-B1→FR39, FR-A1→FR40.

### Non-Functional Requirements (23)

Unchanged count. NFR-S2 extended (EPSS feed; the FR40 actuator named as the sole forge-egress
exception — opt-in, post-verdict, tree-untouched).

### PRD Completeness Assessment

✅ Complete for the D12 v1. The five absorbed items each have a canonical FR and an owning
story; Growth retains only the v1.x set (publish · provenance axis · SARIF · backlog ·
perimeter · engine-swap · provisioner · `vers`).

## Epic Coverage Validation

### Coverage Matrix (delta rows)

| FRs | Owning stories |
|---|---|
| FR32, **FR33 (v1)** | **6.2** (producer + gate flags) |
| FR34, **FR35 (v1)** | **6.3** (producer + gate flags, freshness-preconditioned) |
| **FR36 (KEV + EPSS)** | **6.4** (KEV) + **6.7** (EPSS) |
| FR37 (two-mode) | **6.5** |
| FR38 | 6.1 · **FR39** → **6.8** · **FR40** → **6.9** |
| NFR-S9 → 6.3 · NFR-C1 distribution gate → 6.6 | |

### Missing Requirements

None. All 40 FRs owned by AC tag.

### Stats

6 epics · **29 stories** (4 implemented: 1.1–1.4) · 40 FRs + 23 NFRs covered · delivery order
E1 → E2 → E3/E4 → E6 (6.1 → 6.2/6.3/6.4 ∥ → 6.5 → 6.7/6.8 → 6.9 → 6.6) → E5.

## UX Alignment Assessment

⏭ N/A by design (unchanged). New CLI surface (`--allow/--deny-licenses`, `--max-lag`,
`--require-lts`, `--fail-on-eol`, `--min-epss`, `--baseline`, `--baseline-emit`,
`--open-fix-prs`, `--fix-prs-dry-run`) — all flags on the one frozen verb; no prompts.

## Epic Quality Review

### Structure Validation

✅ Stories 6.7–6.9 follow the house shape (G/W/T, FR tags, pure-numeric IDs). Amended 6.2/6.3
carry their gate-flag ACs; 6.5 proves gate activation is a policy-table flip via a
same-fixtures-both-modes diff.

### Dependency Analysis

✅ Strictly backward: 6.7 → (6.4 feed template, 6.1 epss-object slot); 6.8 → (1.1 finding-ID
grammar, 3.2 waiver semantics as the expiry template); 6.9 → (1.7 typed errors, the composed
verdict — strictly post-verdict). 6.9's forge egress is an explicit, actuator-scoped carve-out
from the C0c socket-deny harness — flagged below.

### Sizing & AC Quality

✅ Single-agent-sized. 6.9 is the riskiest (external API surface + credential handling); its
dry-run + duplicate-protection + verdict-independence ACs bound it.

### 🔴 Critical Violations

None.

### 🟠 Major Issues (3)

1. **`sprint-status.yaml` still stale** (now 29 stories) — carried from 07-15; re-run
   `bmad-sprint-planning` before loop execution.
2. **Architecture reconciled targetedly, not regenerated** — carried from 07-15.
3. **New (D12): the C0c socket-deny carve-out for `actuator.py`** — the deny-by-default harness
   (story 1.2) must gain an actuator-scoped allowance without weakening the global guarantee.
   Story 6.9's AC names this; the harness change itself must land in 6.9, not as a global
   loosening. Flagged so review scrutiny lands there.

### 🟡 Minor Issues (2)

1. Deck/infographic still carry pre-D12 tiering on some slides (partially corrected in the same
   pass; residuals catalogued in the adversarial review §4).
2. The architecture capability-E-numbers vs epics delivery-epic-numbers double numbering
   (carried from 07-15).

### Remediation

(1) merge; (2) `bmad-sprint-planning`; (3) E1-tail → E6 execution per the build order, with
per-epic gate review on 6.9's egress carve-out; (4) decks follow-up pass.

## Summary and Recommendations

### Overall Readiness Status

**READY-WITH-CONDITIONS** — conditions: the sprint feed re-run (🟠1) and explicit review of the
6.9 socket-deny carve-out at implementation time (🟠3).

### Critical Issues Requiring Immediate Attention

None.

### Recommended Next Steps

1. Merge PR #63 (adversarial review + spec re-tier + story-0.1 replan + D12 re-baseline).
2. `bmad-sprint-planning` → refresh `sprint-status.yaml` for 29 stories.
3. Resume loop-driven implementation (E1 tail → wedge → E6).
4. CFE Rules 1 & 2 retro at effort closeout (owed; recorded in the spec DoD).

### Final Note

This report supersedes the 2026-07-15 report (which assessed the pre-D12, gates-at-v1.x shape);
all three prior reports are preserved as history. The spec remains upstream; D12 is recorded in
its § Decisions line and § Reconciliation.
