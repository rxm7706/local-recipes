---
title: 'Story 11.5: Verification reaches across project boundaries'
type: 'feature'
created: '2026-08-21'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 'dddaf50c8baf575dc469733a01f60755503bdc69'
final_revision: '3b837f4bc0ecccdde19f2f4c554b7e6cce8fade8'
---

<intent-contract>

## Intent

**Problem:** A due-for-verification entry in project A can genuinely be fixed by a commit in
project B (the real `atlas DW-I5-1` case: an atlas ledger entry resolved in marshal's
`core/policy.py`). Nothing today tells a verifying agent it should look beyond the owning
project's own tree, and there is no discoverable, machine-readable map of sibling project code
roots — only tribal knowledge (`_bmad-output/projects/<slug>/` ↔ `src/shared/packages/<slug>/`
by directory-name convention). `apply_verification_verdicts.py` (Story 11.4) already accepts
evidence citing any file:line unmodified, so nothing structurally blocks a cross-project close —
the gap is purely discoverability, never a technical sandbox.

**Approach:** Add one small, pure, read-only helper to `chain.py` that maps every known project
slug to its real code root, and surface it as a new evidence key on every `due-for-verification`
Finding (excluding the entry's own project) so a verifying agent sees, right on the finding it is
investigating, exactly which other project trees exist to check.

## Boundaries & Constraints

**Always:**
- Stay pure/read-only: `pyforge.doctor.sources` is read-only by construction
  (`tests/meta/test_read_only_guard.py` AST-scans every module for write call sites).
- Discover sibling projects via filesystem/`git` reads only — never import another station's
  package (`tests/meta/test_source_independence.py` forbids `pyforge.marshal`/`pyforge.atlas`/etc.
  imports from any `sources/*.py` module).
- Leave Stories 11.1–11.3's existing Finding shape, message text, and behavior unchanged for
  every case that doesn't touch the new evidence key — no regression in
  `test_sources_chain_due_for_verification.py`'s existing ~48 tests.
- A project slug counts as having a code root only when `src/shared/packages/<slug>/` actually
  exists as a directory under `target` — degrade to omitting it, never guess or hallucinate a path.

**Block If:** none identified — this is a mechanical, additive discoverability change with clear
precedent (`_known_projects()` in `scripts/apply_verification_verdicts.py`) and no ambiguity in
scope.

**Never:**
- Never write to any project's ledger or code from this helper — writing stays
  `apply_verification_verdicts.py`'s exclusive job, unchanged by this story.
- Never re-derive or duplicate Story 11.1/11.2/11.3's own due/churn/mechanical selection logic.
- Never build CAP-6's cross-entry/near-duplicate correlation (that is Story 11.6, a sibling
  depending on S-11.4, not on this story).
- Never require network access or any external service.
- Never restrict which projects' code roots are surfaced — the Spec is silent on trust boundaries
  and the read-only meta-tests already imply "read every project's tree, write only your own."

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Cross-project fix (precedent shape) | Project A has a due entry; project B's `src/shared/packages/pyforge-b/` tree contains the real fix | Project A's Finding evidence includes `other_project_roots` naming B's code root; an agent citing B's `file:line` as evidence is accepted unmodified by `apply_verification_verdicts.py --fix` and closes A's entry | No error — this is the happy path |
| Single-project fleet | Only one project directory exists under `_bmad-output/projects/` | `other_project_roots` is an empty dict/list on that project's own findings (no siblings to list) | No error |
| Project with no code root | A project slug exists under `_bmad-output/projects/` but has no matching `src/shared/packages/<slug>/` directory (e.g. a doc-only or partially-external station) | That slug is omitted from every `other_project_roots` map — never listed as a false code root | No error |
| Unreadable/missing `_bmad-output/projects/` | `target` is not a monorepo root | Existing `due-for-verification-unevaluable` vacuous-degrade path is unchanged; the new helper is never reached | No error — mirrors existing guard |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` -- add
  `_known_project_code_roots(target: Path) -> dict[str, str]` near the Story 11.1–11.4 section
  (after `DUE_FOR_VERIFICATION_STALENESS_DAYS`/before `_verification`, or beside
  `_due_for_verification_findings`); thread its result through
  `_due_for_verification_findings` → `_check_project_due_for_verification` (mirrors how `today`
  is already threaded) and attach an `other_project_roots` key on every `due-for-verification`
  item (never on `due-for-verification-unevaluable`), excluding the entry's own `proj.name`.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_due_for_verification.py` --
  extend with: (a) a unit test for `_known_project_code_roots` (multi-project fixture, one
  project deliberately missing its `src/shared/packages/<slug>/` dir to prove omission), (b) a
  test that a `due-for-verification` Finding's evidence carries `other_project_roots` excluding
  its own project, (c) an integration-style test reproducing the `atlas DW-I5-1` shape end to
  end: an entry in project A + a real file under project B's code root + a call into
  `apply_verification_verdicts.py`'s `_apply_project` citing B's `file:line` as evidence,
  proving the close succeeds unmodified.
- `scripts/apply_verification_verdicts.py` -- one-line docstring clarification (no behavior
  change) noting evidence may legitimately cite another project's `file:line`, closing the
  "silently possible but never documented" gap CAP-5 targets.

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` -- add
  `_known_project_code_roots` -- discovers every project directory under
  `target/_bmad-output/projects/` and pairs it with `target/src/shared/packages/<slug>/` when
  that directory exists, returning `{slug: relative_code_root}` for pairs that resolve
- [x] `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` -- thread the
  discovered map through `_due_for_verification_findings`/`_check_project_due_for_verification`
  and attach `other_project_roots` (the map minus the entry's own project) to every
  `due-for-verification` item
- [x] `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_due_for_verification.py`
  -- unit-test the I/O matrix's four scenarios above
- [x] `scripts/apply_verification_verdicts.py` -- clarify the docstring that evidence may cite
  another project's code, matching CAP-5's now-explicit contract

**Acceptance Criteria:**
- Given a due entry in project A and a real fix committed under project B's code root, when
  `gather_due_for_verification` runs against a monorepo root containing both projects, then A's
  Finding evidence names B's code root under `other_project_roots`.
- Given that same scenario, when a verifying agent calls
  `apply_verification_verdicts.py --verdicts-file ... --fix` with evidence citing B's `file:line`,
  then A's entry is closed with a new `verified:` line, unchanged from Story 11.4's existing
  write path.
- Given a project slug with no matching `src/shared/packages/<slug>/` directory, when
  `_known_project_code_roots` runs, then that slug is silently omitted, never included with a
  guessed or empty path.
- Given the existing 11.1–11.3 test suite, when it runs after this change, then every existing
  test still passes unmodified (no shape regression for entries that don't exercise the new key).

## Spec Change Log

## Review Triage Log

### 2026-08-21 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 5 (high 1, medium 1, low 3)
- defer: 0
- reject: 9 (low 9)
- addressed_findings:
  - `[high]` `[patch]` Blind Hunter + Edge Case Hunter independently converged on the same root
    cause via different trigger paths: `_known_project_code_roots` had no try/except around its
    per-sibling filesystem probes, and since it recomputes fresh on every project's own turn
    through `_check_project_due_for_verification`, one broken sibling (permission-denied
    ancestor -> `OSError`, or a symlink escaping `target` -> `ValueError` from `relative_to`)
    would abort evaluation of EVERY project, not just the broken one -- silently discarding real
    findings fleet-wide. Fixed: wrapped the per-sibling probe in `try/except (OSError,
    ValueError): continue`, isolating one bad sibling the same way `_collect_dreams`'s own
    established per-unit `try/except OSError` convention already does elsewhere in this file.
  - `[medium]` `[patch]` Edge Case Hunter: `other_roots` was built once per project then assigned
    BY REFERENCE into every finding item for that project; `Finding.__post_init__` only
    shallow-copies `evidence`, so the nested dict still aliased across every `Finding` (and the
    original `raw` items) for that project -- confirmed by reading `models.py:194-203` directly.
    Fixed: each item now gets its own `dict(other_roots)` copy at both assignment sites (verified
    with a new test that mutates one finding's copy and asserts a sibling finding is unaffected).
  - `[low]` `[patch]` Blind Hunter: the spec's own Verification section claimed `ruff check`
    would be "clean," but 7 pre-existing errors (unrelated to this diff, confirmed via `git
    stash` against the pre-change baseline) are present and the spec gave no caveat, unlike the
    caveat already given for the known-flaky speed-budget test. Fixed: reworded the Verification
    section to name the 7 pre-existing findings and the baseline-diff check, mirroring the
    existing flaky-test caveat style.
  - `[low]` `[patch]` Blind Hunter: the integration test's `_load_apply_verdicts_module` helper
    registered a fixed key in `sys.modules` with no cleanup, risking a stale entry (e.g. a
    since-deleted `tmp_path` still referenced by `REPO_ROOT`) persisting for the rest of the test
    session. Fixed: `del sys.modules[spec.name]` in a `finally` immediately after `exec_module`
    completes -- the registry entry is only needed during that call, not afterward.
  - `[low]` `[patch]` Blind Hunter: no test exercised a project with multiple due entries sharing
    the identical `other_project_roots` map, the behavior the recompute-once-per-project design
    implies. Added `test_multiple_due_entries_in_one_project_each_get_their_own_equal_copy`,
    which also directly proves the medium-severity fix above (equal content, distinct objects,
    mutating one never leaks into the other).
  - `[low]` `[reject]` Edge Case Hunter: a race where `_bmad-output/projects/` changes mid-run
    across per-project recomputations within one `gather()` call could yield inconsistent
    `other_project_roots` across findings in the same run. Rejected: this module has no
    cross-project transactional consistency anywhere already (ledger content, churn state, and
    mechanical verdicts are all equally susceptible to concurrent mutation), so this isn't a
    regression introduced by this story -- it's an existing, accepted property of the whole
    read-path design.
  - `[low]` `[reject]` Blind Hunter: `_known_project_code_roots` recomputes per project (O(P^2)
    filesystem work) with an unmeasured "cheap" claim, citing "~20+ live BMAD projects." Rejected
    on a factual check: `ls _bmad-output/projects/` and `ls src/shared/packages/` both show
    exactly 8 real projects in this repo today, not 20+ -- at that scale this is at most ~64 stat
    calls per full sweep, genuinely negligible, and the docstring already documents the
    deliberate tradeoff (avoiding a signature change that would break an existing monkeypatch
    test) with sound reasoning.
  - `[low]` `[reject]` Blind Hunter: the new function's `p.is_dir()` project-dir filter doesn't
    route through the module's own `_is_dir()` collection-site convention. Rejected: this exactly
    mirrors the SAME pre-existing pattern already used one function over in
    `_due_for_verification_findings`'s own `for proj in sorted(p for p in
    projects_dir.iterdir() if p.is_dir())` -- matching existing style, not introducing a new
    inconsistency.
  - `[low]` `[reject]` Blind Hunter: `test_single_project_fleet_other_project_roots_is_empty_dict`
    doesn't itself distinguish "no siblings" from "no code root at all." Rejected: the
    distinguishing scenario (a lone project WITH a real code root, excluded from its own map) is
    already directly covered by `test_due_for_verification_item_carries_other_project_roots_excluding_own`,
    just under a different test name -- coverage exists, the finding overstates the gap.
  - `[low]` `[reject]` Blind Hunter: `other_project_roots` is present-as-`{}` on a
    `due-for-verification` item but absent entirely on a `due-for-verification-unevaluable` one.
    Rejected: this is the spec's own explicit, deliberate Boundaries decision ("never on
    due-for-verification-unevaluable") with a clear rationale (an unevaluable item has no
    specific due entry to attach sibling context to) and is directly tested.
  - `[low]` `[reject]` Blind Hunter: a stray, non-BMAD directory under `_bmad-output/projects/`
    with a matching `src/shared/packages/<name>/` would be surfaced with the same authority as a
    real project. Rejected: this trust assumption is already inherited unchanged from the
    pre-existing `_due_for_verification_findings` project-discovery loop (any directory there is
    already treated as a project today) -- not new or worsened by this story.
  - `[low]` `[reject]` Blind Hunter: threading `_known_project_code_roots` through `target`
    rather than adding a new parameter was a design choice driven by one test's fixed-arity
    monkeypatch rather than reshaping that test. Rejected: this is sound, already-documented
    engineering judgment (avoiding a larger, less surgical change to an existing, orthogonal
    isolation test) consistent with this repo's Surgical Changes principle.
  - `[low]` `[reject]` Blind Hunter: the new docstrings cite "Story 11.5, CAP-5"/"CAP-4" shorthand
    that only resolves inside the BMAD planning artifacts. Rejected: this exactly matches the
    pervasive pre-existing documentation convention throughout this same file (e.g. "CAP-2",
    "Boundaries", "I/O matrix" citations already used by Stories 11.1-11.4's own code).
  - `[low]` `[reject]` Blind Hunter: the Tasks checklist doesn't explicitly restate the read-only
    and station-independence meta-test constraints as their own acceptance line items. Rejected:
    already covered by the spec's own Boundaries "Always" bullets, which name the exact meta-test
    files; restating them a second time in the task list would be redundant, not missing.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- expected: full suite green
  (pre-existing flaky `test_check_speed_budget.py` timing test aside, unrelated to this change)
- `pixi run -e pyforge-doctor ruff check src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py scripts/apply_verification_verdicts.py` -- expected: zero NEW findings (this
  file already carries 7 pre-existing errors on main -- `RUF022`/`FURB167`/`DTZ011` -- unrelated
  to this story; confirm via `git stash` against the pre-change baseline that the count and
  locations are unchanged, not a bare "clean" pass)

## Auto Run Result

Status: done

**Summary.** Added `_known_project_code_roots(target)` to `chain.py` -- a pure, read-only helper
mapping every `_bmad-output/projects/<slug>/` directory to its matching
`src/shared/packages/<slug>/` code root when one exists. Wired it into
`_check_project_due_for_verification` so every `due-for-verification` Finding now carries an
`other_project_roots` evidence key (every OTHER known project's code root, excluding the entry's
own), closing CAP-5's discoverability gap: a verifying agent working an entry now sees, right on
the Finding it is investigating, exactly which sibling project trees exist to check for the real
fix -- reproducing the precedent's real `atlas DW-I5-1` case (an atlas entry resolved in
marshal's `core/policy.py`) end to end in a new integration test.

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` -- new
  `_known_project_code_roots` function (with per-sibling failure isolation, added in review);
  `other_project_roots` evidence key wired into both `due-for-verification` branches (with
  per-item dict copies, fixed in review); docstring updates on
  `_check_project_due_for_verification` and `_due_for_verification_findings`.
- `scripts/apply_verification_verdicts.py` -- one-line docstring clarification: evidence may cite
  another project's `file:line`.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_due_for_verification.py` --
  9 new tests (8 from implementation + 1 added in review) covering the I/O matrix, the
  cross-project integration scenario, and the per-item dict-copy fix.

**Review findings breakdown:** 5 patched (1 high, 1 medium, 3 low -- see Review Triage Log for
full detail), 9 rejected as noise/pre-existing/already-covered/intentional-by-spec, 0 deferred,
0 intent gaps, 0 bad-spec loopbacks.

**Follow-up review recommendation:** false -- the high-severity fix is a small, well-precedented
defensive-isolation addition (mirrors `_collect_dreams`'s own established pattern) directly
proven by a new test; the medium fix is a narrow aliasing correction directly proven by another
new test; the three low fixes are documentation/test-hygiene only. Narrow, verified, not broad
enough to warrant an independent second pass.

**Verification performed:** `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- 1063
passed, 2 skipped (pre-existing flaky speed-budget test unaffected). `ruff check` on all three
touched files -- 7 pre-existing findings, 0 new (confirmed against the pre-change baseline via
`git stash`). `pytest tests/meta/test_read_only_guard.py tests/meta/test_source_independence.py`
-- 68 passed, confirming the new code stays pure read-only and imports no other station's
package.

**Residual risks:** none identified beyond the rejected findings above, all of which were either
pre-existing repo-wide properties, already covered by other tests, or intentional per this
story's own spec.
