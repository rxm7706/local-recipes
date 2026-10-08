---
title: First portal slice — one recall query
type: feature
created: '2026-08-25'
status: done
updated: '2026-10-08'
baseline_revision: c3f75232a15bb3c28730c546e8f955cda59054df
baseline_commit: c3f75232a15bb3c28730c546e8f955cda59054df
followup_review_recommended: false
review_loop_iteration: 0
deferred:
  - summary: >-
      MCP run_recall remains a stub; portal slice AC targets /stations/scribe/ POST only.
    evidence: |-
      django_scribe_portal/mcp_asgi.run_recall returns synthetic completed payload without PortalClient recall job; out of Story 5.2 intent contract.
    location: >-
      src/shared/packages/django-scribe/src/django_scribe_portal/mcp_asgi.py
    severity: low
  - summary: >-
      Real PortalClient.call through emit/verify/subprocess recall still lacks a golden-PEM integration test.
    evidence: |-
      Follow-up patched chrome_home POST with mocked submit_recall; subprocess argv wiring in django_pyforge.assertion.client._grammar_recall remains unexercised in tests (grep shows no scribe recall PortalClient.call test).
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/assertion/client.py
    severity: medium (unverified)
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

### 2026-10-08 — Review pass (follow-up, `followup_pass`)
- verdicts: 28 findings — high 0, medium 1, low 2, false 14, maybe-false 0, reject 11
- findings:
  - `[false]` `[reject]` MCP run_recall stub vs portal recall — mcp_asgi is outside Story 5.2 portal slice AC; stub unchanged by this pass.
  - `[false]` `[reject]` Subprocess recall ignores returncode — `_grammar_recall` behavior predates follow-up; 2026-08-26 pass rejected CLI failure wrapping.
  - `[false]` `[reject]` Subprocess recall has no timeout — same carried rejection as 2026-08-26 residual risks.
  - `[false]` `[reject]` sub/roles not passed into scribe CLI argv — `submit_recall` passes sub/roles into `PortalClient.call`; job uses payload query only by design for first slice.
  - `[low]` `[reject]` No mode/scope in portal form — first slice AC is one query; grammar tests cover optional mode elsewhere.
  - `[false]` `[reject]` chrome_home uncaught exceptions → 500 — 2026-08-26 triage rejected 500 wrapping; assertion failures should surface.
  - `[false]` `[defer]` JWKS/verify collateral lacks unit tests in diff — assertion bundle not owned by Story 5.2; platform tests cover mint/verify.
  - `[false]` `[defer]` JWKS kid/EC algorithms — IdP contract outside portal slice.
  - `[low]` `[reject]` results.html omits grounded flag — ungrounded answers still render text; not required by AC cited fields.
  - `[false]` `[defer]` EVENTS_AUDIENCE unused — unrelated steward/schema collateral in scoped diff.
  - `[false]` `[defer]` parse_recall_cli overwrites multi-citation — pre-existing parser; no AC for multi-cite portal UI.
  - `[false]` `[defer]` register_portal_job at import — shared django-pyforge pattern.
  - `[false]` `[reject]` MCP payload uses target not query — MCP out of slice scope.
  - `[medium]` `[patch]` Verification gap: no test executes chrome_home POST — added `test_chrome_home_post_renders_cited_recall_results` with RequestFactory, role gate, HX branch, Django template render.
  - `[medium]` `[patch]` Verification gap: template check used manual replace — same new test renders `results.html` via Django `Engine`.
  - `[medium]` `[defer]` Verification gap: no golden-PEM PortalClient.call subprocess test — deferred to frontmatter (subprocess integration).
  - `[false]` `[reject]` Edge: subprocess timeout — duplicate of blind hunter; rejected.
  - `[false]` `[reject]` Edge: non-zero exit ignored — duplicate; rejected.
  - `[false]` `[defer]` Edge: parse sentinel vs citation — parser edge pre-existing.
  - `[false]` `[defer]` Edge: multi citation overwrite — pre-existing.
  - `[false]` `[defer]` Edge: missing pyforge/scribe binary — deploy concern, not portal slice.
  - `[false]` `[defer]` Edge: last_diagnose KeyError — mason/diagnose path, not scribe recall.
  - `[false]` `[defer]` Edge: list_loop_homes symlink — marshal collateral in diff.
  - `[false]` `[defer]` Edge: JWKS JSON decode — assertion collateral.
  - `[false]` `[defer]` Edge: verify iat/exp int — assertion collateral.
  - `[false]` `[reject]` Edge claim: POST 500 on submit_recall — rejected with 2026-08-26 500 policy.
  - `[false]` `[reject]` Edge claim: MCP stub — defer not patch.
  - `[false]` `[reject]` Edge claim: full src/platform scan — `test_src_platform_has_no_pyforge_import` follows branch diff-guard pattern (c9bcbaf516); platform tree unchanged in story.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

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

### 2026-10-08 — Follow-up auto run (`bmad-build-auto`, dispatch/pyforge-scribe/5.2)
- Summary: Independent follow-up review on landed portal slice; closed verification gap on `chrome_home` POST + HTMX results template rendering.
- Files changed:
  - `src/shared/packages/pyforge-scribe/tests/meta/test_first_portal_slice.py` — `test_chrome_home_post_renders_cited_recall_results` (role gate, POST, HX-Request, Django template engine)
  - `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/.memlog.md` — surface reconcile entry
  - `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md` — co-governor surface entry
  - this spec — follow-up triage, deferred rows, Auto Run Result
- Review findings: 2 patched (medium verification-gap); 2 deferred (MCP stub, subprocess PortalClient integration); 24 rejected/false/defer as logged
- Follow-up review recommendation: `false` (follow-up pass; no high patches)
- Verification: `pixi run -e pyforge-scribe pytest src/shared/packages/pyforge-scribe/tests/meta/test_first_portal_slice.py -q` → 7 passed, 1 skipped; `python scripts/spec_surface_reconcile.py` → exit 0
- Residual risks: real `PortalClient.call` → subprocess recall still untested end-to-end; MCP recall stub unchanged


**Commands:**
- station test suite for `pyforge-scribe` — expected: new tests pass
- `git diff origin/main -- src/platform` — expected: no `import pyforge` / `from pyforge`
