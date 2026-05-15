# cf_atlas Phases — Overview by Actionable Intelligence

Companion to
[`atlas-actionable-intelligence.md`](atlas-actionable-intelligence.md)
(persona × goal index). This file is the **phase-indexed** view: one
section per pipeline stage, capturing the four things every consumer of
the atlas needs to know about a phase before relying on it.

For each phase:

- **Data source** — exact URL(s), dataset, or upstream table fetched.
- **Purpose** — why the phase exists; what new fact lands in `cf_atlas.db`.
- **What gets written** — tables + columns, so downstream queries are
  grounded in real schema rather than recall.
- **Actionable intelligence** — the CLIs, MCP tools, and SQL queries that
  this phase makes possible. Anything `📋 open` in the persona catalog is
  noted here against the phase that would deliver it.

Cadence + TTL + recovery details live in
[`../guides/atlas-operations.md`](../guides/atlas-operations.md);
engineering patterns (rate limits, GraphQL batching, atomic writes,
checkpoint recovery, enterprise routing) live in
[`atlas-phase-engineering.md`](atlas-phase-engineering.md). Don't
duplicate those here — link out.

Source of truth for each phase's behavior remains the docstring in
`.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py`. This
document distills those docstrings into the intelligence outcomes they
unlock. Update on every release that adds, removes, or materially
changes a phase.

---

## At-a-glance index

| Phase | Name | Primary source | TTL | Default | Feeds |
|---|---|---|---|---|---|
| **B** | Conda enumeration | `conda.anaconda.org/conda-forge/<subdir>/current_repodata.json` | rebuild | always | License audit, baseline for all later phases |
| **B.5** | Feedstock-outputs | `github.com/conda-forge/feedstock-outputs` (master tarball) | rebuild | always | `feedstock_name` mapping + inactive placeholders |
| **B.6** | Status (lite yanked) | Phase B temp table (no network) | rebuild | always | `latest_status` = active/inactive |
| **C** | Parselmouth join | `conda_forge_metadata.autotick_bot.pypi_to_conda` (parselmouth bot, ~12k entries) | rebuild | always | Verified PyPI↔conda name mapping |
| **C.5** | source.url match | folded into Phase E | — | — | URL → conda-package reverse lookup |
| **D** | PyPI universe | `pypi.org/simple/` (Simple v1 JSON, ~40 MB / ~800k projects) | rebuild | always (universe upsert skipped under `--profile consumer`) | "On PyPI but not on conda-forge" candidate list |
| **O** | PyPI activity snapshots | Phase D's `pypi_universe.last_serial` (no new HTTP; snapshot table is local) | retain `PHASE_O_SNAPSHOT_RETAIN_DAYS=90` | always (v8.1.0+) | `pypi_intelligence.activity_band` (hot/warm/cold/dormant) + `serial_delta_{7d,30d}` |
| **P** | PyPI downloads | BigQuery `bigquery-public-data.pypi.file_downloads` (project-level aggregate, last 90 d) | `PHASE_P_TTL_DAYS=30` | opt-in admin-tier (`PHASE_P_ENABLED=1`; needs `google-cloud-bigquery` + `GOOGLE_APPLICATION_CREDENTIALS`) | `pypi_intelligence.downloads_30d` + `downloads_90d` — the demand-side signal for `pypi-intelligence` ranking |
| **Q** | Cross-channel presence | `current_repodata.json` for bioconda / pytorch / nvidia / robostack-staging via `<CHANNEL>_BASE_URL` | `PHASE_Q_TTL_DAYS=7` | default-on under maintainer+admin profiles | `pypi_intelligence.in_<channel>` BOOLs — "this PyPI project is packaged on bioconda but not conda-forge" migration queries |
| **R** | Per-project enrichment | `pypi.org/pypi/<name>/json` for top-N (default 5000) candidate slice | `PHASE_R_TTL_DAYS=7` | opt-in admin-tier (`PHASE_R_ENABLED=1`) | `pypi_intelligence.{latest_version, license_spdx, requires_python, classifiers, repo_url, packaging_shape, has_wheel/sdist, wheel_platforms, python_tags}` |
| **S** | Computed scores | pure SQL over `pypi_intelligence` Tier 1-3 columns | per-run | always when Phase R has data | `pypi_intelligence.conda_forge_readiness` (0-100 composite) + `recommended_template` (full `templates/python/<x>.yaml` path) |
| **E** | cf-graph enrichment | `github.com/regro/cf-graph-countyfair` (master tarball, ~150 MB) | `ATLAS_CFGRAPH_TTL_DAYS` (default 1 d) | enabled by every v8.0.0 profile; otherwise opt-in (`PHASE_E_ENABLED=1`) | Recipe-format, maintainer junction, repo/dev/homepage URLs, extra-registry name columns |
| **E.5** | Archived feedstocks | `gh api graphql` (conda-forge org, `isArchived:true`) | per-run | always | Abandonment detection |
| **F** | Download counts | `api.anaconda.org/package/conda-forge/<name>` OR `anaconda-package-data.s3.amazonaws.com/conda/monthly/<YYYY>/<YYYY-MM>.parquet` | `PHASE_F_TTL_DAYS=7` | always (auto-source; pinned to `s3-parquet` under `--profile consumer`) | Usage signal — leaderboards, bus-factor, adoption-stage, "archived but used" |
| **G** | vdb risk summary | local AppThreat vdb (per-row purls) | `PHASE_G_TTL_DAYS=7` | always when vdb available (auto-skip in `local-recipes` env) | `cve-watcher`, KEV queue, staleness `--by-risk` |
| **G'** | per-version vulns | same vdb, all versions in `package_version_downloads` | `PHASE_GP_TTL_DAYS=30` | opt-in (`PHASE_GP_ENABLED=1`) | "Most recent build set with 0 critical CVEs" lockdown |
| **H** | PyPI current version | `pypi.org/pypi/<name>/json` (PEP 592 yanked) OR Phase E cf-graph cache | `PHASE_H_TTL_DAYS=7` | always (`PHASE_H_SOURCE=pypi-json` default; `cf-graph` on cold-start; pinned to `cf-graph` under `--profile consumer`) | `behind-upstream` (pypi); yanked-upstream alert |
| **I** | Per-version downloads | side-effect of Phase F anaconda-api path | tied to F | with F | `version-downloads`, `release-cadence`, feeds G' |
| **J** | Dependency graph | reuses Phase E cf-graph tarball | rebuild-each-run | always when cf-graph cached | `whodepends`, dependent counts, CVE cascade alerts |
| **K** | VCS upstream | `api.github.com/graphql` (batched) + `gitlab.com/api/v4` + `codeberg.org/api/v1` | `PHASE_K_TTL_DAYS=7` | requires GitHub auth; auto-skip without | `behind-upstream` (github/gitlab/codeberg) |
| **L** | Extra registries | `registry.npmjs.org`, `crandb.r-pkg.org`, `fastapi.metacpan.org`, `luarocks.org`, `crates.io`, `rubygems.org`, `api.nuget.org`, `search.maven.org` | `PHASE_L_TTL_DAYS=7` | always (auto-restricted to populated registries in scope under `--profile maintainer`) | `behind-upstream` (npm/cran/cpan/luarocks/crates/rubygems/nuget/maven) |
| **M** | Feedstock health | reuses Phase E cf-graph (`pr_info/*.json` + `version_pr_info/*.json`) | rebuild-each-run | always when cf-graph cached | `feedstock-health --filter stuck/open-pr/bad` |
| **N** | Live GitHub | `gh api graphql` per feedstock | `PHASE_N_TTL_DAYS=1` | enabled by `--profile maintainer` (auto-scoped to `gh api user`) and `--profile admin` (channel-wide); otherwise opt-in (`PHASE_N_ENABLED=1`, requires `gh auth login`) | Real-time CI / human PRs / issues / pushedAt |

For cron cadence, TTL reset, and recovery playbooks, see
[`../guides/atlas-operations.md`](../guides/atlas-operations.md).

---

## Phase B — Conda enumeration

- **Data source.** `conda.anaconda.org/conda-forge/<subdir>/current_repodata.json`
  for each of the 8 active subdirs (`noarch`, `linux-64`, `linux-aarch64`,
  `linux-ppc64le`, `osx-64`, `osx-arm64`, `win-64`, `win-arm64`). Uses
  plain `urllib` rather than py-rattler's sharded protocol — the sharded
  msgpack endpoint hit transient 502s during testing; `current_repodata.json`
  is one fetch per subdir and far more reliable. Also air-gap / JFrog
  friendly via `CONDA_BASE_URL`.
- **Purpose.** Seed the `packages` table with conda-side facts. Every
  other phase joins to a Phase-B row.
- **What gets written.** `packages.{conda_name, conda_subdirs,
  conda_noarch, latest_conda_version, latest_conda_upload, conda_license,
  conda_license_family, relationship='conda_only', match_source='none'}`.
  Idempotent UPSERT on `conda_name`; later phases refine `relationship`
  and `match_*`.
- **Actionable intelligence.**
  - License audit by `conda_license` / `conda_license_family` (admin
    persona, ✅ shipped SQL).
  - Latest-release age via `latest_conda_upload` — feeds
    `staleness-report`, `release-cadence`, `adoption-stage`.
  - Universe enumeration — backs `detail-cf-atlas`, `lookup_feedstock`,
    `get_conda_name`, and every "is this real?" check.

## Phase B.5 — Feedstock-outputs archive

- **Data source.** `github.com/conda-forge/feedstock-outputs` (master
  tarball, JSON-per-output). Resolves the canonical feedstock for every
  output, including outputs no longer present in repodata (yanked,
  deprecated, or never built).
- **Purpose.** Populate `feedstock_name` for the maintainer/health joins
  and insert placeholder rows for outputs that exist in the registry but
  not in current repodata.
- **What gets written.** `packages.feedstock_name`; placeholder INSERTs
  with `relationship='conda_only'` for rows missing from Phase B.
  Incremental commits every 500 rows survive partial runs.
- **Actionable intelligence.**
  - Canonical feedstock per conda name — backs every maintainer-scoped
    CLI (`staleness-report --maintainer`, `feedstock-health`,
    `behind-upstream`, `cve-watcher`).
  - Yanked-output detection ("was once shipped, no longer present in
    repodata") — backs the "archived but used" composite (Phase E.5 + F + I).

## Phase B.6 — Yanked detection (lite)

- **Data source.** None (operates on the Phase B `current_repodata_names`
  temp table).
- **Purpose.** Classify every row's `latest_status` as `active` or
  `inactive`. Three transitions handled in one pass: first-time activation,
  re-activation, and demotion.
- **What gets written.** `packages.latest_status`. Monolithic transaction
  by design — 3 bulk UPDATEs run in <1 s.
- **Actionable intelligence.**
  - Every downstream CLI filters `latest_status='active'` to skip
    yanked / deprecated rows — feeds correctness, not new outputs.
  - Roll-up "% of channel active vs inactive" (admin persona, ✅ SQL).

## Phase C — Parselmouth PyPI ↔ conda join

- **Data source.** `conda_forge_metadata.autotick_bot.pypi_to_conda.get_pypi_name_mapping()`
  — wraps the prefix-dev/parselmouth bot's hourly output (~12k verified
  entries).
- **Purpose.** Authoritative cross-ecosystem name mapping. Every
  cross-ecosystem CLI (`behind-upstream`, `whodepends`, `scan-project`'s
  conda translation) leans on this mapping first; falls back to D's
  `name_coincidence` only when parselmouth has no entry.
- **What gets written.** `packages.{pypi_name, relationship IN
  ('both_same_name','both_renamed'), match_source='parselmouth',
  match_confidence='verified'}`. Incremental commits every 500 entries.
- **Actionable intelligence.**
  - `get_conda_name` MCP tool — pip → conda name translation.
  - `behind-upstream` joins via `pypi_name` to Phase H's
    `upstream_versions`.
  - `scan-project` resolves PyPI manifest names to conda packages for
    enrichment.

## Phase C.5 — source.url match (folded into Phase E)

- **Data source.** None standalone — uses cf-graph data fetched by Phase E.
- **Purpose.** Match recipe `source.url` patterns to known upstream
  hosts (github/gitlab/codeberg/pypi/npm/cran/...). Folded into E to
  avoid a double-fetch of cf-graph.
- **What gets written.** (via Phase E) `packages.match_source` /
  `match_confidence` refinements; URL→host detection feeds Phase K
  upstream classification.
- **Actionable intelligence.**
  - "Find conda package by upstream URL" — supports `find-alternative`
    + `whodepends` workflows where the user knows the upstream repo
    but not the conda name.

## Phase D — PyPI universe enumeration

- **Data source.** `pypi.org/simple/` (Simple v1 JSON, ~40 MB, ~800k
  project entries with freshness serials).
- **Purpose.** Mark every PyPI name with its latest serial AND insert
  `pypi_only` rows for projects not present on conda-forge.
- **What gets written.** Schema v20+ split:
  - Always-on lean path → `packages.pypi_last_serial` on conda-linked
    rows; name-coincidence rows gain `pypi_name + relationship='both_same_name'
    + match_source='name_coincidence'`.
  - TTL-gated universe upsert (`PHASE_D_UNIVERSE_TTL_DAYS`, default 7d)
    → `pypi_universe(pypi_name, last_serial, fetched_at)` side table.
  - **v19 legacy** (pre-schema-v20): pypi-only projects were inserted as
    `relationship='pypi_only'` rows in `packages`. Schema v20 migrates
    those rows to `pypi_universe` on first `init_schema` and removes the
    INSERT branch entirely. `packages` now holds only the
    conda-actionable working set.
- **Tunables.** `PHASE_D_DISABLED=1`, `PHASE_D_UNIVERSE_DISABLED=1` (skip
  just the universe upsert, keep the lean path), `PHASE_D_UNIVERSE_TTL_DAYS`
  (default 7).
- **Profile defaults (v8.0.0).** Maintainer + admin run both the lean
  path and the universe upsert. Consumer sets `PHASE_D_UNIVERSE_DISABLED=1`
  to skip the ~660k-row universe upsert (air-gap friendliness — universe
  data is reference-only).
- **Actionable intelligence.**
  - `pypi-only-candidates --limit N --min-serial M` — admin candidate
    list of unmatched PyPI projects, ordered by serial DESC (newest /
    most-active first). Reads `pypi_universe LEFT JOIN packages`.
  - `pypi_last_serial` change-detection feeds Phase H's serial-aware
    eligible-rows gate (shipped v8.0.0, schema v21).

## Phase O — PyPI activity snapshots (v8.1.0+)

- **Data source.** None — Phase O reads `pypi_universe.last_serial`
  (populated by Phase D's daily-lean path) and writes one snapshot
  row per pypi_name into `pypi_universe_serial_snapshots`. Zero new
  HTTP. Schema v22.
- **Purpose.** Materialize a per-pypi-name activity classification
  (`hot` / `warm` / `cold` / `dormant`) based on rolling serial deltas
  over 7-day and 30-day windows. Powers the `--activity` filter on the
  new `pypi-intelligence` CLI and the candidate-slice prioritization
  for Phase R (rising-activity rows get re-fetched within TTL).
- **What gets written.**
  - `pypi_universe_serial_snapshots(pypi_name, last_serial, snapshot_at)`
    — one row per `(pypi_name, snapshot_at)` PK. Retention default 90 d
    (`PHASE_O_SNAPSHOT_RETAIN_DAYS`).
  - `pypi_intelligence.{activity_band, serial_delta_7d, serial_delta_30d,
    serial_delta_calc_at}` — upserted via INSERT OR IGNORE + UPDATE-FROM-JOIN.
- **Implementation note.** Initial v8.1.0 implementation used a
  CTE-with-correlated-subqueries pattern that triggered a 806k × 806k
  catastrophic plan on the live atlas (11+ min and counting). L1
  verification 2026-05-15 caught the issue; the fix (commit
  `124c5a449d`) replaces the correlated subqueries with a single-pass
  GROUP BY aggregation + UPDATE-FROM-JOIN. Now **5.2 s** for first-run
  Phase O against 806k snapshot rows.
- **Tunables.** `PHASE_O_DISABLED`, `PHASE_O_HOT_THRESHOLD=5` (events / 7 d),
  `PHASE_O_WARM_THRESHOLD=5` (events / 30 d), `PHASE_O_SNAPSHOT_RETAIN_DAYS=90`.
- **Profile defaults (v8.1.0+).** All three profiles run Phase O (cheap;
  no new HTTP). Consumer runs O only (skips P/Q/R/S).
- **Actionable intelligence.**
  - `pypi-intelligence --activity hot --limit 50` — surfaces actively-
    moving PyPI projects (>= `PHASE_O_HOT_THRESHOLD` events in 7 days).
  - First-run behavior: every row classifies as `dormant` because there
    are no historical snapshots yet to compute deltas against. Steady
    state emerges after the second daily run.

## Phase P — BigQuery PyPI downloads (v8.1.0+, opt-in)

- **Data source.** `bigquery-public-data.pypi.file_downloads` — Google's
  official PyPI analytics dataset. Single project-level aggregation
  query over the last 90 days (~30 GB scanned per run; well within
  BigQuery free tier's 1 TB/month).
- **Purpose.** Populate the only adoption signal `pypi_intelligence`
  has access to. Without Phase P, the `conda_forge_readiness` ranking
  is structural-only (license, requires_python, packaging_shape) and
  surfaces high-readiness-but-zero-demand candidates. Phase P adds the
  demand-side filter (`pypi-intelligence --min-downloads N`).
- **What gets written.** `pypi_intelligence.{downloads_30d, downloads_90d,
  downloads_fetched_at, downloads_source='bigquery-public'}`.
- **Auth.** Lazy-imports `google.cloud.bigquery` (not in `local-recipes`
  env by default — operators run `pixi add google-cloud-bigquery`).
  Reads `GOOGLE_APPLICATION_CREDENTIALS` or `gcloud auth application-default`
  cached creds. Missing library or creds → printed install hint +
  clean skip with structured result dict; never raises.
- **Tunables.** `PHASE_P_DISABLED`, `PHASE_P_ENABLED` (must = "1" to run;
  opt-in admin-tier), `PHASE_P_BQ_PROJECT` (GCP project override),
  `PHASE_P_TTL_DAYS=30`.
- **Profile defaults (v8.1.0+).** Admin only (`PHASE_P_ENABLED=1`).
  Maintainer + consumer skip (BigQuery costs + heavy dep).
- **Per-version granularity is out of scope** for v8.1.0 — would 200×
  the scan cost and blow the BQ free tier. Project-level only.

## Phase Q — Cross-channel presence (v8.1.0+)

- **Data source.** `current_repodata.json` for four non-conda-forge
  anaconda.org channels: `bioconda`, `pytorch`, `nvidia`,
  `robostack-staging`. Each channel's noarch repodata is fetched via
  the new `resolve_anaconda_channel_urls` resolver in `_http.py`, with
  `<CHANNEL>_BASE_URL` env priority (uppercase + `-`→`_` normalization)
  for JFrog mirroring → `repo.prefix.dev/<channel>` fallback →
  `conda.anaconda.org/<channel>` last resort.
- **Purpose.** Surface "this PyPI project is already packaged on
  bioconda but not conda-forge" migration candidates. PEP 503
  canonicalization on both sides via `_pep503_canonical` ensures
  `tree_sitter` (PyPI form) matches `tree-sitter` (bioconda form).
- **What gets written.** `pypi_intelligence.{in_bioconda, in_pytorch,
  in_nvidia, in_robostack, cross_channel_at}` — BOOL flips on match,
  flips back to 0 if a previously-matched name drops off.
- **Per-channel error isolation.** One channel's HTTP 5xx doesn't
  stop the others; per-channel stats logged in the return dict.
- **Tunables.** `PHASE_Q_DISABLED`, `PHASE_Q_TTL_DAYS=7`, per-channel
  `<CHANNEL>_BASE_URL` for JFrog mirroring.
- **Profile defaults (v8.1.0+).** Maintainer + admin run; consumer
  skips (network-bound).
- **Bulk-index ecosystems** (homebrew, nixpkgs, spack, debian, fedora) —
  the `pypi_intelligence.in_<ecosystem>` columns exist in schema v22
  but the per-ecosystem fetch implementations are stretch goals
  deferred to v8.2.0. URL-pointer heuristic (count formulas whose
  source URL points at PyPI) will be the implementation pattern.

## Phase R — Per-project JSON enrichment (v8.1.0+, opt-in)

- **Data source.** `pypi.org/pypi/<name>/json` per row, bounded to the
  top-N (default 5000) pypi-only candidate slice by `last_serial DESC`.
  Reuses Phase H's worker shape: 3-attempt retry + Retry-After
  honored on 429/503 + ±25% jitter on backoff. Default concurrency = 3
  to stay under pypi.org's documented ~30 req/s per-IP ceiling.
- **Purpose.** Fetch the metadata needed for the `conda_forge_readiness`
  score — license, requires_python, classifiers, project URLs, wheel
  coverage, sdist availability, packaging-shape signals.
- **Candidate slice SQL.** `pypi-only rows ORDER BY last_serial DESC,
  excluding TTL-fresh json_fetched_at, LIMIT PHASE_R_CANDIDATE_LIMIT`.
  Activity-band-flagged rows (`activity_band='hot'`) can also enter
  the slice past the TTL gate; this rotation lets surging projects
  re-enrich faster than the default 7-day TTL.
- **What gets written.** `pypi_intelligence.{latest_version,
  latest_upload_at, latest_yanked, requires_python, license_raw,
  license_spdx (normalized), summary, home_page, repo_url, docs_url,
  issues_url, classifiers (JSON array), has_wheel, has_sdist,
  wheel_platforms (JSON list), python_tags (JSON list), packaging_shape,
  json_fetched_at, json_last_error}`.
- **`_classify_packaging_shape` deterministic rules** (priority order):
  rust-pyo3 (maturin / pyo3 / `Programming Language :: Rust` classifier)
  → cython (`Cython` in requires_dist) → pure-python (all wheels are
  `*-none-any.whl`) → c-extension (any `cp3X-cp3X` ABI in wheel
  filename) → unknown. Fortran + multi-output classifications are
  v8.2.0 stretch goals (need upstream-repo introspection).
- **`_normalize_license_to_spdx`.** Covers ~30 OSI-approved canonical
  forms (MIT / Apache-2.0 / BSD-{2,3}-Clause / ISC / GPL/LGPL/AGPL/MPL
  variants / Unlicense / CC0 / Zlib / PSF). Live-DB coverage rate
  measured at ~52% on the top-5k slice; v8.2.0 may expand the map or
  wire in a proper SPDX expression parser.
- **Tunables.** `PHASE_R_DISABLED`, `PHASE_R_ENABLED` (opt-in admin-tier),
  `PHASE_R_CANDIDATE_LIMIT=5000`, `PHASE_R_TTL_DAYS=7`,
  `PHASE_R_CONCURRENCY=3`, `PHASE_R_GH_LOOKUP` (opt-in; adds
  staged-recipes PR-state lookup).
- **Profile defaults (v8.1.0+).** Admin only. Maintainer + consumer skip.
- **Live-DB performance.** Spec estimated ~28 min for the top-5k cold
  pass. **Actual: 171.8 s (~2.9 min) at concurrency=3** because
  pypi.org/json payloads are small + CDN-cached. 9× faster than estimate.

## Phase S — Computed scores (v8.1.0+)

- **Data source.** Pure SQL UPDATE over `pypi_intelligence` Tier 1-3
  columns. No HTTP, no external state.
- **Purpose.** Composite 0-100 `conda_forge_readiness` score that
  ranks pypi-only candidates by how packageable they are, plus a
  `recommended_template` (full path) suggestion for direct conda-
  forge-expert invocation.
- **Readiness formula (6-component weighted sum, max 100):**
  - `license_ok × 25` — `license_spdx IN <OSI-approved-subset>`
  - `requires_python_ok × 20` — `>=3.10` explicit OR NULL (unspecified
    = assumed OK; conda-forge floor is 3.10)
  - `has_repo × 15` — `repo_url` populated
  - `recent_release × 15` — `latest_upload_at` within 2 years
  - `has_sdist × 10`
  - `packaging_shape_ok × 15` — pure-python/rust-pyo3/cython = full;
    c-extension = half (7); fortran/multi-output/unknown = 0
- **`recommended_template` mapping.** pure-python →
  `templates/python/recipe.yaml`; rust-pyo3 →
  `templates/python/maturin-recipe.yaml`; cython / c-extension →
  `templates/python/compiled-recipe.yaml`; else NULL (manual).
- **Skips rows without Phase R data** (`json_fetched_at IS NULL`) —
  score would be meaningless without enrichment.
- **Tunable.** `PHASE_S_DISABLED`.
- **Profile defaults (v8.1.0+).** Always runs when Phase R has data;
  graceful no-op when it doesn't.
- **Live-DB performance.** 0.3 s for 5,000-row score update.
- **Actionable intelligence.**
  - `pypi-intelligence --not-in-conda-forge --score-min 70 --limit 25`
    — flagship admin "what should I package next?" query.
  - `pypi-intelligence --score-min 90 --in-bioconda` — high-readiness
    candidates already on bioconda (migration opportunities).
  - `bus_factor_proxy` + `dependency_blast_radius` columns exist but
    populate NULL in v8.1.0 (v8.2.0 stretch — needs deps.dev /
    repo-contributor data).

## Phase E — cf-graph enrichment

- **Data source.** `github.com/regro/cf-graph-countyfair` (master tarball,
  ~150 MB compressed). The tarball is the basis for E + J + M, so all
  three phases share the same cached download.
- **Purpose.** Pull per-feedstock rendered-recipe metadata that is not in
  repodata: summary, homepage, dev_url, repo_url, keywords, maintainers,
  recipe_format (`meta.yaml` vs `recipe.yaml`), and extra-registry source
  names (npm/cran/cpan/luarocks/maven). C.5's source.url match runs
  here too.
- **What gets written.**
  - `packages.{conda_summary, conda_homepage, conda_dev_url,
    conda_repo_url, conda_keywords, recipe_format, npm_name, cran_name,
    cpan_name, luarocks_name, maven_coord}`.
  - `package_maintainers(conda_name, maintainer_handle)` junction.
  - Page-level checkpoints (`save_phase_checkpoint(cursor=...)`)
    survive mid-pagination interrupts.
- **Tunables.** `PHASE_E_ENABLED=1` (off by default — heavy fetch);
  `ATLAS_CFGRAPH_TTL_DAYS` (cache TTL, default 1 d — set to 7 for
  weekly cron). `GITHUB_BASE_URL` for JFrog Generic Remote routing.
- **Profile defaults (v8.0.0).** All three profiles set `PHASE_E_ENABLED=1`.
  Phase E feeds J + M + L (maintainer junction, dep graph, bot health,
  extra-registry names) and is the foundation of every maintainer- and
  admin-persona CLI; only legacy no-profile invocations leave it off.
- **Actionable intelligence.**
  - Maintainer junction — backs `my_feedstocks`, maintainer leaderboards,
    download-weighted leaderboard, `--maintainer X` flag on every
    persona-I CLI.
  - `recipe_format` distribution — channel-wide v0→v1 migration
    progress (admin); per-maintainer v0 backlog (`staleness-report`
    `recipe_format='meta.yaml'` filter — 📋 CLI flag open).
  - Source-registry name columns — gateway columns Phase L resolves.
  - Pre-recipe-decision context — `detail-cf-atlas` summary/homepage
    section (consumer persona).

## Phase E.5 — Archived feedstocks

- **Data source.** `gh api graphql` against `organization(login:"conda-forge")
  { repositories(first:100, isArchived:true ...) }`. Page-level checkpoints
  preserved.
- **Purpose.** Flag feedstocks GitHub knows are archived plus the
  archive timestamp.
- **What gets written.** `packages.{feedstock_archived, archived_at}`.
  GitHub doesn't expose "archived reason"; the `notes` column on
  `packages` is the right place for hand-curated annotations.
- **Actionable intelligence.**
  - "Archived but actively used" composite (E.5 + F + I) — finds
    should-not-have-archived cases for admin review (✅ SQL).
  - Abandonment detection composite — pairs `feedstock_archived` with
    maintainer-last-active (Phase N) for the open "mass-archive
    take-over" list.

## Phase F — Download counts

- **Data source (auto-dispatch on `PHASE_F_SOURCE`).**
  - `anaconda-api` — `api.anaconda.org/package/conda-forge/<name>` per
    row. Historical default; firewalled at many enterprises.
  - `s3-parquet` — `anaconda-package-data.s3.amazonaws.com/conda/monthly/
    <YYYY>/<YYYY-MM>.parquet`. Air-gap friendly. Redirectable to a
    JFrog mirror via `S3_PARQUET_BASE_URL`.
  - `auto` (default) — probe API once; on success use API with a >25%
    failure-rate fallthrough to S3; on probe failure go straight to S3.
- **Purpose.** Populate the atlas's **only** "is anyone using this?"
  signal.
- **What gets written.**
  - `packages.{total_downloads, downloads_30d, downloads_fetched_at,
    downloads_source}`. `downloads_source ∈
    {'anaconda-api','s3-parquet','merged'}` — API and S3 totals do
    NOT agree numerically (S3 ~1.5× API on popular packages); treat
    as correlated, not interchangeable.
  - `package_version_downloads` (Phase I side-effect, anaconda-api path).
- **Tunables.** `PHASE_F_SOURCE`, `PHASE_F_TTL_DAYS=7`,
  `PHASE_F_CONCURRENCY=3` (lowered 8→3 in v7.8.0 — see
  [`atlas-phase-engineering.md`](atlas-phase-engineering.md) for the
  Retry-After + jitter pattern), `PHASE_F_S3_MONTHS`, `S3_PARQUET_BASE_URL`,
  `ANACONDA_API_BASE_URL`.
- **Profile defaults (v8.0.0).** Maintainer + admin use `PHASE_F_SOURCE=auto`
  (probe-then-fallback). Consumer pins `PHASE_F_SOURCE=s3-parquet`
  (skip the anaconda.org probe — `api.anaconda.org` is firewall-blocked
  in many enterprise environments and is the atlas's only universally
  firewall-blocked dependency).
- **Actionable intelligence.**
  - `version-downloads`, `staleness-report`, `feedstock-health`,
    `adoption-stage` — every CLI that asks "is this used."
  - Bus-factor-1 detection: single-maintainer × high-downloads ×
    many-dependents.
  - Download-weighted maintainer leaderboard.
  - "Archived but actively used" (with E.5 + I).
  - 📋 Open (Wave 2 / 3 in `docs/specs/atlas-phase-f-s3-backend.md`):
    rolling 30/90-day windows, trend slope, platform / Python / channel
    breakdowns, plus `platform_breakdown`, `pyver_breakdown`,
    `channel_split` CLIs.

## Phase G — vdb risk summary

- **Data source.** Local AppThreat **vdb** library (must be importable —
  requires running from the `vuln-db` env). For each active row, derives
  purls (`pkg:pypi/<name>@<version>`, `pkg:github/<o>/<r>@<v>`, ...) and
  queries the multi-source vdb.
- **Purpose.** Cache CVE counts on `latest_conda_version` per package,
  plus a timestamped snapshot for week-over-week deltas.
- **What gets written.**
  - `packages.{vuln_total, vuln_critical_affecting_current,
    vuln_high_affecting_current, vuln_kev_affecting_current,
    vuln_scan_at}`.
  - `vuln_history(snapshot_at, conda_name, vuln_critical, vuln_high,
    vuln_kev)` — the delta engine behind `cve-watcher`.
- **Tunables.** `PHASE_G_DISABLED=1`, `PHASE_G_TTL_DAYS=7`,
  `PHASE_G_LIMIT`.
- **Actionable intelligence.**
  - `cve-watcher --maintainer X --since-days 7 --severity C` — delta
    table of what landed.
  - `cve-watcher --severity C --only-increases` — channel-wide critical
    drift (admin).
  - `staleness-report --by-risk` — weaves CVE pressure into the
    "what should I work on this week?" prioritization.
  - KEV queue via `vuln_kev_affecting_current` aggregate (CISA
    Known-Exploited-Vulnerabilities subset).
  - "Archive vs migrate vs keep" composite (F + H/K + G + J).
  - 📋 Open: CVE cascade alert (G + J join → "CVE-X published, here are
    the feedstocks to repin"); `scan-project --use-cached-vulns`
    offline mode; SBOM `--enrich-vulns-from-atlas`.

## Phase G' — Per-version vuln scoring

- **Data source.** Same vdb as Phase G, but iterates every row in
  `package_version_downloads` instead of only `latest_conda_version`.
- **Purpose.** Score every historical version separately so consumers
  can lock to a known-safe set.
- **What gets written.** `package_version_vulns(conda_name, version,
  vuln_critical_affecting_version, vuln_high_affecting_version,
  vuln_kev_affecting_version, ...)`.
- **Tunables.** `PHASE_GP_ENABLED=1` (off by default), `PHASE_GP_TTL_DAYS=30`,
  `PHASE_GP_MAINTAINER` (scope to one maintainer's packages).
- **Actionable intelligence.**
  - "Most recent build set with 0 critical CVEs" — env-lockdown
    recommendation for consumers (📋 open CLI; Phase G' is the
    enabling data).
  - "Which historical versions are risky for downstream pinners" —
    maintainer-side warning data.

## Phase H — PyPI current version

- **Data source (dispatches on `PHASE_H_SOURCE`).**
  - `pypi-json` (default) — `pypi.org/pypi/<name>/json` per row.
    Real-time; carries PEP 592 `yanked` (yanked iff **all** files of a
    version are yanked).
  - `cf-graph` — reuses the Phase E tarball. Offline, ~30 s, no yanked
    flag, hours-to-days lag behind pypi.org. Cold-start default for
    `bootstrap-data --fresh`.
- **Purpose.** Populate `upstream_versions(source='pypi')` for every
  PyPI-source recipe — the foundation for "is this feedstock behind
  upstream?"
- **Denominator (schema v20+).** The pypi-json path's eligible-rows
  selector applies the canonical persona-filter triplet
  `conda_name IS NOT NULL AND latest_status='active' AND COALESCE(feedstock_archived,0)=0`
  — same shape as Phases F/G/G'/K/L/N. Closes the v19 bug where Phase H
  fetched `pypi.org/pypi/<name>/json` for ~660k `pypi_only` rows whose
  results were silently discarded by the downstream `upstream_versions`
  UPSERT. Post-fix denominator on a freshly-built atlas: ~12k rows.
- **What gets written.**
  - `upstream_versions(conda_name, source='pypi', upstream_version,
    fetched_at)`.
  - `packages.{pypi_current_version, pypi_current_version_yanked,
    pypi_version_source}`. `pypi_version_source ∈
    {'pypi-json','cf-graph'}` — yanked-strict consumers must filter to
    `pypi-json`.
- **Tunables.** `PHASE_H_SOURCE`, `PHASE_H_TTL_DAYS=7`,
  `PHASE_H_CONCURRENCY=3` (audit-closed default; pypi.org's documented
  ~30 req/s ceiling).
- **Profile defaults (v8.0.0).** Maintainer + admin use
  `PHASE_H_SOURCE=auto` (real-time pypi-json). Consumer pins
  `PHASE_H_SOURCE=cf-graph` — offline bulk read from Phase E's tarball,
  accepts hours-to-days lag for air-gap friendliness and zero outbound
  pypi.org traffic.
- **Serial-gate eligibility (v8.0.0 / schema v21+).** Phase H's
  pypi-json path now reads `v_actionable_packages` and combines three
  gates: `pypi_version_fetched_at IS NULL` (never fetched), `pypi_last_serial
  != pypi_version_serial_at_fetch` (Phase D detected the upstream
  serial moved), or `pypi_version_fetched_at < (now − 30d)` (safety
  re-check past TTL). Stats split into `eligible_never_fetched`,
  `eligible_serial_moved`, `eligible_safety_recheck` so operators see
  why each row was selected. Net: warm-daily Phase H drops ~5 min →
  ~30 s on a typical day (only the ~30-100 packages whose serial
  moved get re-fetched).
- **Actionable intelligence.**
  - `behind-upstream --maintainer X` — flagship CLI; PEP 440 lag
    classified major/minor/patch.
  - Yanked-upstream alert — `pypi_current_version_yanked=1` filter on
    `behind-upstream --json`.
  - 📋 Open: `bot-pr-context <feedstock>` composite for autotick PRs
    (H + J + breaking-change scan); `upstream-history` time-series
    (needs a snapshot side table like `vuln_history`).

## Phase I — Per-version download history (side-table)

- **Data source.** Side-effect of Phase F's anaconda-api path
  (`api.anaconda.org/package/conda-forge/<name>` already returns the
  per-file `ndownloads` + `upload_time` payload, so no extra HTTP).
- **Purpose.** Enable release-cadence and adoption-curve analysis
  without additional fetches.
- **What gets written.** `package_version_downloads(conda_name, version,
  upload_unix, file_count, total_downloads, fetched_at, source)`.
- **Actionable intelligence.**
  - `version-downloads <pkg>` — per-version distribution + adoption
    curve.
  - `release-cadence --package <pkg> | --maintainer X` — accelerating
    / stable / decelerating / silent label from rolling window.
  - `adoption-stage <pkg>` — bleeding-edge / stable / mature /
    declining composite (F + I + age).
  - Feeds Phase G' (per-version vuln scoring iterates `package_version_downloads`).

## Phase J — Dependency graph

- **Data source.** Phase E's cached cf-graph tarball — auto-skips if the
  cache is missing.
- **Purpose.** Parse `meta_yaml.requirements` per requirement-type
  (build / host / run / test) into a queryable edge table. Multi-output
  aware: each output's own `requirements` block emits edges with that
  output's `name` as the source (e.g., `metaio-feedstock` produces
  edges from both `libmetaio` and `metaio`).
- **Denominator (v7.9.0+).** Phase J builds an `inactive_feedstocks` set
  from `packages` rows with `feedstock_archived=1 OR latest_status='inactive'`
  before opening the tarball, then skips any cf-graph node_attrs file
  whose basename appears in that set. Stat `skipped_inactive_feedstocks`
  reports the count. Closes the v19 bug where dependency edges from
  archived feedstocks landed in `dependencies` and polluted
  `whodepends --reverse` results.
- **What gets written.** `dependencies(source_conda_name, target_conda_name,
  requirement_type, pin_spec)`. Pin specs preserved verbatim
  (`'python >=3.10'` → `pin_spec='>=3.10'`, bare names → `pin_spec=NULL`).
  Full-snapshot semantics: each run `DELETE FROM dependencies` then
  re-inserts — monolithic transaction by design so consumers never see
  a partial graph. Self-refs, Jinja-placeholder targets, and
  archived/inactive feedstocks skipped.
- **Actionable intelligence.**
  - `whodepends <pkg> --reverse` — blast-radius / dependent list before
    a recipe change (✅ shipped); now noise-free post-v7.9.0 since
    archived feedstocks no longer contribute edges.
  - Dependent counts per package — backs bus-factor + adoption +
    archive composites.
  - 📋 Open: CVE cascade alert (G + J join); multi-output per-output
    dep-graph extension; Python / CUDA support-matrix queries.

## Phase K — VCS upstream versions

- **Data source.**
  - GitHub: `api.github.com/graphql` — **batched** since v7.8.0 (one
    aliased query per 100 repos, ~44 POSTs for 4,400 rows vs ~14,000
    with REST fanout). Per-alias errors map via `path[0]`; `NOT_FOUND`
    → HTTP 404. Auth: `GITHUB_TOKEN` / `GH_TOKEN` / `gh auth token`.
    `GITHUB_API_BASE_URL=https://<ghes>/api` covers GHES REST + GraphQL.
  - GitLab: `gitlab.com/api/v4` (REST fanout; `GITLAB_TOKEN`/`GL_TOKEN`
    optional).
  - Codeberg: `codeberg.org/api/v1` (REST fanout).
- **Purpose.** For ~3.5k feedstocks whose upstream-of-record is a VCS
  repo (no PyPI presence, or PyPI lags, or `source.url` is the VCS
  archive), fetch latest release/tag.
- **What gets written.**
  - `upstream_versions(conda_name, source IN
    ('github','gitlab','codeberg'), upstream_version, fetched_at)`.
  - `packages.github_current_version` (legacy column, backward-compat
    with v6.7+).
- **Tunables.** `PHASE_K_DISABLED`, `PHASE_K_TTL_DAYS=7`,
  `PHASE_K_CONCURRENCY` (REST fanout), `PHASE_K_GRAPHQL_DISABLED`
  (force REST), `PHASE_K_GRAPHQL_BATCH_SIZE=100` (keep <150 for the
  500K node-complexity ceiling). Auto-skips without GitHub auth — 60
  req/hr unauth is too low for backfill.
- **Actionable intelligence.**
  - `behind-upstream --maintainer X` adds a SOURCE column distinguishing
    `pypi` vs `github`/`gitlab`/`codeberg` so VCS-source recipes are no
    longer invisible.
  - 📋 Open: full-channel backfill (currently per-maintainer scope);
    `bot-pr-context` composite with H + J.

## Phase L — Extra registries

- **Data source.** Per-registry concurrency-capped requests (v7.8.0):
  - npm — `registry.npmjs.org`
  - CRAN — `crandb.r-pkg.org`
  - CPAN — `fastapi.metacpan.org`
  - LuaRocks — `luarocks.org` (HTML scraper)
  - crates.io — `crates.io/api`
  - RubyGems — `rubygems.org/api`
  - NuGet — `api.nuget.org/v3-flatcontainer`
  - Maven — `search.maven.org`
- **Purpose.** Same intent as Phase K, generalized to every non-VCS
  ecosystem conda-forge bridges. The behind-upstream resolver fans out
  to whichever upstream the recipe actually tracks.
- **What gets written.** `upstream_versions(conda_name, source IN
  ('npm','cran','cpan','luarocks','crates','rubygems','nuget','maven'),
  upstream_version, fetched_at)`. Phase L now runs registries
  **sequentially** with per-registry concurrency caps reflecting
  documented rate limits (`crates`/`rubygems`=1, `cran`/`cpan`/
  `luarocks`/`maven`=2, `npm`/`nuget`=4).
- **Tunables.** `PHASE_L_DISABLED`, `PHASE_L_TTL_DAYS=7`,
  `PHASE_L_CONCURRENCY` (legacy global), `PHASE_L_CONCURRENCY_<SOURCE>`
  (per-registry override, uppercase), `PHASE_L_SOURCES` (comma list to
  restrict). Each registry honors its `<HOST>_BASE_URL` env for
  enterprise routing.
- **Profile defaults (v8.0.0).** Admin + consumer leave `PHASE_L_SOURCES`
  unset (run all 8 resolvers). Maintainer auto-derives `PHASE_L_SOURCES`
  from `v_actionable_packages JOIN package_maintainers WHERE handle=<gh-user>`
  — the resolver list collapses to only the registries the maintainer
  actually tracks (e.g., a maintainer with no Lua feedstocks skips
  `luarocks` outright). Explicit env-var setting still wins.
- **Actionable intelligence.**
  - `behind-upstream --maintainer X --source npm | --source cran | ...`
    — multi-ecosystem version lag detection.
  - Unified `upstream_versions` table — single shape across 11 sources
    (pypi + 3 VCS + 8 extra registries); `behind-upstream` and
    `bot-pr-context` consume it generically.

## Phase M — Feedstock health

- **Data source.** Phase E's cached cf-graph tarball — parses
  `pr_info/<sharded>/<f>.json` and `version_pr_info/<sharded>/<f>.json`
  side files (lazy-json refs from `node_attrs`). Auto-skips if cache
  missing.
- **Purpose.** Surface feedstocks where the conda-forge bots are stuck,
  where version-update PRs aren't landing, or where cf-graph has set the
  overall "bad" health flag.
- **Denominator (v7.9.0+).** The `rows_to_process` SELECT now applies
  the canonical persona-filter triplet
  `conda_name IS NOT NULL AND latest_status='active' AND feedstock_archived=0`
  — same shape as Phases F/G/G'/K/L/N. Closes the v19 bug where Phase M
  wrote bot-status columns to archived rows that `feedstock-health`
  queries already filtered out at read time. Net: cleaner write
  pattern, no observable read-side change.
- **What gets written.** `packages.{bot_open_pr_count, bot_last_pr_state
  ∈ {'open','closed','merged',NULL}, bot_last_pr_version,
  bot_version_errors_count, feedstock_bad, bot_status_fetched_at}`.
- **Actionable intelligence.**
  - `feedstock-health --maintainer X --filter stuck` — feedstocks where
    the bot tried & failed N times (e.g., the
    `opentelemetry-instrumentation-*` family at 25-27 attempts each).
  - `feedstock-health … --filter open-pr` — open bot PRs awaiting
    review.
  - `feedstock-health … --filter bad` — cf-graph's overall unhealthy flag.
  - Channel-wide stuck count (~4,121 stuck channel-wide as of v6.9.0)
    is the admin's "where's the bot-failure pile?" query.

## Phase N — Live GitHub

- **Data source.** `gh api graphql` per feedstock — one HTTP POST per
  25-feedstock batch (~125 GraphQL points, well under 5,000-pt hourly
  limit). Closes the gap Phase M can't: cf-graph only sees what's in
  `node_attrs`; real-time CI runs, human PRs, and open issues need
  GitHub directly. Rate-limit detection parses `gh api graphql` stderr
  for primary/secondary/abuse-detection wording with 30 s/60 s base +
  ±25% jitter retries (v7.8.1).
- **Purpose.** Real-time signals: CI status on default branch, open
  issue + PR counts, `pushedAt` timestamp.
- **What gets written.** `packages.{gh_ci_status, gh_open_pr_count,
  gh_open_issue_count, gh_pushed_at, gh_status_fetched_at}`.
- **Tunables.** `PHASE_N_ENABLED=1` (off by default), `PHASE_N_MAINTAINER`
  (scope to one handle's ~700 feedstocks), `PHASE_N_TTL_DAYS=1`,
  `PHASE_N_BATCH_SIZE=25`, `PHASE_N_CONCURRENCY=4`. Auto-skips without
  `gh auth login`.
- **Profile defaults (v8.0.0).** Maintainer sets `PHASE_N_ENABLED=1`
  and auto-derives `PHASE_N_MAINTAINER` from `gh api user --jq .login`
  (operator can override via env var). Admin sets `PHASE_N_ENABLED=1`
  and leaves `PHASE_N_MAINTAINER` unset (channel-wide; ~700 feedstocks
  × 25 per batch ≈ 28 GraphQL POSTs ≈ ~30-60 s on the daily slot).
  Consumer leaves Phase N off (air-gap; no outbound api.github.com).
- **Actionable intelligence.**
  - 📋 `gh-pulls --maintainer X` / `gh-issues --maintainer X` — open
    human PRs / issues per maintainer.
  - 📋 `feedstock-health … --filter ci-red` — feedstocks with failing
    main-branch CI.
  - 📋 Abandonment detection composite — pairs `gh_pushed_at` and
    maintainer GitHub last-active with `feedstock_archived` to surface
    take-over candidates.
  - Maintainer last-active (channel-wide) for orphan / dormant
    detection.

---

## How to extend this overview

When adding a new phase or materially changing an existing one:

1. Add or update a row in the at-a-glance table (data source, TTL,
   default, primary intel it unlocks).
2. Add or update the per-phase section with the four required fields:
   data source, purpose, what gets written, actionable intelligence
   (including the corresponding `📋 open` items in
   [`atlas-actionable-intelligence.md`](atlas-actionable-intelligence.md)).
3. Bump the skill `CHANGELOG.md` per semver — MINOR for new phases or
   intel additions, PATCH for clarifications.
4. Cross-link, don't duplicate. Cadence / TTL reset / recovery lives in
   `guides/atlas-operations.md`. Rate limits, GraphQL batching,
   Retry-After + jitter, atomic writes, enterprise routing live in
   `reference/atlas-phase-engineering.md`. Persona × goal × CLI rows
   live in `reference/atlas-actionable-intelligence.md`.

The three files form a triangle:

```
                atlas-actionable-intelligence.md
                          (WHO uses WHAT)
                              /        \
                             /          \
           atlas-phases-overview.md ──── atlas-phase-engineering.md
            (WHAT each phase does)       (HOW phases compute it)
```

Together they answer: *what intelligence does the atlas surface, where
in the pipeline does it come from, and how is it engineered?*

---

## Profile Reference (v8.0.0)

`bootstrap-data --profile <name>` and `build-cf-atlas --profile <name>`
inject a bundle of env-var defaults that select the right phase mix
for each operator persona. Explicit env vars and explicit CLI flags
always win (setdefault semantics). Six phases vary across profiles —
B / B.5 / B.6 / C / G / G' / I / J / K / M are profile-invariant.

| | maintainer (daily) | admin (weekly) | consumer (read-only) |
|---|---|---|---|
| **Persona** | Feedstock maintainer running daily on their own scope | Channel-wide operator (mark-broken, archive sweeps, audits) | Air-gapped enterprise consumer (no `api.anaconda.org` / `api.github.com` egress) |
| **Phase D — universe upsert** | ✅ run | ✅ run | ⏸ skipped (`PHASE_D_UNIVERSE_DISABLED=1`) |
| **Phase E — cf-graph enrichment** | ✅ enabled (`PHASE_E_ENABLED=1`) | ✅ enabled | ✅ enabled |
| **Phase F — download counts** | auto-source (probe API → S3 fallback) | auto-source | pinned `s3-parquet` |
| **Phase H — pypi version** | auto-source (real-time pypi-json) | auto-source | pinned `cf-graph` (offline bulk) |
| **Phase L — extra registries** | auto-restricted to populated registries in scope via `v_actionable_packages JOIN package_maintainers` | all 8 resolvers | all 8 resolvers |
| **Phase N — live GitHub** | ✅ enabled, auto-scoped to `gh api user --jq .login` | ✅ enabled, channel-wide (no `PHASE_N_MAINTAINER`) | ⏸ skipped (`PHASE_N_ENABLED=""`) |
| **Expected wall-clock (warm)** | ~3-5 min (~30 s Phase H serial-gated + ~30-60 s Phase N) | ~5-10 min (channel-wide N adds time) | ~2-3 min (no N, no api.anaconda.org) |
| **Outbound network egress** | pypi.org + api.github.com + small registries | same as maintainer + larger api.github.com volume | s3.amazonaws.com (parquet) + github.com (cf-graph tarball) only |
| **Cron cadence** | daily | weekly | daily |
| **Typical caller** | `bootstrap-data --profile maintainer` | `bootstrap-data --profile admin` | `bootstrap-data --profile consumer` |

### Auto-detection (maintainer profile)

- **`gh api user --jq .login`** — 5 s timeout, gracefully degrades to a
  printed warning + channel-wide Phase N on `FileNotFoundError`
  (gh missing), non-zero exit (unauth), or timeout. The detected login
  is written to `PHASE_N_MAINTAINER` only when env doesn't already set it.
- **`v_actionable_packages JOIN package_maintainers`** — checks which
  of the five `<source>_name` columns (`npm`, `cran`, `cpan`, `luarocks`,
  `maven_coord`) have any populated value among the maintainer's
  feedstocks. Returns `None` (no restriction) when the DB is missing,
  the v21 view doesn't exist, or every registry is empty in scope.

### Backward compatibility

Operators with custom cron invocations pinning env vars manually
(`PHASE_E_ENABLED=1 PHASE_N_ENABLED=1 PHASE_N_MAINTAINER=xyz
bootstrap-data ...`) continue to work — explicit env wins over profile
defaults. The no-profile invocation keeps today's silent-skip behavior
plus an end-of-run advisory (suppressed via `BUILD_CF_ATLAS_QUIET=1`)
recommending `--profile maintainer`. The advisory is the v8.0.0
MAJOR-bump signal; if operators eventually report comfort with the
documented default, v8.1.0 may flip the no-flag invocation silently
to `--profile maintainer`.
