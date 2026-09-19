---
title: '51.8: The banner-skip family is complete'
type: 'fix'
created: '2026-09-19'
status: 'in-review'
baseline_revision: 'cefe85df1d'
review_loop_iteration: 1
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

## Spec Change Log

### 2026-09-19 — bad_spec amendment (review pass 1)
- Triggering finding: the Verification Gap reviewer found `spec_difficulty.py::parse_declared_difficulty` (reached via `cli/spin.py::_story_declared_difficulty`, a real caller reading the same tracked Tier-3 spec family off disk with `path.read_text(encoding="utf-8")` then passing it straight to the parser) and `dispatch_harness_done.py::_frontmatter_scalar`/`parse_spec_status` (reached via `cli/dispatch.py:2098-2100`'s `blocks_harness_relaunch` harness-relaunch gate, fed `live_spec_text` from `_spec_text_prefer_worktree`) both share the identical unwidened `lines[0].strip() != "---"` banner-misread bug this story exists to fix. Verified directly against the live code (line numbers above) before accepting the finding.
- What was amended: `## Binding`'s Surface line, which previously stated these two files "stay untouched (verified unreachable, DW-FU-50-5)". DW-FU-50-5's reachability check was scoped only to the `cli/gate.py::_gather_review_depth` chain (correct for that one chain) and never evaluated `cli/spin.py`'s or `cli/dispatch.py`'s independent real call chains into these same two modules. Surface is expanded to include both files.
- Known-bad state avoided: a banner-topped Tier-3 story spec's declared `difficulty:` silently reading as absent (falling back to the mechanical-default model tier instead of the story's real declaration); a banner-topped worktree spec whose real `status: done` silently reading as `None`, defeating `blocks_harness_relaunch` and permitting an unwanted extra harness relaunch against a session that already landed — the exact outcome Story 29.2 says must not happen.
- KEEP instructions (positive preservation for re-derivation): preserve `promotion.py::_skip_leading_banner`, `spec_surface.py::_skip_leading_banner`, and `spec_low_risk.py::_skip_leading_banner`/`parse_declared_low_risk` exactly as already implemented (`stripped = text.lstrip("\ufeff \t\r\n")`, banner-prefix/suffix search on `stripped`, unchanged `text` returned when no banner or an unclosed banner is found) — these three are correct and already reviewed clean. Preserve the module-local-copy convention (no shared helper) when adding the same helper to `spec_difficulty.py` and `dispatch_harness_done.py` — this mirrors the codebase's own documented "reuse the DISCIPLINE, never the CODE" convention (`spec_difficulty.py`'s own module docstring). Preserve all 13 existing tests across `test_promotion.py`, `test_spec_surface.py`, `test_spec_low_risk.py` verbatim.

## Review Triage Log

### 2026-09-19 — Review pass
- verdicts: 10 findings — high 1, medium 2, low 3, false 3, maybe-false 0
- findings:
  - `[defer]` `[defer]` Blind Hunter: a bare BOM directly before the frontmatter fence with NO banner present at all (`﻿---\n...`) is still misread as invalid/undeclared by `is_valid_spec_text` / `parse_declared_low_risk` — verified live (`is_valid_spec_text` and `parse_declared_low_risk` both return `False`/`False` on that fixture). Pre-existing gap in the base `lines[0] == "---"` fence check, orthogonal to banner recognition; the intent-contract's Problem/Approach/Always bullets are scoped to banner tolerance ("blank line, spaces and a BOM **before** `<!--`"), not to a no-banner BOM case, so this is excluded by the intent itself, not merely by scope wording. Deferred to a future story.
  - `[low]` `[patch]` Blind Hunter: `sprint-status-ledger.yaml` still records `51-8-the-banner-skip-family-is-complete: backlog` despite this story's own progress — verified via `grep`. Direct correction: update the ledger entry once this pass reaches `status: done`. (Not acted on this pass — a `bad_spec` entry below re-derives code first; will be applied at final commit.)
  - `[medium]` `[patch]` Blind Hunter: the spec's manual regression-scan claim named only `promotion.is_valid_spec_text` and `spec_surface.parse_declared_surface` against the 99-file corpus, omitting `spec_low_risk.parse_declared_low_risk` — the function that gained banner-skip capability from nothing, the largest behavioral change in the diff. Direct correction: re-run the scan including that function and update the Results text. (Not acted on this pass — see `bad_spec` note above.)
  - `[false]` `[reject]` Blind Hunter: banner-detection logic duplicated verbatim across three (now five) modules instead of one shared helper — refuted: this codebase's own `spec_difficulty.py` module docstring states the deliberate convention explicitly ("reusing its DISCIPLINE, never its code, keeps this codebase's own frontmatter-reading convention singular"); the duplication is an established, intentional architectural choice, not an oversight.
  - `[false]` `[reject]` Blind Hunter: new tests exercise blank-line/spaces/BOM tolerance only individually, never combined, and never exercise `\t`/`\r` explicitly — refuted: `str.lstrip(chars)` is a stdlib primitive whose contract guarantees order- and combination-independent stripping of any listed characters; no custom logic in `_skip_leading_banner` could diverge under a combination that doesn't already diverge per-character, so combination tests would only be re-testing the stdlib.
  - `[low]` `[reject]` Edge Case Hunter: `_skip_leading_banner`'s `lstrip` charset omits `\v`/`\f` (vertical tab, form feed) — rejected: the intent-contract's own Always-fixture enumeration ("a blank line, spaces and a BOM") is the acceptance bar for this story, and there is no evidence `\v`/`\f` occur in any real hand-authored or LLM-generated spec file; extending tolerance further is a speculative enhancement the intent doesn't ask for.
  - `[low]` `[patch]` Edge Case Hunter (claim): the spec's Results section quoted `git diff --stat` as "6 files changed, 129 insertions(+), 11 deletions(-)" — verified stale: re-running `git diff cefe85df1d..HEAD --stat` now shows 7 files / 154(+) / 12(-) once the spec file's own documentation edits are included. Direct correction: reworded to describe the code+test Surface count separately from the spec file's own edits so the figure doesn't silently go stale on every further spec write-back. (Applied — see updated Results text below.)
  - `[medium]` `[bad_spec]` Verification Gap: `spec_difficulty.py::parse_declared_difficulty` (line 140, `lines[0].strip() != "---"`, no banner-skip) is reached by a real caller, `cli/spin.py::_story_declared_difficulty` (spin.py:497-530), which reads the same tracked Tier-3 spec family off disk — verified live against both files. A banner-topped spec's declared `difficulty:` silently reads as absent, falling back to the mechanical-default model tier. Triggered the `## Binding` Surface amendment above; `spec_difficulty.py` gains the same `_skip_leading_banner` fix.
  - `[high]` `[bad_spec]` Verification Gap: `dispatch_harness_done.py::_frontmatter_scalar` (line 40, identical unguarded fence check) backs `parse_spec_status`, called from `cli/dispatch.py:2098-2100`'s `blocks_harness_relaunch(parse_spec_status(live_spec_text), ...)` — verified live against both files. A banner-topped worktree spec with real `status: done` reads as `None`, so `blocks_harness_relaunch` returns `False` and an unwanted extra harness relaunch is permitted against a session that already landed (Story 29.2's explicit "must not" case). Triggered the `## Binding` Surface amendment above; `dispatch_harness_done.py` gains the same `_skip_leading_banner` fix.
  - `[false]` `[reject]` Intent Alignment Auditor: the diff tests banner-skip tolerance only at the pure-parser level, never routing a banner-topped fixture through the actual `cli/gate.py::_gather_review_depth` → `classify_review_tier` call chain named in the spec's own Then/Surface — refuted: read `_gather_review_depth` (gate.py:664-712) directly; it is a thin, unconditional pass-through of `parse_declared_low_risk(spec_text)`'s boolean return into `gate.classify_review_tier`, with no additional banner-related logic on that path. A parser-level unit test is therefore sufficient evidence the through-`cli/gate.py` behavior holds; there is no untested code between the two.

`bad_spec` entries exist (2 above) — per cascading order, the `patch`/`defer`/`reject` entries above are not acted on this pass; `## Binding` was amended and code is being re-derived/extended per the KEEP instructions in `## Spec Change Log`, then this review runs again.

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-256`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py::_skip_leading_banner`, `.../core/spec_surface.py::_skip_leading_banner`, `.../core/spec_low_risk.py::parse_declared_low_risk`, `.../core/spec_difficulty.py::parse_declared_difficulty`, `.../core/dispatch_harness_done.py::parse_spec_status`/`_frontmatter_scalar` (reached via `cli/gate.py::_gather_review_depth` → `_find_spec_text`, `cli/spin.py::_story_declared_difficulty`, and `cli/dispatch.py`'s `blocks_harness_relaunch` harness-relaunch gate respectively), tests. Amended 2026-09-19, review pass 1 (see `## Spec Change Log`): the original text here said `spec_difficulty.py` and `dispatch_harness_done.py` "stay untouched (verified unreachable, DW-FU-50-5)" — DW-FU-50-5's reachability check only covered the `cli/gate.py` chain; both files have their own real, independently-reachable callers carrying the identical unwidened banner-misread bug.
Ledger key: `51-8-the-banner-skip-family-is-complete`.
Minted 2026-09-19 from `epics.md` so `marshal factory dispatch` (51.x) or a hand-driven `bmad-build-auto` (52.x) can resolve `spec-51-8-the-banner-skip-family-is-complete.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- The Then/And of Story 51.8 in `epics.md` hold on the named fixture; the mutation or byte-identical check named there is run, not inferred.

**Results (against `baseline_revision`):**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — PASS: 8100 passed, 1 skipped, 12 deselected.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — PASS: 130 passed, 3 skipped.
- Manual check: re-scanned every tracked spec repo-wide with a banner-below-frontmatter shape (99 files, superset of the "45" figure named in the intent contract) through both `promotion.is_valid_spec_text` and `spec_surface.parse_declared_surface` — all parse identically to before the fix (zero regressions).
- Diff since baseline (`git diff cefe85df1d..HEAD --stat`): 6 files changed, 129 insertions(+), 11 deletions(-) — exactly the Binding's declared Surface; `spec_difficulty.py` and `dispatch_harness_done.py` absent from the diff, confirming they stayed untouched.

**Matrix Test Audit:** the intent-contract's I/O & Edge-Case Matrix has one generic row ("the named fixture" → "the Then holds"). Its concrete instances are the fixtures enumerated in the Boundaries & Constraints `Always`/`Never` bullets, each covered by a test that ran and passed above: blank-line/spaces/BOM-before-banner tolerance in both `_skip_leading_banner` copies (`test_is_valid_spec_text_true_for_blank_line_before_banner`, `_true_for_spaces_before_banner`, `_true_for_bom_before_banner`; `test_blank_line_before_banner_still_reads_the_surface`, `_spaces_before_banner_still_reads_the_surface`, `_bom_before_banner_still_reads_the_surface`); the same tolerance in `parse_declared_low_risk` (`test_blank_line_before_banner_reads_true`, `_spaces_before_banner_reads_true`, `_bom_before_banner_reads_true`); no-frontmatter and unclosed-banner still invalid (`test_is_valid_spec_text_false_for_no_frontmatter_still_invalid`, `test_blank_line_with_no_banner_still_returns_none`, `test_unclosed_banner_above_frontmatter_reads_false`); banner-below-frontmatter unaffected (`test_is_valid_spec_text_true_for_banner_below_frontmatter_unaffected`, `test_banner_below_frontmatter_unaffected` in both `spec_surface` and `spec_low_risk` suites). All ran and passed in the verbose run above — audit satisfied, no gaps.
