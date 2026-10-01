---
title: '78.1: The platform refuses Langflow auto-login and honours an IdP revocation on the next request'
type: 'fix'
created: '2026-10-01'
status: 'in-review'
baseline_revision: 'cc3a9c0b9d5c397986318518320f7d4eb1546ec5'
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
  - summary: >-
      The Wagtail-admin and staff gates still read login-synced Django groups, so an IdP revocation of
      those groups waits for the next sign-in even though station roles now follow the IdP per request.
    evidence: |-
      `holds_wagtail_admin_group` reads `user.groups.filter(name=settings.WAGTAIL_ADMIN_IDP_GROUP)`, the
      database groups the OIDC adapter syncs at login; it never consults `fetch_current_userinfo`. This
      story did not touch that path (pre-existing). Unverified: whether any code re-syncs those groups
      outside login. Settled by tracing every writer of `User.groups` under `src/platform/`.
    location: src/platform/platformapp/front_door/middleware.py
    severity: medium (unverified)
  - summary: >-
      The new chart wiring test for the Langflow password is skipped in the GitHub Platform CI `test`
      job, because every `@requires_helm` chart test is.
    evidence: |-
      `test_platform_pods_require_the_langflow_superuser_password_from_the_secret` carries
      `requires_helm`; the `test` job installs only `platform-ci-test`, which has no `helm` binary
      (`platform-dev` does, so `platform-ci-local` runs it). The same gating covers every pre-existing
      chart invariant, so closing it means giving that job helm, a separate story.
    location: .github/workflows/platform-ci.yml
    severity: low
  - summary: >-
      An existing deployment's Langflow database and the tokens minted while `/auto_login` was open are
      not addressed: no rotation, audit or upgrade note ships with the fix.
    evidence: |-
      Bearer tokens and API keys issued by the open endpoint stay valid until they expire or the Langflow
      secret key rotates; whether changing `LANGFLOW_SUPERUSER_PASSWORD` changes an existing superuser's
      password was not exercised (the live test runs on a fresh database). A `helm upgrade` against a
      Secret without the new key fails pod creation, and `keys-runbook.md` has no row for this secret.
      Settled by reading Langflow's token lifetime and `get_or_create_super_user` for an existing user.
    location: docs/explanation/enterprise-deployment.md
    severity: medium (unverified)
  - summary: >-
      allauth now stores the IdP refresh token in plaintext in `SocialToken.token_secret`, and nothing
      deletes the row at logout or encrypts it at rest.
    evidence: |-
      The contract requires storing the refresh token, and allauth's `SocialToken` is the sanctioned
      store; its plaintext column and its lack of deletion on logout are allauth's behaviour. A database
      reader gets long-lived IdP credentials. Hardening (encrypt at rest, revoke at logout, retention)
      is a separate design decision, so it needs its own Dream append and Story.
    location: src/platform/config/settings/base.py
    severity: medium
  - summary: >-
      The userinfo and token endpoints are derived from the issuer in the Keycloak layout only, so a BYO
      IdP with another layout is denied everywhere once tokens are stored.
    evidence: |-
      `userinfo_endpoint_url` (pre-existing) and the new `token_endpoint_url` build
      `<issuer>/protocol/openid-connect/{userinfo,token}`, and the refresh reads its client from
      `SOCIALACCOUNT_PROVIDERS` only. The BYO example in the deployment docs uses the same layout, and
      the bundled realm is Keycloak. Unverified: whether any estate runs a BYO IdP with another layout.
      Settled by asking the operator which IdPs are in use; the fix is OIDC discovery or settings.
    location: src/platform/config/authorization/idp_userinfo.py
    severity: medium (unverified)
  - summary: >-
      Two requests that both see a 401 at access-token expiry refresh with the same refresh token, with no
      lock across them.
    evidence: |-
      `_refresh_access_token` rotates the stored refresh token without a row lock; the docstring accepts
      that a racing request is denied once. The bundled realm sets no refresh-token revocation, so
      Keycloak reuse is allowed and the race is benign there. Unverified: a BYO IdP that rotates with
      reuse detection could refuse the loser or end the session. Settled by that IdP's refresh-token
      settings; the fix is a row lock held across the HTTP call.
    location: src/platform/config/authorization/idp_userinfo.py
    severity: medium (unverified)
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

## Code Map

All paths under `src/platform/` unless prefixed. Line anchors are `main` at `a9636014f5`.

- `config/settings/base.py:603-628` -- allauth block: add `SOCIALACCOUNT_STORE_TOKENS = True` beside `SOCIALACCOUNT_*`. `SOCIALACCOUNT_PROVIDERS["openid_connect"]["APPS"][0]` holds the client id/secret the refresh call reuses.
- `config/settings/base.py:635-699` -- Langflow block. Its values reach `os.environ` before `config/asgi.py` imports `langflow_integration.asgi` (`create_app()` reads them then). Force `LANGFLOW_AUTO_LOGIN` by assignment (`os.environ[...] = "False"`, never `env()`/`setdefault`, so a deployer cannot switch it off); mirror `LANGFLOW_SUPERUSER` / `LANGFLOW_SUPERUSER_PASSWORD` from `env(...)` (`env.read_env(.env)` at line 75 also fills `os.environ`).
- `config/startup/stage_one.py:57-103,130-152` -- `REQUIRED_SETTINGS` of `RequiredSetting(name, remedy)`; deployed-only, reads `os.environ`. Add `LANGFLOW_SUPERUSER_PASSWORD` here (the named production refusal). `tests/test_startup_required_settings.py` is "one case per name".
- `config/settings/production.py:24,172-177` -- calls `refuse_required_settings()`; wires `IDP_USERINFO = fetch_current_userinfo` unconditionally.
- `config/authorization/idp_userinfo.py:55-123` -- `_access_token_for` (latest `SocialToken`; always `None` today), `_fetch_userinfo_http` (returns `None` for every failure, so a 401 is indistinguishable), `fetch_current_userinfo` (cache, token, HTTP; `None` on any failure). `userinfo_endpoint_url()` uses the Keycloak `/protocol/openid-connect/userinfo` shape; the refresh endpoint is its `/token` sibling.
- `config/authorization/current_claims.py:22-37` -- the fail-open: a wired `IDP_USERINFO` returning `None` falls through to `session[IDP_TOKEN_CLAIMS_SESSION_KEY]` (login-time claims).
- `config/authorization/adapters.py:56-89` -- the only writer of session claims (`pre_social_login`). Allauth stores a `SocialToken` on `SocialLogin.save` only when `SOCIALACCOUNT_STORE_TOKENS` (allauth `socialaccount/models.py:314`); the refresh token lands in `token_secret`.
- `config/asgi.py:130-153` -- `_dispatch_http`; `/langflow/...` forwards with `root_path` extended. Not changed here (see `deferred`). `langflow_integration/asgi.py:44` -- `create_app()` at import reads Langflow's auth settings from `os.environ`.
- Langflow 1.11.4, read-only evidence (primary checkout `.pixi/envs/platform-dev`): `langflow/api/v1/login.py:108-166` -- `GET /auto_login` mints tokens when `AUTO_LOGIN`, else HTTP 403 `{"detail": {"message": "Auto login is disabled.", "auto_login": false}}`; `lfx/services/settings/auth.py:83` -- default `AUTO_LOGIN=True`; `langflow/services/utils.py::setup_superuser` -- with `AUTO_LOGIN` off it needs a non-empty `SUPERUSER` and `SUPERUSER_PASSWORD` and rejects the legacy default `langflow`, so startup fails without an env password.
- `langflow_integration/tests.py:~143-175` -- `_run_flow_over_http` mints its token through `GET /api/v1/auto_login`; it must log in with the env superuser (`POST /api/v1/login`) instead, and its docstring (the auto-login default) goes stale.
- `tests/test_langflow_mount.py:37-44,94-134` -- `_get` helper and the lifespan test show how to drive `config.asgi.application` and `_LifespanManager(application)`; `pytest.importorskip("langflow")` (needs the `platform-dev` env, Postgres, Redis).
- `tests/test_idp_revoke_next_request.py:153-186` -- the mocked test to replace (it monkeypatches `_access_token_for` and `_fetch_userinfo_http`). `test_login_time_session_claims_hide_idp_revoke` pins hook=`None` reading the session; that stays true.
- Production-leaf env fixtures that need the new key: `tests/test_startup_required_settings.py` (`required_env`), `tests/test_idp_revoke_next_request.py` (`_DEPLOYED_REQUIRED_ENV`), `test_agent_rate_limits_and_run_bounds.py`, `test_broker_tls_verified.py`, `test_mcp_host_sidecar.py`, `test_mcp_transport_auth.py` (find with `grep -rn MCP_HOST_SIDECAR_BASE_URL tests`).
- `deploy/charts/platform/templates/_helpers.tpl:298-379` -- `platform.djangoEnv`, shared by web, worker, worker-builds, beat, consume-events and the migrate Job. Add `LANGFLOW_SUPERUSER_PASSWORD` as a `secretKeyRef` into `existingSecret` (not `optional`). mcp-host runs `mcp_host.settings`, not the production leaf, so it is unaffected.
- `deploy/charts/platform/values.yaml:55-82` -- the `existingSecret` key list to extend; `deploy/overlays/eso/externalsecret-platform-secrets.example.yaml` -- add the key.
- `tests/test_chart_invariants.py:107-126,617-652` -- `_SECRETISH_ENV_NAME` already requires a `secretKeyRef` for any `PASSWORD` env; add an explicit "present and referenced" assertion.
- `compose/compose.yml:148-152` (`platform`) -- literal placeholders under `environment:`; the Langflow password goes in as a `${LANGFLOW_SUPERUSER_PASSWORD:?...}` reference, not a literal. `tests/test_isolation_and_statelessness.py:83-84` parses this file.
- `conftest.py:12-17` -- `os.environ.setdefault` for test env; the throwaway password for lanes that boot Langflow goes here (a harness fixture, not a settings default).
- `docs/reference/environments.md` -- GENERATED pixi-environments table (`scripts/docs_environments.py`, "do not hand-edit"); not a place for runtime variables. See Design Notes.

## Tasks & Acceptance

**Execution:**
- [x] `config/settings/base.py` -- set `SOCIALACCOUNT_STORE_TOKENS = True`; force `LANGFLOW_AUTO_LOGIN` off in settings and `os.environ`; read `LANGFLOW_SUPERUSER`, `LANGFLOW_SUPERUSER_PASSWORD` from the environment, no default password -- closes both findings at the settings seam
- [x] `config/startup/stage_one.py` + the six production-leaf env fixtures -- add the required key and its remedy; one absence case -- production refuses to start without it, named
- [x] `config/authorization/idp_userinfo.py` -- tell a 401 from other failures; refresh once with the stored refresh token (update the `SocialToken` row), retry once; every other outcome denies -- revocation honoured, no stale grant
- [x] `config/authorization/current_claims.py` -- a wired hook is authoritative: a non-mapping answer returns `None`, never the session claims -- removes the fail-open
- [x] `deploy/charts/platform/templates/_helpers.tpl`, `values.yaml`, ESO example, `compose/compose.yml` -- password by secret reference only; document the key where the other secrets are documented
- [x] tests -- replace the mocked revocation test with a real `SocialToken` (stored through allauth's `SocialLogin.save`) against a local HTTP stub of the userinfo and token endpoints, covering every I/O-matrix row; add the auto-login refusal through the real `config.asgi` dispatch; move `_run_flow_over_http` to password login; chart and compose "no literal" checks
- [x] verification -- run both mutations by hand, the station and platform suites, then reconcile every Spec `spec-surface-check` names (memlog first, `git add`, scoped stamp) -- note the run's own guard is `python scripts/spec_surface_reconcile.py`, and a stamp is never passed by this run

**Acceptance Criteria:**
- The seven Given/When/Then criteria in the intent contract above are the acceptance criteria; this story adds none.

## Spec Change Log

- 2026-10-01 (implementation, deviations from the Design Notes; none changes an acceptance criterion):
  - **`request.user` at middleware time.** `TokenRolesMiddleware` sits right after `SessionMiddleware`, before `AuthenticationMiddleware`, so on its call `request.user` is not set and the hook could never find a token. With the hook authoritative that left `request.idp_roles` empty for every request (`django-marshal`'s `watch_report` reads it directly). `fetch_current_userinfo` now resolves the user from the session (`django.contrib.auth.middleware.get_user`, which caches on the request); the new test `test_request_roles_come_from_userinfo_before_the_view_runs` fails without it.
  - **One IdP exchange per request.** A denial is not cached across requests (positive-only cache, unchanged), and the roles are read several times per request, so each read repeated userinfo and the refresh. The outcome, a denial included, is remembered on the request, which is what makes "refreshed once" true per request.
  - **Env wiring beyond the chart and compose.** The container job, `scripts/platform-ci-local.sh` and the three kind/OCP/air-gap smoke Secrets in `.github/workflows/platform-ci.yml` boot the platform image or the chart, so they now carry `LANGFLOW_SUPERUSER_PASSWORD`; the built image is also probed for a 403 at `/langflow/api/v1/auto_login`, because the pytest lane for it needs `langflow`, which `platform-ci-test` does not carry.
  - **Docs.** Besides `values.yaml`, the ESO example and NOTES: the ESO README table, `enterprise-deployment.md` (Secrets table and a revocation paragraph), `platform-deployment-architecture.md`, `ocp-cluster-bringup.md`, `src/platform/README.md` and the local-development tutorial.
  - **Fixtures.** Four production-leaf env fixtures needed the key (`test_startup_required_settings`, `test_idp_revoke_next_request`, `test_agent_rate_limits_and_run_bounds`, `test_broker_tls_verified`); `test_mcp_host_sidecar` and `test_mcp_transport_auth` only set `MCP_HOST_SIDECAR_BASE_URL` for the proxy and never load the production leaf, so they are unchanged.
- Operator-visible: every IdP session that began before this ships holds no stored token and is denied its roles until the user signs in again (fail closed, by the "no stored token" row).

## Design Notes

- **Authority of a wired hook.** `current_claims.fetch_current_idp_claims` keeps its order (snapshot, hook, session). The change: when `IDP_USERINFO` is callable and answers anything but a mapping, the answer is "no claims", not "try the session". Hook unset (local/test) still reads the session, which `test_login_time_session_claims_hide_idp_revoke` pins. Session claims are only written by the OIDC login adapter and the local-dev personas mint bearer tokens, so only IdP-logged-in users are affected, and after this change they have a stored token.
- **Refresh shape.** `grant_type=refresh_token` to `<issuer>/protocol/openid-connect/token` with the app's client id and secret; keep the rotated refresh token if the IdP returns one; a missing `token_secret` is a failed refresh. Positive-only caching stays (`IDP_CLAIMS_CACHE_SECONDS`); there is no negative cache, so a downed IdP costs each request its bounded timeouts, which is the price of failing closed.
- **Forced, not defaulted.** `LANGFLOW_AUTO_LOGIN` is assigned, so a deployer's `LANGFLOW_AUTO_LOGIN=true` cannot revive it. The password has no settings default; an empty value is "unset", never a credential. Deployed boots refuse it by name in stage 1; local and test boots that start Langflow get it from the environment (compose reference, `.env`, or the `conftest.py` fixture), and Langflow itself refuses an empty or legacy-default password.
- **Operator-visible break.** The chart now requires a `LANGFLOW_SUPERUSER_PASSWORD` key in the `existingSecret`; a release whose Secret lacks it fails at pod creation. Intended (fail closed), and called out in `values.yaml` and the ESO example.
- **Deviation: documentation target.** The contract names `docs/reference/environments.md`, which is a generated pixi-environments table. The two names are documented where the other platform secrets already are (`values.yaml`, the ESO example, the compose header, and the deployment how-to/explanation docs that list them) instead.

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
