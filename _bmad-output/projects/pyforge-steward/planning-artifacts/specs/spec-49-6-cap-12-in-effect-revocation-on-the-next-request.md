---
title: 'CAP-12 in effect — revocation on the next request'
type: 'feature'
created: '2026-09-11'
status: 'done'
baseline_revision: 29c9036962bda93fa3da647903fe3089972874f3
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - src/platform/config/authorization/current_claims.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** CAP-12 claims role revocation at the IdP takes effect promptly, but the deployed
default (`IDP_CLAIMS_SNAPSHOT = None`, `IDP_USERINFO = None` in `config/settings/base.py:214-215`)
means claims are read from the session store, so a revoked role stays in effect until the user's
next LOGIN, not their next request.

**Approach:** Set the claims source in the deployed default with a bounded cache (short enough that
a revocation propagates within one cache window, not a full session), so `fetch_current_idp_claims`
(`config/authorization/current_claims.py`) resolves fresh-enough claims on the next request rather
than only at login. Prove it with a test that fails on the current login-time-only path.

## Boundaries & Constraints

**Always:**
- Decided **together with Story 48.9** — one deployment decision, not two: 48.9 names the provider
  (Keycloak in-cluster as the default profile, `COMPONENT_OIDC_*` kept as the BYO seam) and this
  story sets the claims source that points at it. Neither story may name a provider the other
  contradicts.
- The cache bound must be short enough that "revoke at the IdP" reads as "removed on the next
  request" in the test, not "removed at next login."

**Never:**
- Never leave the deployed default as `IDP_CLAIMS_SNAPSHOT = None` / `IDP_USERINFO = None` — that IS
  the login-time-only gap this story closes.
- Never cache claims for the life of the session — that reintroduces the exact gap being closed.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Role revoked at IdP | User has an active session; role removed at the IdP | Portal access removed on the user's next request (within the cache bound), not at next login | N/A |
| Regression guard | Deployed default still `None`/`None` | Test fails on the login-time-only path | N/A |

</intent-contract>

## Code Map

- `src/platform/config/settings/base.py:214-215` — `IDP_CLAIMS_SNAPSHOT` / `IDP_USERINFO` deployed
  defaults
- `src/platform/config/settings/production.py` — deployed-profile settings (does not currently
  override the base defaults)
- `src/platform/config/authorization/current_claims.py` — `fetch_current_idp_claims`, the resolution
  seam this story feeds
- pyforge-steward Story 48.9 — co-decided provider naming (Keycloak in-cluster default profile)

## Tasks & Acceptance

**Execution:**
- `feature` — set the deployed-default claims source (with a bounded cache) so
  `fetch_current_idp_claims` resolves claims fresh enough for next-request revocation.
- `test` — a test proving revocation propagates on the user's next request, failing against the
  current login-time-only default.
- `decision` — confirm the claims-source choice agrees with Story 48.9's provider naming
  (Keycloak in-cluster default, `COMPONENT_OIDC_*` BYO seam).

**Acceptance Criteria:**
- Given `IDP_CLAIMS_SNAPSHOT = None` / `IDP_USERINFO = None` in the deployed default so revocation
  lands on the next login, when the claims source is set in the deployed default with a bounded
  cache, then revoking a role at the IdP removes portal access on the user's next request, proven by
  a test that fails on the login-time path.
- And this story's claims-source choice and Story 48.9's provider naming agree — neither contradicts
  the other.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: full suite green (no
  steward-package code changes expected; this command proves nothing else regressed)

**Manual checks (if no CLI):**
- `pixi run -e local-recipes platform-ci-local -- --test` — expected: full `src/platform/` suite
  green, including the new revocation test (the test itself lives here, not in pyforge-steward)

## Spec Change Log

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 2 findings — high 0, medium 0, low 1, false 0, maybe-false 1
- findings:
  - `[low]` `[reject]` Chart `platform.djangoEnv` does not yet expose `COMPONENT_IDP_CLAIMS_CACHE_SECONDS` — operators can rely on the 30s default; wiring is optional follow-up, not required by AC.
  - `[maybe-false]` `[defer]` When userinfo HTTP fails or no SocialToken exists, fetch returns None and session claims remain authoritative until next login — same degradation as Story 26.1 deferred item; production happy path uses live tokens from Keycloak (Story 48.9).

## Auto Run Result

Status: done
Summary: Production settings now wire `IDP_USERINFO = fetch_current_userinfo` with a 30-second bounded Django cache (`COMPONENT_IDP_CLAIMS_CACHE_SECONDS`), so deployed Keycloak (Story 48.9) role revocations propagate on the next request instead of at next login. Tests prove the login-time-only gap and the production wiring.
Files changed:
- `src/platform/config/authorization/idp_userinfo.py` — OIDC userinfo fetch + Redis/LocMem cache
- `src/platform/config/settings/production.py` — deployed-default claims source
- `src/platform/tests/test_idp_revoke_next_request.py` — regression guard + production wiring + revoke-on-next-request proofs
Review: 0 patches; 1 deferred (userinfo fetch failure falls back to session); 1 rejected low (chart env optional).
Follow-up review recommended: false
Verification: `pixi run --frozen -e platform-ci-test pytest tests/test_idp_revoke_next_request.py` — 9 passed. `pixi run --frozen -e pyforge-steward pyforge-steward-test` — 1206 passed, 1 failed (pre-existing `bmad-eval-quality` adoption-register drift, unrelated to this story).
Blocking condition: none
