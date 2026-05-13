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
| Which of my feedstocks have open *human* PRs? | `gh-pulls --maintainer X` (planned) | Phase N — GitHub Pulls API | List of human PRs with age, status | 📋 open (Phase N) |
| Which of my feedstocks have open issues? | `gh-issues --maintainer X` (planned) | Phase N — GitHub Issues API | Open issue count + most-recent issue title | 📋 open (Phase N) |
| Which of my feedstocks have CI red on default branch? | `feedstock-health --maintainer X --filter ci-red` (planned) | Phase N — GitHub Checks API | List of feedstocks with failing main-branch CI | 📋 open (Phase N) |
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
| Find abandoned feedstocks (no maintainer activity + no upstream activity) | Composite: maintainer GitHub-last-active + feedstock last-commit | Phase N (GH user activity + repo last-commit) + maintainer junction | List for mass-archive or take-over | 📋 open (Phase N) |
| Bus-factor=1 critical infrastructure | Single-maintainer rows with high downloads + many dependents | Phase F + Phase J + maintainer junction | Recruit help / set up co-maintainership | ✅ shipped (SQL) |
| Orphans needing new maintainers | Feedstocks where ALL maintainers ignored bot PRs > 6mo | Phase M + Phase N | Take-over candidates | 📋 open (needs Phase N for human PR response data) |
| Feedstocks marked archived but actively used | `feedstock_archived=1` joined to recent downloads | Phase E.5 + Phase F + Phase I | Find should-not-have-archived cases | ✅ shipped (SQL) |

### Maintainer Distribution

| Goal | Action | Data source | Outcome | Status |
|---|---|---|---|---|
| Top maintainers by feedstock count | Aggregate `package_maintainers` by handle | Phase E maintainer junction | Identify overloaded maintainers | ✅ shipped (SQL) |
| Download-weighted maintainer leaderboard | Same join + downloads sum | Phase F + maintainer junction | Reach-weighted "most-impactful maintainer" list | ✅ shipped (SQL) |
| Maintainer last-active across the channel | GitHub user-activity API | Phase N | Identify dormant maintainers | 📋 open (Phase N) |

### Security & Compliance

| Goal | Action | Data source | Outcome | Status |
|---|---|---|---|---|
| Channel-wide CVE summary by severity | Aggregate `vuln_*_affecting_current` | Phase G | Severity-banded counts | ✅ shipped (SQL); 📋 dashboard open |
| CVE cascade alert: when CVE-X published, find affected feedstocks | Phase G + Phase J join | Phase G + Phase J | Notification list of feedstocks to repin / rebuild | 📋 open (notification daemon) |
| KEV-list (CISA Known Exploited Vulnerabilities) coverage | `vuln_kev_affecting_current` aggregate | Phase G | High-priority remediation queue | ✅ shipped (SQL) |
| License audit (unusual / unknown / proprietary) | Aggregate `conda_license` | Phase B | Legal review queue | ✅ shipped (SQL); 📋 dashboard open |
| License compatibility check for downstream projects | Match license against compatibility matrix | Phase B + static matrix | "Yes/no compatible with target license" + offending deps | 📋 open |

### Cross-Channel Coordination

| Goal | Action | Data source | Outcome | Status |
|---|---|---|---|---|
| Find packages also on bioconda / nvidia / pytorch channels | `inventory-channel` against the other channel | `inventory_channel.py` (existing) | Coordination opportunities | ✅ shipped (separate tool) |
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
| Bus-factor my dependencies | `bus-factor-my-env pixi.lock` (planned) — match manifest names to atlas, get maintainer counts | `scan_project.py` parser + maintainer junction | Single-points-of-failure list | 📋 open |
| License compatibility for my project | `scan-project --license-check --target Apache-2.0` (planned) | `scan_project.py` + license matrix | Yes/no with offending deps | 📋 open |
| SBOM (CycloneDX/SPDX) | `scan-project --sbom cyclonedx` | `scan_project.py` (existing) | Standard SBOM | ✅ shipped |
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
| Air-gap Phase F via public S3 parquet | `PHASE_F_SOURCE=s3-parquet` reads `anaconda-package-data.s3.amazonaws.com`; `S3_PARQUET_BASE_URL` redirects to JFrog mirror | Phase F (v7.6+) | Atlas builds cleanly with `*.anaconda.org` blocked; downloads still populate | ✅ shipped (v7.6.0) |
| Phase F+ richer metrics (rolling 30/90-day, trend slope, platform/python breakdowns) | Same parquet sweep, additional group-bys; new aggregate tables | Phase F+ (planned) | Per-platform/python download distribution; activity-trend signals | 📋 open (Wave 2 in `docs/specs/atlas-phase-f-s3-backend.md`) |
| Platform-/python-/channel-aware ranking CLIs | `platform_breakdown`, `pyver_breakdown` (incl. `--policy-check` for python_min validation), `channel_split` | Phase F+ aggregate tables (planned) | Maintainer-triage tools that surface ARM/win/py-EOL share | 📋 open (Wave 3 in `docs/specs/atlas-phase-f-s3-backend.md`) |

---

## Status Summary (at v7.6.0)

| Status | Count | Notes |
|---|---|---|
| ✅ Shipped | ~60 | All 15 pipeline phases (B/B.5/B.6/C/C.5/D/E/E.5/F/G/G'/H/I/J/K/L/M/N); 17 CLIs; full multi-registry coverage (PyPI/GitHub/GitLab/Codeberg/npm/CRAN/CPAN/LuaRocks/crates/RubyGems/NuGet/Maven — including Phase E auto-detection of Maven coordinates from cf-graph URLs); SBOM input/output across CycloneDX 1.4-1.6 (JSON+XML), SPDX 2.x JSON+tag-value+3.0, syft/trivy native; **SBOM relationship traversal rendered as a tree**; container image + OCI manifest probe + live env + GitOps (Argo/Flux with auto git-clone fallback) + K8s scanning; license-check + find-alternative + adoption-stage + SBOM atlas-vuln enrichment; **PyPI yanked-flag detection (PEP 592)**; **12 MCP tools** wrapping the entire read-side surface; **`bootstrap-data` single-command refresh with `--fresh` hard reset** |
| 📋 Open | ~5 | Channel-wide Phase H/N cron operationalization (per-maintainer scope shipped; full-channel needs PAT rotation or daily 30-min run); per-version vdb-history snapshot side table for time-travel queries; multi-output feedstock per-output dep-graph (Phase J extension — currently captures top-level only); `recipe_format='unknown'` heuristic refinement (116 outliers); CycloneDX Protobuf / SPDX RDF (deferred — heavy deps, marginal use) |
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
