---
sources:
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/__main__.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipeline_registry.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/tools.py
  - src/shared/packages/pyforge-atlas/tools/bootstrap.py
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/contract.md
  - src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py
verified: 2026-11-25
---

# How to run the atlas pipelines and read their datasets

Use the `pyforge atlas` CLI to build atlas's conda-forge intelligence datasets on your machine, then read them through the station's MCP tools or a Kedro shell.

## When to use this

- You have a fresh clone and atlas has no data yet.
- You changed a pipeline and want to rebuild one part of the data.
- You need to read one dataset and know how fresh it is.

## When to skip this

- You want the legacy `cf_atlas.db` that `pyforge doctor monitor` reads. That is a different store, built by the `build-cf-atlas` task; see [How to diagnose with doctor](diagnose-with-doctor.md).
- You are changing atlas's code. Read `src/shared/packages/pyforge-atlas/AGENTS.md` first; it holds the subtree's own rules.

:::note
**Prerequisites.** Run every command from the repository root. Atlas lives in its own pixi environment, `-e pyforge-atlas`; the session default `pyforge-guild` does not carry it. A pipeline run writes under the data root and may fetch public sources, so run one in your own worktree, not as a read-only check.
:::

## Steps

### 1. Check that the CLI answers

```bash
pixi run -e pyforge-atlas pyforge atlas --version    # prints pyforge-atlas <version>, loads no Kedro
pixi run -e pyforge-atlas pyforge atlas              # lists the commands, runs nothing
```

The commands are Kedro's own: `run`, `ipython` and `package`. `--version` is honoured only as the first token.

### 2. Build the data on a fresh clone

```bash
pixi run -e pyforge-atlas pyforge-atlas-bootstrap
```

The task first runs `tools/bootstrap.py` in the atlas package, which creates the store directories and an empty `conf/local/credentials.yml` stub when none exists. It then runs nine pipelines as one Kedro run: `core`, `pypi_intelligence`, `vulnerability`, `vcs_health`, `upstream_discovery`, `derived_artifacts`, `seed_gaps`, `artifactory_downloads` and `semantic_packages`. Nodes that need a credential fall back to their seeded or empty default instead of failing the run.

To write somewhere other than the package's own `data/` directory, set `PYFORGE_ATLAS_DATA_ROOT` to an absolute path first.

### 3. Run one pipeline, or several

```bash
pixi run -e pyforge-atlas pyforge atlas run --pipelines core
pixi run -e pyforge-atlas pyforge atlas run --pipelines core,vcs_health
pixi run -e pyforge-atlas pyforge atlas run                       # the whole __default__ DAG
```

`--pipelines` takes comma-separated names and sums them into one DAG. Twelve pipelines are registered: `artifactory_downloads`, `catalog_index`, `core`, `derived_artifacts`, `pypi_intelligence`, `query_plane_cache`, `seed_gaps`, `semantic_packages`, `universal_sbom`, `upstream_discovery`, `vcs_health` and `vulnerability`. Three of them are left out of `__default__` and run only when named: `catalog_index`, `query_plane_cache` and `universal_sbom` (which reads an intake file named with `--params sbom_intake_path`).

Kedro's other `run` options (`--from-nodes`, `--to-outputs`, `--tags`, `--only-missing-outputs` and the rest) are listed by `pyforge atlas run --help`.

:::note
Each command runs with the atlas package directory as its working directory. A relative path you pass to `run` (`--config`, `--conf-source`) or put in a `PYFORGE_ATLAS_*` variable resolves against that directory, not your shell's. Pass absolute paths.
:::

### 4. Refresh the dataset index

```bash
pixi run -e pyforge-atlas pyforge atlas run --pipelines catalog_index
```

`catalog_index` records every catalog entry's last write, row count, tier and status. It reads what a build wrote, so run it last and on its own.

### 5. Read a dataset

The CLI has no verb that lists or reads datasets. Use one of these:

| Way | Use it for |
| --- | --- |
| MCP tool `list_atlas_datasets` | The declared dataset names. |
| MCP tool `read_atlas_dataset` (argument `name`) | One dataset, returned with its build-provenance envelope. |
| MCP tool `list_atlas_pipelines` | The eight pipelines the MCP face can trigger. |
| `pixi run -e pyforge-atlas pyforge-atlas ipython` | A Kedro shell with `catalog`, `context`, `pipelines` and `session` loaded. |

The MCP tools are served at `POST /stations/atlas/mcp` on the platform host. [Reach a station's MCP endpoint](reach-a-station-mcp-endpoint.md) shows how to start the host and send a request.

The `pyforge` front door gives the same shell. It hands its child the terminal's own stdin, stdout and stderr, so `pyforge atlas ipython` is interactive too, and a long `pyforge atlas run` prints its log as it runs.

Dataset declarations live in `src/shared/packages/pyforge-atlas/conf/base/catalog.yml`.

### 6. Read how fresh the data is

`read_atlas_dataset` returns a `build_stamp` (and `build_stamp_newest`) in the envelope. Judge freshness from those fields, never from the time you read the data. Atlas reports the timestamps and computes no staleness verdict for you.

## What you get

Parquet and other outputs under the data root, in `<layer>/<dataset_name>/` directories, plus the stores under `stores/`. With no override, the data root is `data/` inside the atlas package directory.

## How to tell it worked

| Exit | Meaning |
| --- | --- |
| `0` | The command succeeded (also `--version`). |
| `1` | The command failed or was aborted (Click's code). |
| `2` | A usage error, or a kill-switch refusal before Kedro started. |

Read the exit code directly (`echo $?`), never through a pipe.

`run` refuses with exit `2` when the flag `pyforge.atlas.agent_pipeline_tools` is off; it stays listed in `--help`, marked disabled. Naming `universal_sbom` while `pyforge.atlas.manifest_inventory` is off refuses the same way.

## Tips

- An agent never sets `PYFORGE_ATLAS_CREDENTIALED=1`. It is the operator's per-run opt-in for fetches that carry a credential; without it those datasets keep their uncredentialed path and can stay stale.
- The MCP face triggers eight pipelines (`core`, `vcs_health`, `pypi_intelligence`, `vulnerability`, `seed_gaps`, `universal_sbom`, `derived_artifacts`, `upstream_discovery`). The other four run only from the CLI.
- Every flag, environment variable and exit code is a row of the station contract, `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/contract.md`. Where this page and the contract differ, the contract and the code win.
- For how atlas fits with the other stations, see [PyForge ecosystem architecture](../explanation/pyforge-ecosystem-architecture.md).
