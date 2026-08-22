---
spec: conda-forge-packaging-inventory-operations
status: ready
owner-dream: docs/dreams/conda-forge-packaging-inventory-operations.md
surface: []   # 16.1 claims the quartet + data files and DELETES their allowlist lines
companions: []
sources:
  - ../../../../../../docs/dreams/conda-forge-packaging-inventory-operations.md
open_questions:
  - "parselmouth fold placement: the un-deferred mapping adoption naturally rides this chain's identity layer OR the core mapping_manager — decide at 16.1."
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
enrichment signals per the 2026-08-22 fold charter.

## Non-goals
The recipe work itself (Mason/CFE); the sibling org's issue-ledger
machinery; expanding the OpenTeams universe definition.

## Success signal
From-scratch to execution-ready queues in one governed run, surface claimed,
allowlist shrunk — and the next intake is a re-run, not a rebuild.
