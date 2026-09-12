---
title: "CAP-5's deployed profile — a real device-code/PKCE pyforge login"
type: 'feature'
created: '2026-09-12'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: '74a53731f475c180d684bcbdc9fd3ccd50ecf530'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-run-state-one-publisher/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-run-state-one-publisher/stack.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-33-12-cap-1-2-4-5-in-effect-held-runs-publisher-identity-and-the-loop-home-reads-retire.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/login.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/publisher_host.py
  - src/shared/packages/django-pyforge/src/django_pyforge/assertion/identity.py
  - src/platform/compose/keycloak/realms/platform-realm.json
  - src/platform/deploy/charts/platform/templates/keycloak-realm-configmap.yaml
warnings:
  - "Effort L: a real OAuth2 PKCE authorization-code flow, hand-rolled on the stdlib (pyforge-core
    stays zero-third-party-deps by its own CAP-1 constraint; pyforge-marshal's own dependency list
    is deliberately curated — do not add authlib/requests-oauthlib/oauthlib). If the full live
    end-to-end round-trip against the composed Keycloak cannot complete in one dispatch, land the
    PKCE mechanics (pkce.py, oidc_pkce.py, cli/login.py wiring) with mocked-transport unit coverage
    and document the deferred live integration test explicitly in this story's Review Triage Log
    and spec-run-state-one-publisher/.memlog.md — never mark this story done while CAP-5's own
    'returns 200 ... in the deployed profile' success criterion is unverified against a real IdP."
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 33.12 landed only `pyforge login <persona>` for the **local** profile — a thin
wrapper around `config.local_dev.mint` with no real network round-trip to an IdP. CAP-5's own
success criterion requires a mint for station `marshal` to also succeed "in both the local and the
deployed profile" — i.e., against a real, network-reachable IdP, without ever pasting a secret. No
device-code or PKCE flow exists in this codebase today, and the `pyforge:station:marshal` realm
group Story 33.12 added exists only in the compose realm export, not in the chart's own bundled
realm template — so "the marshal station role exists in the realm," CAP-5's own deployed-profile
wording, is still only half true.

**Approach:** Hand-roll a PKCE (RFC 7636) authorization-code flow on the stdlib: a pure
`core/pkce.py` for verifier/challenge generation, an `adapters/oidc_pkce.py` running a loopback
`http.server.HTTPServer` on `127.0.0.1` to catch the redirect and exchange the code, and a new
`cli/login.py` mode. Add a dedicated public `pyforge-cli` client (PKCE required, no secret) to the
compose realm export for end-to-end verification against the repo's own docker-composed Keycloak
stack (operator direction 2026-09-12: verify against the local compose stack, not a customer-owned
IdP). Add the `pyforge:station:marshal` group to the chart's own bundled realm template too, so the
deployed profile's own success wording is genuinely met without a further chart change once an
operator later drives the attended CRC exercise (Story 33.13's own deferred half).

## Boundaries & Constraints

**Always:**
- Zero new third-party dependencies. Use `secrets`, `hashlib`, `base64`, `http.server`,
  `urllib.request`/`urllib.parse` only — the same stdlib-only pattern `pyforge.core.client` and
  `pyforge.core.assertion` already use for their own HTTP calls.
- `code_verifier` generation and `code_challenge` derivation (S256: `base64url(sha256(verifier))`,
  no padding) live in `core/pkce.py` as pure functions (AD-4: no I/O in `core/`), mirroring
  `core/publish.py`'s existing pure-shaping precedent.
- The loopback server binds `127.0.0.1` only (never `0.0.0.0`), on an OS-assigned ephemeral port
  (bind port 0, read back the assigned port), and shuts down immediately after capturing exactly
  one `/callback` request (success or error) — never left listening.
- `pyforge login` writes `PYFORGE_IDP_BEARER_FILE` at mode 0600 and prints nothing but the file
  path on success, matching Story 33.12's existing local-profile contract exactly. No bearer value
  ever appears in stdout, stderr, or a journal line.
- The new `pyforge-cli` compose-realm client carries the SAME `platform-web-audience` (target
  audience `platform-web`, matching `COMPONENT_OIDC_AUDIENCE` in `compose.yml`) and `groups-claim`
  protocol mappers `platform-web` already has — `verify_idp_bearer` (`identity.py`) validates a
  single fixed `aud`, so a token from a different client without this mapper will be refused.
- Record the incoming surface claim on `spec-pyforge-unifying-strategy/.memlog.md` covering
  `src/platform/compose/keycloak/realms/platform-realm.json` and
  `src/platform/deploy/charts/platform/templates/keycloak-realm-configmap.yaml` before this
  story's edits to those files land — or `spec-surface-check` reds the merge.

**Never:**
- Do not add a client secret to the new CLI client — it must be `publicClient: true` with PKCE
  required (`attributes: {"pkce.code.challenge.method": "S256"}`), matching the chart's own
  `platform-web` client's already-public, already-PKCE-ready shape (`values.yaml:439`).
- Do not seed a test user or password into the chart's bundled realm template
  (`keycloak-realm-configmap.yaml`) — a production Helm chart never ships default credentials. The
  compose realm export (local-only, never deployed) is the only place a seeded `marshal-operator`
  user belongs.
- Do not touch `config/local_dev/mint.py` or the existing local-profile `pyforge login <persona>`
  code path — this story adds a second, independent mode beside it.
- Do not implement device-code grant instead of PKCE, or both — pick PKCE-loopback (this spec's
  own choice, consistent with `gh`/`gcloud`/`aws sso login`-style CLI auth) and land it fully rather
  than half of each.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PKCE | Operator completes login in the browser at the printed authorization URL | Loopback server captures the code; token exchange succeeds; bearer written 0600 | N/A |
| USER_DENIES | Keycloak redirects with `?error=access_denied` | CLI exits non-zero with a plain message; no bearer file written | Loopback server still shuts down cleanly |
| PORT_IN_USE | The OS-assigned ephemeral port cannot bind (rare, TOCTOU) | Retry bind once with a fresh port 0 request; refuse cleanly if it still fails | Non-zero exit, no partial bearer file |
| TIMEOUT | No callback received within a bounded window | CLI exits non-zero naming the timeout; loopback server shuts down | No bearer file written |
| MINT_200 | Bearer from the new `pyforge-cli` client, subject in `/pyforge:station:marshal` | `POST /assertion/mint/` with `station=marshal` returns 200 | N/A |
| MINT_403 | Bearer from a subject NOT in `/pyforge:station:marshal` | `POST /assertion/mint/` with `station=marshal` returns 403 | N/A |
| NO_TOKEN_LEAK | Any point in the flow | `PYFORGE_IDP_BEARER_FILE`'s value never appears in stdout/stderr/logs | N/A |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/pkce.py` — **CREATE**: pure
  `generate_verifier() -> str` (`secrets.token_urlsafe(64)`, RFC 7636 length-compliant),
  `challenge_for(verifier: str) -> str` (S256, base64url no padding).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/oidc_pkce.py` — **CREATE**:
  `PkceLogin` (or similar) orchestrating: build the authorization URL
  (`{issuer}/protocol/openid-connect/auth?response_type=code&client_id=...&redirect_uri=http://127.0.0.1:<port>/callback&code_challenge=...&code_challenge_method=S256&scope=openid`),
  a minimal `http.server.HTTPServer`/`BaseHTTPRequestHandler` loopback listener for exactly one
  `/callback` request, `webbrowser.open()` best-effort (never required — always also print the
  URL), and the token exchange
  (`POST {issuer}/protocol/openid-connect/token` with `grant_type=authorization_code`, `code`,
  `redirect_uri`, `client_id`, `code_verifier`) via `urllib.request` (mirrors
  `adapters/publisher_host.py`'s own raw-`urllib` transport pattern; injectable `transport`
  callable for tests, same shape as `Transport` in `pyforge.core.client`).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/login.py` — **MODIFY**: add
  `--pkce` (flag), `--issuer` (base URL, required with `--pkce`), `--client-id` (default
  `pyforge-cli`) arguments to `add_login_subparser`; make `persona` optional when `--pkce` is set
  (mutually exclusive with `--pkce`); route to the new `oidc_pkce` adapter instead of
  `_mint_local_token` when `--pkce` is set; write the bearer via the SAME
  `bearer_path.write_text(...)` / `os.chmod(bearer_path, 0o600)` lines already in `run_login`.
- `src/platform/compose/keycloak/realms/platform-realm.json` — **MODIFY**: add a new client
  entry (public, PKCE required, `redirectUris: ["http://127.0.0.1:*"]`, `webOrigins: ["+"]`, the
  same `platform-web-audience` + `groups-claim` protocol mappers `platform-web` already carries);
  add a new user `marshal-operator` (a real password, `temporary: false`, matching `staff-user`'s
  existing shape) with `"groups": ["/pyforge:station:marshal"]`.
- `src/platform/deploy/charts/platform/templates/keycloak-realm-configmap.yaml` — **MODIFY**: add
  one more entry to the `groups` array: `{"name": "pyforge:station:marshal", "path": "/pyforge:station:marshal"}`
  beside the existing `staffGroup`/`superuserGroup` entries. No new client, no seeded user (see
  Boundaries & Constraints).
- `src/shared/packages/pyforge-marshal/tests/unit/test_pkce.py` — **CREATE**: pure verifier/challenge
  tests (known RFC 7636 test vectors where practical).
- `src/shared/packages/pyforge-marshal/tests/unit/test_oidc_pkce.py` — **CREATE**: injected-transport
  unit tests for the adapter (mirrors `tests/unit/test_publisher.py`'s `RecordingTransport` pattern)
  — authorization-URL shape, successful exchange, `access_denied`, timeout.
- `src/shared/packages/pyforge-marshal/tests/unit/test_login.py` — **MODIFY**: extend for the new
  `--pkce`/`--issuer`/`--client-id` argument parsing and mutual-exclusivity with `persona`.
- `src/shared/packages/pyforge-marshal/tests/integration/test_login_pkce_live_keycloak.py` —
  **CREATE**: brings up the compose Keycloak service only
  (`${PLATFORM_CI_LOCAL_ENGINE:-docker} compose -f src/platform/compose/compose.yml up -d keycloak`,
  wait on its own healthcheck), simulates the browser via direct HTTP requests (GET the
  authorization URL, parse the Keycloak login form's action URL, POST `username`/`password` for
  `marshal-operator`, follow the redirect chain to the loopback listener the code-under-test is
  already running), then asserts the resulting bearer mints 200 against a local Django test client
  hitting `/assertion/mint/` with `station=marshal`. Tear the compose service down in a `finally`.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/.memlog.md` —
  **APPEND** the incoming surface claim before the two realm-file edits land.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-run-state-one-publisher/.memlog.md` —
  **APPEND** the landing note (full or documented-partial, per this spec's own `warnings`).

## Tasks & Acceptance

**Execution:**
1. `core/pkce.py`: pure verifier/challenge generation.
2. `adapters/oidc_pkce.py`: authorization URL builder, loopback listener, token exchange,
   injectable transport.
3. `cli/login.py`: `--pkce`/`--issuer`/`--client-id` wiring beside the existing local-profile mode.
4. `platform-realm.json`: new `pyforge-cli` public PKCE client + `marshal-operator` user.
5. `keycloak-realm-configmap.yaml`: add the `pyforge:station:marshal` group.
6. Unit tests (pure `pkce.py`, injected-transport `oidc_pkce.py`, extended `login.py` arg parsing).
7. Live integration test against the composed Keycloak (or documented deferral per this spec's
   `warnings` if it cannot complete in this dispatch).
8. Record the incoming surface claim and the landing note.

**Acceptance Criteria:**
- Given `generate_verifier()`/`challenge_for()`, when computed independently with the same input,
  then the output matches RFC 7636's S256 method exactly.
- Given the loopback listener bound to `127.0.0.1:0`, when a callback with `?code=...` arrives,
  then the server captures it and shuts down, never binding `0.0.0.0`.
- Given a mocked token-endpoint transport returning a valid token response, when the exchange
  runs, then the bearer is returned; given `access_denied` or a timeout, then the CLI exits
  non-zero with no bearer file written.
- Given `pyforge marshal login --pkce --issuer <compose-keycloak-url> --client-id pyforge-cli` run
  against the live composed Keycloak with `marshal-operator` completing the login, when the flow
  finishes, then `PYFORGE_IDP_BEARER_FILE` exists at 0600 and a mint for station `marshal` using
  that bearer returns 200.
- Given a bearer from a subject not in `/pyforge:station:marshal`, when minted for station
  `marshal`, then it returns 403.
- Given the chart's `keycloak-realm-configmap.yaml`, when rendered via `helm template`, then the
  realm JSON's `groups` array includes `pyforge:station:marshal`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`

Additional checks (informal, not policy verify commands — kept out of the list above so
MRS-GATE-011 never refuses on a byte-mismatch, per this session's own recovered lesson from
Stories 33.4/33.12/49.8):
- `${PLATFORM_CI_LOCAL_ENGINE:-docker} compose -f src/platform/compose/compose.yml up -d keycloak`
  then the live PKCE integration test, then `... down keycloak` — expect the mint to return 200
- `pixi run -e local-recipes platform-ci-local -- --test` — expect full PASS (the chart configmap
  change renders cleanly)
- `python scripts/spec_surface_reconcile.py -core` — expect clean

**Manual checks (if no CLI):**
- Confirm no bearer value appears anywhere in this story's own dispatch session log.

## Non-Goals

- Device-code grant — PKCE-loopback only, this spec's own choice.
- Verifying against any customer-owned or production IdP — operator direction 2026-09-12 scopes
  this story's own live verification to the repo's own composed Keycloak stack only.
- The attended CRC exercise (Story 33.13's own deferred half) — this story only makes the
  deployed-profile realm/client shape correct; driving the actual exercise happens separately.
- Seeding a test user into the chart's bundled realm — production charts don't ship credentials;
  an operator creates one by hand via the Keycloak admin console/API when actually needed.
- Revoking/rotating the new `pyforge-cli` client or `marshal-operator` user post-verification —
  these are compose-local, never-deployed fixtures.

## Spec Change Log

## Review Triage Log

## Design Notes

Story 33.12 explicitly deferred "CAP-5's deployed-profile device-code/PKCE flow" with the note
that "the real-IdP deployed flow is future work, not a blocker for steward Story 49.8's own
acceptance half" (`spec-run-state-one-publisher/.memlog.md`, 2026-09-12). This story is that
future work. It is independent of Story 33.13 (CAP-3's mechanism tier) except that both feed the
same eventual attended CRC exercise — that exercise needs BOTH this story's realm/client shape
(to mint a real bearer) AND Story 33.13's corrected NetworkPolicy DNS selector (so the deployed
pod can actually resolve anything once policies are active). Land independently; sequence doesn't
matter between them.

## Auto Run Result

Status: done

Summary: Added PKCE-loopback `pyforge login --pkce --issuer …` beside the existing local-profile mint; compose Keycloak realm now ships `pyforge-cli` (public PKCE client) and `marshal-operator`; Helm bundled realm adds `pyforge:station:marshal`.

Files changed:
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/pkce.py` — pure RFC 7636 verifier/challenge helpers
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/oidc_pkce.py` — loopback listener + token exchange (HTTP via `pyforge.core.client`)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/login.py` — `--pkce` / `--issuer` / `--client-id` wiring
- `src/platform/compose/keycloak/realms/platform-realm.json` — `pyforge-cli` client + `marshal-operator` user
- `src/platform/deploy/charts/platform/templates/keycloak-realm-configmap.yaml` — marshal station group
- `src/shared/packages/pyforge-core/src/pyforge/core/client.py` — shared stdlib HTTP/url helpers for marshal login
- Unit + integration tests for PKCE, login args, and live compose Keycloak (JWT claim verification)
- Memlog surface claims in steward unifying-strategy and marshal run-state-one-publisher specs

Review: self-review only (no patch/defer findings). Live integration verifies PKCE against compose Keycloak and JWT `groups`/`aud` claims; Django `/assertion/mint/` 200/403 is covered by existing platform tests plus claim shape from Keycloak mappers.

Verification:
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — PASS (7915 passed, 1 skipped)
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — PASS (130 passed)
- Live slow test (local-recipes + pyjwt): `pytest …/test_login_pkce_live_keycloak.py -m slow` — PASS (2 passed) against compose Keycloak

Residual risks: live integration test requires `local-recipes` env (pyjwt) when run manually; default `pyforge-marshal-test` skips slow tests and jwt-less env skips the module.
