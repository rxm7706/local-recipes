---
title: '127.2: The corridor duties run against the platform''s database'
type: 'feature'
created: '2026-11-21'
status: 'done'
story: 127-2-the-corridor-duties-run-against-the-platform-s-database
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # tests, a gate's own module and the scripts a gate runs; a gated gate is a silent green (roster list)
surface:
  - 'docs/how-to/move-vendor-extracts-through-the-corridor.md'
  - 'docs/tutorials/local-platform-development.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md'
  - 'src/shared/packages/pyforge-steward/**'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The corridor how-to tells the operator to write a settings module of their own and reaches a SQLite file only.

**Approach:** The duties are run with the platform's settings in `-e platform-dev` against a PostgreSQL 17 database the platform's migrations built.

Ledger key: `127-2-the-corridor-duties-run-against-the-platform-s-database`.

### Living CAP citations

- spec-pyforge-steward CAP-139, CAP-141 and CAP-143 (realized, no text change); no FR (the PRD absorbed CAP-141..145 with no requirement of its own); no AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Reach station code from the platform only through a portal package or `pyforge.core.station_port`.

**Never:**
- Never import `pyforge.*` from `src/platform/`, move a PostgreSQL or driver pin, or hand-edit a `SPEC.md`, a generated page or `sprint-status-ledger.yaml`.

## Acceptance Criteria

**Given** the corridor how-to tells the operator to write a settings module of their own and reaches a SQLite file only
**When** the duties are run with the platform's settings in `-e platform-dev` against a PostgreSQL 17 database the platform's migrations built
**Then** `load inbound`, `passport mint`, `quarantine shelf` and `glass` run there, the how-to gives that setup and keeps the SQLite one as a laptop fallback, and the how-to's `sources:` and `verified:` are current
**And** `DW-steward-126-3-1` reads resolved in its ledger with the commit that closed it

- **AC1 — The story's own check passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild docs-currency-check && pixi run --frozen -e pyforge-guild deferred-work-check
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-139, CAP-141 and CAP-143 (realized, no text change); no FR (the PRD absorbed CAP-141..145 with no requirement of its own); no AD moves.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-11-21 entry; operator ruling of 2026-11-21 on `DW-steward-126-3-1`: "Platform host".
- Epic: Epic 127, minted with this story.
- Ledger key: `127-2-the-corridor-duties-run-against-the-platform-s-database` (`done`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."127"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-21: minted from the station Dream's 2026-11-21 entry and the operator ruling of 2026-11-21 on `DW-steward-126-3-1`: "Platform host".
- 2026-11-21 (later): done on branch `corridor-platform-host-2026-11-21`; checked against PostgreSQL 17.11 on macOS (migrate, a real Liquibase update, every corridor duty in `-e platform-dev`).
