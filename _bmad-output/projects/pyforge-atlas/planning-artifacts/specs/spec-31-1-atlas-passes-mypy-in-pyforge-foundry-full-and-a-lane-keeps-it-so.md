---
title: "31.1: Atlas passes mypy in `pyforge-foundry-full`, and a lane keeps it so"
type: 'fix'
created: '2026-10-14'
status: 'done'
baseline_revision: '22e5c19c285e722bcf7d58203689d57e9cc4dd55'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
  - src/shared/packages/pyforge-atlas/pyproject.toml
  - scripts/lint_types.py
  - .github/workflows/lint-types.yml
  - .claude/skills/pyforge-steward/SKILL.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Atlas fails mypy in `pyforge-foundry-full`, the one environment that installs its real runtime libraries.
No lane runs mypy there, so CI stays green while `sbom-laptop-gate` is red on `main`. This story closes
`DW-atlas-steward-100-7-1`. Line numbers below are at `846d8383f5`.

- **Where it fails.** `sbom-laptop-gate` (steward Story 67.2, `fnd:CAP-13`) runs `lint-types` inside
  `pyforge-foundry-full`. That environment installs Vizro 0.1.60 and Dash 4.4.1, Dagster 1.13.24, Kedro 1.6.0,
  openlineage-python 1.53.0, Bokeh 3.10.0, BeautifulSoup 4.15.0 and DuckDB 1.5.5. mypy checks Atlas against their real
  types there.
- **Why CI is green.** `pyforge-guild`, where `.github/workflows/lint-types.yml` and `pr-preflight` run mypy, installs
  none of those libraries. Atlas's `[tool.mypy]` sets `ignore_missing_imports = true`, so mypy reads each of them as
  `Any`. No workflow runs `sbom-laptop-gate` or any mypy in `pyforge-foundry-full`.
- **Measured.** In a fresh worktree at `846d8383f5`, `pixi run --frozen -e pyforge-foundry-full lint-types` exits 1 at
  its mypy leg. `pyforge-atlas` reports `Found 72 errors in 8 files (checked 130 source files)`. The other nine
  `pyforge-*` packages pass, and so do `ruff` and `ruff-format`. The same mypy (2.4.0, the lock's) over `pyforge-guild`
  reports `Success: no issues found in 130 source files`. The primary checkout's `pyforge-foundry-full` env, behind the
  lock on mypy alone (2.3.1), reports the same 72.

**The 72 errors, by file and code:**

| Module (under `src/pyforge/atlas/`) | Errors | Codes |
|---|---|---|
| `dashboard/app.py` | 59 | 54 `call-arg`, 4 `arg-type`, 1 `operator` |
| `views/widgets.py` | 4 | `attr-defined` |
| `datasets/upstream_discovery.py` | 2 | `union-attr`, `call-overload` |
| `orchestration/definitions.py` | 2 | `arg-type` |
| `query_plane_vectors.py` | 2 | `arg-type` |
| `mcp/session.py` | 1 | `misc` |
| `observability.py` | 1 | `arg-type` |
| `rag/store.py` | 1 | `index` |

The DW row's per-file counts summed to 79 and named FastHTML. The counts above are measured; the `Nav` is Dash's
`html.Nav`.

**The 54 `call-arg` errors cannot be typed at the call site.** Each reads "Missing named argument" for a Vizro model:
`Page` (`layout`, `description`, `path`) at :520, :576, :595, :654, :686, :722; `Card` (`href`, `description`, `extra`)
at :434, :645, :658, :684, :708; `AgGrid` (`footer`, `description`) at :515, :588, :660, :685, :727; `Graph` at :442;
`Action` (`inputs`, `notifications`) at :553; `UserInput` at :581; `Button` at :586; `Text` at :587;
`LandmarkDashboard` (`navigation`, `description`) at :1041. Vizro declares those defaults inside
`Annotated[..., Field(default=...)]`, and mypy reads each such field as required.
- The pydantic mypy plugin, tried in a throwaway config, clears 10 of the 54 (`Card.href` and `AgGrid.footer`, declared
  `= Field(...)`) and the `arg-type` at :524. 44 remain, so the plugin does not remove the need for an override.
- Passing the defaults explicitly would change behaviour. Vizro reads `model_fields_set`: an explicit `Action.inputs`
  puts an action on its deprecated legacy path (`vizro/models/_action/_action.py`, `_legacy`), and `Page`'s path
  validator reads whether `id` was set.

**One error is a real defect.** `observability.py:272` passes the `outputStatistics` facet to `OutputDataset(...,
facets=...)`. `OutputStatisticsOutputDatasetFacet` is an `OutputDatasetFacet`, not a `DatasetFacet`. openlineage-python
1.53.0's `OutputDataset` takes it under `outputFacets`, so a strict consumer never finds the row count where the
OpenLineage spec puts it. `tests/unit/observability/test_observability_fixtures.py` pins the wrong key at :120, :229,
:241 and :295.

**The other 17 errors take typed fixes.** Each was proven on a scratch copy; nothing was committed.
- `dashboard/app.py:524` (`arg-type`): `controls` is `list[vm.Filter]` where `vm.Page` takes
  `list[ControlType | ControlGroup]` (an invariant list). Type the value as the element type `vm.Page` declares.
- `dashboard/app.py:550` (`operator`): `model_manager[grid_id]` is a `VizroBaseModel`. Narrow it to `vm.AgGrid` with
  an `isinstance` check that raises `TypeError` otherwise, then call it.
- `dashboard/app.py:761` (3 `arg-type`): `html.Nav(..., **{"aria-label": ...})` spreads a `dict[str, str]` over Dash's
  typed keywords. Spread a `dict[str, Any]`: Dash's `aria-*` wildcard props are untyped by design.
- `views/widgets.py:41` (4 `attr-defined`): `bokeh.models` re-exports its widgets dynamically. Import `Select` and
  `TextInput` from `bokeh.models.widgets.inputs`, and `DataTable` and `TableColumn` from `bokeh.models.widgets.tables`.
  That fix exposes one more error, at :158: `Select(options=...)` gets a `list[tuple[str, str]]` where Bokeh takes
  `list[str | tuple[Any, str]]`. Type the list as Bokeh's element type.
- `datasets/upstream_discovery.py:145` (`union-attr`): `link.get("href")` is `str | AttributeValueList`. Use it only
  when it is a `str`. `:152` (`call-overload`): `article.find(attrs={...})` matches no overload. Call
  `article.find(None, {...})`.
- `orchestration/definitions.py:529` (`arg-type`): `rekeyed` is annotated `dict[dg.NodeInvocation, object]`. Keep the
  value type `graph.dependencies` already carries (Dagster's `IDependencyDefinition` mapping). `:860` (`arg-type`):
  `build_wiki_compile_sensor(job: dg.JobDefinition)` (:687-:689) is passed the `UnresolvedAssetJobDefinition`
  `dg.define_asset_job` returns. Widen the parameter to both. Dagster exports neither type at top level; a typing-only
  import under `TYPE_CHECKING` was proven, and a comprehension that lets mypy infer the mapping's type works for :529.
- `query_plane_vectors.py:40, :83` (`arg-type`): `LockedDuckDB` is passed where `rag/store.py` declares
  `duckdb.DuckDBPyConnection`. `LockedDuckDB` (`duckdb_writer.py:70`) proxies every connection attribute through
  `__getattr__`. Widen `load_vss_offline`'s `con`, the `VssLoader` alias and `DuckdbVssRagStore`'s `connection` to also
  accept `LockedDuckDB`, imported under `TYPE_CHECKING`. `query_plane_vectors.py` itself does not change.
- `mcp/session.py:57` (`misc`): Kedro's `AbstractSession.__enter__` returns `AbstractSession`, not `Self`, so `with
  KedroSession.create(...) as session` yields the base type. Bind `session = KedroSession.create(...)`, then
  `with session: yield session`. Keeping the `with` keeps `KedroSession.__exit__`, which logs the exception before it
  closes the session.
- `rag/store.py:241` (`index`): `fetchone()` is `tuple[Any, ...] | None`. Raise if it is `None`, then index it.

**Proven on a scratch copy.** With those typed fixes and the one override below, mypy reports `Success: no issues found
in 130 source files` against both `pyforge-foundry-full`'s and `pyforge-guild`'s interpreters. The atlas unit and meta
suites, and the dashboard integration tests, fail exactly the same environment-bound tests on the fixed copy and on an
untouched copy, and no others, once the four observability assertions read `outputFacets`. With main's
`observability.py` and the corrected assertions, 2 tests fail. `ruff check` flags one import-order fix (`I001`), and
`ruff format --check` passes.

**Coverage, measured.** Atlas's touched-module floor is 80% unit (`docs/governance/coverage-thresholds.toml`; the gate
is `named-module-gates (atlas)` in `coverage-gates.yml`, and `pyforge-atlas-coverage-gate` is its local twin). Unit and
meta coverage at `846d8383f5`, with no `vss` extension provisioned (the case on the gate's runner and on this host):

| Module | Unit coverage | Touched by this story |
|---|---|---|
| `dashboard/app.py` | 89.8% | yes |
| `datasets/upstream_discovery.py` | 94.3% | yes |
| `observability.py` | 92.7% | yes |
| `orchestration/definitions.py` | 91.5% | yes |
| `views/widgets.py` | 100.0% | yes |
| `mcp/session.py` | 75.0% (`bootstrapped_session`'s body, :50-:57, never runs) | yes |
| `rag/store.py` | 35.1% (`tests/unit/rag/test_vss_similarity_search.py` skips without `vss`) | yes |
| `query_plane_vectors.py` | 30.9% | no: its two errors are fixed in `rag/store.py`'s signatures |

Two scratch tests lifted the two sub-floor modules. One drove `DuckdbVssRagStore` over a real in-memory DuckDB, through
a connection wrapper that drops only the statements the `vss` extension owns. The other ran `bootstrapped_session` with
Kedro's two entry points replaced. `rag/store.py` reached 96.5% and `mcp/session.py` 100%.

**The lane.** `.github/workflows/lint-types.yml` has one job, `lint-types`. It installs `pyforge-guild` and runs `pixi
run --frozen -e pyforge-guild lint-types`. `pr-preflight` builds its lanes from `pixi.toml`'s `pr-preflight-lanes`
`depends-on`, keyed by task and environment, and has no `pyforge-foundry-full` lane.
- The existing `mypy` task (`python scripts/lint_types.py mypy`) runs unchanged in `pyforge-foundry-full`, because that
  environment composes `guild-tasks`. The lock pins mypy 2.4.0 there, as in `pyforge-guild`.
- Over all ten packages, measured with that interpreter, it took 58 s with a cold cache and 2.4 s warm.
- A guild run and a foundry-full run sharing one cache directory, started concurrently three times, each gave its own
  correct verdict (0 and 72). The two lanes can share each package's `.mypy_cache`.

**Approach:**
1. Fix the 17 errors at their call sites and annotations, and the one the Bokeh import fix exposes.
2. Emit `outputStatistics` under `outputFacets`, and move the four assertions to it.
3. Add one `[[tool.mypy.overrides]]` entry, `call-arg` on `pyforge.atlas.dashboard.app`, with a comment naming the
   cause.
4. Lift `mcp/session.py` and `rag/store.py` over the unit floor with two vss-free unit test modules.
5. Run the existing `mypy` task in `pyforge-foundry-full` as a second step of the `lint-types` CI job, and as a
   `pr-preflight` lane. An atlas meta test pins both, so neither can be dropped silently.

Ledger key: `31-1-atlas-passes-mypy-in-pyforge-foundry-full-and-a-lane-keeps-it-so`.
Type / Effort / Deps: fix / M / none.

### Living CAP citations

- **`spec-pyforge-atlas` CAP-20** (a developer runs one command that executes every check CI executes, type checking
  included; a parity check fails on divergence) and **AD-32** (every gate is a named task, and CI invokes tasks; it
  prevents local and CI drifting apart). Here the laptop's type check and CI's diverge. This story makes them agree, and
  the CI step invokes the existing `mypy` task, never an inline command. A `fix`, so no CAP is minted and `SPEC.md`
  does not change.
- **`spec-pyforge-steward:CAP-153`** (lint and types gate the ten `pyforge-*` packages, locally and on the runners
  alike) owns the lane, and **`spec-pyforge-steward:CAP-159`** owns the lane list in `pixi.toml`. **`fnd:CAP-13`** (the
  SBOM is checkable) owns `sbom-laptop-gate`. All three are cited; none of their text changes.
- **AD-11** (gates are never weakened): the override is one module and one code, and no test or assertion is loosened.
- **No flag.** `spec-feature-flag-governance` Q1: a `fix` needs no flag.
- **Origin.** `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-14 (foundry-full mypy) entry;
  `DW-atlas-steward-100-7-1` (recorded by steward Story 100.7); the operator's approval, 2026-10-14: "chain the three
  DWs".

## Acceptance Criteria

- **AC1 — Clean against the real libraries.** **Given** this branch, **When** `pixi run --frozen -e
  pyforge-foundry-full mypy` runs, **Then** it exits 0, and its `pyforge-atlas` line reads `ok` after `Success: no
  issues found in <N> source files` (N ≥ 130).
- **AC2 — Still clean in the Guild env.** `pixi run --frozen -e pyforge-guild lint-types` exits 0. In particular it
  reports no `unused-ignore` in `pyforge-atlas`.
- **AC3 — Typed, not silenced.** Each of the 17 errors the Intent lists under *The other 17 errors take typed fixes*,
  and the `views/widgets.py:158` error the Bokeh import fix exposes, is fixed by a typed call site, annotation or
  narrowing. (Of the 72, 54 are Vizro's `call-arg` (AC4), one is the OpenLineage defect (AC5), and these are the 17.)
  - `git diff origin/main...HEAD -- src/shared/packages/pyforge-atlas/src` adds no `# type: ignore`, no `cast(`, and no
    `ignore_errors`.
  - The diff adds `Any` only for Dash's `aria-*` wildcard props.
  - No existing `[[tool.mypy.overrides]]` entry gains a code.
- **AC4 — One override, and only Vizro's defaults behind it.** `src/shared/packages/pyforge-atlas/pyproject.toml` gains
  exactly one `[[tool.mypy.overrides]]` entry: `module = "pyforge.atlas.dashboard.app"`, `disable_error_code =
  ["call-arg"]`. A comment beside it names the cause: Vizro's `Annotated[..., Field(default=...)]` defaults, the
  plugin's 10 of 54, and `model_fields_set`.
  - The pydantic mypy plugin is not added.
  - With the entry removed on a scratch copy, every error `pixi run --frozen -e pyforge-foundry-full mypy` reports for
    `pyforge-atlas` is a `call-arg` in `dashboard/app.py` reading `Missing named argument "<field>" for "<Vizro model>"`.
    None reads `Unexpected keyword argument`, and none is in another module.
- **AC5 — The row count rides `outputFacets`.**
  - `observability.py` passes the `outputStatistics` facet to `OutputDataset` as `outputFacets`, typed
    `dict[str, OutputDatasetFacet]`.
  - The four assertions at `test_observability_fixtures.py` :120, :229, :241 and :295 read `outputFacets`, and the :120
    test also asserts `"outputStatistics" not in out.facets`.
  - No other line of that file changes.
  - Moving the facet back to `facets=` reds the two positive assertions (mutation).
- **AC6 — Behaviour unchanged elsewhere.**
  - No existing test function, body or assertion changes outside AC5.
  - The diff adds no `skip`, `xfail`, rerun or `flaky` marker.
  - `query_plane_vectors.py`, `duckdb_writer.py` and every module outside the seven named in the Intent keep every line.
- **AC7 — Touched modules meet the coverage floor.** `pixi run --frozen -e pyforge-atlas pyforge-atlas-coverage-gate`
  exits 0: every atlas module this branch touches is at 80% unit or above.
  - `rag/store.py` gets a vss-free unit test module. It drives `DuckdbVssRagStore` over a real in-memory DuckDB and drops
    only the three statements `vss` owns: `SET hnsw_enable_experimental_persistence`, `CREATE INDEX ... USING HNSW` and
    `DROP INDEX`. Ranking still runs in DuckDB (`array_distance` is core).
  - `mcp/session.py` gets a unit test proving `bootstrapped_session` yields the session `KedroSession.create` returned,
    passes `runtime_params` and `env` through, and exits it.
  - `docs/governance/coverage-thresholds.toml` does not change.
- **AC8 — CI runs the leg.** In `.github/workflows/lint-types.yml`, the `lint-types` job's `setup-pixi` installs
  `pyforge-guild pyforge-foundry-full`. After the existing step, it runs `pixi run --frozen -e pyforge-foundry-full
  mypy`.
  - There is still one job and one `setup-pixi` pin site, so `pixi-version-check` and `ci-surface-gates-check` stay
    green with no change to `scripts/pixi_version_registry.py` or `docs/governance/ci-surfaces.yaml`.
  - The header comment says the job runs the `mypy` task twice, once per environment, and why.
- **AC9 — `pr-preflight` runs the same leg.** `pixi.toml`'s `pr-preflight-lanes` `depends-on` gains `{ task = "mypy",
  environment = "pyforge-foundry-full" }`, and its description names the leg.
  - A `pr-preflight` run on this branch runs that lane and records it in `.steward/preflight-runs.jsonl`.
  - If the description edit makes `docs/how-to/pixi-tasks.md` stale, it is regenerated with `docs-pixi-tasks`.
  - `environment.yaml` is regenerated with `pixi run -e pyforge-steward pyforge steward estate reconcile`, which is
    expected to write no diff.
- **AC10 — Pinned.** A new atlas meta test, `tests/meta/test_foundry_full_mypy_lane.py`, reads `lint-types.yml` and
  `pixi.toml` from the repo root. It asserts both AC8's step and AC9's `depends-on` entry, and it fails when either is
  removed (mutation). It reads files only: no `pixi`, no network, no import of another station.
- **AC11 — The lane catches what Guild cannot (mutation).** On a scratch revert of the `views/widgets.py` import fix,
  `pixi run --frozen -e pyforge-foundry-full mypy` exits 1 naming `views/widgets.py`, while `pixi run --frozen -e
  pyforge-guild mypy` still exits 0. The revert is undone before the next commit.
- **AC12 — The laptop gate's leg is green.** `pixi run --frozen -e pyforge-foundry-full lint-types` exits 0.
- **AC13 — Suites.** `pixi run -e pyforge-atlas kedro-test`, `pixi run -e pyforge-atlas kedro-catalog-check` and
  `pixi run --frozen -e pyforge-atlas pyforge-atlas-test` exit 0. Because `pixi.toml` changes, `pixi run --frozen -e
  pyforge-guild pyforge-station-tests` exits 0 too.
- **AC14 — Reconciled and closed.**
  - Every Spec `spec-surface-check` names gets a memlog surface-reconcile entry naming its paths and this story, and is
    stamped scoped, one `--spec` each. `spec-surface-check` then exits 0.
  - `chain-currency-sweep-check` exits 0, after any PRD or spine re-stamp the co-governor memlogs trigger.
  - At landing, `DW-atlas-steward-100-7-1` reads `status: closed` with a `verified:` line citing the merge and AC1's
    command and exit code.

## Boundaries & Constraints

**Always:**
- Type the call site first. An override only where mypy cannot type the call, per module and per error code (the
  2026-09-20 baseline rule).
- Keep every lane a named task (AD-32). The CI step invokes `mypy` by name, with no inline `mypy` command.
- Read `.claude/skills/pyforge-steward/SKILL.md` before editing `lint-types.yml` or `pixi.toml`'s lane list. Run every
  lane those files fire, locally, before the push.

**Never:**
- Never `ignore_errors`, a module-wide `disable_error_code` beyond AC4's one entry, an inline `# type: ignore` or a
  `cast` to silence an error. `warn_unused_ignores` makes an inline ignore that `pyforge-foundry-full` needs an error in
  `pyforge-guild`.
- Never pass Vizro's defaults explicitly to clear `call-arg`; that changes `model_fields_set`.
- Never add the pydantic mypy plugin, a dependency, a new pixi environment or a new script. Never `pixi add` or `pixi
  update`. The lane is the existing `mypy` task in an existing environment.
- Never change `scripts/lint_types.py`, `scripts/sbom_laptop_gate.py`, `docs/governance/coverage-thresholds.toml`,
  `docs/governance/ci-surfaces.yaml` or another station's code.
- Never lower a coverage floor, or skip or delete a `vss` test, to make AC7 pass.
- Never weaken a test (AD-11). AC5's four assertions move to the correct key and gain one; nothing else in a test
  changes.

**Co-governor memlogs the implementer appends** (read from `scripts/.spec-surface-baseline.json` at `846d8383f5`; the
detector's list at implementation time is authoritative):
- The seven atlas `src/` modules: `pyforge-atlas/spec-pyforge-atlas`, `pyforge-marshal/spec-pyforge-core` and
  `pyforge-steward/spec-pyforge-unifying-strategy`.
- The atlas tests and the new test modules: `spec-pyforge-atlas` and `spec-pyforge-unifying-strategy`, or whichever the
  detector names for a new file.
- `src/shared/packages/pyforge-atlas/pyproject.toml`: `spec-pyforge-unifying-strategy`.
- `.github/workflows/lint-types.yml`: `pyforge-steward/spec-pyforge-steward`.
- `pixi.toml`: `pyforge-doctor/spec-pixi-candidate-currency`, `pyforge-herald/spec-deck-family-currency`,
  `pyforge-herald/spec-deck-family-lockstep`, `pyforge-herald/spec-pyforge-pages`, `pyforge-marshal/spec-pyforge-core`,
  `pyforge-marshal/spec-pyforge-marshal` and `pyforge-steward/spec-pyforge-unifying-strategy`.
- `docs/how-to/pixi-tasks.md`, if regenerated: `pyforge-doctor/spec-pyforge-doctor`.
- `environment.yaml`, only if reconcile writes a diff: `spec-pyforge-marshal` and `spec-pyforge-unifying-strategy`.
- The atlas `deferred-work-ledger.md`, when the DW row closes: `spec-pyforge-atlas`.

Each of those memlog appends can trip `chain-currency-sweep-check`'s two-day gate on its station's PRD and spine.
Re-stamp them with a dated Currency reconciliation note, as
`_bmad-output/projects/pyforge-doctor/CHAIN-CURRENCY-RUNBOOK.md` requires.

**Residual risk:**
- The CI job's runtime grows by the `pyforge-foundry-full` install (3.6 GB on disk locally). If it nears the job's
  `timeout-minutes: 20`, raise the timeout from the measured run time and record it in the Spec Change Log.
- The override hides future `call-arg` errors in `dashboard/app.py`, including a mistyped keyword. Vizro's models
  forbid extra fields at runtime, and the dashboard build tests construct every page, so a mistyped keyword still fails
  a test.
- A later Vizro release that moves its defaults out of `Annotated` makes the override unused. That is harmless:
  `warn_unused_configs` covers module sections that match no module, not codes that never fire.

## I/O & Edge-Case Matrix

| Situation | Today (`846d8383f5`) | After |
|---|---|---|
| `pixi run --frozen -e pyforge-foundry-full mypy` | exit 1, atlas 72 errors in 8 files | exit 0, all ten packages `ok` |
| `pixi run --frozen -e pyforge-guild lint-types` | exit 0 | exit 0 |
| A PR adds an error only real library types reveal | CI green, `sbom-laptop-gate` red later | the `lint-types` job and `pr-preflight` red |
| `sbom-laptop-gate`'s `lint-types` leg | exit 1 | exit 0 |
| A node with a sized output emits lineage | `outputStatistics` under `facets` | under `outputFacets` |
| A scalar or unsized output | no `outputStatistics` facet | unchanged |
| `rag/store.py` unit coverage without `vss` | 35.1% | ≥ 80% (scratch: 96.5%) |
| `mcp/session.py` unit coverage | 75.0% | ≥ 80% (scratch: 100%) |
| Guild and foundry-full mypy lanes running concurrently | (no foundry-full lane) | each correct on a shared cache (measured 3/3) |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-20 (AD-32), a `fix`, so no CAP is minted and no `SPEC.md` text
  changes. Co-cited: `spec-pyforge-steward:CAP-153` (the lint/types gate), `spec-pyforge-steward:CAP-159` (the
  `pr-preflight` lane list) and `fnd:CAP-13` (the laptop gate).
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-14 (foundry-full mypy) entry.
- Deferred work closed: `DW-atlas-steward-100-7-1` (`deferred-work-ledger.md`), promoted to this story at mint.
- Epic: Epic 31 (new). No open atlas epic owns the type gate, and Epics 25 to 29 are all `done`, and Epic 31 is the Pages redesign (CAP-62, CAP-63). `epic-31` and
  `epic-31-retrospective` are minted with it.
- Ledger key: `31-1-atlas-passes-mypy-in-pyforge-foundry-full-and-a-lane-keeps-it-so`.
- Ledger status at mint: `backlog`.
- Deps: none.
- Surface: `marshal-policy.toml` `[epic_surfaces]."31"`, added with this mint.
- Minted 2026-10-14 in one planning-only chain commit; implementation is dispatched through `marshal factory dispatch`.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- AC1: `pixi run --frozen -e pyforge-foundry-full mypy` — expected: exit 0; `[lint-types] mypy pyforge-atlas ok`.
- AC2 and AC12: `pixi run --frozen -e pyforge-guild lint-types` and `pixi run --frozen -e pyforge-foundry-full lint-types` — expected: exit 0 each.
- AC3: `D="$(mktemp)"; git diff origin/main...HEAD -- src/shared/packages/pyforge-atlas/src > "$D"; grep -cE '^\+.*(type: ignore|cast\(|ignore_errors)' "$D"` — expected: `0`.
- AC4, on a scratch copy of `pyproject.toml` with the new entry removed: `pixi run --frozen -e pyforge-foundry-full mypy` — expected: exit 1, and every `pyforge-atlas` error line is `src/pyforge/atlas/dashboard/app.py:<n>: error: Missing named argument ... [call-arg]`. Restore the file afterwards.
- AC5: `pixi run --frozen -e pyforge-atlas python -m pytest src/shared/packages/pyforge-atlas/tests/unit/observability -q -p no:cacheprovider` — expected: pass. The mutation (`facets=` restored) — expected: 2 failed.
- AC7: `pixi run --frozen -e pyforge-atlas pyforge-atlas-coverage-gate` — expected: exit 0.
- AC10: `pixi run --frozen -e pyforge-atlas python -m pytest src/shared/packages/pyforge-atlas/tests/meta/test_foundry_full_mypy_lane.py -q -p no:cacheprovider` — expected: pass; with either pinned line removed on a scratch copy, expected: fail.
- AC11, the mutation, on a scratch revert of the Bokeh import fix: `pixi run --frozen -e pyforge-foundry-full mypy` — expected: exit 1 naming `views/widgets.py`; `pixi run --frozen -e pyforge-guild mypy` — expected: exit 0.
- AC13: `pixi run --frozen -e pyforge-atlas pyforge-atlas-test` and `pixi run --frozen -e pyforge-guild pyforge-station-tests` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild pixi-version-check` and `pixi run --frozen -e pyforge-guild ci-surface-gates-check` — expected: exit 0 (AC8).
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and scoped stamps (AC14).
- `pixi run --frozen -e pyforge-guild chain-currency-sweep-check` — expected: exit 0 (AC14).
- `pixi run --frozen -e pyforge-guild pr-preflight`, its exit code read from `$?` — expected: 0, with the `mypy` / `pyforge-foundry-full` lane in the run (AC9).

## Spec Change Log

- 2026-10-14: minted from `DW-atlas-steward-100-7-1` on the operator's approval, "chain the three DWs". `type: fix`, no
  flag, no CAP; bound to `spec-pyforge-atlas` CAP-20 (AD-32). The DW row's per-file counts (79 in total) and its
  "FastHTML" were corrected against a fresh measurement: 72 errors, and Dash's `html.Nav`. The typed fixes, the one
  override, the OpenLineage correction and both coverage tests were proven on a scratch copy; no code was committed.
- 2026-10-14: renumbered from 30.1 to 31.1 the same day, before landing. The Pages redesign chain (`6db9855387`) took
  Epic 30 with Stories 30.1 and 30.2 under CAP-62 and CAP-63; nothing else in this spec changed.

## Review Triage Log

### 2026-10-14 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings:
  - (implementer verification) All AC verification commands run green locally: foundry-full and guild mypy/lint-types, observability unit tests, new meta/unit tests, pyforge-atlas-coverage-gate, `python scripts/spec_surface_reconcile.py`.

## Auto Run Result

Status: done
Verification: `pixi run --frozen -e pyforge-foundry-full mypy` exit 0; `pixi run --frozen -e pyforge-guild lint-types` exit 0; `python scripts/spec_surface_reconcile.py` exit 0; `pixi run --frozen -e pyforge-atlas pyforge-atlas-coverage-gate` exit 0.
