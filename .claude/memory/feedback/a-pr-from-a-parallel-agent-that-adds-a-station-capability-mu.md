---
name: "a-pr-from-a-parallel-agent-that-adds-a-station-capability-mu"
description: "A PR from a parallel agent that adds a station capability must carry the whole Dream-to-code chain before it merges: a…"
metadata:
  type: feedback
---

A PR from a parallel agent that adds a station capability must carry the whole Dream-to-code chain before it merges: a dated entry on that station's Dream (docs/dreams/pyforge-<station>.md, never a new standalone Dream + Spec pair), CAP-n on the station Spec through bmad-spec, a numbered Story in a NEW epic if the natural one is done (ledger-regression), FR/AD citing real CAP ids and a Surface naming paths that exist, a ledger row, a tracked story spec with triage log and Auto Run Result, capability-ledger rows, memlog entries on the owning Spec and every co-governor the spec-surface detector names, and scoped stamps for exactly those Specs. A post-ruling standalone Dream/Spec pair cannot be archived in place — chain-sprawl reads no status — fold its record into the station memlog and remove it. Found 2026-09-19 on PR #1507 (steward sprint-ledger query engine) and again on PR #1513 (AGENTS.md governance).
