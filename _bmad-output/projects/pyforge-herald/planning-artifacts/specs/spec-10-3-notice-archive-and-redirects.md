---
title: 'Notice Archive & Redirects'
type: 'feature'
created: '2026-08-08'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** The original epics-with-stories.md AC (lines 895-901) asks for "archive indexing"
at an HTTP-shaped path (`/operations/notices/[category]/[YYYY-MM]/[component].md`) and "redirect
generation when component renamed" so a renamed component's old URL never 404s. That AC presumes
a live web backend serving those paths -- Herald has none (see
`docs/dreams/herald-moments-2-4-live-backend.md`).

**Approach (scaled down):** archive indexing is Story 10.1's local index, already fast
(`list_notices`/`get_notice` read `.herald/notices-index.json`, never re-globbing `notices/`).
Redirects are file-based bookkeeping only: `herald notice archive --rename OLD NEW` records
`redirects[OLD] = NEW` in the same index document; `get_notice`/`publish_notice`/`close_notice`
resolve a component name through this map before looking it up. This is **not an HTTP redirect**
-- explicitly documented in `notices.py`'s module docstring and repeated here, since no server
exists to serve one and the original AC's "permanent URLs"/"no 404s" language does not apply to a
CLI.

**Judgment call: renaming requires the target to already exist.** `archive_rename` refuses when
`new_component` has no notice yet ("cannot redirect to ... no notice exists for it yet") --
redirecting to nothing would silently produce a dangling pointer a later `get_notice` call could
never resolve. The operator's expected sequence is: author the notice under the new name first
(or it already existed), then record the redirect.

**Judgment call: redirect resolution is capped, not recursive-unbounded.** `_resolve_component`
follows at most `_MAX_REDIRECT_HOPS` (10) hops and raises `HeraldError` on a cycle or an
excessively long chain -- a hand-edited or buggy index producing `A -> B -> A` must fail
structurally (AD-6 discipline, mirrored from `state.py`'s own corruption-handling posture) rather
than hang the process.

## Boundaries & Constraints

**Always:**
- `archive_rename(repo_root, old, new)` requires `new` to already have a notice entry; refuses a
  self-redirect (`old == new`); refuses silently overwriting an existing redirect for `old`
  (explicit `HeraldError` naming the current target).
- `get_notice`/`publish_notice`/`close_notice` all resolve `component` through `redirects` before
  looking up `notices` -- a caller naming the *old* component transparently reaches the *new*
  one's record.
- `author_notice` refuses authoring under a component name that is currently a redirect *source*
  ("author the notice under that name" -- naming the resolved target).

**Block If:** N/A -- local file bookkeeping only, no network, no spike gate.

**Never:**
- No HTTP redirect, no server-side URL rewrite -- the CLI's own docstring and this spec both
  state this explicitly so a later reader does not mistake the file-based map for a web-serving
  concern.

## I/O & Edge-Case Matrix

| Scenario | Expected |
|---|---|
| `archive_rename("old", "new")`, `new` already published | redirect recorded; `get_notice("old")` returns `new`'s record |
| `archive_rename("old", "missing")` | `HeraldError("... no notice exists for it yet")` |
| `archive_rename("x", "x")` | `HeraldError("cannot redirect a component to itself")` |
| `archive_rename` called twice for the same `old` | second call: `HeraldError("... already redirects to ...")` |
| `publish_notice("old")` where `old -> new` and `new` is already published | `HeraldError("... already published")` -- proves resolution happens *before* the publish-state check, not a silent no-op |
| Redirect cycle (hand-edited index) | `HeraldError("... redirect cycle ...")`, never an infinite loop |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/notices.py` -- (Story 10.1's module) --
  `archive_rename`, `_resolve_component`, `_MAX_REDIRECT_HOPS`.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` -- (Story 10.4's wiring) --
  `notice archive --rename OLD NEW` subparser + `_run_notice_archive`.
- `src/shared/packages/pyforge-herald/tests/test_notices.py` -- rename/redirect test block:
  redirect-then-get, target-must-exist, self-redirect refusal, double-redirect refusal,
  redirect-then-publish (proves resolution happens before the lifecycle check).
- `src/shared/packages/pyforge-herald/tests/test_cli_notice_epic10.py` -- CLI-level rename +
  redirect-then-get round trip, write-gate coverage on `notice archive`.

## Design Notes

**Why cap redirect hops instead of just detecting the immediate `A -> A` case?** A single-hop
self-redirect check would not catch a longer cycle produced by two separate `archive_rename`
calls against a hand-edited or corrupted index (`A -> B` from one call, then a hand-edit adding
`B -> A`) -- since `archive_rename` itself refuses to *create* a cycle through the CLI, the
cap exists for the corrupted-file case the same way `state.py`'s duplicate-key rejection exists
for a corrupted `bridge-state.json`: AD-6's "fail structurally" discipline applied uniformly,
not just to inputs this module's own writers can produce.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 595 passed, 2 skipped.
- `ruff format --check` / `ruff check` -- clean.

## Spec Change Log

## Review Triage Log

### 2026-08-08 -- Adversarial review pass (Blind Hunter + Edge Case Hunter, no shared context)

- `[investigated]` `[not applied]` **Blind Hunter flagged that `archive_rename` doesn't
  refuse redirecting a component that already has its own, distinct, live notice** --
  described as "silent shadowing" (redirecting `svc-a` to `svc-b` when both are
  independently authored notices leaves `svc-a`'s own content unreachable via `get`, while
  `list`/the web export still enumerate both). On investigation this is NOT a defect: this
  spec's own function docstring and this file's own tests
  (`test_archive_rename_redirects_get_to_the_new_component`,
  `test_publish_follows_a_redirect` in `test_notices.py`) explicitly exercise and assert
  on exactly this shape as the documented normal workflow -- author under the old name,
  author under the new name (the "requires `new_component` to already have a notice"
  precondition literally cannot be satisfied any other way), then redirect old -> new. An
  initial patch adding the refusal broke 8 previously-green tests across
  `test_notices.py`/`test_cli_notice_epic10.py` and was reverted once the contradiction
  with this spec's own tested contract was confirmed. No code change made.
- `addressed_findings`: 0 (1 finding investigated and correctly not applied). No
  `intent_gap`, no `bad_spec`, no `defer`, no `reject`.

**Re-verification (2026-08-08):** `pixi run --frozen -e pyforge-herald pyforge-herald-test`
-- 599 passed, 2 skipped (all pre-existing rename/redirect tests for this story remain
green, unmodified).

**Follow-up review recommendation:** none outstanding for this story.
