---
status: shipped
implemented_by: bmad-quick-dev
shipped_ref: "v8.19.0"
spec_updated: 2026-06-20
---
# Tech Spec: Atlas Phase F+ Wave 3 — `platform_breakdown` / `pyver_breakdown` / `channel_split` CLIs + MCP

> **BMAD intake document.** Focused execution scope for `bmad-quick-dev`
> (Quick Flow track — well-bounded, single-skill, ~6 stories).
>
> ```
> run quick-dev — implement the intent in docs/specs/atlas-phase-f-wave3-cli-surface.md
> ```
>
> **Parent specs** (canonical detail):
> - [`docs/specs/atlas-phase-f-s3-backend.md`](atlas-phase-f-s3-backend.md) — full Wave 0–3 design (Stories 11/12/13/14 are Wave 3).
> - [`docs/specs/atlas-phase-f-wave2-richer-metrics.md`](atlas-phase-f-wave2-richer-metrics.md) — Wave 2 brief (shipped as v8.18.0).
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

- [`docs/specs/atlas-phase-f-s3-backend.md`](atlas-phase-f-s3-backend.md) — Wave 0-3 full design. Wave 3 = Stories 11/12/13/14.
- [`docs/specs/atlas-phase-f-wave2-richer-metrics.md`](atlas-phase-f-wave2-richer-metrics.md) — Wave 2 brief (shipped v8.18.0).

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
