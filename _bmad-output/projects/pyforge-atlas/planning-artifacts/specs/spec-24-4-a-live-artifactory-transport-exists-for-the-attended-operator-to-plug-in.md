---
title: 'A live Artifactory transport exists for the attended operator to plug in'
type: 'feature'
created: '2026-09-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/artifactory/aql_adapter.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `AqlTransport` (the sole HTTP seam `ArtifactoryAqlAdapter` takes) has only
`_unconfigured_transport` wired anywhere in the package. Story 25.2 needs "an attended operator
runs the pipelines end to end against live sources with the Artifactory credentials configured,"
but no live transport implementation exists for that operator to construct -- only the injectable
seam itself.

**Approach:** Add a `live_transport(base_url, *, api_key=None, username=None, password=None)`
factory beside the existing stub, resolving auth the same way `.claude/skills/conda-forge-expert/
scripts/_http.py` already does for JFrog elsewhere in this repo -- `JFROG_API_KEY` ->
`X-JFrog-Art-Api` header, else `JFROG_USERNAME`/`JFROG_PASSWORD` -> HTTP Basic -- performing
exactly one HTTP round-trip per `AqlRequest`.

## Boundaries & Constraints

**Always:**
- The concrete HTTP client stays constructed OUTSIDE package import time -- no top-level
  `requests`/`urllib` call, no credential read at import.
- The factory is called explicitly by the attended operator's own run, at run time only.
- Auth resolution mirrors `_http.py`'s existing JFrog convention exactly (same env var names,
  same header/Basic-auth split).

**Never:**
- Never runs Story 25.2's live pipeline or touches any credential value itself -- this story only
  makes the missing transport exist.
- Never reads credentials from anywhere but the caller-supplied arguments (the factory itself
  takes explicit params; env-var resolution is the CALLER's job at the Story 25.2 run site, not
  baked into this factory silently reading `os.environ`).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| API-key auth | `api_key` provided | `X-JFrog-Art-Api` header set | n/a |
| Username/password auth | `username`+`password` provided, no `api_key` | HTTP Basic auth header set | n/a |
| Neither configured | No `api_key`, no `username`/`password` | Raises a typed error naming which credential is missing | Typed error, not a silent no-op |
| Successful round-trip | A valid `AqlRequest` against a mocked transport | One HTTP call, `AqlResponse` shape returned | n/a |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-atlas/tools/live_artifactory_transport.py` -- new `live_transport` factory. NOT inside `src/pyforge/atlas/` -- that whole package tree is gated by `tests/unit/catalog/test_no_inline_io.py`'s `IO_DENYLIST` (bans `requests`/`urllib3`/`httpx`/etc. anywhere in package code, scanned via `ATLAS_PKG.rglob("*.py")`). `tools/` is the established sibling location for attended-operator scripts (mirrors `tools/bootstrap.py`).
- `src/shared/packages/pyforge-atlas/tests/tools/test_live_artifactory_transport.py` -- new test file (outside the scanned package tree, matching the module's own location).

## Tasks & Acceptance

**Execution:**
- `feature` -- add `live_transport(base_url, *, api_key=None, username=None, password=None)` factory.
- `feature` -- resolve auth mirroring `_http.py`'s JFrog convention (API-key header, else Basic auth).
- `feature` -- raise a typed error when neither credential is supplied.
- `feature` -- add tests covering all four I/O matrix scenarios with a mocked HTTP layer (no real network).

**Acceptance Criteria:**
- Given `AqlTransport` has only a stub wired anywhere, when a live transport factory is added mirroring `_http.py`'s JFrog auth convention, then it resolves API-key or Basic auth correctly, raises a typed error when neither is configured, and performs exactly one HTTP round-trip per request.
- No credential value or real network call is touched by this story's own tests.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: full suite green, including the new live_artifactory_transport tests

## Spec Change Log

- 2026-09-10: added the missing `## Verification` -> `**Commands:**` section. Its absence made `core.gate.check_spec_binding` (marshal Story 2.7, MRS-GATE-010) unconditionally refuse dispatch verification for any spec authored this way -- confirmed live against `spec-34-2`/`spec-21-13`'s own dispatch runs, which hit the identical refusal.

## Review Triage Log

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `24-4-a-live-artifactory-transport-exists-for-the-attended-operator-to-plug-in: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
