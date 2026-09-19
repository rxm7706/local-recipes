---
title: '51.8: The banner-skip family is complete'
type: 'fix'
created: '2026-09-19'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** both `_skip_leading_banner` copies recognise a banner only at literal text offset 0 (a leading blank line, BOM or space falls through to "no frontmatter" — the failure 50.5 exists to close), and `parse_declared_low_risk` still gates on `lines[0] == "---"` so a banner-topped spec's `declared_low_risk: true` silently reads `False`

**Approach:** the banner skip tolerates leading whitespace/BOM and `parse_declared_low_risk` skips a banner the same way

## Boundaries & Constraints

**Always:**
- fixtures with a blank line, spaces and a BOM before `<!--` are valid in both parsers, and a banner-topped `declared_low_risk: true` spec resolves the declared review depth through `cli/gate.py`
- a spec with no frontmatter or an unclosed banner is still invalid, the 45 banner-below-frontmatter files parse identically, and no second parser or gate appears

**Never:**
- Do not make the supervisor trust a session's self-report, perform the merge marshal only materialises, add a second gate or verdict owner, move a primary checkout that is not a clean `main`, or re-attribute landed history — the Epic 51/52 HARD boundaries in `epics.md` bind.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the named fixture | the real run/journal/PR named in the Given | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-256`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py::_skip_leading_banner`, `.../core/spec_surface.py::_skip_leading_banner`, `.../core/spec_low_risk.py::parse_declared_low_risk` (reached via `cli/gate.py::_gather_review_depth` → `_find_spec_text`), tests. `spec_difficulty.py` and `dispatch_harness_done.py` stay untouched (verified unreachable, DW-FU-50-5).
Ledger key: `51-8-the-banner-skip-family-is-complete`.
Minted 2026-09-19 from `epics.md` so `marshal factory dispatch` (51.x) or a hand-driven `bmad-build-auto` (52.x) can resolve `spec-51-8-the-banner-skip-family-is-complete.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- The Then/And of Story 51.8 in `epics.md` hold on the named fixture; the mutation or byte-identical check named there is run, not inferred.
