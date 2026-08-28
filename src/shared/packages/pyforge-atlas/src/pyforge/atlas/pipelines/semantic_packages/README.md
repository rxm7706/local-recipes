# `semantic_packages` pipeline

Named, downstream-only Kedro pipeline (Story 20.3, CAP-6 / `query-plane-catalog` ruling,
2026-08-26). Composes the `semantic_packages` primary store that `build_packages_model`
(`semantic/models.py`) binds to, from the sealed `core` + `vcs_health` pipelines' own
already-produced catalog outputs. Zero diff inside those sealed pipelines; this package only
reads their outputs by catalog dataset name.

## Operational precondition (fresh checkout)

In a fresh checkout, none of `data/`'s Parquet outputs exist yet. To materialize the
dashboard-bound stores, run, in order:

```
kedro run --pipeline core
kedro run --pipeline vcs_health
kedro run --pipeline semantic_packages
```

Running `core` alone is also what makes `core_feedstock_health` stop being absent in a fresh
checkout (the gap the 2026-08-26 first `dashboard-serve` visual pass found) — `core` already
produces that Parquet directly; this pipeline does not touch it. Until these runs happen, the
dashboard pages that bind to `semantic_packages` degrade honestly to empty (never fabricated),
via `dashboard/data.py`'s existing `_bsl_query_or_empty` seam.
