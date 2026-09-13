# pyforge-scribe — story specs (tracked, durable)

Per-story specs live here, **tracked in git**, not in gitignored
`implementation-artifacts/`. In a spec-driven build the spec *is* the
contract — see `CLAUDE.md` § *Spec-driven, framework-neutral layout*, "Story
specs are durable (tracked), NOT Tier-3." After a story merges, its spec is
promoted from the run's `implementation-artifacts/` into this directory and
committed here as the source of record.

**Status (2026-09-13):** `spec-scribe-knowledge-layers` + Stories 8.4–8.6
(layered compile/recall). Parked CAP-6–CAP-14 live in
`spec-scribe-knowledge-layers/later-caps.md`. Story 8.3
(`spec-8-3-herald-fact-ledgers-join-the-compile.md`) — compile
`presentations/*/facts.yaml` as `doc` nodes. Story 8.2
(`spec-8-2-the-nightly-compile-keeps-the-graphify-code-surface.md`) —
graphifyy callable unwrap + nightly `SCRIBE_GRAPHIFY_EXTRA` default. Prior
note kept below.

**Status (2026-08-08):** all 9 done stories have a spec here. `spec-1-4`
(pointer stub write-back, idempotent re-invocation) and `spec-1-5` (seed
promotion — the story that closed Epic 1) were recovered the same day — no
session transcript or worktree snapshot survived, so both are Tier-3
`epics.md`-derived recoveries (contract only, plus their merged-PR Delivery
Records) per the priority order in `CLAUDE.md`.
