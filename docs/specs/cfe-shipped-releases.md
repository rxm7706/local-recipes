---
status: shipped
implemented_by: bmad-quick-dev
shipped_ref: "consolidated archive — 9 shipped skill/atlas release intakes (v7.9.0 → v8.20.0) + 1 closed packaging effort; per-part refs below"
spec_updated: 2026-07-02
---
# Shipped Releases — consolidated intake-spec archive

> **Consolidated record (2026-07-02).** This file archives every SHIPPED conda-forge-expert
> release intake spec plus the closed graphifyy fanout effort — the "so many versions" cleanup.
> Part bodies are preserved verbatim from the pre-merge files; only frontmatter was consolidated
> (captured per part) and cross-file links between absorbed files rewritten to in-file anchors.
> Release *notes* live in `.claude/skills/conda-forge-expert/CHANGELOG.md`; these are the BMAD
> intake records (stories / FRs / ACs / open questions) kept for history. Do not re-run BMAD on
> any part.
>
> | Former file | Part | Shipped as |
> |---|---|---|
> | `atlas-pypi-universe-split.md` | [Part 1](#p1) | v7.9.0 (2026-05-13) |
> | `conda-forge-expert-v8.0.md` | [Part 2](#p2) | v8.0.0 (2026-05-13; Wave C deferred) |
> | `atlas-pypi-intelligence.md` | [Part 3](#p3) | v8.1.0 (2026-05-15) |
> | `atlas-appthreat-deep-signals.md` | [Part 4](#p4) | v8.6.0 (2026-05-24) |
> | `conda-forge-expert-v8.9.md` | [Part 5](#p5) | v8.9.0 (2026-05-25) |
> | `cfe-pr-artifact-downloader.md` | [Part 6](#p6) | v8.14.0 (2026-06-11) |
> | `atlas-phase-p-incremental.md` | [Part 7](#p7) | v8.15.0 (2026-06-12; corrected v8.15.2, superseded-in-part by v8.16.0 ClickHouse default) |
> | `atlas-phase-f-s3-backend.md` | [Part 8](#p8) | v7.6.0 + v8.17.0 / v8.18.0 / v8.19.0 (2026-05-10 → 2026-06-13) |
> | `atlas-phase-k-cron-runner.md` | [Part 9](#p9) | v8.20.0 (2026-06-13) |
> | `graphifyy-osx-arm64-fanout.md` | [Part 10](#p10) | effort closed 2026-06-17 |


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

<a id="p5"></a>

# Part 5 — maturin/PyO3 generator hardening

> Formerly `conda-forge-expert-v8.9.md` — shipped v8.9.0 (2026-05-25).
> Original frontmatter: `status: shipped; implemented_by: bmad-quick-dev; shipped_ref: "v8.9.0"; spec_updated: 2026-06-20`

# conda-forge-expert v8.9.0 — maturin/PyO3 generator path + template hardening

**Status:** intake-ready (not yet implemented).
**Bump:** MINOR (v8.8.0 → v8.9.0). Additive: new generator code path + template improvements. No breaking change.
**Driver:** `recipes/py-yaml12` recipe build (2026-05-25). Running `recipe-generator.py pypi py-yaml12` produced a noarch:python recipe for what is actually a Rust+PyO3 package — the generator silently misrouted to the wrong template. Hand-customization based on `template python-maturin` produced a clean recipe, but the workflow shouldn't require that step.
**Parent retro:** `_bmad-output/projects/local-recipes/implementation-artifacts/retro-conda-forge-expert-v8.7-v8.8-2026-05-25.md` (gap surfaced during py-yaml12 build).

**Empirical anchor:** Validated against an expanded sample (2026-05-25 second pass):
- **52 Rust label PRs total** (25 v8.7.0 CLI + 27 new — Mar–May 2026): `cargo auditable install` 39/42 = 93% of CLI subset; `--no-track` 22/25 = 88%; `cargo-bundle-licenses` 25/25 = 100%; `stdlib("c")` 24/25 = 96%; **`CARGO_HOME` workaround 0/25 = 0%** (definitively NOT canonical for CLI Rust).
- **27 PyO3/maturin PRs** (Mar 2020 – May 2026): `maturin` in host 18/27 = 67%; `compiler("rust")` 23/27 = 85%; `stdlib("c")` 18/27 = 67%; `cargo-bundle-licenses` 21/27 = 78%; **`cargo auditable` only 2/27 = 7%** (NOT canonical for PyO3 — older recipes pre-date the convention; newer ones still don't bother). **CARGO_HOME workaround 1/27 = 4%** (only ast-serialize, with a package-specific justification). **`version_independent` 2/27 = 7%** (only when paired with `is_abi3` variant). **CFEP-25 dual-version test matrix 1/27 = 4%** (rare in PyO3 — this is a pure-python convention, not a compiled-extension one).
- **30 pure-python PRs** (Apr–May 2026): patterns from v8.8.0 unchanged.
- **5 docs sources read:** [`conda-forge.org/.../rust`](https://conda-forge.org/docs/maintainer/example_recipes/rust/), [`.../pure-python`](https://conda-forge.org/docs/maintainer/example_recipes/pure-python/), [`conda-forge.org/.../knowledge_base`](https://conda-forge.org/docs/maintainer/knowledge_base/), [`rattler-build.../tutorials/python`](https://rattler-build.prefix.dev/latest/tutorials/python/), [`rattler-build.../tutorials/rust`](https://rattler-build.prefix.dev/latest/tutorials/rust/).
- **knowledge_base highlights** (new in this pass): `noarch: python` rules (no compiled extensions, no OS-specific scripts, no version-specific reqs); virtual packages `__unix`/`__win`/`__linux`/`__osx` for OS-conditional run deps under `noarch: python`; `run_constrained` for "installs everywhere but only constrained at runtime"; only `console_scripts` entry_points need recipe attention; "python in host creates a matrix per supported version" (key for compiled-vs-noarch routing).

## Goal

When a PyPI package builds Rust extensions via maturin/PyO3, the generator should emit a compiled-recipe shape (no `noarch: python`, Rust toolchain in build deps, maturin in host, the CFEP-25 test matrix wired correctly) without manual intervention.

Secondary: harden the `python-maturin` template with patterns that 17/17 of the recent merged PyO3 PRs need but the template doesn't pre-include.

## Acceptance criteria

1. `recipe-generator.py pypi <name>` on a maturin/PyO3 package produces a recipe that:
   - omits `noarch: python`
   - includes `${{ compiler("c") }} ${{ stdlib("c") }} ${{ compiler("rust") }} cargo-bundle-licenses` in `requirements.build`
   - includes `maturin >=1.X,<2.0` in `requirements.host` (not `setuptools`)
   - includes `cargo-bundle-licenses --format yaml --output THIRDPARTY.yml` as the first script line
   - lists `LICENSE` + `THIRDPARTY.yml` in `about.license_file`
   - emits the correct import name (read from sdist's `Cargo.toml [lib] name` and/or PyO3 `#[pymodule]` declaration), not the naïve `<dist-name>.replace("-", "_")`
   - includes the conditional Windows `CARGO_HOME=C:\.cargo` + idempotent `if not exist md` block
   - passes `optimize_recipe` with 0 suggestions
2. `recipe-generator.py pypi <name>` on a pure-Python package continues to emit the existing noarch:python shape (no regression).
3. `templates/python/maturin-recipe.yaml` is updated to be a complete drop-in starting point — even hand-instantiation via `template python-maturin` should produce a near-clean recipe (only metadata placeholders need replacement).
4. All 1168+ skill tests still pass; new tests cover the maturin detection + import-name extraction paths.

## Gaps (the four findings)

### G1 — `noarch: python` is hardcoded in `generate_recipe_yaml`

**Where:** `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:273` — `build: noarch: python` is literal in the f-string template.

**Why it's wrong:** PyO3/maturin packages produce platform-specific compiled extensions. `noarch: python` causes the package to be marked as architecture-independent, which breaks the actual build (no `cdylib` shipped) and breaks conda-forge CI matrix expansion.

**Fix:** Detect maturin from `pyproject.toml [build-system].requires` (fetched from sdist or from PyPI's `info` payload), route to a separate emit path that:
- skips `noarch: python`
- adds Rust toolchain to `requirements.build`
- adds maturin to `requirements.host`

The existing `templates/python/maturin-recipe.yaml` is the right shape; the generator can either (a) read the template file and substitute, or (b) keep f-string emission but in a separate `generate_maturin_recipe_yaml` function. Option (a) is simpler and matches the `template` subcommand machinery.

### G2 — `determine_build_backend()` misses maturin

**Where:** `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:96-115` — checks `requires_dist` for backend names.

**Why it's wrong:** Maturin is a **build-system** dependency, not a runtime dependency. PyPI's `info["requires_dist"]` lists only runtime/optional deps. Maturin lives in `pyproject.toml [build-system].requires` which PyPI exposes via the sdist contents or via project_urls/classifiers — not via the JSON metadata's `requires_dist`. The function returns `setuptools` (default) for every maturin package.

**Fix:** Extend `determine_build_backend()` to also inspect:
- the sdist's `pyproject.toml` `[build-system].requires` (preferred — authoritative)
- failing that, look for the `Programming Language :: Rust` classifier in `info["classifiers"]` as a strong hint that the package builds Rust extensions
- failing that, check if any wheel in `info["releases"]` has `cp3XX-cp3XX-<platform>` tags (platform-specific wheel = compiled package)

### G3 — `templates/python/maturin-recipe.yaml` missing canonical patterns

**Where:** `.claude/skills/conda-forge-expert/templates/python/maturin-recipe.yaml`.

**Missing patterns** (each appeared in 17/17 sampled merged Rust+PyO3 PRs):

a. **CFEP-25 dual-version test matrix** — template's `tests` section uses:
   ```yaml
   - python:
       imports: [...]
       pip_check: true
   ```
   Should be:
   ```yaml
   - python:
       imports: [...]
       pip_check: true
       python_version:
         - ${{ python_min }}.*
         - "*"
   ```
   The optimizer's `TEST-002` will fire on any recipe instantiated from this template until it's added.

b. **~~Windows `CARGO_HOME` long-path workaround~~ — DROPPED from this spec.** Initial draft proposed including the `set CARGO_HOME=C:\.cargo` + `if not exist md` block in the template. Empirical reality (verified against the v8.7.0 17/17 CLI Rust PR sample + this session's py-yaml12 build): the workaround is **not** canonical conda-forge style. The original comment in xorq-datafusion/recipe.yaml cited `pixi/issues/3691` which is closed-as-not-planned and is actually about publishing the `pixi_config` *crate*, not a generic path-too-long workaround. The hack is relevant only for packages whose Cargo dependency graph pulls pixi-related crates with deeply nested paths (xorq pulls these for its pixi integration; py-yaml12, ruff, etc. do not). The maturin template should **not** include this block by default. Document in SKILL.md as a per-package conditional pattern instead — only add when the cargo graph actually triggers the issue.

c. **`build.python.version_independent`** — **gated on upstream Cargo.toml abi3 feature**, not unconditional. Empirical 27-PR PyO3 sample: only 2/27 (7%) use it; both pair with `is_abi3` variant. The generator should:
   - Read the sdist's `Cargo.toml` `[features]` block when routing to the maturin path.
   - If `pyo3 = { features = ["abi3-py3XX"] }` or `default = ["abi3"]` + `abi3 = ["pyo3/abi3-py3XX"]` is present → emit `version_independent: true` (unconditional form, simpler for staged-recipes; the conditional `${{ is_abi3 }}` form is feedstock-level optimization).
   - Otherwise → omit. The package builds one wheel per Python version, no abi3 declaration needed.
   - Verified examples: py-yaml12 has `default = ["abi3"]` + `abi3 = ["pyo3/abi3-py310"]` → emit. phonors has `pyo3 = "*"` without abi3 feature → omit. cachebox has no abi3 → omit. ast-serialize has abi3 feature → emit conditional form.
   - Skill-internal G entry for this rule lives in SKILL.md "Recipe Authoring Gotchas" once landed.

d. **Source URL underscore-form filename** — many sdists publish as `<name_with_underscores>-<version>.tar.gz` even though the PyPI distribution name uses hyphens. Currently template uses:
   ```yaml
   url: https://pypi.org/packages/source/${{ name[0] }}/${{ name }}/${{ name }}-${{ version }}.tar.gz
   ```
   Should add a comment near the URL line noting the underscore-rewrite pattern for sdists where the upstream uses it (`py-yaml12` → `py_yaml12-0.1.0.tar.gz`).

### G4 — Generator doesn't extract import name from sdist

**Where:** `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:319` (v1) — `{info.name.replace("-", "_").lower()}` is the hardcoded heuristic.

**Why it's wrong:** This is **G7** from SKILL.md ("Grayskull's inferred Python import name can be wrong — verify against the sdist"). For PyO3 packages the import name is determined by the `#[pymodule]` declaration in `src/lib.rs` and the `[lib] name` in `Cargo.toml`, which is frequently different from the PyPI distribution name. Examples in the wild:
- `py-yaml12` distribution → `yaml12` import
- `microsoft-kiota-bundle` → `kiota_bundle` (re-exported short name)
- `azure-identity-broker` → `azure.identity.broker` (dotted namespace)

**Fix:** Add a helper that downloads the sdist + extracts the import name:
1. For Rust+PyO3 packages: read `Cargo.toml` `[lib] name = "<X>"` and verify against `src/lib.rs` `#[pymodule] pub fn <X>(...)`.
2. For pure-Python packages: read the top-level `__init__.py` path (`grep '__init__.py$'` in the tar listing) and take the first significant segment.
3. Cache the sdist for the duration of the generator run to avoid double-fetching.

The PyPI JSON API doesn't expose the import name. Sdist inspection is the only reliable source.

## Wave breakdown

### Wave A — Generator backend detection + maturin routing (G1 + G2)

**Stories:**
- S1: Extend `determine_build_backend()` to inspect the sdist's `pyproject.toml [build-system].requires` (download the sdist once, cache for the run); fall back to classifier hint + wheel-tag heuristic.
- S2: Add a `generate_maturin_recipe_yaml()` function that reads `templates/python/maturin-recipe.yaml`, substitutes `name`/`version`/`source_url`/`sha256`/`license`/`homepage`/`repository`/`documentation`/`description`/`imports` from PackageInfo, and writes to `recipe.yaml`.
- S3: Route `generate_recipe_yaml()` to either the noarch path or the maturin path based on `info.build_backend == "maturin"`.
- S4: Same routing in `generate_meta_yaml()` for v0/legacy.
- S5: Unit tests: synthetic maturin package fixture (mock sdist with maturin `[build-system].requires`) → assert recipe.yaml has Rust toolchain, no noarch, maturin in host.

**Verification:** `recipe-generator.py pypi py-yaml12` produces a recipe that passes `optimize_recipe` with 0 suggestions; `recipe-generator.py pypi rich` continues to emit the noarch shape.

### Wave B — Template hardening (G3) — REVISED per ~52-PR sample

**Empirical reality** (27 PyO3 PRs): the maturin template should be **minimal**. The patterns we considered including (CFEP-25 test matrix, Windows CARGO_HOME, version_independent, LTO/strip) are NOT canonical for PyO3 — they show up only in single-digit-percent of PyO3 PRs. The modal PyO3 recipe is much closer to **phonors** (a 2-line script: `cargo-bundle-licenses` + `pip install`) than to the CLI Rust pattern.

**Stories:**
- S6: **DROP** the CFEP-25 dual-version test matrix from the maturin template default. Only 1/27 PyO3 PRs use it. Add as a commented-out option for the package author who wants per-version test coverage, with explanation "the CFEP-25 matrix is a pure-python convention; for compiled PyO3 packages the per-Python-version build matrix already exercises each version".
- S7: **DROP** the Windows `CARGO_HOME` proposal entirely. 0/25 new CLI Rust PRs use it; only 1/27 PyO3 PRs (ast-serialize) used a *different* `c:\.cg` short path for a *package-specific* git-checkout depth failure. The xorq-style block in the current py-yaml12 recipe is misattributed to pixi#3691 (which is closed-as-not-planned about an unrelated topic). Per-package conditional pattern only — add as an SKILL.md "Recipe Authoring Gotchas" entry (new G10) explaining when to use it ("only when the cargo dep graph includes git deps with deeply nested checkouts that trigger Windows 260-char path limit; verify the failure mode before adding").
- S8: **Add `version_independent` as a commented annotation, NOT default.** Only 2/27 PyO3 PRs use it. When upstream Cargo.toml declares `pyo3 = { features = ["abi3-py3XX"] }` or has an `abi3` feature, the template should suggest the abi3-aware shape:
  ```yaml
  build:
    # Uncomment when upstream Cargo.toml declares pyo3 abi3 feature.
    # The is_abi3 variant must be supported by the feedstock's CBC; for
    # staged-recipes submission, leave it as unconditional true if the
    # package builds against abi3-py3XX:
    # skip: is_abi3 and not is_python_min
    # python:
    #   version_independent: ${{ is_abi3 }}
  ```
- S9: Update `templates/python/maturin-recipe.yaml` source URL with a comment about the underscore-form sdist filename pattern (e.g., `py-yaml12` → `py_yaml12-<ver>.tar.gz`). PEP 625 normalisation means most modern sdists use underscore form; older ones use the hyphen.
- S10: **Drop `script.env` + `script.content` + LTO/strip from the maturin template.** Only 3/27 PyO3 PRs use `CARGO_PROFILE_RELEASE_LTO` — this is a CLI Rust optimization (binary-size reduction). PyO3 extensions don't benefit meaningfully since the .so/.pyd is small relative to the Python package. The 2-line script (`cargo-bundle-licenses` + `pip install`) is the modal pattern.
- S11: Add a meta-test similar to `test_recipe_yaml_schema_header.py` that asserts the maturin template includes the essentials: schema header, `cargo-bundle-licenses` first, Rust toolchain in build, maturin in host, `THIRDPARTY.yml` in license_file. Do NOT assert CFEP-25 or Windows block (those are conditional).

**Verification:** `template python-maturin --name foo --version 0.1.0` produces a minimal recipe matching the **phonors** pattern (the modal 27/27 PyO3 PR shape). Passes optimizer with 0 suggestions on a real package after metadata replacement.

### Wave C — Import-name extraction (G4)

**Stories:**
- S11: Add `_extract_import_name_from_sdist(sdist_path: Path) -> str` helper. For Rust+PyO3 sdists: parse `Cargo.toml` `[lib] name`. For pure-Python: parse first top-level `__init__.py` path. Return empty string when ambiguous (let the caller fall back to the existing heuristic).
- S12: Wire into `fetch_pypi_info()` to populate a new `PackageInfo.import_name` field; default to the existing heuristic when extraction fails.
- S13: Use `info.import_name` in both `generate_recipe_yaml` and `generate_meta_yaml` instead of the inline `.replace("-", "_")` heuristic.
- S14: Unit tests against fixtures for: PyO3 package (yaml12), namespace package (azure.identity.broker dotted-import shape), pure-Python (rich), unknown shape (fall back to heuristic).

**Verification:** `recipe-generator.py pypi py-yaml12` emits `imports: - yaml12` (not `py_yaml12`); `pypi microsoft-kiota-bundle` emits `imports: - kiota_bundle`; pure-Python packages unaffected.

### Wave D — Knowledge-base patterns + virtual-package selectors (new in this revision)

The conda-forge knowledge_base surfaces patterns the existing generator + templates don't currently handle. Adding them lifts the generator from "produces a builds-clean recipe" to "produces a builds-clean recipe that's idiomatic conda-forge".

**Stories:**
- S15: **`noarch: python` decision validator** — add a generator helper `_can_noarch_python(info)` that returns False if any of these are true (per knowledge_base rules):
  - Has compiled extensions (detected via maturin/scikit-build-core/meson-python backend, or `Programming Language :: Rust`/`C++`/`C` classifier with platform-specific wheels in PyPI releases).
  - Declares OS-specific dependencies in `requires_dist` (`; sys_platform == 'win32'`, etc.) — those need `__win`/`__unix` virtual-package selectors.
  - Has post-link/pre-link/pre-unlink scripts (heuristic: look for `post-install` hooks in `pyproject.toml`).
  - Lists pre-3.0 Python in requires_python.
  The validator is *advisory* — emits a warning when a noarch recipe is generated for a package that probably shouldn't be noarch.

- S16: **Virtual-package selectors for OS-conditional run deps** — when a PyPI dependency has a `sys_platform` marker (e.g., `colorama ; sys_platform == 'win32'`), the noarch-python generator should emit:
  ```yaml
  run:
    - if: win
      then:
        - colorama
    - __win  # virtual package; ensures variant hash differs per platform
  ```
  (Per knowledge_base: "Do not forget to specify the platform virtual packages with their selectors! Otherwise, the solver will not be able to choose the variants correctly.")

- S17: **`run_constrained` for "installs everywhere but only constrained at runtime" deps** — generator currently doesn't emit `run_constrained` at all. Document the rule + add a comment in the noarch template suggesting it for packages whose deps are optional/conditional.

- S18: **Entry-points handling** — generator currently doesn't extract `[project.scripts]` from pyproject.toml. Per knowledge_base: "Only console_scripts entry points have to be listed in meta.yaml". Add `_extract_entry_points()` helper that reads sdist's pyproject.toml `[project.scripts]` and emits:
  ```yaml
  build:
    python:
      entry_points:
        - mycli = mypackage.cli:main
  ```
  Required for CLI Python packages (avoids the package shipping but not creating the bin shim).

- S19: **Sample-anchored doc note** — when the generator routes to the maturin path, emit a header comment in the generated recipe.yaml citing the PR sample (`# Generated 2026-05-25 from python-maturin template; pattern validated against 27 PyO3 PRs (Mar 2020 - May 2026)`). Helps reviewers + future agents understand the lineage.

### Wave E — Closeout

**Stories:**
- S20: Update SKILL.md "Recipe Authoring Gotchas" — G7 entry now references the v8.9.0 generator extraction as the canonical fix. Add **G10** "Windows CARGO_HOME long-path workaround is package-specific, not canonical" with the 0/25 + 1/27 sample evidence and the ast-serialize precedent for *when* to add it.
- S21: CHANGELOG.md v8.9.0 entry covering G1–G4 + the Wave D knowledge_base additions, with verification examples for py-yaml12 (maturin route) + rich (noarch route) + a hypothetical Windows-conditional package (virtual-package selector route).
- S22: Bump `config/skill-config.yaml` to 8.9.0.
- S23: Retro lands in `_bmad-output/projects/local-recipes/implementation-artifacts/retro-conda-forge-expert-v8.9-YYYY-MM-DD.md`. Per Rule 2, retro inspects whether the sample sizes (~52 Rust + 27 PyO3 + 30 pure-python) held up in practice; refreshes the quarterly audit's sample list.

## Risks / non-goals

- **Non-goal**: extending support to `meson-python` / `scikit-build-core` compiled paths in this spec. Those need their own routing logic (different toolchain pinning, different host deps); file a v8.10+ spec when needed.
- **Risk**: sdist download adds network latency to the generator's PyPI path. Mitigate by caching the sdist tarball under `/tmp/cfe-sdist-cache/<name>-<version>.tar.gz` for the lifetime of the run; clear on exit.
- **Risk**: some maturin packages are pure-Python wrappers around a Rust binary (e.g. `ruff`) — they DO need `noarch: python` despite having maturin in build deps. **Disambiguation**: only route to compiled path when both maturin in build-system AND a `src/lib.rs` with `#[pymodule]` is present in the sdist. Pure-binary wrappers don't have a `#[pymodule]` declaration.

## Empirical anchor (sampled merged PRs, Apr–May 2026)

PyO3/maturin packages where the generator would currently produce a broken recipe:
- `cachebox` (#33349) — pure PyO3, would emit `noarch: python` instead of compiled.
- `cocoindex` (#33231) — PyO3 + extra C sources.
- `phonors` (#33286) — maturin + numpy.
- `burner-redis` (#33024) — pyo3 + redis bindings.
- `microsoft-kiota-bundle` (#33355) — re-export naming pattern (G4 trap).
- `py-yaml12` (this session) — PyO3 only.

All five of these required hand-customization on top of the generator output. After v8.9.0, all five should generate cleanly.

## Sign-off

This spec is **intake-ready** — open questions resolved, scope bounded, acceptance criteria measurable. Run via `bmad-quick-dev` when the next conda-forge session has bandwidth for a multi-wave generator change.

---

<a id="p6"></a>

# Part 6 — PR CI-artifact downloader

> Formerly `cfe-pr-artifact-downloader.md` — shipped v8.14.0 (2026-06-11).
> Original frontmatter: `status: shipped; implemented_by: bmad-quick-dev; shipped_ref: "v8.14.0"; spec_updated: 2026-06-20`

# Tech Spec: conda-forge-expert v8.14.0 — PR Artifact Downloader

> **BMAD intake document.** Written for `bmad-quick-dev` (Quick Flow track —
> additive feature; net-new MCP tool + CLI + pixi task). ~9 implementation
> stories across 4 waves. Run BMAD with this file as the intent document:
>
> ```
> run quick-dev — implement the intent in docs/specs/cfe-pr-artifact-downloader.md
> ```
>
> **Per `CLAUDE.md` Rule 1**, any BMAD agent executing this spec MUST invoke
> the `conda-forge-expert` skill before touching skill code. Per Rule 2, the
> effort closes with a CFE-skill retrospective and a `CHANGELOG.md` entry.

---

## Status

| Field | Value |
|---|---|
| Status | **Draft v1** — ready for `bmad-quick-dev` intake |
| Owner | rxm7706 |
| Track | BMAD Quick Flow (tech-spec only, no PRD/architecture phase) |
| Surface area | `conda-forge-expert` skill — new CLI script (`pr_artifacts.py`), new pixi task (`pr-artifacts`), new MCP tool (`download_pr_artifacts`), 1 guide section + 1 quickref entry + 1 reference entry |
| Scope | Given a staged-recipes or feedstock PR (URL or number), resolve the Azure DevOps `buildId` via `gh pr checks`, list published artifacts via the Azure REST API, download all `conda_pkgs_*` ZIPs, optionally extract them into a valid local mamba channel layout. Read-only operation. Anonymous Azure auth. |
| Version | conda-forge-expert v8.13.2 → **v8.14.0** (MINOR — net-new user-facing feature; no breaking changes to existing CLIs / MCP tools / build flow) |
| Out of scope | Auto-installing artifacts into a conda env; re-running CI on the PR; modifying the PR; private Azure project authentication (conda-forge is public); win-host cross-build (already shipped in v8.13.2's `recipe-build-cross`); per-version vdb history of fetched artifacts |
| Created | 2026-06-11 |
| Driven by | gh-copilot-cli staged-recipes#33693 session — reviewers needed an osx-arm64 artifact for hands-on smoke-testing before merge; the Azure UI's per-job artifact download required ~5 clicks per platform with no batch path; same friction every time a PR's `azure.store_build_artifacts: true` is set |
| Predecessor | `docs/specs/conda-forge-expert-v8.0.md` (v8.0.0 — last MINOR-bump feature spec); the v8.13.2 `recipe-build-cross` wrapper landed without a spec (small additive script). This spec re-establishes the spec-driven discipline for v8.14.0 |

---

## Background and Context

### The problem

Staged-recipes' Azure pipeline matrix is hardcoded to `linux_64` / `osx_64` /
`win_64` — the `osx_arm64` and `linux_aarch64` artifacts come only post-merge
from the auto-generated feedstock. For platforms the staged-recipes runners
DO cover, the artifact is published to Azure DevOps as a `.zip` (one per
job: `conda_pkgs_linux`, `conda_pkgs_osx`, `conda_pkgs_win`), but the UI is
optimised for human eyeball-review of build logs, not bulk artifact fetch:

1. Open the Azure URL from the PR's check link.
2. Click "X published" in the artifacts strip.
3. For each artifact: hover, click the kebab, click "Download artifacts".
4. Browser saves a zip per job.
5. Unzip each manually, locate `.conda` inside, organise into a local channel.

Multiply by 3 jobs and any time a reviewer wants to spot-check 2-3 PRs in a
batch, the friction kills the "review the artifact, not just the diff" loop
that `azure.store_build_artifacts: true` (CFE reference
`conda-forge-yml-reference.md` § "Top use cases") was meant to enable.

The v8.13.2 `recipe-build-cross` wrapper closed the gap for platforms
staged-recipes' CI doesn't reach (osx-arm64, linux-aarch64) by building
locally. The remaining gap is the inverse: when CI **did** build, fetch
those exact bytes — same ones the reviewer would see if they merged blind —
without re-building.

### What's been ruled out

- **Inline-only MCP tool with no standalone CLI.** Future CLI ergonomics
  (cron job pulling artifacts on every PR open, sharing the `.conda` over
  Slack, scripted local smoke-test pipelines) all want a shell-callable
  surface. Build the CLI first; the MCP tool is a thin wrapper.
- **Adding artifact-download support to `recipe-build-cross`.** Different
  problem shape: cross-build is recipe-input → `.conda` output; this is
  PR-input → `.conda` output. Different identifier (recipe path vs PR ref),
  different resolution chain (rattler-build vs Azure REST), different
  failure modes (build failures vs network/auth failures). One script per
  concern, one pixi task per concern.
- **Using `az` CLI for Azure auth + API access.** Adds a heavy dep
  (`azure-cli`) for what is a single anonymous REST call to a public
  project. The existing `_http.make_request` helper (CFE reference
  `mcp-tools.md` § "Internal HTTP layer") covers it with the JFrog /
  GitHub / .netrc auth chain already in place.
- **Auto-install the downloaded `.conda` into a mamba env.** Too much
  policy bakes in (which env, which channel priority, --force-reinstall
  semantics). The output layout is already a valid `file://` channel; the
  user can `mamba install -c file:///abs/path/extracted <pkg>` themselves
  in one line. Revisit auto-install as a v8.15 follow-up if the CLI-as-is
  proves cumbersome.

### What's available to leverage

- **`gh pr checks <pr> --repo <owner>/<repo>`** already returns the Azure
  URLs as `link` fields in JSON output. No HTML scraping; no GraphQL.
  Existing dep (already in pixi env).
- **Azure DevOps Build Artifacts REST API** is documented at
  <https://learn.microsoft.com/en-us/rest/api/azure/devops/build/artifacts/list>;
  anonymous read works on the public `conda-forge/feedstock-builds`
  project. URL shape:
  `https://dev.azure.com/conda-forge/feedstock-builds/_apis/build/builds/{buildId}/artifacts?api-version=7.1`.
- **`_http.make_request`** (`.claude/skills/conda-forge-expert/scripts/_http.py`)
  already handles truststore + auth chain + JFrog routing. Streaming
  downloads are supported via `iter_content` pattern used by
  `pypi_intelligence.py` and `feedstock_enrich.py`.
- **`.claude/scripts/conda-forge-expert/`** entrypoint-wrapper layer
  established in v7.0.0 — every new user-facing script lands as
  (canonical-impl-in-skill, thin-wrapper-in-scripts) per the 3-tier
  layout. Meta-test `test_skill_md_consistency.py::test_every_user_script_has_a_pixi_task`
  enforces the pixi-task wiring.
- **Existing FastMCP server pattern** (`.claude/tools/conda_forge_server.py`)
  invokes scripts via subprocess and parses their `--json` output. No new
  MCP plumbing needed beyond defining the tool function + decorating with
  `@mcp.tool()`.

---

## Goals

1. **Single-command PR-to-artifacts**: `pixi run -e local-recipes pr-artifacts 33693` produces a local mamba channel from the PR's Azure-published `.conda` files in one step.
2. **MCP-callable** so Claude can drive the fetch as part of a review workflow (`download_pr_artifacts(pr_ref="33693")` returns the manifest).
3. **Works for both staged-recipes and feedstock PRs** (same Azure project; check-name auto-detect handles the surface).
4. **Idempotent and cacheable**: re-running over a populated output dir is a no-op when the buildId already fetched; `--force` opts back in.
5. **Read-only**: no PR modification, no env mutation, no auto-install. Output is a `file://` channel the user can install from on their own terms.
6. **Anonymous Azure auth**: no PAT, no `az login`, works on a fresh dev box with just `gh` authenticated.

## Non-Goals

- Re-running stale CI (use `@conda-forge-admin, please restart ci`).
- Installing into a conda env.
- Win-host cross-build (already in v8.13.2).
- Private Azure project authentication.
- Per-version vdb-history snapshots.

---

## Lifecycle Expectations

Per `CLAUDE.md` Rule 1, the BMAD agent invokes the `conda-forge-expert`
skill before touching `.claude/skills/conda-forge-expert/*`. Per Rule 2,
the effort closes with a `bmad-retrospective` pass that lands findings in
SKILL.md / reference / guides / CHANGELOG.md.

This is a Quick Flow effort — no PRD / architecture / epics. The spec is
the BMAD intake. Wave sequencing below is the contract.

---

## Design

### CLI surface

```
pr-artifacts <pr-ref> [options]

Positional:
  <pr-ref>            PR number (33693) or full URL
                      (https://github.com/conda-forge/staged-recipes/pull/33693).
                      Repo inferred from URL; defaults to
                      conda-forge/staged-recipes for bare numbers.

Resolution overrides:
  --repo <owner/repo> Override repo (e.g. for feedstock PRs not auto-
                      detected from a bare number). Default:
                      conda-forge/staged-recipes.
  --build-id <id>     Skip gh-CLI lookup; download a specific Azure
                      buildId directly. Useful when working from the
                      Azure URL or selecting a specific re-run.
  --check-name <name> Override "staged-recipes" / "<pkg>-feedstock"
                      auto-detection. Default: auto.

Output:
  --output-dir <path> Destination root. Default:
                      build_artifacts/pr/<pr-number>/
  --extract           Unzip published .zip artifacts and surface the
                      .conda files in a flat channel layout. Default ON.
  --keep-zips         Keep the raw .zip files alongside extracted/.
                      Default: discard zips after extract.
  --force             Re-fetch even when pr-artifacts.json shows the
                      same buildId already downloaded. Default: skip-
                      existing (idempotent).
  --all-runs          If the PR has multiple Azure runs, fetch each.
                      Default: latest run only.

Filtering:
  --platforms <list>  Comma-list, e.g. linux-64,osx-64. Filters which
                      artifact subdirs are extracted. Default: all.
  --all-artifacts     Fetch non-package artifacts too (logs,
                      _build_artifacts.json). Default: filter to
                      conda_pkgs_* by name.

Output mode:
  --json              Emit a JSON summary to stdout (used by the MCP
                      tool wrapper). Default: human-readable text.

Misc:
  -h, --help          Show usage and exit.
```

### MCP tool signature

```python
@mcp.tool()
def download_pr_artifacts(
    pr_ref: str,
    repo: str = "conda-forge/staged-recipes",
    build_id: int | None = None,
    output_dir: str | None = None,   # default build_artifacts/pr/<pr>/
    extract: bool = True,
    platforms: list[str] | None = None,
    all_runs: bool = False,
    force: bool = False,
    check_name: str | None = None,
) -> dict:
    """
    Fetch all CI-published .conda artifacts for a conda-forge staged-recipes
    or feedstock PR into a local mamba channel layout.

    Returns:
        {
          "pr_ref": "33693",
          "repo": "conda-forge/staged-recipes",
          "runs": [
            {
              "build_id": 1536673,
              "azure_url": "https://dev.azure.com/...",
              "result": "succeeded",
              "artifacts": [
                {
                  "name": "conda_pkgs_linux",
                  "platform": "linux-64",
                  "conda_files": ["linux-64/gh-copilot-cli-1.0.61-h....conda"],
                  "size_bytes": 78_641_152,
                },
                ...
              ],
            }
          ],
          "output_dir": "/abs/path/build_artifacts/pr/33693/",
          "channel_url": "file:///abs/path/build_artifacts/pr/33693/1536673/extracted",
          "skipped_cached": false,
          "errors": [],
        }
    """
```

### Resolution chain

```
1. Parse <pr-ref>
     bare digits → (default repo, pr_number)
     github URL  → (parsed repo, parsed pr_number)
   --repo flag overrides parsed repo.

2. Resolve buildId(s):
   IF --build-id given:
       use it directly; skip gh.
   ELSE:
       gh pr checks <pr> --repo <repo> --json name,link,bucket,state
       filter rows where:
           name == --check-name  (if provided)
           OR name == "staged-recipes"  (default for staged-recipes repo)
           OR name matches r"^<pkg>-feedstock$"  (auto for feedstock repo)
       grep `link` for r"dev\.azure\.com/conda-forge/.+?buildId=(\d+)"
       IF --all-runs:
           collect every distinct buildId
       ELSE:
           pick the highest (newest) buildId.

3. For each buildId:
   IF NOT --force AND output_dir/<buildId>/pr-artifacts.json exists:
       emit "skipped (cached)" and continue.
   ELSE:
       GET https://dev.azure.com/conda-forge/feedstock-builds/
           _apis/build/builds/{buildId}/artifacts?api-version=7.1
       parse artifacts list.
       filter to name matches r"^conda_pkgs_(linux|osx|win)$"
           unless --all-artifacts.
       for each artifact:
           stream artifact.resource.downloadUrl → output_dir/<buildId>/<name>.zip
           verify Content-Length matches downloaded bytes.

4. IF --extract (default):
       unzip each <name>.zip into output_dir/<buildId>/extracted/<subdir>/
       (the .zip already contains a subdir like `conda-build_<job>/linux-64/...`;
        we flatten one level so extracted/linux-64/*.conda is the result).
       filter to --platforms if specified.
       IF NOT --keep-zips: rm the .zip after successful extract.

5. Write pr-artifacts.json manifest at output_dir/<buildId>/.
6. Emit JSON or human-readable summary.
```

### Output layout

```
build_artifacts/pr/<pr-number>/
├── <buildId>/
│   ├── conda_pkgs_linux.zip      # only if --keep-zips
│   ├── conda_pkgs_osx.zip
│   ├── conda_pkgs_win.zip
│   ├── extracted/                # default — valid file:// channel
│   │   ├── linux-64/
│   │   │   ├── <pkg>-<ver>-<hash>.conda
│   │   │   └── repodata.json
│   │   ├── osx-64/...
│   │   └── win-64/...
│   └── pr-artifacts.json         # manifest (used by cache check)
└── (additional <buildId>/ dirs if --all-runs)
```

`extracted/<subdir>/repodata.json` is included in the Azure ZIPs — no
re-indexing needed.

### `pr-artifacts.json` manifest schema

```json
{
  "pr_ref": "33693",
  "repo": "conda-forge/staged-recipes",
  "build_id": 1536673,
  "azure_url": "https://dev.azure.com/conda-forge/feedstock-builds/_build/results?buildId=1536673",
  "fetched_at": "2026-06-11T19:42:18Z",
  "result": "succeeded",
  "artifacts": [
    {
      "name": "conda_pkgs_linux",
      "platform": "linux-64",
      "size_bytes": 78641152,
      "conda_files": ["linux-64/gh-copilot-cli-1.0.61-h....conda"],
      "extracted_to": "extracted/linux-64/"
    }
  ],
  "channel_url": "file:///abs/path/build_artifacts/pr/33693/1536673/extracted"
}
```

### Anonymous Azure auth

The `feedstock-builds` Azure project is public; the artifacts REST endpoint
accepts unauthenticated requests. `_http.make_request` must NOT inject
`Authorization: Bearer ...` when the destination host is `dev.azure.com`
(the JFrog / GitHub auth chain would otherwise attach credentials that
expose 401 noise). Add a host-allowlist short-circuit in the helper, or
explicitly pass `auth=False` from the new script.

### Failure modes the script handles explicitly

| Condition | Behavior |
|---|---|
| PR has no Azure check yet (CI pending or never triggered) | exit 1; clear stderr: `"No Azure build found on PR <ref>; CI may still be pending. Re-run when checks complete."` |
| PR has only a failed `linter` check, no `staged-recipes` check | exit 1; clear stderr: `"Build failed before publishing artifacts."` |
| Build succeeded but published 0 conda_pkgs_* artifacts (rare; opt-in needed) | exit 0 with WARN: `"Build published no conda_pkgs_* artifacts. Did the recipe set azure.store_build_artifacts?"` |
| Build was for a different commit (PR has new pushes since the build) | succeed with WARN: `"WARNING: latest buildId is for <sha-short>; PR head is <newer-sha-short>. Use --all-runs to see history."` |
| Network error mid-download | retry per `_http` retry policy; surface clean error after exhaustion |
| ZIP extraction fails (corrupt download) | exit 2; keep the bad ZIP for forensics; don't write the manifest |
| Cached buildId, no `--force` | exit 0; emit `"skipped (cached): <buildId> already fetched at <fetched_at>"` |

### Integration with existing CFE flow

- Step 9 ("Monitor PR build") in SKILL.md already mentions checking CI;
  a new bullet there points at `pr-artifacts` for grabbing the bytes.
- `guides/testing-recipes.md` gains a new § "Downloading artifacts from a
  PR" with a 4-line usage recipe + `mamba install -c file://...` example.
- `reference/mcp-tools.md` adds `download_pr_artifacts` to the tool
  inventory table.
- `quickref/commands-cheatsheet.md` adds one line under the "Local builds
  via pixi" section (which v8.13.2 just added).

---

## Stories — 4 waves, ~9 stories

### Wave A — Core fetch (S1–S3, ships standalone)

| ID | Story | Effort |
|---|---|---|
| **S1** | PR-ref parser + `gh pr checks` → buildId resolver. Accept bare digits or full GitHub URL; default repo `conda-forge/staged-recipes`; `--repo`, `--build-id`, `--check-name`, `--all-runs` flags. Unit-tested with mocked `gh` JSON output covering staged-recipes (`name: "staged-recipes"`) and feedstock (`name: "<pkg>-feedstock"`) cases. | M |
| **S2** | Azure REST artifact lister: `_http.make_request` against `feedstock-builds/_apis/build/builds/<id>/artifacts?api-version=7.1` with explicit `auth=False` (or host-allowlist short-circuit in `_http`). Parse the `value[]` list; filter to `conda_pkgs_*` by default; return artifact dicts with `name`, `downloadUrl`, declared `size`. | S |
| **S3** | Streaming ZIP downloader: writes `output_dir/<buildId>/<name>.zip`; verifies `Content-Length` matches written bytes; retries per `_http` policy; idempotency check against `pr-artifacts.json` cache. | S |

### Wave B — CLI + pixi task (S4–S5, ships behind Wave A)

| ID | Story | Effort |
|---|---|---|
| **S4** | argparse front-end exposing the full flag set above; `--extract` (default ON) wires `zipfile`-based extraction to `extracted/<subdir>/`; `--keep-zips` controls cleanup; `--platforms` filters subdirs; `--json` mode emits the manifest to stdout for MCP consumption. Writes `pr-artifacts.json` to `<buildId>/`. Live test against PR #33693 buildId 1536673 (the gh-copilot-cli session); assert linux/osx/win artifacts present + `.conda` extracted at expected paths. | M |
| **S5** | `[feature.local-recipes.tasks.pr-artifacts]` entry in `pixi.toml` pointing at the wrapper at `.claude/scripts/conda-forge-expert/pr_artifacts.py`. Add `pr_artifacts.py` to `tests/meta/test_all_scripts_runnable.py::SCRIPTS`. | XS |

### Wave C — MCP tool (S6, ships behind Wave B)

| ID | Story | Effort |
|---|---|---|
| **S6** | `download_pr_artifacts` FastMCP tool in `conda_forge_server.py`: subprocess-invokes the CLI with `--json` and parses the manifest. Signature matches the design section above. Two unit tests stubbing `subprocess.run` to verify (a) happy path returns parsed manifest, (b) non-zero exit propagates as an `error` key. Append `download_pr_artifacts` to `reference/mcp-tools.md` tool inventory. | M |

### Wave D — Closeout (S7–S9)

| ID | Story | Effort |
|---|---|---|
| **S7** | Docs: `guides/testing-recipes.md` new § "Downloading artifacts from a PR" (4-line usage + `mamba install -c file://...` example); `quickref/commands-cheatsheet.md` one-line entry; `SKILL.md` step 9 cross-reference. | S |
| **S8** | `CHANGELOG.md` v8.14.0 entry covering the new CLI + MCP tool + the MINOR-bump rationale + the live PR #33693 case study; `config/skill-config.yaml` bump 8.13.2 → 8.14.0. | S |
| **S9** | CFE retrospective per `CLAUDE.md` Rule 2: invoke `bmad-retrospective`; land findings as edits to SKILL.md / reference / guides / a fresh CHANGELOG note if anything cross-cuts. Save cross-skill auto-memory only if the finding crosses skill boundaries. | M |

### Wave sequencing rationale

A → B → C → D is dependency-respecting:

- **A first**: pure-logic primitives (PR parsing, Azure REST, ZIP fetch).
  Unit-testable with mocks; no CLI surface yet. Validating these in
  isolation derisks Wave B's CLI-flag matrix.
- **B second**: CLI flags + pixi task. Wave A's primitives compose into
  the argparse front-end. Live test against PR #33693 happens here —
  closing the user's original request before Wave C adds the MCP
  indirection.
- **C third**: MCP tool is a thin wrapper around the JSON-mode CLI from
  B. Adding it earlier means double-implementing JSON output during dev.
- **D last**: docs + CHANGELOG + retro land after the implementation is
  exercised. Retro findings have material to draw from.

**One-PR strategy**: this is small enough (~9 stories, all additive) to
land as a single PR. No schema change, no breaking surface, no migration
window. The two-PR split that v8.0 needed doesn't apply here.

---

## Acceptance Tests

For each wave, the BMAD agent runs the existing pytest suite plus explicit
new tests:

### Wave A

- `tests/unit/test_pr_artifacts_resolver.py::test_parse_bare_pr_number`
  — `parse_pr_ref("33693")` returns `("conda-forge/staged-recipes", 33693)`.
- `tests/unit/test_pr_artifacts_resolver.py::test_parse_github_url`
  — `parse_pr_ref("https://github.com/conda-forge/staged-recipes/pull/33693")`
  returns `("conda-forge/staged-recipes", 33693)`; also works for a
  feedstock URL.
- `tests/unit/test_pr_artifacts_resolver.py::test_buildid_extraction_from_gh_output`
  — mock `gh pr checks` returning the real shape captured from PR #33693;
  assert single `buildId=1536673` extracted from the `staged-recipes` row.
- `tests/unit/test_pr_artifacts_resolver.py::test_all_runs_returns_multiple`
  — mock `gh` output with 3 distinct Azure URLs across re-runs; assert
  `--all-runs` returns 3 buildIds sorted descending; default returns the
  highest.
- `tests/unit/test_pr_artifacts_resolver.py::test_no_azure_check_errors_clean`
  — mock `gh` output containing only the `linter` check; assert exit 1
  + stderr message mentions "No Azure build found".
- `tests/unit/test_azure_artifacts_lister.py::test_filters_to_conda_pkgs_default`
  — mock Azure REST response containing `conda_pkgs_linux`,
  `conda_pkgs_osx`, `_build_artifacts.json`, `logs`; assert only the
  3 `conda_pkgs_*` are kept by default; `--all-artifacts` keeps all 4.
- `tests/unit/test_azure_download.py::test_content_length_mismatch_raises`
  — stream a short body with a too-large `Content-Length`; assert
  exception raised after exhaustion.

### Wave B

- `tests/unit/test_pr_artifacts_cli.py::test_help_responds`
  — `pr_artifacts.py --help` exit 0, contains "Usage:".
- `tests/unit/test_pr_artifacts_cli.py::test_extract_layout`
  — fixture ZIP containing `linux-64/foo.conda` + `linux-64/repodata.json`;
  assert files land at `extracted/linux-64/foo.conda` after extract.
- `tests/unit/test_pr_artifacts_cli.py::test_keep_zips_default_off`
  — after successful extract, the `.zip` is removed unless `--keep-zips`.
- `tests/unit/test_pr_artifacts_cli.py::test_cached_buildid_skips_when_manifest_present`
  — pre-create `pr-artifacts.json` for buildId 1536673; assert second run
  exits 0 with `"skipped (cached)"` and no network calls.
- `tests/unit/test_pr_artifacts_cli.py::test_force_overrides_cache`
  — same setup with `--force`; assert network call made + manifest
  rewritten with new `fetched_at`.
- `tests/unit/test_pr_artifacts_cli.py::test_json_mode_emits_manifest`
  — `--json` flag; assert stdout is parseable JSON matching the manifest
  schema.
- Live smoke test (not in CI; run from this session's terminal): `pixi
  run -e local-recipes pr-artifacts 33693` against the real PR; assert
  output lands at `build_artifacts/pr/33693/1536673/extracted/{linux-64,
  osx-64,win-64}/*.conda` and `pr-artifacts.json` is well-formed.

### Wave C

- `tests/unit/test_download_pr_artifacts_mcp.py::test_happy_path_returns_manifest`
  — stub `subprocess.run` to return a fixture manifest JSON; assert MCP
  tool returns the parsed dict with expected keys.
- `tests/unit/test_download_pr_artifacts_mcp.py::test_non_zero_exit_propagates`
  — stub `subprocess.run` to return rc=1 + stderr; assert MCP tool result
  has `errors: [...]` key populated; no exception raised.

### Wave D

- `tests/meta/test_skill_md_consistency.py` — `download_pr_artifacts` now
  appears in `reference/mcp-tools.md`; pr_artifacts.py added to
  `tests/meta/test_all_scripts_runnable.py::SCRIPTS`.
- Manual: `pixi task list -e local-recipes` shows `pr-artifacts` with
  description copy matching this spec's CLI surface.
- Manual: CHANGELOG.md TL;DR entry for v8.14.0 reads correctly when
  rendered as Markdown.

---

## Risks

| Risk | Likelihood | Severity | Mitigation |
|---|---|---|---|
| Azure DevOps REST API changes the `artifacts` shape or `api-version=7.1` deprecates before next session | Low | Med | Pin `api-version=7.1` explicitly; have S2's test cover the response shape so a breaking change surfaces as a test failure not a runtime crash. |
| `gh pr checks` JSON shape evolves; the `link` field renamed | Low | Low | S1's mock-based tests fix the expected schema; CI failure is the canary. Document the gh-CLI version we tested against in S1's docstring. |
| `_http.make_request`'s JFrog header injection leaks credentials to dev.azure.com (unlikely on a public project but a smell) | Med | Low | S2 explicitly passes `auth=False` to bypass the chain; alternatively add host-allowlist short-circuit (track as v8.15 hardening if not done here). |
| Some PRs publish artifacts named differently (e.g. `build_artifacts` instead of `conda_pkgs_*`) when `azure.store_build_artifacts: true` is set per-recipe | Med | Low | S2's regex covers the documented names. Add an `--artifact-pattern` flag in a future v8.15 if real PRs surface a different name. `--all-artifacts` is the v1 escape hatch. |
| Multi-output recipes publish multiple `.conda` per platform; the extract path needs to preserve sub-dirs | High | Low | Already handled — the Azure ZIPs preserve the conda-build subdir layout (`linux-64/foo-1.conda`, `linux-64/foo-2.conda`); the extractor doesn't flatten beyond the top level. S4's extract test covers two-`.conda`-per-platform fixture. |
| Caching false-positive: same buildId re-fetched returns stale bytes after a re-run that reused the ID (Azure normally allocates new IDs but theoretically possible) | Very Low | Low | `--force` is the documented escape. Manifest records `fetched_at` so the user can decide. Not worth defending further. |

---

## Rollout

- **One PR** to staged-recipes-style local skill changes — bundles all 9
  stories. No schema change, no breaking surface, no two-PR split needed.
- **Version**: v8.13.2 → **v8.14.0** (MINOR — net-new feature, additive
  only, no breaking changes to existing flows).
- **Backout plan**: revert the v8.14.0 commit. No data migration, no
  state to roll back, no MCP tool deprecation (it's net-new). `gh pr
  revert` or `git revert` is sufficient.
- **Communication**: CHANGELOG TL;DR is the announcement. No external
  zulip / mailing-list post needed (skill-internal feature).

---

## Open Questions

- **Q1** — Default extract behavior: extract by default vs require
  `--extract` opt-in?
  *Recommendation*: extract by default (CLI default `--extract=True`,
  match MCP). Raw ZIPs are rarely the consumer's goal; the channel
  layout is.
  → **Resolved as recommended unless reviewer objects.**
- **Q2** — Output dir default: `build_artifacts/pr/<pr>/` (under existing
  gitignored tree) vs `pr-artifacts/<pr>/` (new top-level tree)?
  *Recommendation*: `build_artifacts/pr/<pr>/` — already gitignored,
  lives alongside other build outputs, no `.gitignore` change needed.
  → **Resolved as recommended.**
- **Q3** — `--all-runs` behavior on a PR with 5 Azure rebuilds: fetch
  all 5? Filter to succeeded-only?
  *Recommendation*: default to latest run; `--all-runs` fetches every
  distinct buildId regardless of result. User can post-filter on
  manifest `result` field.
  → **Resolved as recommended.**
- **Q4** — Feedstock-PR support depth: full parity (same code path) vs
  staged-recipes-only v1 with feedstock support deferred?
  *Recommendation*: full parity. The check-name auto-detect is one regex
  difference. Cost ~0 in S1; deferring would require a follow-up spec.
  → **Resolved as recommended.**
- **Q5** — Auto-install into local mamba channel + smoke-test?
  *Recommendation*: out of scope for v1. Add as v8.15 follow-up only if
  manual `mamba install -c file://...` proves cumbersome. The channel
  layout is already valid.
  → **Resolved as out of scope.**
- **Q6** — Skip-existing cache vs always re-fetch?
  *Recommendation*: skip-existing by default (idempotency is the v1
  default); `--force` overrides. Manifest `fetched_at` lets the user
  decide when stale.
  → **Resolved as recommended.**
- **Q7** — Artifact name filtering: `conda_pkgs_*` only by default vs
  all artifacts?
  *Recommendation*: filter to `conda_pkgs_*` by default; `--all-artifacts`
  opens the floodgates (logs, `_build_artifacts.json`, etc.).
  → **Resolved as recommended.**
- **Q8** — Where does the new CLI's PR-resolution helper live? Standalone
  in `pr_artifacts.py` or extracted into `_pr_resolver.py` for re-use
  by future MCP tools (e.g. a `summarize_pr_checks` analog)?
  *Recommendation*: standalone in `pr_artifacts.py` for v1. Extract only
  if a second caller materialises. Premature abstraction otherwise.
  → **Resolved as recommended.**

---

## References

- `docs/specs/conda-forge-expert-v8.0.md` — last MINOR-bump feature spec; template for the format used here.
- `.claude/skills/conda-forge-expert/CHANGELOG.md` v8.13.2 entry — `recipe-build-cross` precedent; the inverse of this feature's problem (cross-build locally vs fetch CI's build).
- `.claude/skills/conda-forge-expert/reference/conda-forge-yml-reference.md` § "Top use cases" → `azure.store_build_artifacts: true` — the upstream opt-in this skill consumes.
- `.claude/skills/conda-forge-expert/reference/mcp-tools.md` — pattern for FastMCP tool documentation.
- `.claude/scripts/conda-forge-expert/native-build.sh`, `.claude/scripts/conda-forge-expert/cross-build.sh` — entrypoint-wrapper convention; new wrapper follows the same shape.
- `.claude/skills/conda-forge-expert/tests/meta/test_all_scripts_runnable.py` — meta-test that enforces SCRIPTS list updates.
- `.claude/skills/conda-forge-expert/tests/meta/test_skill_md_consistency.py` — meta-test that enforces pixi-task wiring + SKILL.md script-reference correctness.
- Azure DevOps Build Artifacts REST API: <https://learn.microsoft.com/en-us/rest/api/azure/devops/build/artifacts/list>.
- Live case study: <https://github.com/conda-forge/staged-recipes/pull/33693> (buildId 1536673).

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

<a id="p10"></a>

# Part 10 — graphifyy osx-arm64 fanout — 22 tree-sitter-* platform PRs (closed effort)

> Formerly `graphifyy-osx-arm64-fanout.md` — shipped effort closed 2026-06-17.
> Original frontmatter: `doc_type: spec; status: shipped; implemented_by: bmad-quick-dev; shipped_ref: "effort closed 2026-06-17"; spec_updated: 2026-06-20`

# Tech Spec: graphifyy installable on osx-arm64 (22-feedstock fanout)

> Fanout effort: land **22 platform-expansion PRs** (15 Cat-3 net-new
> + 7 Cat-2 uplift) across the
> tree-sitter language-binding feedstocks so that `graphifyy` (which is
> `noarch: python`) resolves and installs on osx-arm64. Each PR matches
> `sumanth-manchala`'s 2026-06-07 pattern in
> `conda-forge/tree-sitter-javascript-feedstock#1`: a `conda-forge.yml`
> `provider:` addition + rerender, scoped to `osx-arm64` + `linux-aarch64`.
> Each PR is gated behind a maintainer-add issue (the killua156/mgorny
> recipe-maintainer pair owns all 22 affected feedstocks).
>
> **BMAD intake document.** Written for `bmad-quick-dev` (Quick Flow
> track, fanout variant). ~3 stories per feedstock × 15 feedstocks +
> 3 orchestration stories = ~48 stories grouped in 5 waves. Run BMAD with
> this file as the intent document; the per-feedstock work is delegated
> to [`docs/specs/feedstock-platform-expansion.md`](feedstock-platform-expansion.md)
> with `target_platforms=osx_arm64,linux_aarch64` and the feedstock name
> taken from the per-row table in Wave B below.
>
> **Per CLAUDE.md Rule 1**, any BMAD agent executing this spec MUST
> invoke the `conda-forge-expert` skill before touching recipe code or
> running recipe tooling. Per Rule 2, the effort closes with a single
> consolidated CFE-skill retrospective and a `CHANGELOG.md` entry
> covering all 22 PRs (fanout retros consolidate; they do not produce
> 22 separate entries).

---

## Status


| Field        | Value                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Status       | **🎉 CLOSED 2026-06-17 03:25Z**. 22 platform-expansion PRs + 8 canonical-conda-forge.yml sweep + tree-sitter-swift dist-info fix + graphifyy v0.8.40 PR #8 (merged `fa094fa`) all shipped in a single ~16h session. Wave D smoke-test PASS: dry-run solve of graphifyy on osx-arm64 returned a complete plan (62 pkgs / 71 MB, all 22 tree-sitter-* deps at osx-arm64 builds). Closeout retro shipped as CFE v8.26.0 (G23 + G24 + DEP-002 sub-rule). S-F4 follow-ups: 3 draft PRs OPEN on staged-recipes (2026-06-17) — [#33752 falkordb](https://github.com/conda-forge/staged-recipes/pull/33752) (win_64 ❌), [#33753 ctranslate2-suite](https://github.com/conda-forge/staged-recipes/pull/33753), [#33754 faster-whisper](https://github.com/conda-forge/staged-recipes/pull/33754) (gated on #33753). |
| Owner        | rxm7706                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| Track        | BMAD Quick Flow (fanout — 22 single-feedstock cycles [15 Cat-3 + 7 Cat-2] + orchestration)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| Surface area | 22 conda-forge tree-sitter-* feedstocks; 22 maintainer-add issues + 22 platform-expansion PRs (15 Cat-3 net-new + 7 Cat-2 uplift); watch policy on the 7 in-flight PRs by`sumanth-manchala`; **no** code changes to `.claude/skills/conda-forge-expert/` (skill-internal work limited to closeout retro per Rule 2)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| Scope        | (1) Open a`@conda-forge-admin, please add user @rxm7706` issue on each of 22 affected feedstocks (15 Cat-3 + 7 Cat-2; see audit table). (2) Per Cat-3 feedstock, sync local mirror → edit `conda-forge.yml` → rerender → open DRAFT PR adding `osx_arm64` + `linux_aarch64` provider blocks. (3) Watch the 7 Cat-2 PRs by `sumanth-manchala`; after 14 days idle, open a competing PR with the same scope. (4) After all 22 PRs merge, verify `mamba install graphifyy` resolves on osx-arm64 via repodata grep. (5) One consolidated CFE-skill retro at closeout.                                                                                                                                                                                                                                        |
| Out of scope | Adding`win-arm64`. **Scope update 2026-06-16**: touching `conda-forge/graphifyy-feedstock` was originally out-of-scope ("already noarch and needs no change — the fix is in its deps") but is now in scope per Wave F § S-F1–S-F4 — driven by mid-session v0.8.10 → v0.8.40 upstream advance + 19 optional-extras enablement. Version bumps on any of the 15 feedstocks. Recipe-code changes beyond a `conda-forge.yml` block + rerender artifacts. Auto-merging any PR. **Scope update 2026-06-16**: `linux-ppc64le` was originally ruled out but has been brought back in scope after Cat-2 validated the hybrid native (linux_aarch64 + osx_arm64) + cross-compile (linux_ppc64le: linux_64) pattern. Cat-3 PRs now target osx-arm64 + linux-aarch64 + linux-ppc64le.                                |
| Created      | 2026-06-15                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| Driven by    | `graphifyy` not installable on osx-arm64. Confirmed empirically 2026-06-15: of 26 tree-sitter-* run-deps + 3 transitive Python deps, only 4 tree-sitter-* + all 3 Python deps ship osx-arm64; 7 are in-flight via `sumanth-manchala`, 15 have no PR yet.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| Predecessor  | `docs/specs/feedstock-platform-expansion.md` (the per-feedstock workflow this spec invokes 15×); `conda-forge/tree-sitter-javascript-feedstock#1` (the canonical PR diff to copy)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |

---

## Background and Context

### The problem

`graphifyy` is `noarch: python` and consumes 26 `tree-sitter-*` language
bindings + 3 transitive Python deps (`networkx`, `datasketch`,
`rapidfuzz`) at runtime. Conda's solver refuses to install a package on
a subdir where any run-dep is missing — so the gap is not in
`graphifyy` itself but in its dep coverage. Confirmed empirically
2026-06-15 against `conda.anaconda.org/conda-forge/osx-arm64/repodata.json`:

```
osx-arm64 coverage of graphifyy 0.8.10 deps:
  ✅ 7 ship: networkx, datasketch, rapidfuzz, tree-sitter (core),
                  tree-sitter-python, tree-sitter-c-sharp, tree-sitter-bash
  🟡 7 in-flight (sumanth-manchala 2026-06-07 PRs): javascript, go, groovy,
                  c, cpp, elixir, fortran
  ❌ 15 missing, no PR yet: typescript, rust, java, ruby, kotlin, scala,
                  php, swift, lua, zig, powershell, objc, julia, verilog, json
  ✅ 1 shipped this session (tree-sitter-markdown — v0.5.3 + platform
                  expansion merged 2026-06-16 22:12Z, SHA `1d7b45b`)
```

**Addendum 2026-06-16**: tree-sitter-markdown was added to Cat-3 as
the 16th feedstock and shipped same-day via PR #5 (v0.5.3 patch +
platform expansion combined) — counted as DONE in the totals above.
Backstory: Wave B would have been the natural home for it, but the
upstream v0.5.3 was a working bot-update blocker (broken setup.py
expected flat `src/parser.c` against the dual-grammar subdirectory
tarball layout — see CFE SKILL.md G5 sibling case). The closeout was:
(1) close stale autotick PR #1; (2) open PR #4 with
`bot.version_updates.exclude: [0.5.2, 0.5.3]` as a safety belt;
(3) author setup.py patch + open PR #5 (v0.5.3 + patch);
(4) operator extended PR #5 with the platform-expansion conda-forge.yml
(canonical hybrid pattern) before merging; (5) close PR #4 as
redundant. So tree-sitter-markdown is functionally done — no Wave B
work needed.

Every one of the 15 missing-without-PR feedstocks shares the same
recipe shape (verified by spot-check):
`schema_version: 1` + `compiler("c") + stdlib("c")` + `python-abi3` host

+ `version_independent: ${{ is_abi3 }}` + `abi3audit` test. Their
  `conda-forge.yml` is bare. The platform-expansion diff is the cookie-cutter
  `provider:` block from
  `conda-forge/tree-sitter-javascript-feedstock#1` — no per-recipe
  customization needed.

All 22 affected feedstocks (Cat-2 + Cat-3) have **identical** recipe
maintainers: `killua156, mgorny`. Because the user has elected a
maintainer-add-before-recipe-PR gate (matching the pattern of
`conda-forge/tree-sitter-javascript-feedstock#2`, opened by `rxm7706`
2026-06-15 with title `@conda-forge-admin, please add user @rxm7706`),
every recipe PR is preceded by an issue opening that request.

### What's been ruled out

- ~~**Adding `linux-ppc64le`.**~~ **RESOLVED 2026-06-16 — ppc64le is
  back in scope** after Cat-2 PRs validated the hybrid pattern
  (`provider: linux_aarch64+osx_arm64: default` + `build_platform: linux_ppc64le: linux_64` cross-compile). The original concern was
  transitive C-dep coverage on conda-forge in mid-2026; the actual
  conda-forge.yml pattern uses x86_64 toolchain to cross-compile for
  ppc64le, so transitive coverage on ppc64le itself isn't needed.
  Cat-2 PRs (including the 6 we uplifted) all shipped ppc64le builds
  green. Cat-3 PRs use the same shape.
- **Touching the `graphifyy-feedstock` recipe itself.** It's already
  `noarch: python` at v0.8.10. The fix is entirely in its deps. No
  change to `recipes/graphify/` or to `conda-forge/graphifyy-feedstock`
  in this effort.
- **A maintainer-add request to the conda-forge core team rather than
  the per-feedstock owners.** Per conda-forge convention, the
  `@conda-forge-admin, please add user @X` issue is the canonical
  mechanism — the existing maintainer(s) approve or reject inline; the
  bot performs the team-add on approval. We follow that pattern.
- **Opening 22 simultaneous PRs as a sympathy/co-pressure tactic on the
  existing 2-maintainer pair.** The fanout proceeds in batches of 5 to
  give `killua156`/`mgorny` reasonable review bandwidth and a chance to
  push back before the full batch ships.
- **Squashing the 15 PRs into a single conda-forge org-level PR.** No
  such mechanism exists — conda-forge feedstocks are independent
  repositories. Each platform expansion is a per-feedstock PR.

### What's available to leverage

- **`conda-forge/tree-sitter-javascript-feedstock#1`** — sumanth's
  canonical diff. Copy `conda-forge.yml` provider-block edits verbatim.
- **`docs/specs/feedstock-platform-expansion.md`** — the parameterized
  per-feedstock workflow. This spec invokes it 15× with
  `target_platforms=osx_arm64,linux_aarch64` and
  `recipe_shape=compiled`. Per-feedstock procedural detail (S1–S13)
  lives there; this spec adds only the orchestration.
- **The empirical 2026-06-15 audit** — pre-computed per-category
  classification in § Empirical state below. No need to re-audit at
  intake.
- **The maintainer-add issue template** — title `@conda-forge-admin, please add user @rxm7706`, body `### Additional comment:` with no
  response (per the `tree-sitter-javascript-feedstock#2` template).
  Single `gh issue create` per feedstock.

### Empirical state (verified 2026-06-15)

graphifyy-feedstock: v0.8.10, noarch:python, maintainers killua156+mgorny
graphifyy run-deps:    29 total (26 tree-sitter-* + networkx + datasketch + rapidfuzz)
graphifyy osx-arm64:   blocked — 22 of 29 deps not yet on osx-arm64

Per-dep status (sorted by category):

[Cat 1 — already ships osx-arm64, NO ACTION (7)]
networkx                noarch:python
datasketch              noarch:python
rapidfuzz               native osx-arm64 build present
tree-sitter (core lib)  osx-arm64 build present
tree-sitter-python      osx-arm64 build present
tree-sitter-c-sharp     osx-arm64 build present
tree-sitter-bash        osx-arm64 build present

[Cat 2 — IN-FLIGHT PR by sumanth-manchala (2026-06-07), watch only (7)]
tree-sitter-javascript   PR #1 — adds osx-arm64 + linux-aarch64 + ppc64le
tree-sitter-go           PR #1 — same scope
tree-sitter-groovy       PR #2 — same scope
tree-sitter-c            PR #1 — same scope
tree-sitter-cpp          PR #1 — same scope
tree-sitter-elixir       PR #1 — same scope
tree-sitter-fortran      PR #2 — same scope

[Cat 3 — NO PR YET, our work (15)]
Each is the same abi3 Python C-extension shape. Each gets a
maintainer-add issue first, then a platform-expansion PR scoped to
osx-arm64 + linux-aarch64 + ppc64le

tree-sitter-typescript    maintainers: killua156, mgorny
tree-sitter-rust          maintainers: killua156, mgorny
tree-sitter-java          maintainers: killua156, mgorny
tree-sitter-ruby          maintainers: killua156, mgorny
tree-sitter-kotlin        maintainers: killua156, mgorny
tree-sitter-scala         maintainers: killua156, mgorny
tree-sitter-php           maintainers: killua156, mgorny
tree-sitter-swift         maintainers: killua156, mgorny
tree-sitter-lua           maintainers: killua156, mgorny
tree-sitter-zig           maintainers: killua156, mgorny
tree-sitter-powershell    maintainers: killua156, mgorny
tree-sitter-objc          maintainers: killua156, mgorny
tree-sitter-julia         maintainers: killua156, mgorny
tree-sitter-verilog       maintainers: killua156, mgorny
tree-sitter-java          maintainers: killua156, mgorny
tree-sitter-markdown      maintainers: killua156, mgorny

→ Total work: **15 maintainer-add issues + 15 platform-expansion PRs**
on Cat-3 feedstocks; plus **7 maintainer-add issues** on Cat-2
feedstocks (so we're in a position to take over if sumanth's PR
stalls); plus **watch policy** on the 7 Cat-2 PRs with a 14-day idle
takeover trigger.

---

## Goals

1. **`mamba install graphifyy` succeeds on osx-arm64.** First-class
   acceptance — verified by Wave D smoke-test after all 22 PRs merge.
2. **15 net-new conda-forge PRs opened** adding `osx_arm64` +
   `linux_aarch64` to each Cat-3 feedstock. One PR per feedstock; no
   bundling across feedstocks (impossible — they're separate
   repositories).
3. **22 maintainer-add issues opened** (15 Cat-3 + 7 Cat-2). The Cat-2
   issues exist so the 14-day takeover policy can execute without an
   extra issue round-trip if needed.
4. **No structural recipe change** on any of the 15 Cat-3 feedstocks
   beyond `conda-forge.yml` provider blocks + standard rerender
   artifacts. Any feedstock requiring deeper changes triggers
   Stop-the-Line per the per-feedstock guide.
5. **Scope match with `sumanth-manchala`'s in-flight PRs**:
   osx-arm64 + linux-aarch64 + linux-ppc64le. Updated 2026-06-16 —
   ppc64le added to scope after Cat-2 validated the hybrid pattern
   (native aarch64+osx_arm64 + cross-compile ppc64le via
   `build_platform: linux_ppc64le: linux_64`).
6. **14-day takeover policy** on Cat-2 PRs (now moot — all 7 Cat-2
   PRs merged 2026-06-16 within ~2 hours of the native+cross uplift,
   no takeovers triggered). Original text retained for record: "if a
   sumanth PR has had no commits, no maintainer comments, and no CI
   runs for 14 calendar days, we open a competing PR with our scope.
   The competing PR credits sumanth in the body and is opened as DRAFT."
7. **One consolidated CFE-skill retro** at closeout — fanout retros
   consolidate findings; they do not produce 15 separate CHANGELOG
   entries.

---

## Five load-bearing workflow rules (apply to every story)

These five rules govern the whole fanout. The first inherits from
`feedstock-platform-expansion.md`; rules 2–5 are fanout-specific.

- **Bump `build.number` on every feedstock-PR-update at the same
  upstream version.** When a feedstock PR changes recipe shape OR
  `conda-forge.yml` shape OR rerender output on the same upstream
  version (no version bump), `recipe/recipe.yaml`'s `build.number`
  MUST increment to supersede main's currently-shipping artifacts. A
  rebase onto main resets the number to main's value (typically 0 for
  the first release); the post-rebase commit must re-bump. Forgetting
  this means the conda solver keeps preferring main's `*_0` artifacts
  over our `*_0` rebuild — solver tie-break is timestamp-on-channel,
  not local merge order, so reviewers won't catch it during PR review
  but users will install the stale build. Applies to every Cat-2 PR
  rebase + every Cat-3 PR opened in Wave B + any subsequent edit-cycle
  after the initial build.number bump (each subsequent edit cycle
  bumps again, e.g. 1 → 2 → 3 as we iterate on review feedback).
- **Every push to a feedstock PR branch is followed immediately by
  `@conda-forge-admin, please rerender`.** No judgment calls about
  "this change doesn't need a rerender" — `build.number` bumps,
  whitespace fixes, README edits, anything pushed to a feedstock PR
  gets the rerender comment. The rerender bot is idempotent and
  fast; running it unconditionally is correct. The cost of always
  commenting is zero; the cost of skipping leaves the next
  operator/reviewer wondering why some pushes get rerenders and
  others don't, and gives the auto-rerender service a chance to fire
  on its own variable timing instead of the explicit-request fast
  path. See `feedback_always_request_rerender_after_feedstock_push.md`.
- **Local mirror is the source of truth, and the mirror must be
  COMPLETE.** Per `feedstock-platform-expansion.md` § "Two load-bearing
  workflow rules": for every Cat-3 feedstock, `recipes/<feedstock>/`
  mirrors the full feedstock state (recipe.yaml + conda-forge.yml +
  LICENSE + patches + build.sh/.bat). Edit in the mirror first;
  verify-build local; mirror to fork; push; request rerender. Not
  optional.
- **Maintainer-add issue gates every recipe PR on that feedstock.**
  Per the user-set policy: because every Cat-3 feedstock's maintainers
  include `killua156` or `mgorny`, we open the `@conda-forge-admin, please add user @rxm7706` issue FIRST. The recipe PR opens only after
  one of: (a) the bot has team-added `rxm7706` (typical resolution
  time: same day), OR (b) 48 hours have passed with no objection on
  the issue (per conda-forge convention — silence implies consent for
  maintainer-adds on inactive feedstocks). The recipe PR body cites
  the maintainer-add issue number.
- **14-day takeover policy for in-flight PRs.** Cat-2 PRs are watched,
  not duplicated. We open a competing PR only when ALL THREE conditions
  hold for that PR: (1) no new commits to the head branch in 14
  calendar days, (2) no maintainer comments in 14 calendar days, (3)
  CI is not currently running. The competing PR is opened DRAFT,
  scoped to osx-arm64 + linux-aarch64 only, credits sumanth in the
  body, and references the original PR number. We do NOT close
  sumanth's PR — that's the maintainer's call.

---

## Stories — Wave A: Maintainer-add issues (22 feedstocks, fast)

Goal: open the maintainer-add issue on every Cat-2 + Cat-3 feedstock
in a single batch. These are cheap (`gh issue create` per feedstock)
and front-load the bot's team-add latency so it doesn't gate Wave B.

### S-A1. Open 15 maintainer-add issues on Cat-3 feedstocks

For each Cat-3 feedstock:

```
gh issue create \
  --repo conda-forge/<feedstock>-feedstock \
  --title "@conda-forge-admin, please add user @rxm7706" \
  --body $'### Additional comment:\n\n_No response_'
```

The title is exactly the conda-forge-admin command; no body content
required (the bot ignores it). Match the template at
`https://github.com/conda-forge/tree-sitter-javascript-feedstock/issues/2`
verbatim.

**Acceptance**: 15 issues created, one per Cat-3 feedstock. Each
returns a URL; record the issue numbers in the per-feedstock tracking
table at the bottom of this spec (Wave E populates it).

### S-A2. Open 7 maintainer-add issues on Cat-2 feedstocks

Same template, same call, but on the 7 Cat-2 feedstocks. Rationale:
even if we never need to take over sumanth's PR, having maintainer
access lets us merge cleanly when the bot processes the
team-add. If we DO need to take over, no extra issue round-trip is
needed.

**Acceptance**: 7 additional issues created. Total of 22 open
maintainer-add issues across both categories.

### S-A3. Operator-confirm checkpoint before Wave B begins

**HALT** — present to operator:

- 22 issue URLs (one block of 15 Cat-3, one block of 7 Cat-2)
- Any issue where the maintainer pair has already commented (positive
  or negative) within the first hour
- The list of feedstocks where the bot has already team-added
  `rxm7706` (visible via `gh api orgs/conda-forge/teams/<feedstock>/members`)

Operator confirms before Wave B begins. Per CLAUDE.md "Executing
actions with care", opening 15 PRs against a 2-maintainer pair is
visibly batched activity — operator gates the cadence.

**Acceptance**: explicit operator approval to begin Wave B (or
redirect — e.g., "wait 48h for the bot to process the team-adds
before opening any PR").

---

## Stories — Wave B: Cat-3 platform-expansion PRs (15 PRs, 3 batches of 5)

Goal: open the 15 platform-expansion PRs in 3 batches of 5, with an
operator checkpoint between batches. Per-feedstock procedural detail
is delegated to `docs/specs/feedstock-platform-expansion.md`
S1–S12; this spec sets only the parameters and the cadence.

### S-B1. Configure per-feedstock invocation parameters

Each of the 15 Cat-3 feedstocks gets a `feedstock-platform-expansion.md`
invocation with these constants:


| Parameter                 | Value                                                                                                 |
| ------------------------- | ----------------------------------------------------------------------------------------------------- |
| `target_platforms`        | `osx_arm64`, `linux_aarch64`, `linux_ppc64le`                                                         |
| `recipe_shape`            | `compiled` (15 of 16 are abi3 Python C-extensions; markdown TBD)                                      |
| `fork_owner`              | `rxm7706`                                                                                             |
| `branch_name`             | `add-osx-arm64-linux-aarch64-ppc64le`                                                                 |
| `local_test_subdir`       | `linux-64` (operator host)                                                                            |
| Maintainer-add issue gate | YES — cite the S-A1 issue number in the PR body                                                      |
| ppc64le?                  | YES — cross-compile via`build_platform: linux_ppc64le: linux_64` (hybrid pattern validated on Cat-2) |
| conda-forge.yml pattern   | Full canonical block — see § "Canonical conda-forge.yml for Wave B Cat-3 PRs" below                 |
| PR state on open          | DRAFT                                                                                                 |

### Canonical conda-forge.yml for Wave B Cat-3 PRs

Use this exact shape on every Wave B platform-expansion PR. Updated
2026-06-16 — supersedes the simpler "just provider+build_platform+test"
template used on the Cat-2 PRs and the earlier tree-sitter-markdown PR
drafts. Includes the canonical `bot:` block for grayskull-driven
autotick + solvability checks + wheel-derived run-deps, plus the
modern `conda_install_tool: pixi`.

```yaml
conda_install_tool: pixi
conda_build_tool: rattler-build
github:
  branch_name: main
  tooling_branch_name: main
conda_build:
  error_overlinking: true
conda_forge_output_validation: true
provider:
  linux_aarch64: default
  osx_arm64: default
build_platform:
  linux_ppc64le: linux_64
test: native_and_emulated
bot:
  automerge: true
  inspection: update-grayskull
  check_solvable: true
  run_deps_from_wheel: true
```

**Why each key:**

- `conda_install_tool: pixi` — canonical 2026 companion to rattler-build (faster than micromamba; matches conda-forge's standardization).
- `bot.automerge: true` — version-bump PRs that pass CI green merge automatically.
- `bot.inspection: update-grayskull` — autotick re-runs grayskull against the new upstream to refresh recipe shape, not just version+sha256. Catches upstream dep/metadata changes.
- `bot.check_solvable: true` — dep-solvability check before opening; broken PRs never reach the queue.
- `bot.run_deps_from_wheel: true` — extract run-deps from upstream's wheel metadata (more accurate than pyproject.toml for some packages).

**Pre-existing `bot:` keys**: if a feedstock's main already has a `bot:` block (e.g., `bot.version_updates.exclude` for skipped broken upstream versions), MERGE the new keys with the existing ones — don't overwrite.

Per-feedstock substitutions for `feedstock` and `upstream_version` are
populated from a `gh api` sweep at batch start (versions change between
audit and execution; do not hardcode).

**Acceptance**: a per-feedstock parameter table is materialized as
section "Per-feedstock invocation table" at the bottom of this spec.

### S-B2. Batch 1 — open PRs on 5 Cat-3 feedstocks

Recommended batch (alphabetical, no per-feedstock dependency):

```
tree-sitter-java
tree-sitter-json
tree-sitter-julia
tree-sitter-kotlin
tree-sitter-lua
```

For each: invoke `feedstock-platform-expansion.md` S1–S11 per the
per-feedstock parameter table from S-B1. All 5 PRs open as DRAFT.

**Acceptance**: 5 draft PR URLs returned. Each PR body cites the
matching S-A1 maintainer-add issue. Each PR's `conda-forge.yml` delta
is the 2-line provider block (`osx_arm64: default` +
`linux_aarch64: default`) plus rerender artifacts. No recipe-code
edits.

### S-B3. Operator-confirm checkpoint between Batch 1 and Batch 2

**HALT** — present to operator:

- 5 PR URLs
- CI status on each (`gh pr checks <PR>`)
- Any maintainer comments on the 5 PRs OR the matching S-A1 issues
- The diff size of each PR's `.ci_support/` regeneration

Operator confirms before Batch 2 ships. If `killua156` or `mgorny` has
pushed back on any of the 5 PRs (or any of the open S-A1 issues),
operator decides whether to pause the remaining 10 PRs and re-engage
the maintainers.

**Acceptance**: explicit operator approval to ship Batch 2 (or
redirect).

### S-B4. Batch 2 — open PRs on 5 more Cat-3 feedstocks

Recommended batch:

```
tree-sitter-objc
tree-sitter-php
tree-sitter-powershell
tree-sitter-ruby
tree-sitter-rust
```

Same procedure as S-B2.

**Acceptance**: 5 more draft PR URLs, same shape as Batch 1.

### S-B5. Operator-confirm checkpoint between Batch 2 and Batch 3

Same shape as S-B3. **HALT** — present 10-PR aggregate status,
confirm.

**Acceptance**: explicit operator approval to ship Batch 3.

### S-B6. Batch 3 — open PRs on the final 5 Cat-3 feedstocks

```
tree-sitter-scala
tree-sitter-swift
tree-sitter-typescript
tree-sitter-verilog
tree-sitter-zig
```

Same procedure.

**Acceptance**: 5 more draft PR URLs. Total: 15 Cat-3 draft PRs open.

### S-B7. Per-PR draft → ready-for-review transitions

For each of the 16 PRs, when CI is green on all 6 legs
(linux-64 + osx-64 + win-64 existing + osx-arm64 + linux-aarch64 native +
linux-ppc64le cross-compiled new), operator flips draft → ready via
`gh pr ready <PR>`. Per `feedstock-platform-expansion.md` S12, this is
per-PR and per-operator-gate.

**Acceptance**: each PR transitions DRAFT → READY → MERGED. Track
state per-feedstock in the Worked Example table.

---

## Stories — Wave C: Watch + native-runner uplift on Cat-2 PRs

Goal: track sumanth's 7 in-flight PRs; **proactively uplift the 6 still-emulation PRs to the native-runner pattern** that sumanth already applied to PR #1 on tree-sitter-javascript; take over only on 14-day idle.

### Scope expansion 2026-06-16 — native-runner uplift on Cat-2 PRs

**CORRECTION 2026-06-16 11:38Z** (per mgorny review on
`conda-forge/tree-sitter-javascript-feedstock#1`):
**`linux_ppc64le` is NOT natively supported on conda-forge.** Only
`linux_aarch64` and `osx_arm64` are first-class native runners. The
correct pattern for ppc64le is cross-compile via `build_platform: linux_ppc64le: linux_64` (emulated test run via QEMU on the
linux-anvil-x86_64:alma9 docker image, with `test: native_and_emulated`
exercising the actual ppc64le binary under emulation). An earlier
draft of this spec treated ppc64le as native — it is not.

**Canonical hybrid pattern** (matches latest javascript PR #1 head after
mgorny review):

```yaml
# conda-forge.yml
provider:
  linux_aarch64: default      # native aarch64 runner (linux-anvil-aarch64:alma9)
  osx_arm64: default          # native arm64 runner (macOS-15-arm64)
build_platform:
  linux_ppc64le: linux_64     # cross-compile from x86_64 (no native ppc64le runner)
test: native_and_emulated     # ppc64le test exercises the binary under QEMU emulation
```

```yaml
# recipe.yaml — simplified requirements.build (no cross-python conditional)
requirements:
  build:
    - ${{ compiler("c") }}
    - ${{ stdlib("c") }}
```

Sumanth dropped the `if: build_platform != target_platform / then: python

+ cross-python_${{ target_platform }}`conditional block from`requirements.build `(see his commit`f4efd05 `"Remove cross python deps"). The cross-compile still works because conda-smithy rerender injects the cross-python toolchain at the`.ci_support/*.yaml `level; the recipe doesn't need to declare it. Removing the block keeps the recipe simpler and matches the abi3 + version_independent pattern's intent — the abi3 stub`python-abi3` in host carries the ABI marker
  without needing a full target-platform Python in build.

Empirical baseline (verified 2026-06-16):


| Cat-2 PR                                                      | linux_aarch64                    | linux_ppc64le                                  | osx_arm64                        | Status                           |
| ------------------------------------------------------------- | -------------------------------- | ---------------------------------------------- | -------------------------------- | -------------------------------- |
| **tree-sitter-javascript #1** (canonical, post-mgorny-review) | **NATIVE** (`provider: default`) | **CROSS-COMPILE** (`build_platform: linux_64`) | **NATIVE** (`provider: default`) | Latest pattern                   |
| tree-sitter-go #1 (our 2026-06-16 push — pre-correction)     | NATIVE                           | (incorrectly) NATIVE                           | NATIVE                           | Needs ppc64le→cross-compile fix |
| tree-sitter-groovy #2                                         | emulation under linux_64         | emulation under linux_64                       | NATIVE                           | Needs aarch64 uplift             |
| tree-sitter-c #1                                              | emulation under linux_64         | emulation under linux_64                       | NATIVE                           | Needs aarch64 uplift             |
| tree-sitter-cpp #1                                            | emulation under linux_64         | emulation under linux_64                       | NATIVE                           | Needs aarch64 uplift             |
| tree-sitter-elixir #1                                         | emulation under linux_64         | emulation under linux_64                       | NATIVE                           | Needs aarch64 uplift             |
| tree-sitter-fortran #2                                        | emulation under linux_64         | emulation under linux_64                       | NATIVE                           | Needs aarch64 uplift             |

The aarch64 portion of the uplift gives true platform fidelity testing

+ faster CI (no QEMU). The ppc64le portion stays at cross-compile —
  the win there is faster CI (linux-anvil-x86_64 is faster than the
  cross-compile-onto-x86_64-then-emulate-test cycle currently used; the
  build_platform: linux_64 pattern skips the cross-compile-prep overhead
  because it just uses the x86_64 toolchain directly with target_platform
  set in the variant).

Because rxm7706 was team-added 2026-06-16, we now have direct push access to all 7 Cat-2 feedstocks. All 7 Cat-2 PRs have `maintainerCanModify: true`, so we can also push commits directly to sumanth's PR branches.

**Approach**: edit `conda-forge.yml` per Cat-2 PR to the hybrid
native+cross pattern (above), simplify `requirements.build` to drop the
cross-python conditional, then rerender via `@conda-forge-admin, please rerender`. Match the tree-sitter-javascript post-mgorny-review pattern
exactly.

### S-C0. Test the uplift on tree-sitter-go first

Before fanning out the uplift to the other 5, validate end-to-end on tree-sitter-go #1:

1. **Mirror sumanth's branch into `recipes/tree-sitter-go/`** (full feedstock state — `recipe/`, `conda-forge.yml`, etc.). Per `feedback_local_mirror_first_then_verify_then_push.md`.
2. **Edit `recipes/tree-sitter-go/conda-forge.yml`** to the hybrid pattern (above): `provider: linux_aarch64+osx_arm64: default`, `build_platform: linux_ppc64le: linux_64`, `test: native_and_emulated`.
3. **Edit `recipes/tree-sitter-go/recipe.yaml`** to drop the `if: build_platform != target_platform / then: python + cross-python_${{ target_platform }}` block from `requirements.build` (match javascript's simplified shape).
4. **Push to `sumanth-manchala:osx-arm64`** (the PR's head branch) — we have `maintainerCanModify: true`.
5. **Comment on PR #1**: `@conda-forge-admin, please rerender`. Per saved feedback, the comment is terse — no preamble or credit prose. Credit lives in commit trailers.
6. **Watch CI**: linux_aarch64 (native) + linux_ppc64le (cross-compiled) + osx_arm64 (native) + linux_64 + osx_64 + win_64 must all go green. If any leg fails, debug per `feedstock-platform-expansion.md` and the CFE Build Failure Protocol.
7. **Operator-confirm HALT** before fanning out to the remaining 5 Cat-2 PRs.

**Acceptance**: tree-sitter-go #1 ships the hybrid native+cross pattern; rerender lands clean; all 6 CI legs go green. Operator confirms the pattern works before applying to the rest.

**Historical note 2026-06-16**: an earlier iteration of this story
pushed `provider: linux_ppc64le: default` to tree-sitter-go #1 and CI
went green on all 6 legs (build artifact `tree-sitter-go-0.25.0-py310h541078d_1.conda`
68.40 KiB on linux-ppc64le). Mgorny's review on tree-sitter-javascript
clarified that ppc64le-native is not actually a thing on conda-forge —
the "native" anvil-ppc64le docker image still runs on x86_64 hardware
with QEMU emulation underneath. The `build_platform: linux_ppc64le: linux_64` pattern is faster because it skips the cross-compile-prep
overhead and just uses the x86_64 toolchain with `target_platform: linux-ppc64le` set in the variant. The fix to tree-sitter-go after the
mgorny review applies S-C0 as written.

### S-C0b. Fan out the uplift to the remaining 5 Cat-2 PRs

Once S-C0 confirms the pattern, apply the same edit to: tree-sitter-groovy, tree-sitter-c, tree-sitter-cpp, tree-sitter-elixir, tree-sitter-fortran. One commit per PR, same shape. Rerender each via `@conda-forge-admin, please rerender`.

**Acceptance**: all 6 remaining Cat-2 PRs carry the native-runner pattern; all 6 PRs' CI goes green on linux_aarch64 + linux_ppc64le + osx_arm64.

### S-C1. Materialize the Cat-2 watch table

For each of the 7 Cat-2 PRs:

```
gh pr view <PR> --repo conda-forge/<feedstock>-feedstock \
  --json number,state,updatedAt,statusCheckRollup,headRefOid
```

Capture the per-PR head SHA, last update timestamp, CI status.
Materialize as section "Cat-2 watch table" at the bottom of this spec.

**Acceptance**: 7-row watch table populated with first observation.

### S-C2. Refresh the watch table every 7 days

A `bmad-quick-dev` or cron-style runner (operator decision per § Open
Questions Q4) re-runs S-C1 every 7 days. The refresh is read-only.

**Acceptance**: watch table carries a timestamped row per refresh.

### S-C3. Trigger takeover when 14-day idle conditions hold

For each Cat-2 PR, takeover triggers when ALL THREE conditions hold:

- No new commit to the head branch in 14 calendar days
  (`headRefOid` unchanged across two consecutive 7-day refreshes).
- No maintainer comment in 14 calendar days
  (`gh pr view <PR> --json comments --jq '.comments[] | select(.author.login == "killua156" or .author.login == "mgorny") | .createdAt'` returns nothing within window).
- CI is not currently running
  (`statusCheckRollup` status is `COMPLETED` or empty, not `IN_PROGRESS`).

If ALL three hold, open a competing DRAFT PR with the same
`feedstock-platform-expansion.md` invocation as Wave B, scoped to
osx-arm64 + linux-aarch64 only. The competing PR body **must** include:

> Friendly heads-up to @sumanth-manchala — taking over to unblock the
> `graphifyy` fanout. The original PR #<N> remains open; this PR is a
> drop-in alternative scoped to osx-arm64 + linux-aarch64 only (no
> ppc64le, deferred to a follow-up). Happy to close in favor of #<N>
> if you'd like to rebase.

If any of the three conditions fails, take no action and continue
watching.

**Acceptance**: per-Cat-2-feedstock, one of: (a) sumanth's PR merged
upstream — no takeover; (b) takeover triggered — competing DRAFT PR
opened with the credit-and-handoff body.

### S-C4. Per-Cat-2 closeout

When each Cat-2 feedstock reaches a merged state (sumanth's PR
merged OR our takeover merged), record the outcome and the merge SHA
in the per-feedstock tracking table.

**Acceptance**: 7 Cat-2 feedstocks all reach a merged state. The
spec does not close until this happens.

---

## Stories — Wave D: Verify graphifyy resolves on osx-arm64

Goal: empirically confirm the whole effort actually delivered the
acceptance goal (Goal 1).

### S-D1. Wait for all 22 PRs to merge AND propagate to repodata

After the last of the 22 PRs merges, conda-forge CDN propagation
typically takes 1–6 hours. Wait until `mamba search 'tree-sitter-*' -c conda-forge --subdir osx-arm64` returns a build of every Cat-3 +
Cat-2 feedstock at the version that the merged PR shipped.

**Acceptance**: each of the 22 tree-sitter-* feedstock names returns
at least one osx-arm64 build via `mamba search`.

### S-D2. Smoke-test `mamba install graphifyy` on osx-arm64

Run the install dry-run via the osx-arm64 subdir override:

```
mamba install -n test-graphifyy -c conda-forge \
  --platform osx-arm64 \
  --dry-run \
  graphifyy
```

(The `--platform osx-arm64 --dry-run` pair lets the solver run from
any host without actually fetching osx-arm64 binaries.) Solver should
return a complete plan — no unresolved deps.

**Acceptance**: solver returns a complete plan including graphifyy and
all 26 tree-sitter-* deps + 3 transitive Python deps, all at osx-arm64
builds.

### S-D3. (Optional, host-permitting) Native install on an osx-arm64 host

If the operator has access to an osx-arm64 host:

```
mamba create -n test-graphifyy -c conda-forge graphifyy
mamba run -n test-graphifyy graphify --help
```

Confirms the actual install + entry-point invocation.

**Acceptance**: `graphify --help` returns successfully. (Skip with
"host unavailable" note if no osx-arm64 host is on hand.)

---

## Stories — Wave F: graphifyy-feedstock v0.8.40 + extras enablement (scope expansion 2026-06-16)

Original spec was scoped to making the **22 tree-sitter-\* dep feedstocks** ship osx-arm64, treating `conda-forge/graphifyy-feedstock` itself as **out of scope**. Scope expanded mid-session 2026-06-16 because:

1. Upstream PyPI advanced from v0.8.10 → v0.8.40 (30 versions; autotick bot's intermediate PRs #1/#2/#3/#5 stalled with stale shapes — all closed in favor of a direct bump).
2. Run-dep list changed materially: `datasketch` dropped (v0.8.37), `numpy>=1.21` added (v0.8.40), all tree-sitter-\* run-deps now version-pinned upstream.
3. The conda-forge.yml was bare (no `conda_install_tool: pixi`, no extended `bot:` block); modernization brings it in line with the 22 platform-expansion PRs shipped earlier in this session.
4. Upstream declares 19 `[project.optional-dependencies]` extras (mcp, neo4j, falkordb, pdf, watch, svg, leiden, office, google, postgres, video, kimi, ollama, bedrock, anthropic, gemini, openai, chinese, sql); main recipe pinned none of them.

### S-F1. Update graphifyy-feedstock to v0.8.40

Open a single PR against `conda-forge/graphifyy-feedstock` that bundles:

- **Version bump** v0.8.10 → v0.8.40 with new sha256.
- **Run-deps refresh** to match upstream `pyproject.toml [project.dependencies]`: + `numpy >=1.21`; − `datasketch`; all `tree-sitter-*` carry their lower bounds.
- **Drop upper bounds** on run-deps. `bot.run_deps_from_wheel: true` (added in S-F2) extracts lower bounds correctly on each version bump; upper bounds were redundant with `pip_check: true` + the `script: graphify --help` runtime test for catching ABI breaks.
- **Fix `tree_sitter` core dep name** to underscore-preserved form (per CFE SKILL.md G10 / `feedback_pypi_conda_mapping_unreliable.md`). conda-forge ships the core as `tree_sitter-X.Y.Z` (109 builds on linux-64), reserving the hyphen prefix `tree-sitter-LANG` for language bindings (456 builds, all our 22 platform-expansion feedstocks).
- **Restore the `script: graphify --help` test** the local mirror carried (catches CLI entry-point breakage at test time — load-bearing now that we dropped upper bounds).
- **Order maintainers alphabetically** (`killua156, mgorny, rxm7706`).
- **Add yaml-language-server schema header** per local-recipes convention.

**Acceptance**: PR opens as DRAFT; `validate` + `check-deps` (29/29 resolve) + `lint-optimize` (0 suggestions) all clean locally. Body cites the maintainer-add issue (already merged 2026-06-16) and the 22 platform-expansion PRs shipped earlier in the session.

### S-F2. Modernize conda-forge.yml to the 2026 canonical shape

In the same PR as S-F1:

```yaml
conda_install_tool: pixi
conda_build_tool: rattler-build
github:
  branch_name: main
  tooling_branch_name: main
conda_build:
  error_overlinking: true
conda_forge_output_validation: true
bot:
  automerge: true
  inspection: update-grayskull
  check_solvable: true
  run_deps_from_wheel: true
```

**Intentionally omits** the `provider:` / `build_platform:` / `test: native_and_emulated` block we shipped on the 22 tree-sitter-* platform-expansion PRs — graphifyy is `noarch: python`, so a single linux-64 build serves all subdirs automatically.

**Why each new key:**

- `conda_install_tool: pixi` — canonical 2026 companion to rattler-build.
- `bot.inspection: update-grayskull` — autotick bumps re-run grayskull against the new upstream, catching dep / metadata changes that a bare version bump misses (would have caught the `datasketch` removal at v0.8.37 if enabled earlier).
- `bot.check_solvable: true` — autotick PRs run dep-solvability check before opening; broken PRs never reach the queue.
- `bot.run_deps_from_wheel: true` — extract run-deps from upstream's wheel metadata (more accurate than parsing pyproject.toml).

**Acceptance**: conda-forge.yml byte-matches the canonical block; existing `bot.automerge: true` preserved (merged with the new keys, not overwritten).

### S-F3. Add `run_constrained` block for all available extras

Upstream defines 19 `[project.optional-dependencies]` groups. **17 of the 19 groups' deps are already on conda-forge across all 6 platforms we ship (incl. the 3 new subdirs)**. Add them to `requirements.run_constrained:` so users can opt in with explicit installs (`mamba install graphifyy mcp openai tiktoken`) and conda guarantees compatibility.

Verified extras availability (2026-06-16):


| Extra                           | Upstream deps                                     | conda-forge status                    |
| ------------------------------- | ------------------------------------------------- | ------------------------------------- |
| sql                             | tree-sitter-sql                                   | ✅ (0.3.11)                           |
| mcp                             | mcp                                               | ✅ (1.27.2)                           |
| neo4j                           | neo4j (PyPI) → neo4j-python-driver (conda-forge) | ✅ (6.2.0)                            |
| pdf                             | pypdf, markdownify                                | ✅                                    |
| watch                           | watchdog                                          | ✅                                    |
| svg                             | matplotlib, numpy>=2.0 (py>=3.13)                 | ✅                                    |
| leiden                          | graspologic (py<3.13)                             | ✅                                    |
| office                          | python-docx, openpyxl                             | ✅                                    |
| google                          | openpyxl                                          | ✅                                    |
| postgres                        | psycopg[binary] → psycopg                        | ✅                                    |
| video (yt-dlp only)             | yt-dlp                                            | ✅                                    |
| kimi / ollama / gemini / openai | openai, tiktoken                                  | ✅                                    |
| bedrock                         | boto3                                             | ✅                                    |
| anthropic                       | anthropic                                         | ✅                                    |
| chinese                         | jieba                                             | ✅                                    |
| **falkordb**                    | **falkordb**                                      | **❌ NOT ON CONDA-FORGE — see S-F4** |
| **video (faster-whisper part)** | **faster-whisper** (py>=3.11)                     | **❌ NOT ON CONDA-FORGE — see S-F4** |

**Acceptance**: PR commit `e2a999a` ships the 17-entry `run_constrained` block; check-deps passes; `mamba install graphifyy openai tiktoken mcp` on any subdir resolves cleanly post-merge.

### S-F4. Package the 2 missing extras (new conda-forge feedstocks)

Two extras blocked on conda-forge availability, drafted locally 2026-06-16:

- **`falkordb` v1.6.1** (`falkordb` extra) — Python client for the FalkorDB graph database. Pure-Python, Redis-protocol-based. **Drafted at `recipes/falkordb/recipe.yaml`** — validates clean (3/3 deps resolve: python-dateutil, redis-py; MIT license). **Ready for staged-recipes submission.**
- **`faster-whisper` v1.2.1** (`video` extra, py>=3.11) — Reimplementation of OpenAI Whisper using CTranslate2. **Drafted at `recipes/faster-whisper/recipe.yaml`** but **BLOCKED on a deeper transitive dep**: `ctranslate2` (C++ library by OpenNMT) is NOT on conda-forge. The other 5 faster-whisper run-deps (`huggingface_hub`, `tokenizers`, `onnxruntime`, `av`, `tqdm`) are all on conda-forge. Switched source from wheel-only PyPI to GitHub tag tarball to get the LICENSE + full source tree.

**Dependency chain**: graphifyy[video] → faster-whisper → ctranslate2 (C++ library, multi-platform native build, optional CUDA support, substantial recipe complexity)

**Recommended path forward**:

1. **`recipes/falkordb/` submitted to staged-recipes 2026-06-17 00:11:50Z as DRAFT [conda-forge/staged-recipes#33752](https://github.com/conda-forge/staged-recipes/pull/33752)** ("Create recipe.yaml for FalkorDB", head `falkordb`). Status: linter ✅ · linux_64 ✅ · osx_64 ✅ · win_64 ❌ — win_64 failure pending diagnosis.
2. **`recipes/ctranslate2/` submitted to staged-recipes 2026-06-17 00:34:29Z as DRAFT [conda-forge/staged-recipes#33753](https://github.com/conda-forge/staged-recipes/pull/33753)** ("Ctranslate2 suite", head `ctranslate2-suite`, sha `4cbc0189`).
3. **`recipes/faster-whisper/` submitted to staged-recipes 2026-06-17 00:44:14Z as DRAFT [conda-forge/staged-recipes#33754](https://github.com/conda-forge/staged-recipes/pull/33754)** ("Faster whisper", head `faster-whisper`, sha `9e13e5ac`). Sequencing note: gated on #33753 landing first (deps `ctranslate2` is not yet on conda-forge); kept as draft until then.
4. **`ctranslate2` packaging detail**: multi-output (`libctranslate2` + `ctranslate2`), 224 lines, adapted from `AnacondaRecipes/ctranslate2-feedstock@main` (Anaconda main channel recipe v4.7.1 by `xkong-anaconda`) with these deltas for conda-forge:

   - Main source bumped v4.7.1 → v4.8.0 (latest PyPI).
   - Converted v0 meta.yaml → v1 recipe.yaml.
   - Dropped MKL variant (Intel MKL is proprietary; conda-forge prefers OpenBLAS/Accelerate by default).
   - Dropped CUDA variants (cuda-12, cuda-13); ships as a separate `ctranslate2-cuda` recipe via conda-forge's CUDA-matrix variant pattern in a follow-up.
   - Dropped all 4 of Anaconda's patches (mkl-shared-libs, mkl-dll-libs-win, use-system-thrust, cuda13-compat) — none apply to the CPU-only OpenBLAS/Accelerate build.
   - Uses the same 3-submodule parallel-source pattern (`spdlog` 1.14.1 + `cxxopts` 3.1.1 + `cpu_features` 0.9.0) at their Anaconda-vetted SHAs.

   **Build-verified locally on linux-64 (2026-06-16)**: `libctranslate2-4.8.0-hbfe361e_0.conda` (1.2 MiB) + `ctranslate2-4.8.0-np2py310h81cc0b8_0.conda` (544 KiB) produced clean; `import ctranslate2; ctranslate2.__version__ == '4.8.0'` works; `from ctranslate2.converters import opennmt_py` succeeds. One non-blocking issue caught and fixed during verification: needed `openblas` (not `libopenblas`) in `host:` requirements — `libopenblas` is the runtime-only conda-forge package; `openblas` is the one that ships the headers + CMake config needed for `find_package(OpenBLAS)` to succeed. The Anaconda-adapted recipe + 3 submodule sources work as designed. **Pre-submission TODOs remaining** (4 items):

   - Verify submodule versions still satisfy v4.8.0's CMake checks (Anaconda's were against v4.7.1) — implicitly verified by the successful linux-64 build, but spot-check on other platforms once CI runs.
   - CUDA variants follow up as a separate `ctranslate2-cuda` recipe.
   - Spot-check `ENABLE_CPU_DISPATCH=ON` on `linux-ppc64le` (VSX) / `linux-aarch64` (NEON) once CI runs (Anaconda's recipe didn't target ARM).
   - Consider bumping spdlog → 1.15.x and cxxopts → 3.2.x once verified compatible.
5. After #33753 merges, mark #33754 ready-for-review (currently draft).
6. Final follow-up PR on graphifyy-feedstock: add `ctranslate2`, `faster-whisper`, `falkordb` to `run_constraints:` and update S-F3's omission note.

**Backend choices in the ctranslate2 draft** (CPU-only):

- Linux + Windows: WITH_OPENBLAS=ON + WITH_RUY=ON; WITH_MKL=OFF (Intel MKL is proprietary, doesn't ship as default on conda-forge).
- macOS: WITH_ACCELERATE=ON + WITH_RUY=ON (Apple's framework + ARM-friendly Ruy).
- All platforms: CUDA / cuDNN / Flash Attention / TensorParallel deferred to a future `ctranslate2-cuda` variant.

**Acceptance**: all three drafts submitted as staged-recipes DRAFT PRs (2026-06-17): #33752 (falkordb, CI partial green — win_64 ❌ outstanding), #33753 (ctranslate2-suite), #33754 (faster-whisper, sequencing on #33753).

### S-F5. tree-sitter-swift dist-info version-metadata fix (2026-06-16)

Caught during graphifyy PR #8's first CI run: `pip check` rejected the build because the installed `tree-sitter-swift` wheel ships `dist-info` declaring `version = "0.0.1"` while graphifyy 0.8.40's `pyproject.toml` pins `tree-sitter-swift<0.9,>=0.7`. The conda solver picks our 0.7.3 conda label, but pip then reads the wheel's metadata and sees `0.0.1 < 0.7` — fail.

**Survey result**: of 22 `tree-sitter-*` packages on conda-forge, only `tree-sitter-swift` has a major dist-info mismatch (0.7.3 vs 0.0.1). `tree-sitter-powershell` has a minor 0.26.5/0.26.4 nit (harmless — within graphifyy's `>=0.26,<0.28` range).

**Root cause**: upstream `alex-pinkus/tree-sitter-swift` has never bumped its `pyproject.toml [project].version` field from the placeholder `"0.0.1"` despite tagging releases up through v0.7.3. PyPI's `tree-sitter-swift` is stuck at v0.0.1 for the same reason.

**Downstream fix** (`conda-forge/tree-sitter-swift-feedstock#5`, opened 2026-06-16 by rxm7706):

1. Bump `tag` context-var template to `${{ version }}-with-generated-files` (was hardcoded `0.7.2-with-generated-files`; autotick-friendly now).
2. Replace static `patches/0001-...patch` (hardcoded destination `0.7.3`) with a `build.script` that rewrites `pyproject.toml`'s `version = ".*"` line in-place using `${{ version }}`. Works for any future version bump without recipe edits.
3. Bump `build.number` 1 → 2 to supersede currently-shipping `*_1` artifacts (same upstream-version recipe-shape change rule).

**Follow-up TODOs** (post Wave F closeout):

- **File upstream issue** at `alex-pinkus/tree-sitter-swift` requesting they bump `pyproject.toml [project].version` to track tag releases. Once they do, our `build.script` rewrite becomes a no-op (sed/python find-replace does nothing if source already matches). The fix is forward-compatible and self-healing.
- Confirm `tree-sitter-powershell`'s 0.26.5/0.26.4 minor mismatch doesn't surface elsewhere (it doesn't break graphifyy, but might break tighter downstream pins).
- Verify the `${{ version }}-with-generated-files` tag pattern works for autotick by spot-checking the bot's next bump attempt on this feedstock.
- **Simplify the Windows path**: the current fix uses a checked-in `recipe/fix_pyproject_version.py` helper because inline `sed` (Unix) + `powershell` (Windows) hit cmd.exe escaping issues — cmd ate the `^` from `[^\"]` outside the powershell-quoted string and mangled the regex (Azure buildId 1539671). A separate helper file is more code than a single inline command should require. **Preferred replacement: add `sed` to `requirements.build` (conda-forge ships GNU sed cross-platform via `m2-sed` on Windows) and use one `sed -i 's/^version = .*/version = "${{ version }}"/' pyproject.toml` line that works on every platform.** Open follow-up PR to swap the helper for the one-liner once this lands. The root cause + canonical pattern is being captured as CFE SKILL.md G23 so it doesn't get re-learned the hard way on the next recipe.

**Acceptance**: PR #5 merges + propagates → graphifyy PR #8's `pip check` passes on next CI run → no further intervention on graphifyy needed.

**Status update 2026-06-17 01:36Z**: PR #5 MERGED at `2cfc104`. Build artifacts (`tree-sitter-swift-0.7.3-*_2.conda`) propagating to conda-forge repodata (typical 30-60 min lag). Once visible on linux-64 + the other 5 subdirs, re-run graphifyy PR #8's CI to confirm `pip check` passes.

**Status update 2026-06-17 (post-propagation)**: ✅ tree-sitter-swift `*_2` build verified shipping `tree_sitter_swift-0.7.3.dist-info` (was `0.0.1`). Triggered graphifyy PR #8 rerender + CI re-run. **PR #8 CI flipped FAILURE → SUCCESS** on the same head (`3227888`) via Azure rebuild 27662710337. `mergeable: MERGEABLE`. **S-F5 acceptance criterion fully met** — no further intervention on graphifyy needed.

**🎉 PR #8 MERGED at 2026-06-17 03:00:06Z (merge SHA `fa094fa`)**. graphifyy v0.8.40 + 2026-canonical conda-forge.yml + 17-entry `run_constrained` block shipped to conda-forge. Combined with the 22 platform-expansion PRs + 8-feedstock canonical-sweep + tree-sitter-swift dist-info fix merged earlier this session, **Wave F closes the entire graphifyy osx-arm64 fanout effort end-to-end**.

### S-F6. Canonical `conda-forge.yml` retrofit sweep (2026-06-17)

Discovered while monitoring S-F5: of the 23 `tree-sitter-*` feedstocks shipped in Wave C + Wave B + tree-sitter-markdown out-of-band, **8 do not match the 2026-canonical `conda-forge.yml` block** that Wave B Batch 1+2+3 adopted. The gap is two missing keys (`conda_install_tool: pixi` + the entire `bot:` block); the rest of the block already matches.


| Subset              | Count | Feedstocks                                                                                                                       |
| ------------------- | ----- | -------------------------------------------------------------------------------------------------------------------------------- |
| ✅ Match canonical  | 15    | typescript, rust, java, ruby, kotlin, scala, php, swift, lua, zig, powershell, objc, julia, verilog, json (all Wave B Cat-3 PRs) |
| ❌ Differ           | 8     | javascript, go, groovy, c, cpp, elixir, fortran (Cat-2), markdown (Cat-3 out-of-band)                                            |
| ➖ Not a maintainer | 4     | tree-sitter (core), python, c-sharp, bash (Cat-1)                                                                                |

**Why the gap**: the 7 Cat-2 PRs shipped during Wave C (uplift of sumanth-manchala's PRs) before the richer 2026-canonical conda-forge.yml was adopted. tree-sitter-markdown was the user's out-of-band v0.5.3 + platform-expansion PR which only added platform-expansion keys, not the `bot:` block. The 15 Cat-3 PRs in Wave B Batches 1-3 shipped after the canonical was adopted and are already aligned.

**Sweep PRs opened 2026-06-17** (all DRAFT, build.number bumped on each):


| Feedstock              | PR | New build.number |
| ---------------------- | -- | ---------------- |
| tree-sitter-javascript | #4 | 1 → 2           |
| tree-sitter-go         | #4 | 1 → 2           |
| tree-sitter-groovy     | #5 | 2 → 3           |
| tree-sitter-c          | #4 | 1 → 2           |
| tree-sitter-cpp        | #4 | 1 → 2           |
| tree-sitter-elixir     | #4 | 1 → 2           |
| tree-sitter-fortran    | #5 | 2 → 3           |
| tree-sitter-markdown   | #6 | 0 → 1           |

Each PR is `+1 commit`, touching only `conda-forge.yml` (adds 5 lines) + `recipe.yaml` (1-line build.number bump). No platform-expansion or recipe-code change. Rerender requested on each.

**Acceptance**: all 8 PRs land green; subsequent autotick PRs on these feedstocks run with `inspection: update-grayskull` (more accurate dep refresh) + `check_solvable: true` (broken PRs filtered at submission) + `run_deps_from_wheel: true` (better dep-list source); install paths use pixi by default.

**Status update 2026-06-17 01:55-01:56Z**: ALL 8 PRs MERGED within ~85 seconds:


| Feedstock              | PR | Merge SHA             |
| ---------------------- | -- | --------------------- |
| tree-sitter-elixir     | #4 | `98e676f` (01:55:19Z) |
| tree-sitter-javascript | #4 | `e1fb790` (01:55:23Z) |
| tree-sitter-go         | #4 | `f9b8380` (01:55:30Z) |
| tree-sitter-groovy     | #5 | `84df721` (01:55:40Z) |
| tree-sitter-c          | #4 | `519eca5` (01:55:50Z) |
| tree-sitter-fortran    | #5 | `ae7bcba` (01:56:01Z) |
| tree-sitter-cpp        | #4 | `0cc295e` (01:56:18Z) |
| tree-sitter-markdown   | #6 | `517d8cd` (01:56:40Z) |

Post-merge canonical-match verification: **all 23 maintainer-owned `tree-sitter-*` feedstocks** (15 Wave B + 7 Cat-2 + tree-sitter-markdown) now match the 2026 canonical `conda-forge.yml` byte-for-byte. Cat-1 feedstocks (tree-sitter core, python, c-sharp, bash) are not in scope (rxm7706 isn't on those teams).

---

### S-E1. Single consolidated retro across all 22 PRs

Invoke `bmad-retrospective` (or follow its protocol manually). Survey:

- Per-feedstock build outcomes (any feedstock CI red on osx-arm64 or
  linux-aarch64? Why?)
- Maintainer-add timing (did the bot process all 22 promptly, or did
  the 48h silence-implies-consent fallback fire?)
- 14-day takeover policy outcomes (how many Cat-2 PRs needed
  takeover? Was the threshold right?)
- Per-feedstock `conda-forge.yml` diffs — did any feedstock diverge
  from the cookie-cutter pattern?
- Any reviewer pushback on ppc64le-omission (Goal 5 / Q1) — did it
  trigger?

**Retro executed 2026-06-17 (post-PR #8 merge)** — landed as CFE skill v8.26.0 (MINOR bump). Findings:


| Bucket                         | Finding                                                                                                                                                                                                                                                                                                                                                                              | Skill landing                                              |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------- |
| Addition                       | **G23** — Inline `sed`/`powershell` in `build.script` hits cmd.exe escape hell. Canonical fix: `sed` with `m2-sed` on Win                                                                                                                                                                                                                                                           | SKILL.md new gotcha section                                |
| Addition                       | **G24** — Conda label ≠ wheel `dist-info` version when upstream's `pyproject.toml` hardcodes a placeholder. Detection helper + canonical fix via G23 pattern                                                                                                                                                                                                                       | SKILL.md new gotcha section                                |
| Refinement                     | Sub-workflow "Special-case categorizations" gains a 4th bullet making upstream-declared upper bounds'`pip_check`-enforcement mechanism explicit (the existing DEP-002 note was easy to skip past — empirically confirmed)                                                                                                                                                           | SKILL.md sub-workflow categorizations table                |
| Audit outcome (no skill delta) | Maintainer-add bot: processed all 22 same-day (no 48h fallback). Takeover policy never fired — all 7 Cat-2 PRs merged via rxm7706 follow-up commits (`maintainerCanModify: true`). ppc64le reviewer pushback DID trigger (mgorny clarified ppc64le is cross-compile, not native), corrected spec mid-session. conda-forge.yml drift discovered post-merge → spawned § S-F6 sweep. | None — process worked                                     |
| Audit outcome (skill memory)   | "Drop upper bounds" without checking`pip_check` impact almost merged broken graphifyy. Empirical confirmation that the existing DEP-002 sub-rule about upstream-declared bounds is load-bearing.                                                                                                                                                                                     | Already captured in feedback memory + now in new sub-rule. |

**Counter-factual estimate**: had G23+G24+the upper-bounds sub-rule been in the skill at intake, graphifyy PR #8 would have shipped with the right shape on commit 1 (skipping iterations 1+2 — drop-upper-bounds revert + pip_check debugging). Iteration 3 (tree-sitter-swift dist-info fix) was unavoidable but would have surfaced at PR-author time, not CI-debug time. Per-future-analogous-fanout savings: ~1-2 PR-iteration cycles + ~30-60 min CI-burn.

**No cross-skill auto-memory deltas** — all findings are CFE-internal. Existing feedback memory entries (`feedback_canonical_conda_forge_yml_for_platform_expansion.md`, `feedback_bump_build_number_on_feedstock_pr_update.md`, `feedback_always_request_rerender_after_feedstock_push.md`) all validated as load-bearing during the session.

### S-E2. Land the retro deltas

Write a single `CHANGELOG.md` entry covering all 22 PRs (not 22
separate entries). Land any skill-guide refinements per Rule 2
(corrections / refinements / additions).

**Acceptance**: new dated `CHANGELOG.md` entry in
`.claude/skills/conda-forge-expert/CHANGELOG.md`. If no novel
findings: explicit "verified existing guidance held across 22-PR
fanout" entry.

---

## Open Questions (resolved 2026-06-15)

### Q1. Scope divergence from sumanth's PRs — ship osx-arm64 + linux-aarch64 only, or match his three (incl. ppc64le)?

**Original resolution (2026-06-15)**: ship osx-arm64 + linux-aarch64 only.
**Updated 2026-06-16**: match all three (osx-arm64 + linux-aarch64 + linux-ppc64le).

Rationale for the update: mgorny's review on `tree-sitter-javascript#1`
clarified that ppc64le is not native on conda-forge anyway — the
canonical pattern is hybrid `provider: linux_aarch64+osx_arm64: default`

+ `build_platform: linux_ppc64le: linux_64`, where the ppc64le build
  cross-compiles on the x86_64 toolchain and tests run emulated via
  QEMU (`test: native_and_emulated`). This sidesteps the original
  transitive-C-dep concern entirely: the build doesn't touch the ppc64le
  package graph at compile time, only at runtime-emulated-test time. All
  7 Cat-2 PRs shipped ppc64le builds green using this pattern. Cat-3 PRs
  use the same shape.

Reviewer-divergence risk: a `killua156`/`mgorny` reviewer comparing
our PRs to sumanth's may ask "why no ppc64le?". The PR body addresses
this preemptively:

> Scope deliberately narrower than #<sumanth-PR-on-this-feedstock> on
> a sibling feedstock — osx-arm64 + linux-aarch64 only. ppc64le
> deferred per `feedstock-platform-expansion.md` transitive-coverage
> caveat; happy to add in a follow-up PR once sumanth's PRs land
> green on ppc64le.

### Q2. Maintainer-add gate — issue first then PR, or both simultaneously?

**Resolution**: issue first, then PR. Either (a) wait for bot
confirmation of team-add, or (b) wait 48h with no objection on the
issue.

Rationale: the user explicitly set this policy. Mechanically simpler
to track per-feedstock; reduces reviewer load by giving maintainers a
chance to weigh in before any recipe surface area is changed.

### Q3. 14-day takeover threshold — too short, too long, or right?

**Resolution**: 14 days. Operator chose this in the intake.

Rationale: sumanth's PRs were opened 2026-06-07. As of 2026-06-15 they
are 8 days old. A 14-day threshold (so first eligible takeover at
2026-06-21) gives `killua156`/`mgorny` reasonable bandwidth without
indefinitely blocking graphifyy. The threshold is per-PR last-activity,
not per-PR open-date — so a PR that received a CI rerun yesterday
resets the clock.

### Q4. Watch-table refresh mechanism — `bmad-quick-dev` invocation or scheduled job?

**Resolution**: defer to operator at S-C1 intake. Recommended: weekly
manual invocation triggered by the operator (low effort — read-only),
not a scheduled job (the schedule infrastructure for this repo is
geared toward atlas-data refresh, not GitHub-state polling).

### Q5. Batch cadence in Wave B — 3 batches of 5 with operator gates, or one batch of 15?

**Resolution**: 3 batches of 5 with operator gates per S-B3 / S-B5.

Rationale: 22 issues + 15 PRs against a 2-maintainer pair is a visible
volume of activity. Batching gives operator visibility into maintainer
response patterns AND gives the maintainers a chance to push back
before the full batch ships. If maintainers respond enthusiastically
to Batch 1, operator may decide to ship Batches 2+3 in quick
succession.

---

## Risks and Mitigations


| Risk                                                                                                                                                                                   | Likelihood  | Impact                                                              | Mitigation                                                                                                                                                                                                                                                          |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `killua156` or `mgorny` rejects the maintainer-add request as inappropriate (e.g. "we maintain these as a coherent set")                                                               | Low–Medium | Wave B can't proceed via the standard maintainer route              | Operator-decision branch: (a) open PRs anyway and ask reviewers to merge on our behalf via`@conda-forge-admin, please merge` once green, or (b) close the fanout and accept that graphifyy on osx-arm64 waits for sumanth's PRs + a separate ppc64le-blocked subset |
| ~~Reviewer pushback on scope divergence (no ppc64le) per Q1~~ Resolved 2026-06-16 — Cat-3 PRs now include ppc64le via hybrid cross-compile pattern, matching Cat-2 + sumanth's scope. | n/a         | n/a                                                                 | n/a                                                                                                                                                                                                                                                                 |
| A Cat-3 feedstock's`recipe.yaml` diverges from the cookie-cutter abi3 shape (recipe-shape audit was a spot-check, not exhaustive)                                                      | Low         | Per-feedstock Stop-the-Line, scope expands to recipe-authoring      | Per-feedstock S-B2/B4/B6 invokes`feedstock-platform-expansion.md` S3 (validate + check-deps), which catches this BEFORE the PR opens. Stop-the-Line per the per-feedstock guide                                                                                     |
| Sumanth's PR merges with ppc64le green on a Cat-2 feedstock between Wave A and Wave B — making the divergence point moot                                                              | Medium      | Slight reviewer-message inconsistency on our Cat-3 PRs              | Acceptable. Update the PR-body boilerplate to drop the "happy to add in a follow-up" clause if all 7 Cat-2 PRs have already merged ppc64le-green                                                                                                                    |
| Sumanth's 7 PRs all stall and need takeover — fanout balloons to 22 net-new PRs from us                                                                                               | Low         | Higher reviewer load on`killua156`/`mgorny`; longer effort timeline | 14-day threshold is the natural backstop; spec already plans for it. Worst case: 22 PRs total in 5 batches across 3+ weeks                                                                                                                                          |
| graphifyy's run-dep list changes between intake and merge (upstream version bump introduces new tree-sitter-*)                                                                         | Low–Medium | Wave D smoke-test fails even with 22 PRs merged                     | Re-run the § Empirical state audit at Wave D start; if a new dep appeared, add it to the fanout. Spec does not close until graphifyy is empirically installable on osx-arm64                                                                                       |
| Operator capacity — 5 operator gates (S-A3, S-B3, S-B5, plus per-PR draft→ready × 15)                                                                                               | High        | Operator-load-driven schedule slip                                  | Group draft→ready transitions by batch (5 at a time) instead of per-PR. Operator gates are mandatory; cadence is flexible                                                                                                                                          |

---

## Acceptance criteria (whole effort)

1. **`mamba install graphifyy --platform osx-arm64 --dry-run`** returns
   a complete plan including all 26 tree-sitter-* deps + 3 transitive
   Python deps, all at osx-arm64 builds. (Wave D, S-D2.)
2. **22 maintainer-add issues opened** (15 Cat-3 + 7 Cat-2) on
   `conda-forge/tree-sitter-*-feedstock` repos.
3. **15 platform-expansion PRs opened** on Cat-3 feedstocks, scoped to
   osx-arm64 + linux-aarch64.
4. **7 Cat-2 feedstocks reach a merged state** (sumanth's PR merged
   OR our takeover merged after 14-day idle).
5. **All 22 PRs land** their osx-arm64 builds in
   `conda-forge/osx-arm64/repodata.json` within ~6 hours of merge.
6. **One consolidated CHANGELOG entry** in
   `.claude/skills/conda-forge-expert/CHANGELOG.md` for the whole
   fanout (not 22 separate entries).
7. **Per-feedstock tracking table** at the bottom of this spec
   populated end-to-end (maintainer-add issue #, PR #, merge SHA, first
   osx-arm64 build on repodata).

---

## Reference

- Per-feedstock workflow: [`docs/specs/feedstock-platform-expansion.md`](feedstock-platform-expansion.md)
- Workflow guide (procedural detail): [`.claude/skills/conda-forge-expert/guides/feedstock-platform-expansion.md`](../../.claude/skills/conda-forge-expert/guides/feedstock-platform-expansion.md)
- Canonical PR diff to copy: `https://github.com/conda-forge/tree-sitter-javascript-feedstock/pull/1`
- Maintainer-add issue template: `https://github.com/conda-forge/tree-sitter-javascript-feedstock/issues/2`
- CFE `SKILL.md` § Critical Constraints, § Build Failure Protocol
- CFE `reference/conda-forge-yml-reference.md` — `provider:`, `workflow_settings.store_build_artifacts:`
- CLAUDE.md § "BMAD ↔ conda-forge-expert integration" — Rule 1 + Rule 2

---

# Per-feedstock tracking table

Populated as the fanout executes. One row per affected feedstock.

## Cat 3 — 15 net-new PRs (our work)


| Feedstock              | Maintainer-add issue                                                                        | Recipe PR                                                                                                                                           | CI green?                         | Merged SHA                           | First osx-arm64 build on repodata? |
| ---------------------- | ------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- | ------------------------------------ | ---------------------------------- |
| tree-sitter-typescript | [#1](https://github.com/conda-forge/tree-sitter-typescript-feedstock/issues/1) (2026-06-16) | [#3](https://github.com/conda-forge/tree-sitter-typescript-feedstock/pull/3) (Wave B Batch 3)                                                       | (CI green at merge)               | `45da046` (merged 2026-06-16 23:22Z) | _<Wave D>_                         |
| tree-sitter-rust       | [#1](https://github.com/conda-forge/tree-sitter-rust-feedstock/issues/1) (2026-06-16)       | [#3](https://github.com/conda-forge/tree-sitter-rust-feedstock/pull/3) (Wave B Batch 2)                                                             | (CI green at merge)               | `bb70dd1` (merged 2026-06-16 23:05Z) | _<Wave D>_                         |
| tree-sitter-java       | [#2](https://github.com/conda-forge/tree-sitter-java-feedstock/issues/2) (2026-06-16)       | [#4](https://github.com/conda-forge/tree-sitter-java-feedstock/pull/4) (Wave B Batch 1)                                                             | (CI green at merge)               | `6b693f6` (merged 2026-06-16 22:42Z) | _<Wave D>_                         |
| tree-sitter-ruby       | [#1](https://github.com/conda-forge/tree-sitter-ruby-feedstock/issues/1) (2026-06-16)       | [#3](https://github.com/conda-forge/tree-sitter-ruby-feedstock/pull/3) (Wave B Batch 2)                                                             | (CI green at merge)               | `832a455` (merged 2026-06-16 23:01Z) | _<Wave D>_                         |
| tree-sitter-kotlin     | [#1](https://github.com/conda-forge/tree-sitter-kotlin-feedstock/issues/1) (2026-06-16)     | [#3](https://github.com/conda-forge/tree-sitter-kotlin-feedstock/pull/3) (Wave B Batch 1)                                                           | (CI green at merge)               | `923956e` (merged 2026-06-16 22:42Z) | _<Wave D>_                         |
| tree-sitter-scala      | [#1](https://github.com/conda-forge/tree-sitter-scala-feedstock/issues/1) (2026-06-16)      | [#3](https://github.com/conda-forge/tree-sitter-scala-feedstock/pull/3) (Wave B Batch 3)                                                            | (CI green at merge)               | `64e3924` (merged 2026-06-16 23:17Z) | _<Wave D>_                         |
| tree-sitter-php        | [#2](https://github.com/conda-forge/tree-sitter-php-feedstock/issues/2) (2026-06-16)        | [#4](https://github.com/conda-forge/tree-sitter-php-feedstock/pull/4) (Wave B Batch 2; PR #1 license-patch already merged 13:42Z)                   | (CI green at merge)               | `1cb1106` (merged 2026-06-16 22:59Z) | _<Wave D>_                         |
| tree-sitter-swift      | [#2](https://github.com/conda-forge/tree-sitter-swift-feedstock/issues/2) (2026-06-16)      | [#4](https://github.com/conda-forge/tree-sitter-swift-feedstock/pull/4) (Wave B Batch 3)                                                            | (CI green at merge)               | `73e78f3` (merged 2026-06-16 23:18Z) | _<Wave D>_                         |
| tree-sitter-lua        | [#1](https://github.com/conda-forge/tree-sitter-lua-feedstock/issues/1) (2026-06-16)        | [#3](https://github.com/conda-forge/tree-sitter-lua-feedstock/pull/3) (Wave B Batch 1)                                                              | (CI green at merge)               | `1c09c91` (merged 2026-06-16 22:42Z) | _<Wave D>_                         |
| tree-sitter-zig        | [#1](https://github.com/conda-forge/tree-sitter-zig-feedstock/issues/1) (2026-06-16)        | [#3](https://github.com/conda-forge/tree-sitter-zig-feedstock/pull/3) (Wave B Batch 3)                                                              | (CI green at merge)               | `a15d42d` (merged 2026-06-16 23:23Z) | _<Wave D>_                         |
| tree-sitter-powershell | [#3](https://github.com/conda-forge/tree-sitter-powershell-feedstock/issues/3) (2026-06-16) | [#5](https://github.com/conda-forge/tree-sitter-powershell-feedstock/pull/5) (Wave B Batch 2)                                                       | (CI green at merge)               | `79c4471` (merged 2026-06-16 23:02Z) | _<Wave D>_                         |
| tree-sitter-objc       | [#1](https://github.com/conda-forge/tree-sitter-objc-feedstock/issues/1) (2026-06-16)       | [#3](https://github.com/conda-forge/tree-sitter-objc-feedstock/pull/3) (Wave B Batch 2)                                                             | (CI green at merge)               | `2fd9e36` (merged 2026-06-16 22:57Z) | _<Wave D>_                         |
| tree-sitter-julia      | [#2](https://github.com/conda-forge/tree-sitter-julia-feedstock/issues/2) (2026-06-16)      | [#4](https://github.com/conda-forge/tree-sitter-julia-feedstock/pull/4) (Wave B Batch 1)                                                            | (CI green at merge)               | `42467c0` (merged 2026-06-16 22:43Z) | _<Wave D>_                         |
| tree-sitter-verilog    | [#1](https://github.com/conda-forge/tree-sitter-verilog-feedstock/issues/1) (2026-06-16)    | [#3](https://github.com/conda-forge/tree-sitter-verilog-feedstock/pull/3) (Wave B Batch 3)                                                          | (CI green at merge)               | `9338e52` (merged 2026-06-16 23:23Z) | _<Wave D>_                         |
| tree-sitter-json       | [#2](https://github.com/conda-forge/tree-sitter-json-feedstock/issues/2) (2026-06-16)       | [#4](https://github.com/conda-forge/tree-sitter-json-feedstock/pull/4) (Wave B Batch 1)                                                             | (CI green at merge)               | `c867432` (merged 2026-06-16 22:43Z) | _<Wave D>_                         |
| tree-sitter-markdown   | [#2](https://github.com/conda-forge/tree-sitter-markdown-feedstock/issues/2) (2026-06-16)   | [#5](https://github.com/conda-forge/tree-sitter-markdown-feedstock/pull/5) (v0.5.3 + setup.py patch + platform expansion, merged 2026-06-16 22:12Z) | (verified by author before merge) | `1d7b45b`                            | _<Wave D>_                         |

## Cat 2 — 7 in-flight (watch + conditional takeover, ALL MERGED 2026-06-16)


| Feedstock              | Maintainer-add issue                                                                          | Sumanth PR #    | Last activity            | Takeover triggered? | Our PR #                                   | Merged SHA |
| ---------------------- | --------------------------------------------------------------------------------------------- | --------------- | ------------------------ | ------------------- | ------------------------------------------ | ---------- |
| tree-sitter-javascript | [#2](https://github.com/conda-forge/tree-sitter-javascript-feedstock/issues/2) (pre-existing) | #1 (2026-06-07) | merged 2026-06-16 12:05Z | no                  | sumanth's #1                               | `d98885e`  |
| tree-sitter-go         | [#2](https://github.com/conda-forge/tree-sitter-go-feedstock/issues/2) (2026-06-16)           | #1 (2026-06-07) | merged 2026-06-16 12:08Z | no                  | sumanth's #1 (with rxm7706 commits on top) | `3d6579b`  |
| tree-sitter-groovy     | [#3](https://github.com/conda-forge/tree-sitter-groovy-feedstock/issues/3) (2026-06-16)       | #2 (2026-06-07) | merged 2026-06-16 13:45Z | no                  | sumanth's #2 (with rxm7706 commits on top) | `d28e6d7`  |
| tree-sitter-c          | [#2](https://github.com/conda-forge/tree-sitter-c-feedstock/issues/2) (2026-06-16)            | #1 (2026-06-07) | merged 2026-06-16 13:53Z | no                  | sumanth's #1 (with rxm7706 commits on top) | `2a3c115`  |
| tree-sitter-cpp        | [#2](https://github.com/conda-forge/tree-sitter-cpp-feedstock/issues/2) (2026-06-16)          | #1 (2026-06-07) | merged 2026-06-16 13:52Z | no                  | sumanth's #1 (with rxm7706 commits on top) | `ea6383e`  |
| tree-sitter-elixir     | [#2](https://github.com/conda-forge/tree-sitter-elixir-feedstock/issues/2) (2026-06-16)       | #1 (2026-06-07) | merged 2026-06-16 13:51Z | no                  | sumanth's #1 (with rxm7706 commits on top) | `01bd434`  |
| tree-sitter-fortran    | [#3](https://github.com/conda-forge/tree-sitter-fortran-feedstock/issues/3) (2026-06-16)      | #2 (2026-06-07) | merged 2026-06-16 13:47Z | no                  | sumanth's #2 (with rxm7706 commits on top) | `bbcf47d`  |

## Final state

- Wave A complete: 2026-06-16 — 22 maintainer-add issues opened; bot processed all 22 team-adds same-day. `rxm7706` confirmed on all 22 `conda-forge/tree-sitter-*` teams via `gh api orgs/conda-forge/teams/<feedstock>/members`. S-A3 checkpoint cleared.
- Wave C complete: 2026-06-16 — all 7 Cat-2 PRs merged (javascript first, then go + groovy + fortran + elixir + cpp + c). No takeovers triggered; sumanth's PRs all merged with rxm7706 follow-up commits on top (native+cross conda-forge.yml uplift via post-mgorny-review canonical pattern). Spec scope-extended addendum 2026-06-16 added tree-sitter-markdown to Cat-3 (16th feedstock).
- tree-sitter-markdown shipped 2026-06-16 22:12Z — out-of-band Cat-3 closeout via PR #5 (`1d7b45b`). Two-step closeout: (a) autotick PR #1 closed (broken upstream v0.5.3 setup.py — flat src/ layout vs dual-grammar tarball — SKILL.md G5 sibling case); (b) PR #4 opened with `bot.version_updates.exclude` as safety belt then closed when PR #5 (v0.5.3 with setup.py patch + platform expansion bundled by operator before merge) shipped the real fix. Local build verified `tree-sitter-markdown-0.5.3-py310h03a07cb_0.conda` 136 KiB before PR. Wave B remaining count drops 16 → 15.
- Wave B Batch 1 complete 2026-06-16 22:42-22:43Z — 5 Cat-3 platform-expansion PRs (tree-sitter-{java, json, julia, kotlin, lua}) all merged within ~1 minute of each other:
  - tree-sitter-java PR #4 (`6b693f6`, 22:42Z)
  - tree-sitter-json PR #4 (`c867432`, 22:43Z)
  - tree-sitter-julia PR #4 (`42467c0`, 22:43Z)
  - tree-sitter-kotlin PR #3 (`923956e`, 22:42Z)
  - tree-sitter-lua PR #3 (`1c09c91`, 22:42Z)
  - All shipped with the full 2026 canonical conda-forge.yml (conda_install_tool: pixi + platform-expansion block + bot.{automerge, inspection: update-grayskull, check_solvable, run_deps_from_wheel}) + build_number supersede + maintainer alphabetical reorder. Wave B remaining count drops 15 → 10 (Batch 2 + Batch 3).
- Wave B Batch 2 complete 2026-06-16 22:57-23:05Z — 5 Cat-3 platform-expansion PRs (tree-sitter-{objc, php, powershell, ruby, rust}) all merged within ~8 minutes:
  - tree-sitter-objc PR #3 (`2fd9e36`, 22:57Z)
  - tree-sitter-php PR #4 (`1cb1106`, 22:59Z) — PR #1 license-patch had already merged 13:42Z; this is the routine platform-expansion follow-up against main's v0.24.2 state
  - tree-sitter-powershell PR #5 (`79c4471`, 23:02Z)
  - tree-sitter-ruby PR #3 (`832a455`, 23:01Z)
  - tree-sitter-rust PR #3 (`bb70dd1`, 23:05Z)
  - Same full 2026 canonical conda-forge.yml shape as Batch 1. Wave B remaining count drops 10 → 5 (Batch 3).
- Wave B Batch 3 complete 2026-06-16 23:17-23:23Z — final 5 Cat-3 platform-expansion PRs (tree-sitter-{scala, swift, typescript, verilog, zig}) all merged within ~6 minutes:
  - tree-sitter-scala PR #3 (`64e3924`, 23:17Z)
  - tree-sitter-swift PR #4 (`73e78f3`, 23:18Z)
  - tree-sitter-typescript PR #3 (`45da046`, 23:22Z)
  - tree-sitter-verilog PR #3 (`9338e52`, 23:23Z)
  - tree-sitter-zig PR #3 (`a15d42d`, 23:23Z)
  - **🎉 Wave B closed. All 22 platform-expansion PRs merged. 16 Cat-3 (incl. markdown) + 7 Cat-2 platform expansions = 23 feedstocks now ship osx-arm64.** Next: Wave D smoke-test after CDN propagation.
- Wave D smoke-test result (2026-06-17 03:25Z): **✅ PASS**. `CONDA_OVERRIDE_OSX=11.0 mamba create -n test-graphifyy-osx-arm64 -c conda-forge --platform osx-arm64 --dry-run graphifyy` resolved cleanly — 62 packages / 71 MB. All 22 tree-sitter-* deps pulled from conda-forge osx-arm64 builds; many at `*_2` builds (Wave B platform-expansion rebuilds); `tree-sitter-swift 0.7.3 py310h28d811c_2` is the dist-info-fixed build from S-F5 PR #5. Solver picked graphifyy 0.8.10 (still-published version at smoke-test time; 0.8.40 uploaded to anaconda.org at 03:01:42Z but conda-forge repodata had not yet refreshed — typical 30-60 min lag). Dep set is identical between 0.8.10 and 0.8.40 base requirements so 0.8.40 resolves the same way once propagated. **Goal 1 (graphifyy installable on osx-arm64) empirically met.** S-D1 ✅ (all 22 names searchable). S-D2 ✅ (dry-run solve complete). S-D3 deferred (no osx-arm64 host on hand).
- Closeout retro CHANGELOG entry: **✅ landed** as CFE v8.26.0 (commit `f9ed72127f`, 2026-06-17). Three deltas: G23 (cmd.exe escape trap with sed+m2-sed canonical fix), G24 (wheel dist-info Version mismatch detection + dynamic-tag remedy), DEP-002 sub-rule (load-bearing upstream-declared upper bounds — do NOT drop). 59 files changed; 3,202 insertions; 23 tree-sitter-* feedstock mirrors synced; 3 staged-recipes drafts (now all OPEN on staged-recipes — see S-F4 follow-ups below). Skill bump 8.25.0 → 8.26.0 (MINOR; additive).
- S-F4 staged-recipes draft PRs (all OPEN 2026-06-17):
  - [#33752](https://github.com/conda-forge/staged-recipes/pull/33752) — Create recipe.yaml for FalkorDB (head `falkordb`, opened 00:11:50Z). CI: linter ✅ · linux_64 ✅ · osx_64 ✅ · win_64 ❌ outstanding.
  - [#33753](https://github.com/conda-forge/staged-recipes/pull/33753) — Ctranslate2 suite (head `ctranslate2-suite` sha `4cbc0189`, opened 00:34:29Z). Multi-output libctranslate2 + ctranslate2 (CPU-only, OpenBLAS/Accelerate, no CUDA/MKL).
  - [#33754](https://github.com/conda-forge/staged-recipes/pull/33754) — Faster whisper (head `faster-whisper` sha `9e13e5ac`, opened 00:44:14Z). Sequencing: gated on #33753 landing first; remains draft until then.
- Effort complete: **2026-06-17 03:25Z** (Wave D smoke-test pass + retro shipped + commit pushed).
