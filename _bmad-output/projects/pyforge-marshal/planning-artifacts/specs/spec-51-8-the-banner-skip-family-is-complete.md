---
title: '51.8: The banner-skip family is complete'
type: 'fix'
created: '2026-09-19'
status: 'in-progress'
baseline_revision: 'cefe85df1d'
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

## Code Map

- `core/promotion.py::_skip_leading_banner` and `core/spec_surface.py::_skip_leading_banner` — pre-existing, identical, banner-recognition anchored at literal offset 0 (`text.startswith(_BANNER_PREFIX)`). Fix: `stripped = text.lstrip("\ufeff \t\r\n")`, then test/search on `stripped` instead of `text`. Both call sites (`is_valid_spec_text` in `promotion.py`; `parse_declared_surface` line ~122 in `spec_surface.py`) already route every input through this helper, so no caller change is needed.
- `core/spec_low_risk.py::parse_declared_low_risk` — had NO banner-skip helper at all; gated directly on `text.splitlines()[0] == "---"`. Fix: add the same `_skip_leading_banner` helper (module-local copy, matching the existing two-copy duplication convention rather than introducing shared code) plus its `_BANNER_PREFIX`/`_BANNER_SUFFIX` constants, and change `lines = text.splitlines()` to `lines = _skip_leading_banner(text).splitlines()`.
- `spec_difficulty.py` and `dispatch_harness_done.py` — confirmed unreachable from `cli/gate.py::_gather_review_depth` for this fixture family (DW-FU-50-5); left untouched, verified via `git diff --stat` against `baseline_revision` showing zero changes to either file.
- Reuse point: `cli/gate.py::_find_spec_text` (reads the tracked spec text) → `_gather_review_depth` (line ~681, calls `parse_declared_low_risk(spec_text)`) → `gate.classify_review_tier`. Read-only for this story; not modified.

## Tasks & Acceptance

- [x] `_skip_leading_banner` in `promotion.py` and `spec_surface.py` tolerates a leading BOM, blank line(s), or spaces before `<!--` — covered by `test_is_valid_spec_text_true_for_blank_line_before_banner` / `_true_for_spaces_before_banner` / `_true_for_bom_before_banner` (`test_promotion.py`) and `test_blank_line_before_banner_still_reads_the_surface` / `_spaces_before_banner_still_reads_the_surface` / `_bom_before_banner_still_reads_the_surface` (`test_spec_surface.py`).
- [x] A spec with genuinely no frontmatter (no banner, no `---`), or an unclosed banner, is still invalid — covered by `test_is_valid_spec_text_false_for_no_frontmatter_still_invalid` and `test_blank_line_with_no_banner_still_returns_none`.
- [x] `parse_declared_low_risk` gains the same banner-skip tolerance so a banner-topped `declared_low_risk: true` spec resolves through `cli/gate.py::_gather_review_depth` instead of silently reading `False` — covered by `test_blank_line_before_banner_reads_true` / `_spaces_before_banner_reads_true` / `_bom_before_banner_reads_true`, plus `test_banner_below_frontmatter_unaffected` (regression: the 45+ existing banner-below-frontmatter specs) and `test_unclosed_banner_above_frontmatter_reads_false` (`test_spec_low_risk.py`).
- [x] `spec_difficulty.py` and `dispatch_harness_done.py` remain untouched — verified via `git diff cefe85df1d..HEAD --stat` (6 files changed, neither of those two among them).
- [x] Full station verification green — see `## Verification` results below.

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
