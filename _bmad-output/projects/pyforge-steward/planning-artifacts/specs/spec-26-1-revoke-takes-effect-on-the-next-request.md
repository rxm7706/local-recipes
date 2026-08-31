---
title: Revoke takes effect on the next request
type: feature
created: '2026-08-25'
status: done
updated: '2026-08-25'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-18-2-the-switcher-shows-only-what-the-user-may-reach.md
  - src/shared/packages/django-pyforge/src/django_pyforge/roles.py
  - src/shared/packages/django-pyforge/src/django_pyforge/middleware.py
  - src/platform/config/authorization/adapters.py
warnings: []
baseline_revision: cef7f261f6b
review_loop_iteration: 0
followup_review_recommended: false
deferred:
  - summary: >-
      Production still has no live Keycloak userinfo/introspection HTTP client;
      revoke is proven via IDP_CLAIMS_SNAPSHOT and IDP_USERINFO hooks.
    evidence: |-
      fetch_current_idp_claims prefers snapshot, then IDP_USERINFO, then the
      session claims document from login. Without a hook, login continuity
      still uses that document until the operator wires userinfo.
    location: >-
      src/platform/config/authorization/current_claims.py
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Portal access still follows the login-time session role snapshot. A security officer who revokes an IdP role must not wait for the user to log in again (FR-31, CAP-12, canopy AD-15).

**Approach:** Re-read IdP roles from the token claims on each request. Switcher and station gates from 18.2 honor that fresh token. Django group tables and the login-time `idp_token_roles` session list are not the authority.

## Boundaries & Constraints

**Always:** Authorization is the current request's IdP token claims (test double: `IDP_CLAIMS_SNAPSHOT` / `idp_token_claims`; production hook: `IDP_USERINFO`). Cite canopy AD-15. Specs under `_bmad-output/projects/pyforge-steward/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only.

**Block If:** Implementation would require a live Keycloak cluster, Token Exchange, or renaming `compliance_face`.

**Never:** Stories 26.2–26.4. Story 18.3 JWT client rework. Wagtail admin group middleware as the portal gate. `import pyforge` / `pyforge.*` under `src/platform/`. `scripts/bmad-switch`. `bmad-loop`. Other stations' ledgers.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Next request denied | User opened portal; IdP claims then omit the station role; same session, no logout | Station `chrome_home` returns 403; switcher omits that station | 403 Forbidden |
| Groups not authority | `User.groups` still contains the station name; live token claims omit it | Request denied; groups accessors are never consulted | Groups ignored |
| Session snapshot ignored | Session `idp_token_roles` still lists the station; live token claims empty | Request denied | Session list ignored |
| Check absent fails | Live token lacks the station role | Test fails if `require_station_role` / token re-read is removed | Assertion failure |

</intent-contract>

## Code Map

- `src/shared/packages/django-pyforge/src/django_pyforge/roles.py` — claims-first `roles_from_request`; do not treat `idp_token_roles` as authority
- `src/shared/packages/django-pyforge/src/django_pyforge/middleware.py` — populate `idp_roles` from current token claims, not the login snapshot
- `src/shared/packages/django-pyforge/src/django_pyforge/access.py` — keep `require_station_role`; it must see fresh roles
- `src/platform/config/authorization/current_claims.py` — **new** getter: snapshot, then userinfo, then session claims document
- `src/platform/config/authorization/adapters.py` — also persist `idp_token_claims` at login (continuity); roles list stays non-authoritative
- `src/platform/config/settings/base.py` — `DJANGO_PYFORGE_IDP_CLAIMS_GETTER`, `DJANGO_PYFORGE_GROUP_CLAIM`, `IDP_CLAIMS_SNAPSHOT`, `IDP_USERINFO`
- `src/platform/tests/test_idp_revoke_next_request.py` — **new** matrix; BoomGroups; mutate claims between requests
- `src/platform/tests/test_django_pyforge_chrome.py` — middleware no longer grants from `idp_token_roles`
- `src/platform/tests/test_oidc_identity.py` — adapter still writes session keys
- `src/platform/tests/meta/test_no_pyforge_import.py` — read-only

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/django-pyforge/src/django_pyforge/roles.py` — re-read roles from this request's token claims
- `src/shared/packages/django-pyforge/src/django_pyforge/middleware.py` — ignore login snapshot as authority
- `src/platform/config/authorization/current_claims.py` — IdP claims getter (snapshot / userinfo / session claims doc)
- `src/platform/config/authorization/adapters.py` — store claims document at login
- `src/platform/config/settings/base.py` — wire getter and group-claim name
- `src/platform/tests/test_idp_revoke_next_request.py` — cover the I/O matrix
- `src/platform/tests/test_django_pyforge_chrome.py` — session role list is not a grant

**Acceptance Criteria:**
- Given a user who can open a portal, when the role is revoked at the IdP, then the next request is denied without a re-login.
- Given Django group membership that would permit the station, when the live token omits that role, then access is denied.
- Given a leftover session `idp_token_roles` list, when live token claims are empty, then access is denied.
- Given the token re-read or station role check is removed, when the revoke tests run, then they fail.

## Spec Change Log

## Review Triage Log

### 2026-08-25 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 1, low 0)
- defer: 1: (high 0, medium 1, low 0)
- reject: 8
- addressed_findings:
  - `[medium]` `[patch]` `roles_from_request` must fail if session `idp_token_roles` is consulted (`test_roles_from_request_ignores_session_role_list`)

## Design Notes

The 18.2 session key `idp_token_roles` is a leftover snapshot. Live authority is token claims on this request. Tests install `IDP_CLAIMS_SNAPSHOT` (or `IDP_USERINFO`) to mutate IdP claims between requests while leaving the session cookie, session role list, and `User.groups` intact.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done
Summary: Portal switcher and station `chrome_home` re-read IdP roles from this request's token claims. A revoke (snapshot or userinfo hook) denies the next request without logout. Django groups and session `idp_token_roles` are not the authority.
Files changed:
- `django_pyforge/roles.py` — claims-first `roles_from_request`
- `django_pyforge/middleware.py` — no grant from login role list
- `config/authorization/current_claims.py` — snapshot / userinfo / session claims document
- OIDC adapter — persist `idp_token_claims` at login
- settings — getter + group-claim name
- `test_idp_revoke_next_request.py` — I/O matrix
- chrome middleware test — session role list is not a grant
Review: 1 medium patch; 1 deferred (live Keycloak userinfo HTTP); 8 rejected (Wagtail groups, 18.3 JWT, nested claim paths, 26.2–26.4).
Follow-up review recommended: false (1 × medium patch; score 3).
Verification: `platform-ci-test` pytest revoke + chrome + no-pyforge-import — 20 passed. ruff clean on new files.
Residual: without `IDP_USERINFO`, login continuity still reads the session claims document.
Blocking condition: none
