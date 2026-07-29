---
title: 'Preserve NULL identity under pandas 3.0'
type: 'bugfix'
created: '2026-07-28'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false  # pass 2 (fresh reviewers): 7 patches, but 5 are comment/doc/registry wording and the 2 medium are a warning on a today-unreachable fallback + a new canary test — no reachable production behavior changed; gates green (788/19, 47/47)
context: []
warnings: ['oversized']
baseline_revision: 'ffd9275b0d4da6a3dd33592ded4ce0adda4ece1d'
final_revision: '1f4a5b1cf7b22e4d313b249bc47517a77dc33d92'
---

<intent-contract>

## Intent

**Problem:** pandas 3.0 defaults every string-like column to its new `str` dtype, whose
missing-value sentinel is a float `NaN`, not `None`. `NaN != NaN`, so a genuine NULL loses
its identity — it can't be looked up, compared, or used as a dict key. This breaks both
this package's own DataFrame construction (`pipelines/core/nodes.py`,
`pipelines/seed_gaps/nodes.py`) AND every semantic-layer query result (`semantic/models.py`
+ `semantic/metrics.py`, executed via Ibis/DuckDB — Ibis's own DuckDB backend builds its
result via a plain `pd.DataFrame(...)` call subject to the same default). Six tests on
`main` reproduce this (`kedro-test`: 781 passed / 6 failed).

**Approach:** pin pandas back to its pre-3.0 default (`pd.set_option("future.infer_string",
False)`) once, at `pyforge.atlas` package-init time, so every DataFrame construction in the
process — this package's own list-to-column assignments AND Ibis's internal DuckDB→pandas
conversion — preserves `None` identity for missing cells. This is a single root-cause fix,
not six per-site patches: `pipelines/core/nodes.py`, `pipelines/seed_gaps/nodes.py`, and
`semantic/models.py`/`metrics.py` need NO changes (verified — see Design Notes). The one
collateral regression the pin causes (an unrelated, already-green pandera test whose empty
`DataFrame` was implicitly relying on the pandas-3.0 default) is fixed alongside it so no
currently-passing test breaks.

## Boundaries & Constraints

**Always:** preserve genuine NULL identity for any DataFrame this package constructs or
receives back from a DuckDB/Ibis query, project-wide — not just in the six regression
tests. Never fabricate a `0` for a NULL measure. Never coalesce away a group-key NULL (a
NULL group must stay reachable as `None`, distinct from being silently dropped or merged
into another group).

**Block If:** the `future.infer_string` pin turns out to require touching any file outside
`src/shared/packages/pyforge-atlas/` to stay green (e.g. a shared/sibling package in the
same pixi env regresses) — HALT and report which file, rather than expanding the fix's
blast radius silently. (Not expected: `pyforge-atlas`'s `kedro-test` task only collects
its own `tests/` tree, and the pin lives in `pyforge.atlas`'s own `__init__.py`.)

**Never:** weaken any of the six listed tests' assertions to tolerate `NaN` as if it were
`None` — the fix is the pandas-3.0 compatibility pin (+ its one collateral repair), not a
test change that masks the underlying loss of identity. Never add `.fill_null(...)` to
`metrics.py`'s `ci_red`/`is_actionable`/etc. as part of this fix — verified unnecessary
once `None` identity is restored (see Design Notes); adding it anyway would be speculative,
unrequested surface area.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| List-built column with a missing cell | `attribute_feedstocks()` builds `feedstock_name` from a Python list mixing strings and `None` (an orphan package with no feedstocks) | The missing cell round-trips as `None` (`m["orphan"] is None`), not `NaN` | No error — this is the happy path once the pin is in place |
| BSL group-by on a NULL-valued dimension column | `join_packages_by_maintainer(...).query(dimensions=["maintainer"], ...)` where one package's `maintainer` is NULL | The null-maintainer group key is `None` and is present (`None in downloads`) with a NULL (not fabricated `0`) measure value; no real package's measure is attributed to it | No error — a present-but-NULL group, never an absent one |
| Boolean predicate over a NULL source column | `ci_red` dimension where `ci_status` is NULL | `bool(value)` for the NULL row is `False` (legacy WHERE-clause semantics: `NULL IN (...)` excludes the row), matching `_legacy_ci_red(None)` | No error |
| `COALESCE`-style dimension over a NULL source column | `is_actionable` where `latest_status` is NULL (falls back to `"active"`) | Already correct pre-fix (the Ibis expression already uses `.fill_null("active")`) — stays `True`; regression here was purely a test-fixture artifact, not a production bug | No error |
| Empty DataFrame, explicit-dtype construction, pandera schema check | `test_validation_hook.py`'s `test_empty_frame_with_valid_columns_passes` builds an empty frame with `pd.Series([], dtype=str)` | Must still validate against `Column(str)` (pandera checks an empty column's *declared* dtype literally, since there are no values to infer from) | Fix: construct with the explicit `dtype="string[pyarrow]"` pandera actually expects, so the check passes regardless of the `future.infer_string` setting |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/__init__.py` -- currently just
  `__version__`; add the `future.infer_string` pin here so it applies before any
  submodule constructs a DataFrame (Python always runs a package's `__init__.py` before
  any of its submodules).
- `src/shared/packages/pyforge-atlas/tests/validation/test_validation_hook.py` --
  `test_empty_frame_with_valid_columns_passes` (~line 324) constructs an empty frame with
  `dtype=str`; needs the explicit `dtype="string[pyarrow]"` fix (collateral, not one of
  the six, but currently-green and must stay green).
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/core/nodes.py` --
  `attribute_feedstocks()` / `_pick_feedstock()` (~line 100-137): investigated, NO CHANGE
  needed — `_pick_feedstock` already returns clean `None`; only the pandas-level dtype
  coercion was losing it, and the `__init__.py` pin fixes that at the source.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/seed_gaps/nodes.py` --
  `report_license_map_gap()`: same — investigated, NO CHANGE needed for the same reason.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/semantic/metrics.py` -- `is_actionable`:
  investigated, NO CHANGE needed — already correct at the Ibis/SQL level. `ci_red`: patched
  in the review pass (`.fill_null(False)`, AUD-ATLAS-012) — its NULL result computed
  correctly once the pin restored identity, but review judged that correctness shouldn't
  depend incidentally on the pin; now null-safe like its siblings regardless.
- `.pixi/envs/pyforge-atlas` verify-gate tasks (pixi.toml `[feature.pyforge-atlas.tasks]`)
  -- `kedro-test` (781→787), `kedro-catalog-check` (must stay 47/47) — no task changes,
  just the commands to verify with.

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-atlas/src/pyforge/atlas/__init__.py` -- add
  `import pandas as _pd` + `_pd.set_option("future.infer_string", False)` with a comment
  explaining why (AUD-ATLAS-011: pandas 3.0's default `str` dtype uses `NaN` as its
  missing-value sentinel instead of `None`, breaking None-identity project-wide,
  including inside Ibis's own DuckDB→pandas result conversion) -- root-causes all six
  regressions in one place instead of six scattered per-site patches.
- [x] `src/shared/packages/pyforge-atlas/tests/validation/test_validation_hook.py` --
  change `test_empty_frame_with_valid_columns_passes`'s two
  `pd.Series([], dtype=str)` constructions to `pd.Series([], dtype="string[pyarrow]")`
  -- prevents the one collateral regression the pin above causes (pandera's `Column(str)`
  dtype-checks an empty column's literal declared dtype, which it always expects to be
  `string[pyarrow]` regardless of the `future.infer_string` setting).
- [x] `src/shared/packages/pyforge-atlas/src/pyforge/atlas/__init__.py` -- (review-pass
  patch) wrap the `set_option` call in `try/except _pd.errors.OptionError` -- the option's
  own pandas docstring flags it for deprecation "at" pandas 3.0 (the version this package
  already floors on), so an unguarded call risks crashing package import on a future
  pandas release; the guard degrades gracefully to the pre-fix pandas-3.0 default instead.
- [x] `src/shared/packages/pyforge-atlas/src/pyforge/atlas/semantic/metrics.py` --
  (review-pass patch, AUD-ATLAS-012) add `.fill_null(False)` to `ci_red`, matching the
  sibling predicates (`has_open_prs`, `has_open_issues`) so a NULL `ci_status` reads as
  not-red independent of the `future.infer_string` pin's specific mechanics.
- [x] `src/shared/packages/pyforge-atlas/src/pyforge/atlas/__init__.py` -- (review pass 2)
  broaden the pin's guard to `(OptionError, ValueError)` and emit a `RuntimeWarning` on
  fallback instead of degrading silently; disclose the import-time side effect in the
  package docstring.
- [x] `src/shared/packages/pyforge-atlas/tests/test_import_smoke.py` -- (review pass 2)
  add `test_pandas_null_identity_pin_applied`, a direct AUD-ATLAS-011 canary (option is
  `False` after import + a missing cell round-trips as `None`), so a future pin failure
  diagnoses HERE instead of as six cryptic downstream NaN mismatches (kedro-test 787→788).
- [x] `src/shared/packages/pyforge-atlas/src/pyforge/atlas/semantic/metrics.py` +
  `tests/semantic/PROVENANCE_NOTES.md` -- (review pass 2) record the AUD-ATLAS-012
  NULL-coalesce in `METRIC_PROVENANCE["ci_red"].note` and the mirrored notes doc; fix the
  docstring's "the same way" claim (siblings coalesce inputs, `ci_red` coalesces the
  membership test's output).
- [x] `src/shared/packages/pyforge-atlas/tests/validation/test_validation_hook.py` --
  (review pass 2) version-scope the "always expects `string[pyarrow]`" comment; strengthen
  `test_empty_frame_missing_a_required_column_halts` to assert the violation is the
  missing `version` column specifically (`column_in_dataframe`) and nothing else.

**Acceptance Criteria:**
- Given a frame with a genuine NULL in a grouping column, when it flows through
  `attribute_feedstocks`, `report_license_map_gap`, and the BSL semantic-layer queries in
  `models.py`, then the null group/cell is `None`, never `NaN`.
- Given the `join_packages_by_maintainer` query grouped by `maintainer`, when a package has
  no maintainer, then the `None`-keyed group is present in the result with a NULL measure
  value, and no real package's measure is attributed to it.
- Given `pixi run -e pyforge-atlas kedro-test`, when it runs after this change, then all
  788 tests pass (0 failed, 19 skipped) — the original 787 (up from 781 passed / 6 failed
  on `main`) plus the review-pass-2 pin canary, with no new failures introduced (the
  pandera collateral fix keeps `test_validation_hook.py` fully green).
- Given `pixi run -e pyforge-atlas kedro-catalog-check`, when it runs after this change,
  then all 47 tests continue to pass.
- Given the six named regression tests, when they run after this change, then every
  original assertion in each is satisfied verbatim — none was loosened, replaced, or
  made NaN-tolerant.

## Design Notes

**Root-cause mechanism (why one pin fixes six symptoms):** pandas 3.0 turned on
`future.infer_string` by default — any `pd.DataFrame(...)`/`pd.Series(...)` construction
from a Python list of strings (optionally mixed with `None`) now infers the new `str`
dtype, whose missing-value sentinel is a float `NaN`, not `None`
(`pd.DataFrame({"c": ["x", None]})["c"].iloc[1]` → `nan`, `type=float`). This hits two
places identically:

1. This package's own pipeline code (`attribute_feedstocks`, `report_license_map_gap`)
   assigns a Python list containing `None` to a DataFrame column.
2. Ibis's DuckDB backend (`ibis/backends/duckdb/__init__.py::execute`) does the *exact
   same thing* internally: for any result column with nulls, it calls
   `col.to_pylist()` (a pyarrow method that correctly yields Python `None`) and then
   passes that list into a plain `pd.DataFrame({...})` constructor — which re-applies
   pandas' own string-dtype inference and re-introduces the `NaN` sentinel. This is why
   the semantic-layer group-key test (`maintainer`) and the `ci_red` boolean-predicate
   test fail too, even though `models.py`/`metrics.py`'s own Ibis expressions are
   already correct.

Setting `pd.set_option("future.infer_string", False)` once, at `pyforge.atlas`
package-init, restores the pre-3.0 default (`object` dtype, `None`-preserving) for BOTH
paths — verified empirically: with only this one-line change, `kedro-test` goes from
781 passed / 6 failed straight to 787 passed / 0 failed, with the sole side effect being
the one pandera collateral case fixed alongside it. No change to `nodes.py`,
`metrics.py`, or `models.py` was needed or made.

**`metrics.py`'s `ci_red` (added in the review pass, AUD-ATLAS-012):** the pin alone was
sufficient to make `test_feedstock_health_filters_match_legacy` pass — once `None`
identity is restored, `bool(None) == False` incidentally matches the legacy WHERE-clause
semantics (`NULL IN (...)` excludes the row) that `_legacy_ci_red(None)` encodes. The
original planning pass judged a `.fill_null(False)` addition out of scope on that basis.
Review (Blind Hunter, cross-checked against this project's audit ledger where
AUD-ATLAS-012 is filed as a distinct, genuine defect — not a pandas-version artifact —
plus `sprint-status.yaml`'s own note on this story: "Related: AUD-ATLAS-012 ... may share
a root cause; verify") judged this correctness should not depend incidentally on the
pandas option's specific mechanics. `ci_red` now matches its siblings (`has_open_prs`,
`has_open_issues`, `is_actionable`) by coalescing its NULL-prone input explicitly, so its
correctness holds independent of the `future.infer_string` pin.

**The `test_is_actionable_matches_legacy_view` failure was pre-existing test fragility,
not a production bug:** `is_actionable`'s Ibis expression already used `.fill_null(...)`
correctly on both `latest_status` and `feedstock_archived`, so its actual query result
was always correct (`True` for a NULL-status row, matching the test's own hardcoded
truth table at the end of the test). The test's *per-row* loop failed only because its
own `_legacy_is_actionable(...)` helper checked `latest_status is not None` against a
value drawn from the test's own `pd.DataFrame(...)`-constructed input — which, under
pandas 3.0, silently became `NaN` instead of `None` for that cell. The pin fixes this
too, since it's the exact same mechanism applied to the test's own local DataFrame
construction (test file needed zero direct changes for this one).

## Review Triage Log

### 2026-07-28 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5 (medium 2, low 3)
- defer: 2 (medium 2)
- reject: 4
- addressed_findings:
  - `[medium]` `[patch]` AUD-ATLAS-012 — `ci_red` (`semantic/metrics.py`) had no `.fill_null(False)` unlike sibling predicates (`has_open_prs`, `has_open_issues`); its NULL-row correctness only held incidentally via the `future.infer_string` pin. Added `.fill_null(False)` so it's null-safe independent of the pin.
  - `[medium]` `[patch]` `_pd.set_option("future.infer_string", False)` in `__init__.py` was unguarded against the option's own documented pandas-3.0 deprecation target — a future pandas release removing it would crash package import. Wrapped in `try/except _pd.errors.OptionError`.
  - `[low]` `[patch]` `__init__.py`'s comment over-claimed "every DataFrame construction... preserves None," ignoring pre-existing `pd.NA`-based nullable-extension-dtype columns elsewhere (e.g. `vcs_health/nodes.py`). Reworded to scope the claim accurately.
  - `[low]` `[patch]` `test_validation_hook.py`'s `test_empty_frame_with_valid_columns_passes` had no comment explaining the `string[pyarrow]` choice. Added one, plus a forward-pointer to the deferred landmine finding below.
  - `[low]` `[patch]` `test_empty_frame_missing_a_required_column_halts` (same file, untouched by the original diff) still used `dtype=str` for its empty frame, incidentally tripping the same dtype mismatch alongside its intended missing-column failure. Aligned to `dtype="string[pyarrow]"` for test isolation.

Deferred (2, both medium — logged to `deferred-work.md`, not code-fixed this pass): a future pandera `Column(str)` contract in `DEFAULT_CONTRACTS` will spuriously halt on a legitimately empty, naturally-`object`-dtype frame; the `future.infer_string` pin is process-wide mutable pandas state with no scoping across a future shared-process `pyforge-*` deployment.

Rejected (4, dropped silently per triage rules — noted here only for this pass's own record): "diff conflicts with the project's audit ledger" (misread — that ledger's later section confirms AUD-ATLAS-011 was OPEN on `main` and deferred to "its own story," i.e. this one, mandating no specific mechanism); "zero regression coverage for the Ibis DuckDB→pandas conversion claim" (the six named tests already exercise it); "no safeguard against a later re-flip of the option" (speculative); "no upper bound on the `pandas` dependency" (superseded by the `OptionError` guard patch above).

### 2026-07-28 — Review pass 2 (follow-up on the `done` spec, fresh reviewers)
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 0, medium 2, low 5)
- defer: 1: (high 0, medium 1, low 0)
- reject: 8
- addressed_findings:
  - `[medium]` `[patch]` the `OptionError` guard in `__init__.py` degraded SILENTLY — a future pandas removing/locking `future.infer_string` would re-expose the AUD-ATLAS-011 NaN regressions with zero runtime signal. Now emits a `RuntimeWarning` on fallback and also catches `ValueError` (option kept but the `False` value rejected).
  - `[medium]` `[patch]` nothing tested the pin itself — coverage was entirely incidental via six downstream tests whose failure mode is cryptic NaN mismatches several layers away. Added `test_pandas_null_identity_pin_applied` to `tests/test_import_smoke.py` (option is `False` after import + a missing cell round-trips as `None`); kedro-test 787→788.
  - `[low]` `[patch]` `METRIC_PROVENANCE["ci_red"].note` + `tests/semantic/PROVENANCE_NOTES.md` still described the bare `IN ('failure','error')` mapping — the pass-1 commit changed the formula without updating the provenance registry that exists to record exactly that (the sibling `has_open_issues` documents its COALESCE). Both now record the AUD-ATLAS-012 NULL-coalesce.
  - `[low]` `[patch]` `ci_red`'s docstring claimed the siblings coalesce "the same way" — they coalesce *inputs* (`fill_null(0) > 0`); `ci_red` coalesces the membership test's *output* (`NULL.isin(...)` is NULL). Reworded: same effect, different site.
  - `[low]` `[patch]` `test_validation_hook.py`'s comment stated `Column(str)` "always expects" `string[pyarrow]` — a pandera-0.32/pandas-3.0 observation asserted as timeless fact. Version-scoped the claim.
  - `[low]` `[patch]` `test_empty_frame_missing_a_required_column_halts` could not distinguish its named missing-column violation from the dtype mismatch it used to (incidentally) also trip — its assertions cannot see WHICH violation fired. Now asserts the failure cases are `column_in_dataframe`/`version` and nothing else.
  - `[low]` `[patch]` the package docstring did not disclose the new import-time side effect (pandas import + global option mutation). Disclosed in `__init__.py`'s docstring.

Deferred (1, medium — appended to `deferred-work.md` as a NEW entry per the orchestrator's instruction; no existing entries touched): `ci_red` is duplicated as raw SQL outside the declared-once `metrics.py` definition (`wasm/index.html`'s projected column; `tests/publish/test_emit_range.py`'s FILTER), and the AUD-ATLAS-012 NULL-coalesce lives only in the metrics.py copy — the surfaces agree on a NULL `ci_status` today only through downstream truthiness accidents.

Rejected (8, dropped per triage rules — noted for this pass's record): the spec's frozen Never-clause vs the shipped `.fill_null` "contradiction" (the layered spec format already records the override — Design Notes/tasks/pass-1 triage give the single reconciling reading: `.fill_null` is the AUD-ATLAS-012 fix, not part of the AUD-ATLAS-011 mechanism the Never clause scopes to; the intent-contract is frozen by design); `reset_option` re-flip fragility (re-raise of a pass-1 decision — state-scoping half already a ledger entry, re-flip half rejected as speculative; the new canary adds detection inside this suite); the pandera empty-frame landmine (already ledger entry #1 from pass 1 — the reviewer checked `planning-artifacts/deferred-work-ledger.md`, the wrong file, and reported it untracked); the test comment's pointer to the gitignored Tier-3 ledger (matches this repo's actual deferred-work convention; the durable record is this spec); the unpinned Ibis-internal dependency of the fix's semantic-layer half (pass-1 rejection stands — the six named tests cover that path; a speculative upper bound contradicts dep policy); the commit message under-reporting the second test edit (immutable record, minor); frames built before `pyforge.atlas` import escaping the pin (within-package ordering is guaranteed by Python's package-init semantics; the cross-package half is ledger entry #2); "deferred-work.md does not exist" (factually wrong — verified present with both pass-1 entries).

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` -- expected: `788 passed, 19 skipped` (0 failed;
  up from the `main` baseline of `781 passed, 6 failed, 19 skipped`; the 788th is the
  review-pass-2 AUD-ATLAS-011 pin canary in `tests/test_import_smoke.py`).
- `pixi run -e pyforge-atlas kedro-catalog-check` -- expected: `47 passed` (unchanged).
- `pixi run -e pyforge-atlas kedro-test -- -k "test_attribute_feedstocks_handles_nan_feedstocks_cell or test_attribute_feedstocks_node or test_licmap_likely_and_report_tiers or test_is_actionable_matches_legacy_view or test_feedstock_health_filters_match_legacy or test_maintainer_with_no_packages_and_package_with_no_maintainer"` -- expected: all six pass, confirming the exact named regression set.


## Auto Run Result

**Status:** done (review pass 2 — follow-up review on the already-`done` spec, per step-01 routing).

**Summary:** fresh Blind Hunter + Edge Case Hunter passes over the full baseline→HEAD diff
(`ffd9275b` → `2e405ce6`) produced 19 raw findings; after dedup and context-grounded triage:
0 intent_gap, 0 bad_spec, 7 patch (2 medium, 5 low), 1 defer (medium), 8 reject. All seven
patches applied and verified; the hardened result committed as `1f4a5b1cf7`.

**Files changed this pass:**
- `src/pyforge/atlas/__init__.py` — pin fallback now warns (`RuntimeWarning`) instead of
  silently degrading; guard broadened to `(OptionError, ValueError)`; import-time side
  effect disclosed in the package docstring.
- `tests/test_import_smoke.py` — new `test_pandas_null_identity_pin_applied` canary
  (option `False` after import + `None` round-trip), so pin failures diagnose at the
  source instead of as six cryptic downstream NaN mismatches.
- `src/pyforge/atlas/semantic/metrics.py` — `METRIC_PROVENANCE["ci_red"].note` records the
  AUD-ATLAS-012 NULL-coalesce; docstring's input-vs-output coalesce claim corrected.
- `tests/semantic/PROVENANCE_NOTES.md` — mirrored provenance note updated.
- `tests/validation/test_validation_hook.py` — `string[pyarrow]` comment version-scoped;
  missing-column test now asserts `column_in_dataframe`/`version` failure cases only.

**Review findings breakdown:** 7 patched (above), 1 deferred (ci_red raw-SQL duplicates on
the WASM/publish surfaces vs the declared-once metrics.py definition — appended to
`deferred-work.md` as a NEW entry; existing entries untouched per the orchestrator's
instruction), 8 rejected (full rationale in the pass-2 triage log; notable: both prior
deferred entries were confirmed PRESENT in `deferred-work.md` — the reviewer claim that
the ledger was missing checked the wrong file).

**Verification:** `pixi run -e pyforge-atlas kedro-test` → 788 passed, 19 skipped, 0
failed (787 + the new canary). `pixi run -e pyforge-atlas kedro-catalog-check` → 47
passed. Working tree clean at `1f4a5b1cf7`.

**Follow-up review recommendation:** false — 5 of 7 patches are comment/doc/registry
wording; the 2 medium patches (fallback warning, canary test) change no reachable
production behavior.

**Residual risks:** the pin remains process-global mutable pandas state (ledger entry from
pass 1); the pandera empty-frame `Column(str)` landmine stays dormant until a real
contract lands in `DEFAULT_CONTRACTS` (ledger entry from pass 1); the semantic-layer half
of the fix still rides Ibis's current DuckDB→pandas conversion internals — covered by the
six regression tests plus the new canary, which localize any future breakage.
