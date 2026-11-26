---
name: "2026-11-25-operator-rulings-on-the-rows-held-open-by-a-named"
description: "2026-11-25 operator rulings on the rows held open by a named blocker (branch named-blocker-rows-2026-11-25; steward Epi…"
metadata:
  type: project
---

2026-11-25 operator rulings on the rows held open by a named blocker (branch named-blocker-rows-2026-11-25; steward Epic 136, atlas Epic 53): 'find all the Still open by design items in the entire code base - we want to resolve them all', then 'All 22 rows'. Of 1,090 open deferred-work rows, 22 gave a named blocker as their reason. Rulings: (1) the two scribe test rows take 'No new lane': the tests run as steps of the lint-types job, which already installs pyforge-guild and pyforge-foundry-full; no ci-surfaces row or budget. (2) DW-atlas-46-1-7 takes 'Layout-free URN': the OpenLineage producer is urn:local-recipes:pyforge-atlas. (3) the seven cutover rows take 'Leave them blocked': DW-steward-121-2, DW-steward-121-3, DW-steward-cutover-2026-11-10-4, -5 and -7, DW-atlas-46-1-3 and DW-atlas-46-1-8 keep their blocker and no blocked key is flipped. Fifteen rows closed. Still the operator's: DW-steward-134-2-1, the session hook's two false denials; a patch was written and handed over, and an agent never applies it. New remainder rows: DW-steward-136-5-1 (Story lines of steward's epics.md the page does not resolve) and DW-steward-136-4-1 (six compiled station skills and briefs cite the persona ids bare; each needs its own skf-update-skill run).
