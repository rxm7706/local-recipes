---
title: Identity is OIDC-delegated, no local passwords
type: feature
created: '2026-08-23'
status: done
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: 9b488aee70
---

<intent-contract>

## Intent

**Problem:** Platform still uses local-password auth (CAP-1 / `spec-platform-fifteen-factors`). Identity must be OIDC-delegated with Keycloak realm-as-code local substrate (devinfra pattern).

**Approach:** Identity keyed on `idp_subject`; `is_staff`/`is_superuser` derive from IdP group claims per-authentication (unmatched groups ignored-and-logged). Retire local passwords and createsuperuser doc-path. Provide local-dev persona/JWT minting path. End-to-end login proven locally in tests. Deps: 16.2 done. Do not implement Epic 17.

## Acceptance Criteria

- Login flows through IdP end-to-end locally (tests or documented dev path).
- User identity keyed on `idp_subject`; staff/superuser from group claims per auth.
- Local passwords and createsuperuser doc-path retired.
- Local-dev JWT/persona minting path exists for tests/dev.
- AD-4/pap:AD-17 topology and chart 12.1 preserved (factors as seams).
- Does not implement steward 12-7 or Epic 17.

## Boundaries & Constraints

**Never:** Chart rewrites beyond env/values seams. Never `scripts/bmad-switch`. Finalize steward ledger only. Do not touch marshal 20-8. Skip 12-7 forever.

</intent-contract>

## Code Map

- `src/platform/` auth backends, user model (`idp_subject`), settings
- Keycloak realm-as-code local substrate (devinfra pattern)
- Docs: retire createsuperuser path
- Tests: OIDC login flow, group-claim staff derivation

## Verification

- E2E or integration test: OIDC login locally
- Unmatched groups ignored-and-logged
- Related platform tests green locally

## Auto Run Result

Status: done
Reconciled 2026-09-20: `shipped` is the Spec-level word; a story's terminal state is `done` (ledger row `16-5-identity-is-oidc-delegated-no-local-passwords: done`).
PR: https://github.com/rxm7706/local-recipes/pull/696
Merge SHA: eb3ab8c95dcb562e2ce0b1e25170acbaa4c73b2b
CI: GitHub Actions billing blocked — admin merge after local tests green
Tests: 57 passed (OIDC + policy + startup + health); 107 passed full `tests/` (langflow mount excluded)
Finalize SHA: d5030f4f82
Blocking condition: none

## Status reconcile 2026-09-20

- frontmatter `status` `shipped` → `done` (ledger row `16-5-identity-is-oidc-delegated-no-local-passwords: done`).
- Auto Run Result `Status: shipped` → `done` (see the reconcile line under it).
