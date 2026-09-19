---
title: '28.1: A frontmatter reader that stops at the fence, not at the first dashes'
type: 'fix'
created: '2026-09-19'
status: 'in-progress'
baseline_revision: 'cefe85df1d6a6fdd7546c804b88f9ad42d5fab36'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `_frontmatter_parse` on marshal's `spec-50-5-the-promoter-reads-a-spec-through-its-banner.md` returns one deferral with no `location:` where the file declares two, and a prose file containing `---` returns `({}, True)`

**Approach:** the block is bounded by line-anchored fences and a leading banner is skipped

## Boundaries & Constraints

**Always:**
- the 50.5 fixture parses both deferrals — the first with `location:` (fingerprint `fdd6bce25c09`), the second (`5434eca8c9e5`, severity high) visible to `deferred-work` and to `deferred_work_intake.py`; a prose file with a `---` rule and no leading fence is `({}, False)`; an unclosed fence is `({}, True)`; a banner-topped tracked spec parses
- every existing caller's fixture set yields byte-identical verdicts, and restoring `split("---", 2)` re-truncates the fixture (mutation test)

**Never:**
- Do not widen what counts as parseable — an unbounded or non-mapping block stays `({}, True)` (Story 17-1 / FR-144); do not change the exit-code domain; do not touch callers.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the named fixture | the real run/journal/PR named in the Given | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-doctor CAP-81`.
Surface: `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py::_frontmatter_parse` (and `_frontmatter_fields`), tests (`tests/` fixture = marshal 50.5's tracked spec as landed on `main`), no caller changes.
Ledger key: `28-1-a-frontmatter-reader-that-stops-at-the-fence-not-at-the-first-dashes`.
Minted 2026-09-19 from `epics.md` so `marshal factory dispatch` can resolve `spec-28-1-a-frontmatter-reader-that-stops-at-the-fence-not-at-the-first-dashes.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).

**Manual checks:**
- The Then/And of Story 28.1 in `epics.md` hold on the named fixture; the mutation or byte-identical check named there is run, not inferred.
