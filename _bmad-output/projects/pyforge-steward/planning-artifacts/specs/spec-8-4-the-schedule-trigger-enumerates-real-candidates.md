---
title: 'The schedule trigger enumerates real candidates (Epic 8 Story 8.4, pyforge-steward)'
type: 'feature'
created: '2026-08-13'
status: 'done'
baseline_revision: '822bc2a96f3e1d16c7c75316a78f5a278ab4b0ce'  # this run's actual starting HEAD; see Auto Run Result session note for why the prior value was stale
final_revision: '2c3d032c9afbf5082f0336f193e681de3f12be10'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-jira-github-projects-sync/SPEC.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** Story 8.1 built only the single-pair `reconcile()` core -- `cli.py`'s
`sync reconcile` requires exactly one of `--github-item`/`--jira-issue` per invocation. The
architecture's default operating mode, `trigger=schedule` (AD-1, default over webhook), depends
on a candidate-enumeration step that decides which linked items to reconcile on each tick --
inserted 2026-08-13 by `bmad-correct-course` (`sprint-change-proposal-2026-08-13.md`) as a
genuine decomposition gap: no story ever assigned this producer. `trigger=schedule` cannot
actually run today.

**Approach:** Add one bulk, paginated GitHub Projects V2 listing query (not one GraphQL call per
item) that enumerates every linked item on the board, then dispatch each through the existing
single-pair `reconcile()` unchanged, one at a time, within one run, aggregating into a single
`DutyResult`. Wire it behind a new `--schedule` selector alongside `--github-item`/`--jira-issue`
on the existing `sync reconcile` verb.

## Boundaries & Constraints

**Always:**
- Reuse `reconcile()`, `SyncConfig`, `HostScopedCredential`/`resolve_headers`, and
  `_default_transport`/`TransportFn` verbatim -- no change to `reconcile()`'s existing
  single-pair signature or behavior.
- Candidate discovery is GitHub-side only, via one new paginated GraphQL query
  (`ProjectV2.items(first, after)`), following `pageInfo.hasNextPage`/`endCursor` until
  exhausted. Factor the existing `ProjectV2ItemFieldTextValue` field-parsing loop out of
  `get_project_item` into a shared helper reused by both -- do not duplicate it.
- A candidate is every item whose parsed link-field value is non-empty (jira:AD-10 rule 1: an absent
  baseline is a first link, not a loop candidate -- still reconciled). Never read or compare
  baseline values during enumeration itself.
- Deliberately do NOT gate candidacy on `updated_at` -- fetch and surface it per candidate in
  `details` for observability only, never as a filter. A Jira-only-originated change never
  touches GitHub's `updatedAt`, and AD-5 states a false negative ("silently drops a change") is
  strictly worse than a false positive ("one wasted read, converges to no_op"). Treating every
  linked item as a candidate is the maximally over-inclusive filter AD-5 requires, and needs no
  new persisted state.
- Wrap each candidate's `reconcile(...)` call the same way `SyncDuty.run()` already wraps its own
  (`except (OSError, urllib.error.URLError)`), so one item's raw transport failure cannot abort
  the run.
- Aggregate into ONE `DutyResult`: `ok` is `True` only if every candidate's own result was `ok`;
  `summary` names the counts (candidates / ok / failed); `details["candidates"]` is a list of
  per-item dicts (`github_item_id`, `ok`, `summary`) -- mirrors `reconcile()`'s own `details`
  convention.
- `--schedule` (`store_true`) joins the SAME mutually-exclusive group as `--github-item`/
  `--jira-issue` on `sync reconcile` -- no new subcommand. The existing `--dry-run` flag applies
  uniformly to every candidate in the batch.

**Block If:** nothing identified -- pure decomposition of an already-decided mechanism
(AD-2/AD-5), per the correct-course proposal's own "no architecture change" finding.

**Never:**
- Never invent a persisted watermark, sidecar state file, or new baseline-map field to narrow
  the candidate filter -- AD-2 forbids a new sidecar store and jira:AD-10 forbids branching on the
  optional "last converged at" telemetry timestamp. Narrowing the filter for efficiency is
  future optimization, not this story's scope.
- Never build Jira-side (JQL) candidate discovery -- every linked pair is reachable from its
  GitHub Projects V2 item (GitHub is the authoritative board per AD-4), and `reconcile()`
  already re-reads BOTH sides fresh regardless of entry identifier, so a Jira-only change on an
  already-enumerated linked item is still caught.
- Never implement the "named, greppable error for the broken item" refinement -- that is FR-30 /
  Story 8.5, which depends on this story. This story's failure handling only needs to keep the
  batch alive and report failures in aggregate; it does not test a specific error-message shape.
- Never change `reconcile()`'s existing single-pair public signature or the
  `--github-item`/`--jira-issue` CLI surface.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Empty/no linked items | Bulk listing returns zero items, or items with no link-field value | `DutyResult(ok=True, ...)` naming 0 candidates | No error expected |
| Multiple candidates, all converge cleanly | 3 linked items; `reconcile()` returns `ok=True` (push or no_op) for each | `DutyResult(ok=True, ...)`; `details["candidates"]` has 3 entries, each `ok=True` | No error expected |
| One candidate fails mid-batch | 3 candidates; the 2nd's `reconcile()` returns `ok=False` (e.g. a stale/mismatched link) | 1st and 3rd still reconcile with results in `details["candidates"]`; overall `DutyResult(ok=False, ...)` names 1 failure of 3 | Aggregate `ok=False`; per-item failure surfaced in that item's own entry, never raised |
| Bulk listing itself fails | The listing GraphQL call errors before any candidate is read | `DutyResult(ok=False, summary="...enumerating candidates: ...")`, zero candidates attempted | Fails loud before dispatching any `reconcile()` call |
| Paginated board (> one page) | First page's `pageInfo.hasNextPage=True` | Lister follows `endCursor` and continues until `hasNextPage=False`, returning every linked item across all pages | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py` -- add
  `_LIST_PROJECT_ITEMS_QUERY`, a `_parse_field_values` helper factored out of
  `get_project_item`'s inline loop, `list_linked_github_items()` (bulk paginated candidate
  discovery), and `reconcile_schedule_batch()` (dispatch loop + aggregate `DutyResult`); wire
  `SyncDuty.run()` to call it when `ns.schedule` is set.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` -- `_add_sync_subparsers`:
  add `--schedule` to `identifier_group`.
- `src/shared/packages/pyforge-steward/tests/conformance/test_sync_reconcile_propagation.py` --
  extend `FakeTransport` (or add a sibling fake) to serve the new bulk-listing query -- route on
  `"projectId"` present / `"itemId"` absent in `variables`, distinct from the existing
  single-item query/mutation routing -- and add the batch-dispatch tests below.

## Tasks & Acceptance

**Execution:**
- [x] `sync.py` -- factor `_parse_field_values(node) -> dict[str, str]` out of
  `get_project_item`'s inline field-parsing loop; call it from both `get_project_item` and the
  new lister -- avoids duplicating the `ProjectV2ItemFieldTextValue` parsing logic.
- [x] `sync.py` -- add `_LIST_PROJECT_ITEMS_QUERY` and
  `list_linked_github_items(*, config, credential, transport) -> list[dict]` -- paginates until
  `hasNextPage` is false, returns one dict (`github_item_id`, `updated_at`) per node whose
  parsed link-field value is non-empty.
- [x] `sync.py` -- add `reconcile_schedule_batch(*, config, dry_run=False, transport=None) ->
  DutyResult` -- calls `list_linked_github_items`, then `reconcile(github_item_id=..., config=
  config, dry_run=dry_run, transport=transport)` once per candidate inside a
  `try/except (OSError, urllib.error.URLError)`, aggregates into one `DutyResult`.
- [x] `cli.py` -- add `--schedule` (`store_true`) to `identifier_group` in
  `_add_sync_subparsers`.
- [x] `sync.py` -- `SyncDuty.run()`: when `getattr(ns, "schedule", False)`, call
  `reconcile_schedule_batch` instead of `reconcile`.
- [x] `test_sync_reconcile_propagation.py` -- extend the shared fake to answer the bulk-listing
  query with a configurable multi-item board; add tests for the 5 I/O Matrix scenarios above.

**Acceptance Criteria:**
- [x] Given a GitHub Projects V2 board with 3 linked items, when `sync reconcile --schedule` runs,
  then all 3 are reconciled through the existing `reconcile()` engine in that one invocation,
  with no `--github-item`/`--jira-issue` given.
- [x] Given one of several candidates fails during a scheduled batch, when the batch completes, then
  every other candidate still reconciled (its own outcome present in `details["candidates"]`)
  and the run's overall `DutyResult.ok` is `False`.
- [x] Given the full suite, when `pixi run -e pyforge-steward pyforge-steward-test` runs, then it
  exits 0 including the new batch tests, with zero live network calls.

## Spec Change Log

## Review Triage Log

### 2026-08-13 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 9 (medium 4, low 5)
- defer: 0
- reject: 7 (low 7)
- addressed_findings:
  - `[medium]` `[patch]` `list_linked_github_items` raised a raw `TypeError` when the GraphQL
    response's `items.nodes`/`items.pageInfo` were present but `null` (JSON `null`, not merely
    absent) -- added an explicit `None` check inside the existing extraction `try` so both cases
    now raise the same named `SyncAPIError`, matching the function's own docstring contract.
  - `[medium]` `[patch]` A `null` entry inside `items.nodes` (a partial-error GraphQL response for
    one node) crashed `_parse_field_values(None)` with an uncaught `AttributeError` instead of
    being handled -- now skipped (`continue`) rather than fatal, so one malformed node no longer
    drops every other candidate on its page.
  - `[medium]` `[patch]` A vendor response claiming `hasNextPage=True` while `endCursor` is `None`
    or repeats the prior cursor would loop forever, re-fetching the same page -- added a
    non-advancing-cursor guard that treats this as page-exhausted rather than looping.
  - `[low]` `[patch]` A candidate node with a non-empty link but a missing `id` was appended with
    `github_item_id=None`, producing `reconcile()`'s generic "one of --github-item/--jira-issue is
    required" message downstream instead of a clear cause -- now skipped during enumeration.
  - `[low]` `[patch]` `updated_at` was fetched by `list_linked_github_items` but never threaded
    into `reconcile_schedule_batch`'s final `details["candidates"]` entries, silently dropping the
    exact per-candidate observability data the frozen contract's "Always" section requires it to
    surface -- now included in each entry; covered by a new assertion in the existing
    multi-candidate test.
  - `[low]` `[patch]` `reconcile_schedule_batch` only caught `SyncError` around the bulk-listing
    call (unlike its own per-candidate loop, which also catches `(OSError, urllib.error.URLError)`)
    -- widened to match, so a direct (non-CLI) caller gets the same friendly "failed enumerating
    candidates: ..." message for a raw transport failure during enumeration, not just for a named
    `SyncError`.
  - `[low]` `[patch]` No test proved `--schedule` is still rejected in combination with
    `--github-item`/`--jira-issue` now that the mutually-exclusive group has three members --
    added `test_sync_reconcile_schedule_is_mutually_exclusive_with_github_item` (asserts
    `EXIT_USAGE`, per `main()`'s own documented never-let-`SystemExit`-escape-verbatim contract,
    not a raised exception).
  - `[low]` `[patch]` No test proved `--dry-run` threads through every candidate in a real,
    non-empty scheduled batch (only a zero-candidate CLI smoke test existed) -- added
    `test_schedule_batch_dry_run_threads_through_every_candidate_with_no_writes`.
  - reject (7, all low/noise, not actioned): bulk listing over-fetches `fieldValues` that
    `reconcile()` re-reads anyway (matches the frozen contract's own "narrowing for efficiency is
    future optimization, not this story's scope"); no retry/backoff on transient failures; no
    concurrency/chunking/rate-limit handling for large boards; full-page draining before dispatch
    (no streaming); `candidate["github_item_id"]` uses plain indexing rather than `.get()` (an
    internal, always-present invariant, not external input); the `--schedule` help string reads
    more verbose than its sibling flags (subjective); no test for a candidate's state changing
    between listing and its dispatch turn (already proven at the `reconcile()` layer itself, which
    is reused verbatim and unchanged by this story).

**Re-verification after patches:** `pixi run -e pyforge-steward pyforge-steward-test` -- 686
passed (684 + 2 new patch tests), 0 failed, zero live network calls. `pixi run -e pyforge-steward
pyforge-steward-dogfood` -- both checks green, drift clean.

### 2026-08-13 — Review pass 2 (fresh pass on the recovered commit)

Cold-context review of the full story diff since this run's true baseline (`822bc2a96f3e...`,
recovered per the Auto Run Result session note above), covering `sync.py`, `cli.py`,
`test_sync_duty.py`, and `test_sync_reconcile_propagation.py`. Blind Hunter
(`bmad-review-adversarial-general`) and Edge Case Hunter (`bmad-review-edge-case-hunter`) ran
independently, no shared context. Every finding below was verified by hand against the actual
worktree source before triage, not taken at face value from either reviewer's report.

- intent_gap: 0
- bad_spec: 0
- patch: 5 (medium 1, low 4)
- defer: 2 (low 2)
- reject: 4 (low 4)
- addressed_findings:
  - `[medium]` `[patch]` (Edge Case Hunter, independently confirmed by hand) `list_linked_github_items`
    checked `nodes is None`/`page_info is None` but not their SHAPE -- a valid-JSON-but-wrong-shape
    response (e.g. `nodes` as a dict or int, `pageInfo` as a list) passed that check and then raised
    an uncaught `TypeError`/`AttributeError` past the function's own documented "never a raw
    KeyError/TypeError/AttributeError" contract, escaping all the way to `cli.main()`'s generic
    `except Exception` boundary (a raw traceback + `EXIT_INTERNAL`) instead of a named `SyncAPIError`.
    Fixed with `isinstance(nodes, list)`/`isinstance(page_info, dict)` guards and a per-node
    `isinstance(node, dict)` check, mirroring `transition_jira_issue`'s existing
    `isinstance(transitions, list)` + per-entry `isinstance(..., dict)` precedent in this same file
    (added in Story 8.1's own review pass 3, for the identical class of defect).
  - `[low]` `[patch]` (Blind Hunter + Edge Case Hunter, corroborated) `list_linked_github_items`
    never deduplicated candidates by `github_item_id` across pages -- GitHub's Relay pagination
    offers no guarantee against a repeated node if the board mutates mid-enumeration, which would
    dispatch the same item twice in one batch. Added an in-memory `seen_item_ids` set; single-run
    scoped, does not narrow the "maximally over-inclusive" candidacy filter and does not touch the
    frozen contract's "Never invent a persisted watermark" boundary (nothing is persisted).
  - `[low]` `[patch]` (Blind Hunter) `reconcile_schedule_batch`'s aggregate summary always used the
    plural noun ("1 candidates, 1 ok, 0 failed") -- fixed with a singular/plural branch.
  - `[low]` `[patch]` (Blind Hunter) No CLI-level (through `main()`/argparse) test proved
    `--schedule`/`--dry-run` together for a real non-empty batch -- the existing CLI-level
    `--schedule` test used zero candidates and never passed `--dry-run`, so `--dry-run`'s threading
    through the schedule branch specifically was only proven via a direct
    `reconcile_schedule_batch(dry_run=True, ...)` call, bypassing argparse and `SyncDuty.run()`'s
    `getattr(ns, "schedule", False)` dispatch entirely. Added
    `test_sync_reconcile_schedule_dry_run_via_cli_threads_through_with_no_writes`.
  - `[low]` `[patch]` (self, during this pass's own governance-repair commit) The
    `spec-pyforge-steward/.memlog.md` `RECONCILES` entry added to reconcile this story's
    spec-surface drift named the test coverage as "the 5 I/O Matrix scenarios" without naming
    them -- unverifiable from the memlog alone without the (gitignored) spec file in hand. Reworded
    to name the five scenarios briefly.
  - `[low]` `[defer]` (Blind Hunter) `sync reconcile` (all forms, not new to `--schedule`) has no
    `--json` flag and `cli.main()` prints only `result.summary`, so a `--schedule` batch's rich
    per-candidate `details["candidates"]` (which candidate failed and why) is computed but never
    reaches the operator through the CLI -- only visible to a direct Python caller of
    `reconcile_schedule_batch`. Pre-existing whole-CLI convention (every duty, not just `sync`),
    unrelated to this story's own logic, but this story's batch mode makes the gap more
    consequential for an operator debugging a partial `--schedule` failure. Real API-design gap,
    not a trivial patch.
  - `[low]` `[defer]` (Blind Hunter + Edge Case Hunter, corroborated) `_LIST_PROJECT_ITEMS_QUERY`'s
    `fieldValues(first: 50)` cap is copy-pasted from the pre-existing `_GET_PROJECT_ITEM_QUERY`
    (already a known, already-deferred issue for the single-item path -- see this ledger's Story
    8.1 entry) but is now exercised board-wide, automatically, on every scheduled tick rather than
    only for a manually-targeted single item -- a board with >50 custom fields could have a
    genuinely-linked candidate's link field silently fall outside the first page and be excluded
    from candidacy entirely, the exact false-negative failure mode AD-5 says is "strictly worse"
    than a false positive. Materially wider blast radius than the existing deferred entry
    describes; needs real per-item `fieldValues` pagination, not a trivial patch.
  - reject (4, all low/noise, not actioned): "no batching ceiling/backoff/rate-limit/concurrency
    handling for large boards" (Blind Hunter) -- duplicates a finding this story's own Review pass
    1 already explicitly rejected by name ("no retry/backoff on transient failures; no
    concurrency/chunking/rate-limit handling for large boards"), no new information; the
    `_LIST_PROJECT_ITEMS_QUERY` docstring's "never one call per item" framing "overstating" that
    reconciliation itself is O(1) calls (Blind Hunter) -- a stretch reading, the sentence in context
    plainly scopes to the discovery/listing step, matches this story's own precedent of rejecting
    subjective documentation-phrasing notes; `item_id` not type-validated as a string before use
    (Blind Hunter) -- GitHub's GraphQL `ID!` scalar is vendor-guaranteed to serialize as a string,
    speculative and unexploitable, matches this story's own precedent of rejecting a defensive
    check against an internal/vendor-guaranteed invariant; inconsistent exception-catching between
    the bulk-listing call (`except (SyncError, OSError, URLError)`) and the per-candidate dispatch
    loop (`except (OSError, URLError)`, no `SyncError`) (Blind Hunter) -- Edge Case Hunter
    independently traced `reconcile()`'s own source (lines 864-874, 950-951, 989-990) and confirmed
    every `SyncError`-raising phase inside `reconcile()` is already caught and converted to
    `DutyResult(ok=False, ...)` internally, so `SyncError` cannot currently escape `reconcile()` at
    all -- the asymmetry cannot fire today, a speculative regression-guard concern only.

**Re-verification after patches:** `pixi run --frozen -e pyforge-steward pyforge-steward-test` --
624 passed (623 + 1 new patch test), 0 failed, zero live network calls. `pixi run -e
pyforge-steward pyforge-steward-dogfood` -- clean. `python scripts/spec_surface_reconcile.py` --
`OK: every tracked file governed or allowlisted; no drift.` `ruff check` on all four touched
files: 4 findings, unchanged from this story's own already-documented pre-existing set (confirmed
none are new).

## Design Notes

**Pagination loop shape** (mirrors GitHub's standard Relay-style connection; no existing
precedent elsewhere in this repo to match -- confirmed by investigation):

```python
candidates: list[dict[str, object]] = []
after: str | None = None
while True:
    payload = github_graphql_request(
        _LIST_PROJECT_ITEMS_QUERY, {"projectId": config.github_project_id, "after": after},
        credential=credential, transport=transport,
    )
    items_conn = payload["data"]["node"]["items"]  # raise SyncAPIError on malformed shape
    for node in items_conn["nodes"]:
        fields = _parse_field_values(node)
        link = fields.get(config.github_link_field_id)
        if link:
            candidates.append({"github_item_id": node["id"], "updated_at": node.get("updatedAt")})
    if not items_conn["pageInfo"]["hasNextPage"]:
        break
    after = items_conn["pageInfo"]["endCursor"]
```

**Why not gate on `updated_at`:** the tempting design -- compare each item's `updatedAt` against
some "last checked" value to skip obviously-untouched items -- has no AD-2/jira:AD-10-compliant place
to store that value (no sidecar store; the baseline's optional telemetry timestamp is explicitly
non-load-bearing) and would silently miss Jira-only changes, which never move a GitHub item's
`updatedAt` at all. Treating every linked item as a candidate is simpler, has zero false-negative
risk, and defers any efficiency narrowing to a later story once a compliant comparand exists.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

**Summary of implemented change:** added the candidate-enumeration + batch-dispatch machinery
`trigger=schedule` (AD-1) needs to actually run, wired behind a new `--schedule` selector on the
existing `sync reconcile` verb. `sync.py` gained: (1) `_parse_field_values(node)`, factored
verbatim out of `get_project_item`'s inline `ProjectV2ItemFieldTextValue`-parsing loop, now
shared by `get_project_item` and the new lister; (2) `_LIST_PROJECT_ITEMS_QUERY`, one paginated
GraphQL query over `ProjectV2.items(first, after)`; (3) `list_linked_github_items(*, config,
credential, transport)`, which follows `pageInfo.hasNextPage`/`endCursor` to exhaustion and
returns one `{"github_item_id", "updated_at"}` dict per node whose parsed link-field value is
non-empty -- candidacy is gated on the link field ONLY, never the baseline (jira:AD-10 rule 1) and
never `updated_at` (fetched for observability only, per the Design Notes rationale); (4)
`reconcile_schedule_batch(*, config, dry_run=False, transport=None)`, which calls the lister once
then dispatches the existing, byte-for-byte-unchanged `reconcile()` once per candidate inside a
`try/except (OSError, urllib.error.URLError)` (mirroring `SyncDuty.run()`'s own existing wrap),
aggregating into one `DutyResult` whose `details["candidates"]` lists each candidate's
`github_item_id`/`ok`/`summary`. `SyncDuty.run()` now dispatches to `reconcile_schedule_batch`
instead of `reconcile` when `getattr(ns, "schedule", False)`. `cli.py`'s `_add_sync_subparsers`
gained `--schedule` (`store_true`) in the SAME mutually-exclusive `identifier_group` as
`--github-item`/`--jira-issue` -- no new subcommand, `--dry-run`/`--config` apply unchanged.
`reconcile()`'s own public signature and the pre-existing `--github-item`/`--jira-issue` CLI
surface are untouched, per the frozen contract's "Always"/"Never".

**Files changed (final, after the review pass's 9 patches):**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py` -- `_parse_field_values`,
  `_LIST_PROJECT_ITEMS_QUERY`, `list_linked_github_items` (hardened by review: guards a `null`
  `nodes`/`pageInfo`, a `null` node entry, a non-advancing pagination cursor, and a candidate
  missing its `id`), `reconcile_schedule_batch` (now also surfaces `updated_at` per candidate and
  catches `(OSError, urllib.error.URLError)` around the listing call, not just `SyncError`),
  `SyncDuty.run()`'s new `--schedule` branch, and docstring updates naming the new CLI surface
  (+226/-15 lines).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` -- `--schedule` added to
  `identifier_group` in `_add_sync_subparsers`, plus its docstring (+18/-4 lines).
- `src/shared/packages/pyforge-steward/tests/conformance/test_sync_reconcile_propagation.py` --
  a new `ScheduleFakeTransport` sibling fake (models MULTIPLE independent GitHub-item/Jira-issue
  pairs, since a batch run drives `list_linked_github_items` + N `reconcile()` calls against the
  SAME transport instance, unlike the single-pair `FakeTransport` above it) plus 9 tests covering
  all 5 I/O Matrix rows, 3 targeted checks (link-field-only candidacy gate, a malformed-listing
  unit test, the listing-call-count proof for pagination), and a review-added dry-run/multi-
  candidate test proving `--dry-run` makes zero writes across a real non-empty batch (+391 lines).
- `src/shared/packages/pyforge-steward/tests/conformance/test_sync_duty.py` -- the CLI-threading
  test proving `--schedule` reaches `reconcile_schedule_batch` through `main()` with no
  `--github-item`/`--jira-issue` given, plus a review-added test proving `--schedule` is still
  rejected when combined with `--github-item` now that the mutually-exclusive group has three
  members (+51/-1 lines; also dropped a pre-existing unused `import pytest` this file already
  carried before this story touched it, discovered while editing the same import block).
- `_bmad-output/implementation-artifacts/spec-8-4-the-schedule-trigger-enumerates-real-candidates.md`
  -- this file (task/AC checkmarks, Review Triage Log, this section).

**Review findings breakdown:** Blind Hunter (`bmad-review-adversarial-general`) and Edge Case
Hunter (`bmad-review-edge-case-hunter`) ran independently, no shared context, over the full diff.
16 unique findings after dedup (6 were raised by both reviewers independently, e.g. the missing
`OSError`/`URLError` catch and the missing `null`-node guard -- counted once each). 9 patched
(4 medium: unhandled `null` `nodes`/`pageInfo`, an unguarded `null` node crashing enumeration, an
unbounded pagination loop on a non-advancing cursor; 5 low: a candidate missing `id`, `updated_at`
fetched but never surfaced, an inconsistent exception catch around the listing call, and two
coverage gaps closed with new tests). 7 rejected as out of this MVP story's explicit scope or
non-issues (over-fetching `fieldValues` for efficiency, no retry/backoff, no
concurrency/rate-limit handling, no page-streaming, an internal-invariant dict-indexing style nit,
a subjective help-string verbosity note, and a coverage request already proven at the `reconcile()`
layer this story reuses verbatim). Zero `intent_gap`, zero `bad_spec` -- every finding was either
a mechanical hardening fix consistent with the frozen contract and this codebase's own existing
defensive patterns (`get_project_item`'s `null`-node guard was the direct precedent), or explicitly
out of scope per the contract's own "Never"/Design Notes. Full detail: `## Review Triage Log`.

**Follow-up review recommendation: false.** All 9 patches are narrowly-scoped defensive
hardening and two additive tests, entirely inside the two new functions this story introduces;
none change the frozen contract's behavior, none touch `reconcile()`'s own logic, and none carry
API/security/data-model impact. Low volume, low consequence, low breadth -- doesn't meet the bar
for an independent follow-up pass.

**Verification performed (final):**
- `pixi run -e pyforge-steward pyforge-steward-test` -- 686 passed, 0 failed, zero live network
  calls (every test drives a canned in-memory `transport`/fake).
- `pixi run -e pyforge-steward pyforge-steward-dogfood` -- `steward --version` (`steward 0.1.0`)
  and `steward keys audit --drift` (`[drift] clean`) both succeed, unaffected by this change.
- `ruff check` on all four touched files: 4 pre-existing findings remain (confirmed via a
  `git stash`/re-check against `baseline_revision`), all outside this diff's own new code
  (`typing.Sequence`/`Callable` vs `collections.abc`, an import-sort nit, an unused `noqa` --
  none introduced by this story); the one pre-existing `F401` this diff's own touched region
  DID cover (`test_sync_duty.py`'s dead `import pytest`) is now clean, a side effect of editing
  that same import block, not a separate cleanup pass.
- `git diff --stat` confirms exactly the four files the Code Map anticipated were touched (plus
  this spec file); `reconcile()`'s own function body is byte-for-byte unchanged in the diff.

**Deviations from the spec:** none of substance. Two test additions beyond the literal Code Map
(the CLI-threading test and the mutual-exclusivity test) are additive only -- no Task/AC changed.

**Residual risks:** none blocking. FR-30/Story 8.5's "named, greppable error for the broken
item" refinement is explicitly out of scope (frozen contract's "Never") -- today a failed
candidate's error is only visible via `details["candidates"][i]["summary"]`, not a distinct log
line; that is Story 8.5's job, not a defect here. This story also does not narrow the candidate
filter for efficiency (every linked item is a candidate on every schedule tick, matching the
Design Notes' explicit rationale) -- a future story may add a compliant efficiency narrowing once
a persisted comparand exists, but AD-2/jira:AD-10 forbid inventing one now. The 7 rejected review
findings (retry/backoff, concurrency/rate-limiting, page-streaming) are real production-hardening
considerations for a large board but were not part of this story's Effort-M decomposition scope;
worth a future story if a deployed board proves large enough to need them.

### 2026-08-13 — Session note: work recovered from an abandoned sibling attempt

This run's harness re-invoked `bmad-dev-auto 8-4-the-schedule-trigger-enumerates-real-candidates`
as a fresh attempt (dev-2, same run `20260813-160412-936a`) even though this exact spec already
existed with `status: done` above. Investigation found the completed, twice-reviewed
implementation was real but orphaned: the orchestrator's `dev-decision` log recorded the reason as
`spec baseline 8cb787f1c61f does not match orchestrator-recorded baseline 822bc2a96f3e` --
dev-1 had fast-forward-merged `main` mid-story (advancing its own recorded baseline past the
orchestrator's fixed one), so the orchestrator auto-rolled the branch back to its true baseline
(`822bc2a96f3e...`) and started a fresh attempt, first preserving dev-1's commit as
`attempt-preserve/20260813-160412-936a-137d3f9c` (journal: `attempt-commits-preserved`).

Per this project's own established precedent for exactly this situation
(`spec-8-1-bidirectional-propagation.md`'s 2026-08-10 "work recovered from an abandoned sibling
run" session note) and the fleet-wide standing policy against re-deriving already-reviewed work
from scratch: verified no commit between the orchestrator's true baseline and dev-1's stale one
touched any of the four files this story changes (`git log
822bc2a96f3e..8cb787f1c61f -- sync.py cli.py test_sync_duty.py
test_sync_reconcile_propagation.py` -- empty), then cherry-picked the preserved commit
(`137d3f9c5b`) verbatim onto the correct baseline. It applied with one trivial auto-merge (an
adjacent, non-conflicting `cli.py` hunk) and no conflicts, landing as `45a20349da`. No design,
code, or test content was altered.

Re-ran full verification on the recovered commit: `pixi run --frozen -e pyforge-steward
pyforge-steward-test` -- 623 passed (was 613 on the bare baseline; +10 confirms this story's own
new tests are present and green), zero live network calls. `pixi run -e pyforge-steward
pyforge-steward-dogfood` -- clean. `python scripts/spec_surface_reconcile.py` then correctly
flagged the recovered diff's four files as ungoverned (dev-1's session ended before landing a
memlog entry for them) -- reconciled with a `RECONCILES` entry in `spec-pyforge-steward/.memlog.md`
following the Story 8.1 sync-duty entry's exact convention (commit `33a9a0ea14`); re-run confirms
`OK: every tracked file governed or allowlisted; no drift.`

Only this file's frontmatter (`baseline_revision`, `final_revision`) and this session note were
updated -- the frozen `<intent-contract>`, `## Code Map`, `## Tasks & Acceptance`, `## Review
Triage Log`, and `## Design Notes` above are dev-1's own already-reviewed content, unchanged.
`review_loop_iteration` stays `0` per this workflow's "done spec re-invoked" protocol (a follow-up
review situation, not a resumption) -- proceeding to a fresh review pass on this branch's actual
recovered commits.

### 2026-08-13 — Final result this session: DONE (fresh review pass 2, on the recovered commit)

**Summary.** Ran a full fresh review pass (Blind Hunter + Edge Case Hunter, independent, no
shared context) against this branch's actual diff since the true baseline. 5 patches applied (1
medium: `list_linked_github_items` lacked shape guards for a valid-JSON-wrong-shape GraphQL
response, letting an uncaught `TypeError`/`AttributeError` escape to `cli.main()`'s generic
crash boundary instead of a named `SyncAPIError` -- fixed to match `transition_jira_issue`'s
existing `isinstance` precedent in this same file; 4 low: candidate dedup across pages, a
summary-string pluralization bug, a missing CLI-level `--schedule`/`--dry-run` test, and this
session's own memlog-wording fix), 2 deferred (no CLI surface for per-candidate batch failure
detail; the `fieldValues(first: 50)` cap now exercised board-wide), 4 rejected (all duplicates of
already-adjudicated concerns or speculative/unexploitable). Zero `intent_gap`, zero `bad_spec`.
Full detail: `## Review Triage Log`, "Review pass 2" above.

**Files changed (this pass, commit `2c3d032c9a`):**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py` -- `list_linked_github_items`
  gained `isinstance(nodes, list)`/`isinstance(page_info, dict)`/`isinstance(node, dict)` guards
  and a `seen_item_ids` dedup set; `reconcile_schedule_batch`'s summary singular/plural fix
  (+30/-11 lines against the recovered commit).
- `src/shared/packages/pyforge-steward/tests/conformance/test_sync_duty.py` -- added
  `test_sync_reconcile_schedule_dry_run_via_cli_threads_through_with_no_writes` (+68 lines).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md`
  -- reworded the "5 I/O Matrix scenarios" phrase to name the five scenarios (this repo's tracked,
  non-gitignored governance record).

**Verification performed:** `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- 624
passed (0 failed), zero live network calls. `pixi run -e pyforge-steward pyforge-steward-dogfood`
-- clean. `python scripts/spec_surface_reconcile.py` -- clean, no drift. `ruff check` on all four
touched source/test files -- 4 findings, all confirmed pre-existing and unrelated to this story
(unchanged from dev-1's own already-documented count).

**Follow-up review recommendation: false.** All 5 patches are narrowly-scoped defensive hardening
(shape guards, dedup, a grammar fix), one additive test, and one documentation wording fix --
none change the frozen contract's behavior, none touch `reconcile()`'s own logic, and none carry
API/security/data-model impact. Low volume, low consequence, low breadth.

**Residual risks:** none blocking, beyond what dev-1's own session already recorded above. The
two newly-deferred findings (no CLI surface for per-candidate batch-failure detail; the
board-wide `fieldValues(first: 50)` cap) are real but bounded -- neither blocks this story's own
Acceptance Criteria, and both are pre-existing whole-CLI/whole-module characteristics this
story's new batch mode surfaces more consequentially rather than causes outright.
