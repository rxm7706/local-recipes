---
name: "traps-met-renaming-registration-names-across-four-packages-2"
description: "Traps met renaming registration names across four packages (2026-11-26, branch plugin-names-2026-11-26, PR #2399; stewa…"
metadata:
  type: feedback
---

Traps met renaming registration names across four packages (2026-11-26, branch plugin-names-2026-11-26, PR #2399; steward 146.1, marshal 125.1, mason 45.1): (1) chain-currency dates a station's code stage by the last commit to its package pyproject.toml, so any pyproject edit (an entry point, a mypy override) makes code newer than the station's last retro and the sweep reds until a real retro covers everything since it (here three: steward, marshal, mason). Budget a retro per station whose pyproject moves. (2) Station tests pin entry-point names by reading pyproject.toml with tomllib (groups[ENTRY_POINT_GROUP]['bmad-loop']), which a grep for the name as a used string misses; grep the tests for the literal key too. (3) Before claiming no capability text moves, grep SPEC.md, the PRD and the spine for every renamed literal: mason CAP-37 named the old entry points and needed a render. (4) A new worktree has no implementation-artifacts/ Tier-3 feed, and the primary checkout's feed can be behind; seed the feed from the worktree that last wrote it, or sprint-ledger-sync skips with 'no Tier-3 feed'. (5) Stamping one Spec exposes the next co-governor's unnamed paths in turn; on a busy day expect to name paths earlier changes left on five or six Specs before spec-surface reads clean.
