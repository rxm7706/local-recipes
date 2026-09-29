---
title: First portal slice — provision inventory
type: feature
created: '2026-08-25'
status: done
updated: '2026-08-26'
review_loop_iteration: 1
baseline_revision: c3f75232a15bb3c28730c546e8f955cda59054df
baseline_commit: c3f75232a15bb3c28730c546e8f955cda59054df
followup_review_recommended: true
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/change-history/sprint-change-proposal-2026-08-25-station-skill-portal.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-1-skf-domain-skills-from-station-packages.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-2-personas-act-only-through-grammar-and-mcp.md
warnings: []
deferred:
  - summary: >-
      django-pyforge chrome base.html does not vendor htmx.min.js, so hx-* on
      the steward inventory section is markup-only until chrome loads HTMX.
    evidence: |-
      src/shared/packages/django-pyforge/src/django_pyforge/templates/django_pyforge/base.html
      has theme.css and the switcher, not an HTMX script. Pre-existing; this
      story server-renders inventory on GET /stations/steward/.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/templates/django_pyforge/base.html
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Empty /stations/steward/ does not show provision --list.

**Approach:** GET /stations/steward/ HTMX renders named pixi environments from provision --list via PortalClient only.

## Acceptance Criteria

- Given an authenticated steward-role session, when the operator opens /stations/steward/, then HTMX renders the environment inventory via django-pyforge PortalClient only.
- Given src/platform/ and django-steward, when reviewed, then no raw HTTP, no pyforge.* import under src/platform/, no chrome copy in django-steward.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-steward/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`. Ledger key `33-2-first-portal-slice-provision-list`.

**Block If:** A change would replace `conda-forge-expert`, add `pyforge.*` under `src/platform/`, or start the paired Wave story this spec does not own.

**Never:** Raw HTTP. pyforge.* under src/platform/. Chrome copy.

</intent-contract>

## Code Map

- django-steward
- PortalClient
- steward provision --list

## Tasks & Acceptance

**Execution:**
- [x] Implement the Approach. Add station-owned tests that fail if ACs are violated. Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 33.2 and the 2026-08-25 station-skill-portal SCP. Follow steward 29.1/29.2 for SKF+persona shape. Wave A stories must not edit `CLAUDE.md` / `AGENTS.md` except steward 33.1 via `skf-export-skill` after rebase if required.

## Spec Change Log

- 2026-08-25: drafted from epics.md for fleet drain preflight

## Review Triage Log

### 2026-08-26 — Implementer self-review (no child reviewers in this worktree)

- intent_gap: 0
- bad_spec: 0
- patch: 2 (33.1 Wave-B fence retired so 33.2 can own django-steward; HTMX section is first-GET render, not a second hx-get)
- defer: 0
- reject: reviewer-layer "spawn subagents" (unavailable under the implementer)

### 2026-08-26 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 2, low 0)
- defer: 1: (high 0, medium 1, low 0)
- reject: 13
- addressed_findings:
  - `[medium]` `[patch]` Home test stubbed `render` so HTMX inventory HTML was never observed — now compiles `steward_portal/home.html` and asserts `data-environment` plus `#steward-provision-list`.
  - `[medium]` `[patch]` `provision_list()` default cwd (`repo_root`) was untested — added `test_portal_client_provision_list_default_cwd_uses_repo_root`.

## Auto Run Result

- Summary: Authenticated `GET /stations/steward/` loads named pixi environments through `PortalClient.provision_list()` (in-process `provision --list`) and server-renders them in an HTMX-marked section. No raw HTTP, no `pyforge.*` under `src/platform/`, no chrome copy in django-steward.
- Files changed:
  - `django-steward` `views.py` — steward home calls `PortalClient().provision_list()`.
  - `django-steward` `home.html` — `#steward-provision-list` inventory.
  - `django-pyforge` `PortalClient.provision_list` — wraps `load_pixi_environments`.
  - `django-pyforge` `assertion/__init__.py` — lazy JWT helpers so PortalClient imports without PyJWT.
  - `pyforge-steward` `test_first_portal_slice_provision_list.py` — station AC tests.
  - `pyforge-steward` `test_skf_steward_skill.py` — Wave B ownership of django-steward.
  - this spec — review + auto-run result.
- Review findings breakdown: 2 medium patches applied; 1 medium deferred (chrome missing HTMX script); other reviewer items rejected as extra readings (hx-get fragment, emit-to-station, degrade-on-missing-pixi.toml) or incorrect (console-home dropped).
- Follow-up review recommendation: true (patched medium 2, low 0; score `3×2 + 1×0 = 6`).
- Verification: station meta suite 32 passed; `git diff origin/main -- src/platform` has no `import pyforge` / `from pyforge`.
- Residual risks: inventory is in-process TOML via PortalClient, not `emit` + MCP; HTMX attributes do not fetch a fragment; chrome still does not vendor `htmx.min.js`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Suggested Review Order

**Entry — portal GET**

- Authenticated steward home loads inventory only through PortalClient.
  [`views.py:13`](../../../../../src/shared/packages/django-steward/src/django_steward_portal/views.py#L13)

**Inventory via PortalClient**

- In-process `provision --list` data; no HTTP on the client.
  [`client.py:33`](../../../../../src/shared/packages/django-pyforge/src/django_pyforge/assertion/client.py#L33)

**HTMX surface, no chrome copy**

- Extends django-pyforge chrome; named environments in an HTMX section.
  [`home.html:6`](../../../../../src/shared/packages/django-steward/src/django_steward_portal/templates/steward_portal/home.html#L6)

**Station-owned AC tests**

- Fail if PortalClient is skipped, raw HTTP appears, chrome is copied, or platform imports pyforge.
  [`test_first_portal_slice_provision_list.py:78`](../../../../../src/shared/packages/pyforge-steward/tests/meta/test_first_portal_slice_provision_list.py#L78)
