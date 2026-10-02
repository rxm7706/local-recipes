---
title: "83.2: Login works on the plain-HTTP local stack, and `sync` retries rate limits and names each failed candidate"
type: 'fix'
created: '2026-10-02'
status: 'done'
baseline_revision: '43bb288d2a022f8bbe1195e49b76472b236ac756'
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

### 2026-10-02 — Review pass
- verdicts: 27 findings — high 0, medium 0, low 22, false 5, maybe-false 0
- findings:
  - `[low]` `[reject]` Blind Hunter 1: a 403 with `x-ratelimit-remaining: 0` is retried after 1s/2s/4s, and `x-ratelimit-reset` is never read, so a primary limit that resets in minutes burns three more calls — the code does what the intent says ("`Retry-After` when given (capped) and exponential backoff otherwise"); the cost is three calls over 7s before a loud `SyncAPIError`; the fix (read the reset header, floor the wait) adds a branch the intent did not ask for.
  - `[low]` `[reject]` Blind Hunter 2: an oversized `Retry-After` (3600) is clamped to 60s rather than honoured, and the HTTP-date form falls back to the 1s backoff — the intent says "(capped)", the clamp is bounded at one retry per 60s for at most three retries, and GitHub and Jira send delta-seconds; HTTP-date support is added surface for a form not seen in these APIs.
  - `[low]` `[reject]` Blind Hunter 3: `_send` retries every method on 502/503/504, so a Jira transition POST that was applied before the gateway error is replayed — verified the call sites: only `transition_jira_issue`'s POST is state-dependent (GraphQL field sets, assignee add/remove and the fields PUT are idempotent); the intent lists 502/503/504 with no method carve-out; the failure is loud, per-candidate, and self-heals on the next run (both sides then hold the same value, which `reconcile` treats as a no-op that refreshes the baselines); it needs a 5xx after the write landed. A POST carve-out is more than a direct correction. Recorded under residual risks.
  - `[low]` `[reject]` Blind Hunter 4: no overall time budget and no jitter — worst case 3 × 60s per call, multiplied across a batch under a sustained limit; the bound the intent requires is per call ("a fixed small number of times"); a persistent limit already fails `list_linked_github_items` first, so the multiplication needs a limit that starts mid-batch and outlasts three minutes; a batch budget is new state and a new parameter, and lockstep backoff is cosmetic.
  - `[low]` `[reject]` Blind Hunter 5: retries are invisible — no log and no attempt count, so a throttled failure reads like a first-answer failure — real but cosmetic; the final error still carries the HTTP status and body, and the fix adds an output channel the intent did not ask for.
  - `[low]` `[reject]` Blind Hunter 6: connection-level failures (`URLError`, a timeout during `resp.read()`) are not retried and the ledger does not say so — the intent's retry set is the three listed statuses and nothing about transport errors; `_default_transport` still raises `SyncAPIError` naming the URL and reason exactly as before, and DW-FU-8-1-3 is about status codes, so its closure is accurate. Recorded under residual risks.
  - `[low]` `[reject]` Blind Hunter 7: `DJANGO_INSECURE_LOCAL_COOKIES=True` on a deployed process is silently ignored, where `broker_tls` precedent names the misconfiguration — the intent says a deployed process composes `Secure` cookies "whatever its environment says", and a typo (`=ture`) resolves to `False`, which is the secure direction; the behaviour is stated in the Design Notes, the compose comment and the test docstring; a warning is added output for a rare local misconfiguration.
  - `[low]` `[reject]` Blind Hunter 8: no test drives a real login or CSRF POST over HTTP, other plain-HTTP launches do not get the switch, and the `worker` setting is dead configuration — the Acceptance Criteria are stated at the settings-load and compose-file surface and the tests observe exactly that (child-process settings load, parsed compose); a browser round trip needs the compose stack. The other launches are checked under Intent Alignment 2 (row 24); AC3 requires the switch on `worker`.
  - `[low]` `[patch]` Blind Hunter 9: the cookie test's docstring says removing the `is_local()` guard turns "the two deployed rows" red, but four parametrized rows fail (reproduced: 4 failed, 5 passed) — fixed: `src/platform/tests/test_local_cookie_posture.py` now says "the deployed-process rows".
  - `[false]` `[reject]` Blind Hunter 10: the new memlog entries do not say whether a baseline was stamped, so `spec-surface-check` will report drift — disproved: `python scripts/spec_surface_reconcile.py` exits 0 ("no drift") and `python -m pyforge.doctor.sources spec-surface` exits 0 with "every tracked file governed or allowlisted; no drift"; no baseline was stamped and none was needed because the memlog entries are the reconcile.
  - `[low]` `[patch]` Blind Hunter 11: `DutyResult.summary` for `--schedule` is now multi-line but the `reconcile_schedule_batch` docstring does not say so — the docstring claim is real and fixed: `sync.py` now states that the summary carries one `<github_item_id>: <summary>` line per failed candidate and that `details["candidates"]` is unchanged. The other claims are refuted: no doc under `docs/` or `.claude/skills/pyforge-steward/` describes the summary shape (searched), and no summary in `sync.py` embeds a raw newline (response bodies are `!r`-escaped).
  - `[low]` `[reject]` Blind Hunter 12: the Code Map names the seven call sites wrongly ("Jira user lookup" where the code has the two GitHub assignee writes) — true, but the fix is to edit this build's spec, which review does not do; the accurate list is recorded under Auto Run Result.
  - `[low]` `[patch]` Blind Hunter 13: test typing — `_graphql` / `_jira_issue` are annotated `-> object` so `state.status` is `attr-defined`, and `HTTPError(..., None, None)` is `arg-type` — reproduced with `mypy tests/unit/test_sync_retry.py` (2 errors, lines 181 and 386; tests are outside the `lint-types` gate, which runs `mypy -p pyforge.steward`); fixed: `_graphql` returns `dict[str, object]`, `_jira_issue` returns `JiraIssueState`, and the deliberate `None` headers carries a commented `# type: ignore[arg-type]`; the file now passes `mypy` (rc 0). The `importorskip("yaml")` and the child-process-per-row loads copy `test_langflow_auth_posture.py` and are not defects.
  - `[low]` `[reject]` Edge Case Hunter 1: the transition POST is replayed after a 5xx that already applied it — same root cause and same evidence as Blind Hunter 3.
  - `[low]` `[reject]` Edge Case Hunter 2: `x-ratelimit-reset` is never read and a no-header secondary limit is retried within 7s — same root cause as Blind Hunter 1; a 60s floor would also contradict the intent's "exponential backoff otherwise".
  - `[low]` `[reject]` Edge Case Hunter 3: a GraphQL primary rate limit arrives as HTTP 200 with `errors[].type == RATE_LIMITED`, which `_send` does not inspect — outside the intent's status-based retry set; a primary limit resets on the hour, so a 1s/2s/4s retry cannot clear it, and the first answer still fails loud with the `RATE_LIMITED` error text in the `SyncAPIError`.
  - `[low]` `[reject]` Edge Case Hunter 4: no cumulative sleep budget across the batch — same root cause as Blind Hunter 4.
  - `[low]` `[reject]` Edge Case Hunter 5: a failed candidate's summary with a newline or a very long body breaks the one-line-per-candidate attribution — no summary construction in `sync.py` embeds a raw newline (bodies are `!r`-escaped, errors are dict reprs) and each entry is bounded by the 500-byte body slice; normalising whitespace is added code for a case not shown reachable.
  - `[low]` `[reject]` Edge Case Hunter 6: the deployed-process switch is silently ignored — same root cause as Blind Hunter 7.
  - `[false]` `[reject]` Edge Case Hunter 7: `scripts/platform-ci-local.sh:184` and `.github/workflows/platform-ci.yml:468` also run plain HTTP with `COMPONENT_RUNTIME=local` but lack the switch, so a cookie-based check against them would fail — disproved at those locations: both only `curl` GET `/ht/`, `/admin/login/`, `/` and `/api/health` (no cookie jar, no POST), so no check depends on a session or CSRF cookie; the intent names `compose.yml` as the documented stack.
  - `[low]` `[reject]` Edge Case Hunter 8: a transient `URLError` fails the candidate on the first attempt while rate limits get three retries — same root cause as Blind Hunter 6.
  - `[low]` `[reject]` Verification Gap, other finding 1: `_send` retries the Jira transition POST and the GitHub assignee writes on 502/503/504, and how Jira answers a repeated transition POST was not verified — same root cause as Blind Hunter 3; if the replay is rejected the cost is one loud per-candidate failure that the next run reconciles, so the claim is low whichever way the unverified part falls.
  - `[low]` `[reject]` Intent Alignment 1: the Problem is stated at the browser surface while the tests observe settings values and parsed YAML — the Acceptance Criteria themselves are stated at that surface ("When production settings load…", "When its environments are read…"), so expectation and test coincide; a login round trip needs the compose stack and is not a unit-level check.
  - `[false]` `[reject]` Intent Alignment 2: other surfaces that already set `DJANGO_SECURE_SSL_REDIRECT=False` (the CI `container` job, `platform-ci-local.sh`, the chart's `secureSslRedirect`) are left without the switch — disproved for the first two (GET-only smoke, see Edge Case Hunter 7); the chart sets no `COMPONENT_RUNTIME`, so it is a deployed process, which the intent's Never bullet bars from switching `Secure` off.
  - `[low]` `[patch]` Intent Alignment 3: the cookie test docstring says "two deployed rows" while four run — same root cause as Blind Hunter 9, fixed there.
  - `[false]` `[reject]` Intent Alignment 4: the retry wraps at the seven call sites, not around the transport callable, so a future direct `transport(...)` call would bypass it — disproved today: the only `transport(` calls left in `sync.py` are the two inside `_send`; AC4 requires the retry inside `github_graphql_request` with a fake passed to it directly, which an entry-point wrapper would not give; a future bypass is speculative.
  - `[false]` `[reject]` Intent Alignment 5: no test goes through the real `open_url`, so the "always `open_url`" boundary rests on reading — disproved: `_default_transport` still calls `http_bridge().open_url(...)` (the retry change only adds the `headers=` argument and does not touch that call), `test_keys_http_bridge.py` (Story 83.1) exercises the real bridge, and `test_sync_retry.py` drives `_default_transport` through a fake bridge to prove header capture.

## Auto Run Result

Status: done

**Summary.** The plain-HTTP compose stack now serves working login and CSRF cookies, `sync` retries rate limits within a bound, and a partial `--schedule` failure names each failed candidate. `production.py` composes `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` and the two cookie names from one switch, `DJANGO_INSECURE_LOCAL_COOKIES`, honoured only when `config.locality.is_local()` is true; a process whose `COMPONENT_RUNTIME` is not exactly `local` composes `Secure` cookies and the `__Secure-` names whatever its environment says. `compose.yml` sets the switch on `platform` and `worker`. `sync.py` gains `_send(transport, request)` at the seven transport call sites (GraphQL, the GitHub assignee add and remove, the Jira issue GET, the Jira fields PUT, and the transitions GET and POST): it makes 4 attempts in total, retries a 429, a 403 carrying `Retry-After` or `x-ratelimit-remaining: 0`, and a 502/503/504, sleeps `Retry-After` (capped at 60s) or 1s/2s/4s through the injectable `sync._sleep`, and returns every other status on the first answer. `TransportResponse` gains `headers` (empty default). `reconcile_schedule_batch` appends one `<github_item_id>: <summary>` line per failed candidate under the count line; `cli.py` is untouched and there is no new flag. DW-10-3-3, DW-8-4-1 and DW-FU-8-1-3 are closed in the tracked ledger.

**Files changed**
- `src/platform/config/settings/production.py` — the local-only cookie switch.
- `src/platform/compose/compose.yml` — the switch on `platform` and `worker`, with the plain-HTTP reason.
- `src/platform/tests/test_local_cookie_posture.py` (new, 9 tests) — child-process settings rows (local with the switch on, local with it off or unset, deployed with `COMPONENT_RUNTIME` unset, `production`, `staging` and `Local`) and the compose assertion.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py` — `_send` and its helpers, `TransportResponse.headers`, the failed-candidate lines.
- `src/shared/packages/pyforge-steward/tests/unit/test_sync_retry.py` (new, 46 tests) — every retry row, all seven call sites, header capture in `_default_transport`.
- `src/shared/packages/pyforge-steward/tests/unit/test_sync_duty.py`, `tests/unit/test_sync_reconcile_propagation.py` — stderr names the failed candidate through `main(["sync", "reconcile", "--schedule", ...])`; summary-line assertions on the existing batch tests.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md` — the three rows closed with `resolution:` and `verified:`.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md`, `.../spec-pyforge-unifying-strategy/.memlog.md` — surface-reconcile entries naming the governed paths.

**Review findings.** 27 findings across four layers, one pass: high 0, medium 0, low 22, false 5. Patches applied: 3 entries (4 rows, all low) — the stale "two deployed rows" docstring in the cookie test, the `reconcile_schedule_batch` docstring that did not mention the new summary lines, and two `mypy` errors in `test_sync_retry.py`. Deferred: none (`deferred: []`). Rejected: 18 `low` rows and 5 `false` rows, each with its reason in the Review Triage Log. The review patches were applied directly rather than by resuming the implementation subagent, because a resumed subagent runs in the background and this workflow forbids that.

**Follow-up review recommendation: `false`.** First pass, and no patched entry was `high` or `medium` (patched counts: high 0, medium 0, low 3). No specific unverified risk remains that a second pass would settle.

**Verification performed** (every verdict read from the exit code; run from the primary checkout's pixi environments with `PYTHONPATH` pointed at this worktree, because the worktree has no `.pixi/envs`)
- Steward station suite (`pytest src/shared/packages/pyforge-steward/tests`), after the patches: rc 0, 1974 passed, 5 skipped.
- Platform settings tests (`test_local_cookie_posture.py`, `test_langflow_auth_posture.py`, `test_broker_tls_verified.py`) in the `platform-ci-test` environment: rc 0, 80 passed; `test_local_cookie_posture.py` alone after the patches: rc 0, 9 passed.
- Mutation check (the spec's last criterion): replacing `is_local()` with `True` in `production.py` turned 4 deployed-process rows red (4 failed, 5 passed); the file was restored byte-for-byte.
- `ruff check`, `ruff format --check` and `mypy -p pyforge.steward` over the steward package: rc 0 each; `mypy tests/unit/test_sync_retry.py`: rc 0; `ruff check` and `ruff format --check` on the platform files touched: rc 0.
- `python scripts/spec_surface_reconcile.py`: rc 0 ("no drift"); `python -m pyforge.doctor.sources spec-surface`: rc 0. No baseline was stamped.
- The implementation subagent reported the full platform suite (1109 passed, 13 skipped) and `tests/packaging` (131 passed); I did not re-run those.
- Not run: the `pixi run ... pyforge-steward-test` and `platform-ci-local -- --test` wrappers as written, and `pr-preflight`.

**Residual risks**
- A Jira transition POST that was applied before a 502/503/504 is replayed and may be rejected, surfacing one loud `SyncAPIError` for a write that landed; the next run reconciles it. Whether Jira rejects the replay is unverified.
- A primary rate limit (`x-ratelimit-remaining: 0` with no `Retry-After`) only gets the 1s/2s/4s backoff, which cannot outlast it; it still fails loud after 4 attempts. A GraphQL primary limit arriving as HTTP 200 with `RATE_LIMITED` is not retried.
- There is no cumulative retry budget across a batch: a limit that starts mid-batch and outlasts three minutes costs up to about 180s per remaining candidate.
- Connection-level failures (`URLError`, a read timeout) are still not retried.
- `DJANGO_INSECURE_LOCAL_COOKIES=True` on a process that is not `COMPONENT_RUNTIME=local` is silently ignored (Secure cookies compose), by design.
- The Code Map above names the seven call sites loosely ("Jira user lookup"); the list in this Summary is the accurate one.
