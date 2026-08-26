---
title: First portal slice — one recall query
type: feature
created: '2026-08-25'
status: done
updated: '2026-08-26'
baseline_revision: c3f75232a15bb3c28730c546e8f955cda59054df
baseline_commit: c3f75232a15bb3c28730c546e8f955cda59054df
followup_review_recommended: true
context:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/change-history/sprint-change-proposal-2026-08-25-station-skill-portal.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-1-skf-domain-skills-from-station-packages.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-2-personas-act-only-through-grammar-and-mcp.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** Empty /stations/scribe/ does not run recall.

**Approach:** Submit one recall query and show cited results via PortalClient only.

## Acceptance Criteria

- Given an authenticated scribe-role session, when the operator submits a query, then results render via PortalClient only.
- Given src/platform/, when scanned, then no raw HTTP, no pyforge.* import, no chrome copy.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-scribe/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-scribe` only — never `scripts/bmad-switch`. Ledger key `5-2-first-portal-slice-recall-query`.

**Block If:** A change would replace `conda-forge-expert`, add `pyforge.*` under `src/platform/`, or start the paired Wave story this spec does not own.

**Never:** Raw HTTP. Chrome copy. Steward-only leftover UI.

</intent-contract>

## Code Map

- django-scribe
- PortalClient

## Tasks & Acceptance

**Execution:**
- [x] Implement the Approach. Add station-owned tests that fail if ACs are violated. Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 5.2 and the 2026-08-25 station-skill-portal SCP. Follow steward 29.1/29.2 for SKF+persona shape. Wave A stories must not edit `CLAUDE.md` / `AGENTS.md` except steward 33.1 via `skf-export-skill` after rebase if required.

## Spec Change Log

- 2026-08-25: drafted from epics.md for fleet drain preflight
- 2026-08-26: implemented first recall POST via PortalClient; station tests landed

## Review Triage Log

### 2026-08-26 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 1, medium 2, low 0)
- defer: 0
- reject: 0
- addressed_findings:
  - `[high]` `[patch]` Operator submit path was only AST-scanned; added `submit_recall` plus a running fake-client test that asserts cited `text`/`citation` land in the results fragment.
  - `[medium]` `[patch]` `parse_recall_cli` never executed; added cited and empty stdout cases.
  - `[medium]` `[patch]` PortalClient call contract untested; the fake client now records station/job/payload/sub/roles.

## Verification

**Commands:**
- station test suite for `pyforge-scribe` — expected: new tests pass
- `git diff origin/main -- src/platform` — expected: no `import pyforge` / `from pyforge`

## Auto Run Result

- Summary: `/stations/scribe/` POST submits one recall query through PortalClient only and renders cited `text` + `citation`. Host `src/platform/` is unchanged.
- Files changed:
  - `src/shared/packages/django-scribe/src/django_scribe_portal/views.py` — POST via `submit_recall(PortalClient(), …)`
  - `src/shared/packages/django-scribe/src/django_scribe_portal/recall_submit.py` — django-free PortalClient.call wrapper
  - `src/shared/packages/django-scribe/src/django_scribe_portal/templates/scribe_portal/home.html` — query form
  - `src/shared/packages/django-scribe/src/django_scribe_portal/templates/scribe_portal/results.html` — cited result fragment
  - `src/shared/packages/django-pyforge/src/django_pyforge/assertion/client.py` — `PortalClient.call` + `parse_recall_cli`
  - `src/shared/packages/pyforge-scribe/tests/meta/test_first_portal_slice.py` — station AC tests
  - this spec — status, triage, verification notes
- Review findings: 3 patches applied; 0 deferred; remaining hunter notes rejected (CLI timeout, empty-query guard, MCP transport, HTMX JS, 500 wrapping)
- Follow-up review recommendation: `true` (patched high 1, medium 2, low 0; score `3×2 + 1×0 = 6`)
- Verification: `pixi run -e pyforge-scribe pytest src/shared/packages/pyforge-scribe/tests/meta/test_first_portal_slice.py -q` → 5 passed; `git diff origin/main -- src/platform` → no `import pyforge` / `from pyforge`
- Residual risks: default runner shells public grammar in process cwd; assertion PEMs required; chrome `base.html` has no HTMX JS (plain POST still works)


**Commands:**
- station test suite for `pyforge-scribe` — expected: new tests pass
- `git diff origin/main -- src/platform` — expected: no `import pyforge` / `from pyforge`
