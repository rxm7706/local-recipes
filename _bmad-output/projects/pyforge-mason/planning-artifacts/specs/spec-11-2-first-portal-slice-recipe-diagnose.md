---
title: First portal slice — last diagnose
type: feature
created: '2026-08-25'
status: done
updated: '2026-08-26'
baseline_revision: c3f75232a15bb3c28730c546e8f955cda59054df
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/change-history/sprint-change-proposal-2026-08-25-station-skill-portal.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-1-skf-domain-skills-from-station-packages.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-2-personas-act-only-through-grammar-and-mcp.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Empty /stations/mason/ does not show diagnose output.

**Approach:** Show one mason diagnose (or equivalent) result via PortalClient only. No MinIO.

## Acceptance Criteria

- Given an authenticated mason-role session, when the operator opens /stations/mason/, then one diagnosis renders via PortalClient only.
- Given src/platform/, when scanned, then no raw HTTP, no pyforge.* import, no chrome copy, no MinIO.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-mason/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-mason` only — never `scripts/bmad-switch`. Ledger key `11-2-first-portal-slice-recipe-diagnose`.

**Block If:** A change would replace `conda-forge-expert`, add `pyforge.*` under `src/platform/`, or start the paired Wave story this spec does not own.

**Never:** MinIO. CFE replace. Raw HTTP. Chrome copy.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Mason GET | Authenticated mason-role request to `/stations/mason/` | 200; `#mason-last-diagnose` shows one last-diagnose (or equivalent) from `PortalClient.last_diagnose` | No error expected |
| Wrong role | Request lacks mason role | 403; no diagnose fetch | Forbidden, no PortalClient call required |
| Portal client only | django-mason Python tree | Uses `PortalClient`; no raw HTTP, no `pyforge.*`, no MinIO, no copied chrome | Test fails on offenders |

</intent-contract>

## Code Map

- `src/shared/packages/django-pyforge/src/django_pyforge/assertion/client.py` — `PortalClient.emit` (line 11); add in-process `last_diagnose` that emits RS256 then dispatches a registered job. Do not add HTTP.
- `src/shared/packages/django-mason/src/django_mason_portal/views.py` — `chrome_home` currently renders empty chrome; must call `PortalClient.last_diagnose` after `require_station_role("mason")`.
- `src/shared/packages/django-mason/src/django_mason_portal/templates/mason_portal/home.html` — keep `{% extends "django_pyforge/base.html" %}`; add `#mason-last-diagnose`.
- `src/shared/packages/django-mason/src/django_mason_portal/apps.py` — `MasonPortalConfig`; register the last-diagnose job in `ready()`.
- `src/shared/packages/django-mason/src/django_mason_portal/urls.py` — `""` → `chrome_home`.
- `src/shared/packages/django-pyforge/src/django_pyforge/access.py` — role gate already on the view.
- `src/platform/tests/test_station_portal_shells.py` — existing `/stations/mason/` shell; do not break `chrome_home` name.
- Read-only: `.claude/skills/conda-forge-expert/`, `CLAUDE.md`, `AGENTS.md`.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/django-pyforge/src/django_pyforge/assertion/client.py` — add in-process last-diagnose dispatch on `PortalClient` — portals must not open HTTP.
- `src/shared/packages/django-mason/src/django_mason_portal/` — register equivalent last diagnose, call it from `chrome_home`, render one result — empty shell is the bug.
- `src/shared/packages/pyforge-mason/tests/meta/test_portal_last_diagnose.py` — station AST + surface gates — fail if ACs are violated.
- `src/platform/tests/test_mason_portal_last_diagnose.py` — mason-role GET renders diagnose via PortalClient — outermost surface.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 11.2 and the 2026-08-25 station-skill-portal SCP. Follow steward 29.1/29.2 for SKF+persona shape. Wave A stories must not edit `CLAUDE.md` / `AGENTS.md` except steward 33.1 via `skf-export-skill` after rebase if required.

Last diagnose is an in-process PortalClient job, not CFE on GET and not MinIO. The equivalent snapshot is a portal projection so django-mason never imports `pyforge.mason`.

## Spec Change Log

- 2026-08-25: drafted from epics.md for fleet drain preflight
- 2026-08-26: planning pass — Code Map, I/O matrix, PortalClient.last_diagnose

## Review Triage Log

### 2026-08-26 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 0, low 1)
- defer: 0
- reject: 4
- addressed_findings:
  - `[low]` `[patch]` drop unused MinIO substring markers that false-positived on comments

## Auto Run Result

Status: done

Summary: `/stations/mason/` now renders one last-diagnose (or equivalent) through `PortalClient.last_diagnose` after a mason-role gate. The job is in-process (emit + verify + registered projection). No MinIO, no CFE replace, no raw HTTP, no `pyforge.*` under `src/platform/`, no chrome copy.

Files:
- `src/shared/packages/django-pyforge/src/django_pyforge/assertion/client.py` — `last_diagnose` + in-process job registry
- `src/shared/packages/django-mason/src/django_mason_portal/` — register job, call client from `chrome_home`, render `#mason-last-diagnose`
- `src/shared/packages/pyforge-mason/tests/meta/test_portal_last_diagnose.py` — station AST/surface gates
- `src/platform/tests/test_mason_portal_last_diagnose.py` — mason-role render + forbidden-without-client
- `planning-artifacts/specs/spec-11-2-….md` — tracked story spec

Review: 1 low patch applied; follow-up score 1 → false. Rejected live CFE-on-GET, Client+Postgres E2E, HTMX hx- extras, and generic multi-station PortalClient jobs.

Verification: 5 passed (`test_portal_last_diagnose.py`); 4 + assertion suite 23 passed under `platform-ci-test`. `git diff origin/main -- src/platform` has no `pyforge` imports.

Residual risks: last diagnose is a portal-owned equivalent snapshot, not a live `mason recipe diagnose <log>` CFE run.

## Verification

**Commands:**
- `pixi run -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/meta/test_portal_last_diagnose.py -q` — expected: all pass
- `pixi run -e local-recipes pytest src/platform/tests/test_mason_portal_last_diagnose.py src/platform/tests/test_station_portal_shells.py -q --ds=config.settings.test` — expected: all pass
- `git diff origin/main -- src/platform` — expected: no `import pyforge` / `from pyforge`
