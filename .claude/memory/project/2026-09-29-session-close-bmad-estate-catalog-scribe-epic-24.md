---
name: "2026-09-29-session-close-bmad-estate-catalog-scribe-epic-24"
description: "2026-09-29 session close (BMAD-estate catalog, scribe Epic 24 / spec-pyforge-scribe CAP-32; PR #1672 on claude/intellig…"
metadata:
  type: project
---

2026-09-29 session close (BMAD-estate catalog, scribe Epic 24 / spec-pyforge-scribe CAP-32; PR #1672 on claude/intelligent-davinci-n1y2lk, head 892f8acf, maintenance label, chain + implementation, stories 24.1-24.3 done after an independent adversarial review). Operator-only asks left open: (1) merge PR #1672 with gh pr merge --merge once CI is green; (2) the role of OpenTeams-WFT-CDO/bmad-suite-package (channel publishing home vs mirror of recipes/bmad-*) is still unverified -- the population was confirmed 2026-09-12, the repo itself is unreachable from a local-recipes session; (3) the first catalog render surfaced four suite-version disagreements (bmad-loop 0.11.1/0.12.0, TEA 1.24.0/1.27.2, skill-forge 2.1.0/2.2.0, eval-quality 0.2.0.dev0 @3172162f/4.3.0: adoption-register vs pixi.toml vs recipe) relayed as steward DW-steward-suite-versions-disagree-2026-09-29 -- the register rows (AD-2) are the stale ones and only steward re-decides them. Not this PR's: detectors-ci's mason_cfe_surface_check finding on main commit 456e33a243; atlas dashboard e2e tests need Playwright's headless Chromium, absent in the cloud sandbox.
