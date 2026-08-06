---
title: 'Verdict aggregation that never false-greens'
type: 'feature'
created: '2026-08-03'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
baseline_revision: 'ef869e2dd23d95df6ecaa7e1fdcf0fcc34504285'
final_revision: '74e7ee1bb4cab47380abe87d36831d9142c4aa21'
---

<intent-contract>

## Intent

**Problem:** Story 2.1 built `core/gate.py`/`core/verdict.py`'s classify/aggregate mechanism correctly, but AD-8's own invariant -- "there exists no input producing `clean` when any check is `unevaluable`" -- has never been proven. Nothing today would catch a future finding registration, a `_CLASSIFY_TABLE` edit, or a `compute_verdict` refactor that quietly opens a false-green path.

**Approach:** Add regression proof only -- no `compute_verdict`/`classify` behavior changes, since the mechanism already satisfies AD-8/AD-31 by construction (`compute_verdict` only ever strengthens `floor` toward a stronger lattice rung, never weakens it). Two new tests in `tests/unit/test_verdict.py`: an exhaustive (not sampled) sweep over every combination of the closed 6-member lattice via synthetic codes, and a derived (never hardcoded) sweep over every REAL code the current registry classifies `unevaluable`.

## Boundaries & Constraints

**Always:** New tests only, in `tests/unit/test_verdict.py`. The exhaustive sweep enumerates ALL combinations (`itertools.product`, not `hypothesis` -- not a project dependency, and the 6-member lattice is small enough that full enumeration is strictly stronger than sampling) of 1-3 synthetic findings, monkeypatching `findings.REGISTERED_CODES`/`verdict._CLASSIFY_TABLE` the same way the file's existing `synthetic_registry` fixture does, across every possible `floor`. The real-registry sweep derives its code list from `verdict._CLASSIFY_TABLE` at test-collection time (`[code for code, v in _CLASSIFY_TABLE.items() if v is Verdict.UNEVALUABLE]`), never a hand-copied literal list, so a future story's new `unevaluable` code is covered automatically (mirrors this repo's derive-don't-declare convention).

**Block If:** N/A -- no ambiguity requiring a human decision; the mechanism and its test gap are both fully determined by reading the existing code.

**Never:** Do not edit `compute_verdict`, `classify`, `_CLASSIFY_TABLE`, or `core/gate.py`'s classification functions -- Story 2.1's review passes already hardened them and explicitly deferred "further verdict-lattice/never-false-green property tests" to this story (spec-2-1's own **Never** clause). Do not add a `hypothesis` dependency. Do not duplicate the existing `test_lattice_order_has_six_members_strongest_first` (already proves "the lattice gains no new members") or the existing `tests/meta/test_ad7_verdict_sole_ownership.py` (already proves "no module assigns a verdict directly") or the existing `cli/main.py` `KeyboardInterrupt -> EXIT_SIGINT` path (already proves "130 on interrupt") -- all three ACs restated by Story 2.2's text are already covered; this spec adds no new tests for them.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/tests/unit/test_verdict.py` -- EDIT. Add the two AD-8 regression tests below the existing `synthetic_registry`-driven tests; reuse that fixture's monkeypatch pattern for the exhaustive sweep rather than inventing a second one.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py` -- READ ONLY. `compute_verdict`/`classify`/`_CLASSIFY_TABLE` confirmed correct by inspection; no edit.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py` -- READ ONLY. `classify_outcome`/`no_commands_configured_finding` confirmed correct by inspection; no edit.

## Tasks & Acceptance

**Execution:**
- [x] `tests/unit/test_verdict.py` -- add `test_ad8_no_combination_of_the_full_lattice_produces_clean_when_any_finding_is_unevaluable`: for every `length in (1, 2, 3)`, every `itertools.product(Verdict, repeat=length)` combo containing `Verdict.UNEVALUABLE`, and every `floor in Verdict`, assert `compute_verdict(...) is not Verdict.CLEAN` -- proves AD-8 exhaustively over the mechanism, independent of today's real registry
- [x] `tests/unit/test_verdict.py` -- add `test_ad8_every_real_unevaluable_code_never_projects_to_clean`, parametrized over `[code for code, v in verdict._CLASSIFY_TABLE.items() if v is Verdict.UNEVALUABLE]` (derived, not hardcoded): a single real `Finding` with that code, under the default `Verdict.CLEAN` floor, computes a non-`Verdict.CLEAN` verdict -- proves the mechanism holds against today's actual registered codes, not only synthetic ones

**Acceptance Criteria:**
- Given any combination of check outcomes (synthetic, spanning the full 6-member lattice), when the verdict is computed, then it is the maximum over emitted findings' classifications plus the command-declared floor (already implemented; re-confirmed by the new exhaustive sweep, not re-implemented)
- Given a finding whose code classifies to `unevaluable` -- synthetic or real, alone or combined with any other findings, under any floor -- when `compute_verdict` runs, then the result is never `Verdict.CLEAN`
- Given the full parametrized suite, when `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` runs, then it passes with the two new tests included and zero existing tests modified

## Spec Change Log

## Review Triage Log

### 2026-08-03 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6 (high 0, medium 3, low 3)
- defer: 0
- reject: 5
- addressed_findings:
  - `[medium]` `[patch]` The exhaustive sweep's assertion (`is not Verdict.CLEAN`) is weaker than AD-8's actual consequence ("projects to a non-zero exit and blocks progression") -- `Verdict.WARN` also satisfies "not clean" while sharing `clean`'s exit-0/`Status.OK` behavior, so a hypothetical regression collapsing `unevaluable` toward `warn` would slip past. Added a second assertion to both `test_ad8_*` tests: `status_for(result) is Status.ERROR` (the precise ok/error partition AD-8 cares about, since `status_for` maps `{clean, warn} -> ok`).
  - `[medium]` `[patch]` `dict(zip(active_codes, combo))` truncates silently if `codes` and the `length` loop bound ever desync (both reviewers independently flagged this). Added `assert len(active_codes) == length` before the zip, naming the exact failure mode in the message.
  - `[medium]` `[patch]` `test_ad8_every_real_unevaluable_code_never_projects_to_clean`'s parametrize list is derived from `_CLASSIFY_TABLE` at collection time with no non-emptiness guard -- pytest silently collects zero cases for an empty parametrize set rather than failing, so a future story reclassifying every `unevaluable` code away would make this regression test quietly vanish. Added `test_ad8_real_unevaluable_code_list_is_non_empty`, a standalone fail-loud guard.
  - `[low]` `[patch]` The exhaustive sweep's `continue`-guarded assertions had nothing proving they ever actually ran -- an inverted/typo'd filter or an emptied `itertools.product` call would leave a vacuously passing test. Added an `executed` counter incremented per assertion, with `assert executed > 0` at the end.
  - `[low]` `[patch]` The docstring's "Exhaustive proof, not sampled" phrasing overclaimed unbounded-length coverage (only lengths 1-3 are swept) -- against this project's own "never overstate coverage" convention. Reworded to "Exhaustive over lengths 1-3 (not sampled)" plus one sentence on why `compute_verdict`'s per-element max fold makes a longer list add no new aggregation behavior.
  - `[low]` `[patch]` The file's module-level docstring (behavior categories under test) was not updated to mention the new AD-8 property tests, breaking this file's own established convention of naming everything it covers up top. Added one sentence.
  - `reject` (5): a duplicate-code-within-one-findings-list edge case (not a shape `cli/gate.py` ever produces -- one `Finding` per distinct verify command); framing the two new tests as "significantly overlapping" (test 2's unique value -- proving real registered codes, independently guarded against silently emptying -- is exactly what the emptiness-guard patch above makes explicit); cross-checking a real `unevaluable` code against every non-default `floor` (the floor-strengthening mechanism is already exhaustively proven generically in test 1; re-running it per real code would duplicate coverage, not add it); shortening the long, fully-descriptive test names (matches this file's and the sibling `test_gate.py`'s own established house style of long, explicit names + docstrings); asking for a "converse" check that CLEAN is reachable absent `unevaluable` (already covered by `test_compute_verdict_empty_findings_returns_floor`/`test_compute_verdict_returns_the_strongest_finding`, both pre-existing in this same file).

## Design Notes

**Why exhaustive enumeration, not `hypothesis`.** The lattice is a closed 6-member enum (AD-31: "the lattice gains no members"), so `itertools.product` over combinations of length 1-3 plus 6 floors is at most `6^3 * 6 = 1296` cases -- small, deterministic, and a strictly *complete* proof rather than a sampled one. `hypothesis` is not a dependency of this package (checked: absent from `pyproject.toml` and `pixi.toml`'s `feature.pyforge-marshal.dependencies`) and pyforge-warden's sibling `test_verdict.py` already establishes this repo's own idiom for lattice invariants: full enumeration via `for status in Status:` / `itertools.product`, never a probabilistic library.

**Why compute_verdict already satisfies AD-8 (no code change needed).** `compute_verdict` starts `winner = floor` and only ever reassigns `winner` to a *stronger* candidate (`if _RANK[candidate] < _RANK[winner]`) -- it can move toward `error` but never back toward `clean`. Since `UNEVALUABLE` outranks both `WARN` and `CLEAN` in `LATTICE_ORDER`, any `unevaluable`-classified finding forces the final rank to `<= _RANK[UNEVALUABLE]`, structurally excluding `CLEAN` regardless of `floor`. This is a proof sketch, not a substitute for the test -- the test is what a future edit to `_RANK`/`LATTICE_ORDER`/`compute_verdict` would actually break against.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: all tests green, including the two new AD-8 tests, with zero regressions in the existing 894+ passing tests
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- expected: green or the same pre-existing two `pyforge-steward` failures already logged in `deferred-work.md` from Story 2.1 (unrelated to this diff -- no dependency added)

## Auto Run Result

Status: `done`.

**Summary.** Story 2.1 already built `core/gate.py`/`core/verdict.py`'s classify/aggregate mechanism correctly and structurally satisfies AD-8 by construction (`compute_verdict` only ever strengthens `floor`, never weakens it). This story adds the missing regression proof: two new tests in `tests/unit/test_verdict.py` proving "no input produces `clean` when any check is `unevaluable`" -- one exhaustive over the full synthetic 6-member lattice (lengths 1-3, every floor), one derived (not hardcoded) over every REAL code the current registry classifies `unevaluable`. No production code (`core/gate.py`, `core/verdict.py`) was touched, per the spec's own **Never** clause.

**Files changed:**
- `src/shared/packages/pyforge-marshal/tests/unit/test_verdict.py` -- added `test_ad8_no_combination_of_the_full_lattice_produces_clean_when_any_finding_is_unevaluable` (exhaustive synthetic sweep), `test_ad8_real_unevaluable_code_list_is_non_empty` (added during review, guards against the next test's parametrize list silently emptying), and `test_ad8_every_real_unevaluable_code_never_projects_to_clean` (derived real-registry sweep, parametrized over 14 real codes today).

**Review findings breakdown:** 6 patches applied (medium 3, low 3), 0 deferred, 5 rejected. Full detail in the Review Triage Log above. Both Blind Hunter and Edge Case Hunter independently flagged the same `dict(zip(...))` silent-truncation risk; Edge Case Hunter additionally caught the empty-parametrize-list silent-skip risk, and Blind Hunter caught that the original assertion (`is not Verdict.CLEAN`) was weaker than AD-8's actual "blocks progression" consequence.

**Verification performed:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- **910 passed, 8 deselected** (baseline 894; +16 from this diff: 1 exhaustive test + 1 non-emptiness guard + 14 parametrized real-code cases). Independently re-run after every patch, not just trusted from the implementing subagent's report.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- **2 failed, 58 passed**, both the same pre-existing `pyforge-steward` failures already logged in `deferred-work.md` from Story 2.1 (unrelated -- this diff touches only `pyforge-marshal`'s test file, no dependency added).
- `pytest tests/unit/test_verdict.py -k ad8 -v` -- all 16 AD-8-related tests pass individually, confirming the real-registry sweep currently covers `MRS-IDENT-001/002`, `MRS-POLICY-001/002/003/004/006`, `MRS-INIT-001/002`, `MRS-PREFLIGHT-010`, `MRS-TEARDOWN-001`, `MRS-GATE-002/003/005`.

**Residual risks:**
- The exhaustive sweep is bounded to findings-list lengths 1-3 (documented rationale: `compute_verdict`'s per-element max fold has no length-dependent state, so a 4th+ finding cannot introduce new aggregation behavior) -- not a risk given that reasoning, but noted since it was raised in review.
- `status_for` now doubles as the "blocks progression" proxy in these tests; if a future architecture change ever decoupled "non-`ok` status" from "blocks progression" (neither planned nor foreseeable today), these tests would need revisiting alongside that change.

