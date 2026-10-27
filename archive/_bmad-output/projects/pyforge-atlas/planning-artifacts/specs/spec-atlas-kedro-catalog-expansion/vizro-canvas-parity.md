# Vizro parity with identity canvases (CAP-7 / Epic 22)

Companion to `SPEC.md`. **Vizro can become a parallel replacement** for the
three Cursor Canvas identity views — this was deferred from Epic 21 for scope,
not because Vizro cannot do it.

## North star

Run **one browser operator surface** (`dashboard-serve`) that matches the three
`.canvas.tsx` generators well enough to **deprecate** them after a parallel
proving period:

| Cursor Canvas today | Vizro parity page (proposed) | Generator today |
|---------------------|------------------------------|-----------------|
| `identity-2026-08-20.canvas.tsx` (catalog) | `identity-catalog` | `priority.py::write_canvas` |
| `identity-ops.canvas.tsx` (Priority/Issues/Builds/Census) | `identity-ops` | `openteams_identity_dashboards.py::write_ops_canvas` |
| `jfrog-workbook.canvas.tsx` (Artifactory map) | `identity-workbook` | `openteams_identity_dashboards.py::write_workbook_canvas` |

Canvases and Vizro run **in parallel** until parity tests pass; then canvas
writers become optional/deprecated — not deleted in v1 of this track.

## What Epic 21 already enables

- `identity_export_parquet` — identity join columns (no ranking)
- `--live-catalog` verification Parquet
- Optional 21.9 health pages (subset, not parity)

## Deferred inputs (Epic 21 → Epic 23 bridge)

Until **Epic 23.5** lands, these stay outside Atlas Kedro nodes; Vizro Epic 22
reads **quartet-written** Parquet. After 23.5, read **`identity_complete_export.parquet` only**.

| Input | Epic 21–19 bridge | Epic 23 closure |
|-------|-------------------|-----------------|
| Ranking columns | quartet `identity_ranked_export.parquet` (22.1) | Kedro `identity_complete_export` (23.5) |
| Enterprise JFROG telemetry | workbook / inventory overlay | `enterprise_jfrog_consumption.parquet` (23.2) |
| Gist YAML rules | `openteams_identity_dashboards.py` | BSL aggregates (23.6 / CAP-8d) |
| UX port | defer after numeric parity | Epic 22.2–19.3 |

**Principle:** Vizro loaders stay BSL read-only. Epic 23 eliminates quartet data merges;
Epic 22.1 is a **bridge** superseded by 23.5.

## Phased stories (Epic 22)

### 22.1 — Ranked export contract (bridge until Epic 23.5)

- **Bridge (pre-23.5):** After `priority.py`, quartet writes
  `identity_ranked_export.parquet` for Vizro 19.2–19.4.
- **Steady state (post-23.5):** Vizro reads `identity_complete_export.parquet`
  only — **22.1 superseded** by `complete-export-contract.md` §4.

### 22.2 — Vizro `identity-catalog` (parallel to catalog canvas)

- BSL page: searchable table over `identity_ranked_export.parquet`.
- Parity test: row count + sample of `P`/`Work`/`Core_Python_Package_Name` vs
  embedded DATA blob from `write_canvas` on same fixture run.
- **Defers:** pixel-perfect UX, Cursor panel integration.

### 22.3 — Vizro `identity-ops` (parallel to ops canvas)

- Four sections: Priority, Issues, Builds, Census — same aggregates as
  `write_ops_canvas` / gist ops markdown.
- Parity test: pane totals vs canvas JSON on fixture corpus.
- **Defers:** exact Cursor component behavior.

### 22.4 — Vizro `identity-workbook` (parallel to workbook canvas)

- Artifactory / consumption map over ranked export + enterprise overlay Parquet.
- **Defers until enterprise export exists:** full workbook canvas parity; ship
  honest empty shell + callout when JFROG Parquet absent.

### 22.5 — Side-by-side parity gate

- Offline test: bootstrap + priority fixture → canvas writers + Vizro loaders →
  compare key metrics (document tolerance: exact row keys, approximate layout N/A).
- CI: extend `dashboard-dryrun` for three parity pages.

### 22.6 — Canvas deprecation switch (deferred)

- Env flag `INVENTORY_IDENTITY_UI=vizro|canvas|both` (default `both`).
- When `vizro` and parity gate green for N releases, remove default canvas paths.
- **Defers:** gist-only workflow changes (CAP-7d).

### CAP-7d — Gist handoff (superseded by CAP-8d / Epic 23.6)

See `complete-export-contract.md` §5. CAP-7d remains the Epic 22-era name; Epic 23.6
is the closure story.

## Non-goals (CAP-7)

- Removing gist publish before CAP-7d.
- Moving ranking rules into Kedro nodes **during Epic 21–19** — Epic 23.3 ports them.
- Moving OpenTeams issue creation into Vizro.
- Replacing Cursor Canvas during Epic 21 or before 22.5 parity gate.

## Success signal (CAP-7)

Operator runs `priority.py` then `dashboard-serve`: three Vizro pages show the
same ranked universe and pane totals as the three `.canvas.tsx` files on a shared
fixture; parity gate passes; canvases can stay on `both` until the operator
chooses deprecation.
