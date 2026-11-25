---
title: '53.2: The lineage producer is a layout-free identifier'
type: 'fix'
created: '2026-11-25'
status: 'ready-for-dev'
story: 53-2-the-lineage-producer-is-a-layout-free-identifier
spec: spec-pyforge-atlas
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-atlas/src/pyforge/atlas/observability.py'
  - 'src/shared/packages/pyforge-atlas/src/pyforge/atlas/**'
  - 'src/shared/packages/pyforge-atlas/tests/**'
  - '_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/contract.md'
  - '_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/.memlog.md'
  - 'docs/**'
  - '_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md'
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-atlas.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `DW-atlas-46-1-7`. `observability.PRODUCER` is `https://github.com/rxm7706/local-recipes/tree/main/pyforge-atlas`, stamped on every emitted OpenLineage event and facet. The path has not existed since the package moved under `src/shared/packages/`, and it names one root's layout. `contract.md` records the value as the code has it.

**Approach:** Operator ruling 2026-11-25: "Layout-free URN". Set `PRODUCER = "urn:local-recipes:pyforge-atlas"`, the form the report-schema `$id`s already use. First write a test that fails on the unchanged tree: the producer is a URN that holds no `/tree/` path and no `src/` segment, and equals the value `contract.md` records. Then change the constant, every test or fixture that pins the old string, and `contract.md`'s `Lineage producer` section. Check that the OpenLineage client accepts a URN as `producer` (it is typed as a URI) by emitting one event in a test.

Ledger key: `53-2-the-lineage-producer-is-a-layout-free-identifier`.

### Living CAP citations

- spec-pyforge-atlas CAP-73 (the public contract, whose `Lineage producer` section records the value; the section moves with the constant); no AD moves.

## Boundaries & Constraints

**Always:**
- Reproduce what the row reports on the unchanged tree before changing it, and record the reproduction in the Spec Change Log.
- Append the surface reconcile to the memlog of each Spec that governs a moved file before the scoped stamps.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never change the OpenLineage namespace or any facet's schema URL.
- Never add a flag: one producer value is emitted.
- Never add a flag, a capability or an architecture decision; a fix that would need one stops and is reported.

## Acceptance Criteria

**Given** `DW-atlas-46-1-7` reports that the producer URI names a path that does not exist, and the operator rules that the producer is a layout-free URN
**When** a test that fails on the unchanged tree is written, and the constant, the tests that pin it and `contract.md` move to `urn:local-recipes:pyforge-atlas`
**Then** every event and facet atlas emits carries `urn:local-recipes:pyforge-atlas` as its producer, no file under the package names the old URL, and `contract.md` records the value the code has
**And** an event with the URN producer is built and serialized by the OpenLineage client in a test, the contract meta-test passes, and the row reads resolved

- **AC1 — The old URL is gone from the package and the contract.** Expected: exit 1 (no line matches).

  ```bash
  grep -rn 'tree/main/pyforge-atlas' src/shared/packages/pyforge-atlas _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/contract.md
  ```

- **AC2 — The constant is the URN.** Expected: exit 0.

  ```bash
  grep -n 'PRODUCER = "urn:local-recipes:pyforge-atlas"' src/shared/packages/pyforge-atlas/src/pyforge/atlas/observability.py
  ```

- **AC3 — Atlas's package suite holds.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-atlas pyforge-atlas-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-atlas CAP-73 (the public contract, whose `Lineage producer` section records the value; the section moves with the constant); no AD moves.
- Dream: `docs/dreams/pyforge-atlas.md`, the 2026-11-25 entry (the rows a lapsed blocker held close); operator ruling of 2026-11-25: "All 22 rows".
- Epic: Epic 53, minted with this story.
- Ledger key: `53-2-the-lineage-producer-is-a-layout-free-identifier`.
- Deferred-work row: `DW-atlas-46-1-7`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."53"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry (the rows a lapsed blocker held close) and the operator's ruling of the same date. Not implemented.
