---
name: "merge-a-story-pr-with-the-marshal-subject-gh-pr-merge-merge"
description: "Merge a story PR with the marshal subject (gh pr merge --merge --subject 'Merge <station>/<E-S> into main'), never the…"
metadata:
  type: feedback
---

Merge a story PR with the marshal subject (gh pr merge --merge --subject 'Merge <station>/<E-S> into main'), never the GitHub UI default, unless the branch is station-named. dispatch_land_finalize corroborates a landing from origin/main commit subjects; 'Merge pull request #N from <owner>/<free-form-branch>' matches no shape, so finalize promotes the sprint-status ledger but leaves the story's epics.md Status line (and any Tier-3 feed row) behind, silently. Repair: a one-line follow-up PR that flips the epics status, merged with the marshal subject (mason 30.1: #2181 then #2182, 2026-10-13).
