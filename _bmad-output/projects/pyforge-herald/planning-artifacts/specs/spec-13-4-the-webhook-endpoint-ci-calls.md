---
title: 'The webhook endpoint CI calls'
type: 'feature'
created: '2026-08-13'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
baseline_revision: '18dca9e3ad21dfccfec2921f485abc57a718e5cb'
final_revision: '2a9196de7f'
---

<intent-contract>

## Intent

**Problem:** Herald's Progress/Claim records are created only by an operator running CLI
commands by hand today -- `cli.py`'s own docstring, `docs/cli-runbooks.md`, and
`docs/automation-troubleshooting.md` all state "no webhook infrastructure exists" -- so an
unrecorded ship is indistinguishable from no ship. Epic 13's LB-2 capability requires a real
HTTP endpoint CI calls automatically, riding Steward's `spec-secure-live-dashboards`
identity/trust boundary (AD-8/AD-9) rather than inventing a bespoke one.

**Approach:** Add one new, framework-agnostic module, `webhook.py`, exposing HMAC-verified
handler logic that calls the exact same `progress.upsert`/`claims.create` storage functions
the CLI verbs already call, wrapped in a thin ASGI3 callable (`create_app(repo_root, secret)`)
matching AD-8's "protocol, not framework" mounting contract. This story builds and fully
tests the handler in isolation; it does not deploy, mount, or wire it into Steward's live
perimeter or any GitHub Actions workflow -- Story 13.6 demonstrates the live end-to-end path,
which is why this story's ACs verify the handler directly rather than via a real merge.

## Boundaries & Constraints

**Always:**
- First AC records the CI-system/events decision (this Spec's second open question, per
  epics.md): CI system = **GitHub Actions** (the repo's only CI system). `on-ship` fires from
  a workflow step run after a successful push to `main` -- mirrors this repo's own existing
  "push to main = ship happened" convention (`dashboard.yml`/`detectors.yml`), not GitHub's
  native `pull_request closed+merged` event, which no existing workflow here uses.
  `on-pr-close` fires from a `pull_request: types: [closed]` step; the handler itself gates
  on the payload's own `merged`+`gates_passed` booleans, never on the HTTP event alone.
- `webhook.py` splits into: (a) small sync, directly-testable core functions
  (`verify_signature`, `handle_on_ship`, `handle_on_pr_close`) with zero framework coupling,
  and (b) a thin `create_app(repo_root, secret)` factory returning a raw
  `async def app(scope, receive, send)` -- mirrors `transport/mcp_transport.py`'s own
  "one `asyncio.run()` boundary around sync core" precedent; avoids a new async-test
  dependency.
- HMAC: `hmac.compare_digest(hmac.new(secret, raw_body, hashlib.sha256).hexdigest(), ...)`
  against an `X-Hub-Signature-256: sha256=<hex>` header (our own convention for our own POST,
  not a GitHub platform requirement). `secret` is read once, at `create_app` construction,
  from env var `HERALD_WEBHOOK_SECRET` -- never a literal or default fallback. Provisioning
  that env var's value via Steward's `keys` surface is a deployment concern, out of Surface.
- `on-ship` calls `progress.upsert(...)`: `station`/`shipped_capabilities`/`compute_hours`/
  `token_spend`/`wall_clock_hours`/`unblock_narrative` read from the payload with the same
  defaults CLI flags default to (`[]`, `0.0`, `0`, `0.0`, `""`); `date` is always server-computed
  `datetime.now(UTC).date().isoformat()`, mirroring `_run_progress_update` exactly, never
  caller-supplied.
- `on-pr-close` calls `claims.create(...)` only when payload `merged` and `gates_passed` are
  both `true`; any other combination is a no-op returning 202 -- never an error. `evidence`
  entries, if present, are passed through as already-shaped `{type,url,label}` objects; the
  handler never parses a PR title or GitHub-specific payload to infer `project_name`.
- Payload validation (structural: required fields present, correct JSON types) happens before
  any storage call and maps to 400; only exceptions raised BY `progress.upsert`/
  `claims.create` are eligible for retry/500.
- Retry wraps the storage call only: max 3 attempts, 1s/2s/4s backoff, on any
  `errors.HeraldError`. The retry helper's sleep function is injectable (default `time.sleep`,
  tests inject a no-op). Any id/timestamp the retried call needs (`claims.create`'s
  `id_factory`) is generated once before the loop -- a retry after a would-be-successful first
  attempt is idempotent (either succeeds once, or hits the existing duplicate-id guard, never
  a silent duplicate).
- Retries exhausted: emit one structured (JSON) ERROR-level log record (event type, payload
  summary, exception) as the operator-alert mechanism -- no email/Slack/other channel exists
  in this repo to build against. Return non-2xx so CI's own delivery-retry can re-fire later.
- New `tests/test_webhook.py` follows this package's conventions: `tmp_path`-scoped DB paths,
  no real sockets (a hand-constructed `scope`/`receive`/`send` triple needs none, honoring
  `deny_network`), `caplog` for the alert-log assertion, mutation-worthy coverage of the
  gating (`merged`/`gates_passed`) and retry-idempotency logic specifically.

**Block If:** none identified -- every input this story's Surface touches (progress/claims
signatures, `db.py`'s transaction seam, AD-8/AD-9's stated contract) is already resolved by
prior stories or this spec's own first-AC decision.

**Never:**
- Add Django/Channels/asgiref/channels_redis (or any web-server framework) as a
  `pyforge-herald` dependency -- the ASGI3 callable is a plain-Python protocol.
- Mount, deploy, or wire this handler into Steward's live perimeter, write any
  `.github/workflows/*.yml`, or stand up a live/listening server -- out of Surface here
  (Story 13.6's job).
- Import `pyforge-steward` at runtime for secret resolution -- its `keys` module's actual API
  is provisioning/rotation-shaped, not a runtime secret-fetch accessor.
- Re-validate `station` against `progress.STATIONS` -- `progress.upsert` already accepts any
  station name by design; the CLI's "did you mean" hint is CLI-only sugar.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Valid on-ship | Signed POST, station + minimal fields | 201, Progress upserted for today | No error |
| Valid on-pr-close, shipped | `merged=true`, `gates_passed=true`, `project_name` present | 201, draft Claim created | No error |
| on-pr-close, not shipped | `merged=false` or `gates_passed=false` | 202, no record created | No error (explicit no-op) |
| Missing/invalid HMAC | Signature header absent or mismatched | 401, no storage call attempted | Rejected before body parsed |
| Malformed payload | Non-JSON body, or missing required field | 400, no storage call attempted | Rejected before storage call |
| Transient failure, recovers | `progress.upsert` raises `HeraldError` on attempt 1, succeeds on attempt 2 | 201, one retry, no alert | Retried once |
| Failure, retries exhausted | `progress.upsert`/`claims.create` raises `HeraldError` on all 3 attempts | 500, one structured ERROR log | Alert logged, non-2xx returned |
| Unknown path/method | GET, or a path other than the two webhook routes | 404 / 405 | Rejected before body read |

</intent-contract>

## Code Map

- `src/pyforge/herald/webhook.py` -- NEW: `verify_signature`, `handle_on_ship`,
  `handle_on_pr_close`, the retry/backoff helper, structured-alert logging, and
  `create_app(repo_root, secret)` returning the ASGI3 callable.
- `src/pyforge/herald/progress.py`, `claims.py` -- READ-ONLY reference: `upsert`/`create`
  signatures the handler calls through unchanged.
- `tests/test_webhook.py` -- NEW: HMAC verify (valid/invalid/missing), payload validation,
  on-ship happy path, on-pr-close gating (both true / either false), retry-then-recover,
  retry-exhausted-then-alert, one raw-ASGI `scope`/`receive`/`send` smoke test.
- `docs/cli-runbooks.md`, `docs/automation-troubleshooting.md`, `docs/operator-guide.md` --
  MODIFY: replace "no webhook infrastructure exists" language with the endpoint's actual
  behavior and its known boundary (built and tested, not yet mounted/deployed).
- `tests/test_bridge.py` -- MODIFY (unplanned, required): `webhook` joins the
  `_BRIDGE_CORE_MODULES` determinism sweep, which fails by design for any new package module.
- `src/pyforge/herald/cli.py` -- MODIFY: correct the now-stale "there is no webhook anywhere
  in this module" docstring comment (~lines 11-14). No behavior change.

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/herald/webhook.py` -- create module (HMAC, handlers, retry/backoff,
  alert logging, ASGI3 factory) -- the whole new capability
- [x] `tests/test_webhook.py` -- create -- proves HMAC/gating/retry-idempotency/alert
  behavior before trusting it
- [x] `docs/cli-runbooks.md`, `docs/automation-troubleshooting.md`, `docs/operator-guide.md`
  -- update stale "no webhook" text -- keeps operator docs truthful after this story
- [x] `src/pyforge/herald/cli.py` -- fix the stale docstring comment -- text only

**Acceptance Criteria:**
- [x] Given the epics.md "which CI system, which events" open question, when this story is
  planned, then the decision (GitHub Actions; `on-ship` on push-to-main, `on-pr-close` on
  `pull_request closed` gated by payload `merged`+`gates_passed`) is recorded above as this
  spec's first, load-bearing constraint.
- [x] Given a POST to the on-ship path with a valid HMAC signature and a minimal valid payload,
  when the handler runs, then a Progress record for today exists for that station, matching
  what `herald progress <station> --update` would create for the same inputs. (Verified by
  `test_handle_on_ship_minimal_payload_uses_the_same_defaults_as_the_cli` +
  `test_handle_on_ship_matches_what_the_cli_update_would_create`, plus the ASGI-level
  `test_asgi_app_valid_signed_on_ship_post_creates_a_progress_record`.)
- [x] Given a POST to the on-pr-close path with `merged=true` and `gates_passed=true`, when
  handled, then a draft Claim exists matching what `herald success create` would create for
  the same inputs; given `merged=false` or `gates_passed=false`, then no Claim is created and
  the response is 202. (Verified by
  `test_handle_on_pr_close_shipped_creates_a_draft_claim_matching_cli_create` +
  `test_handle_on_pr_close_not_shipped_is_a_202_no_op` (parametrized over all 3 non-shipped
  combinations), plus the ASGI-level `test_asgi_app_valid_signed_on_pr_close_post_creates_a_claim`.)
- [x] Given an invalid or missing HMAC signature, when either webhook path is called, then the
  response is 401 and no storage call is attempted. (Verified by
  `test_asgi_app_missing_signature_is_401_and_makes_no_storage_call` +
  `test_asgi_app_wrong_secret_signature_is_401`, both asserting the storage table stays empty.)
- [x] Given `progress.upsert`/`claims.create` raising `errors.HeraldError` on every retry attempt,
  when the retry budget (3 attempts) is exhausted, then exactly one structured ERROR-level log
  record is emitted and the response is a non-2xx status. (Verified by
  `test_handle_on_ship_retry_exhausted_emits_one_alert_and_returns_500` +
  `test_handle_on_pr_close_retry_exhausted_emits_one_alert_and_returns_500`, each asserting
  `len(error_records) == 1`, the JSON body's `event`/`webhook`/`error` fields, and status 500.)
- [x] Given the full existing Herald test suite plus the new `test_webhook.py`, when run inside
  this worktree (`PYTHONPATH=src python -m pytest tests -q`), then every test passes. (851
  passed / 2 skipped before this story's changes -> **905 passed / 2 skipped** after --
  see Dev Notes.)

**Dev Notes (2026-08-13):**
- Built `src/pyforge/herald/webhook.py` exactly per the Code Map: `verify_signature` (HMAC-SHA256
  over the raw body, `hmac.compare_digest`), `resolve_webhook_secret` (an added, small helper --
  not named in the intent-contract's function list, but implied by "`secret` is read once ...
  from env var `HERALD_WEBHOOK_SECRET`"; mirrors `transport.mcp_transport
  .resolve_design_credential`'s injectable-`env` shape so `create_app`'s own signature stays
  literally `create_app(repo_root, secret)` and the env read happens exactly once, at whatever
  call site constructs the app -- Story 13.6's job, out of this story's Surface), `handle_on_ship`/
  `handle_on_pr_close` (sync core, structural-validation-only pre-checks -> 400; every
  business-rule rejection, e.g. `progress.upsert`'s negative-cost check or `claims.create`'s
  empty-`project_name`/bad-evidence-`type` checks, is deliberately left to those functions'
  own `HeraldError`, which the retry helper then handles as any other storage failure --
  matches the Boundaries text literally: only exceptions "raised BY `progress.upsert`/
  `claims.create`" are retry/500-eligible), `_retry_with_backoff` (3 attempts, sleeps
  `RETRY_BACKOFFS[i]` between attempts `i+1`/`i+2`, never after the last), `_log_retry_exhausted`
  (one JSON `ERROR`-level `logging.getLogger(__name__)` record), and `create_app` (a plain
  `async def app(scope, receive, send)` -- route/method checked before the body is read,
  HMAC checked before the body is parsed as JSON, per the I/O matrix's own ordering).
- Routes are the literal paths `epics.md`'s own Story 13.4 line names:
  `/api/herald/webhooks/on-ship` and `/api/herald/webhooks/on-pr-close` (`webhook.ON_SHIP_PATH`/
  `ON_PR_CLOSE_PATH`).
- **The retry-idempotency mechanism** (Design Notes' own "why idempotency matters" section):
  `handle_on_pr_close` pre-generates the claim id once, before the retry loop, and each attempt
  first calls `claims.read_one(claims_path, claim_id)` -- if a prior attempt actually committed
  before raising (the narrow window this module cannot otherwise rule out, since `claims.id`
  carries no schema-level uniqueness per `db.py`'s own documented choice), this finds it and
  returns it unchanged instead of calling `claims.create` a second time with the same id, which
  would silently insert a second row sharing that id (nothing downstream would catch it -- unlike
  `progress`'s `(station, date)` UNIQUE constraint, `claims` has none). Proven directly by
  `test_handle_on_pr_close_retry_is_idempotent_when_the_first_attempt_actually_committed`: a fake
  `claims.create` that genuinely writes via the real function and THEN raises on its first call is
  asserted to be called exactly once (`calls == 1`) and to leave exactly one stored claim --
  reverting the pre-generated-id-plus-`read_one`-check design back to a fresh
  `uuid.uuid4()`-per-attempt (or dropping the `read_one` check and always calling `create`) fails
  this test by producing 2 stored claims. `handle_on_ship` needs no equivalent: `progress.upsert`'s
  own `(station, date)` UNIQUE key already makes a same-day re-invocation an in-place replace, not
  a second record -- verified structurally (no separate test needed; `progress.py`'s existing
  `test_upsert_replaces_the_same_station_date_in_place` already pins that invariant).
- Test suite added: `tests/test_webhook.py`, 51 tests -- HMAC valid/invalid/missing/malformed-header
  (4), `resolve_webhook_secret` present/missing/empty (3), the generic retry helper directly (3),
  `handle_on_ship` happy-path/full-payload/matches-CLI/9-way malformed-payload
  parametrization/retry-then-recover/retry-exhausted (14), `handle_on_pr_close` shipped/no-evidence/
  3-way not-shipped parametrization/5-way malformed-gate parametrization/6-way malformed-shipped-field
  parametrization/retry-then-recover/retry-exhausted/retry-idempotency (18), and the ASGI3 boundary
  itself -- valid on-ship, valid on-pr-close, unknown path (404, body never read), wrong method (405,
  body never read), missing signature (401), wrong-secret signature (401), malformed JSON (400),
  non-`http` scope ignored (9).
- Docs updated per the Code Map: `docs/cli-runbooks.md` gained a new `## The webhook endpoint (CI
  calls, Story 13.4)` section (routes, auth, reliability) plus rewrites of the scope note, the
  "How to publish a claim" intro, "What is *not* a failure mode here", and the escalation path's
  webhook line; `docs/automation-troubleshooting.md`'s intro and "Auto-extract failed" section;
  `docs/operator-guide.md`'s one-sentence architecture summary and its "why doesn't a PR merge
  automatically create a record" FAQ answer. All four now say the same true thing consistently:
  the webhook is **built and fully unit-tested in isolation, but not mounted into any live ASGI
  host or wired into a real GitHub Actions workflow** -- that is Story 13.6's job -- so in practice
  every record today still comes from an operator's CLI command. `src/pyforge/herald/cli.py`'s
  module docstring (~lines 11-14) no longer says "there is no webhook anywhere in this module";
  it names `webhook.py` and explains why it still has no CLI subcommand (it is mounted directly
  into an ASGI host, never dispatched through `argparse`).
- **Unplanned but required fix, found by running the full suite (not by the Code Map):**
  `tests/test_bridge.py`'s `_BRIDGE_CORE_MODULES` sweep (Story 1.4's AD-3/AD-4 static
  determinism-boundary check, run over every non-CLI/non-transport package module) failed once
  `webhook.py` existed, exactly as its own docstring says it should ("a new package module ...
  fails here until it is either added to the sweep or, with cause, to the exclusion set").
  `webhook.py` has the identical profile every other bridge-core module already swept in has --
  calls straight through to `progress`/`claims`, never imports a concrete transport adapter or an
  inference SDK, never does argv parsing -- so it joined `_BRIDGE_CORE_MODULES` (one import, one
  tuple entry, one docstring paragraph) rather than being excluded. Verified: `webhook.py` is
  disjoint from `_FORBIDDEN_ADAPTER_MODULES`/`_FORBIDDEN_ADAPTER_NAMES`/
  `_FORBIDDEN_INFERENCE_PACKAGES`/`_FORBIDDEN_DYNAMIC_IMPORT_NAMES` (all three parametrized
  `_BRIDGE_CORE_MODULES` tests pass for it), and the coverage-sweep test itself passes again.
- **Measured from inside this worktree**, per spec-13-3's own established gotcha: `pixi run -e
  pyforge-herald pyforge-herald-test` resolves its `pytest` invocation against the MAIN checkout,
  not this worktree, so it was not used for this story's numbers either. Used instead:
  `PYTHONPATH=src <main-checkout's pyforge-herald conda env>/bin/python -m pytest tests -q` run
  from `src/shared/packages/pyforge-herald/` inside this worktree (the worktree has no
  materialized `.pixi/envs/pyforge-herald` of its own yet; `PYTHONPATH=src` makes the already-built
  `pyforge-herald` conda env's interpreter import this worktree's own `src/pyforge/herald/`
  package rather than any installed copy -- confirmed via `python -c "import
  pyforge.herald.webhook as w; print(w.__file__)"` resolving to this worktree's path before
  trusting any test result). **851 passed / 2 skipped before this story's changes (measured via
  `git stash`), 905 passed / 2 skipped after** (54 new: 51 in `test_webhook.py` + 3 new
  `_BRIDGE_CORE_MODULES`-parametrized cases for `webhook` picked up automatically by the
  `test_bridge.py` fix above).

## Spec Change Log

(none -- no bad_spec loopback was triggered during this story's review pass)

## Review Triage Log

### 2026-08-13 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7 (high 4, medium 3, low 0)
- defer: 0
- reject: 5 (high 0, medium 0, low 5)
- addressed_findings:
  - `[high]` `[patch]` Cross-delivery duplicate claims: `handle_on_pr_close`'s `claim_id`
    was a fresh random `uuid4()` per HTTP call, so a genuine CI webhook redelivery (a second,
    independent POST for the same logical PR-merge event -- explicitly invited by this
    module's own "non-2xx so CI's delivery-retry can re-fire later" design) created a second,
    duplicate draft Claim; the existing read-before-create guard only caught retries within
    one call. Fixed: `claim_id` is now derived deterministically (`uuid.uuid5`) from
    `project_name` + `shipped_date`/today, so a genuine redelivery computes the same id and
    the existing guard catches it across calls too. New test proves one claim survives two
    independent top-level calls with the same payload.
  - `[high]` `[patch]` Sync `time.sleep` inside `create_app`'s `app()` blocked the entire
    ASGI event loop for up to ~3s during any retry once mounted. Fixed: the handler now runs
    via `await asyncio.to_thread(handler, repo_root, payload)`.
  - `[high]` `[patch]` `_read_body` accumulated an unbounded body with no size cap, before
    HMAC verification -- an unauthenticated memory-exhaustion vector. Fixed: `MAX_BODY_BYTES`
    (1 MB) cap, aborting to a 413 before `verify_signature` runs. New test proves the
    signature check is never reached for an oversized body.
  - `[high]` `[patch]` `app()` had no top-level exception guard; any exception outside
    `errors.HeraldError` (a bug, an unexpected type) propagated uncaught, so no ASGI response
    was ever sent -- violates the ASGI contract and would hang whatever host mounts this.
    Fixed: a catch-all around the request-handling flow logs and returns 500. New test forces
    a non-`HeraldError` exception and asserts a clean 500 instead of an uncaught propagation.
  - `[medium]` `[patch]` `_problem_on_pr_close_shipped` never checked `evidence[].type`
    against `claims.EVIDENCE_TYPES`, nor `project_name` for blank/whitespace-only -- both
    sailed past 400 into a wasted retry-then-500 at the storage layer. Fixed: both are now
    structural 400 checks, with new parametrized test cases.
  - `[medium]` `[patch]` `create_app` never validated its own `secret` argument, so a caller
    bypassing `resolve_webhook_secret` could silently construct a forgeable app. Fixed: a
    non-empty guard raises `HeraldError` at construction. New test covers a blank secret.
  - `[medium]` `[patch]` `_problem_on_ship`'s numeric-type checks accepted `NaN`/`Infinity`
    (Python's `json.loads` parses these non-standard literals by default; `progress.upsert`'s
    own `value < 0` guard is `False` for NaN, so neither layer rejected them). Fixed: added
    `math.isfinite` checks for `compute_hours`/`wall_clock_hours`. New parametrized test cases
    for both.
  - Rejected as noise (5, all low): negative-number payloads reaching a wasted retry-then-500
    (already an explicit, documented tradeoff in this spec's own Boundaries and the module's
    docstring, not an oversight); `_log_retry_exhausted` logging the raw payload unredacted
    (no sensitive field exists in today's schema -- speculative future risk, not a current
    one); no explicit array-length bound on `shipped_capabilities`/`evidence` (subsumed by
    the new body-size cap, which bounds total payload size); `_retry_with_backoff`'s
    `attempts`/`backoffs` independent-override footgun (every real call site uses the matched
    defaults; no concrete failure exists today); missing `Content-Length` response header
    (optional per the ASGI spec, not a correctness issue).
- Post-patch verification: `PYTHONPATH=src <main-checkout's pyforge-herald conda env>/bin/python
  -m pytest tests -q` run from inside this worktree -- **914 passed / 2 skipped** (9 new tests
  from the 7 patches above, up from the 905/2 pre-review count).

### 2026-08-13 — Review pass (follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 12 (high 3, medium 4, low 5)
- defer: 3 (high 0, medium 2, low 1)
- reject: 7 (high 0, medium 0, low 7)
- addressed_findings:
  - `[high]` `[patch]` `verify_signature` RAISED instead of returning `False` for a signature
    header containing a non-ASCII byte: `hmac.compare_digest` on two `str`s raises `TypeError`
    for non-ASCII, and `_header_value` decodes the header `latin-1`, so any byte reaches it.
    Reproduced: `X-Hub-Signature-256: sha256=<0xff x 64>` answered **500** plus one ERROR log
    record -- and ERROR logging is this module's ONLY operator-alert channel, so any
    unauthenticated caller who could reach the route could drown the real `retries_exhausted`
    alerts without holding the secret. Fixed: the hex half is shape-checked (exactly 64 hex
    digits) before `compare_digest` sees it; the check inspects only the caller's own input, so
    it leaks nothing about the secret. New parametrized test over 5 malformed header shapes plus
    an ASGI-level test asserting 401 with zero ERROR records.
  - `[high]` `[patch]` The previous pass's deterministic `claim_id` (`uuid5` over
    `project_name` + `shipped_date`) deduplicated correctly but no longer discriminated: two
    DIFFERENT PRs for one project merging on one day computed ONE id, so the second real ship was
    silently swallowed by the idempotency guard, answered **201**, and its evidence discarded --
    the exact "an unrecorded ship is indistinguishable from no ship" failure this story exists to
    close. Reproduced with two PRs (evidence `.../pr/100` then `.../pr/101`): 1 claim stored,
    only the first URL. Fixed: a per-event discriminator joins the uuid5 name -- the payload's
    own `event_id` when present (a PR number / delivery id, and what 13.6's workflow step should
    send), else its canonically-encoded `evidence` list, which carries the PR URL. Redelivery of
    an identical body still computes the identical id. 4 new tests (2 distinct PRs -> 2 claims;
    distinct `event_id`s -> 2 claims; same `event_id` redelivery -> 1 claim; non-string
    `event_id` -> 400).
  - `[high]` `[patch]` `app()`'s last-resort exception guard had no "response already started"
    flag, so a `send` failure after `http.response.start` -- an ordinary mid-response client
    disconnect -- made it issue a SECOND `http.response.start`; the host rejects that, and the
    rejection then propagated out of `app`, which is precisely the uncaught escape the guard
    exists to prevent. Reproduced: 4 messages sent for one request, then `RuntimeError` escaping.
    Fixed: a `tracking_send` wrapper records whether the response started and a `fail()` helper
    refuses to start a second one (and swallows+logs a failure of the error send itself). New
    test asserts exactly 2 messages, no propagation, and exactly 1 ERROR record.
  - `[medium]` `[patch]` Two numeric-range escapes turned a 400 into an opaque 500 plus a
    spurious `unexpected_exception` alert: `math.isfinite` RAISES `OverflowError` for an `int`
    too large to convert to a float (a 400-digit JSON integer literal is legal JSON), and an
    `int` outside SQLite's signed-64-bit range raises `OverflowError` at bind time -- neither is
    a `HeraldError`, so neither reached the retry helper's translation. Both reproduced. Fixed:
    the three numeric fields share one `_problem_number` check that range-tests ints before
    calling `math.isfinite`.
  - `[medium]` `[patch]` A negative cost field was left to `progress.upsert`'s own
    `HeraldError`, which is indistinguishable from a transient storage failure: it burned all 3
    retry attempts (~3s of real blocking), emitted one ERROR alert blaming storage for a fault
    that was really the payload's, and returned the 500 this module's own contract invites CI to
    re-fire forever -- for a request that can never succeed. The previous pass had already fixed
    exactly this shape on the `on-pr-close` side (blank `project_name`, bad evidence `type`),
    leaving the two handlers under opposite rules. Fixed: `_problem_number` rejects negatives as
    a structural 400, matching the sibling handler.
  - `[medium]` `[patch]` `_claim_id_for` computed its omitted-date fallback in UTC while
    `claims.create`'s own fallback is the LOCAL `date.today()` -- so the stored record's
    `shipped_date` could not reproduce its own id, and a redelivery straddling the two clocks'
    midnight computed a DIFFERENT id and created the duplicate the deterministic id exists to
    prevent. Fixed: the handler resolves `shipped_date` once (UTC, matching `handle_on_ship`'s
    server-computed `date` per Boundaries & Constraints) and passes that one value to both. New
    test recomputes the id from the stored record.
  - `[medium]` `[patch]` `_read_body` treated an `http.disconnect` message as a completed body
    (it carries no `more_body` key), handing a TRUNCATED body to `verify_signature` -- so a
    network truncation was answered `401 invalid or missing HMAC signature`, sending an operator
    hunting a secret mismatch that never happened, and then writing a response to a connection
    already gone. Fixed: a `_ClientDisconnected` exception ends the request silently. New test
    asserts zero messages sent and zero ERROR records.
  - `[low]` `[patch]` Route matching compared `scope["path"]` to the route literals exactly, but
    `path` includes the prefix a host mounts the app under -- reproduced: mounted at `/herald`,
    every valid signed delivery 404'd. Since mounting is Story 13.6's entire job, this callable
    would have failed on first use. Fixed: `root_path` is stripped before routing. New test.
  - `[low]` `[patch]` `json.loads` kept the LAST value for a repeated key, so
    `{"gates_passed": false, "gates_passed": true}` passed the ship gate on a payload that also
    said it should not -- while `progress`/`claims`/`state` all already apply an AD-6
    duplicate-key `object_pairs_hook` to the documents they read. Fixed: the same hook here; the
    parse guard widened to `ValueError` (which covers `JSONDecodeError`, `UnicodeDecodeError`,
    and the hook's own rejection) so it stays a 400 rather than falling to the catch-all 500.
  - `[low]` `[patch]` The retries-exhausted alert could emit a bare `NaN`/`Infinity` token --
    `json.loads` accepts those non-standard literals on the way in through any field
    `_problem_on_ship` does not know about, and `json.dumps` re-emits them -- making the one
    "structured JSON record" unparseable by `jq` and most log pipelines. Fixed: `_json_safe`
    replaces non-finite floats, and the dump is `allow_nan=False`. New test parses the record.
  - `[low]` `[patch]` A blank/whitespace-only `station` was accepted, so every such delivery from
    every repo collapsed onto the single `("", date)` row. Fixed as a structural 400 -- distinct
    from re-validating against `progress.STATIONS`, which Boundaries & Constraints names as an
    explicit "Never" and which this pass did NOT add.
  - `[low]` `[patch]` Documentation accuracy: the module docstring attributed AD-8's rule text
    ("the library binds at the ASGI application boundary ... no adopter may be asked to change
    frameworks to adopt") to AD-9, which says nothing about ASGI shape -- verified against
    Steward's own ARCHITECTURE-SPINE; it also claimed the `asyncio.to_thread` hop bounded worker
    occupancy to "~3s" when each of the 3 attempts can additionally wait `db._BUSY_TIMEOUT_MS`
    (30s) for the write lock. `docs/cli-runbooks.md` likewise said "1s/2s/4s backoff", which
    budgets 7s for a 3s worst case (there is no sleep after the last attempt). All three
    corrected; the runbook also gained the 413/404/405/400 responses and the `event_id` guidance
    it had omitted.
  - Deferred (3, recorded as new ledger entries `DW-FU-13-4`, `DW-FU-13-4-2`, `DW-FU-13-4-3`):
    no replay protection in the spec-pinned HMAC scheme (closing it changes the signed-content
    contract, which needs the not-yet-written 13.6 producer to cooperate); the `read_one`/`create`
    idempotency guard spanning two transactions, so concurrent deliveries can both create a claim
    with one id (`claims.id` has no schema-level uniqueness by Story 13.3's deliberate choice);
    and the unbounded ~93s worst-case worker occupancy, whose mitigation (request timeout,
    bounded executor) belongs to the host wiring. None is reachable today -- nothing is mounted.
  - Rejected as noise (7, all low): not re-validating `station` against `progress.STATIONS`
    (Boundaries & Constraints names it an explicit "Never"); `on-ship` replacing an operator's
    same-day record with payload defaults (that is `progress.upsert`'s specified `(station, date)`
    replace semantics and exactly what `herald progress --update` does -- the spec requires
    mirroring `_run_progress_update`); unknown payload fields being ignored rather than rejected
    (a forward-compatibility tradeoff, not a defect); `_header_value` taking the first matching
    header rather than failing closed on duplicates (an HMAC cannot be forged, so both choices
    answer 401 -- fail-closed only trades one misconfiguration for another); the CLI-parity test
    asserting against `progress.upsert` rather than through `cli._run_progress_update` (the
    parity the spec asks for is the `upsert` call shape, which the test does pin); an unbounded
    empty-chunk trickle (read timeouts are the ASGI host's); and the alert record logging the
    payload unredacted (re-verified rather than inherited: no field in today's Progress/Claim
    schema carries a secret).
- Post-patch verification: `PYTHONPATH=src <main-checkout's pyforge-herald conda env>/bin/python
  -m pytest tests -q` run from inside this worktree -- **938 passed / 2 skipped** (24 new tests,
  up from the 914/2 this pass started at). Every one of the 6 originally-reproduced failures
  re-probed directly and confirmed fixed (401 not 500; 2 claims not 1, with redelivery still
  idempotent; no second `http.response.start` and no propagation; no response at all on
  disconnect; 201 when mounted under `/herald`; 400 for out-of-range/negative/blank). `ruff
  check` reports the same 2 pre-existing findings before and after this pass -- none added.

### 2026-08-13 — Review pass (follow-up 2)
- intent_gap: 0
- bad_spec: 0
- patch: 13 (high 4, medium 6, low 3)
- defer: 1 (high 0, medium 1, low 0)
- reject: 6 (high 1, medium 2, low 3)
- addressed_findings:
  - `[high]` `[patch]` `shipped_date` was type-checked but never format-checked, and nothing
    downstream checks it either: `claims.create` validates only `project_name` and evidence
    `type`, so `"13/08/2026"` / `"yesterday"` / `""` / `"2026-13-45"` were stored verbatim at
    201, and `claims.list_claims` then calls `date.fromisoformat` on them with no guard.
    Reproduced end to end: one such delivery made every subsequent `herald success list
    --date-range ...` raise a bare `ValueError` out of `cli.main` (`cli.dispatch` translates only
    `HeraldError`), permanently, for every operator. Fixed as a structural 400 --
    `_problem_on_pr_close_shipped` already front-loads exactly this class of check for blank
    `project_name` and evidence `type`. The identical hole on the CLI's own `--shipped-date` flag
    is pre-existing and deferred (see below).
  - `[high]` `[patch]` A blank `event_id` was strictly worse than sending none: `_claim_id_for`
    branches on `is not None`, so `""` -- what an unset workflow input or a
    `${{ github.event.number }}` on a non-PR trigger renders to -- became the CONSTANT
    discriminator `"event:"` AND suppressed the evidence fallback. Reproduced: two different PRs
    for one project on one day collapsed onto one claim, the second answered 201 with its
    evidence silently dropped -- re-opening the exact "an unrecorded ship is indistinguishable
    from no ship" failure the previous pass had just closed. Fixed as a structural 400.
  - `[high]` `[patch]` `_read_body` accumulated with `body += chunk` on immutable `bytes`, which
    copies the whole accumulated body per chunk -- quadratic in the chunk count. `MAX_BODY_BYTES`
    bounds the memory but not that work, and this is the one part of a request that cannot leave
    the event-loop thread, so an UNAUTHENTICATED caller (no secret needed) could stall every
    other in-flight request just by streaming a capped-size body in tiny chunks. Measured on this
    machine: 800 KB in 1-byte chunks took **16.57s before, 0.23s after**. Fixed by collecting
    chunks and joining once; the new test asserts both correct reassembly and a 4s ceiling.
  - `[high]` `[patch]` Lone-surrogate strings (legal JSON -- `json.loads` accepts `"\ud800"`)
    were accepted by every string check, which tested type only. Reproduced on both routes: via
    `progress.upsert` it arrived as a `HeraldError` indistinguishable from a transient storage
    fault, so the caller burned all 3 attempts (~3s of real blocking), emitted one ERROR alert
    blaming storage for a payload fault, and returned the 500 this module's own contract invites
    CI to re-fire forever -- for a request that can never succeed; via `_claim_id_for` the
    `UnicodeEncodeError` escaped even the retry helper (not a `HeraldError`) into the catch-all
    500 plus one `unexpected_exception` record per delivery. This is verbatim the anti-pattern
    `_problem_number`'s docstring says its range/sign checks exist to close, left open for the
    string fields. Fixed with a shared `_problem_text` storability check on every string field of
    both payloads.
  - `[medium]` `[patch]` `create_app`'s secret guard checked falsiness but not type, so
    `os.environ["HERALD_WEBHOOK_SECRET"]` passed directly -- a `str`, and the single likeliest
    form of the "resolved some other way" mistake the guard's own docstring names -- built an app
    that then died in `hmac.new` on EVERY request: a silent 100% outage answered 500, one ERROR
    record per delivery flooding this module's only alert channel. Fixed with an `isinstance`
    check that fails at construction.
  - `[medium]` `[patch]` `root_path` was stripped as a raw string prefix. Reproduced: a host
    started with `--root-path /` reports `root_path == "/"`, which matched every path and left
    `api/herald/...` with no leading slash -- 404ing every delivery under an ordinary
    configuration; a non-segment-boundary prefix (mounted at `/her`, request for `/herald`) was
    likewise mangled into a bogus route. Fixed by normalizing the trailing slash away and
    stripping only on segment boundaries.
  - `[medium]` `[patch]` `RecursionError` from deeply nested JSON is not a `ValueError`, so a
    200 KB body of `[` x 100_000 -- well under `MAX_BODY_BYTES`, past the 413 gate and past the
    HMAC check -- fell to the last-resort guard as a 500 plus one `unexpected_exception` record,
    for input that is simply malformed and which CI is then invited to re-fire forever, one alert
    record each time. `progress.py` and `claims.py` already pair the two exceptions when they
    parse, for exactly this. Fixed to a 400.
  - `[medium]` `[patch]` `station` was `.strip()`ped for the blank test but stored raw, so
    `"warden"`, `" warden"` and `"warden\n"` became three separate rows -- and
    `progress.latest_for_station` matches exactly, making two of those three ships records no
    station-scoped reader or dashboard can ever find. Fixed by storing the stripped value.
    Distinct from re-validating against `progress.STATIONS`, which stays an explicit "Never":
    an unrecognized station is still accepted, and case is deliberately left alone.
  - `[medium]` `[patch]` The previous pass's deterministic claim id folded the shipped date into
    the uuid5 name even when a precise `event_id` was present -- but `shipped_date` falls back to
    the SERVER's clock when the payload omits it, and a redelivery is by design a LATER call.
    Reproduced with a controlled clock: the same event delivered at 23:59:50Z and re-fired at
    00:00:20Z computed two ids and stored two claims, the duplicate the whole mechanism exists to
    prevent. Fixed by keying the `event_id` branch on project + event alone; the weaker evidence
    fallback keeps the date, and the runbook now says to send an `event_id` for that reason.
  - `[medium]` `[patch]` Documentation accuracy: `cli-runbooks.md`'s scope note and
    `operator-guide.md`'s "Architecture, in one sentence" both LED with "every record is created
    either by an operator ... or by CI calling the ... webhook handlers" and only then, two
    sentences later, said the webhook is not mounted anywhere. An operator skimming stops at the
    first clause and believes CI is recording ships that it is not -- the very confusion this
    story exists to end. Both rewritten to lead with what is true today.
  - `[low]` `[patch]` `_HEX_DIGITS` admitted uppercase hex through the shape gate, but
    `hexdigest()` is lowercase, so `compare_digest` was guaranteed to reject an otherwise-correct
    uppercase signature -- a Go `%X` / Java `%02X` / PowerShell `[BitConverter]::ToString`
    producer (and the producer is hand-written, in Story 13.6) would get a bare 401 and hunt a
    secret mismatch that never happened. Fixed by case-folding the caller's own input before
    comparison, which is not secret-dependent and so does not affect constant-time behavior.
  - `[low]` `[patch]` A `websocket` scope returned silently, sending nothing -- ASGI requires a
    websocket app to answer the handshake, and a host reports the omission as an application
    error (uvicorn: "ASGI callable returned without sending handshake") once per connection.
    Fixed by declining the connection with `websocket.close`, matching the module's own
    "an ASGI app must always answer" reasoning on the HTTP side.
  - `[low]` `[patch]` Runbook completeness: the webhook section gained the `on-ship`
    replace-not-merge semantics and what a producer must therefore send, the fact that `station`
    is deliberately not validated against the known-station list (and what a typo costs), the
    mount-prefix note (`path` includes `root_path`, and the routes already begin with `/api`),
    and the new 400 cases.
  - Deferred (1, recorded as new ledger entry `DW-FU-13-4-4`): the same malformed-date hole on
    the CLI side -- `herald success create --shipped-date` accepts any string and `claims.create`
    never validates it, so one bad value breaks `herald success list --date-range` for every
    operator afterwards. Reproduced end to end through the CLI with no webhook involved, which is
    what makes it pre-existing (Story 9.2/13.3 surface) rather than this story's: 13.4's own route
    to that hole is closed by the patch above, the CLI's is not.
  - Not re-filed, already tracked: the `read_one`/`create` idempotency guard spanning two
    transactions (both reviewers reproduced it independently, 40/40 concurrent trials, two rows
    sharing one claim id) is already ledger entry `DW-FU-13-4-2` from the previous pass, and the
    "no concurrency test" observation is part of it. Left with its existing owner and status
    rather than re-minted or re-opened; unreachable today, since nothing is mounted.
  - Rejected (6): `on-ship` replacing rather than merging a same-day record, with omitted fields
    reset to the CLI's flag defaults (re-verified rather than inherited -- read
    `cli._run_progress_update` directly and confirmed it passes the identical defaults to the
    identical `progress.upsert` call, so the code matches what Boundaries & Constraints
    explicitly requires; documented in the module docstring and the runbook instead of changed);
    not re-validating `station` against `progress.STATIONS` (an explicit "Never" -- likewise
    documented rather than changed); `_read_body` treating an unrecognized ASGI message type as
    body-complete (only a non-conformant host produces one, and the resulting 400 is a defensible
    answer -- every alternative trades one imperfect answer for another plus new machinery); the
    missing concurrency test as a standalone finding (it belongs to the tracked entry above);
    and `root_path="/api"` colliding with the route literals' own `/api` prefix (correct per the
    ASGI spec, which defines `path` as including `root_path` -- documented for Story 13.6 rather
    than guessed at).
- Post-patch verification: `PYTHONPATH=src <main-checkout's pyforge-herald conda env>/bin/python
  -m pytest tests -q` run from inside this worktree -- **958 passed / 2 skipped** (20 new cases,
  up from the 938/2 this pass started at). Every new case was re-run against the pre-patch module
  to prove it discriminates: 19 of 20 failed outright, and the 20th (the body-accumulation timing
  bound) failed once sized to 800 KB, which is why that size and the 4s ceiling were chosen from
  measurement rather than guessed. One pre-existing test needed amending, not weakening:
  `test_asgi_app_unexpected_exception_is_a_500_...` used `RecursionError` as its stand-in for
  "an exception this module did not anticipate", and that is now a real, handled 400 -- the
  stand-in became `RuntimeError` so the test still proves what it was written to prove. `ruff
  check` output is byte-identical before and after this pass (30 lines both ways, all
  pre-existing and house-wide) -- none added.

### 2026-08-13 — Review pass (follow-up 3)
- intent_gap: 0
- bad_spec: 0
- patch: 13 (high 2, medium 5, low 6)
- defer: 0
- reject: 4 (high 0, medium 1, low 3)
- addressed_findings:
  - `[high]` `[patch]` Unknown payload fields were silently ignored, and on `on-ship` that is
    not a harmless no-op: a same-day delivery REPLACES, so a mistyped `token_spends`/`compute_hrs`
    answered **201** while resetting the real figures recorded minutes earlier. The producer is a
    hand-written workflow YAML with no schema and no linter, so nothing else would ever catch the
    typo. **The previous two passes rejected this as "a forward-compatibility tradeoff"; that
    premise was re-tested and is false for this repo** -- `progress._fields_problem`,
    `claims._claim_from_dict` and `claims._evidence_from_dict` each reject unknown fields, and
    they are the very AD-6 convention this module's own `_reject_duplicate_keys` cites. Fixed:
    both routes (and each evidence entry) reject unknown fields as a 400, with the same message
    shape those functions use. The `on-pr-close` check sits in the gate function so it also runs
    for a not-shipped 202. New test proves the real figures survive the typo.
  - `[high]` `[patch]` `_read_body` bounded accumulated BYTES but not message COUNT, so a stream
    of ZERO-length chunks added nothing to the counter, never satisfied `more_body`, and never
    ended -- an UNAUTHENTICATED caller (this is before `verify_signature`) holding a request open
    forever while the chunk list grew a slot per message. Reproduced: 3,000,001 empty chunks
    drained in 0.6s without the 1 MB cap ever firing, request still unfinished. This is the same
    threat class `_read_body`'s own docstring says the byte cap exists to close, left open for the
    one shape the byte cap cannot see. Fixed: `MAX_BODY_MESSAGES` (10,000 -- ~150x headroom over a
    real host's 16-64 KB chunking) aborts to a 413, and empty chunks are no longer accumulated.
  - `[medium]` `[patch]` `shipped_date` was parse-checked but not format-checked, so it kept the
    promise its own error message makes ("YYYY-MM-DD") only for the shapes it rejected:
    `date.fromisoformat` accepts every ISO 8601 form on 3.11+, so `"20260813"` and `"2026-W33-4"`
    were stored verbatim at 201. `web/src/panels/SuccessPanel.jsx` filters `shipped_date` by raw
    STRING comparison, where `"20260813" > "2026-12-31"` is true, so such a claim disappears from
    every date-filtered dashboard view -- an unrecorded ship indistinguishable from no ship,
    arriving through the field the check added last pass exists to protect. Fixed: round-tripped
    against `.isoformat()`.
  - `[medium]` `[patch]` `notice`-type evidence was accepted with no existence check. A notice
    entry's `url` is a Notice COMPONENT NAME, and both `claims.publish` and
    `claims._revalidated_entry` short-circuit such an entry as trivially valid -- stamped
    `validated=True` without a single check. The CLI compensates (`herald success create
    --evidence-notice` calls `notices.get_notice` first, "rather than letting a claim silently
    cite a notice that was never authored"); this route did not, making it a way to attach
    evidence that passes Story 9.5's entire evidence gate while referring to nothing. Reproduced:
    a claim with two bogus notice entries published with `validated=True`, the validator never
    invoked. Fixed as a 400, matching the CLI.
  - `[medium]` `[patch]` `project_name` was hashed and stored UNstripped while `station` is
    stripped, so `"Marshal\n"` -- a `${{ }}` expansion picking up a trailing newline, the ordinary
    YAML artifact -- computed a different `uuid5` and created a duplicate claim, on the one
    surface with no dedupe key to recover with. The same hazard was identified and fixed for
    `station` last pass and left alone here. Fixed both in `_claim_id_for` and at storage.
  - `[medium]` `[patch]` The retries-exhausted alert embedded the whole caller-controlled payload,
    up to `MAX_BODY_BYTES`. Measured: a 200 KB field produced a 200,141-byte ERROR line; a 1 MB
    body produces ~1 MB, per exhausted delivery, and the module's own non-2xx contract invites CI
    to re-fire. That drowns the real alerts exactly the way `verify_signature`'s and `create_app`'s
    docstrings each argue their own guards exist to prevent. Distinct from the payload-secrecy
    finding rejected in two prior passes (still rejected -- no field in today's schema carries a
    secret); this one is about volume. Fixed: `_MAX_ALERT_PAYLOAD_CHARS` truncation that names
    what was dropped, with a test that a small payload is still recorded verbatim.
  - `[medium]` `[patch]` The 404, 405 and websocket-close sends sat OUTSIDE `app()`'s last-resort
    guard, so a `send` that raises there escaped the callable -- the exact uncaught escape the
    guard exists to prevent, per the module's own "Uncaught exceptions" section. Reachable today:
    uvicorn's websocket `send` raises `ClientDisconnected` up front when the peer is already gone
    (`websockets_sansio_impl.py`). Fixed: routing moved inside the guard, the websocket close given
    its own (an HTTP error response would be wrong for a websocket scope). New parametrized test
    over all three paths.
  - `[low]` `[patch]` `_claim_id_for` built its `uuid5` name by joining caller-controlled strings
    around a bare `|`, so `{"project_name": "A|event:B", "event_id": "C"}` and
    `{"project_name": "A", "event_id": "B|event:C"}` rendered the identical name -- two distinct
    events computing one id, the second silently swallowed at 201, which is the failure this
    function exists to prevent. Fixed: the parts are JSON-encoded as a list.
  - `[low]` `[patch]` The `event_id` guidance recommended "a PR number", which is unique only
    within one repository, while no payload field identifies the repository and the `event_id`
    branch deliberately omits the date -- so two repos' PR #42 collide permanently. Fixed in the
    docstring and the runbook: send something globally unique
    (`${{ github.repository }}#${{ github.event.number }}`, or the delivery GUID).
  - `[low]` `[patch]` Route matching was exact, so a trailing slash (`.../on-ship/`) or the doubled
    slash an nginx `location`/`proxy_pass` pair routinely emits 404'd a correctly-signed delivery --
    while the mount prefix next to it is normalized with real care, precisely because a routing 404
    is indistinguishable from "not deployed". Fixed: the request path gets the same normalization;
    a new test pins that a genuine near-miss (`/on-shipp`) still 404s.
  - `[low]` `[patch]` The webhook bypasses `auth.require_operator_role`, which
    `cli._run_progress_update` enforces (AD-16). The CODE is right -- AD-9's whole point is that a
    machine caller authenticates by proof, not by an operator identity it does not have -- but the
    runbook's "calls the same `progress.upsert`" parity claim hid the consequence: mounting this
    hands anything holding `HERALD_WEBHOOK_SECRET` progress-write access the CLI grants only to a
    verified operator. Disclosed in the module docstring, the runbook and the operator guide as
    the privilege boundary it is.
  - `[low]` `[patch]` The CI-events paragraph (this story's first, load-bearing AC) says `on-ship`
    fires per push to `main`, while the replace-semantics section four sections later says the
    producer must therefore send cumulative figures or fire once per day. A 13.6 author reading
    the first and not the fourth gets silent data loss. Cross-referenced at the point of the claim;
    the docs also now say the replace crosses SOURCES, not just deliveries -- one `on-ship` call
    overwrites an operator's hand-entered record for that day.
  - `[low]` `[patch]` Test coverage: the "same-day `on-ship` deliveries REPLACE, they do not merge"
    contract -- called out in three docstrings and two doc files as a footgun 13.6 must design
    around -- had no test, so a refactor to read-and-merge would have passed the whole suite. The
    nearest existing test delivered four times and asserted only the row count. Added.
  - Not re-filed, already tracked: the `read_one`/`create` idempotency guard spanning two
    transactions (both reviewers reproduced it again independently -- 20/20 through the real ASGI
    callable, 60/60 unsynchronised on threads -- and newly established the downstream consequence
    that `claims._require_unique_ids` then makes `claims.revalidate_all`, i.e. `herald scheduler
    run`'s evidence half, raise permanently with no repair tool) is ledger entry `DW-FU-13-4-2`;
    HMAC replay, including that an `on-ship` replay is destructive rather than a no-op, is
    `DW-FU-13-4`; unbounded worker occupancy is `DW-FU-13-4-3`; the CLI-side `--shipped-date` hole,
    whose root cause the dashboard string-comparison consequence above also traces to, is
    `DW-FU-13-4-4`. All left with their existing owner and status, none modified or re-opened.
    None is reachable today -- nothing is mounted.
  - Rejected (4): `_retry_with_backoff` spending its full budget on a permanently-fatal storage
    error such as a corrupt `herald.db` (re-verified rather than inherited -- a corrupt database
    IS a storage fault, so the "storage failure" alert and the 500 are both accurate; the
    anti-pattern the `_problem_*` docstrings describe is blaming storage for a PAYLOAD fault);
    `on-ship` overwriting an operator's hand-entered same-day record (Boundaries & Constraints
    requires mirroring `_run_progress_update`, whose `(station, date)` replace this is -- a
    scope-based rejection that still holds, so it was documented rather than changed); a host that
    pre-strips the `/api` mount prefix being 404'd by the unconditional `root_path` strip (that
    host violates the ASGI spec, which defines `path` as INCLUDING `root_path` -- the same verified
    premise the prior pass rejected the sibling finding on); and the chunked-body test's wall-clock
    `elapsed < 4.0` bound as a flake risk (the margin was 17x and is now ~100x, since the
    `MAX_BODY_MESSAGES` cap bounds the worst chunk count a caller can reach; a ratio check would
    add machinery for no gain).
- Post-patch verification: `PYTHONPATH=src <main-checkout's pyforge-herald conda env>/bin/python
  -m pytest tests -q` run from inside this worktree -- **984 passed / 2 skipped** (26 new cases, up
  from the 958/2 this pass started at). Interpreter confirmed to import this worktree's own
  `webhook.py` before any result was trusted. Every new case was re-run against the pre-patch
  module to prove it discriminates: **18 of 18 discriminating cases failed pre-patch and 6
  positive controls passed**; the 19th (the empty-chunk flood) was excluded from that run because
  pre-patch it never terminates, which IS the defect it pins. Two pre-existing tests were amended,
  not weakened: the `event_id`-on-`on-ship` case asserted the old silent-ignore behavior and now
  asserts the 400 it is (a max-in-range `token_spend` case was added so the accept path stays
  covered), and the body-linearity test was resized from 800,000 one-byte chunks (now a 413) to
  `MAX_BODY_MESSAGES` equal chunks -- still ~5e9 bytes of copying under the old quadratic
  behavior, so it still discriminates, and it now runs in 0.04s against its 4s bound. `ruff check`
  output is byte-identical before and after this pass (669 lines, 28 errors both ways, all
  pre-existing and house-wide) -- none added.

## Design Notes

**Why sync core + thin ASGI wrapper, not `async def` throughout:** mirrors
`transport/mcp_transport.py`'s "one `asyncio.run()` per call" precedent -- `verify_signature`/
`handle_on_ship`/`handle_on_pr_close` are plain sync functions, directly testable with the
same `tmp_path` pattern `test_progress.py`/`test_claims.py` already use; only
`app(scope, receive, send)` is `async def`, tested by hand-constructing a scope dict plus
fake async `receive`/`send` -- no new `pytest-asyncio`/`anyio`/httpx dependency.

**Why idempotency matters for `claims.create`'s retry:** `claims.id` has no schema-level
uniqueness (Story 13.3's deliberate choice -- duplicate-id detection stays application-level).
A retried `create` call reusing the SAME pre-generated id either succeeds once (the first
attempt truly failed) or hits the existing duplicate-id guard (the first attempt actually
committed, and the retry is provably redundant) -- both outcomes are safe. A fresh
`uuid.uuid4()` per attempt would silently create duplicate draft claims for one CI event.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

**Manual checks (if no CLI):**
- Hand-construct a `scope`/`receive`/`send` triple in a throwaway script, POST a signed
  on-ship payload through `create_app(...)`, then inspect `.herald/herald.db` via `sqlite3`
  for the new row -- expected: one Progress row present.

## Auto Run Result

Status: done (review pass 4 of 4; `followup_review_recommended: false`)

**Summary of implemented change.** Story 13.4 delivers `src/pyforge/herald/webhook.py`: an
HMAC-verified, framework-free ASGI3 callable exposing two CI-callable routes
(`/api/herald/webhooks/on-ship`, `/api/herald/webhooks/on-pr-close`) that write through the exact
`progress.upsert`/`claims.create` functions the CLI verbs already call. Built and fully tested in
isolation -- not mounted, not deployed, no workflow YAML written (Story 13.6's Surface). This
final pass hardened the payload-trust boundary rather than changing the capability: both routes now
reject unknown fields, the body read is bounded by chunk count as well as by size, `shipped_date`
must be canonical `YYYY-MM-DD`, `notice` evidence must name a notice that exists, `project_name` is
normalized like `station`, the claim id's `uuid5` name is unambiguously encoded, every response
send is inside the ASGI contract guard, the alert record is size-bounded, and the request path is
normalized the way the mount prefix already was.

**Files changed.**
- `src/pyforge/herald/webhook.py` -- the whole new capability; this pass added
  `_problem_unknown_fields`, `_alert_payload_summary`, `MAX_BODY_MESSAGES`, canonical-date and
  notice-existence checks, path normalization, and restructured `app()` so routing sits inside the
  exception guard.
- `tests/test_webhook.py` -- 155 tests; 26 added this pass, 2 amended (not weakened).
- `docs/cli-runbooks.md` -- webhook section: the full 400 list, the privilege boundary, globally
  unique `event_id` guidance, cross-source replace semantics, the chunk-count 413.
- `docs/operator-guide.md` -- FAQ answer gained the replace-semantics and privilege-boundary
  caveats.
- `docs/automation-troubleshooting.md`, `src/pyforge/herald/cli.py`, `tests/test_bridge.py` --
  earlier passes (stale "no webhook exists" text; the `_BRIDGE_CORE_MODULES` sweep entry).

**Review findings breakdown (this pass).** 13 patches applied (2 high, 5 medium, 6 low); 0 intent
gaps; 0 spec defects; 0 new deferrals; 4 rejected as noise. Four findings both reviewers raised
were already tracked as ledger entries `DW-FU-13-4`, `-13-4-2`, `-13-4-3`, `-13-4-4` and were left
untouched -- not modified, not re-opened, not re-minted.

**Verification performed.** `PYTHONPATH=src <main-checkout's pyforge-herald conda env>/bin/python
-m pytest tests -q` from inside this worktree: **984 passed / 2 skipped** (from 958/2 at pass
start). Interpreter confirmed to import this worktree's `webhook.py` before trusting any result.
Each new test re-run against the pre-patch module: 18/18 discriminating cases failed, 6 positive
controls passed; the empty-chunk case was excluded because pre-patch it never terminates, which is
the defect. `ruff check` byte-identical before and after (28 errors both ways, all pre-existing).

**Residual risks.** All four are the tracked ledger entries above, and none is reachable while the
callable is unmounted: HMAC replay (closing it changes the signed-content contract, which needs
13.6's not-yet-written producer to cooperate); the two-transaction idempotency guard under genuine
concurrency (reproduced again this pass, 20/20 through the real ASGI callable, and its downstream
effect on `herald scheduler run` newly established); unbounded worker occupancy, whose mitigation
belongs to the host wiring; and the CLI-side `--shipped-date` hole, whose webhook-side route is now
closed. Beyond those: the strict unknown-field rejection makes the payload contract a hard one, so
Story 13.6's workflow step must send exactly the documented fields -- which is the intent, and the
right time to pin it is before the producer exists.


