# Actionable Intelligence Catalog

This document catalogs the **actionable intelligence** the conda-forge-expert
skill produces from `cf_atlas.db` and adjacent data sources. It is organized
by persona (feedstock maintainer / conda-forge admin / package consumer),
then by goal, then by the action — tool, query, or signal — that produces
the outcome.

Each row captures:
- **Goal** — the question the user is trying to answer
- **Action** — the CLI / SQL / tool that produces the answer
- **Data source** — phase, table, or external system
- **Outcome** — what the user does next
- **Status** — `✅ shipped` (in v6.9.0+) / `📋 open` (planned, not yet shipped) / `❌ gap` (no current coverage, not yet planned)

Document version corresponds to skill version. Update on every release that
adds a phase, CLI, or actionable signal. Treat this as the canonical map
between "what data does the atlas expose" and "what actionable intelligence
does it produce."

---

## I. Feedstock Maintainer

The maintainer of one or more conda-forge feedstocks (e.g., `rxm7706` with
~729 feedstocks). Pain points: too many feedstocks to track manually, bot
PR churn, CVE response time, knowing when to update vs archive vs migrate.

### Triage

| Goal | Action | Data source | Outcome | Status |
|---|---|---|---|---|
| What should I work on this week? | `staleness-report --maintainer X --by-risk --limit 25` | Phase B+B.6 (status), Phase G (CVE counts), `package_maintainers` join | Prioritized list combining "old release" + "actively risky" | ✅ shipped |
| Which of my feedstocks have stuck bots? | `feedstock-health --maintainer X --filter stuck` | Phase M (cf-graph `version_pr_info.new_version_errors`) | List of feedstocks where the bot has tried & failed N times to update | ✅ shipped |
| Which of my feedstocks are behind upstream (PyPI)? | `behind-upstream --maintainer X` | Phase H + `upstream_versions` side table | List with conda version, pypi version, lag classification (major/minor/patch) | ✅ shipped |
| Which of my feedstocks are behind upstream (GitHub/GitLab/Codeberg)? | Same CLI; multi-source via Phase K | Phase K + `upstream_versions` side table | Adds SOURCE column distinguishing pypi/github/gitlab | ✅ shipped |
| Which of my feedstocks are behind upstream (npm)? | `behind-upstream --maintainer X --source npm` | Phase L (npm resolver) | Same shape, source='npm' | ✅ shipped |
| Which of my feedstocks are behind upstream (CRAN/CPAN/LuaRocks/Maven/crates/RubyGems/NuGet)? | Same | Phase L (per-registry resolver) | Same shape with source label | ✅ shipped |
| What CVEs landed on my packages this week? | `cve-watcher --maintainer X --since-days 7 --severity C` | Phase G snapshot history (`vuln_history` table) | Delta table: package, then-count, now-count, +N delta | ✅ shipped |
| Which of my feedstocks have open bot PRs awaiting review? | `feedstock-health --maintainer X --filter open-pr` | Phase M (`bot_open_pr_count`) | Count + last bot-tried version per feedstock | ✅ shipped |
| Which of my feedstocks have open *human* PRs? | `feedstock-health --maintainer X --filter open-prs-human` | Phase N — GitHub Pulls API (`gh_open_prs_count`) | Per-feedstock open-PR count (bot + human; triangulate with `--filter open-pr` for bot-only via Phase M) | ✅ shipped (v8.0.0 — Phase N default-on under `--profile maintainer`) |
| Which of my feedstocks have open issues? | `feedstock-health --maintainer X --filter open-issues` | Phase N — GitHub Issues API (`gh_open_issues_count`) | Per-feedstock open-issue count | ✅ shipped (v8.0.0 — Phase N default-on under `--profile maintainer`) |
| Which of my feedstocks have CI red on default branch? | `feedstock-health --maintainer X --filter ci-red` | Phase N — GitHub Checks API (`gh_default_branch_status`) | List of feedstocks with failing main-branch CI | ✅ shipped (v8.0.0 — Phase N default-on under `--profile maintainer`) |
| Which of my feedstocks are flagged 'bad' in cf-graph? | `feedstock-health --maintainer X --filter bad` | Phase M (`feedstock_bad`) | Feedstocks where cf-graph's overall health flag is set | ✅ shipped |

### Decisions

| Goal | Action | Data source | Outcome | Status |
|---|---|---|---|---|
| Should I archive this feedstock? | Composite query: download trend + last upstream activity + CVE pressure + dependent count | Phase F + Phase H/K + Phase G + Phase J | Archive / migrate / keep recommendation | 📋 open (composite tool) |
| Should I split a multi-output feedstock? | Per-output dep graph (currently only primary captured) | Phase J extension | Sub-output dep counts; identify natural split lines | 📋 open (Phase J+) |
| Will my recipe change break dependents? | `whodepends <pkg> --reverse` | Phase J | List of feedstocks with their pin specs against me | ✅ shipped |
| Is this version of mine adopted? | `version-downloads <pkg>` | Phase I (`package_version_downloads`) | Per-version download breakdown; adoption curve | ✅ shipped |
| Is my release cadence accelerating or slowing? | `release-cadence --package <pkg>` or `--maintainer X` | Phase I rolling window aggregation | Trend label: accelerating / stable / decelerating / silent | ✅ shipped |
| Is the upstream PyPI version yanked? | `behind-upstream --maintainer X --json` then filter `pypi_current_version_yanked=1` | Phase H (PEP 592 `releases[v][i].yanked` — yanked iff ALL files yanked) | "yanked" flag on pypi_current_version_yanked | ✅ shipped |

### Response

| Goal | Action | Data source | Outcome | Status |
|---|---|---|---|---|
| Respond to a bot version PR | `bot-pr-context <feedstock>` (planned) — composite of upstream version, breaking-change scan, dependents affected | Phase H/K + Phase J + GitHub PR diff | "merge / rerender / manual-fix" recommendation | 📋 open |
| Audit my recent activity | GitHub PR/commit search by author within conda-forge org | Phase N (or `gh search`) | Activity summary over rolling window | 📋 open (Phase N) |
| Find which of my feedstocks are stuck on the same upstream issue | Cluster by `bot_version_errors_count` + `bot_last_pr_version` | Phase M | Group of feedstocks failing the same way (e.g., the opentelemetry-instrumentation-* family at 25-27 attempts each) | ✅ shipped (manual SQL) |

### v0→v1 Migration

| Goal | Action | Data source | Outcome | Status |
|---|---|---|---|---|
| What's my v0→v1 backlog? | `staleness-report --maintainer X` filtered to `recipe_format='meta.yaml'` (filter exists implicitly via SQL; needs CLI flag) | Phase E classifier | List of v0 recipes still owned | ✅ shipped (via SQL); 📋 CLI flag open |
| Which of my v0 recipes have similar shape? (group migration) | Cluster v0 recipes by source registry, dep set, multi-output pattern | Phase E + Phase J | Migration cohorts to attack together | 📋 open |

---

## II. conda-forge Admin / Core Team

Channel-wide health, abandoned-feedstock detection, security exposure,
migration progress, maintainer-load distribution, license auditing.

### Channel Health

| Goal | Action | Data source | Outcome | Status |
|---|---|---|---|---|
| How many feedstocks have critical CVEs affecting current? | `pixi run -e local-recipes python -c "..."` against `vuln_critical_affecting_current` column (no dedicated CLI yet) | Phase G | Aggregate count + worst-offender list | ✅ shipped (SQL); 📋 dashboard CLI open |
| What's the channel-wide CVE exposure delta? | `cve-watcher --severity C --only-increases --since-days 7` | Phase G snapshot history | Channel-wide changes; new critical CVEs landed | ✅ shipped |
| How many feedstocks are bot-stuck? | `feedstock-health --filter stuck --limit 100` | Phase M | Channel-wide list (4,121 stuck channel-wide as of v6.9.0) | ✅ shipped |
| How many feedstocks are flagged 'bad'? | `feedstock-health --filter bad` | Phase M | List of feedstocks cf-graph has marked unhealthy | ✅ shipped |
| Channel migration progress (v0→v1)? | Aggregate `recipe_format` distribution | Phase E classifier | "%v0 / %v1 / %unknown" roll-up | ✅ shipped (SQL); 📋 dashboard CLI open |
| What's on PyPI but not on conda-forge? (candidate-list) | `pypi-only-candidates --limit N --min-serial M` | Phase D + `pypi_universe` side table (schema v20+) | Newest unmatched PyPI projects, ordered by `last_serial DESC` | ✅ shipped (v7.9.0) |
| Python version coverage matrix? | Parse cf-graph variant configs | Phase J extension | Matrix of feedstocks vs Python 3.10/3.11/3.12 support | 📋 open |
| CUDA support matrix? | Parse cf-graph variant configs | Phase J extension | Same shape, CUDA variants | 📋 open |

### Abandonment Detection

| Goal | Action | Data source | Outcome | Status |
|---|---|---|---|---|
| Find abandoned feedstocks (no maintainer activity + no upstream activity) | SQL composite against `gh_pushed_at` + `latest_conda_upload` + `bot_version_errors_count` | Phase N (`gh_pushed_at` per feedstock — admin profile runs channel-wide) + Phase B (`latest_conda_upload`) + Phase M | List for mass-archive or take-over | ✅ shipped (v8.0.0 — Phase N channel-wide under `--profile admin`; per-user `contributionsCollection` query is a 📋-open enhancement) |
| Bus-factor=1 critical infrastructure | Single-maintainer rows with high downloads + many dependents | Phase F + Phase J + maintainer junction | Recruit help / set up co-maintainership | ✅ shipped (SQL) |
| Orphans needing new maintainers | Feedstocks where ALL maintainers ignored bot PRs > 6mo | Phase M + Phase N | Take-over candidates | 📋 open (needs Phase N for human PR response data) |
| Feedstocks marked archived but actively used | `feedstock_archived=1` joined to recent downloads | Phase E.5 + Phase F + Phase I | Find should-not-have-archived cases | ✅ shipped (SQL) |

### Maintainer Distribution

| Goal | Action | Data source | Outcome | Status |
|---|---|---|---|---|
| Top maintainers by feedstock count | Aggregate `package_maintainers` by handle | Phase E maintainer junction | Identify overloaded maintainers | ✅ shipped (SQL) |
| Download-weighted maintainer leaderboard | Same join + downloads sum | Phase F + maintainer junction | Reach-weighted "most-impactful maintainer" list | ✅ shipped (SQL) |
| Maintainer last-active across the channel | SQL aggregate over `gh_pushed_at` per maintainer (latest feedstock push) | Phase N (`gh_pushed_at` — admin profile runs channel-wide) + maintainer junction | Latest-push timestamp per maintainer; dormant-maintainer signal | ✅ shipped (v8.0.0 — feedstock-push proxy; per-user GitHub-activity API is a 📋-open enhancement) |

### Security & Compliance

| Goal | Action | Data source | Outcome | Status |
|---|---|---|---|---|
| Channel-wide CVE summary by severity | Aggregate `vuln_*_affecting_current` | Phase G | Severity-banded counts | ✅ shipped (SQL); 📋 dashboard open |
| CVE cascade alert: when CVE-X published, find affected feedstocks | Phase G + Phase J join | Phase G + Phase J | Notification list of feedstocks to repin / rebuild | 📋 open (notification daemon) |
| KEV-list (CISA Known Exploited Vulnerabilities) coverage | `vuln_kev_affecting_current` aggregate | Phase G | High-priority remediation queue | ✅ shipped (SQL) |
| Rank by exploitation probability (not just severity) | `staleness-report --by-epss` (v8.6.0) — uses `vuln_max_epss_score` (FIRST.org EPSS overlay populated by `fetch-epss` + Phase G/G' Wave B wiring). Operator question this answers: "of my Critical/High CVEs, which are actively being exploited in the wild right now?" — distinct from raw severity count. | Phase G + EPSS overlay (Wave B v8.6.0) | Top-N feedstocks by exploitation-probability; pairs with KEV as the "most-urgent" signal | ✅ shipped (v8.6.0 Wave B + D) |
| Triage by attack category (RCE vs DoS vs Info-Disclosure vs …) | `staleness-report --has-cwe <CAT>` (v8.6.0) + `my-feedstocks --cwe` + `detail-cf-atlas` (auto-renders) — uses `vuln_cwe_top` + `vuln_cwe_categories_json` (MITRE CWE Research Concepts catalog mapped to 7 cf_atlas categories via committed seed JSON; Wave B). Operator question: "I have 10 CVEs — which are RCE vs which are info-disclosure?" | Phase G + CWE overlay (Wave B v8.6.0) | Per-package CWE-category dominant-bucket + full breakdown JSON | ✅ shipped (v8.6.0 Wave B + D) |
| Per-package binary hardening profile (PIE / RELRO / stack-canary / NX) | ~~Originally specced as Phase T (blint)~~ | ~~blint via Phase T~~ | ~~Hardening score per feedstock~~ | ✋ Wave C cancelled (v8.6.0, 2026-05-23) — conda-forge's hermetic compile environment produces uniform hardening; signal-to-effort too low. See CHANGELOG v8.6.0 Wave C section + `deferred-work.md`. |
| Filter CVE count by active-only (exclude withdrawn OSV/GHSA advisories) | ~~Originally specced as `vuln_total_active` + Phase G/G' withdrawn filter~~ | ~~Phase G/G' overlay loop with vdb `withdrawn` field~~ | ~~Active-only severity count~~ | ✋ Wave B partial-cancel (v8.6.0, 2026-05-23) — vdb's OSV (`osv.py:91`) + GHSA (`gha.py:184-185`) ingest paths skip withdrawn records at source; nothing reaches Phase G to filter. Columns dropped in schema v25 cleanup. |
| License audit (unusual / unknown / proprietary) | Aggregate `conda_license` | Phase B | Legal review queue | ✅ shipped (SQL); 📋 dashboard open |
| License compatibility check for downstream projects | Match license against compatibility matrix | Phase B + static matrix | "Yes/no compatible with target license" + offending deps | 📋 open |

### Cross-Channel Coordination

| Goal | Action | Data source | Outcome | Status |
|---|---|---|---|---|
| Find packages also on bioconda / nvidia / pytorch / robostack channels | `inventory-channel` against the other channel; or `pypi-intelligence --in-bioconda` / `--in-pytorch` / `--in-nvidia` / `--in-robostack` against the v8.1.0 pypi_intelligence `in_<channel>` BOOLs (Phase Q populates them; robostack was 404 until v8.5.2 fixed the subdir + repodata.json fallback) | `inventory_channel.py` (legacy) + Phase Q (v8.1.0+, all 4 channels reporting since v8.5.2) | Coordination opportunities | ✅ shipped (v8.5.2: 4/4 channels) |
| Mirror health (JFrog, prefix.dev) | `inventory-channel --health` | `inventory_channel.py` | Mirror cache hit rate / freshness | ✅ shipped |

### Channel Growth & Churn

| Goal | Action | Data source | Outcome | Status |
|---|---|---|---|---|
| New / archived / renamed feedstocks per month | Diff successive `built_at` snapshots of `packages` | Phase E.5 + meta history | Monthly health graph | 📋 open (needs snapshot side table) |
| Feedstock churn over time | Same, but expanded | Snapshot history | Trend metric | 📋 open |

---

## III. Consumer / Downstream User

Picking safe & maintained packages, evaluating dependency closures,
finding alternatives for archived/yanked things, environment lockdown,
SBOM generation, license compliance.

### Selection

| Goal | Action | Data source | Outcome | Status |
|---|---|---|---|---|
| Evaluate a package before adding to my env | `detail-cf-atlas <name>` (with all v6.9 enrichment sections) | Phases B/E/F/G/H/K/M | Health card: status, downloads, CVEs, behind-upstream, bot-stuck status, dependencies | ✅ shipped (most sections; bot/upstream sections in `detail-cf-atlas` 📋 open) |
| Find maintained alternative to archived X | `find-alternative <archived-name>` (planned) | Phase E keywords + Phase J dep similarity (TF-IDF) | Ranked alternatives by health | 📋 open |
| Predict package health trend | `release-cadence --package <pkg>` | Phase I | "actively maintained" vs "winding down" label | ✅ shipped |
| Adoption stage classifier | Combine release-cadence + downloads + age | Phase F + Phase I + age | bleeding-edge / stable / mature / declining label | 📋 open |

### Environment Auditing

| Goal | Action | Data source | Outcome | Status |
|---|---|---|---|---|
| Scan my pixi.lock / requirements.txt for vulns | `scan-project pixi.lock` | `scan_project.py` (existing) + vdb | CVE list across closure | ✅ shipped |
| Same scan offline (no vuln-db env required) | `scan-project --use-cached-vulns` (planned) | `scan_project.py` + Phase G cache | Same output, no heavy env | 📋 open |
| Bus-factor my dependencies | `env-inspect --bus-factor` (live env via conda-meta + atlas maintainer junction); or `bus-factor-my-env pixi.lock` for manifest-mode (still 📋) | `scan_project.py` parser + maintainer junction | Single-points-of-failure list | ✅ shipped (v8.5.0 — env-mode; manifest-mode still 📋) |
| License compatibility for my project | `env-inspect --licenses` for env rollup + non-permissive flag; `scan-project --license-check --target Apache-2.0` for target-comparison (still 📋) | `scan_project.py` + license matrix | Yes/no with offending deps | ✅ shipped (v8.5.0 — env rollup; target-license comparison still 📋) |
| SBOM (CycloneDX/SPDX) | `scan-project --sbom cyclonedx` (manifest/image/etc.); `env-inspect --sbom cyclonedx\|spdx` (live env mode) | `scan_project.py` + `env_inspect.py` + `_sbom.py` | Standard SBOM | ✅ shipped (v8.5.0 — env mode added) |
| Env-vs-env drift (set + version diff) | `env-inspect --diff OTHER_ENV` | `conda-meta/` of both envs | only-in-A / only-in-B / version-different / in-sync | ✅ shipped (v8.5.0) |
| Env-level CVE rollup | `env-inspect --security` for installed-version CVE counts; `scan-project pixi.lock` for manifest-mode | Phase G `package_version_vulns` | Per-pkg KEV/Critical/High/total ranked | ✅ shipped (v8.5.0 — env-mode; manifest-mode shipped earlier) |
| Env-version-vs-conda-forge-vs-PyPI lag | `env-inspect --freshness` with `--scope roots\|explicits\|all` (live PyPI by default; `--no-live` for atlas-only) | Phase B (cf) + Phase H/live (pypi) + Phase M (bot) | Status-banded list (cf-behind-pypi-no-PR / env-behind-cf / in-sync / …) | ✅ shipped (v8.4.0) |
| Manifest hygiene audit (pure-intent / transitively-covered / drifted explicits) | `env-inspect --audit` | `conda-meta/` + `pixi list --explicit --json` | Three-bucket pixi.toml cleanup list | ✅ shipped (v8.3.2) |
| Maintainer triage (composite) | `my-feedstocks --triage --maintainer NAME` (composes CVE / CI-red / stuck-bot / behind-upstream / open-PRs+issues into one urgency score; severity-banded) | Phase B/G/H/M/N composite | Top-N daily punch list | ✅ shipped (v8.5.0) |
| SBOM enriched with cached vuln annotations | `scan-project --sbom cyclonedx --enrich-vulns-from-atlas` (planned) | `scan_project.py` + Phase G | SBOM with CVE tags, no vdb env required | 📋 open |
| Reproduce env at known-safe state | "Show me the most recent build set with 0 critical CVEs" | Per-version vuln data — Phase G extension | Locked env recommendation | 📋 open (needs per-version vulns) |

### Notification & Tracking

| Goal | Action | Data source | Outcome | Status |
|---|---|---|---|---|
| Track when "my" package gets a security fix | `cve-watcher --watch <pkg> --notify` (poll first, webhook later) | Phase G snapshot history | Alert when CVE-X resolved | 📋 open (needs daemon/webhook) |
| Track upstream version drift over time | `upstream-history <pkg>` (planned) | `upstream_versions` history side table (planned) | Plot upstream version changes | 📋 open |
| Subscribe to risk increases for my dep set | `cve-watcher --watch-pixi-lock <path> --notify` | Phase G + lock parser | Alert on any new C/H/KEV in my closure | 📋 open |

---

## IV. Cross-cutting / Infrastructure

| Goal | Action | Data source | Outcome | Status |
|---|---|---|---|---|
| Phase H full backfill (all 805k pypi names) | Cron-style runner respecting PyPI rate limit | Phase H | Universal `behind-upstream` coverage | 📋 open (operational) |
| Phase K full backfill (all VCS-source rows) | Same, but for github/gitlab/codeberg | Phase K | Universal multi-VCS coverage | 📋 open (operational) |
| Multi-output feedstock dep parsing | Iterate each `outputs_names` element with its own requirements | Phase J extension | Accurate dep graph for big feedstocks | 📋 open |
| Recipe-format detector edge cases (116 unknown rows globally) | Probe `raw_meta_yaml` heuristics for outliers | Phase E classifier | Push 'unknown' below 1% | 📋 open |
| `upstream_versions` historical snapshots | Mirror Phase G's snapshot pattern for upstream versions | New side table | "version churn" trend analysis | 📋 open |
| Per-version vuln scoring | Phase G iterates all `package_version_downloads` rows, not just current | Phase G extension | Lock to "safe set" of versions | 📋 open |
| MCP exposure of all atlas signals | Wrap `query_atlas`, `package_health`, `my_feedstocks`, `staleness_report`, `feedstock_health`, `whodepends`, `behind_upstream`, `cve_watcher`, `version_downloads`, `release_cadence`, `find_alternative`, `adoption_stage`, `scan_project` | All phases | Single tool calls instead of one-off Python | ✅ shipped (v7.0.0) |
| Phase F download-source attribution | `SELECT downloads_source FROM packages` — populated by every Phase F write | Phase F (v7.6+) | Consumers surface which dataset produced each number (`'anaconda-api'` / `'s3-parquet'` / `'merged'`) | ✅ shipped (v7.6.0) |
| Phase P download-source provenance + coverage caveat | `SELECT downloads_source, downloads_30d FROM pypi_intelligence WHERE downloads_30d IS NULL` distinguishes "not in top-1,000" (ClickHouse default) from "never fetched"; `downloads_source='clickhouse-clickpy'` ships only ~1,000 rows (~3.3% of candidates) | Phase P (v8.16.0+, default ClickHouse) | NULL `downloads_30d`/`downloads_90d` means "outside top-1,000 by 90-day downloads" under default backend, NOT "zero downloads". Consumers building demand-side filters MUST check `downloads_source` before treating NULL as zero. For full coverage set `PHASE_P_SOURCE=bigquery` (~$22/refresh, ~30k rows). | ✅ shipped (v8.16.0); coverage caveat documented v8.16.2 |
| Air-gap Phase F via public S3 parquet | `PHASE_F_SOURCE=s3-parquet` reads `anaconda-package-data.s3.amazonaws.com`; `S3_PARQUET_BASE_URL` redirects to JFrog mirror | Phase F (v7.6+) | Atlas builds cleanly with `*.anaconda.org` blocked; downloads still populate | ✅ shipped (v7.6.0) |
| Phase F rolling 30/90-day download windows | `SELECT downloads_30d, downloads_90d FROM packages WHERE downloads_source='s3-parquet'` — monthly-resolution rolling windows from the parquet sweep; NULL on `downloads_source='anaconda-api'` rows (consumer-detection contract) | Phase F+ Wave 2 (v8.18.0) | Adoption-momentum signal comparable to `pypi_intelligence.downloads_30d/90d` but for the conda-forge namespace; feeds adoption-stage classifier, staleness rollups | ✅ shipped (v8.18.0) |
| Phase F 90-day trend slope | `SELECT downloads_trend_90d FROM packages` — `(cur90 - prev90) / prev90` capped at +10.0; NULL when <6mo data or prev90==0 (div-by-zero guard); positive=growing, negative=declining | Phase F+ Wave 2 (v8.18.0) | Direction signal: which packages are gaining vs losing adoption; surface declining-but-popular as candidate for find-alternative | ✅ shipped (v8.18.0) |
| Phase F lifetime activity months | `SELECT first_nonzero_month, last_nonzero_month FROM packages` — earliest/most-recent `'YYYY-MM'` with non-zero downloads | Phase F+ Wave 2 (v8.18.0) | Detect "always-quiet" vs "recently-dormant" packages; compute package age in months without needing release-cadence join | ✅ shipped (v8.18.0) |
| Phase F per-platform download breakdown | `package_platform_downloads(conda_name, pkg_platform, downloads_90d, downloads_total)` — one row per `(package, platform)`; noarch packages aggregate under synthetic `'noarch'` label | Phase F+ Wave 2 (v8.18.0) | Maintainer triage: how much of a package's traffic is ARM64? Win? linux-64? Drives `platform_breakdown` CLI in Wave 3 | ✅ shipped (v8.18.0) |
| Phase F per-Python-version download breakdown | `package_python_downloads(conda_name, pkg_python, downloads_90d, downloads_total)` — one row per `(package, py)`; pkg_python filtered via `^(2\.7|3\.[0-9]{1,2})$` to drop dirty parquet values | Phase F+ Wave 2 (v8.18.0) | Maintainer triage: how much py3.8 traffic remains after EOL? Drives `pyver_breakdown --policy-check` for python_min validation in Wave 3 | ✅ shipped (v8.18.0) |
| Platform-/python-/channel-aware ranking CLIs | `platform_breakdown`, `pyver_breakdown` (incl. `--policy-check` for python_min validation), `channel_split` | Phase F+ Wave 2 aggregate tables (shipped v8.18.0) + Wave 3 `package_channel_downloads` + `packages.python_min` (v8.19.0) | Maintainer-triage tools that surface ARM/win/py-EOL share | ✅ shipped (v8.19.0) |
| `platform-breakdown <pkg>` single-package mode | `package_platform_downloads` JOIN `packages` | Phase F+ Wave 2 (data) + Wave 3 (CLI v8.19.0) | "How much of <pkg>'s traffic is osx-arm64? linux-aarch64?" Drop-old-platforms decisions | ✅ shipped (v8.19.0) |
| `platform-breakdown --top N --platform P` | `package_platform_downloads` filtered by platform | Phase F+ Wave 3 (v8.19.0) | Per-platform leaderboard for ARM/win/aarch64 triage. "Which packages dominate `linux-aarch64`?" | ✅ shipped (v8.19.0) |
| `platform-breakdown --feedstock-roundup --maintainer X` | `package_platform_downloads` JOIN `package_maintainers` | Phase F+ Wave 3 (v8.19.0) | Maintainer's per-feedstock platform-share view; bus-factor-by-platform | ✅ shipped (v8.19.0) |
| `pyver-breakdown <pkg>` single-package mode | `package_python_downloads` JOIN `packages` | Phase F+ Wave 2 (data) + Wave 3 (CLI v8.19.0) | "How much py3.8 traffic remains?" Per-Python adoption signal | ✅ shipped (v8.19.0) |
| `pyver-breakdown --policy-check` bump-safe candidate detection | `packages.python_min` (Phase E write) JOIN `package_python_downloads` | Phase F+ Wave 3 (v8.19.0, schema v28) | **Headline value**: flags feedstocks where the maintainer can safely raise `python_min` without losing material adoption. Sorted bump-safe → aligned → aggressive (Q1=A) | ✅ shipped (v8.19.0) |
| `pyver-breakdown --policy-check --maintainer X --threshold-pct N` | per-maintainer JOIN + threshold knob | Phase F+ Wave 3 (v8.19.0) | Batch maintainer triage with operator-tunable noise floor (default 2%) | ✅ shipped (v8.19.0) |
| Recipe-declared `python_min` cached at atlas-build time | `packages.python_min` (new column, schema v28) | Phase E (cf-graph `raw_meta_yaml` regex) v8.19.0 | Foundation column for any future "is this recipe at the floor?" analysis. Single-writer contract: Phase E only | ✅ shipped (v8.19.0) |
| `channel-split <pkg>` single-package mode | `package_channel_downloads` JOIN `packages` | Phase F+ Wave 3 (v8.19.0, schema v28) | Per-channel breakdown surfacing how much traffic each channel (conda-forge / defaults / bioconda / pytorch / nvidia / ...) carries | ✅ shipped (v8.19.0) |
| `channel-split --defaults-share-min N --top M` | `package_channel_downloads` per-package aggregate + filter | Phase F+ Wave 3 (v8.19.0) | Migration-opportunity leaderboard: which packages have significant `defaults`-channel share and would benefit from a conda-forge feedstock? | ✅ shipped (v8.19.0) |
| `channel-split --migration-checklist --maintainer X` | per-maintainer scope + markdown emitter | Phase F+ Wave 3 (v8.19.0) | Paste-into-GitHub-issue checklist of feedstock migration candidates | ✅ shipped (v8.19.0) |
| Per-channel download breakdown side table | `package_channel_downloads(conda_name, data_source, downloads_90d, downloads_total, fetched_at)` | Phase F+ Wave 3 (v8.19.0) | Raw channel strings written as-is (no normalization); DELETE-by-scope-key + INSERT OR REPLACE chunked on partial re-runs | ✅ shipped (v8.19.0) |

---

## Status Summary (at v8.5.2)

| Status | Count | Notes |
|---|---|---|
| ✅ Shipped | ~70 | All 22 pipeline phases (B/B.5/B.6/C/C.5/D/E/E.5/F/G/G'/H/I/J/K/L/M/N + v8.1.0's O/P/Q/R/S); 17+ CLIs; full multi-registry coverage (PyPI/GitHub/GitLab/Codeberg/npm/CRAN/CPAN/LuaRocks/crates/RubyGems/NuGet/Maven — including Phase E auto-detection of Maven coordinates from cf-graph URLs); SBOM input/output across CycloneDX 1.4-1.6 (JSON+XML), SPDX 2.x JSON+tag-value+3.0, syft/trivy native; **SBOM relationship traversal rendered as a tree**; container image + OCI manifest probe + live env + GitOps (Argo/Flux with auto git-clone fallback) + K8s scanning; license-check + find-alternative + adoption-stage + SBOM atlas-vuln enrichment; **PyPI yanked-flag detection (PEP 592)**; **12 MCP tools** wrapping the entire read-side surface; **`bootstrap-data` single-command refresh with `--fresh` hard reset**; **v8.0.0: `v_actionable_packages` view + structural-enforcement meta-test**; **Phase H serial-aware eligible-rows gate (warm-daily ~5 min → ~30 s)**; **`--profile maintainer\|admin\|consumer` persona-aware default profiles for `bootstrap-data` with `gh api user` auto-detection**; **5 previously-📋 Phase-N-gated catalog rows flipped to ✅** (open human PRs, open issues, ci-red filter, abandonment composite, maintainer last-active — all via Phase N default-on under `--profile maintainer`); **v8.5.2: Phase K hang fix (hard-timeout watchdog + per-batch checkpoint + per-batch progress log); Phase P (BigQuery PyPI downloads) operationally enabled — google-cloud-bigquery bundled, new `gcloud` env, 4-step operator setup walkthrough; **v8.15.0: Phase P incremental refresh — schema v26 `pypi_downloads_daily` side table + dry-run preflight + `maximum_bytes_billed` hard cap + `job_timeout_ms` wall-clock cap; drives sustained refresh cost below $1/run (~$30/year vs ~$2,000+/year pre-fix); new env vars `PHASE_P_MAX_COST_USD=10`, `PHASE_P_MAX_COST_FIRST_PULL_USD=100`, `PHASE_P_RETAIN_DAYS=95`, `PHASE_P_JOB_TIMEOUT_MS=600000`, `PHASE_P_FORCE_FIRST_PULL=1`; cost model at `reference/atlas-phase-p-cost-model.md`**; Phase Q robostack 4/4 channels reporting (was 0); Phase N partial-batch recovery (no more whole-batch poisoning on one missing repo)** |
| 📋 Open | ~6 | Channel-wide Phase H/N cron operationalization (per-maintainer scope shipped; full-channel needs PAT rotation or daily 30-min run); per-version vdb-history snapshot side table for time-travel queries; multi-output feedstock per-output dep-graph (Phase J extension — currently captures top-level only); `recipe_format='unknown'` heuristic refinement (116 outliers); CycloneDX Protobuf / SPDX RDF (deferred — heavy deps, marginal use); per-user GitHub `contributionsCollection` query for finer-grained maintainer-activity signal (current `gh_pushed_at` proxy is feedstock-push, not user activity); drop or properly-wire `vuln_total` column (4 consumers found in v8.0.0 audit — column kept; CLI consolidation deferred) |
| ❌ Gap | 0 | All originally-identified gaps now have a path forward; remaining items are operational/enhancement work, not feature blockers |

The 📋 open items are tracked in
[CHANGELOG.md](../CHANGELOG.md) v6.9.0 "Limitations / known follow-ups" and
in this catalog. Update both when shipping.

---

## How to extend this catalog

When adding a new phase, CLI, or actionable signal:

1. Add a row in the appropriate persona section.
2. Mark status: `✅ shipped` (in the just-merged release), `📋 open` (planned with effort estimate), or `❌ gap` (no current coverage).
3. Tie the row to the phase letter and (if applicable) the specific column / table / CLI.
4. Update the Status Summary count.
5. If the new item promotes an existing 📋 → ✅, leave the row in place but flip the status; that preserves history.

Treat the 📋 → ✅ flip as part of the release work — it's the same edit as
the CHANGELOG entry. The catalog and CHANGELOG together form the
"what does conda-forge-expert do?" answer.
