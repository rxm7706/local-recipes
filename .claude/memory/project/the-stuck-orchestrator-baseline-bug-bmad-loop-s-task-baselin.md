---
name: "the-stuck-orchestrator-baseline-bug-bmad-loop-s-task-baselin"
description: "The stuck-orchestrator-baseline bug: bmad-loop's task.baseline_commit can drift to a later commit while a dev session i…"
metadata:
  type: project
---

The stuck-orchestrator-baseline bug: bmad-loop's task.baseline_commit can drift to a later commit while a dev session is still running (worktree never moves, orchestrator bookkeeping does), so a completed reviewed attempt gets permanently rejected (spec baseline does not match orchestrator-recorded baseline) and the run silently moves to the next story instead of stopping. Hit 5 times in one session (2026-08-14): marshal 8.1-9.5, marshal 9.6, marshal 10.1 (intent-gap variant, no recoverable git artifact at all), mason 3.6/3.7/3.9, mason 3.8. Root-caused against bmad-loop 0.9.0 source; documented in docs/dreams/bmad-loop-baseline-drift.md and docs/dreams/bmad-loop-intent-gap-work-preservation.md (both status: dreamt, no Spec yet, no upstream report filed). If a story shows deferred/escalated with commit_sha null in its loop home's state.json despite the Tier-3 feed marking it done, check for a recoverable attempt-preserve branch or failed/*.patch before assuming the work is lost; for an intent-gap revert with neither, the dev session's own Claude Code transcript may still have the full diff embedded in an adversarial-review Agent prompt.
