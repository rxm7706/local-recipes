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
# Nuke everything and rebuild
pixi run -e local-recipes bootstrap-data --fresh

# Keep vdb but rebuild atlas
rm .claude/data/conda-forge-expert/cf_atlas.db
pixi run -e local-recipes build-cf-atlas
PHASE_E_ENABLED=1 pixi run -e local-recipes build-cf-atlas

# Force-refresh one specific package (e.g., to test Phase H)
pixi run -e local-recipes python -c "
import sqlite3
conn = sqlite3.connect('.claude/data/conda-forge-expert/cf_atlas.db')
conn.execute('UPDATE packages SET pypi_version_fetched_at=NULL WHERE conda_name=?', ('mypkg',))
conn.commit()
"
PHASE_H_LIMIT=5 pixi run -e local-recipes python -c "
import sys; sys.path.insert(0, '.claude/skills/conda-forge-expert/scripts')
from conda_forge_atlas import open_db, init_schema, phase_h_pypi_versions
conn = open_db(); init_schema(conn); phase_h_pypi_versions(conn)
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
