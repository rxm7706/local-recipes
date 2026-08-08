# pyforge-marshal — story specs (tracked, durable)

Per-story specs live here, **tracked in git**, not in gitignored
`implementation-artifacts/`. In a spec-driven build the spec *is* the
contract — see `CLAUDE.md` § *Spec-driven, framework-neutral layout*, "Story
specs are durable (tracked), NOT Tier-3." After a story merges, its spec is
promoted from the run's `implementation-artifacts/` into this directory and
committed here as the source of record.

**Status (2026-08-08):** all 50 done stories (of 86 total; Epics 1-6 shipped,
7-9 backlog) have a spec here — no promotion gap.

This directory also holds Dream-level Specs for Marshal-owned satellite
Dreams (`spec-<dream-slug>/SPEC.md`, distinct from the per-story
`spec-<epic>-<story>-...md` files above) — e.g. `spec-artifact-console`,
`spec-loop-home-fleet-refresh`, `spec-dashboard-project-path-derivation`.
See `_bmad-output/DREAM-TRIAGE-2026-08-08.md` for which of these are ready to
fold into real epics versus still needing an operator decision.
