---
name: "2026-09-28-session-close-fleet-decomposition-dispatchability"
description: "2026-09-28 session close (fleet decomposition + dispatchability; PRs #1639-#1652 merged, main df34e461e2). Marshal 64.1…"
metadata:
  type: project
---

2026-09-28 session close (fleet decomposition + dispatchability; PRs #1639-#1652 merged, main df34e461e2). Marshal 64.1 was dispatched and landed unattended (PR #1647): a dispatch no longer reads the shared BMAD marker, so every station passes the launch scope gate. Marshal CAP-277 found that every automated ledger promotion since the pre-push hook landed on 2026-09-20 was lost (9 of 9): finalize's push to main runs the full pr-preflight and dies at the 120 s timeout, silently. Until marshal Story 68.1 lands, verify the ledger row after every dispatch landing and hand-promote through a PR; dispatch 68.1 first. Operator-owned: flip steward 72.2 after mason 19.1 lands; flip herald 27.5 after steward 71.2; flip doctor 33.1 after marshal 66.2; open the python-foundry Frame PR (branch frames-mason-station-skill-ruling, pushed; the operator runs the prepared gh pr create). Rulings recorded in the Spec memlogs: pixi is never capped (mason 20.1 guard), docsite under /herald/, Mason skills A-only until the cutover flip, Guild size bound restated at 2 GB.
