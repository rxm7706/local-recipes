---
title: 'marshal seed init'
type: 'feature'
created: '2026-08-21'
status: 'done'
baseline_revision: 'fea7cc119f383de9f5759db8f039b78af3824497'
final_revision: 'aaff8ea240741ef39714086194e9b1e6189f72d2'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** Story 10.7's own preserved implementation (`seed/verbs/init.py`, `cli/seed.py`
wiring, `seed/verbs/check.py`'s `applies_to`-vs-`state.mode` fix, all cherry-picked cleanly from
commit `596fdc8a36` onto current `main`) was correctly stopped, not failed: verified live, it
refuses unconditionally on `dreams-readme` (`docs/dreams/README.md`) against the REAL packaged
manifest, the same never-write collision Story 10.8 (now merged, PR #591) fixed for `adopt`.
`init.py`'s own `never_write = fs.NeverWrite(...)` construction was never updated to consume
10.8's fix. Independently re-verified after the cherry-pick: `pixi run --frozen -e
pyforge-marshal pyforge-marshal-test` passes fully (5017), but `marshal seed init <empty-dir>
--slug test` (the real CLI) still fails with `never-write-target: ... 'docs/dreams/README.md' ...
matches never-write pattern 'docs/dreams/*.md'` -- the preserved test suite deliberately never
exercises the real packaged manifest (its own module docstring says so explicitly, written when
the defect was still blocking), so it cannot catch this.

**Approach:** Wire `run_init`'s `never_write = fs.NeverWrite(patterns=tuple(sorted(
effective_never_write(filtered_manifest, inventory))))` construction with the identical one-line
addition `verbs/adopt.py` already received in Story 10.8:
`exempt=writable_exemptions(filtered_manifest, inventory)`. Add `writable_exemptions` to
`init.py`'s existing `from ..detect.inventory import (...)` line. No other code in the preserved
implementation changes -- `init.py`'s own verb logic, `cli/seed.py`'s wiring, and `check.py`'s
`applies_to` fix are unrelated to this gap and already correct. Add the real-packaged-manifest
regression test the original implementation could not add while blocked, and re-verify against
the real CLI (not just the test suite) before landing.

## Boundaries & Constraints

**Always:**
- The fix is confined to `init.py`'s one `never_write = fs.NeverWrite(...)` construction line
  plus its import line -- mirrors `verbs/adopt.py`'s own Story 10.8 change exactly.
- The new real-manifest regression test isolates this fix from the SEPARATE, pre-existing,
  already-deferred `engine/copier.py::_check_manifest_boundary` gap (`DW-FU-10-8`: no whole-file
  template content exists yet for any entry, so routing through the real `_default_commit` ->
  `materialize()` path fails for an unrelated reason regardless of this fix) -- use a `commit=`
  double or call `check_preconditions`/`fs.write` directly, matching Story 10.8's own adopt.py
  test technique, not `template_path=` with synthetic whole-file content for `dreams-readme`.
- Independently verify against the REAL `marshal` CLI (`pixi run -e pyforge-marshal marshal seed
  init <fresh-dir> --slug test`), not only the unit/integration test suite -- the story's own
  history (this exact defect) already proved tests-green does not imply CLI-working here.
- `marshal seed check` on the result of a successful `init` must be green (epics AC), covering
  `check.py`'s own already-landed `applies_to`-vs-`state.mode` fix.

**Block If:** none — the gap and its fix are fully determined by direct comparison against
`verbs/adopt.py`'s own already-reviewed, already-merged Story 10.8 change; no undecidable
question found.

**Never:**
- Do not modify `seed/verbs/init.py`'s existing verb logic, `cli/seed.py`'s CLI wiring, or
  `seed/verbs/check.py`'s `applies_to` fix beyond what is described above -- all three are
  unrelated to the never-write gap and were already implemented/reasoned through in commit
  `596fdc8a36`.
- Do not touch `fs.py`, `verbs/preconditions.py`, or `detect/inventory.py` -- Story 10.8 already
  shipped and reviewed the mechanism this story only needs to CONSUME.
- Do not attempt to close `DW-FU-10-8` (the `_check_manifest_boundary` gap) or `DW-FU-10-8-2`
  (the `hybrid-managed-region` exemption-scope question) here -- both are pre-existing, deferred,
  out of this story's own scope, exactly as they were for Story 10.8.
- A full, unmodified `--apply`-equivalent (`init` has no dry-run) end-to-end run against the real
  packaged manifest, routed through the real `_default_commit`/`materialize()`, will still fail
  on `DW-FU-10-8` regardless of this fix (no whole-file template content exists yet) -- this is
  NOT a regression this story introduces or must resolve; isolate the regression test from it as
  described above, matching Story 10.8's own precedent.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `run_init` against the real packaged manifest, fresh empty target, isolated from the materialize() gap | empty dir, no git repo | `dreams-readme`'s action clears `check_preconditions`; `fs.write` materializes it | none |
| Real CLI: `marshal seed init <empty-dir> --slug test` | empty dir | no longer refuses on `docs/dreams/README.md`'s never-write collision (may still hit the separate, pre-existing `DW-FU-10-8` materialize() gap for OTHER whole-file entries -- report honestly, do not paper over) | n/a |
| `marshal seed check` immediately after a successful real init | init succeeded | green (already covered by `check.py`'s own Story 10.7 fix) | none |
| Every existing `test_seed_verbs_init.py`/`test_seed_cli_seed_init.py` test (synthetic manifests) | — | still passes unchanged | none |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/init.py` -- import
  `writable_exemptions` alongside the existing `effective_never_write` import; `run_init`'s
  `never_write = fs.NeverWrite(...)` line gains `exempt=writable_exemptions(filtered_manifest,
  inventory)`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_init.py` -- NEW: a real-packaged-
  manifest regression test proving `dreams-readme` no longer refuses (mirrors Story 10.8's
  `test_seed_verbs_adopt.py` real-manifest test technique -- isolate via `check_preconditions`/
  `fs.write` called directly, or a `commit=` double, not `template_path=`).
- No other files change -- `cli/seed.py`, `seed/verbs/check.py`, and every other file cherry-picked
  from commit `596fdc8a36` are already correct and unrelated to this gap.

## Tasks & Acceptance

**Execution:**
- [x] `verbs/init.py` -- wire `exempt=writable_exemptions(...)` into `run_init`'s `NeverWrite`
  construction; add the import.
- [x] `tests/unit/test_seed_verbs_init.py` -- real-packaged-manifest regression test isolated from
  the pre-existing `DW-FU-10-8` materialize() gap.
- [x] Independently verify against the real `marshal` CLI (`pixi run -e pyforge-marshal marshal
  seed init <fresh-dir> --slug test`), reporting honestly whether it fully completes or still
  hits the separate, pre-existing `DW-FU-10-8` gap for other whole-file entries.

**Acceptance Criteria:**
- Given the real packaged manifest and a fresh, empty target directory, when `run_init`'s plan is
  checked via `check_preconditions` and `dreams-readme`'s action is written via `fs.write`, then
  neither refuses (previously: unconditional `PreconditionFailure`/`NeverWriteViolation`).
- Given the real `marshal` CLI, when `marshal seed init <empty-dir> --slug test` runs, then it no
  longer refuses on the `docs/dreams/README.md` never-write collision specifically (whatever else
  it may or may not do, honestly reported).
- Given every existing test in `test_seed_verbs_init.py`/`test_seed_cli_seed_init.py`/
  `test_seed_verbs_check.py` (all cherry-picked from `596fdc8a36`, all using synthetic manifests),
  when the suite runs, then all still pass unchanged.

## Spec Change Log

## Review Triage Log

### 2026-08-21 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 0, medium 2, low 2)
- defer: 2: (high 0, medium 0, low 2)
- reject: 1
- addressed_findings:
  - `[medium]` `[patch]` Blind Hunter found the new regression test never called `run_init` itself (the actual line this story changes) -- it manually re-derived the `never_write`/`exempt` construction instead, so a future accidental revert of `run_init`'s own `exempt=writable_exemptions(...)` wiring would not be caught. Added `test_run_init_end_to_end_against_the_real_packaged_manifest`, calling `run_init` for real (with a `commit=` double bypassing the separate, pre-existing `DW-FU-10-8` materialize() gap) against the real packaged manifest, minus its directory-shaped entries (a confirmed-by-execution `_fake_commit` limitation, documented in the test's own docstring, unrelated to this story's fix).
  - `[medium]` `[patch]` Both reviewers independently found `specs-readme` (the `init`-only entry that ALSO collides with `**/planning-artifacts/**`, and that `adopt`'s own equivalent test structurally cannot exercise) was asserted as fixed in the module docstring but never covered by a test. Parametrized the existing regression test over both `dreams-readme` and `specs-readme`.
  - `[low]` `[patch]` Both reviewers flagged a bare `next(...)` manifest-entry lookup with no fallback message. Replaced with a named `_entry_by_id` helper raising a clear `AssertionError` if the packaged manifest ever renames/removes the pinned entry.
  - `[low]` `[patch]` Blind Hunter found the docstring heading "Story 10.8, S-10.7-followup" ambiguous (reads as if the paragraph belongs to Story 10.8). Reworded to "this story's own follow-up work."

Deferred (pre-existing scope, out of this story's own Code Map, surfaced incidentally by review): `writable_exemptions()` now has a second call site (`init.py`) with the same unaudited `hybrid-managed-region` exposure `DW-FU-10-8-2` already named for `adopt` (`DW-FU-10-7`, not reachable today -- confirmed none of `init`'s own hybrid entries collide with any never-write pattern); the `real_manifest` test fixture is now duplicated a fourth time across the package's test files with no shared `conftest.py` (`DW-FU-10-7-2`, a pre-existing pattern this story continued rather than introduced).

Rejected (by-design, already litigated in Story 10.8's own review): a claim that no test proves `writable_exemptions()` doesn't "over-exempt" a non-colliding path -- the exemption is unconditional by design, matching the epics AC's own literal "excluded from the set -- never in the set to begin with" wording (Blind Hunter's identical concern was already raised and rejected on the same grounds during Story 10.8's review).

## Design Notes

This is a narrower repeat of Story 10.8's own fix: `verbs/adopt.py`'s `never_write`
construction already received `exempt=writable_exemptions(filtered_manifest, inventory)`;
`verbs/init.py`'s identically-shaped construction line was simply never updated because it lived
on a separate, unmerged branch at the time. No new design decision is needed -- only applying the
existing one to the second of the two call sites the story's own architecture doc (AD-61,
corrected 2026-08-21) always anticipated needing it.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: full suite green,
  including the new real-manifest regression test.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- expected: green.
- Real CLI: `marshal seed init <fresh-empty-dir> --slug test` -- expected: no `never-write-target`
  refusal for `docs/dreams/README.md` specifically (report the actual outcome honestly).

## Auto Run Result

**Summary:** Resumed Story 10.7 (`marshal seed init`) from its preserved implementation (commit
`596fdc8a36`, cherry-picked cleanly onto current `main`). The verb logic, CLI wiring, and
`check.py`'s `applies_to` fix were already correct and unchanged. The one real gap: `run_init`'s
`never_write = fs.NeverWrite(...)` construction had not yet consumed Story 10.8's
`exempt=writable_exemptions(...)` fix (merged after this branch was preserved). Wired it in,
mirroring `verbs/adopt.py::run_adopt`'s identical, already-merged construction. Independently
confirmed via the real `marshal` CLI, not just tests: the never-write collision on both
`dreams-readme` and `specs-readme` no longer refuses (both correctly appear in a real `init`
run's `.marshal/plan.json`); the run still fails later for the separate, pre-existing,
already-deferred `DW-FU-10-8` materialize()/template-content gap, honestly reported rather than
concealed.

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/init.py` -- import
  `writable_exemptions`; wire `exempt=writable_exemptions(filtered_manifest, inventory)` into
  `run_init`'s `NeverWrite` construction; module-docstring updates (the fix's own account, plus
  a clearer paragraph heading fixed during review).
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_init.py` -- corrected stale
  docstring language; parametrized real-manifest regression test covering both `dreams-readme`
  and `specs-readme` (added `specs-readme` coverage during review); new
  `test_run_init_end_to_end_against_the_real_packaged_manifest` calling `run_init` itself
  end-to-end (added during review, so a revert of the actual fix line is caught); named
  `_entry_by_id` helper replacing a bare `next(...)` lookup (added during review).
- `_bmad-output/projects/pyforge-marshal/implementation-artifacts/deferred-work.md` (edited) --
  two new defer entries (`DW-FU-10-7`, `DW-FU-10-7-2`).

**Review findings breakdown:** 4 patch (0 high, 2 medium, 2 low) -- all auto-fixed with
regression-test proof; 2 defer (0 high, 0 medium, 2 low) -- logged to the Tier-3 deferred-work
ledger; 1 reject (already litigated and settled in Story 10.8's own review, on identical
reasoning); 0 intent_gap; 0 bad_spec.

**Follow-up review recommendation:** `false` -- the four patches were additive test coverage and
documentation-clarity fixes around a single, small, one-line production change (mirroring an
already-reviewed, already-merged sibling construction in `adopt.py`); no new production-code risk
was introduced beyond what this review pass already covered.

**Verification performed:** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- 5020
passed, 9 deselected (re-run after the patch fixes; up from 5017 on the raw cherry-pick, +3 net
new test executions: the one-line implementation fix's own test plus the two review-driven
additions). `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- 84 passed. `ruff check` on both
changed files -- clean.

**Independent real-CLI verification (both by the implementing subagent and re-confirmed by the
orchestrating agent before landing):** `pixi run -e pyforge-marshal marshal seed init <fresh-dir>
--slug test` against a genuinely fresh, empty target directory. Result: no `never-write-target`
refusal anywhere in the output; `.marshal/plan.json` (26 actions) confirms both `dreams-readme`
and `specs-readme` are present, meaning `check_preconditions` cleared them. The run fails later,
inside `run_apply`'s commit callback, with `TemplateBoundaryError` naming `manifest.yaml`,
`__init__.py`, and the six `files/*.j2` region fragments -- the SEPARATE, pre-existing,
already-deferred `DW-FU-10-8` gap (`engine/copier.py::_check_manifest_boundary`'s OTHER
condition: no whole-file template content exists yet for any manifest entry, so `materialize()`
stages the packaged template tree's own internal files alongside real content). This is the
identical, already-disclosed, out-of-scope residual risk Story 10.8's own spec named for `adopt`;
`init` inherits it via the same shared `_default_commit` it reuses directly.

**Residual risks:** the two new deferred findings extend, rather than newly introduce, gaps
Story 10.8 already named (`DW-FU-10-8-2`'s `hybrid-managed-region` audit now spans two call
sites; a pre-existing test-fixture duplication pattern continued). The literal end-to-end
`marshal seed init` CLI invocation still does not fully complete against the real packaged
manifest today -- not because of anything this story's own fix scope covers, but because of the
separate, pre-existing `DW-FU-10-8` template-content gap, reported here rather than concealed.
