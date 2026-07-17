# Full Phase Reference — all 23 cataloged phases

All citations at grounding commit `b18cbb5` (2026-07-17, CFE skill pin v8.78.0, schema v29).
`CFA` = `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py`.
Registry: `PHASES: list[tuple[str, Any]]` [SRC:CFA:L8679], tuples L8680–8701, closing `]` L8702.
Helpers: `get_phase` [SRC:CFA:L8705], `run_single_phase` [SRC:CFA:L8716], `_parse_phase_list` [SRC:CFA:L8730].
Spec phase-catalog paragraph: spec:139–153 (`docs/specs/cfe-atlas-datapipeline-kedro-migration.md`).
Secondary prose per phase: `reference/atlas-phases-overview.md` Part B (heading lines in parentheses below as "ov:").

## Contents

- [Registered phases (22)](#registered-phases-22)
- [Phase I — unregistered](#phase-i--unregistered)
- [Conditional Phase T](#conditional-phase-t)

## Registered phases (22)

| Phase | Registry tuple | def | Docstring purpose (first line) | Overview heading |
|---|---|---|---|---|
| B | L8680 | L1408 | "Phase B: enumerate conda-forge packages via per-subdir current_repodata.json." (L1409) | ov:276 |
| B.5 | L8681 | L1593 | "Phase B.5: download feedstock-outputs archive; populate feedstock_name." (L1594) | ov:300 |
| B.6 | L8682 | L1665 | "Phase B.6: assign latest_status based on current_repodata presence." (L1666) — deliberately LITE yanked detection (spec:157–159) | ov:327 |
| C | L8683 | L1744 | "Phase C: join via parselmouth's PyPI-conda mapping (verified matches)." (L1745) | ov:341 |
| C.5 | L8684 | L1802 | "Phase C.5 — deferred. Recipe source.url match requires cf-graph data fetched in Phase E. Implemented inline within Phase E." (L1803–1805) | ov:360 |
| D | L8685 | L1947 | "Phase D: enumerate PyPI universe via Simple API v1 (schema v20+)." (L1948); TTL example 7 d (spec:241) | ov:374 |
| O | L8686 | L7051 | "Phase O: snapshot pypi_universe.last_serial daily; compute activity bands." (L7052) | ov:405 |
| P | L8687 | L7352 | "Phase P dispatcher — routes to ClickHouse (free, default) or BigQuery." (L7353); `_phase_p_bigquery` L7562, `_phase_p_clickhouse` L7399, `_phase_p_skip` L7342; credentialed (BigQuery ADC), opt-in `PHASE_P_ENABLED=1`, admin profile only (spec:148–151) | ov:440 |
| Q | L8688 | L7847 | "Phase Q: populate pypi_intelligence.in_channel BOOLs from bulk fetches of non-conda-forge channels." (L7848–7849) | ov:560 |
| R | L8689 | L8330 | "Phase R: per-project JSON enrichment for the top-N candidate slice." (L8331); cold-run ~15 min for first 5,000-candidate pull (spec:314) | ov:588 |
| S | L8690 | L8546 | "Phase S: compute conda_forge_readiness + recommended_template." (L8547); `pypi_intelligence.notes` operator overrides survive re-runs (spec:280–281) | ov:629 |
| E | L8691 | L2188 | "Phase E: per-package enrichment via cf-graph-countyfair node_attrs." (L2189); maintainer-universe delta ~44 vs cf-graph must be reconciled or documented (spec:287–292) | ov:665 |
| E.5 | L8692 | L2504 | "Phase E.5: GraphQL query for archived feedstocks in conda-forge org." (L2505); GitHub token (spec:151) | ov:708 |
| F | L8693 | L3560 | "Phase F: per-package download counts." (L3561); TTL `downloads_fetched_at`; provenance discipline — see engineering-contracts.md | ov:725 |
| G | L8694 | L3771 | "Phase G: cache vdb risk summary into the packages table." (L3772); vuln-db env credentialed; KEV/EPSS/CWE overlays L3854–3856 | ov:815 |
| G' | L8695 | L6808 | "Phase G' — per-version vuln scoring." (L6809); TTL via package_version_vulns row-absence (atlas_phase.py L47); fed by Phase I (L6861) | ov:845 |
| H | L8696 | L4517 | "Phase H: cache each pypi-linked package's current upstream version." (L4518); serial gate `_phase_h_eligible_pypi_names` L4174 | ov:863 |
| J | L8697 | L6067 | "Phase J: parse cf-graph requirements into the dependencies table." (L6068) | ov:934 |
| K | L8698 | L5039 | "Phase K: fetch latest release/tag from VCS hosts (GitHub, GitLab, Codeberg)…" (L5040–5042); GitHub token; 3 RPS token bucket | ov:966 |
| L | L8699 | L5841 | "Phase L: resolve the latest upstream version from npm / CRAN / CPAN / LuaRocks / crates.io / RubyGems / NuGet…" (L5842–5844); per-source TTL (atlas_phase.py L50) | ov:1010 |
| M | L8700 | L6263 | "Phase M: parse cf-graph pr_info and version_pr_info side files into health columns on packages…" (L6264–6266) | ov:1048 |
| N | L8701 | L6525 | "Phase N: live GitHub data per feedstock — CI status on default branch, open issue + PR counts, pushedAt timestamp." (L6526–6527); GitHub token | ov:1077 |

TTL-gated set (spec:152–153 + atlas_phase.py L44–50): **F, G, G', H, K, L**.
Credentialed set (spec:148–152): **P** (BigQuery ADC), **G/G'** (vuln-db environment), **E.5/K/N** (GitHub token).

## Phase I — unregistered

- NOT in `PHASES` (no `("I", …)` tuple in L8679–8702; no `def phase_i` in the file) — invisible to `--skip`/`--only` (spec:117).
- Data: `package_version_downloads` table [SRC:CFA:L316], PK `(conda_name, version)` L324, indexes L326–327; schema comment "written by Phase F as a side effect" L312–315.
- Write sites: anaconda-api path `INSERT OR REPLACE` inside `_phase_f_via_api` (def L2836) at [SRC:CFA:L2931]; s3-parquet path `INSERT` inside `_phase_f_via_s3` (def L3009) at [SRC:CFA:L3402].
- Consumers: Phase G' iterates it (L6812 comment, query `FROM package_version_downloads pvd` L6861); `version-downloads` and `release-cadence` CLIs (spec:143–148).
- v17→v18 migration added a `source` discriminator column [SRC:CFA:L958–969].
- Migration contract: promoted to an explicit node (spec:147–148, spec:762).

## Conditional Phase T

Phase T (`phase_t_github_trending`, schema v29→v30, `github_trending_repos` +
`trending_classification`, `v_trending_candidates`) enters the legacy surface only if
trendshift Track A ships before Wave B completes (spec:293–302). **Re-checked
2026-07-17 at commit b18cbb5: NOT shipped** — the only "Phase T" strings in
`conda_forge_atlas.py` are the *cancelled blint Wave C* notes (L726, L923, L1060);
no v30 tables exist. Not modeled beyond this statement.
