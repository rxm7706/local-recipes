---
title: "83.2: Login works on the plain-HTTP local stack, and `sync` retries rate limits and names each failed candidate"
type: 'fix'
created: '2026-10-02'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
warnings: [multiple-goals, oversized]
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
  - src/platform/config/settings/production.py
  - src/platform/config/locality.py
  - src/platform/config/broker_tls.py
  - src/platform/compose/compose.yml
  - src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Three defects, verified at HEAD a7cdb91fe4:

- `src/platform/config/settings/production.py:47` reads `SECURE_SSL_REDIRECT` from `DJANGO_SECURE_SSL_REDIRECT`, but
  `:49` `SESSION_COOKIE_SECURE = True`, `:51` `SESSION_COOKIE_NAME = "__Secure-sessionid"`, `:53`
  `CSRF_COOKIE_SECURE = True` and `:55` `CSRF_COOKIE_NAME = "__Secure-csrftoken"` are literals. The compose stack serves
  plain HTTP (`src/platform/compose/compose.yml:157-160` and `:240` set `DJANGO_SECURE_SSL_REDIRECT: "False"`, with
  `COMPONENT_RUNTIME: local`), and a browser drops `Secure` cookies, and any `__Secure-` cookie, over HTTP. Login, the
  admin and every CSRF-protected POST fail on the documented stack while `/ht/` answers 200 (DW-10-3-3).
- No GitHub/Jira call in `src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py` retries. `_default_transport`
  (`:328-349`) returns any HTTP status, and every caller raises `SyncAPIError` on the first `status >= 400`
  (`:501-502` GraphQL, `:912-913` and `:956` Jira issue, `:982-983` transitions), a 429 or a secondary-rate-limit 403
  included (DW-FU-8-1-3).
- `reconcile_schedule_batch` (`:1699-1762`) records each candidate's `github_item_id`, `ok` and `summary` in
  `details["candidates"]`, but its summary is only the count line (`:1760`), `cli.py:1456-1457` prints only
  `result.summary`, and `sync reconcile` has no `--json` (`cli.py:922-954`). A partial `--schedule` failure cannot be
  attributed from the CLI (DW-8-4-1).

**Approach:**

- `production.py`: the two cookie flags and the `__Secure-` names follow one local-only switch (for example
  `DJANGO_INSECURE_LOCAL_COOKIES`), honoured only when `config.locality.is_local()` (the `broker_tls.py` precedent: a
  weaker posture needs an explicit local process and a request by name). A deployed process composes `Secure` cookies
  and the `__Secure-` names whatever its environment says. `compose.yml` sets the switch on `platform` and `worker`.
- `sync.py`: one bounded retry wrapped around the transport seam (so an injected fake passes through it too) retries a
  429, a 403 that carries `Retry-After` or `x-ratelimit-remaining: 0`, and a 502/503/504, a fixed small number of times,
  sleeping `Retry-After` when given (capped) and exponential backoff otherwise, through an injectable sleep. After the
  last attempt the response goes to the caller, which fails as today. `TransportResponse` gains a `headers` field with
  an empty default, so every existing fake keeps working.
- `reconcile_schedule_batch`: when any candidate failed, the summary gains one line per failed candidate,
  `<github_item_id>: <summary>`, under the count line; `details["candidates"]` is unchanged. No new flag.

Ledger key: `83-2-login-works-on-the-plain-http-local-stack-and-sync-retries-rate-limits-and-names-each-failed-candidate`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- pap:CAP-1 (Story 10.1, the rendered settings) and pap:CAP-6 (Story 10.3, the local compose stack); CAP-57 (FR-27,
  Story 8.1's transport) and CAP-60 (fail loud, fail alone; Story 8.4's batch). Defects of shipped behaviour, so no new
  CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given `COMPONENT_RUNTIME=local` and the switch on When production settings load Then `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` are `False` and neither cookie name starts with `__Secure-`
- Given `COMPONENT_RUNTIME` unset or not `local` and the switch on When production settings load Then both flags are `True` and both names keep `__Secure-`
- Given `compose.yml` When its `platform` and `worker` environments are read Then both set the switch beside `DJANGO_SECURE_SSL_REDIRECT: "False"`
- Given a fake transport answering 429 with `Retry-After: 2` then 200 When `github_graphql_request` runs Then it returns the 200 payload and the injected sleep saw 2 seconds
- Given a fake transport answering 429 on every attempt When a Jira or GitHub call runs Then it raises `SyncAPIError` after the bounded attempts, never looping further
- Given a 404 or a 401 When any sync call runs Then it is not retried
- Given a `--schedule` batch with one failed candidate When `main(["sync", "reconcile", "--schedule", ...])` runs Then stderr names that candidate's `github_item_id` and its summary
- Given the locality guard is removed When the deployed-process settings test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:**
- A deployed process never serves session or CSRF cookies without `Secure`.
- Every HTTP call keeps going through `_http.py`'s `open_url` (never `urlopen` directly).
- `src/platform/` never imports `pyforge.*` (the settings change is host-only).
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not make `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` plain environment toggles a deployed process can switch off.
- Do not retry a 4xx other than 429 and the rate-limited 403, and never retry without a bound.
- Do not add a CLI flag to `sync reconcile` (the per-candidate lines are the fix).
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

</intent-contract>

## Code Map

- `src/platform/config/settings/production.py:47-55` -- the four cookie literals (`SESSION_COOKIE_SECURE`, `SESSION_COOKIE_NAME`, `CSRF_COOKIE_SECURE`, `CSRF_COOKIE_NAME`) beside the env-driven `SECURE_SSL_REDIRECT`; the edit site.
- `src/platform/config/locality.py:39` -- `is_local()` (true only for exactly `COMPONENT_RUNTIME=local`; unset or unrecognised is deployed). Import it into `production.py`.
- `src/platform/config/broker_tls.py:349-383` -- the precedent: a weaker posture is honoured only when `is_local()` and asked for by name; a deployed process composes the strong value.
- `src/platform/compose/compose.yml:155-160` (`platform`) and `:238-240` (`worker`) -- both set `COMPONENT_RUNTIME: local` and `DJANGO_SECURE_SSL_REDIRECT: "False"`; the switch goes beside the latter in both.
- `src/platform/tests/test_langflow_auth_posture.py:29-78,181-190` -- model for the new test: settings loaded in a child process under a controlled env (`_DEPLOYED_ENV`), and `_compose_environments()` parsing `compose.yml`.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py:310-344` -- `TransportResponse(status, body)` and `_default_transport`; `headers` is added here and filled from `resp.headers` / `exc.headers`.
- `sync.py:495,845,857,906,949,976,1005` -- the seven `transport(request)` call sites (GraphQL, Jira user lookup, Jira issue GET, Jira fields PUT, transitions GET and POST); each becomes `_send(transport, request)`.
- `sync.py:1694-1757` -- `reconcile_schedule_batch`; the summary gains one `<github_item_id>: <summary>` line per failed entry. `details["candidates"]` is unchanged.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py:1456-1457` -- `main()` prints `result.summary` to stderr when `not result.ok`, so the extra lines reach stderr with no CLI change.
- `src/shared/packages/pyforge-steward/tests/unit/test_sync_reconcile_propagation.py:71,2348-2722` -- `FakeTransport` and the batch tests; `tests/unit/test_sync_duty.py:95-205` -- the CLI `--schedule` tests (they assert substrings, so extra lines do not break them).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md` -- DW-10-3-3, DW-8-4-1, DW-FU-8-1-3 are closed here (`status: closed`, `resolution:`, `verified:`) once the code lands.

## Tasks & Acceptance

**Execution:**
- `src/platform/config/settings/production.py` -- one local-only switch `DJANGO_INSECURE_LOCAL_COOKIES` (`env.bool`, default `False`), honoured only under `is_local()`; the two `*_COOKIE_SECURE` flags and the two `__Secure-` names follow it (plain `sessionid` / `csrftoken` when on) -- login and CSRF POSTs work over plain HTTP, and a deployed process cannot switch Secure off.
- `src/platform/compose/compose.yml` -- set `DJANGO_INSECURE_LOCAL_COOKIES: "True"` on `platform` and `worker`, beside `DJANGO_SECURE_SSL_REDIRECT: "False"`, with a comment naming the plain-HTTP reason.
- `src/platform/tests/test_local_cookie_posture.py` (new) -- child-process settings tests for the local, deployed and switch-off rows, plus the compose assertion; the deployed row fails if the `is_local()` guard is removed.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py` -- `TransportResponse.headers` (empty default); `_default_transport` fills it; `_send` retries 429, a rate-limited 403 and 502/503/504 a bounded number of times through the injectable `_sleep`; the seven call sites use it; `reconcile_schedule_batch` appends one line per failed candidate.
- `src/shared/packages/pyforge-steward/tests/unit/test_sync_retry.py` (new) and `tests/unit/test_sync_duty.py` -- retry rows (429 then 200 with `Retry-After`, 429 forever, 404/401 not retried, rate-limited 403, 502, backoff without `Retry-After`) and the failed-candidate lines through `main(["sync", "reconcile", "--schedule", ...])`.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md` -- close DW-10-3-3, DW-8-4-1, DW-FU-8-1-3 with resolution and verified lines.

**Acceptance Criteria:**
- Given the eight Acceptance Criteria in the intent contract, when the station suite, the platform settings tests and the mutation check run, then every one passes and the mutation (guard removed) turns the deployed-process test red.

## Spec Change Log

## Binding

Parent capabilities: pap:CAP-1, pap:CAP-6 (Stories 10.1, 10.3); CAP-57, CAP-60 (Stories 8.1, 8.4) (defects of shipped
behaviour; no new CAP).
Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-02 entry.
Closes: DW-10-3-3, DW-FU-8-1-3, DW-8-4-1.
Ledger key: `83-2-login-works-on-the-plain-http-local-stack-and-sync-retries-rate-limits-and-names-each-failed-candidate`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-02 by operator ruling: start Phase 2 of the deferral burn-down after the inflow wave.

## Design Notes

- The cookie switch is `DJANGO_INSECURE_LOCAL_COOKIES` (the contract's "for example", fixed here). `production.py` composes `_insecure_local_cookies = is_local() and env.bool("DJANGO_INSECURE_LOCAL_COOKIES", default=False)`; the flags are `not _insecure_local_cookies`, and the names fall back to Django's own `sessionid` / `csrftoken` when it is on. A deployed process that sets the switch composes Secure cookies and no refusal is added: the contract says "whatever its environment says".
- Retry: 4 attempts in total (1 call + 3 retries), backoff `1s, 2s, 4s` without `Retry-After`, `Retry-After` honoured as seconds and capped at 60s (an unparsable or non-finite value falls back to the backoff). `_sleep` is a module attribute resolved at call time (`time.sleep` by default); tests replace it. `_send(transport, request)` wraps the seam at the call sites, not at the entry points, so `github_graphql_request` and the Jira functions retry when a fake is passed to them directly.
- 403 retries only when `Retry-After` is present or `x-ratelimit-remaining` is `0` (header names matched case-insensitively); a plain 403 (permission) and every other 4xx are returned on the first answer. After the last attempt the last response goes to the caller, which raises `SyncAPIError` as today.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: pass (the platform settings tests).

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
