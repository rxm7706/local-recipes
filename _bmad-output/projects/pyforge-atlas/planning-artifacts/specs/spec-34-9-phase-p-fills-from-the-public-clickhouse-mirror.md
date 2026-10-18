---
title: "34.9: Phase P fills from the public ClickHouse mirror"
type: 'feature'
created: '2026-10-18'
status: 'done'
baseline_revision: 'bde97f7f80'
flag:
  key: pyforge.atlas.live_public_sources          # shared with Stories 34.4 (registered it), 34.5, 34.6 and 34.8
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: on, dev: on}   # unchanged from 34.4
  scope: global                                   # v1 is global only
  fallback: 'the ClickHouse dataset serves its last-good frame (empty on a fresh root) and fetches nothing; pypi_downloads_monthly is then empty, as before'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 2
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/live-sources.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-34-4-the-download-tables-fill-from-anaconda-s-monthly-parquet.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/public_sources.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/clickhouse_downloads.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/request_datasets.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/pypi_intelligence/nodes.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `pypi_downloads_monthly` held 0 rows after the unattended refresh of 2026-10-17.

- Its only source was `PyPIBigQueryDownloadsDataset`. Its default catalog load yields an empty frame, and the
  operator ruled BigQuery off (2026-10-17).
- **Legacy reference:** legacy Phase P's default source is ClickHouse's public PyPI mirror, clickpy
  (`_phase_p_clickhouse`, CFA:7399). It is one query for the top 1,000 projects by downloads over
  `[today - 90, today)`, with PEP 503 names. On 2026-10-18 it wrote 1,000 rows; 39 older rows from 2026-08-29
  remain in `cf_atlas.db`.
- **The mirror's limits**, measured 2026-10-18:
  - The `play` user caps every result at 1,000 rows (`max_result_rows = 1000`, `result_overflow_mode = break`).
  - It is read-only, so it answers queries over GET.
  - `pypi.pypi_downloads_per_month` holds `(month Date, project String, count Int64)`.
  - Errors arrive as HTTP 500 with a `{"exception": ...}` body.

**Approach:**
1. **A new dataset, `PyPIClickHouseDownloadsDataset`** (`datasets/clickhouse_downloads.py`), behind
   `pyforge.atlas.live_public_sources`. It makes small read-only GETs, in sequence, through a composed `APIDataset`,
   with `public_sources.request_args`: a 60 s timeout and no `~/.netrc` credential.
   1. **The server's `today()`.** It pins every later query to one window.
   2. **The ranking.** The top `top_n` projects (default 1,000) by `sum(count)` over `[today - 90, today)`, ordered
      by downloads. This is legacy's ranking; `project` as a tiebreak is new, so paging is deterministic. Each query
      returns one page of at most 1,000 rows.
   3. **The months.** Those projects' downloads per calendar month over the `months` complete months before
      today's month (default 3), from `pypi_downloads_per_month`. Names go in batches of `1000 // months`, so a
      batch's rows stay under the cap.
2. **Rows.** Each row is `pypi_name` (PEP 503; names that collide are summed, as legacy does), `month`
   (`YYYY-MM`) and `downloads`.
3. **Persistence.** Last-good is kept at `<filepath>/downloads.parquet` beside the AD-13 marker.
4. **Failures.** These keep last-good under the marker and never raise:
   - an HTTP error (for an HTTP 500, the marker carries the server's `{"exception": ...}` text, which
     `raise_for_status` would drop);
   - a non-JSON line, or a streamed `{"exception": ...}` object;
   - a date that is not a date;
   - an empty ranking, or no monthly rows.
5. **Flag off:** last-good is served and nothing is requested.
6. **Source selection is in the pure node.** `fetch_pypi_downloads(pypi_clickhouse_downloads_raw,
   pypi_bigquery_downloads_raw)`:
   - BigQuery rows win when present. The attended, credentialed path covers every project, and the default
     catalog load yields none.
   - Otherwise ClickHouse's rows stand.
   - A new `downloads_source` column names the source with legacy's labels, `clickhouse-clickpy` or
     `bigquery-incremental` (CFA:7543, CFA:7803).
   - Provenance reads the dataset's marker and last-good, as it does for Story 34.4's S3 dataset.
   - `PHASE_P_ENABLED=1` alone no longer fails the run. Legacy routes it to ClickHouse unless `PHASE_P_SOURCE`
     is `bigquery` (CFA:7387). The BigQuery stub raises its "attended credentialed run" error only when both are
     set. A shell that exports `PHASE_P_ENABLED=1` for legacy therefore leaves ClickHouse's rows standing.
7. **A new override point, `CLICKHOUSE_PYPI_BASE_URL`** (`extra_overrides`; legacy's own is
   `PHASE_P_CH_BASE_URL`). The env-override surface goes from 42 to 43.

**Deviations, recorded:**
- **Opt-in gate.** Legacy runs even ClickHouse only under `PHASE_P_ENABLED=1`. Here the ClickHouse path runs
  whenever the flag is on, per AD-6's 2026-10-18 amendment and the operator's ruling (public sources fetch in a
  plain run). `PHASE_P_ENABLED` remains BigQuery's gate.
- **Legacy's other Phase P switches.** Legacy skips Phase P for a `PHASE_P_SOURCE` it does not recognise, and
  for `PHASE_P_DISABLED=1`. Here ClickHouse's rows stand in both cases; the flag is the ClickHouse switch.
- **Dagster schedule.** Phase P stays its own unscheduled job (AD-6, "never a default schedule"); a plain
  `kedro run` fills it.
- **Monthly shape.** The output keeps `pypi_downloads_monthly`'s calendar-month shape rather than legacy's rolling
  `downloads_30d` / `downloads_90d` columns. No atlas node reads those columns yet.

Ledger key: `34-9-phase-p-fills-from-the-public-clickhouse-mirror`.
Type / Effort / Deps: feature / S / Story 34.2 (done), Story 34.4 (`public_sources`).

### Living CAP citations

- **`spec-pyforge-atlas` CAP-64** (`live-sources.md`, the ClickHouse row): a feature behind
  `pyforge.atlas.live_public_sources`.
- **AD-2** (dataset-owned IO over a composed `APIDataset`), **AD-6** (Phase P, amended 2026-10-18), **AD-13**,
  **AD-11** (every test's responses are built in memory; the suite pins the flag off).
- **Origin.** Dream entry 2026-10-18 (atlas fills its own data); operator ruling 2026-10-18, extras: Phase P via
  ClickHouse.

## Acceptance Criteria

- **AC1 — The fetch.** Flag on, the dataset requests today, then the ranking over legacy's window (pinned to the
  server's date, ordered by downloads then project), then the complete months, as read-only GETs with no
  credential. It pages the ranking under the cap and stops on a short page, and batches names so each batch stays
  under the cap. Names are PEP 503, collisions are summed, `UInt64` arrives quoted, and a quote in a name is
  escaped.
- **AC2 — AD-13.** Each failure kind keeps last-good under a marker that names it, an HTTP 500's server
  exception included. No monthly rows writes no last-good. A clean refresh clears an earlier marker. Provenance
  reports a fresh fetch, the marker, or the copy as it stood. A file where the store belongs never raises.
- **AC3 — The flag, read at the load.** A dataset built while the flag was on fetches only if the flag is on at
  the load. Off, it serves last-good untouched with no marker. Tested with `flag_states`.
- **AC4 — Source selection.** BigQuery rows win; otherwise ClickHouse's; neither gives the full columns, empty.
  `downloads_source` names the source on every row with legacy's labels. `PHASE_P_ENABLED=1` alone leaves
  ClickHouse's rows standing; with `PHASE_P_SOURCE=bigquery` the stub still demands the attended run.
- **AC5 — Live.** `pypi_downloads_monthly` holds the top 1,000 projects × 3 months, and its project set equals
  legacy Phase P's current 1,000 rows (tolerance: 100% of today's set). No BigQuery call is made.
- **AC6 — Gates.** `pyforge-atlas-test`, `kedro-test`, `kedro-catalog-check`, the coverage gate, `lint-types`
  (and mypy in `pyforge-foundry-full`), `flag-gate-check`; governing Specs reconciled and stamped scoped.

## Verification

- Unit, each named from the repo root:
  - `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_clickhouse_downloads.py`: the fetch, every failure
    kind, the node's source selection, and the two-state test spelled with
    `@flag_states("pyforge.atlas.live_public_sources")`.
  - `src/shared/packages/pyforge-atlas/tests/unit/pipelines/pypi_intelligence/test_nodes.py`: the node's
    idempotency and no-op.
  - `src/shared/packages/pyforge-atlas/tests/unit/catalog/test_override_points.py` and
    `src/shared/packages/pyforge-atlas/tests/unit/catalog/test_catalog_resolution.py`: the override surface (43)
    and the entry counts (129; `pypi_intelligence` 22).
  - `src/shared/packages/pyforge-atlas/tests/unit/parity/test_parity_pypi_intelligence.py`: the shape-only seed,
    now with both inputs.
- Live, recorded 2026-10-18: a scratch copy of the 2026-10-17 data root, flag on (dev),
  `--pipelines pypi_intelligence --nodes fetch_pypi_downloads`.
  - **The first run failed under the marker.** The marker said HTTP 500 and nothing more. Replaying the query by
    hand gave the cause: the alias `month` shadowed the column in `WHERE` (ClickHouse code 386, `NO_COMMON_TYPE`).
    The alias is now `month_start`, and since review round 1 the marker carries the server's exception text. The
    in-memory stand-in cannot catch a semantic SQL error; the live run is what does.
  - **Second run:** exit 0, 6.2 s, peak RSS 0.27 GB, no marker.
  - **After review round 1, with `PHASE_P_ENABLED=1` exported:** exit 0, 4.5 s, the same 3,000 rows, no marker.
  - **`pypi_downloads_monthly`:** 0 → 3,000 rows, 1,000 projects × `2026-07`, `2026-08` and `2026-09`, all
    `clickhouse-clickpy`.
  - **Against legacy `cf_atlas.db`:**
    - Legacy fetched 1,000 rows on 2026-10-18, and atlas holds the same 1,000 projects. Legacy's 39 other rows
      date from 2026-08-29.
    - Atlas's three-month sum to legacy's rolling `downloads_90d`, per project: median 1.063, range 0.73–1.78.
      Calendar months July–September are 92 days, not legacy's 90-day window ending yesterday.
    - Spearman rank correlation 0.993.

## Boundaries & Constraints

**Never:** a credential on the mirror; a BigQuery call on the default path; an HTTP client import in the
package; a test that touches the network; a write to the mirror (the `play` user is read-only).

**Residual risk:**
- **Single-vendor mirror.** If ClickHouse stops hosting clickpy, the dataset keeps last-good under the marker;
  BigQuery is the full-coverage fallback, attended.
- **Coverage is the top 1,000**, as legacy's default. `top_n` pages past 1,000; legacy measured HTTP 500s above
  about four concurrent queries, and these queries run one at a time.
- **The mirror lags about a day,** and the current month is never read. On the 1st of a month the lag leaves the
  previous month, read as complete, one day short.
- **The `play` user reads at most 10 billion rows a query** (`max_rows_to_read`, `read_overflow_mode = break`,
  read-only, so it cannot be raised). The ranking reads about 1.1 billion today. If the per-day table grew about
  nine-fold, the ranking would truncate silently.
- **The generated kedro-viz prototype** (`src/prototype/packages/pyforge-atlas-kedro-viz/`) still shows the
  node's single input. It has been stale since 2026-07-18, and no gate reads it.
- **A new project with no complete month** ranks but has no monthly rows.
- **netrc on a redirect:** a redirect to another host still consults `~/.netrc` for that host. The mirror does
  not redirect today.

## I/O & Edge-Case Matrix

| Situation | Before | After |
|---|---|---|
| Live run, flag on | `pypi_downloads_monthly` empty | 3,000 rows, `clickhouse-clickpy` |
| Flag off | empty | last-good served, nothing requested |
| The mirror errors or streams an exception | — | last-good kept, marker names it |
| An attended BigQuery run supplies rows | BigQuery rows | BigQuery rows win, `downloads_source = bigquery-incremental` |
| `PHASE_P_ENABLED=1` exported for legacy | the run fails | ClickHouse's rows stand |
| `PHASE_P_ENABLED=1` and `PHASE_P_SOURCE=bigquery` | the run fails | unchanged: the attended run is required |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-64 (FR-72), a feature.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, 2026-10-18 (atlas fills its own data); operator
  ruling 2026-10-18 (extras: Phase P via ClickHouse).
- Epic 34 / Story 34.9 in `planning-artifacts/epics.md`.
- Flag: `pyforge.atlas.live_public_sources` (`feature-flag-governance:CAP-1`), registered by Story 34.4.

## Spec Change Log

- 2026-10-18: written with the implementation (branch `atlas-34-9-clickhouse-phase-p`, cut from `main` at
  `bde97f7f80`).
- 2026-10-18: independent review round 1 FAIL: 1 blocker, 4 should-fix, 7 nits; 48 mutants, 9 survived. No
  code-correctness blocker.
  - **B1, two false claims in this spec.**
    - The BigQuery label is now legacy's `bigquery-incremental`.
    - The first live run's marker did not name the cause; the sentence is corrected, and S2 now makes it true.
  - **Should-fix:**
    - **S1:** provenance reads the dataset, with 34.4's two provenance tests ported.
    - **S2:** an HTTP 500's `{"exception": ...}` body reaches the marker.
    - **S3:** `PHASE_P_ENABLED=1` alone no longer fails the run (legacy's dispatch), pinned both ways.
    - **S4:** `RESULT_CAP` and the 333-name batch are pinned.
  - **Nits:**
    - **N1:** the redundant `mkdir` is gone; a file at the store path never raises.
    - **N2:** each defensive branch has a test.
    - **N3:** two residual risks are added.
    - **N4:** the tiebreak is named as new.
    - **N5:** a URL with a query string is refused.
    - **N6:** epics.md and the ledger are promoted at landing.
    - **N7:** the kedro-viz prototype is recorded as a residual risk.
- 2026-10-18: re-review round 2 PASS. All gates exit 0; 59 mutants, 57 killed. Every round-1 finding was tested,
  not taken from this log, and the spec-surface stamp was checked against the tree. Its nits were fixed:
  - **N1:** the BigQuery stub's docstring, the catalog comment and `tools/bootstrap.py` now name
    `PHASE_P_SOURCE=bigquery`.
  - **N2:** legacy's other Phase P switches are added to Deviations.
  - **N3:** a 500 body that starts with `{` but is not JSON, and a `PHASE_P_SOURCE` with surrounding space, are
    tested.
  - **N4:** the misleading test parameter is trimmed.
  Promoted to `done`.
