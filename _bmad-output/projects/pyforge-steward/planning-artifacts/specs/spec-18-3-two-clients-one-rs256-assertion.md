---
title: Two clients, one RS256 assertion
type: feature
created: '2026-08-24'
status: done
baseline_revision: f55f8e116fa8eb81737bec1ba8cb7a6a645a0b3b
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
deferred:
  - summary: >-
      Host mint parses an IdP JWT payload without verifying signature, issuer,
      or expiry. Live Keycloak Token Exchange remains Deferred.
    evidence: |-
      identity_from_idp_bearer base64-decodes the payload. Spec Block If /
      Never Keycloak Token Exchange. Tests use a three-segment fake JWT.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/assertion/identity.py
    severity: high
  - summary: >-
      AssertionMiddleware is host-global; an ingress that always sets
      X-Forwarded-User will 401 browser routes that have no service assertion.
    evidence: |-
      Identity-header AC is anti-spoof, not a full service gate. Ingress
      should not inject those headers on interactive chrome.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/assertion/middleware.py
    severity: medium
  - summary: >-
      PortalClient only signs; it does not perform the outbound HTTP call to a
      station service. AST bans portal-local HTTP clients instead.
    evidence: |-
      Intent also admits an emitter-plus-scan reading; Epic 19.2 owns remaining
      portal shells calling through the client.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/assertion/client.py
    severity: medium
  - summary: >-
      Production PYFORGE_ASSERTION_* keys default empty; no rotation, kid, or
      env documentation in this story.
    evidence: |-
      Sign/verify fail at call time if unset. Test settings inject golden PEMs.
    location: >-
      src/platform/config/settings/base.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** Station services cannot independently verify who called them. A trusted identity header, HMAC-SHA256, or a laptop-minted shared secret would let a caller impersonate an IdP user.

**Approach:** Ship one RS256 claim schema and golden vector in `django-pyforge`. The portal client signs in-process. The CLI client (stdlib `pyforge.core` wrapper) mints by authenticating to the host (same IdP) and never signs locally. Both emissions pass the same verifier. Services refuse bad signature, wrong `aud`, expired `exp`, and identity headers without a valid assertion.

## Boundaries & Constraints

**Always:** Claims `sub`, `roles`, `aud=mcp:<station>`, `exp` ≤ 5 minutes from `iat`, `delegated_by=pyforge-host`; listed `alg` is `RS256` only. Golden vector lives in `django-pyforge`. Parent AD-2: no `pyforge.*` import under `src/platform/`. `pyforge-core` stays stdlib-only (`tests/meta/test_leaf_constraint.py`); do not add PyJWT/cryptography there. Crypto sign/verify stay in `django-pyforge`. Portals call services only through `django-pyforge`'s client.

**Block If:** Satisfying the dual-emitter AC would require a third-party crypto import in `pyforge.core` (halt rather than violate the leaf). Live Keycloak Token Exchange is required to make mint work (Deferred — tests use an in-process mint transport).

**Never:** HMAC-SHA256 / HS256; laptop-minted HMAC secrets; Keycloak Token Exchange; S-19.1 warden rename; S-18.2 rework; `pyforge.*` under `src/platform/`; FastAPI identity path; MinIO.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Dual emit | Portal client and `pyforge.core` host-mint client emit against golden RS256 key | Both tokens verify: `sub`, `roles`, `aud=mcp:<station>`, `exp-iat`≤300s, `delegated_by=pyforge-host` | No error expected |
| Bad signature | Token bytes flipped after sign | `verify` refuses | Raise typed refusal; no claims returned |
| Wrong audience | `aud=mcp:other` presented to station verifier | Refused | Typed refusal |
| Expired | `exp` in the past | Refused | Typed refusal |
| Identity header only | `X-Forwarded-User` (or `X-Remote-User` / `Remote-User`) and no valid Bearer assertion | HTTP 401/403 | Middleware refuses |
| HMAC / HS256 | Source scan of assertion + portal trees | No `hmac`/`HS256`/laptop HMAC secret | Test fails on presence |
| Portal raw HTTP | Portal module builds `urllib`/`httpx`/`requests` call to a service | Review-blocking AST finding fails the test | Assertion failure |

</intent-contract>

## Code Map

- `src/shared/packages/django-pyforge/src/django_pyforge/assertion/` -- claim schema, RS256 sign/verify, golden PEM vector, portal client, host mint view, assertion middleware
- `src/shared/packages/django-pyforge/pyproject.toml` -- add `PyJWT` + `cryptography` (already pinned in `platform-ci-test`; not in `pyforge-core`)
- `src/shared/packages/pyforge-core/src/pyforge/core/assertion.py` -- stdlib-only `HostMintClient` (`urllib.request`); claim-name constants; no jwt/cryptography import
- `src/platform/config/settings/base.py` -- install assertion middleware after `TokenRolesMiddleware`; no `pyforge` import
- `src/platform/config/urls.py` -- include django-pyforge mint path (host chrome package, not a station roster)
- `src/platform/tests/test_django_pyforge_assertion.py` -- I/O matrix + golden vector dual-emit
- `src/platform/tests/meta/test_no_pyforge_import.py` -- read-only; must stay green
- `src/shared/packages/pyforge-core/tests/meta/test_leaf_constraint.py` -- read-only; must stay green
- Read-only: `src/platform/config/local_dev/tokens.py` (OIDC persona mint, `aud` is OIDC not `mcp:<station>` — do not reuse as service assertion)
- Read-only: `src/platform/compliance_face/` chrome (18.2 shipped); do not rename

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/django-pyforge/src/django_pyforge/assertion/` -- schema, golden vector, sign, verify, portal client, mint view, middleware -- CAP-6 / canopy:AD-7
- `src/shared/packages/django-pyforge/pyproject.toml` -- declare PyJWT+cryptography -- crypto stays with chrome package
- `src/shared/packages/pyforge-core/src/pyforge/core/assertion.py` -- urllib host-mint client -- leaf-safe CLI emitter
- `src/platform/config/settings/base.py` + `urls.py` -- wire middleware + mint URL -- host consumes chrome client
- `src/platform/tests/test_django_pyforge_assertion.py` -- cover I/O matrix including AST bans

**Acceptance Criteria:**
- Given the golden vector in django-pyforge, when the portal client and the pyforge.core host-mint client emit a token, then both pass the same RS256 verification (`sub`, `roles`, `aud=mcp:<station>`, `exp`≤5m from `iat`, `delegated_by=pyforge-host`)
- Given a call with a bad signature, wrong audience, or expired `exp`, when verified, then it is refused
- Given a request with an identity header and no valid assertion, when it hits assertion middleware, then it is refused
- Given assertion and portal source trees, when scanned, then HMAC-SHA256 and laptop-minted secrets are absent
- Given a portal constructing a raw HTTP request to a service, when the AST scan runs, then the test fails (review-blocking)
- Given the CLI client, when it obtains a service token, then it authenticates to the host (same IdP) and does not hold a long-lived laptop HMAC secret

## Spec Change Log

## Review Triage Log

### 2026-08-24 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 11: (high 3, medium 6, low 2)
- defer: 4: (high 1, medium 2, low 1)
- reject: 12
- addressed_findings:
  - `[high]` `[patch]` Identity header + invalid/expired Bearer now refused and tested
  - `[high]` `[patch]` Mint view exercised via RequestFactory POST (ATOMIC_REQUESTS / no live DB)
  - `[high]` `[patch]` Middleware validates via `verify_assertion` (signature, exp, delegated_by, mcp: aud)
  - `[medium]` `[patch]` IdP payload must be a JSON object; mint catches PyJWTError
  - `[medium]` `[patch]` HostMintClient timeout=30s and rejects CR/LF in the bearer
  - `[medium]` `[patch]` Empty station/sub refused; PEM stripped
  - `[medium]` `[patch]` Runtime HS256 token refused by `verify_assertion`
  - `[medium]` `[patch]` Portal AST scan covers `http.client`
  - `[low]` `[patch]` Import order / ruff I001 and PLC0415 on tests

## Auto Run Result

Status: done
Summary: django-pyforge owns RS256 service assertions (schema, golden PEMs, portal signer, host mint, middleware). pyforge.core HostMintClient is stdlib urllib only. Dual-emit, refusal, HMAC/HTTP AST, and mint-view tests pass. Leaf constraint stays green.
Files: `django_pyforge/assertion/**`; `pyforge/core/assertion.py`; host settings/urls; `test_django_pyforge_assertion.py`; story spec.
Review: 11 patches (3 high); 4 deferred; 12 rejected (Token Exchange, 19.1, frozen JWT, nbf/jti, pixi.lock, Django-free verifier, csrf_exempt, full service HTTP client).
Follow-up review recommended: true (3 high patches; score 3×6 medium + 1×2 low = 20).
Tests: 33 passed (assertion + chrome + no-pyforge-import); 26 leaf-constraint passed; ruff clean.
Residual: mint does not verify IdP JWT (TE deferred); global identity-header middleware vs proxy headers; PortalClient is a signer not an HTTP client.

## Design Notes

`pyforge.core` cannot import PyJWT. The CLI "emitter" is `HostMintClient`: it POSTs the caller's IdP bearer token to the host mint view; django-pyforge signs. Tests inject an in-process transport that calls `mint_assertion(...)` so dual-emit does not need a live IdP.

Portal client: `PortalClient.emit(sub, roles, station)` using the same signer. Portals must use this client; they must not open HTTP to services themselves.

Identity headers watched: `X-Forwarded-User`, `X-Remote-User`, `Remote-User`. A valid `Authorization: Bearer` RS256 assertion is the only identity path this story adds.

Do not reuse `config.local_dev.tokens.mint_token` (OIDC `aud`, 15m default).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
