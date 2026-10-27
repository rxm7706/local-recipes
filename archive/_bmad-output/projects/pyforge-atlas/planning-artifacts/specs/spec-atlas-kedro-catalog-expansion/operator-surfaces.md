# Operator surfaces — Vizro follow-on + Kedro-Viz CI

Companion to `SPEC.md`. Stories **21.1–21.8** deliver the data plane only.
Stories **21.9–21.10** are optional follow-ons for a single operator surface
around the independent bootstrap.

## Epic 21 core (21.1–21.8) — no new Vizro

Success does **not** require new dashboard pages. Operators use:

- `pixi run pyforge-atlas-bootstrap`
- `metrics.py --live-catalog`
- `parity-diff` / `bsl-metric-check`
- Existing Kedro-Viz (updates passively when pipeline stories land)

## Story 21.9 — Vizro pages (optional follow-on, CAP-5)

Add **three** BSL-grounded pages to `pyforge.atlas.dashboard` (same patterns as
Story 23.5 — `PageDef` + `semantic/models.py` + `dashboard.data` loaders).
**BSL measures only** — read Parquet under `PYFORGE_ATLAS_DATA_ROOT`; no new
fetch logic in dashboard code.

| Page id | Title | Primary Parquet / sources | Operator question answered |
|---------|-------|---------------------------|----------------------------|
| `bootstrap-index-health` | Bootstrap index health | Tier 0/1 raw + derived catalog outputs | Did bootstrap materialize indexes? Row counts vs scale floors? Staleness markers? |
| `identity-export-snapshot` | Identity export snapshot | `identity_export_parquet` | Associator vs inventory-derived vs unmapped counts; `primary_purl` / `OpenTeams_Issue_URL` coverage |
| `live-catalog-coverage` | Live catalog coverage | Verification-matrix datasets (PyPI, CF, Basilisk, AOSS, Anaconda, cross-channel) | Aggregate BOOL coverage aligned with `verification-matrix.md` |

### Constraints (21.9)

- Pages degrade to empty/honest shell when Parquet absent (existing DW-D2-2 pattern).
- **No** ranking columns (`P`/`Score`/`Work`) — those stay gist/quartet.
- **No** replacement of inventory `.canvas.tsx` generators.
- `dashboard-dryrun` gate extended: assert three new `PageDef` entries + stable ids.
- Register pages in `PAGE_INVENTORY` / `build_dashboard()` per Story 23.5 precedent.

### Success (21.9)

`pixi run -e local-recipes dashboard-serve` shows the three pages with non-empty
tables after a green bootstrap; row-count widgets match scale sanity gates from
`catalog-sources.md`.

## Story 21.10 — Kedro-Viz CI path sync (optional follow-on, CAP-6)

Today `.github/workflows/kedro-viz-publish.yml` triggers only on:

```yaml
paths:
  - 'src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/**'
```

Catalog-only changes (new datasets in `catalog.yml`, new dataset classes) can
merge without republishing the static DAG export.

### Change

Extend `paths` to include:

```yaml
  - 'src/shared/packages/pyforge-atlas/conf/base/catalog.yml'
  - 'src/shared/packages/pyforge-atlas/conf/base/globals.yml'
  - 'src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/**'
```

Optional: document `regenerate-kedro-viz-proto` in bootstrap operator runbook when
working locally without pushing pipeline files.

### Success (21.10)

A PR touching only `catalog.yml` + a new dataset class triggers
`kedro-viz-publish` on merge to `main`; `docs/dashboard/kedro-viz/` reflects new
dataset nodes without a manual publish step.

## Operator surface map (after 18.8 + optional 21.9–21.10)

| Need | Surface | Story |
|------|---------|-------|
| Pipeline DAG | Kedro-Viz (Pages) | passive 18.x; CI 21.10 |
| Index row counts / staleness | Vizro `bootstrap-index-health` | 21.9 |
| Identity join quality | Vizro `identity-export-snapshot` | 21.9 |
| Verification BOOL summary | Vizro `live-catalog-coverage` | 21.9 |
| Priority / OpenTeams ranking | Gist + `.canvas.tsx` → Epic 22 Vizro; data from **23.5** complete export | 18.x bridge; 23.5 steady state |
| Enterprise JFROG workbook | `enterprise_jfrog_consumption.parquet` | Epic 23.2 |
| Factory fleet analytics | Existing 28 Vizro pages | unchanged |

## Epic 23 — Complete export, zero deferred (CAP-8)

See **`complete-export-contract.md`**. Enterprise builds **`enterprise_jfrog_consumption.parquet`**
(§1) as the live Artifactory handoff; **`identity_complete_export.parquet`** (§4) is the
single consumer surface for Vizro, gist, and `--live-catalog`.

| Story | Deliverable |
|-------|-------------|
| 23.1 | Tier 3 OS bulk indexes |
| 23.2 | **Enterprise JFROG consumption Parquet** |
| 23.3 | Priority rules in Kedro |
| 23.4 | Deliverable A + candidate status |
| 23.5 | **`identity_complete_export.parquet`** |
| 23.6 | BSL gist aggregates (CAP-8d) |
| 23.7 | E2E zero-deferred gate |

## Epic 22 — Vizro canvas parity (CAP-7)

See **`vizro-canvas-parity.md`**. Vizro **can** replace the three Cursor canvases
in parallel; ranking + enterprise + gist + UX port are **deferred slices**, not
capability blockers.

| Story | Deliverable | Deferred if not ready |
|-------|-------------|------------------------|
| 22.1 | `identity_ranked_export.parquet` from quartet | — |
| 19.2 | Vizro `identity-catalog` | UX polish |
| 19.3 | Vizro `identity-ops` | UX polish |
| 19.4 | Vizro `identity-workbook` | enterprise JFROG Parquet → empty shell OK |
| 22.5 | Parity gate vs canvas DATA blobs | — |
| 22.6 | Canvas deprecation switch (`both` default) | until 22.5 green |
| CAP-7d | Gist markdown from BSL aggregates | entire slice deferred |
