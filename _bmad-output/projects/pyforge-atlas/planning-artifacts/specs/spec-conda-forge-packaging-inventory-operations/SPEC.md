---
spec: conda-forge-packaging-inventory-operations
status: in-progress   # CAP-1 (17.1) chartered; CAP-2 (17.2) code landed, live-execution verification deferred (attended, credentialed run pending)
owner-dream: docs/dreams/conda-forge-packaging-inventory-operations.md
surface:            # 17.1 claims the quartet + data files (per-file, not a glob — a
                     # scripts/conda-forge-packaging-inventory-operations* glob would
                     # be the same invisible-by-construction breadth the 2026-08-08
                     # scripts/ allowlist split removed; see spec_surface_allowlist.txt)
  - scripts/conda-forge-packaging-inventory-operations_metrics.py
  - scripts/tests/test_conda_forge_packaging_inventory_operations_metrics.py   # Story 21.3 (atlas), 2026-08-30
  # Story 23.8 (atlas), 2026-08-30: the workbook-free inventory_universe fixture set
  - scripts/tests/fixtures/inventory_universe/generate_fixtures.py
  - scripts/tests/fixtures/inventory_universe/mini-workbook.xlsx
  - scripts/tests/fixtures/inventory_universe/catalog/derived/inventory_universe/inventory_universe.parquet
  - scripts/tests/fixtures/inventory_universe/catalog/intermediate/core_packages_enumerated/core_packages_enumerated.parquet
  - scripts/tests/fixtures/inventory_universe/catalog/intermediate/pypi_universe/pypi_universe.parquet
  - scripts/tests/fixtures/inventory_universe/catalog/primary/pypi_conda_mapping/pypi_conda_mapping.parquet
  - scripts/tests/fixtures/inventory_universe/catalog/raw/openteams_project_1_board_raw/openteams_project_1_board.parquet
  - scripts/conda-forge-packaging-inventory-operations_openteams_identity.py
  - scripts/conda-forge-packaging-inventory-operations_priority.py
  - scripts/openteams_identity_dashboards.py
  - conf/conda-forge-packaging-inventory-operations.local.env.example
  - conf/conda-forge-packaging-inventory-operations_curated_groups.json
companions:          # the other two named quartet members ("prompt"/"replay" in
                     # § Why); already covered separately by docs/reference/**'s own
                     # blanket allowlist entry, listed here for spec-internal
                     # cross-reference, not as a governance claim
  - ../../../../../../docs/reference/conda-forge-packaging-inventory-operations_prompt.md
  - ../../../../../../docs/reference/conda-forge-packaging-inventory-operations_replay.md
sources:
  - ../../../../../../docs/dreams/conda-forge-packaging-inventory-operations.md
open_questions: []   # parselmouth fold placement RESOLVED 2026-08-22 at 17.1 — see § Constraints
---

# SPEC — The packaging-inventory intake engine, governed

## Why
The quartet (runner/prompt/config/replay) and its data files already run in
`scripts/`+`conf/` but are spec-surface ALLOWLISTED with an explicit
"delete the line when a Spec claims them" rule — four stations
independently flagged them ungoverned. This pass charters the capability
the Dream describes: a repeatable from-scratch intake engine, never
consuming a previous consolidated inventory as input.

## Capabilities
- **CAP-1 — the governed from-scratch run.** Master Prompt v3.0 bound;
  clean-workspace regeneration from the workbook, live indexes, and curated
  feeds; every package with one PEP-503 identity, source provenance, and a
  timestamped verify decision; inspectable ranking (P1–P10 + Score 1–100 +
  work label); dated identity tabs (`identity-YYYY-MM-DD`, append-only) and
  the pinned secret gist (id via env, never git). *Success:* a clean run
  reproduces the inventory; the spec's `surface:` claims the quartet and
  the allowlist lines are DELETED.
- **CAP-2 — execution-ready handoffs.** The OpenTeams universe
  (`CDO-ENT-JFROG` ∪ `CDO-ENT-CONDA`): one `[Conda-Forge Packaging] {name}`
  issue per library + the dated Mason handoff tab
  (Fix vulnerability / Create recipe / File tracking issue / Already
  tracked); AOSS-Free names (PyPI-yes, conda-forge-no, CDO-no) as the extra
  Mason queue that never expands the universe. *Success:* Mason can consume
  a dated tab without asking questions; the three dashboard views render
  from the live identity tab.

## Constraints
Never consume a prior consolidated inventory; the quartet stays the ONE
toolchain (no second engine); gist id never in git; p2cf's three heuristics
(all-main-builds-broken, builds-from-PyPI-source, DoD auto-check) join as
enrichment signals per the 2026-08-22 fold charter. Parselmouth PyPI↔conda
mapping fold placement (RESOLVED 2026-08-22, Story 17.1): the core
pyforge-atlas `mapping_manager`/`name_resolver` chain is the fold target,
not this quartet — `..._openteams_identity.py`'s existing direct
purl-associator fetch (`ASSOCIATOR_URL`) is a separate, narrower join and
stays as-is; no code in this quartet folds parselmouth.

**Superseded 2026-08-31 (Story 21.7, atlas Epic 21 CAP-4):** the
`ASSOCIATOR_URL`-stays-in-quartet clause above no longer holds. That direct
purl-associator/OpenTeams-board/feedstock-outputs/staged-prs fetch is
retired: `..._openteams_identity.py`'s `main()` now reads the pyforge-atlas
Kedro catalog's `identity_export_parquet` (Story 21.6's `upstream_discovery`
Phase D join) via `PYFORGE_ATLAS_DATA_ROOT` — never a direct HTTP/GraphQL
call — and `--gist-only` merges ranking columns from the ranked identity tab
into that same Parquet-sourced data by name. See
`spec-atlas-kedro-catalog-expansion/identity-contract.md` for the join
semantics this quartet now consumes rather than performs. The Parselmouth
fold-placement resolution above is unaffected by this — Parselmouth's
PyPI↔conda mapping still folds into pyforge-atlas's
`mapping_manager`/`name_resolver` chain, not this quartet.

## Non-goals
The recipe work itself (Mason/CFE); the sibling org's issue-ledger
machinery; expanding the OpenTeams universe definition.

## Success signal
From-scratch to execution-ready queues in one governed run, surface claimed,
allowlist shrunk — and the next intake is a re-run, not a rebuild.
