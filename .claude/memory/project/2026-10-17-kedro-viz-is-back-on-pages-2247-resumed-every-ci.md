---
name: "2026-10-17-kedro-viz-is-back-on-pages-2247-resumed-every-ci"
description: "2026-10-17: Kedro-Viz is back on Pages. #2247 resumed every CI surface (no PAUSE_* variable, no disabled workflow); atl…"
metadata:
  type: project
---

2026-10-17: Kedro-Viz is back on Pages. #2247 resumed every CI surface (no PAUSE_* variable, no disabled workflow); atlas 32.1 (#2248, 6fa7150e2b) fixed kedro-viz-publish (stub credentials come from tools/bootstrap.py --credentials-only, viz-build fails on a failed build, the flag step runs in -e pyforge-atlas); producer run 39019867740 uploaded kedro-viz-export and Pages run 39020410506 mounted it (live /dashboard/kedro-viz/ renders); DW-steward-102-4-1 closed. OPERATOR-OWNED: the local src/shared/packages/pyforge-atlas/conf/local/credentials.yml predates six catalog keys (gitlab_token, codeberg_token, npm_token, crates_token, rubygems_token, nuget_token), so a local viz-build or pyforge-atlas-bootstrap now fails naming them -- add '<key>: {}' for each; pyforge-atlas:CAP-62's SPEC.md success clause ('the stub-credentials step unchanged') is stale and waits for the next bmad-spec re-derive.
