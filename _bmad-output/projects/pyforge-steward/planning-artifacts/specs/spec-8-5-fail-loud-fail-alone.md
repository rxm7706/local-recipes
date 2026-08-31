---
title: 'Fail loud, fail alone (Epic 8 Story 8.5, pyforge-steward)'
type: 'feature'
created: '2026-08-13'
status: 'done'
baseline_revision: 'd34ce6193c597cb9861d48a2cdae8e8b3a1ca558'
final_revision: '38596f204849193b0f55103e0aff118872d08bb2'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-jira-github-projects-sync/SPEC.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** During a `--schedule` batch, `list_linked_github_items()` silently drops any board
item whose link field is empty -- no log line, no error entry, no record it ever existed. A batch
containing an unlinked item completes as if nothing were wrong, violating AD-6 ("An item missing
its cross-system link emits a named greppable error and is skipped ... the batch continues and
exits non-zero at the end") and leaving Story 8.4's own frozen boundary ("Never implement the
'named, greppable error for the broken item' refinement -- that is FR-30 / Story 8.5") unclosed.

**Approach:** Remove the link-based candidacy filter so every enumerated board item becomes a
batch candidate (dedup unchanged); dispatch each through the existing, unchanged single-pair
`reconcile()`. `reconcile()` already raises `SyncUnlinkedError` (`"unlinked: github item <id> has
no linked jira issue"`, via `_read_both_sides`) when a dispatched item turns out unlinked, and
`reconcile_schedule_batch()`'s existing per-candidate try/except already folds that into a named,
failed entry -- no new exception class, message format, or aggregation logic required.

## Boundaries & Constraints

**Always:**
- Reuse `reconcile()`'s existing `SyncUnlinkedError` path (`_read_both_sides`) verbatim as the
  single source of the "unlinked" failure message -- do not add a second, parallel unlinked-check
  inside `list_linked_github_items()` or `reconcile_schedule_batch()`.
- Every non-null, deduplicated node the bulk listing returns becomes a candidate regardless of its
  link-field value -- `list_linked_github_items()` stops parsing field values and stops gating on
  `config.github_link_field_id` entirely; only `id`/`updatedAt` are read per node.
- `reconcile_schedule_batch()`'s per-candidate loop, aggregation, and `DutyResult` shape stay
  exactly as Story 8.4 built them -- an unlinked candidate's entry has the same shape as any other
  failed candidate's (`github_item_id`, `updated_at`, `ok=False`, `summary`).
- Update the two now-stale docstring claims: `list_linked_github_items` ("a candidate is every
  item whose LINK field is non-empty") and `reconcile_schedule_batch` ("never implements the
  'named, greppable error for the broken item' refinement -- that is FR-30 / Story 8.5").

**Block If:** nothing identified -- this reuses an already-built, already-tested single-pair
mechanism verbatim; no new failure mode, exception class, or architecture decision is needed.

**Never:**
- Never duplicate the unlinked check inside `list_linked_github_items()` or
  `reconcile_schedule_batch()` -- `reconcile()`'s existing path is the only source of truth for
  this message; a second implementation risks the two diverging.
- Never change `reconcile()`'s existing single-pair signature, `SyncUnlinkedError`'s message
  format, or the CLI surface.
- Never add retry/backoff/rate-limit handling for the extra single-item re-read `reconcile()`
  performs on a still-unlinked candidate -- out of scope, matches this epic's own precedent of
  deferring such concerns (Story 8.4 Review Triage Log).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Batch with one unlinked item among linked ones | 3 board items; ITEM_2 has no link field value, ITEM_1/ITEM_3 linked and converge cleanly | `DutyResult(ok=False, ...)`; ITEM_1/ITEM_3 entries `ok=True`; ITEM_2 entry `ok=False` with `summary` containing `"unlinked: github item ITEM_2 has no linked jira issue"` | Named per-item failure; other candidates unaffected |
| Batch entirely unlinked items | Every board item has no link field value | `DutyResult(ok=False, ...)`; every entry `ok=False` carrying the named unlinked summary; `"N failed"` in the aggregate summary | Batch completes for all, exits non-zero via existing `EXIT_FAILED` plumbing |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py` -- `list_linked_github_items()`
  (currently ~L504-585): drop the `_parse_field_values`/link-truthiness gate so every deduplicated
  node becomes a candidate; update its docstring. `reconcile_schedule_batch()` (currently
  ~L1030-1096): docstring-only update -- no functional change, since it already dispatches every
  candidate through `reconcile()` and folds an `ok=False` result into `entries` unchanged.
- `src/shared/packages/pyforge-steward/tests/conformance/test_sync_reconcile_propagation.py` --
  `test_list_linked_github_items_filters_by_link_field_only_never_baseline` (~L1293, its "unlinked
  excluded" premise is now false) and `test_schedule_batch_with_no_linked_items_is_ok_with_zero_candidates`
  (~L1323, its "0 candidates" premise is now false) both need rewriting; add one new mixed-batch
  test proving the frozen AC directly.

## Tasks & Acceptance

**Execution:**
- [x] `sync.py` -- `list_linked_github_items()`: remove `fields = _parse_field_values(node)` /
  `link = fields.get(config.github_link_field_id)` / `if link:` -- every deduplicated node appends
  unconditionally (`{"github_item_id": item_id, "updated_at": node.get("updatedAt")}`); update the
  docstring to describe every board item as a candidate, with the unlinked case surfaced by
  `reconcile()`'s existing `SyncUnlinkedError` path, not by this function.
- [x] `sync.py` -- `reconcile_schedule_batch()`: update the docstring paragraph that currently says
  this story "never implements the 'named, greppable error for the broken item' refinement" -- that
  refinement is now closed by the `list_linked_github_items()` change above; no code change to this
  function's body.
- [x] `test_sync_reconcile_propagation.py` -- rewrite `test_list_linked_github_items_filters_by_link_field_only_never_baseline`
  (rename to reflect the new behavior) to prove: an item with a link but no baseline is still a
  candidate (unchanged), AND an item with no link is now ALSO a candidate (changed) -- `list_linked_github_items`
  returns all three fixture items.
- [x] `test_sync_reconcile_propagation.py` -- rewrite `test_schedule_batch_with_no_linked_items_is_ok_with_zero_candidates`
  (rename to reflect the new behavior) so an all-unlinked-item batch yields `DutyResult(ok=False, ...)`
  with every entry's `summary` containing `"unlinked:"` and the matching item id.
- [x] `test_sync_reconcile_propagation.py` -- add a new test (sibling to
  `test_schedule_batch_one_candidate_failing_does_not_abort_the_others`) covering a MIXED batch:
  two linked items that converge cleanly plus one unlinked item, asserting the linked items' entries
  are `ok=True`, the unlinked item's entry is `ok=False` with `"unlinked: github item ITEM_2 has no
  linked jira issue"` in its `summary`, and the aggregate `result.ok is False` -- this is the frozen
  AC's literal scenario.

**Acceptance Criteria:**
- Given a `--schedule` batch containing one unlinked item among otherwise-linked items, when
  `reconcile_schedule_batch` runs, then every linked item's own entry is `ok=True`, the unlinked
  item's entry is `ok=False` with a summary containing the named, greppable prefix `"unlinked:
  github item <id> has no linked jira issue"`, and the aggregate `DutyResult.ok` is `False`.
- Given the full test suite, when `pixi run -e pyforge-steward pyforge-steward-test` runs, then it
  exits 0 including the rewritten and newly added tests, with zero live network calls.

## Spec Change Log

## Review Triage Log

### 2026-08-13 — Review pass

Blind Hunter (`bmad-review-adversarial-general`) and Edge Case Hunter (`bmad-review-edge-case-hunter`)
ran independently, no shared context, against the diff since `baseline_revision`. Every finding
below was verified by hand against the actual worktree source before triage, not taken at face
value from either reviewer's report.

- intent_gap: 0
- bad_spec: 0
- patch: 2 (low 2)
- defer: 2 (medium 1, low 1)
- reject: 5 (low 5)
- addressed_findings:
  - `[low]` `[patch]` (Blind Hunter) `_parse_field_values`'s docstring still claimed
    `list_linked_github_items` calls it -- this diff removed that call entirely. Reworded the
    docstring to say the function is no longer called from there.
  - `[low]` `[patch]` (Blind Hunter + Edge Case Hunter, corroborated) `_LIST_PROJECT_ITEMS_QUERY`
    still requested `fieldValues(first: 50)` per node even though the rewritten loop no longer
    reads any field value -- removed the now-dead `fieldValues` block from the query string.
  - `[medium]` `[defer]` (Blind Hunter) this worktree's local `epics.md`/tracked
    `sprint-status-ledger.yaml` are 60 commits stale against `main`'s 2026-08-13 correct-course
    renumbering, and misled Blind Hunter itself into rating this story's own correct labeling as
    its highest-severity finding ("mislabeled as 8.5, should be 8.4"). Verified false against the
    correct-course proposal document, the Tier-3 `sprint-status.yaml` backlink, and the git
    history of the already-landed 8.4 story -- this story's numbering is correct. Logged as
    `DW-FU-8-5` for whoever next syncs this loop-home branch against `main`.
  - `[low]` `[defer]` (Blind Hunter) no opt-out exists for a board item deliberately never meant
    to link to Jira -- it fails loudly, by name, on every scheduled tick forever. Matches CAP-4's
    own frozen intent text verbatim (no silent skip, ever) and this story's own "Never" boundary
    forbids inventing a new filtering mechanism here -- a real product/architecture decision for
    whoever next operates a mixed board. Logged as `DW-FU-8-5-2`.
  - reject (5, all low/noise, not actioned): the extra single-item GraphQL round-trip
    `reconcile()` makes for each still-unlinked candidate (Blind Hunter) -- an intentional,
    precedented tradeoff (AD-5: "a false negative is strictly worse than a false positive, one
    wasted read"), matches this story's own frozen "Never add retry/backoff" boundary and Design
    Notes rationale; `list_linked_github_items` is "now a misnomer" since it returns unlinked
    items too (Blind Hunter) -- cosmetic/subjective naming, a rename ripples across call sites the
    frozen Code Map did not scope, matches this file's own precedent of rejecting subjective
    phrasing concerns; "test coverage gap for the genuinely-empty-board 0-candidates path" (Blind
    Hunter) -- verified false, that coverage is untouched and still lives in
    `test_sync_duty.py:127` (a CLI-level test using zero board items), just not in the file the
    reviewer read; the rewritten all-unlinked-items test checks call *host* but not call *count*
    (Blind Hunter) -- a speculative test-strengthening suggestion pinning an implementation detail,
    not a behavior requirement already asserted by the I/O Matrix, matches this story's own
    precedent of rejecting similar suggestions; a GraphQL node with a falsy-but-not-`None` `id`
    (e.g. empty string) has no dedup/emptiness guard beyond `is None` (Edge Case Hunter) --
    pre-existing, unchanged by this diff (the same guard existed before Story 8.5), and matches
    Story 8.4's own precedent rejecting the identical "item_id not type-validated" concern
    (GitHub's GraphQL `ID!` scalar is vendor-guaranteed non-null/non-empty).

**Re-verification after patches:** `pixi run -e pyforge-steward pyforge-steward-test` -- 625
passed, 0 failed, zero live network calls (unchanged count -- both patches were docstring/query-
string only, no test logic changed).

## Design Notes

**Before (Story 8.4, silently excludes):**
```python
fields = _parse_field_values(node)
link = fields.get(config.github_link_field_id)
if link:
    seen_item_ids.add(item_id)
    candidates.append({"github_item_id": item_id, "updated_at": node.get("updatedAt")})
```

**After (this story, every item is a candidate; `reconcile()` names the unlinked failure):**
```python
seen_item_ids.add(item_id)
candidates.append({"github_item_id": item_id, "updated_at": node.get("updatedAt")})
```

`reconcile()` already re-reads the GitHub item fresh via `_read_both_sides` and raises
`SyncUnlinkedError(f"unlinked: github item {github_item_id} has no linked jira issue")` the moment
it finds no link -- before ever attempting a Jira call (`sync.py:819-822`). `reconcile()` itself
already catches `SyncError` and returns `DutyResult(ok=False, summary=f"sync reconcile: {exc}")`
(`sync.py:884-885`), and `reconcile_schedule_batch()` already folds that `DutyResult` into the
candidate's own `entries` record unchanged. This is why no new code is needed beyond removing the
filter: the "named, greppable error" is the exact string Story 8.1 already wrote and already
tested at the single-pair level, now reached for the first time via the batch path.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Summary.** Story 8.5 (CAP-4 "fail loud, fail alone on broken links", FR-30) closes the gap
Story 8.4 deliberately deferred: a `--schedule` batch item with no linked Jira issue now surfaces
a named, greppable `SyncUnlinkedError` (`"unlinked: github item <id> has no linked jira issue"`)
in its own `details["candidates"]` entry, while every other candidate in the batch still
completes. The fix reused an existing, already-tested single-pair mechanism verbatim (`reconcile()`
/ `_read_both_sides()` / `SyncUnlinkedError`, all unchanged) rather than inventing a new one --
`list_linked_github_items()` simply stopped filtering candidates by link-field presence, so every
enumerated board item now flows through `reconcile()`'s existing unlinked-detection path.

**Files changed:**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py` -- removed the link-based
  candidacy filter from `list_linked_github_items()` (every deduplicated node is now a candidate);
  updated its docstring and `reconcile_schedule_batch()`'s docstring to describe the now-closed
  behavior; removed the now-unused `fieldValues(first: 50)` block from `_LIST_PROJECT_ITEMS_QUERY`
  and corrected `_parse_field_values`'s stale docstring (both review-pass patches).
- `src/shared/packages/pyforge-steward/tests/conformance/test_sync_reconcile_propagation.py` --
  rewrote two tests whose old assertions assumed unlinked items were silently excluded, and added
  one new test proving the frozen AC's literal mixed-batch scenario directly.

**Review findings breakdown:** intent_gap 0, bad_spec 0, patch 2 (both low, auto-fixed: a stale
docstring and an unused GraphQL query field), defer 2 (`DW-FU-8-5` medium -- this loop-home
worktree's local `epics.md`/tracked ledger are 60 commits stale against `main`'s correct-course
renumbering, which misled the Blind Hunter reviewer itself; `DW-FU-8-5-2` low -- no opt-out exists
for a board item deliberately never meant to link to Jira), reject 5 (all low/noise: an
intentional precedented over-fetch tradeoff, a subjective function-naming nit, a verified-false
"coverage gap" claim, a speculative test-strengthening suggestion, and a pre-existing/vendor-
guaranteed edge case unrelated to this diff).

**Follow-up review recommendation:** false -- both patches were mechanical (a docstring correction
and removing a dead query field), no behavior change, and the full suite's pass count was
unchanged before and after (625/625). Low volume, low consequence, fully localized.

**Verification performed:** `pixi run -e pyforge-steward pyforge-steward-test` -- 625 passed, 0
failed, zero live network calls (independently re-run twice: once after implementation, once after
the review-pass patches). `pixi run -e pyforge-steward pyforge-steward-dogfood` -- clean, both
before and after patches. `ruff check` on both touched files -- 3 pre-existing findings, confirmed
unchanged from baseline via `git stash`/re-check (none introduced by this diff).

**Residual risks:** none blocking. Two items intentionally deferred to the ledger (`DW-FU-8-5`,
`DW-FU-8-5-2`) -- neither is a defect in this story's own behavior, both are pre-existing or
architecture-level concerns explicitly out of this story's scope per its frozen "Never" boundary.
</content>
