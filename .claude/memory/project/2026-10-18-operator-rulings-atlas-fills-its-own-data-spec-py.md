---
name: "2026-10-18-operator-rulings-atlas-fills-its-own-data-spec-py"
description: "2026-10-18 operator rulings, atlas fills its own data (spec-pyforge-atlas CAP-64..CAP-68, Epics 34-36, 16 stories): pyf…"
metadata:
  type: project
---

2026-10-18 operator rulings, atlas fills its own data (spec-pyforge-atlas CAP-64..CAP-68, Epics 34-36, 16 stories): pyforge-atlas public sources go live in-package by default (APIDataset composition / pyforge.core.process; no-inline-IO denylist unchanged); credentialed fetches only when the operator sets PYFORGE_ATLAS_CREDENTIALED=1 for a run (AD-11); VCS and registry population = the full conda-forge universe (legacy K/L/N parity), not the OpenTeams identity subset; extras in scope: Phase P via ClickHouse (BigQuery stays off), Basilisk, OpenTeams identity sources, the query_plane_estate_source producer; order: Kedro first, then the legacy cf-graph fix (conda-forge moved node_attrs/pr_info/version_pr_info into conda-forge-bot-data-node_attrs/-pr_info/-version_pr_info, so legacy Phases E/J/M read 0 rows since then: dependencies table empty, bot/maintainer status stale); SPEC.md script render approved for this effort. Open before 36.1/36.3: Basilisk unattended vs opt-in; which OLTP tables the estate source extracts.
