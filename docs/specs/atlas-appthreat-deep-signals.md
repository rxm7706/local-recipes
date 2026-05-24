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
| Surface area | `conda-forge-expert` skill — schema v23 → v24 migration adding 3 new side tables (`epss_scores`, `cwe_categories`, `package_hardening`); 2 new atlas phases (T, U); Phase G + G' overlay enhancements for CWE rollup + withdrawn filter (no new phases for those); 2 new fetcher CLIs (`fetch-epss`, `fetch-cwe-catalog`); 1 new admin CLI (`blint-channel-top-n`); persona profile integration |
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

### Wave C — Phase T (blint) + Phase U (EPSS overlay phase) (~5 stories)

| ID | Story | Effort |
|---|---|---|
| S11 | `phase_t_blint_hardening` — local mode (scan `build_artifacts/`); writes per-(conda_name, version, subdir) rows. Imports `blint` lazily; graceful skip if not installed | L |
| S12 | `phase_t_blint_hardening` — admin top-N mode (download top-N from anaconda.org, blint, populate). Reuses Phase F's anaconda.org URL resolution; per-package concurrency from `_http.py` | L |
| S13 | `phase_u_epss_overlay` — pure-SQL backfill when `package_version_vulns` has fresh CVE-list data; falls back to vdb re-scan otherwise. Tunables documented | M |
| S14 | `tests/unit/test_phase_t_blint.py` — ~6 tests: local-mode fixture with sample `.conda`, hardening-score computation, top-N candidate query | M |
| S15 | `tests/unit/test_phase_u_epss.py` — ~5 tests: pure-SQL backfill, missing-epss-scores graceful degrade, max-EPSS computation across CVE list | M |

### Wave D — CLI flags + profile integration + closeout (~5 stories)

| ID | Story | Effort |
|---|---|---|
| S16 | CLI flag additions: `staleness-report --by-epss / --has-cwe / --active-only`; `my-feedstocks --epss --cwe --hardening`; `cve-watcher --epss-threshold`; `detail-cf-atlas` auto-renders new rows | M |
| S17 | Persona profile updates in `bootstrap_data.py`: admin enables Phase T top-N + U + fetch-epss + fetch-cwe-catalog; maintainer enables Phase T local + U + fetch-epss; consumer enables U only if epss_scores pre-populated | M |
| S18 | Closeout: CHANGELOG v8.6.0 entry covering all four signal additions + cdxgen ruling rationale; SKILL.md atlas-section bumped to v24; `skill-config.yaml` 8.5.3 → 8.6.0; `reference/atlas-actionable-intelligence.md` catalog flips (4 rows: EPSS / CWE / hardening / active-only); CFE retro per CLAUDE.md Rule 2 | M |

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
