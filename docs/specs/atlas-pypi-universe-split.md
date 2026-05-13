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
