---
stepsCompleted: [1, 2, 3, 4, 5, 6]
project: pyforge-marshal
scope: dream-chain closure (2 missing Specs) + full-chain drift verification, headless
---

# Implementation Readiness Assessment Report

**Date:** 2026-08-02
**Project:** pyforge-marshal (Marshal CLI chain)

## Context for this pass

Two Dreams sat at `dream-chain-check` INV-1 (dream, no Spec) against pyforge-marshal
going into this session: `pyforge-marshal-loop-orchestrator.md` and
`pyforge-testing-charter.md`. This pass closed both, then re-ran the full readiness
gate to confirm nothing else drifted. Findings below are additive to the
2026-08-01 report and its same-day addendum, which remain the record of the
FR-59..65 / AD-40..50 decomposition.

## Step 1 — Document Discovery

Physical path `_bmad-output/projects/pyforge-marshal/planning-artifacts/` used
directly (parallel-agent / physical-path convention).

| Type | File | Status |
|---|---|---|
| Dream (Tier 0) | `docs/dreams/pyforge-marshal.md` | realized |
| Dream (follow-on, retired) | `docs/dreams/pyforge-marshal-loop-orchestrator.md` | **archived (duplicate), this session** |
| Dream (follow-on, real) | `docs/dreams/pyforge-testing-charter.md` | specified, real content — **spec authored this session** |
| Spec (kernel) | `specs/spec-pyforge-marshal/SPEC.md` + `glossary.md` | 9 CAPs, unchanged |
| Spec (retirement record, new) | `specs/spec-pyforge-marshal-loop-orchestrator/SPEC.md` | **new this session** |
| Spec (new capability, standalone) | `specs/spec-pyforge-testing-charter/SPEC.md` + `station-tea-status.md` | **new this session, status: ready** |
| PRD | `prds/prd-pyforge-marshal-2026-07-25/prd.md` | final, FR-1..65, **unchanged** — see Non-Decomposition below |
| Architecture | `architecture/architecture-pyforge-marshal-2026-07-25/architecture.md` | final, AD-1..50, unchanged |
| Epics & Stories | `epics.md` | 6 epics / 50 stories, **1 story amended this session** (2.1, drift fix) |
| UX | — | correctly absent (unchanged rationale, see 2026-08-01 report) |

Confirmed (unchanged from 2026-08-01): the `PRD.md` / `architecture.md` / 6 other
flat files in this directory are `local-recipes`-project documents, not a
pyforge-marshal duplicate — `bmad-drift-check` tracks and pin-syncs them, deliberate
placement, not stray. No action taken, none needed.

## Step 2 — Non-Decomposition Decision (testing-charter)

`spec-pyforge-testing-charter`'s 5 capabilities (correct dashboard TEA signal,
`bmad_tea_playwright.py` run for real fleet-wide, shared `pyforge-testing-kit`,
CI coverage gate, keeping test-architecture docs current) were evaluated against
this PRD and **not decomposed into it**. All 4 capabilities that became FRs in a
first pass were reverted: none touch `src/shared/packages/pyforge-marshal/`, all
are repo-level tooling (dashboard glob, a standalone script, a new sibling
package, CI pixi config) — the exact shape this PRD's own memlog already
excludes elsewhere (durable-runs CAP-1/CAP-2; fidelity-enforcement CAP-2/5/7/8:
"repo-level detector/BMAD-skill tooling... not the marshal CLI package, so no
marshal FR"). `spec-pyforge-testing-charter` stands alone, `status: ready`,
implementable directly (`bmad-quick-dev`/`bmad-dev-auto` against the Spec) —
it does not block or extend this readiness gate.

`spec-pyforge-marshal-loop-orchestrator` is a retirement record only (duplicate
of already-specified scope); no FR/AD/story implication.

**PRD unchanged: still FR-1..65 / NFR-1..14 / C-1..10.** Architecture unchanged:
still AD-1..50.

## Step 3 — Epic Coverage Validation (full mechanical re-check, not sampled)

- PRD declares 65 FRs (`#### FR-N:` headers) — all 65 referenced in `epics.md`. **Zero missing.**
- `epics.md` references 65 distinct FR ids — all 65 exist in the PRD. **Zero orphans.**
- Architecture declares 50 ADs — 47 referenced in `epics.md`; 3 unreferenced, each explicable:
  - **AD-18** — `[SUPERSEDED BY AD-34]`, retained only so old citations resolve. Correctly zero live references.
  - **AD-41** — cross-cutting doctrine ("Marshal sequences on verdicts it never authors"), enforced structurally wherever verdict-reads happen, not tied to one story. Consistent with the 2026-08-01 report's own finding on this AD.
  - **AD-44** — explicitly scoped to "Epics 10–12," the sibling `epics-genesis-installer.md` — a different project's epic numbering, correctly out of pyforge-marshal's own epics.md.
- `epics.md` references 0 AD ids with no matching architecture AD. **Zero orphans.**
- Story-id sanity: 50 declared, 50 unique. **No duplicates.**
- Dependency-graph walk over every story's `Deps:` line: **zero dangling references** (every dep resolves to a real story id).

**Coverage: 100%, both directions, mechanically verified — not a re-assertion of the 2026-08-01 table.**

## Step 4 — UX Alignment

Unchanged from 2026-08-01: correctly absent, Marshal is a deterministic CLI with no UX artifact declared anywhere upstream.

## Step 5 — Epic Quality Review / Drift Check

**Real gap found and fixed this session.** The 2026-08-01 report named five
resolved-but-unpropagated design questions (F-2, F-3, F-4, F-5, F-6, from the
2026-07-30 `ALL-RESOLVED` adversarial architecture review) as blocking Stories
2.1, 2.3, 2.5, 3.1, 3.2, 3.7. Re-checked against the actual story text, not the
report's own characterization:

| Finding | Resolution location | Propagated into story AC? |
|---|---|---|
| F-2 (scoped unevaluability) | AD-30 | ✓ Story 3.2 — verbatim |
| F-3 (policy-seed-only fold) | AD-26 | 🔴 **Story 2.1 — missing, fixed this session** |
| F-4 (tamper-evident, not tamper-proof) | AD-27 (declaration) | ✓ consistent — no story claims otherwise |
| F-5 (freeze narrows/widens split) | AD-26/AD-27 | ✓ Story 2.3 — present |
| F-6 (composite `(writer_id, counter)` id) | AD-28 | ✓ Story 3.1 — verbatim |

Only Story 2.1 ("Standalone verify-command runner, project-scoped") was
missing F-3's resolution: its acceptance criteria said nothing about the
`scope: policy-seed-only` marker or the `mid-run freezes not visible` note that
AD-26 requires for a no-run-in-flight evaluation. **Fixed**: two new
`**And**` clauses added to Story 2.1, citing AD-26/F-3, plus a dated note
explaining the drift and its source. No other story required a change — the
2026-08-01 report's blanket characterization ("F-2/F-3/F-5/F-6/F-4 correctly
still open") undercounted; four of the five were already correctly threaded
through by the time of this pass.

**Epic independence:** unchanged — Story 2.3 → Story 3.2 forward reference
remains the one known, adjudicated (F-9, 2026-07-30) exception; not
re-litigated here, not newly introduced.

**Story-level dependency check:** clean, per Step 3's programmatic walk.

## Summary and Recommendations

### Overall Readiness Status

**READY.** Not "ready with conditions" — the condition the 2026-08-01 report
carried forward (F-2/3/4/5/6 propagation into story text) is now resolved: 4
of 5 were already there, the 5th (F-3 → Story 2.1) is fixed this pass. The one
remaining named exception (Story 2.3 → Story 3.2) is a deliberate, dated,
self-documented epic-boundary decision, not an open question — Epic 1 already
proved the same interleaved-delivery pattern works operationally (10/10
shipped). Nothing blocks starting implementation at Story 2.1.

### Critical Issues Requiring Immediate Action

None. The prior CRITICAL (Story 2.3→3.2) is accepted, not blocking, per the
2026-08-01 report's own disposition — carried forward unchanged.

### Recommended Next Steps

1. **Run bmad-loop starting at Story 2.1.** Nothing else in the PRD → Architecture → Epics chain is outstanding for pyforge-marshal.
2. **Optional, low-cost, non-blocking:** `epics-with-stories.md` self-declares as "automatically derived... from epics.md" but was not regenerated after this session's Story 2.1 edit — it is a reference/companion copy consumed by `bmad_tea_playwright.py`, not the source of truth, so this is cosmetic drift only. Regenerate before next running the TEA generator against Marshal.
3. **`spec-pyforge-testing-charter` is ready for direct implementation** (not through this PRD) whenever fleet test-tooling work is prioritized — see the Spec's own capabilities for scope.

### Final Note

This pass found and fixed **1 real drift item** (F-3 not propagated into
Story 2.1), confirmed **0 FR/AD coverage gaps** (mechanical, full re-check),
confirmed **0 dangling story dependencies**, and closed the **2 remaining
dream-chain gaps** (1 duplicate retired, 1 real Spec authored and correctly
kept out of this PRD's scope). The chain is coherent end to end. **The only
step left on pyforge-marshal is running bmad-loop.**

---

**Assessor:** bmad-check-implementation-readiness (headless autonomous run, within a larger session)
**Date:** 2026-08-02
**Supersedes:** nothing — additive to `implementation-readiness-report.md` and `implementation-readiness-report-2026-08-01.md`, both of which remain the record of their own passes.

Implementation Readiness complete.
