---
title: IdP bearer is verified before mint
type: fix
created: '2026-09-02'
status: ready-for-dev
updated: '2026-09-02'
baseline_commit: 2e3f108f
severity: CRITICAL
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/resilience-invariants.md
  - src/shared/packages/django-pyforge/src/django_pyforge/assertion/identity.py
  - src/shared/packages/django-pyforge/src/django_pyforge/assertion/views.py
  - src/platform/config/settings/base.py
  - src/platform/config/startup/stage_one.py
  - src/platform/tests/test_django_pyforge_assertion.py
warnings:
  - The current test suite ENCODES the vulnerability. `_idp_bearer()` in
    `test_django_pyforge_assertion.py:96` builds `header.payload.sig` with a
    literal `sig` string and `test_host_mint_view_emits_a_verifiable_assertion`
    asserts the host mints from it. That test must flip to a refusal.
deferred:
  - Keycloak Token Exchange (RFC 8693) for long Celery tasks — BS-3, still deferred.
  - Per-subject rate limit on `/assertion/mint/` and MCP — red-team R-8.
  - Role namespace prefixes (`pyforge:station:<name>`) — red-team R-13.
  - Assertion `jti` + revocation list — not this story.
---

<intent-contract>

## Intent

**Problem:** `POST /assertion/mint/` is the root of the whole delegation chain
(unifying CAP-6, canopy AD-7, RFC-3 revised). It is `csrf_exempt`, reads the
`Authorization: Bearer` header, and calls `identity_from_idp_bearer`, which
splits the token on `.`, base64-decodes segment 2, and returns `sub` and
`groups` **without verifying the signature, issuer, audience, expiry, or
algorithm** (`django_pyforge/assertion/identity.py`). The result is passed to
`mint_assertion`, which signs a real RS256 five-minute assertion for the
requested station with the requested roles. Anyone who can reach the host
becomes any subject with any roles for any station; supervisor `start`, Lane 3
row slicing, and MCP tool leasing all accept it. The module docstring records
"Live token-exchange is deferred" — the deferral shipped as the production
path. Red-team finding **X-1**, directive **R-1**.

**Approach:** Replace the decoder with a real verifier that reuses the OIDC
settings the host already declares (`OIDC_ISSUER`, `OIDC_JWKS_URL`,
`OIDC_AUDIENCE`, `OIDC_ALGORITHMS`, `OIDC_LEEWAY_SECONDS` in
`config/settings/base.py`; the local profile already points `OIDC_JWKS_URL` at
the dev `jwks.json` that `config/local_dev/keys.py` writes). Verification uses
PyJWT (`pyjwt >=2.13` is already pinned) with a JWKS key set loaded from
`https://` (through `truststore`) or `file://` (laptop / CI), cached with a
single refresh on unknown `kid`. Roles come from the configured group claim
(`DJANGO_PYFORGE_GROUP_CLAIM` / `ClaimsContract.group_claim`), never from a
hard-coded `roles`/`groups` fallback. Mint is fail-closed: unconfigured
verifier → 503 in every profile, including `COMPONENT_RUNTIME=local` (local
verifies against the dev JWKS file; it does not skip). Production stage-1
required-settings gains the three OIDC keys the verifier needs.

## Acceptance Criteria

- Given the existing `_idp_bearer()` fixture (`header.payload.sig`, no real
  signature), when it is POSTed to `/assertion/mint/`, then the response is
  **401** and no assertion is minted. (`test_host_mint_view_emits_a_verifiable_assertion`
  is rewritten to sign with a test RSA key served from a `file://` JWKS; the
  old fixture becomes `test_unsigned_bearer_is_refused`.)
- Given a bearer signed by a key **not** in the JWKS, when minted, then 401.
- Given a bearer with `alg: none`, `HS256`, or any algorithm outside
  `OIDC_ALGORITHMS`, when minted, then 401 (the HS256 case already exists for
  assertions; add it for the bearer).
- Given a bearer whose `iss` ≠ `OIDC_ISSUER`, or whose `aud` does not include
  `OIDC_AUDIENCE`, or whose `exp` has passed (beyond `OIDC_LEEWAY_SECONDS`),
  or missing `exp`/`iat`/`sub`, when minted, then 401 and the refusal reason
  is logged as a structured event without echoing the token.
- Given a bearer with an unknown `kid`, when minted, then the JWKS is
  refreshed **once**; a second unknown `kid` within the cache window is
  refused without a network call (no refresh amplification).
- Given a valid bearer whose group claim does not contain the requested
  `station`, when minted, then **403** — mirrors `django_pyforge.access`
  reachability (`station_name in roles`). A `flags` audience follows the same
  rule.
- Given a valid bearer, when minted, then the assertion's `roles` equal the
  verified group claim verbatim (never caller-supplied), `sub` is the
  verified `sub`, and every existing assertion test in
  `test_django_pyforge_assertion.py` still passes unchanged.
- Given `OIDC_JWKS_URL` unset or non-`https://`/`file://`, when the mint view
  is called in **any** profile, then 503 with a configuration error; the
  process still boots (fail-closed at the endpoint, not a CrashLoop).
- Given production/cluster settings, when `manage.py check` runs without
  `COMPONENT_OIDC_ISSUER`, `COMPONENT_OIDC_JWKS_URL`, or
  `COMPONENT_OIDC_AUDIENCE`, then stage-1 refuses (`refuse_required_settings`
  pattern, one fixture case per name), and laptop / `platform-ci-test` keep
  the dev-JWKS defaults.
- Given the chrome package source, when the policy test runs, then no module
  outside `django_pyforge/assertion/identity.py` calls `b64decode` /
  `urlsafe_b64decode` on a bearer, and `identity.py` contains no decode path
  that bypasses `jwt.decode` (AST test, same shape as
  `test_hmac_and_laptop_secrets_are_absent`).
- Given the verifier at import time, when the host boots air-gapped, then no
  network request is made (JWKS is fetched lazily on first mint and cached).

## Boundaries & Constraints

**Always:** Write under `_bmad-output/projects/pyforge-steward/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`.
Ledger key `40-1-idp-bearer-is-verified-before-mint`. Host never imports
`pyforge.*`. Reuse the existing `OIDC_*` settings; do not mint a second
settings surface. `pyjwt` + `cryptography` are already pinned — no new
dependency. Corporate CA via `truststore`, never `verify=False`.

**Block If:** Implementation would keep the unverified decoder reachable
behind a flag, env var, or `COMPONENT_RUNTIME=local` shortcut; add a shared
secret or HMAC anywhere; change the assertion claim schema (`schema.py`);
touch `mcp-host` or the proxy (that is R-7); introduce Token Exchange (BS-3
stays deferred); or widen into rate limiting (R-8).

**Never:** `alg=none`. HS256. `verify_signature: False`. A second identity
framework beside `django-allauth`. Trusting `X-Forwarded-User` on this path.
Logging a bearer or an assertion body.

</intent-contract>

## Tasks

- [ ] `django_pyforge/assertion/identity.py`: replace `identity_from_idp_bearer`
      with `verify_idp_bearer(token) -> tuple[sub, roles]` built on
      `jwt.decode(..., key=<jwk>, algorithms=settings.OIDC_ALGORITHMS,
      issuer=settings.OIDC_ISSUER, audience=settings.OIDC_AUDIENCE,
      leeway=settings.OIDC_LEEWAY_SECONDS, options={"require": ["exp","iat","sub","iss","aud"]})`.
- [ ] `django_pyforge/assertion/jwks.py` (new): `JWKSKeySet` — loads from
      `file://` or `https://` (truststore SSL context), caches by `kid`, one
      refresh on miss with a minimum refresh interval; no I/O at import.
- [ ] `django_pyforge/assertion/views.py`: 401 on refusal, 403 when the
      station is not in the verified roles, 503 when the verifier is
      unconfigured; structured log `assertion.mint_refused{reason}`.
- [ ] `src/platform/config/startup/stage_one.py`: add the three
      `COMPONENT_OIDC_*` keys to the deployed required set.
- [ ] `src/platform/config/settings/local.py` / `test.py`: confirm the dev
      JWKS file path resolves and the test settings serve a test key set.
- [ ] Tests (`src/platform/tests/test_django_pyforge_assertion.py`): rewrite
      `_idp_bearer()` to sign with a test RSA key; add the refusal matrix
      (unsigned, wrong key, `none`, HS256, wrong `iss`, wrong `aud`, expired,
      missing claims, unknown `kid` refresh-once, station-not-in-roles); AST
      policy test; stage-1 fixture cases.
- [ ] `resilience-invariants.md` RFC-3 row: append "Mint verifies the IdP
      bearer (Story 40.1)"; SPEC CAP-6 success line unchanged (it already
      says "independently verify").
- [ ] Ledger `40-1-idp-bearer-is-verified-before-mint` → `review` then `done`
      via `sprint-ledger-sync`.

## Design notes

- **Why not allauth's own verification?** allauth verifies the ID token at
  browser login and stores claims in the session; the mint path is a headless
  CLI/agent path that presents a bearer directly (see
  `test_cli_client_authenticates_to_the_host_and_does_not_sign`). It needs
  its own verifier, but it must use the **same** issuer/JWKS/audience
  settings so there is one IdP contract, not two.
- **`file://` JWKS is a feature, not a shortcut.** Air-gapped clusters may
  pin a mirrored JWKS on a ConfigMap; the laptop already writes one. The
  scheme allow-list is `https` and `file` only.
- **Station-in-roles check.** Today roles are bare station names (red-team
  X-3). Enforcing `station in roles` at mint closes lateral minting now and
  survives the R-13 prefix migration unchanged if implemented through
  `django_pyforge.roles`.
- **Do not add `jti`/revocation here.** Five-minute TTL plus verified root is
  the contracted posture (AD-7); revocation is a later story if needed.

## Verification

`pixi run -e python-agent-platform -- python -m pytest -o addopts=
src/platform/tests/test_django_pyforge_assertion.py
src/platform/tests/test_startup_required_settings.py` (cwd `src/platform`).
Host import-linter still green. Manual: from a shell with no IdP token,
`curl -X POST /assertion/mint/ -H 'Authorization: Bearer a.b.c' -d '{"station":"warden"}'`
returns 401; with a `local_dev` persona token (`config/local_dev/tokens.py`)
it returns an assertion that `verify_assertion` accepts.

## Suggested Review Order

**The root**

- Unverified decode today
  [`identity.py:15`](../../../../../../src/shared/packages/django-pyforge/src/django_pyforge/assertion/identity.py#L15)
- Mint trusts it
  [`views.py:34`](../../../../../../src/shared/packages/django-pyforge/src/django_pyforge/assertion/views.py#L34)

**The settings already there**

- `OIDC_ISSUER` / `OIDC_JWKS_URL` / `OIDC_AUDIENCE`
  [`base.py:445`](../../../../../../src/platform/config/settings/base.py#L445)
- Dev JWKS file the local profile already serves
  [`local.py:86`](../../../../../../src/platform/config/settings/local.py#L86)

**The test that must flip**

- Fake `.sig` bearer accepted
  [`test_django_pyforge_assertion.py:96`](../../../../../../src/platform/tests/test_django_pyforge_assertion.py#L96)
