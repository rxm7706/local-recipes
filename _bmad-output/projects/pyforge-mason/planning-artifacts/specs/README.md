# pyforge-mason — story specs (tracked, durable)

Per-story specs live here, **tracked in git**, not in gitignored
`implementation-artifacts/`. In a spec-driven build the spec *is* the
contract — see `CLAUDE.md` § *Spec-driven, framework-neutral layout*, "Story
specs are durable (tracked), NOT Tier-3." After a story merges, its spec is
promoted from the run's `implementation-artifacts/` into this directory and
committed here as the source of record.

**Status (2026-08-10, Phase 1 audit):** all 10 done stories (Epic 1
complete; Epics 2-5 backlog, 28 stories) have a spec here — the 2026-08-08
claim of "no promotion gap" was false: specs 1-5..1-10 lived only in
gitignored Tier-3 and were promoted by the audit (the warden-loss failure
mode, caught before a teardown could eat them).

This directory also holds a Dream-level Spec for a Mason-owned satellite
Dream (`spec-conda-forge-expert-rebuild/SPEC.md`, distinct from the
per-story `spec-<epic>-<story>-...md` files above) — `status: draft`, not
yet decided fold-in vs. archive. See
`_bmad-output/DREAM-TRIAGE-2026-08-08.md`.
