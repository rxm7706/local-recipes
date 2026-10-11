---
title: "87.5: The herald webhook forward survives a client disconnect and proves AC 6 in any order"
type: 'fix'
created: '2026-10-10'
status: 'in-review'
baseline_revision: '47397de509c4b12b68309f77022ca915db29d5b5'
review_loop_iteration: 2
followup_review_recommended: false
landing_review: 'passed'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-87-4-the-herald-webhook-forward-closes-its-review-findings.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-87-3-the-host-forwards-herald-s-webhooks-to-the-mcp-host-sidecar.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-87-1-the-platform-host-boots-without-herald-and-says-why.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-83-18-a-re-dispatched-send-back-waits-for-its-landing-review.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-19-2-one-real-ship-records-itself-against-a-persistent-store.md
  - src/shared/packages/django-pyforge/src/django_pyforge/sidecar_forward.py
  - src/platform/config/asgi.py
  - src/platform/config/optional_components.py
  - src/platform/mcp_host/app.py
  - src/platform/config/flag-overlays.json
  - src/platform/tests/test_webhook_herald_forward_host.py
  - src/platform/tests/test_herald_webhook_sidecar.py
  - src/platform/tests/test_openfeature_file_flags.py
  - src/shared/packages/pyforge-core/tests/unit/test_flags.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/webhook.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/webhook_host.py
  - docs/explanation/platform-deployment-architecture.md
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 87.4 landed on `main` (merge `cd32c401cc`, spec promoted to `done`) without a held review. A
separate agent then reviewed the landed merge against 87.4's spec and recorded, in 87.4's `## Review Triage Log`, the
entry "2026-10-10 — Independent review of the landed merge `cd32c401cc`: FAIL (1 high, 1 medium, 3 low)". Its probes
confirmed what 87.4 fixed: every traversal, query, fragment, CRLF, case and slash variant gets the host's 404 and never
reaches the sidecar; `mcp-host-serve` binds `127.0.0.1:8090` and `/health` answers 200; `environment.yaml` equals its
export; both body caps answer 413 before the sidecar; the sidecar's 404 reads `exc.name`. It found five defects, and the
operator turned `pyforge.steward.herald_webhook_sidecar` OFF in dev again the same day (hygiene branch
`hygiene-874-dark-2026-10-10`). Line numbers below are at `bab2162d73`; the hygiene change touches none of these source
files.

- **[high] A client disconnect spins the host's event loop.** `_read_webhook_body`
  (`django_pyforge/sidecar_forward.py:74`-`:95`) `continue`s on every message whose type is not `http.request`
  (`:80`-`:81`). After a partial body (`more_body: true`), an `http.disconnect` arrives, and every later `receive()`
  returns `http.disconnect` again, so the loop never ends and never awaits anything that blocks. One unauthenticated
  connection pins a worker's event loop at 100% CPU. The review reproduced it through `config.asgi.application`:
  100,001 `receive()` calls. Herald's own reader raises `_ClientDisconnected` on `http.disconnect` and its handler
  returns without answering (`pyforge/herald/webhook.py:1019`, `:1064`-`:1065`, `:1316`-`:1317`).
- **[medium] The AC 6 tests pass only in one order.** `test_flag_off_reaches_in_process_herald` (`:313`-`:347`) and
  `test_host_unset_sidecar_url_does_not_forward` (`:350`-`:380`) of `src/platform/tests/test_webhook_herald_forward_host.py`
  reach the in-process herald, whose app is built once and cached in `webhook_host._application`
  (`pyforge/herald/webhook_host.py:224`, `__getattr__` `:230`-`:241`). The review found that the first test's
  `asyncio.run` shuts the executor the cached app depends on, and the second test then runs against that app. The file
  fails when run alone. Both tests also accept `201` or `401`, so a cached app holding another secret still passes.
- **[low] With the forward inactive, an unknown webhook path loses Story 87.1's answer.**
  `dispatch_herald_webhook_forward` (`:112`-`:132`) answers the host's generic 404 for any path under the prefix that
  is not on the allowlist (`:123`-`:125`) before it reads `MCP_HOST_SIDECAR_BASE_URL` (`:126`-`:128`) or the flag
  (`:129`-`:130`). So with the flag OFF or the URL unset, such a path no longer reaches the in-process herald (which
  answers its own 404, `webhook.py:1271`-`:1278`) or Story 87.1's 404 with the absent reason
  (`config/asgi.py:142`-`:149`).
- **[low] A sidecar env with no `pyforge` package answers 500.** `_dispatch_herald_webhook`
  (`src/platform/mcp_host/app.py:43`-`:66`) treats a `ModuleNotFoundError` as herald absent only when `exc.name` is
  `pyforge.herald` or starts with `pyforge.herald.` (`:50`-`:52`). Importing `pyforge.herald.webhook_host` where no
  `pyforge.*` package is installed raises with `exc.name == "pyforge"`, which is re-raised as a 500.
- **[low] AC 4's forward-ON tests prove less than they claim.** `test_host_forwards_only_literal_paths_no_query`
  (`:206`-`:229`) and `test_host_forwards_on_pr_close` (`:232`-`:245`) build the ASGI scope by hand (`_asgi_request`,
  `:125`-`:162`). They assert that `authorization` and `cookie` are dropped, but not that `content-type`,
  `x-hub-signature-256` and `x-hub-timestamp` reach the sidecar unchanged, nor that the sidecar's JSON body reaches the
  caller.

**Approach:** stop on a disconnect the way herald does, leave the host untouched while the forward is inactive, and
prove the forward through the host's real entry point in any test order. Then turn dev back ON, and land only after a
separate review passes.

- **A read that ends on a disconnect.** `_read_webhook_body` treats `http.disconnect` as the end of the request: it
  stops at once, the forward contacts no sidecar, and nothing is sent to the client, which is gone. Any other message
  whose type is not `http.request` ends the read the same way. The read never skips a message. The two caps and
  their 413 are unchanged.
- **AC 6 tests that share nothing.** A fixture sets `webhook_host._application` to `None` before and after each test
  that reaches the in-process herald, so each builds herald's app with its own secret and repo root. The tests assert
  the in-process herald's answer; neither accepts `401` as an alternative to it.
- **The forward inactive is Story 87.1's host.** `dispatch_herald_webhook_forward` reads the URL and the flag before the
  allowlist. With either missing it returns unhandled, so every path under the prefix behaves as Story 87.1 left it.
  The allowlist 404 applies only while the forward is active.
  - **Decision: keep Story 87.1's behaviour; do not document a change.** It is safe. With the forward inactive
    nothing leaves the process. The allowlist exists to stop a forward from reaching the sidecar's unauthenticated MCP
    faces. Herald's in-process router already matches its two paths with `==` and answers its own 404 for the rest.
    The generic 404 bought no safety and dropped 87.1's absent reason.
- **A sidecar without `pyforge` says herald is absent.** `_dispatch_herald_webhook` answers 404 when `exc.name` is
  `pyforge.herald`, its parent `pyforge`, or a module under `pyforge.herald.`. Any other missing module is re-raised,
  as 87.4 required.
- **Forward-ON tests through the real entry point.** AC 4's tests send the request with `httpx.ASGITransport` on
  `config.asgi.application`, as the flag-OFF tests already do. They assert the sidecar received `content-type`,
  `x-hub-signature-256` and `x-hub-timestamp` with the caller's values and no other request header. They assert the
  caller got the sidecar's status, content type and JSON body.
- **The flag comes back ON in dev, last.** Only after ACs (1) to (5) pass, in the same commit set:
  `src/platform/config/flag-overlays.json` (`dev` on), the two flag-default tables
  (`src/platform/tests/test_openfeature_file_flags.py` `_SHIPPED_BOOLEANS`,
  `src/shared/packages/pyforge-core/tests/unit/test_flags.py`), and 87.3's spec: its `flag.default` reads dev on, its
  **Flag** bullet names both dark periods, and its Spec Change Log gains one line naming this story. Staging and
  production stay OFF, for 87.3's reason (the chart and compose still hand the sidecar no herald store or secret,
  `DW-steward-87-3-2`).
- **The landing waits for an independent review.** This uses marshal Story 83.18's hold, unchanged:
  - The frontmatter above declares `landing_review: 'required'`. Marshal reads it with `parse_landing_review` and
    `landing_review_requires_hold`, and `resolve_hold_dispatch_landing` turns it into a hold
    (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_harness_done.py`).
  - The operator also dispatches with `--hold-landing`:
    `pixi run -e pyforge-guild marshal factory dispatch pyforge-steward 87.5 --hold-landing`. The flag is journaled on
    the launch INTENT under `hold_landing` (`HOLD_LANDING_PAYLOAD_KEY`), and the supervisor reads it back with
    `_hold_landing_from_launch` (`dispatch_supervisor/__main__.py`).
  - Held, a verified run pushes the branch, opens its PR as a draft and journals a `dispatch-land` verdict
    `held-for-review` (`DispatchLandingVerdict.HELD_FOR_REVIEW`, `dispatch_land.py`). It merges nothing, so dev stays
    OFF on `main`.
  - A separate agent, not the implementing session, reviews the diff against this spec and appends its verdict to this
    spec's `## Review Triage Log`.
  - If the review passes, the operator sets `landing_review: 'passed'` (or marks the PR ready for review) and
    `status: 'in-review'`, and re-dispatches. Story 83.7's land-only path lands it, and Story 89.1's gate lets it land
    only because the spec reads `in-review` and its latest entry records no failed review.
  - If the review fails, its entry carries `FAIL`, the story goes back to `ready-for-dev`, and nothing lands.
- **Herald 19.2 waits for this story.** Herald Story 19.2 (`blocked`) is gated on this story being `done` on `main`
  with its independent review passed, no longer on 87.3 or 87.4. That text in herald's spec, and the flip of its key,
  are herald's to write. This story flips no key.

Ledger key: `87-5-the-herald-webhook-forward-survives-a-client-disconnect-and-proves-ac-6-in-any-order`.
Type / Effort / Deps: fix / M / S-87.4.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-68 (the isolated mcp-host env and its task) and CAP-69 (the host
  forwards to the sidecar; sidecar down is loud), both from `spec-mcp-era-isolation`. These are the CAPs Stories 87.3
  and 87.4 bound. This story fixes their realization, so it mints no CAP and changes no `SPEC.md`.
- `spec-pyforge-unifying-strategy` CAP-10 stays met through Story 87.1: with the forward inactive, the host behaves
  exactly as 87.1 left it, now under the webhook prefix too.
- pap:AD-2: `src/platform/` never imports `pyforge.*`, and `django_pyforge` never imports `pyforge.herald`. Module
  names stay strings.
- **No flag of its own.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag. It restores the behaviour 87.3's
  flag gates, and it sets that flag's dev default back to ON.
- **Origin.** `docs/dreams/pyforge-steward.md` Realization log, 2026-10-10 (herald forward disconnect). Operator ruling
  2026-10-10, verbatim label: "Dark again + mint 87.5 (Recommended)".

## Acceptance Criteria

Every criterion runs in `platform-ci-test` (through `platform-ci-local -- --test`), where herald is installed beside the
host's packages. A fake sidecar records every request it receives.

- **(1) A disconnect ends the read.**
  - **Given** the forward active **When** `config.asgi.application` receives a `POST` to `on-ship` whose `receive()`
    returns one `http.request` with a partial body and `more_body: true`, then `http.disconnect` on every later call
    **Then** the call returns within one second (`asyncio.wait_for`), `receive()` was awaited exactly twice, the fake
    records nothing, and no `http.response.start` is sent.
  - The same holds when the second message has a type other than `http.request` or `http.disconnect`.
  - A body completed normally, a body of exactly 1,000,000 bytes, and both 413 cases behave as 87.4 left them.
- **(2) The AC 6 tests pass in any order.**
  - A fixture sets `webhook_host._application` to `None` before and after each test that reaches the in-process
    herald (restored by `monkeypatch`, so no test leaks a built app).
  - `test_flag_off_reaches_in_process_herald` and `test_host_unset_sidecar_url_does_not_forward` assert the in-process
    herald's answer to the signed request; neither accepts `401` as an alternative.
  - Proven three ways, each exiting 0: the file alone (`pytest -p no:randomly` on the file); the two tests in reverse
    order (their node ids passed to `pytest -p no:randomly` reversed); and the full suite (`platform-ci-local -- --test`).
- **(3) The forward inactive keeps Story 87.1's answers.**
  - **Given** the flag OFF, and separately `MCP_HOST_SIDECAR_BASE_URL` unset **When** `POST
    /stations/herald/api/v1/webhooks/other` reaches `config.asgi.application` **Then** the in-process herald answers it
    (its own 404, `no such webhook route`), and with herald refused by a meta-path finder it gets Story 87.1's 404 with
    the absent reason. The fake records nothing.
  - **Given** the forward active **Then** the same path gets the host's `{"detail": "Not Found"}` and 87.4's AC (1)
    rejections pass unchanged.
- **(4) A sidecar without `pyforge` says herald is absent.** Through `starlette.testclient.TestClient(mcp_host.app.app)`:
  - a meta-path finder refusing `pyforge` itself, with `pyforge` and every `pyforge.herald*` module taken out of
    `sys.modules` through `monkeypatch` (so they come back), gives 404 with JSON naming the missing module;
  - 87.4's cases stay: a finder refusing `pyforge.herald` gives 404, and a finder refusing `pyforge.core.errors` gives
    no 404 (the error propagates), with `/health` still 200 afterwards;
  - no test patches `importlib.import_module`.
- **(5) The forward-ON tests prove the headers and the answer.** Through `httpx.ASGITransport` on
  `config.asgi.application`, with the forward active:
  - a signed `POST …/webhooks/on-ship?x=1` with body B and the headers `Content-Type`, `X-Hub-Signature-256`,
    `X-Hub-Timestamp`, `Authorization` and `Cookie` reaches the fake once, at `<base>/stations/herald/api/v1/webhooks/on-ship`
    with no query string, with body B byte for byte;
  - the fake's recorded headers are exactly `content-type`, `x-hub-signature-256` and `x-hub-timestamp`, each with the
    caller's value;
  - the caller gets the fake's status (`201`), its `content-type` (`application/json`) and its JSON body
    (`{"forwarded": true}`);
  - `on-pr-close` is forwarded the same way.
- **(6) The flag comes back ON in dev, and only in dev.**
  - `src/platform/config/flag-overlays.json` reads `dev` on, `staging` off, `production` off for
    `pyforge.steward.herald_webhook_sidecar`, and both flag-default tables expect the same.
  - 87.3's spec `flag.default` reads `{production: off, staging: off, dev: on}`. Its **Flag** bullet says dev was OFF
    from the first hygiene change until 87.4, and again from the second until this story. Its Spec Change Log gains one
    dated line naming this story.
  - `test_herald_webhook_sidecar_flag_two_states` passes unchanged.
  - `pixi run --frozen -e pyforge-guild flag-gate-check` exits 0, and `flag-gate-check -- --spec` on 87.3's spec
    returns `pass`.
  - This change lands in the same commit set as ACs (1) to (5), never before them.
- **(7) Nothing else moves.**
  - `src/platform/tests/test_mcp_host_sidecar.py`, `test_mcp_transport_auth.py` and `test_host_boots_without_herald.py`
    pass unedited, and 87.4's ACs (1), (2) and (3) still pass.
  - `pixi.toml`, `pixi.lock` and `environment.yaml` do not change.
  - `git diff origin/main -- src/platform` contains no `import pyforge` or `from pyforge`, and
    `git diff origin/main -- src/shared/packages/django-pyforge` contains no `pyforge.herald`.
  - `docs/explanation/platform-deployment-architecture.md` says that with the forward inactive the whole webhook prefix
    behaves as Story 87.1 left it, and that a client disconnect mid-body ends the read with nothing forwarded.
    `docs-currency-check` exits 0.
- **(8) Mutations fail the tests.**
  - Restoring the `continue` on a message that is not `http.request` fails AC (1).
  - Dropping the fixture's cache reset fails AC (2)'s reversed-order run.
  - Moving the allowlist check back before the URL and flag checks fails AC (3).
  - Dropping the parent `pyforge` from the absent check fails AC (4).
  - Forwarding a header off the allowlist, or answering with anything but the sidecar's body, fails AC (5).
- **(9) The landing is held for an independent review.**
  - The verified run journals a `dispatch-land` verdict `held-for-review` naming a draft PR, and `main` does not move.
  - The story lands only after a separate agent's passing entry is the latest in this spec's `## Review Triage Log`
    and the operator has released the hold (`landing_review: 'passed'`, or the PR marked ready).

## Boundaries & Constraints

**Always:**
- Change only these paths:
  - `src/shared/packages/django-pyforge/src/django_pyforge/sidecar_forward.py`;
  - `src/platform/mcp_host/app.py`;
  - `src/platform/tests/` (`test_webhook_herald_forward_host.py`, `test_herald_webhook_sidecar.py`,
    `test_openfeature_file_flags.py`, and new tests), `src/platform/config/flag-overlays.json`, and
    `src/shared/packages/pyforge-core/tests/unit/test_flags.py`, for the flag and the tests;
  - 87.3's spec (`flag.default`, its **Flag** bullet and one Spec Change Log line only);
  - `docs/explanation/platform-deployment-architecture.md`, and `docs/governance/flag-inventory/` through
    `flag-inventory` only.
- Turn the dev default ON in the same commit set as the fixes, after they pass.
- Keep `landing_review: 'required'` in this spec's frontmatter until the operator releases the hold.
- Reconcile every governed path the change touches on the memlogs of the Specs that govern it, then stamp those Specs
  scoped: `spec-pyforge-steward` and every co-governor `spec-surface-check` names (`spec-pyforge-core` governs
  `test_flags.py`; AGENTS.md pre-PR item 5).
- Run every pixi task from the repo root, and read every verdict from its exit code, never through a pipe.

**Never:**
- Never contact the sidecar, or send a response, after a client disconnect that arrives before the full body has
  been read (mid-body). A disconnect after the full body has been read is the accepted case below.
- Never forward a path outside herald's two webhook paths, any client query string, or a header off 87.3's allowlist.
- Never write `import pyforge` or `from pyforge` under `src/platform/`, and never import `pyforge.herald` from
  `django_pyforge`.
- Never change the MCP proxy path, `mcp_dual_era.read_body`, herald's code, `config/asgi.py`, `pixi.toml`, the chart,
  compose or the Containerfile.
- Never turn the flag ON in staging or production.
- Never edit 87.3's or 87.4's acceptance criteria, Review Triage Log or status. The implementing session never edits
  this spec's `landing_review:`, and never rewrites or removes a Review Triage Log entry it did not write.
- Never run `pixi add`, `pixi update` or an unfrozen install, and never hand-edit `SPEC.md`, a ledger or a derived
  file.

**Accepted (not watched):**
- A client disconnect after the full body has been read is not watched. The forward completes against the sidecar,
  bounded by the 300 s timeout floor (`CELERY_HARD_LIMIT_SECONDS` through `proxy_timeout_seconds`,
  `django_pyforge/mcp_http.py`), and the server drops the response sent into the closed connection. Nothing spins,
  nothing leaks, and no exception escapes. (Independent review iteration 1, F6.)

## I/O & Edge-Case Matrix

| Request | Today (`bab2162d73`) | After |
|---|---|---|
| forward active, partial body then `http.disconnect` | `receive()` called forever; the event loop spins | read ends at once; nothing forwarded or sent |
| forward active, a message type other than `http.request` | skipped; the read keeps waiting | read ends; nothing forwarded or sent |
| forward active, body complete, or over a cap | forwarded, or 413 | unchanged |
| forward active, client disconnects after the full body is read | forwarded; the server drops the answer | unchanged (accepted, not watched) |
| flag OFF or URL unset, `…/webhooks/other` | host's generic 404 | in-process herald's 404, or 87.1's 404 with the absent reason |
| forward active, `…/webhooks/other` | host's 404, nothing forwarded | unchanged |
| sidecar, no `pyforge` package at all | 500 | 404 naming the missing module |
| sidecar, `pyforge.herald` missing | 404 | unchanged |
| sidecar, a dependency of herald missing | the error propagates | unchanged |
| the AC 6 tests run alone or reversed | fail | pass |

</intent-contract>

## Binding

- Parent Spec capabilities: `spec-pyforge-steward` CAP-68 and CAP-69 (both from `spec-mcp-era-isolation`), the CAPs
  Stories 87.3 and 87.4 bound.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-10 (herald forward disconnect) entry.
- Epic: Epic 87 (`in-progress`). No new epic: 87.4, whose review findings this story closes, is in the same epic.
- Ledger key: `87-5-the-herald-webhook-forward-survives-a-client-disconnect-and-proves-ac-6-in-any-order`.
- Ledger status at mint: `backlog`.
- Deps: S-87.4 (`done` on `main`), whose code this story fixes.
- Review source: 87.4's spec, `## Review Triage Log`, "2026-10-10 — Independent review of the landed merge
  `cd32c401cc`: FAIL (1 high, 1 medium, 3 low)". This story closes its five items.
- Landing: held for an independent review by marshal Story 83.18's mechanism (`landing_review: 'required'` above, and
  `--hold-landing` at dispatch), released only after that review passes.
- Cross-station: herald Story 19.2 (`19-2-one-real-ship-records-itself-against-a-persistent-store`, `blocked`) is gated
  on this story, not on 87.3 or 87.4. 19.2's spec still names 87.3 as its gate. That text and the flip of 19.2's key
  are herald's to write, after this story is `done` on `main` with its independent review passed. This story flips no
  key.
- Spec: the `spec-pyforge-steward` memlog records the ruling and this mint. No `SPEC.md` changes.
- Surface: Epic 87's `[epic_surfaces]` entry already holds every path in the Always list.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `python scripts/spec_surface_reconcile.py` — expected: exit 0 (the derived surface guard).

**Manual checks (not a dispatch gate):**
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: exit 0, including the new tests of ACs (1) to
  (5), `test_herald_webhook_sidecar_flag_two_states`, and the unedited files of AC (7).
- AC (2)'s order proof, from `src/platform` with the `platform-ci-test` interpreter `platform-ci-local` uses
  (`env -u PYTHONSAFEPATH python -m pytest -p no:cacheprovider -p no:randomly`): the file
  `tests/test_webhook_herald_forward_host.py` alone, then
  `tests/test_webhook_herald_forward_host.py::test_host_unset_sidecar_url_does_not_forward`
  `tests/test_webhook_herald_forward_host.py::test_flag_off_reaches_in_process_herald` in that order — expected: exit 0
  both times.
- `pixi run --frozen -e pyforge-guild flag-gate-check` and `… flag-gate-check -- --spec` on 87.3's spec — expected:
  exit 0 and `pass`.
- The five mutations of AC (8) — expected: each fails its named test.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconciles and scoped
  stamps.
- `git diff origin/main -- src/platform` searched for `import pyforge` and `from pyforge`, and
  `git diff origin/main -- src/shared/packages/django-pyforge` searched for `pyforge.herald` — expected: no match.
- AC (9): the run's journal holds a `dispatch-land` verdict `held-for-review`, and the PR is a draft until the
  independent review's passing entry is recorded here.

## Spec Change Log

### 2026-10-11 — Implementer response to review iteration 1

Answers the send-back "Independent review, iteration 1: sent back (1 major, 4 minor, 2 info, 1 trivial)" in the Review
Triage Log. No change to `sidecar_forward.py` or `mcp_host/app.py`; the review found that code correct.

- **F1 (major, required).** `src/platform/tests/test_webhook_herald_forward_host.py`: both fake `receive()` functions
  in `test_client_disconnect_after_partial_body_ends_read` and `test_non_request_message_ends_body_read` now
  `await asyncio.sleep(0)` first, as a real server's `receive()` suspends, so `asyncio.wait_for(timeout=1.0)` can fire
  when the read loop skips a message and calls again.
  - **AC (8) bullet 1, mutation evidence.** Done in a scratch copy (`git archive HEAD src pixi.toml`, this pass's two
    test files copied in), never in the worktree. Control, unmutated: `timeout 120 env -u PYTHONSAFEPATH python -m
    pytest -p no:cacheprovider -p no:randomly -q` on the two node ids, from the copy's `src/platform` with the
    `platform-ci-test` interpreter: exit 0, `2 passed`. Mutation: `raise _ClientDisconnected()` in
    `_read_webhook_body` replaced by `continue` (87.4's line), same command: exit 1 (not 124), `2 failed` in about
    2.7 s; each test's call phase took 1.00 s and failed with `E   TimeoutError` (`asyncio/timeouts.py:115`, raised
    from the `CancelledError` delivered at the fake's `await asyncio.sleep(0)`). Repeated on the final test files with
    the same result; the worktree's `sidecar_forward.py` equals `HEAD`.
- **F2 (minor).** `src/platform/tests/test_herald_webhook_sidecar.py`: the dependency-missing test removes
  `pyforge.core.errors` and the `pyforge.herald.*` modules with `monkeypatch.delitem(sys.modules, name,
  raising=False)`, so they come back at teardown, and its `finally` no longer re-imports herald while they are out
  (that re-import minted the second `pyforge.core.errors`; the autouse fixture resets `webhook_host._application` on
  the restored module). The herald-absent test's bare `del sys.modules[name]` in the same file got the same fix (same
  defect class, same "any order" property). Proof: the dependency-missing test then
  `test_mcp_host_sidecar_missing_secret_503`, by explicit node ids in that order with `-p no:randomly`: exit 0
  (`2 passed`); the same pair against `HEAD`'s copy of the file, in the scratch copy: exit 1
  (`test_mcp_host_sidecar_missing_secret_503` fails with a `HeraldError` that escapes the 503 handler).
- **F3 (minor).** The no-pyforge test asserts `detail.endswith("(pyforge)")`, matching `mcp_host/app.py`'s
  `f"pyforge.herald is not installed ({name})"`.
- **F4 (minor).** A parametrized `forward_inactive` fixture (`flag_off`: URL set, flag OFF; `url_unset`: URL unset,
  flag ON; providers cleared at teardown) drives both AC (3) inactive tests, so herald present and herald absent each
  run under both, four combinations in all.
- **F5 (minor).** `test_host_forwards_on_pr_close` posts a non-empty body with a query string and, through a helper
  shared with the on-ship test, asserts the exact sidecar URL (no query), one request, body bytes, the three forwarded
  header names and values, and the response's status, `content-type` and JSON body.
- **F6 (info).** Boundaries & Constraints gains **Accepted (not watched)**: a disconnect after the full body has been
  read is not watched; the forward completes against the sidecar within the 300 s floor and the server drops the
  answer. The **Never** bullet now names the mid-body case only, and the I/O matrix gains the matching row.
- **F7 (info), F9.** No action; both were already closed by the merge of `origin/main` (`c7162c5438`).
- **F8 (trivial).** `docs/explanation/platform-deployment-architecture.md:322`: the triple space is one space.
- **Order proofs.** Using a scratch-only seeded reordering plugin over the two test files (39 tests): forward, files
  reversed, every item reversed, eight file-grouped shuffles (seeds 1-8) and sixteen interleaved shuffles (seeds
  1-16): every run exit 0. The same plugin and seeds against `HEAD`'s two files (37 tests) failed 5 of 8 grouped and
  4 of 16 interleaved runs, every failure `test_mcp_host_sidecar_missing_secret_503`. AC (2)'s two runs: the file
  alone, exit 0 (`23 passed`); the two tests reversed by node id, exit 0.
- **Surface.** `spec-surface-check` exited 2 with drift on `spec-pyforge-unifying-strategy` alone: the two test files
  and three of this story's implementation paths (`sidecar_forward.py`, `flag-overlays.json`,
  `test_openfeature_file_flags.py`), whose stamp atlas Story 25.1 recorded on `main` before the merge. Two memlog
  entries on that Spec name those five paths and the two more the scoped stamp moves (`mcp_host/app.py`,
  `pyforge-core/tests/unit/test_flags.py`); stamped with `--spec pyforge-steward/spec-pyforge-unifying-strategy`
  only, then `spec-surface-check` exit 0.
- **Verification (exit codes).** `pixi run --frozen -e pyforge-guild platform-ci-local -- --test`: 0 (every step
  PASS; full suite `1204 passed, 13 skipped`). The three platform test files with `helm` on `PATH`: 0
  (`91 passed`), and 0 in four interleaved shuffles across all three. `ruff check`, `ruff format --check` and `mypy`
  (src/platform's own config) on the two changed test files: 0, 0, 0. `spec-surface-check`,
  `chain-currency-sweep-check`, `deferred-work-check`, `docs-currency-check`, `story-status-check`: 0 each.

### 2026-10-10 — Minted

- 2026-10-10: minted from the operator's ruling "Dark again + mint 87.5 (Recommended)": Story 87.4 stays `done` on
  `main`, the forward is dark in dev again, and this story closes 87.4's independent review findings, then turns dev
  back ON. A `fix` under the CAPs 87.3 and 87.4 bound, in Epic 87, with no flag of its own, landed only after an
  independent review passes (marshal Story 83.18's hold).

## Review Triage Log

### 2026-10-11 — Independent review, iteration 2: PASS (1 minor, 1 trivial and 1 pre-existing hang deferred)

- Separate agent, fresh review of `git diff origin/main...HEAD` at `60935ffe6c` (origin/main `15b4d5cf42`, merges cleanly); every mutation in a scratch copy. ACs (1)-(9) pass with file:line evidence.
- Iteration-1 findings re-probed: F1 closed (restoring `continue` now fails both disconnect tests in 1.00 s with `TimeoutError`, exit 1, also under platform-ci-local's concurrent load); F2 closed (dependency-missing then `missing_secret_503` exits 0; 24 interleaved and 18 further shuffled orders exit 0); F3, F4, F5 closed (each named mutation fails its test); F6 recorded as accepted; F8 fixed. Every AC (8) mutation fails its test.
- Gates, each exit 0: `platform-ci-local -- --test` (1204 passed, 13 skipped), `pyforge-steward-test` (2306 passed, 3 skipped), `lint-types`, `spec-surface-check`, `flag-gate-check`, `docs-currency-check`, `scripts/spec_surface_reconcile.py`, pyforge-core `test_flags.py` (161).
- Spec-surface stamp moves only `pyforge-steward/spec-pyforge-unifying-strategy`; its two memlog entries name all seven moved paths with reasons.
- Deferred: `DW-steward-87-5-1` (minor: the AC (3) herald-absent test leaks `_absent_reasons`/`_logged_absent` and re-imports a second herald copy in its `finally`; trivial: two docstrings still say the flag is OFF until 87.4) and `DW-steward-87-5-2` (info, predates 87.5: the module-scoped `TestClient(mcp_host_app)` fixture hangs at teardown when set up twice in one process).
- Note: the branch no longer carries the flag-inventory regeneration (iteration-1 F7); references to it in this spec's Auto Run Result and the 2026-10-10 steward memlog event describe the first pass only.
- Verdict: landing review passed; `landing_review` set to `passed`.

### 2026-10-11 — Independent review, iteration 1: sent back (1 major, 4 minor, 2 info, 1 trivial)

Separate agent, on `1ff032b979` (PR #2111, held for review). Code in `sidecar_forward.py` and `mcp_host/app.py` is
correct; ACs (1)–(7) and (9) pass, each probed by mutation in a scratch copy. Gates exit 0: pyforge-steward suite
(2306 passed, 3 skipped), pyforge-core `test_flags.py` (161), the three platform test files (89), ruff/format/mypy on
the changed files, `spec-surface-check`. AC (8) bullet 1 FAILS: the disconnect regression test cannot fail.

- `[major]` `[patch]` F1 `src/platform/tests/test_webhook_herald_forward_host.py:372-381`, `:396` (same at
  `:411-420`, `:435`): the fake `receive()` never suspends, so with the `continue` restored the read loop never yields
  and `asyncio.wait_for(timeout=1.0)` cannot fire -- the test hangs (killed at a 60 s cap, exit 124) instead of
  failing, and would hang `platform-ci-local`/pr-preflight indefinitely and CI to its 45-minute timeout. Fix: `await
  asyncio.sleep(0)` at the top of both fake `receive()` functions (or raise after ~3 calls); then re-run AC (8) bullet
  1 and record that the mutation fails in about 1 s with `TimeoutError`.
- `[minor]` `[patch]` F2 `src/platform/tests/test_herald_webhook_sidecar.py:463-483` (from 87.4, in a file this story
  edits, and it breaks the "any order" property): the dependency-missing test pops `pyforge.core.errors` and
  `pyforge.herald.*` from `sys.modules` and never restores them, so `HeraldError` splits into two classes and
  `test_mcp_host_sidecar_missing_secret_503` fails whenever it runs after it (2 of 8 file-grouped shuffles, 5 of 16
  interleaved). Fix: `monkeypatch.delitem(sys.modules, ...)`.
- `[minor]` `[patch]` F3 `test_herald_webhook_sidecar.py:158`: `"pyforge" in detail` is always true (every detail
  starts "pyforge.herald is not installed"); assert `detail.endswith("(pyforge)")`.
- `[minor]` `[patch]` F4 AC (3) tests cover 2 of 4 combinations (flag OFF with herald present; URL unset with herald
  absent); parametrize over both axes.
- `[minor]` `[patch]` F5 the on-pr-close test (`test_webhook_herald_forward_host.py:277-298`) does not check body
  bytes, header values or response content type; assert them as the on-ship test does.
- `[info]` F6 a client disconnect after the full body is read is not watched: the forward still calls the sidecar,
  waits up to the 300 s timeout floor (`mcp_http.py:63`, `:295`) and sends into a closed connection that uvicorn drops
  -- no spin, no leak, no escaping exception. Record this as an explicit acceptance in the spec's Boundaries (the
  "Never" bullet reads broader than the edge-case matrix, which covers only mid-body disconnects).
- `[info]` F7 the flag-inventory rewrite is real generator output catching up main's drift, not this story's; the
  merge of `origin/main` (`c7162c5438`) takes main's inventory, so the branch no longer carries it.
- `[trivial]` F8 triple space at `docs/explanation/platform-deployment-architecture.md:322`.
- F9 (merge conflict in `spec-pyforge-core/.memlog.md`): resolved main-first in `c7162c5438`.

Send-back: F1 required; F2, F3, F4, F5, F8 in the same pass; F6 recorded as an acceptance. No change to the code
under test. A fresh independent review (iteration 2) gates the landing.

### 2026-10-11 — Build-auto review pass

- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (none — diff matches intent-contract ACs (1)–(7); verification green locally)
- note: `landing_review: required` — a separate agent must still review the landed diff and append a passing entry before merge (marshal Story 83.18).

## Auto Run Result

Status: in-review

Implementation on branch `dispatch/pyforge-steward/87.5`: `_read_webhook_body` stops on non-`http.request` messages (including `http.disconnect`); `dispatch_herald_webhook_forward` checks URL and flag before the allowlist; mcp-host treats missing `pyforge` as herald absent; AC 6 tests reset `_LazyWebhookASGI` and `webhook_host._application`; forward-ON tests use `ASGITransport` and assert forwarded headers and sidecar JSON; dev flag ON restored in overlays and flag-default tables; 87.3 spec flag metadata updated; platform deployment doc and flag-inventory regenerated.

Verification: `python scripts/spec_surface_reconcile.py` exit 0; `pixi run --frozen -e pyforge-steward pyforge-steward-test` 2307 passed; `pixi run --frozen -e pyforge-guild platform-ci-local -- --test` PASS; `flag-gate-check` and `flag-gate-check -- --spec` on 87.3 pass; AC (2) reversed-order pytest exit 0.

Surface reconcile memlogs: `spec-pyforge-steward/.memlog.md` and `spec-pyforge-core/.memlog.md` (pyforge-marshal project) name every governed path touched.

Follow-up review recommended: false (no patched review findings this pass).

Residual: independent landing review and draft PR hold per AC (9); ledger sync and scoped spec-surface stamps before merge PR.
