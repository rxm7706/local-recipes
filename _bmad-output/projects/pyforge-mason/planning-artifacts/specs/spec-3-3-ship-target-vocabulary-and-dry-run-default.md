---
title: 'Ship-target vocabulary and dry-run default'
type: 'feature'
created: '2026-08-13'
status: 'done'
baseline_revision: 'b32a475f63696d07e78bc69323d16448b3661b78'
final_revision: 'f3f316c3491e87bc224d7f75acd126abedb2af1c'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/src/shared/packages/pyforge-mason/src/pyforge/mason/recipe.py'
warnings: []
---

<intent-contract>

## Intent

**Problem:** `--ship`/`--to` (FR-16, FR-19, NFR-9) has no vocabulary type or validator yet, and
nothing produces a safe "plan and print, upload nothing" default -- `package.py` has only
`build()` (Story 3.2); a user has no way to name a ship destination or see what shipping *would*
do before any upload engine (Stories 3.4-3.6) or the `ship` verb (Story 3.9) exist.

**Approach:** Add a closed `ShipTargetKind`/`ShipTarget` vocabulary to `models.py`, a
`parse_ship_targets()` validator and a `plan_ship()` planner to `package.py`, and a new
`InvalidShipTargetError` to `errors.py` -- mirroring `recipe.py::submit()`'s already-established
`ShipTargetResult(state=NOT_ATTEMPTED, reference=None, ...)` dry-run mapping (AD-9) rather than
inventing a second shape. No CLI wiring: the `ship` verb and its flags are Story 3.9's scope,
built only after the target adapters (3.4-3.6) exist to dispatch to.

## Boundaries & Constraints

**Always:**
- Exactly three forms accepted: `pypi`, `conda-forge`, `channel:<name>` (`<name>` non-empty) --
  Story 3.3's AC1 literal set (no `pypi-test`; that form is FR-50/Story 3.9's scope).
- `parse_ship_targets(value)` splits on `,`, strips each token, and parses each independently;
  ANY invalid token raises `InvalidShipTargetError` naming that token and listing the three valid
  forms verbatim (AC1: "rejected with the valid set listed").
- `plan_ship()` is the only ship-related behavior this story implements, and it is always the
  dry-run path -- there is no `confirm`/execute parameter yet (no engine exists to execute
  against until 3.4-3.6). Each target's entry reuses `models.ShipTargetResult`
  (`state=ShipState.NOT_ATTEMPTED`, `reference=None`), the exact shape `recipe.py::submit()`
  already produces for its own dry run -- never a second "plan" shape.
- The `pypi` target's plan message states explicitly that the upload is irreversible
  (epic-3-context Requirements: "the `pypi` plan states the upload is irreversible").
- `ShipTargetResult.target` stays a plain `str` (the target's canonical form, e.g.
  `"channel:myorg"`) -- `models.py`'s own docstring precedent; `recipe.py::submit()` is untouched.
- Zero `cfe` reference anywhere touched by this story (AD-6): both new functions are pure and
  CFE-independent; `tests/meta/test_capability_tiers.py` already guards `package.py`.

**Block If:** a live grep of `models.py`/`package.py`/`errors.py` at execution time shows
`ShipTarget`, `ShipTargetKind`, `parse_ship_targets`, or `plan_ship` already defined (a concurrent
story landed first) -- reconcile with an operator rather than silently overwriting or duplicating.

**Never:**
- No CLI flag, verb, or `main()` dispatch wiring -- `cli.py` is untouched. The `ship` verb,
  `--to`/`--ship` flags, and the bare-noun `mason package --ship` alias are Story 3.9's scope.
- No actual upload/submission execution -- no `twine`/`pixi publish`/staged-recipes call, no
  `confirm`/`--yes` parameter. Stories 3.4-3.6 add the adapters this story's plan describes but
  never invokes.
- No `ShipReceipt` aggregate -- Story 3.7's scope (Cross-Story Dependencies).
- No `pypi-test` vocabulary form -- Story 3.9/FR-50's scope.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path, all three forms | `"pypi,conda-forge,channel:myorg"` | 3 `ShipTarget`s, kinds `PYPI`/`CONDA_FORGE`/`CHANNEL` in order, last one's `channel_name == "myorg"` | No error expected |
| Invalid value | `"pypi,bogus"` | Nothing parsed | `InvalidShipTargetError` (`ship:invalid-target`) naming `"bogus"`, listing the three valid forms |
| Empty channel name | `"channel:"` | Nothing parsed | `InvalidShipTargetError` naming `"channel:"` |
| Whitespace tolerance | `"pypi, conda-forge"` | 2 targets parsed, whitespace trimmed | No error expected |
| Dry-run plan | 3 parsed targets + a `PackageBuildResult` | 3 `ShipTargetResult`s, all `state=NOT_ATTEMPTED`, `reference=None`; pypi entry's message states irreversibility; no subprocess/engine call occurs | No error expected |

</intent-contract>

## Code Map

- `src/pyforge/mason/models.py` -- add `ShipTargetKind(StrEnum)` and `ShipTarget` (frozen
  dataclass).
- `src/pyforge/mason/errors.py` -- add `InvalidShipTargetError(value: str)`.
- `src/pyforge/mason/package.py` -- add `parse_ship_targets()` and `plan_ship()`.
- `src/pyforge/mason/recipe.py` -- read-only reference: `submit()`'s `confirm=False` branch and
  `_ship_target_result_from_cfe_result` (lines ~444-534) are the exact dry-run `ShipTargetResult`
  mapping this story mirrors; not edited.
- `tests/unit/test_models.py` -- extend with `ShipTargetKind`/`ShipTarget` coverage.
- `tests/unit/test_errors.py` -- extend with `InvalidShipTargetError` coverage.
- `tests/unit/test_package.py` -- extend with `parse_ship_targets`/`plan_ship` coverage.

## Tasks & Acceptance

**Execution:**
- [x] `models.py` -- add `ShipTargetKind(StrEnum)` with members `PYPI = "pypi"`,
  `CONDA_FORGE = "conda-forge"`, `CHANNEL = "channel"`; add `ShipTarget` frozen dataclass
  (`kind: ShipTargetKind`, `channel_name: str | None`, no defaults, mirrors `ShipTargetResult`'s
  own field convention).
- [x] `errors.py` -- add `InvalidShipTargetError(value: str)`: identifier `ship:invalid-target`,
  message names `value` and lists `pypi`, `conda-forge`, `channel:<name>` verbatim, raises
  `ValueError` on an empty `value` (mirrors `PackageProjectPathError`'s validation rigor),
  `__reduce__` override returning `(self.__class__, (self.value,))`.
- [x] `package.py` -- add `parse_ship_targets(value: str) -> tuple[ShipTarget, ...]`: split on
  `,`, strip each token; `"pypi"`/`"conda-forge"` match exactly, a `"channel:"`-prefixed token
  with a non-empty suffix becomes `CHANNEL` with that suffix as `channel_name`; anything else
  raises `InvalidShipTargetError(token)`.
- [x] `package.py` -- add `plan_ship(targets: Sequence[ShipTarget], build_result:
  PackageBuildResult) -> tuple[ShipTargetResult, ...]`: one `ShipTargetResult` per target
  (`state=ShipState.NOT_ATTEMPTED`, `reference=None`), `target` = the canonical string form
  (`"pypi"`, `"conda-forge"`, or `"channel:<name>"`); `message` names the relevant build
  artifact(s) and destination -- pypi: `wheel_path` + `sdist_path`, states the upload is
  irreversible; conda-forge: notes a staged-recipes pull request would be opened; channel:
  `conda_path` and the channel name.
- [x] `tests/unit/test_models.py` -- `ShipTargetKind` has exactly the 3 members; `ShipTarget`
  construction/immutability/equality, mirroring `ShipTargetResult`'s own test shape.
- [x] `tests/unit/test_errors.py` -- `InvalidShipTargetError` identifier/message/`__reduce__`/
  deepcopy/pickle-round-trip/rejects-empty-value, mirroring `PackageProjectPathError`'s suite.
- [x] `tests/unit/test_package.py` -- `parse_ship_targets`: each of the 3 forms individually, all
  three comma-separated (order preserved), invalid value (message + identifier), empty channel
  name, whitespace tolerance. `plan_ship`: dry-run plan content for all three kinds (state,
  reference, pypi irreversibility wording, channel name in message).

**Acceptance Criteria:**
- Given `parse_ship_targets("pypi")` / `("conda-forge")` / `("channel:myorg")`, when each is
  called, then it returns exactly one `ShipTarget` of the matching kind.
- Given `parse_ship_targets("bogus")`, when called, then `InvalidShipTargetError` is raised naming
  `"bogus"` and listing `pypi`, `conda-forge`, `channel:<name>` as the valid set.
- Given `parse_ship_targets("pypi,conda-forge,channel:myorg")`, when called, then all three
  targets are returned in order, each parsed independently of the others.
- Given three parsed targets and a `PackageBuildResult`, when `plan_ship()` is called, then it
  returns three `ShipTargetResult`s, all `state=ShipState.NOT_ATTEMPTED`, `reference=None`,
  uploading nothing (no subprocess or engine call occurs), and every result's `message` names its
  target's artifact and destination -- the `pypi` entry's message additionally states the upload
  is irreversible.

## Spec Change Log

## Review Triage Log

### 2026-08-13 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 9: (high 0, medium 2, low 7)
- defer: 0
- reject: 8
- addressed_findings:
  - `[medium]` `[patch]` `parse_ship_targets` let an empty token (from a leading/trailing/doubled
    comma, or an all-whitespace value, e.g. `"pypi,"`, `",pypi"`, `" "`) escape as a bare
    `ValueError` from `InvalidShipTargetError.__init__`'s own empty-value guard, instead of the
    `InvalidShipTargetError` the function's own docstring promises for "any other token" -- added
    an explicit empty-token check raising `InvalidShipTargetError("<empty>")` before the general
    match/raise logic.
  - `[medium]` `[patch]` `plan_ship`'s `PYPI`/`CHANNEL` messages interpolated `wheel_path`/
    `sdist_path`/`conda_path` directly with `!r}`, so a `PackageBuildResult` from a failed engine
    build (`None` on those fields, a documented state per `models.py`) rendered the literal text
    `"None"` into the printed plan as if it were a real path -- contradicts the AC's "the plan
    names every target, every artifact, and every destination." Added `_describe_artifact()`,
    rendering a `"no {label} was built"` note instead of `None`.
  - `[low]` `[patch]` `parse_ship_targets("channel: myorg")` (whitespace immediately after the
    `channel:` prefix) retained the leading space in `channel_name`, inconsistent with the
    whitespace tolerance already applied around commas -- now stripped.
  - `[low]` `[patch]` `plan_ship`'s `CHANNEL` branch was an unguarded `else`, silently treating any
    non-`PYPI`/`CONDA_FORGE` kind as a channel target -- changed to an explicit
    `elif target.kind is ShipTargetKind.CHANNEL`, with a final `else: raise AssertionError(...)`
    for exhaustiveness.
  - `[low]` `[patch]` Added a test proving `parse_ship_targets` is case-sensitive (`"PyPI"` is
    rejected), matching the docstring's existing claim, which was previously untested.
  - `[low]` `[patch]` Added a test for `InvalidShipTargetError`'s `not isinstance(value, str)`
    validation branch (previously only the empty-string branch was tested).
  - `[low]` `[patch]` Added a parametrized test (`test_parse_ship_targets_raises_invalid_ship_
    target_error_not_bare_value_error`) and a `plan_ship` `None`-artifact test covering the two
    fixes above.
  - Rejected (noise or matches deliberate spec/precedent, no action): the claim that
    `epic-3-context.md` does not exist (it does, at `_bmad-output/implementation-artifacts/
    epic-3-context.md` -- confirmed by reading it directly; the reviewing subagent's search missed
    the gitignored `implementation-artifacts/` tree); the `conda-forge` plan message naming no
    build artifact (deliberate -- a staged-recipes submission ships the recipe source, not the
    built `.conda` binary, per this spec's own Tasks section); duplicate targets left
    un-deduplicated (deliberate spec Always boundary: "no deduplication, no reordering"); a channel
    name containing a literal comma (unrealistic -- conda channel names do not contain commas;
    matches Story 3.2's own precedent for rejecting low-probability malformed-input scenarios);
    `parse_ship_targets(None)` raising `AttributeError` instead of a typed error (matches Story
    3.2's own precedent of not adding defensive validation beyond a parameter's declared type,
    since no current caller passes anything but a `str` -- this story adds no CLI wiring at all);
    `InvalidShipTargetError.value`'s docstring claim that it is "the ORIGINAL stripped token"
    (accurately describes the sole real call site, `parse_ship_targets`, not an enforced class
    invariant -- no other constructor call site exists in this codebase); `ShipTarget` accepting a
    `channel_name` inconsistent with its `kind` when constructed directly, bypassing the parser
    (`models.py` is documented as behaviour-free -- AD-1 -- so a `__post_init__` validation there
    would violate that architecture; `parse_ship_targets` is the sole real constructor today); the
    PRD's FR-16 naming four target forms while this story implements three (deliberate -- the
    fourth, `pypi-test`, is FR-50/Story 3.9's scope, matching this story's own AC1 literal set).

## Design Notes

`recipe.py::submit()` already established the dry-run mapping this story mirrors
(`recipe.py:516-520`):
```python
if not confirm:
    return ShipTargetResult(
        target="conda-forge", state=ShipState.NOT_ATTEMPTED,
        reference=None, message=message,
    )
```
`plan_ship()` generalizes this same mapping across all three vocabulary kinds, without a `confirm`
parameter at all -- this story's own scope has no code path that ever ships for real, so there is
nothing to invert. The `ship` verb (Story 3.9) is deliberately implemented AFTER the individual
target adapters (Stories 3.4-3.6), per this epic's own sprint-status story order (3.3 -> 3.4 ->
3.5 -> 3.6 -> 3.9 -> 3.7 -> 3.8): wiring a real `mason package ship` command before any adapter
exists to dispatch to would be premature, so this story stops at the vocabulary + plan layer.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Summary:** Added the closed `ShipTargetKind`/`ShipTarget` vocabulary (`pypi`, `conda-forge`,
`channel:<name>`) to `models.py`, `parse_ship_targets()` and `plan_ship()` to `package.py`, and
`InvalidShipTargetError` to `errors.py` -- the always-dry-run ship plan, mirroring
`recipe.py::submit()`'s established `ShipTargetResult(state=NOT_ATTEMPTED, reference=None, ...)`
mapping. No CLI wiring (Story 3.9's scope), matching the frozen intent contract.

**Files changed** (commit `ce442b3eee`):
- `src/pyforge/mason/models.py` -- `ShipTargetKind(StrEnum)`, `ShipTarget` frozen dataclass.
- `src/pyforge/mason/errors.py` -- `InvalidShipTargetError`.
- `src/pyforge/mason/package.py` -- `parse_ship_targets()`, `plan_ship()`, `_describe_artifact()`.
- `tests/unit/test_models.py`, `tests/unit/test_errors.py`, `tests/unit/test_package.py` --
  matching coverage.

**Review findings** (2026-08-13 pass, recorded in the Review Triage Log above): 9 patch (0 high, 2
medium, 7 low), all fixed in the same commit; 8 rejected as noise or matching deliberate
spec/precedent; 0 defer, 0 bad_spec, 0 intent_gap.

**Repair pass (this session, 2026-08-13/14, bmad-dev-auto resume):** the prior session's work
(commit `ce442b3eee`) failed bmad-loop's own S-13.7 deterministic verify gate --
`python scripts/spec_surface_reconcile.py` reported 6 `[drift]` findings because the owning Spec
(`spec-pyforge-mason`)'s `.memlog.md` did not name the six changed paths. No code or intent-contract
change was needed or made. Repaired by naming the six paths in `spec-pyforge-mason/.memlog.md`
(matching the established S-3.1/S-3.2 precedent for this same gap) and re-stamping the baseline via
`python scripts/spec_surface_check.py --write-baseline --spec pyforge-mason/spec-pyforge-mason`,
committed as `f3f316c349`.

**Verification performed:**
- `python scripts/spec_surface_reconcile.py` -- now exits 0 ("OK: every tracked file governed or
  allowlisted; no drift"), reproduced failing before the repair and passing after.
- `pixi run -e pyforge-mason pyforge-mason-test` -- 1086 passed, 1 deselected.

**Follow-up review recommendation:** `false` -- the repair touched only the parent Spec's
governance memlog and baseline stamp; no code or test content changed in this pass.

**Residual risks:** None identified. This story adds no CLI wiring by design; the vocabulary and
dry-run planner are exercised only by direct unit tests until Story 3.9 wires the `ship` verb.

