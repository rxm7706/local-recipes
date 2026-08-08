# pyforge-herald — story specs (tracked, durable)

Per-story specs live here, **tracked in git**, not in gitignored
`implementation-artifacts/`. In a spec-driven build the spec *is* the
contract — see `CLAUDE.md` § *Spec-driven, framework-neutral layout*, "Story
specs are durable (tracked), NOT Tier-3." After a story merges, its spec is
promoted from the run's `implementation-artifacts/` into this directory and
committed here as the source of record.

**Status (2026-08-08):** all 47 stories (Epics 1-12) have a spec here — no
promotion gap.

This directory also holds a Dream-level Spec for a Herald-owned satellite
Dream (`spec-herald-moments-2-4-live-backend/SPEC.md`, distinct from the
per-story `spec-<epic>-<story>-...md` files above) — `status: draft`,
archive-leaning per its own open questions. See
`_bmad-output/DREAM-TRIAGE-2026-08-08.md`.
