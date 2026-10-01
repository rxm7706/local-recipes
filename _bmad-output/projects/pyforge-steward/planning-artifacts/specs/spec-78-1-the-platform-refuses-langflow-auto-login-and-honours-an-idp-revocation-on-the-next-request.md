---
title: '78.1: The platform refuses Langflow auto-login and honours an IdP revocation on the next request'
type: 'fix'
created: '2026-10-01'
status: 'done'
baseline_revision: 'cc3a9c0b9d5c397986318518320f7d4eb1546ec5'
review_loop_iteration: 0
followup_review_recommended: true
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
- 2026-10-01 (review pass and reconcile follow-through; none changes an acceptance criterion):
  - **`enterprise-deployment.md` is not touched.** The Docs bullet above names it; the file is restored to its pre-story content. `spec-pyforge-doctor` governs it, and naming it on the doctor memlog moves that memlog and reds `chain-currency-sweep-check` (`chain-audit-checkpoint-staleness`). The revocation note and the `LANGFLOW_SUPERUSER` line live in `src/platform/README.md`; `platform-deployment-architecture.md` keeps the Secrets row.
  - **No baseline stamp.** Task 5 of the contract asks for a scoped `--write-baseline --spec` per named Spec; this run's directive is never to pass `--write-baseline`. The paths are named on the owning memlogs instead, and `python scripts/spec_surface_reconcile.py` and `spec-surface-check` exit 0. The stamp is the operator's landing step.
  - **Compose callers.** `compose.yml`'s `${LANGFLOW_SUPERUSER_PASSWORD:?...}` is evaluated for every compose command, so the two tests that drive it (`test_login_pkce_live_keycloak.py`, whose `up` failure became a silent skip, and `test_isolation_and_statelessness.py`) now pass a throwaway value. `compose.yml` is unchanged.

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

### 2026-10-01 — Review pass
- verdicts: 36 findings — high 0, medium 5, low 22, false 2, maybe-false 7
- layers, in the order they reported: intent-alignment (IA, 8 divergences), blind-hunter (BH, 14 bullets; BH5 carries two claims, logged as 5a and 5b), edge-case-hunter (ECH, 9), verification-gap (VG, 4). The story spec went to the edge-case layer alone; the shared diff excluded it.
- findings:
  - IA1 `[low]` `[reject]` Langflow refusal is proven mostly at settings level; the ASGI test is `importorskip("langflow")`; no record of the mutation runs — the live `config.asgi` test passed here under `platform-dev` (Langflow 1.11.4, real Postgres and Redis), the built-image 403 smoke is the CI proof, and both mutations were run (recorded under Auto Run Result); a further lane adds machinery for little.
  - IA2 `[low]` `[reject]` The headline next-request test runs at cache 0 — the contract keeps the bounded cache, `test_claims_are_cached_for_the_bounded_window` pins the production window, and "literal next request" is only deterministic at 0.
  - IA3 `[low]` `[reject]` Token storage is proven at the adapter/`SocialLogin` seam, not through the OIDC callback — the `STORE_TOKENS` gate is allauth's `SocialLogin.save`, which the test drives for real and the mutation proves; the callback view needs a live IdP.
  - IA4 `[low]` `[patch]` `docs/reference/environments.md` untouched and `LANGFLOW_SUPERUSER` documented nowhere — that file is a generated pixi-environments table (`docs-environments`), not a place for variables (deviation in Design Notes); fixed by documenting the username in `src/platform/README.md` (grouped with BH12).
  - IA5 `[maybe-false]` `[defer]` The refresh stub mirrors the implementation's assumptions (Keycloak layout, confidential client) — the public-client half is patched under VG3; the layout half needs the operator to say whether any non-Keycloak BYO IdP is in use → DW-steward-78-1-6 (grouped with BH3).
  - IA6 `[low]` `[reject]` "Deny" is role-level and applies only where `IDP_USERINFO` is wired — that is the contract's "unauthenticated for role purposes"; production wires the hook, local/test keep the session by design.
  - IA7 `[low]` `[reject]` A local runtime is not refused for a missing password — stage 1 is deployed-only by design (CAP-3 locality), and Langflow refuses an empty password at lifespan.
  - IA8 `[low]` `[reject]` No baseline stamp — the run directive forbids `--write-baseline`; paths are named on the memlogs and both surface guards exit 0 (Spec Change Log).
  - BH1 `[maybe-false]` `[defer]` Concurrent refresh has no lock — the bundled realm sets no refresh-token revocation (Keycloak's default allows reuse) so it is benign there; a rotating BYO IdP might refuse the loser; settled by that IdP's settings → DW-steward-78-1-7 (grouped with ECH3).
  - BH2 `[low]` `[reject]` Token lookup not scoped to the OIDC provider, NULL-first `expires_at` ordering — only `openid_connect` is installed, one app is configured and `(app, account)` is unique, so a user has one row; a mismatch would deny, not grant; scoping by user is pinned by the new VG1 test; the fix adds a guard (grouped with ECH5).
  - BH3 `[maybe-false]` `[defer]` Token endpoint hard-coded to the Keycloak layout — the pre-existing userinfo URL already was, and the BYO docs example uses the same layout; unverified whether any estate runs another → DW-steward-78-1-6.
  - BH4 `[low]` `[reject]` No negative cache, breaker, break-glass or metrics — the contract denies on any failure to confirm and keeps the existing bounded cache, so softening is excluded; each request is bounded by the 5 s timeouts.
  - BH5a `[low]` `[patch]` The settings comment says the access token is the only credential stored — reworded to say both tokens are stored and what each is for (comment only).
  - BH5b `[medium]` `[defer]` The refresh token is plaintext at rest and not deleted at logout — the contract requires storing it and allauth's `SocialToken` is the store; encryption, revocation and retention are their own design → DW-steward-78-1-5.
  - BH6 `[low]` `[reject]` The password reaches every pod through the shared `djangoEnv` — the contract wants a deployed boot refused "as for other required secrets"; stage 1 applies per leaf like `MCP_HOST_SIDECAR_BASE_URL`; compose's `worker` runs `COMPONENT_RUNTIME=local`.
  - BH7 `[medium]` `[patch]` The compose `${…:?}` breaks unrelated compose commands — real (`docker compose config` exits 15 without the variable); the two tests that drive compose now pass a throwaway value; the whole-stack refusal is the contract's intent (grouped with ECH1).
  - BH8 `[maybe-false]` `[defer]` Existing deployments: tokens minted while `/auto_login` was open stay valid, a legacy default password, no rotation or upgrade note — unverified how long they live and what an existing superuser does on a changed password → DW-steward-78-1-4 (grouped with ECH8).
  - BH9 `[low]` `[reject]` Refusal and credentialed login not proven on CI, smoke checks status only — the built-image 403 smoke is the CI proof, the credentialed-login control is in the live test run here, and no proxy sits between curl and its own container.
  - BH10 `[low]` `[patch]` IdP tests leave branches untested — added a parametrized 401/503 token-endpoint test and `token_calls == []` on the timeout test; the public-client half is patched under VG3.
  - BH11 `[low]` `[reject]` The posture test spawns five settings loads and pins the `env(...)` call shape — test-only cost of a few seconds; the source check is the contract's "no default" clause.
  - BH12 `[low]` `[patch]` Dead settings values and an undocumented username — the two settings are what the contract prescribes (`env(...)`); the username line was added to `src/platform/README.md` (grouped with IA4).
  - BH13 `[false]` `[reject]` The edge gap is tracked only in memlog prose — the story spec's `deferred:` list carries it and the intake tool promoted it to `DW-steward-78-1` in `deferred-work-ledger.md`.
  - BH14 `[false]` `[reject]` A memlog cross-reference is inaccurate — at review time the doctor and unifying-strategy memlogs each named `enterprise-deployment.md` (two mentions each); the file's edits were reverted afterwards and a correction entry appended.
  - ECH1 `[medium]` `[patch]` The compose `:?` makes the live-Keycloak PKCE test's `up -d keycloak` fail and `pytest.skip` — verified at the test's `up` call; `_compose_env()` now feeds all three compose calls, and `_compose` in `test_isolation_and_statelessness.py` likewise; the test skips here (no `jwt`), so only `docker compose config` was run (exit 15 without, 0 with).
  - ECH2 `[low]` `[reject]` Langflow's legacy default `langflow` passes stage 1 — `setup_superuser` raises a named `ValueError` at lifespan, so the app fails closed at boot; the fix adds a branch for an unlikely value.
  - ECH3 `[maybe-false]` `[defer]` Concurrent refresh on one rotating refresh token → DW-steward-78-1-7 (same as BH1).
  - ECH4 `[low]` `[reject]` `save()` or the expiry arithmetic raising after a rotation — needs a database error or an absurd `expires_in`; the request errors out and never grants.
  - ECH5 `[low]` `[reject]` Provider scoping and NULL expiry → same as BH2.
  - ECH6 `[low]` `[reject]` The request memo across a mid-request user switch — the memo is per request object, login views start anonymous and an anonymous answer is never memoized; the fix adds a comparison guard.
  - ECH7 `[low]` `[reject]` A plain-http token endpoint in a deployed boot — the issuer scheme is deployer configuration and the pre-existing userinfo fetch already accepted http; the fix adds a branch.
  - ECH8 `[maybe-false]` `[defer]` An existing Langflow database holding the old bootstrap superuser → DW-steward-78-1-4 (same as BH8).
  - ECH9 `[maybe-false]` `[defer]` The Wagtail-admin and staff gates read login-synced groups — `holds_wagtail_admin_group` reads `user.groups` (pre-existing, untouched); unverified whether any code re-syncs them outside login → DW-steward-78-1-2.
  - VG1 `[medium]` `[patch]` The token lookup is not pinned to the requesting user (22/22 tests pass with the filter loosened) — added a two-user test; the `.all()` mutation now fails it.
  - VG2 `[low]` `[patch]` Refresh persistence is unasserted — added `test_a_non_rotating_refresh_keeps_the_refresh_token_and_renews_the_expiry`; dropping `expires_at` from `update_fields` now fails it.
  - VG3 `[medium]` `[patch]` The public-client refresh path (the bundled-profile default) is untested — the stub takes a configurable secret and a new test uses `secret=""`; always sending `client_secret` now fails it.
  - VG4 `[low]` `[defer]` The chart wiring test is helm-gated and skipped in the GitHub `test` job — the same gating covers every chart invariant (pre-existing) → DW-steward-78-1-3.

## Auto Run Result

### Summary of implemented change

- **Langflow:** `config/settings/base.py` assigns `LANGFLOW_AUTO_LOGIN = False` and `os.environ["LANGFLOW_AUTO_LOGIN"] = "False"` (assigned, not read, so no deployer value revives it) and reads `LANGFLOW_SUPERUSER` / `LANGFLOW_SUPERUSER_PASSWORD` from the environment with no default. A deployed boot without the password is refused by name in stage 1 (`REQUIRED_SETTINGS`). The chart requires it as a non-optional `secretKeyRef` in the shared `djangoEnv`; compose takes it by `${…:?}` reference. The built image is smoke-probed for a 403 at `/langflow/api/v1/auto_login`.
- **IdP revocation:** `SOCIALACCOUNT_STORE_TOKENS = True`. On a userinfo 401 the stored refresh token is used once and userinfo retried once; no token, no refresh token, a failed refresh, or any other userinfo failure denies. `current_claims` treats a wired hook as authoritative (a non-mapping answer is "no claims", never the session claims). Two deviations are recorded in the Spec Change Log (`request.user` resolved at middleware time; one IdP exchange per request).

### Files changed

- `src/platform/config/settings/base.py` — store tokens, forced auto-login, environment-sourced superuser
- `src/platform/config/startup/stage_one.py` — `LANGFLOW_SUPERUSER_PASSWORD` is a required deployed setting
- `src/platform/config/authorization/idp_userinfo.py` — 401 vs other failures, refresh once, deny on every other outcome, per-request memo
- `src/platform/config/authorization/current_claims.py` — a wired hook is authoritative
- `src/platform/conftest.py` — throwaway password for lanes that boot Langflow
- `src/platform/compose/compose.yml`, `src/platform/deploy/charts/platform/{templates/_helpers.tpl,templates/NOTES.txt,values.yaml}`, `src/platform/deploy/overlays/eso/{README.md,externalsecret-platform-secrets.example.yaml}` — password by secret or env reference only
- `.github/workflows/platform-ci.yml`, `scripts/platform-ci-local.sh` — password for the container job and the chart smokes; the auto-login 403 smoke
- `src/platform/tests/test_idp_revoke_next_request.py` — mocked test replaced by real-token tests against a loopback IdP stub (revoke, refresh, every deny row, two users, public client, token-endpoint failures)
- `src/platform/tests/test_langflow_auth_posture.py` (new), `src/platform/tests/test_langflow_mount.py`, `src/platform/langflow_integration/tests.py` — settings seams, the live `config.asgi` refusal, password login
- `src/platform/tests/test_chart_invariants.py`, `test_startup_required_settings.py`, `test_agent_rate_limits_and_run_bounds.py`, `test_broker_tls_verified.py`, `test_isolation_and_statelessness.py` — chart/compose/fixture coverage and the compose env
- `src/shared/packages/pyforge-marshal/tests/integration/test_login_pkce_live_keycloak.py` — compose env so the live test no longer skips on the new guard
- `src/platform/README.md`, `docs/explanation/platform-deployment-architecture.md`, `docs/how-to/ocp-cluster-bringup.md`, `docs/tutorials/local-platform-development.md` — the new names and the revocation note
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md`, `.../spec-pyforge-unifying-strategy/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` — surface reconcile entries
- `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md` — seven rows promoted by `deferred_work_intake.py --fix --project steward`

### Review findings breakdown

- **Patches applied (7 entries):** compose env for the two compose-driving tests (medium, BH7+ECH1); two-user token isolation (medium, VG1); public-client refresh (medium, VG3); persistence of a non-rotating refresh (low, VG2); token-endpoint failures and the timeout assertion (low, BH10); the settings comment (low, BH5a); the `LANGFLOW_SUPERUSER` documentation (low, IA4+BH12).
- **Deferred (6 new, plus the plan-time edge-gate item):** `DW-steward-78-1` (the `/langflow/` edge has no platform gate), `-2` (Wagtail-admin groups), `-3` (helm-gated chart test), `-4` (existing deployments), `-5` (refresh token at rest), `-6` (non-Keycloak endpoints), `-7` (concurrent refresh).
- **Rejected (18), reasons in the triage rows:** IA1, IA2, IA3, IA6, IA7, IA8; BH2, BH4, BH6, BH9, BH11, BH13 (false), BH14 (false); ECH2, ECH4, ECH5, ECH6, ECH7.

### Follow-up review recommendation

`followup_review_recommended: true` — three medium entries were patched (compose env, VG1, VG3) and four low. The specific unverified risk: the compose-env change to `test_login_pkce_live_keycloak.py` was verified only by a code read and `docker compose config` (exit 15 without the variable, 0 with it); the test skips in this environment (`jwt` is not installed), so the live Keycloak flow was not executed with the new env.

### Verification performed

- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — exit 0, 1896 passed, 2 skipped (before and after the patch round).
- `pixi run -e pyforge-guild platform-ci-local -- --test` — exit 0, 1093 passed, 13 skipped after the patch round (1088 before it); ruff, mypy, policy suite and sqlmigrate extraction pass in it.
- Live refusal through `config.asgi` (`test_auto_login_hands_out_no_token_through_the_platform`) under `platform-dev` against private Postgres 17 and Redis — passed (403, no token, wrong password 401, right password 200). No lane has both `langflow` and `pytest-django`, so `platform-ci-local` skips that module; the built-image smoke is the CI proof. In that run the pre-existing `test_unknown_non_api_path_falls_through_to_django` failed only because the lane has no pytest-django (Django rejects the `testserver` host); it is untouched by this story.
- Mutations, by hand, each restored byte-for-byte: Langflow fix removed — the live `config.asgi` test and 6 posture tests fail; `SOCIALACCOUNT_STORE_TOKENS` removed — 8 revocation tests fail; user filter dropped, `client_secret` always sent, `expires_at` not saved — each fails exactly its new test; the control run is green.
- `python scripts/spec_surface_reconcile.py` — exit 0; `pixi run -e pyforge-guild spec-surface-check` — exit 0; `chain-currency-sweep-check` — exit 0; `deferred-work-check` — exit 0 after the intake.
- Matrix Test Audit: every I/O row has a passing covering test — auto-login probe (live test), missing password (stage-1 and posture tests), revoked role, expired token, refresh fails, no stored token, userinfo down (5xx, timeout, unreachable).

### Residual risks

- The live Keycloak PKCE flow is unexecuted with the compose env change (see the follow-up note).
- The refusal through `config.asgi` has no pytest lane in CI; the built-image `curl` smoke stands in (DW-steward-78-1-3 covers the sibling helm gating).
- The `/langflow/` edge still has no IdP role gate (`DW-steward-78-1`); Langflow's own login is the only gate.
- Operator rollout: every pre-change IdP session is denied its roles until the next sign-in, and a `platform-secrets` Secret without `LANGFLOW_SUPERUSER_PASSWORD` fails pod creation. The Spec's baseline stamp is the operator's landing step.
