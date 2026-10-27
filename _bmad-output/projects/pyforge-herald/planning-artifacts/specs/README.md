# pyforge-herald — story specs (tracked, durable)

Per-story specs live here, **tracked in git**, not in gitignored
`implementation-artifacts/`. In a spec-driven build the spec *is* the
contract — see `CLAUDE.md` § *Spec-driven, framework-neutral layout*, "Story
specs are durable (tracked), NOT Tier-3." After a story merges, its spec is
promoted from the run's `implementation-artifacts/` into this directory and
committed here as the source of record.

**Status (2026-09-18):** every ledger story key has an exact `spec-<key>.md`
(13 remaining gaps closed here: 11 slug renames on 2.x/6.x/9.x/11.x; Epic 21.11
and blocked 19.2 minted from `epics.md`). Stories 21.1–21.4 already live on
`main` as 2026-09-17 recovered originals — those files were kept, not overwritten
by the thinner `epics.md` drafts. Ledger statuses were not flipped.

**Status (2026-08-11):** all 48 stories through Epic 13's first promoted spec
(13.1) have a spec here — no promotion gap.

This directory also holds the station Spec (`spec-pyforge-herald/`, which since 2026-10-27 also
carries the deck facts catalog `facts-ledger.md` and the infographic standard
`infographic-standard.md`, the live companions of the absorbed `spec-deck-family-currency`). The
absorbed pointer Specs, among them the Dream-level `spec-herald-moments-2-4-live-backend/`, moved to
`archive/_bmad-output/projects/pyforge-herald/planning-artifacts/specs/` on 2026-10-27 with their
memlogs and record companions (Story 49.1, spec-one-chain-per-station:CAP-11). See
`archive/_bmad-output/DREAM-TRIAGE-2026-08-08.md`.
