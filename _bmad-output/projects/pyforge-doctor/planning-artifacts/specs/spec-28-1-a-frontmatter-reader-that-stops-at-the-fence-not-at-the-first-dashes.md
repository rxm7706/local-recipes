---
title: '28.1: A frontmatter reader that stops at the fence, not at the first dashes'
type: 'fix'
created: '2026-09-19'
status: 'in-review'
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

## Auto Run Result

Status: blocked
Blocking condition: implementation verification failed

**Summary of implemented change:** `_frontmatter_parse` in `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` no longer uses `text.split("---", 2)`. It now skips a leading `<!-- ... -->` provenance banner (`_skip_leading_banner`, ported from `pyforge.marshal.core.promotion`'s Story 50.5 helper), requires the opening fence to be a whole line that is exactly `---`, and scans line-by-line for the closing fence — so a `"---"` embedded mid-body (e.g. inside a quoted YAML scalar, or a markdown thematic break) can no longer truncate or fabricate a frontmatter boundary. A file with no leading fence is now `({}, False)` (absent metadata); an unbounded/unclosed fence still returns `({}, True)` (Story 17-1 / FR-144's refusal semantics preserved). `_frontmatter` and every existing caller inherit the fix with no code changes, per the Binding's "no caller changes" constraint.

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` — line-anchored fence parsing + banner skip, replacing the substring-split implementation.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_frontmatter_parse.py` (new) — direct unit coverage of every I/O-matrix row.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py` — added a live-fixture test against marshal's real tracked `spec-50-5-the-promoter-reads-a-spec-through-its-banner.md`, confirming both deferrals now parse (fingerprints `3bc3d91bdf95`/`5434eca8c9e5` — see note below).
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_dream_chain.py` — updated `test_markdown_without_a_leading_frontmatter_fence_surfaces_unparseable` (renamed `..._is_absent_not_unparseable`) to assert the corrected `({}, False)` behavior for a `---` rule with no leading fence, per Story 28.1's own Always clause superseding the Story 17-1/FR-144 expectation for that exact shape.

**Note on the Always clause's fingerprint:** the intent-contract's Always clause names `fdd6bce25c09` as the first deferral's fingerprint. Cross-checked against marshal's tracked `deferred-work-ledger.md` (`origin: spec-deferred 3bc3d91bdf95 ... also read as spec-deferred fdd6bce25c09 by doctor's pre-fix _frontmatter_parse`) and `epics.md` itself: `fdd6bce25c09` is the *old, pre-fix, buggy* fingerprint produced by the truncating parser this story replaces; `3bc3d91bdf95` is the already-reconciled correct value, and is what `gather_deferred_work` requires to recognize the item as already-ingested. The implementation produces `3bc3d91bdf95`. Not treated as a bad_spec finding — flagging here for record since it's a literal mismatch against the Always clause's stated text, resolved in favor of verified ledger evidence rather than the spec's prose.

**Review findings breakdown:** not reached — blocked before step 4 (review).

**Verification performed:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`: 1761 passed, 1 skipped, **1 failed** (`test_sources_status_body_promissory.py::test_gather_live_herald_pair_and_zero_false_positives`).
- The one failure is a live-repo-content snapshot assertion in `status_body_consistency.py` (CAP-3 / Story 21.14) — a module with zero import/call relationship to `chain.py` (confirmed by grep: no reference to `chain` in `status_body_consistency.py`). It asserts `scanned_terminal` document counts and promissory-language hits measured live against the current repo tree; the test's own docstring ("Re-measured 2026-09-18 (was herald_pair_fired == 1)") and the last commit that touched it (`25e10952e9 fix(ci): refresh doctor/steward live-baseline tests after absorbed specs`) show this is a known class of live-baseline snapshot test that periodically needs its own dedicated recalibration commit as unrelated repo content drifts — it is not a regression this story's diff introduced.
- Confirmed pre-existing and diff-independent two ways: (1) the diff touches only `chain.py` and three test files under `tests/unit/test_sources_chain_*`, never `status_body_consistency.py` or its test file; (2) ran `test_sources_status_body_promissory.py` in isolation — same failure, same assertion, unaffected by test ordering.
- Mutation check: reverting `chain.py` to `baseline_revision` and rerunning the new/updated `chain`-scoped tests reproduces the pre-fix failures (marshal-50.5 fixture loses the second deferral and the first deferral's `location:`), confirming the fix is load-bearing.

**Residual risk:** none introduced by this story's change. The blocking condition is entirely pre-existing, unrelated drift in a different capability (CAP-3) outside this story's declared Surface (`chain.py::_frontmatter_parse`, "no caller changes") — fixing it here would require touching `status_body_consistency.py`/its test, which Dream-first governance does not authorize under this story's spec. Recommend routing the live-baseline recalibration as its own small maintenance item (same pattern as the prior `25e10952e9` commit), independent of CAP-81.

**Re-dispatched 2026-09-19 (this invocation):** the invocation prompt pointed directly at this spec file, whose frontmatter `status` is `blocked`. Per `bmad-build-auto` step 1's intent-check routing, a directly-supplied `blocked` spec HALTs immediately with blocking condition `blocked spec supplied` — no resumption attempted this pass.

Noted for whoever re-routes this next: the failure recorded above (`test_gather_live_herald_pair_and_zero_false_positives`, pre-existing and unrelated to this story's `chain.py` diff) has since been fixed on `main` by commit `41ec2b4c802993000bd98e5ebeb97f400e4e24cf` ("doctor: the live promissory test filters on WARN status — the clean-state OK summary is not a hit (red-main fallout after #1493)"), which landed after this branch's `baseline_revision` (`cefe85df1d`). This branch has not merged that commit yet. Merging/rebasing onto current `main` and re-running `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` is the likely path to unblock — flagged here as a lead, not asserted as verified, since this HALT did not attempt it.

**Re-routed 2026-09-19 by the operator (hand step):** the blocking test was fixed on `main` by PR #1494 (`7380ecdb41`); `origin/main` merged into this branch, `status` set back to `in-review` so the next dispatch resumes at the review step over the diff since `baseline_revision` (this story's `chain.py` change plus #1494's three files). The `blocked` verdict above was the gate's, not this story's.
