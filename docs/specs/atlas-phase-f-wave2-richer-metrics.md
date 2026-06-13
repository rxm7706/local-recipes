# Tech Spec: Atlas Phase F+ Wave 2 — richer metrics from the existing parquet sweep

> **BMAD intake document.** Focused execution scope for `bmad-quick-dev`
> (Quick Flow track — well-bounded, single-skill, ~5 stories).
>
> ```
> run quick-dev — implement the intent in docs/specs/atlas-phase-f-wave2-richer-metrics.md
> ```
>
> **Parent spec** (canonical detail): [`docs/specs/atlas-phase-f-s3-backend.md`](atlas-phase-f-s3-backend.md).
> This brief is the **subset** of that spec scoped to Wave 2 (stories
> 3, 7, 8, 9, 10). Wave 1 (S3 backend + dispatcher + `downloads_source`
> provenance column) already shipped in v7.6.0; Wave 1 default-flip for
> `--profile admin` shipped in v8.17.0. Wave 3 (new operator CLIs)
> waits for Wave 2 and ships as a separate effort.
>
> **Per `CLAUDE.md` Rule 1**, any BMAD agent executing this brief MUST
> invoke the `conda-forge-expert` skill before touching atlas code.
> Per Rule 2, the effort closes with a CFE-skill retrospective and a
> `CHANGELOG.md` entry.

---

## Status

| Field | Value |
|---|---|
| Status | **Draft v1** — ready for `bmad-quick-dev` intake |
| Owner | rxm7706 |
| Track | BMAD Quick Flow (no separate PRD / architecture phase — parent spec carries those) |
| Scope | (1) Schema migration v26 → v27; (2) rolling 30/90-day downloads + trend slope; (3) per-platform + per-Python download breakdowns. All computed in one extra parquet sweep — zero new network. |
| Out of scope | Wave 3 CLIs (`platform_breakdown`, `pyver_breakdown`, `channel_split`); daily-granularity downloads; defaults-channel atlas |
| Predecessor | `atlas-phase-f-s3-backend.md` Wave 1 (shipped v7.6.0 + v8.17.0) |
| Successor | Wave 3 CLI brief (to be written when Wave 2 lands) |
| Created | 2026-06-13 |

---

## Background and Context

The Phase F S3 backend already exists. `_phase_f_via_s3` in
`scripts/conda_forge_atlas.py` reads monthly parquet files from
`anaconda-package-data.s3.amazonaws.com` and writes the
`packages.total_downloads` + `latest_version_downloads` columns. The
parquet schema is:

```
time | data_source | pkg_name | pkg_version | pkg_platform | pkg_python | counts
```

— 6 dimensions, 1 metric, ~13 MB per month, ~110 months of history available. Wave 1 consumes
3 of the 6 dimensions (`time`, `pkg_name`, `counts`) and aggregates to
`(pkg_name → total)`. The 3 unused dimensions are sitting in the byte stream.

Wave 2 adds three more aggregations on the same cached parquet bytes:

1. **Rolling-window cuts** (`time` × `counts` filtered to N trailing months) — adoption signals comparable to the `pypi_intelligence` table's `downloads_30d/90d` columns, but for the conda-forge namespace.
2. **Trend slope** (rolling-window-now vs. rolling-window-prior ratio) — direction signal: growing vs. declining.
3. **Per-platform** and **per-Python** breakdowns (`pkg_platform` / `pkg_python` group-bys) — maintainer-triage data: how much of a package's traffic is ARM64? Python 3.8? defaults? Currently this requires reading parquet at query-time; we materialize it into the atlas DB so consumer CLIs are offline-safe.

The same parquet sweep produces all three. No new HTTP calls. No new top-level dependencies.

### What's already shipped (do not re-implement)

- `_parquet_cache.py` (Wave 0 Story 2) — month-list + per-month cache + filtered reader.
- `_http.py` S3 routing with `S3_PARQUET_BASE_URL` + JFrog auth (Wave 0 Story 1).
- `_phase_f_via_s3` (Wave 1 Story 5) — current parquet aggregation that populates `total_downloads`.
- `packages.downloads_source` provenance column (Wave 1 Story 3) — already accepts `{'anaconda-api', 's3-parquet', 'merged'}`.
- `PROFILES["admin"]["PHASE_F_SOURCE"] = "s3-parquet"` (v8.17.0) — admin runs hit the parquet path by default.

### Schema target — important correction vs. parent spec

The parent spec (written 2026-05-10) assumed migration `v17 → v18`.
Current schema is **v26** (verified 2026-06-13 via
`SCHEMA_VERSION = 26` at `conda_forge_atlas.py:137`). Wave 2's migration target is
**v26 → v27**.

---

## Goals

- **G1.** Populate three new rolling-window columns on `packages`: `downloads_30d`, `downloads_90d`, `downloads_trend_90d`.
- **G2.** Populate two new lifetime-history columns on `packages`: `first_nonzero_month`, `last_nonzero_month`.
- **G3.** Materialize per-platform breakdown into a new table `package_platform_downloads`.
- **G4.** Materialize per-Python-version breakdown into a new table `package_python_downloads`.
- **G5.** All five additions computed in **one** extended parquet sweep that runs in the existing `_phase_f_via_s3` path — no extra network, no separate phase.
- **G6.** Schema migration v26 → v27 is forward-only and idempotent (same pattern as existing additions).

---

## Non-Goals

- **NG1.** No new CLIs or MCP tools — those are Wave 3, separate ship.
- **NG2.** No backfill of channels other than `conda-forge` (parent spec NG2).
- **NG3.** No daily granularity (parent spec NG1 — S3 publishes monthly only).
- **NG4.** No retro-fitting the API path. `_phase_f_via_api` continues to populate only `total_downloads` + `latest_version_downloads`; the new columns stay `NULL` when `downloads_source='anaconda-api'`. Consumers detect via `downloads_source`.
- **NG5.** No materialization of full per-(package, platform, month) time-series (38M rows). We aggregate to the cuts we need: 90-day rollup and lifetime totals. Per-month detail stays in the parquet cache, queryable on demand by Wave 3 if needed.

---

## User Stories

### Story 1 — Schema migration v26 → v27

Add columns to `packages` table:

- `downloads_30d INTEGER` — sum of `counts` over the most recent month (monthly resolution; documented as such).
- `downloads_90d INTEGER` — sum of `counts` over the last 3 months available.
- `downloads_trend_90d REAL` — `(downloads_90d - downloads_prev_90d) / downloads_prev_90d` where `downloads_prev_90d` is months 4-6 trailing. `NULL` when either window is zero (avoid div-by-zero) or fewer than 6 months of data exist. Capped at `+10.0` to dampen new-package outliers.
- `first_nonzero_month TEXT` — `'YYYY-MM'` of earliest non-zero month.
- `last_nonzero_month TEXT` — `'YYYY-MM'` of most recent non-zero month.

Add two new tables:

```sql
CREATE TABLE IF NOT EXISTS package_platform_downloads (
    conda_name        TEXT NOT NULL,
    pkg_platform      TEXT NOT NULL,
    downloads_90d     INTEGER NOT NULL,
    downloads_total   INTEGER NOT NULL,
    fetched_at        INTEGER NOT NULL,
    PRIMARY KEY (conda_name, pkg_platform)
);
CREATE INDEX IF NOT EXISTS idx_package_platform_downloads_conda_name
    ON package_platform_downloads(conda_name);

CREATE TABLE IF NOT EXISTS package_python_downloads (
    conda_name        TEXT NOT NULL,
    pkg_python        TEXT NOT NULL,
    downloads_90d     INTEGER NOT NULL,
    downloads_total   INTEGER NOT NULL,
    fetched_at        INTEGER NOT NULL,
    PRIMARY KEY (conda_name, pkg_python)
);
CREATE INDEX IF NOT EXISTS idx_package_python_downloads_conda_name
    ON package_python_downloads(conda_name);
```

Migration is forward-only and follows the existing
`_apply_pending_migrations` pattern. Bump `SCHEMA_VERSION` from 26 to 27.
Add an entry to the migrations list and update
`tests/meta/test_schema_migration.py` if it asserts on the version number.

### Story 2 — Rolling 30 / 90-day download windows + lifetime months

Extend `_phase_f_via_s3` to compute, in the same parquet pass:

- `downloads_30d` = SUM(counts) WHERE time == most-recent available month.
  Documented as "single-month resolution at monthly granularity";
  callers needing finer resolution must consult `pypi_intelligence`.
- `downloads_90d` = SUM(counts) WHERE time IN (last 3 months available).
- `first_nonzero_month` = MIN(time) WHERE counts > 0.
- `last_nonzero_month` = MAX(time) WHERE counts > 0.

All four computed in one pyarrow group-by. Bulk-update `packages` in
batches of 500 (same transaction pattern as Wave 1).

### Story 3 — 90-day trend slope

Compute `downloads_trend_90d` as
`(downloads_90d - downloads_prev_90d) / downloads_prev_90d`
where `downloads_prev_90d` = SUM(counts) over months 4-6 trailing.

- Returns `NULL` if either window has zero downloads (avoid
  ZeroDivisionError) or if fewer than 6 months of data exist for the
  package.
- Sign convention: positive = growing, negative = declining.
- Cap at `+10.0` to dampen new-package "infinite growth" outliers in
  downstream reporting.

Same parquet sweep as Story 2 — one additional aggregation, no new
reads.

### Story 4 — Per-platform breakdown

In the same parquet sweep, group by `(pkg_name, pkg_platform)` for:

- `downloads_90d` (last 3 months)
- `downloads_total` (lifetime)

Bulk-insert into `package_platform_downloads` (Story 1 table) with
`fetched_at = current Unix time`. Use `INSERT OR REPLACE` keyed on
`(conda_name, pkg_platform)`.

Filter out empty `pkg_platform` values — noarch packages have
`pkg_platform=''` in the parquet; map them to a synthetic `'noarch'`
platform string for clarity in output tables.

### Story 5 — Per-Python-version breakdown + data-quality regex

Mirror Story 4 against `pkg_python` into `package_python_downloads`.

**Data-quality filter (parent spec Story 10 caveat).** The parquet
contains dirty `pkg_python` values like `2.30`, `7.3`, `3.81`
(confirmed via inspection 2026-05-10). Drop rows where `pkg_python`
doesn't match `^(2\.7|3\.[0-9]{1,2})$`. Document the regex in code
comments so future maintainers know why it's there.

### Story 6 — Tests, docs, SKILL.md updates, CHANGELOG, retro

- **Schema migration test** (`tests/meta/test_schema_migration.py`
  or equivalent) — assert `SCHEMA_VERSION == 27`, columns exist with
  correct types, new tables exist with correct columns, indexes
  created.
- **Aggregation correctness tests** (unit) — given a known parquet
  fixture, verify per-story numbers come out right. Specifically:
  trend slope NULL on insufficient data; trend slope cap at +10.0;
  per-platform/per-python `INSERT OR REPLACE` idempotency; dirty
  `pkg_python` regex filter (e.g. `7.3` dropped, `3.11` kept).
- **Integration test** — mock parquet pull, run `_phase_f_via_s3`
  end-to-end, assert all five new columns + both new tables populated.
- **Reference doc updates** —
  `.claude/skills/conda-forge-expert/reference/atlas-phases-overview.md`
  Phase F section gains the new columns/tables and updates the
  "what gets written" bullet.
- **Actionable-intelligence catalog** —
  `.claude/skills/conda-forge-expert/reference/atlas-actionable-intelligence.md`
  gets new rows for `downloads_30d/90d`, `downloads_trend_90d`,
  per-platform/per-python tables — marked `✅ shipped (v8.<NEW>.0)`.
- **CHANGELOG.md** entry per CLAUDE.md Rule 2. MINOR bump
  (additive — new columns + new tables; no breaking).
- **CFE-skill retrospective** per CLAUDE.md Rule 2 — focused on what
  this Wave 2 effort surfaced that future Phase F+ work or future
  parquet-sweep extensions should know.

---

## Functional Requirements

### FR-1: Same-sweep computation

All five new outputs (3 columns + 2 tables) must be computed in **one**
extended `_phase_f_via_s3` pass. No additional `urlopen` calls relative
to current Wave 1 behavior. Verified by net-call assertion in
integration test.

### FR-2: Source attribution

The new columns + new tables are populated **only** when
`packages.downloads_source = 's3-parquet'` (or `'merged'`). Rows with
`downloads_source = 'anaconda-api'` retain `NULL` for the new columns
and have no rows in the new tables. Consumers tolerating missing
metrics check `downloads_source` first.

### FR-3: Trend slope discipline

- `NULL` when either window is empty or fewer than 6 months of data.
- Capped at `+10.0` (i.e. 1000% growth) to dampen new-package outliers.
- Sign: positive = growing, negative = declining.
- Floored at `-1.0` is implicit (downloads can't go below zero).

### FR-4: Data-quality filter on `pkg_python`

Dirty values like `2.30`, `7.3`, `3.81` MUST be dropped before
aggregation. Regex `^(2\.7|3\.[0-9]{1,2})$` documented in code comments
with the inspection-date provenance.

### FR-5: Idempotent table writes

`package_platform_downloads` + `package_python_downloads` use
`INSERT OR REPLACE` keyed on PK. Re-running Phase F replaces, doesn't
accumulate. `fetched_at` tracks the most recent write.

### FR-6: Schema migration safety

Migration v26 → v27 runs cleanly on:

- Fresh DB (`--fresh`).
- Existing v26 DB (in-place upgrade).
- Already-v27 DB (idempotent no-op).

Verified by `tests/meta/test_schema_migration.py` covering all three
paths.

---

## Technical Approach

### Where the code lands

- **`scripts/conda_forge_atlas.py`** — `_phase_f_via_s3` extended.
  Schema migration entry added to `_apply_pending_migrations`.
  `SCHEMA_VERSION` bumped 26 → 27.
- **`scripts/_parquet_cache.py`** — likely no changes. If a
  read-path helper makes the multi-aggregation cleaner, add it here.
- **`tests/unit/test_phase_f_s3.py`** (or wherever current
  `_phase_f_via_s3` is tested) — extended with the new assertions.
- **`tests/meta/test_schema_migration.py`** — updated to v27.

### Key implementation notes

- **One read, multiple aggregations.** pyarrow tables are zero-copy
  views; pass the same loaded Table to multiple group-by passes
  without re-reading the parquet file.
- **Memory budget.** A 12-month rolling window of conda-forge data is
  ~150 MB of parquet → ~600-900 MB pyarrow Table in memory. Acceptable
  for the local-recipes env's typical 16+ GB host. If this surfaces as a
  concern, fall back to per-month streaming aggregation with a
  running-dict accumulator — but only if profiling shows it matters.
- **Trend slope's prior-90d window.** Months 4-6 trailing from
  `last_nonzero_month` (not from today's calendar) so the trend isn't
  thrown off by recently-uploaded packages that have a 6-month
  hiatus before activity began.

### Env-var matrix (no new env vars)

Wave 2 ships with **no new env vars**. The existing `PHASE_F_SOURCE` /
`PHASE_F_S3_MONTHS` / `S3_PARQUET_BASE_URL` cover the new behavior. If
operators want to disable just the breakdown tables (e.g. to save the
~50 MB they'd add to the DB), they can already use
`PHASE_F_SOURCE=anaconda-api` to skip the parquet path entirely. Don't
add a separate disable knob unless real demand surfaces.

---

## Acceptance Criteria (Whole Feature)

- **AC-1.** Schema migration v26 → v27 runs cleanly on fresh + existing
  + already-migrated DBs. Tests cover all three.
- **AC-2.** After running `--profile admin` against a populated DB,
  `packages.downloads_30d` is non-NULL for ≥95% of rows with
  `downloads_source = 's3-parquet'`.
- **AC-3.** `downloads_trend_90d` is non-NULL for ≥80% of packages
  with `first_nonzero_month` more than 6 months in the past.
- **AC-4.** `package_platform_downloads` contains ≥1 row per package
  with non-empty `pkg_platform` in the parquet.
- **AC-5.** `package_python_downloads` contains only rows matching
  the data-quality regex; no `7.3`, `3.81`, `2.30` values present.
- **AC-6.** Phase F wall-clock under `--profile admin --fresh` does
  NOT increase by more than 30 seconds vs. v8.17.0 baseline (parquet
  is already loaded; new aggregations are cheap).
- **AC-7.** The whole test suite passes (`pixi run -e local-recipes
  test`) with no new failures introduced.
- **AC-8.** Per CLAUDE.md Rule 2: a CHANGELOG.md entry lands, a
  retrospective runs against the CFE skill, and the actionable-
  intelligence catalog rows for the new signals flip from `📋 open`
  to `✅ shipped (v8.<NEW>.0)`.

---

## Open Questions

### Pre-resolved (recommendations)

- **OQ-1.** Should `downloads_30d` use calendar-month or rolling-30-day
  resolution? **Recommendation: calendar-month** — that's what the
  parquet gives natively (monthly cadence). Rolling-30-day would
  require per-day data the parquet doesn't carry. Document explicitly:
  "single most-recent month at monthly resolution, not 30 calendar
  days from today." Aligns with parent spec Story 7.

- **OQ-2.** Should `last_nonzero_month` exclude the current
  (in-progress) month? **Recommendation: no** — include it. The
  parquet's current-month file updates daily; whatever value is
  cached reflects the actual data and is the right thing to surface.
  Document the staleness: "current-month value reflects parquet
  refresh time; consult `downloads_fetched_at` for staleness."

- **OQ-3.** Cap `downloads_trend_90d` at `+10.0` (per parent spec)
  but also floor at what? **Recommendation: floor at `-1.0`** — a
  100% decline is the worst case (zero downloads); negative-infinity
  values are nonsense. Per Story 3 FR-3.

### Genuinely open (design call — get user input at intake)

- **OQ-4.** Should v8.<NEW>.0 ship trigger an opportunistic Phase F
  re-run on `--profile admin` even when the TTL hasn't expired, so
  operators see populated v8.<NEW> columns on first run after upgrade?
  Cost: ~30-60 seconds re-aggregating the cached parquet. Benefit:
  immediately-useful new columns instead of a 7-day wait for TTL
  expiry. **Recommendation: yes** — add `PHASE_F_FORCE_REFRESH=1`
  env tag that the v8.<NEW> migration step sets once on the first
  post-migration run, then clears. Operators can also set it
  manually.

- **OQ-5.** Should the breakdown tables track `first_nonzero_month` /
  `last_nonzero_month` per (package, platform) and per (package,
  python) too? **Recommendation: no** — that's 38M rows of dimension
  history; Wave 2 sticks to 90-day + lifetime totals. If demand
  surfaces later, add as Wave 4.

---

## Dependencies and Constraints

- **`pyarrow`** — already in the `local-recipes` pixi env (Wave 0).
  Verified.
- **Atlas schema** at v26 prior to migration. Verified
  `SCHEMA_VERSION = 26` at `scripts/conda_forge_atlas.py:137` on
  2026-06-13.
- **`_phase_f_via_s3`** as the integration point. Wave 1 implementation
  intact.
- **CLAUDE.md Rules 1 + 2** apply (CFE skill invocation + closeout retro).
- **No new top-level dependencies.** Stays inside the existing env footprint.

---

## Out of Scope (Explicit)

- **OoS-1.** Wave 3 CLIs (`platform_breakdown`, `pyver_breakdown`,
  `channel_split`). Separate effort once Wave 2 lands.
- **OoS-2.** API-path retrofit. `_phase_f_via_api` keeps its
  current 2-column output; the new columns stay NULL when source is
  `anaconda-api`.
- **OoS-3.** Daily-granularity downloads, defaults-channel atlas,
  per-build-hash detail — all carry through from parent spec NG1,
  NG2, NG5.
- **OoS-4.** Schema migration tooling improvements. The existing
  `_apply_pending_migrations` pattern is sufficient; don't fold
  refactor work into Wave 2.

---

## References

### Parent spec (source of truth for detail)

- [`docs/specs/atlas-phase-f-s3-backend.md`](atlas-phase-f-s3-backend.md)
  — full Wave 0 + 1 + 2 + 3 detail. This brief is the Wave 2 subset.

### Code (entry points)

- `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py`
  — `_phase_f_via_s3` (extend), `SCHEMA_VERSION` (bump),
  `_apply_pending_migrations` (add migration entry).
- `.claude/skills/conda-forge-expert/scripts/_parquet_cache.py`
  — likely no changes; existing reader is enough.

### Tests

- `.claude/skills/conda-forge-expert/tests/unit/test_phase_f_s3.py`
  (or wherever current Wave 1 tests live — confirm path at intake).
- `.claude/skills/conda-forge-expert/tests/meta/test_schema_migration.py`
  — update for v27.

### Documentation to update

- `.claude/skills/conda-forge-expert/reference/atlas-phases-overview.md`
  — Phase F section + catalog row.
- `.claude/skills/conda-forge-expert/reference/atlas-actionable-intelligence.md`
  — new rows for the 5 new signals.
- `.claude/skills/conda-forge-expert/CHANGELOG.md` — new entry per
  Rule 2.
- `.claude/skills/conda-forge-expert/config/skill-config.yaml`
  — version bump.
