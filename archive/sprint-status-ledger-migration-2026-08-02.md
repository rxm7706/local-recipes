# Sprint Status Ledger Migration — 2026-08-02

## Change Summary

Migrated from hand-maintained, unstructured `sprint-status-ledger-{slug}.yaml` files to machine-readable, structured `sprint-status-{slug}.yaml` format.

## Rationale

**Legacy format (ledger):**
- Loose YAML with arbitrary keys and historical entries
- Difficult to parse for CI/CD integration
- No standard schema; each station interpreted differently
- Velocity/metrics calculations required manual parsing

**New format (status):**
- Structured YAML with defined schema
- Machine-readable for CI/CD gates and dashboards
- Standardized across all 8 stations
- Supports metric extraction, readiness checks, gate enforcement

## Migration Details

**Date:** 2026-08-02  
**Scope:** All 9 ledger files (8 stations + 1 root)

| Station | Archived Path |
|---------|---------------|
| atlas | `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/sprint-status-ledger.yaml` |
| doctor | `archive/_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml` |
| genesis | `archive/_bmad-output/projects/pyforge-genesis/planning-artifacts/sprint-status-ledger.yaml` |
| herald | `archive/_bmad-output/projects/pyforge-herald/planning-artifacts/sprint-status-ledger.yaml` |
| marshal | `archive/_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml` |
| mason | `archive/_bmad-output/projects/pyforge-mason/planning-artifacts/sprint-status-ledger.yaml` |
| scribe | `archive/_bmad-output/projects/pyforge-scribe/planning-artifacts/sprint-status-ledger.yaml` |
| steward | `archive/_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml` |
| warden | `archive/_bmad-output/projects/pyforge-warden/planning-artifacts/sprint-status-ledger.yaml` |

## Code Changes

**Generator update** (`docs/dashboard/generate.py`):
- Removed `sprint-status-ledger-{slug}.yaml` pattern from `_stage_globs()`
- Kept only `sprint-status-{slug}.yaml` pattern
- Generator now looks for new format exclusively

## Access

Historical ledger data is preserved in `/archive/` for reference but is no longer part of active pipelines.

New tool entry point: `_bmad-output/projects/{slug}/planning-artifacts/sprint-status-{slug}.yaml`

## Related Decisions

- **Schema versioning:** New format uses YAML frontmatter + structured sections for durability
- **Backfill:** Existing stories' progress tracked in `sprint-status-ledger*.yaml` artifacts gitignored during dev
- **Transition:** No data loss; old ledger is queryable via git history if needed
