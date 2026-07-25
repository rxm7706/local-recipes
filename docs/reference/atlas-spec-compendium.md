# Atlas Spec Compendium — every BMAD spec used to build cf_atlas

> **Compilation, not source of truth** (assembled 2026-07-25). This file collects, in one
> place and verbatim, every BMAD intake spec that was used to build the cf_atlas
> intelligence layer (`cf_atlas.db`, its pipeline phases, and the atlas CLIs / MCP tools).
> The canonical copies remain where they live today — `docs/specs/cfe-shipped-releases.md`
> (Parts 1–4, 7–9) and the three standalone shipped specs named below. If a canonical file
> changes, regenerate this compendium from it; never edit history here. Release *notes* per
> version live in `.claude/skills/conda-forge-expert/CHANGELOG.md`. Do not re-run BMAD on
> any section.
>
> Seven of the ten atlas-building specs exist **only** as parts of the consolidated
> `cfe-shipped-releases.md` — the original files (`atlas-pypi-universe-split.md`,
> `atlas-pypi-intelligence.md`, …) were merged before this repo's git history begins and
> are not independently recoverable. Their bodies below are the surviving verbatim record.

## Index — spec → shipped as → atlas contribution

| § | Spec (former / canonical file) | Shipped as | Atlas contribution |
|---|---|---|---|
| 1 | `atlas-pypi-universe-split.md` (→ shipped-releases Part 1) | v7.9.0 (2026-05-13) | `pypi_universe` split; Phase D/H/J/M denominator fixes; schema v20; `pypi-only-candidates` CLI |
| 2 | `conda-forge-expert-v8.0.md` (→ Part 2) | v8.0.0 (2026-05-13) | `v_actionable_packages` view; Phase H freshness gate; **Phase N** (GH issues/PRs/checks); persona profiles |
| 3 | `atlas-pypi-intelligence.md` (→ Part 3) | v8.1.0 (2026-05-15) | **Phases O–S** PyPI intelligence layer (`pypi_intelligence` table, readiness score) |
| 4 | `atlas-appthreat-deep-signals.md` (→ Part 4) | v8.6.0 (2026-05-24) | EPSS + CWE overlays (`epss_scores`, `cwe_categories`); feeds `cve-watcher` |
| 5 | `atlas-phase-p-incremental.md` (→ Part 7) | v8.15.0 → v8.15.2 / v8.16.0 (2026-06-12) | Cost-capped incremental BigQuery **Phase P** (ClickHouse default from v8.16.0) |
| 6 | `atlas-phase-f-s3-backend.md` (→ Part 8; itself a 3-way merge of the Wave-1 umbrella + Wave-2 + Wave-3 intakes) | v7.6.0 + v8.17.0/18/19 (2026-05-10 → 2026-06-13) | **Phase F/F+** S3-parquet download backend; richer metrics; `platform-breakdown` / `pyver-breakdown` / `channel-split` CLIs |
| 7 | `atlas-phase-k-cron-runner.md` (→ Part 9) | v8.20.0 (2026-06-13) | Token-bucket **Phase K** multi-source upstream scheduler |
| 8 | `docs/specs/cyclonedx-universe-inventory.md` | CFE v8.73.0 (2026-07-06, Waves A–E) | Universe SBOM + inventory: `export-purls`, `mapping-gap`, `universe-sbom`, `inventory-match`, `add-handoff`, `library-futures`, `recommend-2027`; **schema v28→v29** |
| 9 | `docs/specs/lts-registry-gap.md` | CFE v8.74.0 (2026-07-06) | `lts-registry-gap` suggester (endoflife.date ↔ `v_actionable_packages` diff → `lts-registry.yaml` proposals) |
| 10 | `docs/specs/seed-gap-suggesters.md` | CFE v8.75.0 + v8.76.0 (2026-07-06) | `cwe-seed-gap`, `spdx-schema-gap`, `license-map-gap` read-only seed-map suggesters |

## Atlas specs not yet built (pointers only — not compiled here)

These are atlas specs in the backlog; they have not "built" anything yet. They stay
canonical in `docs/specs/` and join this compendium only if/when they ship:

- **`docs/specs/cfe-atlas-datapipeline-kedro-migration.md`** (`ready`, 1037 lines) — migrate
  the hand-rolled atlas orchestrator to a Kedro/Dagster/DuckDB stack (Waves 0 + A–H).
- **`docs/specs/trendshift-conda-forge.md` Track A** (`ready`) — cf_atlas **Phase T**
  GitHub-trending discovery engine (schema v30, `trending-candidates` CLI/MCP tool). Track B
  of that file is packaging work, not atlas.

## Deliberately excluded

`cfe-shipped-releases.md` Parts 5 (maturin/PyO3 generator hardening, v8.9.0), 6 (PR
CI-artifact downloader, v8.14.0) and 10 (graphifyy osx-arm64 fanout, closed effort) are
skill/packaging work, not atlas — they remain only in the consolidated archive.

---

<a id="p1"></a>

# Part 1 — pypi_universe split + Phase H denominator fix

> Formerly `atlas-pypi-universe-split.md` — shipped v7.9.0 (2026-05-13).
> Original frontmatter: `status: shipped; implemented_by: bmad-quick-dev; shipped_ref: "v7.9.0"; spec_updated: 2026-06-20`

# Tech Spec: Atlas Actionable-Scope Audit — Phase D / H / J / M

> **BMAD intake document.** Written for `bmad-quick-dev` (Quick Flow track —
> well-bounded, single-skill scope, 11 implementation stories in 4 waves).
> Run BMAD with this file as the intent document:
>
> ```
> run quick-dev — implement the intent in docs/specs/atlas-pypi-universe-split.md
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
| Surface area | `conda-forge-expert` skill — atlas pipeline (Phase D / H / J / M), schema v20, one new CLI / MCP tool |
| Scope | (1) Phase H denominator one-line fix; (2) Phase J + M archived-feedstock filter; (3) `pypi_universe` side-table extraction + Phase D refactor; (4) `pypi-only-candidates` CLI surfacing the new table |
| Out of scope | Persona-aware default profiles for `build-cf-atlas`; `v_actionable_packages` SQL view; Phase H `pypi_last_serial` freshness-gate (separate spec); dropping `vuln_total` column |
| Created | 2026-05-13 |
| Driven by | Audit transcript 2026-05-13 — phase-by-phase denominator review against `atlas-actionable-intelligence.md` |

---

## Background and Context

### The problem

A phase-by-phase audit of `cf_atlas.db`'s data-pull surface against
`atlas-actionable-intelligence.md` found that four of the seventeen
pipeline phases write data nobody reads, or fetch over a denominator that
includes rows no persona's CLI / MCP / SQL surface ever consumes:

1. **Phase H (`pypi-json` path)** — the SELECT in
   `_phase_h_eligible_pypi_names` filters only on
   `pypi_name IS NOT NULL + TTL`. Because Phase D inserts ~660k
   `relationship='pypi_only'` rows with `pypi_name` populated, Phase H's
   denominator is ~672k packages instead of the ~12k conda-linked rows
   the `behind-upstream` CLI actually queries. The downstream
   `upstream_versions` UPSERT (line 2585) already gates on
   `AND conda_name IS NOT NULL`, so the result of every
   pypi_only fetch is silently discarded after the network round-trip.
   The docstring claims "~25k requests"; actual cold-run cost is ~672k
   requests against pypi.org's 30 req/s ceiling at 3 workers ≈ **6+
   hours**, not the documented 30 min.

2. **Phase D `pypi_only` INSERTs** — Phase D fetches the PyPI Simple v1
   JSON (~40 MB, ~800k projects) and INSERTs a fresh `packages` row for
   every project not already on conda-forge. ~660k rows of bloat per
   build, consuming ~660k UPSERTs and persisting in the table that
   every CLI's "show me real packages" query has to filter past. Only
   one 📋-open admin query in the catalog reads these rows.

3. **Phase J (dependency graph)** — iterates every feedstock in the
   cf-graph tarball with no archived/inactive filter. Archived
   feedstocks contribute dependency edges to the `dependencies` table
   that `whodepends` and `whodepends --reverse` then have to filter at
   read time. Adds noise to the persona-actionable signal.

4. **Phase M (feedstock health)** — same shape as J: the
   `rows_to_process` SELECT filters on `feedstock_name IS NOT NULL` but
   not on `latest_status='active'` or `feedstock_archived=0`. Bot-status
   columns get written on archived feedstocks; `feedstock-health` queries
   then re-filter those rows out at read time.

The audit also found one cross-cutting issue: `packages.pypi_last_serial`
is written by Phase D on every build but **read by no other phase**.
The intended use (gate Phase H's full-JSON fetches to only rows whose
upstream actually moved) is unrealized. That's a separate optimization
covered in a follow-up spec — out of scope here.

### What's been ruled out

- **Removing Phase D entirely.** Phase D does two valuable things
  alongside the `pypi_only` INSERTs: (a) updates `pypi_last_serial` on
  conda-linked rows from the same Simple-API blob, and (b) discovers
  name-coincidence matches (PyPI name == conda name, not in parselmouth).
  Both stay; only the `pypi_only` INSERT branch moves.
- **Replacing the 40 MB Simple API fetch with per-package queries.**
  PyPI offers no bulk "give me serials for these 12k names" endpoint;
  the Simple v1 JSON is the only catalog-style fetch. The 40 MB
  download is necessary even when we only consume the 12k-row subset.
- **Per-package fetching to populate the universe** (e.g., one HTTP per
  PyPI project). 800k requests against pypi.org would be hostile and
  blocked. The Simple API's bulk shape is the right tool.
- **Dropping the "what's on PyPI but not on conda-forge" use case.**
  One 📋-open admin candidate-list query depends on the corpus. We
  preserve the data, just not in `packages`.
- **An `is_pypi_only` boolean column on `packages`.** Adding a column
  doesn't fix the bloat — the rows still exist in the working-set
  table. Separation by table is cleaner.

### What's available to leverage

- **Existing `_http.py` resolvers** for PyPI Simple endpoints
  (`_resolve_pypi_simple_urls`) and the `_fetch_with_fallback` helper —
  unchanged by this spec.
- **Schema migration framework** in `init_schema(conn)` already handles
  additive `ALTER TABLE` migrations idempotently (lines ~450–510). A new
  table + index follows the same pattern.
- **TTL-gate convention** (`PHASE_<X>_TTL_DAYS` + `<col>_fetched_at` < cutoff)
  used by Phases F / G / H / K / L. Phase D's universe-upsert side
  adopts the same convention.
- **Phase E's checkpoint pattern** (`save_phase_checkpoint(cursor=...)`)
  for resumable mid-run state — reused for the universe-upsert
  long loop.
- **Atomic-write helpers** (`atomic_writer` from `_http.py`) — already
  used by Phase E's cache writes; pattern extends to any new cache the
  spec might add (none planned).
- **`conda_name IS NOT NULL + latest_status='active' + feedstock_archived=0`
  triplet** already appears verbatim in Phases F / G / G' / K / L / N
  selectors. Phases H / J / M align to it.

### Verified facts (informational)

Counts measured against a freshly-built `cf_atlas.db` (2026-05-13):

| Metric | Value |
|---|---|
| Total `packages` rows | ~700k |
| Rows where `conda_name IS NOT NULL` | ~32k |
| Rows where `pypi_name IS NOT NULL` | ~672k |
| Rows where `relationship = 'pypi_only'` | ~660k |
| Rows passing the proposed `v_actionable_packages` filter (active, !archived, conda) | ~28k |
| Phase H pypi-json cold denominator (TODAY) | ~672k |
| Phase H pypi-json cold denominator (AFTER) | ~12k |
| Phase D writes per build (TODAY) | ~672k UPDATEs + INSERTs |
| Phase D writes per build (AFTER, daily lean) | ~12k UPDATEs |
| Phase D writes per build (AFTER, weekly universe pass) | ~12k UPDATEs + ~800k pypi_universe UPSERTs |
| Phase J `dependencies` rows from archived feedstocks | ~5-15% of total edges (estimated) |

---

## Goals

- **G1.** **Phase H denominator drops to conda-linked rows only.** Cold
  Phase H run on the `pypi-json` path completes in ~30 min (matching the
  docstring), not ~6 hours. Bandwidth and rate-limit pressure scale to
  the actionable-data subset.
- **G2.** **`pypi_only` rows stop polluting `packages`.** A new
  `pypi_universe` side table holds the directory of all PyPI projects;
  `packages` shrinks to the ~32k conda-forge subset. `SELECT COUNT(*)
  FROM packages` returns honest numbers; `detail-cf-atlas` no longer
  returns confusing pypi-only matches.
- **G3.** **Phase D split by cadence.** The cheap part (update
  conda-linked serials + discover name-coincidence) runs every build;
  the expensive part (refresh the 800k-row universe) runs on its own
  TTL (default weekly).
- **G4.** **Phase J + M operate on actionable rows only.** Dependency
  edges from archived feedstocks stop landing in the `dependencies`
  table; bot-status columns stop being written on archived rows.
  `whodepends` and `feedstock-health` results sharpen without read-side
  filter changes.
- **G5.** **Migration is self-healing.** Existing v19 atlases upgrade
  cleanly on next `init_schema`: the `pypi_only` rows move from
  `packages` to `pypi_universe` and are deleted from `packages` in one
  pass. No operator action required.
- **G6.** **One new CLI surfaces the universe.** `pypi-only-candidates`
  (CLI + MCP tool) reads from `pypi_universe LEFT JOIN packages` to
  produce the admin "on PyPI but not on conda-forge" candidate list
  that was 📋-open in `atlas-actionable-intelligence.md`.

## Non-Goals

- **NG1.** No persona-aware default profile for `build-cf-atlas`. That
  was raised in the same audit but is a separate, larger architectural
  shift (Phase E default-on, Phase N auto-scoping, per-registry Phase L
  scoping) — separate spec.
- **NG2.** No `v_actionable_packages` SQL view. The audit recommended it
  as enforcement infrastructure; it's a follow-up that prevents *future*
  drift but doesn't fix the current bugs. Out of scope so this spec
  ships small.
- **NG3.** No Phase H `pypi_last_serial` freshness-gate. Wiring D's
  serial into H's gate is a separate spec — it depends on this one
  landing first (Phase H's denominator must already be right) but adds
  schema (`pypi_version_serial_at_fetch` column) and gating logic that
  is independently reviewable.
- **NG4.** No `vuln_total` column cleanup. Audit found it unread; out
  of scope — handled as a schema v21 chore.
- **NG5.** No daily refresh of the universe. Weekly TTL is the default;
  operators can lower via `PHASE_D_UNIVERSE_TTL_DAYS` if they need
  fresher candidate-list data, but the spec doesn't optimize for that
  case.
- **NG6.** No Phase F / K / L / N changes. Those phases already have
  the correct denominator (active + !archived + conda_name); audit
  confirmed.

---

## Lifecycle Expectations

- **One-time migration cost** when first upgrading from schema v19 to
  v20: ~660k rows copied from `packages` to `pypi_universe` + ~660k
  DELETEs. Runs in a single transaction in `init_schema`; ~30 s wall on
  a typical SSD. Idempotent — re-running has no effect.
- **Steady-state per-build cost** (daily-lean Phase D):
  - 40 MB Simple API fetch (unchanged).
  - ~12k UPDATEs on `packages.pypi_last_serial` (a fraction of today's
    work).
  - ~few hundred name-coincidence UPSERTs.
  - Skip universe upsert when TTL is fresh.
- **Weekly cost** (universe upsert when TTL elapses):
  - Same 40 MB Simple API fetch.
  - ~800k UPSERTs against `pypi_universe`.
  - ~10–30 s wall clock.
- **Cold-build cost** (no prior data):
  - Phase D: full universe upsert (no TTL to gate against).
  - Phase H: ~30 min (12k full JSON fetches at 3 workers / 30 req/s
    ceiling), not the prior ~6 hours.
- **Storage delta**:
  - `packages` table shrinks by ~660k rows (~50–100 MB depending on
    column widths).
  - `pypi_universe` table grows by ~800k rows × 3 columns ≈ 30 MB.
  - Net: ~70 MB smaller `cf_atlas.db`, faster index scans on
    `packages`.

---

## Design

### 1. Schema v20 — `pypi_universe` side table

In `conda_forge_atlas.py` near the existing schema DDL (~line 270, next
to the `package_version_downloads` and `upstream_versions` table
definitions):

```sql
-- Phase D side table: the PyPI universe directory. One row per public
-- PyPI project. Separated from `packages` so the working set stays
-- conda-actionable. Refreshed on its own TTL (PHASE_D_UNIVERSE_TTL_DAYS,
-- default 7); the daily Phase D run updates pypi_last_serial on
-- conda-linked rows in `packages` without touching this table.
CREATE TABLE IF NOT EXISTS pypi_universe (
    pypi_name   TEXT PRIMARY KEY,
    last_serial INTEGER,
    fetched_at  INTEGER
);
CREATE INDEX IF NOT EXISTS idx_pypi_universe_serial
    ON pypi_universe(last_serial);
CREATE INDEX IF NOT EXISTS idx_pypi_universe_fetched
    ON pypi_universe(fetched_at);
```

Bump `SCHEMA_VERSION` from 19 → 20 in `conda_forge_atlas.py:113`.

### 2. Schema v20 — migration

In `init_schema(conn)` after the new table DDL, inside the existing v20
migration block (added next to the v17 → v18 block at ~line 489):

```python
# v19 → v20: pypi_only rows move from `packages` to `pypi_universe`.
# Self-healing: re-running is a no-op because the SELECT returns 0 rows
# after the DELETE; INSERT OR IGNORE handles any concurrent partial run.
v20_pre_count = conn.execute(
    "SELECT COUNT(*) FROM packages WHERE relationship = 'pypi_only'"
).fetchone()[0]
if v20_pre_count > 0:
    print(f"  v20 migration: moving {v20_pre_count:,} pypi_only rows "
          f"to pypi_universe...")
    conn.execute("BEGIN TRANSACTION")
    try:
        conn.execute("""
            INSERT OR IGNORE INTO pypi_universe (pypi_name, last_serial, fetched_at)
            SELECT pypi_name, pypi_last_serial, COALESCE(downloads_fetched_at, 0)
            FROM packages
            WHERE relationship = 'pypi_only'
              AND pypi_name IS NOT NULL
        """)
        conn.execute("DELETE FROM packages WHERE relationship = 'pypi_only'")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
```

The migration is wrapped in its own transaction so a crash mid-migration
doesn't leave half-migrated state. Idempotent: the `INSERT OR IGNORE` +
`DELETE` pair is safe to re-run.

### 3. Phase D refactor — daily lean + TTL'd universe upsert

Current `phase_d_pypi_enumeration` (line 998) has three branches in one
for-loop over the Simple API projects:
1. Update `pypi_last_serial` on rows where `pypi_name` already matches.
2. Discover name-coincidence matches.
3. INSERT `pypi_only` rows.

Refactor into a three-phase body where (3) becomes the universe upsert
gated by its own TTL:

```python
def phase_d_pypi_enumeration(conn):
    """Phase D: enumerate PyPI universe via Simple API v1.

    Two-tier write strategy:
      - Always: update `packages.pypi_last_serial` on conda-linked rows
        and discover name-coincidence matches. Drives the working-set
        freshness signal.
      - TTL-gated (default 7d): refresh `pypi_universe` side table with
        the full ~800k-project catalog. Surfaced via the
        `pypi-only-candidates` CLI.

    Tunables (env vars):
      - PHASE_D_DISABLED            : "1" to skip the entire phase
      - PHASE_D_UNIVERSE_DISABLED   : "1" to skip the universe upsert
                                      branch (keep the lean per-row work)
      - PHASE_D_UNIVERSE_TTL_DAYS   : days the universe table stays fresh
                                      before re-upserting (default 7)
    """
    t0 = time.monotonic()
    simple = _fetch_pypi_simple()  # unchanged: 40 MB, ~1s
    projects = simple.get("projects", [])

    # Branches (1) + (2): always run — cheap, drives Phase H gate.
    matched, coincidence = _phase_d_update_working_set(conn, projects)

    # Branch (3): universe upsert, TTL-gated.
    universe_upserts = 0
    universe_skipped_reason = None
    if not os.environ.get("PHASE_D_UNIVERSE_DISABLED"):
        ttl_days = int(os.environ.get("PHASE_D_UNIVERSE_TTL_DAYS", "7"))
        if _phase_d_universe_is_fresh(conn, ttl_days):
            universe_skipped_reason = f"universe TTL fresh (< {ttl_days}d)"
        else:
            universe_upserts = _phase_d_upsert_universe(conn, projects)
    else:
        universe_skipped_reason = "PHASE_D_UNIVERSE_DISABLED=1"

    elapsed = time.monotonic() - t0
    return {
        "projects_seen": len(projects),
        "matched_serial_updates": matched,
        "name_coincidence_promotions": coincidence,
        "universe_upserts": universe_upserts,
        "universe_skipped_reason": universe_skipped_reason,
        "duration_seconds": round(elapsed, 1),
    }
```

Helper functions (`_phase_d_update_working_set`,
`_phase_d_universe_is_fresh`, `_phase_d_upsert_universe`) encapsulate
the three sub-tasks. The `_phase_d_universe_is_fresh` helper checks
`SELECT MAX(fetched_at) FROM pypi_universe` against the TTL cutoff.

**Critical:** the existing INSERT branch (line 1083 `# PyPI-only row`)
is **removed entirely**. New rows go to `pypi_universe`, never to
`packages`.

### 4. Phase H one-line denominator fix

In `_phase_h_eligible_pypi_names` (line 2522):

```python
# BEFORE:
sql = (
    "SELECT DISTINCT pypi_name FROM packages "
    "WHERE pypi_name IS NOT NULL "
    "  AND COALESCE(pypi_version_fetched_at, 0) < ?"
)

# AFTER:
sql = (
    "SELECT DISTINCT pypi_name FROM packages "
    "WHERE pypi_name IS NOT NULL "
    "  AND conda_name IS NOT NULL "
    "  AND COALESCE(latest_status, 'active') = 'active' "
    "  AND COALESCE(feedstock_archived, 0) = 0 "
    "  AND COALESCE(pypi_version_fetched_at, 0) < ?"
)
```

Adopting the same triplet (active + !archived + conda) that Phases F /
G / G' / K / L / N already use makes Phase H structurally consistent
with the rest of the pipeline. The structural fix (G2: pypi_only rows
leave `packages`) makes the `conda_name IS NOT NULL` clause redundant
in steady state, but keeping it is defense-in-depth: if any future
code path repopulates pypi_only rows in `packages`, the gate still
holds.

Update the Phase H docstring "~25k requests" → "~12k requests" to
reflect reality.

### 5. Phase J archived-feedstock filter

In `phase_j_dependency_graph` (line 3976), the for-member loop over the
cf-graph tarball currently has no filter. Add a pre-pass that builds a
set of archived/inactive feedstock basenames from `packages`:

```python
# Build the skip set BEFORE the BEGIN TRANSACTION so the DELETE+INSERT
# inside the transaction sees a coherent snapshot.
inactive_feedstocks = set(
    row[0] for row in conn.execute(
        "SELECT DISTINCT feedstock_name FROM packages "
        "WHERE feedstock_name IS NOT NULL "
        "  AND (COALESCE(feedstock_archived, 0) = 1 "
        "       OR latest_status = 'inactive')"
    )
)

# Inside the tarball loop, after computing `feedstock_basename`:
if feedstock_basename in inactive_feedstocks:
    skipped_inactive += 1
    continue
```

Stats dict gains `skipped_inactive` so operators can audit the impact.

### 6. Phase M archived-feedstock filter

In `phase_m_feedstock_health` (line 4149), the `rows_to_process` SELECT
gains the same triplet:

```python
# BEFORE:
rows_to_process = list(conn.execute(
    "SELECT conda_name, feedstock_name FROM packages "
    "WHERE conda_name IS NOT NULL AND feedstock_name IS NOT NULL"
))

# AFTER:
rows_to_process = list(conn.execute(
    "SELECT conda_name, feedstock_name FROM packages "
    "WHERE conda_name IS NOT NULL "
    "  AND feedstock_name IS NOT NULL "
    "  AND COALESCE(latest_status, 'active') = 'active' "
    "  AND COALESCE(feedstock_archived, 0) = 0"
))
```

### 7. New CLI: `pypi-only-candidates`

Adds a thin Tier-2 wrapper at
`.claude/scripts/conda-forge-expert/pypi-only-candidates.py` calling a
canonical Tier-1 script at
`.claude/skills/conda-forge-expert/scripts/pypi_only_candidates.py`.

```python
# pypi_only_candidates.py — canonical impl
def main():
    parser = argparse.ArgumentParser(
        description="List PyPI projects that don't have a conda-forge equivalent."
    )
    parser.add_argument("--limit", type=int, default=100,
                        help="Maximum rows to return (default 100)")
    parser.add_argument("--min-serial", type=int, default=0,
                        help="Filter to projects with last_serial >= N "
                             "(rough proxy for activity)")
    parser.add_argument("--json", action="store_true",
                        help="Emit JSON instead of a text table")
    args = parser.parse_args()

    conn = open_db()
    rows = list(conn.execute("""
        SELECT pu.pypi_name, pu.last_serial, pu.fetched_at
        FROM pypi_universe pu
        LEFT JOIN packages p ON p.pypi_name = pu.pypi_name
        WHERE p.conda_name IS NULL
          AND pu.last_serial >= ?
        ORDER BY pu.last_serial DESC
        LIMIT ?
    """, (args.min_serial, args.limit)))
    # ... format and print
```

`pixi.toml` task: `[feature.local-recipes.tasks.pypi-only-candidates]`.
Test entry in `tests/meta/test_all_scripts_runnable.py` SCRIPTS list.
MCP tool wrapper in `.claude/tools/conda_forge_server.py` exposing
`pypi_only_candidates(limit, min_serial)`.

---

## Stories — 4 waves, 11 stories

### Wave 1 — Phase H one-line fix (ships immediately, no migration)

| ID | Story | Effort |
|---|---|---|
| **S1** | Add `conda_name IS NOT NULL + active + !archived` triplet to `_phase_h_eligible_pypi_names` SQL | XS |
| **S2** | Update Phase H docstring (~25k → ~12k requests) + add a unit test exercising the gate against a fixture with mixed conda-linked + pypi-only rows + update `reference/atlas-phases-overview.md` Phase H section | XS |

### Wave 2 — Phase J + M archived filter (independent, low-risk)

| ID | Story | Effort |
|---|---|---|
| **S3** | Phase J: pre-pass build of `inactive_feedstocks` set + skip-clause in the tarball-iteration loop + `skipped_inactive` stats field | S |
| **S4** | Phase M: add `latest_status='active' AND feedstock_archived=0` to `rows_to_process` SELECT + update unit tests for fixture coverage | XS |

### Wave 3 — `pypi_universe` side-table extraction (the architectural change)

| ID | Story | Effort |
|---|---|---|
| **S5** | Schema v20 migration: add `pypi_universe` table + indexes; bump `SCHEMA_VERSION`; idempotent migration block that copies existing `pypi_only` rows to the new table and DELETEs them from `packages` | S |
| **S6** | Refactor Phase D: extract `_phase_d_update_working_set`, `_phase_d_universe_is_fresh`, `_phase_d_upsert_universe` helpers; remove the legacy `INSERT INTO packages ... 'pypi_only'` branch entirely | M |
| **S7** | Add `PHASE_D_UNIVERSE_DISABLED` + `PHASE_D_UNIVERSE_TTL_DAYS` env vars + propagate to docstrings + add fixture-driven test for the daily-lean vs weekly-full split | S |
| **S8** | Update `reference/atlas-phases-overview.md` Phase D section (split daily-lean vs weekly-universe behavior; note the new table); update `reference/atlas-actionable-intelligence.md` to point the admin "on PyPI not on conda-forge" row at the new CLI; update `CLAUDE.md` reference list if schema mention surfaces | XS |

### Wave 4 — CLI surface + closeout

| ID | Story | Effort |
|---|---|---|
| **S9** | New canonical script `pypi_only_candidates.py` + Tier-2 wrapper + `pixi.toml` task + SCRIPTS-list entry in `tests/meta/test_all_scripts_runnable.py` + happy-path unit test | M |
| **S10** | New MCP tool `pypi_only_candidates` in `.claude/tools/conda_forge_server.py` + schema entry; flip the 📋-open row in `reference/atlas-actionable-intelligence.md` § Cross-cutting to ✅ shipped | S |
| **S11** | CFE retrospective per `CLAUDE.md` Rule 2: invoke `bmad-retrospective`; land findings as edits to `SKILL.md` / `reference/*` / `CHANGELOG.md` (skill version bump per semver — MINOR for the new CLI + schema migration); auto-memory feedback entry only if a cross-skill finding surfaces | M |

**Wave sequencing rationale.** Waves 1 + 2 are surgical, no schema
change, no migration. They ship value (the 56× Phase H denominator cut;
J / M cleanups) without waiting on Wave 3's larger refactor. Wave 3 is
the architectural shift gated on the schema v20 migration; Wave 4
delivers the operator-facing surface so the work doesn't ship invisibly.

---

## Acceptance Tests

For each wave, the BMAD agent runs the existing pytest suite plus
explicit new tests:

### Wave 1
- `tests/unit/test_phase_h_eligible.py::test_excludes_pypi_only_rows`
  — fixture has 10 conda-linked rows + 10 pypi_only rows; assert
  `_phase_h_eligible_pypi_names` returns exactly the 10 conda-linked.
- `tests/unit/test_phase_h_eligible.py::test_excludes_archived_and_inactive`
  — fixture has 5 active + 3 archived + 2 inactive conda-linked rows;
  assert only the 5 active are returned.
- Manual smoke: rebuild atlas, observe Phase H stats `eligible` count
  drops from ~672k to ~12k.

### Wave 2
- `tests/unit/test_phase_j.py::test_skips_archived_feedstocks` —
  fixture tarball has 5 active + 3 archived feedstocks; assert
  `dependencies` table after Phase J contains edges from only the 5
  active.
- `tests/unit/test_phase_m.py::test_skips_archived_feedstocks` —
  fixture has 5 active + 3 archived rows in `packages`; assert
  `bot_*` columns are written only on the 5 active rows.

### Wave 3
- `tests/unit/test_schema_v20_migration.py::test_pypi_only_rows_migrate`
  — start with a v19 fixture DB containing N pypi_only rows in
  `packages`; run `init_schema`; assert all N rows now in
  `pypi_universe` with matching serials and 0 remaining in `packages`.
- `tests/unit/test_schema_v20_migration.py::test_migration_is_idempotent`
  — run `init_schema` twice; second run is a no-op.
- `tests/unit/test_phase_d_split.py::test_daily_lean_skips_universe`
  — fixture has fresh `pypi_universe.fetched_at`; assert Phase D's
  `universe_upserts` is 0 and `universe_skipped_reason` is set.
- `tests/unit/test_phase_d_split.py::test_universe_refresh_on_ttl_expiry`
  — fixture has stale `fetched_at`; assert universe is re-upserted.

### Wave 4
- `tests/unit/test_pypi_only_candidates.py::test_returns_unmatched_only`
  — fixture has 5 packages with conda equivalents + 100 pypi_universe
  rows where 5 join to packages and 95 don't; assert CLI returns only
  the 95.
- `tests/unit/test_pypi_only_candidates.py::test_respects_min_serial_filter`.
- `tests/meta/test_all_scripts_runnable.py` passes with the new entry.
- MCP tool smoke test via the existing `test_mcp_tools_register.py`
  pattern.

### Cross-cutting
- Full atlas rebuild against a real connection produces a `cf_atlas.db`
  where `SELECT COUNT(*) FROM packages` ≈ 32k (down from ~700k) and
  `SELECT COUNT(*) FROM pypi_universe` ≈ 800k.

---

## Risks

| Risk | Mitigation |
|---|---|
| Migration runs on a 700k-row table and takes longer than expected on slow disks | Wrapped in single transaction; bounded by row count; logged with progress prints; idempotent re-run if interrupted |
| Some downstream caller (out-of-repo script, ad-hoc SQL) reads `relationship='pypi_only'` rows from `packages` | Low likelihood — no in-repo caller does. Mitigation: keep the `relationship` enum value defined in schema (don't drop it in v20); deprecate in v21 after a release of soak time. The MIGRATION_NOTES section of CHANGELOG flags the change. |
| `pypi-only-candidates` CLI without Phase D having ever run produces empty results | Helper detects empty `pypi_universe` and prints actionable "run `atlas-phase D` first" message. |
| Phase D's universe upsert under TTL pressure (e.g., very long-running atlas builds) leaves stale serials in `pypi_universe` | Fine — the universe table is reference data, not the working set. `pypi_last_serial` on `packages` updates every build regardless. |
| Test fixtures referencing `relationship='pypi_only'` rows in `packages` break post-migration | Audit pass during S5: grep for `'pypi_only'` across `tests/`; update any fixture that depended on the old shape. |
| The 40 MB Simple API fetch's failure mode changes (network flake mid-fetch) | Already handled by `_fetch_with_fallback` + `_resolve_pypi_simple_urls`; no change. |

---

## Rollout

### Pre-merge
- BMAD agent executes Waves 1-4 in order; each wave's tests pass before
  the next starts.
- Manual smoke run on the dev `cf_atlas.db` to confirm
  `pypi-only-candidates` returns sensible output (e.g., the top hit on
  `--limit 5 --min-serial 100000000` should be a real, active PyPI
  project with no conda counterpart — e.g., a niche framework or a
  recently-uploaded package).
- CFE skill version bumps per semver: 7.8.1 → **7.9.0** (MINOR — new
  CLI + new schema migration + audit-driven phase corrections).

### Merge order
- Single PR bundling all 4 waves, **or** four sequenced PRs (one per
  wave) if the BMAD agent prefers smaller review surface. Wave 1 alone
  is the highest-impact change; the others are additive.

### Post-merge
- `CHANGELOG.md` v7.9.0 entry summarizing the four findings + 56×
  Phase H denominator cut + the new `pypi_universe` table + the new
  CLI.
- `MIGRATION_NOTES` in CHANGELOG flagging schema v19 → v20 (existing
  atlases auto-migrate on next open; no operator action).
- Skill files updated per Rule 2 retro: `SKILL.md` § Atlas Intelligence
  Layer mentions the new `pypi-only-candidates` CLI; `INDEX.md` gains
  an entry under "I want to: query the cf_atlas"; `atlas-operations.md`
  mentions the new `PHASE_D_UNIVERSE_TTL_DAYS` tunable in the cron
  table.
- Auto-memory feedback entry: only if a cross-skill finding surfaces
  (e.g., BMAD's quick-dev workflow tripped on the schema-migration
  pattern in a way that warrants documenting). Most findings stay in
  skill files per Rule 2.

### Backout plan
- Schema v20 migration is reversible by hand (re-INSERT pypi_universe
  rows back into `packages` with `relationship='pypi_only'`). But the
  more practical backout is: revert the PR, then on next `init_schema`
  the v20 block is a no-op (no pypi_only rows in `packages` to migrate)
  but the table stays. Operators can `DROP TABLE pypi_universe` if they
  prefer a clean rollback; the CLI degrades to "table not found" with a
  clear error.

---

## Open Questions

1. **Should `pypi-only-candidates` rank by activity proxy beyond
   `last_serial`?** PyPI's serial counter is monotonic per project; it
   says nothing about download volume or upload age. A more useful
   ranking might join to a downloads dataset (BigQuery / pypistats) or
   simply use `MAX(fetched_at)` as a "was seen recently" proxy. **Out
   of scope for this spec; defer to a follow-up if the CLI proves
   useful enough to warrant.**
2. **Should the universe upsert use the existing parquet cache
   pattern?** No — the Simple API JSON is ~40 MB and changes daily; a
   parquet cache adds complexity without saving meaningful I/O.
3. **Should `relationship='pypi_only'` be retired from the schema in
   v20 or held over to v21?** Hold over for safety — schemas are
   forever-extending; one release of soak time is cheap.
4. **Should Phase D's per-row `pypi_last_serial` UPDATE also include
   `pypi_version_serial_at_fetch` shadow tracking for the Layer-2
   freshness gate?** No — that's a separate spec
   (`atlas-phase-h-serial-gate.md`, to be drafted) that depends on
   this one landing first. Keep them independent for review.

---

## References

### Source-of-truth code

- `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py`:
  - `phase_d_pypi_enumeration` (line 998) — current 3-branch impl
  - `_phase_h_eligible_pypi_names` (line 2509) — Phase H selector
  - `_phase_h_via_pypi_json` (line 2535) — the pypi-json fetch path
  - `phase_j_dependency_graph` (line 3976) — tarball iteration
  - `phase_m_feedstock_health` (line 4149) — `rows_to_process` selector
  - `init_schema` (~line 450) — schema migration framework
  - `SCHEMA_VERSION` (line 113) — bump to 20

### Related specs

- `docs/specs/atlas-phase-f-s3-backend.md` — the prior atlas spec;
  same BMAD-quick-dev shape, parquet-cache + Phase F+ extensions.
- (To be drafted) `docs/specs/atlas-phase-h-serial-gate.md` — Layer-2
  freshness gate using `pypi_last_serial`; depends on this spec.

### Audit context

- `.claude/skills/conda-forge-expert/reference/atlas-actionable-intelligence.md`
  — persona × goal × CLI catalog. Two rows shift status after this
  spec lands:
  - "On PyPI but not on conda-forge candidate list" → ✅ shipped
    (was 📋 open SQL only).
  - "Channel-wide Phase H operationalization" — moves closer to
    tractable; full closure is a follow-up.
- `.claude/skills/conda-forge-expert/reference/atlas-phases-overview.md`
  — per-phase data source + purpose + intel mapping. Phase D + Phase H
  + Phase J + Phase M sections updated in S2, S4, S8.
- `.claude/skills/conda-forge-expert/reference/atlas-phase-engineering.md`
  — rate-limit / atomic-write / checkpoint patterns. Unchanged by this
  spec; the new helpers in S6 inherit existing conventions.

### Documentation

- `.claude/skills/conda-forge-expert/SKILL.md` — Atlas Intelligence
  Layer + Critical Constraints (no changes); INDEX.md cross-link.
- `.claude/skills/conda-forge-expert/CHANGELOG.md` — v7.9.0 entry per
  Rule 2.
- `CLAUDE.md` — reference list update if the new table surfaces in the
  reference/ enumeration line.
- `.claude/skills/conda-forge-expert/quickref/commands-cheatsheet.md`
  — `pypi-only-candidates` CLI usage example.

---

<a id="p2"></a>

# Part 2 — v8.0.0 bundle — actionable view, Phase H freshness gate, persona profiles

> Formerly `conda-forge-expert-v8.0.md` — shipped v8.0.0 (2026-05-13; Wave C deferred).
> Original frontmatter: `status: shipped; implemented_by: bmad-quick-dev; shipped_ref: "v8.0.0"; spec_updated: 2026-06-20`

# Tech Spec: conda-forge-expert v8.0.0 — Structural Enforcement + Persona Profiles

> **BMAD intake document.** Written for `bmad-quick-dev` (Quick Flow track —
> bundled v8.0.0 release closing four deferred follow-ups from the
> v7.9.0 actionable-scope audit retro). ~22 implementation stories
> across 4 waves. Run BMAD with this file as the intent document:
>
> ```
> run quick-dev — implement the intent in docs/specs/conda-forge-expert-v8.0.md
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
| Surface area | `conda-forge-expert` skill — schema v21, atlas pipeline (Phase D / G / H / + every selector), `build-cf-atlas` orchestrator + new `--profile` flag, MCP server (auto-detection helpers), planning artifacts (PRD + architecture-cf-atlas + epics) |
| Scope | (A5) `v_actionable_packages` SQL view + structural enforcement meta-test; (A3) Phase H `pypi_last_serial` freshness gate (Layer 2 of the audit's serial-gate thread); (A6) drop `vuln_total` column from schema; (A4) persona-aware default profiles (`maintainer` / `admin` / `consumer`) for `build-cf-atlas` |
| Version | conda-forge-expert v7.9.0 → **v8.0.0** (MAJOR — A4 changes default behavior of `build-cf-atlas`) |
| Out of scope | Channel-wide Phase H/N cron operationalization (separate spec); per-version vdb-history snapshot side table for time-travel queries; multi-output feedstock per-output dep-graph (Phase J extension); CycloneDX Protobuf / SPDX RDF |
| Created | 2026-05-13 |
| Driven by | `_bmad-output/projects/local-recipes/implementation-artifacts/retro-atlas-pypi-universe-split-2026-05-13.md` action items A3 / A4 / A5 / A6 |
| Predecessor | `docs/specs/atlas-pypi-universe-split.md` (v7.9.0 — actionable-scope audit) |

---

## Background and Context

### The problem

The v7.9.0 actionable-scope audit closed four phase-denominator findings
but surfaced a deeper class of issues that are out-of-scope for a Quick
Dev pass and were deferred to follow-up specs. Each is independently
shippable but they share structural concerns + a schema bump, making a
bundled release coherent:

1. **Structural drift is invisible without structural enforcement.**
   Six phases (F/G/G'/K/L/N) used the canonical persona-filter triplet
   `conda_name IS NOT NULL AND latest_status='active' AND COALESCE(feedstock_archived,0)=0`
   correctly. Three (H/J/M) drifted. No test or lint rule caught it;
   v7.9.0 fixed each by-hand. The next phase author (or refactor) has
   no enforcement preventing the same drift.
2. **`pypi_last_serial` is collected but unused.** Phase D's daily-lean
   path populates `pypi_last_serial` on every conda-linked row from the
   40 MB PyPI Simple API dump. Phase H's gate uses only TTL — it
   re-fetches every package past TTL even when the upstream serial
   hasn't moved. Wiring the serial into Phase H's gate drops warm
   daily Phase H from ~5 min (TTL-boundary day) → ~30 s (only rows
   whose upstream actually moved).
3. **`vuln_total` column is written every Phase G run but read by
   nothing.** Audit verified: no CLI, MCP tool, SQL query, or report
   touches it. Pure write waste. Either expose via a CLI flag or drop.
4. **The build-cf-atlas default targets nobody.** It runs all 17 phases
   silently skipping 5 (E, G, K, N, G'), producing a degraded atlas
   where `whodepends`, `feedstock-health`, `cve-watcher`, and 5+ open
   📋 catalog entries return empty. The most common user (a maintainer
   with a few hundred feedstocks) needs E + N + maintainer-scoped K.

### What's been ruled out

- **Splitting into four separate releases.** The four sub-specs share
  schema v21 and would otherwise require four migrations + four retros
  + four CHANGELOG entries. Bundling is the cheaper coordination cost.
- **Holding the bundle for a v8.0.0 cut-line that includes additional
  unspecified items.** The four items here have well-bounded scope; adding
  speculative items would dilute the release. Future v8.x roadmap items
  (channel-wide Phase H cron, multi-output dep graph, per-version vdb
  history) get their own specs.
- **Making A4 (persona profiles) the entire v8.0.0.** A4 alone would be
  a substantial spec, but it depends on A5's view-based enforcement to
  prevent the new profile-aware defaults from re-creating the drift
  v7.9.0 just fixed. Bundling A5 + A3 + A6 + A4 gives the structural
  cleanup + the UX shift one coherent migration story.
- **Targeting v7.10.0.** A4's default-behavior change for `build-cf-atlas`
  is exactly the textbook MAJOR criterion. Operators with custom
  invocations expecting the v7.x silent-skip behavior need an explicit
  signal.

### What's available to leverage

- **The canonical persona-filter triplet** is already verbatim in
  six phases (F/G/G'/K/L/N selectors) — A5 extracts it into the
  view; A3 uses the view.
- **`pypi_last_serial`** is populated on every conda-linked row by
  v7.9.0's Phase D daily-lean path — A3 just needs to read it.
- **Phase E's cf-graph cache + Phase N's GraphQL batching** are already
  the right primitives for `--profile maintainer` to enable them by
  default — A4 just changes the gating from opt-in to opt-out.
- **`gh api user`** returns the authenticated GitHub user's login — A4
  uses it to auto-derive `PHASE_N_MAINTAINER` for `--profile maintainer`.
- **The v20 schema migration framework** in `init_schema` extends
  naturally to v21 (same `if v21_pre_count > 0:` pattern as v20).
- **The 6-phase precedent of `conda_name + active + !archived`** makes
  the view trivially correct: it's exactly what F/G/G'/K/L/N already
  query.
- **The `bmad-edit-prd` + `bmad-correct-course` pattern from v7.9.0**
  is the right shape for the v8.0.0 BMAD-artifact sync.

### Verified facts (informational)

Measured against the post-v7.9.0 atlas (verified 2026-05-13 09:43):

| Metric | Value |
|---|---|
| `packages` rows (conda-actionable working set) | 32,988 |
| `pypi_universe` rows (PyPI directory) | 786,302 |
| Schema version | 20 |
| Phases using canonical triplet | 6 (F/G/G'/K/L/N) directly; H/J/M also after v7.9.0 |
| Selectors that read `FROM packages WHERE conda_name IS NOT NULL ...` | 8 (counts include both query selectors + write gates) |
| Rows with `pypi_last_serial` populated | ~12,000 (all conda-linked rows post-Phase-D) |
| `vuln_total` reads in code/CLI/MCP/SQL | 0 |
| Default `build-cf-atlas` phases that silently skip on fresh install | 5 (E, G, K, G', N) |
| Open 📋 catalog rows gated on Phase N | 5 (gh-pulls, gh-issues, ci-red filter, abandonment composite, maintainer last-active) |

---

## Goals

- **G1.** **Structural drift becomes impossible.** A new `v_actionable_packages`
  SQL view encodes the canonical persona-filter triplet; six existing
  selectors refactor to `FROM v_actionable_packages` instead of `FROM
  packages WHERE conda_name IS NOT NULL AND ...`. A meta-test asserts
  every remaining `SELECT ... FROM packages WHERE ...` either uses the
  view OR has an inline `# scope: ...` justification comment. Next
  phase author can't accidentally drift.
- **G2.** **Phase H warm-daily wall-clock drops 10×.** With the serial-gate
  wired, daily Phase H runs only fetch rows whose `pypi_last_serial` moved
  since the last successful fetch. Warm-daily wall-clock drops from ~5
  min (TTL-boundary day) to ~30 s (typical day: 30-100 packages move).
- **G3.** **Schema cleanup ships the column drop.** `vuln_total` column
  removed from `packages` in schema v21 migration; Phase G stops writing
  it; cve-watcher CLI gains optional `--show-total` if/when the data is
  ever needed (compute from `vuln_critical + vuln_high + vuln_kev`).
- **G4.** **`build-cf-atlas --profile maintainer`** is the default for
  maintainer-scoped CLIs (`staleness-report --maintainer X`, etc.) and
  produces a complete atlas with E + J + M + K + N all populated for
  the maintainer's scope. Five 📋-open catalog rows flip to ✅.
- **G5.** **`--profile admin`** runs channel-wide N (multi-PAT-aware if
  configured) + full L + D universe upsert on weekly cadence.
- **G6.** **`--profile consumer`** prioritizes air-gap friendliness:
  Phase F via s3-parquet, Phase H via cf-graph, no Phase N, no Phase D
  universe upsert.
- **G7.** **Schema v21 migration is self-healing.** Existing v20 atlases
  upgrade cleanly on next `init_schema`: drop `vuln_total` column (via
  table rebuild — SQLite limitation), create `v_actionable_packages`
  view, add `pypi_version_serial_at_fetch` column (idempotent). No
  operator action.
- **G8.** **Persona profile auto-detection.** `--profile maintainer`
  auto-derives `PHASE_N_MAINTAINER` from `gh api user` when available.
  `--profile admin` warns if no multi-PAT rotation configured but
  proceeds with single-PAT degraded mode.
- **G9.** **Catalog flips reflect actual surface changes.** `atlas-actionable-intelligence.md`
  rows for "gh-pulls", "gh-issues", "feedstock-health --filter ci-red",
  "abandonment composite", "maintainer last-active" — all 5 currently
  📋-open — flip to ✅ shipped (V8.0.0+).

## Non-Goals

- **NG1.** No channel-wide Phase H/N cron operationalization. Separate
  spec; depends on PAT rotation strategy which is a deployment-level
  concern.
- **NG2.** No per-version vdb-history snapshot side table for
  time-travel CVE queries. Separate spec; touches Phase G' design.
- **NG3.** No multi-output feedstock per-output dep-graph (Phase J
  extension). Separate spec; touches Phase J + downstream `whodepends`.
- **NG4.** No new MCP tools for persona profiles. The `build-cf-atlas`
  CLI gains `--profile`; MCP exposure of the same is a follow-up if
  operators want programmatic profile selection.
- **NG5.** No `vuln_total` re-introduction. Audit confirmed zero
  consumers; this spec drops it. Future re-adds (e.g., for a dashboard
  CLI) would write a fresh column with explicit consumer commitment.
- **NG6.** No backward-compat shim for the dropped `vuln_total`. Direct
  schema migration — no `vuln_total_deprecated` rename or view.

---

## Lifecycle Expectations

- **One-time migration cost** when first upgrading from schema v20 to
  v21: `vuln_total` column drop requires SQLite table rebuild (~5-15 s
  on a 32k-row `packages` table). View + column-add are instant.
- **Steady-state per-build cost** (post-v8.0.0 with `--profile maintainer`
  as the documented default):
  - Phase E: same as v7.9.0 (cf-graph cache 7d TTL).
  - Phase H **warm daily**: ~30 s (serial-gated; only moved packages
    re-fetch).
  - Phase H **cold**: ~30 min (unchanged; serial-gate has no prior
    state to compare).
  - Phase N: ~30-60 s for ~700 feedstocks (auto-scoped to `gh api user`).
- **Per-build cost (admin profile)**: similar to maintainer scope plus
  channel-wide Phase N (~30 min) — only run weekly.
- **Per-build cost (consumer profile)**: similar to v7.9.0 (no Phase N,
  no Phase D universe upsert).
- **Storage delta**:
  - `packages` shrinks by ~10 MB (vuln_total column drop).
  - `pypi_version_serial_at_fetch` adds ~96 KB (12k INTEGER rows).
  - `v_actionable_packages` is a view (no storage cost).
  - Net: ~10 MB smaller `cf_atlas.db`.

---

## Design

### Part A — `v_actionable_packages` view + structural enforcement (A5)

#### Schema v21 (A5 component)

```sql
-- Canonical persona-filter triplet, encoded once as a view so phase
-- authors can't drift. Refactor existing selectors to read FROM
-- v_actionable_packages; new selectors do the same by default.
CREATE VIEW IF NOT EXISTS v_actionable_packages AS
SELECT *
FROM packages
WHERE conda_name IS NOT NULL
  AND COALESCE(latest_status, 'active') = 'active'
  AND COALESCE(feedstock_archived, 0) = 0;
```

#### Phase-selector refactor

Refactor 6 existing phase selectors to read from the view. Each
becomes `FROM v_actionable_packages` (drop the verbose triplet):

- `_phase_f_eligible_rows` (conda_forge_atlas.py:1696)
- Phase G eligible-rows (~line 2243)
- Phase G' eligible-rows (~line 4724)
- `_phase_h_eligible_pypi_names` (~line 2509) — must add `AND pypi_name IS NOT NULL` since the view doesn't include pypi-name filter
- `phase_k_vcs_versions` selector (~line 3209)
- `phase_l_extra_registries` selector (~line 3805)
- Phase N's `base_select` (~line 4456)

(Phases B, B.5, B.6, C, D, E, E.5, J, M write to or read from `packages`
without the actionable filter — leave them on direct `FROM packages`
with `# scope: ...` justification comments per the new meta-test.)

#### Structural enforcement meta-test

New `tests/meta/test_actionable_scope.py`:

```python
"""Every SELECT ... FROM packages WHERE ... must use v_actionable_packages
OR have a `# scope: ...` justification comment.

Prevents the kind of drift v7.9.0 fixed by-hand. New phase authors
either query the view (and inherit the canonical triplet) or
explicitly justify why a broader scope is needed.
"""
def test_packages_selectors_use_view_or_justify_scope():
    src = Path(SCRIPTS_DIR / "conda_forge_atlas.py").read_text()
    for match in re.finditer(r"SELECT [^;]+ FROM packages\b", src, re.DOTALL):
        # walk upward to find the preceding comment or context
        ... # see tests/meta/test_actionable_scope.py for full impl
```

### Part B — Phase H `pypi_last_serial` freshness gate (A3)

#### Schema v21 (A3 component)

```sql
-- Track the serial at the time of each successful Phase H fetch.
-- Compared against pypi_last_serial (populated by Phase D's daily-lean
-- path) to decide whether to re-fetch.
ALTER TABLE packages ADD COLUMN pypi_version_serial_at_fetch INTEGER;
CREATE INDEX IF NOT EXISTS idx_pypi_serial_at_fetch
    ON packages(pypi_version_serial_at_fetch);
```

#### Phase H gate refactor

```python
# BEFORE (v7.9.0):
sql = (
    "SELECT DISTINCT pypi_name FROM v_actionable_packages "
    "WHERE pypi_name IS NOT NULL "
    "  AND COALESCE(pypi_version_fetched_at, 0) < ?"
)

# AFTER (v8.0.0 — Layer 2):
sql = (
    "SELECT DISTINCT pypi_name FROM v_actionable_packages "
    "WHERE pypi_name IS NOT NULL "
    "  AND ("
    "       pypi_version_fetched_at IS NULL "       # never fetched
    "    OR pypi_last_serial != pypi_version_serial_at_fetch "  # upstream moved
    "    OR pypi_version_fetched_at < ? "           # safety re-check (30d cap)
    "  )"
)
```

Phase H's successful-fetch write also stamps the serial:

```python
conn.execute(
    "UPDATE packages SET pypi_current_version = ?, "
    "    pypi_current_version_yanked = ?, "
    "    pypi_version_fetched_at = ?, "
    "    pypi_version_source = 'pypi-json', "
    "    pypi_version_serial_at_fetch = ? "  # NEW
    "WHERE pypi_name = ?",
    (version, yanked_int, now, current_serial, pypi_name),
)
```

`current_serial` comes from the Phase H worker: either re-fetched from
the Simple API alongside the JSON (one extra row in `pypi_last_serial`
write-back per fetched row) OR read from `packages.pypi_last_serial`
(the value Phase D wrote on its most recent run — accurate enough for
gating since Phase D and Phase H both run daily).

### Part C — Drop `vuln_total` (A6)

#### Schema v21 (A6 component)

SQLite doesn't support `ALTER TABLE DROP COLUMN` in versions <3.35.0
(and even when supported, requires a rebuild for indexed/PK columns).
Use the standard rebuild pattern:

```python
# v20 → v21: drop vuln_total column (write-only, no consumer reads).
v21_drop_vuln_total = bool(list(conn.execute(
    "SELECT 1 FROM pragma_table_info('packages') WHERE name='vuln_total'"
)))
if v21_drop_vuln_total:
    print("  v21 migration: dropping unused vuln_total column from packages...")
    # SQLite ≥ 3.35 supports DROP COLUMN directly; fall back to rebuild
    # if older. conda-forge ships SQLite 3.46+, so the simpler path is
    # the documented one.
    conn.execute("ALTER TABLE packages DROP COLUMN vuln_total")
```

Phase G stops writing `vuln_total`. CHANGELOG breaking-change note:
"Column `packages.vuln_total` dropped in schema v21. Use
`vuln_critical_affecting_current + vuln_high_affecting_current +
vuln_kev_affecting_current` if a sum is needed."

### Part D — Persona-aware default profiles (A4)

#### New `--profile` flag on `build-cf-atlas`

```bash
# build-cf-atlas adds a --profile flag with three preset bundles:

pixi run -e local-recipes build-cf-atlas --profile maintainer
  # E default-on, N auto-scoped to `gh api user`, K (GitHub auth required),
  # L restricted to populated registries in scope, F via auto-source

pixi run -e local-recipes build-cf-atlas --profile admin
  # All maintainer features + channel-wide N (no PHASE_N_MAINTAINER),
  # D universe upsert on weekly cadence, full L

pixi run -e local-recipes build-cf-atlas --profile consumer
  # Air-gap friendly: F via s3-parquet, H via cf-graph cold-start,
  # no N, no D universe upsert, no K (or K skipped if no GitHub auth)

pixi run -e local-recipes build-cf-atlas  # no flag = default (today's behavior)
```

Profile resolution lives in `bootstrap_data.py` (the orchestrator
entry point); each profile is a dict of env-var defaults that gets
merged into `os.environ` before invoking the phase dispatcher:

```python
PROFILES = {
    "maintainer": {
        "PHASE_E_DISABLED": "",        # opt-out (default-on)
        "PHASE_N_ENABLED": "1",
        "PHASE_F_SOURCE": "auto",
        "PHASE_H_SOURCE": "auto",
        # PHASE_N_MAINTAINER set dynamically from `gh api user`
    },
    "admin": { ... },
    "consumer": {
        "PHASE_E_DISABLED": "",
        "PHASE_N_ENABLED": "",          # opt-in stays opt-in
        "PHASE_F_SOURCE": "s3-parquet",
        "PHASE_H_SOURCE": "cf-graph",
        "PHASE_D_UNIVERSE_DISABLED": "1",
    },
}
```

The auto-derivation of `PHASE_N_MAINTAINER` for `--profile maintainer`:

```python
import subprocess
def _auto_detect_gh_user():
    try:
        result = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        pass
    return None
```

If `gh` is unavailable or unauth'd, `--profile maintainer` prints a
warning and proceeds with channel-wide N (which is slower but
correct).

#### Default behavior change (the MAJOR-bump trigger)

`pixi run -e local-recipes build-cf-atlas` (no `--profile`) keeps
today's silent-skip behavior — backward-compat for cron jobs that
pin env vars manually. But the **documented default** in
`atlas-operations.md` flips to `--profile maintainer`. New
quickstart documentation tells users to use the profile.

To make this a true MAJOR signal: `build-cf-atlas` with no `--profile`
prints an end-of-run advisory:

> ⓘ No --profile specified. Consider `--profile maintainer` for the
> default maintainer-scoped atlas (enables Phase E + Phase N + auto-
> scoping). See `atlas-operations.md` for the full profile reference.

The advisory is opt-out via `BUILD_CF_ATLAS_QUIET=1`.

---

## Stories — 4 waves, ~22 stories

### Wave A — `v_actionable_packages` view + structural enforcement (A5, ~7 stories)

| ID | Story | Effort |
|---|---|---|
| **S1** | Add `v_actionable_packages` view to SCHEMA_DDL; bump SCHEMA_VERSION 20 → 21 | XS |
| **S2** | Refactor `_phase_f_eligible_rows`: `FROM v_actionable_packages` + drop verbose triplet | XS |
| **S3** | Refactor Phase G + Phase G' eligible-rows selectors to the view | S |
| **S4** | Refactor `_phase_h_eligible_pypi_names` to the view (keep `pypi_name IS NOT NULL`) | XS |
| **S5** | Refactor Phase K + Phase L eligible-rows selectors to the view | S |
| **S6** | Refactor Phase N's `base_select` to the view | XS |
| **S7** | New `tests/meta/test_actionable_scope.py`: assert every `SELECT ... FROM packages WHERE ...` either uses the view OR has `# scope: ...` comment | M |

### Wave B — Phase H serial-gate (A3, ~5 stories)

| ID | Story | Effort |
|---|---|---|
| **S8** | Schema v21: add `pypi_version_serial_at_fetch INTEGER` column + index | XS |
| **S9** | Phase H's pypi-json successful-fetch path writes `pypi_version_serial_at_fetch` alongside `pypi_version_fetched_at` | S |
| **S10** | Phase H eligible-rows gate becomes serial-aware (3-condition OR: never fetched / serial moved / 30d safety re-check) | S |
| **S11** | Phase H stat reporting: split `eligible` count into `eligible_never_fetched`, `eligible_serial_moved`, `eligible_safety_recheck` so operators can see why each row was selected | XS |
| **S12** | New `tests/unit/test_phase_h_serial_gate.py`: fixture with mixed serial states; assert only-moved rows are queued; assert safety re-check fires past 30d | M |

### Wave C — Drop `vuln_total` (A6, ~2 stories)

| ID | Story | Effort |
|---|---|---|
| **S13** | Schema v21 migration: `ALTER TABLE packages DROP COLUMN vuln_total`; remove `vuln_total` from Phase G's UPDATE statements; remove from `init_schema` ALTER-table list | XS |
| **S14** | Test: `tests/unit/test_schema_v21_migration.py` covers the column drop + idempotency (re-run = no-op) | XS |

### Wave D — Persona profiles (A4, ~8 stories)

| ID | Story | Effort |
|---|---|---|
| **S15** | `bootstrap_data.py`: define `PROFILES` dict (maintainer/admin/consumer) + `--profile` argparse flag + profile resolution that merges into env before phase dispatch | M |
| **S16** | `_auto_detect_gh_user()` helper: shells out to `gh api user --jq .login`; handles missing-gh / unauth / timeout gracefully; sets `PHASE_N_MAINTAINER` for `--profile maintainer` when available | S |
| **S17** | `_auto_detect_phase_l_sources()` helper: queries `v_actionable_packages` for which `<source>_name` columns are populated in scope; restricts `PHASE_L_SOURCES` accordingly for `--profile maintainer` | S |
| **S18** | End-of-run advisory print when no `--profile` is specified; opt-out via `BUILD_CF_ATLAS_QUIET=1` | XS |
| **S19** | Tests: `tests/unit/test_persona_profiles.py` exercises (a) profile resolution merges env correctly; (b) `--profile maintainer` enables E + N; (c) `--profile consumer` sets s3-parquet + cf-graph; (d) `--profile admin` runs channel-wide N; (e) `--profile maintainer` without `gh` prints warning + proceeds | M |
| **S20** | Update `reference/atlas-phases-overview.md`: each phase section gains a "Profile defaults" line indicating which profiles enable/disable it; new `## Profile Reference` appendix with the three profile bundles | S |
| **S21** | Update `reference/atlas-actionable-intelligence.md`: flip 5 📋-open Phase-N-gated rows to ✅ shipped (gh-pulls, gh-issues, ci-red filter, abandonment composite, maintainer last-active); update `## Status Summary` counts | S |
| **S22** | Update `guides/atlas-operations.md`: quickstart section documents `--profile maintainer` as the recommended default; cron snippet examples use profiles instead of raw env vars; troubleshooting "Phase N skipped" tip removed (auto-detect handles it) | S |

### Closeout

| ID | Story | Effort |
|---|---|---|
| **S23** | CHANGELOG.md v8.0.0 entry covering all 4 sub-specs + the MAJOR-bump rationale + the 5 catalog rows that flipped + the schema v20→v21 migration notes | M |
| **S24** | `config/skill-config.yaml` bump 7.9.0 → 8.0.0; SKILL.md "Atlas Intelligence Layer (v8.0.0)" heading; INDEX.md picks up new `--profile` quickstart | XS |
| **S25** | CFE retrospective per `CLAUDE.md` Rule 2: invoke `bmad-retrospective`; land findings | M |
| **S26** | `bmad-correct-course` for BMAD planning artifact sync: PRD (v1.1.1 → v1.2.0 — minor since this is a feature-level shift, or v2.0.0 if the PRD's MVP language changes substantively); architecture-cf-atlas + architecture-conda-forge-expert + epics + project-parts.json + sprint-change-proposal-YYYY-MM-DD; pin-only bumps across the rest | L |

### Wave sequencing rationale

Waves A → B → C → D is the dependency-respecting order:

- **A first**: the view + meta-test land before any new selector work
  so subsequent waves inherit the enforcement. Wave A is also
  zero-behavior-change (same rows returned, just via a view).
- **B second**: serial-gate refactors Phase H's selector — uses the
  view from A. Validates that the view-based refactor works under
  real selector changes.
- **C third**: small column drop; shares the v21 migration with A and
  B so all three schema changes apply in one `init_schema` pass.
- **D last**: profiles depend on the structural cleanup landing first
  so the new profile-aware defaults inherit the enforced filters.
  Also the most UX-facing wave; lands after the internal refactors
  prove stable.

**Two-PR vs one-PR strategy:** Waves A-C are tightly coupled (one
schema v21 migration). Wave D is independent (no schema change). Two
PRs is the cleaner review surface: PR #1 = A+B+C (structural +
performance + cleanup), PR #2 = D (UX). Both land before the v8.0.0
release tag.

---

## Acceptance Tests

For each wave, the BMAD agent runs the existing pytest suite plus
explicit new tests:

### Wave A
- `tests/unit/test_v_actionable_packages_view.py::test_view_returns_canonical_subset`
  — fixture with mixed conda-linked/pypi-only/archived/inactive rows;
  assert the view returns only conda-linked + active + !archived.
- `tests/unit/test_v_actionable_packages_view.py::test_refactored_selectors_match_old_results`
  — run the 6 refactored selectors against a v20-snapshot fixture +
  the equivalent post-v21 selectors; assert identical row sets.
- `tests/meta/test_actionable_scope.py::test_packages_selectors_use_view_or_justify`
  — parse `conda_forge_atlas.py`; every `SELECT ... FROM packages WHERE
  ...` either uses the view OR has a `# scope:` comment within 3 lines
  above. Fails if a future commit reintroduces drift.

### Wave B
- `tests/unit/test_phase_h_serial_gate.py::test_skips_unchanged_rows`
  — fixture with `pypi_last_serial == pypi_version_serial_at_fetch`;
  assert row is NOT eligible.
- `tests/unit/test_phase_h_serial_gate.py::test_includes_moved_rows`
  — fixture where `pypi_last_serial != pypi_version_serial_at_fetch`;
  assert row IS eligible.
- `tests/unit/test_phase_h_serial_gate.py::test_safety_recheck_past_30d`
  — fixture with `pypi_version_fetched_at` > 30d ago AND
  serial-unchanged; assert row IS eligible (safety re-check).
- `tests/unit/test_phase_h_serial_gate.py::test_never_fetched`
  — fixture with `pypi_version_fetched_at IS NULL`; assert eligible.
- `tests/unit/test_phase_h_serial_gate.py::test_successful_fetch_writes_serial`
  — call `_phase_h_via_pypi_json` against a mock fetcher; assert
  `pypi_version_serial_at_fetch` is populated post-fetch.

### Wave C
- `tests/unit/test_schema_v21_migration.py::test_drops_vuln_total_column`
  — start with v20 fixture DB containing `vuln_total` populated; run
  `init_schema`; assert column is gone from `packages`.
- `tests/unit/test_schema_v21_migration.py::test_migration_is_idempotent`
  — run `init_schema` twice; second run is a no-op.

### Wave D
- `tests/unit/test_persona_profiles.py::test_profile_maintainer_enables_e_and_n`
  — `--profile maintainer` sets `PHASE_E_DISABLED=""` and
  `PHASE_N_ENABLED=1`.
- `tests/unit/test_persona_profiles.py::test_profile_maintainer_auto_scopes_n`
  — mock `gh api user` to return "rxm7706"; assert
  `PHASE_N_MAINTAINER=rxm7706`.
- `tests/unit/test_persona_profiles.py::test_profile_maintainer_without_gh_warns_and_proceeds`
  — mock `gh` as unavailable; assert warning printed + N runs
  channel-wide.
- `tests/unit/test_persona_profiles.py::test_profile_consumer_sets_air_gap_sources`
  — assert `PHASE_F_SOURCE=s3-parquet`, `PHASE_H_SOURCE=cf-graph`,
  `PHASE_D_UNIVERSE_DISABLED=1`.
- `tests/unit/test_persona_profiles.py::test_profile_admin_runs_channel_wide_n`
  — assert no `PHASE_N_MAINTAINER` is set.
- `tests/unit/test_persona_profiles.py::test_no_profile_prints_advisory_unless_quiet`
  — run without `--profile`; assert advisory printed. Run with
  `BUILD_CF_ATLAS_QUIET=1`; assert silent.

### Cross-cutting
- Full atlas rebuild against the real connection (deferred to the next
  session if the MCP server holds the lock — same pattern as v7.9.0)
  produces a `cf_atlas.db` at schema v21 with no `vuln_total` column,
  `v_actionable_packages` view present, and Phase H eligible-rows
  drops sharply on the second run when only a few serials moved.

---

## Risks

| Risk | Mitigation |
|---|---|
| SQLite `ALTER TABLE DROP COLUMN` requires SQLite ≥ 3.35.0; older Debian/RHEL distros ship older SQLite | conda-forge ships SQLite 3.46+; the `pixi run -e local-recipes` env always satisfies this. Direct DROP COLUMN works. Fallback table-rebuild pattern documented in `_bmad-output/projects/local-recipes/planning-artifacts/architecture-cf-atlas.md` if needed for downstream copies. |
| Phase H serial-gate edge case: `pypi_last_serial` is NULL on a never-Phase-D-run atlas | Gate handles: `pypi_last_serial IS NULL` short-circuits to "needs fetch" via the existing `pypi_version_fetched_at IS NULL` clause and the 30d safety re-check. Tested fixture covers. |
| `gh api user` auth fails mid-run for `--profile maintainer` | Detected at profile-resolution time (start of run, not mid-phase); warning printed; `PHASE_N_MAINTAINER` left unset (runs channel-wide, slower but correct). |
| Operator's cron job pins env vars manually + uses `--profile` (conflict) | Profile resolution merges *defaults*; explicitly-set env vars win (the `os.environ.get(key, profile_default)` pattern). Operators with custom env keep their behavior. |
| Meta-test test_actionable_scope flags a legitimate `SELECT ... FROM packages` (e.g., admin candidate-list queries) | Justification mechanism: a `# scope: <reason>` comment within 3 lines above the SELECT marks it as deliberate. Meta-test parses and accepts. |
| MAJOR bump confuses cron-based downstream consumers | CHANGELOG MIGRATION_NOTES section explicitly lists the only behavior change: documented default flipped to `--profile maintainer`. No invocation breaks; the silent-skip behavior remains available via no-flag invocation. |
| 22 stories across 4 waves exceeds quick-dev token budget gates | Same pattern as v7.9.0: user explicit K (keep all) at the token gate; commit checkpoints at end of each wave so a context-rot mid-stream can resume from the last green wave. |

---

## Rollout

### Pre-merge
- Two-PR strategy: PR #1 lands waves A + B + C (one schema v21
  migration); PR #2 lands wave D (independent).
- BMAD agent executes waves in order; each wave's tests pass before
  the next starts.
- Manual smoke run on the dev `cf_atlas.db` after each wave to confirm
  expected behavior changes (Phase H eligible count drops on warm
  daily run; `--profile maintainer` populates E + N; etc.).
- CFE skill version bumps per semver: 7.9.0 → **8.0.0** (MAJOR — A4's
  documented-default change).

### Merge order
- PR #1 first: lands the schema migration + structural enforcement +
  serial-gate + column drop. Allows ~1-2 days of soak before PR #2.
- PR #2: lands persona profiles + 5 catalog row flips.
- Both PRs merged before v8.0.0 release tag.

### Post-merge
- `CHANGELOG.md` v8.0.0 entry summarizing the four sub-specs + the
  MAJOR-bump rationale + the explicit list of catalog rows that
  flipped from 📋 to ✅.
- `MIGRATION_NOTES` in CHANGELOG flagging:
  - Schema v20 → v21 (existing atlases auto-migrate on next open).
  - `packages.vuln_total` dropped (use the severity-banded counts).
  - Default-behavior signal: documented `build-cf-atlas` default
    flipped to `--profile maintainer`. No invocation breaks.
- Skill files updated per Rule 2 retro: `SKILL.md` § Atlas
  Intelligence Layer mentions profile defaults; `INDEX.md` gains
  quickstart with `--profile maintainer`; `atlas-operations.md`
  rewritten quickstart + cron snippets.
- Auto-memory feedback entry: only if a cross-skill finding surfaces
  (e.g., BMAD's quick-dev workflow needs the new profile-aware default
  documented as a CFE invariant). Most findings stay in skill files.

### Backout plan
- Schema v21 migration is reversible by hand (re-create the dropped
  column + restore via SQL). The more practical backout: revert the
  PR(s), then on next `init_schema` the v21 block is a no-op (column
  already dropped) and the view stays but isn't read by anything in
  the reverted code. Operators can `DROP VIEW v_actionable_packages`
  manually if they prefer a clean rollback.
- Wave D rollback (persona profiles): the `--profile` flag is additive;
  reverting removes the flag with no schema impact. Cron jobs that
  pinned env vars continue to work.

---

## Open Questions

1. **Should the v8.0.0 default `build-cf-atlas` invocation switch from
   no-profile (current silent-skip) to `--profile maintainer`?** This
   spec proposes "no flag keeps today's behavior + advisory print"
   rather than "no flag = maintainer profile" because true
   default-flip would silently break cron jobs. The documentation
   recommends `--profile maintainer`. **Defer until operator feedback
   on the advisory print: if no one notices the advisory, escalate to
   silent default-flip in v8.1.0.**
2. **Should `--profile maintainer` auto-derive `PHASE_N_MAINTAINER`
   from `gh api user` or require an explicit flag?** This spec proposes
   auto-derive. Edge case: a power-user with multiple GitHub identities
   may not want auto-detection — they can override via explicit
   `PHASE_N_MAINTAINER=<other-handle>`.
3. **Should `--profile admin` warn about missing multi-PAT rotation?**
   This spec proposes yes (admin-scope Phase N benefits from rotation
   to avoid secondary rate limits). Operators without rotation see
   warning + degraded mode.
4. **Should the meta-test apply to other files beyond
   `conda_forge_atlas.py`?** Phases write inside the atlas script;
   other scripts (`staleness_report.py`, etc.) read from the DB but
   don't have "phase selector" semantics. **Scope: atlas script only.**
5. **Does the PRD need a v1.x → v2.0.0 bump or stay at v1.x with a
   minor-bump?** The v8.0.0 skill version reflects a behavior shift;
   the PRD's stated requirements don't change (still "operator runs
   build-cf-atlas; gets an actionable atlas"). Recommend PRD MINOR
   bump (v1.2.0); no breaking PRD-level change.

---

## References

### Source-of-truth code (current state — v7.9.0 baseline)

- `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py`:
  - `SCHEMA_VERSION` (line 135) — bump to 21
  - SCHEMA_DDL block (~line 270) — add view
  - `init_schema` migration block (~line 489) — add v21 sub-block (3 changes: view + column + drop)
  - `_phase_f_eligible_rows` (line 1696)
  - Phase G eligible-rows (~line 2243)
  - Phase G' eligible-rows (~line 4724)
  - `_phase_h_eligible_pypi_names` (line 2509)
  - Phase K eligible-rows (~line 3209)
  - Phase L eligible-rows (~line 3805)
  - Phase N eligible-rows (~line 4456)
- `.claude/skills/conda-forge-expert/scripts/bootstrap_data.py` — primary
  edit surface for Wave D (`--profile` flag + PROFILES dict + auto-detect)
- `.claude/skills/conda-forge-expert/scripts/atlas_phase.py` — `_reset_ttl`
  helper may need a `pypi_version_serial_at_fetch` reset target for
  Wave B (mirror existing `pypi_version_fetched_at` reset pattern)

### Related specs

- `docs/specs/atlas-pypi-universe-split.md` — predecessor (v7.9.0).
  This v8.0.0 spec implements 4 deferred follow-ups from that effort.
- `docs/specs/atlas-phase-f-s3-backend.md` — sibling spec; Phase F
  air-gap backend already shipped (v7.6.0). No conflicts.

### Audit context

- `_bmad-output/projects/local-recipes/implementation-artifacts/retro-atlas-pypi-universe-split-2026-05-13.md`
  — action items A3 / A4 / A5 / A6 each map to one wave in this spec.
- `.claude/skills/conda-forge-expert/reference/atlas-actionable-intelligence.md`
  — five 📋-open rows that flip to ✅ in Wave D.
- `.claude/skills/conda-forge-expert/reference/atlas-phases-overview.md`
  — per-phase data source / purpose / actionable intelligence (added
  v7.9.0); Wave D extends with "Profile defaults" lines.
- `.claude/skills/conda-forge-expert/reference/atlas-phase-engineering.md`
  — engineering rule book; unchanged by this spec.

### Documentation

- `.claude/skills/conda-forge-expert/SKILL.md` — Atlas Intelligence
  Layer + Critical Constraints; v8.0.0 heading update.
- `.claude/skills/conda-forge-expert/CHANGELOG.md` — v8.0.0 entry per
  Rule 2 + MIGRATION_NOTES.
- `.claude/skills/conda-forge-expert/guides/atlas-operations.md` —
  quickstart + cron snippets rewritten for `--profile`.
- `CLAUDE.md` — add `docs/specs/conda-forge-expert-v8.0.md` to the
  BMAD-consumable spec list.
- `.claude/skills/conda-forge-expert/quickref/commands-cheatsheet.md` —
  `--profile` usage examples.

---

<a id="p3"></a>

# Part 3 — PyPI intelligence layer (Phases O–S)

> Formerly `atlas-pypi-intelligence.md` — shipped v8.1.0 (2026-05-15).
> Original frontmatter: `status: shipped; implemented_by: bmad-quick-dev; shipped_ref: "v8.1.0"; spec_updated: 2026-06-20`

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

> **🛑 Erratum (2026-06-12, v8.14.3 hot-patch).** This spec's cost claims for
> Phase P (lines 105–111, 134, 245, 437, 743) state "~30 GB scanned per
> query, within the 1 TB/month free tier". That number is **wrong by
> ~1000×**. The real per-run scan is **~2.5–4 TB** (~$15–25/run at on-demand
> $6.25/TB); pre-fix queries occasionally degraded to ~25–45 TB scans
> (~$170+/run). A 2026-06-12 operator invoice surprise of **$500+** was the
> trigger to investigate. The v8.14.3 hot-patch adds dry-run preflight +
> `maximum_bytes_billed` hard cap on the existing single-shot query; the
> v8.15.0 architectural fix (`docs/specs/atlas-phase-p-incremental.md`)
> replaces it with an incremental-refresh design that drives steady-state
> cost below $1/run while preserving full per-package exactness. **Read
> those two documents** for current behavior. This spec's body below
> records what shipped in v8.1.0 and is preserved as-is for historical
> context.

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

---

<a id="p4"></a>

# Part 4 — EPSS + CWE overlays

> Formerly `atlas-appthreat-deep-signals.md` — shipped v8.6.0 (2026-05-24).
> Original frontmatter: `status: shipped; implemented_by: bmad-quick-dev; shipped_ref: "conda-forge-expert v8.6.0"; spec_updated: 2026-06-20`

# Tech Spec: AppThreat Deep Signals — blint hardening + EPSS + CWE rollup + withdrawn filter

> **BMAD intake document.** Written for `bmad-quick-dev` (Quick Flow track —
> additive enrichment layer that reuses the Path C overlay pattern shipped in
> v8.5.3). ~18 implementation stories across 4 waves. Run BMAD with this file
> as the intent document:
>
> ```
> run quick-dev — implement the intent in docs/specs/atlas-appthreat-deep-signals.md
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
| Surface area | `conda-forge-expert` skill — schema v23 → v24 migration in Wave A provisioning `epss_scores` + `cwe_categories` (kept) + `package_hardening` (dropped in Wave D's v25 cleanup, Wave C cancelled); 2 new fetcher CLIs (`fetch-epss`, `fetch-cwe-catalog`); Phase G + G' overlay enhancements for EPSS-max + CWE rollup (withdrawn filter dropped pre-Wave-B; Phase T/U + `blint-channel-top-n` cancelled pre-Wave-C). Final shipped surface: 2 new tables + 2 new fetcher CLIs + Phase G/G' overlay wiring + Wave D persona-profile + Wave D schema v25 cleanup. |
| Scope | Four signal expansions surfaced by the v8.5.3 DW12/DW13 retro: **(A)** blint hardening profiles for built artifacts (PIE/RELRO/stack-canary/NX); **(B)** EPSS scores (FIRST.org `epss_scores-current.csv.gz`) joined per CVE; **(C)** CWE category rollups (MITRE CWE catalog → high-level RCE/DoS/traversal/etc. labels) folded into Phase G/G' output; **(D)** withdrawn-advisory filter excluding OSV `withdrawn`-marked entries from vuln counts. Architecture mirrors the DW13 Path C pattern: external-catalog fetcher + side table + Phase G/G' overlay helper. |
| Version | conda-forge-expert v8.5.x → **v8.6.0** (MINOR — additive features, no breaking change; new fetchers / phases / CLI / schema additions, no deprecations) |
| Out of scope | Full-channel blint scan (we'd need to download every `.conda` artifact — ~150 GB; Phase T is **bounded** to either locally-built `build_artifacts/` OR a top-N CVE-flagged slice); CWE → CVSS v4 metric inference; auto-yanking of conda packages based on EPSS; CVSS v4 ingestion (separate spec — NVD's CVSS v4 rollout still incomplete); `cdxgen` / `atom` / `dep-scan` integration (see "What's been ruled out" §); per-CVE EPSS history (we store the latest snapshot only; FIRST.org's daily CSV is overwrite-only — historical trends would need our own snapshot retention table, deferred) |
| Created | 2026-05-23 |
| Predecessor | `docs/specs/conda-forge-expert-v8.0.md` (v8.0.0 — schema v21 + persona profiles); `docs/specs/atlas-pypi-intelligence.md` (v8.1.0 — schema v22 + Phase O-S); CHANGELOG v8.5.3 DW13 entry (Path C overlay pattern this spec reuses) |
| Driven by | 2026-05-23 DW12/DW13 retro at `_bmad-output/projects/local-recipes/implementation-artifacts/retro-dw12-dw13-2026-05-23.md` § "Follow-ups (DW-track candidates for the PRD)" — items 1-4. Also the post-DW13 conversation evaluating an unrelated "AppThreat Deep Security & Dependency Graph" workflow proposal (filed nothing useful; ruled out below). |

---

## Background and Context

### The problem

`v8.5.3` shipped the CISA KEV overlay (DW13 / Path C), which surfaced **exactly one** actionable feedstock channel-wide (`salt-2016.3.0`, 3 KEV CVEs). That's correct — most CISA-catalogued CVEs target OS software (Windows, Cisco IOS, Fortinet, Ivanti, Adobe) that doesn't map to conda-forge package coordinates. But the narrow result also tells us KEV is a **necessary but not sufficient** lens for prioritizing channel-wide CVE response. Three signals would materially expand the actionable surface:

- **CWE category** — vdb returns `CWE-79` (XSS) and `CWE-22` (path traversal) and `CWE-94` (code injection) per CVE. Without a category rollup, the operator has to grep the per-CVE listings by hand to triage "which of these are RCE vs which are info-disclosure?" A `vuln_cwe_categories` column rolling these up into 5-8 high-level buckets ("RCE", "DoS", "Info-Disclosure", "Auth-Bypass", "Memory-Safety", "Traversal", "Injection", "Other") lets the maintainer triage by severity *type*, not just by count.

- **EPSS** (Exploit Prediction Scoring System) — FIRST.org's free daily CSV (`epss_scores-current.csv.gz`, ~3 MB) assigns every CVE a 0.0-1.0 exploitation-probability score plus a 0-100 percentile. A medium-severity CVE with EPSS 0.94 (in the worst 6%) is operationally more dangerous than a critical-severity CVE with EPSS 0.02. cf_atlas today ranks by Critical/High count, missing the dimension that distinguishes "theoretical critical" from "actively exploited in the wild" — which is precisely what EPSS quantifies.

- **Withdrawn-advisory filter** — OSV and GHSA records can be marked `withdrawn` when the advisory is retracted (false positive, duplicate, scope correction). vdb returns withdrawn records inline with active ones; cf_atlas inherits that inflation in `vuln_total` and the affecting-version counts. A pre-2024 audit of OSV showed ~5-8% of Python ecosystem advisories carry a `withdrawn` field at any given time. Filtering withdraws cleans the count without losing signal.

Separately, **blint hardening profiles** (PIE, RELRO, stack canary, NX bit, fortify-source) are a *binary-property* signal that vdb cannot provide because vdb is CVE-database-only. AppThreat's `blint` reads ELF/PE/Mach-O headers and reports compile-time hardening. For conda-forge, this is the operator question "are the binaries my feedstock ships hardened against memory-corruption exploitation?" — a real question with no atlas-side answer today. Scope-bounded to either the maintainer's local `build_artifacts/` or a top-N CVE-flagged channel slice (full-channel scan would require downloading ~150 GB of `.conda` files).

### What's been ruled out

- **Full-channel blint scan.** Downloading every `.conda` artifact across the channel for binary inspection is ~150 GB of fetch and many hours of CPU. Phase T scans (1) the operator's local `build_artifacts/` after `pixi run recipe-build` (the per-maintainer view), OR (2) an admin-bounded top-N slice of CVE-flagged packages (the `--top-cves` mode of `blint-channel-top-n`).

- **`cdxgen` / `atom` / `dep-scan` integration for the channel-wide phase pipeline.** Verified 2026-05-23 against `lib/helpers/utils.js` lines 9798-9920 in CycloneDX/cdxgen: cdxgen **does** support pixi via `parsePixiLockFile` — it reads `pixi.lock` and emits proper `pkg:conda/...` purls (per the in-source comment: `"pkg:{kind}/{name}@{version}-{build}?os={os}"` where `{kind}` comes directly from the lock entry — `conda` for channel-installed packages, `pypi` for pip-installed ones in the same lock). It captures URL, sha256, license, license_family, and `depends:` edges. The README doesn't advertise this; the docs site does (`createPixiBom()` short-circuit per `ARCHITECTURE_ECOSYSTEM_EXAMPLES?id=python-example`). **However**: cdxgen requires `pixi.lock` as input — it does **not** parse `recipe.yaml` or `meta.yaml` (which are the conda-forge authoring artifacts cf_atlas's phase pipeline operates on). It produces an *environment-level* SBOM ("what does this pixi workspace install?"), not a *channel-level* dependency graph ("what does every active feedstock depend on?"). The former is a strict subset of the latter: cf_atlas Phase B (channel inventory) + Phase J (294,830 cf-graph dep edges across 27,499 feedstocks) already supersede what cdxgen-on-one-pixi.lock could contribute at the atlas layer. Where cdxgen-on-pixi.lock **would** add value is as a new input format to `scan_project` (alongside the existing `--conda-env`, `--venv`, `--sbom-in` modes) — operator workflow: `pixi run … fetch_with_pixi … && scan-project --pixi-lock pixi.lock`. That integration is filed as a small follow-up after v8.6.0 (separate from this spec's blint/EPSS/CWE/withdrawn scope) — see Appendix A § "Where cdxgen-on-pixi.lock would belong." AppThreat's `atom` slices application source code (no relevance to a recipe directory). AppThreat's `dep-scan` is a vdb frontend; cf_atlas already invokes vdb directly via `vdb.lib.search`, so `dep-scan` would add subprocess overhead without new signal. (Sources: `lib/helpers/utils.js@9798-9920` verified at https://github.com/CycloneDX/cdxgen on 2026-05-23; vdb already imported in `phase_g_vdb_summary` and `phase_g_prime_per_version_vulns`.)

- **Per-CVE EPSS history table.** FIRST.org's `epss_scores-current.csv.gz` is overwrite-only (daily snapshot of current state). EPSS history-of-history would require us to snapshot the CSV ourselves with a retention table. Defer to v8.7.x — the immediate value is "what's the current EPSS for this CVE?" not "how did this CVE's EPSS trend?"

- **CVSS v4 ingestion.** NVD's CVSS v4 rollout is incomplete (most CVEs still carry only v2/v3.x); vdb's `_walk_for_cvss` handles v2/v3 only. Separate spec when NVD coverage stabilizes (likely 2027).

- **Auto-yanking of conda packages by EPSS or KEV.** cf_atlas surfaces signals; the maintainer or admin decides what to mark-broken. Out of scope.

- **`vuln_*_affecting_current` rollup re-engineering.** DW12 already shipped both the `v_current_version_vulns` view AND the `_phase_g_sync_current_rollup` tail step. CWE/EPSS/withdrawn signals layer ON TOP of the existing rollup, not under it.

### What's available to leverage

- **DW13 Path C pattern proved out.** `scripts/cisa_kev_fetcher.py` + `cisa_kev` table + `_load_kev_cves` helper + Phase G/G' overlay loop is the template for both Path B (EPSS) and Path D (CWE rollup). New phases T and U mirror this structure end-to-end. Three-place rule + filename-match-canonical convention codified in `feedback_cfe_new_script_three_places.md` apply.
- **vdb's per-CVE record already carries CWE.** `detail_cf_atlas._walk_for_cwe(d)` is in production; we just need to aggregate per package instead of displaying per CVE.
- **vdb's per-CVE record already carries `withdrawn` for OSV-backed records.** `_extract_vuln_fields` doesn't currently surface it; one-line addition.
- **`blint` is pip-installable** (`owasp-blint` on PyPI) and `pixi`-friendly (no native deps beyond Python). Adding it to the `vuln-db` env's pypi-dependencies costs ~30 MB.
- **MITRE CWE catalog is a single XML/CSV file** at https://cwe.mitre.org/data/csv/2000.csv.zip (Research Concepts view, ~2 MB compressed). Stable schema since 2012.

### Verified facts (informational)

- **FIRST.org EPSS feed URL:** `https://epss.cyentia.com/epss_scores-current.csv.gz` (per FIRST.org docs at https://www.first.org/epss/data_stats — published daily, current-day snapshot, no auth, no rate limit documented but conservative concurrency=1 advised).
- **FIRST.org EPSS row count (Apr 2026):** ~280,000 CVEs (every CVE since 1999 with sufficient data for the model).
- **MITRE CWE catalog row count:** ~960 CWE entries (Research Concepts) → mapped to 5-8 cf_atlas categories via a one-time hand-curated lookup committed in this repo.
- **OSV `withdrawn` field semantics:** ISO-8601 timestamp when the advisory was retracted; presence-of-field = withdrawn-state. (Per OSV schema 1.6 at https://ossf.github.io/osv-schema/.)
- **`blint` output shape:** JSON per binary with `securityProperties` array containing `{name, value}` pairs (e.g., `{"name": "PIE", "value": "yes"}`). One file scan returns ~6-8 hardening properties. (Per `blint --help` and sample runs.)

---

## Goals

- **G1.** **`epss_scores` side table** (schema v24) populated by a new `fetch-epss` CLI from FIRST.org's daily CSV. Joined on `cve_id` (same pattern as `cisa_kev`). Phase G + G' overlay loop reads max-EPSS per package and writes new columns `vuln_max_epss_score` (REAL 0.0-1.0) and `vuln_max_epss_percentile` (REAL 0-100) into `packages` + `package_version_vulns`.

- **G2.** **`cwe_categories` reference table + `vuln_cwe_top` rollup**. New `fetch-cwe-catalog` CLI pulls MITRE's CSV once (TTL 90 d — CWE catalog is slow-changing); a committed `cwe_categories_seed.json` provides the cf_atlas-specific 5-8 high-level category mapping (RCE / DoS / Info-Disclosure / Auth-Bypass / Memory-Safety / Traversal / Injection / Other). Phase G + G' aggregate per-CVE CWE into per-package `vuln_cwe_top` (most-frequent category) + `vuln_cwe_categories_json` (full category-count map).

- **G3.** **Withdrawn-filter applied at Phase G/G' loop site**. `_extract_vuln_fields` (in `detail_cf_atlas.py`) gains a `withdrawn` boolean; Phase G/G' skip any `affecting[i]` where `withdrawn=True`. The `vuln_total` baseline column ALSO gets a sibling `vuln_total_active` (active-only count). Old column retained for trend continuity.

- **G4.** **Phase T — blint hardening profiles** for built `.conda` artifacts. Two modes:
  - **Local mode (default):** scans `build_artifacts/<config>/<subdir>/*.conda` produced by `pixi run recipe-build`. Writes per-package rows into `package_hardening` keyed on `(conda_name, version, subdir)`. Per-maintainer surface; runs in ~seconds per artifact.
  - **Admin top-N mode:** opt-in via `blint-channel-top-n --top 100 --by vuln_critical_affecting_current`. Downloads N highest-risk `.conda` files from anaconda.org, runs blint, populates `package_hardening`. Bounded to top-100 by default; configurable via `BLINT_TOP_N_LIMIT`.

- **G5.** **Phase U — EPSS overlay**. Loads `epss_scores` into a `dict[cve_id, (score, percentile)]` once at phase start; Phase G + G' compute `vuln_max_epss_score = max(epss_scores.get(v['id'], 0.0) for v in affecting)`. Same pattern as DW13 KEV overlay; degrades cleanly to 0.0 when `epss_scores` table is empty.

- **G6.** **New CLI flags.** `staleness-report --by-epss` sorts by max-EPSS across the feedstock; `staleness-report --has-cwe RCE` filters to feedstocks with an RCE-category CVE in current. `my-feedstocks` adds `--epss` and `--cwe` columns. `cve-watcher --epss-threshold 0.7` filters delta to high-EPSS CVEs only.

- **G7.** **Persona profile integration**. `--profile admin` enables Phase T (admin top-N) + Phase U + auto-runs `fetch-epss` daily + `fetch-cwe-catalog` weekly. `--profile maintainer` enables Phase T (local mode only) + Phase U + `fetch-epss` daily. `--profile consumer` runs Phase U if `epss_scores` is pre-populated (offline-friendly); skips Phase T entirely.

- **G8.** **Schema v23 → v24 migration is self-healing**. New tables created via `CREATE TABLE IF NOT EXISTS`; new columns added via `ALTER TABLE` in the existing ADD-COLUMN migration block (between v21 and v22 patterns). Existing v23 atlases upgrade cleanly on next `init_schema` call.

- **G9.** **Catalog flips reflect actual surface changes.** `reference/atlas-actionable-intelligence.md` admin section flips:
  - "EPSS score per package" (📋 → ✅)
  - "CWE category breakdown per package" (📋 → ✅)
  - "Binary hardening profile per feedstock" (📋 → ✅)
  - "Filter CVE count by active-only (exclude withdrawn)" (📋 → ✅ via `vuln_total_active`)

- **G10.** **CHANGELOG + retro per CLAUDE.md Rule 2.** Single CHANGELOG v8.6.0 entry; standard retro at `_bmad-output/projects/local-recipes/implementation-artifacts/retro-appthreat-deep-signals-<DATE>.md`.

## Non-Goals

- **NG1.** Full-channel binary scan. Phase T is bounded — local artifacts (per-maintainer) or top-N CVE-flagged (admin). No "blint every .conda in the channel" mode.
- **NG2.** EPSS history retention. Latest-snapshot only. v8.7.x candidate.
- **NG3.** CWE → CVSS v4 metric inference. CVSS v4 separate spec.
- **NG4.** `cdxgen` / `atom` / `dep-scan` integration — verified ruled out (see §"What's been ruled out").
- **NG5.** Auto-yanking. cf_atlas surfaces; operator decides.
- **NG6.** Reverse blint deltas (compare hardening between versions). v8.7.x.
- **NG7.** Static-analysis layer (`bandit`, `semgrep`). Out of scope — cf_atlas tracks *upstream* vulns, not first-party Python code quality.
- **NG8.** Replacement of `vuln_total` with `vuln_total_active`. Old column retained for backward-compat + trend continuity. New column added alongside.

---

## Lifecycle Expectations

- **One-time migration cost** (v23 → v24): `CREATE TABLE epss_scores` + `CREATE TABLE cwe_categories` + `CREATE TABLE package_hardening` + ~6 `ALTER TABLE packages ADD COLUMN` + ~3 `ALTER TABLE package_version_vulns ADD COLUMN`. <1 second.
- **Phase U cost per run:** `_load_epss_scores(conn)` (~280k rows into memory; ~30 MB peak); no per-row HTTP. Adds <1 s to Phase G; <5 s to Phase G' (touches more rows).
- **`fetch-epss` cost:** ~3 MB CSV download + decompress + ~280k UPSERTs. <30 s end-to-end. TTL 1 d.
- **`fetch-cwe-catalog` cost:** ~2 MB CSV + ~960 UPSERTs. <10 s. TTL 90 d.
- **Phase T (local mode) cost:** ~1-3 s per `.conda` artifact via blint. Per-maintainer typical build is 1-5 artifacts → <15 s. Triggered manually post-build or automatically as a `pixi run recipe-build` post-hook (opt-in via `BLINT_AUTO_RUN=1`).
- **Phase T (admin top-N) cost:** 100 packages × (~30 MB download + ~3 s blint) ≈ 5-15 min for top-100 at conservative concurrency=3.

---

## Design

### Schema v24

```sql
-- v24 (v8.6.0): EPSS scores — FIRST.org daily snapshot.
-- Populated by `fetch-epss` CLI. Joined per-CVE during Phase G/G' overlay.
CREATE TABLE IF NOT EXISTS epss_scores (
    cve_id              TEXT PRIMARY KEY,
    epss_score          REAL NOT NULL,    -- 0.0-1.0 exploitation probability
    epss_percentile     REAL NOT NULL,    -- 0-100 (CISA documents this as 0-1; FIRST.org publishes as 0-1; normalize to 0-100 at store time)
    snapshot_date       TEXT,             -- ISO date from FIRST.org's `date` column
    source_fetched_at   INTEGER           -- UNIX seconds when this row was upserted
);
CREATE INDEX IF NOT EXISTS idx_epss_score      ON epss_scores(epss_score);
CREATE INDEX IF NOT EXISTS idx_epss_percentile ON epss_scores(epss_percentile);

-- v24 (v8.6.0): CWE categories — MITRE catalog + cf_atlas-specific high-level mapping.
-- Populated by `fetch-cwe-catalog` CLI + committed `cwe_categories_seed.json`.
CREATE TABLE IF NOT EXISTS cwe_categories (
    cwe_id              TEXT PRIMARY KEY,  -- e.g., 'CWE-79', 'CWE-22'
    cwe_name            TEXT,              -- MITRE's `Name` column
    cf_atlas_category   TEXT,              -- one of: RCE / DoS / Info-Disclosure / Auth-Bypass / Memory-Safety / Traversal / Injection / Other
    cwe_abstraction     TEXT,              -- MITRE's `Weakness Abstraction` (Class/Base/Variant/Compound)
    source_fetched_at   INTEGER
);
CREATE INDEX IF NOT EXISTS idx_cwe_category ON cwe_categories(cf_atlas_category);

-- v24 (v8.6.0): Per-package binary hardening profile from blint.
-- Populated by Phase T. Per (conda_name, version, subdir) row.
CREATE TABLE IF NOT EXISTS package_hardening (
    conda_name              TEXT NOT NULL,
    version                 TEXT NOT NULL,
    subdir                  TEXT NOT NULL,   -- linux-64 / osx-arm64 / win-64 / noarch
    binary_count            INTEGER,         -- # binaries in the .conda artifact
    pie_pct                 REAL,            -- % of binaries with Position Independent Executable
    relro_pct               REAL,            -- % with full RELRO
    stack_canary_pct        REAL,            -- % with stack canary
    nx_pct                  REAL,            -- % with non-executable stack
    fortify_pct             REAL,            -- % with fortify-source
    hardening_score         INTEGER,         -- 0-100 composite (mean of the 5 % columns)
    blint_version           TEXT,            -- blint version that produced this profile
    source_fetched_at       INTEGER,
    PRIMARY KEY (conda_name, version, subdir)
);
CREATE INDEX IF NOT EXISTS idx_hardening_score   ON package_hardening(hardening_score);
CREATE INDEX IF NOT EXISTS idx_hardening_conda   ON package_hardening(conda_name);
```

Schema-version `packages` and `package_version_vulns` columns added via `ALTER TABLE` in the existing migration ladder:

```sql
-- packages (existing table; ALTER TABLE additions)
ALTER TABLE packages ADD COLUMN vuln_max_epss_score        REAL;
ALTER TABLE packages ADD COLUMN vuln_max_epss_percentile   REAL;
ALTER TABLE packages ADD COLUMN vuln_cwe_top               TEXT;     -- e.g., 'RCE'
ALTER TABLE packages ADD COLUMN vuln_cwe_categories_json   TEXT;     -- JSON {"RCE": 3, "Info-Disclosure": 1}
ALTER TABLE packages ADD COLUMN vuln_total_active          INTEGER;  -- vuln_total minus withdrawn
ALTER TABLE packages ADD COLUMN vuln_withdrawn_count       INTEGER;  -- count of advisories filtered out

-- package_version_vulns (existing table; ALTER TABLE additions)
ALTER TABLE package_version_vulns ADD COLUMN vuln_max_epss_score      REAL;
ALTER TABLE package_version_vulns ADD COLUMN vuln_cwe_top             TEXT;
ALTER TABLE package_version_vulns ADD COLUMN vuln_total_active        INTEGER;
```

The DW12 `_phase_g_sync_current_rollup` tail step gains rows for the new columns automatically (it copies all per-version columns to per-current; only the column list needs to be extended).

The `v_current_version_vulns` view (also DW12) gets new columns exposed via the same query-time JOIN.

### Phase T — blint hardening profiles

```python
def phase_t_blint_hardening(conn: sqlite3.Connection) -> dict:
    """Phase T: per-package binary hardening profile via blint.

    Two modes controlled by env:
      - PHASE_T_MODE='local' (default): scan build_artifacts/ from the
        operator's local builds. Per-maintainer surface; cheap.
      - PHASE_T_MODE='top-cves': download top-N CVE-flagged packages
        from anaconda.org, blint them, populate package_hardening.
        Admin-tier; expensive (bounded by BLINT_TOP_N_LIMIT, default 100).

    Auto-skip when blint not importable (graceful degradation in non-vuln-db
    envs without owasp-blint installed).
    """
```

Tunables:
- `PHASE_T_DISABLED` — skip entirely
- `PHASE_T_MODE` — `local` (default) or `top-cves`
- `PHASE_T_BUILD_ARTIFACTS_DIR` — override default `build_artifacts/` location
- `BLINT_TOP_N_LIMIT` — default 100 (admin top-N mode)
- `BLINT_TOP_N_RANK_BY` — default `vuln_critical_affecting_current`; accepts any `packages.*` numeric column
- `PHASE_T_TTL_DAYS` — default 30 d (binary hardening doesn't change without a rebuild)
- `PHASE_T_CONCURRENCY` — default 3 (download fanout in top-cves mode)

### Phase U — EPSS overlay

```python
def phase_u_epss_overlay(conn: sqlite3.Connection) -> dict:
    """Phase U: EPSS score overlay onto Phase G/G' output.

    This is NOT a stand-alone scan phase — it's the EPSS-aware companion to
    Phase G/G'. Runs AFTER Phase G' (or independently as a pure-SQL backfill
    when Phase G/G' last-scanned data is fresh enough that re-scanning is
    wasteful). Reads epss_scores, joins to package_version_vulns (per-version
    CVE list aggregation), writes vuln_max_epss_score + vuln_max_epss_percentile.

    Pure-SQL when package_version_vulns already has the CVE list; falls back to
    a live vdb re-scan when only counts are stored.
    """
```

Tunables:
- `PHASE_U_DISABLED` — skip entirely
- `PHASE_U_TTL_DAYS` — default 1 d (matches `fetch-epss` cadence)

### CWE rollup + withdrawn filter (in-place Phase G/G' enhancement)

No new phase. Modifies the existing Phase G + Phase G' loop:

```python
# Phase G loop (modified)
kev_cves = _load_kev_cves(conn)      # existing (DW13)
epss_map = _load_epss_scores(conn)   # new (v8.6.0) — pre-Phase-U fast path
cwe_map = _load_cwe_categories(conn) # new (v8.6.0)
# ... existing loop ...
for v in affecting:
    if v.get("withdrawn"):              # new: skip withdrawn
        withdrawn_count += 1
        continue
    # existing severity/kev counters ...
    cwe_id = v.get("cwe")
    if cwe_id and (cat := cwe_map.get(cwe_id)):
        cwe_counts[cat] = cwe_counts.get(cat, 0) + 1
    epss = epss_map.get(v.get("id"), 0.0)
    max_epss = max(max_epss, epss)
# ... write new columns alongside existing ones ...
```

The withdrawn filter requires `_extract_vuln_fields` in `detail_cf_atlas.py` to surface the `withdrawn` field (one-line addition reading from `source_data`'s OSV/GHSA models).

### CLI surface

| New CLI | Purpose |
|---|---|
| `pixi run -e local-recipes fetch-epss` | Refresh `epss_scores` from FIRST.org. TTL 1 d. `--dry-run`, `--json`. |
| `pixi run -e local-recipes fetch-cwe-catalog` | Refresh `cwe_categories` from MITRE + reapply committed seed mapping. TTL 90 d. |
| `pixi run -e vuln-db blint-channel-top-n` | Admin: download top-N highest-risk packages, blint, populate `package_hardening`. |
| `pixi run -e local-recipes blint-local` | Maintainer: scan local `build_artifacts/`, populate `package_hardening` for this feedstock. |

| Existing CLI gains a flag | Purpose |
|---|---|
| `staleness-report --by-epss` | Sort by max-EPSS across the feedstock (admin triage) |
| `staleness-report --has-cwe RCE` | Filter to feedstocks with an RCE-category CVE in current |
| `staleness-report --active-only` | Exclude withdrawn from counts |
| `my-feedstocks --epss --cwe --hardening` | Add EPSS/CWE/hardening columns to the maintainer triage table |
| `cve-watcher --epss-threshold 0.7` | Delta filter to high-EPSS CVEs only |
| `detail-cf-atlas` (no flag — auto on) | Render new EPSS/CWE/hardening rows in the per-package card |

### Persona profile integration

| Profile | New behavior |
|---|---|
| `admin` | + `PHASE_T_MODE=top-cves`, `BLINT_TOP_N_LIMIT=100`, `PHASE_U_ENABLED=1`. Bootstrap-data step inserts `fetch-epss` (daily TTL) + `fetch-cwe-catalog` (weekly TTL) before Step 4. |
| `maintainer` | + `PHASE_T_MODE=local`, `PHASE_U_ENABLED=1`. Bootstrap-data step inserts `fetch-epss` daily. `fetch-cwe-catalog` runs weekly. |
| `consumer` | + `PHASE_U_ENABLED=1` *only if `epss_scores` already populated* (pure-SQL, no network). `PHASE_T_DISABLED=1`. |

---

## Stories — 4 waves, ~18 stories

### Wave A — Schema v24 + EPSS pipeline (~5 stories)

| ID | Story | Effort |
|---|---|---|
| S1 | Add `epss_scores` + `cwe_categories` + `package_hardening` tables to SCHEMA_DDL; add new columns to `packages` + `package_version_vulns` via ALTER TABLE migration block; bump SCHEMA_VERSION 23 → 24 | S |
| S2 | `scripts/epss_fetcher.py` — fetches FIRST.org daily CSV, upserts into `epss_scores`; standalone CLI with `--dry-run` / `--json` / `--db` / `--timeout` (mirrors `cisa_kev_fetcher.py` structure) | M |
| S3 | Three-place rule: pixi task `fetch-epss` + wrapper `.claude/scripts/conda-forge-expert/epss_fetcher.py` (filename matches canonical) + SCRIPTS list entry in `test_all_scripts_runnable.py` | XS |
| S4 | `tests/unit/test_epss_fetcher.py` — ~12 tests: CSV parsing, percentile normalization (FIRST publishes 0-1, we store 0-100), upsert idempotency, malformed-row skip, missing-creds error path | M |
| S5 | `_load_epss_scores(conn)` helper in `conda_forge_atlas.py`; degrades to empty dict when table missing | XS |

### Wave B — CWE catalog + withdrawn filter (~5 stories)

| ID | Story | Effort |
|---|---|---|
| S6 | `scripts/cwe_catalog_fetcher.py` — pulls MITRE CWE Research Concepts CSV, upserts into `cwe_categories` with committed seed-mapping (`data/cwe_categories_seed.json` — hand-curated 5-8 high-level categories); standalone CLI mirror of `cisa_kev_fetcher.py` structure | M |
| S7 | Three-place rule for `cwe_catalog_fetcher.py` (pixi `fetch-cwe-catalog` task + matching-name wrapper + SCRIPTS) | XS |
| S8 | `tests/unit/test_cwe_catalog_fetcher.py` — ~10 tests: CSV parsing, seed-mapping application, unknown-CWE → 'Other' fallback, upsert idempotency | M |
| S9 | `_load_cwe_categories(conn)` helper; `_extract_vuln_fields` in `detail_cf_atlas.py` gains `withdrawn` field surfacing | S |
| S10 | Phase G + Phase G' overlay loop modifications: CWE category counting, withdrawn-skip, EPSS-max — all in the existing per-CVE iteration; write new columns alongside existing | M |

### ~~Wave C — Phase T (blint) + Phase U (EPSS overlay phase)~~ — **CANCELLED 2026-05-23 (pre-implementation kill)**

Cancelled during the Wave C `bmad-quick-dev` verification phase after low-signal-to-effort assessment. See `_bmad-output/projects/local-recipes/implementation-artifacts/deferred-work.md` § "Wave C cancellation (Phase T blint + Phase U EPSS overlay)" for full rationale + Wave D follow-up.

**Summary of reasoning:**
- **Phase T (blint hardening)** — conda-forge's hermetic compile environment sets PIE / RELRO / stack-canary / NX via channel-wide global pinning. Per-package variance is minimal; even when a non-hardened binary surfaces, the actionable response is "file an upstream issue and wait for a compiler flag" — not a triage signal. Blint is genuinely useful for vendor-supplied binaries (Windows EXEs, distro packages); for conda-forge it would surface ~32k uniform answers at ~150 GB of download cost.
- **Phase U (EPSS overlay)** — redundant with Wave B's `_phase_g_sync_current_rollup` extension which already propagates `vuln_max_epss_score` from `package_version_vulns` to `packages` with COALESCE-to-existing. The "pure-SQL backfill" wording conflated "rerun max-EPSS computation" with "re-fetch vdb data" — they're equivalent today because per-package CVE lists aren't stored. A genuine Phase U would require a new `package_cves` table — separate spec, not v8.6.0.
- **blint output verification** also surfaced that the package name is `blint` not `owasp-blint` (PyPI 404 on the latter) AND that blint cannot scan `.conda` archives directly (requires extract-then-walk). Both would have been pre-implementation friction without delivering operational signal.

Schema columns provisioned in Wave A for this wave (`package_hardening` table, `packages.vuln_total_active`, `packages.vuln_withdrawn_count`, `package_version_vulns.vuln_total_active`) are dropped in Wave D via a v24 → v25 migration. (The `vuln_total_active` + `vuln_withdrawn_count` columns also become moot because the v8.6.0 Wave B withdrawn-filter was already dropped after verifying vdb pre-filters at ingest — see existing parent-spec-correction entry in deferred-work.md.)

### Wave D — Schema v25 cleanup + CLI flags + profile integration + closeout (~5 stories)

Wave D scope was rebalanced 2026-05-23 after Wave C was cancelled. Original CLI flags for `--has-hardening` + `--active-only` + persona-profile entries for Phase T/U dropped. New stories S16′ (schema v25 migration) added.

| ID | Story | Effort |
|---|---|---|
| **S16′** (new) | **Schema v25 migration**: DROP TABLE `package_hardening` (+ its 2 indexes); DROP COLUMN `packages.vuln_total_active` + `packages.vuln_withdrawn_count` + `package_version_vulns.vuln_total_active`. Remove the corresponding SCHEMA_DDL entries + the ALTER TABLE ladder entries. Bump SCHEMA_VERSION 24 → 25. Self-healing v24→v25 migration block (idempotent — SQLite 3.35.0+ supports `ALTER TABLE … DROP COLUMN`; for older SQLite fall back to "rebuild via SELECT INTO new table" — but pixi pins to 3.46+ so the modern path applies). | M |
| S16 (reduced) | CLI flag additions: `staleness-report --by-epss / --has-cwe`; `my-feedstocks --epss --cwe`; `cve-watcher --epss-threshold`; `detail-cf-atlas` auto-renders new rows. **DROPPED from S16:** `--active-only` flag (no withdrawn data to filter), `--hardening` column (no `package_hardening` data to show). | M |
| S17 (reduced) | Persona profile updates in `bootstrap_data.py`: admin auto-runs `fetch-epss` daily + `fetch-cwe-catalog` weekly; maintainer auto-runs `fetch-epss` daily. **DROPPED from S17:** Phase T enablement (cancelled), Phase U enablement (cancelled), consumer-mode logic for Phase U. | S |
| S18 | Closeout: CHANGELOG v8.6.0 entry covering EPSS + CWE rollup + Wave C cancellation rationale + schema v25 cleanup + cdxgen ruling rationale; SKILL.md atlas-section bumped to v25; `skill-config.yaml` 8.5.3 → 8.6.0; `reference/atlas-actionable-intelligence.md` catalog flips (2 rows: EPSS / CWE — withdrawn + hardening rows stay 📋 with Wave-C-cancelled rationale); CFE retro per CLAUDE.md Rule 2 | M |

### Wave sequencing rationale

- **Wave A first** — schema + EPSS is the foundation. EPSS is the highest single-value signal (operational exploitation probability) and the simplest to ship (CSV pull + UPSERT).
- **Wave B in parallel-or-after A** — CWE catalog is independent of EPSS; the Phase G/G' overlay extension in S10 wires both together so they ship in the same release.
- **Wave C after A+B** — Phase T (blint) is the heaviest implementation; Phase U is intentionally lightweight (pure-SQL when possible).
- **Wave D is closeout** — CLI flags + profile + retro. Same shape as v8.1.0 / v8.5.3 closeouts.

**Two-PR strategy:** Waves A + B in PR #1 (schema bump + EPSS + CWE + Phase G/G' enhancement; ships immediate value). Waves C + D in PR #2 (blint + CLI surface + closeout). Both before v8.6.0 tag.

---

## Acceptance Tests

For each wave, the BMAD agent runs the full pytest suite plus explicit new tests:

### Wave A

- `tests/unit/test_epss_fetcher.py::test_csv_parses_well_formed_row` — fixture CSV → expected `epss_scores` row
- `tests/unit/test_epss_fetcher.py::test_percentile_normalized_to_0_100` — FIRST's 0.94 → stored 94.0
- `tests/unit/test_epss_fetcher.py::test_upsert_idempotent` — re-fetch same CSV → no net delta
- `tests/unit/test_epss_fetcher.py::test_malformed_row_skipped` — missing cve_id → skipped, others land
- `tests/unit/test_epss_fetcher.py::test_load_epss_scores_empty_table` — `_load_epss_scores` returns `{}` cleanly

### Wave B

- `tests/unit/test_cwe_catalog_fetcher.py::test_seed_mapping_applied` — CWE-79 → cf_atlas_category='Injection' (per seed)
- `tests/unit/test_cwe_catalog_fetcher.py::test_unknown_cwe_other_fallback` — CWE-NEW-9999 not in seed → category='Other'
- `tests/unit/test_phase_g_overlay.py::test_withdrawn_filter_skips_advisory` — fixture vuln with `withdrawn=True` → not counted
- `tests/unit/test_phase_g_overlay.py::test_cwe_rollup_picks_top_category` — 3 RCE + 1 DoS → vuln_cwe_top='RCE'
- `tests/unit/test_phase_g_overlay.py::test_epss_max_across_cve_list` — 3 CVEs at 0.1/0.5/0.9 → vuln_max_epss_score=0.9

### Wave C

- `tests/unit/test_phase_t_blint.py::test_local_mode_scans_build_artifacts` — fixture `.conda` → `package_hardening` row
- `tests/unit/test_phase_t_blint.py::test_hardening_score_composite` — PIE=1.0 RELRO=1.0 STACK=0.5 NX=1.0 FORTIFY=0.5 → score=80
- `tests/unit/test_phase_t_blint.py::test_blint_not_installed_skips_gracefully` — ImportError → skip dict
- `tests/unit/test_phase_t_blint.py::test_top_cves_candidate_query` — admin mode picks top-N by `BLINT_TOP_N_RANK_BY` column
- `tests/unit/test_phase_u_epss.py::test_pure_sql_backfill` — fresh `package_version_vulns` → no vdb re-scan needed
- `tests/unit/test_phase_u_epss.py::test_falls_back_to_vdb_when_stale` — old data → re-scan path triggered

### Wave D

- `tests/unit/test_cli_extensions.py::test_staleness_report_by_epss` — sort order matches max-EPSS desc
- `tests/unit/test_cli_extensions.py::test_staleness_report_has_cwe_filter` — `--has-cwe RCE` returns only feedstocks with RCE-category CVE in current
- `tests/unit/test_cli_extensions.py::test_my_feedstocks_renders_new_columns` — header includes EPSS / CWE / Hardening
- `tests/unit/test_persona_profiles.py::test_admin_enables_phase_t_top_cves` — admin profile sets `PHASE_T_MODE=top-cves`
- `tests/unit/test_persona_profiles.py::test_consumer_skips_blint` — consumer sets `PHASE_T_DISABLED=1`

### Cross-cutting

- Full atlas rebuild against the real connection produces `cf_atlas.db` at schema v24; `epss_scores` populated for ~280k rows; `cwe_categories` for ~960 rows; `vuln_max_epss_score` populated for any package whose Phase G' scan saw a CVE in `epss_scores`; sample command `staleness-report --by-epss --limit 10` returns 10 packages with non-NULL `vuln_max_epss_score` ordered descending.
- Live `fetch-epss` against FIRST.org completes in <30 s end-to-end; live `fetch-cwe-catalog` against MITRE in <10 s.
- Schema v23 → v24 migration on a real-world cf_atlas.db (~33 k rows) completes in <2 s; no data loss; all new columns NULL on pre-migration rows (correct).

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| FIRST.org rate-limits or moves the EPSS URL | Low | Medium | `EPSS_BASE_URL` env override; conservative concurrency=1 documented; the URL `https://epss.cyentia.com/epss_scores-current.csv.gz` has been stable since 2022 |
| MITRE CWE CSV schema changes | Low | Low | TTL 90 d means infrequent fetches; parser tested against fixture; failure-to-parse degrades to "all CWEs map to Other" not crash |
| blint installation issues on macOS / Windows | Medium | Low | Lazy import + graceful skip dict; Phase T degrades silently when blint unimportable; admin operator on macOS sees a printed warning |
| Top-N blint mode hits anaconda.org bandwidth limits | Low | Medium | Default `BLINT_TOP_N_LIMIT=100` keeps total fetch <3 GB; concurrency=3 via `_http.py` resolver |
| EPSS percentile interpretation drift | Low | Low | Hard-pinned normalization to 0-100 at store time; documented in schema comment + fetcher docstring; tests cover the normalization |
| CWE category seed mapping becomes stale as new CWEs added | Medium | Low | `fetch-cwe-catalog` runs weekly under admin profile; unknown CWEs default to 'Other' (visible signal that seed needs update); quarterly review of unmapped CWEs documented in operator-runbook |
| `vuln_total_active` introduces confusion alongside `vuln_total` | Medium | Low | `vuln_total` retained for backward-compat; CHANGELOG explicitly notes "use vuln_total_active in new code, vuln_total preserves trend continuity"; documentation reference call-out |
| Phase U pure-SQL fast path produces stale EPSS if `epss_scores` table fetched between Phase G' run and Phase U run | Low | Low | Phase U runs AFTER `fetch-epss` in the bootstrap pipeline; standalone Phase U invocation reads current `epss_scores` so no staleness possible |

---

## Rollout

### Pre-merge

- All Wave A-D acceptance tests pass.
- Live `fetch-epss` against FIRST.org succeeds (no credentialed access, just connectivity check).
- Live `fetch-cwe-catalog` against MITRE succeeds.
- Local `blint` smoke test against a freshly built `.conda` artifact produces non-zero hardening properties.
- Schema migration tested against a real cf_atlas.db copy (not just fixture DB).
- Meta-tests (`test_skill_md_consistency`, `test_all_scripts_runnable`) green.

### Merge order

- PR #1 (Waves A+B): schema v24 + EPSS fetcher + CWE fetcher + Phase G/G' overlay enhancement + Wave A+B tests.
- PR #2 (Waves C+D): Phase T (blint) + Phase U (EPSS overlay) + CLI flag additions + persona profile updates + Wave C+D tests + CHANGELOG + retro.

### Post-merge

- Tag `conda-forge-expert-v8.6.0`.
- Single-line operator advisory: run `pixi run -e local-recipes fetch-epss && pixi run -e local-recipes fetch-cwe-catalog` once; next `bootstrap-data --profile admin` picks up daily/weekly TTLs automatically.

### Backout plan

- Roll back the two PRs (revert).
- Schema is additive — leaving the new tables in place is harmless (`init_schema` becomes the only writer; readers that don't know about v24 columns ignore them).
- No data loss: rollback drops the new tables but preserves `packages` / `package_version_vulns` content.

---

## Open Questions — to resolve before BMAD intake

| Q | Decision needed | Resolution |
|---|---|---|
| Q1 | EPSS percentile storage range: 0-1 or 0-100? | Resolve to 0-100 (matches CISA's published convention; FIRST.org's CSV uses 0-1 but normalizing at store time is cheaper than at every read). |
| Q2 | CWE seed mapping — committed JSON or DB seed? | Committed JSON at `.claude/skills/conda-forge-expert/data/cwe_categories_seed.json` (review-via-PR; survives `--clean`). |
| Q3 | Phase T local mode trigger — post-build hook or separate command? | Separate command (`pixi run -e local-recipes blint-local`); operator decides. Post-build hook is a v8.7.x stretch. |
| Q4 | `vuln_total_active` calculation — at Phase G overwrite-time or query-time view? | Phase G overwrite-time (matches existing `vuln_total` semantics; simpler reads). |
| Q5 | Should Phase U run inside the cf_atlas build phases list, or stay as a separate post-bootstrap step? | Inside the phases list (after Phase G'). Justification: same pattern as DW12's `_phase_g_sync_current_rollup` tail step — pure-SQL post-processing belongs in the build, not as a separate operator step. |
| Q6 | Should `blint-channel-top-n` rank-by support arbitrary SQL or a fixed allowlist? | Fixed allowlist of numeric `packages.*` columns (security: SQL-injection guard for CLI input). |

---

## References

- DW13 Path C implementation (the template this spec reuses end-to-end): `.claude/skills/conda-forge-expert/CHANGELOG.md` v8.5.3 entry, `.claude/skills/conda-forge-expert/scripts/cisa_kev_fetcher.py`, `_load_kev_cves` helper in `scripts/conda_forge_atlas.py`.
- DW12 rollup-sync + v_current_version_vulns view (the column-extension this spec layers onto): same CHANGELOG entry; `_phase_g_sync_current_rollup` in `scripts/conda_forge_atlas.py`.
- DW12/DW13 retro: `_bmad-output/projects/local-recipes/implementation-artifacts/retro-dw12-dw13-2026-05-23.md` § "Follow-ups (DW-track candidates for the PRD)".
- FIRST.org EPSS docs: https://www.first.org/epss/data_stats
- FIRST.org EPSS daily CSV: https://epss.cyentia.com/epss_scores-current.csv.gz
- MITRE CWE CSV download: https://cwe.mitre.org/data/csv/2000.csv.zip
- OSV schema (for `withdrawn` field): https://ossf.github.io/osv-schema/
- `owasp-blint` on PyPI: https://pypi.org/project/owasp-blint/
- AppThreat vulnerability-db (vdb): https://github.com/appthreat/vulnerability-db
- cdxgen ruling rationale: verified 2026-05-23 against `lib/helpers/utils.js@9798-9920` at https://github.com/CycloneDX/cdxgen. cdxgen DOES support `pixi.lock` via `parsePixiLockFile` (emits `pkg:conda/...` purls with `?os=<subdir>`, captures URL + sha256 + license + `depends:`), but does NOT parse `recipe.yaml` / `meta.yaml` / `environment.yml` / `conda-lock.yml` directly. Python coverage (pip / poetry / requirements / pyproject) is documented in the README; pixi coverage is documented at https://cdxgen.github.io/cdxgen/#/ARCHITECTURE_ECOSYSTEM_EXAMPLES?id=python-example. Channel-wide use ruled out (cf_atlas Phase B + J already supersede); per-workspace use filed as follow-up DW17 (see Appendix A § "Where cdxgen-on-pixi.lock would belong").
- Three-place rule (now four with the wrapper-filename match): auto-memory `feedback_cfe_new_script_three_places.md`.
- Persona profile pattern: `docs/specs/conda-forge-expert-v8.0.md` § Wave D + `scripts/bootstrap_data.py` `PROFILES` dict.

---

## Appendix A — Why cdxgen / atom / dep-scan don't belong in cf_atlas's channel-wide phase pipeline

A 2026-05-23 conversation evaluated a separate "AppThreat Deep Security & Dependency Graph Pipeline" workflow proposal that would have wired `atom` + `blint` + `cdxgen` + `dep-scan` into a GitHub Actions workflow submitting to the GitHub Dependency Graph API. Critical analysis found:

1. **Wrong target.** GitHub Dependency Graph Submission is per-repo. cf_atlas operates channel-wide across ~25,000 feedstocks. A per-feedstock GH-Deps-Graph workflow would produce 25,000 disconnected graphs vs. cf_atlas's one unified Phase J graph (294,830 edges across 27,499 feedstocks).

2. **`atom` is an application-source slicer.** Feedstock repos contain `recipe.yaml` + maybe `build.sh` — no application code to slice. Running `atom` against a recipe directory produces either empty output or a misleading slice of build tooling.

3. **`cdxgen` has pixi.lock support but no recipe.yaml / meta.yaml support** (verified 2026-05-23 against `CycloneDX/cdxgen` `lib/helpers/utils.js@9798-9920`). cdxgen's `parsePixiLockFile` reads a `pixi.lock` and produces proper conda-aware purls (`pkg:conda/<name>@<version>-<build>?os=<subdir>`), capturing URL + sha256 + license + `depends:` edges. So the *capability* exists. **However**, the proposed workflow ran `cdxgen -t python,conda` against a recipe directory — which enumerates the workflow's runtime environment (stock GitHub-actions runner Python + node), not the conda-forge package being authored. To get the conda-purl-emitting behavior, the workflow would have to (a) create a pixi workspace inside the runner, (b) `pixi install` the recipe's runtime deps into it, (c) THEN run cdxgen against the resulting `pixi.lock`. That's a three-step setup the proposal didn't include. Even when correctly wired, the result is an environment-level SBOM for a single feedstock's *runtime* — a strict subset of what cf_atlas Phase B + Phase J already provide channel-wide.

4. **`dep-scan` is a vdb frontend.** cf_atlas already invokes `vdb.lib.search` directly from Phase G + G'. Adding `dep-scan` as a wrapper layer introduces subprocess overhead without producing any signal vdb didn't already produce.

5. **`blint` IS useful** — but only for the binary-properties signal it produces (PIE/RELRO/stack-canary/NX), not as part of the proposed GH-Deps-Graph workflow. This spec adopts `blint` as Phase T (Wave C) for exactly that reason, bounded to maintainer-local + admin-top-N scopes rather than full-channel.

The proposed workflow also had fabricated inputs (`actions/setup-python` `python-with-history`, `cdxgen-action upload-snapshot`) that wouldn't have passed a YAML lint, and a validation script reading a different file than the upload step submitted. The whole proposal was discarded; the actually-useful AppThreat-ecosystem signal (blint hardening) is captured here as Phase T.

### Where cdxgen-on-pixi.lock *would* belong (separate follow-up, not v8.6.0)

> **DISCHARGED (2026-07-05, cross-ref added at the cyclonedx S-retro):** the DW17
> follow-up shipped as `cyclonedx-universe-inventory` **S5a** — `scan_project`
> gained a NATIVE `pixi.lock` parser (no cdxgen subprocess needed), policy-tier
> `policy`, wired into `scan-project` and `inventory-match` intake. See that
> spec's Wave C and `reference/dependency-input-formats.md`.

cdxgen-on-pixi.lock is a legitimate **`scan_project` input format**. Today, `scan_project` accepts `--conda-env <path>` (live env scan), `--venv <path>` (live env scan), `--sbom-in <file>` (pre-built CycloneDX/SPDX consumption), and a handful of manifest/lockfile types — but not `--pixi-lock <file>`. Adding `--pixi-lock` as a new input mode (which would shell out to `cdxgen -t pixi -o /tmp/bom.json <path>` and then re-enter the `--sbom-in` code path with the produced BOM) gives operators a one-command flow for any pixi-managed workspace:

```bash
pixi run -e local-recipes scan-project --pixi-lock ./pixi.lock --license-check
```

This is **filed as a separate follow-up** rather than added to v8.6.0 scope because:
- It's `scan_project` enrichment, not atlas-side enrichment.
- It introduces a Node.js / npm runtime dependency (`@cyclonedx/cdxgen`) that wasn't in the v8.5.x dependency set.
- The operator-facing value is meaningfully different from this spec's blint/EPSS/CWE/withdrawn scope (per-workspace SBOM vs. channel-wide CVE intelligence).
- Bundling them would muddy the v8.6.0 narrative ("AppThreat Deep Signals" should mean signals into the atlas, not new scanner front-doors).

**Follow-up tracking:** add as new PRD §9 row "DW17 — scan-project `--pixi-lock` mode via cdxgen `parsePixiLockFile`" after v8.6.0 ships, with a small standalone spec (~6-8 stories: install cdxgen as a vuln-db env dep, wrapper, integration test against a fixture pixi.lock, doc updates). Reuses zero of this spec's surface.

---

<a id="p7"></a>

# Part 7 — cost-capped incremental BigQuery Phase P

> Formerly `atlas-phase-p-incremental.md` — shipped v8.15.0 (2026-06-12; corrected v8.15.2, superseded-in-part by v8.16.0 ClickHouse default).
> Original frontmatter: `status: shipped; implemented_by: bmad-quick-dev; shipped_ref: "v8.15.0"; spec_updated: 2026-06-20`

# Tech Spec: Atlas Phase P — Incremental BigQuery Refresh + Cost Guardrails

> **BMAD intake document.** Written for `bmad-quick-dev` (Quick Flow track —
> architectural refactor of one phase + one new schema table). ~12 implementation
> stories across 3 waves. Run BMAD with this file as the intent document:
>
> ```
> run quick-dev — implement the intent in docs/specs/atlas-phase-p-incremental.md
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
| Surface area | `conda-forge-expert` skill — schema v25 → v26 migration adding `pypi_downloads_daily` side table; refactor of `phase_p_pypi_downloads` to incremental refresh + dry-run preflight + hard cost cap; new env-var tunables; spec/docstring/CHANGELOG corrections to the wrong "~30 GB scan" claim |
| Scope | Replace the single-shot 90-day BigQuery aggregate query with an incremental partition-by-partition refresh that stores per-day per-package counts locally and recomputes `pypi_intelligence.downloads_30d/90d` from the local table. Adds dry-run preflight that aborts above operator-set USD cap. Adds `maximum_bytes_billed` hard cap on the live query. Preserves exact per-package counts for the full PyPI namespace (no top-N filter, no aggregator fallback). |
| Version | conda-forge-expert v8.14.x → **v8.15.0** (MINOR — additive: new schema table, new tunables, new BQ source value; existing `downloads_30d/90d` consumer surface unchanged) |
| Out of scope | Per-version download granularity (deferred to v8.16.0+ if operator demand surfaces — same Q2 deferral from `atlas-pypi-intelligence.md`); replacement of BigQuery as the source (no top-N aggregator can satisfy the full-coverage + exactness requirement); auto-provisioning of BQ credentials (operator BYO unchanged); per-platform download breakdowns (a `pypi.file_downloads.details.installer` slice — not in scope for this spec) |
| Created | 2026-06-12 |
| Predecessor | `docs/specs/atlas-pypi-intelligence.md` (v8.1.0 — introduced Phase P + `pypi_intelligence` table). This spec rewrites the Phase P implementation; the consumer table is unchanged. |
| Driver | The 2026-06-12 BigQuery invoice surprise: a recent Phase P refresh cost **$500+** against the documented "well within 1 TB free tier (~30 GB / query)" expectation. Root cause: the "~30 GB" figure is wrong by ~1000× — the real per-run scan is ~25–45 TB (~$170 / run at on-demand pricing). The spec, the code docstring, the CHANGELOG, and three reference docs all repeat the wrong number. Operator needs (a) the bleeding stopped via hard caps, and (b) the steady-state refresh cost driven below $10 / month while keeping full-namespace exactness. |

---

## Background and Context

### The problem

Phase P (`conda_forge_atlas.py:6237`) issues one query per refresh against
`bigquery-public-data.pypi.file_downloads`, aggregating the trailing 90 days
of every PyPI download event into per-project totals:

```sql
SELECT
    REGEXP_REPLACE(LOWER(file.project), r'[-_.]+', '-') AS pypi_name,
    SUM(IF(timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY), 1, 0)) AS downloads_30d,
    SUM(IF(timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY), 1, 0)) AS downloads_90d
FROM `bigquery-public-data.pypi.file_downloads`
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
GROUP BY pypi_name
```

The query is **correct** — partition filter prunes properly, column
projection is minimal, single round-trip. The problem is volume:

- `bigquery-public-data.pypi.file_downloads` is now around **~30 GB scanned
  per day** at the `file.project + _PARTITIONDATE` projection level
  (verifiable via dry-run; exact number drifts up ~30% YoY).
- A 90-day window scans **~2.7 TB** at minimum, sometimes ~3-4 TB depending
  on packaging-event-density on the days in window.
- On-demand pricing is $6.25/TB → **~$15-25 per run** baseline.
- The "$500+ invoice" trace: ~3 runs at ~$170 each, consistent with a
  scan that the planner failed to project-prune optimally (older BQ
  planners occasionally degrade `file.project` STRUCT-field projection
  when the `WHERE` predicate references the sibling `timestamp` column).

The **spec, code docstring, CHANGELOG entry, `atlas-operations.md`,
`atlas-phases-overview.md`, and `commands-cheatsheet.md`** all claim the
query scans **~30 GB**. That figure is wrong by roughly 1000×. It traces
back to a 2016-era napkin number copied through the spec without
re-verification when v8.1.0 went to intake.

### What's been ruled out

- **pypistats.org as the source.** Rate-limited (~1 req/s soft ceiling,
  429s on bursts), and its dataset is capped to the historical top ~5 k
  packages. A 12 k-actionable backfill takes >3 hours and *still* misses
  the long tail. The full `pypi_universe` (~600 k packages) is
  intractable at that rate. Even if we filtered to the actionable slice,
  the long-tail rows would carry NULL counts, breaking Phase S's
  readiness ranking for the candidates that matter most.

- **hugovk/top-pypi-packages GitHub release JSON.** Free, fast, single
  HTTP fetch — but the published artifacts cap at top 15 k by 30-day or
  365-day downloads. Operator requirement is per-package exactness for
  *all* packages, not top-N.

- **Bucket-coded ranking instead of exact counts** (e.g., classifying
  each package into `top-100 / top-1k / top-5k / top-15k / long-tail`).
  Loses the precision needed for `conda_forge_readiness` differentials
  inside a tier, especially when triaging adjacent candidates.

- **ClickHouse `clickpy` public dataset.** Free, full-coverage, fast — but
  operator-trust dependency on a third party we don't control. Reasonable
  fallback / verification source; not a primary.

- **ecosyste.ms bulk PyPI parquet.** Pulled from BigQuery at monthly
  cadence; full PyPI namespace. Reasonable secondary, but its
  `downloads_period` semantics need verification (last-month? last-90d?
  cumulative?) before we can hot-swap it in. Tracked as a v8.16.0
  follow-up for operators who want a BQ-credentials-free path.

- **Google Cloud Storage Read API on the BQ table.** Bypasses query
  pricing, but you pay $0.011/GB storage read. ~3 TB read = $33/run for
  data we then have to aggregate locally. Worse than just running the
  query.

- **Replacing BigQuery as the source.** The operator hard-constraint is
  *full-namespace + exact counts*. Only `bigquery-public-data.pypi.file_downloads`
  satisfies both. The fix has to live in *how* we run it, not in
  *whether* we run it.

### What's available to leverage

- **The BQ table is daily-partitioned on `_PARTITIONDATE`.** Per-day
  partition cost is ~$0.06–$0.20 with column projection. A refresh that
  queries only the *new* days since the last refresh costs proportional
  to the elapsed window.
- **`pypi_intelligence` is already populated** by v8.1.0+ — the table
  shape is fine. We only need to change how the `downloads_30d/90d`
  columns get filled.
- **BigQuery's dry-run mode returns `total_bytes_processed` for free.**
  No quota consumed, no cost. Lets us print a cost estimate before
  committing.
- **`bigquery.QueryJobConfig(maximum_bytes_billed=N)` is a server-side
  hard ceiling.** If a job would scan more than N bytes, BQ aborts it
  with `400 Bytes Billed Limit Exceeded` and charges $0. This is the
  right failure mode for runaway prevention.
- **Operator cost tolerances are now known**: ≤ $10 / refresh,
  ≤ $100 / first-pull. Both are achievable.

---

## Goals

- **G1.** **Refresh cost ≤ $10 in 99% of runs.** Achieved by querying
  only the partitions that haven't been seen since the last refresh
  (typically 1–30 days depending on cadence).
- **G2.** **First-pull cost ≤ $100, typically ~$15-25.** Achieved by the
  initial 90-day scan paying the unavoidable cold-start cost once, with
  a dry-run preflight that aborts if the estimate exceeds the cap.
- **G3.** **Hard server-side cap on every BQ job** via
  `maximum_bytes_billed`. Operator-tunable; default 1.6 TB for refresh
  (~$10), 16 TB for first-pull (~$100). Job aborts and bills $0 if
  exceeded.
- **G4.** **Full per-package exactness preserved.** No top-N filter, no
  bucket coding, no aggregator fallback. Every pypi_name that appears
  in `bigquery-public-data.pypi.file_downloads` gets an exact count.
- **G5.** **Air-gap-friendly steady state.** Once the daily table is
  warm, queries against `pypi_intelligence.downloads_30d/90d` (and the
  derived `conda_forge_readiness`) work offline. Only the BQ refresh
  needs network + creds.
- **G6.** **Spec / docs / code all carry the correct cost numbers**
  after this lands. No future operator should see "~30 GB" written
  anywhere in the skill.

## Non-goals

- **NG1.** Per-version downloads. Project-level only (same Q2 deferral
  as `atlas-pypi-intelligence.md`). Per-version multiplies scan cost
  ~200×.
- **NG2.** Per-platform / per-installer / per-pyver download breakdowns.
  Those live in `file_downloads.details.*`; pulling them would expand
  scan width. Future spec if operator demand surfaces.
- **NG3.** Replacing BigQuery as the primary source. ClickHouse and
  ecosyste.ms remain documented fallback paths in `atlas-operations.md`;
  not implemented as code paths in v8.15.0.
- **NG4.** Auto-provisioning of BQ credentials. Operator BYO via
  `GOOGLE_APPLICATION_CREDENTIALS` or `gcloud auth application-default
  login` — unchanged from v8.1.0.
- **NG5.** Changing the consumer surface (`pypi_intelligence.downloads_30d`,
  `pypi_intelligence.downloads_90d`). Phase S, the `pypi-intelligence`
  CLI, and the `pypi_intelligence` MCP tool all continue to read those
  columns unchanged. New `pypi_downloads_daily` is an internal cache,
  not a public surface.
- **NG6.** Changing the default Phase P opt-in posture. Phase P remains
  opt-in via `PHASE_P_ENABLED=1`. Admin-profile activation continues
  to set it.
- **NG7.** Backfill of historical daily data from before the first run.
  We start collecting per-day data from the first incremental refresh
  forward. The first-pull scans the trailing 90 days as today.

---

## Lifecycle Expectations

- **One-time migration cost** (v25 → v26): `CREATE TABLE pypi_downloads_daily`
  + 2 indexes. < 1 second; idempotent.

- **First-pull cost** (no existing daily rows):
  - Dry-run preflight: free.
  - Real query for the trailing 90 days: ~$15–25 estimate, capped at $100.
  - Bulk INSERT into `pypi_downloads_daily`: ~5–30 s wall-clock.
  - Recompute `pypi_intelligence.downloads_30d/90d`: ~1 s pure SQL.

- **Steady-state per-refresh cost** (incremental):
  - Daily cadence (queries 1 new day): ~$0.06–0.20 / run.
  - Weekly cadence: ~$0.40–1.40 / run.
  - Monthly cadence (default; `PHASE_P_TTL_DAYS=30`): ~$2–6 / run.
  - All well below the $10 cap.
  - If the gap since last refresh exceeds 90 days, the run falls back
    to first-pull mode and dry-run-aborts unless `PHASE_P_MAX_COST_USD`
    is raised.

- **Storage delta**:
  - `pypi_downloads_daily`: only stores rows where `downloads > 0` on a
    given day. ~50 k–100 k packages have any same-day downloads;
    × 90 days × ~50 bytes/row = ~225–450 MB at steady state.
  - GC: rows older than 95 days are deleted on each refresh
    (5-day slack beyond the 90 d window for boundary safety).
  - Existing `cf_atlas.db` is typically 200–500 MB; new delta is
    significant but acceptable for the admin profile.

- **BigQuery quota**: With monthly cadence + cost caps in place, total
  annual BQ spend is bounded at:
  - First-pull: 1 × ~$25 = $25
  - 11 × monthly refresh × ~$3 = $33
  - **Annual: ~$60 (vs. $500+ in the pre-fix regime)**

---

## Design

### Schema v26

#### New: `pypi_downloads_daily`

```sql
-- Per-day per-package download counts. Source of truth for computing
-- pypi_intelligence.downloads_30d/90d via local SQL aggregation.
-- INSERT-only on Phase P refresh; GC prunes rows older than
-- PHASE_P_RETAIN_DAYS (default 95).
CREATE TABLE IF NOT EXISTS pypi_downloads_daily (
    pypi_name      TEXT NOT NULL,
    download_date  TEXT NOT NULL,    -- ISO 'YYYY-MM-DD' (SQLite has no DATE)
    downloads      INTEGER NOT NULL, -- always >= 1; zero-count rows not stored
    PRIMARY KEY (pypi_name, download_date)
);
CREATE INDEX IF NOT EXISTS idx_pypi_dl_daily_date
    ON pypi_downloads_daily(download_date);
CREATE INDEX IF NOT EXISTS idx_pypi_dl_daily_name
    ON pypi_downloads_daily(pypi_name);
```

#### Unchanged: `pypi_intelligence`

The `downloads_30d`, `downloads_90d`, `downloads_fetched_at`,
`downloads_source` columns are unchanged. The new pipeline writes to
them via aggregation queries against `pypi_downloads_daily` instead of
direct from BQ.

`downloads_source` gains a new permitted value: `'bigquery-incremental'`.
The old `'bigquery-public'` value remains valid for migration-period
rows; downstream consumers should treat both as "BQ-sourced exact
counts" (no semantic difference).

### Refactored `phase_p_pypi_downloads`

```python
def phase_p_pypi_downloads(conn: sqlite3.Connection) -> dict:
    """Phase P: incremental per-day PyPI download counts via BigQuery.

    v8.15.0 architecture — supersedes v8.1.0's single-shot 90-day query.

    Mode selection:
      - first-pull (pypi_downloads_daily empty): query trailing 90 days,
        cap at PHASE_P_MAX_COST_FIRST_PULL_USD (default $100).
      - incremental (table populated): query [last_stored_date + 1, today),
        cap at PHASE_P_MAX_COST_USD (default $10).
      - if gap > 90 days: revert to first-pull mode + log warning.

    Steps:
      1. Determine mode + window.
      2. Build _PARTITIONDATE-literal query (no CURRENT_TIMESTAMP()).
      3. Dry-run preflight: print estimated cost; abort if > cap.
      4. Real query with maximum_bytes_billed hard cap.
      5. Bulk INSERT OR IGNORE into pypi_downloads_daily.
      6. Recompute pypi_intelligence.downloads_30d/90d from local table.
      7. GC: delete pypi_downloads_daily rows older than retain window.

    Source: bigquery-public-data.pypi.file_downloads — project-level
    aggregation, one row per (pypi_name, _PARTITIONDATE).

    Tunables:
      PHASE_P_DISABLED                   : "1" to skip
      PHASE_P_ENABLED                    : must be "1" (opt-in) to run
      PHASE_P_BQ_PROJECT                 : GCP project override
      PHASE_P_TTL_DAYS                   : default 30 (driver gate; monthly cadence)
      PHASE_P_RETAIN_DAYS                : default 95 (GC threshold; 5d slack beyond 90d window)
      PHASE_P_MAX_COST_USD               : default 10 (incremental cap)
      PHASE_P_MAX_COST_FIRST_PULL_USD    : default 100 (first-pull cap)
      PHASE_P_JOB_TIMEOUT_MS             : default 600000 (10 min wall-clock cap)
      PHASE_P_FORCE_FIRST_PULL           : "1" to wipe + re-bootstrap
    """
    import datetime
    t0 = time.monotonic()
    print("  Phase P: PyPI download counts via BigQuery (incremental v8.15.0)")

    # --- Gates (unchanged from v8.1.0) ---
    if os.environ.get("PHASE_P_DISABLED"):
        return _skip("PHASE_P_DISABLED=1 set", t0)
    if not os.environ.get("PHASE_P_ENABLED"):
        print("  Phase P is opt-in; set PHASE_P_ENABLED=1 to run.")
        return _skip("PHASE_P_ENABLED not set", t0)

    try:
        from google.cloud import bigquery
    except ImportError:
        return _skip("google-cloud-bigquery not importable", t0)

    bq_project = os.environ.get("PHASE_P_BQ_PROJECT") or None
    try:
        client = bigquery.Client(project=bq_project)
    except Exception as e:
        return _skip(f"BigQuery client init failed: {e}", t0)

    # --- Mode + window selection ---
    today = datetime.date.today()
    force_first = bool(os.environ.get("PHASE_P_FORCE_FIRST_PULL"))
    if force_first:
        conn.execute("DELETE FROM pypi_downloads_daily")

    last_row = conn.execute(
        "SELECT MAX(download_date) FROM pypi_downloads_daily"
    ).fetchone()
    last_date_str = last_row[0] if last_row else None

    if last_date_str is None:
        mode = "first-pull"
        window_start = today - datetime.timedelta(days=90)
        cap_usd = float(os.environ.get("PHASE_P_MAX_COST_FIRST_PULL_USD", "100"))
    else:
        last_date = datetime.date.fromisoformat(last_date_str)
        gap_days = (today - last_date).days
        if gap_days > 90:
            mode = "first-pull-after-gap"
            window_start = today - datetime.timedelta(days=90)
            cap_usd = float(os.environ.get("PHASE_P_MAX_COST_FIRST_PULL_USD", "100"))
            print(f"  gap since last refresh ({gap_days} d) > 90; "
                  f"reverting to first-pull mode")
        else:
            mode = "incremental"
            window_start = last_date + datetime.timedelta(days=1)
            cap_usd = float(os.environ.get("PHASE_P_MAX_COST_USD", "10"))

    window_end = today  # excluded
    if window_start >= window_end:
        elapsed = time.monotonic() - t0
        print(f"  pypi_downloads_daily already current through {last_date_str}; "
              f"no new partitions to query.")
        return {
            "skipped": True,
            "reason": "no new partitions since last refresh",
            "mode": mode,
            "duration_seconds": round(elapsed, 1),
        }

    # --- Build query (literal dates, no CURRENT_TIMESTAMP) ---
    query = f"""
        SELECT
            REGEXP_REPLACE(LOWER(file.project), r'[-_.]+', '-') AS pypi_name,
            _PARTITIONDATE AS download_date,
            COUNT(*) AS downloads
        FROM `bigquery-public-data.pypi.file_downloads`
        WHERE _PARTITIONDATE >= DATE '{window_start.isoformat()}'
          AND _PARTITIONDATE <  DATE '{window_end.isoformat()}'
        GROUP BY pypi_name, _PARTITIONDATE
    """

    # --- Dry-run preflight ---
    try:
        dry = client.query(
            query,
            job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False),
        )
        est_gb = dry.total_bytes_processed / 1e9
        est_usd = (est_gb / 1000.0) * 6.25
    except Exception as e:
        return _skip(f"BigQuery dry-run failed: {e}", t0)

    days = (window_end - window_start).days
    print(f"  mode={mode}; window=[{window_start}, {window_end}) "
          f"({days} d); dry-run: ~{est_gb:,.0f} GB scan, "
          f"est ~${est_usd:.2f} (cap ${cap_usd:.2f})")

    if est_usd > cap_usd:
        return {
            "skipped": True,
            "reason": (f"estimated ${est_usd:.2f} exceeds cap ${cap_usd:.2f}; "
                       f"raise PHASE_P_MAX_COST_USD or PHASE_P_MAX_COST_FIRST_PULL_USD "
                       f"to override"),
            "estimated_usd": round(est_usd, 2),
            "cap_usd": cap_usd,
            "mode": mode,
            "duration_seconds": round(time.monotonic() - t0, 1),
        }

    # --- Real query with hard byte cap + wall-clock timeout ---
    # Belt-and-braces: maximum_bytes_billed prevents runaway scan cost;
    # job_timeout_ms prevents zombie jobs charging slot time on flat-rate
    # billing accounts. Real queries complete in 30-60 s; 10 min is generous.
    max_bytes = int((cap_usd / 6.25) * 1e12)
    timeout_ms = int(os.environ.get("PHASE_P_JOB_TIMEOUT_MS", "600000"))
    try:
        rows = list(
            client.query(
                query,
                job_config=bigquery.QueryJobConfig(
                    maximum_bytes_billed=max_bytes,
                    job_timeout_ms=timeout_ms,
                ),
            ).result()
        )
    except Exception as e:
        return _skip(f"BigQuery query failed: {e}", t0)

    # --- Bulk INSERT into pypi_downloads_daily ---
    insert_rows = []
    for r in rows:
        name = r["pypi_name"]
        if not name:
            continue
        date_val = r["download_date"]
        date_str = date_val.isoformat() if hasattr(date_val, "isoformat") else str(date_val)
        insert_rows.append((name, date_str, int(r["downloads"])))

    conn.execute("BEGIN")
    try:
        conn.executemany(
            "INSERT OR IGNORE INTO pypi_downloads_daily "
            "(pypi_name, download_date, downloads) VALUES (?, ?, ?)",
            insert_rows,
        )
        rows_inserted = conn.execute(
            "SELECT changes()"
        ).fetchone()[0]

        # --- Recompute downloads_30d/90d from local table ---
        cutoff_30d = (today - datetime.timedelta(days=30)).isoformat()
        cutoff_90d = (today - datetime.timedelta(days=90)).isoformat()
        now = int(time.time())
        conn.execute("""
            INSERT INTO pypi_intelligence (
                pypi_name, downloads_30d, downloads_90d,
                downloads_fetched_at, downloads_source
            )
            SELECT
                pypi_name,
                COALESCE(SUM(CASE WHEN download_date >= ? THEN downloads ELSE 0 END), 0),
                COALESCE(SUM(downloads), 0),
                ?,
                'bigquery-incremental'
            FROM pypi_downloads_daily
            WHERE download_date >= ?
            GROUP BY pypi_name
            ON CONFLICT(pypi_name) DO UPDATE SET
                downloads_30d        = excluded.downloads_30d,
                downloads_90d        = excluded.downloads_90d,
                downloads_fetched_at = excluded.downloads_fetched_at,
                downloads_source     = excluded.downloads_source
        """, (cutoff_30d, now, cutoff_90d))

        # --- GC: prune old daily rows ---
        retain_days = int(os.environ.get("PHASE_P_RETAIN_DAYS", "95"))
        gc_cutoff = (today - datetime.timedelta(days=retain_days)).isoformat()
        rows_pruned = conn.execute(
            "DELETE FROM pypi_downloads_daily WHERE download_date < ?",
            (gc_cutoff,),
        ).rowcount

        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    elapsed = time.monotonic() - t0
    print(f"  Phase P done in {elapsed:.1f}s — mode={mode}, "
          f"inserted {rows_inserted:,} daily rows, pruned {rows_pruned:,}; "
          f"actual cost ~${est_usd:.2f}")
    return {
        "mode": mode,
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "rows_inserted": rows_inserted,
        "rows_pruned": rows_pruned,
        "estimated_usd": round(est_usd, 2),
        "source": "bigquery-incremental",
        "duration_seconds": round(elapsed, 1),
    }


def _skip(reason: str, t0: float) -> dict:
    return {
        "skipped": True,
        "reason": reason,
        "duration_seconds": round(time.monotonic() - t0, 1),
    }
```

### Cost-cap behavior (BigQuery semantics)

`bigquery.QueryJobConfig(maximum_bytes_billed=N)` is a **server-side
hard ceiling**:

- If the planner estimates ≤ N bytes, the query runs normally and bills
  on actual processed bytes.
- If actual processed bytes would exceed N, BQ aborts with HTTP 400
  `Query exceeded limit for bytes billed` and **bills $0** for that job.
- Operator gets a fail-fast signal, not a surprise invoice.

The dry-run preflight is a *softer* gate: it abort-with-clear-error
*before* submitting the real job, with a printable estimate. The real
query *also* carries `maximum_bytes_billed` as a defence-in-depth
backstop in case the planner re-estimates upward between dry-run and
live run.

Both gates respect the same operator-set cap. Tuning is a single env
var per mode.

### Profile integration

No change from v8.1.0:
- `admin`: sets `PHASE_P_ENABLED=1`. Picks up the new defaults.
- `maintainer`: does NOT enable Phase P.
- `consumer`: does NOT enable Phase P.

Operators on the admin profile see the new cost-cap behavior
automatically. To opt into a higher cap for a one-off catch-up run:

```bash
PHASE_P_MAX_COST_USD=25 pixi run -e local-recipes build-cf-atlas --profile admin
```

To force a clean first-pull (e.g., after suspecting daily-table
corruption):

```bash
PHASE_P_FORCE_FIRST_PULL=1 pixi run -e local-recipes build-cf-atlas --profile admin
```

---

## Stories — 3 waves, ~12 stories

### Wave A — Schema v26 + Phase P refactor (~6 stories)

| ID | Story | Effort |
|---|---|---|
| S1 | Add `pypi_downloads_daily` table + 2 indexes to SCHEMA_DDL; bump `SCHEMA_VERSION` 25 → 26 | XS |
| S2 | Schema v26 migration block in `init_schema` (idempotent guards via `pragma_table_info` + `IF NOT EXISTS`) | XS |
| S3 | Refactor `phase_p_pypi_downloads`: mode-selection logic, `_PARTITIONDATE`-literal query, dry-run preflight, hard byte cap, INSERT into `pypi_downloads_daily`, aggregation INSERT into `pypi_intelligence`, GC | L |
| S4 | Tunables: `PHASE_P_MAX_COST_USD`, `PHASE_P_MAX_COST_FIRST_PULL_USD`, `PHASE_P_RETAIN_DAYS`, `PHASE_P_JOB_TIMEOUT_MS`, `PHASE_P_FORCE_FIRST_PULL` (env-var contracts + documentation block in docstring) | XS |
| S5 | Drop unused tunable: `PHASE_P_BQ_WINDOW_DAYS` (declared in spec but unused; window is now mode-determined). Deprecate gently — log warning if set | XS |
| S6 | Add a `_skip` helper for the early-exit pattern used 6 times in the new function (DRY cleanup) | XS |

### Wave B — Tests + spec/doc corrections (~4 stories)

| ID | Story | Effort |
|---|---|---|
| S7 | Rewrite `tests/unit/test_phase_p_bigquery.py`: 8 new test cases covering mode selection (first-pull / incremental / gap-revert / no-op), dry-run abort, cap respected, GC prune, idempotent re-run | L |
| S8 | New `tests/unit/test_pypi_downloads_daily.py`: schema migration, INSERT OR IGNORE idempotency, aggregation correctness against fixture rows | M |
| S9 | Correct "~30 GB" misclaim across: spec line 105 + 134 + 743 in `docs/specs/atlas-pypi-intelligence.md`; docstring at `conda_forge_atlas.py:6250`; CHANGELOG entry for v8.1.0; `reference/atlas-phases-overview.md` line 45 + 242-245; `quickref/commands-cheatsheet.md` line 556. Replace with the empirical numbers + a pointer to the dry-run preflight | M |
| S10 | Add a new `reference/atlas-phase-p-cost-model.md` documenting the cost math, cap behavior, dry-run preflight semantics, and the BQ partition-pruning sensitivity that caused the 2026-06-12 surprise. Cross-link from `atlas-phases-overview.md` § Phase P | M |

### Wave C — Closeout (~3 stories)

| ID | Story | Effort |
|---|---|---|
| S11 | `CHANGELOG.md` v8.15.0 entry; SKILL.md heading bump; skill-config 8.9.x → 8.10.0; CFE retrospective per CLAUDE.md Rule 2 (this effort touches conda-forge work + ships skill updates) | M |
| S12 | Update `atlas-actionable-intelligence.md` catalog: Phase P entries gain a "cost-bounded" annotation + the operator-facing tunables. No new ✅-flips (functionality unchanged from consumer view) | S |
| S13 | Append a CLAUDE.md one-liner under "Project Documentation Reference" pointing at this spec | XS |

### Wave sequencing rationale

- **Wave A is the implementation.** Self-contained refactor — touches one
  function + one schema table + one set of env-var defaults. Ship-ready
  alone.
- **Wave B is correctness + truth-in-docs.** Tests guard the refactor;
  the doc corrections close the spec/code/CHANGELOG divergence that
  caused the cost surprise. Ships in the same PR as Wave A — no soak
  needed.
- **Wave C is closeout.** Single PR, single tag.

**Single-PR strategy** unless test work in S7+S8 exceeds review-load
preference. The schema change is additive, the refactor is local, and
the doc corrections all link to the same root cause.

---

## Acceptance Tests

### Wave A

- `tests/unit/test_pypi_downloads_daily.py::test_schema_v26_migration` —
  `init_schema` against a v25 DB produces v26 with the new table + 2
  indexes; idempotent on second run.
- `tests/unit/test_phase_p_bigquery.py::test_first_pull_window` — empty
  daily table → 90-day window submitted; cap defaults to $100.
- `tests/unit/test_phase_p_bigquery.py::test_incremental_window` — daily
  table populated through D-7 → window = [D-6, today); cap defaults
  to $10.
- `tests/unit/test_phase_p_bigquery.py::test_gap_revert_to_first_pull` —
  daily table's last row is 120 days ago → reverts to first-pull mode +
  $100 cap + warning logged.
- `tests/unit/test_phase_p_bigquery.py::test_no_new_partitions_noop` —
  daily table's last row is `today - 1` → query window is empty →
  early return with `skipped=True, reason="no new partitions"`.
- `tests/unit/test_phase_p_bigquery.py::test_dryrun_above_cap_aborts` —
  mocked dry-run returns `total_bytes_processed = 3e12` (~$18); cap is
  $10 → returns `skipped=True` with cost in the reason string;
  `client.query` is NOT called a second time.
- `tests/unit/test_phase_p_bigquery.py::test_maximum_bytes_billed_set` —
  real query is submitted with `QueryJobConfig.maximum_bytes_billed` ==
  `int((cap / 6.25) * 1e12)`.
- `tests/unit/test_phase_p_bigquery.py::test_job_timeout_ms_set` —
  real query is submitted with `QueryJobConfig.job_timeout_ms == 600000`
  by default; `PHASE_P_JOB_TIMEOUT_MS=120000` env override propagates.
- `tests/unit/test_phase_p_bigquery.py::test_pypi_intel_aggregation` —
  populated `pypi_downloads_daily` fixture → after Phase P,
  `pypi_intelligence.downloads_30d/90d` match the expected sums for the
  fixture's date ranges.
- `tests/unit/test_phase_p_bigquery.py::test_gc_prunes_old_rows` — rows
  older than `PHASE_P_RETAIN_DAYS=95` are deleted; rows within the
  window survive.

### Wave B

- `tests/meta/test_no_thirty_gb_lie.py` (new) — grep across spec/
  /reference/ /quickref/ /SKILL.md / CHANGELOG.md / `conda_forge_atlas.py`
  for the phrase "30 GB" near "Phase P" or "bigquery". Fails if any
  match survives. Guards against the bad-number regression.
- `tests/meta/test_phase_p_docstring_matches_envvars.py` (new) — parse
  the `phase_p_pypi_downloads` docstring for `PHASE_P_*` env-var
  mentions; cross-check against the names actually read by `os.environ.get`.
  Fails if either side drifts.

### Cross-cutting

- Full atlas rebuild against the dev `cf_atlas.db` at schema v26
  produces a sane `pypi_downloads_daily` with ~50k–100k unique
  `pypi_name` × ~90 `download_date` rows. `pypi_intelligence.downloads_30d`
  for the top 100 packages by downloads correlates within ~10% of the
  pre-fix `bigquery-public` values (sanity check for aggregation
  correctness — not bit-identical because of inflight days).
- Meta-test `test_actionable_scope.py` continues to recognize Phase P;
  no false drift flags from the table addition.
- Dry-run smoke (operator-runnable, not in CI): `PHASE_P_ENABLED=1
  PHASE_P_MAX_COST_USD=0.01 pixi run build-cf-atlas --profile admin` —
  should abort with "estimated $X exceeds cap $0.01" without submitting
  the real query.

---

## Risks

| Risk | Mitigation |
|---|---|
| Operator's BigQuery project has zero free-tier headroom left → even the dry-run reports a non-zero bill | Dry-run is FREE per BQ docs (no quota consumed). If we observe charges, document the surprise and switch the preflight to use the BQ pricing calculator REST endpoint instead |
| `_PARTITIONDATE` projection still scans more than estimated due to planner quirks | `maximum_bytes_billed` is a hard server-side cap; planner mis-estimation cannot exceed it. Worst case: job aborts with $0 bill and operator sees a clear error |
| 30-day window aggregation produces values that diverge from the old single-shot 90-day query (e.g., because the new approach counts whole-day partitions while the old one used a sliding `timestamp >=` predicate) | Document the off-by-up-to-1-day boundary semantics in `atlas-phase-p-cost-model.md`. Downstream consumers (`conda_forge_readiness`) use these as ordering signals — 1-day boundary error does not affect ranking |
| `pypi_downloads_daily` grows unbounded if GC fails | GC runs on every Phase P invocation; failure to prune is logged but doesn't fail the phase. Cron-style cleanup via `pixi run cf-atlas-gc` proposed as v8.16.0 follow-up |
| Operator runs back-to-back Phase P refreshes in a single day → tiny incremental window → many no-op INSERTs | `INSERT OR IGNORE` makes re-inserts a no-op. The `no new partitions` early return short-circuits before the query is even built |
| First-pull on a brand-new install runs against a stale `PHASE_P_MAX_COST_FIRST_PULL_USD` operator-defined value (e.g., set to "1") | Documented in `atlas-operations.md` § Phase P quickstart with explicit suggested values; dry-run output prints both the estimate and the cap so the operator can see they need to raise it |
| The `bigquery-public-data.pypi.file_downloads` schema changes (e.g., `file.project` renamed) | Phase P is opt-in and TTL-gated; a schema change surfaces as a BQ query failure on next refresh. Same failure mode as v8.1.0. Detection latency = TTL gap (default 30 d) |
| Storage delta (~225–450 MB) materially slows down DB clone / backup / sync operations | Air-gapped operators can disable Phase P entirely; the daily table is only created when Phase P first runs. Documented as a tradeoff in `reference/atlas-phase-p-cost-model.md` |
| The "spec / code / docs all carry the wrong number" lesson recurs | New meta-test `test_no_thirty_gb_lie.py` is the structural guard. Adds a new convention: cost claims in spec/code/docs must reference the dry-run preflight as the source of truth |

---

## Rollout

### Pre-merge

- Single-PR strategy: all 3 waves in one PR.
- BMAD agent executes waves in order; each wave's tests pass before the
  next starts.
- Manual smoke: operator runs `PHASE_P_ENABLED=1 PHASE_P_MAX_COST_USD=15
  pixi run build-cf-atlas --profile admin` against the dev `cf_atlas.db`
  to verify first-pull cost matches the dry-run estimate within ±10%.
- CFE skill version bump: 8.9.x → **8.10.0** (MINOR — additive schema +
  new env vars + new table; no breaking change to consumer surface).

### Merge order

- Single PR. No predecessor dependency. Can land after v8.9.0 (the
  maturin generator spec) ships, or in parallel if v8.9.0 doesn't
  touch `phase_p_*` (it does not — disjoint scope).

### Post-merge

- `CHANGELOG.md` v8.15.0 entry summarizing: schema v26 migration, Phase
  P refactor, new cost-cap env vars, the corrected "30 GB → ~30 GB/day"
  spec lie.
- `atlas-phases-overview.md` § Phase P updated with the cost model
  pointer.
- `atlas-operations.md` Phase P quickstart: new section "Cost
  expectations" with the per-cadence table, the cap-tuning recipe, and
  the force-first-pull recovery procedure.
- New `reference/atlas-phase-p-cost-model.md` — single source of truth
  for cost claims.
- Auto-memory feedback entry: **add** a `feedback_cost_claims_must_cite_dryrun.md`
  rule — "Any 'this BQ query scans N GB' claim in spec/code/docs MUST be
  paired with a dry-run preflight as the source of truth, not a copied
  napkin number." Cross-skill (BMAD specs + CFE), worth durable memory.

### Backout plan

- Schema v26 migration is reversible: `DROP TABLE pypi_downloads_daily`
  and downgrade SCHEMA_VERSION to 25.
- Phase P revert: restore the v8.1.0 single-shot query from git
  history. The `pypi_intelligence.downloads_30d/90d` columns continue
  to work; the new `downloads_source = 'bigquery-incremental'` rows
  remain valid (revert reader queries to accept both values).
- Doc corrections are not reverted (the old numbers were wrong).

---

## Open Questions

Q1, Q2, Q5, Q7 resolved 2026-06-12 by operator. Q3, Q4, Q6, Q8 carry
recommendations only; BMAD intake may proceed with the recommended
defaults or surface them for explicit resolution at sprint planning.

1. **Default refresh cadence — monthly (current) or weekly?** →
   **RESOLVED 2026-06-12: monthly.** `PHASE_P_TTL_DAYS=30` stays the
   default driver gate, matching v8.1.0 behavior. Weekly is the
   documented escape hatch (`PHASE_P_TTL_DAYS=7`) for operators who
   need fresher ranking signals; it fits comfortably under the $10/run
   cap (~$1.40/run empirically). Rationale: 30-day staleness on a
   download-popularity ranking is well within signal tolerance for
   `conda_forge_readiness` consumers; weekly buys little incremental
   value at the cost of 4× more refresh events to monitor.

2. **Should `PHASE_P_MAX_COST_USD` default to $10 or something tighter
   like $5?** → **RESOLVED 2026-06-12: $10.** Matches the operator's
   stated tolerance ("hard cap at 2 TB ~$10/run is the max I want to
   spend for refreshes"). $10 leaves headroom for an occasional
   ~60-day catch-up after a missed monthly cycle without manual
   intervention. Operators wanting tighter discipline can drop to $5
   via the env var; the dry-run preflight prints both estimate and cap
   so the right number is visible at run time.

3. **Per-version downloads — defer (matches `atlas-pypi-intelligence.md`
   Q2) or include in the daily table?** Including would multiply scan
   ~200×, blowing the cap. **Recommendation:** defer to v8.16.0+.
   `pypi_downloads_daily` schema deliberately omits `version` to keep
   this door open without committing.

4. **Pricing-flex per region — does the operator's BQ project live in
   a non-default region where on-demand pricing differs from $6.25/TB?**
   The cost-model math assumes US pricing. **Recommendation:** read
   `PHASE_P_USD_PER_TB` env override (default 6.25); document the EU
   and APAC variants in the cost-model doc.

5. **Should the live query also carry a 5-min timeout / `job_timeout_ms`
   to prevent a runaway "slot starvation" scenario?** →
   **RESOLVED 2026-06-12: yes, `job_timeout_ms = 600000` (10 min).**
   Belt-and-braces complement to `maximum_bytes_billed`: byte-cap
   prevents runaway scan cost, timeout prevents zombie jobs charging
   slot time on flat-rate billing accounts. Real queries complete in
   30-60 s; a 10-min cap is generous and aborts with a clear error
   well before any zombie-job scenario becomes expensive. Operator
   override via `PHASE_P_JOB_TIMEOUT_MS` for the rare case where a
   first-pull on a slow region needs more wall-clock headroom.

6. **ClickHouse `clickpy` as a verification source for the test suite?**
   Could compare top-1000 counts from BQ vs ClickHouse as an unit-test
   sanity check. Network-dependent, brittle in CI. **Recommendation:**
   document the comparison procedure in `atlas-phase-p-cost-model.md`
   as an operator-runnable diagnostic; no CI integration.

7. **What's the right value for `PHASE_P_RETAIN_DAYS` — 95 (5 days
   slack) or higher (e.g., 180) for year-over-year analysis?** →
   **RESOLVED 2026-06-12: 95.** Minimizes storage (~225-450 MB
   steady-state); 5-day slack covers any boundary edge cases between
   the 90-day window and the GC sweep. 180 (or 365) is documented as
   the operator-tunable escape hatch for the day operator demand for
   `downloads_180d` / year-over-year analysis surfaces — at that point
   the storage delta becomes ~450-900 MB which is a deliberate
   admin-tier tradeoff. Default stays tight; door is left open.

8. **Backward-compat handling for the existing
   `downloads_source = 'bigquery-public'` rows after v8.15.0 ships.**
   Should the migration recompute them from a forced first-pull, or
   leave them in place until natural TTL expiry overwrites them?
   **Recommendation:** leave in place. They're valid data from the
   pre-fix query. `downloads_fetched_at` lets consumers detect
   staleness independently of the source label.

---

## References

### Source-of-truth code (current state — v8.14.x baseline)

- `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py`:
  - `SCHEMA_VERSION` (line 137) — bump 25 → 26
  - SCHEMA_DDL block — add `pypi_downloads_daily` table + 2 indexes
  - `init_schema` migration block — add v26 sub-block
  - `phase_p_pypi_downloads` (line 6237) — full refactor
  - PHASES registry — no change (Phase P slot unchanged)
- `.claude/skills/conda-forge-expert/scripts/bootstrap_data.py` (line
  175) — no change; `admin` profile continues to set `PHASE_P_ENABLED=1`
- `.claude/skills/conda-forge-expert/tests/unit/test_phase_p_bigquery.py` —
  rewrite per Wave B
- `.claude/skills/conda-forge-expert/tests/unit/test_pypi_downloads_daily.py` —
  NEW
- `.claude/skills/conda-forge-expert/tests/meta/test_no_thirty_gb_lie.py` —
  NEW (regression guard)
- `.claude/skills/conda-forge-expert/tests/meta/test_phase_p_docstring_matches_envvars.py` —
  NEW (drift guard)

### Related specs

- `docs/specs/atlas-pypi-intelligence.md` — v8.1.0 introduced Phase P
  and `pypi_intelligence`. This spec rewrites the Phase P body while
  preserving the consumer surface. Spec lines 105, 134, 743 carry the
  "~30 GB" lie that this effort corrects.
- `docs/specs/conda-forge-expert-v8.0.md` — v8.0.0 introduced personas.
  Phase P's `admin`-tier opt-in continues unchanged.
- `docs/specs/atlas-phase-f-s3-backend.md` — v7.6.0 introduced source
  dispatch via `PHASE_F_SOURCE`. This spec does NOT add a source
  switch for Phase P (operator stays on BigQuery); follow-up spec
  may add `PHASE_P_SOURCE = bigquery | clickpy | ecosystems` if
  operators want a no-creds path.

### Audit context

- **Conversation log 2026-06-12** — "the last refresh cost over $500
  dollars for the bigquery pypi data refresh". This spec is the
  recorded fix.
- **BigQuery dry-run output** (operator-verifiable): `bq query
  --dry_run --use_legacy_sql=false '<query>'` returns
  `totalBytesProcessed`. Empirical baseline as of 2026-06-12: a 90-day
  `_PARTITIONDATE`-pruned + `file.project + _PARTITIONDATE`-projected
  query reports ~2.7 TB processed; on-demand cost ~$17.

### Documentation

- `.claude/skills/conda-forge-expert/SKILL.md` — Atlas Intelligence
  Layer heading update to v8.15.0
- `.claude/skills/conda-forge-expert/CHANGELOG.md` — v8.15.0 entry per
  Rule 2
- `.claude/skills/conda-forge-expert/reference/atlas-phases-overview.md` —
  Phase P section updated with the cost-model pointer; "30 GB" lie
  removed
- `.claude/skills/conda-forge-expert/reference/atlas-phase-p-cost-model.md` —
  NEW; single source of truth for cost claims, dry-run preflight
  semantics, cap-tuning, force-first-pull recovery
- `.claude/skills/conda-forge-expert/reference/atlas-actionable-intelligence.md` —
  catalog annotation update (no flips)
- `.claude/skills/conda-forge-expert/guides/atlas-operations.md` —
  Phase P quickstart gains a "Cost expectations" section
- `.claude/skills/conda-forge-expert/quickref/commands-cheatsheet.md` —
  Phase P cost-cap recipes; "30 GB" lie removed
- `CLAUDE.md` — add `docs/specs/atlas-phase-p-incremental.md` to the
  BMAD-consumable spec list (one-line entry under Project Documentation
  Reference)

---

<a id="p8"></a>

# Part 8 — Phase F/F+ S3 backend + richer metrics + breakdown CLIs (Waves 1–3)

> Formerly `atlas-phase-f-s3-backend.md` — shipped v7.6.0 + v8.17.0 / v8.18.0 / v8.19.0 (2026-05-10 → 2026-06-13).
> Original frontmatter: `status: shipped; implemented_by: bmad-quick-dev; shipped_ref: "Wave 1: v7.6.0 + v8.17.0; Wave 2: v8.18.0; Wave 3: v8.19.0"; spec_updated: 2026-07-02`

> **Consolidated record (2026-07-02).** This file merges the three shipped Phase F / Phase F+
> intake specs into one historical record:
>
> - **[Part 1](#part-1)** — the original S3/parquet-backend umbrella spec (this file's original
>   body). Shipped **v7.6.0** (S3 backend + `PHASE_F_SOURCE` dispatcher) + **v8.17.0** (admin
>   profile default-flip).
> - **[Part 2](#part-2)** — the Wave 2 richer-metrics focused intake (formerly
>   `atlas-phase-f-wave2-richer-metrics.md`). Shipped **v8.18.0** (commit f28ed3ea56, 2026-06-13);
>   the v8.18.1 retro landed sub-rules (g)/(h)/(i) in `reference/atlas-phase-engineering.md` § 10.
> - **[Part 3](#part-3)** — the Wave 3 CLI-surface focused intake (formerly
>   `atlas-phase-f-wave3-cli-surface.md`). Shipped **v8.19.0** (commit d5095dde18, 2026-06-13);
>   the v8.19.1 retro landed sub-rules (j)/(k) in `reference/atlas-phase-engineering.md` § 10.
>
> Part bodies are preserved verbatim from the pre-merge files; only frontmatter was consolidated
> and cross-file links between the three parts rewritten to in-file anchors. Textual mentions of
> the two former filenames inside part bodies are historical and refer to the parts above.

<a id="part-1"></a>

# Part 1 — S3/parquet backend umbrella spec (Waves 0–1)

> Original frontmatter before the merge: `status: shipped; implemented_by: bmad-quick-dev; shipped_ref: "v7.6.0 + v8.17.0 (Wave 1; Waves 2-3 split to wave2/wave3 specs)"; spec_updated: 2026-06-20`

# Tech Spec: Atlas Phase F — S3 / condastats backend + Phase F+ metrics

> **BMAD intake document.** Written for `bmad-quick-dev` (Quick Flow track —
> well-bounded, single-skill scope, ~14 implementation stories in 4 waves).
> Run BMAD with this file as the intent document:
>
> ```
> run quick-dev — implement the intent in docs/specs/atlas-phase-f-s3-backend.md
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
| Surface area | `conda-forge-expert` skill — atlas pipeline (Phase F / Phase F+) + 3 new CLIs / MCP tools |
| Scope | (1) S3 backfill backend for Phase F; (2) richer Phase F+ metrics from same sweep; (3) `platform_breakdown` / `pyver_breakdown` / `channel_split` CLIs and MCP tools |
| Out of scope | Daily-granularity downloads, defaults-channel atlas, BigQuery integration |
| Created | 2026-05-10 |

---

## Background and Context

### The problem

`conda-forge-expert`'s atlas pipeline Phase F is the only stage of the
9-phase build that has **no firewall-friendly alternative source**. It
fetches per-package download counts from `https://api.anaconda.org/package/conda-forge/{name}`
— one HTTP request per package, ~32k requests for a cold backfill — and
those counts feed `staleness_report`, `package_health`, `version_downloads`,
`release_cadence`, and the staleness-score column used by `find_alternative`
and `adoption_stage`.

Two problems compound:

1. **Air-gapped / enterprise-firewall users** that block `*.anaconda.org`
   today have no fallback. The atlas builds, but every `total_downloads`
   column ends up NULL and the affected MCP tools return blanks. The
   workaround documented in `_http.py` (`ANACONDA_API_BASE` env var) only
   helps if the operator has already stood up their own mirror of the
   anaconda.org API, which is rare.
2. **The API surface is information-poor.** It gives only cumulative
   `ndownloads` per artifact. Time-series, platform breakdown, and
   per-python-version distribution are absent — even though the
   downstream consumers (`platform_breakdown` is on the v8 roadmap;
   python_min policy enforcement currently relies on intuition rather
   than data) could use them.

### What's been ruled out

- **BigQuery (pypistats-style).** No public BigQuery dataset mirrors
  conda-forge downloads. `condastats` itself reads from S3, not BigQuery.
- **Defaults-channel-only data.** Plenty of internal Anaconda dashboards
  exist; none are publicly accessible.
- **Per-build-hash granularity.** The S3 dataset is keyed by version
  string, not build hash. Acceptable — Phase F doesn't use build hashes
  either.
- **Daily granularity.** S3 publishes monthly parquet files only.
  Acceptable — Phase F's TTL is already 7 days and downstream consumers
  use downloads as a coarse signal.

### What's available to leverage

- **Public S3 bucket `s3://anaconda-package-data/`** — `conda/monthly/{YYYY}/{YYYY-MM}.parquet`.
  No auth required, listable over HTTPS, served from `*.s3.amazonaws.com`
  (different host than `*.anaconda.org`). **Verified current 2026-05-10:**
  `2026-04.parquet` uploaded 2026-05-01 17:34 UTC, monthly cadence intact
  since the 2024 condastats relaunch.
- **Parquet schema** (verified):
  `time` (YYYY-MM) · `data_source` (channel) · `pkg_name` · `pkg_version` ·
  `pkg_platform` · `pkg_python` · `counts`. 6 dimensions, 1 metric, ~13MB/month.
- **`_http.py`** already provides the JFrog/GitHub/.netrc auth chain and
  truststore injection. Adding S3 HTTPS as a routable host is a small extension.
- **`pyarrow`** is already a dependency of the `local-recipes` pixi env
  via `pandas` and `duckdb`. No new top-level dep needed.
- **Existing Phase F schema** (`packages.total_downloads`,
  `latest_version_downloads`, `downloads_fetched_at`, `downloads_fetch_attempts`,
  `downloads_last_error`) and Phase I side-effect table
  (`package_version_downloads`) are well-defined; the S3 backend writes
  to the same shape.

### Verified discrepancies (informational)

Comparing API totals vs S3-lifetime sums for three packages on 2026-05-10:

| Package | API `ndownloads` sum | S3 lifetime sum (conda-forge) | Ratio |
|---|---:|---:|---:|
| `requests` | 81,699,781 | 122,921,283 | 1.50× |
| `django` | 3,317,504 | 1,861,625 | 0.56× |
| `bmad-method` | 3,625 | 3,084 | 0.85× (partial May missing) |

**Implication:** the two sources are not numerically identical and the
gap direction is not consistent. Phase F+ must persist a
`downloads_source` discriminator and report consumers must surface it.
Treat the two as correlated-but-distinct metrics, not interchangeable.

---

## Goals

- **G1.** **Air-gap parity for Phase F.** With `*.anaconda.org` blocked, an
  atlas build must still populate `total_downloads` and
  `latest_version_downloads` to within "order-of-magnitude-correct, ranking-correct"
  fidelity, using only `*.s3.amazonaws.com` (or a JFrog mirror of it).
- **G2.** **No regression for online users.** When `*.anaconda.org` is
  reachable and `PHASE_F_SOURCE=auto`, behavior matches today's Phase F
  exactly — same numbers, same TTL gating, same throughput envelope.
- **G3.** **Source attribution.** Every `packages` row carries a
  `downloads_source` column so reports can disclose which dataset
  produced the number.
- **G4.** **Richer metrics from the same data pass** — rolling 30/90-day
  downloads, 90-day trend slope, first/last non-zero month, per-platform
  and per-python download breakdowns. Computed in one parquet sweep, no
  extra network.
- **G5.** **Three new operator CLIs / MCP tools** —
  `platform_breakdown`, `pyver_breakdown`, `channel_split` — each
  reading only from the atlas DB (offline-safe by construction).
- **G6.** **JFrog/enterprise-mirror routable.** S3 HTTPS URLs route
  through `_http.py` so `JFROG_API_KEY` / `JFROG_USERNAME+PASSWORD`
  authenticate transparently against a mirrored copy.
- **G7.** **Local cache for parquet.** Static monthly files cache to
  `.claude/data/conda-forge-expert/cache/parquet/` and are re-fetched
  only when the current month rolls over or the cache file is corrupt.

## Non-Goals

- **NG1.** No daily granularity. Monthly is what S3 publishes; we don't
  synthesize finer resolution.
- **NG2.** No backfill of channels other than `conda-forge`. Phase F
  has always been conda-forge-scoped; the `data_source` filter stays.
- **NG3.** No BigQuery integration. Spec stays within the published S3
  parquet surface.
- **NG4.** No automatic anaconda.org → S3 reconciliation logic.
  Discrepancies are surfaced (via `downloads_source`), not "fixed."
- **NG5.** No per-build-hash drill-down. Version is the finest grain.
- **NG6.** No new persistence of data we already compute on demand
  (e.g., we don't materialize "downloads per (package, platform, month)"
  for all 32k × 11 × 110 = 38M rows; we aggregate to the cuts we need).
- **NG7.** No web UI / dashboard. CLI + MCP tools only; rendering is
  downstream's job.
- **NG8.** No `condastats` Python package dependency. We read parquet
  directly via `pyarrow` — same data source, fewer dep layers.

---

## Lifecycle Expectations

- **One-time backfill cost** when first enabled: ~110 parquet files
  (~13 MB each, ~1.4 GB total) downloaded sequentially over residential
  bandwidth in ~5–10 minutes. Cached locally; subsequent runs fetch only
  the new current-month file (~13 MB).
- **Per-atlas-run cost** in steady state: one HTTP GET for the current
  month's parquet (if it's the first run that month) plus the existing
  Phase F TTL gating; otherwise zero new network.
- **Schema migration** is forward-only and idempotent — same pattern as
  existing Phase F column additions.

---

## User Stories

Stories grouped into 4 waves. **Wave 1 ships the air-gap fix as a
minimum-viable result** (G1, G2, G3); subsequent waves layer on G4–G7.

### Wave 0 — Foundations

#### Story 1 — S3 HTTPS routing in `_http.py`

Extend `_http.py` so requests to `https://anaconda-package-data.s3.amazonaws.com/`
participate in the same resolver chain that already handles
`https://conda.anaconda.org/conda-forge/`:

- Add `resolve_s3_parquet_urls(month: str) -> list[str]` returning, in
  order: `S3_PARQUET_BASE_URL` env override, JFrog-mirrored URL if
  configured, then the public S3 HTTPS URL.
- Inject JFrog auth headers automatically when `JFROG_API_KEY` or
  `JFROG_USERNAME+PASSWORD` are set and the resolved host matches the
  enterprise prefix.
- Add `list_s3_parquet_months() -> list[str]` that probes the S3
  list-objects-v2 XML endpoint (`?list-type=2&prefix=conda/monthly/`)
  and parses out `YYYY-MM` keys. Cached for the lifetime of one atlas run.

#### Story 2 — Parquet cache + reader helper

Create `scripts/_parquet_cache.py` (NEW; private module like `_http.py`,
`_sbom.py`):

- `cache_dir()` → `.claude/data/conda-forge-expert/cache/parquet/`
  (created on first use, gitignored).
- `ensure_month(month: str) -> Path`: downloads `YYYY-MM.parquet` via
  `_http.py` if not cached or if `month` equals the current month (always
  refresh current month in case mid-month updates land — they don't, per
  the dataset docs, but cheap insurance).
- `read_filtered(months: list[str], pkg_names: set[str] | None = None,
  data_source: str = 'conda-forge') -> pa.Table`: reads listed parquet
  files with pushdown filters on `data_source` and (optional) `pkg_name`.
  Uses `pyarrow.parquet.read_table` with the `filters=` arg — no
  pandas/duckdb round-trip in the hot path.

#### Story 3 — Atlas schema migration v17 → v18

Add columns to `packages` table:

- `downloads_source TEXT` — one of `'anaconda-api'`, `'s3-parquet'`,
  `'merged'`, or `NULL` if Phase F has never run for this row.
- `downloads_30d INTEGER`
- `downloads_90d INTEGER`
- `downloads_trend_90d REAL` — pct change vs prior 90-day window
  (positive = growing); `NULL` if fewer than 6 months of data.
- `first_nonzero_month TEXT` — `'YYYY-MM'` of earliest non-zero
  downloads month.
- `last_nonzero_month TEXT` — `'YYYY-MM'` of most recent non-zero
  downloads month.

Add two new tables:

- `package_platform_downloads` — `(conda_name, pkg_platform,
  downloads_90d, downloads_total, fetched_at)`. Indexed on
  `(conda_name)`.
- `package_python_downloads` — `(conda_name, pkg_python,
  downloads_90d, downloads_total, fetched_at)`. Indexed on
  `(conda_name)`.

Migration is forward-only and follows the existing
`_apply_pending_migrations` pattern. Schema version bumps to **v18**
(currently v17 per `conda_forge_atlas.py`); add an entry to the
migrations list and verify the test that asserts the migration version.

### Wave 1 — Phase F S3 backfill (air-gap fix; minimum viable)

#### Story 4 — `PHASE_F_SOURCE` env var + source dispatch

Refactor `phase_f_downloads` to read `PHASE_F_SOURCE` (default `auto`):

- `anaconda-api` — current behavior, unchanged.
- `s3-parquet` — skip the API entirely; read from cached parquet.
- `auto` — try API per row; on `urllib.error.URLError` or 5xx without
  successful response after retries, fall back to S3 for that row
  (`downloads_source = 'merged'` when API succeeded for *most* rows
  but S3 filled gaps; `'s3-parquet'` when API was unreachable entirely).

`auto` mode probes reachability by attempting one API call against a
small known package (`pip`) before launching the worker pool; on failure
it short-circuits to `s3-parquet` for the whole run rather than burning
retries 32k times.

#### Story 5 — `s3-parquet` Phase F implementation

When `s3-parquet` mode is selected:

- Determine the months to load (default: all available; respect
  `PHASE_F_S3_MONTHS` env var as a count of trailing months, e.g.
  `PHASE_F_S3_MONTHS=24` for the last 2 years only — useful for
  reduced-disk-footprint deployments).
- Download missing months via Story 2's `ensure_month`.
- Run a single `pyarrow` aggregation:
  ```python
  SELECT pkg_name,
         SUM(counts) AS total_downloads,
         MIN(time) AS first_nonzero_month,
         MAX(time) AS last_nonzero_month
  FROM <parquets>
  WHERE data_source = 'conda-forge' AND counts > 0
  GROUP BY pkg_name
  ```
- For `latest_version_downloads`, run a second aggregation grouped by
  `(pkg_name, pkg_version)` and pluck the row matching each package's
  `latest_conda_version`.
- Bulk-update `packages` in batches of 500 (same transaction pattern as
  today's API path). Set `downloads_source='s3-parquet'`.

Update `package_version_downloads` (Phase I side-effect table) from the
same per-version aggregation — but **set `upload_unix` to `NULL` when
sourcing from S3** since the parquet has no upload-time column. Add a
`source TEXT` column to `package_version_downloads` to track this.

#### Story 6 — `auto` mode merge + reachability probe

Implement the reachability probe and the per-row merge:

- Probe: `urllib.urlopen(API_URL_FOR_PIP, timeout=10)`. On success, run
  the existing API path. On failure, log the reason and fall through to
  `s3-parquet`.
- Per-row failure recovery: when `PHASE_F_CONCURRENCY` workers report
  >25% failure rate after the first 1,000 rows, abort the API pool, drop
  to `s3-parquet`, and continue.
- Source attribution: `downloads_source='anaconda-api'` for rows
  fetched cleanly via API; `'s3-parquet'` for rows whose API call failed
  and were filled from S3; `'merged'` when both contributed.

### Wave 2 — Phase F+ richer metrics

#### Story 7 — Rolling 30 / 90-day download windows

In the parquet aggregation pass, compute:

- `downloads_30d` = SUM(counts) WHERE time = most-recent-month and time
  is no more than 30 days behind today. (Single-month at monthly
  resolution; documented as such.)
- `downloads_90d` = SUM(counts) WHERE time IN (last 3 months available).

Write to the new columns from Story 3. Do this in the same parquet
sweep — no extra reads.

#### Story 8 — 90-day trend slope

Compute `downloads_trend_90d` as
`(downloads_90d - downloads_prev_90d) / downloads_prev_90d` where
`downloads_prev_90d` is the SUM over months 4–6 trailing.

- Returns `NULL` if either window has zero downloads (avoid div-by-zero)
  or if fewer than 6 months of data exist for the package.
- Sign convention: positive = growing; negative = declining.
- Cap at `+10.0` to dampen new-package "infinite growth" outliers in
  reporting.

#### Story 9 — Platform breakdown aggregation

Per package, aggregate per-platform downloads over the last 3 months
(`downloads_90d`) and lifetime (`downloads_total`), write to
`package_platform_downloads`. Filter out empty `pkg_platform` (noarch
folds into `''` which becomes a synthetic platform `'noarch'` in the
output table for clarity).

#### Story 10 — Python-version breakdown aggregation

Same pattern as Story 9, against `pkg_python`. Add a data-quality
filter: drop rows where `pkg_python` doesn't match the regex
`^(2\.7|3\.[0-9]{1,2})$` (the parquet contains a few dirty values like
`2.30`, `7.3`, `3.81` — confirmed via inspection on 2026-05-10).

### Wave 3 — New CLIs and MCP tools

#### Story 11 — `platform_breakdown` CLI + MCP tool

Create `.claude/skills/conda-forge-expert/scripts/platform_breakdown.py`
(canonical) and `.claude/scripts/conda-forge-expert/platform_breakdown.py`
(CLI wrapper).

CLI surface:

```
platform-breakdown <package>                  # one-package detail
platform-breakdown --top 50 --platform linux-aarch64    # rank packages by aarch64 share
platform-breakdown --feedstock-roundup        # group by feedstock_name for maintainer triage
```

Reads only from atlas SQLite. Emits markdown table by default, JSON
with `--json`. Add to `pixi.toml` as a task; register as MCP tool in
`conda_forge_server.py`.

#### Story 12 — `pyver_breakdown` CLI + MCP tool

Mirror of Story 11 against `package_python_downloads`. Two
domain-specific modes:

- `pyver-breakdown <package>` — single-package table; calls out the
  smallest python version with ≥2% downloads as the "empirical
  python_min floor."
- `pyver-breakdown --policy-check <package>` — compares the recipe's
  declared `python_min` (read via the existing recipe parser) against
  the empirical floor; flags packages where `python_min` is more
  conservative than the data justifies (i.e., bump-safe candidates).

#### Story 13 — `channel_split` CLI + MCP tool

Aggregates downloads across `data_source` (channels). Unlike Stories 11–12,
this requires reading parquet at query time because the atlas DB only
stores conda-forge data. So:

- Cache the channel-split aggregation in a fourth small table,
  `package_channel_downloads` (`conda_name, data_source, downloads_90d,
  downloads_total`), populated during the Phase F+ sweep (one extra
  group-by, ~negligible cost).
- CLI: `channel-split <package>` — table of channel × download volume
  for the last 90 days; flags packages with significant defaults-channel
  share (>10%) as migration-opportunity targets.

#### Story 14 — Tests, docs, SKILL.md updates

- Unit tests for `_parquet_cache.py` (mock S3 responses, verify cache
  hit/miss logic, verify month list parsing).
- Integration test for Phase F `auto` mode: mocked API failure forces
  S3 path; assert `downloads_source` is set correctly.
- Add `PHASE_F_SOURCE`, `PHASE_F_S3_MONTHS`, `S3_PARQUET_BASE_URL` to
  `.claude/skills/conda-forge-expert/quickref/commands-cheatsheet.md`.
- Update `.claude/skills/conda-forge-expert/SKILL.md` "Atlas
  Intelligence Layer" section with the new CLIs.
- Update
  `.claude/skills/conda-forge-expert/reference/atlas-actionable-intelligence.md`
  with the three new tools mapped to personas (esp.
  `pyver-breakdown --policy-check` under § Feedstock Maintainer →
  Decisions, and `platform-breakdown --feedstock-roundup` under same
  section). Also update the Phase F row in
  `.claude/skills/conda-forge-expert/reference/atlas-phases-overview.md`
  with the new aggregate tables and CLIs.
- Per CLAUDE.md Rule 2, end with a CHANGELOG.md entry and a
  `bmad-retrospective` run focused on the CFE skill.

---

## Functional Requirements

### FR-1: Air-gap parity (G1)

With `PHASE_F_SOURCE=s3-parquet` and only `*.s3.amazonaws.com` (or a
JFrog-mirrored equivalent) reachable, `pixi run -e local-recipes
build-cf-atlas` must complete Phase F with non-NULL `total_downloads`
for ≥95% of active conda-forge packages.

### FR-2: Online no-regression (G2)

With `PHASE_F_SOURCE=auto` (default) and full network, the atlas's
Phase F output must match the current production behavior — same
columns populated, same TTL gating, same ±0% throughput. Verified by
running both old and new code paths on the same DB snapshot and diffing
the `packages` table.

### FR-3: Source attribution (G3)

Every populated `downloads_*` cell carries a non-NULL `downloads_source`
value (`anaconda-api` | `s3-parquet` | `merged`). MCP tools that emit
download counts (`package_health`, `staleness_report`,
`version_downloads`) include the source in their output.

### FR-4: Cache discipline

- Parquet cache lives under
  `.claude/data/conda-forge-expert/cache/parquet/`; gitignored.
- Current-month file always refreshed on first atlas run of a month
  (timestamp-based).
- `cache_dir` cleanup CLI: `clean-parquet-cache --older-than 12m` for
  operators wanting to bound disk usage.

### FR-5: JFrog routing

S3 HTTPS URLs flow through `_http.py`'s resolver. The env-var sequence
that wins:

1. `S3_PARQUET_BASE_URL` — full base, e.g.
   `https://jfrog.internal/anaconda-package-data` (host + path prefix
   that mirrors S3 layout).
2. `JFROG_API_KEY` or `JFROG_USERNAME+PASSWORD` → injected on requests
   whose host matches `*.jfrog.*` or the `S3_PARQUET_BASE_URL` host.
3. Public S3 HTTPS — fallback.

### FR-6: Schema migration safety

Migration v17 → v18 must run cleanly on:

- Fresh DB (creates new columns / tables alongside existing schema).
- v17 DB with existing Phase F data (adds columns with `NULL` defaults;
  no data loss).
- v18 DB (idempotent — no-op).

### FR-7: New-CLI offline guarantee

`platform_breakdown`, `pyver_breakdown`, and `channel_split` must
complete with zero network access when the atlas DB has been built.
Verified by running them under `unshare -n` (or equivalent) in CI.

### FR-8: Data quality guardrails

- Empty/dirty `pkg_python` values are filtered out of `pyver_breakdown`
  output (Story 10 regex).
- Packages with zero downloads in the last 90 days are omitted from
  "top N" rankings (avoid noise from dead packages).
- Packages first published in the current or previous month are flagged
  as "insufficient history" rather than reported as `downloads_90d=0`.

---

## Technical Approach

### Stack

- **Reader:** `pyarrow.parquet.read_table` with `filters=`. Already
  available via `local-recipes` pixi env. No `duckdb`, no `pandas`, no
  `s3fs`, no `boto3`.
- **HTTP:** existing `_http.py` extended with one new resolver function.
- **Cache:** plain filesystem under existing
  `.claude/data/conda-forge-expert/cache/` tree.
- **Schema:** SQLite migrations in the existing
  `_apply_pending_migrations` framework in `conda_forge_atlas.py`.

### File layout (delta only)

```
.claude/skills/conda-forge-expert/scripts/
  _parquet_cache.py            NEW  (private module, ~120 LOC)
  _http.py                     EDIT (+~40 LOC for S3 resolver)
  conda_forge_atlas.py         EDIT (Phase F refactor; Phase F+ aggregations;
                                     schema v18 migration)
  platform_breakdown.py        NEW  (~150 LOC)
  pyver_breakdown.py           NEW  (~180 LOC; includes --policy-check)
  channel_split.py             NEW  (~120 LOC)

.claude/scripts/conda-forge-expert/
  platform_breakdown.py        NEW  (thin subprocess wrapper)
  pyver_breakdown.py           NEW  (thin subprocess wrapper)
  channel_split.py             NEW  (thin subprocess wrapper)

.claude/tools/
  conda_forge_server.py        EDIT (+3 @mcp.tool registrations)

.claude/data/conda-forge-expert/cache/parquet/    NEW DIR (gitignored)

.claude/skills/conda-forge-expert/
  SKILL.md                     EDIT (Atlas Intelligence Layer + Critical Constraints
                                     section noting api.anaconda.org failure mode)
  CHANGELOG.md                 EDIT (v7.x or v8.0.0 entry per retro semver call)
  quickref/commands-cheatsheet.md  EDIT
  reference/atlas-actionable-intelligence.md    EDIT
  reference/atlas-phases-overview.md            EDIT (Phase F row)

pixi.toml                      EDIT (+3 task entries)

tests/                         EDIT (+new test files; +meta-test SCRIPTS list
                                     per feedback_cfe_new_script_three_places)
```

**Memory checkpoint:** per `feedback_cfe_new_script_three_places`, each
new script touches three places: pixi.toml task + SCRIPTS list in
`test_all_scripts_runnable.py` + wrapper. Story 14 must verify all
three for each of `platform_breakdown`, `pyver_breakdown`,
`channel_split`.

### Schemas

```sql
-- packages additions (migration v18)
ALTER TABLE packages ADD COLUMN downloads_source TEXT;
ALTER TABLE packages ADD COLUMN downloads_30d INTEGER;
ALTER TABLE packages ADD COLUMN downloads_90d INTEGER;
ALTER TABLE packages ADD COLUMN downloads_trend_90d REAL;
ALTER TABLE packages ADD COLUMN first_nonzero_month TEXT;
ALTER TABLE packages ADD COLUMN last_nonzero_month TEXT;

CREATE TABLE IF NOT EXISTS package_platform_downloads (
    conda_name       TEXT NOT NULL,
    pkg_platform     TEXT NOT NULL,
    downloads_90d    INTEGER,
    downloads_total  INTEGER,
    fetched_at       INTEGER,
    PRIMARY KEY (conda_name, pkg_platform)
);
CREATE INDEX idx_ppd_conda_name ON package_platform_downloads(conda_name);

CREATE TABLE IF NOT EXISTS package_python_downloads (
    conda_name       TEXT NOT NULL,
    pkg_python       TEXT NOT NULL,
    downloads_90d    INTEGER,
    downloads_total  INTEGER,
    fetched_at       INTEGER,
    PRIMARY KEY (conda_name, pkg_python)
);
CREATE INDEX idx_ppyd_conda_name ON package_python_downloads(conda_name);

CREATE TABLE IF NOT EXISTS package_channel_downloads (
    conda_name       TEXT NOT NULL,
    data_source      TEXT NOT NULL,
    downloads_90d    INTEGER,
    downloads_total  INTEGER,
    fetched_at       INTEGER,
    PRIMARY KEY (conda_name, data_source)
);
CREATE INDEX idx_pcd_conda_name ON package_channel_downloads(conda_name);

-- existing package_version_downloads gets a source column
ALTER TABLE package_version_downloads ADD COLUMN source TEXT;
```

### Env-var matrix (final)

| Var | Default | Purpose |
|---|---|---|
| `PHASE_F_SOURCE` | `auto` | `auto` / `anaconda-api` / `s3-parquet` |
| `PHASE_F_DISABLED` | unset | (existing) skip Phase F entirely |
| `PHASE_F_TTL_DAYS` | `7` | (existing) per-row skip cutoff |
| `PHASE_F_CONCURRENCY` | `8` | (existing) API worker pool |
| `PHASE_F_LIMIT` | `0` | (existing) row cap for debugging |
| `PHASE_F_S3_MONTHS` | `0` (= all) | trailing months to load from S3 |
| `S3_PARQUET_BASE_URL` | unset | enterprise mirror override |
| `ANACONDA_API_BASE` | unset | (existing) enterprise API mirror |
| `CONDA_FORGE_BASE_URL` | unset | (existing) enterprise channel mirror |
| `JFROG_API_KEY` / `JFROG_USERNAME` / `JFROG_PASSWORD` | unset | (existing) injected by `_http.py` |

### Key decisions

- **Why not `s3fs` / `boto3`?** Anonymous public-read of static URLs
  doesn't justify the dep weight. Direct HTTPS via `_http.py` reuses
  the JFrog auth path we already maintain.
- **Why not store full monthly time-series in SQLite?** 32k pkgs ×
  110 months ≈ 3.5M rows of low-value data. The aggregated derivatives
  (rolling 30/90-day, trend, first/last nonzero) deliver 90% of the
  utility at ~32k rows. Operators wanting the full series can read the
  parquet directly.
- **Why one consolidated parquet sweep instead of streaming?** All
  Phase F+ metrics (rolling windows, trend, platform/python/channel
  breakdowns) derive from the same data — running them as one pyarrow
  pass with multiple group-bys is much cheaper than 5 separate passes.
- **Why `auto` mode probes with `pip`?** It's the most-downloaded
  package; the API call returns a small payload (~5KB metadata) but
  reliably exercises the same code path as the real fetches. A failure
  there is a strong signal the rest will fail.
- **Why cap `downloads_trend_90d` at +10.0?** New packages can show
  +1000% growth (1 download → 1000 downloads in 3 months); uncapped,
  they dominate "top growing" rankings. +10.0 (1000%) is the threshold
  beyond which the signal stops being useful for triage.

---

## Acceptance Criteria (Whole Feature)

- **AC-1.** `pixi run -e local-recipes build-cf-atlas` with
  `PHASE_F_SOURCE=s3-parquet` and `*.anaconda.org` blocked at the
  network level populates `total_downloads` for ≥95% of active
  conda-forge packages.
- **AC-2.** `pixi run -e local-recipes build-cf-atlas` with default
  env (no `PHASE_F_SOURCE` set, `*.anaconda.org` reachable) produces
  output that diffs identically against pre-change behavior on the
  `total_downloads`, `latest_version_downloads`,
  `downloads_fetched_at`, `downloads_fetch_attempts`,
  `downloads_last_error` columns.
- **AC-3.** `staleness_report`, `package_health`, `version_downloads`
  MCP tools include `downloads_source` in their response payloads.
- **AC-4.** New CLIs `platform-breakdown`, `pyver-breakdown`,
  `channel-split` each run end-to-end against a real
  `local-recipes`-built atlas DB and emit sensible markdown +
  `--json`.
- **AC-5.** `pyver-breakdown --policy-check requests` (or any other
  popular package) returns an empirical python_min suggestion that's
  internally consistent with the per-version download distribution.
- **AC-6.** `unshare -n env PHASE_F_SOURCE=s3-parquet pixi run …` —
  or equivalent network-disabled test — fails with a clear error
  pointing at S3, NOT with a cryptic socket error.
- **AC-7.** Re-running with a pre-warmed cache completes the parquet
  step in <5 seconds; verified by timing log.
- **AC-8.** All three new scripts pass the
  `test_all_scripts_runnable.py` meta-test (i.e., the SCRIPTS list +
  pixi.toml task + wrapper trio per the
  `feedback_cfe_new_script_three_places` rule).
- **AC-9.** CHANGELOG.md has a new version entry (PATCH if no
  unexpected gotchas surfaced; MINOR if new ones did); the retro
  CHANGELOG entry references this spec by filename.

---

## Open Questions

### Must answer (v1-blocking)

- **OQ-1.** Should `auto` mode's API failure trigger an S3 backfill for
  *only the failed rows*, or fall back to the bulk S3 read for *all
  rows*? Bulk is simpler and pre-warms the cache; per-row is more
  precise. Recommendation: bulk-fallback on probe failure; per-row
  marker only when the API path mostly worked but had isolated 5xxs.
- **OQ-2.** Is `pip` the right reachability probe target, or should it
  be a hash-stable "canary" package the team owns? `pip` is robust to
  Anaconda Inc. reorganizations of its API; a canary is more
  deterministic but adds maintenance burden. Recommendation: `pip`.

### Behavior — confirm or override

- **OQ-3.** Should `downloads_source='merged'` apply when EITHER the
  per-package total OR the per-version table was sourced from S3 (not
  both)? Recommendation: yes, to make the discriminator broadly
  meaningful as "treat this row's download data as approximate."
- **OQ-4.** Should the S3 backfill respect `PHASE_F_LIMIT`? In API
  mode, limit caps per-row HTTP requests. In S3 mode, the cost is one
  big read regardless of row count. Recommendation: limit caps which
  rows get *written* (post-aggregation slice), not which rows get
  read.

### v2 — explicitly deferred

- **OQ-5.** `condastats`-style pip install path for users who don't
  want `pyarrow` directly? Defer to user request; `pyarrow` is already
  in env.
- **OQ-6.** Full per-month time-series materialized in SQLite for use
  in dashboards? Defer; the parquet cache is the source for that.
- **OQ-7.** Daily granularity via anaconda.org S3 `daily/` prefix
  (if it exists — unconfirmed)? Defer; verify the prefix exists before
  speccing.

### Genuinely open (design call)

- **OQ-8.** Should `find_alternative` rank candidates with the new
  `downloads_90d` instead of cumulative `total_downloads`? Recent
  activity is a better "is this maintained" signal but breaks
  ranking-stability across atlas rebuilds. Defer to Wave 3 user
  feedback.

---

## Dependencies and Constraints

- **`pyarrow`** — already in `local-recipes` pixi env via pandas.
  Verified.
- **Python 3.11+** — same baseline as the atlas pipeline today.
- **No new top-level deps.** Stays inside the existing env footprint.
- **Conda-forge atlas DB at v17+** before migration to v18. Migration
  framework handles the version bump itself.
- **`_http.py`** must already inject SSL truststore + JFrog auth
  (verified; the existing code path handles this for conda-forge
  channel URLs and will extend cleanly to S3).
- **CLAUDE.md Rule 1** (BMAD invokes `conda-forge-expert` first) and
  **Rule 2** (effort closes with a CFE-skill retro) apply.

---

## Out of Scope (Explicit)

- **OoS-1.** Mirroring the S3 dataset to a non-AWS location is the
  operator's problem; the spec provides the env-var hooks
  (`S3_PARQUET_BASE_URL`) but doesn't ship mirroring tooling.
- **OoS-2.** Backfilling `package_version_downloads.upload_unix` from
  some third source when S3 is used as the data source. The column is
  set to `NULL` and tagged `source='s3-parquet'`; consumers must
  tolerate missing upload times in that case.
- **OoS-3.** `bioconda`-channel or `pytorch`-channel atlas pipelines.
  The parquet sweep reads only `data_source='conda-forge'`. The
  channel-split CLI surfaces the others for awareness but doesn't
  build an atlas over them.
- **OoS-4.** Reconciling specific numeric discrepancies between API
  and S3. The `downloads_source` discriminator is the documentation;
  fixing the upstream is Anaconda Inc.'s call.
- **OoS-5.** Web dashboards consuming the new tables. MCP tools and
  CLIs only.

---

## References

### Code (source of truth)

- `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py`
  Phase F at `phase_f_downloads` (~L1453); Phase I side-effect at
  `package_version_downloads` schema (~L233).
- `.claude/skills/conda-forge-expert/scripts/_http.py` — JFrog auth
  chain at `_make_req`; conda-forge URL resolver at
  `resolve_conda_forge_urls`.
- `.claude/tools/conda_forge_server.py` — `@mcp.tool` registration
  pattern for the three new tools.

### Documentation

- `.claude/skills/conda-forge-expert/SKILL.md` — Atlas Intelligence
  Layer section; Critical Constraints; Operating Principles.
- `.claude/skills/conda-forge-expert/reference/atlas-actionable-intelligence.md`
  — persona map for the new CLIs.
- `.claude/skills/conda-forge-expert/reference/atlas-phases-overview.md`
  — Phase F row gets the new aggregate tables and CLIs.
- `.claude/skills/conda-forge-expert/quickref/commands-cheatsheet.md`
  — env-var matrix lands here.
- `docs/enterprise-deployment.md` — JFrog routing context; the air-gap
  case study this spec resolves.

### External

- Public S3 bucket: `https://anaconda-package-data.s3.amazonaws.com/`
  — list endpoint: `?list-type=2&prefix=conda/monthly/`.
- condastats: `https://github.com/conda-incubator/condastats` —
  reference implementation, not a dependency.
- condastats relaunch announcement:
  `https://conda.org/blog/condastats-is-back/` — confirms the dataset
  is live and updated monthly.

### Memory

- `feedback_cfe_new_script_three_places.md` — each new script touches
  pixi.toml + SCRIPTS list + wrapper.
- `project_cf_atlas_rattler_502.md` — context on why Phase B uses
  `current_repodata.json` (parallel rationale: HTTPS-static URLs are
  more enterprise-friendly than fancier protocols).
- `project_cf_atlas_suite.md` — atlas evolves quickly; this spec
  bumps to **v8.0.0** (MINOR for new schema + tools, MAJOR if Wave 1
  ships with a behavior change to `total_downloads` defaults — retro
  team decides).

---

## Suggested BMAD Invocation

```
# From repo root:
run quick-dev — implement the intent in docs/specs/atlas-phase-f-s3-backend.md

# Wave-by-wave execution recommended:
# - Wave 0+1 in one pass (foundations + air-gap fix; ships value alone)
# - Wave 2 in a second pass (Phase F+ metrics)
# - Wave 3 in a third pass (new CLIs / MCP tools)
# Close with bmad-retrospective per CLAUDE.md Rule 2.
```


---

<a id="part-2"></a>

# Part 2 — Wave 2 focused intake: richer metrics

> Original frontmatter before the merge: `status: shipped; implemented_by: bmad-quick-dev; shipped_ref: "v8.18.0"; spec_updated: 2026-06-20`

# Tech Spec: Atlas Phase F+ Wave 2 — richer metrics from the existing parquet sweep

> **BMAD intake document.** Focused execution scope for `bmad-quick-dev`
> (Quick Flow track — well-bounded, single-skill, ~5 stories).
>
> ```
> run quick-dev — implement the intent in docs/specs/atlas-phase-f-wave2-richer-metrics.md
> ```
>
> **Parent spec** (canonical detail): [`docs/specs/atlas-phase-f-s3-backend.md`](#part-1).
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

- [`docs/specs/atlas-phase-f-s3-backend.md`](#part-1)
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


---

<a id="part-3"></a>

# Part 3 — Wave 3 focused intake: CLI surface

> Original frontmatter before the merge: `status: shipped; implemented_by: bmad-quick-dev; shipped_ref: "v8.19.0"; spec_updated: 2026-06-20`

# Tech Spec: Atlas Phase F+ Wave 3 — `platform_breakdown` / `pyver_breakdown` / `channel_split` CLIs + MCP

> **BMAD intake document.** Focused execution scope for `bmad-quick-dev`
> (Quick Flow track — well-bounded, single-skill, ~6 stories).
>
> ```
> run quick-dev — implement the intent in docs/specs/atlas-phase-f-wave3-cli-surface.md
> ```
>
> **Parent specs** (canonical detail):
> - [`docs/specs/atlas-phase-f-s3-backend.md`](#part-1) — full Wave 0–3 design (Stories 11/12/13/14 are Wave 3).
> - [`docs/specs/atlas-phase-f-wave2-richer-metrics.md`](#part-2) — Wave 2 brief (shipped as v8.18.0).
>
> Wave 1 (S3 backend + dispatcher + provenance column) shipped in v7.6.0;
> Wave 1 admin default-flip in v8.17.0; Wave 2 (richer metrics + breakdown
> tables) in v8.18.0. Wave 3 ships the consumer-facing CLIs that read the
> Wave 2 tables.
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
| Track | BMAD Quick Flow (parent spec carries PRD/architecture detail) |
| Scope | (1) `platform_breakdown` CLI + MCP tool; (2) `pyver_breakdown` CLI + MCP tool incl. `--policy-check`; (3) `channel_split` CLI + MCP tool; (4) Wave 2 leftover — populate `package_channel_downloads` during the existing parquet sweep so `channel_split` has data to read. |
| Out of scope | Wave 4 richer metrics; new aggregation tables beyond `package_channel_downloads`; recipe-format consumers (the CLIs are read-only) |
| Predecessor | `atlas-phase-f-wave2-richer-metrics.md` (shipped v8.18.0) |
| Successor | none planned |
| Created | 2026-06-13 |

---

## Background and Context

Wave 2 (v8.18.0) materialized two read-side tables in the atlas DB:

- `package_platform_downloads(conda_name, pkg_platform, downloads_90d, downloads_total, fetched_at)`
- `package_python_downloads(conda_name, pkg_python, downloads_90d, downloads_total, fetched_at)`

Both populated from the same `_phase_f_via_s3` parquet sweep that runs under `--profile admin`. No CLI exposes them yet — they exist for Wave 3 to consume.

Wave 3 ships **three new operator CLIs**, each backed by an existing Wave 2 table (plus one minor Wave 2 leftover for channel_split):

1. **`platform_breakdown`** — reads `package_platform_downloads`. Maintainer-triage signal for "should I drop osx-x86_64 from feedstock X?" questions.
2. **`pyver_breakdown`** — reads `package_python_downloads`. Includes a `--policy-check` flag that compares the recipe's declared `python_min` against the empirical downloads floor and flags bump-safe candidates.
3. **`channel_split`** — reads a NEW `package_channel_downloads` table that Wave 3 adds + populates during the existing parquet sweep. Surfaces packages with significant defaults-channel share (migration opportunity targets).

All three CLIs are **offline-safe by construction** — they read only from `cf_atlas.db`, never from the network. They're symmetric in shape to existing CLIs (`staleness-report`, `feedstock-health`, `behind-upstream`): markdown table by default, `--json` for machine output, `--top N` for ranking, `--feedstock-roundup` where applicable.

### What's already shipped (do not re-implement)

- `package_platform_downloads` + `package_python_downloads` tables — v8.18.0 schema v27.
- `_phase_f_via_s3` extended parquet sweep — v8.18.0; reads 6 parquet dimensions.
- `downloads_30d` / `downloads_90d` / `downloads_trend_90d` / `first_nonzero_month` / `last_nonzero_month` on `packages` — v8.18.0.
- `PHASE_F_FORCE_REFRESH=1` sentinel + env-var — v8.18.0.
- CLI wrapper pattern (`.claude/scripts/conda-forge-expert/<name>.py` → `python .claude/skills/conda-forge-expert/scripts/<name>.py`) — used by every existing CLI.
- MCP tool registration pattern in `.claude/tools/conda_forge_server.py` — 30+ tools already registered.

### Schema target

Wave 3 adds **one new table** for channel_split:

```sql
CREATE TABLE IF NOT EXISTS package_channel_downloads (
    conda_name        TEXT NOT NULL,
    data_source       TEXT NOT NULL,   -- channel: conda-forge / bioconda / defaults / etc.
    downloads_90d     INTEGER NOT NULL,
    downloads_total   INTEGER NOT NULL,
    fetched_at        INTEGER NOT NULL,
    PRIMARY KEY (conda_name, data_source)
);
CREATE INDEX IF NOT EXISTS idx_package_channel_downloads_conda_name
    ON package_channel_downloads(conda_name);
```

**Schema migration**: v27 → v28. Same forward-only + IF NOT EXISTS pattern as v8.18.0. No new columns on `packages`.

---

## Goals

- **G1.** `platform_breakdown` CLI + MCP tool reading `package_platform_downloads` with three modes: single-package detail, `--top N --platform <p>` ranking, `--feedstock-roundup` maintainer grouping.
- **G2.** `pyver_breakdown` CLI + MCP tool reading `package_python_downloads` with a `--policy-check <pkg>` flag that surfaces the empirical Python floor vs. the recipe's declared `python_min`.
- **G3.** `channel_split` CLI + MCP tool reading a new `package_channel_downloads` table, with a defaults-channel-share filter (>10% by default).
- **G4.** Populate `package_channel_downloads` from the existing `_phase_f_via_s3` parquet sweep — one additional group-by on the loaded pyarrow Table, same single-pass discipline as Wave 2 (§ 10 (g) + (h) of `atlas-phase-engineering.md`).
- **G5.** All three CLIs registered as MCP tools in `conda_forge_server.py` and as `pixi.toml` tasks.
- **G6.** Schema migration v27 → v28 is forward-only, idempotent, and follows the `INSERT OR REPLACE` semantic discipline from v8.18.1 § 10 (g) (DELETE + INSERT for breakdown tables on partial re-runs).

---

## Non-Goals

- **NG1.** No new external data sources. Wave 3 reads only from `cf_atlas.db` and the cached parquet (via the existing `_phase_f_via_s3` extension for `package_channel_downloads`).
- **NG2.** No "recommend python_min bump" auto-fixer. `pyver_breakdown --policy-check` surfaces the data; the maintainer decides.
- **NG3.** No dashboard / web UI. CLI + MCP tools only.
- **NG4.** No retro-fitting Wave 2 columns to per-channel resolution (`packages.downloads_90d` stays conda-forge-scoped; `package_channel_downloads` carries the per-channel cuts).
- **NG5.** No per-(package, channel, month) full time-series materialization. 90-day + lifetime totals only, same discipline as Wave 2.
- **NG6.** No write-side surface from any of the three CLIs. Read-only.

---

## User Stories

### Story 1 — Schema migration v27 → v28 + `package_channel_downloads` Wave 2 leftover

Add the new table to `SCHEMA_DDL`:

```sql
CREATE TABLE IF NOT EXISTS package_channel_downloads (
    conda_name        TEXT NOT NULL,
    data_source       TEXT NOT NULL,
    downloads_90d     INTEGER NOT NULL,
    downloads_total   INTEGER NOT NULL,
    fetched_at        INTEGER NOT NULL,
    PRIMARY KEY (conda_name, data_source)
);
CREATE INDEX IF NOT EXISTS idx_package_channel_downloads_conda_name
    ON package_channel_downloads(conda_name);
```

Bump `SCHEMA_VERSION` 27 → 28. Add v27 → v28 comment block to `init_schema`. No new `packages` columns. Migration is purely additive (CREATE TABLE IF NOT EXISTS).

**Force-refresh sentinel** (carried forward from v8.18.0 v26 → v27): the v27 → v28 migration writes `meta.phase_f_force_refresh_pending = '1'` so the first post-migration Phase F run re-aggregates the cached parquet and populates `package_channel_downloads` immediately.

### Story 2 — Extend `_phase_f_via_s3` with a per-(pkg, channel) group-by

In the same parquet sweep, group by `(pkg_name, data_source)` (i.e. raw parquet channel column) for:

- `downloads_90d` (last 3 months — same window as Wave 2)
- `downloads_total` (lifetime)

Bulk-write into `package_channel_downloads` using **DELETE-by-scope-key + INSERT OR REPLACE** in the same transaction (per v8.18.1 § 10 (g)). The DELETE pattern mirrors Wave 2's v8.18.0 H1 fix:

```sql
DELETE FROM package_channel_downloads WHERE conda_name IN (<chunked, 500-row batches>);
-- then bulk INSERT OR REPLACE for the new rows
```

**No new env vars.** No filter on `data_source` (unlike Wave 2's parquet sweep which filters to `'conda-forge'` for the main aggregations) — the channel breakdown intentionally captures all channels the parquet ships, including `defaults` / `bioconda` / `pytorch` / `nvidia` / etc.

### Story 3 — `platform_breakdown` CLI + MCP tool

**File**: `.claude/skills/conda-forge-expert/scripts/platform_breakdown.py` (canonical) + `.claude/scripts/conda-forge-expert/platform_breakdown.py` (thin wrapper).

**CLI surface**:

```
platform-breakdown <package>                                # one-package detail
platform-breakdown --top 50 --platform linux-aarch64        # rank packages by aarch64 share
platform-breakdown --top 50 --platform win-64               # ARM/win-64 share table
platform-breakdown --feedstock-roundup --maintainer X       # group by feedstock_name for maintainer triage
platform-breakdown --json                                   # machine output
```

**Output (single-package, default)**:

```
numpy — per-platform downloads (90d)
─────────────────────────────────────────────
Platform          90d downloads    Share
linux-64          1,234,567        62.3 %
linux-aarch64       234,567        11.8 %
osx-arm64           198,765        10.0 %
osx-64              112,345         5.7 %
win-64               98,765         5.0 %
noarch                5,432         0.3 %
─────────────────────────────────────────────
Total             1,984,441        100 %
```

Reads only from `cf_atlas.db` (`packages` join `package_platform_downloads`). Offline-safe.

### Story 4 — `pyver_breakdown` CLI + MCP tool incl. `--policy-check`

**File**: `.claude/skills/conda-forge-expert/scripts/pyver_breakdown.py` (canonical) + wrapper.

**Two-mode CLI**:

```
pyver-breakdown <package>                          # single-package python-version distribution
pyver-breakdown --policy-check <package>           # compare declared python_min vs. empirical floor
pyver-breakdown --policy-check --maintainer X      # batch policy-check across maintainer's feedstocks
pyver-breakdown --policy-check --threshold-pct 2.0 # change the "noise floor" (default 2 %)
```

**Single-package mode output**:

```
numpy — per-Python downloads (90d)
─────────────────────────────────────────────
Python            90d downloads    Share
3.12              1,234,567        62.3 %
3.11                567,890        28.7 %
3.10                123,456         6.2 %
3.13                 45,678         2.3 %
3.9                  10,234         0.5 %
─────────────────────────────────────────────
Empirical python_min floor (≥2%): 3.10
```

**Policy-check mode**:

For each package, read the recipe's declared `python_min` (via the existing recipe parser used by `validate_recipe.py`) AND compute the empirical floor (the smallest python with ≥`--threshold-pct` share of 90-day downloads). Flag packages where:

- `empirical_floor > declared_min` → **bump-safe candidate** (operator can raise the recipe's python_min without losing material adoption).
- `empirical_floor < declared_min` → **already-aggressive** (no action; recipe is already at or below the empirical floor).
- `empirical_floor == declared_min` → **aligned** (no action).

**Output (policy-check, default)**:

```
Python-min policy check — maintainer rxm7706
─────────────────────────────────────────────────────────────────
Feedstock              Declared    Empirical   Status         90d Δ
numpy                  3.10        3.11        bump-safe     -123k (3.10 share)
pandas                 3.10        3.10        aligned       —
some-niche             3.11        3.10        aggressive    +12k (3.10 share)
─────────────────────────────────────────────────────────────────
```

Reads from `packages` (declared `python_min` via recipe parser; cached column if available) + `package_python_downloads`.

### Story 5 — `channel_split` CLI + MCP tool

**File**: `.claude/skills/conda-forge-expert/scripts/channel_split.py` (canonical) + wrapper.

**CLI surface**:

```
channel-split <package>                          # single-package channel distribution
channel-split --defaults-share-min 10.0          # rank packages by defaults share (migration targets)
channel-split --defaults-share-min 10.0 --top 50 # top-50 by defaults share
channel-split --json
```

**Single-package output**:

```
matplotlib — per-channel downloads (90d)
─────────────────────────────────────────────
Channel           90d downloads    Share
conda-forge       2,345,678        72.1 %
defaults            567,890        17.5 %
bioconda            234,567         7.2 %
pytorch             100,000         3.1 %
nvidia                3,210         0.1 %
─────────────────────────────────────────────
Migration opportunity: 17.5 % on defaults — consider rerendering for cross-channel adoption.
```

**Top-50 mode**: list packages with `>= --defaults-share-min` defaults share, ranked by absolute defaults 90d downloads (not share — high-absolute-volume is the actionable target).

### Story 6 — Tests, docs, SKILL.md updates, MCP registration, CHANGELOG, retro

- **Unit tests** for each of the 3 new scripts: fixture DB with seeded data, assert table-output shape, assert `--json` payload, assert `--policy-check` correctly compares declared vs. empirical.
- **Schema migration test**: `tests/unit/test_schema_v28_migration.py` mirrors v27's pattern. Fresh DB / v27 → v28 upgrade / already-v28 idempotency cases. Asserts `SCHEMA_VERSION == 28` + new table exists.
- **Phase F dispatch test extension**: 1 new case in `TestS3ParquetWave2Metrics` (now arguably `TestS3ParquetWave2And3Metrics`) verifying `package_channel_downloads` populates with expected channel cuts after a sweep.
- **MCP registration** in `.claude/tools/conda_forge_server.py` for all 3 new tools, following the existing pattern (one decorator per tool, one wrapper function each).
- **`pixi.toml` tasks** for all 3 new CLIs (`platform-breakdown`, `pyver-breakdown`, `channel-split`).
- **Reference docs**: update `atlas-phases-overview.md` Phase F section with the new table; update `atlas-actionable-intelligence.md` — five rows for `platform_breakdown` modes + four rows for `pyver_breakdown` + two rows for `channel_split` all flip from `📋 open` to `✅ shipped (v8.19.0)`.
- **`SKILL.md` Atlas Intelligence Layer section** gains the three new CLIs in the "Daily-use CLIs" list.
- **`CHANGELOG.md`** v8.19.0 entry per Rule 2.
- **Retro** at `_bmad-output/projects/local-recipes/implementation-artifacts/retro-cfe-phase-f-wave3-<DATE>.md`.

---

## Functional Requirements

### FR-1: Read-only contract

All three CLIs read only from `cf_atlas.db`. No `urllib`, no `requests`, no network access at runtime. Verified by `grep -r "urllib\|requests" .claude/skills/conda-forge-expert/scripts/{platform_breakdown,pyver_breakdown,channel_split}.py` returning zero hits.

### FR-2: Offline-safe by atlas dependency

If the atlas DB is missing or stale, the CLIs print a clear error message pointing at `bootstrap-data --profile admin` and exit non-zero. No partial output.

### FR-3: `--json` machine output on all three

Every CLI supports `--json` and emits a stable, documented schema (list of records keyed by `conda_name` + dimension). Consumers should be able to pipe to `jq` and `gh` without parsing the markdown table.

### FR-4: `--policy-check` data freshness

`pyver_breakdown --policy-check` skips packages whose `package_python_downloads.fetched_at` is older than `PHASE_F_TTL_DAYS=7` and prints a "stale; run `bootstrap-data --profile admin` to refresh" notice. Threshold is per-package, not global.

### FR-5: Channel breakdown discipline (v8.18.1 § 10 (g))

`_phase_f_via_s3`'s new `package_channel_downloads` write uses **DELETE-by-scope-key + INSERT OR REPLACE** in the same transaction. Re-running Phase F replaces per-package channel rows, doesn't accumulate zombies when a channel's downloads drop to zero.

### FR-6: Provenance attribution (v8.18.1 § 10 (h))

The new `package_channel_downloads` rows are populated **only** when the parquet sweep runs (i.e. when `_phase_f_via_s3` writes the corresponding `packages.downloads_source='s3-parquet'`). The API-path fallback (`_phase_f_via_api`) does NOT touch `package_channel_downloads`. Verified by grepping the writers.

### FR-7: Schema migration safety

v27 → v28 runs cleanly on:
- Fresh DB (`--fresh`).
- Existing v27 DB (in-place upgrade — adds the new table).
- Already-v28 DB (idempotent no-op).

Per v8.18.1 § 10 (i), this Wave-3 ship goes through the step-04 three-reviewer adversarial pass.

---

## Technical Approach

### Where the code lands

- **`scripts/conda_forge_atlas.py`** — `SCHEMA_VERSION` bump 27 → 28; new `CREATE TABLE IF NOT EXISTS package_channel_downloads` in `SCHEMA_DDL`; v27 → v28 comment block; `_phase_f_via_s3` extended with one more group-by + DELETE+INSERT writer (mirrors v8.18.0's H1 pattern).
- **`scripts/platform_breakdown.py`** (NEW) — argparse + SQL queries + markdown formatter + `--json` mode.
- **`scripts/pyver_breakdown.py`** (NEW) — same pattern; `--policy-check` mode reads recipe's `python_min` (use the existing recipe parser from `validate_recipe.py` if helpful).
- **`scripts/channel_split.py`** (NEW) — same pattern; `--defaults-share-min` filter.
- **`.claude/scripts/conda-forge-expert/{platform_breakdown,pyver_breakdown,channel_split}.py`** — thin wrappers (5-line subprocess.run pattern as documented).
- **`pixi.toml`** — 3 new tasks.
- **`.claude/tools/conda_forge_server.py`** — 3 new MCP tool decorators.
- **`tests/unit/test_schema_v28_migration.py`** (NEW) — mirrors v27 test.
- **`tests/unit/test_platform_breakdown.py`** (NEW), **`tests/unit/test_pyver_breakdown.py`** (NEW), **`tests/unit/test_channel_split.py`** (NEW).
- **`tests/unit/test_phase_f_dispatch.py`** — 1 new case for `package_channel_downloads` write.

### Key implementation notes

- **Recipe parser for `--policy-check`**: prefer to read the cached `python_min` from `packages` (if Wave 2 or earlier stored it; if not, this becomes a Wave 4 issue). If not cached, parse `recipes/<name>/recipe.yaml` via the existing recipe parser. Document the fallback.
- **Channel-name normalization**: parquet ships `data_source` as raw channel string (e.g. `'conda-forge'`, `'defaults'`, `'bioconda'`). No normalization — write as-is. Consumers see exactly what the parquet has.
- **`platform_breakdown --top --platform`**: rank by **absolute 90d downloads on that platform**, not share. High-absolute-volume on a niche platform is the actionable signal (e.g. "this 50k-download-on-aarch64 package is one of the top-20 aarch64-loved packages").

### Env-var matrix

Wave 3 ships **no new env vars**. CLI flags are the only operator-tunable surface.

---

## Acceptance Criteria (Whole Feature)

- **AC-1.** Schema migration v27 → v28 runs cleanly on fresh + existing v27 + already-v28 DBs; tests cover all three.
- **AC-2.** After `--profile admin` populates the DB, `package_channel_downloads` has ≥1 row per `(conda_name, 'conda-forge')` pair for packages with `downloads_source='s3-parquet'`.
- **AC-3.** `platform_breakdown numpy` (or any populated package) prints a markdown table with ≥3 platform rows + a Total line; `--json` returns a list of dicts with `conda_name`, `pkg_platform`, `downloads_90d`, `downloads_total`, `share_pct`.
- **AC-4.** `pyver_breakdown --policy-check <pkg>` flags ≥1 known bump-safe candidate from the seeded test fixture; categories are `bump-safe`, `aligned`, `aggressive`.
- **AC-5.** `channel_split --defaults-share-min 10.0 --top 10` returns ≤10 rows, each with `defaults_share_pct >= 10.0`, sorted by absolute 90d defaults downloads DESC.
- **AC-6.** All 3 CLIs registered as pixi tasks AND as MCP tools; `mcp list` shows them.
- **AC-7.** Test suite 1,386 → ≥1,410 passing (≥24 new tests across 3 CLI test files + schema migration test + dispatch extension). 0 failed, 0 errors.
- **AC-8.** Step-04 adversarial review pass runs (per v8.18.1 § 10 (i)); any HIGH/MED findings either auto-patched (`patch` classification) or pre-resolved (`bad_spec`/`intent_gap` triggers loopback to step-02).
- **AC-9.** Closeout per CLAUDE.md Rule 2: CHANGELOG v8.19.0 + retro artifact + actionable-intelligence catalog rows flipped to `✅ shipped (v8.19.0)`.

---

## Open Questions

### Pre-resolved (recommendations)

- **OQ-1.** Should `pyver_breakdown --policy-check` consume the recipe's declared `python_min` from the SQLite atlas (if cached) or always reparse `recipes/<name>/recipe.yaml`? **Recommendation: cached if available, fall back to reparse with a stale-warning if not.** Reparse on every `--policy-check` invocation would be slow for `--maintainer X` batch runs.

- **OQ-2.** Should `platform_breakdown --feedstock-roundup` group by `feedstock_name` (which exists on `packages`) or `conda_name` (one row per package)? **Recommendation: `feedstock_name`** — that's the maintainer's mental model (one feedstock = one rerender target).

- **OQ-3.** Should `channel_split` use the parquet's raw `data_source` strings or normalize to a canonical channel name (e.g. `'main'` vs `'defaults'`)? **Recommendation: raw, no normalization.** Consumers see exactly what the parquet has; if normalization is needed later, it lives in a Wave 4 layer.

- **OQ-4.** What's the noise floor for `--policy-check`? **Recommendation: 2 % default**, overridable via `--threshold-pct N.M`. Aligns with the parent spec's "smallest python with ≥2% downloads" definition.

### Genuinely open (design call — surface at intake)

- **OQ-5.** Should `pyver_breakdown --policy-check` also surface packages where the empirical floor is *strictly less than* the declared min (`aggressive` category)? Or hide them since the maintainer can't act ("already-good" feedback)? **Recommendation: surface but de-prioritize** — sort the output so `bump-safe` candidates appear first; `aggressive` rows are background information.

- **OQ-6.** Should the three CLIs share a common `--format markdown|json|csv` flag, or keep `--json` as the single non-default? **Recommendation: just `--json`** — CSV is rare for atlas consumers (most pipe to `jq`); a single flag is simpler.

- **OQ-7.** Should `channel_split` add a `--migration-checklist` mode that emits a markdown checklist suitable for pasting into a GitHub issue ("[ ] Open conda-forge feedstock for <pkg>; defaults has X% share")? **Recommendation: defer to Wave 4** — keep Wave 3 read-only and stick to numeric output.

---

## Dependencies and Constraints

- **`package_platform_downloads`** + **`package_python_downloads`** at v27 (shipped v8.18.0). Verified `SCHEMA_VERSION == 27` at start of Wave 3.
- **Wave 2's `_phase_f_via_s3` extension** — adds one more group-by + table write inside the same single-pass discipline.
- **`pyarrow`** — already in the `local-recipes` pixi env.
- **CLAUDE.md Rules 1 + 2** apply (CFE skill invocation + closeout retro).
- **v8.18.1 § 10 (g), (h), (i)** apply — Wave 3 has both a many-to-many breakdown table (DELETE + INSERT) and a new write target (provenance-attribution discipline).

---

## Out of Scope (Explicit)

- **OoS-1.** Wave 4 features: `--migration-checklist` mode; recipe-edit automation; per-channel time-series; per-channel rolling window cuts. All deferred.
- **OoS-2.** Per-month time-series data — Wave 3 keeps 90d + lifetime totals only, same discipline as Wave 2.
- **OoS-3.** Non-CLI consumers (dashboards, web UIs). MCP tools count as machine consumers; UI is downstream's job.
- **OoS-4.** Channel-name normalization (parquet's raw `data_source` strings are written as-is; future normalization is Wave 4).
- **OoS-5.** Write-side automation: `pyver_breakdown --policy-check` flags candidates; it does NOT edit recipes or open PRs. The maintainer decides.

---

## References

### Parent specs (source of truth for detail)

- [`docs/specs/atlas-phase-f-s3-backend.md`](#part-1) — Wave 0-3 full design. Wave 3 = Stories 11/12/13/14.
- [`docs/specs/atlas-phase-f-wave2-richer-metrics.md`](#part-2) — Wave 2 brief (shipped v8.18.0).

### Code (entry points)

- `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py` — `SCHEMA_VERSION` (bump), `SCHEMA_DDL` (new table), `_phase_f_via_s3` (extend with channel group-by + DELETE+INSERT).
- `.claude/skills/conda-forge-expert/scripts/{platform_breakdown,pyver_breakdown,channel_split}.py` — NEW.
- `.claude/scripts/conda-forge-expert/{platform_breakdown,pyver_breakdown,channel_split}.py` — NEW wrappers.
- `.claude/tools/conda_forge_server.py` — 3 new MCP tool decorators.

### Tests

- `.claude/skills/conda-forge-expert/tests/unit/test_schema_v28_migration.py` — NEW.
- `.claude/skills/conda-forge-expert/tests/unit/test_{platform_breakdown,pyver_breakdown,channel_split}.py` — NEW.
- `.claude/skills/conda-forge-expert/tests/unit/test_phase_f_dispatch.py` — 1 new case for `package_channel_downloads` write.

### Documentation to update

- `.claude/skills/conda-forge-expert/reference/atlas-phases-overview.md` — Phase F section.
- `.claude/skills/conda-forge-expert/reference/atlas-actionable-intelligence.md` — ~11 new rows flipped to `✅ shipped (v8.19.0)`.
- `.claude/skills/conda-forge-expert/SKILL.md` Atlas Intelligence Layer — three new CLIs in the daily-use list.
- `.claude/skills/conda-forge-expert/CHANGELOG.md` — v8.19.0 entry.
- `.claude/skills/conda-forge-expert/config/skill-config.yaml` — version bump.
- `.claude/skills/conda-forge-expert/quickref/commands-cheatsheet.md` — three new CLI examples.
- `pixi.toml` — 3 new tasks.

---

<a id="p9"></a>

# Part 9 — token-bucket Phase K scheduler

> Formerly `atlas-phase-k-cron-runner.md` — shipped v8.20.0 (2026-06-13).
> Original frontmatter: `status: shipped; implemented_by: bmad-quick-dev; shipped_ref: "v8.20.0"; spec_updated: 2026-06-20`

# Tech Spec: Atlas Phase K — sustained-rate cron runner (secondary rate-limit fix)

> **BMAD intake document.** Focused execution scope for `bmad-quick-dev`
> (Quick Flow track — well-bounded, single-skill, ~5 stories).
>
> ```
> run quick-dev — implement the intent in docs/specs/atlas-phase-k-cron-runner.md
> ```
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
| Track | BMAD Quick Flow (no PRD/architecture phase — single-phase operational fix) |
| Scope | Replace Phase K's 8-worker burst with sustained-rate scheduler that respects GitHub's secondary rate limit. Preserve the current behavior as an opt-in via `PHASE_K_AGGRESSIVE=1` for tight-time-budget operators. |
| Out of scope | Phase L (extra registries) — different rate-limit profiles, not in this ship; Phase N (live GitHub) — already runs at a slow per-batch cadence; Phase H (PyPI) — no rate-limit issues. |
| Predecessor | v8.16.5 session retro carryover P2; auto-memory `project_phase_k_secondary_rate_limit.md` (2026-05-12 incident) |
| Successor | none planned |
| Created | 2026-06-13 |

---

## Background and Context

### The empirical problem

On 2026-05-12, a single `atlas-phase K` run with ~4,400 net-new VCS rows produced **15% HTTP 403s (659/4,400)** against authenticated `api.github.com/repos/<o>/<r>/releases/latest`. Primary token quota was barely consumed (32/5,000 used at the same time). The 403s are **GitHub's secondary rate limit** — concurrent-request / burst pattern — which:

- Does NOT surface in `/rate_limit` endpoint output
- Is enforced separately from the 5,000/hour primary quota
- Triggers on sustained high-concurrency or burst patterns, not on total volume
- Penalizes the *next several seconds* of requests, not just the offending one

### What Phase K does today

`_fetch_release_or_tag` in `scripts/conda_forge_atlas.py` runs an 8-worker `ThreadPoolExecutor` against the GitHub REST API. Retries 403/429 with `2**attempt + 2`-second backoff. The retries succeed for transient cases but stretch wall-clock significantly on sustained bursts; rows that don't recover land as `last_error='HTTP 403'` in `upstream_versions`.

Empirically observed (2026-05-12):
- 8 workers × ~9 req/s nominal → ~70 req/s sustained burst peak
- Total Phase K wall-clock: ~30 min for 4,400 net-new rows
- 15% (659) rows failed with `last_error='HTTP 403'` after retry exhaustion
- Primary quota usage: 32/5,000 (~0.6% of available)

The 8-worker burst is the bottleneck — not quota. The pool's aggressive concurrency exceeds GitHub's tolerance for secondary-limit detection.

### What's been ruled out

- **Raising primary quota** — irrelevant; the bottleneck is concurrency, not volume.
- **Switching to GitHub App tokens** — App tokens get the same secondary limit; this isn't a token-tier issue.
- **Increasing per-worker backoff** — current `2**attempt + 2` already retries 4 times for transient cases. The issue is sustained pressure during the next request batch.
- **Dropping to a single worker** — would solve the burst problem but stretches wall-clock to ~75 min for 4,400 rows. Acceptable trade-off but a global drop would also affect incremental TTL-skip runs (which currently are fast). Need a tunable.

### What's available to leverage

- **`_fetch_release_or_tag` already isolates the per-row fetch.** No refactor required to swap the dispatcher.
- **`PHASE_K_TTL_DAYS=7` already filters to expired-or-new rows** — incremental runs typically touch <100 rows and don't trigger the burst.
- **`upstream_versions.last_error` already records the 403 outcome** — recoverable rows can be retried on next Phase K run via TTL bypass.
- **Phase F's existing `PHASE_F_CONCURRENCY` env var pattern** — established convention for operator-tunable per-phase concurrency.

---

## Goals

- **G1.** Reduce sustained Phase K 403 rate from ~15% to <1% on full-channel fanouts.
- **G2.** Preserve incremental (TTL-skip) Phase K speed — runs with <100 new rows should finish in roughly the same time as today.
- **G3.** Operator escape hatch — `PHASE_K_AGGRESSIVE=1` opt-in restores current 8-worker behavior for operators who prefer faster wall-clock at the cost of 403 churn.
- **G4.** No new schema. No new tables. No new persisted state.
- **G5.** Honors existing `PHASE_K_TTL_DAYS=7` semantics; no behavior change to row-eligibility logic.

---

## Non-Goals

- **NG1.** No cross-process scheduling or daemon — this is a single-process per-phase fix; no `cron` daemon, no separate worker process.
- **NG2.** No retry strategy changes for Phase L / Phase H / Phase N — those phases have different rate-limit profiles and ship as-is.
- **NG3.** No GitHub-only optimization that breaks GitLab + Codeberg branches — the same scheduler must work for all three VCS hosts (though only GitHub has the secondary-rate-limit issue at scale; GitLab + Codeberg fan-outs are smaller).
- **NG4.** No dynamic rate detection from response headers — GitHub's `X-RateLimit-Remaining` reports primary quota, not secondary. We use a hard-coded sustained-rate target instead.
- **NG5.** No retry strategy for already-403'd rows from prior runs — the existing TTL bypass on `last_error != NULL` already handles this.

---

## Lifecycle Expectations

- **One-time wall-clock impact**: cold full-channel Phase K grows from ~30 min → ~60-75 min (matches the observed single-worker rate target).
- **Steady-state cost**: incremental runs (<100 new rows) finish in roughly the same time as today — they don't trigger the burst pattern anyway.
- **Per-run quota cost**: primary quota usage unchanged (Phase K never exceeds ~5% of primary quota).
- **Recovery**: any 403 that does occur lands in `upstream_versions.last_error`; next Phase K run picks it up via existing TTL bypass on `last_error != NULL`.

---

## User Stories

### Story 1 — Replace the worker pool with a sustained-rate scheduler

In `scripts/conda_forge_atlas.py` `_fetch_release_or_tag` (or the enclosing Phase K driver), replace the `ThreadPoolExecutor(max_workers=8)` with a single-token-bucket scheduler that:

- Issues at most `PHASE_K_REQUESTS_PER_SECOND` requests per second (default `3.0` — well under GitHub's secondary-limit threshold; empirically safe for sustained bursts).
- Uses a **single worker** in non-aggressive mode (or `PHASE_K_CONCURRENCY` workers if set, but capped at the rate-per-second budget).
- Honors a token-bucket pattern: tokens replenish at `RPS` rate; each request consumes one token; when tokens are depleted, the scheduler sleeps until the next token is available.
- Continues to handle GitLab + Codeberg with the same scheduler (no host-specific carve-out — the rate is well within all three providers' limits).

Implementation: a small `_RateLimitedScheduler` class in `scripts/conda_forge_atlas.py` (or a new helper file if it grows). ~50 LOC.

### Story 2 — `PHASE_K_AGGRESSIVE=1` opt-in restoring current behavior

For operators who prefer the 8-worker burst (faster wall-clock at the cost of higher 403 churn), `PHASE_K_AGGRESSIVE=1` switches back to the current `ThreadPoolExecutor(max_workers=8)` path. Document the trade-off in the env-var docs + reference doc.

The default (`PHASE_K_AGGRESSIVE` unset) is the new sustained-rate scheduler.

### Story 3 — Surface new env vars in `bootstrap_data.py` docstring

`scripts/bootstrap_data.py` already documents per-step timeouts. Extend the docstring with:

```
  PHASE_K_REQUESTS_PER_SECOND     default 3.0  (sustained-rate target;
                                                 well below GitHub's
                                                 secondary-rate-limit
                                                 threshold)
  PHASE_K_AGGRESSIVE              unset (=use sustained-rate scheduler);
                                  =1 to restore the previous 8-worker
                                  burst behavior (faster wall-clock,
                                  ~15% 403 rate on full-channel fanouts)
```

Update the `cf_atlas` timeout comment at `_DEFAULT_TIMEOUTS` to note Phase K's expected ~60-75 min wall-clock under the new default (the v8.16.6 14,400s = 4h cap still has slack).

### Story 4 — Tests

Add `tests/unit/test_phase_k_scheduler.py`:

- **TestRateLimitedScheduler**:
  - 3.0 RPS bucket: 30 requests take ≥10 s under the scheduler (within 10% tolerance).
  - Token-bucket math: bucket starts at full capacity; depletes correctly; replenishes at RPS rate.
  - `PHASE_K_REQUESTS_PER_SECOND` env-var override is honored.
- **TestPhaseKDispatch**:
  - Default mode: uses `_RateLimitedScheduler` (verifiable by mock).
  - `PHASE_K_AGGRESSIVE=1` mode: uses `ThreadPoolExecutor(max_workers=8)` (verifiable by mock).
  - Both modes write to `upstream_versions` correctly (no schema change).

### Story 5 — Docs, CHANGELOG, retro

- Update `reference/atlas-phases-overview.md` Phase K section with the new scheduler + env vars + expected ~60-75 min cold-fanout wall-clock.
- Update `reference/atlas-phase-engineering.md` § 1 (Per-host secondary rate limits) — add a concrete example referencing the v8.20.0 implementation as the canonical pattern.
- Update `quickref/commands-cheatsheet.md` if it has a Phase K example.
- `CHANGELOG.md` v8.20.0 entry per CLAUDE.md Rule 2.
- Retro at `_bmad-output/projects/local-recipes/implementation-artifacts/retro-cfe-phase-k-cron-runner-2026-06-13.md`.

---

## Functional Requirements

### FR-1: Sustained-rate default behavior

When `PHASE_K_AGGRESSIVE` is unset, Phase K issues at most `PHASE_K_REQUESTS_PER_SECOND` requests per second (default 3.0). Verified by a timing test in `test_phase_k_scheduler.py` (30 requests ≥ 10s).

### FR-2: Aggressive opt-in

When `PHASE_K_AGGRESSIVE=1`, Phase K restores the previous 8-worker `ThreadPoolExecutor` behavior. Verified by mock + timing test (30 requests complete in <5s).

### FR-3: Empirical 403 rate target

After a full-channel admin run, `SELECT COUNT(*) FROM upstream_versions WHERE last_error LIKE '%403%'` divided by total Phase K rows ≤ 1% on the new default. (Verifiable manually after a live run; not blocking the ship since live measurement requires admin profile.)

### FR-4: No row-eligibility behavior change

`PHASE_K_TTL_DAYS` semantics unchanged; the row-selection query is untouched. The scheduler only replaces the fetch dispatcher.

### FR-5: GitLab + Codeberg parity

The same scheduler dispatches to all three VCS hosts. No host-specific rate; same 3.0 RPS default applies. (GitLab + Codeberg fan-outs are much smaller and wouldn't trigger their own rate limits even at the previous 8-worker rate.)

---

## Technical Approach

### Where the code lands

- **`scripts/conda_forge_atlas.py`** — new `_RateLimitedScheduler` class; `_fetch_release_or_tag` (or the Phase K driver function) gains a branch: aggressive mode uses ThreadPoolExecutor, default uses the new scheduler.
- **`scripts/bootstrap_data.py`** — docstring update for new env vars; comment update on `cf_atlas` timeout.
- **`tests/unit/test_phase_k_scheduler.py`** — NEW; covers scheduler correctness + env-var handling + dispatch routing.
- **`reference/atlas-phases-overview.md`** — Phase K section update.
- **`reference/atlas-phase-engineering.md`** — § 1 augmented with v8.20.0 reference.
- **`CHANGELOG.md`** — v8.20.0 entry.
- **`config/skill-config.yaml`** — 8.19.1 → 8.20.0.

### Token-bucket math (canonical)

```python
class _RateLimitedScheduler:
    def __init__(self, rps: float, bucket_capacity: int = 10):
        self.rps = rps
        self.bucket = bucket_capacity
        self.bucket_capacity = bucket_capacity
        self.last_refill = time.monotonic()

    def acquire(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.bucket = min(
            self.bucket_capacity,
            self.bucket + elapsed * self.rps,
        )
        self.last_refill = now
        if self.bucket < 1.0:
            # Sleep until 1 token available
            wait = (1.0 - self.bucket) / self.rps
            time.sleep(wait)
            self.bucket = 0.0
            self.last_refill = time.monotonic()
        else:
            self.bucket -= 1.0
```

Caller invokes `scheduler.acquire()` immediately before each HTTP request.

### Env-var matrix

| Env var | Default | Purpose |
|---|---|---|
| `PHASE_K_REQUESTS_PER_SECOND` | `3.0` | Sustained-rate target; well below GitHub's secondary-limit threshold |
| `PHASE_K_AGGRESSIVE` | unset (=use sustained-rate) | Set `=1` to restore previous 8-worker burst behavior |
| `PHASE_K_TTL_DAYS` | `7` | Unchanged |
| `PHASE_K_CONCURRENCY` | unset | Unchanged; only consulted under `PHASE_K_AGGRESSIVE=1` |

### Key decisions

- **Single worker in non-aggressive mode by default.** Even with the rate limiter, multiple workers competing for the same token bucket adds complexity without benefit at 3 RPS. If a future workload demands higher throughput, set `PHASE_K_REQUESTS_PER_SECOND` higher (up to ~10 RPS appears safe based on auto-memory observations) — or use `PHASE_K_AGGRESSIVE=1`.
- **Hard-coded sustained-rate target, not dynamic.** GitHub's secondary limit isn't exposed via headers; dynamic detection requires probing the limit, which itself triggers the limit. A conservative hard-coded default is simpler.
- **No persistent cross-process state.** Single-process scheduler. If two admin runs collide (rare), they're each at 3 RPS = 6 RPS combined, still well within limits.

---

## Acceptance Criteria (Whole Feature)

- **AC-1.** Given the new scheduler with `PHASE_K_REQUESTS_PER_SECOND=3.0`, when 30 requests are issued, then the total elapsed time is ≥10 s (within 10% tolerance). Verified by `test_phase_k_scheduler.py`.
- **AC-2.** Given `PHASE_K_AGGRESSIVE=1`, when Phase K runs, then `ThreadPoolExecutor(max_workers=8)` is used (verifiable by mock).
- **AC-3.** Given the default scheduler, when Phase K runs against the live GitHub API in a full-channel sweep, then the 403 rate is <1% of total rows (manual verification; not gating the ship).
- **AC-4.** Given the v8.16.6 14,400s (`cf_atlas` step timeout), when Phase K runs ~60-75 min under the new default, then the wrapper does not time out and `bootstrap-data --profile admin` reports `✓ cf-atlas-build` with `rc=0`.
- **AC-5.** Given the test suite, when `pixi run -e local-recipes test` runs, then 1,423 → ≥1,430 passing (≥7 new tests). 0 failed, 0 errors.
- **AC-6.** Given the v8.18.1 § 10 (i) discipline, when this ship reaches step-04, then the three-reviewer adversarial pass runs and HIGH/MED findings are classified.
- **AC-7.** Given closeout per CLAUDE.md Rule 2, when v8.20.0 ships, then CHANGELOG entry + retro artifact + Phase K row note in `atlas-phases-overview.md` are all landed.

---

## Open Questions

### Pre-resolved (recommendations)

- **OQ-1.** Default RPS value? **Recommendation: `3.0`.** Empirically: the v8.5.2 8-worker burst hit ~70 req/s peak with 15% 403s; observation hints that GitHub's secondary-limit threshold for the per-IP-per-token combination sits around ~10 req/s sustained. 3.0 RPS leaves a 3× safety margin and was a known-good value in the GitHub docs for "polite" applications.
- **OQ-2.** Bucket capacity? **Recommendation: `10`.** Allows brief 10-request bursts (e.g., catching up after a brief delay) without sustained burst risk.
- **OQ-3.** Should the scheduler be host-aware (different RPS per host)? **Recommendation: no.** GitLab + Codeberg have higher tolerances and smaller fan-outs; the same 3.0 RPS applied to all three hosts is below all their limits.

### Genuinely open (surface at intake)

- **OQ-4.** Should `PHASE_K_AGGRESSIVE=1` print a stderr warning at run start? Operators opting in to the burst pattern know what they're doing, but a one-line warning helps debugging when admins see 403 spam later. **Recommendation: yes — one stderr line on Phase K entry**.
- **OQ-5.** Should the scheduler log per-request timing for the first ~30 seconds, then go silent? Useful for verifying the rate is actually being applied; noisy in steady state. **Recommendation: no — keep the implementation silent; add a `PHASE_K_DEBUG_SCHEDULER=1` opt-in for diagnostics**.
- **OQ-6.** Should we ship a backfill tool that re-runs all `last_error LIKE '%403%'` rows after the migration? The existing TTL bypass on `last_error != NULL` already handles this on the next natural Phase K run. **Recommendation: no — let the natural TTL recovery happen**.

---

## Dependencies and Constraints

- **No new top-level deps.** Token-bucket scheduler uses stdlib `time.monotonic()` only.
- **CLAUDE.md Rules 1 + 2** apply.
- **v8.18.1 § 10 (i)** — step-04 adversarial review is load-bearing for any change touching a phase's dispatcher. Verified by spec FR-6.
- **v8.19.1 § 10 (j) + (k)** — population-distribution claims (`<1% 403 rate`) carry empirical citation (2026-05-12 incident); Ask First clauses (none in this brief) — the spec is concrete enough to not need any.

---

## Out of Scope (Explicit)

- **OoS-1.** Phase L (extra registries) rate-limit work — different profiles, ships separately if needed.
- **OoS-2.** A `PHASE_K_REQUESTS_PER_SECOND` calibration tool that probes GitHub's actual current threshold — too risky (probing triggers the limit).
- **OoS-3.** Cross-process / distributed rate limiting — single-process scheduler only.
- **OoS-4.** GitHub App authentication switchover — orthogonal; would need its own spec.
- **OoS-5.** Retry-budget changes for already-403'd rows — existing TTL recovery is sufficient.

---

## References

### Code (entry points)

- `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py` — `_fetch_release_or_tag` (Phase K per-row fetch); enclosing Phase K driver function (locate by grep "Phase K" or "phase_k").
- `.claude/skills/conda-forge-expert/scripts/bootstrap_data.py` — env-var docstring + `cf_atlas` timeout comment.

### Tests

- `.claude/skills/conda-forge-expert/tests/unit/test_phase_k_scheduler.py` — NEW.

### Documentation to update

- `.claude/skills/conda-forge-expert/reference/atlas-phases-overview.md` — Phase K section.
- `.claude/skills/conda-forge-expert/reference/atlas-phase-engineering.md` — § 1 (Per-host secondary rate limits) gains v8.20.0 reference.
- `.claude/skills/conda-forge-expert/quickref/commands-cheatsheet.md` — if Phase K examples exist.
- `.claude/skills/conda-forge-expert/CHANGELOG.md` — v8.20.0 entry.
- `.claude/skills/conda-forge-expert/config/skill-config.yaml` — version bump.

### Auto-memory

- `project_phase_k_secondary_rate_limit.md` — empirical 2026-05-12 incident; cite as the source for the 15% 403 baseline and the "single-digit per-second" target.

---

> Source: `docs/specs/cyclonedx-universe-inventory.md` (canonical file — still lives there).
> Original frontmatter: `status: shipped; spec_updated: 2026-07-12; implemented_by: bmad-quick-dev (web waves A-E on claude.ai/code) + local live-gate slices (Waves B/C/D local surfaces + gates); shipped_ref: "local-recipes@main — Wave A ad0d3be3c1+4821907ab0, B dd54e47d4d+a3f4b9b0ad (PR #33), C 44ea7345b0+aacd5776d9 (PRs #34/#35), D 7b0c84cc3c+c6b6a650cd+5a1ee00a10 (PRs #36/#37), E S9 PR #38 + S-retro (CFE v8.73.0); all local gates PASS, dated Dev Notes in §§ Wave B/C/D"`

# Tech Spec: CycloneDX Universe Inventory — full PyPI + full conda-forge, purl mapping, gap/version-lag matching, and 2027–2030 library recommendations

> **BMAD intake document.** Written for `bmad-quick-dev` (Quick Flow track).
> Run BMAD with this file as the intent document:
>
> ```
> run quick-dev — implement the intent in docs/specs/cyclonedx-universe-inventory.md
> ```
>
> **Rule-1 reminder:** every atlas-touching / recipe-touching sub-task here MUST go
> through the `conda-forge-expert` skill (CLAUDE.md BMAD↔CFE Rule 1). The skill's
> Operating Principles (esp. "pair quantitative claims with a verifiable source"),
> Critical Constraints, and the atlas-phase-engineering rule book
> (`reference/atlas-phase-engineering.md`) are authoritative over any story text below.
> **Rule-2 reminder:** the effort closes with a CFE-skill retrospective (Wave E, S-retro).

---

## Status

- **ready** — authored 2026-07-05, grounded against the live `cf_atlas.db` and the
  2026-07-04 ad-hoc purl exports; hardened same day by a 3-lens adversarial review
  (17 findings applied). **Scope amendment (same day, per user):** the universe is
  **full PyPI + full conda-forge** (not the mapped/actionable slice), and — because the
  users are conda-forge **consumers** — **non-Python conda-forge packages (Go, Rust,
  npm-origin, R, C libs) are first-class** in the matcher and the 2027+ recommendation
  layer: they don't map to PyPI, but freshness/quality/recommendation apply via their
  own upstream-of-record. **Second amendment (same day, per user):** the recommendation
  window is **2027–2030**, with two first-class horizon signals — **Python 3.14
  readiness** (tiered, from wheel tags / classifiers / requires_python + conda py314
  build evidence) and an **LTS-policy flag** (curated registry + labeled heuristic;
  e.g. Python, Django). **Third amendment (same day): Wave A is
  implementation-READY** — plan-mode exploration (3 agents) + a design pass pinned
  the S1/S2 file surfaces, artifact contracts, decisions D1–D4, and live verification
  gates directly into § Wave A; a second-pass Ultraplan refinement on Claude Code web
  may further revise this spec before implementation. **Fourth amendment (same day,
  per user): schema changes are permitted when the atlas owns them** — D3 upgraded
  from a code-side guard to a **v28→v29 migration** (`v_pypi_intelligence_valid`
  view); `trendshift-conda-forge.md` Phase T renumbered v29→v30 in the same pass
  (schema numbers allocate in implementation order). **Fifth amendment (same day,
  per user): endoflife.date API v1 is the authoritative LTS/EOL source**
  (live-verified: 460 products; django 4.2 LTS → EOL 2026-04-07) — registry demoted
  to slug-map + overrides, `eol-before-window` check added; the Phase P downloads
  refresh became an operator-gated S8 option (data verified fresh 2026-07-04); and
  **cross-spec sync is an explicit implementation + retro obligation** — the
  2026-07-05 all-specs impact analysis (2 impacted / 9 none / 1 historical) is
  encoded in § Cross-spec impact & sync. **Sixth amendment (same day, per user):
  aligned with the Python Dependency Policy write-up**
  (`gist.github.com/rxm7706/6dfaa127f4b86c8d4717522ff0107e6c`) — S5 gains the
  freshness policy check (top-20th-percentile / last-eligible−1, configurable
  defaults), built-in transitive resolution for bare manifests (+ depth/fan-out →
  S7), a CI policy-gate mode with exit codes, and policy-tiered input formats
  (+`meta.yaml`/`recipe.yaml` as manifests, +`pdm.lock`); exception lists +
  `--verify-against` BOM drift explicitly deferred. **Seventh amendment
  (2026-07-05, the anticipated second-pass refinement on Claude Code web):
  spec re-verified against the live repo — zero claim drift found.** Confirmed
  live: both `_sbom.py` defects (`_purl` at `scripts/_sbom.py:48-50` emits no
  channel qualifier; license emission at `:86` is always `{"license": {"id": …}}`);
  `SCHEMA_VERSION = 28` (`conda_forge_atlas.py:138` — v29 still free); the
  trendshift v30 + kedro-migration cross-spec sync lines are in place;
  endoflife.date API v1 re-verified live (django 4.2 `isMaintained: false`,
  EOL 2026-04-07; 5.2 EOL 2028-04-30); 84 recipes currently carry
  `pending-`/`blocked-` cfe status (consistent with the 84-line ad-hoc
  exceptions baseline → 82 expected post-D1); all `recipes/*/recipe.yaml`
  parse clean (G92/G98 gate green). Two refinements: (a) **S4's
  `?channel=` qualifier risk is nil by construction** —
  `scan_project.parse_sbom_cyclonedx` classifies by purl *prefix* only and
  reads name/version from the component's own fields, so the qualifier cannot
  break ingestion; keep the pinned test as a regression formality. (b) **Path
  clarification**: every `tests/…` path in this spec is relative to
  `.claude/skills/conda-forge-expert/` (e.g.
  `.claude/skills/conda-forge-expert/tests/unit/test_export_purls.py`), not a
  repo-root `tests/` tree. See also § Execution-environment split (web pass)
  below. **Implementation state: Wave A shipped 2026-07-05** (`ad0d3be3c1` +
  adversarial patches `14dfd218d7`; live gates run same day, incl. the D2
  `uncorroborated` live-gate fix `4821907ab0`). **Wave B shipped 2026-07-05**
  (web slice `dd54e47d4d` + adversarial patches `5e39ffe293`, PR #33; local
  live gates ALL PASS 2026-07-05 — see § Wave B Dev Notes). **Wave C S5+S5a
  web slice shipped 2026-07-05** (`44ea734` + adversarial patches, PR #34
  merged `29542f3`). **Wave C S6 web slice shipped 2026-07-05**
  (`2800eb2` + adversarial/Gemini patches, PR #35, branch
  `claude/wave-c-s6-add-handoff`). **Wave C local slice + live gates
  shipped 2026-07-05 (local)** — all five S5 deferred surfaces implemented
  (transitive resolver, live channeldata cross-check, live eligible sets,
  `vulns.*` thresholds, container chain) and the S5 end-to-end smoke + S6
  live-enrichment gate PASSED (incl. a normalizer fix the S6 gate
  surfaced); see § Wave C Dev Notes. **Wave D S7 web slice shipped
  2026-07-06** (branch `claude/wave-d-s7-library-futures` — library-futures
  scorer + EolClient + lts-registry.yaml + adversarial patches). **Wave D
  S8 web slice shipped 2026-07-06** (branch
  `claude/wave-d-s8-recommend-2027` — recommend-2027 scorecard + MCP tool
  + the full calibration gate as fixture tests + the dated `kev_cap`
  calibration amendment + v8.71.0; PRs #36+#37 merged 2026-07-06). **Wave D local slice + live gates shipped 2026-07-06 (local)** — the lts-like releases heuristic implemented + live-verified, endoflife live smoke, Phase-P freshness confirmed, measured distributions recorded; see § Wave D Dev Notes.
  **Wave E S9 docs shipped 2026-07-06** (branch `claude/wave-e-s9-docs` —
  mcp-tools/+4, SKILL.md CLI table +7, overview persona rows,
  cheatsheet, regen cadence, dependency-input-formats S5a re-grounding
  with policy tiers, kedro cross-spec extension, v8.72.0). Remaining:
  **Wave D local gates** (user machine — live endoflife smoke, measured
  distributions, real Phase-P path) and the **S-retro** (Rule 2; gated on
  those gates — runs the closing all-specs sweep + the BMAD baseline
  re-stamp, both local). Resume at **Wave D local gates → S-retro**.

### Execution-environment split (web pass)

Wave A work splits cleanly between Claude Code web and a local machine — the
web container clones the repo fresh, so the gitignored
`.claude/data/conda-forge-expert/` (cf_atlas.db, `purl-export/` baseline,
grayskull cache) does **not** exist there, and `pixi` is not installed:

- **Web-executable**: all code (S1/S2 six-file surfaces), all fixture-DB unit
  tests (the `open_db()` + `init_schema()` + raw-INSERT pattern needs no live
  DB), the v28→v29 migration + its idempotency test, the three-place
  meta-tests, and spec/docs edits. Tests run via a scratch venv
  (`pip install pytest pyyaml`) invoking pytest directly.
- **Local-only**: the entire § Verification Wave A live-gate block (baseline
  copy, `export-purls` count assertions, sort checks, exceptions diff,
  `mapping-gap` dry-run → human spot-check → `--write` → idempotency re-run,
  D3 view count, re-export growth check, `pixi run -e local-recipes test`),
  and every dated Dev-Notes count. A web pass must NOT fabricate these
  numbers — they come from the local run (CFE live-verification principle).
  **Wave B local-only additions (recorded 2026-07-05, with the web slice):**
  the S4 validator run against the REAL full BOM; the measured full-universe
  size/emit-time numbers that decide single-file-vs-split (S3 Dev Notes);
  and the CLI-level `scan-project --sbom-in` invocation of the ~50-component
  round-trip (the web tests cover the same parser in-process with a
  60-component slice — the CLI surface needs the full pixi env).
  **Wave C local-only additions (recorded 2026-07-05, with the web slice):**
  transitive resolution of bare manifests (pip `--dry-run --report` /
  conda-pixi solve — web rows are flagged `resolution: direct` until then,
  and graph depth + fan-out for S7 come with the resolver); decision-4 live
  channeldata probing (web resolution chain stops at mapping → inverse-G10
  bare fold); the live PyPI eligible-set provider for the freshness check
  (yanked / requires-python filtering — the web default provider derives
  eligible sets from `upstream_versions_history` and stamps its basis into
  every report); vuln-severity policy thresholds (need the local vdb — the
  web gate REFUSES them fail-closed as an explicit violation); container
  intake `--image`/`--oci-archive` (locally: `scan-project --image …
  --sbom cyclonedx` → `inventory-match --sbom-in`); and the § Verification
  S5 end-to-end smoke (real pixi.toml env + real SBOM, hand-verified bucket
  members incl. the G10-rename / stale-atlas / unreliable-comparison /
  non-Python-GitHub-upstream cases).
  **Wave C S6 local-only additions (recorded 2026-07-05, with the S6 web
  slice):** the bounded live `pypi.org/pypi/<name>/json` enrichment of
  ADD-bucket names — the web slice injects a fake fetcher in every test and
  defers the real `_phase_r_fetch_one` worker (now mirror-routed via
  `_http.resolve_pypi_json_urls`, so air-gapped JFrog reaches its mirror) to
  the local run; and the § Verification S6 hand-check that a real ADD slice
  enriches, scores readiness-desc, and blocks non-OSI/unknown-license/gone
  projects. Idempotency (`--no-enrich` offline mode + zero-fetch re-run) is
  covered by the web fixture tests. The extracted `phase_r_upsert_one` /
  `apply_readiness_scores(names=…)` helpers are the SAME write/score paths
  Phase R/S bulk use — no parallel scorer to drift.
  **Wave D S7 local-only additions (recorded 2026-07-06, with the S7 web
  slice):** the live `endoflife.date` fetch (the default `_http`-backed
  fetcher over `resolve_endoflife_urls` with the `ENDOFLIFE_BASE_URL`
  override — every web test injects a fake; run one dated live smoke
  locally); the live-PyPI `lts-like` releases heuristic (shares S6's fetch
  budget; web slice reaches `lts-like` only via registry `heuristic-seed`
  entries); endoflife live `identifiers`/`aliases` slug-matching (web slug
  resolution = registry aliases → bare name); and the measured
  `futures_score` distribution / tier counts / wall time over the REAL
  atlas (Wave D Dev Notes, dated — never estimated). Scoring notes pinned
  with the slice: EPSS/CWE surface REPORT-ONLY per row
  (`vuln_enrichment`, from the stale rollup) and never enter the
  composite (the load-bearing vuln subscore reads
  `v_current_version_vulns`); PyPI downloads are weight-0 (non-portable);
  `py314-likely` requires a release within the 3.14 cycle (dated
  `py314_cycle_start: 2025-10-07` in the weights dict); the 18-month
  silence cap is its own dated constant (547 d), distinct from the
  24-month adoption-stage `silent` class.
  **Wave D S8 local-only additions (recorded 2026-07-06, with the S8 web
  slice):** the measured `futures_score` distribution / tier counts / wall
  time over the REAL atlas per § Verification's "recorded from actual
  runs with dates — never estimated" (the web slice ships NO measured
  numbers); the real Phase-P downloads refresh execution (the web slice
  only DETECTS >90 d staleness and prints the § 13 cost-preflight offer);
  and a real-inventory `recommend-2027` smoke (this repo's pixi env +
  one real SBOM, hand-checking a few tier verdicts against the per-signal
  breakdown). The calibration gate itself is WEB (fixture DB + fake
  endoflife fetcher — deterministic); a weights change that breaks the
  spec's ranking fails the suite (verified by perturbation during the S8
  adversarial review).

### Adjacent prefix.dev / nebari tooling (survey 2026-07-05, per user — the eighth amendment)

Live survey of nebi, recent pixi releases, prefix-dev org repos, and wolfv's
repos, asking "can any of their tooling be used here?" Verdicts:

| Tool | Verdict for this effort |
|---|---|
| **`prefix-dev/purl-associator`** (pushed 2026-06-24) | **ADOPT as an optional S2 corroboration source + a standing cross-check.** Canonical conda-forge→PURL mappings (primary + alternative purls, optional CPE 2.3 prefixes) maintained via auto-inference + edit-via-PR; published artifacts: `web/public/mappings.json` (full bundle), `mappings-index.json` (compact), sharded per-package JSONs; repo-side `mappings/{auto,manual}.json`. S2 (D2-ext): a TTL-cached fetch of the bundle may serve as a SECOND independent corroborator alongside the reverse grayskull cache — agreement from either ⇒ `verified`; cache absent → warn + continue (same discipline as the grayskull cache; keeps S2's offline-only rule). S3/S1 follow-up: cross-check our conda purls + `cfe:upstream_purl` values against its alternative-purls; its externally-maintained CPE prefixes also vindicate the 2026-06-19 decision NOT to cache `cfe-cpe` in recipes (consume, don't cache). |
| **pixi 0.71.0+ configurable conda↔PyPI mappings** (2026-06-24) | **Follow-up, not scope**: pixi now accepts custom per-channel `conda-pypi-map` files (default source: the parselmouth-hosted mapping — the same provenance tier the atlas already ingests). Emitting our `purls_conda-pypi_mapped.tsv` additionally in pixi's mapping format (an `--pixi-map` flag on `export-purls`) would let any pixi user point at the atlas-derived mapping. Deferred — record as a Wave E candidate, do not widen S1's pinned artifact contract. |
| **py-rattler / rattler** | **USE for decision 3's conda-side comparison** (upgraded from "evaluate": `py-rattler >=0.22.0` is already pinned in `pixi.toml` `[feature.local-recipes.dependencies]` (verified 2026-07-05) — as are `py-rattler-build`, `pixi-inspect`, `pixi-diff`). `rattler.Version` implements conda version ordering natively; fall back to conda's `VersionOrder` only if the import fails at runtime. No change to Wave A. |
| **nebi** (`nebari-dev/nebi`, Go/TS, alpha) | **No new intake needed — and `nebi-cli >=0.13` is already pinned in `pixi.toml` `[feature.local-recipes.dependencies]`** (verified 2026-07-05). nebi is a pixi-lockfile-based team environment manager (push/pull/diff envs via OCI registries); a nebi workspace IS a pixi workspace, so S5's `pixi.toml`/`pixi.lock` intake covers nebi-managed inventories (`nebi pull` → lockfile → `inventory-match`). S9 runbook line cites the env-resident CLI. |
| **Env-resident pixi extensions** — `pixi-to-conda-lock >=0.4.3`, `pixi-inspect >=2.0.2`, `pixi-diff >=0.1.6`, `pixi-pack`/`pixi-unpack`, `conda-lock >=4.0.1`, `conda-pypi >=0.10.1` (all pinned in `[feature.local-recipes.dependencies]`) | **S5a implementation option**: `pixi-to-conda-lock` converts `pixi.lock` → `conda-lock.yml`, so the S5a pixi.lock intake (the DW17 discharge) may EITHER parse pixi.lock natively OR shell out to the converter and reuse `scan_project`'s existing conda-lock parser — decide in S5a by which is simpler + testable offline (fixture-driven either way). `pixi-inspect` (conda-artifact metadata) and `pixi-diff` (lock-diffs) are candidate corroborators for S5's three-way version comparison at Wave C; not Wave A scope. |
| pixi releases 0.68–0.72, rattler-build, resolvo, rip, pixi-build-backends | **Nothing to adopt**: no SBOM/CycloneDX/purl-export surface found in recent pixi releases or the full prefix-dev + wolfv repo sweeps — S3's `_sbom.py` extension remains the right implementation path (no existing wheel to reuse). |
| prefix.dev attestation cluster — `siglog` (Merkle transparency log, Jul 2026), `sigstore-example` (signing conda pkgs), `vouched`; wolfv's `sigstore-rust`/`tough` (TUF)/`ceps` fork | **Watch only**: this is the ecosystem's SBOM-*signing*/provenance direction (CEP #127 territory — SBOM's home is `conda-meta/`, attestation in external Sigstore bundles). Orthogonal to this effort's inventory/matcher scope; revisit at the S-retro if a signed-BOM ask appears. |

## Intent (the user's ask, decomposed)

The users are **consumers of conda-forge**: Python libraries may come from PyPI-mapped
conda packages, and non-Python tools (Go/Rust CLIs, npm-origin tools, C libs) are
consumed from conda-forge directly. Build a **CycloneDX inventory of the FULL PyPI and
FULL conda-forge universes**, with an explicit **purl-level mapping** where one exists
(which `pkg:pypi/<name>` corresponds to which `pkg:conda/<name>?channel=conda-forge`;
non-Python conda packages instead carry their upstream-of-record identity), then use it to:

1. **Match a user inventory** (a CycloneDX SBOM or any `scan-project` input) against the
   combined universe to classify each library as:
   - **ADD** — on PyPI, not on conda-forge → candidate for packaging (feeds the CFE
     10-step recipe loop, ranked by the existing Phase S `conda_forge_readiness` score);
     non-Python dependencies absent from conda-forge surface as **ADD-NONPYPI**
     (reported with upstream identity, unscored — packaging them is trendshift-style
     manual triage, out of scope here);
   - **UPDATE** — a version-lag exists → reported as a **three-way comparison**
     (inventory-pinned version vs conda-forge latest vs upstream-of-record latest —
     PyPI for Python packages, GitHub/npm/crates/… for the rest), so "the feedstock is
     behind upstream" and "my pin is behind conda-forge" are distinct, actionable rows;
   - **CURRENT** — present and version-aligned on all three axes.
2. **Run data-quality analysis** over source-code / pypi.org / conda-forge metadata
   (already harvested into the atlas) to produce a per-library **"continue using in
   2027–2030?" recommendation** (keep / watch / plan-migration / replace) — **for every
   conda-forge package in the user's inventory regardless of ecosystem** — with
   `find-alternative` suggestions for the bottom tier. Two horizon signals are
   first-class (per user): **Python 3.14 readiness** and whether the library is
   **LTS-supported** (publishes a long-term-support policy, like Python or Django).

## Grounding: what ALREADY exists (do not rebuild)

All facts verified **2026-07-05** against the live DB / repo (per the CFE
quantitative-claims discipline — re-verify at implementation time, the atlas moves):

| Asset | Where | State |
|---|---|---|
| purl exports (ad-hoc, 2026-07-04) | `.claude/data/conda-forge-expert/purl-export/` | `purls_conda-forge.txt` 33,392 · `purls_conda-forge_versioned.txt` · `purls_pypi.txt` 843,641 (the 843,764-row live universe emits 843,641 purls — exactly 123 names collapse under G98 normalization (case/`_` collisions); verified 2026-07-05, this is dedup, NOT drift) · `purls_conda-pypi_mapped.tsv` 21,403 pairs (`conda_purl · pypi_purl · match_source · match_confidence`) · `recipe-purl-exceptions.txt` 82. **No committed generator script.** The exceptions file derives from `recipes/*/recipe.yaml` cfe metadata (NOT the DB) — see S1. |
| conda↔pypi mapping (source of truth) | `cf_atlas.db packages.pypi_name` **+ per-row provenance columns `match_source` / `match_confidence`** | 21,490 rows with `pypi_name` set (of 33,624 total / 32,655 in `v_actionable_packages`). Provenance tiers (the LITERAL `packages.match_source` enum): parselmouth / recipe_source_url / name_coincidence / **`none`** (= the 3,527 "unattributed" rows; use `'none'` in SQL — it is the real stored value); plus the grayskull cache (`pypi_conda_map.json`, `update_mapping_cache`). |
| **Non-Python upstream-of-record** | `upstream_versions` (+ `upstream_versions_history`) | **47,143 rows across sources: github 25,154 · pypi 21,217 · gitlab 381 · npm 198 · rubygems 165 · codeberg 16 · crates 10 · maven 2.** This is the freshness backbone for non-Python packages. Registry-name columns on `packages` are sparse (`npm_name` 198; `cran_name`/`cpan_name`/`luarocks_name` 0) — GitHub tracking is the dominant non-Python upstream identity. `behind-upstream` CLI already consumes this. |
| **Conda-side downloads (ecosystem-agnostic)** | `package_version_downloads` (417,850 rows, **32,636 distinct packages**) + `package_platform_downloads` + `package_channel_downloads` | Phase F; covers non-Python packages equally — adoption signal for the 2027+ scoring. |
| PyPI universe | `pypi_universe` (843,764 rows: name + last_serial + fetched_at) + `pypi_universe_serial_snapshots` | Phase D populates; serial history for activity bands. |
| PyPI per-package intelligence | `pypi_intelligence` (48 cols, 937,154 rows) | **Coverage is uneven — load-bearing for Waves C/D:** `json_fetched_at`/`conda_forge_readiness` on **43,717** rows; `license_spdx` on **22,450**; `downloads_90d` on **851,359** (Phase P/BQ ran at scale on this DB). **93,390 rows have no `pypi_universe` counterpart** (deleted/renamed projects — never version-truth; see S2). |
| Version-lag signals (Python) | `packages.pypi_current_version` / `pypi_last_serial` (Phase H, serial-gated) | conda-vs-PyPI lag already computable per package. |
| Vulnerability overlays | `package_version_vulns`, `cisa_kev`, `epss_scores`, `cwe_categories` + `vuln_*` rollups on `packages` | Phase G/G′; **32,687 packages carry rollups, of which 11,588 have NO `pypi_name`** — non-Python vuln posture is covered. Read-side offline. |
| Lifecycle / health classifiers | `adoption-stage`, `release-cadence`, `feedstock-health`, `package_health`, `find-alternative`, `whodepends` CLIs | shipped, offline; cadence/stage run off `upstream_versions_history` (multi-source, not Python-only). `gh_default_branch_status` on `packages` adds repo-liveness. |
| **Python 3.14 readiness raw signals** | `pypi_intelligence.python_tags` (43,306 rows; **1,099 already carry cp314/py314**), `classifiers` (`:: 3.14` on 6,488), `requires_python` (40,690) + conda-side `package_python_downloads.pkg_python` (35,961 rows — direct evidence a feedstock ships AND users run py3.14 builds; `pyver-breakdown` CLI reads it) | all present; S7 composes them into a tiered readiness signal. |
| **LTS detection — negative finding** | `upstream_versions_history` (499,654 rows: `snapshot_at · conda_name · source · version`) | **latest-version snapshots only — parallel maintenance branches (the LTS signature, e.g. Django 4.2.x patches landing after 6.0) are NOT detectable from the atlas.** Hence the S7 LTS design: endoflife.date (authoritative) → registry slug-map/overrides → bounded releases-fetch heuristic. |
| **LTS/EOL authoritative source (external)** | **endoflife.date API v1** (`https://endoflife.date/docs/api/v1/`) | **Live-verified 2026-07-05**: 460 products (python, django, numpy, wagtail, …); per release line: `isLts`/`ltsFrom`, `isEol`/`eolFrom`, `isMaintained`, `releaseDate`; product `aliases` + `identifiers` aid name→slug mapping. Decision-grade for the window: python 3.12→EOL 2028-10-31, 3.14→2030-10-31; django LTS 5.2→2028-04-30, **4.2→2026-04-07 (EOL before 2027)**. Free, no auth. |
| CycloneDX emitter | `.claude/skills/conda-forge-expert/scripts/_sbom.py` | `emit_cyclonedx()` — CycloneDX **1.6** JSON. **Two known defects to fix in S3 before universe-scale use:** (a) licenses always emitted as `{"license": {"id": ...}}`, schema-invalid for SPDX *expressions* (live data: `0BSD AND LGPL-2.1-or-later`) and for non-SPDX junk (`(FTL or GPLv2+) and BSD and ...`); (b) `_purl()` emits no `?channel=conda-forge` qualifier, contradicting the G98 purl convention. |
| CycloneDX ingester | `scan_project.py` (`--sbom-in`, 8+ formats) | user-inventory input side is already solved. **Verify it parses purls carrying the `?channel=` qualifier (S4).** |
| "PyPI-not-on-cf" channel-wide | `pypi-only-candidates` CLI + `v_pypi_candidates` view | the universe-level ADD list exists; this spec adds the *per-user-inventory* variant. |

**Consequence:** this effort is composition + productization, not new harvesting. No new
atlas phase is required (no new HTTP fanout); Waves B–D **read** existing tables. Three
bounded exceptions: S2 **writes** mapping recoveries back to `packages` (write-path
discipline applies — idempotent SQL + incremental commits per
`atlas-phase-engineering.md`; any recipes/ writeback follows G98 parse-gates), S2 ships
the **v28→v29 schema migration** (the D3 `v_pypi_intelligence_valid` view — schema
changes are permitted when the atlas owns them, per user 2026-07-05; cross-spec
renumbering applied to trendshift), and S5/S6 may perform a **bounded live fetch**
(PyPI JSON / channeldata) limited to the user-inventory slice.

## Not Doing

- No full npm / CRAN / CPAN / crates universe inventories (the two universes are PyPI +
  conda-forge, per the ask). **But non-Python conda-forge packages are first-class**
  in the BOM, the matcher, and the 2027+ scoring — they carry their upstream-of-record
  identity (`cfe:upstream_purl` from `upstream_versions` / registry-name columns) instead
  of a PyPI mapping, and their freshness compares against that upstream.
- No mandatory BigQuery. `downloads_30d/90d` (PyPI side) are broadly populated on THIS
  DB (851k rows) but the signal is **non-portable** — a fresh atlas rebuild without BQ
  credentials loses it — so S7 weights must not make PyPI downloads load-bearing, and
  every use is freshness-stamped from `downloads_fetched_at`. (Conda-side Phase F
  downloads are credential-free and portable.)
- No recipe generation / PR submission inside this effort — the ADD bucket *feeds* the
  existing CFE loop (`generate_recipe_from_pypi` → … → `submit_pr`), it does not run it.
- No re-derivation of the mapping from scratch — `packages.pypi_name` +
  `match_source`/`match_confidence` are the source of truth; Wave A only closes *gaps*
  and productizes the export.
- **Exception-list handling and deploy-time `--verify-against` BOM drift verification
  are DEFERRED** (user decision 2026-07-05) — the Python Dependency Policy write-up
  names both (approved exception lists; build-BOM vs deployed-graph verification with
  ticketing), but only the policy gate mode ships now. The gate's JSON output and
  exit-code contract are designed so both can be added by amendment without breaking
  consumers.

## Design decisions (pre-resolved)

1. **Identity representation in CycloneDX** — a mapped conda↔pypi pair is **ONE
   component** (the conda one), carrying namespaced properties mirroring the recipe
   `cfe-purls` convention — never two sibling components (SBOM consumers would
   double-count):
   ```json
   { "purl": "pkg:conda/dvc@3.63.0?channel=conda-forge",
     "properties": [
       {"name": "cfe:pypi_purl", "value": "pkg:pypi/dvc"},
       {"name": "cfe:match_source", "value": "parselmouth"},
       {"name": "cfe:match_confidence", "value": "verified"} ] }
   ```
   **Non-Python conda components carry `cfe:upstream_purl` instead** where the atlas
   knows the upstream (`pkg:npm/<name>`, `pkg:cargo/<name>`, `pkg:gem/<name>`,
   `pkg:github/<org>/<repo>` from `upstream_versions.source` + repo URL), plus
   `cfe:upstream_source`. Standalone `pkg:pypi/` components appear only for **unmapped**
   PyPI names. PyPI purl names use **purl-spec normalization: lowercase + `_`→`-`, dots
   PRESERVED** (G98 — PEP 503 over-normalizes dotted names).
2. **BOM scope — FULL universes by default (per user).** The default deliverable is the
   complete inventory: **all 33,624 conda-forge packages** (archived/inactive included,
   flagged via `cfe:latest_status` / `cfe:feedstock_archived` properties — a consumer
   may be running one) **+ all 843,764 PyPI projects**. Physical layout (one combined
   file vs a conda BOM + a PyPI BOM pair sharing the mapping on the conda side) is
   decided in S3 from **measured** sizes/emit times — both full either way; convenience
   flags (`--actionable-only`, `--mapped-only`, `--conda-only`, `--pypi-only`) produce
   smaller slices for tooling that can't ingest the full set. No napkin size numbers —
   record real ones in Dev Notes.
3. **Version truth + comparison authority** — conda side: atlas `packages` (Phase B),
   compared with conda's `VersionOrder`. Upstream side: Python → `pypi_intelligence.
   latest_version` read via the D3 `v_pypi_intelligence_valid` view (orphan-guarded;
   only where `json_fetched_at` set) → `packages.pypi_current_version`
   (Phase H) → bounded live `pypi.org/pypi/<name>/json` via `_http.py` (Wave C only,
   inventory slice), compared with PEP 440; **non-Python → `upstream_versions`**
   (github/gitlab/npm/rubygems/crates/maven/codeberg). Comparisons that fail either
   parser (date tags, epochs, `v`-prefixed or scheme-shifted tags — live realities)
   degrade to string-inequality **flagged `version_comparison: unreliable`** — never a
   silent guess.
4. **"Missing from conda-forge" is only declared after** the G10 five-spelling check +
   the grayskull mapping cache + (for destructive/report-final decisions) a live
   `channeldata.json` cross-check (G74 — the atlas can lag freshly-created feedstocks).
5. **2027+ recommendation = a transparent, weighted composite** (not ML), **computed for
   every conda-forge package in the inventory regardless of ecosystem**: each signal
   contributes a named, documented sub-score; weights live in one dict; the report
   always shows the per-signal breakdown so a human can audit any verdict. Missing
   signals shrink the denominator (no silent zeros) AND are listed in the output as
   `signals_absent` (for non-Python packages the `pypi_intelligence`-only signals are
   legitimately absent; the conda-side backbone — upstream freshness, Phase F downloads,
   vuln rollups, feedstock health, license quality — carries the score). Operator
   overrides via the existing `pypi_intelligence.notes` column (Python) / a small
   `futures_overrides` sidecar file (non-Python). **The horizon is the 2027–2030
   window, and it is defined, not vibes:**
   (a) **Python 3.14 readiness (key factor, per user)** — tiered per Python package:
   `py314-ready` (cp314/py314 wheel tags, or `:: 3.14` classifier, or conda py3.14
   builds shipping per `package_python_downloads`), `py314-likely` (pure-Python +
   `requires_python` does not exclude 3.14 + released within the 3.14 cycle),
   `py314-not-ready` (caps `<3.14`, or compiled with no cp314 wheels/builds),
   `unknown`. By 2030, 3.14 is a mid-life floor — `py314-not-ready` caps the tier at
   `watch` and is flagged in every report row;
   (b) **LTS + EOL flags (key factor, per user)** — source hierarchy: (1)
   **endoflife.date API v1** — authoritative LTS lines + per-line EOL dates
   (live-verified 2026-07-05: 460 products), matched by product
   `identifiers`/`aliases` then the registry slug-map; (2) the curated registry —
   now a thin name→slug map + entries only for LTS-policy projects endoflife.date
   lacks; (3) `lts-like` heuristic last (patch releases observed on an older line
   after a newer line exists — labeled heuristic, never presented as policy).
   Flags: `lts-supported` (pin on an active LTS line), `lts-available` (LTS lines
   exist; the recommendation includes "move to the LTS line"), `lts-like`,
   `none/unknown`. **EOL-line check:** the pinned line's `eolFrom` vs the window —
   line EOL **< 2027** → `eol-before-window` (upgrade lines or replace; live
   example: django 4.2 LTS → EOL 2026-04-07); product fully EOL/unmaintained →
   floor `plan-migration`. LTS standing with in-window EOL dates is a positive
   keep-tier signal: dated, predictable support through the window;
   (c) all ecosystems: silence window — no release AND no upstream movement
   > 18 months caps the tier at `watch`;
   (d) archived feedstock or yanked/broken latest → floor at `plan-migration`.
   Thresholds are dated constants in the weights dict, revisited at each retro.
6. **Freshness contract** — every emitted BOM/report stamps the atlas `built_at` (from
   `cf_atlas_meta.json`) and per-signal `*_fetched_at` ages as metadata properties
   (`cfe:atlas_built_at`, …). Reports refuse to run (override: `--allow-stale`) when the
   atlas is older than 14 days — this repo's G74/G78 lessons are precisely "cached
   records decay."

## Waves & stories

### Wave A — Productize the purl + mapping export (close the ad-hoc gap)

Wave A is **implementation-ready** (plan-mode exploration + design pass, 2026-07-05):
file surfaces, artifact contracts, and the write-path SQL are pinned below. Model
files: `scripts/pypi_only_candidates.py` (canonical CLI shape),
`tests/unit/test_pypi_only_candidates.py` (fixture-DB pattern via
`conda_forge_atlas.open_db()` + `init_schema()` + raw INSERTs, in-process helper
calls), the 19-line wrapper template in `.claude/scripts/conda-forge-expert/`.

- **S1 — `export-purls` CLI** (read-only exporter; two declared inputs: `cf_atlas.db`
  + the `recipes/` tree).
  **File surface (6, per the three-place rule + tests + MCP):** canonical
  `.claude/skills/conda-forge-expert/scripts/export_purls.py` (stdlib + `yaml`,
  conn-taking pure helpers, `main() -> int`); wrapper
  `.claude/scripts/conda-forge-expert/export_purls.py`; `pixi.toml` task
  `export-purls`; `"export_purls.py"` in `tests/meta/test_all_scripts_runnable.py`
  SCRIPTS; MCP tool `export_purls` in `conda_forge_server.py` (`ATLAS_EXPORT_PURLS`
  const, always-`--json` wrap via `_run_script`); unit tests
  `tests/unit/test_export_purls.py`. Flags: `--out-dir` (default the data-dir
  `purl-export/`), `--json` (per-artifact `{lines, previous_lines}` +
  `recipes_scanned`/`recipes_parse_errors`/`unparseable_upstream`).

  **Artifact contract (the regression surface — live-verified 2026-07-05):**

  | # | File | Population | Line format | Order |
  |---|---|---|---|---|
  | 1 | `purls_conda-forge.txt` | `packages WHERE latest_status='active'` (33,392) — deliberately broader than `v_actionable_packages` (archived-but-active INCLUDED: a consumer may run one); selector carries a `# scope:` comment for the meta-test | `pkg:conda/{name}?channel=conda-forge` | **by `conda_name`, C-locale — NEVER full-line sort** (`-` 0x2D < `?` 0x3F flips name-prefix pairs) |
  | 2 | `purls_conda-forge_versioned.txt` | same rows, same order | `…@{latest_conda_version}?channel=conda-forge`; NULL version → unversioned line (count parity with #1 asserted) | same |
  | 3 | `purls_pypi.txt` | all `pypi_universe` | `pkg:pypi/{name}` — G98: lowercase + `_`→`-`, **dots preserved** | full-line C-sort |
  | 4 | `purls_conda-pypi_mapped.tsv` | #1 rows AND `pypi_name <> ''` (21,403) — **includes** the 3,527 `match_source='none'`/`match_confidence='n/a'` rows (straight provenance passthrough from `packages.match_source`/`match_confidence`, no filtering) | header `conda_purl\tpypi_purl\tmatch_source\tmatch_confidence` verbatim | by `conda_name` |
  | 5 | `recipe-purl-exceptions.txt` | `recipes/*/recipe.yaml` whose `extra.cfe-on-conda-forge-status` starts `pending-`/`blocked-` (`yaml.safe_load`; parse failure → warn + skip + count) | `{dir}: conda:{name} not-on-cf (status={s})` when the conda name is absent from #1; else, for pypi-registry recipes, `{dir}: pypi:{name} not-in-pypi-export` when absent from #3 | by recipe dir |
  | 6 | `purls_conda-upstream_mapped.tsv` (NEW) | active, PyPI-unmapped, having a non-pypi `upstream_versions` row (one row per conda_name × source) | header `conda_purl\tupstream_purl\tupstream_source`; purl by source: github→`pkg:github/{owner}/{repo}`, npm→`pkg:npm/{n}`, crates→`pkg:cargo/{n}`, rubygems→`pkg:gem/{n}`, maven→`pkg:maven/{g}/{a}`, gitlab/codeberg→`pkg:generic/{repo}?vcs_url=git+{url}`; unparseable URL → skip + count | by (conda_name, source) |

  **Decision D1 — the exceptions dots-bug is FIXED, not reproduced.** The 2026-07-04
  ad-hoc run PEP-503-folded the recipe-side pypi name but not the export side,
  manufacturing 2 false `not-in-pypi-export` lines (`fs.googledrivefs`,
  `pymilvus.model` — both ARE in #3 under their dotted names). Rule: fold **both**
  sides for membership lookup ONLY (`re.sub(r"[-_.]+","-",n.lower())` — how PyPI
  itself resolves names); always emit G98-style. Expected baseline divergence:
  84 → 82 lines. The exporter reports `previous_lines` vs `lines` per artifact on
  overwrite instead of hardcoding baselines. Pinned tests: sort-by-name regression
  (`foo` before `foo-bar`, and `lines != sorted(lines)`), G98 dots-preserved, the D1
  bug pin (dotted name present in universe → zero `pypi:` lines; genuinely absent →
  line emitted, keeping the branch alive), determinism (double-run byte-identical),
  TSV headers + `none`-row passthrough, missing-DB → rc 1.

- **S2 — `mapping-gap` CLI** (the effort's ONE DB write path; **dry-run by default**).
  **File surface (6):** canonical `scripts/mapping_gap.py`, wrapper, `pixi.toml` task
  `mapping-gap`, SCRIPTS entry, unit tests `tests/unit/test_mapping_gap.py`, and
  `conda_forge_atlas.py` (the D3 v28→v29 migration + schema-version test). **No MCP
  tool** (S9's +4 list is unchanged). Flags: `--write` (default = dry-run: full
  classification + report, zero UPDATEs), `--json`, `--limit N`, `--report PATH`.

  **Classification** (working set = `v_actionable_packages WHERE pypi_name IS NULL OR
  pypi_name = ''`, ~11k): Python-track iff a `python` run-dep exists in
  `dependencies` (`target_conda_name='python' AND requirement_type='run'`) OR
  `upstream_versions` has a `source='pypi'` row; else non-Python, subdivided by
  whether ANY upstream identity exists (none → the "freshness unknowable until Phase
  L/K covers them" bucket — reported, not fixed here).

  **Recovery — offline only (no live probing; decision-4 live checks gate "missing
  from conda-forge" declarations, which S2 never makes):** inverse-G10 candidates
  from the conda name — folding subsumes the `-`/`_` swap, so ≤4 distinct: bare,
  strip `-py`, strip `-python`, strip `python-` — validated against a fold-keyed
  index of `pypi_universe` plus a one-time REVERSE index of the grayskull cache
  (`pypi_conda_map.json` is `{pypi_lower: conda_name}`-keyed). The written value is
  the universe's **stored spelling** (folding is lookup-only, G98-safe). Grayskull
  cache absent → warn + continue in `likely`-only mode (refreshing it remains
  `update_mapping_cache`'s job).

  **Decision D2 — two confidence tiers under `match_source='g10_spelling'`:**
  `verified` only when the reverse grayskull cache independently agrees; `likely` on
  universe membership alone (mirrors `name_coincidence` semantics). **Ambiguous**
  (2+ distinct candidates hit, no grayskull tiebreak) → NO write; `ambiguous` triage
  bucket with the candidate list. **Collision** (candidate pypi name already set on
  a different conda package) → skip; `collisions` bucket — the
  `wasmtime`-vs-`wasmtime-py` trap; never a "bare name wins" heuristic.
  (**D2-ext, eighth amendment:** the `prefix-dev/purl-associator` mapping
  bundle may serve as a second independent corroborator — agreement from
  EITHER the reverse grayskull cache OR purl-associator ⇒ `verified`; both
  caches absent → `likely`-only mode. Optional; see § Adjacent prefix.dev
  tooling.)
  **D2 refinement (live-gate finding, 2026-07-05):** the writeback is further
  restricted to **`bare`-transform pairs (PEP 503 name equivalence — the same
  registry entry) OR corroborated (`verified`) pairs**; a suffix/prefix
  recovery backed only by universe membership queues in a new
  `uncorroborated` triage bucket instead of writing. Proven necessary by the
  first live dry-run: `tvm-py` (Apache TVM) resolved via strip-py to PyPI
  `tvm` — the "Time Value of Money" package, an unrelated project the
  collision guard cannot catch (no conda package claims PyPI `tvm`).
  Regression-pinned in `test_uncorroborated_suffix_not_written`.

  **Writeback (pinned SQL — idempotent, no-clobber, `commit_every=500` per the
  Phase C pattern):**
  ```sql
  UPDATE packages
     SET pypi_name = ?, match_source = 'g10_spelling', match_confidence = ?
   WHERE conda_name = ?
     AND (pypi_name IS NULL OR pypi_name = '')
     AND match_source NOT IN ('parselmouth', 'recipe_source_url')
  ```
  A second `--write` run reporting 0 rows written IS the idempotency proof.

  **Decision D3 (REVISED 2026-07-05 — schema changes are permitted when the atlas
  owns them, per user): orphan rule as a SCHEMA-LEVEL view.** S2 ships an idempotent
  **v28→v29 migration** in `conda_forge_atlas.py` (`SCHEMA_VERSION` bump +
  `init_schema` self-healing, modeled on the v21 `v_actionable_packages` precedent)
  adding:
  ```sql
  CREATE VIEW IF NOT EXISTS v_pypi_intelligence_valid AS
    SELECT pi.* FROM pypi_intelligence pi
    JOIN pypi_universe pu ON pu.pypi_name = pi.pypi_name;
  ```
  Wave C/D consumers read the VIEW, never the raw table for version truth — enforced
  the `test_actionable_scope.py` way (any `FROM pypi_intelligence` outside the view
  needs a `# scope:` justification comment; meta-test added in the same story). The
  `ORPHAN_RULE` docstring, the `orphan_intelligence_stats()` report section (93,390
  orphans at 2026-07-05), and the unit test (seeded orphan excluded by the view;
  migration idempotent on a v28 fixture DB) all stay. `conda_forge_atlas.py` (the
  migration) + the schema-version test update are part of S2's 6-file surface.
  **Cross-spec consequence (applied 2026-07-05):** v29 is CLAIMED by this effort;
  `docs/specs/trendshift-conda-forge.md` Phase T renumbered v29→**v30**. Schema
  numbers are allocated in implementation order — whichever effort lands first takes
  the next free version, and the other spec renumbers again if needed.

  **Report** — `mapping-gap-report.md` is **runtime output into the gitignored data
  dir** (`.claude/data/conda-forge-expert/`), NOT a repo doc. Sections: (1) header
  (generated_at, atlas `built_at`, DRY-RUN/WRITE mode, grayskull-cache presence +
  mtime); (2) summary (actionable · mapped before/after · recovered · remaining);
  (3) per-class counts incl. non-Python-no-identity and recovered by confidence ×
  transform; (4) ambiguous + collision listings (the human-triage queue); (5) orphan
  section (rule verbatim + count + sample); (6) recovered-pairs appendix.

  **Decision D4 — sequencing:** S1 → S2 dry-run → human review of the report
  (spot-check ≥5 recovered pairs against pypi.org/the feedstock) → S2 `--write` →
  idempotency re-run (0 rows) → **re-run S1**: the mapped TSV must grow by exactly
  `rows_written` (the wave's success metric).

### Wave B — CycloneDX universe inventory

- **S3 — `universe-sbom` CLI.** Extends `_sbom.py` (shared code, no fork) with two
  **prerequisite fixes** (both defects verified live, see Grounding):
  (i) license normalization — single SPDX id → `{"license":{"id":...}}`, SPDX expression
  → `{"license":{"expression":...}}` (validated against the SPDX expression grammar),
  anything else → `{"license":{"name":...}}` fallback; (ii) purl qualifiers — `_purl()`
  gains channel-qualifier support so conda purls emit `?channel=conda-forge` (G98).
  Then emits the **full-universe inventory** per design decisions 1–2: all conda
  components (version, normalized license, `cfe:pypi_purl`/`cfe:match_*` for mapped
  Python, `cfe:upstream_purl`/`cfe:upstream_source` for non-Python,
  `cfe:latest_status`/`cfe:feedstock_archived` flags) + all PyPI projects (standalone
  components for unmapped names; name + last_serial always, version/license where
  `pypi_intelligence` is enriched); `cfe:atlas_built_at` stamped in BOM metadata
  (decision 6). Flags: `--actionable-only`, `--mapped-only`, `--conda-only`,
  `--pypi-only`, `--with-vulns` (joins `v_current_version_vulns`; off by default at
  universe scale), `--format cyclonedx|spdx`, `--out`. Offline-safe. Record measured
  output size + wall time for the full inventory and each slice in Dev Notes (verified
  numbers, dated); the single-file-vs-split layout decision is made HERE from those
  numbers. MCP: expose as `universe_sbom`.
- **S4 — BOM validity gate.** Validate emitted BOMs against the CycloneDX 1.6 schema
  (`cyclonedx-python-lib` if already in the env, else JSON-schema check) as a unit test
  with a small fixture DB **whose fixtures include an SPDX-expression license, a
  non-SPDX junk license, and a non-Python package with a `cfe:upstream_purl`** (the live
  variance). Meta-test asserts purl forms follow G98 normalization. Round-trip gate is
  **slice-based**: a bounded (~50-component) BOM slice through `scan-project --sbom-in`,
  plus an explicit test that `scan_project`'s purl parser accepts the
  `?channel=conda-forge` qualifier. Success: schema-valid on live data, not just
  fixtures (run the validator once against the real full BOM and record the result).

#### Wave B Dev Notes — local live-gate run (2026-07-05; measured, not estimated)

Environment: pixi 0.72.0 (user-level — the env-resident 0.70.2 no longer
satisfies the manifest's `requires-pixi >=0.71`), atlas `built_at`
2026-07-05 17:49 UTC (fresh; no `--allow-stale`), 16-core / 60 GiB host.

**S3 measured emits** (each run via `pixi run -e local-recipes universe-sbom`;
`bytes`/`wall_seconds` from the CLI's own `--json` summary, RSS from
`/usr/bin/time`):

| Run | Components (conda + pypi) | Bytes | Emit wall | Peak RSS |
|---|---|---|---|---|
| full CycloneDX (default) | 856,766 (33,624 + 823,142) | 160,904,709 (~153 MiB) | 10.2 s | ~0.69 GiB |
| `--actionable-only` | 855,797 (32,655 + 823,142) | 160,529,118 | 10.2 s | ~0.69 GiB |
| `--mapped-only` | 21,615 (conda only) | 9,503,402 (~9.1 MiB) | 0.6 s | ~87 MiB |
| `--conda-only` | 33,624 | 13,808,379 (~13.2 MiB) | 1.0 s | ~103 MiB |
| `--pypi-only` | 823,142 | 147,096,931 (~140 MiB) | 9.5 s | ~624 MiB |
| full SPDX (`--format spdx`) | 856,766 | 304,148,686 (~290 MiB) | 15.0 s | ~1.24 GiB |

PyPI-side reconciliation: 843,641 G98-distinct universe purls − 823,142
standalone components = 20,499 names folded into mapped conda components
(the D1 fold-suppression path; 21,615 mapped conda components > 20,499
because multiple conda packages can share one pypi_name and some mapped
names have no universe row).

**Layout decision (D2, made HERE from the numbers): SINGLE combined file.**
~153 MiB / ~10 s emit is tractable to store, transfer, and stream-parse;
consumers that can't ingest the full set already have the split pair on
demand (`--conda-only` + `--pypi-only`) plus the smaller slices. No code
change; revisit only if the universe outgrows ~1 GiB.

**S4 real-data gates (all PASS, 2026-07-05):**

- **CycloneDX 1.6 schema validation of the REAL full BOM: VALID** — all
  856,766 components, using the test suite's exact schemas + Draft7
  validator (jsonschema 4.26.0, vendored bom-1.6/spdx/jsf), 17.3 s wall
  across 14 worker chunks + a 4.3 s exact `uniqueItems` check (0 duplicate
  components, canonical-JSON identity). **Method note (retro candidate):**
  the naive single-pass `Draft7Validator.validate(doc)` the unit tests use
  is INTRACTABLE on the real BOM — jsonschema implements the components
  array's `uniqueItems: true` as an O(n²) pairwise dict scan (~3.7×10¹¹
  comparisons at 856k; a run was killed after 75 min of a projected
  multi-day walk). The gate run strips `uniqueItems` from the schema copy,
  checks that predicate exactly in O(n) via canonical-JSON hashing, and
  chunk-parallelizes the remaining walk — semantically identical verdicts.
  Fixture-scale tests can never surface this class; the live gate did.
- **CLI-level round-trip**: a 50-component slice of the real mapped BOM
  (purls carrying `?channel=conda-forge`) through
  `pixi run -e vuln-db scan-project -- --sbom-in`: 50/50 deps loaded,
  50/50 atlas-matched, clean vuln report, 0.69 s.
- **Full suite in the real env**: `pixi run -e local-recipes test` —
  1914 passed / 2 skipped (known `--help` skips) / 1 xpassed, 89 s.

### Wave C — Inventory gap / version-lag matcher

- **S5 — `inventory-match` CLI.** **Input contract (pinned per user 2026-07-05;
  policy-TIERED 2026-07-05 per the Python Dependency Policy write-up —
  `gist.github.com/rxm7706/6dfaa127f4b86c8d4717522ff0107e6c`):**
  - **policy-supported** (the write-up's CI formats): pyproject.toml (PEP 621;
    517/518/639/735), requirements.txt (+ frozen), environment.yaml, conda-lock.yml,
    pixi.toml, pixi.lock (S5a — **discharges the DW17 follow-up** filed in
    `cfe-shipped-releases.md`), and **`meta.yaml` (v0) + `recipe.yaml` (v1) as
    dependency manifests** (S5a, NEW per the policy: parse `requirements.host/run`
    from recipes, reusing the repo's existing recipe parsers);
  - **tool-supported beyond policy** (the tool runs ahead of the policy):
    CycloneDX/SPDX SBOM (`--sbom-in`), live conda env (`--conda-env`), venv
    (`--venv`), container image (`--image`/`--oci-archive`), plus S5a text intake:
    `pip list`/`pip freeze` output and `conda list` output (incl. `--export`);
  - **future-tier** (S5a builds the parsers; rows flagged `policy: future`):
    `pylock.toml` (PEP 751), `poetry.lock`, `uv.lock`, **`pdm.lock`**.
  **S5a extends `scan_project`'s intake parsers** (shared with the plain
  `scan-project` surface — not an inventory-match-only fork); all formats feed the
  same `Dep` dataclass; each gets a fixture-driven unit test and a row (with policy
  tier) in `reference/dependency-input-formats.md` (Wave E docs).
  **Transitive resolution (per policy § 3, decision 2026-07-05):** bare manifests
  (direct-pinned, no lock) are RESOLVED to the full graph before matching — PyPI
  manifests via pip's resolver (resolvelib / `pip install --dry-run --report`),
  conda/pixi manifests via a conda/pixi solve; lockfiles, SBOMs, and live envs are
  used as-given (already complete). Resolver-derived rows are flagged
  `resolution: resolved` (vs `locked`); per-package graph **depth + fan-out** are
  computed from the resolved graph (feeds S7). *(Vocabulary note, 2026-07-05: the
  web slice flags unresolved bare-manifest rows `resolution: direct`; the local
  wave's resolver upgrades those rows to `resolved` — `locked` unchanged. Three
  values total.)*
  **Freshness policy check (defaults from the Dependency Policy, dated + configurable
  in the weights dict):** per dep, compute the ELIGIBLE version set
  (runtime-Python-compatible, non-yanked); dense history (≥ N eligible versions,
  default N=10) → the pinned version must sit in the **top 20th percentile** of
  eligible versions; sparse history → **last-eligible −1** or newer suffices.
  Output pass/warn/fail + the percentile on every row.
  **Policy gate mode (CI):** `--policy <file>` (thresholds: freshness,
  metadata-completeness, vuln severity, license) + deterministic **exit codes**
  (0 = pass, 2 = policy violations, 1 = error) so CI can block; when enabled,
  incomplete/ambiguous metadata blocks per the policy. (Exception lists and
  deploy-time `--verify-against` BOM drift are deliberately deferred — see Not
  Doing.) Plus an **optional criticality/weight sidecar** (`--weights <csv|json>`:
  per-package multiplicity or criticality the user's estate assigns — conda-forge
  blast radius is not the user's blast radius). For **every** dep (any ecosystem): resolve to conda name (mapping →
  G10 → live channeldata per decision 4), then bucket on the **three-way version
  comparison** (decision 3: inventory-pinned vs cf-latest vs upstream-of-record):
  **ADD** (Python, not on cf; attach `conda_forge_readiness`, `recommended_template`,
  `staged_recipes_pr_url` if a PR exists, and local `recipes/<name>/` presence),
  **ADD-NONPYPI** (non-Python, not on cf; upstream identity reported, unscored),
  **UPDATE-FEEDSTOCK** (cf behind upstream — report both versions + lag in
  releases/days where `upstream_versions_history` allows), **UPDATE-PIN** (inventory
  behind cf), **CURRENT**, **UNKNOWN** (not decidable — no cf version, name absent
  from every source, or a conda identifier not on conda-forge). *(Amended 2026-07-05
  with the web slice, per the Risks section's "UNKNOWN-leaning" soft reading: a
  MATCHED package with no `upstream_versions` row still buckets on the inv-vs-cf
  comparison where decidable and carries `signals_absent: upstream_freshness` —
  demoting a decidable row to UNKNOWN would hide a real UPDATE-PIN.)*
  Every row carries `match_confidence` (never present `unattributed`/`name_coincidence`
  mappings as verified) and the `version_comparison` reliability flag. Output: markdown
  report + `--json` + `--sbom-out` (input BOM annotated with `cfe:gap_status` /
  `cfe:conda_purl` properties). MCP: `inventory_match`.
#### Wave C Dev Notes — local slice + live gates (2026-07-05; measured, not estimated)

The web slice deliberately deferred five surfaces to local (see § Execution-
environment split); all five shipped in the local slice, each with an
`--offline` opt-out that reproduces the web behavior exactly, plus offline
unit tests (injected fetchers / monkeypatched resolvers; suite total after
the local slice: **2,039 passed / 2 known skips / 1 xpassed, 103 s**):

1. **Transitive resolver (policy § 3)** — pip `install --dry-run --report`
   (PyPI track) + py-rattler 0.22 conda-forge solve (conda track); direct
   rows upgrade to `resolution: resolved` with depth + fan-out (S7 feed),
   resolver-discovered packages join as `via: transitive` rows; failure
   warns and leaves rows `direct`.
2. **Decision-4 live channeldata cross-check** — every would-be-missing row
   (ADD / ADD-NONPYPI / conda-UNKNOWN) probes the TTL-cached (24 h) live
   `channeldata.json`; a hit re-buckets as `atlas_stale`, a miss stamps
   `live_cf_check: absent-confirmed`.
3. **Live PyPI eligible-set provider** — pypi.org JSON per pypi-mapped
   matched package (memoized, inventory-bounded), yanked + requires-python
   filtered; history-provider fallback per name.
4. **`vulns.*` policy thresholds** — `max_critical` / `max_high` / `max_kev`
   row ceilings read from the atlas's Phase G rollups
   (`vuln_*_affecting_current` — current-cf-version posture, stamped);
   matched rows without rollups get `signals_absent: vuln_rollups` and count
   against thresholds under `block_on_missing_data` (default true).
5. **Container intake** — via scan-project as designed (no new matcher code).

New flags: `--offline`, `--no-resolve`, `--no-live-cf`, `--python-version`.

**S5 end-to-end smoke (all PASS, run 2026-07-05 on the fresh same-day atlas):**

- **Repo `pixi.toml` (bare manifest, full live path)**: 46 direct conda deps
  → rattler solve → **1,150 rows, 100% `resolution: resolved`** in 122 s
  wall (solve + live channeldata + live PyPI freshness). Buckets: 982
  CURRENT · 122 UPDATE-FEEDSTOCK · 45 UPDATE-PIN · 1 ADD · 0 UNKNOWN; max
  graph depth 6 (`at-spi2-core`, fan-out 6); vuln rollups attached (e.g.
  `dulwich` 3 High, `intake` 1 High).
- **Hand-verified bucket members** (per § Verification):
  *G10 rename*: `tzdata`→`python-tzdata` (parselmouth/verified),
  `certifi`→`ca-certificates` (recipe_source_url/verified).
  *Atlas-stale / channeldata-fresh (real G74 event)*: `refleak` + `doclang`
  (staged-recipes merged 2026-07-04, ABSENT from the 2026-07-05 atlas) were
  **recovered live** — `match_via: channeldata_live`, `atlas_stale: true`,
  CURRENT at cf 0.1.1 / 0.7.2 — where `--offline` misreports both as ADD.
  *`version_comparison: unreliable`*: the `azure-*-cpp` family (upstream
  github tags in the `azure-template_1.1.0-beta.*` scheme vs cf `1.16.3`).
  *Non-Python conda + GitHub upstream*: the `aws-c-*` C family across all
  three matched buckets (aws-c-auth UPDATE-FEEDSTOCK 0.10.3→0.27.2;
  aws-c-common UPDATE-PIN 0.14.0→0.14.1; aws-c-compression CURRENT).
  *ADD*: `kedro-mcp` — live **absent-confirmed** (decision-4 gate exercised).
- **Real SBOM round-trip**: the Wave B 50-component mapped-BOM slice →
  39 CURRENT + 11 UPDATE-FEEDSTOCK, all rows `locked`; `--sbom-out` wrote
  `cfe:gap_status` + `cfe:conda_purl` per component.
- **Policy gate**: `{"vulns": {"max_high": 0}}` on a dulwich inventory →
  **exit 2** with `vulns.max_high` naming dulwich (3 High affecting current).
- **Container chain (daemonless)**: docker-daemon socket is root-gated on
  the gate host, so: `pixi exec skopeo` (needs a v2 `--registries-conf`
  override — conda-forge's skopeo ships a rejected v1 file) → OCI archive
  of `python:3.12-slim` (43 MB) → `scan-project --oci-archive` with a
  pixi-exec'd `syft` on PATH (2,747 deps, 6.0 s; syft/trivy are not in this
  host's vuln-db env) → `inventory-match --sbom-in`: 5.7 s, `pip` 25.0.1
  correctly UPDATE-PIN vs cf 26.1.2, 2,724 deb packages → ADD-NONPYPI with
  **all 2,724 live-confirmed absent** (the probe scales: one channeldata
  fetch, in-memory fold checks).
- **S6 gate — live ADD-slice enrichment (PASS)**: a 4-name real ADD slice
  (kedro-mcp, ragstack-ai-knowledge-store, flyte-controller-base,
  langflow-sdk) through `add-handoff`: eligible 2 → fetched 2 (live
  pypi.org JSON via the mirror-routed `_phase_r_fetch_one`, idempotently
  upserted through `phase_r_upsert_one`), worklist sorted readiness-desc
  (65 · 60 · 50 · 50), fail-closed license rule held (NULL never passed).
  **Gate finding, fixed in this slice:** `_normalize_license_to_spdx`
  dropped literal SPDX ids absent from its OSI-common map — live case:
  ragstack's `info.license = 'BUSL-1.1'` stored as NULL, degrading the
  blocker to `license-unknown`. Fixed with a case-corrected pass-through
  via the Wave B vendored SPDX enum (+3 regression tests); the re-run
  blocks it as **`license-non-osi (BUSL-1.1)`**. kedro-mcp correctly stays
  `license-unknown` (its PyPI metadata is the full Apache license TEXT with
  no expression/classifier — the G90 metadata class; human triage).

- **S6 — ADD-bucket handoff artifact (with on-demand enrichment).** Readiness/license
  coverage is sparse (43,717 / 22,450 rows — see Grounding), so for ADD-bucket names
  lacking `json_fetched_at`, run a **bounded Phase-R-style single-package enrichment**
  (one `pypi.org/pypi/<name>/json` fetch each, capped at the inventory slice, written
  back to `pypi_intelligence` idempotently) BEFORE scoring — a NULL `license_spdx` must
  never silently pass the OSI-eligibility blocker check. Then emit the ready-to-consume
  packaging worklist (name, readiness score, template, blockers e.g. non-OSI license)
  sorted readiness-desc, with `signals_absent` listed per row; ADD-NONPYPI entries
  appended unscored with their upstream identity. No recipes generated in this story.

### Wave D — Data-quality analysis + 2027+ recommendation

- **S7 — `library-futures` scoring.** New module computing, per matched conda-forge
  package **in any ecosystem**, a composite from **existing** signals (offline;
  Python-side enrichment gaps already closed by S6 for the inventory slice).
  **Ecosystem-agnostic backbone** (available for ~all cf packages): upstream freshness
  (`upstream_versions` + `behind-upstream` lag, `gh_default_branch_status`),
  release-cadence class, adoption-stage class, conda-side downloads (Phase F: version /
  platform / channel), vuln posture (Critical/High counts, KEV, max EPSS, CWE
  categories — verified present for 11,588 non-PyPI packages), feedstock health +
  archived flag, license quality (`conda_license` present? SPDX-parseable? OSI?),
  cf-graph blast radius (`whodepends --reverse`), the user-estate weight from the
  S5 sidecar, plus two S5-computed signals (per the Dependency Policy write-up):
  the **freshness percentile / policy verdict** and the resolved-graph
  **depth + fan-out** of each package within the user's own inventory. **Python-only enrichment layer** (adds precision where present):
  activity_band + serial deltas, PyPI downloads, bus_factor_proxy, packaging health
  (has_wheel/has_sdist/packaging_shape/yanked), metadata completeness
  (repo_url/docs_url/classifiers/requires_python currency), cross-channel `in_*`
  redundancy, `dependency_blast_radius`. **Horizon signals (decision 5, both key
  factors per user):**
  - **Python 3.14 readiness** — composed offline from `python_tags` + `classifiers` +
    `requires_python` (PyPI side) corroborated by `package_python_downloads.pkg_python`
    (conda side); tiering per decision 5(a). N/A → `signals_absent` for non-Python.
  - **LTS + EOL flags** — primary source: **endoflife.date API v1** (see Grounding;
    460 products), fetched via `_http.py` with an `ENDOFLIFE_BASE_URL` env override
    (the `<HOST>_BASE_URL` enterprise-routing convention) into a TTL'd
    `eol_cache.json` in the data dir (default TTL 7 d; offline → stale cache + age
    warning in the report, never a hard fail). Slug resolution: product
    `identifiers`/`aliases` first, then the git-tracked registry
    `.claude/skills/conda-forge-expert/data/lts-registry.yaml` — now a thin
    name→slug map + manual entries ONLY for LTS-policy projects endoflife.date
    doesn't cover (schema + seed entries unit-tested; every entry dated). Heuristic
    corroboration unchanged: a bounded per-package PyPI **releases** fetch (shares
    S6's live-fetch budget; the atlas cannot detect parallel maintenance branches —
    see Grounding) marks `lts-like`. Tiering + the EOL-line check per decision 5(b);
    endoflife.date beats registry beats heuristic. Report rows carry `lts_status`
    AND `eol_date` (of the pinned line).
  Output tier: **keep / watch / plan-migration / replace**, with per-signal
  breakdown + `signals_absent`; `py314_readiness` and `lts_status` appear as explicit
  columns in every report row (and as `cfe:py314_readiness` / `cfe:lts_status`
  properties in annotated BOMs); `replace` tier auto-attaches `find-alternative`
  suggestions. Weights + dated thresholds in one auditable dict.
- **S8 — `recommend-2027` report.** Runs S5 then S7 over a user inventory → a single
  scorecard report (markdown + JSON + optional annotated CycloneDX with
  `cfe:futures_tier` / `cfe:futures_score` properties, `cfe:atlas_built_at` stamped).
  Calibrate on a fixture set of known-good (e.g. numpy, pydantic, **and one healthy
  non-Python package, e.g. a maintained Go/Rust CLI**) and known-bad (archived /
  KEV-listed / >18-months-silent, **including one non-Python case**) packages as unit
  tests — plus horizon-signal calibration cases: **django** (endoflife-driven: a
  5.2 pin → `lts-supported`, EOL 2028-04-30; a **4.2 pin → `eol-before-window`**,
  EOL 2026-04-07, and must NOT tier `keep`), one `py314-not-ready` package (must
  cap at `watch`), and one `py314-ready` compiled package. The tiers must rank all
  of these correctly before weights are accepted. The CLI name stays
  `recommend-2027`; the report header states the **2027–2030 window** explicitly.
  **Optional pre-run downloads refresh (operator-gated, per user 2026-07-05):**
  when `downloads_fetched_at` age exceeds ~90 d (the window the signal measures),
  the report offers a Phase P refresh (BigQuery; the user has cost-optimized it) —
  ALWAYS run the § 13 dry-run cost preflight first and present the measured
  estimate for approval; never run implicitly. Verified 2026-07-05: data is fresh
  (max fetched 2026-07-04; 818,868 `bigquery-public` + 32,491 `clickhouse-clickpy`
  rows) — no refresh needed at authoring time. MCP: `recommend_2027`.

#### Wave D Dev Notes — local slice + live gates (2026-07-06; measured, not estimated)

The S7/S8 web slices deferred four surfaces to local; three were RUN live and
one (the decision-5(b) `lts-like` releases heuristic) was IMPLEMENTED here —
like Wave C, the web slice could only reach `lts-like` via registry
`heuristic-seed` entries; the live releases-based heuristic did not exist:

1. **`lts_like_from_releases`** (new, pure + 6 offline tests): a strictly-older
   MAJOR line with a non-yanked upload AFTER the newest line first appeared,
   recent within the dated `LTS_LIKE_RECENT_DAYS = 547`. Wired as
   `EolClient(releases_fetcher=…)` — the live default shares S6's bounded
   pypi.org JSON fetcher (memoized); consulted ONLY when endoflife + registry
   both miss AND a pypi identity exists. **Live verification (2026-07-06):**
   `pydantic` → `lts-like` (1.10.26 uploaded 2025-12-18, 2.x first
   2023-04-03 — active parallel maintenance, hand-verified);
   `sqlalchemy` + `urllib3` correctly stay `unknown` (their old-line patches
   fell outside the 18-month window).
2. **Live endoflife.date fetch** (the default `_http` fetcher over
   `resolve_endoflife_urls`): verified across the measured run — `openssl`
   pinned-line EOL 2026-11-01 → plan-migration, `perl` line EOL 2023-06-20,
   `django` lts-available with line EOL 2027-04-30 (in-window keep signal),
   `oniguruma` product-fully-EOL. The TTL cache works: a cached 3-package
   re-run is 1.2 s vs live fetching during the 323 s full run.
3. **Phase-P real path**: `downloads_staleness: None`, all `signal_ages`
   ≤ 1 day (downloads refreshed 2026-07-04, atlas built 2026-07-05) — the
   § 13 cost-preflight offer correctly did NOT fire; no refresh executed.
4. **Measured `futures_score` distribution** (repo pixi env, the Wave C
   1,150-row resolved inventory; 1,149 scored + kedro-mcp not_evaluated
   [ADD]): **wall 323 s** (incl. live endoflife + eligible-set fetches),
   71 MB peak RSS. Tiers: **keep 996 · watch 143 · plan-migration 3 ·
   replace 7** — a healthy spread, no recalibration needed. Scores:
   min 61.4 · p25 77.0 · median 81.2 · p75 84.0 · max 95.6 (mean 80.8).
   py314: 1,028 unknown (mostly non-Python rows — legitimately absent) ·
   120 ready · 1 likely. LTS: 1,135 unknown · 5 lts-available · 9 none.

**S8 real-inventory smoke (PASS):** hand-checked verdicts trace to real
signals — `openssl`/`perl` (EOL floors, live dates), `blosc`/`pexpect`/`httpx`
(>18 mo silence caps — httpx's last upstream release genuinely >18 mo old),
`grpcio`/`libmamba`/`email_validator` (archived floors: `feedstock_archived=1`
confirmed in the atlas; escalated to replace with alternatives — the
`email_validator`→`email-validator` suggestion is exactly right), `numpy`
keep/py314-ready. **Quality note (report-only, for the S-retro):**
`find-alternative` suggestions on replace rows are mixed (`cherrypy` for
`grpcio`) — a known similarity-scoring limitation, surfaced verbatim.
The real-SBOM leg: the Wave B 50-component slice → 32 keep / 18 watch in
17.1 s, `--sbom-out` annotated `cfe:futures_tier`/`cfe:futures_score`/
`cfe:py314_readiness`/`cfe:lts_status` per component.

Suite after the local slice: **2,119 passed / 2 known skips / 1 xpassed,
102 s** (`pixi run -e local-recipes test`).

### Wave E — Closeout

- **S9 — Docs + surfaces.** `reference/mcp-tools.md` (**+4 tools**: `export_purls`,
  `universe_sbom`, `inventory_match`, `recommend_2027`),
  `reference/atlas-phases-overview.md` Part A persona rows (consumer/architect:
  "which of my libraries — Python or not — should survive 2027–2030?"),
  `quickref/commands-cheatsheet.md`, SKILL.md Atlas CLI table (+4 rows). Regeneration
  cadence documented: `export-purls` + `universe-sbom` run after every atlas rebuild
  (noted in `guides/atlas-operations.md` next to the bootstrap-data runbook — wiring an
  automatic hook is optional follow-up, the freshness gate in decision 6 is the
  enforcement). **Cross-spec re-sync** per § Cross-spec impact & sync (extend the
  kedro-migration note with the `g10_spelling` writeback + `cfe:*`/`?channel=` purl
  conventions; BMAD planning artifacts re-grounded via the documented sync loop).
  CHANGELOG entry; **MINOR** skill version bump.
- **S-retro — CFE retrospective (Rule 2, mandatory).** `bmad-retrospective` over the
  effort; land corrections/refinements/additions in skill files; re-stamp the BMAD sync
  baseline (`bmad-drift-check -- --write-baseline`) since counts/tool-lists change.
  The retro also runs the **closing all-specs sync sweep** (§ Cross-spec impact &
  sync, retro tasks): re-verify the impacted specs against what actually shipped.

## Verification (per-wave gates)

- Every new CLI: unit tests on a fixture DB + the three-place meta-tests green
  (`pixi run -e local-recipes` test suite).
- **Wave A live gates** (run in order; record dated counts in Dev Notes):
  ```bash
  cp -r .claude/data/conda-forge-expert/purl-export <scratch>/purl-export.baseline-20260704
  pixi run -e local-recipes export-purls -- --json
  # VERIFIED 2026-07-05: conda 33,392 · versioned 33,392 · pypi 843,641 (= the
  # G98-distinct count of the 843,764 universe rows) · mapped 21,403 → 21,528
  # after S2 (+125) · exceptions 84 — the D1 gate is `not-in-pypi-export == 0`
  # (confirmed), NOT the total, which tracks pending/blocked recipe drift
  # (2 recipes gained pending status since the 2026-07-04 baseline)
  LC_ALL=C sort -c .claude/data/conda-forge-expert/purl-export/purls_pypi.txt
  sed 's|^pkg:conda/||; s|[@?].*$||' .claude/data/conda-forge-expert/purl-export/purls_conda-forge.txt | LC_ALL=C sort -c
  diff <baseline>/recipe-purl-exceptions.txt <live>  # expected: ONLY the 2 dots-bug lines removed + status drift
  pixi run -e local-recipes mapping-gap -- --json    # dry-run: rows_written==0; review report; spot-check 5 pairs
  pixi run -e local-recipes mapping-gap -- --write --json
  # then assert: g10_spelling row count == rows_written; parselmouth/recipe_source_url rows byte-unchanged
  pixi run -e local-recipes mapping-gap -- --write --json   # idempotency: rows_written==0
  sqlite3 "file:.claude/data/conda-forge-expert/cf_atlas.db?mode=ro" \
    "SELECT COUNT(*) FROM v_pypi_intelligence_valid;"   # D3 view live post-migration (< pypi_intelligence count by ~93k)
  pixi run -e local-recipes export-purls -- --json   # mapped TSV lines == previous_lines + rows_written
  pixi run -e local-recipes test
  ```
- S3/S8 quantitative claims (BOM size, emit time, score distributions) recorded from
  actual runs with dates — never estimated (CFE live-verification principle). S4's
  schema validation runs once against the REAL full BOM, not only fixtures.
- S5 end-to-end smoke: run against this repo's own `pixi.toml` env and one real CycloneDX
  SBOM; hand-verify 3 members of each bucket (incl. one G10 rename, one
  atlas-stale/channeldata-fresh case, one `version_comparison: unreliable` case, **and
  one non-Python conda package with GitHub upstream** — e.g. a Go/Rust CLI from the env).
- After Wave E: `pixi run -e local-recipes bmad-drift-check` clean.

## Risks / open items

- **Full-universe BOM size is unmeasured** — ~844k PyPI components as CycloneDX JSON
  will be large; S3 measures before the single-file-vs-split layout is fixed. Slices
  exist for consumers that can't ingest the full set.
- **Non-Python upstream identity coverage is partial**: `upstream_versions` tracks
  47,143 packages (GitHub-dominant); registry-name columns are near-empty (npm 198,
  cran/cpan/luarocks 0). Non-Python packages with no upstream row get
  `signals_absent: upstream_freshness` and a UNKNOWN-leaning match — S2 reports the
  count; expanding Phase L/K coverage is deliberately out of scope here.
- **Signal portability**: PyPI `downloads_*` (851k rows) exists only because Phase P/BQ
  ran on this DB; a credential-less rebuild loses it. S7 treats PyPI downloads as
  optional (denominator-shrinking), never load-bearing. Conda-side Phase F downloads
  are the portable adoption signal.
- **93,390 orphan `pypi_intelligence` rows** (no universe counterpart) — S2 owns the
  reconciliation rule; until then they are excluded from version truth.
- Mapping tiers `none` (3,527 unattributed rows, `match_confidence='n/a'`) and
  `name_coincidence` (40, `likely`) are lower-confidence; S5 surfaces
  `match_confidence` per row rather than presenting all mappings as equally verified.
- S6's bounded live enrichment writes to `pypi_intelligence` — same write-path
  discipline as S2 (idempotent upsert, respects `_http.py` enterprise routing).

## Cross-spec impact & sync (implementation + retro tasks, per user 2026-07-05)

`docs/specs/` stays mutually consistent: changes this spec makes to shared atlas
facts propagate to affected siblings **as part of implementation** and are
re-verified **at the retro**. Full-tree impact analysis (all 13 specs, 2026-07-05):

| Spec | Verdict |
|---|---|
| `trendshift-conda-forge.md` | **IMPACTED — synced 2026-07-05**: Phase T renumbered v29→v30 (incl. the A1 acceptance line), v29 fixture-base conditional, `v_pypi_intelligence_valid` read note |
| `cfe-atlas-datapipeline-kedro-migration.md` | **IMPACTED — synced 2026-07-05**: re-enumerate-at-intake note (+5 CLIs / +4 MCP tools / +1 view / endoflife.date cache / trendshift v30) |
| `cfe-shipped-releases.md` | INFORMATIONAL — dated archive, no update (retro cross-ref: its DW17 `scan_project --pixi-lock` follow-up is **discharged by S5a**'s lockfile-intake work — note it at the retro) |
| the other 9 (conda-forge-tracker, claude-team-memory, copilot-bridge, db-gpt, flyte, langflow, feedstock-refresh / -platform-expansion / -failure-remediation) | NONE — recipe-authoring / process docs; no atlas read-surface touched (their `python_min` / `schema_version: 1` / parselmouth mentions are recipe-level, verified line-by-line) |

**Implementation-time tasks (owned by the wave that ships the change):**
- **Wave A/S2** — extend the kedro-migration cross-spec note with the
  `packages.pypi_name`/`match_source='g10_spelling'` writeback + the `cfe:*`
  property namespace + `?channel=conda-forge` purl qualifier (its FR-13 CycloneDX
  normalizer must preserve both); re-confirm trendshift's base-version conditional.
- **Every wave** — after shipping: repo-wide grep for the changed fact (e.g. `v29`,
  tool counts) + `pixi run -e local-recipes bmad-drift-check --specs`. BMAD planning
  artifacts (`index.md`, `implementation-readiness-report.md`,
  `architecture-cf-atlas.md`, `architecture-mcp-server.md` — all pin schema v28 /
  42 MCP tools / 22 phases) are re-grounded via the documented sync loop
  (`bmad-groundtruth` → reconciler skills → `-- --write-baseline`), never hand-edited.

**Post-ship amendment (2026-07-12, from the pyforge-warden Phase-0
review):** the S5 `inventory-match --policy` exit-code convention shipped as
`0 = pass, 2 = policy violations, 1 = error` — **inverted** relative to
`pyforge-warden.md`'s frozen enum (`0` pass / **`1` policy-violation** /
**`2` error** / `130` SIGINT) and to the kedro-migration **FR-18 unified gate**,
which is specced to the pyforge-warden convention while naming
`inventory-match --policy` as a co-source. `rc==2` therefore means "block the
merge" here and "operational error, page the platform owner" there. **Obligation
(owned at the FR-18 implementation, or earlier if a shared CI template lands):**
flip `inventory-match --policy` to the pyforge-warden convention with
a deprecation window for existing consumers (e.g. honor an
`INVENTORY_MATCH_LEGACY_EXIT=1` env for one release). Cross-ref:
`pyforge-warden.md` § Cross-spec impact & sync item 1; full analysis
in gist `326be5f25e702e0fcce343046c70a6b2` (finding X1).

**Retro-time tasks (S-retro):** the closing all-specs sync sweep — re-verify both
impacted specs against what actually shipped, add the optional cfe-shipped-releases
DW17 cross-ref, re-stamp the BMAD baseline.
- **endoflife.date is an external dependency** (availability; v1 schema stability;
  460-product coverage ≪ the universe). Mitigations: TTL'd cache with
  stale-plus-age-warning (never a hard fail); uncovered products fall through to
  the registry slug-map/overrides then the labeled `lts-like` heuristic; registry
  entries stay dated and the S-retro revisits them (expired → `unknown`, never a
  silent support assertion). A project back-porting patches is not the same as a
  published LTS policy.

---

> Source: `docs/specs/lts-registry-gap.md` (canonical file — still lives there).
> Original frontmatter: `doc_type: spec; part_id: lts-registry-gap; display_name: lts-registry-gap suggester; project_type_id: tooling; date: 2026-07-06; status: shipped; implemented_by: conda-forge-expert v8.74.0; shipped_ref: c428c5849aa88abccc170582c222babc6f6b1260; spec_updated: 2026-07-06`

# Spec: `lts-registry-gap` — propose lts-registry.yaml entries (mapping-gap sibling)

## Goal

`data/lts-registry.yaml` is deliberately hand-curated (every entry encodes a
verified conda-name → endoflife.date-slug decision or a manual LTS line), so
the pipeline never writes it. The automation gap is **discovery**: nobody
systematically diffs endoflife.date's product list against the atlas to find
packages the registry *could* cover. `lts-registry-gap` closes that gap in
the `mapping-gap` mold — a read-only suggester that **proposes** entries with
confidence tiers; accept/reject stays with git review. The registry keeps the
property that every entry was verified by a human.

## Design

- **Inputs**: `cf_atlas.db` (`v_actionable_packages` — the canonical
  persona-filter view), endoflife.date's all-products list
  (`/api/all.json` via `_http.resolve_endoflife_urls("all")`, mirror-routable
  per `ENDOFLIFE_BASE_URL`; TTL-7d cache `eol_products.json` in the runtime
  data dir, offline-stale fallback — the `EolClient` cache pattern), and the
  current registry via `library_futures.load_lts_registry` (already-covered
  names are excluded, aliases included).
- **Matching tiers** (conservative; no fuzzy matching):
  - `exact` — `conda_name` or `pypi_name` lowercase-equals a product slug.
  - `likely` — equality after `_`→`-` normalization, or after stripping a
    `python-` / `py-` conda-name prefix.
- **Output**: ready-to-paste YAML entry snippets grouped by tier (stdout or
  `--out FILE`), each stamped `source: endoflife` + a `note:` naming the
  match basis; `--json` machine summary; `--limit` per tier;
  `--products-file` for offline/test injection. **Never writes
  `lts-registry.yaml`**; exit code 0 always (report tool).

## Acceptance criteria

- Three-place rule: canonical script + wrapper + pixi task + SCRIPTS meta
  entry; `--help` clean.
- Fixture tests: exact + likely tiers, registry-covered exclusion,
  no-match exclusion, stale-cache fallback, `--json` shape, `--limit`.
- Registry file provably untouched by any code path (no write call sites).
- Docs: SKILL.md atlas CLI table row + Version History, CHANGELOG v8.74.0
  (MINOR — new tool), commands-cheatsheet row. CLI/pixi-only (no MCP tool),
  matching `library-futures`/`add-handoff`.

---

> Source: `docs/specs/seed-gap-suggesters.md` (canonical file — still lives there).
> Original frontmatter: `doc_type: spec; part_id: seed-gap-suggesters; display_name: seed-gap suggesters (CWE + SPDX + license-map); project_type_id: tooling; date: 2026-07-06; status: shipped; implemented_by: conda-forge-expert v8.75.0 (cwe/spdx) + v8.76.0 (license-map); shipped_ref: 6b23022a335bfce317b961937ce52fb2a4699464; spec_updated: 2026-07-06`

# Spec: seed-gap suggesters — `cwe-seed-gap` + `spdx-schema-gap` + `license-map-gap`

## Goal

Two more git-tracked seed assets under `data/` are hand-curated and grow only
by hand, with no systematic view of what they're missing:

- **`cwe_categories_seed.json`** (67 CWE-ID → cf_atlas-category mappings) —
  every CWE not in the seed defaults to `Other` in the `cwe_categories`
  atlas table, so a genuinely-classifiable weakness silently sits in the
  `Other` bucket forever.
- **`spdx.schema.json`** (811-ID SPDX enum, vendored at v3.28.0) — used by
  `_sbom.normalize_license` + `conda_forge_atlas._normalize_license_to_spdx`.
  It drifts behind the upstream SPDX license list, and real package licenses
  can fall outside it unnoticed.

This effort adds two read-only suggesters in the `mapping-gap` / `lts-registry-gap`
mold — they **propose** additions with confidence tiers; accept/reject stays
with git review. **Neither ever writes its seed.** Both continue the
"push automation further" line (v8.74.0 `lts-registry-gap`) and register two
more external-data-asset maintenance loops for the kedro migration (§ below).

## `cwe-seed-gap` (offline; atlas-grounded)

- **Input**: the `cwe_categories` table (MITRE's full catalog, populated by
  `fetch-cwe-catalog`) + the seed via `cwe_catalog_fetcher._load_seed_mapping`.
- **Discovery**: rows with `cf_atlas_category = 'Other'` whose `cwe_name`
  matches a curated keyword heuristic for the 7 real categories. Two tiers:
  `strong` (a category-defining phrase — `sql injection`, `use after free`,
  `path traversal`) and `weak` (a generic word — `injection`, `memory`,
  `authorization`). First strong hit across a fixed category precedence
  wins; else first weak hit. No match → not proposed (stays `Other`).
- **Impact headline**: count of packages whose `vuln_cwe_categories_json`
  carries a non-zero `Other` bucket — the universe cost of the gap. (Per-CWE
  package attribution isn't recoverable — Phase G/G' aggregates CWE-IDs to
  categories — so the heuristic, not package count, ranks proposals.)
- **Output**: ready-to-paste `"CWE-NNN": "Category"` seed lines grouped by
  tier, each with the matched keyword as justification; `--json`; `--limit`
  per tier. Reads `cwe_categories` only — fully offline.

## `spdx-schema-gap` (atlas-grounded; upstream cross-check)

- **Inputs**: the vendored enum from `spdx.schema.json`; the upstream SPDX
  license list (`spdx/license-list-data` `json/licenses.json` via
  `_http.resolve_github_raw_urls`, `GITHUB_RAW_BASE_URL`-routable; TTL-7d
  cache `spdx_license_list.json` with offline-stale fallback — the
  lts-registry-gap products-cache contract; `--source-file` for offline/test);
  distinct `conda_license` (+ `pypi_intelligence.license_spdx`) from
  `v_actionable_packages` with package counts.
- **Classification** of each distinct atlas license string not in the
  vendored enum (compound SPDX *expressions* — containing `AND`/`OR`/`WITH`/
  parens — are skipped; the enum holds single IDs only):
  - in the upstream SPDX ID set → **add-to-schema** (real staleness: SPDX has
    it, the vendored copy predates it) — ranked by package count.
  - not upstream either → **non-standard** (a normalization candidate,
    report-only — NOT a schema add).
- **`--drift`** (opt-in): upstream IDs entirely absent from the vendored enum,
  independent of atlas usage (the pure staleness count).
- **Output**: ready-to-paste enum-ID additions (the `add-to-schema` tier) +
  the non-standard normalization list; `--json`; `--limit`; `--out`. Never
  writes `spdx.schema.json`.

## `license-map-gap` (offline; atlas-grounded) — added v8.76.0

The third family member targets an **in-code** curated map rather than a
git-tracked seed: `conda_forge_atlas._LICENSE_TO_SPDX` (~36 lowercased
free-text → canonical-SPDX entries; `_normalize_license_to_spdx` returns
`None` on a miss, silently degrading the Phase R/S license-readiness score).

- **Input**: `pypi_intelligence` — the discovery signal is `license_raw`
  rows whose `license_spdx IS NULL` (the map missed), grouped with package
  counts. Fully offline; also imports `_LICENSE_TO_SPDX` (exclusion +
  coverage count) and `_sbom._spdx_id_enum` (vendored SPDX ID universe).
- **Junk filter** (not single-map entries): empty / `unknown`; over-long
  strings (>60 chars = a pasted full license text); `see …` / URL /
  copyright forms; SPDX **expressions** (`AND`/`OR`/`WITH` or parens);
  forms already keyed in `_LICENSE_TO_SPDX`.
- **Conservative candidate hint**: the vendored SPDX ids whose lowercased id
  is a **whole-token** match inside the lowercased form (never a substring —
  `isc` won't match inside `basiclicense`; 2-char ids skipped). No fuzzy
  matching — a wrong license map is a correctness bug.
- **Two tiers**: `likely` = exactly one candidate → a ready-to-paste
  `"<form>": "<SPDX-id>",` line (human still verifies); `report` = zero /
  multiple candidates → the form + candidate set, ranked by package count,
  for a human to pick the target.
- **Output**: paste-ready `likely` lines + the ranked `report` list;
  `--json`, `--limit` per tier, `--out`, `--db`. **Never writes
  `conda_forge_atlas.py`** (no write path at all).

## Acceptance criteria

- Three-place rule per tool (canonical script + wrapper + pixi task +
  SCRIPTS meta entry); `--help` clean; CLI/pixi-only (no MCP tool).
- Fixture tests per tool: tier classification, seed/enum-covered exclusion,
  no-match/expression exclusion, stale-cache fallback (SPDX), `--json` +
  `--limit` shape, and a **seed-file-untouched** assertion (byte-identical
  across a full CLI run) for each.
- Docs: SKILL.md atlas CLI rows + Version History; CHANGELOG v8.75.0 (MINOR);
  cheatsheet rows. CLAUDE.md spec-table row.
- Kedro reflection (cross-branch follow-up): the migration spec's § 3.4
  (on the in-flight boundary branch) + the kedro-viz prototype (on its own
  branch) gain the three seed-gap loops (lts-registry, cwe, spdx) as
  read-only "seed freshness report" nodes fanned out from the external seed
  datasets — the mapping-gap-writeback analogue for curated seeds. Folded
  into those branches once they land (kept off this main-based branch to
  avoid a § 3.4 collision).
