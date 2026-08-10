---
name: "bmad-loop-escalation-and-landing-traps"
description: "Four traps in bmad-loop escalation recovery and landing — the destructive re-arm default, the misleading --no-interactive flag, the baseline the restore patch must be diffed against, and the intent feed dashboard-gen reads by default."
metadata:
  type: reference
---

bmad-loop escalation recovery and landing mechanics — four traps that cost real work to rediscover.

(1) `rearm_escalation` DEFAULTS TO DESTRUCTIVE. With `restore_patch=None` it flips the escalated story back to PENDING, resets the tree to the story's baseline, and sets the spec status to `ready-for-dev` — so the dev session RE-IMPLEMENTS FROM SCRATCH. Committed work on the story branch is not consulted. On doctor 6-8 that would have discarded 1,197 lines of `sources/factory.py`, a 1,197-line test suite, and roughly 677K output tokens.

(2) `--no-interactive` IS NOT THE SAFE FLAG. It reads like the conservative option — it only skips the interactive resolve agent. ONLY `--restore-patch` changes the re-drive mode: it sets the spec to `in-review` and re-applies the saved diff, so review resumes on the attempted change instead of re-implementing it. 'Just re-arm and resume' is the destructive path.

(3) THE RESTORE PATCH MUST BE DIFFED AGAINST CURRENT MAIN, not against the story's recorded baseline. `rearm_escalation` advances the baseline to the project's current HEAD, so a patch diffed from the stale baseline fails to apply and the engine escalates again. Build it as `git diff origin/main...<story-HEAD>` and prove it with `git apply --check --3way` BEFORE invoking resolve.

(4) `dashboard-gen` DEFAULTS TO THE INTENT FEED. `--source sprint-status` reads the Tier-3 sprint feed, which marks a story done at attempt-1 dev completion — before review. Because `docs/dashboard/data.js` is shared across all eight stations, regenerating it during a landing imports OTHER stations' premature state and makes board-vs-ledger diverge whichever way you move; `apply_tracked_ledger` is upgrade-only by design, so the board cannot be walked back. Use `--source git` for landings: it derives the done set from merge commits reachable from HEAD, so it renders what actually merged and cannot inherit the feed's claims.
