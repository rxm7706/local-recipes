---
title: "83.13: The landing heal keeps the team-memory index's blank lines"
type: 'fix'
created: '2026-10-03'
status: 'done'
baseline_revision: '33a7af0cb5e1f58540ba1f14385991ee74582cdf'
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

### 2026-10-04 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings:
  - (no findings from blind-hunter, edge-case-hunter, verification-gap, or intent-alignment layers after self-orchestrated review of the diff against acceptance criteria)

## Auto Run Result

Status: done

**Summary.** `union_team_memory_index_texts` now keeps `main` byte-for-byte and inserts branch-only appended lines after each section's last non-blank line instead of re-rendering through `_render_team_memory_index`.

**Files changed**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_landing.py` — line-preserving reconstruction helpers; union uses `main` as skeleton.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_land_heal.py` — unchanged-input, live-file blank-line, and mutation tests for Story 83.13.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` — surface reconcile entry naming governed paths.

**Review.** No patch, defer, intent_gap, or bad_spec entries.

**Verification**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — pass
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — pass
- `pixi run --frozen -e pyforge-guild lint-types` — exit 0
- `python scripts/spec_surface_reconcile.py` — OK (after memlog reconcile on `spec-pyforge-marshal/.memlog.md`)

**Surface reconcile (S-13.7).** Governed paths named on owning Spec memlog:
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_landing.py`
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_land_heal.py`

No co-governor Spec required a second memlog entry (`spec_surface_reconcile.py` reported no drift with only the `spec-pyforge-marshal` reconcile).

**Residual risk.** Preamble-only parallel appends on the live index are covered by the same insertion helper but are rare in practice.
