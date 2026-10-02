---
title: "83.2: Login works on the plain-HTTP local stack, and `sync` retries rate limits and names each failed candidate"
type: 'fix'
created: '2026-10-02'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
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

## Binding

Parent capabilities: pap:CAP-1, pap:CAP-6 (Stories 10.1, 10.3); CAP-57, CAP-60 (Stories 8.1, 8.4) (defects of shipped
behaviour; no new CAP).
Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-02 entry.
Closes: DW-10-3-3, DW-FU-8-1-3, DW-8-4-1.
Ledger key: `83-2-login-works-on-the-plain-http-local-stack-and-sync-retries-rate-limits-and-names-each-failed-candidate`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-02 by operator ruling: start Phase 2 of the deferral burn-down after the inflow wave.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: pass (the platform settings tests).

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
