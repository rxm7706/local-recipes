---
name: "2026-10-23-steward-story-13-6-workspace-started-from-another"
description: "2026-10-23 steward Story 13.6 (workspace started --from another branch is landed once its branch is on origin/main): sc…"
metadata:
  type: project
---

2026-10-23 steward Story 13.6 (workspace started --from another branch is landed once its branch is on origin/main): scoped by the operator after nine review rounds. A workspace directory deleted by hand never loses more than at the baseline, but its own clean still drops a detached commit no ref holds (DW-steward-13-6), and a present landed worktree loses a commit only its refs/worktree/* or refs/bisect/* ref holds under --merged-only (DW-steward-13-6-2); both pre-existing, proposed as a separate steward fix story. Every workspace clean now unregisters only its own worktree (worktree remove --force; a locked registration stays) instead of a bare git worktree prune.
