---
title: 'The ship verb and TestPyPI rehearsal'
type: 'feature'
created: '2026-08-13'
status: 'done'
baseline_revision: '1d3385d4a4d662276722ee31a557eb64edac91c3'
final_revision: 'a42bdbdfb95b514022dd8e04c5c6de39b9ef65e3'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/src/shared/packages/pyforge-mason/src/pyforge/mason/package.py'
  - '{project-root}/src/shared/packages/pyforge-mason/src/pyforge/mason/cli.py'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `package.py` has three per-target ship functions (Stories 3.4-3.6) but no `ship` verb
exists anywhere on the CLI, no dispatcher combines them into one multi-target command, and no
`pypi-test` (TestPyPI) target exists at all -- so SM-1's real publish has no rehearsal and no
command reaches any of the three functions.

**Approach:** Add `ShipTargetKind.PYPI_TEST` (same code path as `PYPI`, differing only in a new
`repository_url` knob on `engines.twine.upload`/`package.ship_pypi`). Add `package.py::ship()`, a
sequential per-target dispatcher that builds-or-plans once, calls the right per-kind function per
target, catches `MasonError` per target so one failure never blocks another (AD-9/FR-18), and gates
a same-invocation `pypi` target on its `pypi-test` sibling reaching `terminal` (FR-24/FR-50/AD-26).
Wire `mason package ship --to <targets>` (canonical) and `mason package --ship <targets>` (the one
documented bare-noun exception, D-12) in `cli.py`.

## Boundaries & Constraints

**Always:**
- Ship's `project_path` is always `Path.cwd()`, never a flag or positional -- every canonical
  example in the dream/PRD/epics (`mason package ship --to pypi,conda-forge`, `mason package
  --target library --ship pypi,conda-forge`, `mason package --ship pypi`) omits one; FR-48's closed
  v1 knob set has no project-path knob either. `package build` keeps its own explicit positional --
  ship does not adopt it.
- The confirming flag is `--yes` (mirrors `recipe submit`'s established name/shape exactly, not a
  new `--confirm`/`--force`). No `--dry-run` flag is added: omitting `--yes` already is the dry-run
  default (FR-19); a redundant flag for the same default is not introduced.
- `--to`/`--ship` accept exactly four tokens after this story: `pypi`, `pypi-test`, `conda-forge`,
  `channel:<name>` (FR-16). `ShipTargetKind.PYPI_TEST = "pypi-test"` is a new bare literal in
  `parse_ship_targets`, mirroring `"pypi"`/`"conda-forge"`'s own handling -- no prefix, no dedup (same
  no-reordering-of-INPUT, no-dedup precedent `parse_ship_targets` already documents for the other
  three).
- `pypi-test` reuses `ship_pypi` verbatim (AD-26: "identical code path... differing only in
  repository configuration") via a new `repository_url: str | None = None` keyword forwarded to
  `engines.twine.upload`, which appends `--repository-url <url>` to argv when set. Same
  `TWINE_USERNAME`/`TWINE_PASSWORD` credential check, same build-then-upload sequence, same
  `ShipTargetResult` shape -- only the computed `canonical` target string (`"pypi-test"` vs
  `"pypi"`) and the upload URL differ. The TestPyPI endpoint is a fixed constant,
  `"https://test.pypi.org/legacy/"` (PyPI's own documented TestPyPI upload URL) -- no flag, no env
  var; D-13 forbids a config file (`.pypirc`) as the alternative twine mechanism.
- `ship()` (new, `package.py`) is the ONE place multi-target dispatch happens.
  Dry-run (`confirm=False`): one `build()` call, then `plan_ship(targets, build_result)` -- `plan_ship`
  gains a `PYPI_TEST` branch (message names TestPyPI, never claims irreversibility -- that claim
  stays exclusive to `pypi`, FR-50). Real ship (`confirm=True`): NO shared upfront `build()` call --
  each target kind's own function owns its own build-or-none (`ship_pypi`/`ship_channel` each call
  `build()` internally per spec-3-4's own documented "accepting the minor redundancy... belongs to
  3.9" allowance; `ship_conda_forge` builds nothing, unchanged). A project needing only
  `conda-forge` must not be forced through `pep517`/`pixi` build engines it may not even have.
- `ship()` catches `MasonError` around each target's own function call and converts it to
  `ShipTargetResult(state=FAILED, message=str(exc))` for THAT target only, then continues the rest
  (spec-3-6's own docstring: "leaving a caller -- a future multi-target dispatcher -- free to catch
  it and continue", and 3.6's own AC: "the conda-forge target alone fails... and the pypi target
  completes normally"). Consequence: `ship`'s aggregate exit code is always `EXIT_OK`/`EXIT_FAILED`,
  **never** `EXIT_CFE_UNAVAILABLE` -- even for a lone `--to conda-forge` with an unresolved CFE root
  -- since a per-target `FAILED` result, not a raised exception, is what reaches `main()` uniformly
  regardless of how many targets were requested (deliberate; not every raised `MasonError` still
  reaches `main()`'s own except-clause taxonomy the way a single-target verb's does).
- FR-24/FR-50/AD-26 rehearsal gate: when both a `pypi-test` and a `pypi` target are requested in the
  SAME invocation, the FIRST `pypi-test` target always executes before the loop's normal per-target
  pass (regardless of which order the user typed them), and its result is reused (not re-run) at its
  original position in the OUTPUT order. Every `pypi` target in that same invocation is gated on
  that cached result: if its state is not `terminal`, that `pypi` target's own result is
  `NOT_ATTEMPTED` naming the gate and the rehearsal's actual state, and `ship_pypi`/`twine upload` is
  never called for it. A `pypi` target with no `pypi-test` sibling in the same invocation is
  unaffected (D-11: no cross-invocation memory exists to check against).
- `ship`'s aggregate exit code: `EXIT_FAILED` if any returned `ShipTargetResult.state ==
  ShipState.FAILED`, else `EXIT_OK` (AD-9: "failure if any target failed to *initiate*... success if
  every target reached `pending` or `terminal`" -- `NOT_ATTEMPTED`, including a dry-run and a
  rehearsal-gated skip, counts as success). The JSON/text envelope's own `status` field stays the
  literal `"ok"` regardless (matches every existing dispatch branch's "Mason ran successfully"
  convention; AD-9 governs the exit code, not this field).
- `--to`/`--ship`, `--target`, `--yes`, `--recipe-path` are registered TWICE: once on `ship`'s own
  verb subparser (canonical form, flag named `--to`) and once directly on the `package` NOUN parser
  itself (alias form, flag named `--ship`) -- argparse scoping requires this (a noun-level flag
  cannot be read after a verb token consumes the remaining argv, and vice versa); factor the
  four-flag registration into one shared `_add_ship_flags(parser, *, targets_flag)` helper in
  `cli.py` to avoid duplicating the `add_argument` bodies.
- The bare-noun exception check (`ns.noun == "package" and not verb and ns.ship`) is inserted BEFORE
  the existing generic `if not getattr(ns, "verb", None): ... return EXIT_USAGE` branch in `main()`
  -- it is the one documented carve-out from that rule (D-12/FR-30), not a replacement for it: bare
  `mason package` (no `--ship`) and bare `mason recipe`/`mason environment` remain EXIT_USAGE
  unchanged.
- `--recipe-path` (new, optional, default `None`) supplies `ship_conda_forge`'s `recipe_path`
  argument; inert when `conda-forge` is not among the requested targets (no warning emitted for
  this -- unlike `recipe update`'s `--repo`/`--pre`, no AC calls for one). Omitting it while
  targeting `conda-forge` is not a CLI usage error -- `ship_conda_forge`'s own
  `ShipCondaForgeRecipeMissingError` (already built, Story 3.6) is caught per-target like any other
  structural precondition, satisfying FR-23's "offers... does not generate silently" via that
  error's own message.

**Block If:** none -- every open question above (project-path defaulting, confirming-flag name,
`--recipe-path` mechanism, rehearsal env-var reuse, TestPyPI endpoint) is resolved by direct textual
evidence in the dream/PRD/epics/architecture or by an already-built precedent; no unattended
decision point remains.

**Never:**
- No `ShipReceipt` aggregate class, no idempotence/interrogation check (already-shipped detection)
  -- both AD-10/Story 3.7's scope. `ship()` returns a plain `tuple[ShipTargetResult, ...]`.
- No concurrent/parallel target execution (architecture "Deferred: Concurrency... every operation is
  sequential in v1"). A plain sequential loop, not threads/asyncio.
- No new engine, no `.pypirc`, no `TWINE_REPOSITORY`/`TWINE_REPOSITORY_URL` env-var reads -- the
  TestPyPI URL is a hardcoded constant passed as an explicit `--repository-url` argv value.
- No change to `ship_channel`'s signature, behavior, or credential handling.
- No `mason doctor` changes -- no AC in this story references `doctor`, and the existing
  `conda_forge_ship_ready` proxy (Story 3.6) already covers what `doctor` can observe.
- Story 3.8 ("Mason ships Mason", the actual self-hosting exercise against
  `src/shared/packages/pyforge-mason/`) is out of scope -- this story only builds the mechanism
  FR-24 describes, not the act of running it for a real release.
- No `--project-path`/positional path flag on `ship` (see Always).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Canonical happy path | `package ship --to pypi,channel:myorg --yes`, valid creds | both `TERMINAL`; aggregate `EXIT_OK` | No error |
| Alias happy path | `package --ship pypi --yes` (no verb token) | identical dispatch/result to the canonical form above | No error |
| Other bare nouns unaffected | `mason recipe`, `mason environment`, `mason package` (no `--ship`) | unchanged `EXIT_USAGE`, stderr | Usage error |
| Dry-run default | `package ship --to pypi` (no `--yes`) | `NOT_ATTEMPTED` plan; `pypi` message states irreversibility; nothing uploaded; `EXIT_OK` | No error |
| pypi-test dry-run | `package ship --to pypi-test` (no `--yes`) | `NOT_ATTEMPTED` plan naming TestPyPI; no irreversibility claim | No error |
| Rehearsal passes | `--to pypi-test,pypi --yes`, TestPyPI upload succeeds | `pypi-test` `TERMINAL`, then `pypi` runs for real and is `TERMINAL` | No error |
| Rehearsal fails | `--to pypi-test,pypi --yes`, TestPyPI upload fails | `pypi-test` `FAILED`; `pypi` is `NOT_ATTEMPTED` naming the gate, no upload attempted; `EXIT_FAILED` | Gated, not raised |
| pypi alone | `--to pypi --yes` (no pypi-test sibling) | runs immediately, no gate | No error |
| conda-forge precondition fails alongside others | `--to pypi,conda-forge --yes`, CFE unresolved | `conda-forge` alone `FAILED` naming the precondition; `pypi` completes normally; `EXIT_FAILED` (not `EXIT_CFE_UNAVAILABLE`) | Caught per-target |
| Invalid token | `--to bogus` | whole command fails before any target runs; message lists all four valid forms | Raises `InvalidShipTargetError`, `EXIT_FAILED` |

</intent-contract>

## Code Map

- `src/pyforge/mason/models.py` -- add `ShipTargetKind.PYPI_TEST = "pypi-test"`; update its
  docstring (the "no `pypi-test` form lands here... Story 3.9's own scope" sentence is now false).
- `src/pyforge/mason/errors.py` -- `InvalidShipTargetError`'s message: add `'pypi-test'` to the
  listed valid forms.
- `src/pyforge/mason/engines/twine.py` -- `upload()` gains `repository_url: str | None = None`;
  argv appends `["--repository-url", repository_url]` when set; update module + function
  docstrings (the "no repository_url parameter... Story 3.9's own scope" sentence is now false).
- `src/pyforge/mason/package.py` -- `parse_ship_targets`: add the `"pypi-test"` literal branch.
  `plan_ship`: add a `PYPI_TEST` branch (extract the existing inline `canonical` construction into a
  small `_canonical_target_name(target: ShipTarget) -> str` helper, reused by the new dispatcher's
  exception-catch path). `ship_pypi`: add `repository_url: str | None = None`, forward to
  `twine.upload`, compute `canonical = "pypi-test" if repository_url is not None else "pypi"` once
  at the top and use it at all three `ShipTargetResult(target=...)` construction sites. New
  module-level `_TESTPYPI_REPOSITORY_URL = "https://test.pypi.org/legacy/"` constant. New `ship()`
  function (the dispatcher) and its internal `_ship_one()` per-target helper -- **corrected, review
  pass 2**: the `confirm=False` branch calls `build()` only when at least one target is not
  `conda-forge`, else passes `plan_ship` an all-`None` placeholder `PackageBuildResult` (see Spec
  Change Log; mirrors the real-ship path's own already-stated "don't force build engines for a
  conda-forge-only ship" principle, previously applied inconsistently). Import `MasonError` from
  `.errors`.
- `src/pyforge/mason/cli.py` -- new `_add_ship_flags(parser, *, targets_flag: str) -> None` helper
  (`--target`/`--yes`/`--recipe-path` all `default=argparse.SUPPRESS` -- **corrected, review pass
  1**: a plain default caused a confirmed silent-clobber bug, see Spec Change Log -- plus one flag
  named by `targets_flag`, either `"--to"` (`required=True`) or `"--ship"` (`default=None`)).
  Capture `_noun_parsers: dict[str, argparse.ArgumentParser]` during the existing noun-registration
  loop (mirrors `_noun_verbs`) so the `package` noun parser is addressable afterward. Register `ship`
  on `_noun_verbs["package"]` (`_add_ship_flags(..., targets_flag="--to")`) alongside the existing
  `package build` block. Call `_add_ship_flags(_noun_parsers["package"], targets_flag="--ship")`
  once, also in that block. Add the bare-noun-exception check (`getattr(ns, "ship", None) is not
  None` -- **corrected, review pass 1**: was a truthy check, which mishandled `--ship ""`) before
  the existing generic usage-error branch. Add the `ns.noun == "package" and ns.verb == "ship"`
  dispatch branch. New `_dispatch_package_ship(ns: argparse.Namespace, *, raw_targets: str) -> int`
  helper shared by both call sites -- **corrected, review pass 1**: resolves `confirm`/`target`/
  `recipe_path` itself via `getattr(ns, ...)` rather than receiving them as parameters the callers
  read off `ns` directly (parses format, calls `package.ship(...)`, renders
  `{"targets": [{**dataclasses.asdict(r), "state": r.state.value} for r in results]}` -- **corrected,
  review pass 2**: was a bare `dataclasses.asdict(r)`, which left `state` as a raw `ShipState` member
  one level inside a list, where `render_text` does not strip its `repr()` (see Spec Change Log) --
  computes the aggregate exit code). Import `ShipState` from `.models`.
- `tests/unit/test_models.py` -- `ShipTargetKind.PYPI_TEST` coverage.
- `tests/unit/test_errors.py` -- `InvalidShipTargetError` message includes `pypi-test`.
- `tests/unit/test_engines_twine.py` -- `repository_url` argv coverage (present/absent).
- `tests/unit/test_package.py` -- `parse_ship_targets`/`plan_ship` pypi-test coverage; `ship_pypi`
  repository_url coverage; `ship()` dispatcher coverage (all matrix rows above).
- `tests/unit/test_cli.py` -- `ship` verb + `--ship` alias coverage; bare-noun-exception coverage
  (other nouns/bare `package` still `EXIT_USAGE`); exit-code aggregation coverage.

## Tasks & Acceptance

**Execution:**
- [x] `models.py` -- add `ShipTargetKind.PYPI_TEST = "pypi-test"`; update the enum's docstring.
- [x] `errors.py` -- `InvalidShipTargetError.__init__`'s message: `"'pypi', 'pypi-test',
  'conda-forge', 'channel:<name>'"`.
- [x] `engines/twine.py` -- `upload(paths, *, timeout=None, repository_url=None)`: when
  `repository_url` is not `None`, argv becomes `["twine", "upload", "--non-interactive",
  "--disable-progress-bar", "--repository-url", repository_url, *paths]`; update docstrings to
  remove the "Story 3.9's own scope, not this adapter's" disclaimer and document the new parameter.
- [x] `package.py` -- `_TESTPYPI_REPOSITORY_URL = "https://test.pypi.org/legacy/"` module constant.
- [x] `package.py::parse_ship_targets` -- add `elif stripped == "pypi-test": targets.append(
  ShipTarget(kind=ShipTargetKind.PYPI_TEST, channel_name=None))`.
- [x] `package.py` -- extract `_canonical_target_name(target: ShipTarget) -> str` from `plan_ship`'s
  existing inline logic (four branches: `pypi`/`pypi-test`/`conda-forge`/`channel:<name>`); update
  `plan_ship` to call it and add the `PYPI_TEST` branch's own message (names wheel/sdist via
  `_describe_artifact`, states upload to TestPyPI, never claims irreversibility).
- [x] `package.py::ship_pypi` -- add `repository_url: str | None = None` keyword; compute `canonical
  = "pypi-test" if repository_url else "pypi"` once, after the credential check; use `canonical` at
  all three existing `target="pypi"` literal sites; forward `repository_url=repository_url` to
  `twine.upload(...)`; update docstring.
- [x] `package.py` -- new `ship(raw_targets: str, *, confirm: bool, environ: Mapping[str, str],
  target: str = "library", recipe_path: str | None = None, cfe_root_arg: str | None,
  cfe_python_arg: str | None, cfe_timeout_arg: float | None, start_directory: Path) ->
  tuple[ShipTargetResult, ...]`: parses `raw_targets` via `parse_ship_targets` (letting
  `InvalidShipTargetError` propagate); when `not confirm`, calls `build()` once and returns
  `plan_ship(targets, build_result)`; else dispatches per target via an internal `_ship_one(t)`
  closure (calls `ship_pypi`/`ship_channel`/`ship_conda_forge` per `t.kind`, catching `MasonError`
  into a `FAILED` `ShipTargetResult` named via `_canonical_target_name`), pre-running the first
  `PYPI_TEST` target ahead of the main loop only when a `PYPI` target is also present, reusing that
  cached result at its original index and gating every `PYPI` target on its `state is
  ShipState.TERMINAL` (else `NOT_ATTEMPTED` naming the gate and the rehearsal's actual state) -- see
  intent-contract Always boundary for the exact algorithm.
- [x] `cli.py::_add_ship_flags(parser, *, targets_flag)` -- **corrected (review pass 1, see Spec
  Change Log):** `--target`/`--yes`/`--recipe-path` must use `default=argparse.SUPPRESS` (mirroring
  `_build_global_flags_parser`'s own established pattern and its own documented rationale for
  exactly this dual-registration hazard), NOT a plain `"library"`/implicit-`False`/`None` default.
  `--ship` (the `targets_flag != "--to"` branch) keeps `default=None` (single registration, no
  clobber risk) but its metavar/help text is unchanged from before.
- [x] `cli.py::build_parser` -- unchanged from before: capture `_noun_parsers[name] = noun_parser`
  inside the existing noun loop; register `ship_parser` on `_noun_verbs["package"]`, call
  `_add_ship_flags(ship_parser, targets_flag="--to")`; call
  `_add_ship_flags(_noun_parsers["package"], targets_flag="--ship")` once; refresh
  `_noun_verbs["package"].metavar`.
- [x] `cli.py::_dispatch_package_ship` -- **corrected (review pass 1):** signature becomes
  `_dispatch_package_ship(ns: argparse.Namespace, *, raw_targets: str) -> int` (drop the `confirm`/
  `target`/`recipe_path` parameters entirely) and resolve all three itself, inside the function body,
  via `getattr(ns, "yes", False)`, `getattr(ns, "target", "library")`, `getattr(ns, "recipe_path",
  None)` -- mirroring how every existing dispatch branch already reads the six AD-13 global flags,
  never `ns.yes`/`ns.target`/`ns.recipe_path` directly. This is the ONE place the resolution happens
  now, so both call sites in `main()` no longer need to read those three attributes themselves at
  all. Everything else about this helper (the `package.ship(...)` call, the render shape, the
  aggregate-exit-code rule) is unchanged from before.
- [x] `cli.py::main` -- both call sites simplify to `_dispatch_package_ship(ns, raw_targets=ns.ship)`
  and `_dispatch_package_ship(ns, raw_targets=ns.to)` respectively (no more `confirm=`/`target=`/
  `recipe_path=` kwargs -- the helper now resolves them itself, see above). **Corrected (review pass
  1):** the bare-noun-alias check's condition changes from `getattr(ns, "ship", None)` (truthy) to
  `getattr(ns, "ship", None) is not None` -- an explicit `--ship ""` must reach `package.ship("")`
  and fail with `InvalidShipTargetError` (matching `--to ""`'s existing behavior, spec I/O matrix
  "Alias happy path... identical dispatch/result to the canonical form"), not silently fall through
  to the generic bare-noun usage error. Import `ShipState` from `.models` (unchanged from before).
- [x] `package.py::_canonical_target_name` -- **new correction (review pass 1):** add
  `# pragma: no cover` to its `raise AssertionError(...)` fallback, matching `_ship_one`'s own
  identical fallback (both are structurally unreachable given `ShipTargetKind`'s closed membership;
  the coverage-tooling annotation should be consistent between the two, not present on one and
  absent on the other).
- [x] `package.py::ship_pypi` -- **new correction (review pass 1):** change `canonical = "pypi-test"
  if repository_url else "pypi"` to `canonical = "pypi-test" if repository_url is not None else
  "pypi"`, matching `engines.twine.upload`'s own `if repository_url is not None:` identity check a
  few lines away in the same feature (currently the only two `repository_url` call sites in the
  codebase disagree on truthiness vs. identity for the same value -- harmless today since
  `repository_url` is always exactly `None` or the fixed non-empty constant, but the two checks
  should agree on the same idiom regardless).
- [x] `tests/unit/test_package.py` -- **new test (review pass 1):** a real-ship invocation
  containing a `PYPI_TEST` target with NO `PYPI` sibling anywhere in the same `targets` tuple (a
  lone `--to pypi-test --yes`, and a duplicated `--to pypi-test,pypi-test --yes`) exercises the
  ordinary per-target loop, not the pre-run/gate path -- assert `ship_pypi` is called once per
  `PYPI_TEST` token (no caching/reuse without a `PYPI` sibling present) and the pre-run block never
  runs (e.g. via call-count assertions on a mocked `ship_pypi`).
- [x] `tests/unit/test_cli.py` -- **new tests (review pass 1):** `--yes`/`--recipe-path`/`--target`
  given BEFORE the verb token (`mason package --yes ship --to pypi`, `mason package --recipe-path X
  ship --to conda-forge`) parse identically to giving them after (`mason package ship --to pypi
  --yes`) -- assert `package.ship`'s `confirm`/`recipe_path`/`target` kwargs match regardless of
  flag position, via `build_parser().parse_args(...)` and via `main()` + mocked `package.ship`. Also:
  `mason package --ship ""` (empty string) reaches `package.ship("")` (mock it and assert called
  with `raw_targets=""`), not the generic bare-noun usage error.
- [x] `tests/unit/test_models.py` -- `ShipTargetKind.PYPI_TEST.value == "pypi-test"`.
- [x] `tests/unit/test_errors.py` -- `InvalidShipTargetError` message contains `pypi-test`.
- [x] `tests/unit/test_engines_twine.py` -- `upload(..., repository_url="https://test.pypi.org/legacy/")`
  puts `--repository-url` + the URL in argv immediately before the paths; omitted when `None`
  (existing tests' argv assertion still holds unchanged).
- [x] `tests/unit/test_package.py` -- `parse_ship_targets("pypi-test")` returns `PYPI_TEST`;
  `plan_ship` with a `PYPI_TEST` target produces a `NOT_ATTEMPTED` message naming TestPyPI with no
  irreversibility claim; `ship_pypi(..., repository_url=...)` sets `target="pypi-test"` on all three
  result branches and forwards `repository_url` to a mocked `twine.upload`; `ship()`: every I/O
  matrix row above, plus -- multiple `pypi-test` tokens: only the first gates `pypi`, later ones
  still execute independently; a `MasonError` from any one target's function does not stop later
  targets in the loop; dry-run calls `build()` exactly once regardless of target count; real-ship
  with only `conda-forge` requested never calls `build()`/`pep517`/`pixi` (mock and assert
  `not_called`).
- [x] `tests/unit/test_cli.py` -- `package ship --to pypi --yes` and `package --ship pypi --yes`
  both dispatch to `pyforge.mason.cli.package.ship` with equivalent kwargs; bare `mason package`
  (no `--ship`) still `EXIT_USAGE`; `mason recipe`/`mason environment` bare-noun tests unaffected;
  `--to` omitted on `ship` is a native argparse usage error; JSON mode's `data["targets"]` is a list
  of `ShipTargetResult` dicts; a mocked multi-result return with one `FAILED` entry projects
  `EXIT_FAILED`; an all-`NOT_ATTEMPTED`/`TERMINAL` mocked return projects `EXIT_OK`;
  `--cfe-root`/`--cfe-timeout` reach `package.ship`'s `cfe_root_arg`/`cfe_timeout_arg` kwargs (unlike
  `package build`'s established never-reads-cfe-flags precedent, `ship` DOES need them for its
  `conda-forge` target).
- [x] `package.py::ship` -- **corrected (review pass 2, see Spec Change Log):** the `confirm=False`
  (dry-run) branch must NOT unconditionally call `build()` -- only when at least one requested
  target is NOT `ShipTargetKind.CONDA_FORGE` (i.e. `any(t.kind is not ShipTargetKind.CONDA_FORGE for
  t in targets)`). When every requested target IS `conda-forge`, skip `build()` entirely and pass
  `plan_ship` a placeholder `PackageBuildResult(target=target, project_path=project_path,
  wheel_path=None, sdist_path=None, conda_path=None, wheel_version=None, conda_version=None,
  pep517_returncode=0, pixi_returncode=0, pep517_stdout="", pixi_stdout="")` instead -- safe because
  `plan_ship`'s own `CONDA_FORGE` branch never reads any `build_result` field (its message is a fixed
  string). This mirrors the real-ship path's own already-stated principle two paragraphs later in
  this same docstring ("A project needing only `conda-forge` must not be forced through
  `pep517`/`pixi` build engines it may not even have") -- previously that principle was applied only
  to the real-ship path, not the dry-run path, so `mason package ship --to conda-forge` (no `--yes`)
  crashed with `EngineAbsentError` on a host missing pep517/pixi tooling instead of printing the
  intended plan -- exactly the safe-preview scenario `FR-19`'s dry-run default exists to support.
- [x] `cli.py::_dispatch_package_ship` -- **corrected (review pass 2):** the `data` payload's
  `"targets"` list must not embed a raw `ShipState` member -- `render_text`'s existing
  `f"{data[key]}"` line only strips `StrEnum`'s wrapper for a value sitting directly at `data`'s own
  top level (`models.py`'s own documented reason for choosing `StrEnum`), but `"targets"` is a LIST
  of dicts one level deeper, which `render_text` was never exercised against before this story (no
  prior dispatch branch ever rendered a list). Build each target's dict as `{**dataclasses.asdict(r),
  "state": r.state.value}` rather than a bare `dataclasses.asdict(r)`, so `state` is already a plain
  `str` by the time it reaches either renderer. (JSON output is unaffected either way --
  `json.dumps` already serializes a `StrEnum` member as its plain string value -- this is a
  text-mode-only defect.)
- [x] `tests/unit/test_package.py` -- **new test (review pass 2):** `ship("conda-forge", confirm=False,
  ...)` (and a mix like `"conda-forge,conda-forge"`) never calls `build()` (mock it, assert
  `not_called`) and still returns a `plan_ship`-shaped `NOT_ATTEMPTED` result for each target; a
  dry-run mixing `conda-forge` with `pypi`/`channel:<name>` still calls `build()` exactly once
  (existing coverage, unchanged) -- the skip applies only when EVERY target is `conda-forge`.
- [x] `tests/unit/test_cli.py` -- **new test (review pass 2):** `--format text` (the default) on a
  `package ship` result renders the plain state value (e.g. `terminal`, `not_attempted`) for each
  target, never the `ShipState` member's own `repr()` (`<ShipState.TERMINAL: 'terminal'>`) -- assert
  the literal enum-repr substring `ShipState.` never appears anywhere in `capsys`-captured stdout.
- [x] `cli.py::main` -- **new (review pass 3, patch):** reject `--ship <targets>` combined with an
  explicit verb token (`mason package --ship pypi build .` / `mason package --ship pypi ship --to
  conda-forge`) as `EXIT_USAGE` naming the conflict, rather than silently discarding `ns.ship` --
  two independent review passes (3 total reviewer instances across this diff's history) flagged the
  silent-drop as a plausible real trigger (editing a prior `--ship ...` invocation to add an
  explicit verb, leaving the stale `--ship` in place). Checked before both the bare-noun-alias
  branch and the verb-dispatch branches.
- [x] `errors.py::ShipCredentialMissingError` -- **new (review pass 3, patch):** message no longer
  claims "shipping to pypi" specifically -- `ship_pypi` raises this identically for a real `pypi`
  ship and a `pypi-test` rehearsal (AD-26's "identical code path"), and the message is built before
  `ship_pypi` computes which of the two it is, so the prior wording was actively wrong for a
  `pypi-test` invocation missing credentials. Genericized to "set them before shipping" (no
  constructor parameter added -- a cosmetic distinction not worth threading through).
- [x] `tests/unit/test_cli.py` -- **new test (review pass 3):** `--ship <targets>` combined with an
  explicit verb (`build`, and `ship --to ...`) is `EXIT_USAGE`, names `--ship` in the diagnostic, and
  never reaches `package.ship`/`package.build`.
- [x] `tests/unit/test_errors.py` -- **new test (review pass 3):** `ShipCredentialMissingError`'s
  message never contains the substring "to pypi".
- [x] `tests/unit/test_package.py` -- **new tests (review pass 3):** a dry-run mixing `conda-forge`
  with `pypi-test` still calls `build()` exactly once (the skip-build boundary proven against
  `pypi-test` specifically, not only `pypi`/`channel:<name>`); a real-ship `--to
  conda-forge,pypi-test` (no plain `pypi` sibling) runs both targets through the ordinary per-target
  loop with no gating/reordering, confirming the rehearsal-gate pre-run never triggers without a
  `PYPI` target present.

**Acceptance Criteria:**
- Given FR-30's noun-verb rule and FR-15's build-uploads-nothing rule, when the command surface is
  built, then `mason package ship --to <targets>` exists as the canonical shipping command.
- Given the crew charter's cadence, when a user runs `mason package --target library --ship
  pypi,conda-forge`, then it works, dispatching to the same code path as `mason package ship`, and a
  test asserts this is the only bare-noun form that runs (other nouns, and bare `package` without
  `--ship`, remain `EXIT_USAGE`).
- Given `ship` invoked with no artifacts present, when it runs, then it builds by calling `build()`
  (FR-15's implementation), never a duplicated build sequence of its own.
- Given `--to pypi-test`, when it runs, then the upload goes to TestPyPI through the identical code
  path as `pypi` (`ship_pypi`), differing only in the `repository_url` argument.
- Given the FR-24 self-hosting sequence (both `pypi-test` and `pypi` requested together), when it
  executes, then `pypi-test` runs first regardless of the order given, and `pypi` runs only if that
  rehearsal reached `terminal`.
- Given a dry-run plan naming the `pypi` target, when it is printed, then it states explicitly that
  a PyPI upload is irreversible; the `pypi-test` plan message never makes that claim.

## Design Notes

**Why the aggregate exit code deviates from every other dispatch branch's "always EXIT_OK" rule:**
Every existing `cli.py` branch (`recipe build`, `package build`, ...) always returns `EXIT_OK` for a
Mason-successful invocation, treating a delegated tool's own failure as data (AD-4). `ship` is
different because AD-9 itself specifies the exit-code rule ("failure if any target failed to
initiate"), and a multi-target command has no single delegated-tool returncode to defer to -- the
aggregate has to be computed from the per-target state tuple. This is the one dispatch branch in
`cli.py` whose numeric exit code is genuinely data-dependent rather than uniformly `EXIT_OK`.

**Why `EXIT_CFE_UNAVAILABLE` never surfaces from `ship`, even for a lone `--to conda-forge`:**
`main()`'s top-level `except CfeUnresolvedError` clause only fires when that exception propagates
out of `package.ship(...)` itself -- but `ship()`'s own per-target catch (required by 3.6's own AC
for the multi-target case) intercepts it before it gets that far, for every invocation shape,
including a single-target one. Keeping single- and multi-target `conda-forge` shipping
exit-code-consistent was judged more valuable than preserving the finer-grained top-level exit code
for this one target kind alone.

## Spec Change Log

### 2026-08-13 — Review pass 1: the "no SUPPRESS/getattr dance" claim was wrong

**Triggering finding:** two independent reviewers (Blind Hunter, Edge Case Hunter), each without
sight of the other's work, both live-reproduced the same defect via `build_parser().parse_args(...)`:
`mason package --yes ship --to pypi` parses to `ns.yes == False` (confirmed independently: `--yes`
given before the verb token is silently clobbered back to its default when the `ship` subparser
re-parses the remaining argv into a fresh namespace and copies it onto the parent). Same mechanism
for `--recipe-path`. Re-verified directly against this worktree's own `build_parser()` before
writing this entry.

**What was amended:** the Always boundary bullet asserting "`--target`/`--yes`/`--recipe-path`...
need no `argparse.SUPPRESS`/`getattr` dance: they are per-verb-shaped flags, not part of that closed
six-knob AD-13 set" was factually wrong -- the SUPPRESS/getattr requirement has nothing to do with
AD-13's six-knob set; it applies to ANY flag registered on both an ancestor and a descendant parser
in this codebase's argparse subparsers structure, which `_build_global_flags_parser`'s own docstring
already documents for exactly this reason. That sentence is left in place inside `<intent-contract>`
(read-only per this workflow's rules) since the BOUNDARY it is attached to -- "a value set by one
registration and left untouched by the other never disagrees" -- states the correct, unchanged
requirement; only the incorrect technical justification for how to satisfy it was wrong. The actual
correction lands outside `<intent-contract>`, in `## Code Map` and `## Tasks & Acceptance`: `--target`/
`--yes`/`--recipe-path` now use `default=argparse.SUPPRESS` (both registration sites), and
`_dispatch_package_ship` resolves them via `getattr(ns, ..., <default>)`, mirroring the six AD-13
global flags' own established pattern exactly. Also folded into this same pass, from the same two
reviewers, since they are small and directly related to the same code region: the bare-noun-alias
check changes from a truthy `getattr(ns, "ship", None)` to an explicit `is not None` (an empty
`--ship ""` was silently falling through to the generic bare-noun usage error instead of reaching
`package.ship("")`'s own `InvalidShipTargetError`, contradicting this spec's own "byte-identical
dispatch" claim for the two forms); a `repository_url` truthy-vs-`is not None` inconsistency between
`ship_pypi` and `engines.twine.upload`; a missing `# pragma: no cover` on `_canonical_target_name`'s
unreachable-fallback (present on `_ship_one`'s identical fallback, absent here); and one missing test
for a lone/duplicated `PYPI_TEST` target with no `PYPI` sibling.

**Known-bad state avoided:** a real `mason package --yes ship --to pypi` (or any invocation putting
a AND global flag AFTER a ship-specific one but BEFORE the verb -- the natural place to put a
confirming flag when composing a command left-to-right) silently downgrades to a dry run and reports
`EXIT_OK`, with no error, no warning, and a rendered plan that -- read quickly -- could be mistaken
for evidence a real upload happened. This directly undermines FR-24/SM-1 (the primary success
metric: Mason publishing itself for real).

**KEEP instructions (what already worked and must survive unchanged):** `package.py::ship()`'s own
dispatcher body -- the rehearsal pre-run/gate algorithm, the per-target `MasonError` catch, the
`plan_ship`/`ship_pypi`/`_canonical_target_name` extraction -- was independently verified correct and
test-covered by both reviewers ("no deletion regressions found... behavior-preserving and
test-covered"; "Notably not a finding... [FR-18/AD-10 idempotence]... correctly out of scope"). None
of that requires any change. `models.py`, `errors.py`, and `engines/twine.py`'s `repository_url`
plumbing were not implicated by either review and must also survive unchanged (beyond the one
`is not None` idiom fix noted above). Only `cli.py`'s `_add_ship_flags`/`_dispatch_package_ship`
region, plus the two trivial cross-file consistency fixes above, need to change.

### 2026-08-13 — Review pass 2: dry-run build-forcing and a nested-StrEnum text-mode leak

**Triggering findings:** two independent reviewers (fresh instances, no sight of pass 1's own
findings or triage), both live-reproduced two NEW defects in the pass-1-corrected diff:

1. `render.render_text` on a `package ship` result prints the literal `<ShipState.TERMINAL:
   'terminal'>` instead of `terminal` -- reproduced directly against `render.render_text`. Root
   cause: `_dispatch_package_ship` built `"targets": [dataclasses.asdict(r) for r in results]` (a
   LIST of dicts, one level below `data`'s own top level), and `render_text`'s existing
   `f"{data[key]}"` line only strips `StrEnum`'s `repr()` wrapper for a value sitting directly at
   that top level -- no prior dispatch branch in this codebase ever rendered a list, so this gap in
   `render_text` was never exercised before this story. JSON output was never affected (`json.dumps`
   already serializes a `StrEnum` member as its plain value regardless of nesting depth).
2. `ship("conda-forge", confirm=False, ...)` on a host missing `pep517`/`pixi` tooling raises
   `EngineAbsentError` and aborts instead of printing the dry-run plan -- reproduced by reading
   `ship()`'s own `if not confirm:` branch, which calls `build()` unconditionally regardless of
   target composition.

**What was amended:** both root causes trace to this spec's own `<intent-contract>` Always boundary
bullets (read-only, left unchanged, per this workflow's rules) -- but in both cases the TRUE,
already-stated intent is unambiguous and unchanged; only an incomplete carry-through of that intent
into `## Code Map`/`## Tasks & Acceptance` (both outside `<intent-contract>`) was wrong, mirroring
review pass 1's own resolution shape:
- For (2): the SAME Always boundary paragraph that states "Dry-run... one `build()` call" ALSO
  states, two sentences later, for the real-ship path: "A project needing only `conda-forge` must
  not be forced through `pep517`/`pixi` build engines it may not even have." That second sentence's
  principle was never carried through to the dry-run path's own Code Map/Tasks description, which
  said "one `build()` call" unconditionally. Corrected: `## Code Map`/`## Tasks & Acceptance` now
  specify the dry-run branch skips `build()` entirely when every target is `conda-forge`, passing
  `plan_ship` a placeholder `PackageBuildResult` instead (safe, since `plan_ship`'s own
  `CONDA_FORGE` branch reads no `build_result` field).
- For (1): no Always boundary bullet specifies the exact `data` shape -- the literal
  `{"targets": [dataclasses.asdict(r) for r in results]}` expression lived only in `## Code Map`/
  `## Tasks & Acceptance`, entirely outside `<intent-contract>`, and directly caused the bug as
  written. Corrected there to `{**dataclasses.asdict(r), "state": r.state.value}` per target.

**Known-bad state avoided:** (1) every real `mason package ship` invocation (any state, any format)
printed a Python-internal `repr()` fragment in its default text output -- the flagship new command's
default output mode was broken for every non-trivial invocation. (2) the safest, most common way to
preview a conda-forge-only release (`mason package ship --to conda-forge`, no `--yes`, FR-19's own
dry-run default) crashed instead of showing a plan, on the exact class of repository (one with no
wheel-build tooling installed) D-10's own boundary already anticipates as a legitimate conda-forge-
only use case.

**KEEP instructions:** everything else already implemented and reviewed across two prior passes --
`ship()`'s rehearsal-gate algorithm, the real-ship per-target dispatch and its `MasonError` catch,
the `argparse.SUPPRESS` flag-registration fix from pass 1, `models.py`/`errors.py`/
`engines/twine.py` -- was not implicated by either reviewer this pass and must survive unchanged.
Both reviewers explicitly re-verified the pass-1 `SUPPRESS` fix as complete and correct with no
remaining clobbering path, and found no deletion-check regressions.

## Review Triage Log

### 2026-08-13 — Review pass 1
- intent_gap: 0
- bad_spec: 1: (high 1)
- patch: 3: (low 3) -- moot this pass (bad_spec present); re-evaluated next pass after re-derivation
- defer: 1: (low 1) -- moot this pass (bad_spec present); re-evaluated next pass after re-derivation
- reject: 5: (low 5)
- addressed_findings:
  - `[high]` `[bad_spec]` `--yes`/`--recipe-path` (and, as the same root cause's mirror image,
    `--target`) silently reset to their default when given BEFORE the `ship`/`--ship` verb token,
    because `_add_ship_flags` used plain defaults instead of `argparse.SUPPRESS` on both of its two
    registration sites -- live-reproduced independently by both reviewers and re-verified directly
    against this worktree. Root cause: the spec's own Always boundary asserted these three flags
    "need no `argparse.SUPPRESS`/`getattr` dance," which is factually wrong (the hazard is generic to
    any dual-registered argparse flag in this codebase's subparser structure, unrelated to AD-13's
    six-knob set). See Spec Change Log entry above for the full amendment; `## Code Map` and
    `## Tasks & Acceptance` corrected; looping back through `step-03-implement.md` to apply the fix.
  - `[low]` `[bad_spec]` (bundled into the same pass, not a separate loopback) `--ship ""` (empty
    string) silently fell through to the generic bare-noun usage error instead of reaching
    `package.ship("")`'s own `InvalidShipTargetError`, contradicting the spec's own "byte-identical
    dispatch" claim for the canonical/alias forms. Fixed alongside the primary finding above (same
    code region, same loopback).
  - `[low]` `[bad_spec]` (bundled) `ship_pypi`'s `canonical = "pypi-test" if repository_url else
    "pypi"` used truthiness while `engines.twine.upload`'s own `repository_url` check (added by the
    same story) uses `is not None` -- inconsistent idiom for the same value, two lines of the same
    feature disagreeing. Fixed alongside the primary finding.
  - `[low]` `[bad_spec]` (bundled) `_canonical_target_name`'s unreachable-fallback `raise
    AssertionError` lacked the `# pragma: no cover` its structural twin in `_ship_one` carries.
    Fixed alongside the primary finding.
  - `[low]` `[bad_spec]` (bundled) no test exercised `ship()`'s real-ship path for a lone or
    duplicated `PYPI_TEST` target with no `PYPI` sibling (only the pre-run/gate path was covered for
    that target kind). Test added alongside the primary finding.
- **Deferred** (moot this pass; will be re-evaluated by the next review pass since the finding is
  independent of the code being re-derived):
  - `[low]` architecture doc `AD-9`'s literal text ("success if every target reached `pending` or
    `terminal`") does not explicitly name `not_attempted` as a success state, though the correct,
    unambiguous reading (required by FR-19: a dry run, where every target is `not_attempted`, must
    never report failure) already treats it as one, and this spec's own Always boundary states that
    correct reading explicitly. Pre-existing architecture-doc imprecision, predates this story, not
    caused by this diff -- a documentation-clarity issue for `ARCHITECTURE-SPINE.md` itself, not a
    code defect.
- **Rejected** (matches established/spec-directed precedent, or not a real defect):
  - `[low]` `[reject]` TestPyPI and real PyPI have separate credential namespaces in practice, but
    `ship_pypi` checks the same `TWINE_USERNAME`/`TWINE_PASSWORD` for both. Explicitly spec-directed
    (Always boundary, citing AD-26's literal "identical code path... differing only in repository
    configuration" -- no separate credential vocabulary is named anywhere in FR-50/AD-26), and
    inventing a new TestPyPI-specific credential pair is out of this story's scope.
  - `[low]` `[reject]` the JSON/text envelope's `status` field stays `"ok"` even when the process
    exit code is `EXIT_FAILED`. Explicitly spec-directed (Always boundary, Design Notes) and matches
    the SAME established convention every other dispatch branch in this file already follows (AD-4:
    a delegated failure is data, not a reason to change the envelope's own success-reporting field).
  - `[low]` `[reject]` `--to conda-forge --yes` with an unresolved CFE root reports `EXIT_FAILED`
    rather than the more specific `EXIT_CFE_UNAVAILABLE` every other CFE-dependent verb reports for
    the identical root cause. Explicitly documented and reasoned in this spec's own Design Notes
    section ("Why `EXIT_CFE_UNAVAILABLE` never surfaces from `ship`...") as a deliberate trade-off,
    not an oversight.
  - `[low]` `[reject]` `tests/meta/test_credential_isolation.py` (the NFR-2 guard) has no awareness
    of `repository_url`/`pypi-test`. Verified: `repository_url` is a public URL constant, never a
    credential, and `TWINE_USERNAME`/`TWINE_PASSWORD` handling is completely unchanged by this
    story -- the existing guard's scope already covers this diff's only credential-touching code.
  - `[low]` `[reject]` `mason package --ship pypi build .` (both `--ship` and an explicit verb given)
    silently ignores the now-inert `--ship` value; the explicit verb always wins. Deterministic,
    unsurprising precedence (explicit beats implicit) for a self-contradictory input combination;
    matches this codebase's own established "inert flag combo, no warning" precedent (`recipe
    update`'s `--repo`/`--pre` without `--github`).

### 2026-08-13 — Review pass 2
- intent_gap: 0
- bad_spec: 2: (high 2)
- patch: 3: (low 3) -- moot this pass (bad_spec present); re-evaluated next pass after re-derivation
- defer: 0
- reject: 5: (low 5)
- addressed_findings:
  - `[high]` `[bad_spec]` `--format text` (the default) on any `package ship` result printed the raw
    `<ShipState.X: 'x'>` `repr()` instead of the plain state value -- reproduced directly against
    `render.render_text`. Root cause: `_dispatch_package_ship` embedded a raw `ShipState` member one
    level inside the rendered `"targets"` list, a shape `render_text` was never exercised against
    before this story. See Spec Change Log entry above; `## Code Map`/`## Tasks & Acceptance`
    corrected to stringify `state` before rendering; looping back through `step-03-implement.md`.
  - `[high]` `[bad_spec]` `mason package ship --to conda-forge` (dry-run, no `--yes`) crashed with
    `EngineAbsentError` on a host missing `pep517`/`pixi` build tooling, instead of printing the
    intended plan -- reproduced by reading `ship()`'s unconditional `build()` call in its
    `confirm=False` branch. Root cause: this spec's own stated "don't force build engines for a
    conda-forge-only ship" principle (already applied to the real-ship path) was never carried
    through to the dry-run path's Code Map/Tasks description. Fixed alongside the finding above
    (same loopback).
- **Deferred:** none this pass.
- **Rejected** (matches established precedent, duplicates a pass-1 rejection, or is speculative with
  no current defect):
  - `[low]` `[reject]` ship-only flags (`--yes`/`--recipe-path`) parse without error before the
    `build` verb (`mason package --yes --recipe-path /foo build ./proj`) and are silently unread by
    that branch. Same "inert flag combo, no warning" precedent already accepted for `recipe update`'s
    `--repo`/`--pre` and (pass 1) `--ship` + an explicit verb; no functional harm, no misleading
    output.
  - `[low]` `[reject]` `--ship <targets>` combined with an explicit verb token silently drops the
    `--ship` value. Duplicate of pass 1's already-rejected finding (explicit verb deterministically
    wins; same inert-combo precedent); re-surfaced by a fresh reviewer instance with no sight of that
    prior triage, re-confirmed on re-review.
  - `[low]` `[reject]` the JSON envelope's `status: "ok"` regardless of aggregate ship failure is an
    "easy-to-miss trap" for API consumers checking `status` instead of the exit code or per-target
    `state`. Duplicate of pass 1's already-rejected finding (explicitly spec-directed, matches AD-4's
    established codebase-wide convention); re-confirmed.
  - `[low]` `[reject]` `--target`'s two registrations (noun-level, verb-level) "agree only by luck"
    of `choices=("library",)` currently being a single-element tuple -- true, but purely speculative:
    nothing in this story or its scope widens that choice set, and no current defect exists to fix
    (Simplicity First: not designing for a hypothetical future requirement).
  - `[low]` `[reject]` `_add_ship_flags`'s `if targets_flag == "--to": ... else: ...` dispatch
    silently treats any string other than `"--to"` as the alias form, with no validation against a
    typo'd third value. Speculative -- exactly two call sites exist today, both correct and
    test-covered; no current defect.

### 2026-08-14 — Review pass 3
- intent_gap: 0
- bad_spec: 0
- patch: 5: (low 5)
- defer: 1: (low 1)
- reject: 1: (low 1)
- addressed_findings:
  - `[low]` `[patch]` `--ship <targets>` combined with an explicit verb token silently discarded the
    `--ship` value with no error or warning (`mason package --ship pypi build .` / `mason package
    --ship pypi ship --to conda-forge`). Re-surfaced independently by both reviewers this pass, on
    top of pass 1's identical finding (rejected then) -- upgraded from reject to patch given the
    persistence across three independent passes/six reviewer instances and a plausible realistic
    trigger (editing a prior `--ship ...` command to add an explicit verb, leaving the stale `--ship`
    in place). Fixed directly: `main()` now rejects the combination as `EXIT_USAGE` before either the
    bare-noun-alias or verb-dispatch branches; test added.
  - `[low]` `[patch]` `ShipCredentialMissingError`'s message unconditionally claimed "shipping to
    pypi" even when raised from a `pypi-test` rehearsal (`ship_pypi` raises it identically for both,
    per AD-26, before computing which one applies) -- misleading for a `pypi-test` invocation missing
    credentials. Fixed: genericized to "before shipping" (no repository name); test added asserting
    the substring "to pypi" never appears.
  - `[low]` `[patch]` no dry-run test proved the `build()`-skip boundary against `pypi-test`
    specifically (only `pypi`/`channel:<name>` mixes were covered). Test added.
  - `[low]` `[patch]` no real-ship test exercised `--to conda-forge,pypi-test` (no plain `pypi`
    sibling) to confirm the rehearsal-gate pre-run correctly never triggers without a `PYPI` target
    present. Test added.
  - `[low]` `[patch]` (grouped with the above, same fix) both new tests bundled into one triage entry
    for brevity; see `## Tasks & Acceptance` for the itemized checklist.
- **Deferred** (tracked station `pyforge-mason`; full entry in `deferred-work.md`):
  - `[low]` `[defer]` **`DW-3-9-1`** -- the FR-24/FR-50 rehearsal gate validates a `pypi-test`
    artifact that is not provably the SAME bytes later uploaded to `pypi`: `ship_pypi` calls `build()`
    independently for the rehearsal and the real upload (spec-3-4's own already-accepted "minor
    redundancy," reaffirmed by this story's own Always boundary and pass-1's KEEP instructions). For
    a project with a fully reproducible build (Mason's own `hatchling`/static-version self-hosting
    case, SM-1) the two builds are byte-identical and this is moot; for a project with a
    non-reproducible build (VCS-derived dynamic versioning, embedded timestamps) the rehearsal could
    pass while validating an artifact that differs from the one shipped for real, undermining FR-50's
    stated purpose. Raised by Blind Hunter (pass 3). Not fixed here: properly closing this gap means
    sharing one `PackageBuildResult` between the rehearsal and real-ship calls, which reopens
    spec-3-4's own already-decided, twice-cited "`ship_pypi` owns its own `build()` call" design --
    a real redesign, not a patch, and out of THIS story's remit to revise a prior story's decision.
- **Rejected** (matches established/spec-directed precedent, or is speculative with no current
  defect):
  - `[low]` `[reject]` `--target`'s two registrations (`_add_ship_flags` on the `package` noun
    parser, `package build`'s own pre-existing verb-level registration) share the SAME dual-
    registration clobbering hazard pass 1 fixed elsewhere, dormant only because both currently share
    the single-value `choices=("library",)` constraint. Duplicate, third occurrence, of pass 2's
    already-rejected finding (Simplicity First: `choices=("library",)` is FR-21's own stated
    permanent v1 boundary, not a near-term change; no current defect to fix). Re-confirmed.

### 2026-08-14 — Review pass 4 (follow-up, post-`done`)
- intent_gap: 0
- bad_spec: 0
- patch: 3: (medium 1, low 2)
- defer: 0
- reject: 8: (low 8)
- addressed_findings:
  - `[medium]` `[patch]` `render_text`'s default `package ship` text output rendered a raw Python
    dict/list `repr()` dump (e.g. `[{'target': 'pypi', 'state': 'terminal', ...}]`, embedded
    newlines shown escaped) instead of human-readable text -- Story 3.9 is the first caller to put a
    `list` under a top-level `data` key, a shape `render_text`'s `f"{data[key]}"` line was never
    exercised against before (pass 2 fixed only the narrower nested-`ShipState`-repr leak, not this
    broader list-formatting gap). Reproduced directly. Fixed: `render_text` now formats a `list`
    value as one indented sub-line per item, each dict item's fields sorted onto their own line;
    test added asserting no `repr()`-shaped substring appears.
  - `[low]` `[patch]` `--yes`/`--recipe-path` (registered on the `package` noun parser for `ship`'s
    bare-noun alias, same as `--ship` itself) silently parsed and were discarded when combined with
    an explicit `build` verb (`mason package --yes --recipe-path X build .`) -- the exact sibling of
    pass 3's `--ship`+verb fix, left unaddressed then (pass 2 rejected it; pass 3 only revisited
    `--ship`+verb). Both fresh reviewers this pass (no shared context) independently rediscovered it.
    Reproduced directly (build silently proceeded, flags had zero effect). Fixed: extended the same
    usage-error guard pass 3 added, rejecting `--yes`/`--recipe-path` ahead of `build` as
    `EXIT_USAGE`; `--target` deliberately excluded (harmless, already-rejected precedent -- `build`
    has its own `--target` registration). Test added.
  - `[low]` `[patch]` no test exercised `parse_ship_targets("")` (the real, unmocked parser) reaching
    `InvalidShipTargetError` for the literal empty-string case `mason package --ship ""` sends --
    the existing regression test for this CLI path mocks `package.ship` and only proves routing, and
    the parser's own parametrized empty-token coverage tested `","`/`"pypi,"`/`" "`/etc. but never
    the bare `""` itself. Verified the real parser already handles it correctly (`InvalidShipTargetError`,
    `"<empty>"`) -- coverage-only gap. Added `""` to the existing parametrize list.
- **Rejected** (matches established/spec-directed precedent from a prior pass, is a duplicate of an
  already-recorded deferral, or the claimed consequence does not reproduce):
  - `[low]` `[reject]` TestPyPI/real-PyPI share one credential pair via `ship_pypi`'s environ check.
    Duplicate of pass 1's rejected finding, re-confirmed pass 2 (explicitly spec-directed, AD-26).
  - `[low]` `[reject]` the rehearsal and real upload each call `build()` independently, so a
    non-reproducible build's rehearsal doesn't provably validate the same bytes shipped for real.
    Identical to already-deferred `DW-3-9-1` (pass 3) -- not a new finding, no new ledger entry.
  - `[low]` `[reject]` the JSON/text envelope's `status` stays `"ok"` even when the exit code is
    `EXIT_FAILED`. Duplicate of pass 1's rejected finding, re-confirmed pass 2 (explicitly
    spec-directed, AD-4's codebase-wide convention).
  - `[low]` `[reject]` `_dispatch_package_ship`'s aggregate exit-code check uses `==` against
    `ShipState.FAILED` where `ship()`'s own new code elsewhere in this diff uses `is`/`is not` for
    the same closed `StrEnum`. Real stylistic inconsistency, zero behavioral difference (`StrEnum`
    member equality and identity agree for members of the same enum) -- cosmetic only.
  - `[low]` `[reject]` the genericized `ShipCredentialMissingError` message ("...before shipping")
    no longer names which of TestPyPI/real-PyPI the missing credential applies to. Re-litigates pass
    3's own deliberate, reasoned tradeoff (factually-correct-but-generic over specific-but-sometimes-
    wrong) -- not a new defect; the per-target `ShipTargetResult.target` field already disambiguates
    downstream.
  - `[low]` `[reject]` credential presence is checked twice (once per leg) for a combined
    `pypi-test,pypi` invocation against the same `environ`, so it cannot distinguish a credential
    valid for one service from the other. Symptom of the already-rejected shared-credential finding
    above, not a distinct defect.
  - `[low]` `[reject]` the extensive per-function docstring volume across this diff pushes against
    Simplicity First. Subjective style observation, not a functional defect, and matches this file's
    own established convention (unchanged by, and predating, this story).
  - `[low]` `[reject]` `ship()`'s dry-run branch calls `build()` unwrapped by a local `try`/`except
    MasonError` (unlike the real-ship path's per-target `_ship_one` isolation), so a missing build
    engine during a mixed-target dry run (e.g. `--to pypi,conda-forge`, no `--yes`) was claimed to
    abort "with no output at all." Reproduced directly: it does NOT crash or produce no output --
    the `MasonError` propagates cleanly to `main()`'s pre-existing, already-tested generic
    `except MasonError` handler (`cli.py`, unchanged since Story 1.3), which prints a clean one-line
    diagnostic and returns `EXIT_FAILED` -- the same established pattern every other structural
    precondition failure in this file already uses. Claimed consequence did not reproduce; false
    premise.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: `done` (review pass 4, a follow-up review triggered after the story had already reached
`done`; converged after two bad_spec loopbacks in passes 1-2, with passes 3 and 4 both patch-only,
no further loopback).

**Implemented change:** `mason package ship --to <targets>` (canonical) and `mason package --ship
<targets>` (the D-12 bare-noun alias) now exist and dispatch through a new `package.py::ship()`
multi-target orchestrator. `ship()` parses the closed four-form vocabulary (`pypi`, the new
`pypi-test` TestPyPI rehearsal target, `conda-forge`, `channel:<name>`), either plans (dry-run,
default) or dispatches each target to its own `ship_pypi`/`ship_channel`/`ship_conda_forge`
function, catches `MasonError` per target so one failure never blocks another (AD-9/FR-18), and
implements the FR-24/FR-50/AD-26 rehearsal gate: a `pypi-test` target requested alongside `pypi`
always runs first regardless of input order, and `pypi` only ships for real if that rehearsal
reached `terminal`. `pypi-test` reuses `ship_pypi` verbatim (`engines.twine.upload` gained a
`repository_url` knob) rather than a separate implementation, per AD-26.

**Files changed:** `models.py` (`ShipTargetKind.PYPI_TEST`), `errors.py` (`InvalidShipTargetError`'s
valid-forms list; `ShipCredentialMissingError`'s message genericized), `engines/twine.py`
(`repository_url` param), `package.py` (`parse_ship_targets`/`plan_ship` extended;
`_canonical_target_name` extracted; `ship_pypi` extended; new `ship()` dispatcher), `cli.py`
(`_add_ship_flags` helper; `ship` verb + `--ship` alias registration; `_dispatch_package_ship`
helper; the one documented bare-noun exception plus a new `--ship`+explicit-verb usage-error guard,
plus pass 4's sibling `--yes`/`--recipe-path`+`build` usage-error guard), `render.py` (pass 4:
`render_text` list-of-dict formatting), plus matching test coverage across all five
`tests/unit/*.py` files.

**Review process:** four adversarial passes (Blind Hunter + Edge Case Hunter, run independently
without shared context, per pass), with two bad_spec loopbacks through `step-03-implement.md` and
two direct patch-only passes:
- **Pass 1** found a HIGH-severity, live-reproduced bug: `--target`/`--yes`/`--recipe-path`, needed
  on both the `ship` verb parser and the `package` noun parser for the bare-noun alias, used plain
  (non-`SUPPRESS`) defaults -- so a value set on one parser was silently clobbered by the other's
  default when the flag was given on the "wrong" side of the verb token (`mason package --yes ship
  --to pypi` parsed to `confirm=False`). Traced to this spec's own incorrect Always-boundary claim
  that no `argparse.SUPPRESS` treatment was needed. Fixed via the same `SUPPRESS`+`getattr` pattern
  already established for the six AD-13 global flags. Bundled in the same loopback: an `--ship ""`
  dispatch inconsistency, a `repository_url` truthy-vs-`is not None` idiom mismatch, one missing
  `# pragma: no cover`, one missing test.
- **Pass 2** found two more HIGH-severity bugs in the pass-1-corrected diff: (a) `--format text` (the
  default) leaked a raw `<ShipState.X: 'x'>` repr for every `package ship` result, since
  `render_text` was never exercised against a nested list before this story; (b) a dry-run `--to
  conda-forge` unconditionally called `build()`, crashing with `EngineAbsentError` on a host missing
  wheel-build tooling, inconsistent with the real-ship path's own already-stated "don't force build
  engines for a conda-forge-only ship" principle. Both traced to incomplete carry-through of already-
  correct intent into `## Code Map`/`## Tasks & Acceptance`. Fixed via a second loopback.
- **Pass 3** re-verified all three prior fixes as complete and correct (both reviewers explicitly
  confirmed no remaining clobbering path and no regression), then found only low-severity findings:
  applied directly without a further loopback -- a new `EXIT_USAGE` guard for `--ship` combined with
  an explicit verb (persistent across all three passes; upgraded from reject to patch given six
  independent reviewer confirmations and a plausible real trigger), a genericized
  `ShipCredentialMissingError` message (previously falsely claimed "pypi" for a `pypi-test`
  rehearsal), and two small test-coverage additions. One finding -- the rehearsal gate not
  guaranteeing byte-identical rehearsal/real artifacts for non-reproducible builds -- was deferred
  (`DW-3-9-1`) as a real but out-of-scope architectural question, reopening an already-decided
  Story 3.4 design choice.
- **Pass 4** (follow-up, triggered by re-invoking dev-auto after the story had reached `done`; fresh
  Blind Hunter + Edge Case Hunter, no sight of any prior pass) found no bad_spec and no intent gaps:
  one new, real, medium-severity finding (`render_text`'s list-of-dict formatting had never been
  exercised for readability, only for the narrower enum-repr leak pass 2 fixed) and one real,
  low-severity finding rediscovered independently by both reviewers -- the exact sibling of pass 3's
  `--ship`+verb fix, left unaddressed for `--yes`/`--recipe-path`+`build` specifically (pass 2
  rejected it before pass 3's precedent-setting upgrade existed to apply to it too). A third,
  low-severity finding was a genuine test-coverage gap with no code defect. Six other findings
  restated already-rejected precedent from passes 1-3 (or an already-recorded deferral) and were
  re-rejected; one (the dry-run `build()`-not-locally-wrapped claim) reproduced as factually
  incorrect -- the pre-existing generic `MasonError` handler already reports it cleanly, matching
  every other structural-precondition failure in this file. All three real findings fixed directly,
  no loopback needed.

**Findings breakdown (cumulative across 4 passes):** 4 bad_spec (both loopbacks fully converged and
re-verified clean by fresh reviewers), 11 patch (1 high-severity-adjacent folded into pass-1's
bad_spec bundle, 10 low/medium, all applied), 1 defer (`DW-3-9-1`, low), 23 reject (all low, matching
established precedent, an explicitly spec-directed decision, an already-recorded deferral, or a
claimed consequence that did not reproduce -- see each pass's Review Triage Log entry for the
itemized list). No intent gaps at any pass -- every finding had exactly one correct, unambiguous
resolution.

**Verification:** `pixi run -e pyforge-mason pyforge-mason-test` -- **1276 passed, 1 deselected**
(1205 before this story; +71 new tests across all four passes, 0 failures). Every fix in every pass
was independently live-verified against the actual parser/dispatcher/renderer (not just trusted from
the test suite) before being accepted as complete.

**Residual risks:**
- `DW-3-9-1` (deferred, low-medium): the TestPyPI rehearsal and the real PyPI upload each build
  independently; for a project with a non-reproducible build (dynamic VCS-derived versioning,
  embedded timestamps), the rehearsal does not guarantee it validated the exact artifact later
  shipped for real. Moot for Mason's own self-hosting case (static `hatchling` versioning).
- Story 3.8 ("Mason ships Mason") has not yet run this mechanism against a real release -- this
  story builds the capability FR-24 describes; exercising it for real remains that story's job.
- `DW-3-4-1`/`DW-3-5-1`/`DW-3-5-2`/`DW-3-6-1`/`DW-3-6-2`/`DW-3-6-3` (pre-existing, from prior
  stories) all remain open and untouched by this story.
