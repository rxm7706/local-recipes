# pyforge-steward — story specs (tracked, durable)

Per-story specs live here, **tracked in git**, not in gitignored
`implementation-artifacts/`. In a spec-driven build the spec *is* the
contract — see `CLAUDE.md` § *Spec-driven, framework-neutral layout*, "Story
specs are durable (tracked), NOT Tier-3." After a story merges, its spec is
promoted from the run's `implementation-artifacts/` into this directory and
committed here as the source of record.

**Status (2026-08-08):** all 18 stories (Epics 1-4) have a spec here — no
promotion gap.

This directory also holds the station Spec (`spec-pyforge-steward/`, which since 2026-10-27 also
carries the live companions of the absorbed bmad-suite, canopy, build-league and intelligence-hub
Specs: `install-matrix.md`, `adoption-register.md`, `release-cadence.md`, `install-class-playbook.md`,
`ARCHITECTURE-SPINE.md`, `measure-catalog.md`, `vocabulary-map.md`), the unifying strategy
(`spec-pyforge-unifying-strategy/`) and the declared seams
(`spec-python-foundry-cutover/SPEC.md` (`ready`; `fnd:CAP-1..11`, Epic 44 cutover; Epic 54 kernel),
`spec-foundry-regenerate-not-fold/SPEC.md` (`ready`; `fnr:CAP-1..5`, regenerate-not-fold),
`spec-foundry-capability-ledger/SPEC.md` (`ready`; `fcl:CAP-1..3`, strangler ledger + extract),
and the earlier records under the archive home:
every absorbed pointer Spec (`spec-unified-container/`, `spec-bmad-module-provisioning/`,
`spec-platform-image-one-pixi-env/`, `spec-mcp-era-isolation/`, `spec-platform-dev-boots-local/`,
`spec-build-league-scorecard/` and the rest, 35 folders) moved to
`archive/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/` on 2026-10-27 with its memlog
and record companions (Story 116.1, spec-one-chain-per-station:CAP-11, CHAIN-STANDARD § 11);
`archive/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-htap-query-plane/SPEC.md`
(`archived` / absorbed — retirement record, moved to the archive home on 2026-10-26 with
`spec-pyforge-steward-feedstock-maintenance/` and the superseded `spec-22-prep-atlas-kedro-cli-introspection.md`,
Story 113.1, CHAIN-STANDARD § 11; query plane is unifying CAP-19 / Epic 34),
distinct from the per-story `spec-<epic>-<story>-...md` files above). See
`archive/_bmad-output/DREAM-TRIAGE-2026-08-08.md`.
