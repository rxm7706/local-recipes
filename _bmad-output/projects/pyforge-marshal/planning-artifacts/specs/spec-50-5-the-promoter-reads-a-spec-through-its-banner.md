---
title: '50.5: The promoter reads a spec through its banner'
type: 'fix'
created: '2026-09-18'
status: 'in-progress'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** on 2026-09-18 herald 23.1's finalize committed `b0b7f3019f marshal: promote 1 story spec(s) to tracked artifacts` on local `main`, replacing the reconciled tracked `spec-1-4` (2026-08-30 Verification reconcile) with its stale Tier-3 twin, because the tracked copy began `<!-- Promoted from implementation-artifacts/ … -->` and `is_valid_spec_text` requires `text.startswith("---")`; PR #1460 moved 45 such banners fleet-wide as the data-side fix

**Approach:** both parsers skip a leading `<!-- … -->` block (possibly multi-line) before looking for the frontmatter fence

## Boundaries & Constraints

**Always:**
- the fixture's tracked copy is valid, `_already_promoted_keys` includes 1.4, `_scan_promotions` yields an empty `to_promote` for the pair, and `parse_declared_surface` returns the banner-topped spec's `surface:` list
- a spec with no frontmatter at all, or an unclosed banner, is still invalid (negative fixtures), and the 45 banner-below-frontmatter files #1460 produced parse identically before and after

**Never:**
- Do not make the supervisor trust a session's self-report, add a second gate, or re-attribute landed history — the Epic 50 HARD boundaries in `epics.md` bind.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the 2026-09-18 fixture | the real run/journal named in the Given | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-248`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py::is_valid_spec_text`, `.../core/spec_surface.py::parse_declared_surface` (shares the "line 1 must be `---`" assumption), `.../cli/deploy.py::_already_promoted_keys` (covered by test, no behaviour change expected), tests with herald's pre-#1460 `spec-1-4-…` as a fixture beside its Tier-3 twin.
Ledger key: `50-5-the-promoter-reads-a-spec-through-its-banner`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-50-5-the-promoter-reads-a-spec-through-its-banner.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- Herald's pre-#1460 `spec-1-4` (banner-topped) is valid and counts as promoted beside its Tier-3 twin (`to_promote` empty); `parse_declared_surface` reads through the banner; no-frontmatter and unclosed-banner negatives stay invalid.
