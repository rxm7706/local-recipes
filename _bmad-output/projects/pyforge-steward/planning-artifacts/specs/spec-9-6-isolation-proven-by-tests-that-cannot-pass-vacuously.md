---
title: 'Isolation proven by tests that cannot pass vacuously (Epic 9 Story 9.6, pyforge-steward)'
type: 'feature'
created: '2026-08-13'
status: 'done'
baseline_revision: '257094dcc2cf99a95c8553b6c05ae3cc09fe876f'
final_revision: 'bc2be959012a7c777ad3cea9a62e62af604291e2'
review_loop_iteration: 0
followup_review_recommended: false # judged: 1 medium (test-coverage-only) + 2 low patches, no production code, no API/behavior change
context: []
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** CAP-7 requires that the dashboard-isolation guarantees (9.1-9.5) be proven by tests
that impersonate distinct identities and would themselves fail if their guard were removed — "a
suite that cannot fail is a failing suite." Investigation confirms two concrete gaps the epics.md
AC names by name: the cache invariant (9.1, AD-5/CAP-2 — a role-filtered frame must never be
written back to the shared cache) has no test exercising the real `filter_by_role` + real
`get_master_dataset` together across two roles sharing one cache key, and `cache.py`'s own
docstring documents a leak scenario ("an east-role closure warms key='master', ... west role ...
is served east rows") that is asserted in prose but never pinned as an executable regression. The
retention refusal (9.3, AD-7) already carries a genuine mutation-proof case
(`test_purge_expired_entries_rechecks_days_a_subclass_could_have_skipped`,
`test_dashboard_audit.py`) — that AC clause is already satisfied and needs verification, not new
code. Separately, `filter_by_role`/`build_navigation`/`authorize_export` each have real guard
logic but no single test that impersonates two roles and asserts both directions ("privileged
sees more, unprivileged sees less") together, nor any test proving the check would fail if that
guard were removed.

**Approach:** Add one new test file, `tests/unit/test_dashboard_isolation_proof.py`, the CAP-7
proof suite. For each of filtering, navigation, and export: one test using the real production
function that impersonates two roles and asserts both directions in one body, paired with a
second test proving the same assertion fails against a locally-defined guard-removed variant of
that function (never a monkeypatch of production internals). For the cache invariant: one test
proving correct two-role wiring holds (disjoint per-role views, and the raw cached value equals
the complete unfiltered master, not a subset), paired with one test reproducing `cache.py`'s
documented misuse scenario end-to-end, pinning that claim as a real regression. No production
code changes — this is a test-only story.

## Boundaries & Constraints

**Always:**
- Every "isolation is not vacuous" test impersonates 2+ distinct roles/identities in one test
  body and asserts both directions together (never split across separate tests for the same
  guard).
- Every such test is paired with a companion test proving the identical check fails when that
  surface's guard is deliberately removed — the guard-removed variant is a small function defined
  locally in the test file (reproducing what the guard's absence would do), never a monkeypatch of
  the real production module.
- The "holds" half of every pair calls the real production function
  (`filter_by_role`/`build_navigation_view`/`authorize_export`/`get_master_dataset`), never a
  reimplementation.
- New tests live in exactly one new file, `tests/unit/test_dashboard_isolation_proof.py`, matching
  the existing `tests/unit/test_dashboard_*.py` convention.
- Follow the established `pytest.importorskip("django", ...)` + guarded `settings.configure()`
  pattern from sibling files, so the package suite still collects (not errors) when the
  `[dashboard]` extra is absent, and remains compatible regardless of test-collection order.

**Block If:** `pixi run -e pyforge-steward pyforge-steward-test` does not pass green on the
current baseline before any change is made (a pre-existing, unrelated failure) — HALT and report;
a proof suite built over unverified infrastructure is not sound.

**Never:**
- Never add or modify a CI/GitHub Actions workflow. Verified: zero `.github/workflows/*.yml`
  references any `pyforge-*-test` pixi task, for any pyforge package, not just steward — gating
  merges is a repo-wide gap belonging to the separate, already-tracked detectors/fidelity
  initiative (`detectors.yml`'s own header), not this story.
- Never add role-filtering to `audit.py`'s `query_audit_entries` — its unfiltered-by-role read
  surface is a known, already-deferred gap (`DW-FU-9-3-2`); fixing it is production code outside
  a test-type story's mandate.
- Never modify any of the 8 existing `tests/unit/test_dashboard_*.py` files — additive only.
- Never add a runtime role-aware guard to `cache.py` — its docstring and the deferred-work ledger
  already scope that redesign to a future story with a real consumer; this story proves the
  current caller-contract invariant, it does not re-architect it.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `filter_by_role`, real guard | master rows, more tagged role A than role B | A's view is the larger disjoint set, B's the smaller; each filtered independently | No error expected |
| `filter_by_role`, guard removed | same master, local variant returns all rows regardless of role | the two-role isolation assertion raises `AssertionError` | `pytest.raises(AssertionError)` |
| `build_navigation_view`, real guard | pages declared per-role, admin + shared + viewer-only pages | admin's response contains admin+shared paths, not viewer-only; viewer's contains only shared, not admin-only | No error expected |
| `build_navigation_view`, guard removed | same pages, local variant returns all pages regardless of role | the isolation assertion raises `AssertionError` | `pytest.raises(AssertionError)` |
| `authorize_export`, real guard | role in `policy.allowed_roles` vs. role outside it | authorized returns `None` silently; unauthorized raises `ExportUnauthorizedError` | `pytest.raises(ExportUnauthorizedError)` for the unauthorized case |
| `authorize_export`, guard removed | same unauthorized role, local always-authorize variant | the isolation assertion raises `AssertionError` (expected raise never happens) | `pytest.raises(AssertionError)` |
| `get_master_dataset` + `filter_by_role`, correct wiring | two roles, one shared cache key, `fetch` returns the unfiltered master | each role's downstream filter is correct/disjoint; raw cached value equals the full master | No error expected |
| `get_master_dataset`, misuse wiring | first caller's `fetch` closure pre-filters by role before caching | second, different-role caller sharing the key is served the first caller's filtered rows | Asserted directly (documents a real hazard; not a defect fixed in this story) |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/tests/unit/test_dashboard_isolation_proof.py` -- NEW: the
  CAP-7 proof suite, 8 tests across 4 guard-pairs (filtering, navigation, export, cache), using
  `filter_by_role`/`build_navigation_view`/`authorize_export`/`get_master_dataset` from the
  existing `dashboard/filtering.py`, `dashboard/views.py`, `dashboard/export.py`, `dashboard/cache.py`.
- `src/shared/packages/pyforge-steward/tests/unit/test_dashboard_audit.py` -- REFERENCE ONLY, no
  change: lines ~355-361 (`test_purge_expired_entries_requires_a_retention_argument`) and
  ~778-801 (`test_purge_expired_entries_rechecks_days_a_subclass_could_have_skipped`) already
  satisfy the AC's "retention refusal (9.3) carries a mutation-proof case."

## Tasks & Acceptance

**Execution:**
- [x] `tests/unit/test_dashboard_isolation_proof.py` -- NEW -- module docstring + `pytest.importorskip("django", ...)` + guarded `settings.configure(CACHES=...)` mirroring `test_dashboard_views.py`'s minimal block (this file needs no `INSTALLED_APPS`/`DATABASES`, and collects alphabetically after `audit`/`cache`, so it is compatible with the existing race-tolerant convention)
- [x] same file -- `test_filter_by_role_isolation_is_not_vacuous` -- real `filter_by_role`, master rows skewed so one role has strictly more rows than the other, assert each role's set is correct and disjoint in one test body -- CAP-2/CAP-7
- [x] same file -- `test_filter_by_role_isolation_check_fails_if_the_equality_guard_is_removed` -- local `_filter_without_role_guard(master, role)` returning every row unconditionally; run the same isolation assertion against its output inside `pytest.raises(AssertionError)`
- [x] same file -- `test_navigation_isolation_is_not_vacuous_in_either_direction` -- via `build_navigation_view` + hand-built `ASGIRequest` (mirrors `test_dashboard_views.py`'s `_request` helper, duplicated locally per this package's established per-file convention), one test asserting admin's response bytes contain admin+shared paths and omit the viewer-only path, and viewer's contain only shared and omit the admin-only path -- CAP-3/CAP-7
- [x] same file -- `test_navigation_isolation_check_fails_if_the_role_membership_guard_is_removed` -- local `_navigation_view_without_role_guard(pages)` returning every page regardless of role; run the same isolation assertion against it inside `pytest.raises(AssertionError)`
- [x] same file -- `test_export_authorization_isolation_is_not_vacuous` -- real `authorize_export`, one test: authorized role returns `None` with no raise, unauthorized role raises `ExportUnauthorizedError` -- CAP-5/CAP-7
- [x] same file -- `test_export_authorization_isolation_check_fails_if_the_role_check_is_removed` -- local `_authorize_export_without_role_guard(**kwargs)` returning `None` unconditionally; run the same isolation assertion against it inside `pytest.raises(AssertionError)`
- [x] same file -- `test_cache_invariant_holds_under_correct_two_role_wiring` -- real `get_master_dataset` + real `filter_by_role`, two roles sharing one cache key with a correct (unfiltered) `fetch`, assert each role's downstream-filtered view is correct/disjoint AND the raw backend-stored value equals the complete unfiltered master -- the AC-named mutation-proof case for AD-5/CAP-2
- [x] same file -- `test_cache_invariant_is_violated_when_a_caller_pre_filters_before_caching` -- reproduce `cache.py`'s own documented misuse (first caller's `fetch` closure calls `filter_by_role` before returning, warming the shared key); assert the second, different-role caller's result equals the first caller's filtered rows, not its own -- pins the module docstring's "Demonstrated" claim as an executable regression

**Acceptance Criteria:**
- Given the new proof suite, when `pixi run -e pyforge-steward pyforge-steward-test -k test_dashboard_isolation_proof` runs, then all 8 new tests pass.
- Given `test_filter_by_role_isolation_check_fails_if_the_equality_guard_is_removed`,
  `test_navigation_isolation_check_fails_if_the_role_membership_guard_is_removed`, and
  `test_export_authorization_isolation_check_fails_if_the_role_check_is_removed`, when each runs,
  then it demonstrates — via `pytest.raises(AssertionError)` around the same isolation assertion
  used by that surface's "is not vacuous" test — that the check fails against a guard-removed
  variant, proving it is not vacuous.
- Given `test_cache_invariant_holds_under_correct_two_role_wiring`, when two roles fetch through
  `get_master_dataset` + `filter_by_role` sharing one cache key, then each receives its own
  disjoint filtered rows and the raw cached value equals the complete unfiltered master dataset.
- Given `test_cache_invariant_is_violated_when_a_caller_pre_filters_before_caching`, when a
  caller's `fetch` closure pre-filters by role before caching, then a second, different-role
  caller sharing the same key receives the first caller's filtered rows.
- Given the retention-refusal AC, when
  `pixi run -e pyforge-steward pyforge-steward-test -k "test_purge_expired_entries_requires_a_retention_argument or test_purge_expired_entries_rechecks_days_a_subclass_could_have_skipped"`
  runs, then both existing tests in `test_dashboard_audit.py` pass, confirming "the retention
  refusal (9.3) carries a mutation-proof case" is already satisfied.
- Given the whole `pyforge-steward` package, when `pixi run -e pyforge-steward pyforge-steward-test` runs, then the full suite (existing + 8 new tests) passes with zero regressions, and `tests/meta/test_invariants.py`'s django-import-boundary guard is unaffected (the new file adds no production import).

## Spec Change Log

## Review Triage Log

### 2026-08-13 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 1, low 2)
- defer: 1: (high 0, medium 1, low 0)
- reject: 5: (high 0, medium 0, low 5)
- addressed_findings:
  - `[medium]` `[patch]` Doubly-confirmed by both Blind Hunter and Edge Case Hunter (independently, no shared context): CAP-1's fail-closed `role=None` default — explicitly documented as security-critical in `filter_by_role`, `build_navigation`/`build_navigation_view`, and `authorize_export`'s own docstrings — was never exercised anywhere in this "isolation proven, not claimed" suite; `_request`'s `include_role_key=False` parameter existed but was dead code. Fixed by adding `test_filter_by_role_degrades_to_zero_rows_with_no_identity`, `test_navigation_degrades_to_no_pages_with_no_identity`, and `test_export_authorization_degrades_to_refusal_with_no_identity`, each calling the real production function with `role=None` and asserting the documented fail-closed behavior.
  - `[low]` `[patch]` `test_cache_invariant_holds_under_correct_two_role_wiring` called `get_master_dataset` twice with the identical `fetch` closure object, while its own comment said "two different-role callers" and its sibling misuse test correctly used two distinct closures — fixed by giving each caller its own closure (`east_caller_fetch`/`west_caller_fetch`), plus an explicit assertion that the second caller's fetch never runs (served from the first caller's cache write), matching the misuse test's rigor.
  - `[low]` `[patch]` The file's module docstring described itself as covering CAP-7 without acknowledging that the AC's "retention refusal (9.3)" half is satisfied by pre-existing tests in a different file (`test_dashboard_audit.py`), leaving a reader with no way to find that connection from this file alone — fixed by adding a paragraph naming the specific existing test and the reasoning already recorded in this spec's Design Notes.
  - `[medium]` `[defer]` `DW-FU-9-6` — this file's `settings.configure()` block (matching `test_dashboard_views.py`'s existing minimal pattern) aborts the whole run with `AssertionError: INSTALLED_APPS is []` when collected ahead of `test_dashboard_audit.py` on the command line; reproduced against both this new file and, identically, the pre-existing `test_dashboard_views.py` — confirming the pattern predates this story (Story 9.2) and is not this story's to fix. Latent in normal use (alphabetical full-suite collection always lets `test_dashboard_audit.py`'s fuller declaration win), real when a developer cherry-picks files. The actual fix (a shared `conftest.py`) touches the three existing sibling files this story's spec forbids modifying.
  - `[low]` `[reject]` (5, all noise relative to this story's stated scope, verified independently): the guard-removed variants only demonstrate total guard removal, not a partially-weakened check such as substring matching (a materially larger mutation-testing effort than CAP-7's literal "fails when its guard is removed" asks for, and not named by the AC); `_navigation_view_without_role_guard` also drops `build_navigation_view`'s wiring-time path-uniqueness validation alongside the role guard (irrelevant to what the paired test actually checks — page visibility per role); the module docstring's "privileged sees more, unprivileged sees less" framing doesn't literally describe the filtering pair's peer (east/west) roles (the per-function docstrings there already say "disjoint", not "privileged", so no reader is actually misled within the file); `test_cache_invariant_is_violated_when_a_caller_pre_filters_before_caching`'s name could be misread as reporting a live regression rather than a documented, pinned demonstration (its own docstring immediately clarifies "not a defect fixed by this story"); coverage is exclusively two-actor with no 3+-role test (stronger than what CAP-7 or the epics.md AC ask for — "privileged... unprivileged", i.e. two).

## Design Notes

**Why a guard-removed local variant, not a monkeypatch.** `filter_by_role`'s guard is an inline
`value == role` comparison, not a named, patchable seam; `build_navigation`'s and
`authorize_export`'s guards are similarly inline. Reproducing the guard's absence as a small,
explicitly-named local function (`_filter_without_role_guard`, etc.) makes the "guard removed"
state readable and intentional, mirrors this package's own established idiom for demonstrating a
bug class explicitly (e.g. `test_dashboard_audit.py`'s subclass-bypass test), and avoids coupling
the proof suite to production internals that could change shape without changing behavior.

**Why the cache invariant needs two tests, not one.** `cache.py` has no runtime guard for CAP-2 —
its own docstring states plainly that the invariant is a caller contract it cannot enforce. A
single "holds" test would prove correct usage works but not that the suite can catch a real
regression; the second test reproduces the exact misuse the module docstring already narrates in
prose, converting a claim into an executable, pinned demonstration — directly answering CAP-7's
"demonstrated rather than claimed."

**Why the retention refusal needs no new code.** `test_purge_expired_entries_rechecks_days_a_subclass_could_have_skipped`
already bypasses one guard (`AuditRetention.__post_init__`, via a subclass skipping validation)
and proves a second, independent guard (`purge_expired_entries`'s own re-check) still catches it,
plus asserts the refused purge deletes nothing — the exact shape CAP-7 asks for. Adding a
duplicate test would be redundant coverage, not new proof.

**Why CI-gating is out of scope.** CAP-7's SPEC-level "intent" prose mentions the suite running
"before a merge is permitted," but the epics.md Given/When/Then AC — the authoritative bar for
this story — does not. No pyforge-* package in this repo has its pytest suite wired into any
GitHub Actions workflow today; wiring only pyforge-steward's would be inconsistent scope creep
into a repo-wide gap the `detectors.yml` header already names and tracks separately.

## Verification

**Commands:**
- `pixi run -e pyforge-steward pyforge-steward-test` -- expected: full suite green, including the
  new `tests/unit/test_dashboard_isolation_proof.py` and zero regressions in the pre-existing
  suite. (Confirmed at 613 passed = 602 pre-story baseline + 11 new -- see Auto Run Result.)
- `pixi run -e pyforge-steward pyforge-steward-test -k test_dashboard_isolation_proof -v` --
  expected: all tests in the new file pass, names matching the Tasks list above plus the 3
  fail-closed tests added in review pass 1.
- `ruff check src/shared/packages/pyforge-steward/tests/unit/test_dashboard_isolation_proof.py` --
  expected: zero findings (or only the pre-existing repo-wide baseline, verified via `git stash`).

## Auto Run Result

**Summary:** Added `tests/unit/test_dashboard_isolation_proof.py`, the CAP-7 isolation-proof suite --
4 guard-pairs (filtering, navigation, export authorization, cache invariant), each an
"is-not-vacuous" test using the real production function plus a companion proving the same
assertion fails against a locally-defined guard-removed variant, and 3 CAP-1 fail-closed
`role=None` tests added during review. No production code changed.

**Files changed:**
- `src/shared/packages/pyforge-steward/tests/unit/test_dashboard_isolation_proof.py` -- NEW, 11
  tests across 4 guard-pairs plus 3 fail-closed regressions.

**Review findings breakdown (2026-08-13 pass):** patch 3 (medium 1, low 2) -- all fixed; defer 1
(medium, `DW-FU-9-6`, a pre-existing `settings.configure()` collection-order hazard predating this
story); reject 5 (low, noise). Full detail in the Review Triage Log above.

**Follow-up review recommendation:** false -- test-coverage-only patches, no production code, no
API/behavior change.

**Verification performed:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- 613 passed (602 pre-story baseline
  + 11 new), zero regressions.
- `pixi run -e pyforge-steward pyforge-steward-test -k test_dashboard_isolation_proof -v` -- all 11
  tests in the new file pass.
- `ruff check` on the new file -- findings match the pre-existing repo-wide baseline shape
  (`RUF100`/non-enabled-`E402`-noqa, `I001`, `RET501`), confirmed by parity against untouched
  sibling file `test_dashboard_views.py` and the package-wide baseline; no new finding class
  introduced.
- `python scripts/spec_surface_reconcile.py` -- **repair pass (this session):** the story's own dev
  commit (`8f9cd4ee47`) landed the new test file under `spec-pyforge-steward`'s governed
  package-path glob without that spec's `.memlog.md` naming the path, failing the loop's S-13.7
  verify gate (`[drift] ... test_dashboard_isolation_proof.py added but the spec's memlog did not
  move`). Repaired by appending a `RECONCILES` entry to
  `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md`
  naming the new path (matching the established convention used by every prior Story 9.x entry in
  that memlog) and stamping the baseline scoped to that one spec
  (`python scripts/spec_surface_check.py --write-baseline --spec pyforge-steward/spec-pyforge-steward`),
  committed as `bc2be959012a7c777ad3cea9a62e62af604291e2`. This governance-bookkeeping fix is
  outside this story's own `<intent-contract>` and Code Map (it reconciles the surrounding
  `spec-pyforge-steward` SPEC's drift ledger, not this story's own artifact) and changes no test or
  production code. Re-ran clean: `OK: every tracked file governed or allowlisted; no drift.`

**Residual risks:** `DW-FU-9-6` remains open (deferred, pre-existing, latent under normal
alphabetical full-suite collection) -- its real fix is a shared `conftest.py`, out of this
test-only story's mandate per its own `Never` constraints.

