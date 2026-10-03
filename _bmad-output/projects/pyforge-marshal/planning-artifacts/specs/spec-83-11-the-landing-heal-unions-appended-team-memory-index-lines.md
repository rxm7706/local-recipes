---
title: "83.11: The landing heal unions appended team-memory index lines"
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
  - .claude/memory/README.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Every dispatch session's closeout captures a team-memory entry (the `scribe capture` session-close ritual), which adds one line to `.claude/memory/MEMORY.md` at the end of a section. Two stories that land one after the other both append at the same spot, and the landing heal treats `MEMORY.md` as an unknown conflict path, so the second landing is refused (MRS-DISP-038) and fixed by hand. On 2026-10-03 this refused 83.7 (merged by hand) and 83.4.

**Approach:** Add `.claude/memory/MEMORY.md` to the heal's mechanical set, resolved like a Spec memlog: when both sides only appended whole lines to the base (each side's lines are the base's lines in order, plus new lines), the resolution is the base, then main's new lines, then the branch's new lines not already present, kept in the section each side appended them to. Anything else (an edit or removal of an existing line, a reordered section) is not append-only and stays an escalation.

Ledger key: `83-11-the-landing-heal-unions-appended-team-memory-index-lines`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-283 (Story 78.1, the landing heal's append-only union) and Story 28.20 (the CAP-4 heal). A defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given main and the branch each appended a line to the same section of `.claude/memory/MEMORY.md` When the landing heals Then the merged file holds the base plus both new lines, each in the section it was appended to, and the landing proceeds
- Given both sides appended the identical line When the landing heals Then it appears once
- Given either side edited, removed or reordered an existing line When the landing heals Then `MEMORY.md` escalates as today (MRS-DISP-038)
- Given the live `.claude/memory/MEMORY.md` as base with one line appended to a section on each side When the union runs Then every base line survives byte for byte and the entry count is base + 2 (tested on a copy of the real file)
- Given the `MEMORY.md` rule removed When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Fix the defect where the heal lives (`core/dispatch_landing.py`'s mechanical set and a pure union function; `dispatch_land_heal.py` wiring), and pin it with a test that fails without the fix. Treat lines as opaque text; never filter or rewrite a line.

**Never:** Never resolve from conflict markers. Never drop or reorder an existing line. Never extend the mechanical set beyond `.claude/memory/MEMORY.md` in this story. Never stop sessions from capturing team memory.

</intent-contract>

## Design notes (non-binding)

- Story 83.3 (sent back 2026-10-03) also extends the heal's mechanical set, for appended deferred-work rows, and its review found that a union which filters entries can silently delete rows. Build on whichever lands first, and keep this union line-opaque.

## Binding

Parent: `spec-pyforge-marshal` CAP-283 (Story 78.1) and Story 28.20.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-03 (night) entry.
Ledger key: `83-11-the-landing-heal-unions-appended-team-memory-index-lines`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 at the operator's request (the twelfth defect found landing Epic 83).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
