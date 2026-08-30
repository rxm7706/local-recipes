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

## Non-goals
The recipe work itself (Mason/CFE); the sibling org's issue-ledger
machinery; expanding the OpenTeams universe definition.

## Success signal
From-scratch to execution-ready queues in one governed run, surface claimed,
allowlist shrunk — and the next intake is a re-run, not a rebuild.
