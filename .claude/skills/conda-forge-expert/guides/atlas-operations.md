# Atlas Operations Guide

Operational guide for keeping `cf_atlas.db` and the vulnerability index
fresh. Covers cron schedules, full backfill strategies, and recovery.

This is the doc that closes the "Phase H/N full conda-forge-wide
backfill cron operationalization" follow-up from earlier releases.

---

## Single-command refresh

The fastest way to bring all data current:

```bash
# Default — refreshes mapping cache + CVE DB + vdb + cf_atlas (Phases B/B.5/B.6/C/C.5/D/E/E.5/F/G/H/J/K/L/M).
pixi run -e local-recipes bootstrap-data

# Hard reset — wipe `.claude/data/conda-forge-expert/` first
pixi run -e local-recipes bootstrap-data --fresh

# Skip the heavy 2.5 GB vdb refresh
pixi run -e local-recipes bootstrap-data --no-vdb

# Add live GitHub data (Phase N) — needs `gh auth login` first
pixi run -e local-recipes bootstrap-data --gh --maintainer <handle>

# Add per-version vuln scoring (Phase G') — needs the vuln-db env
pixi run -e local-recipes bootstrap-data --with-per-version-vulns

# See what would happen without executing
pixi run -e local-recipes bootstrap-data --dry-run
```

Cold-start total: roughly 30–45 minutes on residential bandwidth (2.5 GB
vdb is the dominant cost; the rest is < 5 minutes combined).

---

## Cron schedules — recommended cadence per data source

Most data has natural refresh cadences. The TTL guards in each phase
handle warm reuse, so frequent crons are cheap once the cold backfill
has run.

| Source | Cadence | Cost | What's stale if you skip |
|---|---|---|---|
| `bootstrap-data` (everything) | weekly | ~30 min | Complete refresh |
| Phase F (anaconda.org downloads) | daily | ~5 min warm (TTL=7d) | Download counts |
| Phase H (PyPI versions, with yanked) | daily | ~5 min warm (TTL=7d) | "behind upstream" detection |
| Phase G (vdb risk summary) | daily after `vdb-refresh` | ~30 s | CVE counts |
| Phase G' (per-version vulns) | weekly | ~5 min warm (TTL=30d) | Historical version vuln records |
| Phase E + Phase J + Phase M (cf-graph cached pull) | every 6h | ~1 min (cached tarball) | Dep graph + bot status drift |
| Phase E.5 (archived feedstocks via GraphQL) | daily | ~10 s | New archives |
| Phase K (VCS upstream — GitHub/GitLab/Codeberg) | daily | per-row TTL=7d | "behind upstream" for VCS-source recipes |
| Phase L (npm/CRAN/CPAN/LuaRocks/crates/RubyGems/NuGet/Maven) | daily | per-row TTL=7d | Same |
| Phase N (live GitHub: CI / issues / PRs) | hourly **per maintainer** | ~30 s for 700 feedstocks | Real-time issue + PR counts |
| `vdb-refresh` (vdb itself) | weekly | ~5–10 min | New CVEs missed |
| `update-cve-db` (legacy OSV) | weekly | ~1 min | Used only by `scan_for_vulnerabilities` MCP tool |
| `update-mapping-cache` (parselmouth) | weekly | ~10 s | New PyPI↔conda renames |

### Sample crontab

```cron
# Hourly: live GitHub data for one maintainer (cheap, scoped)
0 * * * *  cd /path/to/repo && \
    PHASE_N_ENABLED=1 PHASE_N_MAINTAINER=rxm7706 \
    pixi run -e local-recipes build-cf-atlas >> ~/.cache/cf-atlas.log 2>&1

# Daily 03:00: download counts (Phase F) + PyPI versions (Phase H) + VCS upstream (Phase K)
0 3 * * *  cd /path/to/repo && \
    pixi run -e local-recipes build-cf-atlas >> ~/.cache/cf-atlas.log 2>&1

# Daily 04:00: vdb risk summary (Phase G — needs vuln-db env)
0 4 * * *  cd /path/to/repo && \
    pixi run -e vuln-db build-cf-atlas >> ~/.cache/cf-atlas.log 2>&1

# Weekly Sunday 02:00: vdb-refresh (heavy) + cf_atlas full bootstrap
0 2 * * 0  cd /path/to/repo && \
    pixi run -e local-recipes bootstrap-data >> ~/.cache/cf-atlas.log 2>&1
```

### Channel-wide vs per-maintainer

Phase H + Phase N are tractable at per-maintainer scope (a few hundred
feedstocks). Channel-wide scope is ~32k feedstocks — Phase H takes 30+
min, Phase N takes hours due to GitHub GraphQL rate limits. For
channel-wide intelligence, prefer:

- **Phase H channel-wide**: split across multiple cron windows (e.g.,
  fetch 1k rows per hour), or accept the 30-min run as a daily cost.
- **Phase N channel-wide**: only feasible with multiple GitHub PATs in
  rotation OR an enterprise GitHub tier. Per-maintainer scope is the
  recommended default.

---

## Hard reset / recovery

If the atlas gets corrupted (rare — most failures are gracefully
recoverable via TTL re-fetch):

```bash
# Nuke everything and rebuild (preserves cache/parquet by default since v7.7)
pixi run -e local-recipes bootstrap-data --fresh

# Keep vdb but rebuild atlas
rm .claude/data/conda-forge-expert/cf_atlas.db
pixi run -e local-recipes build-cf-atlas
PHASE_E_ENABLED=1 pixi run -e local-recipes build-cf-atlas
```

### Recovery playbook — when phase X fails, do Y

Every TTL-gated phase (F, G, G', H, K, L) has the same recovery shape:
re-running picks up where it stopped because the per-row `*_fetched_at`
timestamp gates the SELECT. The table below summarizes what to do when
a phase fails, hangs, or finishes with errors logged in `packages.*_last_error`.

| Phase | Symptom | Recovery |
|---|---|---|
| **B** (conda enumeration) | Crash / partial DB | `rm cf_atlas.db && build-cf-atlas` (B is single-transaction; rerun rebuilds in ~2 min) |
| **B.5** (feedstock outputs) | Crash | Rerun `build-cf-atlas` — the tarball download is cached and the parse is idempotent |
| **C / C.5** (parselmouth / source-URL match) | Wrong PyPI mapping | Force refresh via `update-mapping-cache` then rerun `atlas-phase C` |
| **D** (PyPI enumeration) | Crash mid-run | Rerun `build-cf-atlas`; D's UPSERTs converge |
| **E** (cf-graph) | Corrupted tarball | `rm cf-graph-countyfair.tar.gz` then `PHASE_E_ENABLED=1 atlas-phase E` |
| **E.5** (archived feedstocks) | GraphQL 502 | `atlas-phase E.5` retries cleanly |
| **F** (downloads) | api.anaconda.org blocked / slow | `PHASE_F_SOURCE=s3-parquet atlas-phase F` (v7.6+ S3 backend) |
| **F** (downloads) | Some rows have `downloads_last_error` | `atlas-phase F --reset-ttl` to retry all rows in one pass, or NULL just the failures (recipe below) |
| **G** (vdb summary) | vdb env not active | Run from `vuln-db` env: `pixi run -e vuln-db build-cf-atlas` |
| **G'** (per-version vulns) | Crash / partial | Rerun in `vuln-db` env with `PHASE_GP_ENABLED=1` — TTL 30d, per-row resume |
| **H** (PyPI versions) | Hangs on pypi.org | `PHASE_H_SOURCE=cf-graph atlas-phase H` (v7.7+ offline path) |
| **H** (PyPI versions) | Need yanked status after cf-graph run | Reset cf-graph rows, then `PHASE_H_SOURCE=pypi-json atlas-phase H` (recipe below) |
| **J** (dependency graph) | cf-graph not present | Run Phase E first |
| **K** (VCS upstream) | GitHub rate limit (403) | Wait an hour or set `GITHUB_TOKEN`; rerun `atlas-phase K` |
| **L** (extra registries) | One registry source 5xx'ing | `atlas-phase L` — TTL-gated per source, only failed rows re-fetch |
| **M** (feedstock health) | cf-graph not present | Run Phase E first |
| **N** (live GitHub) | Killed mid-run | Rerun `build-cf-atlas` with `PHASE_N_ENABLED=1`; v7.7+ resumes from the last completed feedstock via `phase_state.last_completed_cursor` |
| **N** (live GitHub) | `gh auth` missing | `gh auth login` then rerun |
| **DB corrupted** | `database disk image is malformed` | `bootstrap-data --fresh --yes` (preserves S3 parquet cache by default) |

### TTL reset recipes

Force a specific row to re-fetch on the next phase run (skip the TTL gate
for one package):

```bash
# Example: force Phase H to re-fetch numpy on the next run
pixi run -e local-recipes python -c "
import sqlite3
conn = sqlite3.connect('.claude/data/conda-forge-expert/cf_atlas.db')
conn.execute('UPDATE packages SET pypi_version_fetched_at=NULL WHERE conda_name=?', ('numpy',))
conn.commit()
"
pixi run -e local-recipes atlas-phase H
```

Force a specific phase to re-process *every* eligible row (drop the
entire TTL gate for that phase):

```bash
# Single command — atlas-phase has built-in --reset-ttl
pixi run -e local-recipes atlas-phase H --reset-ttl
```

Backfill PEP 592 yanked status after a cf-graph cold start:

```bash
# Reset just the cf-graph-tagged rows so pypi-json can repopulate yanked
pixi run -e local-recipes python -c "
import sqlite3
conn = sqlite3.connect('.claude/data/conda-forge-expert/cf_atlas.db')
conn.execute(\"UPDATE packages SET pypi_version_fetched_at=NULL \"
             \"WHERE pypi_version_source = 'cf-graph'\")
conn.commit()
print(f'reset rows: {conn.total_changes}')
"
PHASE_H_SOURCE=pypi-json pixi run -e local-recipes atlas-phase H
```

Retry just the rows that errored in the last run:

```bash
# Phase F example — same pattern works for any phase with a *_last_error column
pixi run -e local-recipes python -c "
import sqlite3
conn = sqlite3.connect('.claude/data/conda-forge-expert/cf_atlas.db')
conn.execute('UPDATE packages SET downloads_fetched_at=NULL '
             'WHERE downloads_last_error IS NOT NULL')
conn.commit()
print(f'reset rows: {conn.total_changes}')
"
pixi run -e local-recipes atlas-phase F
```

### Phase N resume

Phase N (the only phase with a true checkpoint as of v7.7) writes its
progress to the `phase_state` table after every batch. To check resume
state without running anything:

```bash
pixi run -e local-recipes python -c "
import sqlite3
conn = sqlite3.connect('.claude/data/conda-forge-expert/cf_atlas.db')
conn.row_factory = sqlite3.Row
for r in conn.execute('SELECT * FROM phase_state'):
    print(dict(r))
"
```

To force a fresh Phase N run (ignore checkpoint), mark the prior
checkpoint completed:

```bash
pixi run -e local-recipes python -c "
import sqlite3, time
conn = sqlite3.connect('.claude/data/conda-forge-expert/cf_atlas.db')
conn.execute(\"UPDATE phase_state SET status='completed', \"
             \"run_completed_at=? WHERE phase_name='N'\", (int(time.time()),))
conn.commit()
"
```

---

## Air-gapped operations

In offline / air-gapped environments:

1. Run `bootstrap-data` on a connected machine.
2. Copy `.claude/data/conda-forge-expert/` to the air-gapped machine.
3. All atlas read-side CLIs work without network access.
4. Phase F / Phase G fresh fetches need the vuln-db env on a connected box;
   the *cached counts* in `cf_atlas.db` work everywhere.
5. The `--enrich-vulns-from-atlas` flag on `scan-project --sbom` reads
   from the cached counts — produces SBOMs with vuln annotations even
   when offline.

For corporate enterprise routing (JFrog Artifactory etc.), set the env
vars described in `quickref/commands-cheatsheet.md` § "Enterprise routing"
before running `bootstrap-data`.

### Phase F behind `*.anaconda.org` firewall (v7.6+)

`api.anaconda.org` was historically Phase F's only hard dependency. As of
v7.6.0, Phase F has an `s3-parquet` backend that reads
`anaconda-package-data.s3.amazonaws.com` directly (same dataset as
`condastats`, served from AWS, no `*.anaconda.org` access required).

```bash
# Default: auto-probe api.anaconda.org once, fall through to S3 on failure
pixi run -e local-recipes build-cf-atlas

# Force S3 (skip the probe — useful behind a strict firewall)
PHASE_F_SOURCE=s3-parquet pixi run -e local-recipes build-cf-atlas

# Reduced footprint: trailing 24 months instead of full 9+ years
PHASE_F_S3_MONTHS=24 PHASE_F_SOURCE=s3-parquet pixi run -e local-recipes build-cf-atlas

# JFrog mirror of the bucket (parquet files served from your Artifactory)
export S3_PARQUET_BASE_URL=https://artifactory.example.com/artifactory/anaconda-package-data
PHASE_F_SOURCE=s3-parquet pixi run -e local-recipes build-cf-atlas
```

Every populated `packages` row carries a `downloads_source` discriminator
(`'anaconda-api'` | `'s3-parquet'` | `'merged'`). API and S3 totals do
NOT agree numerically — treat them as correlated-but-distinct metrics,
not interchangeable. The ordering (which packages are most-downloaded)
agrees; absolute numbers diverge (e.g. `requests` lifetime is 1.50× higher
on S3 than via API).

**Cache:** `.claude/data/conda-forge-expert/cache/parquet/` (~13 MB per
month, ~1.4 GB for all months). Current-month file is always re-fetched;
older months are cached indefinitely. Set `S3_PARQUET_BASE_URL` to point
at a JFrog mirror that serves the same `conda/monthly/<YYYY>/<YYYY-MM>.parquet`
layout.

**JFROG_API_KEY scope warning:** if you set `JFROG_API_KEY` without also
setting `S3_PARQUET_BASE_URL`, the key currently leaks to public AWS S3
(see SKILL.md § "`_http.py` Cross-Resolver Credential Leak"). Work
around by exporting the key in a sub-shell, or by always pairing it
with the corresponding `*_BASE_URL`.

### Phase H cold-start via cf-graph (v7.7+)

Phase H normally fetches `pypi.org/pypi/<name>/json` per package — ~25k
requests, ~30 minutes wall clock on a cold DB, and the most common
source of "the pipeline is hanging" reports. As of v7.7.0, Phase H has
a `cf-graph` backend that reuses the tarball Phase E already cached
locally; the read is offline and finishes in ~30 seconds.

```bash
# Default cold-start: bootstrap-data --fresh auto-picks cf-graph for Phase H
pixi run -e local-recipes bootstrap-data --fresh

# Force cf-graph on a warm run (e.g. behind a pypi.org firewall)
PHASE_H_SOURCE=cf-graph pixi run -e local-recipes build-cf-atlas

# Force pypi-json (real-time, carries PEP 592 yanked)
PHASE_H_SOURCE=pypi-json pixi run -e local-recipes build-cf-atlas

# bootstrap-data: explicit override (default 'auto' = cf-graph on --fresh)
pixi run -e local-recipes bootstrap-data --phase-h-source pypi-json
```

Every populated `packages` row carries a `pypi_version_source`
discriminator (`'pypi-json'` | `'cf-graph'`). Consumers needing strict
yanked status should filter to `pypi_version_source = 'pypi-json'` or
re-run Phase H with `PHASE_H_SOURCE=pypi-json` to backfill — the TTL
gate ensures only un-pypi-json'd rows are re-fetched.

**Trade-offs:**

| Source | Latency | Yanked? | Network | Lag |
|---|---|---|---|---|
| `pypi-json` | ~30 min cold, ~5 min warm | ✅ PEP 592 | pypi.org | real-time |
| `cf-graph` | ~30 sec | ❌ NULL | none (offline) | hours-to-days (bot polling) |

### Per-row resume for Phase H

Phase H is TTL-gated like Phase F. To force a re-fetch of specific rows
without lowering the global TTL, NULL their `pypi_version_fetched_at`:

```bash
pixi run -e local-recipes python -c "
import sqlite3
conn = sqlite3.connect('.claude/data/conda-forge-expert/cf_atlas.db')
conn.execute(\"UPDATE packages SET pypi_version_fetched_at=NULL \"
             \"WHERE pypi_version_source = 'cf-graph'\")
conn.commit()
print(f'reset rows: {conn.total_changes}')
"
# Now backfill yanked precisely:
PHASE_H_SOURCE=pypi-json pixi run -e local-recipes build-cf-atlas
```

---

## Storage budget

After full bootstrap:

- `cf_atlas.db`: ~200 MB
- `cf-graph-countyfair.tar.gz`: ~150 MB cached
- `vdb/`: ~2.5 GB (apsw multi-source vuln index)
- `cve/`: ~50 MB (legacy OSV)
- Other caches: <50 MB

Total: ~3 GB. The `vdb/` dir is the dominant cost; pass `--no-vdb` to
`bootstrap-data` if your workflow only needs cached vuln counts (Phase G
already wrote them; `scan-project --sbom --enrich-vulns-from-atlas`
works without vdb).
