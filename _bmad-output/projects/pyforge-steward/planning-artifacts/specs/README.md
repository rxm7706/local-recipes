# pyforge-steward — story specs (tracked, durable)

Per-story specs live here, **tracked in git**, not in gitignored
`implementation-artifacts/`. In a spec-driven build the spec *is* the
contract — see `CLAUDE.md` § *Spec-driven, framework-neutral layout*, "Story
specs are durable (tracked), NOT Tier-3." After a story merges, its spec is
promoted from the run's `implementation-artifacts/` into this directory and
committed here as the source of record.

**Status (2026-08-08):** all 18 stories (Epics 1-4) have a spec here — no
promotion gap.

This directory also holds Dream-level Specs for Steward-owned satellite
Dreams (`spec-unified-container/SPEC.md`, `spec-bmad-module-provisioning/SPEC.md`,
`spec-platform-image-one-pixi-env/SPEC.md` (`shipped`),
`spec-mcp-era-isolation/SPEC.md` (`ready`; CAP-4 / Epic 35 cluster fail-loud),
`spec-python-foundry-cutover/SPEC.md` (`ready`; `fnd:CAP-1..11`, Epic 44 cutover; Epic 54 kernel),
`spec-foundry-regenerate-not-fold/SPEC.md` (`ready`; `fnr:CAP-1..5`, regenerate-not-fold),
`spec-foundry-capability-ledger/SPEC.md` (`ready`; `fcl:CAP-1..3`, strangler ledger + extract),
`spec-platform-dev-boots-local/SPEC.md` (`ready`; `pdl:CAP-1`, toolbar on `platform-dev` only; Epic 56),
`spec-build-league-scorecard/SPEC.md` (`draft`, Q5 parked),
`spec-htap-query-plane/SPEC.md` (`archived` / absorbed — retirement record;
query plane is unifying CAP-19 / Epic 34),
distinct from the per-story `spec-<epic>-<story>-...md` files above). See
`_bmad-output/DREAM-TRIAGE-2026-08-08.md`.
