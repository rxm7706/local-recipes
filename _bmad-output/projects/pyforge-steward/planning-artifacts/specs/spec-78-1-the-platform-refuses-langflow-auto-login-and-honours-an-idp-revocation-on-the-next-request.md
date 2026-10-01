---
title: '78.1: The platform refuses Langflow auto-login and honours an IdP revocation on the next request'
type: 'fix'
created: '2026-10-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - src/platform/config/asgi.py
  - src/platform/config/settings/base.py
  - src/platform/config/settings/production.py
  - src/platform/config/authorization/idp_userinfo.py
  - src/platform/config/authorization/current_claims.py
  - src/platform/langflow_integration/asgi.py
  - src/platform/langflow_integration/tests.py
  - src/platform/tests/test_langflow_mount.py
  - src/platform/tests/test_idp_revoke_next_request.py
warnings: [multiple-goals, oversized]
deferred:
  - summary: >-
      The platform edge still forwards every `/langflow/...` request into Langflow with no platform-side
      auth gate; after this story Langflow's own login (the env superuser) is the only gate.
    evidence: |-
      `_dispatch_http` in `config/asgi.py` routes `/langflow/` paths straight to `langflow_application`
      without checking the IdP session or a role. This story only stops Langflow handing out a token
      without credentials. Read in the installed Langflow 1.11.4 (`lfx/services/settings/auth.py`,
      not exercised here): `ENABLE_SIGNUP` defaults on, so `POST /api/v1/users/` may still create
      (inactive, `NEW_USER_IS_ACTIVE=False`) accounts. Putting `/langflow/` behind an IdP role is a
      design decision (which role, how the Langflow session follows it), so it needs its own Dream
      append and Story rather than a fix inside a security hotfix.
    location: src/platform/config/asgi.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** two auth controls the platform claims are not in effect. Both were found by the 2026-09-30 deferral
burn-down and verified by hand on `main` at `ddff15e9d9`.

1. **Langflow mints a superuser token for anyone (DW-FU-11-1, CAP-99).** `config/asgi.py:148-149` forwards every
   `/langflow/…` request into `langflow_application` with no auth gate. Nothing in `src/platform` sets
   `LANGFLOW_AUTO_LOGIN=False` (settings, chart, compose and env files all checked), so Langflow's default `True` holds,
   and `GET /langflow/api/v1/auto_login` returns a bearer token for the bootstrap superuser with no credentials. The
   repo's own `langflow_integration/tests.py:152` documents that default.
2. **An IdP revocation waits for the next login (DW-FU-26-1, duplicate DW-FU-18-2; CAP-86 and
   `spec-pyforge-unifying-strategy` CAP-12, Story 49.6).** `SOCIALACCOUNT_STORE_TOKENS` is never set, and allauth
   defaults it to `False`, so no `SocialToken` row is ever saved. `idp_userinfo._access_token_for` therefore always
   returns `None`, the userinfo re-check never runs, and `current_claims` serves the login-time claims on every
   request. An expired access token (userinfo answers 401) falls back to the same stale claims. The only test of the
   path, `test_idp_revoke_next_request.py`, monkeypatches `_access_token_for`, so it passes while production fails open.

**Approach:**

- **Langflow:** in `config/settings/base.py`, beside the other exported `LANGFLOW_*` values, export
  `LANGFLOW_AUTO_LOGIN=False` and read `LANGFLOW_SUPERUSER` and `LANGFLOW_SUPERUSER_PASSWORD` from the environment
  (`env(...)`, no default password; production refuses to start without one, as it does for other required
  secrets). Wire the password from a Secret in the chart and from the env file in compose; document both names in
  `docs/reference/environments.md`.
- **IdP revocation:** set `SOCIALACCOUNT_STORE_TOKENS = True`. When userinfo answers 401, refresh the access token
  once with the stored refresh token and retry; if there is no token, no refresh token, the refresh fails, or
  userinfo fails, deny (the request is treated as unauthenticated for role purposes), never fall back to the
  login-time claims. Keep the existing bounded cache.

Ledger key: `78-1-the-platform-refuses-langflow-auto-login-and-honours-an-idp-revocation-on-the-next-request`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- CAP-99 (Langflow joins as a pluggable Django application); CAP-86 (OIDC-delegated identity);
  `spec-pyforge-unifying-strategy` CAP-12 (revocation on the next request, Story 49.6).
- canopy:AD-19: deployed pods carry secret references, never values.
- `spec-feature-flag-governance` Q1: a `fix` needs no flag. Neither control may be switchable off.

## Acceptance Criteria

- Given the platform's ASGI app When a client sends `GET /langflow/api/v1/auto_login` with no credentials Then it gets no bearer token (Langflow refuses auto-login), tested through the real `config.asgi` dispatch
- Given settings load When `LANGFLOW_AUTO_LOGIN` is read from the process environment Then it is `False`, and `LANGFLOW_SUPERUSER_PASSWORD` comes only from the environment (no default; production refuses to start without it)
- Given a user who logged in through the IdP When their row is checked Then a `SocialToken` with the access token (and refresh token, when the IdP issues one) is stored
- Given a stored token and a fake userinfo endpoint When the IdP stops returning a role Then the user's next request no longer has that role, with no mock of `_access_token_for`
- Given userinfo answers 401 When a refresh token is stored Then the token is refreshed once and the request uses the fresh claims; Given the refresh fails, or there is no token, or userinfo errors Then access the claims would grant is denied, never served from the login-time claims
- Given the chart and compose files When rendered Then the Langflow superuser password comes from a Secret or env file reference, never a literal
- Given the Langflow fix is removed When the auto-login test runs Then it fails; Given `SOCIALACCOUNT_STORE_TOKENS` is removed When the revocation test runs Then it fails (mutation)

## Tasks

1. Read `config/asgi.py`, `config/settings/base.py` (the `LANGFLOW_*` block) and `production.py`, `config/authorization/idp_userinfo.py`, `current_claims.py`, and both existing tests.
2. Langflow: export the auto-login setting and the environment-sourced superuser credential; wire chart and compose; document the variables.
3. IdP: set `SOCIALACCOUNT_STORE_TOKENS = True`; add the refresh-once-on-401 path and the deny-on-failure rule.
4. Replace the mocked revocation test with one that stores a real `SocialToken` and stubs only the HTTP userinfo and token endpoints; add the auto-login refusal test through the real ASGI dispatch; run both mutations by hand.
5. Run the station suite and the platform suite; reconcile every Spec `spec-surface-check` names (memlog first, `git add`, then a scoped `--write-baseline --spec` for each).

## Boundaries & Constraints

**Always:**
- Credentials come from the environment or a secret, never code, defaults or CLI flags (canopy:AD-19).
- A failure to confirm claims denies; it never grants from older claims.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not mock the function under test (`_access_token_for`, the ASGI dispatch).
- Do not add a feature flag or setting that turns either control off.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| auto-login probe | `GET /langflow/api/v1/auto_login`, no credentials | no token | — |
| missing superuser password | production settings, variable unset | refuses to start | named error |
| revoked role | stored token, userinfo drops the role | role gone on next request | — |
| expired token | userinfo 401, refresh token stored | refreshed once, fresh claims | — |
| refresh fails | refresh endpoint errors | denied | never login-time claims |
| no stored token | legacy session with no token row | denied | never login-time claims |
| userinfo down | 5xx or timeout | denied | never login-time claims |

</intent-contract>

## Binding

Parent capabilities: CAP-99; CAP-86; `spec-pyforge-unifying-strategy` CAP-12 (defects; no new CAP).
Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-01 entry.
Ledger key: `78-1-the-platform-refuses-langflow-auto-login-and-honours-an-idp-revocation-on-the-next-request`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: none. This is a `fix` (`spec-feature-flag-governance` Q1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: pass, including the new auto-login and revocation tests.
- The two mutations in Task 4 — expected: each new test fails with its fix removed.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
