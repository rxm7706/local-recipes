# Version History

## TL;DR — what's new in the latest release

**v8.1.0** (May 15, 2026) — PyPI intelligence layer. 5 new phases (O/P/Q/R/S) + new `pypi-intelligence` CLI + MCP tool + persona-profile integration. **MINOR bump** — fully additive: no schema deletions, no existing-CLI changes, no breaking FR/NFR. Driven by `docs/specs/atlas-pypi-intelligence.md` via `bmad-quick-dev`. Architecture lock (per spec frontmatter): `pypi_universe` stays reference-data-only (3 cols forever); all enrichment in a new `pypi_intelligence` side table joined on `pypi_name`.

### Schema v22 — additive only

Three new objects, all `IF NOT EXISTS`-guarded so v21 atlases upgrade on next `init_schema` without operator action:

- **`pypi_intelligence`** — 35-column side table (Tier 1: activity_band + serial deltas; Tier 2: downloads_30d/90d + cross-channel `in_*` BOOLs; Tier 3: license/requires_python/classifiers/repo_url/wheel coverage/packaging_shape; Tier 4: conda_forge_readiness + recommended_template; Tier 5: staged_recipes_pr_url + operator `notes`). PK = pypi_name. Indexed on activity_band, downloads_30d, conda_forge_readiness, in_bioconda, packaging_shape.
- **`pypi_universe_serial_snapshots`** — `(pypi_name, last_serial, snapshot_at)` PK. Powers Phase O's delta-based activity classification. Retention 90 d default (`PHASE_O_SNAPSHOT_RETAIN_DAYS`).
- **`v_pypi_candidates`** view — pre-joins universe + intelligence + packages LEFT-OUTER for the new CLI's read path. Surfaces conda_name (NULL = pypi-only candidate).

### Phase O — activity band classification (no HTTP)

Runs immediately after Phase D. Writes a daily snapshot of `pypi_universe.last_serial`, prunes retention-aged rows, then computes per-name `serial_delta_7d` / `serial_delta_30d` via temp-table CTE and classifies into `hot` / `warm` / `cold` / `dormant`. First-run = all-dormant (no historical data). Two-step upsert preserves Phase P/Q/R/S columns on existing intelligence rows.

Tunables: `PHASE_O_DISABLED`, `PHASE_O_HOT_THRESHOLD=5`, `PHASE_O_WARM_THRESHOLD=5`, `PHASE_O_SNAPSHOT_RETAIN_DAYS=90`.

### Phase P — BigQuery PyPI downloads (opt-in, admin profile)

Lazy-imports `google.cloud.bigquery` (not in local-recipes env by default; operators add via `pixi add google-cloud-bigquery`). Three-layer gate: PHASE_P_DISABLED > PHASE_P_ENABLED required > library importable + BQ client init. Single project-level aggregation query against `bigquery-public-data.pypi.file_downloads` for the last 90 days (~30 GB scanned; well within 1 TB/month free tier). Default cadence monthly via `PHASE_P_TTL_DAYS=30`. Per-version granularity deferred to v8.2.0 (per spec Q2 resolution — per-version would 200× the scan cost and blow the BQ free tier).

### Phase Q — Cross-channel presence (default-on)

Bulk-fetches `current_repodata.json` from bioconda / pytorch / nvidia / robostack-staging via the new `resolve_anaconda_channel_urls` resolver in `_http.py` (with `<CHANNEL>_BASE_URL` JFrog mirror env support). PEP 503-canonical name matching on both sides via the new `_pep503_canonical` helper. Per-channel error isolation — one channel's 5xx doesn't stop the others. Flips `in_<channel> = 1` on matches and back to 0 on drop-off. Bulk-index ecosystems (homebrew/nixpkgs/spack/debian/fedora) have columns in `pypi_intelligence` but implementations are stretch goals deferred to v8.2.0.

Tunables: `PHASE_Q_DISABLED`, `PHASE_Q_TTL_DAYS=7`, `<CHANNEL>_BASE_URL` per-channel mirror env.

### Phase R — Per-project JSON enrichment (opt-in, admin profile)

Bounded by `PHASE_R_CANDIDATE_LIMIT=5000`. Candidate slice SQL: pypi-only rows ordered by `last_serial DESC`, excluding TTL-fresh (`json_fetched_at < now - PHASE_R_TTL_DAYS×86400`). Worker pattern reuses `_phase_h_fetch_one`'s shape (3-attempt retry + Retry-After + ±25% jitter; default concurrency 3). Per fetched row parses license / requires_python / project_urls / classifiers / wheel coverage and stores raw classifier list + wheel platforms + python tags as JSON. Computes `packaging_shape` via deterministic classifier: pure-python / rust-pyo3 (maturin or `Programming Language :: Rust` classifier) / cython (Cython in requires_dist) / c-extension (cp3X ABI tags in wheel filenames) / unknown. License normalization via `_normalize_license_to_spdx` covering MIT, Apache, BSD-{2,3}-Clause, ISC, GPL/LGPL/AGPL/MPL variants, Unlicense, CC0, Zlib, PSF.

Cold-cost at concurrency=3: ~28 min for the top-5k slice. Warm-daily TTL gate keeps re-fetches small.

### Phase S — Computed scores (default-on, pure SQL)

Reads upstream Tier 1+3 columns and writes Tier 4 (`conda_forge_readiness` 0-100 composite + `recommended_template` full path). 6-component weighted formula:

- license_ok × 25 (license_spdx in OSI-approved set)
- requires_python_ok × 20 (>=3.10 explicit OR NULL = unspecified)
- has_repo × 15 (repo_url populated)
- recent_release × 15 (latest_upload_at within 2 years)
- has_sdist × 10
- packaging_shape_ok × 15 (pure-python/rust-pyo3/cython=full; c-extension=half=7; else 0)

`recommended_template` maps packaging_shape → `templates/python/{recipe.yaml | maturin-recipe.yaml | compiled-recipe.yaml}` (full paths so consumers can directly invoke conda-forge-expert with the template, per spec Q3 resolution).

### New `pypi-intelligence` CLI + MCP tool

Reads `v_pypi_candidates` with rich filter composition: `--not-in-conda-forge`, `--activity hot|warm|cold|dormant`, `--license-ok`, `--noarch-python-candidate`, `--min-downloads N`, `--score-min N`, `--in-{bioconda,pytorch,nvidia,robostack,...}`, `--sort-by score|downloads|serial|name`, `--limit N`, `--json`. Default surfaces top-25 pypi-only candidates by `conda_forge_readiness DESC` — the flagship admin "what should I package next?" query.

`pypi_intelligence` MCP tool exposes the same filter surface. Pixi task `pypi-intelligence` wired in `pixi.toml`; canonical impl + thin wrapper + meta-test SCRIPTS entry per the three-place rule.

### Persona profile integration

| Profile | Phase O | Phase P | Phase Q | Phase R | Phase S |
|---|---|---|---|---|---|
| `maintainer` | ✓ | — | ✓ | — | ✓ (no-op without R data) |
| `admin` | ✓ | ✓ (BQ creds-gated) | ✓ | ✓ | ✓ |
| `consumer` | ✓ | ✗ | ✗ | ✗ | ✓ (no-op without R data) |

### MIGRATION_NOTES (v21 → v22)

Existing v21 atlases auto-migrate on next `init_schema`:

- New tables `pypi_intelligence`, `pypi_universe_serial_snapshots` created via `CREATE TABLE IF NOT EXISTS`
- New view `v_pypi_candidates` created via `CREATE VIEW IF NOT EXISTS`
- `packages` table is NOT modified
- `pypi_universe` table is NOT modified (stays 3 cols by design)

No operator action; no behavior change for existing CLIs. The new `pypi-intelligence` CLI is the only new operator surface.

### Test totals

51 new unit tests across 5 new test modules (test_phase_o_snapshots.py = 10, test_phase_p_bigquery.py = 4, test_phase_q_cross_channel.py = 12, test_phase_r_enrichment.py = 18, test_phase_s_scores.py = 13, test_pypi_intelligence_cli.py = 10) + meta-test `SCRIPTS` list updated with `pypi_intelligence.py`. Skill suite: **1,064 passing** (was 1,039 post-v8.0.2; +25 new across Wave C+D after Wave A+B's +10+16 = +26 went in earlier commits = +51 total v8.1.0 = ✓). No regressions.

### Open questions resolution (all pre-locked before BMAD intake)

All 8 spec open questions resolved 2026-05-14:

1. `notes` column for hand-curated overrides → **yes**, added to schema.
2. BigQuery granularity → **project-level**, per-version deferred to v8.2.0.
3. `recommended_template` → **full path** (e.g., `templates/python/recipe.yaml`).
4. Non-PyPI ecosystem heuristic → **URL-pointer** (files.pythonhosted.org / pypi.org); columns exist but stretch implementations deferred to v8.2.0.
5. `staged_recipes_pr_url` source → **fallback chain** (local fork default; `PHASE_R_GH_LOOKUP=1` opt-in for GitHub Search).
6. Snapshot retention → **90 days** default, env-tunable.
7. Readiness formula → **raw weights** (percentile rank deferred to v8.2.0).
8. PRD bump → **MINOR** (v1.2.0 → v1.3.0) — additive, no breaking FR/NFR.

### Out of scope (deferred)

- Bulk-index ecosystems (homebrew/nixpkgs/spack/debian/fedora) — columns exist; implementations stretch to v8.2.0.
- Per-version BigQuery granularity — would blow free tier; v8.2.0 if operator demand surfaces.
- `bus_factor_proxy` + `dependency_blast_radius` — columns exist but populated NULL in v8.1.0 (needs deps.dev / repo-contributor data).
- Auto-recipe-generation from `recommended_template` — column is a suggestion only.
- BigQuery service-account provisioning automation — operator BYO via `GOOGLE_APPLICATION_CREDENTIALS`.
- `conda_forge_readiness_percentile` — raw-weight only in v8.1.0; percentile derived column is v8.2.0.

---

**v8.0.2** (May 14, 2026) — First live `bootstrap-data --profile maintainer` run end-to-end surfaced two follow-up bugs in v8.0.1's profile plumbing. Step 4 (cf-atlas build) completed correctly — Phase H stamped 19,386 rows in ~12.6 min, Phase N fetched 722 feedstocks for `rxm7706`, atlas reached steady state (Phase H eligibility dropped 19,442 → 4). Step 6 (Phase N redundant re-invocation) crashed at `PHASE_H_SOURCE='auto' is not one of pypi-json, cf-graph`.

### Root causes

1. **`PROFILES` injected an atlas-illegal value.** `"PHASE_H_SOURCE": "auto"` was set on the maintainer + admin profiles. "auto" is a bootstrap-data CLI concept (resolves to `cf-graph` on `--fresh`, else `pypi-json`). The atlas only accepts `pypi-json` or `cf-graph`. `os.environ.setdefault` from `_resolve_profile_env` injected the bogus value, Step 4's `env_overrides` happened to override it with the resolved concrete value, but Step 6's `env_overrides` only set `PHASE_N_ENABLED`/`PHASE_N_MAINTAINER` — Step 6's subprocess inherited `PHASE_H_SOURCE=auto` from `os.environ` and crashed.

2. **Step 6 was structurally redundant under profiles.** With a profile setting `PHASE_N_ENABLED=1` in env, Step 4's `build-cf-atlas` subprocess sees Phase N enabled via env inheritance and already runs Phase N. Re-invoking `build-cf-atlas` in Step 6 to "add Phase N" re-runs every phase — wasteful and the trigger for the crash above.

### Fixes

- **`bootstrap_data.py:PROFILES`** — `PHASE_H_SOURCE` removed from maintainer + admin (atlas default `pypi-json` covers the warm-run case; the bootstrap-data `--phase-h-source` CLI default still resolves `auto` correctly in Step 4's `env_overrides`). Consumer keeps `PHASE_H_SOURCE=cf-graph` (atlas-valid).
- **`bootstrap_data.py` Step 6** — now checks `phase_n_ran_in_step4 = not args.no_cf_atlas and bool(os.environ.get("PHASE_N_ENABLED", "").strip())`. When true and `--gh` is set, prints a skip message instead of re-invoking `build-cf-atlas`. Legacy `--gh` invocations without a profile still run Step 6 as before.
- **`tests/unit/test_persona_profiles.py`** — `test_maintainer_enables_e_and_n` updated to assert `PHASE_H_SOURCE not in env` for maintainer; new `test_maintainer_and_admin_omit_phase_h_source` regression covers the omission for both profiles + the consumer's explicit `cf-graph` value.

### Live verification (post-fix)

- `bootstrap-data --profile maintainer --dry-run`: Step 4 shows `env PHASE_H_SOURCE=pypi-json` (resolved by CLI, not leaked from profile). Step 6 prints the skip message instead of dispatching another subprocess. Summary clean.
- Atlas DB state confirmed steady: `eligible_never_fetched=1, eligible_serial_moved=3, eligible_safety_recheck=0` — 4-row warm-daily working set, exactly the v8.0.0 spec target.

---

**v8.0.1** (May 14, 2026) — Live-DB verification (retro D1/D2) surfaced two bugs in v8.0.0's Wave B + Wave D code; PATCH bump fixes them. Plus the stat-split that Wave B specced but never landed.

### D1 fix — `_auto_detect_phase_l_sources` SQL was malformed

The helper joined `package_maintainers pm ON pm.conda_name = p.conda_name WHERE pm.handle = ?`, but production `package_maintainers(conda_name, maintainer_id)` doesn't have a `handle` column — it joins via `maintainer_id` to a separate `maintainers(id, handle)` table. The test fixture used a 2-table simplification that masked the bug; under live-DB verification the helper would always return `None` for any maintainer because the SQL silently produced no rows. Fix:

- `bootstrap_data.py:_auto_detect_phase_l_sources` now joins the 3-table shape `v_actionable_packages p JOIN package_maintainers pm ON pm.conda_name = p.conda_name JOIN maintainers m ON m.id = pm.maintainer_id WHERE LOWER(m.handle) = LOWER(?)`. The `LOWER()` mirrors `feedstock_health.query`'s case-insensitive handle match (gh handles are case-insensitive on GitHub).
- `tests/unit/test_persona_profiles.py` fixture updated to the production 3-table schema. New `test_maintainer_handle_match_is_case_insensitive` regression.

### D2 fix — Phase H serial-gate missed the entire post-migration working set

Wave B's serial-gate SQL used `pypi_last_serial != pypi_version_serial_at_fetch`. SQL's `X != NULL` evaluates to NULL (falsy in `WHERE`), so when `pypi_version_serial_at_fetch IS NULL` — the state of every row immediately after the v20 → v21 migration adds the column — condition 2 doesn't fire. Live-DB verification showed 9,788 rows (≈ half the working set) would be silently skipped from the first post-migration warm-daily Phase H run. Fix:

- `conda_forge_atlas.py:_phase_h_eligible_pypi_names` SQL: `pypi_last_serial != pypi_version_serial_at_fetch` → `pypi_last_serial IS NOT pypi_version_serial_at_fetch`. `IS NOT` is the NULL-safe form; it returns TRUE when one side is NULL and the other isn't, so post-migration rows with a populated `pypi_last_serial` get re-fetched once to stamp `pypi_version_serial_at_fetch`.
- `tests/unit/test_phase_h_serial_gate.py` adds a `post-migr-f` fixture (`fetched_at=recent, last_serial=700, serial_at_fetch=NULL`) that exercises this case. Without the `IS NOT` fix the test would fail.

### D3 ship — Phase H stat-split (specced in v8.0.0, never implemented)

v8.0.0's CHANGELOG + spec promised "stat reporting splits the eligible count into `eligible_never_fetched`, `eligible_serial_moved`, `eligible_safety_recheck` so operators can see why each row was selected." The code only printed `len(rows)`. Now actually shipped:

- New `conda_forge_atlas.py:_phase_h_eligibility_stats(conn) -> dict` returns the three branch counts via mutually-exclusive SQL. Buckets sum to the eligible-rows count.
- Both `_phase_h_via_pypi_json` and `_phase_h_via_cf_graph` print a `breakdown: never_fetched=X, serial_moved=Y, safety_recheck=Z` line after the eligible-count print, and include the same three keys in the return dict.
- `tests/unit/test_phase_h_serial_gate.py` adds `TestEligibilityStats` (2 fixtures: bucket counts match branch semantics; buckets sum to eligible-rows count).

### Live verification outcome

Against the real 32,053-row v21 atlas (post-migration state) the gate eligibility now reads:

- never_fetched:     9,654
- serial_moved:      9,788  (post-migration NULL-serial-at-fetch — would have been 0 without D2 fix)
- safety_recheck:    0
- **total eligible:  19,442**

First post-v21 Phase H run is heavy (one-time ~30 min wall-clock at concurrency=3) since every row needs its `pypi_version_serial_at_fetch` stamped. After that, warm-daily should drop to the ~30-100 specced.

### Documentation

Retro `_bmad-output/projects/local-recipes/implementation-artifacts/retro-conda-forge-expert-v8.0-2026-05-13.md` updated with D1 + D2 + D3 verification outcomes and the two bugs caught.

---

**v8.0.0** (May 13, 2026) — Structural enforcement + persona profiles. Bundle closes 3 of the 4 v7.9.0 audit follow-ups (A3, A4, A5); A6 deferred after the planned drop discovered actual consumers. **MAJOR** bump because `bootstrap-data --profile maintainer` (new) is the documented default. No invocation breaks; legacy no-flag runs print an end-of-run advisory (silenced via `BUILD_CF_ATLAS_QUIET=1`). Driven by `docs/specs/conda-forge-expert-v8.0.md` via `bmad-quick-dev`.

### Wave A — `v_actionable_packages` view + structural enforcement (A5, shipped)

- Schema **v21** adds `CREATE VIEW v_actionable_packages` encoding the canonical persona-filter triplet (`conda_name IS NOT NULL AND latest_status='active' AND COALESCE(feedstock_archived,0)=0`). 7 phase selectors refactored to `FROM v_actionable_packages` (Phase F, G, G', H, K, L, N). Pre-/post-refactor row sets are identical.
- New `tests/meta/test_actionable_scope.py` parses `conda_forge_atlas.py` and asserts every `SELECT ... FROM packages WHERE ...` either reads the view OR has a `# scope: <reason>` justification comment within 3 lines above. Prevents the kind of drift v7.9.0 had to fix by hand.
- The view + meta-test ship together so future phase authors inherit the enforcement automatically.

### Wave B — Phase H serial-aware eligible-rows gate (A3, shipped)

- Schema v21 adds `pypi_version_serial_at_fetch INTEGER` column + index on `packages`. Phase H's pypi-json worker stamps this on every successful fetch (sourced from the row's current `pypi_last_serial`).
- Phase H eligible-rows SELECT becomes a 3-condition OR: `pypi_version_fetched_at IS NULL` (never fetched) OR `pypi_last_serial != pypi_version_serial_at_fetch` (Phase D detected the upstream serial moved) OR `pypi_version_fetched_at < (now − 30d)` (safety re-check past TTL).
- Stat reporting splits the eligible count into `eligible_never_fetched`, `eligible_serial_moved`, `eligible_safety_recheck` so operators see why each row was selected.
- Net: **warm-daily Phase H drops ~5 min → ~30 s** on a typical day (only the ~30-100 packages whose upstream actually moved get re-fetched). Cold start is unchanged.
- Test: `tests/unit/test_phase_h_serial_gate.py` — 5 fixtures covering each gate branch + the post-fetch write.

### Wave C — `vuln_total` drop (A6, **DEFERRED**)

Wave C was specced to drop the unused `vuln_total` column on the strength of the v7.9.0 audit's "0 consumers" claim. The v8.0.0 implementation audit found that claim was wrong:

- `detail_cf_atlas.py:827` — record display (`c_total = record.get("vuln_total")`)
- `cve_watcher.py:71` — severity-letter column `T` maps to `vuln_total`
- `staleness_report.py:110, 182` — SELECT projection + risk-sort column
- `scan_project.py:1408, 2672, 2690, 3293, 3311` — SBOM `cdx:atlas:vuln_total` enrichment + the atlas-vulns-detected lookup

The column stays. The v7.9.0 retro at `_bmad-output/projects/local-recipes/implementation-artifacts/retro-atlas-pypi-universe-split-2026-05-13.md` has been corrected with the consumer list. A future spec should consolidate the four consumers behind a single accessor and decide whether the persisted column or a computed `vuln_critical + vuln_high + vuln_kev` sum is the right answer — only then is a drop safe.

### Wave D — Persona profiles + auto-detection (A4, shipped)

`bootstrap-data --profile {maintainer,admin,consumer}` ships in `bootstrap_data.py`. The flag injects a bundle of env-var defaults via `os.environ.setdefault` so explicit user env vars and CLI flags always win.

- **`maintainer`**: enables Phase E (`PHASE_E_ENABLED=1`) + Phase N (`PHASE_N_ENABLED=1`); auto-derives `PHASE_N_MAINTAINER` from `gh api user --jq .login` (5 s timeout; graceful degradation to channel-wide on missing-gh / unauth / timeout with a printed warning); auto-restricts `PHASE_L_SOURCES` to populated registries in scope via `v_actionable_packages JOIN package_maintainers WHERE handle=<gh-user>`. Phase F/H source = auto.
- **`admin`**: enables Phase E + channel-wide Phase N (no `PHASE_N_MAINTAINER`). Full Phase L. Auto-source for F + H.
- **`consumer`**: air-gap friendly — `PHASE_F_SOURCE=s3-parquet`, `PHASE_H_SOURCE=cf-graph`, `PHASE_N_ENABLED=""`, `PHASE_D_UNIVERSE_DISABLED=1`.
- **No `--profile`**: today's behavior + end-of-run advisory recommending `--profile maintainer`. Suppress via `BUILD_CF_ATLAS_QUIET=1`. The advisory is the MAJOR-bump signal; once operators report comfort with the documented default, v8.1.0 may silently flip the no-flag invocation to `--profile maintainer`.
- New helpers in `bootstrap_data.py`: `PROFILES` dict, `_auto_detect_gh_user(timeout=5)`, `_auto_detect_phase_l_sources(maintainer, db_path)`, `_resolve_profile_env(profile)`, `_print_no_profile_advisory(profile)`.
- Test: `tests/unit/test_persona_profiles.py` — 19 fixtures covering profile resolution + auto-detect (success/missing/timeout/unauth) + advisory print (print/silent/quiet-env) + Phase L source auto-detection (missing DB / pre-v21 / populated / channel-wide).

### Catalog impact

`reference/atlas-actionable-intelligence.md` flips **5 previously 📋-open Phase-N-gated rows** to ✅ shipped, all because v8.0.0's `--profile maintainer` runs Phase N by default with auto-scoping:

- "Which of my feedstocks have open *human* PRs?" → `feedstock-health --maintainer X --filter open-prs-human`
- "Which of my feedstocks have open issues?" → `feedstock-health --maintainer X --filter open-issues`
- "Which of my feedstocks have CI red on default branch?" → `feedstock-health --maintainer X --filter ci-red`
- "Find abandoned feedstocks" → SQL composite on `gh_pushed_at + latest_conda_upload + bot_version_errors_count` (per-user `contributionsCollection` query still 📋-open enhancement)
- "Maintainer last-active across the channel" → SQL aggregate over `gh_pushed_at` per maintainer (feedstock-push proxy; per-user GitHub-activity API still 📋-open)

Status Summary updated: ~65 shipped (up from ~60), ~6 open (added the `vuln_total` consumer-consolidation + per-user contributionsCollection items), 0 gaps.

### Documentation

- `reference/atlas-phases-overview.md` — at-a-glance index annotated with profile-aware defaults for D / E / F / H / L / N; per-phase "Profile defaults" lines under each of those six phases; new `## Profile Reference (v8.0.0)` appendix with the three-profile matrix + auto-detection + backward-compat notes.
- `reference/atlas-actionable-intelligence.md` — 5 row flips + Status Summary updated to v8.0.0.
- `guides/atlas-operations.md` — single-command refresh quickstart leads with `--profile maintainer`; sample crontab rewritten to profile-driven invocations (daily maintainer + weekly admin); air-gapped section uses `--profile consumer`; recovery table updated for v8.0.0's auto-detect warning behavior.

### MIGRATION_NOTES (v20 → v21)

Existing v20 atlases auto-migrate on next `init_schema`:

- Adds `pypi_version_serial_at_fetch INTEGER` column + index on `packages` (idempotent — guarded by `pragma_table_info('packages')`).
- Creates `v_actionable_packages` view via SCHEMA_DDL `CREATE VIEW IF NOT EXISTS`.
- `vuln_total` column is **NOT** dropped (Wave C deferred — see above).

Migration is self-healing and a no-op on re-run.

The only operator-visible default-behavior change is the documented `bootstrap-data` invocation: the recommended default flipped from no-flag to `--profile maintainer`. No invocation breaks; cron jobs that pinned env vars manually continue to work because explicit env vars win over profile defaults (`os.environ.setdefault` semantics). The legacy no-flag invocation prints an end-of-run advisory; silence via `BUILD_CF_ATLAS_QUIET=1`.

### Test totals

24 new unit tests in v8.0.0 (19 persona profiles + 5 Phase H serial-gate from Wave B's commit `e671ef463d`) on top of Wave A's `v_actionable_packages` view test + `tests/meta/test_actionable_scope.py`. Skill suite: 989 passing (1 pre-existing `test_whodepends_reverse_json` failure unrelated to this work; predates the audit).

### Out of scope (deferred)

- Channel-wide Phase H/N cron operationalization (per-maintainer + admin profiles cover most use cases; full-channel with PAT rotation = separate spec).
- Per-version vdb-history snapshot side table for time-travel CVE queries.
- Multi-output feedstock per-output dep-graph (Phase J extension).
- New MCP tools for persona profiles (`--profile` CLI flag only; MCP exposure is a follow-up).
- Drop or properly-wire `vuln_total` (Wave C — needs consumer consolidation first).
- Per-user `contributionsCollection` query for finer-grained maintainer-activity signal.

Each will get its own quick-dev spec when its trigger fires.

---

**v7.9.0** (May 13, 2026) — Actionable-scope audit closure: phase-by-phase review against `reference/atlas-actionable-intelligence.md` found 4 phases writing data no persona reads. Bundled fix lands as schema v20 + 29 new unit tests + a new `pypi-only-candidates` CLI / MCP tool. Driven by `docs/specs/atlas-pypi-universe-split.md` via `bmad-quick-dev`.

### Phase H — 56× cold-run denominator cut

`_phase_h_eligible_pypi_names` (`pypi-json` path) lacked a `conda_name IS NOT NULL` filter, so it fetched `pypi.org/pypi/<name>/json` for the ~660k `relationship='pypi_only'` rows that Phase D inserted under v19. The downstream `upstream_versions` UPSERT silently discarded every fetched result via its own `conda_name IS NOT NULL` clause — the network round-trip was pure waste.

- Selector now applies the canonical persona-filter triplet `conda_name IS NOT NULL AND latest_status='active' AND COALESCE(feedstock_archived,0)=0` used by Phases F/G/G'/K/L/N. Denominator drops from ~672k → ~12k.
- After the schema v20 migration (below) removes pypi_only rows from `packages`, the structural fix makes the gate naturally correct; the explicit clauses are defense-in-depth.
- Test: `tests/unit/test_phase_h_eligible.py` — 6 fixtures covering pypi_only, archived, inactive, TTL-fresh, no-pypi-name, and the happy path.

### Phase D — split into daily-lean + TTL-gated universe upsert

The legacy v19 Phase D inserted ~660k `pypi_only` rows into `packages` on every build. Refactor into three helpers:

- `_phase_d_update_working_set` (always-on) — updates `pypi_last_serial` on conda-linked rows + discovers name-coincidence matches. Same 40 MB Simple API fetch as before, but no INSERTs.
- `_phase_d_universe_is_fresh` — TTL probe against `MAX(pypi_universe.fetched_at)`.
- `_phase_d_upsert_universe` — bulk UPSERT into the new `pypi_universe` side table when TTL is stale. Idempotent via `ON CONFLICT(pypi_name) DO UPDATE`.

New env tunables: `PHASE_D_DISABLED=1`, `PHASE_D_UNIVERSE_DISABLED=1` (keep the lean path, skip universe), `PHASE_D_UNIVERSE_TTL_DAYS` (default 7d).

### Schema v20 — `pypi_universe` side table + self-healing migration

```sql
CREATE TABLE pypi_universe (
    pypi_name   TEXT PRIMARY KEY,
    last_serial INTEGER,
    fetched_at  INTEGER
);
```

- `init_schema` detects existing `relationship='pypi_only'` rows in `packages` and migrates them to `pypi_universe` in a single transaction (`INSERT OR IGNORE` + `DELETE`). Idempotent — re-running is a no-op.
- Net: ~32k rows in `packages` (down from ~700k), ~800k in `pypi_universe`. `SELECT COUNT(*) FROM packages` finally returns an honest number. `detail-cf-atlas <name>` stops returning confusing pypi-only "matches."
- Tests: `tests/unit/test_schema_v20_migration.py` — migration correctness, idempotency, fresh-v20 state.

### Phases J + M — archived-feedstock filter at write site

Phase J wrote dependency edges from archived feedstocks into `dependencies` (polluting `whodepends --reverse`); Phase M wrote bot-status columns to archived rows that `feedstock-health` already filtered out at read time. Both now apply the canonical triplet at the write site:

- Phase J builds an `inactive_feedstocks` skip-set from `packages` before opening the cf-graph tarball; reports `skipped_inactive_feedstocks` in stats.
- Phase M's `rows_to_process` SELECT gains `AND latest_status='active' AND COALESCE(feedstock_archived,0)=0`.
- Test: `tests/unit/test_phase_j_m_archived.py` — 2 fixtures with mixed active + archived + inactive cases.

### New CLI / MCP tool — `pypi-only-candidates`

Reads the `pypi_universe LEFT JOIN packages` to surface admin-persona "what's on PyPI but not on conda-forge" candidates. Ordered by `last_serial DESC` (newest/most-active first). Flags: `--limit`, `--min-serial`, `--json`. Empty-universe state prints an actionable hint to run `atlas-phase D`. Three-place rule applied: canonical impl + thin wrapper + `pixi.toml` task + meta-test SCRIPTS entry. MCP tool exposed via `conda_forge_server.py`. Test: `tests/unit/test_pypi_only_candidates.py`.

### Catalog impact

`reference/atlas-actionable-intelligence.md` § Channel Health: new row "What's on PyPI but not on conda-forge? (candidate-list)" → ✅ shipped (v7.9.0). Previously a 📋-open SQL-only item.

### Test totals

29 new unit tests (Phase H = 6, Phase J + M = 2, schema v20 = 3, Phase D split = 11, pypi-only-candidates = 7). Plus the meta-test (`test_all_scripts_runnable.py`) gains a `pypi_only_candidates.py` entry. All 432 tests pass after this change (403 prior + 29 new); 1 pre-existing failure (`test_whodepends_reverse_json`) is unrelated and predates the audit.

### Out of scope (deferred specs)

- Persona-aware default profiles for `build-cf-atlas` (E default-on, N auto-scoped).
- `v_actionable_packages` SQL view as a structural enforcement.
- Phase H `pypi_last_serial` freshness-gate (depends on this spec landing first).
- Dropping the unused `vuln_total` column.

Each will get its own quick-dev spec.

---

**v7.8.1** (May 12, 2026) — Audit close-out pass: every remaining HIGH / MEDIUM / LOW finding from the v7.8.0 deep audit is now addressed or explicitly justified as intentional. 44 new unit tests; 403 total tests passing across the CFE suite. Follows the patterns established in `reference/atlas-phase-engineering.md` (added in v7.8.0).

### Phase H — same rate-limit-safety pattern as Phase F

The audit's last HIGH-severity item. Phase H's pypi-json default path used 8 worker threads against pypi.org's documented ~30 req/s per-IP ceiling, with `time.sleep(2 ** attempt + 1)` as the only 429 handling and no `Retry-After` parsing.

- `_phase_h_fetch_one` now honors the server's `Retry-After` header on 429 / 503 via the shared `_parse_retry_after` helper (capped at 60s). On other transient failures: exponential backoff + ±25% jitter so the worker pool doesn't re-hit pypi.org in lockstep.
- Default `PHASE_H_CONCURRENCY` lowered **8 → 3** to stay under pypi.org's per-IP rate ceiling. Override-friendly for trusted setups.
- `phase_h_pypi_versions` docstring updated with the new defaults and a pointer to the `PHASE_H_SOURCE=cf-graph` escape hatch for cold-start backfills (which sidesteps pypi.org entirely).

### OSV — air-gap parity for vulnerability scanning

Both ends of the OSV pipeline were hardcoded; air-gap deployments couldn't run vulnerability scans at all.

- `vulnerability_scanner.py`: new `OSV_API_BASE_URL` env var via `_osv_api_base()` + `_osv_querybatch_url()` helpers. Live caller resolves URL at request time so env changes take effect without re-importing.
- `cve_manager.py`: new `OSV_VULNS_BUCKET_URL` env var via `_osv_vulns_bucket_base()` + `_osv_ecosystem_zip_url(eco)`. `ECOSYSTEMS_TO_FETCH` switched from dict (with baked URLs) to tuple of ecosystem names; URL is composed per-iteration.
- 8 new tests across `TestOsvApiBase` (4) and `TestOsvVulnsBucketUrl` (4): default public hosts, env redirects, trailing-slash strip, empty-string fallback.

### GitLab / Codeberg / GitHub-API resolvers — self-hosted-friendly Phase K

Phase K's REST tail still hardcoded `gitlab.com/api/v4` and `codeberg.org/api/v1`. The GitHub GraphQL endpoint was also hardcoded — earlier deferred on GHES grounds, but a single env var DOES work for GHES since the `/graphql` endpoint lives under the same `/api` root as REST.

- `_http.py` gains three new resolvers, same shape as `resolve_maven_urls` (path-suffix arg, list return):
  - `resolve_github_api_urls(path_suffix="")` — `GITHUB_API_BASE_URL` → `https://api.github.com`. Covers BOTH REST and GraphQL under a single env var (set to `https://<ghes>/api`).
  - `resolve_gitlab_api_urls(path_suffix="")` — `GITLAB_API_BASE_URL` → `https://gitlab.com/api/v4`. Self-hosted GitLab CE/EE has identical path layout.
  - `resolve_codeberg_api_urls(path_suffix="")` — `CODEBERG_API_BASE_URL` → `https://codeberg.org/api/v1`. Forgejo + self-hosted Gitea share the API.
- `_phase_k_github_graphql_batch` endpoint resolved via `_resolve_github_api_urls("graphql")[0]`.
- `_phase_k_fetch_one` GitHub/Codeberg/GitLab REST branches all consult the matching resolver.
- 11 new tests across the three resolver classes.

### Phase E — cf-graph cache TTL is now env-tunable

The cache TTL was hardcoded at 1 day; weekly-cron operators were re-downloading the ~150MB archive every run for no information gain.

- New `ATLAS_CFGRAPH_TTL_DAYS` env var (default `1.0`, float-parseable for fractional days). Invalid values silently fall back to the default. Cache-hit log message now includes the active TTL so operators see why a re-download was skipped or fired. Phases J and M reuse the same cache, so the TTL is shared across them.

### Phase N — rate-limit detection on the `gh api graphql` subprocess

Phase N called `gh api graphql` as a subprocess and treated any non-zero exit as a permanent failure. Transient rate-limit errors then baked into the checkpoint as "gh api failed", costing more quota every subsequent run to re-fetch the same already-failed rows.

- New `_GH_RATE_LIMIT_INDICATORS` tuple — lowercased substrings: `"api rate limit exceeded"`, `"secondary rate limit"`, `"you have exceeded a rate limit"`, `"abuse detection mechanism"`.
- New `_is_gh_rate_limit_stderr(stderr)` helper — case-insensitive substring match.
- `_phase_n_query_batch` now retries up to 3 attempts when stderr matches a rate-limit indicator. Backoff is more patient than Phase F/H (30s/60s base vs `2^attempt+1`) because GitHub's secondary-limit windows are minutes, not seconds. ±25% jitter applies.
- 6 new tests covering primary / secondary / abuse-detection wording, case-insensitivity, unrelated errors, and empty-stderr safety.

### Phase C — incremental commits

The parselmouth-join loop wrapped ~12k UPDATEs in a single `BEGIN TRANSACTION ... COMMIT`. Mid-loop interrupt rolled back everything.

- Now commits every 500 entries. UPDATEs are idempotent (UPDATE-by-conda_name, no UNIQUE violations on re-run), matching the pattern already used in Phase B5 / E / M.

### Phase B6 / J — intentional-design documentation

The audit flagged these as Low-severity monolithic transactions. Closer inspection: both are intentional, not bugs.

- **Phase B6** (`phase_b6_yanked_detection`): issues 3 bulk UPDATEs (no per-row loop), runs in <1s. Mid-statement interrupt is virtually impossible; re-running is free. Comment added so the next auditor doesn't re-flag it.
- **Phase J** (`phase_j_dependency_graph`): `DELETE FROM dependencies` at transaction start gives the table full-snapshot semantics — consumers never see a partial dependency graph. Switching to incremental commits would leak partial graphs between an interrupt and the next re-run. The proper fix would be a staging-table swap, but for a Low-severity finding with a cheap (~2 min) re-extract from a local cache, that's disproportionate. Comment added.

### `fetch_to_file_resumable` + cve_manager 4 GB Range/resume

The OSV PyPI `all.zip` is ~4 GB. The previous `requests.get(url).content` pattern loaded the entire response into memory and OOMed under tight container limits; a dropped connection at 95% restarted from byte 0.

- New `_http.fetch_to_file_resumable(target, urls, *, chunk_size, timeout, ...)` helper:
  - Streams response body to a `.part` sibling of `target` in chunks (default 1 MB).
  - On retry: reads `.part.stat().st_size` and sends `Range: bytes=<existing>-`.
  - Handles **206 Partial Content** (append + resume), **200 OK to a Range request** (server ignored Range → restart from 0), and **416 Range Not Satisfiable** (stale `.part` → discard + retry from 0).
  - Atomic finalize via `os.replace(.part, target)` so consumers never see a half-written file.
  - Per-URL fallback chain; auth headers via `make_request`; exponential backoff.
- `cve_manager.fetch_and_unzip` rewired to use the helper:
  - Streams the OSV zip to `<DATABASE_DIR>/_downloads/<basename>` with 4 MB chunks.
  - Decompresses from the on-disk file via `zipfile.ZipFile(target_path)` + `z.open(filename)` for per-file streaming reads — no more `io.BytesIO(response.content)` materialization of the full 4 GB in RAM.
  - On corrupt-zip detection: unlinks the cached file so the next run does a clean re-download.
  - Falls back to a streaming `requests` path if `_http.py` isn't importable.
  - Removed now-unused `io` import.
- 7 new tests in `TestFetchToFileResumable`: fresh download, resume from 206, server-ignores-Range restart, 416 retry, parent-dir auto-create, all-URLs-exhausted, multi-chunk read.

### inventory_channel — intentional in-memory + comment

The audit's last Range/resume finding. `_fetch_url_or_path` returns `bytes` and loads the full body into RAM. For the in-band repodata.json / parquet use cases (~100 MB max) plus the 24h cache TTL, the failure mode is bounded — interrupted fetches re-run from scratch at most once per day. Migration to `fetch_to_file_resumable` would require changing the function signature from returning `bytes` to returning a `Path`, which is a wider refactor than warranted for the LOW severity. Comment added pointing future callers (any artifact >500 MB) at the resumable helper.

### Why this matters

- **Air-gap parity completed**: the atlas now talks to ZERO public hosts that can't be redirected via an env var. JFrog / Artifactory deployments can route every dependency: conda-forge, PyPI, GitHub (archives + API + GraphQL), GitLab API, Codeberg API, npm, CRAN, CPAN, LuaRocks, crates, RubyGems, Maven, NuGet, S3 parquet, OSV API, OSV vulns bucket, api.anaconda.org.
- **Rate-limit survival completed**: every fanout phase (F / H / K / L / N) now has documented per-host concurrency caps, `Retry-After` parsing (where applicable), and jittered backoff. No HIGH-severity rate-limit findings remain.
- **Range/resume**: the largest single artifact in the atlas (4 GB OSV zip) no longer restarts from 0 on a dropped connection, and its RAM footprint dropped from ~4 GB to ~4 MB per chunk.

### Files touched

- `.claude/skills/conda-forge-expert/scripts/_http.py` — `fetch_to_file_resumable` + 3 new API resolvers.
- `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py` — Phase H rate-limit safety, Phase E TTL override, Phase N rate-limit detection, Phase C incremental commits, B6/J intentional-design comments, Phase K resolver wiring (REST + GraphQL).
- `.claude/skills/conda-forge-expert/scripts/vulnerability_scanner.py` — `_osv_api_base()` / `_osv_querybatch_url()` helpers.
- `.claude/skills/conda-forge-expert/scripts/cve_manager.py` — `_osv_vulns_bucket_base()` / `_osv_ecosystem_zip_url()` helpers + Range/resume download via `_http.fetch_to_file_resumable`.
- `.claude/skills/conda-forge-expert/scripts/inventory_channel.py` — in-memory rationale comment.
- `.claude/skills/conda-forge-expert/tests/unit/test_http_resolvers.py` — 11 resolver tests + 7 resumable-fetch tests (18 new).
- `.claude/skills/conda-forge-expert/tests/unit/test_cve_manager.py` — `TestOsvVulnsBucketUrl` (4 new).
- `.claude/skills/conda-forge-expert/tests/unit/test_vulnerability_scanner.py` — `TestOsvApiBase` (4 new).
- `.claude/skills/conda-forge-expert/tests/unit/test_phase_k_vcs_extraction.py` — Phase N rate-limit + Phase E TTL tests (9 new).
- `.claude/skills/conda-forge-expert/tests/unit/test_phase_f_dispatch.py` — no test changes (Phase H reuses Phase F's `_parse_retry_after` helper).

### Caveats / known limits

- **GitHub Enterprise Server**: `GITHUB_API_BASE_URL=https://<ghes>/api` covers REST + GraphQL. Tested via the resolver chain; not yet exercised against an actual GHES instance.
- **OSV API rate-limit handling**: `vulnerability_scanner.py` still uses `requests.post(...)` without `Retry-After` parsing. The OSV API doesn't currently rate-limit the way GitHub does, so this is unaddressed by design. Watch the OSV docs if behavior changes.
- **`fetch_to_file_resumable` size limit**: the resumable helper streams chunks but reads response status / headers eagerly. For pathological cases where a single chunk read blocks longer than the connection's idle timeout, the worker can stall. This isn't a real issue at 4 GB / 4 MB chunks but documented here for future tuning.
- **`PHASE_L_CONCURRENCY=0` would fully serialize** — handled correctly (clamped to 1 via `max(1, int(...))`). Just noting in case anyone wonders.

### Verification

- **403 unit tests pass** across the full CFE suite (was 359 at start of v7.8.0; +44 since v7.8.0 retro).
- 1 pre-existing xpass marker, no regressions.
- Module imports clean smoke-tested for cve_manager, vulnerability_scanner, conda_forge_atlas after every edit.
- End-to-end smoke confirmed env-var precedence chains for: OSV API + bucket, GitLab/Codeberg/GitHub API, Phase H concurrency, Phase E TTL.
- Resumable-fetch tests cover the four real-world branches (200, 206, 200-to-Range, 416) plus parent-dir auto-create, all-URLs-exhausted, and multi-chunk reads.

---

**v7.8.0** (May 12, 2026) — Atlas hardening pass: enterprise-routing parity across 7 more registries, GraphQL Phase K, Phase F rate-limit safety, per-registry Phase L caps, atomic file writes, and incremental commits across B5/E/E5/M. 39 new unit tests; 368 total tests passing across the CFE suite.

The work landed across five waves, each addressing one of the "Top 5 next fixes" from a deep audit of `conda_forge_atlas.py` + sibling scripts that surfaced after the v7.7.2 4,400-row Phase K rate-limit incident. All five themes share the same root: the atlas was originally written for fast public-network runs and accumulated patterns that break in (a) air-gapped JFrog environments, (b) high-volume / sustained runs that trip secondary rate limits, and (c) any environment where a phase can be interrupted mid-run.

### `_http.py` — shared utility surface expanded

- New `auth_headers_for(url)` factored out of `make_request` so `requests`-based callers (`npm_updater.py`, `recipe-generator.py`) can pick up the same JFROG / .netrc / GitHub-token header chain that the urllib path got for free. `make_request` now delegates to it; caller-supplied `extra_headers` still win via `setdefault`.
- Seven new registry resolvers following the existing `resolve_npm_urls` pattern: `resolve_cran_urls`, `resolve_cpan_urls`, `resolve_luarocks_urls`, `resolve_crates_urls`, `resolve_rubygems_urls`, `resolve_maven_urls` (takes a query-path suffix since Maven uses query strings), `resolve_nuget_urls` (lowercases per NuGet flat-container requirement). Each honors `<HOST>_BASE_URL` env var → public default. Unlocks JFrog air-gap routing for the 7 non-PyPI/non-GitHub upstreams Phase L talks to.
- `resolve_npm_urls` honors `npm_config_registry` / `NPM_CONFIG_REGISTRY` (the npm CLI standard) in addition to the project-convention `NPM_BASE_URL`.
- New atomic-write utilities: `atomic_writer(path, mode)` context manager + `atomic_write_bytes` / `atomic_write_text` thin wrappers. Writes to a `.tmp` sibling, fsyncs (best-effort), `os.replace` into place. On exception inside the `with` block: unlinks the `.tmp`, re-raises. Parent directory auto-created. Replaces the bare `json.dump(obj, f)` / `path.write_bytes(data)` patterns that previously left corrupt JSON or truncated caches behind on interrupt.

### Phase K — GraphQL batch replaces REST fanout

The 2026-05-12 incident report (`project_phase_k_secondary_rate_limit.md`): an 8-worker REST pool issued ~14,000 calls against `api.github.com/repos/<o>/<r>/releases/latest` + `/tags` fallback for a 4,400-row Phase K run and tripped GitHub's secondary rate limit on 15% of fetches.

- New `_phase_k_github_graphql_batch(repos, gh_token, batch_size=100)` issues one HTTP POST per ~100 repos. Each repo's aliased subquery asks for both `releases(first:1, orderBy:CREATED_AT)` and `refs(refPrefix:"refs/tags/", first:1, orderBy:TAG_COMMIT_DATE)` so release-then-tag fallback resolves in a single round-trip. 4,400 repos → ~44 requests instead of ~14,000. Per-alias errors (NOT_FOUND, SUSPENDED) come back via `path[0]` and map to the existing `(None, "HTTP 404")` shape so downstream branching is unchanged.
- `phase_k_vcs_versions` now partitions work into GitHub vs GitLab+Codeberg. GitHub goes through the GraphQL batch; GitLab+Codeberg keep the REST `ThreadPoolExecutor` (no GraphQL equivalents, small volume).
- Per-result write/commit logic factored into `_process_result` nested function so both paths share it.
- New env vars: `PHASE_K_GRAPHQL_DISABLED=1` reverts to REST fanout for GitHub if the GraphQL endpoint ever goes down; `PHASE_K_GRAPHQL_BATCH_SIZE` (default 100) tunes batch size below GitHub's ~500K node-complexity ceiling.
- 5 new unit tests in `test_phase_k_vcs_extraction.py` covering: v-prefix normalization, tag-only fallback, NOT_FOUND mapping, no-release-no-tag → `no tags`, batch splitting (5 repos / batch_size=2 → 3 POSTs).

### Phase F — rate-limit safety on `api.anaconda.org`

- Default `PHASE_F_CONCURRENCY` lowered **8 → 3**. 8-worker fanouts on 32k-row backfills reliably tripped api.anaconda.org's per-IP secondary rate limit; 3 stays under the threshold while still parallelizing.
- New `_anaconda_api_base()` helper resolves `ANACONDA_API_BASE_URL` (new) → `ANACONDA_API_BASE` (legacy, used by `detail_cf_atlas.py`) → `https://api.anaconda.org`. Trailing slash stripped. Both `_phase_f_fetch_one` and `_phase_f_probe_api` now honor the override.
- New `_parse_retry_after(value, fallback)` handles both delta-seconds and HTTP-date `Retry-After` header forms, hard-capped at 60 seconds. `_phase_f_fetch_one` now honors the server's `Retry-After` on 429/503 instead of guessing a backoff. When no header is present, falls back to exponential + **±25% jitter** so a synchronized worker pool doesn't re-hit the API in lockstep after a transient blip.
- `phase_f_downloads` docstring expanded with the new tunables and an explicit pointer for large orgs: *"set `PHASE_F_SOURCE=s3-parquet` to skip the API path entirely."*
- 12 new unit tests in `test_phase_f_dispatch.py`: 4 cases for `_anaconda_api_base` env-var precedence + trailing-slash handling, 8 cases for `_parse_retry_after` (integer / whitespace / negative / unparseable / 60s cap / HTTP-date / negative fallback / None).

### Phase L — per-registry concurrency caps, sequential across registries

The original all-in-one ThreadPoolExecutor with `PHASE_L_CONCURRENCY=8` could fire **up to 56 simultaneous outbound requests** at startup across all 7 registries, immediately tripping crates.io's and rubygems.org's documented ~1 req/sec ceilings.

- Work is now partitioned by registry and processed **sequentially across registries**, each with its own `ThreadPoolExecutor` at the per-registry concurrency cap.
- Per-registry defaults reflect documented or empirically-observed limits: **npm=4, nuget=4, cran=cpan=luarocks=maven=2, crates=1, rubygems=1**.
- New env var `PHASE_L_CONCURRENCY_<SOURCE>` (uppercase) overrides per source. Legacy `PHASE_L_CONCURRENCY` still works as a uniform cap (so `PHASE_L_CONCURRENCY=1` forces fully serial across everything).
- Phase L startup now prints a per-registry breakdown: `npm=1,234@4w, crates=89@1w, …`.
- All 7 `_resolve_*` functions (`_resolve_cran`, `_resolve_cpan`, `_resolve_luarocks`, `_resolve_crates`, `_resolve_rubygems`, `_resolve_maven`, `_resolve_nuget`) rewired to use the new `_http.resolve_<host>_urls` chain via `_fetch_with_fallback`. Hardcoded public URLs preserved only as fallback for clones without `_http.py`.
- Return-dict field rename: `concurrency` → `per_source_workers` (a dict of `{source: workers}`). No internal consumers read this field; if external monitors parse atlas summaries, they may need to update.
- 14 new resolver unit tests in `test_http_resolvers.py` covering external-default + env-var-redirect for each of the 7 hosts.

### Phases B5 / E / E5 / M — resumability

Monolithic `BEGIN TRANSACTION ... COMMIT` blocks around 20k+ row write loops meant a mid-phase interrupt rolled back all of a phase's work. Replaced with periodic commits + idempotent SQL across four phases:

- **Phase B5** (`phase_b5_feedstock_outputs`): commits every 500 rows. `INSERT` switched to `INSERT OR IGNORE` for re-run idempotency.
- **Phase E** (`phase_e_enrichment`): commits every 200 enriched rows. The cf-graph tarball is now streamed directly from disk via `tarfile.open(cache_path, "r:gz")` instead of being re-read into `io.BytesIO(tar_bytes)` — saves ~150MB peak RAM. The download path uses `atomic_write_bytes` for the cache file so an interrupted download no longer corrupts the cache; next-run reads the prior file intact.
- **Phase E5** (`phase_e5_archived_feedstocks`): `save_phase_checkpoint(cursor=<endCursor>)` after each GraphQL page so observers can see pagination progress mid-run. Apply-stage commits every 500 UPDATEs. Final `status='completed'` checkpoint.
- **Phase M** (`phase_m_feedstock_health`): commits every 500 UPDATEs. Iterator buffered into a list first to avoid cursor invalidation when committing mid-loop.

### npm registry — hardcoded `registry.npmjs.org` purged

The `npm_updater.py` and `recipe-generator.py` autotick/generator scripts hardcoded `https://registry.npmjs.org/<name>` and would 401/403 in air-gapped JFrog environments where users had `npm config set registry <jfrog-url>`. Fixed in three call sites:

- `conda_forge_atlas.py:_resolve_npm` — uses `resolve_npm_urls` via `_fetch_with_fallback`.
- `npm_updater.py:get_latest_npm_version` — iterates `resolve_npm_urls(name)` with `requests.get(url, headers=auth_headers_for(url))` (matches the existing `fetch_pypi_info` pattern in this file). Refactored a `_choose_npm_version` helper so the `_http`-available and `_http`-unavailable code paths share the version-picking logic.
- `recipe-generator.py:fetch_npm_info` AND `fetch_pypi_info` — same pattern; `fetch_pypi_info` was a latent bug for any private artifactory PyPI Remote that required `JFROG_API_KEY`. Fixed at the same time.

### New reference doc

- `reference/atlas-phase-engineering.md` — captures the patterns surfaced this session as the default rule book for new phases or refactors. Nine sections: per-host rate limits, GraphQL batching, Retry-After + jitter, per-registry concurrency, atomic writes, incremental commits + idempotent SQL, streaming tarfiles, page-level checkpoints, `<HOST>_BASE_URL` enterprise routing convention.

### Why this matters

- **Air-gap parity**: `behind-upstream`, `staleness-report`, and Phase L now work behind JFrog Artifactory for npm + CRAN + CPAN + LuaRocks + crates + RubyGems + Maven + NuGet (previously only conda-forge / PyPI / GitHub had resolvers).
- **Rate-limit survival**: Phase F (api.anaconda.org), Phase K (api.github.com), and Phase L (7 registries) now all survive sustained / high-volume runs without secondary-limit failures.
- **Interrupt survival**: B5 / E / E5 / M / L preserve progress across mid-phase interrupts. Phase E specifically: a 1.5GB cf-graph re-download is no longer the cost of an interrupted Phase E enrichment loop.
- **No corrupted caches**: cve_manager / mapping_manager / inventory_channel + Phase E's cf-graph tarball can no longer leave truncated JSON / partial bytes behind on SIGINT/OOM. The user's `--sbom-out` file is similarly protected.

### Caveats

- **Phase L return-dict field rename** (`concurrency` → `per_source_workers`) is the only breaking change. Searched the codebase and test suite for consumers; none found. External dashboards parsing atlas build summaries may need a small update.
- **Phase E cf-graph cache TTL** is still hardcoded to 1 day. For weekly-cron deployments that's a 150MB re-download per run for no information gain. Future: `ATLAS_CFGRAPH_TTL_DAYS` env var override.
- **`JFROG_API_KEY` still attaches to every outbound request** regardless of host (pre-existing cross-resolver leak documented in `project_http_jfrog_unconditional_injection.md`). `auth_headers_for` preserves the existing semantics; tightening the leak (only attach when URL host matches a `*_BASE_URL` value) is a separate, larger change.
- **GitHub Enterprise Server is not yet supported** by the Phase K GraphQL path. The endpoint is hardcoded `https://api.github.com/graphql`. GHES uses a different API shape entirely; a single env var won't be enough. Deferred until someone needs it.

---

**v7.7.2** (May 12, 2026) — Phase K URL-derivation regex tightened. The `_GITHUB_REPO_RE` / `_CODEBERG_REPO_RE` repo character classes used to exclude only `/ ? # .`, so when a recipe's `about.dev_url` or `about.repository` field held a multi-URL string (comma-joined, space-joined, or with a parenthetical annotation — common in R/ropensci feedstocks) the captured repo group leaked everything up to the next `/`. Phase K then attempted `releases/latest` URLs like `/repos/eheinzen/arsenal, https:/releases/latest` and `urllib` rejected them with `InvalidURL`. Char class now also excludes `\s , ( ) < > " '`; the gitlab regex got matching whitespace/comma sentinels in its terminator. Surfaced during the 2026-05-12 `atlas-phase K` run on ~4 ropensci feedstocks (r-arsenal, r-azureauth, r-aricode, r-ascii) out of 8,893 fetches. Affected rows auto-heal on the next Phase K run (TTL re-fetch retries them with the corrected derivation). New `test_phase_k_vcs_extraction.py` (14 cases) locks the clean-input, multi-URL, and empty-repo-segment branches.

**v7.7.1** (May 12, 2026) — Three findings landed from staged-recipes PR #33308 (12-recipe `tree-sitter-*` bundle for `repowise`):

- New **Recipe Authoring Gotcha G5** (widened from initial "v1+ only" framing after second-pass build evidence): `tree-sitter-*` PyPI sdists **inconsistently** strip `src/tree_sitter/parser.h` + `array.h` + `alloc.h` — not a clean version-based cutoff. PR #33308 saw 8 of 11 PyPI sources fail across v0.23.x, v0.24.x, v0.26.x, v1.1.x, v1.2.x; three other PyPI sources at v0.25.0 / v0.7.2 happened to ship the headers. **Default to GitHub-tag source for all `tree-sitter-<lang>` recipes**; only fall back to PyPI sdist after `tar tzf … | grep tree_sitter/parser.h` confirms the headers ship. Matches the existing `tree-sitter-python-feedstock` pattern.
- G5 also documents a second-class upstream bug encountered in the same bundle: `tree-sitter-php` v0.24.2's GitHub `pyproject.toml` has `license = "LICENSE"`, which modern setuptools (≥70) rejects as an invalid SPDX identifier. Fix is a downstream `patches/0001-fix-invalid-pep621-license-field.patch` rewriting the line to `license = "MIT"`. The `patches:` list under `source:` is the conda-forge pattern for upstream-bug shims.
- Workflow step 8 (Monitor Build) annotated with a **`get_build_summary` false-negative caveat**: the tool sometimes reports `"build may have crashed"` when the build actually succeeded — its summary-file detection is brittle. Authoritative completion signal is `build_artifacts/<config>/<subdir>/<name>-<version>-*.conda` files with mtime newer than the build start; deeper diagnosis lives in `build_artifacts/<config>/bld/rattler-build_<name>_<id>/work/conda_build.log`.

**v7.7.0** (May 11, 2026) — Phase H gains a cf-graph offline bulk backend that drops cold-start time from ~30 minutes of pypi.org fan-out to ~30 seconds of local tarball scan. Resolves the long-standing Phase H "hangs" problem and removes pypi.org as a hard dependency on `bootstrap-data --fresh`.

- New env var `PHASE_H_SOURCE={pypi-json, cf-graph}` (default `pypi-json`): controls which source populates `pypi_current_version`. `cf-graph` reads the `version_pr_info/<sharded>/<feedstock>.json` shards already on disk after Phase E — zero network, zero auth.
- New `bootstrap-data --phase-h-source {auto,pypi-json,cf-graph}` flag (default `auto`): on `--fresh` runs the cf-graph path automatically for fast cold-start; otherwise pypi-json. Override forces one path.
- New `_cf_graph_versions.py` module — streams the cf-graph tarball, projects `new_version` onto `packages.pypi_name` via `feedstock_name`. Filters out null/false/non-string `new_version` values (bot's "no upstream detected" sentinels).
- Schema v18 → v19 (additive only): `packages.pypi_version_source` discriminator (`'pypi-json'` | `'cf-graph'`) on every Phase H-populated row. Migration is idempotent.
- **Yanked caveat:** cf-graph does not carry PEP 592 yanked status. Rows populated via cf-graph leave `pypi_current_version_yanked = NULL`. Re-run with `PHASE_H_SOURCE=pypi-json` to backfill yanked precisely; the per-row TTL gate ensures the rerun only hits pypi.org for un-pypi-json'd rows.
- **Freshness caveat:** cf-graph lags pypi.org by hours-to-days (autotick-bot polling cadence). Verified 2026-05-11: `requests` cf-graph=`2.33.1` vs pypi.org=`2.34.0` (~24h lag). Acceptable for cold-start "behind-upstream" detection; for strict real-time use the pypi-json source.
- New unit tests: `test_phase_h_dispatch.py` (7 cases — dispatcher routing, cf-graph write/read, malformed-JSON resilience, missing-tarball graceful-skip, null/false `new_version` filtering).
- **`--fresh` now preserves `cache/parquet/` by default** (QW4): the S3 monthly parquet files are immutable historical data — re-downloading them costs ~30 min and ~1.4 GB of network for no information gain. `hard_reset()` stashes the directory before delete and restores it after. New `--reset-cache` flag opts into the old behavior (wipe everything).
- **`--fresh` now confirms before deleting** (QW3): non-interactive 5-second countdown with Ctrl+C abort. Skip with `--yes` / `-y` for CI / scripted use. Aborted runs exit with code 130 (SIGINT-style). Dry-run bypasses the countdown entirely.
- **New `atlas-phase` CLI** (QW1): `pixi run -e local-recipes atlas-phase <ID>` invokes one phase against the existing DB instead of rerunning the full ~30-45 min pipeline. Accepts B / B.5 / B.6 / C / C.5 / D / E / E.5 / F / G / G' / H / J / K / L / M / N (case-insensitive). `--list` enumerates phases; `--reset-ttl` NULL's the phase's `*_fetched_at` columns first (for TTL-gated phases F / G / H / K). Backed by a module-level `PHASES` registry + `get_phase()` / `run_single_phase()` so any future entrypoint can introspect the pipeline without duplicating the order.
- **Phase N checkpointing** (QW2): new `phase_state` table + `load_phase_checkpoint()` / `save_phase_checkpoint()` helpers. Phase N now commits per batch (previously every 4 batches → up to 100 feedstocks of work lost on interrupt) and writes the alphabetically-largest processed feedstock to `phase_state.last_completed_cursor`. On resume, Phase N skips feedstocks ≤ cursor and prints a "Resuming Phase N from cursor > X" message. `status='completed'` markers prevent the next clean run from triggering false resume.
- **Phase B / Phase D batch-commit checkpointing** (M5): both phases now commit every 1k (B) / 5k (D) rows instead of one giant transaction. UPSERTs were already idempotent so the change is correctness-preserving and makes interrupts much cheaper. Both phases write `phase_state` with cursor + items_completed + items_total for visibility.
- **`bootstrap-data --status` / `--resume`** (BL7): `--status` prints the `phase_state` checkpoint table (per-phase status, items completed, cursor, last run time) plus a TTL-gated phase eligibility summary (how many rows are stale, how many have `*_last_error` set) and exits. `--resume` prints the same status on entry, then continues with the standard bootstrap chain. Default behavior was already resume-friendly via TTL gates; the flag formalizes it as an opt-in mode for scripted workflows.
- Reason for the QW2+M5+BL7 bundle: long-running phases that died mid-run had no way to communicate where they stopped, and the `*_fetched_at` columns only said "this row succeeded" — not "the run as a whole completed cleanly." `phase_state` is now a single source of truth for both kinds of state, and the new `--status` command makes it auditable from a single command.
- **Progress-cadence cap + heartbeat** (mid-shift discovery): every phase with a `progress_every = max(N, len(rows) // 40)` formula now also caps at 2,500 — `min(max(N, len // 40), 2500)`. For a 770k-row Phase H run the prior formula would have produced `progress_every=20,000`, meaning the first progress line appeared after ~5-11 minutes of "silence" that operators reliably misdiagnosed as a hang. **The historical "Phase H hangs" reports were almost certainly this UX bug, not a network hang** — verified by per-thread kernel wait-channel inspection + per-socket TCP state inspection during a real run: 8 ESTAB sockets to `151.101.*.223` (pypi.org Fastly), connection ports rotating between snapshots (workers completing + reopening), and a clean 71 req/s ramping to 89 req/s with **zero failures**. Phase H's pypi-json loop also gets a 60-second wall-clock heartbeat: prints a "still alive" line if no progress fired in the last minute regardless of completion count. Six callsites fixed: `_phase_f_via_api`, `_phase_h_via_pypi_json`, Phase G prime, Phase K, Phase L, Phase M.
- **`--reset-ttl` scope fix**: `pixi run atlas-phase X --reset-ttl` now scopes the `UPDATE packages SET *_fetched_at = NULL` to rows the phase would actually process (e.g. Phase H gates on `pypi_name IS NOT NULL`, Phase F on `conda_name IS NOT NULL`). Previously the bare UPDATE touched every row in `packages` (~817k), including ~12k rows where the column was already NULL because the phase wouldn't pick them up anyway. New 4-test unit suite (`test_atlas_phase_reset_ttl.py`) locks the scoping in.
- **Bootstrap step timeouts sized for `--fresh` cold runs**: the prior `cf_atlas` step timeout was 2,400s (40 min), which killed mid-run during a real cold `--fresh` (Phase F took 23 min via API + Phase K was 15% into a 30-min run when the wrapper SIGTERM'd it). New `_timeout_for()` helper + `_DEFAULT_TIMEOUTS` table sizes cf_atlas at 7,200s (2h) plus default-bumped vdb/phase_gp/phase_n to 3,600s. Each is overridable via `BOOTSTRAP_<STEP>_TIMEOUT` env var (invalid / negative / zero falls back to the default with a warning). 6-test suite `test_bootstrap_timeouts.py` locks the resolver behavior. **No data was lost in the timeout incident** — Phases B-J completed and their checkpoints/TTL gates ensure `pixi run build-cf-atlas` cleanly resumes Phase K from row 3,546 without a `--fresh`.
- New unit tests: `test_bootstrap_hard_reset.py` (8 cases — preserve/nuke parquet, confirmation abort, dry-run skip, `--yes` short-circuit, missing-data-dir no-op).
- Reason: pypi.org fan-out was the most common atlas-pipeline hang (no per-future timeout, 25k requests × 30 s socket timeout × 3 retries). Cold-start via bulk local file scan eliminates the hang surface entirely on `--fresh`; warm runs keep pypi-json as default for real-time accuracy. The QW3+QW4 changes shore up the `--fresh` UX so the destructive op is auditable and the immutable cache survives reset.

**v7.6.0** (May 10, 2026) — Phase F gains an S3 parquet backend that closes the atlas pipeline's last hard `*.anaconda.org` dependency. Air-gapped / firewall users can now build a complete atlas (downloads column included) without any anaconda.org access.

- New env var `PHASE_F_SOURCE={auto, anaconda-api, s3-parquet}` (default `auto`): probes `api.anaconda.org/package/conda-forge/pip` once, runs the existing API path on success, falls through to S3 on URLError/timeout/HTTP≥500. Mid-run >25%-failure-after-1,000-rows trigger also flips to S3 for unwritten rows (the run summary then reports `source='merged'`).
- New `s3-parquet` backend reads `s3://anaconda-package-data/conda/monthly/{YYYY}/{YYYY-MM}.parquet` directly over HTTPS — same dataset as `condastats`, served from AWS S3 (not `*.anaconda.org`). Uses `pyarrow.parquet.read_table` with pushdown filters; no new top-level deps. Routes through `_http.py`'s JFrog auth chain — `S3_PARQUET_BASE_URL=https://artifactory.example.com/anaconda-package-data` works the same way `CONDA_FORGE_BASE_URL` does today.
- New parquet cache at `.claude/data/conda-forge-expert/cache/parquet/` — current-month file always re-fetched, older months cached indefinitely. ~13 MB/month, ~1.4 GB for full 9+ years. Optional trailing-N-months cap via `PHASE_F_S3_MONTHS=24`.
- Schema v17 → v18 (additive only): `packages.downloads_source` discriminator (`'anaconda-api'` | `'s3-parquet'` | `'merged'`) on every Phase F-populated row; `package_version_downloads.source` parallel column. Migration is idempotent; rerunning `init_schema` on a v18 DB is a no-op.
- **Numeric caveat:** API and S3 totals do NOT agree (verified 2026-05-10: `requests` 1.50× higher on S3, `django` 0.56×, `bmad-method` matches modulo partial-current-month). Treat as correlated-but-distinct metrics; consumers (`staleness_report`, `package_health`, `version_downloads`, `release_cadence`) must surface `downloads_source`.
- **Multi-source-table writes use UPSERT, not `INSERT OR REPLACE`.** S3 path writes `package_version_downloads` rows with `ON CONFLICT(conda_name, version) DO UPDATE SET total_downloads=…, fetched_at=…, source=…` so any prior API-path `upload_unix`/`file_count` are preserved during mixed auto-mode runs. New SKILL.md Critical Constraint documents the pattern.
- **Known limitation flagged.** Pre-existing `_http.py` `make_request` injects `JFROG_API_KEY` for ANY URL whenever the env var is set, regardless of host — affects conda-forge channel URLs going to public `conda.anaconda.org`, S3 parquet URLs going to public AWS, GitHub raw URLs going to public github.com. Cross-resolver credential leak; logged as deferred-work and as a new SKILL.md Critical Constraint. Operators using JFROG_API_KEY should pair it with the corresponding `*_BASE_URL` for every channel consumed.
- **Tests + verification.** 13 new unit tests across 4 files (`test_s3_resolver.py`, `test_parquet_cache.py`, `test_phase_f_dispatch.py`, `test_schema_migration_v18.py`); 766 passed full-suite. Real-S3 smoke test verified end-to-end against the live 2026-04 file. Online byte-identical verification deferred to post-merge.
- **Wave 2 + Wave 3 deferred.** This release ships Wave 0+1 from `docs/specs/atlas-phase-f-s3-backend.md` (foundations + air-gap fix); Phase F+ richer metrics (rolling 30/90-day, trend slope, per-platform/python breakdowns) and the three new CLIs (`platform_breakdown`, `pyver_breakdown`, `channel_split`) remain deferred to follow-on waves. Schema columns NOT yet provisioned for those — separate migration when Wave 2 lands.
- Reason: `api.anaconda.org` was the lone firewall blocker in the entire atlas pipeline. Every other anaconda.org fetch already auto-falls-back through `_http.py` resolvers (Phase B current_repodata.json → prefix.dev; detail-cf-atlas → current_repodata.json fallback). With this release the pipeline is fully firewall-tolerant.

**v7.5.0** (May 9, 2026) — Close the schema-header gap v7.4 missed: the MCP grayskull path now emits the header, every existing v1 recipe is backfilled, and a meta-test enforces it forever.

- v7.4 fixed `generate_npm_recipe_yaml` and `_run_rattler_generate` but not the MCP grayskull path — `generate_recipe_from_pypi` in `.claude/tools/conda_forge_server.py` post-processed the recipe with `_normalize_grayskull_test_matrix` only. Every recipe generated through the MCP server (the most-used generator path: `pixi run generate-recipe`, the `generate_recipe_from_pypi` MCP tool, and the autonomous-loop step 1) silently dropped the directive. Discovered when authoring `recipes/pptx2md/recipe.yaml`.
- Fix: added `_ensure_yaml_language_server_header(recipe_path)` to `conda_forge_server.py`, called immediately after `_normalize_grayskull_test_matrix`. Idempotent — bails out if the header is already present. Result includes a new `post_processing.yaml_language_server_header` boolean.
- New meta-test: `tests/meta/test_recipe_yaml_schema_header.py` parametrizes over every `recipes/*/recipe.yaml` and asserts line 1 is the directive. The skip rule is "no `schema_version:` line in the file" — covers both jinja-style v0 content and v1-shaped recipes that happen to omit the optional `schema_version: 1` declaration. 447 recipes covered; 9 skipped (3 v0/jinja + 6 v1-shaped-no-schema-version).
- Backfilled: 95 v1 recipes that were missing the header now have it (previously v7.4 explicitly chose "going-forward only"; this release reverses that — committed recipes are part of the contract the test enforces).
- Skipped by the test, in two distinct categories:
  - **v0/jinja-style `recipe.yaml`** (3): `openmetadata-managed-apis`, `pyarrow`, `weasel` — file is named `recipe.yaml` but content is conda-build `meta.yaml` (jinja `{% set %}` form). Filename-mismatch bug; the directive is v1-only and these aren't v1.
  - **v1-shaped without `schema_version:`** (6): `git-hound`, `teradata-mcp-server`, `wagtail-draftail-plugins`, `wagtail-pdf-view`, `xformers`, `zensical` — uses v1 syntax (`context:` block) but omits the optional `schema_version: 1` declaration. Adding both `schema_version: 1` and the directive would be the right fix; deferred to a follow-up so v7.5's blast radius stays "header backfill only".
- Reason: a v7.4 fix that doesn't cover the most-used generator and doesn't enforce its invariant via test will silently regress. v7.5 closes both gaps so the directive is a contract of the repo, not a convention.

**v7.4.0** (May 9, 2026) — All generated `recipe.yaml` files carry the `# yaml-language-server: $schema=…` directive so editors (VS Code, Helix, Neovim) get live schema validation from prefix-dev/recipe-format.

- `generate_npm_recipe_yaml` now prepends the directive above `schema_version: 1`.
- `_run_rattler_generate` (PyPI/CRAN/etc. via `rattler-build generate-recipe`) post-processes the written file with `_ensure_yaml_language_server_header`. Idempotent — bails out if the header is already present.
- Existing PyPI path (`generate_recipe_yaml`) and every `templates/**/*-recipe.yaml` template were already emitting the header; this release closes the npm + rattler-generate gaps.
- Test `test_recipe_generator.py` flipped: was asserting the npm path must NOT emit the header (canonical PRs omit it); now asserts it must. Going-forward only — existing committed `recipe.yaml` files in `recipes/` are not retroactively backfilled.
- Reason: editors silently lose schema validation when the directive is missing, which costs catch-rate on the easiest class of recipe bugs (typo'd field names, wrong nesting, deprecated keys). The directive is a comment, so emitting it is harmless for rattler-build; it's pure editor UX.

**v7.3.0** (May 9, 2026) — Document `conda-forge.yml` and ship two starter templates, in the same shape as existing reference + template pairs.

- New reference: [`reference/conda-forge-yml-reference.md`](reference/conda-forge-yml-reference.md). Practical, high-signal subset (not exhaustive — that's what the canonical docs are for): per-recipe staged-recipes override scope, feedstock-level scope, top use cases with rationale (`azure.store_build_artifacts`, `os_version`, `provider`, `bot.version_updates.exclude`, `noarch_platforms`, per-job timeouts), less-common but useful keys table, deprecated keys to remove.
- New templates: [`templates/conda-forge-yml/staged-recipes/conda-forge.yml`](templates/conda-forge-yml/staged-recipes/conda-forge.yml) (staged-recipes per-recipe override) and [`templates/conda-forge-yml/feedstock/conda-forge.yml`](templates/conda-forge-yml/feedstock/conda-forge.yml) (feedstock-root). Both keep keys commented out so a verbatim drop-in is a no-op until you uncomment a specific override; single-line trailing annotations (`# default cos7 (glibc 2.17)`) match the inline-comment style of existing templates like `templates/python/noarch-recipe.yaml`. Leaf filename is `conda-forge.yml` so a copy-paste into the destination needs no rename; the parent directory (`staged-recipes/` vs `feedstock/`) names the scope.
- SKILL.md step 8b's optional-add-on note points at the reference + template.
- CLAUDE.md skill-doc index gains the new reference.

**v7.2.0** (May 9, 2026) — Split submission into two user-authorized steps so the human can inspect the branch on the fork before the PR opens.

- New step **8b** in the autonomous loop: `prepare_submission_branch(recipe_name)`. Syncs your fork, creates the recipe branch, copies the recipe in, commits, and pushes to `<your-user>/staged-recipes` — but **does not open a PR**. Returns `fork_branch_url` for browser inspection.
- Idempotent push: skips the force-push when the remote branch's tree already matches the local HEAD (`pushed: false`); reports `synced_commits` so you see how many commits the fork's main was behind upstream.
- Force pushes default to `--force-with-lease` (instead of plain `--force`) — a divergent remote branch errors instead of being silently overwritten. `force=False` (or `--no-force`) opts into a plain push.
- `submit_pr` is now thin: calls `prepare_submission_branch` then `gh pr create`. When step 8b already ran, the prep phase short-circuits (idempotency) and `submit_pr` only opens the PR. If the PR step fails after a successful push, the result includes the branch info and a hint to retry just the PR step — no re-push.
- New pixi task: `pixi run -e local-recipes prepare-pr <recipe>`. New wrapper at `.claude/scripts/conda-forge-expert/prepare_pr.py` (delegates to canonical `submit_pr.py --prepare-only`).
- SKILL.md autonomous-loop expanded to 10 steps (8b inserted); Pre-PR checklist gains the prep-branch + optional `azure.store_build_artifacts` lines; tools table documents both surfaces.

**v7.1.0** (May 9, 2026) — Adopt the `[python_min, "*"]` test-matrix convention for noarch:python recipes.

- New optimizer check **TEST-002**: flags `tests[].python.python_version` when set to a single string (or a list missing `"*"`) on `noarch: python` recipes.
- New post-processor on `generate_recipe_from_pypi`: rewrites grayskull's single-string `python_version: ${{ python_min }}.*` to the two-entry list form on every recipe generation. Idempotent.
- `templates/python/noarch-recipe.yaml` updated to the list form so hand-written recipes follow the same convention.
- Total optimizer check codes: **16** (was 15).
- Convention source: ocefpaf review on [conda-forge/staged-recipes#32857 r3039190932](https://github.com/conda-forge/staged-recipes/pull/32857#discussion_r3039190932). Rationale: a noarch:python package builds once but runs across the whole 3.10→3.14 matrix; testing only the floor lets Python-version-specific breakage (3.13/3.14 stdlib removals, deprecated APIs) slip past review.

**v7.0.0** (May 9, 2026) — Atlas intelligence layer goes GA, fully exposed via MCP, **zero open feature gaps**.

- 15 pipeline phases (B → N), **17 schema versions**, 17 CLIs, **34 MCP tools**.
- Unified scanner accepts ~28 input formats (manifests, lock files, SBOMs, container images, live envs, GitOps CRs with auto git-clone fallback, K8s manifests, OCI archives, OCI registry probes).
- New CLIs: `staleness-report`, `feedstock-health`, `whodepends`, `behind-upstream`, `cve-watcher`, `version-downloads`, `release-cadence`, `find-alternative`, `adoption-stage`, **`bootstrap-data`**.
- New MCP tools wrap all of the above + `query_atlas`, `package_health`, `my_feedstocks`, `scan_project`.
- **`bootstrap-data`** — single command refreshes everything; `--fresh` hard-resets from scratch.
- **PyPI yanked detection** (PEP 592), **Maven coord autopopulation** from cf-graph URLs, **SBOM relationship tree rendering**, **Argo/Flux git-clone fallback** all landed.
- Documentation consolidated: `INDEX.md` is the task-→-tool navigator; `guides/atlas-operations.md` covers cron schedules / hard reset / air-gapped use.

For the full v7.0.0 release note, see below. For older releases, scroll past the v7.0 entry. Each release has its own date-stamped block.

---

- **v7.3.0**: Document `conda-forge.yml` and ship two starter templates (May 9, 2026). The submission-flow split landed in v7.2.0 surfaced a recurring need: every other recipe wants some staged-recipes-default override (newer glibc, additional CI matrix, kept artifacts) but the only existing source for those keys was the upstream conda-forge docs site — no skill-internal reference, no copy-pasteable starter. Two artifacts ship together:

    1. **Reference** — `reference/conda-forge-yml-reference.md`. Covers: where the file lives in each context (per-recipe override in staged-recipes vs. permanent feedstock root); the high-frequency keys (`azure.store_build_artifacts` for downloadable Azure artifacts, `os_version` for newer Linux glibc/sysroot, `provider.linux_64: github_actions` for the conda-smithy 3.57.1 opt-in, `bot.version_updates.exclude` for stuck-tag PRs, `noarch_platforms` for extra noarch:python matrix, per-job `timeout_minutes`, `azure.free_disk_space`); less-common keys table (channel priority, output validation, recipe_dir, lint skip, idle timeout); deprecated keys to remove (`compiler_stack`, `build_with_mambabuild`, `clone_depth`, `pinning`); five common patterns (artifact retention, glibc bump, bot tag exclusion, macOS noarch testing); and the local-lint command. Cites the canonical conda-forge docs page as the exhaustive source — the skill reference is the practical-use subset, not a re-implementation of the schema.

    2. **Templates** — `templates/conda-forge-yml/staged-recipes/conda-forge.yml` (per-recipe override) and `templates/conda-forge-yml/feedstock/conda-forge.yml` (feedstock root). Leaf filename matches the destination filename so a copy-paste into a recipe directory or feedstock root needs no rename; the scope subdirectory (`staged-recipes/` vs `feedstock/`) disambiguates the two starters. Both ship with every key commented out and a one-line description above each block, so dropping the file in is zero-behavior until the user uncomments a specific override. Header comment in each template explicitly tells the user not to commit an all-empty file ("an empty conda-forge.yml just adds noise to the PR diff").

    **Why this lives in the skill, not just the conda-forge docs**: when an agent needs a staged-recipes override during a recipe build, it's already inside this skill's context. Asking it to webfetch the upstream docs and synthesize a one-line override is a longer, more error-prone path than reading the practical-subset reference and copying from the template. The trade-off is that the reference can drift from upstream — mitigated by citing the canonical doc and including a note that conda-smithy lint is the source of truth for valid keys.

    **Wiring**: SKILL.md step 8b's optional-add-on note now links the reference + template (was a one-liner mentioning `azure.store_build_artifacts` inline). CLAUDE.md skill-doc index updated to list the new reference. No optimizer or generator changes — this is documentation + templates only.

- **v7.2.0**: Split staged-recipes submission into two user-authorized steps (May 9, 2026). The submission flow used to be a monolithic `submit_pr` that ran fork-clone → sync → branch → copy → commit → push → `gh pr create` end-to-end, with no inspection point in between. With more recipes shipping, the gap between "build is green locally" and "PR is live on conda-forge/staged-recipes" needed a human-in-the-loop checkpoint — somewhere to open the branch on GitHub and *look* at the recipe in its destination context before reviewers pull it.

    **Three changes ship together**:

    1. **Refactor `submit_pr.py`** — extract three top-level functions:
       - `prepare_branch(recipe_name, branch=None, force=True, dry_run=False)` — does steps 1–6 of the old flow (validate recipe, gh auth check, fork clone/sync, branch checkout, copy recipe in, commit, push). Returns `{branch, fork_branch_url, head_sha, synced_commits, pushed}`.
       - `open_pr(recipe_name, branch=None, ...)` — does step 7 only (`gh pr create` from `<user>:<branch>` against `conda-forge/staged-recipes:main`).
       - `submit_pr(...)` — composes the two. If `prepare_branch` succeeds and `open_pr` then fails, the result includes `branch` + `fork_branch_url` + a `hint` to retry just the PR step.

    2. **Idempotency + safer force-push**:
       - Before pushing, the script checks `git ls-remote origin <branch>`; if the remote tip's tree-hash already matches the local HEAD's tree-hash, the push is skipped (`pushed: false`). This makes the prep step safely re-runnable from the same recipe directory without burning a force-push when nothing changed.
       - Force-pushes default to `--force-with-lease` (was plain `--force`). A remote branch that diverged unexpectedly between fetch and push will error instead of being silently overwritten. The `--no-force` flag falls back to a plain push (errors on any divergence at all).
       - The fork sync step now returns `synced_commits` (the count from `git rev-list --count main..upstream/main` before the reset) so the caller sees how stale their fork was.

    3. **Two MCP tools, two pixi tasks**:
       - New MCP tool `prepare_submission_branch(recipe_name, dry_run, branch, force)` wraps `prepare_branch` (canonical script `submit_pr.py --prepare-only`).
       - Existing `submit_pr` MCP tool gains `branch` + `force` parameters; docstring clarifies it now no-ops on prep when step 8b already ran.
       - New pixi task `pixi run -e local-recipes prepare-pr <recipe>` (description distinguishes it from `submit-pr`); new wrapper `.claude/scripts/conda-forge-expert/prepare_pr.py` delegates to the canonical `submit_pr.py` with `--prepare-only`.

    **Why the inspection checkpoint matters**: a green local build doesn't catch everything a reviewer will see. The PR diff against staged-recipes is what the human eye actually scans — relative paths in `license_file`, accidental files left in the recipe directory (build_artifacts, `.pyc`, editor swapfiles), the `extra.recipe-maintainers` ordering relative to existing maintainers in the file, and so on. With step 8b, those land on `<user>/staged-recipes` first; you eyeball them in the GitHub UI; *then* you open the PR. For trivial re-submissions, skip 8b and call `submit_pr` directly — it's still atomic.

    **Optional artifact-retention hint**: SKILL.md step 8b documents that you can ship a per-recipe `conda-forge.yml` with `azure: { store_build_artifacts: true }` so the upstream PR's Azure run keeps the built `.conda` files as downloadable pipeline artifacts (default is `false`). Useful for reviewers who want to test the package in a real env before approving — paste the `.conda` URL from the Azure run page into a fresh conda env.

    **Documentation**: SKILL.md autonomous-loop expanded from 9 to 10 steps (8b inserted between Monitor Build and Submit PR); both new and updated tools land in the Maintenance Reference table; Pre-PR checklist gains the prep-branch + optional store_build_artifacts lines.

- **v7.1.0**: Adopt the `[${{ python_min }}.*, "*"]` test-matrix convention for noarch:python recipes (May 9, 2026). The convention surfaced during the deepxiv-sdk submission review and was canonicalized by ocefpaf in [staged-recipes#32857 r3039190932](https://github.com/conda-forge/staged-recipes/pull/32857#discussion_r3039190932). Three changes ship together so the convention is enforced end-to-end:

    1. **Generator post-processor** — `generate_recipe_from_pypi` now applies `_normalize_grayskull_test_matrix` after grayskull writes the recipe. Grayskull emits `python_version: ${{ python_min }}.*` (single string); the post-processor rewrites it to the list form. Regex-based, indentation-preserving, idempotent. Verified against grayskull's deepxiv-sdk output and on a re-run (zero matches on second pass).
    2. **Optimizer check TEST-002** — `analyze_noarch_python_test_matrix` flags any noarch:python recipe whose `tests[].python.python_version` is a single string OR a list missing `"*"`. Skips non-noarch:python recipes and entries without a `python_version` key. Confidence 0.85. Brings the optimizer to **16 check codes** (was 15).
    3. **Template** — `templates/python/noarch-recipe.yaml:41` updated to the list form so hand-written recipes follow the same shape.

    **Why the list form is better**: a noarch:python package builds once but is dispatched across the entire Python build matrix (3.10 → 3.14 today). A test pinned to `${{ python_min }}.*` only exercises the floor; Python-version-specific breakage at the top of the matrix (`cgi`/`asyncore` removed in 3.13, `pkg_resources` deprecation, dict-ordering changes, etc.) sails past review and surfaces as a downstream user bug. The `"*"` entry resolves to the latest Python in the build environment so every (re)build verifies both the floor and the ceiling. On rerender, when conda-forge-pinning lands a new Python version, the list form re-runs the test against that new top — silent regressions become loud.

    Documentation: SKILL.md `## Core Tools Reference` updated for both `generate_recipe_from_pypi` (post-processing note) and `optimize_recipe` (16 check codes; TEST-002 description with PR link). The deepxiv-sdk recipe shipped in `recipes/deepxiv-sdk/recipe.yaml` is the first recipe to use this form end-to-end.

- **v7.0.0**: MCP exposure of the entire actionable-intelligence layer + final pre-MCP cluster + documentation consolidation (May 9, 2026). Major version bump because cf_atlas's surface is now reachable from any Claude Code session as MCP tools — every signal we've shipped (Phases B → N) becomes a single tool call instead of a one-off Python invocation.

    **(1) Final pre-MCP cluster.** Six discrete additions before MCP:
      - **Maven Central resolver + `maven_coord` schema column** (schema v15→v16). Phase L now dispatches to `_resolve_maven` via the existing name-column path (when `maven_coord` is populated) AND via URL pattern detection (`search.maven.org/artifact/<g>/<a>`, `mvnrepository.com/artifact/<g>/<a>`, `central.sonatype.com/artifact/<g>/<a>`). Coords use the `<groupId>:<artifactId>` form. Verified: `com.google.guava:guava` → `33.4.8-jre`. Closes the eighth-and-final Phase L registry.
      - **SBOM relationship traversal**. New `parse_sbom_relationships` reads CycloneDX `dependencies[].dependsOn[]` and SPDX `relationships[].relationshipType ∈ {DEPENDS_ON, DEPENDS_FOR, CONTAINS}`. Returns the parent→child graph for downstream tree-view rendering. Verified on a hand-crafted CycloneDX with `app→[lib1,lib2]` + `lib1→[lib2]`.
      - **Argo CD `Application` CR handler** (`--argo-app <file>`). Reads `spec.source.{repoURL, path, helm, kustomize}`; resolves to a local path (cwd or CR-relative); dispatches to `helm_template_images` / `kustomize_build_images` / `parse_kubernetes_manifest` based on what's present. Remote `repoURL` cloning is out of scope (no git fetcher in scan-project).
      - **Flux CD `HelmRelease` / `Kustomization` CR handler** (`--flux-cr <file>`). Same shape as Argo: reads `spec.chart.spec` for HelmRelease (with optional inline `spec.values` written to a temp file as `-f values.yaml`); reads `spec.path` for Kustomization. Closes the GitOps deployment story for OCP / GKE / AKS / VMs.
      - **OCI manifest probe** (`--oci-manifest <ref>`). Lightweight registry-direct probe: hits `/v2/<repo>/manifests/<tag>` with the standard Accept-headers, handles Bearer-challenge dance (ghcr.io / docker.io), supports anonymous + token-auth registries. Returns the manifest dict only — no layer download, no SBOM extraction (those still need syft/trivy). Use case: air-gapped tag verification + tag→digest pinning for reproducible deploys. Verified: `alpine:3.19` returns OCI image-index with 14 platform manifests.
      - **VEX render in scan-project output**. The `parse_vex_cyclonedx` parser shipped in v6.6.x stashes `not_affected` / `false_positive` statements on `dep.extras["vex"]`; v7.0 surfaces them in the formatted card so users see "this CVE doesn't apply, justification=code_not_present" without needing to inspect the JSON.

    **(2) MCP exposure (the headline).** Twelve new MCP tools wrap the entire cf_atlas surface, exposed via `.claude/tools/conda_forge_server.py`:

      | MCP tool | Wraps | Use case |
      |---|---|---|
      | `query_atlas` | direct SQL against `packages` (read-only, LIMIT-enforced) | escape hatch for ad-hoc questions |
      | `package_health` | `detail-cf-atlas` | full health card (B + E + F + G + H + J + K + M + N) |
      | `my_feedstocks` | `query_atlas` join through `package_maintainers` | portfolio overview by maintainer |
      | `staleness_report` | `staleness_report.py` | stalest / risk-ranked / has-vulns / bot-stuck filters |
      | `feedstock_health` | `feedstock_health.py` | stuck / bad / open-pr / ci-red / open-issues / open-prs-human / all |
      | `whodepends` | `whodepends.py` | forward + reverse dep graph queries (Phase J data) |
      | `behind_upstream` | `behind_upstream.py` | multi-source upstream-of-record comparison |
      | `cve_watcher` | `cve_watcher.py` | snapshot diff (Phase G history) |
      | `version_downloads` | `version_downloads.py` | per-version adoption curves (Phase I) |
      | `release_cadence` | `release_cadence.py` | accelerating / stable / decelerating / silent classifier |
      | `find_alternative` | `find_alternative.py` | suggest healthier replacement for archived/abandoned packages |
      | `adoption_stage` | `adoption_stage.py` | bleeding-edge / stable / mature / declining / silent classifier |
      | `scan_project` | `scan_project.py` | unified scanner: project / image / SBOM / live env / Helm / Kustomize / Argo / Flux / k8s / SPDX / VEX |

      All twelve tools verified end-to-end via direct function invocation: `my_feedstocks('rxm7706')` returns 732 packages; `staleness_report --by-risk` correctly surfaces `weasyprint` (the only rxm7706 feedstock with a non-zero High count); `whodepends opentelemetry-api --reverse` returns the 149 dependents; `feedstock_health stuck` returns the opentelemetry-instrumentation-* family at 27 errs; `find_alternative vllm-nccl-cu12` returns ranked candidates; `adoption_stage cachetools` returns "mature".

    **(3) Cumulative scope of the v7.0 release** (built incrementally across this session's v6.5 → v7.0 chain): cf_atlas now ships **schema v16** with 16 schema versions of migration history, **15 pipeline phases** (B / B.5 / B.6 / C / C.5 / D / E / E.5 / F / G / G' / H / J / K / L / M / N) all idempotent and TTL-gated where appropriate, and **17 CLIs** (validate-recipe, optimize-recipe, build-cf-atlas, query-cf-atlas, stats-cf-atlas, detail-cf-atlas, detail-cf-atlas-vdb, staleness-report, whodepends, behind-upstream, cve-watcher, version-downloads, release-cadence, feedstock-health, find-alternative, adoption-stage, scan-project) plus 12 MCP tools wrapping the read-side. The persona-mapped `actionable-intelligence-catalog.md` and the format-coverage `dependency-input-formats.md` are the canonical guides; both updated incrementally throughout the chain.

    **(4) Format coverage at v7.0.** Inputs accepted by `scan-project`: pixi.lock + pixi.toml, requirements.txt + requirements.in, pyproject.toml (PEP 621 + PEP 735 + Poetry incl. v1.2 groups + PDM dev + Hatch envs + setuptools + Flit), uv.lock, poetry.lock, Pipfile + Pipfile.lock, environment.yml, Cargo.lock + Cargo.toml, package.json + package-lock.json, yarn.lock (v1 + v2+ Berry), pnpm-lock.yaml, go.mod + go.sum, Gemfile.lock, composer.lock, conda-lock.yml, Containerfile/Dockerfile (with multi-stage `COPY --from=` chains), Kubernetes/OpenShift/Knative/Argo/Helm/Kustomize manifests, CycloneDX (JSON 1.4-1.6 + XML), SPDX (JSON 2.x + 2.3 + 3.0 JSON-LD + tag-value), syft native JSON, trivy native JSON, container images (via syft/trivy with multi-image support), OCI archives, live conda envs, live Python venvs, live K8s clusters (via kubectl), Helm chart rendering (via helm template), Kustomize overlays (via kustomize build), Argo CD Applications, Flux HelmReleases / Kustomizations, OCI registry manifests (direct, no syft/trivy needed). VEX (CycloneDX 1.5+) statements parsed and surfaced. License compatibility checking against any SPDX target. SBOM emit (CycloneDX / SPDX) with optional Phase G atlas vuln annotations.

    **(5) Persona-mapped intelligence**. From `actionable-intelligence-catalog.md`: ~30 actionable signals across feedstock-maintainer / conda-forge-admin / consumer personas, all queryable offline from `cf_atlas.db` (Phase G needs vdb env for *fresh* vuln data; cached counts work everywhere). Catalog status counts post-v7.0: ~50 ✅ shipped / 1 ❌ gap (PyPI yanked-version detection — needs a pypi.org API call) / a small handful of 📋 open enhancements (per-version PyPI yanked status, SBOM relationship rendering as a tree, Phase H/N full backfill cron operationalization, additional registries when needed).

    **Validation matrix.**
      - All 12 MCP tools instantiate cleanly and return correct results when called directly. ✓
      - Maven resolver returns latest version for known coords. ✓
      - SBOM relationship parser extracts dependency tree from both CycloneDX and SPDX shapes. ✓
      - Argo + Flux CR handlers gracefully fail when local source path is missing. ✓
      - OCI manifest probe handles anonymous + Bearer-challenge auth (verified on docker.io alpine). ✓
      - VEX statements appear in scan-project render output. ✓
      - CHANGELOG entries v6.5.0 → v7.0.0 form a continuous narrative. ✓

    **(6) v7.0 closeout — zero open items.** Final pass against the gap audit landed these items, all rolled into the same v7.0.0 release:

      - **PyPI yanked-version detection** (schema v16→v17, new `pypi_current_version_yanked INTEGER` column). Phase H worker now reads PEP 592 semantics: a version is yanked iff *all* file entries under `releases[<v>][i].yanked` are truthy. 4-tuple return shape `(pypi_name, version, yanked, err)` plumbed through the worker pool. Surfaces in `behind-upstream --json` so maintainers can filter for "I'm pinned to a yanked upstream" — closes the lone ❌ gap from the v6.9 catalog.
      - **Maven coord autopopulation** (Phase E). New `_MAVEN_SOURCE_RE` matches cf-graph URLs of the form `repo.maven.apache.org/maven2/<group>/<artifact>/...` and writes `maven_coord = "<groupId>:<artifactId>"` so Phase L's Maven resolver picks them up automatically — no manual coord entry required for any recipe whose `meta.yaml` already points at Maven Central. Verified against the small set of conda-forge feedstocks that ship Maven artifacts.
      - **SBOM relationship rendering**. The parser shipped earlier now feeds the formatted card: `scan-project` renders the top 15 parents with up to 8 children each from `dep.extras["depends_on"]`, producing a bounded dependency-tree view without overwhelming the output.
      - **Argo/Flux git-clone fallback**. Both CR handlers now auto-clone a transient checkout to a temp dir when the resolved local path is missing (uses `targetRevision` for the ref, `tmp.cleanup` on exit). Closes the prior "remote-repo cloning out of scope" caveat — users no longer need to pre-clone.
      - **`bootstrap-data` single-command refresh** (`.claude/skills/conda-forge-expert/scripts/bootstrap_data.py` + thin wrapper). One command refreshes mapping cache + CVE DB + vdb + cf_atlas (Phases B/B.5/B.6/C/C.5/D/E/E.5/F/G/G'/H/J/K/L/M) and optional Phase N. Flags: `--fresh` (hard reset — wipes `.claude/data/conda-forge-expert/` first), `--no-vdb` (skip the 2.5 GB vdb refresh), `--no-cf-atlas` (mapping + CVE only), `--with-per-version-vulns` (Phase G'), `--gh --maintainer X` (Phase N), `--dry-run`. Pixi task: `pixi run -e local-recipes bootstrap-data`. Cold-start total ~30–45 min on residential bandwidth (vdb dominates).
      - **`guides/atlas-operations.md`**. New operational guide documents cron schedules per data source, sample crontab, channel-wide vs per-maintainer trade-offs, hard-reset/recovery flows, air-gapped operation, and the storage budget. This closes out the long-standing "Phase H/N full conda-forge-wide backfill cron operationalization" follow-up — the cron design is now documented even though the per-maintainer scope remains the recommended default.

    **Limitations / known follow-ups (post-7.0 closeout).** (a) Channel-wide Phase H/N (~32k feedstocks) is now *operationalizable* via the documented cron schedule, but full-channel Phase N still requires multiple GitHub PATs in rotation. (b) Per-version vdb-history snapshot side table (for time-travel queries against historical vuln state) — Phase G' writes per-version current vuln counts but no time series yet. (c) Multi-output feedstock per-output dep-graph (Phase J extension) still captures only the primary output's deps. (d) `recipe_format='unknown'` heuristic refinement (116 outliers globally) — low-priority cleanup. (e) MCP `query_atlas` allows raw WHERE clauses — defensively blocked write keywords and capped LIMIT, but operators should still treat it as the privileged escape hatch. (f) The `_atlas_records` parameter in `fetch_atlas_vuln_summary` triggers a Pyright unused-variable diagnostic that won't quiet via underscore prefix; left as-is to match the broader codebase convention.

    **Docs.** SKILL.md frontmatter + `config/skill-config.yaml` bumped 6.9.0 → 7.0.0. `conda_forge_server.py` net change ~250 lines (12 new MCP tools + path constants). `scan_project.py` net change ~400 lines (Argo/Flux/OCI/VEX/relationship/Maven additions). `conda_forge_atlas.py` net change ~200 lines (Maven resolver + URL detector + schema columns v16+v17 + Phase H yanked plumbing + dispatcher). New `bootstrap_data.py` (~250 lines) + `guides/atlas-operations.md` (~160 lines). `dependency-input-formats.md` and `actionable-intelligence-catalog.md` updated to reflect zero open feature gaps. No changes to the existing recipe-authoring MCP tools (validate_recipe / check_dependencies / etc.); v7.0 only ADDS to the surface.

- **v6.9.0**: Atlas v13 — actionable-intelligence layer (Phases H/J/K/M + side tables + 5 new CLIs) (May 9, 2026). Five new pipeline phases plus a redesigned upstream-version side table layer. Closes long-standing gaps around "is my feedstock behind upstream?", "who depends on my package?", "which of my feedstocks have stuck bots?", and "what's changed since last week?". Schema bumps: 6 → 13 (one bump per cohesive feature: 7=deps, 8=pypi-version, 9=vuln-history, 10=per-version-downloads + 11=github-version, 12=upstream-side-table, 13=feedstock-health).

    **(1) Phase J — dependency graph** (schema v6→v7). Parses `meta_yaml.requirements` from cf-graph node_attrs into a new `dependencies(source_conda_name, target_conda_name, requirement_type, pin_spec)` table. Build/host/run/test edges captured with pin specs preserved verbatim. Live result: **282,504 edges across 27,740 feedstocks in 15.7 s** from the cached cf-graph tarball — zero new HTTP. Skips self-references and Jinja-placeholder targets. Multi-output feedstocks use the primary output as source (sub-output deps are a future enhancement). New `whodepends <name> [--reverse] [--type build|host|run|test]` CLI with display joining downloads + vuln counts for downstream impact analysis. **Why**: bus-factor / blast-radius / CVE-cascade questions all reduce to dependency-graph queries — `opentelemetry-api` (rxm7706) has 149 dependents; that's bus-factor=1 critical infra worth knowing.

    **(2) Phase H — PyPI current version** (schema v7→v8). Fetches `info.version` from `https://pypi.org/pypi/<name>/json` per pypi-named row. Default-on, opt-out via `PHASE_H_DISABLED=1`. 8-worker `ThreadPoolExecutor`, TTL-gated 7d, 120s per-request timeout. Failure tracking: `pypi_version_last_error` records HTTP code or exception class. Live: ~85k rows fetched in the partial run (rate-limited by PyPI's per-IP limits at ~90 req/s sustained); rxm7706's 720 packages full backfill in 7.8 s. New `behind-upstream` CLI uses this + Phase K (below) to identify feedstocks lagging their upstream-of-record.

    **(3) Phase G snapshot history** (schema v8→v9). New `vuln_history(snapshot_at, conda_name, vuln_total, vuln_critical_affecting_current, vuln_high_affecting_current, vuln_kev_affecting_current)` side table. Phase G writes one row per scanned package per run at the end of its loop. Tiny addition (~30 lines); enables "what changed since last week?" queries via the new `cve-watcher` CLI. CLI flags: `--maintainer`, `--since-days N` (default 7), `--severity C|H|K|T`, `--only-increases`, `--limit`. Validated against synthetic delta (salt critical 5→10, +5 correctly diffed).

    **(4) Phase I — per-version downloads** (schema v9→v10). New `package_version_downloads(conda_name, version, upload_unix, file_count, total_downloads, fetched_at)` side table. Phase F's success path now ALSO writes per-version aggregates from the same anaconda.org payload — zero extra HTTP. Smoke tested on 3 packages (llms-py: 23 versions, oldest 199 dl decreasing to newest 83 dl; correct adoption-curve shape). Two new CLIs: `version-downloads <name>` (per-version detail with --by-downloads sort) and `release-cadence` (rolling-window release counts + accelerating/stable/decelerating/silent classification). Per-version backfill happens organically as Phase F TTL expires; no forced re-fetch needed.

    **(5) Phase K — VCS upstream-version cache** (schema v11) + side table (schema v12). Closes the gap raised mid-session: many recipes source from GitHub/GitLab/Codeberg directly, or from PyPI but the author releases to a VCS first. Phase K queries `releases/latest` (GitHub/Codeberg) or `/releases?per_page=1` (GitLab) per row, falls back to `/tags` if no release object exists. Multi-host: detects host from URL (`github.com`, `gitlab.com`, `codeberg.org`) and dispatches to the right API. Tag normalization is case-insensitive on the prefix (`Release_1_6_15` → `1_6_15`, `v3.0` → `3.0`, `RELEASE-2.0` → `2.0`). Auth: `GITHUB_TOKEN` env, then `gh auth token` fallback; `GITLAB_TOKEN` env for gitlab.com (works unauth at lower rate). Auto-skip when no GitHub auth — unauth API is 60 req/hr (too few). New `upstream_versions(conda_name, source, version, url, fetched_at, last_error)` side table holds ALL upstream versions across registries, keyed by source — adding a new registry (npm/cran/cpan/luarocks/maven/crates/rubygems/nuget) means adding a new resolver, not new columns. `behind-upstream` CLI now picks the right upstream-of-record per row based on `conda_source_registry` (pypi → pypi resolver; github → vcs first; other → vcs preferred). Validated: rxm7706 has 2 behind-upstream feedstocks (`bigframes 2.32.0→2.39.0`, `askbot 0.11.7→0.12.8`); displayed with a SOURCE column showing which upstream triggered the lag classification.

    **(6) Phase M — feedstock health from cf-graph pr_info** (schema v12→v13). Parses cf-graph's `pr_info/<sharded>/<f>.json` and `version_pr_info/<sharded>/<f>.json` lazy-json side files (already in the cached tarball). 6 new columns: `bot_open_pr_count`, `bot_last_pr_state`, `bot_last_pr_version`, `bot_version_errors_count`, `feedstock_bad`, `bot_status_fetched_at`. Live: parsed 28,862 pr_info + 28,862 version_pr_info files in 15.4 s, surfaced **4,121 bot-stuck feedstocks** channel-wide. Real signal: pytorch family at 1,811 stuck attempts each (notoriously hard to update on conda-forge); rxm7706's `opentelemetry-instrumentation-*` family at 25-27 attempts. New `feedstock-health` CLI with `--filter stuck|bad|open-pr|all`. **Why**: closes the user's directly-asked gap ("how do I get intelligence on failed PRs / broken builds / feedstocks with open issues / unmerged PRs") for the bot-driven cases. Human-PR / CI-status / open-issues count are out of scope (require live GitHub API); tracked as Phase N for v6.10.

    **Persona-mapped intelligence (now actionable):**

    | Persona | Question | CLI / Source |
    |---|---|---|
    | maintainer | What's behind upstream? | `behind-upstream --maintainer X` |
    | maintainer | Where are bots stuck? | `feedstock-health --filter stuck --maintainer X` |
    | maintainer | What's risky? | `staleness-report --maintainer X --by-risk` |
    | maintainer | What changed this week? | `cve-watcher --maintainer X` |
    | maintainer | Who depends on me? | `whodepends <pkg> --reverse` |
    | maintainer | What do I depend on? | `whodepends <pkg>` |
    | admin | Channel CVE exposure delta | `cve-watcher --severity C --only-increases` |
    | admin | Bot-stuck channel-wide | `feedstock-health --filter stuck` |
    | admin | Bus-factor=1 + heavy deps | `whodepends <pkg> --reverse` (combined with maintainer count) |
    | consumer | Per-version adoption / curve | `version-downloads <pkg>` |
    | consumer | Release cadence | `release-cadence --package <pkg>` |
    | consumer | Pkg health card | `detail-cf-atlas <pkg>` (gets all the above) |

    **Migration semantics.** Schema v6→v13: 7 sequential bumps but one cohesive `init_schema` migration. All ALTER TABLE / CREATE TABLE / CREATE INDEX statements are idempotent. Old DBs auto-migrate on next open. No data loss; backward-compat via `pypi_current_version` / `github_current_version` columns retained on `packages` while ALSO mirroring to `upstream_versions`. The legacy columns can be dropped in v7.0 once all callers migrate to the side table.

    **Validation matrix.**
      - Phase J: 282,504 edges across 27,740 feedstocks; `whodepends opentelemetry-api --reverse` returns 149 dependents. ✓
      - Phase H: 720 rxm7706 pypi names → 697 fetched + 23 404 in 7.8 s; `bigframes` and `askbot` correctly surfaced as behind-upstream. ✓
      - Phase G snapshot: 31,995 history rows written; `cve-watcher` correctly diffs synthetic delta (salt 5→10 +5). ✓
      - Phase I: per-version writes verified for llms-py (23 versions, expected adoption curve). ✓
      - Phase K: GitHub fetcher works on small sample (4/10 success, 6 no-tags from internal hack feedstocks); multi-host extraction passes manual probes for github.com / gitlab.com / codeberg.org. ✓
      - Phase M: 28,862 pr_info files parsed; 4,121 bot-stuck channel-wide; rxm7706 opentelemetry-instrumentation-* family correctly flagged with 25-27 stuck attempts. ✓
      - `behind-upstream` multi-source: shows SOURCE column ('pypi'|'github'|'gitlab'|'codeberg') so maintainers see WHICH upstream triggered the lag. ✓

    **Limitations / known follow-ups.** (a) GitHub auth required for Phase K — unauth API too low. (b) GitLab/Codeberg fetch tested via single sample; full backfill happens on first authenticated cf_atlas build. (c) Phase H's full PyPI backfill takes ~10 minutes serial; the partial run hit 85k of 805k rows before SIGTERM; remaining rows pick up via TTL on next build. (d) Per-version downloads only populate as Phase F TTL expires (7 days); existing rows retain `total_downloads` from before — no regression. (e) Phase M only captures cf-graph's view of bot PRs, not the live human-PR list, CI status, or open-issues count — those need a Phase N GitHub-API fetcher. (f) Multi-output feedstocks: Phase J only captures the primary output's deps. (g) Other registries (npm, cran, cpan, luarocks, maven, crates, rubygems, nuget) need resolvers — the side table architecture makes this a "add a resolver function + wire it in" change, but none ship in v6.9.0.

    **Docs.** SKILL.md frontmatter + `config/skill-config.yaml` bumped 6.8.0 → 6.9.0. `conda_forge_atlas.py` net change ~750 lines (5 new phase functions + schema migrations + dispatchers + new module-level helpers). Five new canonical scripts (`whodepends.py`, `cve_watcher.py`, `behind_upstream.py`, `version_downloads.py`, `release_cadence.py`, `feedstock_health.py`) with thin pixi-wrapper layer. Six new pixi tasks. No changes to MCP tool surface (deferred to v7.0).

- **v6.8.0**: Atlas v6 — Phase G vdb risk-summary cache + risk-aware tooling (May 9, 2026). Mirrors the actionable counts from the AppThreat vulnerability database into `cf_atlas.db` so risk queries work offline, in any pixi env, and at aggregate scale. Adds 6 schema columns, one new pipeline phase, two CLI flags on `staleness-report`, and a cached-vuln section in `detail-cf-atlas`.

    **(1) Phase G — risk-summary cache.** New `phase_g_vdb_summary` writes 4 count columns + a scan timestamp + a last-error TEXT for every active conda-forge row: `vuln_total` (lifetime CVEs across all purls), `vuln_critical_affecting_current`, `vuln_high_affecting_current`, `vuln_kev_affecting_current` (CISA Known Exploited Vulnerabilities), `vdb_scanned_at`, `vdb_last_error`. Reuses `fetch_vdb_data` from `detail_cf_atlas.py` (purl derivation + scoring logic) so there's one canonical source for "how does this row map to vdb?" — caching just the *counts* keeps storage modest while preserving the actionable signal. **Auto-skip when vdb library unavailable** via `importlib.util.find_spec("vdb.lib.search")` wrapped against `ModuleNotFoundError` (find_spec raises when top-level package missing, doesn't return None) — graceful degradation in the `local-recipes` env. Opt-out via `PHASE_G_DISABLED=1` in vuln-db env. Tunables: `PHASE_G_TTL_DAYS` (default 7), `PHASE_G_LIMIT` (debug). **Performance**: in-memory apsw-backed search → ~1500 req/s, full backfill of 31,969 rows in 20.6 s (vs Phase F's 30 min for downloads at 28 req/s — vdb is two orders of magnitude faster because the index is local). Concurrency stays serial; vdb's reader isn't documented as thread-safe and the perf is already excellent.

    **(2) Schema v5→v6 migration.** Six new columns via `ALTER TABLE`, all nullable so the migration is non-blocking. Same `init_schema` migration block as the prior version bumps (downloads, archived_at) — adds the new columns to existing DBs on next open. Verified the migration applies cleanly against the live DB and against a fresh DB created from the new SCHEMA_DDL. The view `v_packages_enriched` exposes the new columns via `p.*` (verified — 47 columns now visible through the view).

    **(3) `detail-cf-atlas` cached VDB section.** New section between Feedstock and Build matrix, conditional on (a) live vdb data NOT being shown (no `--vdb`, or `--no-vdb`, or vdb library unavailable) AND (b) the atlas having a cached scan. Renders RISK level (CRITICAL/HIGH/MEDIUM/LOW), the C/H/KEV breakdown for the current version, the lifetime total, the scan timestamp, and any last_error. Includes a hint pointing to `detail-cf-atlas-vdb` for the full CVE list. Lets `local-recipes`-env callers see the risk signal without spinning up the heavy vuln-db env. Verified against `salt`: from `local-recipes`, the section reads `RISK: CRITICAL — Affecting v2016.3.0: 10 Critical, 10 High, 0 KEV — Total: 45`.

    **(4) `staleness-report --by-risk` and `--has-vulns`.** Two new flags on the existing CLI:
      - `--by-risk` reorders the result by `vuln_critical_affecting_current DESC, vuln_high_affecting_current DESC, vuln_kev_affecting_current DESC, latest_conda_upload ASC` — surfaces feedstocks that combine "actively risky" with "old release."
      - `--has-vulns` filters to feedstocks where Critical or High CVEs affect the current version — the actionable subset.

    The table renderer gained a `C/H/KEV` column showing affecting-current counts and a `TOTAL` column showing lifetime CVEs. The C/H/KEV column shows `—` when `vdb_scanned_at` is NULL (Phase G hasn't run for that row), keeping the schema-old-DB case readable. Validated: `staleness-report --by-risk --limit 5` correctly surfaces `salt 2016.3.0 (10/10/0)` and four versioned `airflow-with-*` packages with high concentrations of affecting-current CVEs; `staleness-report --maintainer rxm7706 --by-risk` correctly highlights `weasyprint 67.0` (the only rxm7706 feedstock with a non-zero High count: 0/1/0).

    **vdb data refresh (operational note).** During v6.8.0 development the existing `~/.../vdb/data.vdb6` file (2.5 GB on disk) had **0 rows in `cve_data`** — a stale cache from before the apsw schema migration. `pixi run -e vuln-db vdb-refresh` (the `--cache` path) reloaded ~875k CVEs from OSV + GitHub sources successfully. The faster `--download-image` path is currently broken upstream (oras-py's `Container.manifest_url` API changed; the vdb library still calls the old name); this is an external bug and not something v6.8.0 can fix. Ops doc: if Phase G shows all packages with `vuln_total=0`, run `vdb-refresh` first to repopulate the index.

    **Validation matrix.**
      - Schema migration: 6 new columns added; init_schema idempotent; no data loss. ✓
      - Phase G auto-skip in `local-recipes` env: returns `{"skipped": True, "reason": "vdb library not installed..."}` cleanly without crashing on missing module. ✓
      - Phase G full backfill in `vuln-db` env: 31,969 rows in 20.6 s, 0 failures, 0 no_purls. ✓
      - Real signal verification: `django=90`, `cryptography=19`, `urllib3=16`, `jinja2=8`, `requests=6` total CVEs (none affecting current — well-patched releases); `salt=45` total / 10 Critical / 10 High affecting current; `weasyprint=2` total / 1 High affecting current. ✓
      - Cached VDB section in `local-recipes` detail card: renders only when no live vdb data AND `vdb_scanned_at IS NOT NULL`; correctly omits otherwise. ✓
      - `staleness-report --by-risk` and `--has-vulns` exercised against live data; render correctly with the new C/H/KEV column and "(ordered by risk)" title decoration. ✓

    **Limitations / known follow-ups.** (a) Phase G stores only counts, not the CVE rows themselves — full CVE listings still require the vuln-db env's `detail-cf-atlas-vdb` task. Storing rows would 100x the DB size; the current shape is the right trade-off. (b) `vuln_total` is the *lifetime* count across all versions, not affecting-current — consumers wanting "is this version safe" should look at `vuln_critical_affecting_current` + `vuln_high_affecting_current` + `vuln_kev_affecting_current`. (c) The vdb meta sidecar (`vdb.meta`) is not consulted by Phase G — staleness of the underlying vdb is operator-tracked. A future Phase G enhancement could read the meta and warn when the vdb itself is older than N days. (d) Phase G is opt-out only via env var; there's no per-row failure mode beyond `vdb_last_error` (which today is set only when fetch_vdb_data raises). Catastrophic failure modes (e.g., vdb library imports but the index is corrupted) would result in 0 vulns reported across the board, which is what we just lived through.

    **Docs.** SKILL.md frontmatter + `config/skill-config.yaml` bumped 6.7.1 → 6.8.0. `conda_forge_atlas.py` net change ~150 lines (Phase G function + schema migration). `detail_cf_atlas.py` net change ~30 lines (cached VDB section + None-narrowing fix on the live VDB section). `staleness_report.py` net change ~50 lines (--by-risk + --has-vulns + extended renderer). No changes to MCP tool surface. No new files.

- **v6.7.1**: VDB on-by-default in the `vuln-db` pixi env (May 9, 2026). Tiny operational patch that shifts the vuln pass from "you must remember `--vdb`" to "it's automatic in the env that has the dep." No schema changes, no atlas changes; one pixi-task tweak and a small argparse upgrade.

    **(1) `[feature.vuln-db.tasks.detail-cf-atlas]` cmd now passes `--vdb`.** The vuln-db env already ships `appthreat-vulnerability-db[all]` and a 2.5 GB local index — making the user pass `--vdb` every time was redundant friction. New default behavior: `pixi run -e vuln-db detail-cf-atlas <name>` always shows the VDB Security section (severity counts, KEV flag, affecting-current-version). `pixi run -e local-recipes detail-cf-atlas <name>` is unchanged — vuln lookup stays opt-in there because the env doesn't have the dep. The verbose variant `detail-cf-atlas-vdb` (`--vdb --vdb-all`) is unchanged — still the right call when you want every CVE listed, not just the summary.

    **(2) `--vdb` upgraded to `argparse.BooleanOptionalAction`.** Adds a real `--no-vdb` flag for the case where someone is in the vuln-db env but wants the fast non-vdb card (e.g., a quick license/maintainer lookup with no need to scan vulns). Last-wins argparse semantics mean `pixi run -e vuln-db detail-cf-atlas <name> --no-vdb` correctly skips the vdb pass even though the task command passes `--vdb`. The flag's help text documents this. **Why**: without the negation, baking `--vdb` into the task would have removed an escape hatch — users could no longer get the fast card from the vuln-db env. With it, the env's default is "show vulns" and the override is "actually skip them."

    **Validation.**
      - `pixi run -e vuln-db detail-cf-atlas llms-py` (default): VDB Security section renders, RISK: LOW, 0 vulns across 4 purls in 0.1 s. ✓
      - `pixi run -e vuln-db detail-cf-atlas llms-py --no-vdb`: source summary shows `— vdb ... — --vdb not requested`, no VDB section. ✓
      - `pixi run -e local-recipes detail-cf-atlas llms-py`: unchanged behavior, no VDB section. ✓

    **Limitations / known follow-ups.** The architectural decision to keep vdb data outside `cf_atlas.db` (per the v6.7.0 review) still stands — vdb is its own multi-source database with its own refresh cycle (`vdb-refresh`). A future "Phase G — risk summary cache" would mirror just the counts (`vuln_total`, `vuln_critical_affecting_current`, `vdb_scanned_at`) into `packages` so the staleness CLI and any non-vuln-db-env caller can rank by risk without spinning up the heavy env. Tracked but not in this patch.

    **Docs.** SKILL.md frontmatter + `config/skill-config.yaml` bumped 6.7.0 → 6.7.1. `pixi.toml` two-line edit (cmd + description). `detail_cf_atlas.py` one-line argparse switch. No other files changed.

- **v6.7.0**: Atlas v5 — symmetric status transitions, archived-at timestamps, and a code-hygiene pass (May 9, 2026). Three independent atlas refinements that close lingering correctness and cosmetic gaps; one new column; no breaking changes.

    **(1) `latest_status` symmetric promotion + demotion (Phase B.6 rewrite).** Pre-v6.7 Phase B.6 ran a single `UPDATE ... SET latest_status='active' WHERE latest_conda_version IS NOT NULL AND latest_status IS NULL` — first-time activation only. Two related correctness gaps shipped silently for months: (a) **demotion miss** — packages dropped from `current_repodata.json` between builds kept stale `'active'` because Phase B's UPSERT doesn't touch unseen rows and `latest_conda_version` stayed populated from the prior build; (b) **promotion miss** — Phase B.5 inserts (registered in feedstock-outputs but absent from current repodata) start as `'inactive'`; if the package later appeared in repodata, Phase B's UPSERT wrote `latest_conda_version` but Phase B.6's `IS NULL` guard prevented the row from being promoted, leaving it stuck `'inactive'` forever. Sample on the live DB surfaced 3 such ghosts — `ad-hoc-diffractometer v0.10.1`, `pyfuga v0.3.0`, `chexus v26.5.2` — all uploaded 2026-05-08 and showing as `inactive`. Fix: Phase B now populates a `current_repodata_names` TEMP table (per-connection, per-session lifetime) inside its existing transaction; Phase B.6 then runs two SQL statements that together compute `active = name in current_repodata_names`: a promote pass (any row whose name is in the temp table and whose status isn't already `'active'`) and a demote pass (any row marked `'active'` whose name isn't in the temp table). Verified: same run promoted exactly the 3 ghosts to `'active'`, post-condition `latest_status='inactive' AND conda_name IN current_repodata` returns 0. Falls back to the original lite rule for partial-pipeline runs that skip Phase B (no temp table → no signal). Stats dict now reports `promoted_count` and `demoted_count` separately. **Why**: any quarterly maintenance review that filters on `latest_status='active'` was either undercounting (missed promotions) or overcounting (missed demotions) — the bug was silent because per-package lookups happened to land on whichever status they had on the first-build day.

    **(2) `archived_at` column (schema v4→v5).** Phase E.5 already had the GraphQL data — `Repository.archivedAt` is a documented field on conda-forge org repos — but only stored the boolean `feedstock_archived`. Now writes the timestamp. Implementation: GraphQL query extended from `nodes { name }` to `nodes { name archivedAt }`; ISO 8601 string parsed via `datetime.fromisoformat` (with the standard `Z`→`+00:00` substitution) into UNIX seconds; `archived_at` column added to `packages` schema and `init_schema` migration. Phase E.5's reset pass now clears stale `archived_at` on rows that were unarchived since the last build (defaulting both columns together keeps them in sync). Result on the live DB: 742 archived rows, all with timestamps; oldest 2020-04-22 (`terraform-provider-atlas`), newest 2026-05-01 (`pytorch-lightning`); `vllm-nccl-cu12` (the only rxm7706 archived feedstock) stamped 2025-03-18. **Decision: no `archived_reason` column.** GitHub's GraphQL Repository type does not expose an "archive reason" field — that's manual operator knowledge not stored on the repo. The existing `notes` column on `packages` is the right place for hand-curated annotations if the signal becomes useful.

    **(3) Pyright unused-identifier cleanup.** Three standing diagnostics from before this session: `filename` in `_aggregate_repodata_records` (unused tuple element from `dict.items()`), `conn` in the `phase_c5_source_url_match` stub (folded-into-E placeholder), `args` in `cmd_stats` (uniform argparse dispatch signature). Fixed by: switching the loop to `dict.values()` directly (eliminates the unused name); adding `_ = arg` no-op assignments in the two phase/dispatch stubs (the standard Python idiom Pyright respects, after the underscore-prefix rename and inline `# pyright: ignore` pragma both failed to suppress the hint). Net diff: one less variable binding in the hot Phase B aggregate, two trivial `_ = arg` lines. **Why**: standing diagnostics tax future readers who can't tell signal from noise; clearing them keeps the panel honest so real warnings register.

    **Validation matrix.**
      - Phase B + Phase B.6 isolated re-run: promoted=3, demoted=0, post-condition `latest_status='inactive' AND name IN current_repodata` = 0. ✓
      - Phase E.5 with extended GraphQL: 742 rows marked archived, 742 with `archived_at` populated, ISO-to-UNIX conversion verified against 2026-05-01 timestamp. ✓
      - `stats-cf-atlas`: meta JSON exit code 0, schema_version reads "5". ✓
      - `phase_c5_source_url_match` and `cmd_stats` smoke imports: both execute, no stack changes. ✓

    **Limitations / known follow-ups.** (a) Phase B.6's lite mode still defers true per-version yanked detection (the `removed/` set inside repodata) — out of scope for v6.7; tracked since v6.5. (b) `archived_at` is per-feedstock, not per-package — multi-output feedstocks share the same archive timestamp by design (the feedstock is the GitHub repo). (c) The temp-table approach in Phase B requires Phase B and Phase B.6 to run in the same connection, which they do via `cmd_build`'s shared `conn`; if a future caller breaks that invariant, B.6 falls back to lite mode rather than crashing.

    **Docs.** SKILL.md frontmatter + `config/skill-config.yaml` bumped 6.6.0 → 6.7.0. `conda_forge_atlas.py` net change ~70 lines (Phase B.6 rewrite, Phase E.5 GraphQL extension + ISO parsing, schema migration, hygiene cleanups). Schema v4→v5 migration adds one column via `ALTER TABLE`; auto-runs in `init_schema` on next open.

- **v6.6.0**: Atlas v4 — recipe-format detector fix, Phase F failure tracking, and staleness CLI (May 9, 2026). Three independent improvements that close real bug + ergonomics gaps surfaced by the v6.5.0 sweep. Schema bumps v3→v4; one new public command; no breaking changes.

    **(1) Phase E `recipe_format` classifier fix.** The pre-v6.6 detector inspected `payload.get("rendered_recipes")` — a field cf-graph-countyfair does not emit. The branch fell through to `"unknown"` for every package globally, hiding real v0/v1 distribution. Replacement: read `meta_yaml.schema_version` (cf-graph's actual key — `0` for v0 `meta.yaml`, `1` for v1 `recipe.yaml`), with a `raw_meta_yaml` head-byte fallback (`{% set` → v0; `context:` → v1) for entries missing the explicit schema_version. Verified against 6 mixed samples (django/awscli/cachetools/json5 → v0; numpy/pyiceberg → v1) before applying. Re-running Phase E reclassified 31,389 rows: global distribution now **24,598 v0 / 6,675 v1 / 116 unknown / 1,539 NULL**; rxm7706's 732 packages split **475 v0 / 257 v1** (35% v1, vs 0% under the broken classifier). **Why**: any aggregate or filter on `recipe_format` was silently broken — affected the v6.5.0 retro reports and any future "which of my recipes still need v0→v1 migration" queries.

    **(2) Phase F failure-tracking columns (schema v4).** Two new columns on `packages`: `downloads_fetch_attempts INTEGER` (incremented on every fetch attempt — success, 404, or fail) and `downloads_last_error TEXT` (populated on failure, cleared on success). v6.5.0 conflated transient and persistent failures: yesterday's "1 transient failure" was actually `awscli` failing every time because its 120 MB / 55 s response exceeded the 30 s urllib timeout — invisible to the operator until I manually re-ran the fetch and watched it fail again. With v6.6, the same situation surfaces immediately:

        SELECT conda_name, downloads_fetch_attempts, downloads_last_error
          FROM packages
         WHERE downloads_last_error IS NOT NULL
         ORDER BY downloads_fetch_attempts DESC;

    `_phase_f_fetch_one` now returns a 5-tuple `(name, latest, payload, status, err_msg)`. Success: clears `last_error`, bumps `attempts`. 404: sets short `HTTP 404` error, bumps `attempts`. Fail: writes the HTTP code or exception class name (truncated to 120 chars), bumps `attempts`, leaves `downloads_fetched_at` untouched so the row stays TTL-eligible. Schema v3→v4 migration is automatic in `init_schema` via the existing `ALTER TABLE` block.

    **(3) `staleness-report` CLI — first dedicated maintainer dashboard.** New canonical `.claude/skills/conda-forge-expert/scripts/staleness_report.py` + thin wrapper `.claude/scripts/conda-forge-expert/staleness_report.py` + `pixi run -e local-recipes staleness-report` task. Reads `cf_atlas.db` offline; lists active feedstocks ordered by oldest `latest_conda_upload`. CLI:

        staleness-report [--maintainer HANDLE] [--days N]
                         [--limit N] [--all-status] [--json]

    Default scope: active (non-archived) feedstocks. `--maintainer HANDLE` joins through `package_maintainers`; `--days N` applies an age floor; `--all-status` includes archived; `--json` swaps the table for structured output (suitable for piping into `jq` or feeding back to the agent). Table columns: package, version, uploaded date, age in days, lifetime downloads, recipe format, archived flag. Validated against rxm7706's stalest 10 (correctly surfaces `django_compressor` at 2,504 days and the dbt 1.0.0 supersession lurking at 1,611 days) and against the global stalest-since-2017 cohort (`llvm-lto-tapi` at 3,160 days). **Why**: the kind of question maintainers ask quarterly ("which of my feedstocks need attention?") was previously a one-off SQL session; now it's a single command that persists across sessions and is JSON-queryable for automation.

    **Validation matrix.**
      - Phase E re-run with corrected classifier: 31,389 rows enriched in 21.3s (cached cf-graph tarball, no network refetch). ✓
      - Phase F failure-tracking write paths exercised on `llms-py` (success path: `attempts=1`, `last_error=NULL`). 0 rows in the entire DB carry a non-null `last_error` after the first run, confirming no silent persistent failures. ✓
      - `staleness-report --maintainer rxm7706 --limit 10`: returns the same 10 packages the v6.5.0 ad-hoc query produced. ✓
      - `staleness-report --days 1825 --limit 5`: surfaces oldest-globally cohort starting from 2017. ✓
      - `staleness-report --json`: well-formed JSON with `age_days` and `uploaded_iso` derived fields included. ✓

    **Limitations / known follow-ups.** (a) `staleness-report` orders by `latest_conda_upload` only — does not yet compare to upstream PyPI version. A "behind PyPI" view would require either a Phase F-style fetch loop over `pypi.org/pypi/<name>/json` or a reuse of `pypi_last_serial` (which only changes on PyPI activity, not just version bumps). Tracked as a future enhancement. (b) The 116 globally-unknown `recipe_format` rows likely have empty `meta_yaml` and missing `raw_meta_yaml` in the cf-graph snapshot — usually feedstocks where parsing failed upstream. Could be probed via a separate phase that hits the feedstock repo directly, but the cost/benefit doesn't justify it yet.

    **Docs.** SKILL.md frontmatter + `config/skill-config.yaml` bumped 6.5.0 → 6.6.0. `conda_forge_atlas.py` gained ~50 lines (failure-tracking + classifier rewrite). New `staleness_report.py` (skill canonical, ~155 lines) + thin wrapper (~15 lines) + pixi task. No changes to MCP tool surface. Schema v3→v4 migration automatic; old DBs add the two new columns on next `init_schema` call.

- **v6.5.0**: Atlas v3 — download counts, deduplication, and rebuild idempotency (May 9, 2026). Three coordinated changes to `conda_forge_atlas.py` plus a `detail_cf_atlas.py` polish; closes long-standing rebuild duplication and extends the per-package metadata surface.

    **(1) Phase F — per-package download counts via anaconda.org.** New `phase_f_downloads` reads `https://api.anaconda.org/package/conda-forge/<name>` for every active row and writes three columns: `total_downloads` (lifetime, summed across every file/version), `latest_version_downloads` (subset matching `latest_conda_version`), and `downloads_fetched_at` (UNIX seconds; TTL guard). 8-worker `ThreadPoolExecutor`, single SQLite writer thread, periodic commits every 500 rows. Per-request timeout 120s — calibrated against `awscli`, the outlier whose endpoint returns ~120 MB / 61k files / 2.5k versions in ~55 s; with 8 workers one slow row doesn't gate the others. Cold backfill: 32,893 rows in 30 min (~28 req/s steady, no 429s, 0 failures after the timeout calibration). TTL-gated re-runs are cheap; default-on since TTL keeps warm runs ~free. Tunables: `PHASE_F_DISABLED=1` (opt-out), `PHASE_F_TTL_DAYS` (default 7), `PHASE_F_CONCURRENCY` (default 8), `PHASE_F_LIMIT` (debug). Failure handling: 429 retries 3× per task with exponential backoff (caps at 5s); 404 records `0 / 0 / now` so we don't re-poll dead packages; transient network errors leave the row untouched and retry next run. **Why**: download counts are the most-requested signal for triaging "which feedstocks matter" and "is this the right pin priority"; previously the only path was hand-curling anaconda.org per package.

    **(2) Schema v3 + `packages` deduplication migration.** Pre-v3 rebuilds duplicated every conda row because Phase B's `INSERT INTO packages` had no conflict resolution — each rebuild appended a fresh row beside the existing one (32,629 distinct conda_names had exactly 2 rows after the May-8 rebuild). Diagnosis: 47/50 sample duplicates were bit-identical; the other 3 differed only in `pypi_last_serial` (Phase D's `existing_pypi` set was built from current state and only matched the originally-inserted row). Three-layer fix: (a) `_dedupe_packages_by_conda_name()` migration runs in `init_schema` before the unique index is created — keeps the row with non-NULL `pypi_last_serial` (`ROW_NUMBER() OVER (PARTITION BY conda_name ORDER BY (pypi_last_serial IS NULL), rowid)`), drops the rest; (b) `CREATE UNIQUE INDEX uq_conda_name ON packages(conda_name)` — SQLite's NULL-distinct UNIQUE semantics keep PyPI-only rows (where conda_name is NULL) coexisting freely; (c) Phase B's `INSERT` becomes `INSERT ... ON CONFLICT(conda_name) DO UPDATE SET conda_subdirs = excluded.conda_subdirs, ...` — refreshes `conda_*` fields and resets `relationship`/`match_*` to the `conda_only` baseline (later phases re-classify), preserves `pypi_*`, `feedstock_*`, `total_downloads`, and `downloads_fetched_at` so a rebuild doesn't trash work from later phases. Verification: 32,629 duplicate rows deleted; 0 remaining; subsequent Phase B re-run produced +4 net rows (genuine repodata churn) and 0 new duplicates; `llms-py` retained `pypi_last_serial=36433785` and `total_downloads=6356`. **Why**: any aggregate query (`COUNT(*)`, `SUM(total_downloads)`) was previously off by 2× for conda packages; the bug was silent because per-package lookups happened to land on either duplicate.

    **(3) `detail-cf-atlas` Downloads section.** New section between Feedstock and Build matrix:

        ──────────────────────────────────────────────────────────
          Downloads (anaconda.org, cached in atlas)
        ──────────────────────────────────────────────────────────
          Lifetime:        6,356
          Latest (v3.0.44):    82
          Fetched:         2026-05-08 22:22 UTC (today)

    Conditional — packages without download data (e.g., archived feedstocks excluded by Phase F's filter) cleanly omit the section. Reuses the existing `_humanize_timestamp` helper and `record.get(...)` accessor pattern, so no new code paths in `fetch_atlas`.

    **Migration semantics.** v1→v2 (download columns via `ALTER TABLE`) and v2→v3 (dedupe + UNIQUE INDEX) both run automatically on every `init_schema` call. Idempotent — once `uq_conda_name` exists, the dedup is skipped. No data loss on either step; `llms-py` and 49 other sampled packages verified column-by-column post-migration.

    **Validation matrix.**
      - Atlas full build (PHASE_E_ENABLED=1, default Phase F): all phases green; row counts dropped from 849,284 → 816,659 (the −32,629 dedup + 4 new repodata rows). ✓
      - rxm7706 maintenance summary across 732 packages: 88,319,648 lifetime downloads, 8,043,692 latest-version. ✓
      - `detail-cf-atlas llms-py` renders Downloads section with correct values matching the upstream anaconda.org API. ✓
      - `package_maintainers` junction table unaffected (foreign-keyed on `conda_name`); 1 maintainer link per `(conda_name, handle)` survived the dedup. ✓

    **Limitations / known follow-ups.** (a) Phase E's `recipe_format` detector returns `"unknown"` for 100% of v0 `meta.yaml` recipes — the classifier only inspects v1 `recipe.yaml` schema. Affects all conda-forge stats, not just one maintainer's view. Tracked for a future Phase E refinement. (b) `latest_status` doesn't have a clean `active → inactive` transition path: a package that disappears from `current_repodata.json` between builds keeps `latest_status='active'` because Phase B's UPSERT doesn't touch unseen rows and Phase B.6 only flips to `'active'`. Minor — usually self-healing via Phase B.5's feedstock-outputs source. (c) The `packages` table's pre-v3 duplication produced 31,389 Phase E enrichment matches today vs 62,488 yesterday (exactly half), confirming yesterday's number was inflated by the duplicates — anyone with stored Phase E stats from before the migration should redo the count.

    **Docs.** SKILL.md frontmatter + `config/skill-config.yaml` bumped 6.4.0 → 6.5.0. `conda_forge_atlas.py` gained ~110 lines (Phase F + dedup migration + UPSERT change); `detail_cf_atlas.py` gained 12 lines (Downloads section). No changes to MCP tool surface. No backward-incompatible changes — old DBs auto-migrate; old detail-card output is a strict subset of the new.

- **v6.4.0**: Feedstock-aware generation — recipes for packages with an existing conda-forge feedstock automatically inherit hand-curated maintainers and metadata, and a new MCP tool surfaces feedstock issues as planning context (May 7, 2026). Three new sub-features built on one shared lookup primitive; eliminates the previous manual step of cross-referencing `conda-forge/<pkg>-feedstock` after generation.

    **(1) `feedstock_lookup.py` — shared primitive.** New `.claude/skills/conda-forge-expert/scripts/feedstock_lookup.py`. Probes `gh api /repos/conda-forge/<pkg>-feedstock` for existence, then fetches `recipe/recipe.yaml` (preferred) or `recipe/meta.yaml`, base64-decodes the contents, parses YAML (Jinja2 `{% set %}` directives stripped, `{{ var }}` substituted with bare `JINJA_PLACEHOLDER` tokens to keep multi-token scalars like `{{ PYTHON }} -m pip install` valid). Caches results for 1 hour at `.claude/data/conda-forge-expert/feedstock_cache/`. Returns `exists=False` (with no error) for new packages — that's the common case and shouldn't trigger error handling. **Why**: 3a, 3b, and 3c all need the same lookup; doing it once and caching avoids three GitHub API round-trips for what is essentially one question.

    **(2) `feedstock_enrich.py` — items 3a + 3b combined.** New post-processor invoked after grayskull/recipe-generator finishes. Field-by-field merge policy verified against `prefix-dev/recipe-format` `$defs.About` and the `reference_v0_v1_about_fields` skill memory: `extra.recipe-maintainers` is always a union with `rxm7706` (dedup, idempotent — runs cleanly even when no feedstock exists); `extra.recipe-maintainers-emeritus` and `extra.feedstock-name` carry over verbatim; `about.homepage`/`repository`/`documentation` are feedstock-wins-when-grayskull-empty; `about.description` is feedstock-wins-if-longer (hand-written paragraphs); `about.summary` always grayskull-wins (freshest from PyPI); `about.license_file` is feedstock-wins (often involves resolved paths or secondary sources, like cocoindex's missing-LICENSE GitHub fallback). License divergence is a **hard abort** — `enrich_from_feedstock` returns `abort_reason` rather than silently picking a side, since license changes have legal implications. v0→v1 about-field translation (`home`→`homepage`, `dev_url`→`repository`, `doc_url`→`documentation`) handles meta.yaml feedstocks transparently. Per Q&A D3: `requirements.host/run/build` are **never** carried over — grayskull is always authoritative for dependency resolution.

    **(3) `feedstock_context.py` — item 3c, issue surface.** New `gh issue list`-backed tool fetches open + last 10 closed issues from the feedstock and returns structured summaries (number, title, labels, author, url, comment count, timestamps). 30-minute cache (issues change faster than recipe content). Per Q&A D1: non-blocking — the agent surfaces findings to the user as planning context, never auto-applies. Per Q&A D2: cap at 50 open + 10 closed (overridable via `--max-open` / `--max-closed`). Verified end-to-end against `conda-forge/django-feedstock`: returned 2 open bug-tagged issues + recently closed Windows-build failures (one filed by rxm7706 — the issue catalog is genuinely useful planning context).

    **(4) Three new MCP tools** in `.claude/tools/conda_forge_server.py`: `lookup_feedstock(pkg_name, no_cache)`, `enrich_from_feedstock(recipe_path, dry_run)`, `get_feedstock_context(pkg_name, max_open, max_closed, no_cache)`. Each thin-wraps the corresponding script; the agent invokes them just like the existing `validate_recipe`/`optimize_recipe` MCP tools.

    **(5) SKILL.md Step 1b "Feedstock-aware enrichment".** New step inserted between Step 1 (generate) and Step 2 (validate). Codifies the recommended sequence: `get_feedstock_context` first (planning input) → `enrich_from_feedstock` (apply merges) → continue with Step 2 validation. Documents the carry-over policy concisely with a "what never carries over" guard rail and the hard-abort behavior on license divergence.

    **End-to-end validation.**
      - cocoindex (no feedstock yet): `enrich_from_feedstock` reports `feedstock_exists=False`, idempotently ensures `rxm7706` is in maintainers, and writes nothing else. ✓
      - django (existing v0 meta.yaml feedstock): correctly merged 3 existing maintainers + rxm7706, translated v0 about names to v1 (`home`→`homepage`, `dev_url`→`repository`, `doc_url`→`documentation`), carried over `license_file: LICENSE`, did NOT overwrite the grayskull-supplied summary. ✓
      - django issue surface returned `2 open + 2 recent-closed`, with bug-labels and a real PR-relevant Windows tzdata failure visible. ✓

    **Q&A locked at start of release** (per session memory): D1 — issue surface non-blocking. D2 — last 10 closed + all open, capped at 50 open. D3 — never carry feedstock requirements. D4 — for v0→v1 translation, reuse the v0/v1 mapping memory (the active feedstock_enrich just inlines that 4-key map; it does not call `migrate_to_v1` because that tool rewrites whole recipes, which is the wrong scope here).

    **Limitations / known follow-ups.** No automatic re-fetch when a feedstock's recipe is edited mid-cache-window — agents who suspect staleness should pass `no_cache=True`. Issue surface is gh CLI-dependent — works in environments where `gh auth` is configured (the same precondition `submit_pr` relies on). Description-length comparison (3b) uses `len(str(...))`; if a feedstock has a Markdown-rich description that's longer but lower-quality than grayskull's PyPI summary, the heuristic prefers the longer one — manual override remains available via direct `edit_recipe`.

    **Docs.** SKILL.md frontmatter + `config/skill-config.yaml` bumped 6.3.0 → 6.4.0. Three new scripts (`feedstock_lookup.py`, `feedstock_enrich.py`, `feedstock_context.py`). Three new MCP tools. New SKILL.md Step 1b. No backward-incompatible changes — existing workflow is a strict superset.

- **v6.3.0**: Two-tier build workflow — native rattler-build is the new default; Docker is opt-in (May 7, 2026). Codifies the v6.2.2 manual `--variant-config` overlay pattern as a first-class build path with auto-platform-detection. The previous single Docker-driven Step 7 in SKILL.md is split into 7a (native, mandatory) and 7b (Docker, opt-in) with explicit triggering rules.

    **(1) `mcp__conda_forge_server__trigger_build` adds `mode={"native","docker"}`.** Default is `"native"` — runs `rattler-build build` directly on the host with two `--variant-config` flags: the platform variant from `.ci_support/<config>.yaml` and conda-forge-pinning's `conda_build_config.yaml` from the local-recipes pixi env. Auto-detects the platform via `platform.system()/platform.machine()` (`Linux/x86_64` → `linux64`, `Darwin/arm64` → `osxarm64`, etc.) when `config` is omitted. The new `recipe=<path>` parameter is required for native mode (Docker mode builds all of `recipes/`). Output lands in `build_artifacts/<config>/`. **Why**: the v6.2.2 fix documented the two-overlay invocation manually; v6.3 makes it a tool-level default so the agent never reaches for Docker accidentally and the correct env stays consistent across sessions.

    **(2) New pixi tasks `recipe-build` and `recipe-build-docker`** in `pixi.toml` under `[feature.local-recipes.tasks.*]`. `recipe-build` invokes a new shell wrapper `.claude/scripts/conda-forge-expert/native-build.sh` that does the same auto-detect + dual-variant-config invocation but from the CLI side (`pixi run -e local-recipes recipe-build recipes/<name>`). The wrapper warns clearly if the conda-forge-pinning overlay is missing and tells the user how to populate it (`pixi install -e local-recipes`). `recipe-build-docker` is a thin wrapper around `python build-locally.py <config>`. Both tasks live alongside the existing `submit-pr` task so the build → submit pipeline is one cohesive set.

    **(3) SKILL.md workflow restructure.** The single Step 7 ("Trigger Build") is replaced with **Step 7a (Native build, mandatory)** and **Step 7b (Docker build, opt-in)**. The new section codifies four rules: native is the default verification gate; noarch:python recipes need only one host build (no platform iteration); compiled recipes use 7a for recipe-correctness verification, 7b for non-host platforms; Docker is **never** invoked automatically — only on explicit user request or to debug a CI failure. The Build Failure Protocol gains a new distinction: "host build passes + Docker fails → sysroot/CDT mismatch (alma9 vs host glibc)" vs "host build fails → fix the recipe first; don't try Docker as a workaround."

    **Q&A locked at start of release** (per session memory): Q1 — compiled recipes never auto cross-target (Docker only). Q2 — auto-detect host via `uname -ms`. Q3 — Docker always opt-in. Q4 — task names `recipe-build` + `recipe-build-docker` (avoiding bare `build` to prevent collision with conda-build's `build/` artifact dir).

    **Validation.** `recipe-build` executed against `recipes/cocoindex` with `--render-only` substituted manually produces the same render that v6.2.2's documented invocation produces; `mode="native"` invocation through the MCP tool wraps the same command set. Pyright clean.

    **Limitations / known follow-ups.** `get_build_summary()` does not yet write a structured summary file for native-mode builds (it currently relies on `build-locally.py` to produce `build_summary.json`). Native builds report `status: in_progress` while running and `status: unknown` after exit; the agent must check the artifact directory (`build_artifacts/<config>/*.conda`) to confirm success. Will be addressed in a follow-up patch when a JSON summary path is added to the rattler-build wrapper.

    **Docs.** SKILL.md frontmatter + `config/skill-config.yaml` bumped 6.2.2 → 6.3.0. New `.claude/scripts/conda-forge-expert/native-build.sh` (executable, 51 lines). `pixi.toml` gains 2 task entries. `mcp__conda_forge_server__trigger_build` MCP tool docstring describes both modes and the auto-detection table. No backward-incompatible changes for `mode="docker"` callers (existing `trigger_build(config=...)` calls still work — old positional config arg now requires `mode="docker"` to retain prior behavior, but the default `mode="native"` requires the recipe path which existing code didn't pass).

- **v6.2.2**: Correction of v6.2.1's rule #6 (May 7, 2026). v6.2.1 added a Python Version Policy rule claiming that `noarch: python` recipes "must now declare `python_min` explicitly in `context:`" because variant configs stopped providing the default. **That diagnosis was wrong** — the canonical source of `python_min: '3.10'` has always been the `conda-forge-pinning` package, not `.ci_support/*.yaml`. The May 2026 upstream sync removed redundant declarations from the platform variant configs but did NOT change the underlying default. Recipes that reference `${{ python_min }}` without declaring it in context still resolve correctly when conda-forge-pinning is on the variant-config path — exactly as upstream CI has always handled it.

    **What changed.** SKILL.md § Python Version Policy rule #6 rewritten:
    - Old (wrong): "All noarch:python recipes must now declare python_min explicitly in their context: block."
    - New (correct): "Recipes do NOT need python_min in context unless overriding the default. Only set context.python_min when upstream python_requires demands a floor higher than 3.10."

    **Local rattler-build instruction added.** When invoking rattler-build directly, pass conda-forge-pinning's `conda_build_config.yaml` as a second `--variant-config`. The `local-recipes` pixi env already installs conda-forge-pinning; the file lands at `.pixi/envs/local-recipes/conda_build_config.yaml`. Verified by rendering `recipes/python-magic/recipe.yaml` (uses `${{ python_min }}` four times, no `context.python_min` declaration) — fails with the platform variant alone, succeeds with the pinning overlay.

    **How it was caught.** Audit-driven: the user pointed out that recipes don't need `python_min` for conda-forge submission, so the local build flow shouldn't either. Investigation found that `conda-forge-pinning` (already installed in the pixi env, version 2026.05.04.16.48.45) ships exactly the missing keys and rattler-build accepts multiple `--variant-config` flags.

    **Impact on prior diagnosis.** The earlier "SEL-002 false-negative" hypothesis (that the optimizer should warn when `${{ python_min }}` is referenced but not in context) is also dropped — that pattern is now confirmed correct, not a bug. SEL-002's existing logic stands.

    **Docs.** SKILL.md frontmatter + `config/skill-config.yaml` bumped 6.2.1 → 6.2.2. No other files changed.

- **v6.2.1**: Skill alignment with conda-forge/staged-recipes upstream sync (May 7, 2026). Pure documentation patch; no code changes. Driven by an audit of ~22 staged files pulled from upstream that revealed two stale doc claims and three new ecosystem facts.

    **(1) Variant configs no longer auto-provide `python_min`.** `.ci_support/linux64.yaml` and `.ci_support/linux_aarch64.yaml` previously declared a global `python: 3.12.* *_cpython` and `python_min: '3.10'` for staged-recipes builds. Both keys were removed in the May 2026 upstream sync. **Why**: the previous skill text implied recipes could rely on a sensible global default; that's no longer true. **How to apply**: SKILL.md § Python Version Policy adds rule #6 — `noarch: python` recipes must now declare `python_min` explicitly in `context:`. SEL-002's existing warning is now load-bearing rather than advisory.

    **(2) CUDA 11.8 opt-back instruction is stale.** `reference/pinning-reference.md:500–502` previously instructed users to "opt back into 11.8 by copying `cuda118.yaml` into `.ci_support/migrations/`". That migrations entry was removed from staged-recipes upstream — the workaround no longer works. **How to apply**: stale text replaced with the current matrix (CUDA 12.9 + 13.0); legacy 11.8 opt-back path is documented as removed.

    **(3) New CUDA 12.9 + 13.0 explicit variants.** `.ci_support/linux64_cuda129.yaml` and `linux64_cuda130.yaml` are the new active variant configs. SKILL.md § Ecosystem Updates and `reference/pinning-reference.md` Active Variant Matrix table both updated to list them.

    **(4) `osx-arm64` is now a first-class variant.** `.ci_support/osx_arm64.yaml` ships alongside `osx_64.yaml`. Documented in SKILL.md and pinning-reference.md.

    **(5) New `## Active Variant Matrix (May 2026)` table** in `reference/pinning-reference.md` lists all 7 variant configs the staged-recipes repo currently ships, with a note about which platforms no longer set Python defaults.

    **Audit scope.** ~22 files modified/added across `.azure-pipelines/`, `.ci_support/`, `.scripts/`, `.github/workflows/`. Most are align-with-upstream cosmetic changes (Docker image cos7→alma9, swap script idempotence, issue-template Gitter→Zulip references, OSX_SDK_DIR validation in `run_osx_build.sh`). Two upstream changes affect skill assumptions and required this patch (#1 and #2). One additive — the new `.github/workflows/staged-recipes-linter.yml` workflow checks PR-meta hygiene (maintainer approval, feedstock collision, name lookup) and is **complementary** to the skill's `optimize_recipe` (which checks recipe content); no overlap or conflict.

    **Investigation note.** During audit, the audit agent reused the name "SEL-003" for a hypothetical "missing python_min" check. SEL-003 is taken (shipped in v6.2.0 for the `py < N` selector check). No new optimizer check was added in this release — SEL-002's existing `noarch:python` gate already covers the case the upstream sync makes load-bearing.

    **Docs.** SKILL.md frontmatter + `config/skill-config.yaml` bumped 6.2.0 → 6.2.1. No new files. No backward-incompatible changes.

- **v6.2.0**: Recipe-authoring bug fixes and gotchas documentation, driven by the cocoindex case study (May 7, 2026). All discoveries below traced back to a single PR — `conda-forge/staged-recipes#33231` — where a Rust + PyO3 + maturin recipe failed on all three platforms despite passing `validate_recipe`. Three independent latent issues land together as bug-fix + new optimizer checks + new doc material.

    **(1) ABT-002 — v0/meta.yaml about-field names in v1 recipe.yaml.** New optimizer check in `scripts/recipe_optimizer.py`. **Why**: rattler-build's recipe-format schema accepts unknown `about.*` keys silently, so `dev_url`, `doc_url`, `home`, `license_family` in a `schema_version: 1` recipe are dropped at build time without warning — users see incomplete project metadata on conda-forge.org. Verified against `prefix-dev/recipe-format` `$defs.About` schema (May 2026): only `homepage`, `repository`, `documentation`, `summary`, `description`, `license`, `license_file`, `license_family`, `prelink_message` are recognized. **How it works**: `analyze_about_section` now also scans for the v0 names and emits a per-field suggestion (`dev_url` → `repository`, `doc_url` → `documentation`, `home` → `homepage`, `license_family` → remove). Confidence 1.0 — false positive impossible since the field name is a hard mapping. Gated on `schema_version == 1` so v0 meta.yaml recipes (where these names are correct) aren't flagged.

    **(2) SEL-003 — bare `py < N` selector silently ignored in v1 build.skip.** New optimizer check. **Why**: cocoindex PR #33231 had `build.skip: - py < 311` per the previous skill guidance, but rattler-build does not auto-inject the integer `py` variable from the `python` variant string in staged-recipes-style builds — the condition evaluates against an undefined symbol and never fires. All three platforms (linux/osx/win) attempted the Python 3.10 matrix entry; pip rejected install per upstream's `requires-python>=3.11`. **How it works**: `analyze_selectors` regex-matches `^\s*py\s*[<>=!]+\s*\d+\s*$` entries in `build.skip:` of v1 recipes and suggests the rattler-build form `match(python, "<X.Y")`. The previous skill guidance to use `py < 311` (introduced in v5.9.0) was empirically wrong — the v6.2 docs are corrected and the optimizer guards against regressions.

    **(3) Recipe Authoring Gotchas — new SKILL.md section.** Four documented gotchas (G1–G4): script-entry shell isolation (env vars don't carry across `script:` list entries — needs single multi-line `then: |` or `script.env:` map; reference build.sh/build.bat); literal-only `script.env:` values (no shell expansion of `${VAR}`); v0 about-field silent acceptance (G2, paired with ABT-002); v0 `py < N` silent ignore (G3, paired with SEL-003); sdist-may-omit-LICENSE (G4, paired with new guides/ entry). Each gotcha cites the cocoindex case where applicable.

    **(4) `guides/sdist-missing-license.md` — secondary-source pattern.** New short guide. **Why**: cocoindex's PyPI sdist (built by maturin) shipped only `THIRD_PARTY_NOTICES.html`, no LICENSE — rattler-build's "Copying license files" step fails with `No license files were copied` after a successful wheel build. **How it works**: detection (rattler-build error or ABT-001), verification (`pip download` + `tar tzf`), fix (add a secondary `source:` block fetching LICENSE from the upstream GitHub tag with pinned sha256 and `file_name: LICENSE`), caveats (don't fetch from `main`/`master`; pin version; refresh sha on version bumps). Cocoindex 1.0.3 worked example.

    **(5) Doc fixes — `py < N` examples corrected across reference and templates.** `reference/recipe-yaml-reference.md:200`, `reference/selectors-reference.md` (lines 82, 87, 314, 320–321), `templates/python/maturin-recipe.yaml:26`, `templates/python/compiled-recipe.yaml:21,23`, `examples/python-compiled/recipe.yaml:21` — all updated to `match(python, "<3.11")` with explainer notes that v0 syntax is silently ignored. v0 meta.yaml examples elsewhere in `selectors-reference.md` are unchanged (correct for v0 context).

    **(6) `templates/r/cran-recipe.yaml` — `r_base` undefined fix.** The cross-r-base build requirement at line 28 referenced `${{ r_base }}` but the v0→v1 conversion didn't carry over the variant-config injection mechanism that conda-build uses. Added `r_base: "4.4"` to the `context:` block (matches conda-forge global pin verified May 2026; r_base matrix is `4.4, 4.5`). Documents how to override.

    **(7) `recipe_optimizer.py` accepts a directory path.** Previously `optimize_recipe(/path/to/recipe-dir)` (without trailing `/recipe.yaml`) silently returned 0 suggestions — the script's argparse handler tried to open the directory as a file, the inner `open()` failed, and `optimize_recipe()` returned an empty suggestion list. Caller couldn't distinguish "no issues" from "you passed a directory I couldn't parse." Fixed: `main()` now detects a directory and resolves to `recipe.yaml` (preferred) or `meta.yaml` inside. Discovered while validating ABT-002/SEL-003 against the real cocoindex recipe directory.

    **Investigation note.** During the cocoindex work, a spurious `python_min: "3.10"` injection was observed in the recipe between Read calls. Source confirmed: NOT the optimizer's SEL-002 check (which is correctly gated on `noarch == "python"` at line 248, never fires for compiled recipes). Most likely from the IDE's yaml-language-server schema-aware auto-completion. No skill-side fix needed.

    **Tests / validation.** Validated against (a) cocoindex (compiled, schema_v1) — should NOT trigger ABT-002, SEL-002, or SEL-003; (b) a noarch:python recipe with v0 `dev_url` field — SHOULD trigger ABT-002; (c) a v1 recipe with `py < 311` in `build.skip:` — SHOULD trigger SEL-003.

    **Docs.** SKILL.md + `config/skill-config.yaml` bumped 6.1.0 → 6.2.0. New "Recipe Authoring Gotchas" section in SKILL.md. New `guides/sdist-missing-license.md`. Memory entry `reference_v0_v1_about_fields.md` codifies the v0↔v1 about-field mapping for cross-session recall. No backward-incompatible changes.

- **v6.1.0**: `detail_cf_atlas.py` air-gap-friendly improvements (May 3, 2026). Two compatible additions in one minor bump.

    **(1) `--version VER` flag scopes `--vdb` to an arbitrary release.** The CVE check previously always evaluated against `record["latest_conda_version"]` from the atlas. **Why**: a feedstock's atlas-latest often diverges from the version deployed downstream (e.g., `django` atlas-latest = 6.0.4 but the `noarch` channel build is 5.2.12, and an internal app may be pinned to 5.2.x); the old behavior always answered "for the newest version conda-forge knows about," which is the wrong question for ops. **How it works**: `fetch_vdb_data(record, version_override)` substitutes the override into the version-pinned purls (`pkg:pypi/<name>@<ver>`, `pkg:conda/<name>@<ver>`, `pkg:npm/<name>@<ver>`); un-pinned purls and the historical-vuln baseline are unchanged. Render labels the risk line `queried_version <ver>` instead of `latest_conda_version <ver>` when the override is set. Atlas-derived sections (header, build matrix, channel storefronts) keep showing `latest_conda_version` — the override is scoped to the vuln check only. New pixi task `[feature.vuln-db.tasks.detail-cf-atlas-vdb]` presets `--vdb --vdb-all`.

    **(2) Build-matrix fallback for air-gapped networks (`fetch_repodata_build_matrix`).** When `api.anaconda.org` is unreachable (commonly blocked at corporate egress), the script now falls back to per-subdir `current_repodata.json` from a conda channel mirror. **Why**: the original v5.11 design only honored `ANACONDA_API_BASE`, which is useful when IT proxies anaconda.org through Artifactory but useless when only conda channels are mirrored. Air-gapped users were left with an atlas-only card and no build matrix. **How it works**: when `fetch_anaconda_files` returns an error, `main()` calls `fetch_repodata_build_matrix(name, subdir_filter, atlas_subdirs)` which iterates `_http.resolve_conda_forge_urls()` (CONDA_FORGE_BASE_URL → pixi `mirrors` → pixi `default-channels` → repo.prefix.dev/conda-forge → conda.anaconda.org/conda-forge). For each subdir, fetches `<base>/<sd>/current_repodata.json`, picks the latest matching package by timestamp, and reshapes to the same dict the files API would have returned (so `render()` is source-agnostic). JFrog auth (`X-JFrog-Art-Api` / Basic) is injected by `_http_make_request` automatically. The build-matrix header label is dynamic: "from anaconda.org" on the happy path, "from `https://repo.prefix.dev/conda-forge`" (or whatever resolved) on the fallback. The fallback drops `upload_time` (repodata's `timestamp` is build time, not upload time, and is in millis) — the renderer prints that field as empty cleanly. Verified end-to-end with `ANACONDA_API_BASE=https://nope.invalid pixi run -e local-recipes detail-cf-atlas django`: prefix.dev fallback returned 6 subdirs (current builds; the legacy 2018 win-32 build is gone from `current_repodata.json`).

    **Cleanup landed alongside.** Dead `CONDA_FORGE_BASE = os.environ.get("CONDA_FORGE_BASE_URL", ...)` constant deleted (it was defined but never used; the docstring advertised it as a redirect, which was misleading). Pyright `possibly-unbound` warning on `_http_make_request` resolved by switching the runtime guards from `if _HTTP_AVAILABLE:` to `if _http_make_request is not None:` — same semantics, narrower for static analysis.

    **Tests.** New `tests/unit/test_detail_cf_atlas.py` adds 8 offline tests: 6 cover the repodata fallback (shape parity with files API, subdir filter, candidate-chain walk on 502, no-match error, missing `_http` helper, standard-subdir constant), 2 cover the `--version` purl substitution (override path + default path). Mocks `urllib.request.urlopen` and `_http.resolve_conda_forge_urls` so no network calls happen. Full offline suite: 213 pass / 2 skipped / 1 xfail (was 205 before this change).

    **Docs.** Top-level `README.md` quick-reference table, `quickref/commands-cheatsheet.md`, and `docs/enterprise-deployment.md` updated. SKILL.md and `config/skill-config.yaml` bumped 6.0.0 → 6.1.0. No backward-incompatible changes.
- **v6.0.0**: Major skill restructure — three-tier BMAD-aligned architecture and dual-mode (external + JFrog) HTTP layer (May 3, 2026). This is a structural release: no behavioral changes to recipe authoring, but the skill is now installable, mirror-friendly, and enterprise-deployable without forking. Three independent changes land together as a single major bump:

    **(1) Three-tier directory layout.** The skill is split into three locations with distinct lifecycles, mirroring how BMAD organizes its installable skills:

      - `.claude/skills/conda-forge-expert/` — canonical source of truth (code, templates, reference docs, tests). BMAD-installable.
      - `.claude/scripts/conda-forge-expert/` — **new** stable public entrypoint layer (22 thin subprocess wrappers, one per public CLI). What `pixi run` calls. README.md at this path documents the wrapper pattern + rules for adding new scripts.
      - `.claude/data/conda-forge-expert/` — **moved** from `.claude/skills/data/`. All mutable runtime state (cf_atlas.db, vdb/, cve/, pypi_conda_map.json, inventory_cache/, cf-graph cache). Gitignored.

      All 22 entrypoint wrappers use the same 13-line subprocess pattern (`subprocess.run([sys.executable, skill_script] + sys.argv[1:])`) — sys.argv pass-through, dataclass resolution, exit code propagation all preserved. Three internal helpers stay private (no wrapper): `_sbom.py`, `_http.py`, `recipe_editor.py` (JSON-arg API), `test-skill.py` (internal smoke test).

      All 8 data-touching scripts gained a `_get_data_dir()` helper resolving to the new path: `mapping_manager.py`, `conda_forge_atlas.py`, `cve_manager.py`, `detail_cf_atlas.py`, `inventory_channel.py`, `name_resolver.py`, `scan_project.py`, `vulnerability_scanner.py`. `pixi.toml` `[feature.vuln-db.activation.env]` exports `VDB_HOME` / `VDB_CACHE` under the new path. `pixi.toml` retargets all 22 task `cmd` lines from `.claude/skills/conda-forge-expert/scripts/` to `.claude/scripts/conda-forge-expert/` (pytest paths intentionally still point inside the skill — test infra is not public surface).

    **(2) Enterprise HTTP layer that works externally and internally.** New `.claude/skills/conda-forge-expert/scripts/_http.py` (185 lines) is a shared helper consumed by `conda_forge_atlas.py`, `detail_cf_atlas.py`, `github_version_checker.py`, and `inventory_channel.py`. **Design constraint**: routing must be runtime-driven; no enterprise URLs may live in committed `pixi.toml`. The helper detects environment and routes accordingly:

      - **SSL trust:** `inject_ssl_truststore()` pulls system CA roots via the `truststore` package (idempotent, safe to call repeatedly). Honors `REQUESTS_CA_BUNDLE` / `SSL_CERT_FILE` env vars when set. Falls back to certifi if `truststore` is missing.
      - **Auth chain (first match wins):** `JFROG_API_KEY` → `X-JFrog-Art-Api`; `JFROG_USERNAME+PASSWORD` → Basic auth; `GITHUB_TOKEN` / `GH_TOKEN` for `*.github.com` → Bearer; `~/.netrc` (or `$NETRC`) for any host → Basic. Unauthenticated otherwise.
      - **Each consumer guards the import** so the helper is optional — scripts work without it but lose the auth chain.

      `mapping_manager.py` gains a curl-based SSL fallback: when `conda-forge-metadata.autotick_bot.pypi_to_conda` raises an SSL trust failure (matched against `_looks_like_ssl_trust_failure()`), the manager re-fetches via system `curl` from `regro/cf-graph-countyfair`'s `name_mapping.yaml` / `name_mapping.json`. Fixes networks where Python's TLS trust is broken but OS trust isn't.

      **`pixi.toml` deliberately stays clean.** No `[feature.vuln-db.pypi-options]` block, no hardcoded `index-url`, no Linux-specific `SSL_CERT_*` activation env, no inline `export REQUESTS_CA_BUNDLE` prefix on `vdb-refresh`. Enterprise routing happens via env vars + `_http.py` at runtime, not via committed config that would break external clones.

    **(3) Test + meta-test refresh.** `tests/meta/test_skill_md_consistency.py` regex (`pixi.toml` script-reference scanner) now matches both layouts: `.claude/skills/conda-forge-expert/scripts/<name>.py` (canonical) and `.claude/scripts/conda-forge-expert/<name>.py` (entrypoint). Both meta-tests skip underscore-prefixed scripts (`_http.py`, `_sbom.py`) as internal helpers. `tests/meta/test_all_scripts_runnable.py::SCRIPTS` adds the four scripts that v5.11/v5.12 introduced but never registered: `conda_forge_atlas.py`, `detail_cf_atlas.py`, `scan_project.py`, `inventory_channel.py`.

    **End-to-end smoke verification.** All 22 wrappers `--help` clean through the pixi env. Offline pytest: 172 pass / 2 skipped / 1 xfail (pre-existing). All data-fetch tasks run end-to-end through the new wrapper paths: `update-mapping-cache --force` (12,272 mappings), `update-cve-db --force` (12,611 packages, 19,213 CVEs), `build-cf-atlas` full 8-phase rebuild (165MB DB, 32,628 active conda packages, 7 subdirs), `vdb-refresh` (879,488 CVEs, 2.5GB). `scan-project .` exercises the full pipeline (1,975 deps across 9 manifests, 4 Critical / 12 High flagged). `inventory-channel https://conda.anaconda.org/conda-forge/noarch/repodata.json` fetches 170MB and matches 22,594 / 22,594 against the atlas.

    **Bug fixes that landed during this release.** (a) `conda_forge_atlas.py` `CONDA_FORGE_SUBDIRS` / `CONDA_FORGE_CHANNEL` constants were inadvertently deleted during an LLM-edit and replaced with a literal `# ...existing code...` placeholder; restored before any user impact. (b) `pixi.toml` had a hardcoded JFrog `index-url` and Debian-specific SSL cert paths that broke external `pixi install`; reverted in favor of runtime detection via `_http.py`. (c) Two staged files (`README.md`, `_http.py`) were committed empty and re-staged with content. (d) `.gitignore` now covers `.claude/data/` and `.claude/scheduled_tasks.lock` (Claude Code session-lock artifact).
- **v5.12.0**: Project + channel-level intelligence on top of the Atlas — three new tools at `scripts/scan_project.py`, `scripts/inventory_channel.py`, `scripts/_sbom.py`, all running in the lean `vuln-db` pixi env (May 2, 2026). **`scan_project.py`**: scans a directory, GitHub URL (`--github`), or specific manifest for CVEs across `pixi.lock` (preferred over `pixi.toml` when both exist), `pixi.toml`, `Cargo.lock` (full dep-tree extracted), `Cargo.toml`, `requirements.txt`, `pyproject.toml`, `environment.yml`, and `Containerfile`/`Dockerfile`. Cross-references each dep against `cf_atlas.db` so the scan report shows how many of the project's conda/pypi deps are tracked on conda-forge. `--os` flag enables OS-level CVE lookups via `vdb` for apt/dnf packages parsed out of containerfiles; optional trivy integration (`--no-trivy` to skip) covers the base image's full filesystem. Honors `--ref` for non-default git branches and `--keep-clone` for inspection. Aggregate-risk classifier (CRITICAL/HIGH/MEDIUM/LOW/CLEAN) plus top-N risk-prioritized package list (default 10, 5 with `--brief`) including the highest-severity CVE id, CVSS score, severity tier, CWE, and a 55-char description excerpt. Per-manifest breakdown shows where the risk concentrates. `_SKIP_PATH_PARTS` walks ignore conda/pixi/cargo build dirs (`target`, `vendor`, `.cargo`, `output`, `src_cache`, `bld`, `work`, `_bmad-output`, `gopath`) so scans don't pick up build artifacts or vendored test fixtures. **`inventory_channel.py`**: auto-detects channel format from URL pattern + content sniff — conda `repodata.json` (local file or `https://conda.anaconda.org/...`), PyPI Simple v1 JSON index, npm registry CouchDB `_all_docs`, crates.io sparse index. JFrog Artifactory authentication via `JFROG_API_KEY` or `JFROG_USERNAME+PASSWORD` env vars routes through `_make_request()` for all URL fetches. Cross-references every package against `cf_atlas.db` and reports the match rate (typically 100% for upstream conda-forge). Default `--with-vulns` ON for conda channels (~60s for 22k packages), OFF for PyPI/npm/cargo (too large to scan in default flow); `--no-vulns` overrides per-channel default. `--diff <upstream-url>` compares a local mirror against upstream conda-forge; `--health` derives mirror signals from atlas (archived feedstocks, stale versions, inactive packages, no-atlas-match). 24h cache at `.claude/skills/data/inventory_cache/`. Output formats: rendered terminal report (default + `--brief`), JSON (`--json`), CSV (`--csv`), or SBOM (`--sbom {cyclonedx,spdx}` + `--sbom-out PATH`). **`_sbom.py`**: shared SBOM emitter consumed by both scripts. CycloneDX 1.6 JSON: `bomFormat`/`specVersion`/`serialNumber`/`metadata.tools`/components[] (with PURLs and atlas-derived licenses)/dependencies[] (Cargo dep-tree preserved as `ref → dependsOn[]` graph)/vulnerabilities[] (always populated per Option A — complete-but-larger over portable-but-incomplete; CVSS rating with method mapping `v4→CVSSv4`, `v3.1→CVSSv31`, `v3→CVSSv3`, `v2→CVSSv2`; CWE numeric extraction; KEV → `analysis.state: exploitable`). SPDX 2.3 JSON: SPDXRef-DOCUMENT/packages[] (with externalRefs.purl)/relationships[] (DESCRIBES + DEPENDS_ON); vulnerabilities attached as `annotationType: REVIEW` annotations on affected packages since SPDX 2.3 has no native vulns section. **Pixi tasks added**: `scan-project` and `inventory-channel`, both in the `vuln-db` feature. **Bug fixed in flight**: `inventory_channel.fetch_source()` was falling through to URL-fetch path when a local file argument didn't exist, then `_make_request()` would URL-parse the filesystem path and raise `ValueError`. Restructured to URL-detect first via `startswith(("http://", "https://"))`, return clear "local file not found" error otherwise. **Bug fixed during smoke test — conda→pypi vuln probe**: vdb keys advisories by `pkg:pypi/...`, not `pkg:conda/...`, so `scan_project.lookup_vulns` and `inventory_channel.scan_vulns` returned zero matches for conda deps even when their pypi-equivalent had real CVEs (e.g., `requests@2.30.0` from a `pixi.toml` was reported CLEAN despite 4 known CVEs in the same version on PyPI). Fix: both functions now also probe `pkg:pypi/<pypi_name>@<version>`, with the pypi name resolved from the atlas record (`atlas_records["conda:<name>"].pypi_name` for scan-project, `atlas_xref[<name>].pypi_name` for inventory-channel) and falling back to the conda name when the atlas has no mapping. Results de-duped by CVE ID across both purls. Validated end-to-end: a 5,911-package conda channel scan that previously returned 0 vulns now flags 28 packages (1 Critical, 117 High, 235 Medium, 22 Low). **Data layout consolidation**: all package-intelligence data now lives under `.claude/skills/data/` (gitignored) instead of XDG defaults — added `[feature.vuln-db.activation.env]` to `pixi.toml` exporting `VDB_HOME=$PIXI_PROJECT_ROOT/.claude/skills/data/vdb` and `VDB_CACHE=$PIXI_PROJECT_ROOT/.claude/skills/data/vdb-cache`; existing `~/.local/share/vdb/` (~2.5 GB) migrated in place. Tradeoff documented: per-checkout DB instead of one global copy, accepted because all data-pull happens in dev (not air-gapped runtime). Inventory-channel cache stays at `.claude/skills/data/inventory_cache/`. Atlas DB and cf-graph cache continue at `.claude/skills/data/`. Temporary git clones from `scan-project --github` continue to use `tempfile.mkdtemp` under `/tmp/` (tmpfs, auto-cleared) — they're throwaway, not state worth keeping.
- **v5.11.0**: Conda-Forge Atlas suite — three new scripts under `scripts/` providing comprehensive cross-channel package intelligence (May 2, 2026). **`conda_forge_atlas.py`**: 8-phase pipeline building `cf_atlas.db` (~7 MB SQLite, 812k packages) — aggregates conda-forge (33k packages) with PyPI (800k names) plus npm/CRAN/CPAN/LuaRocks linkage parsed from conda recipe `source.url`; deliberately uses urllib + `current_repodata.json` per subdir instead of py-rattler's sharded msgpack protocol (which hit transient 502s in testing — the simpler approach also works for air-gapped/JFrog mirrors via env-var redirection); 24-column packages table + maintainers junction table + `v_packages_enriched` view computing URL templates on the fly; pixi tasks `build-cf-atlas` / `query-cf-atlas` / `stats-cf-atlas`. **`detail_cf_atlas.py`**: per-package detail card renderer with sectioned terminal output (header, cross-channel relationship, feedstock, build matrix from anaconda.org files API, project links, channel storefronts including auto-built conda-metadata-app deep-inspect URL); graceful per-source degradation with `✓/✗/—` status summary at bottom; honors `CONDA_FORGE_BASE_URL` and `ANACONDA_API_BASE` env vars for air-gapped/JFrog redirection; flags `--deep` (per-build artifact metadata via `conda_forge_metadata.types.ArtifactData`), `--files` (paths.json sample), `--subdir` (filter to one platform), `--json` (machine-readable). **New `vuln-db` pixi feature**: lean separate env (~30 MB Python deps over base) with `appthreat-vulnerability-db[all]` PyPI dep + `conda-forge-metadata`; new `vdb-refresh` task builds the multi-source DB at `~/.local/share/vdb/` (~707 MB; sources: NVD + GHSA + OSV + Snyk + npm + Aqua + custom); detail-cf-atlas gains `--vdb` / `--vdb-deep` / `--vdb-all` flags that derive 1-5 purls per package (pypi-pinned + un-pinned, conda-pinned + un-pinned, npm-pinned + un-pinned, github), aggregate vulns across sources, and render risk header + severity counts (with version-affected breakdown) + top-N actionable CVEs with CVSS scores + CWE codes + KEV markers; recursive `_walk_for_cvss/_descriptions/_cwe/_kev` model walkers handle MITRE 5.0 schema's variable nesting (cna vs adp containers). **Migration path**: `cf_atlas.db` is a strict superset of the legacy `pypi_conda_map.json` produced by `mapping_manager.py` — same 12k parselmouth matches plus 779k pypi-only rows, 8k name-coincidence matches, and 5.5k recipe-source.url-verified matches; supersedes the flat dict with a queryable single-source-of-truth. **CLAUDE.md sync tag** for `pypi_conda_map.json` will need updating in a follow-up; `mapping_manager.py` deprecation deferred to v6.x.
- **v5.10.0**: Multi-skill restructure of the project's `CLAUDE.md` (May 2, 2026). The repo is moving from conda-forge-only toward a multi-skill BMAD-driven monorepo, so `CLAUDE.md` (loaded every turn) was reduced from 480 to 89 lines (~81% reduction) by colocating conda-forge specifics with this skill rather than having them in always-loaded context. **Three new files added under `reference/`**: `python-min-policy.md` (47 lines — procedural rules for setting `python_min`; the bare 3.10 floor stays sourced from `recipe-yaml-reference.md` § Python Build Matrix); `mcp-tools.md` (48 lines — all 18 MCP tools grouped by purpose with special notes for `dry_run` defaults, JFrog Artifactory support, and the migrate-then-validate flow that aren't in tool docstrings); `conda-forge-ecosystem.md` (114 lines — verbatim move of the full ecosystem glossary including Local Tooling, Submission Pipeline, Automation/Bots/Backend, Post-Submission, Documentation & Knowledge Bases, Community Roles & Personas, Channels, Storefronts). **Existing files updated**: `reference/recipe-yaml-reference.md` § Requirements gains a `>` callout requiring `stdlib` for compiler-using recipes (with the `go-nocgo` / legacy `compiler("go")` exception); `quickref/commands-cheatsheet.md` gains a new § "Project Pixi Tasks" with the 7 pixi tasks defined in this repo's `pixi.toml` that aren't generic conda-forge tooling (`update-cve-db`, `update-mapping-cache`, `sync-upstream`, `submit-pr`, `health-check`, `autotick`, `lint`); `scripts/recipe_optimizer.py` STDLIB-001 docstring now references `SKILL.md` Critical Constraints + `recipe-yaml-reference.md` § Requirements (was: "CLAUDE.md Critical Constraints" — the named section no longer exists in `CLAUDE.md`). **`CLAUDE.md` content moved/deleted**: Recipe Formats deleted (fully subsumed by `recipe-yaml-reference.md` 866 lines + `meta-yaml-reference.md` 658 lines); Manual CLI Commands deleted (3 generic commands already in cheatsheet, 7 unique pixi tasks merged into cheatsheet); AI-Assisted Workflow + 3 tool tables deleted (lifecycle loop already in `SKILL.md` § Primary Workflow with more detail; tool tables consolidated into `mcp-tools.md`); Python Version Policy deleted (procedural rules moved to `python-min-policy.md`); Critical Build Requirement: `stdlib` deleted (rule absorbed into `recipe-yaml-reference.md` callout, canonical version remains in `SKILL.md` § Critical Constraints); Conda-Forge Ecosystem Reference deleted (verbatim move). **Karpathy section in `CLAUDE.md` trimmed** from 50 to 8 lines: heading names preserved verbatim (`Think Before Coding` / `Simplicity First` / `Surgical Changes` / `Goal-Driven Execution`) so `.claude/settings.json` `customInstructions` reference still resolves; bodies replaced with one-sentence summaries. Added a **Skill Reference table** to `CLAUDE.md` mapping skills to purpose & invocation triggers (conda-forge-expert, bmad-quick-dev, BMAD planning chain, bmad-document-project, bmad-agent-* personas), plus a **memory pointer** to the auto-memory directory. **Cross-references updated**: 5 `docs/specs/conda-forge-tracker.md` references rerouted from "CLAUDE.md `## Conda-Forge Ecosystem Reference`" to `reference/conda-forge-ecosystem.md` (lines 22–23, 51, 68, 178, 341, 691); 8 `(Sync: …)` tags + frontmatter in `_bmad-output/projects/local-recipes/project-context.md` rerouted to skill files (Recipe Formats → recipe-yaml-reference.md + meta-yaml-reference.md; stdlib → SKILL.md Critical Constraints + recipe-yaml-reference.md § Requirements; Python Version Policy → python-min-policy.md; AI-Assisted Workflow → mcp-tools.md; Autonomous Recipe Lifecycle Loop → SKILL.md § Primary Workflow; Manual CLI Commands → quickref/commands-cheatsheet.md § Project Pixi Tasks; submit_pr → mcp-tools.md); frontmatter `sync_source` (string) replaced with `sync_sources` (array of 4 paths). **Risks documented** (in plan): token-savings claim is unmeasured (CLAUDE.md is loaded every turn vs. skill files load on-demand — net win depends on conda-forge-vs-other ratio of session work); `meta-yaml-reference.md` quality verified before claiming Recipe Formats subsumed; skill-ownership coupling for the ecosystem glossary is acceptable for now (revisit if a sibling rattler-build skill emerges).
- **v5.9.0**: Second live documentation pass against conda-forge.org and github.com/conda-forge (Apr 25, 2026). Also added `automation/` directory committing the prompt + local runner for the new quarterly remote routine `trig_015z9XF8ExDJuN9qsZYGYKcu` (cron `0 14 1 */3 *` → Jan/Apr/Jul/Oct 1, 14:00 UTC). `automation/quarterly-audit.prompt.md` is the canonical prompt run by both the cloud routine and the local CLI; `automation/run-audit-local.sh` strips the YAML frontmatter and invokes `claude -p` from the repo root. `automation/README.md` documents cloud vs local invocation tradeoffs, cron/systemd schedule examples, and a recreation procedure if the cloud routine is deleted. New `## Skill Automation` section in SKILL.md links the directory. **rattler-build version-specific changes** added to `reference/recipe-yaml-reference.md`: v0.61.0 — `--debug` flag removed, use `rattler-build debug` subcommand instead; v0.62.0 — three-mode `--env-isolation` (`strict` default, `conda-build`, `none`), with `build.script.env` declaration pattern; v0.63.0 — **breaking change** for multi-output recipes: per-output `build.sh`/`build.bat` is no longer auto-discovered, each output must declare `script: <name>` explicitly. **CI Infrastructure** updated in `SKILL.md`: GitHub Actions for `linux_64` is now an opt-in build provider via conda-smithy 3.57.1+ (Mar 8, 2026 announcement) — no longer "rerendering only"; added `provider:` configuration example; Cirun for native ARM/Power; clarified Windows ARM64 status. **Community Channels** table added: Zulip is primary (`conda-forge.zulipchat.com`); Discourse is read-only since Oct 15, 2025; Gitter is decommissioned. **Ecosystem Updates section** in `SKILL.md` consolidating: macOS minimum 11.0 (Feb 2026), `/opt/conda-sdks` SDK directory (conda-smithy 3.54.0, Dec 2025), Accelerate BLAS shim (Jul 2025), CUDA 12.9 default + Tegra SOC support (Jan 2026), MPI external label `conda-forge/label/mpi-external` (Jan 29, 2026), CFEP-26 naming guidelines accepted, SPDX case-sensitivity, bundled-language licensing. **Pinning reference** updates: NVIDIA Tegra notes for CUDA 12.9, MPI external label section, simplified CUDA matrix example (removed retired 11.8). **`py < 39` cleanup**: replaced obsolete skip across `templates/python/compiled-recipe.yaml`, `templates/python/maturin-recipe.yaml`, `templates/python/maturin-meta.yaml`, `examples/python-compiled/recipe.yaml`, and `templates/README.md` (the conda-forge build matrix already starts at 3.10, so `py < 310` is a no-op). `reference/selectors-reference.md` and `reference/recipe-yaml-reference.md` updated examples to `py < 311` with explanation. **Multi-output template** `templates/multi-output/lib-python-recipe.yaml` annotated with v0.63 explicit-script discovery note. `config/skill-config.yaml` and `SKILL.md` bumped to 5.9.0. **Project CLAUDE.md** updated: replaced the four-link `## References` block with a structured `## Conda-Forge Ecosystem Reference` section organizing 25+ repos and docs into Local Tooling (pixi, rattler-build, rattler, rattler-build-conda-compat, miniforge, grayskull), Submission Pipeline (staged-recipes, conda-smithy, conda-forge-pinning-feedstock, conda-forge.github.io), Automation/Bots/Backend (admin-requests, regro/cf-scripts, regro/cf-graph-countyfair, conda-forge-metadata, webservices, feedstock-tokens), Post-Submission, Documentation & Knowledge Bases (maintainer docs, news, status, knowledge base, v1 announcement, CFEPs, recipe-format schema, rattler-build publishing, pixi-build-rattler-build), and Community Channels — gives a one-stop map of the conda-forge + prefix-dev ecosystems used by this project.
- **v5.8.0**: Live documentation pass against conda-forge.org and github.com/conda-forge (Apr 2026). **Go template fix**: `compiler("go")` corrected to `compiler("go-nocgo")` in both pure-Go templates (recipe.yaml and meta.yaml) — `compiler("go")` is the legacy name; the correct current names are `go-nocgo` (pure Go) and `go-cgo` (CGO). **STD-001 check refined**: no longer flags `go-nocgo` or legacy `go`; correctly flags `go-cgo` (which does link against C stdlib). **New global pins table** in `reference/pinning-reference.md`: GCC 14 (Linux), Clang 19 (macOS), MSVC 2022 (Windows), NumPy 2, CUDA 12.9, OpenSSL 3.5, Boost 1.88, PyTorch 2.9, Arrow 20–23; GCC version in ci_support example corrected 12 → 14. **New `## CI Infrastructure Reference` section** in SKILL.md: Azure Pipelines is the build platform (GitHub Actions is rerendering/automerge only); 6-hour build limit; OS version options (cos7/alma8/alma9/alma10); bot version_updates.exclude configuration; package immutability policy. **Critical Constraints** updated: Go compiler usage (`go-nocgo` vs `go-cgo`), `compiler_stack` deprecated warning. **`optimize_recipe` tool description** updated with all 13 check codes. `skill-config.yaml` bumped to 5.8.0.
- **v5.7.0**: Major skill enhancement pass using CLAUDE.md behavioral guidelines and all 21 addyosmani/agent-skills. SKILL.md completely rewritten: added Operating Principles (Karpathy think/simplicity/surgical/goal-driven + using-agent-skills non-negotiables), Critical Constraints (stdlib requirement, format mixing prohibition, python_min floor), Recipe Security Boundaries (three-tier Always/Ask First/Never Do), Build Failure Protocol (six-step triage, max-5-iteration rule, category table), Pre-PR Quality Gate Checklist, Migration Protocol (Strangler pattern, Churn Rule), Python Version Policy (full rules + code examples for both formats), Recipe Formats Quick Reference, and enhanced all 9 workflow steps with explicit success criteria. `recipe_optimizer.py` gains five new checks: STD-001 (compiler without stdlib, confidence=1.0), STD-002 (format mixing, confidence=1.0), SEC-001 (source URL without sha256, confidence=0.95), TEST-001 (no tests section, confidence=0.85), MAINT-001 (missing maintainers, confidence=0.9). Check ordering now prioritizes critical/CI-blocking issues first. `failure_analyzer.py` adds three new patterns: MESON_NOT_FOUND, AUTOTOOLS_NOT_FOUND (BUILD_TOOLS category), NETWORK_ACCESS_BLOCKED (ENV_ISOLATION category); pattern count updated to 42 across 13 categories. `skill-config.yaml` adds `behavioral_principles` block, `agent_skills.lifecycle_mapping` (all 21 skills mapped to 11 workflow phases), and updated linting check codes with category comments.
- **v5.6.0**: Installed all 21 addyosmani/agent-skills at `.claude/skills/`. Each skill file includes a `## Conda-Forge Application` section mapping generic engineering patterns to specific conda-forge workflows: `debugging-and-error-recovery` → analyze_build_failure loop, `security-and-hardening` → scan_for_vulnerabilities, `deprecation-and-migration` → migrate_to_v1, `test-driven-development` → recipe test design, `shipping-and-launch` → submit_pr workflow, `git-workflow-and-versioning` → staged-recipes PR discipline, `ci-cd-and-automation` → conda-forge CI patterns. `using-agent-skills` SKILL.md updated with `## Conda-Forge Skill Stack` section. conda-forge-expert SKILL.md updated with `## Agent Skills Cross-Reference` table linking all 9 lifecycle steps to their skill counterparts.
- **v5.5.0**: Standards alignment audit (conda-forge 2025/2026 changes). Fixed `generate_recipe_from_pypi` broken version argument (now passes `pkg==ver` instead of 3 tokens). Replaced fragile `CONDA_EXE`-based Python detection in MCP server with `sys.executable`. Fixed SEL-002 optimizer suggestion hardcoded `python_min: "3.9"` → `"3.10"` (Python 3.9 dropped Aug 2025). Fixed `recipe-yaml-reference.md` complete example DEP-002 anti-pattern (Python upper bound moved from `run` to `run_constrained`). Enhanced SEL-002 check to verify full CFEP-25 triad (context + host + run + tests). Added `migrate_to_v1` MCP tool via `feedrattler`. Updated `noarch-recipe.yaml` template with `python_version: ${{ python_min }}.*` in tests. Updated pinning reference (NumPy 2.x default, Python 3.10–3.14 matrix). Updated `skill-config.yaml` to v5.5.0, `default_maintainer: rxm7706`. Added comprehensive `python_min` policy section to CLAUDE.md.
- **v5.4.0**: Documentation audit pass. Corrected `failure_analyzer.py` pattern count (30→33 patterns, 9→10 categories). Updated `check_dependencies` MCP tool to expose `--channel` and `--subdirs` parameters; added batch repodata.json / JFrog Artifactory / air-gapped environment docs. Updated `scan_for_vulnerabilities` description (OSV.dev API primary, local DB fallback). Updated `generate_recipe_from_pypi` docstring (grayskull only). Updated `optimize_recipe` docstring with full check-code table (DEP-001→SEL-002).
- **v5.3.0**: Added `github_updater.py` + `update_recipe_from_github` MCP tool — GitHub Releases autotick write path (mirrors `recipe_updater.py`). Auto-detects GitHub repo from recipe; updates `context.version`, resets `build.number`, recalculates SHA256. Pre-releases skipped by default. `check_github_version` clarified as read-only.
- **v5.2.0**: Added `check_github_version` MCP tool for GitHub-only packages (complements `update_recipe`). FastMCP 3.x Context injection on `trigger_build` and `update_cve_database` for progress logging. Fixed `recipe_optimizer.py` selector analysis to handle recipe.yaml v1 list-based `skip` conditions; added CFEP-25 `python_min` check (SEL-002). Fixed Pyright `reportPossiblyUnboundVariable` diagnostics.
- **v5.1.0**: Added `submit_pr` MCP tool, completing the full autonomous loop from generation to PR submission. Includes `dry_run` mode for safe prerequisite checks before writing to GitHub.
- **v5.0.0**: Major architectural overhaul. Implemented a full suite of autonomous tools, including a closed-loop build/debug system, a local "autotick" bot, vulnerability scanning, a programmatic recipe editor, and an intelligent failure analyzer. The skill is now a true autonomous agent.
- **v4.2.1**: Removed the `stdlib` local testing hack by implementing an automatic variant override.
- **v4.0.0**: Initial modular architecture.
