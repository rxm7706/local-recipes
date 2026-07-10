# cf_atlas — Phases & Actionable Intelligence

> **Consolidated reference (2026-07-02).** This file absorbed
> `atlas-actionable-intelligence.md` (the persona × goal catalog); the two views now live
> together. **Part A** is the persona-indexed catalog (WHO uses WHAT); **Part B** is the
> phase-indexed overview (WHAT each phase does and writes). Engineering patterns (rate
> limits, GraphQL batching, atomic writes, checkpoints, the Phase P cost model) live in
> [`atlas-phase-engineering.md`](atlas-phase-engineering.md); cadence, TTLs, profile
> invocations, and recovery playbooks live in
> [`../guides/atlas-operations.md`](../guides/atlas-operations.md) — link out, don't
> duplicate.

Source of truth for each phase's behavior remains the docstrings in
`scripts/conda_forge_atlas.py`. This document distills them into the intelligence
outcomes they unlock. Update on every release that adds a phase, CLI, or actionable
signal — both parts plus the Status Summary, in the same edit as the CHANGELOG entry.

---

## Part A — Actionable-intelligence catalog (persona × goal)

Organized by persona (feedstock maintainer / conda-forge admin / consumer / cross-cutting),
then by goal, then by the action that produces the outcome. Each row captures:

- **Goal** — the question the user is trying to answer
- **Action** — the CLI / SQL / tool that produces the answer
- **Data source** — phase, table, or external system
- **Outcome** — what the user does next
- **Status** — `✅ shipped` / `📋 open` (planned, not yet shipped) / `❌ gap` (no current coverage, not yet planned)

### I. Feedstock Maintainer

The maintainer of one or more conda-forge feedstocks (e.g., `rxm7706` with
~729 feedstocks). Pain points: too many feedstocks to track manually, bot
PR churn, CVE response time, knowing when to update vs archive vs migrate.

#### Triage

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

#### Decisions

| Goal | Action | Data source | Outcome | Status |
|---|---|---|---|---|
| Should I archive this feedstock? | Composite query: download trend + last upstream activity + CVE pressure + dependent count | Phase F + Phase H/K + Phase G + Phase J | Archive / migrate / keep recommendation | 📋 open (composite tool) |
| Should I split a multi-output feedstock? | Per-output dep graph (currently only primary captured) | Phase J extension | Sub-output dep counts; identify natural split lines | 📋 open (Phase J+) |
| Will my recipe change break dependents? | `whodepends <pkg> --reverse` | Phase J | List of feedstocks with their pin specs against me | ✅ shipped |
| Is this version of mine adopted? | `version-downloads <pkg>` | Phase I (`package_version_downloads`) | Per-version download breakdown; adoption curve | ✅ shipped |
| Is my release cadence accelerating or slowing? | `release-cadence --package <pkg>` or `--maintainer X` | Phase I rolling window aggregation | Trend label: accelerating / stable / decelerating / silent | ✅ shipped |
| Is the upstream PyPI version yanked? | `behind-upstream --maintainer X --json` then filter `pypi_current_version_yanked=1` | Phase H (PEP 592 `releases[v][i].yanked` — yanked iff ALL files yanked) | "yanked" flag on pypi_current_version_yanked | ✅ shipped |

#### Response

| Goal | Action | Data source | Outcome | Status |
|---|---|---|---|---|
| Respond to a bot version PR | `bot-pr-context <feedstock>` (planned) — composite of upstream version, breaking-change scan, dependents affected | Phase H/K + Phase J + GitHub PR diff | "merge / rerender / manual-fix" recommendation | 📋 open |
| Audit my recent activity | GitHub PR/commit search by author within conda-forge org | Phase N (or `gh search`) | Activity summary over rolling window | 📋 open (Phase N) |
| Find which of my feedstocks are stuck on the same upstream issue | Cluster by `bot_version_errors_count` + `bot_last_pr_version` | Phase M | Group of feedstocks failing the same way (e.g., the opentelemetry-instrumentation-* family at 25-27 attempts each) | ✅ shipped (manual SQL) |

#### v0→v1 Migration

| Goal | Action | Data source | Outcome | Status |
|---|---|---|---|---|
| What's my v0→v1 backlog? | `staleness-report --maintainer X` filtered to `recipe_format='meta.yaml'` (filter exists implicitly via SQL; needs CLI flag) | Phase E classifier | List of v0 recipes still owned | ✅ shipped (via SQL); 📋 CLI flag open |
| Which of my v0 recipes have similar shape? (group migration) | Cluster v0 recipes by source registry, dep set, multi-output pattern | Phase E + Phase J | Migration cohorts to attack together | 📋 open |

---

### II. conda-forge Admin / Core Team

Channel-wide health, abandoned-feedstock detection, security exposure,
migration progress, maintainer-load distribution, license auditing.

#### Channel Health

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

#### Abandonment Detection

| Goal | Action | Data source | Outcome | Status |
|---|---|---|---|---|
| Find abandoned feedstocks (no maintainer activity + no upstream activity) | SQL composite against `gh_pushed_at` + `latest_conda_upload` + `bot_version_errors_count` | Phase N (`gh_pushed_at` per feedstock — admin profile runs channel-wide) + Phase B (`latest_conda_upload`) + Phase M | List for mass-archive or take-over | ✅ shipped (v8.0.0 — Phase N channel-wide under `--profile admin`; per-user `contributionsCollection` query is a 📋-open enhancement) |
| Bus-factor=1 critical infrastructure | Single-maintainer rows with high downloads + many dependents | Phase F + Phase J + maintainer junction | Recruit help / set up co-maintainership | ✅ shipped (SQL) |
| Orphans needing new maintainers | Feedstocks where ALL maintainers ignored bot PRs > 6mo | Phase M + Phase N | Take-over candidates | 📋 open (needs Phase N for human PR response data) |
| Feedstocks marked archived but actively used | `feedstock_archived=1` joined to recent downloads | Phase E.5 + Phase F + Phase I | Find should-not-have-archived cases | ✅ shipped (SQL) |

#### Maintainer Distribution

| Goal | Action | Data source | Outcome | Status |
|---|---|---|---|---|
| Top maintainers by feedstock count | Aggregate `package_maintainers` by handle | Phase E maintainer junction | Identify overloaded maintainers | ✅ shipped (SQL) |
| Download-weighted maintainer leaderboard | Same join + downloads sum | Phase F + maintainer junction | Reach-weighted "most-impactful maintainer" list | ✅ shipped (SQL) |
| Maintainer last-active across the channel | SQL aggregate over `gh_pushed_at` per maintainer (latest feedstock push) | Phase N (`gh_pushed_at` — admin profile runs channel-wide) + maintainer junction | Latest-push timestamp per maintainer; dormant-maintainer signal | ✅ shipped (v8.0.0 — feedstock-push proxy; per-user GitHub-activity API is a 📋-open enhancement) |

#### Security & Compliance

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

#### Cross-Channel Coordination

| Goal | Action | Data source | Outcome | Status |
|---|---|---|---|---|
| Find packages also on bioconda / nvidia / pytorch / robostack channels | `inventory-channel` against the other channel; or `pypi-intelligence --in-bioconda` / `--in-pytorch` / `--in-nvidia` / `--in-robostack` against the v8.1.0 pypi_intelligence `in_<channel>` BOOLs (Phase Q populates them; robostack was 404 until v8.5.2 fixed the subdir + repodata.json fallback) | `inventory_channel.py` (legacy) + Phase Q (v8.1.0+, all 4 channels reporting since v8.5.2) | Coordination opportunities | ✅ shipped (v8.5.2: 4/4 channels) |
| Mirror health (JFrog, prefix.dev) | `inventory-channel --health` | `inventory_channel.py` | Mirror cache hit rate / freshness | ✅ shipped |

#### Channel Growth & Churn

| Goal | Action | Data source | Outcome | Status |
|---|---|---|---|---|
| New / archived / renamed feedstocks per month | Diff successive `built_at` snapshots of `packages` | Phase E.5 + meta history | Monthly health graph | 📋 open (needs snapshot side table) |
| Feedstock churn over time | Same, but expanded | Snapshot history | Trend metric | 📋 open |

---

### III. Consumer / Downstream User

Picking safe & maintained packages, evaluating dependency closures,
finding alternatives for archived/yanked things, environment lockdown,
SBOM generation, license compliance.

#### Selection

| Goal | Action | Data source | Outcome | Status |
|---|---|---|---|---|
| Evaluate a package before adding to my env | `detail-cf-atlas <name>` (with all v6.9 enrichment sections) | Phases B/E/F/G/H/K/M | Health card: status, downloads, CVEs, behind-upstream, bot-stuck status, dependencies | ✅ shipped (most sections; bot/upstream sections in `detail-cf-atlas` 📋 open) |
| Find maintained alternative to archived X | `find-alternative <archived-name>` (planned) | Phase E keywords + Phase J dep similarity (TF-IDF) | Ranked alternatives by health | 📋 open |
| Predict package health trend | `release-cadence --package <pkg>` | Phase I | "actively maintained" vs "winding down" label | ✅ shipped |
| Adoption stage classifier | Combine release-cadence + downloads + age | Phase F + Phase I + age | bleeding-edge / stable / mature / declining label | 📋 open |

#### Environment Auditing

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
| Which of my deps aren't on conda-forge / are version-lagging? | `inventory-match <manifest/lock/SBOM>` (+ `--policy` for a CI gate rc 2, `--weights` criticality sidecar) | mapping (packages) + `upstream_versions` + `v_pypi_intelligence_valid` + S5 three-way comparison | ADD / ADD-NONPYPI / UPDATE-FEEDSTOCK / UPDATE-PIN / CURRENT / UNKNOWN buckets with `match_confidence` + freshness percentile per row | ✅ shipped (v8.71.0, cyclonedx-universe-inventory S5) |
| Hand my not-on-cf deps to the packaging factory | `add-handoff --matches <inventory-match.json>` | ADD bucket + Phase R single-package enrichment + canonical Phase S scoring | Readiness-sorted packaging worklist with fail-closed license blockers | ✅ shipped (v8.71.0, S6) |
| Which of my libraries — Python or not — survive 2027–2030? | `recommend-2027 <inventory>` (MCP: `recommend_2027`) | S5 rows + backbone signals (upstream/cadence/adoption/Phase F downloads/`v_current_version_vulns`/health/license/blast radius) + py314 + endoflife.date LTS/EOL | `futures_score` + keep/watch/plan-migration/replace tier per package, per-signal breakdown, overrides shown never-silent | ✅ shipped (v8.71.0, S7+S8) |
| Full-universe purl/mapping export or SBOM | `export-purls` / `universe-sbom [--format spdx] [--<slice>-only]` | `packages` + `pypi_universe` + `upstream_versions` (+ vuln rollups with `--with-vulns`) | Six purl artifacts; CycloneDX 1.6 / SPDX BOM (mapped pair = ONE conda component) | ✅ shipped (v8.71.0, S1/S3) |

#### Notification & Tracking

| Goal | Action | Data source | Outcome | Status |
|---|---|---|---|---|
| Track when "my" package gets a security fix | `cve-watcher --watch <pkg> --notify` (poll first, webhook later) | Phase G snapshot history | Alert when CVE-X resolved | 📋 open (needs daemon/webhook) |
| Track upstream version drift over time | `upstream-history <pkg>` (planned) | `upstream_versions` history side table (planned) | Plot upstream version changes | 📋 open |
| Subscribe to risk increases for my dep set | `cve-watcher --watch-pixi-lock <path> --notify` | Phase G + lock parser | Alert on any new C/H/KEV in my closure | 📋 open |

---

### IV. Cross-cutting / Infrastructure

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
| Phase P download-source provenance + coverage caveat | `pypi_intelligence.downloads_source` — under the default ClickHouse backend, NULL `downloads_30d`/`downloads_90d` means "outside top-1,000 by 90-day downloads", NOT "zero downloads"; check provenance (`'clickhouse-clickpy'` ships only ~1,000 rows ≈ 3.3% of candidates) before any demand-side filter. Full caveat: Part B § Phase P | Phase P (v8.16.0+, default ClickHouse) | Correct NULL interpretation; `PHASE_P_SOURCE=bigquery` (~$22/refresh, ~30k rows) for full coverage | ✅ shipped (v8.16.0); coverage caveat documented v8.16.2 |
| Air-gap Phase F via public S3 parquet | `PHASE_F_SOURCE=s3-parquet` reads `anaconda-package-data.s3.amazonaws.com`; `S3_PARQUET_BASE_URL` redirects to JFrog mirror | Phase F (v7.6+) | Atlas builds cleanly with `*.anaconda.org` blocked; downloads still populate | ✅ shipped (v7.6.0) |
| Phase F rolling 30/90-day windows + 90-day trend slope + lifetime activity months | `SELECT downloads_30d, downloads_90d, downloads_trend_90d, first_nonzero_month, last_nonzero_month FROM packages` — s3-parquet path only; NULL on `anaconda-api` rows (provenance contract). Column semantics + NULL/cap rules: Part B § Phase F | Phase F+ Wave 2 (v8.18.0) | Adoption-momentum + direction signals; feeds adoption-stage, staleness rollups, find-alternative | ✅ shipped (v8.18.0) |
| Phase F per-platform / per-Python / per-channel breakdown tables | `package_platform_downloads` + `package_python_downloads` (Wave 2) + `package_channel_downloads` (Wave 3) — table semantics, noarch/dirty-value handling, and re-run discipline: Part B § Phase F | Phase F+ Waves 2–3 (v8.18.0 / v8.19.0) | The raw data behind the three Wave-3 CLIs below | ✅ shipped |
| `platform-breakdown` CLI — 3 modes: `<pkg>` / `--top N --platform P` / `--feedstock-roundup --maintainer X` | `package_platform_downloads` JOIN `packages` / `package_maintainers` | Phase F+ Wave 3 (v8.19.0) | "How much of the traffic is ARM / win / aarch64?" — drop-old-platform decisions, per-platform leaderboards, maintainer roundup | ✅ shipped (v8.19.0) |
| `pyver-breakdown` CLI — single-package + `--policy-check [--maintainer X] [--threshold-pct N]` (default 2%) | `package_python_downloads` + `packages.python_min` (Phase E write, schema v28; single-writer contract) | Phase F+ Wave 3 (v8.19.0) | **Headline value**: flags feedstocks where `python_min` can be raised without losing material adoption; sorted bump-safe → aligned → aggressive (Q1=A) | ✅ shipped (v8.19.0) |
| `channel-split` CLI — 3 modes: `<pkg>` / `--defaults-share-min N --top M` / `--migration-checklist --maintainer X` | `package_channel_downloads` JOIN `packages` | Phase F+ Wave 3 (v8.19.0) | Per-channel traffic split; defaults-channel migration leaderboard + paste-into-GitHub-issue checklist | ✅ shipped (v8.19.0) |

---

### Status Summary (at v8.5.2)

| Status | Count | Notes |
|---|---|---|
| ✅ Shipped | ~70 | All 22 pipeline phases (B/B.5/B.6/C/C.5/D/E/E.5/F/G/G'/H/I/J/K/L/M/N + v8.1.0's O/P/Q/R/S); 17+ CLIs; full multi-registry coverage (PyPI/GitHub/GitLab/Codeberg/npm/CRAN/CPAN/LuaRocks/crates/RubyGems/NuGet/Maven — including Phase E auto-detection of Maven coordinates from cf-graph URLs); SBOM input/output across CycloneDX 1.4-1.6 (JSON+XML), SPDX 2.x JSON+tag-value+3.0, syft/trivy native; **SBOM relationship traversal rendered as a tree**; container image + OCI manifest probe + live env + GitOps (Argo/Flux with auto git-clone fallback) + K8s scanning; license-check + find-alternative + adoption-stage + SBOM atlas-vuln enrichment; **PyPI yanked-flag detection (PEP 592)**; **12 MCP tools** wrapping the entire read-side surface; **`bootstrap-data` single-command refresh with `--fresh` hard reset**; **v8.0.0: `v_actionable_packages` view + structural-enforcement meta-test**; **Phase H serial-aware eligible-rows gate (warm-daily ~5 min → ~30 s)**; **`--profile maintainer\|admin\|consumer` persona-aware default profiles for `bootstrap-data` with `gh api user` auto-detection**; **5 previously-📋 Phase-N-gated catalog rows flipped to ✅** (open human PRs, open issues, ci-red filter, abandonment composite, maintainer last-active — all via Phase N default-on under `--profile maintainer`); **v8.5.2: Phase K hang fix (hard-timeout watchdog + per-batch checkpoint + per-batch progress log); Phase P (BigQuery PyPI downloads) operationally enabled — google-cloud-bigquery bundled, new `gcloud` env, 4-step operator setup walkthrough; **v8.15.0: Phase P incremental refresh — schema v26 `pypi_downloads_daily` side table + dry-run preflight + `maximum_bytes_billed` hard cap + `job_timeout_ms` wall-clock cap; drives sustained refresh cost below $1/run (~$30/year vs ~$2,000+/year pre-fix); new env vars `PHASE_P_MAX_COST_USD=10`, `PHASE_P_MAX_COST_FIRST_PULL_USD=100`, `PHASE_P_RETAIN_DAYS=95`, `PHASE_P_JOB_TIMEOUT_MS=600000`, `PHASE_P_FORCE_FIRST_PULL=1`; cost model at `atlas-phase-engineering.md` § 13**; Phase Q robostack 4/4 channels reporting (was 0); Phase N partial-batch recovery (no more whole-batch poisoning on one missing repo)** |
| 📋 Open | ~6 | Channel-wide Phase H/N cron operationalization (per-maintainer scope shipped; full-channel needs PAT rotation or daily 30-min run); per-version vdb-history snapshot side table for time-travel queries; multi-output feedstock per-output dep-graph (Phase J extension — currently captures top-level only); `recipe_format='unknown'` heuristic refinement (116 outliers); CycloneDX Protobuf / SPDX RDF (deferred — heavy deps, marginal use); per-user GitHub `contributionsCollection` query for finer-grained maintainer-activity signal (current `gh_pushed_at` proxy is feedstock-push, not user activity); drop or properly-wire `vuln_total` column (4 consumers found in v8.0.0 audit — column kept; CLI consolidation deferred) |
| ❌ Gap | 0 | All originally-identified gaps now have a path forward; remaining items are operational/enhancement work, not feature blockers |

The 📋 open items are tracked in
[CHANGELOG.md](../CHANGELOG.md) v6.9.0 "Limitations / known follow-ups" and
in this catalog. Update both when shipping.

---

## Part B — Phase-indexed overview

One section per pipeline stage. For each phase: **data source** (exact URLs/datasets),
**purpose** (what new fact lands in `cf_atlas.db`), **what gets written** (tables +
columns), and **actionable intelligence** (the CLIs, MCP tools, and SQL it makes
possible; `📋 open` items from Part A are noted against the phase that would deliver
them).

### At-a-glance index

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
| **F** | Download counts | `api.anaconda.org/package/conda-forge/<name>` OR `anaconda-package-data.s3.amazonaws.com/conda/monthly/<YYYY>/<YYYY-MM>.parquet` | `PHASE_F_TTL_DAYS=7` | always (`s3-parquet` pinned under `--profile admin` (v8.17.0+) and `--profile consumer`; `--profile maintainer` uses `auto` since maintainer-scoped row sets are small) | Usage signal — leaderboards, bus-factor, adoption-stage, "archived but used" |
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

### Phase B — Conda enumeration

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

### Phase B.5 — Feedstock-outputs archive

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
- **Known caveat (follow-up, 2026-07-10).** For an output published by >1
  feedstock, `feedstock_name` is set to `feedstocks[0]`, which can be the
  historical umbrella feedstock rather than the dedicated one — e.g.
  `dbt-bigquery` maps to `['dbt','dbt-bigquery']` and is mis-attributed to
  `dbt`, collapsing the whole `dbt-*` adapter family into one feedstock.
  Fix (see the `FOLLOW-UP` note at the `feedstocks[0]` line in
  `phase_b5_feedstock_outputs`): when `len(feedstocks) > 1`, prefer the entry
  equal to the conda name. Affects feedstock-granular maintainer views only
  (surfaced building the rxm7706/about sole-vs-co lists); ~1 in 810 for that
  maintainer.
- **Actionable intelligence.**
  - Canonical feedstock per conda name — backs every maintainer-scoped
    CLI (`staleness-report --maintainer`, `feedstock-health`,
    `behind-upstream`, `cve-watcher`).
  - Yanked-output detection ("was once shipped, no longer present in
    repodata") — backs the "archived but used" composite (Phase E.5 + F + I).

### Phase B.6 — Yanked detection (lite)

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

### Phase C — Parselmouth PyPI ↔ conda join

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

### Phase C.5 — source.url match (folded into Phase E)

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

### Phase D — PyPI universe enumeration

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

### Phase O — PyPI activity snapshots (v8.1.0+)

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

### Phase P — BigQuery PyPI downloads (v8.1.0+, opt-in)

- **Data source (v8.16.0+).** Default backend is ClickHouse clickpy —
  free, no auth, no billing, sub-minute refresh. BigQuery available
  as `PHASE_P_SOURCE=bigquery` opt-in for operators needing raw event
  data. Selection via `PHASE_P_SOURCE` env var; see
  `atlas-phase-engineering.md` § 13 "Source backends".
- **ClickHouse (default, free).** `pypi.pypi_downloads_per_day` at
  `sql-clickhouse.clickhouse.com/?user=play` — pre-aggregated
  (date, project, count) materialized view mirrored daily from the
  same BigQuery source. Single-query top-N (ORDER BY 90-day
  downloads DESC LIMIT 1,000) in ~2 s; $0 verified 2026-06-12.
  **Coverage caveat (verify-quantitative-claims, v8.16.2):** the
  default ships top-1,000 packages, which is ~3.3% of the ~30k
  `pypi_intelligence` candidate rows. Packages outside top-1,000
  by 90-day downloads have NULL `downloads_30d`/`downloads_90d`
  under the default backend — NULL means "not in top-1,000",
  NOT "zero downloads". `downloads_source = 'clickhouse-clickpy'`
  is the provenance marker; consumers should check it before
  acting on missing-data assumptions. The bucket-paginated
  full-coverage design v8.16.0 originally specified was abandoned
  during implementation — ClickHouse Play's ~1,000-row aggregated
  response cap + rate-limit on sustained bursts made full coverage
  impractical (25+ min wall-clock with 95% retry overhead). For
  full ~870k-project coverage from a free source, set
  `PHASE_P_SOURCE=bigquery` and wait for the GCP free-tier
  monthly quota reset, or accept the ~$22 monthly cost. Note:
  `pypi_downloads_daily` (schema v26) is **unused** under the
  ClickHouse default — the table stays at 0 rows; it only
  populates when `PHASE_P_SOURCE=bigquery`.
- **BigQuery (opt-in, paid).** `bigquery-public-data.pypi.file_downloads`
  — Google's official PyPI analytics dataset (~1.14 PB,
  column-partitioned on `timestamp` with DAY granularity, clustered
  on `project`). **Cost (verified 2026-06-12 via live dry-run
  preflight):** 90-day first-pull ~9.5 TB → ~$59; 30-day monthly
  refresh ~3.5 TB → ~$22; 7-day weekly ~860 GB → ~$5.37; 1-day daily
  ~140 GB → ~$0.88. Monthly cadence EXCEEDS the $10 default cap —
  raise `PHASE_P_MAX_COST_USD` to ~$25 or use weekly/daily. v8.14.3
  added dry-run preflight + `maximum_bytes_billed` hard cap; v8.15.2
  corrected the SQL that v8.14.3+v8.15.0 shipped broken.
- **Purpose.** Populate the only adoption signal `pypi_intelligence`
  has access to. Without Phase P, the `conda_forge_readiness` ranking
  is structural-only (license, requires_python, packaging_shape) and
  surfaces high-readiness-but-zero-demand candidates. Phase P adds the
  demand-side filter (`pypi-intelligence --min-downloads N`).
- **What gets written.** `pypi_intelligence.{downloads_30d, downloads_90d,
  downloads_fetched_at, downloads_source='bigquery-public'}`.
- **Auth.** Lazy-imports `google.cloud.bigquery` (bundled in
  `local-recipes` env since v8.5.2+; the lib reads
  `GOOGLE_APPLICATION_CREDENTIALS` or `gcloud auth application-default`
  cached creds at `~/.config/gcloud/application_default_credentials.json`).
  Missing library or creds → printed install hint + clean skip with
  structured result dict; never raises.
- **Tunables.** `PHASE_P_DISABLED`, `PHASE_P_ENABLED` (must = "1" to run;
  opt-in admin-tier), `PHASE_P_BQ_PROJECT` (GCP project override),
  `PHASE_P_TTL_DAYS=30`.
- **Profile defaults (v8.1.0+).** Admin only (`PHASE_P_ENABLED=1`).
  Maintainer + consumer skip (BigQuery costs + heavy dep).
- **Per-version granularity is out of scope** for v8.1.0 — would 200×
  the scan cost and blow the BQ free tier. Project-level only.

#### Phase P operator setup (one-time)

Phase P needs a GCP billing project (free to create at
console.cloud.google.com — even free-tier queries bill against one)
and a one-time interactive `gcloud` auth. Once configured, future
runs are unattended.

```bash
# 1. Set the GCP project ID (any project where the BigQuery API is
#    enabled and you have query access). Put this in .env so every
#    pixi-activated shell picks it up automatically.
echo 'PHASE_P_BQ_PROJECT=<your-gcp-project-id>' >> .env

# 2. One-time interactive auth — opens a browser for OAuth. The
#    `gcloud` env (separate from `local-recipes` because the SDK is
#    ~91 MB) carries the `gcloud` CLI; it's linux + macOS only.
pixi run -e gcloud gcloud auth application-default login \
    --project <your-gcp-project-id>

# 3. One-time API enable. Two ways — either the browser console:
#      https://console.developers.google.com/apis/api/bigquery.googleapis.com/overview?project=<your-gcp-project-id>
#    Click "Enable". Or via gcloud (requires a *second* auth — the
#    CLI uses different creds than ADC):
pixi run -e gcloud gcloud auth login   # needed once for the CLI itself
pixi run -e gcloud gcloud services enable bigquery.googleapis.com \
    --project <your-gcp-project-id>

# 4. Verify the client lib + creds resolve cleanly.
pixi run -e local-recipes python -c "
from google.cloud import bigquery; import google.auth
creds, proj = google.auth.default()
print('lib version:', bigquery.__version__)
print('creds type:', type(creds).__name__)
"
```

#### Phase P run

```bash
# Standalone (just Phase P — fastest when the rest of the atlas is fresh)
PHASE_P_ENABLED=1 pixi run -e local-recipes \
    python .claude/scripts/conda-forge-expert/atlas_phase.py P

# As part of a channel-wide refresh (admin profile auto-sets
# PHASE_P_ENABLED=1 when google-cloud-bigquery is importable):
pixi run -e local-recipes bootstrap-data --profile admin
```

Expected: dry-run preflight prints estimated scan + cost (typical
~2.5–4 TB scan → ~$15–25 at on-demand $6.25/TB); if the estimate is
below the operator cap (`PHASE_P_MAX_COST_USD` default $10 refresh /
`PHASE_P_MAX_COST_FIRST_PULL_USD` default $100 first-pull), the real
query runs with `maximum_bytes_billed` as a hard server-side ceiling.
Completes in ~1-2 min and upserts `downloads_30d` + `downloads_90d`
into `pypi_intelligence` for the ~300k PyPI projects with any download
activity in the last 90 days. See `docs/specs/cfe-shipped-releases.md` Part 7
for the v8.15.0 incremental architecture that drives steady-state
cost below $1/run.

### Phase Q — Cross-channel presence (v8.1.0+)

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

### Phase R — Per-project JSON enrichment (v8.1.0+, opt-in)

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

### Phase S — Computed scores (v8.1.0+)

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

### Phase E — cf-graph enrichment

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
  - `packages.python_min` (**v8.19.0 Wave 3**, schema v28) — recipe-author
    override of the conda-forge-pinning default, regex-extracted from
    `raw_meta_yaml` (v1: `python_min: "3.11"` inside `context:`; v0:
    `{% set python_min = "3.11" %}`). NULL for recipes that inherit the
    pinning default (~91% of feedstocks per a 2026-06-13 survey of cached
    node_attrs). Single-writer contract: Phase E owns; Phase F never
    touches. Consumed by `pyver_breakdown --policy-check` to flag
    bump-safe candidates.
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

### Phase E.5 — Archived feedstocks

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

### Phase F — Download counts

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
  - `packages.{total_downloads, latest_version_downloads,
    downloads_fetched_at, downloads_source}`. `downloads_source ∈
    {'anaconda-api','s3-parquet','merged'}` — API and S3 totals do
    NOT agree numerically (S3 ~1.5× API on popular packages); treat
    as correlated, not interchangeable.
  - `packages.{downloads_30d, downloads_90d, downloads_trend_90d,
    first_nonzero_month, last_nonzero_month}` (**v8.18.0 — Wave 2,
    s3-parquet path only**). Rolling-window adoption signals + slope
    + lifetime months. NULL on `downloads_source='anaconda-api'`
    rows (consumer-detection contract — check provenance first).
    `downloads_trend_90d` capped at `+10.0`; NULL when <6 months
    of data or prev-90d window is zero (div-by-zero guard).
  - `package_platform_downloads` + `package_python_downloads`
    (**v8.18.0 — Wave 2 breakdown tables**). Per-`(conda_name,
    platform/python)` 90d + lifetime totals. Re-runs INSERT OR
    REPLACE keyed on PK. Empty `pkg_platform=''` (noarch) is
    remapped to synthetic `'noarch'`. Dirty `pkg_python` (e.g.
    `'7.3'`, `'2.30'`) dropped via regex
    `^(2\.7|3\.[0-9]{1,2})$`.
  - `package_channel_downloads` (**v8.19.0 — Wave 3 breakdown
    table**, schema v28). Per-`(conda_name, data_source)` 90d +
    lifetime totals captured from a SEPARATE parquet read that
    skips the Wave 2 `data_source='conda-forge'` filter so the
    channel cuts include `defaults` / `bioconda` / `pytorch` /
    `nvidia` / etc. Raw channel string written as-is (no
    normalization). DELETE-by-scope-key + INSERT OR REPLACE
    chunked (mirrors v8.18.0 H1 pattern). Consumed by
    `channel-split` CLI to surface migration opportunities.
  - `package_version_downloads` (Phase I side-effect, both paths).
- **Tunables.** `PHASE_F_SOURCE`, `PHASE_F_TTL_DAYS=7`,
  `PHASE_F_CONCURRENCY=3` (lowered 8→3 in v7.8.0 — see
  [`atlas-phase-engineering.md`](atlas-phase-engineering.md) for the
  Retry-After + jitter pattern), `PHASE_F_S3_MONTHS`, `S3_PARQUET_BASE_URL`,
  `ANACONDA_API_BASE_URL`.
- **Profile defaults (v8.17.0+).** Admin + consumer pin
  `PHASE_F_SOURCE=s3-parquet`. Maintainer uses `auto` (probe-then-fallback)
  because maintainer-scoped row sets are small (~dozens to hundreds of
  feedstocks) and the API path completes in seconds at that size.
  **Why admin flipped from `auto` to `s3-parquet` in v8.17.0** (verified
  2026-06-13): the API path is serial ~6 req/s × ~32k packages = ~83 min
  wall-clock for a full --fresh admin run; the S3 parquet bulk sweep
  covers the same row set in seconds. The numbers disagree by
  ~0.5–1.5× per the discrepancy table in
  `docs/specs/cfe-shipped-releases.md` Part 8 § "Verified discrepancies".
  **Consumer impact**: admin-profile `total_downloads` numbers shift to
  S3 totals; consumers querying `packages.total_downloads` for an
  admin-built DB MUST check `packages.downloads_source = 's3-parquet'`
  before treating them as API-equivalent. Operators wanting API
  numbers for admin runs can set `PHASE_F_SOURCE=auto` (or `=anaconda-api`)
  explicitly to override.
- **Actionable intelligence.**
  - `version-downloads`, `staleness-report`, `feedstock-health`,
    `adoption-stage` — every CLI that asks "is this used."
  - Bus-factor-1 detection: single-maintainer × high-downloads ×
    many-dependents.
  - Download-weighted maintainer leaderboard.
  - "Archived but actively used" (with E.5 + I).
  - ✅ shipped v8.18.0 (Wave 2 intake archived at `docs/specs/cfe-shipped-releases.md` Part 8):
    rolling 30/90-day windows, 90-day trend slope, first/last nonzero month,
    per-platform + per-Python breakdown tables. Computed in one extended
    parquet sweep — no extra HTTP. A v26 → v27 migration writes a
    one-shot `phase_f_force_refresh_pending` meta sentinel so the new
    columns populate from the cached parquet on first post-migration
    Phase F run (operator can also set `PHASE_F_FORCE_REFRESH=1`
    manually).
  - ✅ shipped v8.19.0 (Wave 3 intake archived at `docs/specs/cfe-shipped-releases.md` Part 8):
    `platform-breakdown`, `pyver-breakdown` (incl. `--policy-check` for
    python_min validation against the new `packages.python_min` column),
    `channel-split` (incl. `--migration-checklist` markdown emit) CLIs +
    MCP tools + pixi tasks. All three consume the Wave 2/3 breakdown
    tables (`package_platform_downloads`, `package_python_downloads`,
    `package_channel_downloads`) and `packages.python_min` (Phase E
    write). Schema migration v27 → v28 sets BOTH
    `phase_e_force_refresh_pending` AND `phase_f_force_refresh_pending`
    one-shot sentinels so the column + table populate on the next
    bootstrap-data run without waiting for natural TTL expiry.

### Phase G — vdb risk summary

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

### Phase G' — Per-version vuln scoring

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

### Phase H — PyPI current version

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

### Phase I — Per-version download history (side-table)

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

### Phase J — Dependency graph

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

### Phase K — VCS upstream versions

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
  `PHASE_K_CONCURRENCY=8` (REST fanout; only consulted under
  `PHASE_K_AGGRESSIVE=1`), `PHASE_K_GRAPHQL_DISABLED` (force REST),
  `PHASE_K_GRAPHQL_BATCH_SIZE=100` (keep <150 for the 500K node-
  complexity ceiling). **v8.20.0 sustained-rate scheduler**:
  `PHASE_K_REQUESTS_PER_SECOND=3.0` (REST fanout target; ~3× under
  GitHub's secondary-rate-limit threshold), `PHASE_K_AGGRESSIVE`
  (unset = use scheduler; `=1` to restore the previous 8-worker burst),
  `PHASE_K_DEBUG_SCHEDULER` (unset = silent after 30s; `=1` to keep
  timing logs streaming). Auto-skips without GitHub auth — 60 req/hr
  unauth is too low for backfill.
- **Cold wall-clock.** ~60-75 min full-channel under the default
  sustained-rate scheduler; ~30 min with `PHASE_K_AGGRESSIVE=1` at the
  cost of ~15% HTTP 403 churn (v8.5.x baseline, 2026-05-12 incident).
  Incremental TTL-skip runs (<100 new rows) finish in roughly the same
  wall-clock either way — burst pattern never triggers at that scale.
- **Actionable intelligence.**
  - `behind-upstream --maintainer X` adds a SOURCE column distinguishing
    `pypi` vs `github`/`gitlab`/`codeberg` so VCS-source recipes are no
    longer invisible.
  - ✅ Resolved in v8.20.0: secondary-rate-limit 403 churn on full-
    channel REST fanouts (15% → <1% target via sustained-rate scheduler).
  - 📋 Open: full-channel backfill (currently per-maintainer scope);
    `bot-pr-context` composite with H + J.

### Phase L — Extra registries

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

### Phase M — Feedstock health

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

### Phase N — Live GitHub

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

## How to extend this document

When adding a new phase, CLI, or actionable signal:

1. **Part A** — add a row in the appropriate persona section; tie it to the phase letter
   and the specific column / table / CLI. If the item promotes an existing 📋 → ✅, flip
   the status in place (preserves history) and update the Status Summary count. The flip
   is part of the release work — the same edit as the CHANGELOG entry.
2. **Part B** — add or update the at-a-glance row + the per-phase section with the four
   required fields (data source, purpose, what gets written, actionable intelligence).
3. Bump the skill `CHANGELOG.md` per semver — MINOR for new phases or intel additions,
   PATCH for clarifications.
4. Cross-link, don't duplicate: cadence / TTL reset / recovery →
   [`../guides/atlas-operations.md`](../guides/atlas-operations.md); rate limits, GraphQL
   batching, Retry-After + jitter, atomic writes, enterprise routing, volume-billed-API
   cost caps → [`atlas-phase-engineering.md`](atlas-phase-engineering.md).

The atlas docs form a triangle (consolidated 2026-07-02 from five files):

```
            atlas-phases-overview.md  (this file)
        Part A: WHO uses WHAT · Part B: WHAT each phase does
                    /                        \
  atlas-phase-engineering.md          ../guides/atlas-operations.md
  (HOW phases compute it, incl.       (HOW to run it: profiles,
   the Phase P cost model)             cadence, cron, recovery)
```

Together they answer: *what intelligence does the atlas surface, where in the pipeline
does it come from, how is it engineered, and how do I operate it?*

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
| **Phase F — download counts** | auto-source (probe API → S3 fallback) | pinned `s3-parquet` (v8.17.0+ — was `auto`) | pinned `s3-parquet` |
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

### Wrapper false-negative — fixed structurally in v8.22.0

Through v8.16.5 the `bootstrap-data` orchestrator ran the entire
cf_atlas build as one `cf-atlas-build` subprocess under a single
14,400 s wrapper timeout. When the wrapper hit the deadline before the
underlying Python subprocess returned, the bootstrap printed `✗ cf-
atlas-build` while the subprocess continued running to clean exit —
operators relying on the wrapper exit code saw a false negative.
v8.16.6 mitigated the symptom by raising the timeout; v8.22.0 lands
the structural fix.

**The split.** `bootstrap-data` now invokes the cf_atlas pipeline as
**four independently-reported sub-steps**, each with its own timeout
+ ✓/✗ line:

| Sub-step         | Phases run                                     | Default timeout (env override)         | Failure semantics |
|------------------|------------------------------------------------|----------------------------------------|-------------------|
| `cf-atlas-core`  | All EXCEPT F/K/N (B/B.5/B.6/C/C.5/D/O/P/Q/R/S/E/E.5/G/G'/H/J/L/M) | 1,800 s (`BOOTSTRAP_CF_ATLAS_CORE_TIMEOUT`) | HARD — aborts the bootstrap |
| `cf-atlas-F`     | Phase F only (anaconda.org downloads)          | 7,200 s (`BOOTSTRAP_CF_ATLAS_F_TIMEOUT`)    | SOFT — continue |
| `cf-atlas-K`     | Phase K only (VCS upstream fanout)             | 7,200 s (`BOOTSTRAP_CF_ATLAS_K_TIMEOUT`)    | SOFT — continue |
| `cf-atlas-N`     | Phase N only (live GitHub); runs when admin profile is active OR `--gh` is set | 3,600 s (`BOOTSTRAP_CF_ATLAS_N_TIMEOUT`)    | SOFT — continue |

The bootstrap summary aggregates the four sub-step outcomes into a
single `cf-atlas-build` line — `✓` when all four succeeded, `⚠` when
core succeeded but at least one of F/K/N returned non-zero, `✗` when
core failed. The aggregate `⚠` is NOT counted toward the bootstrap
exit code (operators told the bootstrap to continue past soft
failures; the sub-step `✗` already surfaces what went wrong).

**Routing.** Each sub-step shells out to
`pixi run -e local-recipes build-cf-atlas -- --only PHASE_LIST` (or
`--skip F,K,N` for core). The `--skip` / `--only` flags landed on
`conda_forge_atlas.py build` in v8.22.0 specifically to make the
split atomic — they're mutually exclusive and case-insensitive.

**Legacy escape hatch.** Setting `BOOTSTRAP_CF_ATLAS_TIMEOUT`
explicitly RESTORES the v8.16.6 single-subprocess invocation. Useful
when an operator wants pre-v8.22.0 behavior (one timeout, one ✓/✗
line) or when the split surfaces an unexpected interaction. Operators
who never set `BOOTSTRAP_CF_ATLAS_TIMEOUT` get the new behavior by
default.
