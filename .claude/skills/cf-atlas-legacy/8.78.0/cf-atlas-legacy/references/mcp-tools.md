# Full MCP Tool Surface — conda_forge_server.py

`MCP` = `/home/user/local-recipes/.claude/tools/conda_forge_server.py` (2,266 lines).
46 `@mcp.tool()` functions total; **23 atlas-relevant** (spec:172–177 expects exactly
this split). Verified at commit `b18cbb5`; lines below are `decorator:def`.
`library-futures`, `add-handoff`, and the 4 seed-gap suggesters are deliberately
CLI/pixi-only — "do not add MCP tools for them during the port" (spec:174–176).
Second unregistered server `gemini_server.py` is outside FR-7's audit scope
(spec:176–177) — not modeled.

## Contents

- [Atlas-relevant tools (23)](#atlas-relevant-tools-23)
- [Recipe-authoring / non-atlas tools (23)](#recipe-authoring--non-atlas-tools-23)

## Atlas-relevant tools (23)

| # | Tool | decorator:def |
|---|------|----------------|
| 1 | `staleness_report` | [SRC:MCP:L1461]:1462 |
| 2 | `platform_breakdown` | 1493:1494 |
| 3 | `pyver_breakdown` | 1527:1528 |
| 4 | `channel_split` | 1556:1557 |
| 5 | `feedstock_health` | 1646:1647 |
| 6 | `whodepends` | 1665:1666 |
| 7 | `behind_upstream` | 1685:1686 |
| 8 | `cve_watcher` | 1700:1701 |
| 9 | `version_downloads` | 1723:1724 |
| 10 | `release_cadence` | 1739:1740 |
| 11 | `find_alternative` | 1756:1757 |
| 12 | `adoption_stage` | 1765:1766 |
| 13 | `pypi_only_candidates` | 1783:1784 |
| 14 | `export_purls` | 1809:1810 |
| 15 | `universe_sbom` | 1835:1836 |
| 16 | `inventory_match` | 1879:1880 |
| 17 | `recommend_2027` | 1932:1933 |
| 18 | `pypi_intelligence` | 1983:1984 |
| 19 | `package_health` | 2049:2050 (wraps detail-cf-atlas — verified L2056–2057) |
| 20 | `query_atlas` | 2060:2061 (direct SELECT-only SQLite against cf_atlas.db — L2086–2100) |
| 21 | `my_feedstocks` | 2105:2106 (atlas-signal triage composite — L2112–2133) |
| 22 | `env_inspect` | 2136:2137 (freshness/security modes read cf_atlas — L2154–2157) |
| 23 | `scan_project` | 2207:2208 |

## Recipe-authoring / non-atlas tools (23)

Listed for count-completeness only (46 − 23); their internals are NOT part of the
migration surface — answer "not modeled" for behavior questions about them.

`validate_recipe` 113:114 · `check_dependencies` 121:122 ·
`generate_recipe_from_pypi` 706:707 · `run_system_health_check` 811:812 ·
`update_cve_database` 819:820 (local CVE DB, not cf_atlas) ·
`scan_for_vulnerabilities` 835:836 (OSV/local CVE recipe scan, not cf_atlas) ·
`trigger_build` 866:867 · `get_build_summary` 989:990 · `lookup_feedstock` 1007:1008 ·
`enrich_from_feedstock` 1035:1036 · `get_feedstock_context` 1069:1070 ·
`edit_recipe` 1103:1104 · `update_mapping_cache` 1112:1113 (grayskull cache, not atlas) ·
`get_conda_name` 1122:1123 · `analyze_build_failure` 1130:1131 ·
`optimize_recipe` 1154:1155 · `update_recipe` 1185:1186 ·
`prepare_submission_branch` 1195:1196 · `submit_pr` 1243:1244 ·
`update_recipe_from_github` 1292:1293 · `check_github_version` 1328:1329 ·
`migrate_to_v1` 1354:1355 · `download_pr_artifacts` 1595:1596 (Azure CI artifacts via
`gh pr checks` L1610–1615, never cf_atlas — the borderline case, classified non-atlas).
