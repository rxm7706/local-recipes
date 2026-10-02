---
title: '83.3: The landing heal unions appended deferred-work rows the way it unions memlog entries'
type: 'fix'
created: '2026-10-02'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The landing heal (CAP-283, Story 78.1) resolves a merge conflict mechanically only for append-only memlogs and refuses every other path (MRS-DISP-038). Stories run as one parallel wave that each defer work append `### DW-` rows at the same tail of the station's `deferred-work-ledger.md`, so the second landing always refuses: on 2026-10-02 82.9 refused against 82.10 on that file alone and was resolved by hand. git folds the identical trailing lines of both last rows (`severity`, `promoted`, `status`) out of the hunk as shared context.

**Approach:** A sibling of `union_memlog_texts` resolves the station's own ledger when both sides' changes since the merge base are pure appends of whole rows: base, then `main`'s rows, then the branch's rows, each row rebuilt whole from its side's text, never from the conflict markers. Any other edit to the ledger, or another project's ledger, still refuses.

Ledger key: `83-3-the-landing-heal-unions-appended-deferred-work-rows-the-way-it-unions-memlog-entries`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- CAP-283 / Story 78.1 (FR-230), widened as the HARD boundary of Epic 83 states. A defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given both sides appended whole DW rows after the same point of the station's own ledger When the heal runs Then the ledger holds base, main's rows, then the branch's rows, each whole, and the landing merges
- Given either side edited an existing row When the heal runs Then it refuses (MRS-DISP-038)
- Given the conflict is in another project's ledger When the heal runs Then it refuses
- Given the ledger rule removed When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Fix the defect where the shipped behaviour lives, and pin it with a test that fails without the fix.

**Never:** Never resolve from conflict markers, never drop or duplicate a row, never touch another project's ledger.

</intent-contract>

## Binding

Parent: CAP-283 / Story 78.1 (FR-230), widened as the HARD boundary of Epic 83 states.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 (night) entry.
Ledger key: `83-3-the-landing-heal-unions-appended-deferred-work-rows-the-way-it-unions-memlog-entries`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-02 at the operator's request to chain the defects found landing Phase 2.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
