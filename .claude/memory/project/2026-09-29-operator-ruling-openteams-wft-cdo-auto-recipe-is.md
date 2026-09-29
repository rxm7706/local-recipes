---
name: "2026-09-29-operator-ruling-openteams-wft-cdo-auto-recipe-is"
description: "2026-09-29 operator ruling: OpenTeams-WFT-CDO/auto-recipe is retired -- Mason + conda-forge-expert already cover it (pr…"
metadata:
  type: project
---

2026-09-29 operator ruling: OpenTeams-WFT-CDO/auto-recipe is retired -- Mason + conda-forge-expert already cover it (preflight, repodata dep audit, scaffold, the eight recipe decisions, hard rules, verify loop, staged-recipes branch, enforced_by failure catalog). The three missing pieces go into CFE as spec-pyforge-mason CAP-33 / FR-55 / Epic 23: 23.1 license-checker refuses a GPL-family -only id whose LICENSE grants any later version; 23.2 recipe-generator.py reports its six unsettled choices (Decided/Ambiguous; --strict refuses); 23.3 a negative corpus pins each check to its defect. Dropped: auto-recipe's unattended issue->PR/watch/LLM-fix layer and its diagnosis signatures (this repo opens no staged-recipes PR without an explicit ask). The OpenTeams-WFT-CDO and openteams-ai GitHub orgs are the operator's own, so their code may be ported with a provenance line. Archiving the auto-recipe repo is the operator's act.
