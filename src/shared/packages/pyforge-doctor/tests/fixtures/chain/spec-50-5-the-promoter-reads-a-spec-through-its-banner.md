---
title: '50.5: The promoter reads a spec through its banner'
type: 'fix'
created: '2026-09-18'
status: 'done'
baseline_revision: '3e2859425c20e0114042befd50b3529d2785c50d'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred:
  - summary: >-
      Three sibling frontmatter parsers share the identical pre-banner-skip
      fence-check bug this story fixed in `promotion.py`/`spec_surface.py`.
      Of the three, `spec_low_risk.py::parse_declared_low_risk` is verified
      reachable via a promoted, banner-topped tracked spec and silently
      misreads its `declared_low_risk: true` as `False`;
      `dispatch_harness_done.py::parse_spec_status` and `spec_difficulty.py`
      are verified NOT reachable that way (both only ever read Tier-3/
      worktree draft spec text, which never carries a promotion banner).
    evidence: |-
      Traced `cli/gate.py::_gather_review_depth` -> `_find_spec_text`
      (gate.py:494-519) -> `spec_low_risk.py::parse_declared_low_risk`
      (spec_low_risk.py:55-68): the latter still gates on
      `lines[0] == "---"` with no banner-skip, so a banner-topped tracked
      spec's `declared_low_risk: true` is read as `False`, pushing
      `classify_review_tier` to a heavier review tier than declared.
      Separately traced `cli/dispatch.py:2098-2099`'s one call site for
      `dispatch_harness_done.py::parse_spec_status` through
      `_spec_text_prefer_worktree` (dispatch.py:465-480): it reads only
      the current dispatch worktree's relocated spec text, never a
      promoted tracked copy. Flagged by both the Blind Hunter and
      Verification Gap review layers on this story's 2026-09-18 review
      pass; explicitly out of this story's declared Surface (intent
      contract "Never" clause names all three modules as excluded).
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/spec_low_risk.py::parse_declared_low_risk
    severity: medium
  - summary: >-
      `_skip_leading_banner` (both `promotion.py` and `spec_surface.py`)
      only recognizes a banner starting at literal text offset 0 — a
      leading blank line, BOM, or other whitespace before the `<!--`
      marker falls through to "no frontmatter," reproducing the same
      failure mode this story exists to close.
    evidence: |-
      Raised independently by the Blind Hunter and Edge Case Hunter
      review layers on this story's 2026-09-18 review pass
      (promotion.py:433, spec_surface.py:69); not exercised by any test
      in this story's added coverage. Undecided from the diff/code alone:
      confirmed via repo-wide search
      (`grep -rn "Promoted from implementation-artifacts" --include="*.py"`)
      that no code in this repository programmatically writes the
      provenance banner text at all — it is always hand/LLM-authored —
      so whether any real authoring path ever introduces leading
      whitespace before the banner could not be settled from this
      codebase alone.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py::_skip_leading_banner
    severity: high
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** On 2026-09-18, herald 23.1's finalize (commit `b0b7f3019f`) overwrote a reconciled tracked spec (`spec-1-4`) with its stale Tier-3 twin, because the tracked copy began with an HTML-comment provenance banner (`<!-- Promoted from implementation-artifacts/ ... -->`) ABOVE its frontmatter fence, and `is_valid_spec_text` required `text.startswith("---")` -- so it read a valid, reconciled tracked spec as invalid and let the stale candidate win.

**Approach:** Both `is_valid_spec_text` (`core/promotion.py`) and `parse_declared_surface` (`core/spec_surface.py`) skip a leading `<!-- ... -->` block (single- or multi-line) before looking for the frontmatter fence, so a tracked copy is recognized as valid/promoted regardless of which side of the fence its banner sits on. `cli/deploy.py::_already_promoted_keys` needs no behavior change (it delegates to `is_valid_spec_text`) -- only test coverage proving the delegation still holds for the banner-topped shape.

## Boundaries & Constraints

**Always:** Skip only a well-formed leading `<!-- ... -->` block (closed, anywhere before the fence) before applying each function's existing fence/status/surface logic unchanged; keep the banner-skip helper AD-4 pure (no I/O, no subprocess, no clock) in both `core/promotion.py` and `core/spec_surface.py`, matching this codebase's existing per-module duplication convention for frontmatter-fence parsing (`spec_low_risk.py`, `spec_difficulty.py`, `dispatch_harness_done.py` each already duplicate it rather than sharing a helper).

**Never:** Do not treat an unclosed `<!--` as a banner (text must still fail the fence check when the comment never closes); do not touch `dispatch_harness_done.py`, `spec_low_risk.py`, or `spec_difficulty.py` -- out of the spec's declared Surface even though they share the identical latent bug; do not change behavior for the PR #1460 shape (banner BELOW the fence) which never starts with `<!--` and is already handled.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Banner above frontmatter (single line) | `<!-- Promoted ... -->\n---\ntitle: ...\nstatus: ...\n---\n\nbody` | `is_valid_spec_text` returns `True`; `parse_declared_surface` reads the `surface:` key through the banner | No error expected |
| Banner above frontmatter (multi-line) | `<!--\nRECOVERED\n...\n-->\n---\n...\n---\n\nbody` | Same as above -- banner-close search is not line-bound | No error expected |
| Banner below frontmatter (PR #1460 shape) | `---\n...\n---\n\n<!-- Promoted ... -->\n\nbody` | Unaffected -- parses exactly as before the fix (never starts with `<!--`) | No error expected |
| Unclosed banner | `<!-- never closed\n---\n...\n---\n\nbody` | `is_valid_spec_text` returns `False`; `parse_declared_surface` returns `None` | Falls through to the pre-existing "no frontmatter" path, not a new error type |
| No frontmatter at all | `no frontmatter here\n` | `is_valid_spec_text` returns `False`; `parse_declared_surface` returns `None` | Unaffected pre-existing behavior |
| `_already_promoted_keys` sees a banner-topped tracked copy | Tracked `spec-1-4` banner-topped + valid; stale Tier-3 `spec-1-4` also present | Tracked copy counts as already-promoted; stale Tier-3 candidate never overwrites it (`to_promote` empty for that key) | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py` -- `is_valid_spec_text(text)` (pre-existing, required `text.startswith("---")`); add `_skip_leading_banner` module-level helper + call it first inside `is_valid_spec_text`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/spec_surface.py` -- `parse_declared_surface(text)`'s fence check `lines[0].strip() != _FRONTMATTER_DELIMITER`; add the identical `_skip_leading_banner` helper (module is AD-4 pure, stdlib-only, no cross-module import per this codebase's duplication convention) + apply it to `text` before `.splitlines()`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py::_already_promoted_keys` -- delegates to `promotion.is_valid_spec_text`; no code change, add an integration test only.
- `src/shared/packages/pyforge-marshal/tests/unit/test_promotion.py` -- existing `_VALID_SPEC` fixture + `is_valid_spec_text` test block; add banner-topped / multiline-banner / banner-below (regression) / unclosed-banner cases.
- `src/shared/packages/pyforge-marshal/tests/unit/test_spec_surface.py` -- existing `_frontmatter`/`_HEADER` helpers; add the same four banner scenarios for `parse_declared_surface`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_deploy.py` -- existing `_write_tier3_spec`/`_write_tracked_spec`/`_FakeVcs` fixtures + `test_promote_never_overwrites_a_good_tracked_copy_with_a_broken_tier3_one` as the direct model; add the banner-topped-tracked-copy promotion scenario.
- `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-1-4-bridge-core-skeleton-state-errors-determinism-boundary.md` -- real-world source of the exact banner text used in fixtures (`<!-- Promoted from implementation-artifacts/ to tracked specs on 2026-08-04 -->`), confirming the current on-disk shape already has the banner below the fence (PR #1460's fix).

## Tasks & Acceptance

**Execution:**
- `core/promotion.py` -- add `_BANNER_PREFIX`/`_BANNER_SUFFIX` constants + `_skip_leading_banner` helper; call it inside `is_valid_spec_text` before the `text.startswith("---")` check -- makes a banner-topped tracked spec parse valid.
- `core/spec_surface.py` -- add the identical `_BANNER_PREFIX`/`_BANNER_SUFFIX`/`_skip_leading_banner` helper; apply it to `text` before computing `lines` in `parse_declared_surface` -- makes the `surface:` key readable through a leading banner.
- `tests/unit/test_promotion.py` -- unit-test all four `is_valid_spec_text` I/O-matrix rows that apply to it (banner above, multiline banner above, banner below unaffected, unclosed banner).
- `tests/unit/test_spec_surface.py` -- unit-test all four `parse_declared_surface` I/O-matrix rows.
- `tests/unit/test_deploy.py` -- integration-test the `_already_promoted_keys`/promotion-orchestration I/O-matrix row (banner-topped tracked copy beside a stale Tier-3 twin).

**Acceptance Criteria:**
- Given a tracked spec text beginning with a single-line `<!-- ... -->` banner followed by a valid `---`-fenced frontmatter block with a `status:` key, when `is_valid_spec_text` is called, then it returns `True`.
- Given the same shape but with a multi-line banner, when `is_valid_spec_text` is called, then it returns `True`.
- Given a spec text with the banner placed below the closing fence (the PR #1460 shape), when `is_valid_spec_text` is called, then it returns `True` exactly as before this change (no behavior change for that shape).
- Given a spec text with an unclosed `<!--` before any `---` fence, when `is_valid_spec_text` is called, then it returns `False`.
- Given a frontmatter block with a `surface:` key, preceded by a leading banner (single- or multi-line), when `parse_declared_surface` is called, then it returns the declared globs as a tuple, unaffected by the banner.
- Given a banner-topped, otherwise-valid tracked `spec-1-4` and a stale Tier-3 `spec-1-4` candidate both present, when the promotion scan runs (`_already_promoted_keys` / `run_promote`), then the tracked copy is classified as already-promoted, `to_promote`/`promoted` is empty for that key, and the tracked file's bytes are never overwritten.

## Spec Change Log

<!-- Append-only. Populated by step-04 during review loops. No bad_spec loopback occurred during this run's review pass; empty. -->

## Review Triage Log

### 2026-09-18 — Review pass

- verdicts: 13 findings — high 0, medium 3, low 2, false 5, maybe-false 3
- findings:
  - `[false]` `[reject]` (Blind Hunter) `_skip_leading_banner` is duplicated verbatim between `promotion.py` and `spec_surface.py` instead of factored into a shared helper — refuted: the intent-contract's own Boundaries "Always" clause explicitly mandates per-module duplication matching the codebase's existing convention (`spec_low_risk.py`, `spec_difficulty.py`, `dispatch_harness_done.py` already duplicate the identical frontmatter-fence check independently); not a defect.
  - `[medium]` `[defer]` (Blind Hunter) Fix is incomplete: `spec_difficulty.py`, `spec_low_risk.py`, and `dispatch_harness_done.py` share the identical pre-banner-skip fence-check bug and were left unpatched — grouped with the Verification Gap layer's grounded version of this same root cause (below). `dispatch_harness_done.py::parse_spec_status` verified (traced its one call site, `cli/dispatch.py:2098-2099`, through `_spec_text_prefer_worktree`) to read only Tier-3/worktree draft spec text, never a promoted banner-topped tracked copy, so not reachable.
  - `[medium]` `[patch]` (Blind Hunter) `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml:279` still records `50-5-the-promoter-reads-a-spec-through-its-banner: backlog` even though the story's implementation is complete and verified — action: update the ledger entry to `done`.
  - `[low]` `[patch]` (Blind Hunter) The Tier-2 CAP spec (`_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-50-5-the-promoter-reads-a-spec-through-its-banner.md`) frontmatter still reads `status: 'ready'` — action: advance it to `in-progress` per this repo's "keep the spec's status current" convention.
  - `[maybe-false]` `[defer]` (Blind Hunter) `_skip_leading_banner` only recognizes a banner starting at literal text offset 0 — a leading blank line, BOM, or other whitespace before `<!--` falls through to "no frontmatter," reproducing the original failure mode; untested — grouped with the two Edge Case Hunter rows below (same root cause). Could not settle whether any current or future banner-authoring path could ever introduce such leading whitespace (confirmed zero code in this repo programmatically writes the banner text at all — see the stacked-banner refutation below — so the banner is always hand/LLM-authored). If true, this reproduces the same HIGH-severity incident class this story exists to close. What would settle it: whether herald's or any future promotion-recovery tooling ever writes a tracked spec with content preceding the banner's `<!--`.
  - `[low]` `[patch]` (Blind Hunter) `parse_declared_surface`'s docstring ("the region between the first line -- which must be exactly `---`, after skipping a leading HTML-comment provenance banner if one is present... -- and the next line that is exactly `---`") is grammatically tangled — "the first line" is ambiguous between the literal first line of `text` and the first line after banner-skipping — action: reword for clarity.
  - `[false]` `[reject]` (Blind Hunter) Blank-line spacing "inconsistency" between the new module constants and the new helper function in `promotion.py` — refuted: a single blank line between two module-level constant assignments and two blank lines before the following `def` is standard PEP 8 usage, not an inconsistency.
  - `[maybe-false]` `[defer]` (Edge Case Hunter) `promotion.py:433` — leading whitespace/blank line before the `<!--` banner marker reproduces the pre-fix failure — same root cause and disposition as the Blind Hunter row above.
  - `[false]` `[reject]` (Edge Case Hunter) `promotion.py:423-438` — two stacked `<!-- --> <!-- -->` banners would leave the second unstripped — refuted: repo-wide search (`grep -rn "Promoted from implementation-artifacts" --include="*.py"`) confirms no code in this repository programmatically writes provenance-banner text at all; the banner is a one-time, hand/LLM-authored artifact (PR #1460), so there is no live mechanism by which a spec could ever acquire two stacked banners.
  - `[maybe-false]` `[defer]` (Edge Case Hunter) `spec_surface.py:69` — same leading-whitespace gap as above, in the sibling module — same root cause and disposition.
  - `[false]` `[reject]` (Edge Case Hunter) `spec_surface.py:61-74` — same stacked-banner claim as above, in the sibling module — same refutation (no code path ever writes a banner).
  - `[medium]` `[defer]` (Verification Gap) `spec_low_risk.py::parse_declared_low_risk` (used by `cli/gate.py::_gather_review_depth`, which reads a story's own TRACKED spec text via `_find_spec_text`) still runs the un-fixed `lines[0] == "---"` gate with no banner-skip: verified live by tracing `_find_spec_text` (`gate.py:494-519`) → `parse_declared_low_risk` (`spec_low_risk.py:55-68`) — a banner-topped tracked spec's `declared_low_risk: true` is silently read as `False`, pushing `classify_review_tier` to a heavier review tier than declared. Pre-existing (not introduced by this diff) and explicitly excluded from this story's declared Surface by the intent-contract's own "Never" clause, so deferred rather than fixed here; smallest correct fix reuses `_skip_leading_banner` inside `spec_low_risk.py::parse_declared_low_risk`. (Same layer separately checked `spec_difficulty.py` and found it unreachable — Tier-3-draft-only reads — and did not file that as a finding.)
  - `[false]` `[reject]` (Intent Alignment) `_skip_leading_banner`'s unbounded `text.find(_BANNER_SUFFIX, ...)` scan could in principle treat a coincidental `-->` in body prose as closing a genuinely unclosed `<!--`, swallowing the real frontmatter — refuted: the intent-contract's own "Always" clause defines closed as "anywhere before the fence," and any `<!--` followed anywhere later by `-->` is, by definition, a syntactically closed (possibly multi-line) HTML comment, not an "unclosed" one; verified by direct execution against a constructed adversarial input (an unrelated `-->` inside otherwise non-banner text) that the function still correctly returns invalid when residual non-`---` text remains before the true fence.

## Design Notes

`_skip_leading_banner` is duplicated verbatim (module-scoped constants + a 9-line function) in both `core/promotion.py` and `core/spec_surface.py` rather than factored into a shared helper module. This matches the codebase's existing convention: `_FRONTMATTER_DELIMITER = "---"` / `lines[0].strip() != _FRONTMATTER_DELIMITER` is already independently reimplemented in four separate `core/*.py` modules (`spec_surface.py`, `spec_low_risk.py`, `spec_difficulty.py`, `dispatch_harness_done.py`); introducing a new shared module for a 9-line helper would be a larger surface change than the spec's declared Surface (`core/promotion.py`, `core/spec_surface.py`, `cli/deploy.py`) calls for, and would touch modules never named in scope.

```python
def _skip_leading_banner(text: str) -> str:
    if not text.startswith("<!--"):
        return text
    end = text.find("-->", len("<!--"))
    if end == -1:
        return text
    return text[end + len("-->") :].lstrip()
```

## Auto Run Result

**Summary:** Fixed the 2026-09-18 herald-23.1 finalize incident where a promoted, reconciled tracked spec beginning with an HTML-comment provenance banner above its frontmatter fence was misread as invalid and overwritten by its stale Tier-3 twin. Both `is_valid_spec_text` (`core/promotion.py`) and `parse_declared_surface` (`core/spec_surface.py`) now skip a leading `<!-- ... -->` block (single- or multi-line, closed anywhere before the fence) before their existing fence/status/surface logic runs, unchanged otherwise. `cli/deploy.py::_already_promoted_keys` needed no behavior change — only new integration-test coverage proving the delegation holds for the banner-topped shape.

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py` — added `_BANNER_PREFIX`/`_BANNER_SUFFIX` constants + `_skip_leading_banner` helper; `is_valid_spec_text` now calls it before the `text.startswith("---")` check.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/spec_surface.py` — added the identical duplicated helper (per this codebase's per-module duplication convention); `parse_declared_surface` applies it before computing `lines`; docstring reworded (review patch) to remove an ambiguous "the first line" reference.
- `src/shared/packages/pyforge-marshal/tests/unit/test_promotion.py` — 4 new cases covering all applicable I/O-matrix rows (banner above, multiline banner above, banner below unaffected, unclosed banner).
- `src/shared/packages/pyforge-marshal/tests/unit/test_spec_surface.py` — 4 new cases, same matrix rows for `parse_declared_surface`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_deploy.py` — 1 new integration test: banner-topped tracked copy beside a stale Tier-3 twin is never overwritten.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml` — `50-5-the-promoter-reads-a-spec-through-its-banner`: `backlog` → `done` (review patch).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-50-5-the-promoter-reads-a-spec-through-its-banner.md` — `status: 'ready'` → `'in-progress'` (review patch; not yet merged to `main`).
- This spec file — status progression `draft` → `ready-for-dev` → `in-progress` → `in-review` → `done`; `deferred:` populated (2 items); `## Review Triage Log` populated (1 pass, 13 findings).

**Review findings breakdown:** 13 findings across 4 parallel reviewers (blind-hunter 7, edge-case-hunter 4, verification-gap 1, intent-alignment 1), grouped into 9 root-cause entries. 3 patched (1 medium — stale sprint ledger; 2 low — stale Tier-2 spec status, tangled docstring), 2 deferred (1 medium — the same sibling-parser gap independently raised by blind-hunter and verification-gap, grounded reachable only for `spec_low_risk.py`; 1 maybe-false/high-if-true — leading whitespace before the banner falls through to "no frontmatter"), 5 rejected as `false` (duplication-instead-of-shared-helper — matches an explicit spec convention; blank-line-spacing — standard PEP 8; two stacked-banner claims — no code anywhere writes the banner text, confirmed by repo-wide search; the unbounded `-->` scan — any `-->` after a leading `<!--` is by definition a closed comment per the intent's own "closed, anywhere before the fence" wording, confirmed by direct execution against a constructed adversarial input). 0 intent_gap, 0 bad_spec. Full per-finding detail in `## Review Triage Log` above.

**Follow-up review recommendation:** `false`. First pass; patched-entry verdicts were medium ×1, low ×2, high ×0 — the rule requires either one `high` or two-or-more `medium` patched entries, and neither condition is met.

**Verification performed:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — `8087 passed, 1 skipped, 12 deselected` before the review-patch pass; re-ran identically after applying the 3 patches (docstring-only code change) — `8087 passed, 1 skipped, 12 deselected` again, unchanged.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — `130 passed, 3 skipped` (no dependency-manifest changes made).
- Frontmatter integrity: parsed the complete spec-file frontmatter as YAML after appending the `deferred:` items and confirmed `status`, `deferred` (2 items, correct severities), and all other keys round-trip correctly.
- Matrix Test Audit (step-03): all 6 I/O-matrix rows confirmed covered by tests that actually ran and passed (no skipped/filtered/disabled covering test).

**Residual risks:**
- The two deferred items above (sibling-parser gap in `spec_low_risk.py`; leading-whitespace-before-banner gap in `_skip_leading_banner` itself) reproduce related failure classes in code explicitly out of this story's declared Surface — tracked in frontmatter `deferred:` for a future story.
- The Tier-2 CAP spec's status was advanced to `in-progress` rather than a terminal state, since this work is verified in-worktree but not yet merged to `main`; a human or a future automated pass should advance it to its terminal status after merge.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: all tests pass, including the new banner-scenario tests in `test_promotion.py`, `test_spec_surface.py`, `test_deploy.py`. Confirmed: `8087 passed, 1 skipped, 12 deselected`.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- expected: pass (no dependency-manifest changes made). Confirmed: `130 passed, 3 skipped`.

**Manual checks (if no CLI):** N/A -- all scenarios in the I/O matrix are covered by the automated commands above; ran an additional ad-hoc sanity script directly against `is_valid_spec_text`/`parse_declared_surface` reproducing every I/O-matrix row (banner-topped valid=True, no-frontmatter valid=False, unclosed-banner valid=False, surface-through-banner returns the declared tuple) to confirm the worktree's own edited source (not a stale editable install) was exercised.
