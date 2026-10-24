# `semantic_packages` pipeline

Named, downstream-only Kedro pipeline (Story 20.3, CAP-6 / `query-plane-catalog` ruling,
2026-08-26). Composes the `semantic_packages` primary store that `build_packages_model`
(`semantic/models.py`) binds to, from the sealed `core` + `vcs_health` pipelines' own
already-produced catalog outputs and (Story 38.1) `derived_artifacts`' `derived_release_cadence`
and `derived_graph_archived_feedstocks`. Zero diff inside those sealed pipelines; this package only
reads their outputs by catalog dataset name.

## Operational precondition (fresh checkout)

In a fresh checkout, none of `data/`'s Parquet outputs exist yet. To materialize the
dashboard-bound stores, run, in order:

```
pyforge atlas run --pipelines core
pyforge atlas run --pipelines vcs_health
pyforge atlas run --pipelines derived_artifacts,semantic_packages
```

`semantic_packages` and `derived_artifacts` read each other's outputs (the release cadence in;
find-alternative's scorer reads `semantic_packages`), so neither runs alone on a fresh data root;
run them together, as above, or run the default pipeline.

Running `core` alone is also what makes `core_feedstock_health` stop being absent in a fresh
checkout (the gap the 2026-08-26 first `dashboard-serve` visual pass found) — `core` already
produces that Parquet directly; this pipeline does not touch it. Until these runs happen, the
dashboard pages that bind to `semantic_packages` degrade honestly to empty (never fabricated),
via `dashboard/data.py`'s existing `_bsl_query_or_empty` seam.
