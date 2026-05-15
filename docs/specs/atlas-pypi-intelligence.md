# Tech Spec: PyPI Intelligence — `pypi_intelligence` side table + 5-phase enrichment pipeline

> **BMAD intake document.** Written for `bmad-quick-dev` (Quick Flow track —
> additive enrichment layer on top of v8.0.x's `pypi_universe`). ~24 implementation
> stories across 5 waves. Run BMAD with this file as the intent document:
>
> ```
> run quick-dev — implement the intent in docs/specs/atlas-pypi-intelligence.md
> ```
>
> **Per `CLAUDE.md` Rule 1**, any BMAD agent executing this spec MUST invoke
> the `conda-forge-expert` skill before touching atlas code. Per Rule 2, the
> effort closes with a CFE-skill retrospective and a `CHANGELOG.md` entry.

---

## Status

| Field | Value |
|---|---|
| Status | **Draft v1** — ready for `bmad-quick-dev` intake |
| Owner | rxm7706 |
| Track | BMAD Quick Flow (tech-spec only, no PRD/architecture phase) |
| Surface area | `conda-forge-expert` skill — schema v22 migration adding `pypi_intelligence` side table + `pypi_universe_serial_snapshots` snapshot table; 5 new atlas phases (O, P, Q, R, S); new `pypi-intelligence` CLI; new `pypi_intelligence` MCP tool; new `_http.py` resolver for BigQuery + cross-channel sources |
| Scope | Tier 1 (serial-snapshot deltas + activity_band) + Tier 2 (BigQuery 30/90 d downloads + cross-channel `in_*` BOOLs) + Tier 3 (per-project JSON enrichment for top-N candidates) + Tier 4 (computed `conda_forge_readiness` + `packaging_shape` + `recommended_template`) + Tier 5 (staged-recipes / issue cross-reference). Architecture: `pypi_universe` stays reference-data-only; all enrichment lands in a new `pypi_intelligence` side table joined on `pypi_name`. |
| Version | conda-forge-expert v8.0.x → **v8.1.0** (MINOR — additive features, no breaking change; new CLI / MCP tool / schema additions, no deprecations) |
| Out of scope | Full enrichment of all 806 k pypi names (Phase R is bounded to a candidate slice — top 5 k by `last_serial` plus delta-flagged "rising" rows); ML-based packageability inference; auto-recipe generation; BigQuery service-account provisioning (operator BYO); ecosyste.ms / libraries.io tarball ingest (Tier 4 stretch — separate spec); auto-opening of staged-recipes PRs from `recommended_template` |
| Created | 2026-05-14 |
| Predecessor | `docs/specs/atlas-pypi-universe-split.md` (v7.9.0 — introduced `pypi_universe`) + `docs/specs/conda-forge-expert-v8.0.md` (v8.0.0 — Phase H serial-gate, profiles) |
| Driven by | The 2026-05-14 conversation about "what useful metadata can be added to pypi_universe" — recommendation locked on keeping `pypi_universe` minimal and pushing enrichment into a side table |

---

## Background and Context

### The problem

`pypi_universe` (schema v20+) holds 806,703 PyPI projects with three columns:
`pypi_name`, `last_serial`, `fetched_at`. That's just enough to power the
`pypi-only-candidates` admin CLI ("which PyPI projects have no conda-forge
equivalent yet, ordered by most-recently-active"), but it leaves every
subsequent question unanswered:

- *Is this project popular?* No download counts.
- *Is it packageable as conda-forge?* No license, no `requires_python`, no
  build-system info, no wheel/sdist availability.
- *Is it already packaged elsewhere?* No cross-channel BOOLs (bioconda,
  pytorch, robostack) or cross-ecosystem flags (homebrew, nixpkgs, spack).
- *What kind of recipe shape would fit?* No `packaging_shape` classifier
  (pure-python / cython / rust-pyO3 / c-extension).
- *Is this fresh activity or a one-off namespace squat?* No serial-delta
  history.
- *Has someone already requested a feedstock for it?* No cross-reference to
  staged-recipes PRs or issues.

The current `pypi-only-candidates` CLI surfaces *names* but no *judgment data*.
A maintainer scanning the list for packageable candidates has to fetch
`pypi.org/pypi/<name>/json` by hand for each one and apply the conda-forge
mental checklist (license OK? Python >= 3.10? pure-Python? recent
release?). That's the gap this spec closes.

### What's been ruled out

- **Enriching all 806 k pypi_universe rows with per-project JSON fetches.**
  At pypi.org's documented ~30 req/s ceiling, that's ~7 hours of HTTP. The
  vast majority of pypi-only projects are dead-namespace noise (abandoned,
  internal-mirrored, namesquats). Phase R is **deliberately scoped** to a
  candidate slice — top 5 k by `last_serial` plus delta-flagged "rising"
  rows from Phase O snapshots. Operators who want to widen the slice can
  bump `PHASE_R_CANDIDATE_LIMIT`.

- **Replacing `pypi_universe` with a fatter table.** Architecture review
  flagged that mixing reference data (the universe directory) with
  computed scores would mirror the v19→v20 mistake (`packages` getting
  polluted with `pypi_only` rows). Keep `pypi_universe` minimal; push
  enrichment into a side table.

- **Auto-generating recipes from intelligence data.** The
  `recommended_template` column is a *suggestion*, not an autorun.
  Recipe generation stays in the `conda-forge-expert` skill's explicit
  workflow (steps 1-9). Future spec may close that loop.

- **BigQuery service-account provisioning automation.** Operators set
  `GOOGLE_APPLICATION_CREDENTIALS` themselves; Phase P reads from env or
  falls back to public dataset access via gcloud-default-credentials. Phase
  P is opt-in (`PHASE_P_ENABLED=1`) — no operator action means no BQ work.

- **Cross-ecosystem package indexes via per-package fetches.** Use bulk
  indexes only — bioconda/pytorch/nvidia/robostack via `current_repodata.json`
  (same as Phase B), homebrew/nixpkgs/spack/debian/fedora via their
  published bulk dumps. Per-package lookups would be a non-starter at 806 k
  scale.

### What's available to leverage

- **`pypi_universe` is already populated** — 806,703 rows, indexed on
  `pypi_name`. Adding a side table joined on `pypi_name` is zero migration
  cost.
- **`packages` already mirrors `pypi_last_serial`** on the conda-actionable
  working set (~20 k rows). Phase O's snapshot-based delta logic can compare
  against this for the conda-side intersection without re-fetching.
- **Phase D's daily-lean path runs every day** and already fetches
  `pypi.org/simple/` (~40 MB Simple v1 JSON). Phase O adds a one-line
  snapshot insert at the end of Phase D — no new fetch.
- **BigQuery has a public PyPI downloads dataset**
  (`bigquery-public-data.pypi.file_downloads`) with the official PyPI
  analytics. ~30 GB scanned per query, within the free tier monthly budget
  for atlas operators.
- **`current_repodata.json`** is the same pattern Phase B uses for
  conda-forge. Pointing it at bioconda, pytorch, nvidia, robostack channels
  costs ~30 s and a few MB per channel.
- **`pypi.org/pypi/<name>/json`** is the API Phase H already uses. Phase R
  reuses the worker pattern (`_phase_h_fetch_one`) with the same retry +
  jitter + Retry-After plumbing.
- **The `_phase_l_concurrency_for` per-registry concurrency pattern** from
  v7.8.0 generalizes to Phase R's per-source concurrency caps.
- **`atlas-phase-engineering.md`** documents the 9 patterns to follow for
  any new phase — concurrency caps, atomic writes, incremental commits,
  page-level checkpoints, `<HOST>_BASE_URL` env-var conventions.

### Verified facts (informational)

Measured against the post-v8.0.2 atlas (verified 2026-05-14):

| Metric | Value |
|---|---|
| `pypi_universe` rows | 806,703 |
| Distinct `last_serial` values | 806,703 (all unique by design — global counter) |
| Highest `last_serial` | 37,034,622 |
| Pypi-only rows (no conda-forge match) | 787,129 |
| Pypi ∩ conda-forge | 19,574 |
| Existing `pypi-only-candidates` CLI rows displayed | unbounded (default --limit 25) |
| pypi.org/json effective fetch rate | ~3 req/s (PHASE_H_CONCURRENCY=3 default; v7.8.1 audit-closed) |
| Fetch cost for top 5 k slice at 3 req/s | ~28 minutes wall-clock |
| BigQuery monthly free tier | 1 TB scanned (one downloads query ~30 GB; ~30 queries/month free) |
| Cross-channel bulk repodata size (per channel) | ~5-50 MB compressed |

---

## Goals

- **G1.** **`pypi_intelligence` side table** introduced as the cleanly-separated
  enrichment layer. `pypi_universe` stays reference-data-only (3 columns
  forever); all computed scores, cross-references, and per-project
  enrichment live in `pypi_intelligence` keyed on `pypi_name`. Same join cost,
  cleaner ownership.

- **G2.** **Phase O ships activity classification** without any new HTTP.
  `pypi_universe_serial_snapshots` records a daily `(pypi_name, last_serial,
  snapshot_at)` triple; `pypi_intelligence.activity_band ∈ {'hot', 'warm',
  'cold', 'dormant'}` is computed from rolling serial-delta windows. Powers
  the new `pypi-intelligence --activity` filter.

- **G3.** **Phase P ships official PyPI downloads** via BigQuery's public
  `pypi.file_downloads` dataset. Populates `downloads_30d` and `downloads_90d`
  for all 806 k rows in one query. Sortable, filterable. **This is the
  single most-impactful column** — the difference between "active by
  serial" (release events) and "active by adoption" (download volume).

- **G4.** **Phase Q ships cross-channel presence**. `in_bioconda`,
  `in_pytorch`, `in_nvidia`, `in_robostack` BOOLs populated from each
  channel's bulk `current_repodata.json`. Powers "this PyPI project is on
  bioconda but not conda-forge — migrate it" queries. Optional second-pass
  `in_homebrew` / `in_nixpkgs` / `in_spack` from upstream bulk indexes.

- **G5.** **Phase R ships per-project enrichment for the candidate slice**.
  Top 5 k pypi-only candidates by `last_serial` (configurable via
  `PHASE_R_CANDIDATE_LIMIT`), plus all "rising" candidates flagged by
  Phase O's serial-delta. Fetches `pypi.org/pypi/<name>/json`, parses
  license / requires_python / classifiers / project URLs / wheel coverage,
  classifies `packaging_shape`. Bounded fetch cost (~30 min at concurrency=3
  for the default 5 k slice).

- **G6.** **Phase S ships computed `conda_forge_readiness_score`**. 0-100
  composite of license_ok × requires_python × has_repo × recent_release ×
  packaging_shape. Sorts candidates by "how packageable" — surfaces low-hanging
  fruit to the maintainer/admin persona.

- **G7.** **New `pypi-intelligence` CLI** + MCP tool. Reads
  `pypi_intelligence` and surfaces candidates with rich filters
  (`--activity hot`, `--license-ok`, `--noarch-python-candidate`,
  `--min-downloads N`, `--in-bioconda`, `--score-min N`, `--json`).
  Output is the answer to "what's worth packaging next?"

- **G8.** **Schema v22 migration is self-healing**. New tables created via
  `CREATE TABLE IF NOT EXISTS`; existing v21 atlases upgrade cleanly on next
  `init_schema`. No operator action.

- **G9.** **Persona profile integration**. `bootstrap-data --profile admin`
  enables all 5 new phases on weekly cadence. `--profile maintainer`
  enables only Phase O + Phase Q (cheap signals; opt out of P/R/S).
  `--profile consumer` skips all new phases (air-gap friendliness preserved).

- **G10.** **Catalog flips reflect actual surface changes.**
  `atlas-actionable-intelligence.md` admin section flips 3-4 currently-📋
  rows to ✅ shipped (the "pypi candidates ordered by adoption" / "what's
  packageable now" / "cross-channel migration opportunities" queries).

## Non-Goals

- **NG1.** No full-universe per-project JSON enrichment. Phase R caps at
  5 k by default; widening requires explicit `PHASE_R_CANDIDATE_LIMIT`.
- **NG2.** No ML-based packageability inference. `packaging_shape` and
  `recommended_template` are deterministic classifiers over deterministic
  inputs.
- **NG3.** No auto-recipe-generation from `recommended_template`. The
  column is a *suggestion*; recipe authoring stays in the
  `conda-forge-expert` skill's explicit workflow.
- **NG4.** No new MCP tools beyond `pypi_intelligence` (the single read-side
  query tool). MCP exposure of individual phases (e.g., trigger Phase R from
  MCP) is a follow-up if operators request it.
- **NG5.** No automatic BigQuery credentials provisioning. Operator sets
  `GOOGLE_APPLICATION_CREDENTIALS` or `gcloud auth application-default
  login`; absence means Phase P silently skips with a printed warning.
- **NG6.** No per-package fetches against homebrew / nixpkgs / spack /
  debian / fedora. Phase Q uses bulk indexes only; per-ecosystem rate
  limits make per-package impractical at 806 k scale.
- **NG7.** No ecosyste.ms / libraries.io tarball ingest in v8.1.0. Stretch
  goal for v8.2.0 if operator demand surfaces.
- **NG8.** No automatic GitHub-side staged-recipes PR detection in
  Phase R's first version. `staged_recipes_pr_url` column ships in v8.1.0
  but populates only via opt-in GraphQL pass (`PHASE_R_GH_LOOKUP=1`).

---

## Lifecycle Expectations

- **One-time migration cost** (v21 → v22): `CREATE TABLE pypi_intelligence`
  + `CREATE TABLE pypi_universe_serial_snapshots` + indexes. < 1 second.
- **Steady-state per-build cost** (post-v8.1.0):
  - Phase O: ~5 s (single bulk INSERT into snapshot table at end of Phase D).
  - Phase P: ~30-60 s for the BigQuery query + bulk UPDATE.
    Monthly cadence; daily is overkill and burns BQ quota.
  - Phase Q: ~30 s per channel × 4-8 channels = 2-4 min weekly.
  - Phase R (warm, top-5 k slice): ~5-10 min — TTL gate skips JSON-fetched
    rows; only the delta from Phase O's serial-delta gets re-fetched.
  - Phase R (cold, top-5 k slice): ~28 min at concurrency=3.
  - Phase S: ~10-30 s (pure SQL UPDATE chain — no HTTP).
- **Storage delta**:
  - `pypi_intelligence`: ~5 MB at top-5 k populated rows (~1 KB each).
  - `pypi_universe_serial_snapshots`: ~20 MB after 30 days of daily
    snapshots × 806 k rows × 12 bytes/row. Pruneable to 90 days
    (operator-tunable via `PHASE_O_SNAPSHOT_RETAIN_DAYS`).
  - Net: ~25 MB on a warm atlas. Negligible.
- **BigQuery quota cost**: 1 query × ~30 GB scanned per Phase P run.
  Monthly cadence = 12 GB/year vs. 12 TB/year free tier.

---

## Design

### Schema v22

#### Reference-data table (unchanged)

```sql
-- Unchanged from v20+. The PyPI directory; one row per project, three columns.
CREATE TABLE IF NOT EXISTS pypi_universe (
    pypi_name    TEXT PRIMARY KEY,
    last_serial  INTEGER,
    fetched_at   INTEGER
);
```

#### New: `pypi_universe_serial_snapshots`

```sql
-- One row per (pypi_name, snapshot_at). Phase D's daily-lean tail writes a
-- snapshot of the full universe; Phase O computes serial deltas off this.
-- Retention default 90 days (operator-tunable via PHASE_O_SNAPSHOT_RETAIN_DAYS).
CREATE TABLE IF NOT EXISTS pypi_universe_serial_snapshots (
    pypi_name    TEXT NOT NULL,
    last_serial  INTEGER NOT NULL,
    snapshot_at  INTEGER NOT NULL,
    PRIMARY KEY (pypi_name, snapshot_at)
);
CREATE INDEX IF NOT EXISTS idx_pypi_serial_snap_at
    ON pypi_universe_serial_snapshots(snapshot_at);
CREATE INDEX IF NOT EXISTS idx_pypi_serial_snap_name
    ON pypi_universe_serial_snapshots(pypi_name);
```

#### New: `pypi_intelligence`

```sql
-- Per-pypi-name enrichment + computed scores. Joins to pypi_universe on
-- pypi_name. Population is opt-in: Phase O writes always; P/Q/R/S are
-- TTL-gated or candidate-gated.
CREATE TABLE IF NOT EXISTS pypi_intelligence (
    pypi_name                  TEXT PRIMARY KEY,

    -- Tier 1 — Phase O (no HTTP; from serial-snapshot deltas)
    activity_band              TEXT,            -- 'hot' / 'warm' / 'cold' / 'dormant'
    serial_delta_7d            INTEGER,
    serial_delta_30d           INTEGER,
    serial_delta_calc_at       INTEGER,

    -- Tier 2 — Phase P (BigQuery, bulk)
    downloads_30d              INTEGER,
    downloads_90d              INTEGER,
    downloads_fetched_at       INTEGER,
    downloads_source           TEXT,            -- 'bigquery-public' / 'bigquery-private' / 'cached'

    -- Tier 2 — Phase Q (cross-channel bulk repodata)
    in_bioconda                INTEGER,         -- 0/1/NULL
    in_pytorch                 INTEGER,
    in_nvidia                  INTEGER,
    in_robostack               INTEGER,
    in_homebrew                INTEGER,
    in_nixpkgs                 INTEGER,
    in_spack                   INTEGER,
    in_debian                  INTEGER,
    in_fedora                  INTEGER,
    cross_channel_at           INTEGER,

    -- Tier 3 — Phase R (pypi.org/json per-project for candidate slice)
    latest_version             TEXT,
    latest_upload_at           INTEGER,
    latest_yanked              INTEGER,         -- 0/1/NULL
    requires_python            TEXT,
    license_raw                TEXT,
    license_spdx               TEXT,
    summary                    TEXT,
    home_page                  TEXT,
    repo_url                   TEXT,
    docs_url                   TEXT,
    issues_url                 TEXT,
    classifiers                TEXT,            -- JSON array string
    has_wheel                  INTEGER,         -- 0/1/NULL
    has_sdist                  INTEGER,
    wheel_platforms            TEXT,            -- JSON array: "any","linux_x86_64","macosx_11_0_arm64",...
    python_tags                TEXT,            -- JSON array: "cp310","cp311","cp312","py3","py2.py3"
    packaging_shape            TEXT,            -- 'pure-python' / 'cython' / 'c-extension' / 'rust-pyo3' / 'fortran' / 'multi-output' / 'unknown'
    json_fetched_at            INTEGER,
    json_last_error            TEXT,

    -- Tier 4 — Phase S (computed; pure SQL)
    conda_forge_readiness      INTEGER,         -- 0-100 composite
    bus_factor_proxy           INTEGER,
    dependency_blast_radius    INTEGER,         -- from packages.dependencies reverse-counts
    recommended_template       TEXT,            -- 'noarch-python' / 'maturin' / 'cython' / 'compiled-cpp' / etc.
    score_calc_at              INTEGER,

    -- Tier 5 — Phase R extension (opt-in GH lookup)
    staged_recipes_pr_url      TEXT,
    staged_recipes_pr_state    TEXT,            -- 'open' / 'merged' / 'closed' / NULL
    feedstock_request_issue    INTEGER,         -- GitHub issue number
    cf_lookup_at               INTEGER,

    -- Operator overrides (Q1 RESOLVED) — survives Phase S re-runs
    notes                      TEXT,
    notes_updated_at           INTEGER
);
CREATE INDEX IF NOT EXISTS idx_pypi_intel_activity   ON pypi_intelligence(activity_band);
CREATE INDEX IF NOT EXISTS idx_pypi_intel_downloads  ON pypi_intelligence(downloads_30d);
CREATE INDEX IF NOT EXISTS idx_pypi_intel_readiness  ON pypi_intelligence(conda_forge_readiness);
CREATE INDEX IF NOT EXISTS idx_pypi_intel_in_bio     ON pypi_intelligence(in_bioconda);
CREATE INDEX IF NOT EXISTS idx_pypi_intel_shape      ON pypi_intelligence(packaging_shape);
```

#### View: `v_pypi_candidates`

```sql
-- Pre-joined view for the pypi-intelligence CLI / MCP tool. Surfaces
-- pypi-only projects (no conda-forge match) with all enrichment columns.
-- Filtering / sorting is done at query time.
CREATE VIEW IF NOT EXISTS v_pypi_candidates AS
SELECT
    u.pypi_name,
    u.last_serial,
    u.fetched_at AS universe_fetched_at,
    i.activity_band, i.serial_delta_7d, i.serial_delta_30d,
    i.downloads_30d, i.downloads_90d,
    i.in_bioconda, i.in_pytorch, i.in_nvidia, i.in_robostack,
    i.in_homebrew, i.in_nixpkgs, i.in_spack, i.in_debian, i.in_fedora,
    i.latest_version, i.latest_upload_at, i.latest_yanked,
    i.requires_python, i.license_spdx, i.summary,
    i.repo_url, i.has_wheel, i.has_sdist, i.packaging_shape,
    i.conda_forge_readiness, i.recommended_template,
    i.staged_recipes_pr_url, i.staged_recipes_pr_state,
    p.conda_name        -- NULL = pypi-only candidate
FROM pypi_universe u
LEFT JOIN pypi_intelligence i ON i.pypi_name = u.pypi_name
LEFT JOIN packages p ON p.pypi_name = u.pypi_name AND p.conda_name IS NOT NULL;
```

### Phase O — Serial-delta snapshots + activity bands (Tier 1)

#### Trigger

End-of-Phase-D hook (no new fetch). Default-on; opt-out via `PHASE_O_DISABLED=1`.

#### Implementation

```python
def phase_o_serial_snapshots(conn: sqlite3.Connection) -> dict:
    """Phase O: snapshot pypi_universe.last_serial daily; compute activity bands.

    Cheap — single bulk INSERT of (pypi_name, last_serial, now) for all rows
    of pypi_universe. Then a UPDATE-from-aggregate against
    pypi_universe_serial_snapshots to populate pypi_intelligence.activity_band
    + serial_delta_{7d,30d}.

    Activity bands (configurable via PHASE_O_*_THRESHOLD env):
      - hot       : serial_delta_7d   >= 5    (>= 5 events / 7 days)
      - warm      : serial_delta_30d  >= 5    (>= 5 events / 30 days)
      - cold      : serial_delta_30d  >= 1
      - dormant   : serial_delta_30d  == 0    (no events in 30 days)
    """
```

#### Retention

Snapshots older than `PHASE_O_SNAPSHOT_RETAIN_DAYS` (default 90) are pruned
on every Phase O run. Bounded growth — ~20 MB ceiling.

### Phase P — PyPI downloads via BigQuery (Tier 2)

#### Trigger

Opt-in via `PHASE_P_ENABLED=1`. Monthly cadence recommended.
`--profile admin` sets `PHASE_P_ENABLED=1`. `--profile maintainer` does not.

#### Implementation

```python
def phase_p_pypi_downloads(conn: sqlite3.Connection) -> dict:
    """Phase P: bulk-load 30-day and 90-day PyPI download counts.

    Source: bigquery-public-data.pypi.file_downloads (Google's official
    PyPI analytics). Single query covers all 806k pypi names.

    Auth: env GOOGLE_APPLICATION_CREDENTIALS OR `gcloud auth
    application-default` cached creds. Missing creds → log + skip
    gracefully.

    Cost: ~30 GB scanned per query, well within BigQuery free tier (1 TB/mo).

    Tunables:
      PHASE_P_DISABLED       : "1" to skip
      PHASE_P_BQ_PROJECT     : GCP project override (uses ADC default)
      PHASE_P_BQ_WINDOW_DAYS : default 30 + 90 windows; can extend to 7d
      PHASE_P_TTL_DAYS       : default 30 (re-fetch monthly)
    """
    query = '''
        SELECT
            LOWER(REGEXP_REPLACE(file.project, '[-_.]+', '-')) AS pypi_name,
            SUM(IF(timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(),
                                              INTERVAL 30 DAY), 1, 0))
                AS downloads_30d,
            SUM(IF(timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(),
                                              INTERVAL 90 DAY), 1, 0))
                AS downloads_90d
        FROM `bigquery-public-data.pypi.file_downloads`
        WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(),
                                          INTERVAL 90 DAY)
        GROUP BY pypi_name
    '''
```

Result is bulk-loaded via `INSERT INTO pypi_intelligence (pypi_name,
downloads_30d, downloads_90d, downloads_fetched_at, downloads_source) ...
ON CONFLICT(pypi_name) DO UPDATE SET ...`. Idempotent.

### Phase Q — Cross-channel presence (Tier 2)

#### Trigger

Default-on weekly (`PHASE_Q_TTL_DAYS=7`). Opt-out via `PHASE_Q_DISABLED=1`.

#### Per-source dispatchers

```python
_PHASE_Q_CHANNELS = {
    "bioconda":   "https://conda.anaconda.org/bioconda/noarch/current_repodata.json",
    "pytorch":    "https://conda.anaconda.org/pytorch/noarch/current_repodata.json",
    "nvidia":     "https://conda.anaconda.org/nvidia/noarch/current_repodata.json",
    "robostack":  "https://conda.anaconda.org/robostack-staging/noarch/current_repodata.json",
}
_PHASE_Q_BULK_INDEXES = {
    "homebrew":   "https://formulae.brew.sh/api/formula.json",
    "nixpkgs":    "https://channels.nixos.org/nixos-unstable/packages.json.br",
    "spack":      "https://github.com/spack/spack/raw/develop/var/spack/repos/builtin/packages/<...>",
    "debian":     "https://sources.debian.org/api/list/",
    "fedora":     "https://src.fedoraproject.org/rest/projects/",
}
```

Each source returns a set of package names; Phase Q parses PEP 503-canonicalized
name → BOOL update on `pypi_intelligence.in_<channel>`.

`<CHANNEL>_BASE_URL` env-var convention for JFrog mirroring (e.g.,
`BIOCONDA_BASE_URL`, `PYTORCH_BASE_URL`).

### Phase R — Per-project JSON enrichment (Tier 3)

#### Trigger

Opt-in via `PHASE_R_ENABLED=1`. Weekly cadence recommended. `--profile admin`
sets `PHASE_R_ENABLED=1`.

#### Candidate selection

```sql
-- The candidate slice — top-N pypi-only by last_serial PLUS rising-activity
-- rows flagged by Phase O.
WITH pypi_only AS (
    SELECT u.pypi_name, u.last_serial
    FROM pypi_universe u
    LEFT JOIN packages p ON p.pypi_name = u.pypi_name AND p.conda_name IS NOT NULL
    WHERE p.pypi_name IS NULL
)
SELECT pypi_name FROM pypi_only
WHERE pypi_name NOT IN (SELECT pypi_name FROM pypi_intelligence
                        WHERE json_fetched_at > ?)  -- TTL gate
   OR pypi_name IN (SELECT pypi_name FROM pypi_intelligence
                    WHERE activity_band = 'hot'      -- always re-fetch hot
                      AND json_fetched_at < ?)
ORDER BY last_serial DESC
LIMIT ?  -- PHASE_R_CANDIDATE_LIMIT, default 5000
```

#### Worker

Same pattern as `_phase_h_fetch_one` — concurrency=3, Retry-After honored,
±25% jitter on exponential backoff. Atomic per-row UPDATE on success.

#### Packaging-shape classifier

Deterministic rules over JSON fields:

```python
def _classify_packaging_shape(json_doc: dict) -> str:
    """Return one of: pure-python, cython, c-extension, rust-pyo3, fortran,
    multi-output, unknown."""
    requires = json_doc.get("info", {}).get("requires_dist", []) or []
    files = json_doc.get("urls", []) or []

    # Pure-python: only -none-any.whl wheel files OR sdist with no
    # build_system requires beyond setuptools/poetry/hatchling
    if all(f.get("packagetype") == "bdist_wheel"
           and "none-any" in (f.get("filename") or "")
           for f in files if f.get("packagetype") == "bdist_wheel"):
        return "pure-python"

    # Rust-pyO3: requires_dist or build_system_requires contains "maturin"
    # or filename has cp3X-cp3X-linux_*.whl AND repo has Cargo.toml signal
    if any("maturin" in (r or "").lower()
           for r in [*requires, *_get_build_system_requires(json_doc)]):
        return "rust-pyo3"

    # Cython: build_system_requires contains "cython"
    if any("cython" in (r or "").lower()
           for r in _get_build_system_requires(json_doc)):
        return "cython"

    # C-extension: per-platform wheels with cp3X tags and no maturin/cython
    if any("cp3" in (f.get("filename") or "") for f in files):
        return "c-extension"

    # Fortran: very rare — look for "fortran" or "gfortran" in requires
    # (heuristic; few PyPI packages declare this)

    return "unknown"
```

### Phase S — Computed scores (Tier 4)

#### Trigger

Default-on. Runs after Phase R completes. Pure SQL UPDATE chain — no HTTP.

#### `conda_forge_readiness` formula

```python
# Composite 0-100 score; each component is 0-N points
SCORE_LICENSE_OK         = 25  # OSI-approved SPDX / not "UNKNOWN"
SCORE_REQUIRES_PYTHON_OK = 20  # explicit >= 3.10 OR unspecified (assumed OK)
SCORE_HAS_REPO           = 15  # repo_url populated
SCORE_RECENT_RELEASE     = 15  # latest_upload_at within 2 years
SCORE_HAS_SDIST          = 10  # sdist available
SCORE_PACKAGING_SHAPE_OK = 15  # pure-python / rust-pyo3 / cython
                               # = full points; c-extension / unknown = half;
                               # multi-output / fortran = 0 (manual)
```

#### `recommended_template` mapping

```python
PACKAGING_SHAPE_TO_TEMPLATE = {
    "pure-python":   "templates/python/recipe.yaml",
    "rust-pyo3":     "templates/python/maturin-recipe.yaml",
    "cython":        "templates/python/cython-recipe.yaml",
    "c-extension":   "templates/python/compiled-recipe.yaml",
    "fortran":       "templates/python/fortran-recipe.yaml",   # new
    "multi-output":  None,                                     # manual
    "unknown":       None,
}
```

### CLI — `pypi-intelligence`

```bash
pixi run -e local-recipes pypi-intelligence \
    --activity hot                    # filter by activity_band
    --license-ok                       # only license_spdx is OSI-approved
    --noarch-python-candidate          # pure-python + requires_python>=3.10
    --min-downloads 1000               # downloads_30d >= 1000
    --in-bioconda                      # only in_bioconda=1 (migration candidates)
    --not-in-conda-forge               # only conda_name IS NULL
    --score-min 70                     # conda_forge_readiness >= 70
    --limit 50
    --json                             # JSON output

# Default invocation:
pixi run -e local-recipes pypi-intelligence \
    --not-in-conda-forge --score-min 60 --activity hot --limit 25
```

### MCP exposure

One new MCP tool: `pypi_intelligence(filter, limit, sort_by) -> list[dict]`.
Wraps the CLI's read path. Same filter surface.

### Persona profile integration

| Profile | Phases enabled by default |
|---|---|
| `maintainer` (daily) | O + Q (cheap; no opt-in fetches) |
| `admin` (weekly) | O + P + Q + R + S (full enrichment) |
| `consumer` (air-gap) | O only (snapshot is local; no outbound) |

---

## Stories — 5 waves, ~24 stories

### Wave A — Schema v22 + Phase O foundation (~6 stories)

| ID | Story | Effort |
|---|---|---|
| S1 | Add `pypi_intelligence` + `pypi_universe_serial_snapshots` + `v_pypi_candidates` to SCHEMA_DDL; bump SCHEMA_VERSION 21 → 22 | XS |
| S2 | Schema v22 migration block (idempotent guards on `pragma_table_info` + view existence) | XS |
| S3 | `phase_o_serial_snapshots`: nightly INSERT into snapshots + UPDATE pypi_intelligence (activity_band, serial_delta_*); retention prune | M |
| S4 | Tunables: `PHASE_O_DISABLED`, `PHASE_O_HOT_THRESHOLD`, `PHASE_O_WARM_THRESHOLD`, `PHASE_O_SNAPSHOT_RETAIN_DAYS` | XS |
| S5 | `tests/unit/test_phase_o_snapshots.py`: 5 fixtures covering each activity_band + retention prune + idempotency | M |
| S6 | Hook Phase O into the cf_atlas PHASES registry; runs after Phase D | XS |

### Wave B — Phase P + Phase Q (bulk fetches, Tier 2) (~6 stories)

| ID | Story | Effort |
|---|---|---|
| S7 | `phase_p_pypi_downloads`: BigQuery client + query + bulk UPSERT; graceful skip on missing GOOGLE_APPLICATION_CREDENTIALS | L |
| S8 | Tunables: `PHASE_P_ENABLED`, `PHASE_P_BQ_PROJECT`, `PHASE_P_BQ_WINDOW_DAYS`, `PHASE_P_TTL_DAYS` | XS |
| S9 | `tests/unit/test_phase_p_bigquery.py`: mock BQ client; verify SQL query shape + ON CONFLICT update | M |
| S10 | `phase_q_cross_channel`: bulk `current_repodata.json` fetch per channel + PEP 503 name canonicalization + BOOL UPDATE | L |
| S11 | `<CHANNEL>_BASE_URL` env-var conventions for JFrog mirroring; per-channel concurrency caps | S |
| S12 | `tests/unit/test_phase_q_cross_channel.py`: fixture repodata per channel + cross-channel `in_*` correctness | M |

### Wave C — Phase R (per-project JSON enrichment, Tier 3) (~5 stories)

| ID | Story | Effort |
|---|---|---|
| S13 | `phase_r_pypi_json_enrich`: candidate-slice query + worker pool reusing `_phase_h_fetch_one` pattern; per-row UPDATE | L |
| S14 | `_classify_packaging_shape` helper: deterministic rules over JSON fields (pure-python / cython / c-extension / rust-pyo3 / fortran / multi-output / unknown) | M |
| S15 | Tunables: `PHASE_R_ENABLED`, `PHASE_R_CANDIDATE_LIMIT`, `PHASE_R_TTL_DAYS`, `PHASE_R_CONCURRENCY` | XS |
| S16 | `tests/unit/test_phase_r_enrichment.py`: 8 fixtures across packaging-shape classifier + candidate-slice gate + JSON parse | L |
| S17 | License SPDX normalizer (raw → canonical SPDX); reuses existing `license_checker.py` patterns | M |

### Wave D — Phase S + CLI + MCP + profile integration (~5 stories)

| ID | Story | Effort |
|---|---|---|
| S18 | `phase_s_computed_scores`: SQL UPDATE chain populating `conda_forge_readiness` + `recommended_template`; reads `dependencies` for `dependency_blast_radius` | M |
| S19 | New `pypi_intelligence.py` CLI in `scripts/`; thin wrapper in `.claude/scripts/conda-forge-expert/`; `pixi.toml` task; meta-test SCRIPTS entry | M |
| S20 | New `pypi_intelligence` MCP tool in `conda_forge_server.py` | S |
| S21 | Persona profile updates: `admin` → enable P/R; `maintainer` → enable O/Q only; `consumer` → O only | XS |
| S22 | `tests/unit/test_pypi_intelligence_cli.py` + `tests/meta/test_actionable_scope.py` extension to recognize new phase selectors | M |

### Wave E — Closeout (~3 stories)

| ID | Story | Effort |
|---|---|---|
| S23 | CHANGELOG v8.1.0 entry; SKILL.md heading bump; skill-config 8.0.x → 8.1.0; CFE retrospective per CLAUDE.md Rule 2 | M |
| S24 | Update `reference/atlas-phases-overview.md` (5 new phase sections + Profile Reference appendix update); `atlas-actionable-intelligence.md` catalog flips for the new admin queries | M |
| S25 | `bmad-correct-course` for BMAD planning artifact sync (PRD pin bump v1.2.x → v1.3.0; architecture-cf-atlas; epics; project-parts; new sprint-change-proposal) | L |

### Wave sequencing rationale

- **Wave A first** — schema + Phase O is the foundation. Cheap, no new HTTP, but unlocks every subsequent phase's snapshot-delta dependency.
- **Wave B parallel-shippable** — P and Q are independent of each other and of Wave C/D. They populate different columns. Either could ship alone; bundling makes one schema-migration release cleaner.
- **Wave C depends on Wave A** — Phase R reads Phase O's `activity_band` for candidate selection. Could be slightly relaxed (Phase R could compute its own delta on the fly), but the snapshot table is cheaper.
- **Wave D depends on A+B+C** — Phase S's score reads all upstream columns. CLI + MCP wrap the joined view.
- **Wave E is closeout** — same shape as v8.0.0 closeout.

**Two-PR strategy:** Waves A + B in PR #1 (schema bump + reference-data enrichment, cheap to ship and review). Waves C + D + E in PR #2 (the candidate-enrichment + CLI surface). Both before v8.1.0 tag.

---

## Acceptance Tests

For each wave, the BMAD agent runs the existing pytest suite plus explicit new tests:

### Wave A

- `tests/unit/test_phase_o_snapshots.py::test_activity_band_hot` — fixture with serial_delta_7d >= threshold → activity_band='hot'
- `tests/unit/test_phase_o_snapshots.py::test_retention_prune` — old snapshots beyond `PHASE_O_SNAPSHOT_RETAIN_DAYS` are deleted
- `tests/unit/test_phase_o_snapshots.py::test_idempotent_rerun` — re-running Phase O is a no-op (same activity_band, same snapshot row)

### Wave B

- `tests/unit/test_phase_p_bigquery.py::test_query_shape` — query string matches the documented form
- `tests/unit/test_phase_p_bigquery.py::test_missing_creds_skips` — no `GOOGLE_APPLICATION_CREDENTIALS` → skip with warning
- `tests/unit/test_phase_q_cross_channel.py::test_bioconda_presence` — fixture repodata.json → `in_bioconda` flips for matched names
- `tests/unit/test_phase_q_cross_channel.py::test_pep503_normalization` — `tree_sitter` and `tree-sitter` collapse to one canonical name

### Wave C

- `tests/unit/test_phase_r_enrichment.py::test_pure_python_classifier` — only `*-none-any.whl` files → `packaging_shape='pure-python'`
- `tests/unit/test_phase_r_enrichment.py::test_rust_pyo3_classifier` — maturin in build_system_requires → `packaging_shape='rust-pyo3'`
- `tests/unit/test_phase_r_enrichment.py::test_cython_classifier` — cython in build_system_requires → `packaging_shape='cython'`
- `tests/unit/test_phase_r_enrichment.py::test_candidate_slice_limit` — only top-N by last_serial fetched
- `tests/unit/test_phase_r_enrichment.py::test_spdx_normalization` — raw license "MIT License" → SPDX "MIT"

### Wave D

- `tests/unit/test_phase_s_scores.py::test_readiness_score_max` — all components present + OK → 100
- `tests/unit/test_phase_s_scores.py::test_readiness_score_min` — no license + no repo + old → 0
- `tests/unit/test_phase_s_scores.py::test_recommended_template_pure_python` — pure-python shape → `templates/python/recipe.yaml`
- `tests/unit/test_pypi_intelligence_cli.py::test_filter_chain` — CLI flags compose as expected SQL WHERE clauses
- `tests/unit/test_pypi_intelligence_cli.py::test_json_output_shape` — `--json` round-trips through `json.loads`

### Cross-cutting

- Full atlas rebuild against the real connection produces `cf_atlas.db` at schema v22; `pypi_intelligence` populated for the candidate slice; `pypi-intelligence --not-in-conda-forge --score-min 70 --limit 10` returns 10 actionable candidates.
- Meta-test `test_actionable_scope.py` recognizes Phase O/P/Q/R/S selectors (no false drift flags).

---

## Risks

| Risk | Mitigation |
|---|---|
| BigQuery free tier exhausted by aggressive Phase P cadence | Default cadence is monthly (TTL 30 d); explicit `PHASE_P_ENABLED=1` required; documented "1 query per month = ~30 GB" budget vs 1 TB free tier in `atlas-operations.md` § Phase P |
| pypi.org rate-limits the Phase R top-5 k cold backfill | Same `_phase_h_fetch_one` rate-limit machinery (Retry-After + ±25% jitter + concurrency=3 default); the slice cap (5 k vs 806 k) keeps the cold cost bounded at ~28 min |
| Packaging-shape classifier false-positives | `unknown` is the safe default; only deterministic rules in v8.1.0. ML-based classification deferred to a follow-up spec. `recommended_template = NULL` for `unknown`. |
| Cross-channel `current_repodata.json` schemas drift | Phase Q parses only the package-name field (stable across schema versions). Channel addition requires explicit `_PHASE_Q_CHANNELS` update — review-gated. |
| Stale `pypi_intelligence.json_fetched_at` causes false "low readiness" scores | Phase O's serial-delta flags rising-activity rows for re-fetch even within TTL; safety cap (90 d) catches anything missed |
| Operator runs Phase R without Phase O snapshot history | Phase R falls back to "top-N by last_serial" without delta enrichment; logged as a warning. Phase O is foundational so this only happens on a brand-new install |
| Schema v22 migration introduces a query that locks `packages` | All new phases write to `pypi_intelligence` / `pypi_universe_serial_snapshots` only; no writes to `packages`. Read locks on `v_pypi_candidates` view do brief joins, no exclusive locks |
| `_classify_packaging_shape` mis-classifies a complex multi-output package as `c-extension` | Score = half-points for c-extension; `recommended_template = compiled` but the recipe author can override. Mis-class is annoying, not breaking. Hand-curated overrides table is a follow-up if many cases surface |
| GitHub `staged_recipes_pr_state` ages out (PR closed/merged after lookup) | `cf_lookup_at` TTL of 7 d; weekly Phase R refresh catches state changes |
| New phases add to total `bootstrap-data` wall-clock | Phase O is < 5 s; Phase Q ~2-4 min; Phase P + R + S are opt-in via profile. Maintainer profile only adds O + Q (< 5 min). Admin profile is weekly so the extra time is acceptable |

---

## Rollout

### Pre-merge

- Two-PR strategy: PR #1 = Waves A+B (schema + Phase O + P + Q); PR #2 = Waves C+D+E (Phase R + S + CLI + closeout).
- BMAD agent executes waves in order; each wave's tests pass before the next starts.
- Manual smoke run on the dev `cf_atlas.db` after each wave to confirm expected behavior.
- CFE skill version bumps per semver: 8.0.x → **8.1.0** (MINOR — additive).

### Merge order

- PR #1 first: lands the schema + reference-data layer + bulk-fetch phases. Sufficient soak (~1 week) before PR #2.
- PR #2: lands per-project enrichment + scores + CLI / MCP. Both before the v8.1.0 release tag.

### Post-merge

- `CHANGELOG.md` v8.1.0 entry summarizing the 5 new phases + the new CLI / MCP tool + the catalog flips.
- `atlas-phases-overview.md` extended with 5 new phase sections (O / P / Q / R / S); Profile Reference appendix updated.
- `atlas-actionable-intelligence.md`: catalog flips for the new admin/maintainer queries that `pypi-intelligence` unlocks:
  - "Sort pypi-only candidates by actual usage (downloads)" — ✅ shipped (Phase P)
  - "Find pypi projects packaged on bioconda but not conda-forge" — ✅ shipped (Phase Q)
  - "Surface high-readiness pypi candidates for next packaging session" — ✅ shipped (Phase S + CLI)
  - "Detect rising PyPI projects (activity_band='hot')" — ✅ shipped (Phase O)
- `guides/atlas-operations.md`: quickstart for `pypi-intelligence` CLI, sample queries, BigQuery setup notes.
- Auto-memory feedback entry only if cross-skill findings surface (e.g., BMAD's quick-dev workflow needs the new profile-aware Phase R behavior documented as a CFE invariant).

### Backout plan

- Schema v22 migration is reversible by hand: `DROP TABLE pypi_intelligence; DROP TABLE pypi_universe_serial_snapshots; DROP VIEW v_pypi_candidates`. Revert + downgrade leaves a clean v21 atlas.
- The 5 new phases write only to new tables; no existing column is modified. Revert is column-set additive only.

---

## Open Questions — All RESOLVED 2026-05-14

1. **`notes` column for hand-curated overrides?** → **RESOLVED: yes, add it.** Two columns added to `pypi_intelligence` schema: `notes TEXT`, `notes_updated_at INTEGER`. NULL by default. Operator-curated via SQL in v8.1.0; CLI `--annotate <pypi_name> --note "..."` flag deferred to v8.2.0. Insurance against computed-score formula churn — operator's overrides survive Phase S re-runs.

2. **Phase P BigQuery granularity — per-project or per-version?** → **RESOLVED: project-level only.** Per-version would multiply scan cost ~200× (~6 TB/query) and blow the BQ free tier. Version-level adoption data already lives in `package_version_downloads` for conda-actionable rows. `pypi_intelligence`'s purpose is "is this packageable," not "is this version popular." Per-version is a v8.2.0 follow-up if operator demand surfaces.

3. **`recommended_template` — template name or full path?** → **RESOLVED: full path.** Store strings like `templates/python/recipe.yaml`, `templates/python/maturin-recipe.yaml`. Single source of truth in `PACKAGING_SHAPE_TO_TEMPLATE`; consumers can directly invoke the `conda-forge-expert` skill with the path. Survives template refactors via one update site.

4. **Phase Q heuristic for non-PyPI ecosystems (homebrew, nixpkgs, spack, debian, fedora)?** → **RESOLVED: URL-pointer heuristic.** `in_<channel> = 1` only when that channel's package metadata cites a `files.pythonhosted.org` OR `pypi.org/packages/` URL (homebrew formula `url`; nixpkgs `src.url`; spack `pypi`-line; debian `Source:` PyPI redirect; fedora `pypi-version` macro). Otherwise 0. Accept false-negatives, zero false-positives — conservative truthy signal beats chatty noise.

5. **`staged_recipes_pr_url` source — GitHub Search vs local fork?** → **RESOLVED: fallback chain.** Default: query the local `staged-recipes` fork for `add-recipe-<name>` branches (air-gap-safe, no auth, fast). Behind `PHASE_R_GH_LOOKUP=1` opt-in: also query GitHub Search for global coverage. Local-fork-only is the cheap default; GH-search adds the global-view enrichment when operator opts in.

6. **Phase O snapshot retention window?** → **RESOLVED: 90 days default.** `PHASE_O_SNAPSHOT_RETAIN_DAYS=90` default; documented env var for operators who want longer (e.g., `=365` for year-over-year growth queries — admin-tier opt-in, ~80 MB on disk vs 20 MB). 90 d supports 30 d rolling delta queries which is what `activity_band` needs.

7. **`conda_forge_readiness` — raw weights vs percentile rank?** → **RESOLVED: raw weights for v8.1.0.** Absolute 0-100 score; comparable across runs (lets operators detect "score went up because license info was filled in" via Phase R). `conda_forge_readiness_percentile` derived column is a v8.2.0 follow-up if operators want triage-relative ranking. Raw + indexed = SQL queries are fast either way.

8. **PRD bump — v1.3.0 (MINOR) or v2.0.0 (MAJOR)?** → **RESOLVED: MINOR (v1.2.0 → v1.3.0).** Fully additive: no breaking FR/NFR, no existing-CLI changes, no schema deletions. New CLI (`pypi-intelligence`) and new MCP tool (`pypi_intelligence`) are opt-in surfaces; existing `pypi-only-candidates` continues to work unchanged. Per the PRD discipline established in v7.8.1 + v7.9.0 + v8.0.0 syncs, MAJOR is reserved for FR/NFR scope changes (e.g., changing the documented `bootstrap-data` default invocation as v8.0.0 did) — this spec doesn't touch documented defaults for existing surfaces.

---

## References

### Source-of-truth code (current state — v8.0.2 baseline)

- `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py`:
  - `SCHEMA_VERSION` (line 113) — bump to 22
  - SCHEMA_DDL block (~line 270) — add `pypi_intelligence`, `pypi_universe_serial_snapshots`, `v_pypi_candidates`
  - `init_schema` migration block (~line 600) — add v22 sub-block (idempotent IF NOT EXISTS guards)
  - End of Phase D (~line 1230) — hook in Phase O snapshot insert
  - New phase fns: `phase_o_serial_snapshots`, `phase_p_pypi_downloads`, `phase_q_cross_channel`, `phase_r_pypi_json_enrich`, `phase_s_computed_scores`
  - PHASES registry update
- `.claude/skills/conda-forge-expert/scripts/bootstrap_data.py` — profile updates for O/P/Q/R/S
- `.claude/skills/conda-forge-expert/scripts/pypi_intelligence.py` — NEW (Wave D)
- `.claude/scripts/conda-forge-expert/pypi_intelligence.py` — NEW wrapper (Wave D)
- `.claude/skills/conda-forge-expert/scripts/_http.py` — extend with `resolve_bigquery_urls`, `resolve_anaconda_channel_urls`, `resolve_homebrew_urls`, etc.
- `.claude/tools/conda_forge_server.py` — new `pypi_intelligence` MCP tool

### Related specs

- `docs/specs/atlas-pypi-universe-split.md` — v7.9.0 introduced `pypi_universe`. This spec extends it without altering it.
- `docs/specs/conda-forge-expert-v8.0.md` — v8.0.0 introduced personas + Phase H serial-gate. Phase O reuses the serial-gate's delta-comparison pattern.
- `docs/specs/atlas-phase-f-s3-backend.md` — v7.6.0 introduced multi-source dispatch on `PHASE_F_SOURCE`. Phase Q reuses the same pattern for per-channel dispatch.

### Audit context

- Conversation log 2026-05-14: "what useful metadata can be added to pypi_universe to make it more actionable" → recommendation locked on side-table architecture
- `.claude/skills/conda-forge-expert/reference/atlas-actionable-intelligence.md` — admin section will gain 3-4 ✅-flips on v8.1.0 ship

### Documentation

- `.claude/skills/conda-forge-expert/SKILL.md` — Atlas Intelligence Layer heading update to v8.1.0
- `.claude/skills/conda-forge-expert/CHANGELOG.md` — v8.1.0 entry per Rule 2
- `.claude/skills/conda-forge-expert/reference/atlas-phases-overview.md` — 5 new phase sections + Profile Reference appendix updated
- `.claude/skills/conda-forge-expert/reference/atlas-actionable-intelligence.md` — catalog flips
- `.claude/skills/conda-forge-expert/reference/atlas-phase-engineering.md` — Phase R's per-project JSON pattern + Phase Q's bulk-channel pattern added to the rule book
- `.claude/skills/conda-forge-expert/guides/atlas-operations.md` — `pypi-intelligence` quickstart + BigQuery setup notes
- `CLAUDE.md` — add `docs/specs/atlas-pypi-intelligence.md` to the BMAD-consumable spec list
- `.claude/skills/conda-forge-expert/quickref/commands-cheatsheet.md` — `pypi-intelligence` usage examples
