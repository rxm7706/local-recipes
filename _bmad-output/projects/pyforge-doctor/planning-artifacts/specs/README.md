# pyforge-doctor — story specs (tracked, durable)

Per-story specs live here, **tracked in git**, not in gitignored
`implementation-artifacts/`. In a spec-driven build the spec *is* the
contract — see `CLAUDE.md` § *Spec-driven, framework-neutral layout*, "Story
specs are durable (tracked), NOT Tier-3." After a story merges, its spec is
promoted from the run's `implementation-artifacts/` into this directory and
committed here as the source of record.

**Status (2026-08-08):** all 16 done stories have a spec here. `spec-2-1`
(Atlas gather filter / staleness axis / MCP-first with CLI fallback) was
recovered the same day — no session transcript or worktree snapshot
survived (it landed via a manual maintainer-edit PR, not a bmad-loop run),
so it's a Tier-3 `epics.md`-derived recovery (contract only, plus its
merged-PR Delivery Record) per the priority order in `CLAUDE.md`.
