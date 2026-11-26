---
title: '53.2: The lineage producer is a layout-free identifier'
type: 'fix'
created: '2026-11-25'
status: 'done'
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

- 2026-11-25: reproduction on the unchanged tree: AC1's grep exits 0 with two lines (`observability.py:84`, `contract.md:481`); three new tests fail (`test_the_producer_is_a_layout_free_urn`, the event-and-facet producer test, and the contract meta-test `test_the_lineage_producer_in_the_contract_is_the_one_the_code_stamps`). No test or fixture pinned the old URL.
- 2026-11-25: change: `observability.PRODUCER = "urn:local-recipes:pyforge-atlas"`; `contract.md` § Lineage producer records the URN. The new test serializes every captured event with the OpenLineage client's `Serde` and found the `atlasNodeMetrics` run facet still carrying the client library's producer (the open row DW-E2-3), so `AtlasNodeMetricsRunFacet.__attrs_post_init__` now stamps `PRODUCER` when none is given (through `getattr`/`setattr`: mypy cannot see the base class's field where openlineage is not installed, and a `producer=` call argument reds the guild mypy lane). DW-E2-3 is met by this change; its ledger row is the session lead's to close. The client adds its own `tags` run facet with its own producer; the test excludes it by name. No namespace, schema URL or flag changed.
- 2026-11-25: tests added: 4 in `tests/unit/observability/test_observability_fixtures.py`, 1 in `tests/meta/test_public_contract.py`. Touched modules: observability, catalog `test_no_inline_io.py` and the contract meta-test, 51 passed, exit 0. Working-tree coverage gate (`coverage_gates_ci.py --paths-file`, the one AST-changed source module `pyforge.atlas.observability`, 92.9% in the package half): exit 0. `lint-types` for pyforge-atlas: ruff, ruff-format and mypy ok; the task as a whole exits 1 on `ruff-format` findings in pyforge-steward and pyforge-testing-kit files this story does not touch.
- 2026-11-25: AC1 exit 1 (no line matches, as expected); AC2 exit 0; AC3 exit 0 (2995 passed, 27 skipped; 53 passed, 5 skipped). `pyforge-atlas-live-test` exit 0. The memlog reconcile, the scoped stamp and the ledger row are the session lead's.
- 2026-11-25: closed. Implemented, independently reviewed against this spec (a read-only reviewer over the whole diff), its findings applied; the deferred-work row or rows are closed in their ledgers by the session lead, and the full local `pr-preflight` gates the PR that lands it (branch `named-blocker-rows-2026-11-25`).
