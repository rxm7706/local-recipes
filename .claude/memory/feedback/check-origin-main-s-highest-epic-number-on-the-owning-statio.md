---
name: "check-origin-main-s-highest-epic-number-on-the-owning-statio"
description: "Check origin/main's highest epic number on the owning station right before minting an Epic and again before every merge…"
metadata:
  type: feedback
---

Check origin/main's highest epic number on the owning station right before minting an Epic and again before every merge of main into a long-lived branch: steward Story 131.1 was minted as 129.1 and had to move twice (to 130.1, then 131.1) because main landed its own Epics 129 and 130 while the PR was open. Renumber only the lines the branch added (diff against the merge base), rename the story spec file and the feed keys, and put the conda-forge-expert edits in a retro(cfe) commit that also moves its CHANGELOG (mason's test_persona_consults_cfe rejects any other commit touching CFE).
