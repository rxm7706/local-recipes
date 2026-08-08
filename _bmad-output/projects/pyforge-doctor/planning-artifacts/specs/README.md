# pyforge-doctor — story specs (tracked, durable)

Per-story specs live here, **tracked in git**, not in gitignored
`implementation-artifacts/`. In a spec-driven build the spec *is* the
contract — see `CLAUDE.md` § *Spec-driven, framework-neutral layout*, "Story
specs are durable (tracked), NOT Tier-3." After a story merges, its spec is
promoted from the run's `implementation-artifacts/` into this directory and
committed here as the source of record.

**Status (2026-08-08):** 15 of 16 done stories have a spec here. **Gap:
`spec-2-1` (Atlas gather filter / staleness axis / MCP-first with CLI
fallback) was never promoted** — recover per the priority order in
`CLAUDE.md`: Claude Code session transcripts first, then bmad-loop
run-worktree snapshots, then regenerate contract-only from `epics.md` as a
last resort.
