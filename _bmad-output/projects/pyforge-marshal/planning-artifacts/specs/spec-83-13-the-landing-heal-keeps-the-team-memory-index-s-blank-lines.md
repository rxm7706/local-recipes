---
title: "83.13: The landing heal keeps the team-memory index's blank lines"
type: 'fix'
created: '2026-10-03'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_landing.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_heal.py
  - .claude/memory/MEMORY.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 83.11's `union_team_memory_index_texts` re-renders the whole `.claude/memory/MEMORY.md`: every `## ` heading loses the blank line before it and gains an extra one after (probe on the live file: `…branch line\n## Reference\n\n\n- [fleet…`), so one heal churns every untouched section.

**Approach:** Reconstruct the file from its own lines: insert the branch-only lines after the last non-blank line of the section each side appended to, and keep every other byte as it was.

Ledger key: `83-13-the-landing-heal-keeps-the-team-memory-index-s-blank-lines`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- Story 83.11 (the team-memory index union, CAP-283). A defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given the live `MEMORY.md` as base with one line appended to a section on each side When the union runs Then the result equals the base with both lines inserted at the end of that section, byte for byte everywhere else (including every blank line)
- Given no change on either side When the union runs Then the result equals the input byte for byte
- Given the reconstruction removed When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Treat lines as opaque text; pin the fix with a test on a copy of the live file.

**Never:** Never drop, reorder or reflow an existing line or blank line.

</intent-contract>

## Binding

Parent: Story 83.11 (`spec-pyforge-marshal` CAP-283, Story 78.1).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-03 (night, later) entry.
Ledger key: `83-13-the-landing-heal-keeps-the-team-memory-index-s-blank-lines`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 at the operator's request.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
