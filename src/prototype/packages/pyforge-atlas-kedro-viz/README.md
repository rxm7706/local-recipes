# pyforge-atlas-kedro-viz — kedro-viz DAG mirror of pyforge-atlas

A **dependency-free Kedro project that mirrors the _shape_ of the shipped
`pyforge-atlas` DAG** (`src/shared/packages/pyforge-atlas`) so it can be explored
with `kedro viz` and smoke-run with `kedro run` **without installing
pyforge-atlas's heavy stack** (pandas, DuckDB, Dagster, Vizro, …). Every node is
a stub passthrough and every dataset is a `MemoryDataset`; the value is the DAG
structure — pipeline grouping, node names, dataset flow, and storage layers.

It is **generated, not hand-maintained**: `tools/regenerate_from_atlas.py`
statically parses (AST — no imports, so none of pyforge-atlas's deps are needed)
each real `pyforge-atlas/.../pipelines/<name>/pipeline.py` `create_pipeline()`
and emits the matching stub pipelines + catalog + registry here. Re-run it
whenever pyforge-atlas changes so the viz never drifts.

## Regenerate + run

```bash
pixi run -e local-recipes regenerate-kedro-viz-proto   # re-mirror from pyforge-atlas
pixi run -e local-recipes kedro-run-proto              # <1 s smoke run (77 stub tasks)
pixi run -e local-recipes kedro-viz-proto              # interactive DAG in the browser
# static SPA export: `cd` here, then `kedro viz build`  (build/ is gitignored)
```

Both `kedro` and `kedro-viz` are already in the `local-recipes` pixi env.

## The DAG (mirrors pyforge-atlas — 77 nodes across 7 pipelines)

| Pipeline | Nodes | What it mirrors in pyforge-atlas |
|---|---|---|
| `core` | 13 | conda-forge enumeration + dependency graph / feedstock health / downloads |
| `vcs_health` | 19 | VCS & feedstock health signals |
| `pypi_intelligence` | 15 | PyPI intelligence + the recommend chain |
| `vulnerability` | 14 | KEV / EPSS / CWE feeds + advisory matching |
| `seed_gaps` | 9 | read-only seed-freshness gap reports |
| `universal_sbom` | 6 | purl export, universe SBOM, inventory-match |
| `derived_artifacts` | 1 | regenerated downstream artifacts |

Node counts include the zero-input **extraction** stubs the generator adds for
each free/raw input so `kedro run` executes end-to-end on MemoryDatasets.

Dataset **layers** (the kedro-viz left rail) are copied from the real
`pyforge-atlas` catalog's `kedro-viz.layer` metadata (`raw` API feeds → `atlas`
compute → `views` → `derived`), falling back to a dataset-name heuristic.

## What it is NOT

- **Not pyforge-atlas.** The real ported logic lives in
  `src/shared/packages/pyforge-atlas`; this is only a viz/docs stub of its shape.
- **No IO.** Every dataset is a `MemoryDataset` — no DB, network, or DuckDB.
- **The outputs are machine-authored.** `pipelines/*.py`, `pipeline_registry.py`,
  `conf/base/catalog.yml`, and `conf/base/parameters.yml` are emitted by the
  generator — edit `tools/regenerate_from_atlas.py`, never the outputs.
