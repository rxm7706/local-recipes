# pyforge-mason — story specs (tracked, durable)

Per-story specs live here, **tracked in git**, not in gitignored
`implementation-artifacts/`. In a spec-driven build the spec *is* the
contract — see `CLAUDE.md` § *Spec-driven, framework-neutral layout*, "Story
specs are durable (tracked), NOT Tier-3." After a story merges, its spec is
promoted from the run's `implementation-artifacts/` into this directory and
committed here as the source of record.

**Status (2026-08-08):** all 4 done stories (of 38 total; Epic 1 stories
1.1-1.4 shipped, 1.5 onward + Epics 2-5 backlog) have a spec here — no
promotion gap.

This directory also holds a Dream-level Spec for a Mason-owned satellite
Dream (`spec-conda-forge-expert-rebuild/SPEC.md`, distinct from the
per-story `spec-<epic>-<story>-...md` files above) — `status: draft`, not
yet decided fold-in vs. archive. See
`_bmad-output/DREAM-TRIAGE-2026-08-08.md`.
