---
title: 'Genesis seeds the token-economy kit (Story 28.3, Epic 28)'
type: 'feature'
created: '2026-08-30'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: heavy
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/integration-layers.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings:
  - caveman is ACTIVE in pixi since 2026-08-30 (2.4.0 patched build 2, linux-64 —
    `caveman-install` verified live; see recipes/caveman for the nodejs-24 hold);
    codegraph is likewise linux-64-only. Seeding must STILL treat each instrument as
    optional-with-named-finding (non-linux fleets, future regressions) — availability
    changed, the design constraint did not.
---

<intent-contract>

## Intent

**Problem:** Output compression (caveman skill) and the code-structure graph (codegraph
index) only help if they exist in every loop home — and today nothing provisions them, so
any adoption would be per-home ritual.

**Approach:** Genesis (`marshal seed`) installs the per-loop-home kit — caveman skill
deployment into the agent config, CCR store directory, codegraph index build + agent
integration — and `marshal seed check` verifies each piece, gated by Story 28.1's
`[context]` declaration. Dev sessions talk compressed; review verdicts, journals, and
escalation context stay fully articulated.

## Acceptance Criteria

- Given a seeded loop home with layers declared, when `marshal seed check` runs, then it
  verifies caveman-skill deployment, the CCR store dir, and a present+fresh codegraph index,
  each as a distinct check.
- Given a dev session in a seeded home, when a story lands, then the landed verdict and
  journal entries read as normal fully-articulated prose (never caveman-compressed).
- Given an unavailable instrument (pixi blocker, platform gap), when seed applies, then the
  seed still applies, the layer is skipped, and a named finding reports exactly which
  instrument and why.
- Given a home seeded with layers off, when checked, then no token-economy findings are
  raised (the kit is declared-off, not missing).

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-marshal/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`. Ledger
key `28-3-genesis-seeds-the-token-economy-kit`.

**Block If:** A change would apply caveman compression to review verdicts / journals /
escalation context, or install the BSL-1.1 `@caveman-ai/cli` proxy.

**Never:** Hand-edits inside a loop home as the mechanism (Genesis owns provisioning).
Blocking a seed on a missing optional instrument.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/` (Genesis apply/check/derive)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/seed.py`
- loop-home provisioning path in `cli/init.py` / spin preflight

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated
(seed-check items, articulate-verdict guarantee, per-instrument named-finding degradation).
Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 28.3 and spec-marshal-token-economy CAP-3/CAP-4. Follow the Genesis
managed-region/manifest idiom (Epics 8–11): the kit is seed-managed state with a conformance
check, not ad-hoc files. The caveman recipe ships `caveman-install` (MIT installer); the
skill deploys into the agent's skills/plugins dirs per loop home.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, including this story's own new/updated test coverage.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (no undeclared dependency surface).

## Spec Change Log

- 2026-08-30: drafted from epics.md Epic 28 for fleet-drain preflight (Dream/Spec chain: docs/dreams/marshal-token-economy.md → spec-marshal-token-economy)
