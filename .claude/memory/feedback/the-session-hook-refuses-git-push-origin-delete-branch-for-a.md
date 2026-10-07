---
name: "the-session-hook-refuses-git-push-origin-delete-branch-for-a"
description: "The session hook refuses 'git push origin --delete <branch>' for an already-merged branch with 'Cannot resolve this rem…"
metadata:
  type: feedback
---

The session hook refuses 'git push origin --delete <branch>' for an already-merged branch with 'Cannot resolve this remote branch's tip' even after git fetch origin makes refs/remotes/origin/<branch> resolve and merge-base --is-ancestor proves it is on origin/main (seen 2026-10-07 on steward-free-threading-review after steward workspace clean --merged-only removed the local refs). match_unreachable_ref_deletion resolves the tip in ctx.cwd; the false positive is in that resolution, not in the branch. Do not route around the hook (no update-ref, no preserve tag): hand the operator the one-line delete; a fix belongs on steward's chain as a hook story.
