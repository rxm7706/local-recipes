# pyforge-steward — story specs (tracked, durable)

Per-story specs live here, **tracked in git**, not in gitignored
`implementation-artifacts/`. In a spec-driven build the spec *is* the
contract — see `CLAUDE.md` § *Spec-driven, framework-neutral layout*, "Story
specs are durable (tracked), NOT Tier-3." After a story merges, its spec is
promoted from the run's `implementation-artifacts/` into this directory and
committed here as the source of record.

**Status (2026-08-08):** all 18 stories (Epics 1-4) have a spec here — no
promotion gap.

This directory also holds Dream-level Specs for two Steward-owned satellite
Dreams (`spec-unified-container/SPEC.md`, `spec-bmad-module-provisioning/SPEC.md`,
distinct from the per-story `spec-<epic>-<story>-...md` files above) — both
`status: draft`, both fold-in-ready per their own readiness signals. See
`_bmad-output/DREAM-TRIAGE-2026-08-08.md`.
