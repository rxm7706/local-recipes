---
title: 'An unauthorized page is absent, not hidden (Epic 9 Story 9.2, pyforge-steward)'
type: 'feature'
created: '2026-08-11'
status: 'done'
baseline_revision: 'f6b3e8f2b32efdedb498c47fa2352f5e17bb4594'
final_revision: '2c3a04771c6f17515527a129db0ddaf2ef852716'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-secure-live-dashboards/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-secure-live-dashboards-2026-08-09/ARCHITECTURE-SPINE.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** Story 9.1 shipped identity extraction and the declaration schema but explicitly implements no filtering ("declared, not implemented"); CAP-2's actual row-filtering, CAP-3's role-built navigation, and AD-6's filter-then-search API shape have zero implementation, and two Story 9.1 deferrals (un-namespaced `scope` keys, an `get_master_dataset()` cache key an adopter could misuse to store a role-filtered frame) name this story as their first real consumer.

**Approach:** Add three django-free primitives to `pyforge.steward.dashboard` — a `Page` declaration + `build_navigation(role, pages)` that returns only pages the role may see (CAP-3), and a `filter_by_role(master, declaration, role)` producing a distinct `RoleFilteredRows` type that a new `search(frame, predicate)` is the *only* way to query, so passing an unfiltered master object to `search()` fails by type, not by convention (AD-6) — plus one Django view factory, `build_navigation_view(pages)`, that renders the filtered navigation as JSON so CAP-3's "absent from the served response" claim is provable by inspecting an actual `HttpResponse`, not by reading code.

## Boundaries & Constraints

**Always:**
- `role` is read from `request.scope.get("dashboard_role")` (Story 9.1's `DashboardIdentityMiddleware` output) and treated as an opaque string compared by exact equality only — no `.strip()`/normalization added here. Story 9.1 review pass 3 explicitly deferred role/identity normalization to Story 9.3's audit rows; this story inherits that deferral rather than re-deciding it.
- `role=None` (no identity established) degrades to zero visible pages and zero visible rows — never an error, never every page/row. This matches CAP-1's "degrades to a known-unprivileged identity, never an elevated one."
- `filter_by_role`'s only entry point into the master dataset is Story 9.1's `get_master_dataset()` return value; `filter_by_role` never accepts or derives a per-role cache key, and its output (`RoleFilteredRows`) is never written back into the shared cache — closing the CAP-2 misuse Story 9.1 pass 4 demonstrated (an east-role closure warming a shared key, served to a west-role caller).
- `search()`'s sole parameter accepting row data is typed and runtime-checked as `RoleFilteredRows`; a caller passing `get_master_dataset()`'s raw return value (or any other type) raises `TypeError` before any row is inspected — this is AD-6's "enforced by signature," proven by a test that calls `search()` with the unfiltered master and asserts the raise.
- `Page` and `RoleFilteredRows` are frozen dataclasses with construction-time validation mirroring `declarations.py`'s style (named, loud errors — never a silent empty result from a malformed declaration).
- `navigation.py` and `filtering.py` import neither `django` nor `channels` (mirrors `middleware.py`/`declarations.py`); only `views.py` needs `django`.

**Block If:**
- If constructing a Django `ASGIRequest` directly from a hand-built `scope` dict (verified feasible pre-implementation: only `scope["method"]` and `scope["path"]` are required by the installed Django 5.2 `ASGIRequest.__init__`, everything else defaults) proves insufficient to produce a real `HttpResponse` from `build_navigation_view` in a test — HALT and report. CAP-3's acceptance criterion requires proof by inspecting an actual response, not a bare function-return assertion.

**Never:**
- Implement the audit trail (9.3), export gating (9.4), the deployment perimeter (9.5), the proof suite (9.6), or static export (9.7) — foundation and this story only.
- Add `channels`, `channels_redis`, or `daphne` — nothing here needs them.
- Commit the master dataset to a specific shape beyond "a sequence of row-mappings" (`Sequence[Mapping[str, Any]]`); no `pandas` dependency is introduced (the architecture Stack table names no dataframe library for the library layer, only for adopters).
- Add URL routing (`urls.py`) or a template — `build_navigation_view` is a plain view callable an adopter wires into their own `urlpatterns`, matching AD-1's "library provides the pipeline," not the routing.
- Treat an unrecognized role (present but outside `declaration.roles`) the same as `role=None` — a role string that fails to match the declared vocabulary is a configuration defect and raises loudly (`ValueError` naming the role), never silently degrading like the no-identity case.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Role matches some declared pages | `role="viewer"`, 3 `Page`s, 1 declares `roles=("viewer",)` | `build_navigation` returns a 1-tuple containing only that page | No error expected |
| No identity (`role=None`) | any `Page` list | `build_navigation` returns `()` | No error expected |
| `Page` declared with empty `roles` | `Page(path=..., label=..., roles=())` | — | `ValueError` at construction naming the empty field |
| Filter by a declared role | master rows across two roles' data, `role="east"` in `declaration.roles` | `RoleFilteredRows` containing only rows where `row[access_column] == "east"` | No error expected |
| Filter by `role=None` | master has rows | `RoleFilteredRows` with zero rows | No error expected (fail-closed degrade) |
| Filter by an undeclared role | `role="superadmin"` not in `declaration.roles` | — | `ValueError` naming the offending role |
| Row missing the declared access column | one row lacks `declaration.access_column` | — | clear error naming the missing column and the row's index |
| `search()` given the raw master object | e.g. the list `get_master_dataset()` returned, not a `RoleFilteredRows` | — | `TypeError` before any row is inspected; master never searched |
| `search()` given a real `RoleFilteredRows` | a predicate matching a subset | tuple of only the matching rows | No error expected |
| Navigation view, low-privilege role | `build_navigation_view(pages)` called with a request whose scope role sees 1 of 3 pages | `response.content` (JSON) contains that page's path/label and *no* trace of the other two — asserted on the serialized bytes, not on a Python list | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/navigation.py` -- NEW: `Page` frozen dataclass (path, label, roles) with construction-time validation; `build_navigation(role, pages)` -- CAP-3
- `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/filtering.py` -- NEW: `RoleFilteredRows` frozen wrapper, `filter_by_role(master, declaration, role)`, `search(frame, predicate)` -- CAP-2's filtering half + AD-6's filter-then-search API shape
- `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/views.py` -- NEW: `build_navigation_view(pages)`, a Django view factory returning JSON-rendered navigation -- CAP-3's "absent from the served response" proof surface
- `src/shared/packages/pyforge-steward/tests/unit/test_dashboard_navigation.py` -- NEW
- `src/shared/packages/pyforge-steward/tests/unit/test_dashboard_filtering.py` -- NEW
- `src/shared/packages/pyforge-steward/tests/unit/test_dashboard_views.py` -- NEW: constructs a real Django `ASGIRequest` from a hand-built scope, calls the view, inspects `response.content`
- `src/shared/packages/pyforge-steward/tests/meta/test_invariants.py` -- MODIFY: add `navigation.py` and `filtering.py` to the django-free module list already covering `middleware.py`/`declarations.py`/`__init__.py`

## Tasks & Acceptance

**Execution:**
- [x] `dashboard/navigation.py` -- implement `Page` + `build_navigation` -- CAP-3's declaration + builder
- [x] `dashboard/filtering.py` -- implement `RoleFilteredRows`, `filter_by_role`, `search` -- CAP-2's filtering half, AD-6's signature-enforced ordering
- [x] `dashboard/views.py` -- implement `build_navigation_view` reading `request.scope.get("dashboard_role")` -- the testable "served response" surface
- [x] `tests/unit/test_dashboard_navigation.py` -- exercise all navigation I/O-matrix rows
- [x] `tests/unit/test_dashboard_filtering.py` -- exercise all filtering/search I/O-matrix rows, including the `TypeError`-on-master-passed-to-`search` proof
- [x] `tests/unit/test_dashboard_views.py` -- build a real `ASGIRequest`, call the view, assert the restricted page's path/label are absent from `response.content` bytes
- [x] `tests/meta/test_invariants.py` -- extend the django-free guard's file list to include `navigation.py` and `filtering.py`

**Acceptance Criteria:**
- Given a caller's role, when `build_navigation` runs against a set of declared pages, then the returned tuple contains only pages whose declared `roles` include that role, and a role of `None` returns an empty tuple.
- Given a low-privilege role and a Django request built from a real ASGI scope, when `build_navigation_view(pages)` handles it, then the restricted page's path and label are absent from the serialized response body (checked on the bytes, not a pre-serialization Python object).
- Given a master dataset and a declared role in the vocabulary, when `filter_by_role` runs, then the result is a `RoleFilteredRows` containing only rows whose `access_column` value equals that role, and the master dataset itself is never mutated or written back to any cache.
- Given any object that is not a `RoleFilteredRows`, when it is passed to `search`, then `search` raises `TypeError` without inspecting any row.
- Given `pyforge-steward` installed without the `[dashboard]` extra, when `tests/meta/test_invariants.py` runs, then `navigation.py` and `filtering.py` still import cleanly and are confirmed django-free by the extended guard.

## Spec Change Log

## Review Triage Log

### 2026-08-12 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3 (high 0, medium 2, low 1)
- defer: 2 (high 0, medium 0, low 2)
- reject: 11 (high 0, medium 0, low 11)
- addressed_findings:
  - `medium` `patch` `filter_by_role` appended references to `master`'s own row dicts directly into the returned `RoleFilteredRows` (`matched.append(row)`), so a caller mutating a result row could silently corrupt the shared master dataset it was filtered from. Fixed by copying each matched row (`dict(row)`) before appending.
  - `medium` `patch` `build_navigation` (and the `pages` closed over by `build_navigation_view`) iterated its `pages` parameter twice with no normalization; a one-shot iterable would pass the type-check pass then be silently exhausted before the filtering pass, permanently returning zero pages for every role. Fixed by materializing `pages` into a tuple once, at both call sites.
  - `low` `patch` `filtering.py` imported `Sequence`/`Mapping` from `collections.abc` while every sibling module in the package (`middleware.py`, `navigation.py`, `views.py`) imports the equivalent generics from `typing`. Aligned `filtering.py` to `typing.Mapping`/`typing.Sequence` for consistency.

### 2026-08-12 — Review pass 2
- intent_gap: 0
- bad_spec: 0
- patch: 4 (high 0, medium 1, low 3)
- defer: 1 (high 0, medium 0, low 1)
- reject: 8 (high 0, medium 0, low 8)
- addressed_findings:
  - `medium` `patch` `filter_by_role`'s `matched.append(dict(row))` was only a shallow copy, so a nested mutable value (e.g. a list/dict field) inside a matched row was still the same object shared with `master` — contradicting the function's own documented "never mutates ... never reach back into the master dataset" guarantee, confirmed by execution. Fixed by deep-copying each matched row (`copy.deepcopy(row)`) instead.
  - `low` `patch` `filter_by_role`'s `master` parameter and `build_navigation`/`build_navigation_view`'s `pages` parameter raised bare, unhelpful built-in `TypeError`s on a non-iterable input (e.g. `None`), unlike every other parameter in these modules which gets a descriptive, purpose-built error message. Added explicit `isinstance(..., Sequence)` checks with descriptive messages to all three, matching the modules' established validation style.
  - `low` `patch` Three already-implemented validation branches had zero test coverage: `build_navigation`'s per-page `isinstance(page, Page)` guard, `build_navigation_view`'s non-`Page`/duplicate-path guards, and `search`'s non-callable-predicate guard. Added one test per branch.
  - `low` `patch` `build_navigation_view`'s `Cache-Control: private, no-store` paired a redundant `private` directive with `no-store`, which alone already forbids storage by any cache, private or shared. Dropped `private`.

## Design Notes

**Two independent declared vocabularies, not one shared list.** `Page.roles` (page visibility) and `AccessDeclaration.roles` (row visibility) are deliberately separate declarations rather than one shared role list: CAP-2 and CAP-3 are listed as independent capabilities in the architecture's Capability→Architecture Map, and a dashboard may reasonably want a page visible to a role that sees no rows filtered by that same role name (e.g. an "auditor" page-only role). Nothing in the Spec or architecture ties them together.

**Why a `TypeError`, not a documentation convention, is what AD-6 means by "enforced by signature."** The rejected alternative in AD-6 is literally "documenting the order and trusting adopters to honour it." A runtime `isinstance` check on `search()`'s parameter cannot stop a determined caller from hand-constructing a `RoleFilteredRows` around unfiltered rows, but it does stop the accidental misuse the AD's rationale describes (search-then-filter by carelessness, not by malice) -- the same scope Story 9.1's `TrustedIngress`/`AccessDeclaration` type checks already operate in.

**Master dataset shape.** A `Sequence[Mapping[str, Any]]` -- plain row-mappings, not a `pandas.DataFrame`. The architecture's Stack table names no dataframe library at the library layer (Vizro, the first adopter, is explicitly framework-neutral per AD-8); adopters using a DataFrame convert with `.to_dict("records")` before caching.

**Implementation-time judgment calls, not covered above:**
- `Page.path`/`Page.label` reject blank AND whitespace-padded values, mirroring `AccessDeclaration.access_column`'s existing pattern exactly (per the task prompt's explicit steer) -- a padded path is not where the route is actually mounted, so rejecting rather than trimming keeps the declaration meaning what it says.
- `RoleFilteredRows` gained its own construction-time validation (rejects a non-tuple `rows`, and a non-`Mapping` element) to satisfy the Boundaries & Constraints line "`Page` and `RoleFilteredRows` are frozen dataclasses with construction-time validation mirroring `declarations.py`'s style" -- the Code Map's one-line description ("frozen wrapper") didn't spell this out, but the constraint above does.
- `filter_by_role`'s missing-access-column case raises `KeyError` (caught from `row[column]` and re-raised with the row index and column name in the message) rather than a bare `ValueError` -- one of the two shapes the task prompt explicitly permitted ("catch the KeyError and re-raise ... or check with `.get()`/`in` first — your call").

## Verification

**Commands:**
- `pixi run -e pyforge-steward pyforge-steward-test` -- expected: full suite green, including the three new `tests/unit/test_dashboard_*.py` files and the extended `tests/meta/test_invariants.py`
- `pixi run -e pyforge-steward steward --version` -- expected: succeeds unchanged, evidence the base package still runs without the dashboard code path being invoked

## Auto Run Result

**Summary.** This session opened on a `done` spec whose implementation (commit `6725b773fd`, produced by a prior invocation in this same bmad-loop run) had been dropped from the branch — the worktree's `HEAD` had reverted to its parent, `1fe009f099`, while the finished commit survived only on a run-local `attempt-preserve/…` safety branch. Since that commit's parent was exactly this branch's `HEAD` (a clean fast-forward, not a rebase/restore-patch situation), the branch was fast-forwarded (`git merge --ff-only`) to restore it non-destructively, verified green, then routed to a fresh Review pass per the `done`-spec rule: two independent reviewers (Blind Hunter, Edge Case Hunter) in parallel on the diff isolated to this story's own commit (the recorded `baseline_revision` predates Story 9.5 landing on this branch, so a literal diff-since-baseline would have pulled in unrelated, already-reviewed code), findings deduplicated and independently re-verified against the actual source before triage.

**Files changed this session:**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/filtering.py` -- MODIFY: `filter_by_role` now deep-copies matched rows (closing a nested-value aliasing gap the shallow `dict(row)` copy left open) and validates `master` is a `Sequence` before iterating it.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/navigation.py` -- MODIFY: `build_navigation` validates `pages` is a `Sequence` before materializing it.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/views.py` -- MODIFY: `build_navigation_view` validates `pages` the same way; dropped the redundant `private` directive from `Cache-Control: private, no-store`.
- `src/shared/packages/pyforge-steward/tests/unit/test_dashboard_filtering.py`, `test_dashboard_navigation.py`, `test_dashboard_views.py` -- MODIFY: added coverage for the previously-untested `isinstance(page, Page)` guard, `build_navigation_view`'s non-`Page`/duplicate-path guards, `search`'s non-callable-predicate guard, the new `master`/`pages` type checks, and the deep-copy fix.
- `_bmad-output/projects/pyforge-steward/implementation-artifacts/deferred-work.md` -- 1 new Tier-3 entry, `DW-FU-9-2-3`.

**Review findings breakdown (pass 2):** 18 raw findings from the two reviewers (11 Blind Hunter, 7 Edge Case Hunter), deduplicated to 13 distinct findings. 4 patches applied (0 high / 1 medium / 3 low), 1 deferred to the ledger (low), 8 rejected as noise after independent re-verification against the source and spec — mostly prose-precision nitpicks on docstring claims, and edge cases outside this story's stated boundaries (see Review Triage Log for the per-finding rationale). No intent_gap, no bad_spec.

**Follow-up review recommendation:** `false`. The one medium fix (deep-copying filtered rows) is a narrow, well-understood one-line change mirroring a pattern the prior pass already applied; the remaining three patches are mechanical (validation-message consistency, test-only additions, a header-directive trim). No API-shape change, no new capability, no change to any spec-required behavior.

**Verification performed:**
- `pixi run -e pyforge-steward pyforge-steward-test` -- 484 passed (477 + 7 new tests from this pass).
- `pixi run -e pyforge-steward steward --version` -- `steward 0.1.0`, exit 0.
- `git status --short` before committing showed exactly the six files this pass touched — no stray changes.

**Residual risks:** `DW-FU-9-2` / `DW-FU-9-2-2` (carried over from pass 1, see ledger) -- the `dashboard_role` scope-key duplication between `middleware.py`/`views.py`, and the duplicate-path guard's byte-identical-only comparison. `DW-FU-9-2-3` (new, see ledger) -- a whitespace-padded role (stored verbatim by Story 9.1's middleware whenever non-blank) is refused loudly by `filter_by_role` but silently emptied by `build_navigation` for the same request; root cause is Story 9.1's already-deferred role-normalization decision, out of this story's scope to resolve.
