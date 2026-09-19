---
id: SPEC-sprint-ledger-query-module
spec: sprint-ledger-query-module
status: ready
created: "2026-09-19"
updated: "2026-09-19"
owner-dream: docs/dreams/sprint-ledger-query-module.md
---

# Spec: Pluggable Estate Sprint Ledger Query Module, Work Passports & Ecosystem Integration

## Intent

**Problem:** Sprint ledgers and `epics.md` files across all eight stations are fragmented, requiring ad-hoc manual scans. Operators, agent tools, execution runners, and dashboards need a unified, pluggable, feature-flagged, and multi-system telemetry engine.

**Approach:** Implement `pyforge.steward.sprint_ledger_query` in `pyforge-steward` with a plugin architecture (`QueryFormatterPlugin`, `LedgerSourcePlugin`, `LedgerQueryHook`), OpenFeature SDK feature flag evaluation, Work Passports UUID minting, Django Admin/HTMX views, and multi-system exporters for Jira, GitHub, bmad-dashboard, Marshal, Herald, and Atlas.

## Boundaries & Constraints

**Always:**
- Work Passport identity is a minted UUID (`passport_id`). Jira keys and GitHub item/issue numbers are external nicknames/aliases.
- Preserve canopy AD-13/AD-23 boundary invariant: `pyforge-steward` never imports `vizro` directly. Steward exports data payloads; Atlas renders Vizro pages.
- Enforce strict `stdout` vs `stderr` separation in CLI outputs so JSON payloads parse cleanly for `bmad-dashboard` VS Code Extension (VSX) and Web views.

**Never:**
- Never hardcode public URLs or unauthenticated remote endpoints.
- Never mix `meta.yaml` and `recipe.yaml`.

## Interface Specifications

- **Module API:** `pyforge.steward.sprint_ledger_query.SprintLedgerQueryEngine`
- **CLI Duty:** `steward ledger-query`
- **Pixi Task:** `pixi run -e local-recipes sprint-ledger-query`
- **BMAD Skill:** `.claude/skills/bmad-sprint-ledger-query/SKILL.md`
