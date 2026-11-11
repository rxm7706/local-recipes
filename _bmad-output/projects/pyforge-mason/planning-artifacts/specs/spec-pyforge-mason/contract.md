# Public contract — Mason

Companion to `SPEC.md` (CAP-5, amended 2026-11-10; FR-60; AD-9, AD-13; decision D1). It records everything Mason
serves to a caller: every parser path with its positionals and options, every environment variable Mason reads or
sets, the exit codes, the error identifiers, the MCP tool and portal-job names and the feature-flag keys Mason reads.
A second root that rebuilds Mason from its Spec rebuilds this surface.

The guard is `src/shared/packages/pyforge-mason/tests/meta/test_public_contract.py`. It derives the code side and
fails, naming the family and the item, when the code has an item this file lacks or this file names an item the code
lacks. A change that adds a parser path, option, positional, variable, exit code, error identifier, MCP or portal name
or flag key adds its row here in the same change. The code side, family by family:

- **Parser paths, options and positionals:** `pyforge.mason.cli.build_parser()`, walked through its subparsers.
  `-h`/`--help` is argparse's own on every path and is not listed.
- **Environment variables:** an AST scan of the package source (`src/pyforge/mason/**/*.py`): every module-level name
  whose identifier contains `ENV` bound to an `UPPER_SNAKE` string literal, every string member of a module-level
  tuple whose identifier contains `CREDENTIAL`, and every `UPPER_SNAKE` literal passed as the first argument of
  `.get(` on `environ` or `env`, or used as an `os.environ[...]` key.
- **Exit codes:** the module-level `EXIT_*` names of `exit_codes.py`, with their numbers.
- **Error identifiers:** the literal first argument of each `super().__init__` call in `errors.py`.
- **MCP tool and portal-job names:** the module-level `*_TOOL` constants of django-mason's `mcp_asgi.py` and
  `LAST_DIAGNOSE_TOOL` in django-pyforge's `assertion/client.py`, read as text with `ast`, never imported.
- **Feature-flag keys:** string literals passed to a `pyforge.core.flags` reader anywhere in the package source.

How the test reads this file: only the table rows under the eight `##` headings from *Parser paths* to *Feature-flag
keys*, and only each row's first cell as a backticked token (the second cell too, for an exit code's number). Every
other line is prose the test does not judge. Keep those headings exact.

## Parser paths

The program is `mason` (`[project.scripts] mason = "pyforge.mason.cli:main"`); the same tree is reached as
`pyforge mason` through pyforge-core's `pyforge` dispatcher. Run it from the repository root: CFE auto-discovery and
manifest discovery start at the current directory. A bare noun prints that noun's verbs and exits 2; the one
documented exception is `mason package --ship <targets>` (D-12), an option row of `mason package` below.

| Path | Positionals | What it does |
|---|---|---|
| `mason` | — | The root. `--version` prints `mason <version>`; a bare `mason` prints help and exits 0. |
| `mason recipe` | — | Noun: author, validate and build conda recipes by wrapping conda-forge-expert (CFE) by subprocess. |
| `mason recipe new` | — | Generates a v1 recipe from one upstream source at `--output` through CFE. |
| `mason recipe validate` | `recipe_path` | Runs CFE's validator; the validator's outcome is the exit code. |
| `mason recipe build` | `RECIPE_PATH` | Native build by default; `--docker` with `--config` runs the CI-parity build. A `factory/recipes/<r>` path builds on the factory island (see *Layout*). |
| `mason recipe diagnose` | `log_path` | Runs CFE's failure analyzer on a build log. |
| `mason recipe optimize` | `recipe_path` | Runs CFE's recipe optimizer lint. |
| `mason recipe scan` | `recipe_path` | Runs CFE's vulnerability scan over exactly pinned dependencies. |
| `mason recipe submit` | `recipe_path` | CFE's two-phase staged-recipes submission; a dry run unless `--yes`. |
| `mason recipe update` | `recipe_path` | CFE's autotick version bump (PyPI, or GitHub Releases with `--github`). |
| `mason package` | — | Noun: build and ship distributions; carries the bare-noun `--ship` alias. |
| `mason package build` | `PROJECT_PATH` | Builds a wheel and sdist (PEP 517) and a `.conda` (`pixi build`); CFE-independent. |
| `mason package ship` | — | Ships to `--to` targets; a dry run unless `--yes`. |
| `mason environment` | — | Noun: resolve dependency manifests into one lockfile; CFE-independent. |
| `mason environment lock` | `MANIFEST_PATH` (zero or more) | Locks the manifests (discovered in the current directory when none is given) into `--output` through conda-lock. |
| `mason environment check` | `MANIFEST_PATH` (zero or more) | Reports whether `--lockfile` is stale against the manifests; stale or a failed check exits 1. |
| `mason doctor` | — | Reports Mason's version, CFE resolution, the import floor and each engine; always exits 0. |

## Global options

AD-13's closed set of six knobs. Each is accepted on every parser path above, before or after the noun and verb, and
resolves flag, then its variable, then the default. No global option is required for any command to run.

| Option | Variable | Default | What it sets |
|---|---|---|---|
| `--cfe-root` | `MASON_CFE_ROOT` | the walk up from the current directory | The CFE root (`PATH`). |
| `--cfe-python` | `MASON_CFE_PYTHON` | the running interpreter | The interpreter that runs CFE's scripts (`PATH`). |
| `--cfe-timeout` | `MASON_CFE_TIMEOUT` | none (each adapter's own default) | Per-operation CFE subprocess timeout in seconds; finite and positive. |
| `--format` | `MASON_FORMAT` | `text` | `text` or `json`; `json` is the only machine contract. |
| `--verbose` | `MASON_VERBOSE` | off | Log at INFO. |
| `--quiet` | `MASON_QUIET` | off | Log at ERROR only; wins over `--verbose`. |

## Options and positionals

Every option and positional a single path adds on top of the six global options, one row each, keyed as
`<path> <option>` (aliases joined with `/`) or `<path> <positional>`.

| Path and argument | Kind | Notes |
|---|---|---|
| `mason --version` | option | Prints `mason <version>` and exits 0. |
| `mason recipe new --from-pypi` | option (`PACKAGE`) | One of the four `--from-*` options is required; they exclude each other. |
| `mason recipe new --from-github` | option (`OWNER/REPO`) | As above. |
| `mason recipe new --from-cran` | option (`PACKAGE`) | As above. |
| `mason recipe new --from-npm` | option (`PACKAGE`) | As above. |
| `mason recipe new --output/-o` | option (`PATH`), required | Where the generated recipe is written. |
| `mason recipe validate recipe_path` | positional | A recipe file or its directory. |
| `mason recipe build RECIPE_PATH` | positional | A recipe file or directory, or `factory/recipes/<r>`. |
| `mason recipe build --docker` | flag | The CI-parity build; requires `--config`. |
| `mason recipe build --config` | option (`CONFIG`) | Platform-variant config name for `--docker`, e.g. `linux64`. |
| `mason recipe diagnose log_path` | positional | A build-failure log file. |
| `mason recipe optimize recipe_path` | positional | A recipe file or its directory. |
| `mason recipe scan recipe_path` | positional | A recipe file or its directory. |
| `mason recipe submit recipe_path` | positional | The recipe's own directory; its basename is the submission slug. |
| `mason recipe submit --yes` | flag | Confirms a real push and PR; without it CFE runs with `--dry-run`. |
| `mason recipe submit --prepare-only` | flag | Stops after pushing the branch; opens no PR. |
| `mason recipe update recipe_path` | positional | A v1 `recipe.yaml` (with `--github`, a directory too). |
| `mason recipe update --dry-run` | flag | Shows the plan and writes nothing; without it the update is written. |
| `mason recipe update --github` | flag | Uses CFE's GitHub Releases updater instead of the PyPI one. |
| `mason recipe update --repo` | option (`OWNER/REPO`) | GitHub repository override; forwarded only with `--github`. |
| `mason recipe update --pre` | flag | Includes pre-releases; forwarded only with `--github`. |
| `mason package --target` | option (`library`) | Same as `package ship --target`, on the bare-noun alias. |
| `mason package --yes` | flag | Same as `package ship --yes`. |
| `mason package --recipe-path` | option (`RECIPE_PATH`) | Same as `package ship --recipe-path`. |
| `mason package --ship` | option (`TARGETS`) | The D-12 bare-noun alias of `package ship --to`; give it once. |
| `mason package build PROJECT_PATH` | positional | The project to build (its own `pyproject.toml` and `pixi.toml`). |
| `mason package build --target` | option (`library`) | What to build; v1 accepts `library` only (the default). |
| `mason package ship --target` | option (`library`) | What to build before shipping; `library` only. |
| `mason package ship --yes` | flag | Confirms a real ship; without it every target is `not_attempted`. |
| `mason package ship --recipe-path` | option (`RECIPE_PATH`) | The recipe directory for the `conda-forge` target; inert for the others. |
| `mason package ship --to` | option (`TARGETS`), required | Comma-separated targets in one value: `pypi`, `pypi-test`, `conda-forge`, `channel:<name>`. A repeated `--to` is a usage error. `pypi-test` named with `pypi` runs first and gates it. |
| `mason environment lock MANIFEST_PATH` | positional, zero or more | `pyproject.toml`, `environment.yml`, `requirements*.txt` or `pixi.toml`. |
| `mason environment lock --output/-o` | option (`PATH`), required | Where the lockfile is written. |
| `mason environment lock --platform` | option (`PLATFORMS`), repeatable | Repeat it, give comma-separated values, or both; omitted, conda-lock's own default applies. |
| `mason environment check MANIFEST_PATH` | positional, zero or more | As for `lock`. |
| `mason environment check --lockfile/-l` | option (`PATH`), required | The existing lockfile to verify; never written. |
| `mason environment check --platform` | option (`PLATFORMS`), repeatable | Pass the platforms the lockfile was locked with. |

## Environment variables

`MASON_FOUNDRY_ROOT` and `MASON_FACTORY_ROOT` have no flag form; AD-13's six-flag set is closed. Mason passes its own
environment through to every child it starts; the two rows marked *set for the child* add a key to one child's
environment and nothing else.

| Variable | Use | Where |
|---|---|---|
| `MASON_CFE_ROOT` | read | `--cfe-root`'s variable. |
| `MASON_CFE_PYTHON` | read | `--cfe-python`'s variable. |
| `MASON_CFE_TIMEOUT` | read | `--cfe-timeout`'s variable. |
| `MASON_FORMAT` | read | `--format`'s variable; a value other than `json` renders text. |
| `MASON_VERBOSE` | read | `--verbose`'s variable; `""`, `0`, `false` and `no` (any case) are off, anything else on. |
| `MASON_QUIET` | read | `--quiet`'s variable; truthiness as for `MASON_VERBOSE`. |
| `MASON_FOUNDRY_ROOT` | read, and set for the child | `recipe build` on a `factory/recipes/<r>` path: the python-foundry root, before the walk for `factory/pixi.toml` with `factory/pixi.lock`; the resolved root is set for the CFE build child. |
| `MASON_FACTORY_ROOT` | set for the child | `recipe build` on a factory-island path sets it to `<foundry>/factory` for the CFE build child; the adapter reads it back from that child environment to report `artifact_dir`. |
| `TWINE_USERNAME` | read | `package ship` to `pypi` or `pypi-test` refuses with `ship:credential-missing` unless it is present and non-empty; twine reads it from the inherited environment. |
| `TWINE_PASSWORD` | read | As for `TWINE_USERNAME`. |
| `PREFIX_API_KEY` | read | `package ship` to `channel:<name>` refuses with `ship:channel-credential-missing` unless it is present and non-empty; `pixi upload` reads it from the inherited environment. |
| `CFE_RECIPES_ROOT` | set for the child | `recipe submit` sets it to the recipe directory's parent for CFE's submission child; Mason never reads it. |

## Exit codes

`exit_codes.py` is the one owner; `main()` alone returns them, and no verb calls `sys.exit()`. An argparse
`SystemExit` passes its own code through (0 for `--help` and `--version`, 2 for a usage error).

| Name | Value | When |
|---|---|---|
| `EXIT_OK` | 0 | The command ran. For most verbs this says nothing about the delegated tool: read `data.returncode`, or each ship target's `state` (see *Not judged by the test*). |
| `EXIT_FAILED` | 1 | A `MasonError` other than `cfe:unresolved`, or an unanticipated exception (traceback on stderr); or the outcome projected by `recipe validate` (validator failed), `environment lock` (conda-lock failed), `environment check` (stale or failed) and `package ship` (a target is `failed`). |
| `EXIT_USAGE` | 2 | A usage error: a bare noun with no verb, an argparse-rejected invocation, or a `SystemExit` with a non-integer payload. |
| `EXIT_CFE_UNAVAILABLE` | 3 | The CFE root could not be resolved for a CFE-dependent command (`cfe:unresolved`). |
| `EXIT_INTERRUPTED` | 130 | A keyboard interrupt (128 + SIGINT). |

## Error identifiers

Identifiers are API: changing one is a major version bump. Each is `<segment>:<segment>`, lowercase and hyphenated.
An error that reaches `main()` prints `identifier: message` on stderr and, under `--format json`, fills the error
envelope's `errors` list; `package ship` instead catches each target's own error and reports it as that target's
`failed` result, with `identifier: message` as its `message`. `channel:<name>` is a ship-target form for `--to`, not
an error identifier.

| Identifier | Class | Raised when |
|---|---|---|
| `cfe:import-floor-missing` | `CfeImportFloorError` | The selected CFE interpreter lacks part of CFE's import floor. |
| `factory:missing-island` | `FactoryIslandMissingError` | A `factory/recipes/<r>` path cannot be mapped to a factory island and recipe. |
| `cfe:unresolved` | `CfeUnresolvedError` | No step of the resolution chain found a CFE root (exit 3). |
| `recipe:generation-failed` | `RecipeGenerationError` | CFE's recipe generator exited non-zero for `recipe new`. |
| `cfe:timeout` | `CfeTimeoutError` | A CFE subprocess outran its timeout. |
| `engine:absent` | `EngineAbsentError` | A required engine executable is not on `PATH`. |
| `package:version-mismatch` | `PackageVersionMismatchError` | The built artifacts disagree on the project's version. |
| `package:build-timeout` | `PackageBuildTimeoutError` | A package build engine outran its timeout. |
| `package:project-path-invalid` | `PackageProjectPathError` | `PROJECT_PATH` is not a buildable project directory. |
| `ship:invalid-target` | `InvalidShipTargetError` | A `--to`/`--ship` token is not one of the four target forms. |
| `ship:credential-missing` | `ShipCredentialMissingError` | `TWINE_USERNAME` or `TWINE_PASSWORD` is absent or empty. |
| `ship:upload-timeout` | `ShipUploadTimeoutError` | A PyPI upload outran its timeout. |
| `ship:channel-credential-missing` | `ShipChannelCredentialMissingError` | `PREFIX_API_KEY` is absent or empty. |
| `ship:channel-upload-timeout` | `ShipChannelUploadTimeoutError` | A channel upload outran its timeout. |
| `ship:conda-forge-recipe-missing` | `ShipCondaForgeRecipeMissingError` | The `conda-forge` target has no `--recipe-path`. |
| `ship:conda-forge-recipe-location` | `ShipCondaForgeRecipeLocationError` | The `conda-forge` recipe is not under the CFE root's `recipes/` directory. |
| `environment:lock-timeout` | `EnvironmentLockTimeoutError` | conda-lock outran its timeout during `environment lock`. |
| `environment:lockfile-missing` | `EnvironmentLockfileMissingError` | `environment check`'s `--lockfile` does not exist. |
| `environment:lockfile-malformed` | `EnvironmentLockfileMalformedError` | `environment check`'s `--lockfile` cannot be read as a conda-lock lockfile. |
| `environment:check-temp-unreadable` | `EnvironmentCheckTempCopyUnreadableError` | `environment check` could not read the content hash from its temporary lockfile copy after conda-lock ran. |
| `environment:check-timeout` | `EnvironmentCheckTimeoutError` | conda-lock outran its timeout during `environment check`. |
| `environment:manifests-not-found` | `EnvironmentManifestsNotFoundError` | No manifest path was given and none was discovered in the current directory. |

## MCP tool and portal-job names

Mason's package ships no MCP server. Its station face is `POST /stations/mason/mcp` on the platform host, built by
django-pyforge's `build_station_mcp_asgi` in django-mason (`src/shared/packages/django-mason/src/django_mason_portal/mcp_asgi.py`),
code governed by `spec-pyforge-unifying-strategy`, not by this Spec. What the face runs is under *Not judged by the
test*.

| Name | Kind | Defined in |
|---|---|---|
| `start_build` | MCP tool | django-mason `mcp_asgi.py`, `START_BUILD_TOOL`. Starts a supervised run and returns a handle. |
| `get_build` | MCP tool | django-mason `mcp_asgi.py`, `GET_BUILD_TOOL`. Returns the supervisor's record of that run. |
| `run_build` | supervisor runner, not an MCP tool | django-mason `mcp_asgi.py`, `RUN_BUILD_TOOL`. The runner `start_build` hands to the supervisor. |
| `last_diagnose` | portal job | django-pyforge `assertion/client.py`, `LAST_DIAGNOSE_TOOL`. django-mason registers its portal job under this name at app start, and the `/stations/mason/` page reads the last diagnosis through `PortalClient`. |

## Feature-flag keys

Mason reads no feature flag: nothing under `src/pyforge/mason/` calls a `pyforge.core.flags` reader or reads
`pyforge.cutover_root`. The table is empty, and a key the code starts reading fails the test until it has a row here.

| Key | Default | What it gates |
|---|---|---|

## Not judged by the test

The rest of this file is the contract as prose. The test does not read it; a change to what it describes updates it
by hand in the same change.

### The JSON envelope

Under `--format json` stdout carries exactly one JSON document or nothing, and every diagnostic goes to stderr. The
document has exactly five keys (`render.py`, rendered with sorted keys):

- `schema_version`: `"1"`.
- `command`: the path without `mason`, e.g. `"recipe build"`, `"package ship"`, `"doctor"`; `"mason"` when the
  failure comes before the arguments are parsed.
- `status`: `"ok"` when the command ran, whatever the delegated tool did; `"error"` when a `MasonError` was raised.
- `data`: the command's result object. A delegated tool's return code is data, never an error: it is
  `data.returncode` (`recipe build`, `package build`, `environment lock`, `environment check`, and each verb that
  wraps a CFE script). `package ship` puts its results in `data.targets[]`, each `{target, state, reference,
  message}`; `recipe submit` returns one such result as `data` (its `reference` is the pull-request URL, else the
  pushed branch). An error envelope has `data` `{}`.
- `errors`: `[]`, or `[{"identifier": ..., "message": ...}]` for the `MasonError` raised.

`--format text` is a human summary and is not a contract.

### Ship states (AD-9)

Every ship target result is in one of four states:

- `not_attempted`: no `--yes`, a dry run; nothing was pushed, uploaded or opened. Also a `pypi` target whose
  `pypi-test` rehearsal did not reach `terminal`.
- `pending`: a confirmed attempt started something real that is not yet confirmed (a conda-forge pull request was
  opened or its branch pushed), or the target could not be interrogated, so no upload was made.
- `terminal`: the target reached its end state (uploaded, or the version was already there).
- `failed`: a confirmed attempt did not succeed, or a precondition refused it.

`package ship` exits 1 only when a target is `failed`; `not_attempted`, `pending` and `terminal` all exit 0, and
`recipe submit` exits 0 in every state. **exit 0 does not mean shipped**: read `data.targets[].state` (or
`data.state` for `recipe submit`). `pending` is never rendered as success.

### The doctor report

`mason doctor --format json` puts these fields in `data` (`models.DoctorReport`): `mason_version`, `cfe_root`,
`cfe_root_step`, `cfe_interpreter`, `cfe_interpreter_step`, `cfe_import_floor_satisfied`,
`cfe_import_floor_missing`, `unavailable_verbs`, `engines` (each `{name, available, version}`),
`conda_forge_ship_ready` and `conda_forge_ship_blockers`. It never raises and always exits `EXIT_OK`: a missing CFE or
engine is data in the report, not a failure.

### The build-engine hook

Mason publishes the hook spec `pyforge.mason.build_engine` (owner `mason`) on pyforge-core's `pyforge.core.hooks`
entry-point group with two entry points: `rattler-build` (`pyforge.mason.engines.build_hooks:RattlerBuildPlugin`, the
default, which runs today's CFE native build) and `conda-build` (`pyforge.mason.engines.build_hooks:CondaBuildPlugin`,
registered for selection; it spawns nothing). A caller selects one plugin and calls it; it never invokes every plugin
on the spec.

### Layout

Mason assumes this layout and creates none of it:

- At the CFE root: `<cfe-root>/.claude/scripts/conda-forge-expert/<script>`, where `<script>` is a value of
  `cfe._CFE_SCRIPTS`, the one table of the CFE scripts Mason runs. That directory is also the marker the walk for the
  CFE root looks for. The table's `build_docker` entry is the one exception: it sits at the root itself,
  `<cfe-root>/build-locally.py`.
- For a `conda-forge` ship: the recipe at `<cfe-root>/recipes/<name>/`.
- For a factory-island build (`recipe build factory/recipes/<r>`): `<foundry>/factory/pixi.toml`,
  `<foundry>/factory/pixi.lock` and `<foundry>/factory/recipes/<r>`, with `<foundry>` from `MASON_FOUNDRY_ROOT` or the
  walk up from the current directory. The island is wired for the native build; `--docker` on an island path is
  recorded, not built. Island artifacts are reported under `<foundry>/factory/build_artifacts/<config>`, any other
  build's under `build_artifacts/<config>`.
- Which root a `package ship --to conda-forge` resolves on a foundry checkout is recorded here as layout only; the
  behaviour waits on steward Stories 44.8 and 44.9.

### The MCP face

The face is a supervisor face: `start_build` returns a handle and `get_build` the run's record. Its runner
`run_build` runs one row of django-pyforge's closed verb table (`django_pyforge.station_cli.STATION_VERBS`):
`pyforge mason recipe build recipes/<slug> --format json` in the `pyforge-mason` environment, for a recipe tracked in
git, never started again on a redelivery, and judged by `data.returncode` (Mason exits 0 whatever the build did). It refuses while the kill switch
`pyforge.steward.start_tool_cli` is off; django-pyforge reads that key, Mason does not. No other Mason verb is
reachable through the face. That code is django-mason's and django-pyforge's, governed by
`spec-pyforge-unifying-strategy`.
