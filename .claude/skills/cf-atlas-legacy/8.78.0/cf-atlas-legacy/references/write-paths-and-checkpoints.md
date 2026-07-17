# Full Write Paths and Checkpoints

Citations at commit `b18cbb5`. `CFA` = conda_forge_atlas.py, `BD` = bootstrap_data.py,
`AP` = atlas_phase.py (all under `.claude/skills/conda-forge-expert/scripts/`).

## Contents

- [The 6 cf_atlas.db write paths](#the-6-cf_atlasdb-write-paths)
- [Checkpoint machinery](#checkpoint-machinery)
- [TTL machinery](#ttl-machinery)
- [Bootstrap sub-step driver](#bootstrap-sub-step-driver)
- [Profiles](#profiles)
- [Timeouts — the 1800 s cap](#timeouts--the-1800-s-cap)

## The 6 cf_atlas.db write paths

Spec § 3.3 "Write paths — exactly 6 writers" (spec:200–208):

1. **`conda_forge_atlas.py`** — sole top-level writing entry point is `cmd_build`
   [SRC:CFA:L8757] (`open_db` L8773 + `init_schema` L8774 + phase pipeline
   L8778–8779 + `write_meta` INSERT OR REPLACE into `meta` L8662–8664; dry-run meta
   L8805–8807). `run_single_phase` L8716 writes via whichever phase it runs but takes
   a caller-supplied conn (invoked by atlas_phase.py, writer #2). `cmd_query` L8829
   and `cmd_stats` L8847 are SELECT-only; `export_json` L8668 writes a JSON file, not
   the DB. Shared helpers `phase_r_upsert_one` L8198 + `apply_readiness_scores` L8484
   are the add-handoff single-write-path (spec:201–203).
2. **`atlas_phase.py` TTL reset** — CLI entry `atlas_phase.main` [SRC:AP:L72]; `_reset_ttl` [SRC:AP:L54]:
   `UPDATE packages SET {col} = NULL WHERE {scope}` per `_TTL_GATED` tuple (L63–66),
   commit L68; empty spec list → no-op L59–61. Also drives writes indirectly via
   `cfa.init_schema` (L97) + `cfa.run_single_phase` (L106–107).
3. **`mapping_gap.py`** — CLI entry `mapping_gap.main` [SRC:mapping_gap.py:L584]; `g10_spelling` no-clobber writeback: `WRITEBACK_SQL`
   [SRC:mapping_gap.py:L76–82], applied by `write_recoveries` L360–376 only under
   `--write` (L551–553, flag L588–589); DRY-RUN default opens read-only L605–609.
4. **`cisa_kev_fetcher.py`** — `cisa_kev` table: `upsert_kev_rows` `INSERT OR REPLACE` (13 columns)
   [SRC:cisa_kev_fetcher.py:L103–110], txn L111–142; source
   `CISA_KEV_URL` L42–44 via `fetch_with_fallback` L62–75; ransomware tri-state
   L51–59; `--dry-run` skips write L178–180; schema delegated to
   `atlas.open_db` + `atlas.init_schema` L182–188; CLI entry `cisa_kev_fetcher.main` L246.
5. **`epss_fetcher.py`** — `epss_scores` table: `upsert_epss_rows` `INSERT OR REPLACE`
   [SRC:epss_fetcher.py:L124–127], per-row L145–148, txn L131–152; percentile
   normalized 0–1 → 0–100 at store (`_normalize_percentile` L60–62, applied L141);
   score stored raw 0–1 L140; source `EPSS_URL` (epss.empiricalsecurity.com) L57;
   snapshot-date from `score_date:` header L65–79; CLI entry `epss_fetcher.main` L245.
6. **`cwe_catalog_fetcher.py`** — `cwe_categories` table: `upsert_cwe_rows` `INSERT OR REPLACE`
   [SRC:cwe_catalog_fetcher.py:L126–129], per-row L152–155, txn L131–159; seed
   `data/cwe_categories_seed.json` (L56, loader L59–69); seed-miss → `Other`
   L146–151; CWE-ID canonicalization L139–143; source `CWE_URL` 1000.csv.zip
   Research Concepts L55 (corrects the parent spec's `2000.csv.zip` — note L13–16);
   CLI entry `cwe_catalog_fetcher.main` L250. Loaded into the atlas by
   `_load_cwe_categories` [SRC:CFA:L3700] for the Phase G/G' CWE overlay.

Phase G / G' overlay the three fetcher tables at build time (spec:206–208;
overlay loads [SRC:CFA:L3854–3856] and L6886–6888).

**bootstrap_data.py is NOT a 7th writer** — it performs no SQLite writes itself; its
two DB touches are read-only (`_auto_detect_phase_l_sources` opens `mode=ro`
[SRC:BD:L348]; `print_status` L563 issues only SELECTs L580–584/L623–632). All
mutation is delegated to `build-cf-atlas` subprocesses. The destructive path it DOES
own is filesystem-level: `hard_reset` L513 (rmtree + recreate DATA_DIR L552–553,
preserving `cache/parquet` via `_PRESERVED_RELATIVE_PATHS` L464).

## Checkpoint machinery

- `phase_state` table [SRC:CFA:L274] — columns `phase_name` PK, `run_started_at`,
  `last_completed_cursor`, `items_completed`, `items_total`, `run_completed_at`,
  `status`, `last_error` (L275–283; resume-cursor rationale L270–273).
- `load_phase_checkpoint(conn, phase_name)` [SRC:CFA:L3989] — most recent row or None (query L3999).
- `save_phase_checkpoint(conn, phase_name, *, cursor=None, ..., status="in_progress")`
  [SRC:CFA:L4005] — UPSERT (INSERT ... ON CONFLICT L4024–4028) with auto-commit "so
  the checkpoint survives an interrupt" L4015–4017.
- Direct page-level checkpoint writes also at L4890 (Phase H) and L5481 (Phase K),
  best-effort (L4884 comment).

## TTL machinery

- `_TTL_GATED` [SRC:AP:L44] (comment L37–43):
  `"F": [("downloads_fetched_at", "conda_name IS NOT NULL")]` L45;
  `"G": [("vdb_scanned_at", "conda_name IS NOT NULL")]` L46;
  `"G'": []` (resets via `package_version_vulns` row absence) L47;
  `"H": [("pypi_version_fetched_at", "pypi_name IS NOT NULL")]` L48;
  `"K": [("github_version_fetched_at", "conda_name IS NOT NULL")]` L49;
  `"L": []` (per-registry `*_fetched_at`; reset is per-source) L50.
- Reset semantics: timestamps NULLed, nothing deleted — `_reset_ttl` L54–69.
- CLI: `atlas-phase PHASE_ID [--reset-ttl] [--list]` (docstring L10–17; ids L13;
  `main` L72; `open_db`+`init_schema` L96–97; `run_single_phase` + JSON dump L106–107).

## Bootstrap sub-step driver

Ordered sub-steps in `main()` [SRC:BD:L765], executed via `_run` (L430,
`subprocess.run` L449, env = full parent copy + overrides L444–446):

1. mapping cache (`update-mapping-cache`) L880–885
2. CVE DB (`update-cve-db`) L888–892
3. CISA KEV (`fetch-cisa-kev`, gated `BOOTSTRAP_FETCH_CISA_KEV`) L894–899
4. EPSS (`fetch-epss`, gated `BOOTSTRAP_FETCH_EPSS`) L901–906
5. CWE catalog (`fetch-cwe-catalog`, gated `BOOTSTRAP_FETCH_CWE_CATALOG`) L908–913
6. vdb (`pixi run -e vuln-db vdb-refresh`) L915–920
7. cf_atlas build L947–1005 — the v8.22.0 4-sub-step split `_step_cf_atlas_split`
   (L672) → `_run_cf_atlas_subprocess` (L641; command
   `pixi run -e local-recipes build-cf-atlas` L656, `--only`/`--skip` L660–662):
   `cf-atlas-core` L703–719 (**HARD** — failure short-circuits F/K/N L717–719),
   `cf-atlas-F` L722–731 (SOFT), `cf-atlas-K` L734–743 (SOFT), `cf-atlas-N`
   L746–760 (SOFT, gh-gated). Legacy monolithic escape hatch when
   `BOOTSTRAP_CF_ATLAS_TIMEOUT` set L967–978. Aggregate status L988–1005.
8. Phase G' (gated `--with-per-version-vulns`, vuln-db env, `PHASE_GP_ENABLED=1`) L1007–1014
9. Phase N L1016–1045 — skipped when `phase_n_ran_in_step4` (L1028–1036)

Summary + exit code L1047–1072 (soft ⚠ not counted as failure L1063–1066).

## Profiles

`PROFILES` [SRC:BD:L221] (comment L211–220):

- **maintainer** L222–249: `PHASE_E_ENABLED=1` L223, `PHASE_N_ENABLED=1` L224,
  `PHASE_F_SOURCE=auto` L225, 3× `BOOTSTRAP_FETCH_*=1` L229–231;
  `PHASE_H_SOURCE` deliberately unset (L232–237); `PHASE_N_MAINTAINER` +
  `PHASE_L_SOURCES` dynamic (L238–239, via `_auto_detect_gh_user` L294 and
  `_auto_detect_phase_l_sources` L328).
- **admin** L250–278: channel-wide Phase N (L252, no maintainer),
  `PHASE_F_SOURCE=s3-parquet` L262, fetchers L265–267, `PHASE_P_ENABLED=1` L274,
  `PHASE_R_ENABLED=1` L275.
- **consumer** L279–290: `PHASE_N_ENABLED=""` L281, `PHASE_F_SOURCE=s3-parquet` L282,
  `PHASE_H_SOURCE=cf-graph` L283, `PHASE_D_UNIVERSE_DISABLED=1` L284,
  `PHASE_P/Q/R_DISABLED=1` L287–289 (air-gap friendly).

Resolution: `_resolve_profile_env` L388, merged `os.environ.setdefault` L836–837
(explicit env wins); profile implies `--gh` L838–839; maintainer lifts
`PHASE_N_MAINTAINER` L840–846; consumer pins `phase_h_source=cf-graph` L847–849.
No-profile advisory `_print_no_profile_advisory` L1075 (called L1067).

## Timeouts — the 1800 s cap

- `_DEFAULT_TIMEOUTS` dict [SRC:BD:L153–194] with `"cf_atlas_core": 1800` at L166;
  module-docstring documentation L64–67; known-undersized note (cold-run Phase R
  abort, observed 2026-07-09) L170–182.
- Override: `BOOTSTRAP_CF_ATLAS_CORE_TIMEOUT` (generic `BOOTSTRAP_STEP_TIMEOUT`
  pattern) via `_timeout_for` L197–208.
- Enforcement: `timeout=_timeout_for("cf_atlas_core")` L707 →
  `subprocess.run(cmd, env=env, timeout=timeout)` L449, `TimeoutExpired` L450–452.
