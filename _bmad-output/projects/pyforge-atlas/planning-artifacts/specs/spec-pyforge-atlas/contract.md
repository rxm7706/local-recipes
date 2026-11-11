# The public contract — what atlas exposes and what it reads

Companion to `SPEC.md` (spec-pyforge-atlas:CAP-73, FR-78). A reader who has only this Spec folder can name
everything the `pyforge-atlas` package exposes from this file: every CLI verb and option, every MCP tool, every
feature-flag key with its default per environment, every environment variable with its default, every exit code,
and what the package reads outside itself. The catalog datasets are `catalog-contract.md`'s and the gate tasks
`gate-contract.md`'s (spec-pyforge-atlas:CAP-73's other half, Story 47.2).

Written by Story 47.1 against the tree Stories 48.2 and 48.3 leave: no views runtime, and the query plane's default
path resolved from the member.

**How this file is held to the code.** `src/shared/packages/pyforge-atlas/tests/meta/test_public_contract.py`
derives six families from the code and fails when a derived name is not a code token in its own section here:
`## CLI verbs`, `## CLI options` (one `###` subsection per entry point), `## MCP tools`, `## Feature flags`,
`## Environment variables` and `## Exit codes` (one table row per entry point). The flag keys it derives must also
equal the `pyforge.atlas.*` keys of the flag tree. Every section after `## Exit codes` is prose the test does not
judge. Paths below are relative to the member, `src/shared/packages/pyforge-atlas/`, unless they start at the
repository root.

## CLI verbs

`pyforge atlas …` is the unified dispatch onto the console script `pyforge-atlas`
(`pyforge.atlas.__main__:main`, also `python -m pyforge.atlas`). `--version` is answered first; any other argv goes
to Kedro's project command group, which `__main__.discover_cli_verbs` reads. Each command runs with the member as its
working directory, and the caller's directory comes back afterwards, so a relative path passed to `run` resolves
against the member. A bare `pyforge atlas` lists the commands and runs nothing.

| Verb | What it does |
|---|---|
| `pyforge atlas run` | Kedro's `run`: runs the registered pipelines (`--pipelines a,b` sums them into one DAG). With the kill switch `pyforge.atlas.agent_pipeline_tools` off it stays listed in `--help` marked `[disabled: flag <key> is off]` and refuses with exit `2` before Kedro runs; naming `universal_sbom` with `pyforge.atlas.manifest_inventory` off refuses the same way. |
| `pyforge atlas ipython` | Kedro's `ipython`: an IPython shell with the project's `catalog`, `context`, `pipelines` and `session` loaded. |
| `pyforge atlas package` | Kedro's `package`: builds the project wheel and a tarball of `conf/` into `dist/`. |
| `pyforge atlas --version` | First token only: prints `pyforge-atlas <version>` and returns without importing Kedro. |

The other entry points are run as modules or scripts, not as `pyforge atlas` verbs (each has a subsection under
`## CLI options` and a row under `## Exit codes`):

| Entry point | Run as |
|---|---|
| `python -m pyforge.atlas.trending_candidates` | pixi task `trending-candidates` |
| `python -m pyforge.atlas.trending_candidates.handoff_main` | pixi task `trending-handoff` |
| `python -m pyforge.atlas.query_plane_boot` | pixi task `query-plane-boot` |
| `python -m pyforge.atlas.publish` | pixi task `publish` |
| `python -m pyforge.atlas.datasets.vdb_extract` | by file, `python -I <path>`, inside the `vuln-db` env (`datasets/refresh.py`); no pyforge import |
| `tools/bootstrap.py` | pixi task `pyforge-atlas-bootstrap` (then `kedro run`); `--credentials-only` in `kedro-viz-publish.yml` |
| `tools/lasuite_bringup.py` | by hand, at the attended La Suite bring-up (not a gate) |
| `tools/live_artifactory_transport.py` | imported by `tests/tools/test_live_artifactory_transport.py`; no `__main__` |
| `tools/normalize_viz_build.py` | pixi task `viz-publish-stage` |
| `tools/print_viz_export_flag.py` | `kedro-viz-publish.yml` (writes `enabled=true` or `enabled=false` to `GITHUB_OUTPUT`) |
| `tools/viz_build_check.py` | pixi task `viz-build` |
| `tools/viz_manifest.py` | imported by `tools/viz_publish_finish.py` and `tools/vizro_static_export.py`; also runnable alone |
| `tools/viz_publish_finish.py` | pixi task `viz-publish-stage` |
| `tools/vizro_static_export.py` | pixi task `vizro-static-export` |

## CLI options

Every argparse entry point also takes `-h` / `--help`, and exits `2` on a usage error (argparse's own code).

### `pyforge atlas run`

Kedro's own `run` options.

| Option | Meaning |
|---|---|
| `--pipelines` | Comma-separated registered pipelines, summed into one DAG (Kedro 1.6's spelling; the MCP `run_*` tools map onto it). |
| `--pipeline`, `-p` | One registered pipeline; `__default__` when unset. Deprecated by Kedro 1.6 in favour of `--pipelines`. |
| `--env`, `-e` | Kedro configuration environment; `local` by default. |
| `--from-inputs` | Dataset names to start from. |
| `--to-outputs` | Dataset names to end at. |
| `--from-nodes` | Node names to start from. |
| `--to-nodes` | Node names to end at. |
| `--nodes`, `-n` | Run only these nodes. |
| `--tags`, `-t` | Run only nodes carrying these tags. |
| `--namespaces`, `-ns` | Run only nodes in these namespaces. |
| `--runner`, `-r` | The runner class (Kedro's `SequentialRunner` by default). |
| `--async` | Load and save node inputs and outputs asynchronously, with threads. |
| `--runner-params` | Extra runner keyword arguments, `key=value,…`. |
| `--load-versions`, `-lv` | The dataset version (timestamp) to load. |
| `--params` | Extra parameters, `key=value,…`. |
| `--config`, `-c` | A YAML file of `run` arguments. |
| `--conf-source` | The configuration directory to read. |
| `--only-missing-outputs` | Run only nodes whose persisted outputs are missing. |

### `pyforge atlas ipython`

| Option | Meaning |
|---|---|
| `--env`, `-e` | Kedro configuration environment; `local` by default. |
| `--verbose`, `-v` | Extensive logging and error stack traces. |
| `args` | Positional, any number: passed through to IPython. |

### `pyforge atlas package`

No options.

### `python -m pyforge.atlas.trending_candidates`

Read-side query over the classified trending list (`trending_candidates_classified`); the CLI twin of the MCP tool
`query_trending_candidates`.

| Option | Meaning |
|---|---|
| `--period` | `daily`, `weekly`, `monthly` or `all`; `weekly` by default. |
| `--tier` | Comma list of `1`, `2`, `skip`, or `all`; `1,2` by default. |
| `--top` | Display cap; `25` by default. |
| `--not-on-cf` | Keep only candidates not yet on conda-forge (the default). |
| `--all` | Include candidates already on conda-forge (clears `--not-on-cf`). |
| `--min-stars` | Star floor; `500` by default. |
| `--json` | JSON output instead of a table. |

### `python -m pyforge.atlas.trending_candidates.handoff_main`

The handoff of one tier-1 or tier-2 candidate to Mason, as one JSON record.

| Option | Meaning |
|---|---|
| `--repo` | Required: `owner/repo`, case-insensitive. |
| `--verdict` | Required: the recorded health-screen verdict, `pass` or `fail`; only `pass` hands off. |
| `--abandonment-signal` | Required: the recorded abandonment-signal evidence (non-empty). |
| `--license-clarity` | Required: the recorded license-clarity evidence (non-empty). |

### `python -m pyforge.atlas.query_plane_boot`

Boots the query plane; with the platform stack up (`PYFORGE_PLATFORM_STACK_UP`) it raises and supervises the
`duckdb-server` HTTP face.

| Option | Meaning |
|---|---|
| `--path` | The plane database; its basename must be `atlas.duckdb`. Default: the member's `data/plane/atlas.duckdb`, resolved from the member (Story 48.2), not moved by `PYFORGE_ATLAS_DATA_ROOT`. |
| `--host` | The host in the reported HTTP endpoint; `127.0.0.1` by default. |
| `--port` | The HTTP face port; `3000` by default (the installed `duckdb-server` listens on 3000 whatever is passed). |

### `python -m pyforge.atlas.publish`

Emits the static-host site from a seed CSV.

| Option | Meaning |
|---|---|
| `--target` | Output directory; `src/pyforge/atlas/publish/_site` by default. |
| `--seed` | Seed CSV; `wasm/data/feedstock_health.csv` by default. |
| `--rows-per-chunk` | Rows per emitted chunk; `250000` by default. |
| `--row-group-size` | Parquet row-group size; `100000` by default. |

### `python -m pyforge.atlas.datasets.vdb_extract`

The `vuln-db` env's own tool (not an atlas verb).

| Option | Meaning |
|---|---|
| `command` | Positional: `age` (seconds since `$VDB_HOME/vdb.meta` was built, `-1` when none) or `extract`. |
| `--targets` | `extract`: a JSON file of targets (required with `extract`). |
| `--versions` | `extract`: a JSON file of versions per target (optional). |
| `--out` | `extract`: the Parquet file to write (required with `extract`). |

### `tools/bootstrap.py`

| Option | Meaning |
|---|---|
| `--credentials-only` | Write only the `conf/local/credentials.yml` stub (every key `conf/base/catalog.yml` names, each `{}`), and only when the file is absent or empty; no store directories. Without it the tool also creates the data root's `stores/vdb` and `stores/osv`. |

### `tools/lasuite_bringup.py`

No options; it reads `LASUITE_BASE_URL`, `LASUITE_API_TOKEN` and `ATLAS_WIKI_ROOT`.

### `tools/live_artifactory_transport.py`

No options: a module of factories the attended Artifactory run imports; it reads no environment variable.

### `tools/normalize_viz_build.py`

No options.

### `tools/print_viz_export_flag.py`

No options.

### `tools/viz_build_check.py`

| Option | Meaning |
|---|---|
| `--build-dir` | The kedro-viz build directory; the member's `build/` by default. |

### `tools/viz_manifest.py`

| Option | Meaning |
|---|---|
| `--staged-dir` | The staged export root; `docs/dashboard/kedro-viz` under the repository root by default. |
| `--flag-on` | Required (with its negation `--no-flag-on`): when false, write nothing and exit `0`. |
| `--export-commit` | The 40-hex commit; `GITHUB_SHA`, else `HEAD`, by default. |

### `tools/viz_publish_finish.py`

No options.

### `tools/vizro_static_export.py`

| Option | Meaning |
|---|---|
| `--out` | Output directory; `docs/dashboard/vizro` under the repository root by default. |
| `--data-root` | The data root; the dashboard's own by default. |
| `--flags-path` | The flag tree; `PYFORGE_FLAGS_PATH` or the repository's by default. |
| `--export-commit` | The 40-hex commit; `GITHUB_SHA`, else `HEAD`, by default. |
| `--print-flag` | Print `enabled=true` or `enabled=false` and exit `0`. |
| `--clock` | What `exported_at` is: `commit` (the export commit's committer time, the default) or `now`. |

## MCP tools

Thirteen tools, registered in `mcp/tools.py`'s `TOOL_SPECS` and on the official `mcp` SDK in `mcp/server.py`'s
`build_server` (the SDK is imported lazily, so the package imports without it). Each tool body is one call to
`mcp/tools.py`, which crosses the one session seam (`mcp/session.py`). The HTTP face is `POST /stations/atlas/mcp`
(see *The HTTP face* below).

| Tool | Arguments | What it does | CLI twin |
|---|---|---|---|
| `run_core_pipeline` | none | Runs the `core` pipeline through `KedroSession.run`; returns a receipt of output names. | `pyforge atlas run --pipelines core` |
| `run_vcs_health_pipeline` | none | Runs `vcs_health`. | `pyforge atlas run --pipelines vcs_health` |
| `run_pypi_intelligence_pipeline` | none | Runs `pypi_intelligence`. | `pyforge atlas run --pipelines pypi_intelligence` |
| `run_vulnerability_pipeline` | none | Runs `vulnerability`. | `pyforge atlas run --pipelines vulnerability` |
| `run_seed_gaps_pipeline` | none | Runs `seed_gaps`. | `pyforge atlas run --pipelines seed_gaps` |
| `run_universal_sbom_pipeline` | none | Runs `universal_sbom`; refuses when `pyforge.atlas.manifest_inventory` is off. | `pyforge atlas run --pipelines universal_sbom` |
| `run_derived_artifacts_pipeline` | none | Runs `derived_artifacts`. | `pyforge atlas run --pipelines derived_artifacts` |
| `run_upstream_discovery_pipeline` | none | Runs `upstream_discovery`. | `pyforge atlas run --pipelines upstream_discovery` |
| `read_atlas_dataset` | `name` | Loads one catalog dataset with its build-provenance envelope. | none |
| `list_atlas_pipelines` | none | The eight MCP-triggerable pipeline names (`PIPELINE_NAMES`). | none |
| `list_atlas_datasets` | none | The declared catalog dataset names. | none |
| `query_vizro_ai` | `query` | A natural-language Vizro-AI query over the semantic graph; with no model backend configured it returns an advisory and makes no call. | none |
| `query_trending_candidates` | `period`, `tier`, `top`, `not_on_cf`, `min_stars` | The classified trending list, filtered. | `python -m pyforge.atlas.trending_candidates` |

Every `run_*` tool refuses when the kill switch `pyforge.atlas.agent_pipeline_tools` is off. Unknown pipeline names
raise `AtlasMCPError`.

## Feature flags

Eleven keys, each read through `pyforge.core.flags`. The tree is `src/platform/config/flags.json` (found by
`pyforge.core.cutover_root.resolve_flags_path`; `PYFORGE_FLAGS_PATH` overrides it), the environment is
`PYFORGE_ENVIRONMENT` (`dev` when unset), and `src/platform/config/flag-overlays.json` picks each key's variant per
environment. In the tree every key is `ENABLED`; its `defaultVariant` is the value with no overlay. A
`read_boolean(key, default=False)` site reads off when the tree is missing or unreadable; a `kill_switch_on` site
reads on when no tree is in reach.

| Key | Read by | No tree | Tree default | `dev` | `staging` | `production` |
|---|---|---|---|---|---|---|
| `pyforge.atlas.agent_pipeline_tools` | `mcp/session.py`, `__main__.py` (`kill_switch_on`): agents trigger and read pipelines natively; the `run` verb | on | on | on | on | on |
| `pyforge.atlas.manifest_inventory` | `mcp/session.py`, `__main__.py`, `pipeline_registry.py` (`kill_switch_on`): `universal_sbom` | on | on | on | on | on |
| `pyforge.atlas.dependency_history` | `datasets/dependency_history.py`, `pipelines/vcs_health/nodes.py`: the per-repo dependency history | off | off | on | on | off |
| `pyforge.atlas.dependency_history_sensor` | `orchestration/fleet_inventory_sensor.py`, `orchestration/definitions.py`: the poll-cursor sensor | off | off | on | on | off |
| `pyforge.atlas.live_public_sources` | `datasets/public_sources.py`: public sources fetched live | off | off | on | on | off |
| `pyforge.atlas.live_vcs_universe` | `datasets/credentials.py`: the VCS universe, GitHub authenticated | off | off | on | off | off |
| `pyforge.atlas.basilisk_population` | `datasets/basilisk.py`: the Basilisk population run | off | off | on | off | off |
| `pyforge.atlas.identity_live_sources` | `datasets/identity_sources.py`: the identity board's live sources | off | off | on | off | off |
| `pyforge.atlas.board_projections` | `dashboard/data.py`: boards read the pipelines' datasets | off | off | on | off | off |
| `pyforge.atlas.viz_export_artifact` | `viz_export_artifact.py`, `tools/print_viz_export_flag.py`, `tools/viz_publish_finish.py`: the DAG export reaches Pages | off | off | on | off | off |
| `pyforge.atlas.vizro_static_boards` | `vizro_static_boards.py`, `tools/vizro_static_export.py`: the static Vizro boards | off | off | on | off | off |

## Environment variables

The default is what the code does when the variable is unset (the catalog override points and the data and lock
roots also treat an empty value as unset). The first three tables are derived by the meta-test; the fourth lists
reads it does not derive.

### Read directly

`os.environ.get` / `os.environ[...]` / `os.getenv` in `src/` and `tools/`, the name a literal or a module-level
constant.

| Variable | Read by | Default |
|---|---|---|
| `PYFORGE_ATLAS_DATA_ROOT` | `admission.py`, `dashboard/data.py`, `tools/bootstrap.py`; also `conf/base/globals.yml` `paths.data_root` | `data`, relative to the member (see *The data root*) |
| `PYFORGE_ATLAS_LOCK_ROOT` | `admission.py` | the lock store `<data root>.locks`, the data root's sibling; a value gives `<value>/.locks`, refused inside the data root |
| `PYFORGE_ATLAS_CREDENTIALED` | `datasets/credentials.py` | off; only the exact value `1` turns the credentialed fetches on |
| `PYFORGE_ATLAS_BASILISK_TOKEN` | `datasets/credentials.py` | no Basilisk bearer auth; read only with `PYFORGE_ATLAS_CREDENTIALED=1` |
| `PYFORGE_ATLAS_LOCAL_RECIPES_REPO_SLUG` | `datasets/identity_sources.py` | `rxm7706/local-recipes` |
| `PYFORGE_PLATFORM_STACK_UP` | `query_plane_boot.py` | stack down; `1`, `true`, `yes` or `on` (any case) raises the HTTP face |
| `PHASE_K_AGGRESSIVE` | `datasets/basilisk.py` | one worker; exactly `1` gives eight |
| `PYPI_JSON_FANOUT_LIMIT` | `datasets/request_datasets.py` | live public sources off: a rotation of `200` per cycle; on: the whole eligible set, uncapped; `0` skips the live fetch this cycle |
| `PHASE_P_ENABLED` | `datasets/request_datasets.py` | off; only the exact value `1` enables Phase P |
| `PHASE_P_SOURCE` | `datasets/request_datasets.py` | `clickhouse`; `bigquery` with Phase P enabled refuses on the default load path (an attended run only) |
| `KEDRO_ENV` | `orchestration/definitions.py` | `local` |
| `VDB_HOME` | `datasets/vdb_extract.py` (`age`) | no home: age `-1`; `datasets/refresh.py` sets it to the store's own vdb |
| `ATLAS_WIKI_ROOT` | `tools/lasuite_bringup.py`; `orchestration/definitions.py` through its mapping | the member's `wiki/` |
| `GITHUB_SHA` | `tools/viz_manifest.py` | `git rev-parse HEAD` |

### Read through a variable

Each resolved from the table or the call sites that feed it.

| Variable | Read by (fed by) | Default |
|---|---|---|
| `BIOCONDA_BASE_URL` | `datasets/core_sources.py` (`_CROSS_CHANNEL_SPECS`: `<CHANNEL>_BASE_URL`) | the mirror chain `https://repo.prefix.dev/bioconda`, then `https://conda.anaconda.org/bioconda` |
| `PYTORCH_BASE_URL` | same | the same chain for `pytorch` |
| `NVIDIA_BASE_URL` | same | the same chain for `nvidia` |
| `ROBOSTACK_STAGING_BASE_URL` | same | the same chain for `robostack-staging` |
| `SELFEXPLAINML_BASE_URL` | same | the same chain for `selfexplainml` |
| `PHASE_P_USD_PER_TB` | `datasets/request_datasets.py` (`_env_float`) | `6.25` |
| `PHASE_P_MAX_COST_USD` | same | `10.0` |
| `PHASE_P_MAX_COST_FIRST_PULL_USD` | same | `100.0` |
| `PHASE_P_JOB_TIMEOUT_MS` | `datasets/request_datasets.py` (`_env_int`) | `600000` |
| `ATLAS_WIKI_S3_ENDPOINT` | `factory/storage.py` (`_env_or`) | none: the wiki stays on the local filesystem |
| `ATLAS_WIKI_S3_BUCKET` | same | empty |
| `ATLAS_WIKI_S3_ACCESS_KEY` | same | empty (credentials absent) |
| `ATLAS_WIKI_S3_SECRET_KEY` | same | empty (credentials absent) |

### Catalog override points

Every `${env_or:NAME,<default>}` in `conf/base/globals.yml`, resolved by `settings._env_or` (an empty value counts as
unset). `CONFIG_LOADER_ARGS` registers that resolver as `env_or`.

| Variable | `globals.yml` key | Default |
|---|---|---|
| `CONDA_FORGE_BASE_URL` | `endpoint_bases` | `https://conda.anaconda.org/conda-forge` |
| `PYPI_BASE_URL` | `endpoint_bases` | `https://pypi.org/simple` |
| `PYPI_JSON_BASE_URL` | `endpoint_bases` | `https://pypi.org` |
| `GITHUB_BASE_URL` | `endpoint_bases` | `https://github.com` |
| `GITHUB_RAW_BASE_URL` | `endpoint_bases` | `https://raw.githubusercontent.com` |
| `NPM_BASE_URL` | `endpoint_bases` | `https://registry.npmjs.org` |
| `CRAN_BASE_URL` | `endpoint_bases` | `https://crandb.r-pkg.org` |
| `CPAN_BASE_URL` | `endpoint_bases` | `https://fastapi.metacpan.org` |
| `LUAROCKS_BASE_URL` | `endpoint_bases` | `https://luarocks.org` |
| `CRATES_BASE_URL` | `endpoint_bases` | `https://crates.io` |
| `RUBYGEMS_BASE_URL` | `endpoint_bases` | `https://rubygems.org` |
| `MAVEN_BASE_URL` | `endpoint_bases` | `https://search.maven.org` |
| `NUGET_BASE_URL` | `endpoint_bases` | `https://api.nuget.org` |
| `ENDOFLIFE_BASE_URL` | `endpoint_bases` | `https://endoflife.date` |
| `GITHUB_API_BASE_URL` | `endpoint_bases` | `https://api.github.com` |
| `GITLAB_API_BASE_URL` | `endpoint_bases` | `https://gitlab.com/api/v4` |
| `CODEBERG_API_BASE_URL` | `endpoint_bases` | `https://codeberg.org/api/v1` |
| `ANACONDA_CHANNEL_BASE_URL` | `endpoint_bases` | `https://conda.anaconda.org` |
| `S3_PARQUET_BASE_URL` | `endpoint_bases` | `https://anaconda-package-data.s3.amazonaws.com` |
| `BASILISK_BASE_URL` | `endpoint_bases` | `https://api.basilisk.prefix.dev` |
| `ANACONDA_DIST_BASE_URL` | `endpoint_bases` | `https://www.anaconda.com` |
| `AOSS_PREMIUM_BASE_URL` | `endpoint_bases` | `https://docs.cloud.google.com` |
| `HOMEBREW_BASE_URL` | `endpoint_bases` | `https://formulae.brew.sh` |
| `NIXPKGS_BASE_URL` | `endpoint_bases` | `https://channels.nixos.org` |
| `SPACK_PACKAGES_BASE_URL` | `endpoint_bases` | `https://packages.spack.io` |
| `DEBIAN_BASE_URL` | `endpoint_bases` | `https://deb.debian.org` |
| `FEDORA_SRC_BASE_URL` | `endpoint_bases` | `https://src.fedoraproject.org` |
| `ANACONDA_API_BASE_URL` | `extra_overrides` | `https://api.anaconda.org` |
| `OSV_VULNS_BUCKET_URL` | `extra_overrides` | `https://osv-vulnerabilities.storage.googleapis.com` |
| `BIGQUERY_BASE_URL` | `extra_overrides` | `https://bigquery.googleapis.com/bigquery/v2` |
| `PURL_ASSOCIATOR_BASE_URL` | `extra_overrides` | `https://prefix-dev.github.io` |
| `CLICKHOUSE_PYPI_BASE_URL` | `extra_overrides` | `https://sql-clickhouse.clickhouse.com` |
| `CISA_KEV_URL` | `fetcher_urls` | `https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json` |
| `EPSS_FEED_URL` | `fetcher_urls` | `https://epss.empiricalsecurity.com/epss_scores-current.csv.gz` |
| `CWE_CATALOG_URL` | `fetcher_urls` | `https://cwe.mitre.org/data/csv/1000.csv.zip` |
| `PYFORGE_ATLAS_DATA_ROOT` | `paths.data_root` | `data` |
| `PYFORGE_ATLAS_SEED_ROOT` | `paths.seed_root` | `../../../../.claude/skills/conda-forge-expert/data` (from the member: the repository's conda-forge-expert seeds) |
| `PYFORGE_ATLAS_LOCAL_RECIPES_DIR` | `paths.local_recipes_dir` | `../../../../recipes` (from the member: the repository's `recipes/`) |

### Read through an injected mapping

These functions take an `env` mapping that defaults to `os.environ`; the meta-test does not derive them (Story 47.1's
planned deferral, DW-atlas-47-1-1).

| Variable | Read by | Default |
|---|---|---|
| `LASUITE_BASE_URL` | `factory/lasuite.py` | unconfigured: no push (both this and the token are required) |
| `LASUITE_API_TOKEN` | `factory/lasuite.py` | unconfigured |
| `OPENAI_BASE_URL` | `nl/backend.py` | unconfigured: `query_vizro_ai` returns its advisory |
| `OPENAI_API_KEY` | `nl/backend.py` | unconfigured |
| `ANTHROPIC_BASE_URL` | `nl/backend.py` | unconfigured (the fallback provider) |
| `ANTHROPIC_API_KEY` | `nl/backend.py` | unconfigured |
| `VIZRO_AI_MODEL` | `nl/backend.py` | no model override |
| `PYFORGE_ATLAS_SCOPE` | `orchestration/definitions.py` (`resolve_profile_config`) | the profile's `scope` |
| `PYFORGE_ATLAS_PHASE_E` | same | the profile's `phase_e` |
| `PYFORGE_ATLAS_PHASE_N` | same | the profile's `phase_n` |
| `PYFORGE_ATLAS_PHASE_P` | same | the profile's `phase_p` |
| `PYFORGE_ATLAS_READ_ONLY` | same | the profile's `read_only` |
| `INVENTORY_MATCH_LEGACY_EXIT` | `pipelines/universal_sbom/gate.py` | the frozen exit codes; `1` restores the legacy inverted codes for one release |

Atlas also hands child processes a curated environment: `datasets/dependency_history.py` drops `GIT_DIR`,
`GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_COMMON_DIR`, `GIT_OBJECT_DIRECTORY` and `GIT_ALTERNATE_OBJECT_DIRECTORIES`
from every git call and sets `GIT_TERMINAL_PROMPT=0`; `datasets/refresh.py` sets `VDB_HOME` and `VDB_CACHE` for the
`vuln-db` child. `pyforge.core.flags` reads `PYFORGE_FLAGS_PATH` and `PYFORGE_ENVIRONMENT` on atlas's behalf.

## Exit codes

The frozen domain (`degradation-contract.md`, spec-pyforge-atlas:CAP-13): `0` pass, `1` policy fail, `2` error,
`130` interrupted; an indeterminate result maps to `1`. The one exception is the attended La Suite bring-up,
`tools/lasuite_bringup.py`, which is not a gate and keeps `0` to `4`: `3` when there is no `outputs/` stage or
nothing synced, `4` on a local read or write error. Every argparse entry point also exits `2` on a usage error.

| Entry point | Codes | Meaning |
|---|---|---|
| `pyforge atlas` | `0` `1` `2` | `0` success, and `--version`; `2` a kill-switch refusal before Kedro runs; otherwise Click's own codes (`1` a failed or aborted command, `2` usage). |
| `python -m pyforge.atlas.trending_candidates` | `0` `1` | `1` any failure, a bad filter value included, as one stderr line. |
| `python -m pyforge.atlas.trending_candidates.handoff_main` | `0` `1` `2` `130` | `1` an ineligible candidate, a missing or failing health screen, or a dataset not yet ingested; `2` any other error. |
| `python -m pyforge.atlas.query_plane_boot` | `0` `1` `2` `130` | `1` a typed refusal (a second writer, or `duckdb-server` not provisioned); `130` also on SIGTERM while supervising. |
| `python -m pyforge.atlas.publish` | `0` `1` | `1` the seed CSV is missing. |
| `python -m pyforge.atlas.datasets.vdb_extract` | `0` | argparse's `2` on a bad command. |
| `tools/bootstrap.py` | `0` | — |
| `tools/lasuite_bringup.py` | `0` `1` `2` `3` `4` | `1` not configured (`LASUITE_BASE_URL` and `LASUITE_API_TOKEN` both needed); `2` the CMS call failed or the HTTP client could not be built; `3` nothing to push or zero pages synced; `4` the wiki tree is unreadable, unwritable or holds a non-UTF-8 page. |
| `tools/normalize_viz_build.py` | `0` | a missing `build/` raises, which Python reports as `1`. |
| `tools/print_viz_export_flag.py` | `0` | — |
| `tools/viz_build_check.py` | `0` `1` | `1` kedro-viz wrote no complete build. |
| `tools/viz_manifest.py` | `0` `1` | `1` the export commit or its committer time cannot be resolved. |
| `tools/viz_publish_finish.py` | `0` `1` | what `viz_manifest.write_manifest` returns. |
| `tools/vizro_static_export.py` | `0` `1` `2` `130` | `1` the export refused or the commit could not be resolved; `2` the flag is off, or a crash. |

`wasm/build.py` (the `wasm-build` task) sits outside `src/` and `tools/`, so the meta-test does not derive it
(DW-atlas-47-1-1); it exits through `sys.exit("<message>")`, which Python reports as `1`, when npm or a DuckDB-WASM
asset is missing.

## The HTTP face

Atlas has one HTTP face, `POST /stations/atlas/mcp`, hosted by django-atlas
(`src/shared/packages/django-atlas/src/django_atlas_portal/mcp_asgi.py`) on the platform host; it serves the MCP tools
above. How to start the host and send a request: `docs/how-to/reach-a-station-mcp-endpoint.md`. The query plane's
`duckdb-server` face (`python -m pyforge.atlas.query_plane_boot`) is a data face, not an agent face.

## Hook registration

`pyproject.toml` registers five entry points on the `pyforge.core.hooks` group, each a thin wrapper over a live Kedro
hook backend:

| Entry point | Object |
|---|---|
| `atlas-catalog-ttl` | `pyforge.atlas.cap18:CatalogTtlPlugin` |
| `atlas-pipeline-observability` | `pyforge.atlas.cap18:PipelineObservabilityPlugin` |
| `atlas-node-observability` | `pyforge.atlas.cap18:NodeObservabilityPlugin` |
| `atlas-node-validation` | `pyforge.atlas.cap18:NodeValidationPlugin` |
| `atlas-pipeline-admission` | `pyforge.atlas.cap18:PipelineAdmissionPlugin` |

`cap18.py` is named for spec-pyforge-unifying-strategy:CAP-18 (one hook-spec and plugin-registration shape), not
for this Spec's own CAP-18, a retired satellite. Kedro stays the runtime: `settings.HOOKS` and the `@hook_impl`
backends are unchanged, and the hook specs are named `pyforge.atlas.catalog`, `pyforge.atlas.pipeline` and
`pyforge.atlas.node` (hook names, not flag keys).

## The one cross-station import

`pipelines/universal_sbom/gate.py` imports `pyforge.warden` lazily inside its nodes (the `ComplianceReport` schema
and `pyforge.warden.verdict`'s exit projection), through the optional `gate` extra (`pyproject.toml`
`[project.optional-dependencies] gate = ["pyforge-warden"]`). Without the extra the gate node fails with an install
hint and everything else runs. No other station is imported, and warden imports nothing of atlas.

## The data root

Four places resolve the data root from `PYFORGE_ATLAS_DATA_ROOT`, each with `data` as the default and a relative
value anchored at the member (the catalog's paths resolve against the working directory, which `pyforge atlas` sets
to the member); they differ in what counts as blank:

| Resolver | Blank handling |
|---|---|
| `conf/base/globals.yml` `paths.data_root` (`${env_or:PYFORGE_ATLAS_DATA_ROOT,data}`, through `settings._env_or`) | an empty value is unset; whitespace passes through unstripped |
| `admission._data_root` | empty or whitespace-only is unset (stripped); a relative value is anchored at the project the run resolves |
| `dashboard/data.default_data_root` | empty or whitespace-only is unset (stripped); the member when it holds `conf/base/catalog.yml`, else the working directory |
| `tools/bootstrap._resolve_data_root` | an empty value is unset; whitespace is not stripped |

The admission locks sit beside the data root (`<data root>.locks`) unless `PYFORGE_ATLAS_LOCK_ROOT` moves them. The
query plane's default file, `data/plane/atlas.duckdb` under the member, does not follow the data root.

## Reads outside the package

| What | Where the package reads it | How |
|---|---|---|
| The conda-forge-expert seeds | `conf/base/catalog.yml` `seed_lts_registry`, `seed_cwe_categories`, `seed_spdx_schema` | `${globals:paths.seed_root}`: `PYFORGE_ATLAS_SEED_ROOT`, default the repository's `.claude/skills/conda-forge-expert/data` |
| The conda-forge-expert scripts | `dashboard/scan_submit.py` | `pixi run -e pyforge-guild python .claude/scripts/conda-forge-expert/env_inspect.py …` for the `env-inspect` page, and the `scan-project` task in the `vuln-db` env for the `scan-project` page, both through `pyforge.core.process.PosixProcess` |
| The `vuln-db` env | `datasets/refresh.py` (the vdb store, with live public sources on) | `pixi run --frozen -e vuln-db env VDB_HOME=… VDB_CACHE=… …` from the nearest directory above the package holding a `pixi.toml` (an injected project root overrides it): the vdb refresh and `python -I datasets/vdb_extract.py` (`age`, `extract`) |
| The legacy `cf_atlas.db` | no package module after Story 48.3 | read only by the credentialed parity comparator under `tests/unit/parity/` (`parity_runner.py`, `capture_fixtures.py`); `live-sources.md`'s parity floors are taken against it, on A only |
| The `recipes/` tree | `conf/base/catalog.yml` `discovery_local_recipes_raw`, `discovery_recipe_extras_raw` | `${globals:paths.local_recipes_dir}`: `PYFORGE_ATLAS_LOCAL_RECIPES_DIR`, default the repository's `recipes/` |
| The planning tree | `dashboard/factory_status.py` | walks up from the module to the first directory holding `.git` or `_bmad-output`, then reads `_bmad-output/projects/pyforge-atlas/implementation-artifacts/sprint-status.yaml` and `_bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md` |
| The flag tree | every flag read | `src/platform/config/flags.json` and `src/platform/config/flag-overlays.json`, through `pyforge.core.flags` |
| The Pages staging tree | `tools/normalize_viz_build.py`, `tools/viz_manifest.py`, `tools/vizro_static_export.py` | the repository root is the first ancestor holding `docs/dashboard/README.md`; `tools/normalize_viz_build.py` rewrites the build under `src/shared/packages/pyforge-atlas/build` (that literal member path is its anchor), which `viz-publish-stage` copies to `docs/dashboard/kedro-viz`; the Vizro boards stage at `docs/dashboard/vizro` |

The recipes repository slug lives in two places: `datasets/identity_sources.py`
(`PYFORGE_ATLAS_LOCAL_RECIPES_REPO_SLUG`, default `rxm7706/local-recipes`, building
`https://github.com/<slug>/tree/main/recipes/<dir>`) and
`pipelines/derived_artifacts/identity_export_contract.py` (the `Local_Recipes_URL` column's description, the literal
`github.com/rxm7706/local-recipes/tree/main/recipes/{dir}`).

## Lineage producer

`observability.PRODUCER`, stamped on every OpenLineage facet and event, is exactly
`https://github.com/rxm7706/local-recipes/tree/main/pyforge-atlas`: a path that does not exist (the package lives at
`src/shared/packages/pyforge-atlas`). Deferred row DW-atlas-46-1-7. The default OpenLineage namespace is `cf_atlas`.
