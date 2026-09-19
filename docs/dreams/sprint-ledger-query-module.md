---
id: DREAM-sprint-ledger-query-module
status: dreamt
owning-station: pyforge-steward
created: 2026-09-19
updated: 2026-09-19
kinships:
  - pyforge-steward
  - pyforge-marshal
  - pyforge-herald
  - pyforge-atlas
  - bmad-dashboard
---

# Dream: Pluggable Estate Sprint Ledger Query Module, Work Passports, and Ecosystem Integrations

The PyForge estate consists of eight active stations, each maintaining its own tracked sprint status ledger (`sprint-status-ledger.yaml`) and `epics.md` planning chain. Operators, AI agent frameworks, execution runners, and dashboard surfaces currently lack a unified, pluggable, and feature-flagged query engine to inspect, filter, audit, and export story and epic telemetry across all stations.

## The Aspiration

Provide a single, highly extensible Python query engine (`pyforge.steward.sprint_ledger_query`) in `pyforge-steward`, accompanied by a `steward` CLI duty, a `pixi` task (`sprint-ledger-query`), and a BMAD skill (`bmad-sprint-ledger-query`).

Key capabilities:
1. **Multi-Station Query & Presets:** Filter by status (`--status`), presets (`--unimplemented`, `--blocked`, `--in-flight`, `--done`), station (`--station`), epic (`--epic`), or text query (`--query`).
2. **Pluggable & Hookable Architecture:** Abstract plugin interfaces for formatters (`QueryFormatterPlugin`) and sources (`LedgerSourcePlugin`), plus lifecycle hooks (`LedgerQueryHook`: `pre_query`, `post_query`, `on_export`).
3. **Feature Flags:** OpenFeature SDK (`openfeature-sdk`) + `flagd` FILE provider (`flags.json`) for toggling capabilities (`enable_postgres_sync`, `enable_dossier_export`, `enable_vizro_dataset`, `enable_herald_facts`, `enable_jira_github_matrix`).
4. **Work Passports & PostgreSQL Persistence (Epic 61 Alignment):** Mint UUID primary identities (`passport_id`) bound to Jira keys and GitHub item/issue aliases, persisting telemetry into PostgreSQL (`WorkPassport`, `StoryLedgerEntry`).
5. **Django Admin & HTMX Reactive Portal Views:** Register `WorkPassportAdmin` in Django Admin and supply HTMX reactive views (`/dashboard/backlog/`).
6. **Ecosystem Exporters & Connectors:**
   - `bmad-dashboard` (VS Code Extension & Web): Schema-validated JSON payload (`$id: urn:local-recipes:pyforge-steward:sprint-ledger-query-schema`).
   - `PyForge Marshal`: `get_runnable_backlog()` helper for autonomous dispatch.
   - `PyForge Herald`: Static HTML Dossier (`docs/dashboard/sprint-backlog/index.html`) & Herald facts (`presentations/sprint-backlog/facts.yaml`).
   - `PyForge Atlas`: Vizro data connector (`_bmad-output/projects/pyforge-atlas/data/sprint_telemetry.json`).
   - `Jira Cloud & GitHub Projects V2`: 3-way sync matrix (`--format sync-matrix`), unlinked detection (`--unlinked`), Jira CSV bulk import export, and GitHub GraphQL payload export.
