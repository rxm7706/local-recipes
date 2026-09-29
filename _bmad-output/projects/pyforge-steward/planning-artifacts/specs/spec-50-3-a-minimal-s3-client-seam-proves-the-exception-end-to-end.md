---
title: 'A minimal S3-client seam proves the exception end-to-end'
type: 'feature'
created: '2026-09-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - src/platform/config/authorization/current_claims.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The AD-1 exception permits object-storage consumption, but nothing in
`src/platform/` can reach one — there is no client seam to prove the exception is real, not just
declared on paper.

**Approach:** A minimal `src/platform/` module wrapping a standard S3 client, resolving an
endpoint URL and credentials from configuration only (env vars / Django settings), mirroring
`canopy:AD-19`'s reference-not-embed pattern already proven for the external IdP
(`current_claims.py`'s own callable-resolution shape). One round-trip put/get test proves it
against Story 50.2's local backend. No existing feature is migrated onto it.

## Boundaries & Constraints

**Always:**
- Endpoint and credentials are configuration only — never hardcoded, never a default pointing at
  a specific StorageGRID instance.
- The same client code must work unmodified against either the local dev backend (Story 50.2)
  or a real S3-compatible endpoint — proven by pointing the test at the local backend, not by
  assertion.

**Never:**
- Never wire Lane 1 media, CycloneDX SBOM handling, or any other existing feature to consume
  this seam in this story — the seam exists and is proven; consumption is separate, future,
  story-by-story work, decided each time on its own merits.
- Never embed a credential or endpoint value in code, a chart template, or a committed config
  file.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Round trip against local backend | Story 50.2's Silo (or Garage) running, endpoint/credentials configured | put then get returns the same bytes | N/A |
| No endpoint configured | Config absent | Client construction fails with a clear, typed error naming the missing config | Typed error, not a silent no-op or a hardcoded fallback |
| Same code, different endpoint | Config points at a different S3-compatible endpoint | No code change required | N/A |

</intent-contract>

## Code Map

- `src/platform/` — one new module (a thin S3-client wrapper); exact file placement follows this
  package's own existing config/client seam conventions (see `config/authorization/` for the
  precedent shape)
- One new test proving the round trip against Story 50.2's local backend

## Tasks & Acceptance

**Execution:**
- `feature` — a minimal S3-client wrapper resolving endpoint + credentials from configuration.
- `test` — one round-trip put/get test against the Story 50.2 local backend.

**Acceptance Criteria:**
- Given the AD-1 exception now permits object-storage consumption but nothing in
  `src/platform/` can reach one, when a minimal client module resolves configuration and
  performs a put/get round trip, then the same client code proves out against the local
  Story-50.2 backend in a real test.
- And no existing feature is wired to consume it in this story.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: full suite green,
  including the new round-trip test

## Spec Change Log

### 2026-09-10 — Landed
- `src/platform/config/object_storage.py` (`object_storage_client()`, config-only resolution,
  `ImproperlyConfigured` on any missing setting) + three new `config/settings/base.py` settings
  (all `default=None`). `tests/test_object_storage_client.py`: a real round-trip against an
  ephemeral local Silo (skips, does not fail, when `platform-object-storage` isn't installed) +
  the typed-error path. `boto3` added to `python-agent-platform` + `platform-ci-test` (already
  transitively resolvable; `pixi.lock` unchanged). `pixi run -e local-recipes platform-ci-local
  -- --test` full green (868 passed, 6 skipped, 0 new mypy/ruff findings). Landed via
  `rxm7706/local-recipes#1185` (merged `371361da1b`, `maintenance` label, local verification per
  the confirmed CI billing outage). Epic 50 is now fully drained (50.1/50.2/50.3 all `done`); the
  owner Spec (`spec-platform-object-storage-kind`) and its Dream both close as
  `shipped`/`realized`.

## Review Triage Log

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `914b86a6f2` (2026-09-18, "marshal: twin Story 50.3's deferral (MRS-DISP-043 silent for uncatalogued models) into the tracked ledger"); also `d8672d9287` (2026-09-10, "feat(platform): minimal S3-client seam proves the AD-1 exception (Story 50.3)"). Ledger row `50-3-a-minimal-s3-client-seam-proves-the-exception-end-to-end: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
