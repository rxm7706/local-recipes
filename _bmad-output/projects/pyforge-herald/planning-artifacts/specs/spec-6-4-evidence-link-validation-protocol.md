---
title: 'Implement Evidence Link Validation Protocol (Shared Infrastructure)'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** AD-15 requires a shared evidence-link validation library (404 detection at publish
time, weekly stale-link re-checks) so every later Moment that stores evidence links (Epic 9's
claim publish, Epic 10's notice authoring) validates through one library instead of a
per-Moment copy. Nothing in this package can make an HTTP call yet.

**Approach:** A new `evidence.py` module -- `validate_link` (one HTTP `HEAD`, redirects followed
up to 3 hops, `is_valid` on a 200-299 final status), `validate_for_publish` (wraps it, raises
`errors.EvidenceLinkError` naming the broken URL), and `schedule_async_validation` (a plain
synchronous callable re-validating a batch of prior results, flagging any that were already
overdue as `is_stale`). **HTTP client:** `httpx2`, not a new `requests` dependency -- `mcp`
(already a run-dependency since Story 1.2) transitively ships it, and `transport/base.py`'s own
docstring already assumes an "httpx-style" response shape for a comparable check, so this module
uses the client already in the dependency graph rather than adding a second one.

## Boundaries & Constraints

**Always:**
- `validate_link(url) -> LinkValidation{is_valid, status, redirects, last_validated_at, is_stale}`.
- A 200-299 final status (after following redirects) is valid; 404/403 (or any other status
  outside that range) is invalid; a connection failure, timeout, or too-many-redirects is invalid
  with `status=None` (never raises for these -- they are ordinary "link is broken" outcomes, not
  library-internal failures).
- Redirects followed up to **exactly 3 hops** (`httpx2.Client(max_redirects=3)`; checked as
  `len(history) > max_redirects` inside `httpx2` itself, so 3 hops resolve, a 4th raises
  `TooManyRedirects`, caught here and reported as invalid).
- A chain longer than 2 hops (i.e. 3+) logs a warning ("... may be fragile") -- still valid if
  the final hop is 200-299; the AC's "warns if chain > 2" is distinct from "invalid."
- `validate_for_publish(url)` raises `EvidenceLinkError("Evidence link broken: {url}. Fix or
  remove before publishing.")` when the link is not valid.
- `schedule_async_validation(previous: Sequence[LinkValidation]) -> list[LinkValidation]`:
  re-validates every entry, marking `is_stale=True` on any whose prior `last_validated_at` was
  already more than 7 days old (`STALE_AFTER`, overridable) *before* this call -- the "overdue,
  worth a look" signal for operator review. The actual notification mechanism is explicitly out
  of scope (the AC says so).
- Both functions accept an injectable `client` (duck-typed `_HttpClient` Protocol: one
  `.head(url)` method) so every test runs offline, honoring `conftest.py`'s `deny_network`
  autouse fixture.

**Block If:** N/A -- no spike, no live gate; the package's `deny_network` fixture would fail any
test that forgot to inject a fake client anyway.

**Never:**
- No new HTTP client dependency (`requests`, a second `httpx`-family package) -- `httpx2` is
  already in the graph via `mcp`; declared explicitly in `pyproject.toml`/both `pixi.toml`s per
  this story's own patch (see Review Triage Log) so it is not an undeclared ride on `mcp`'s own
  transitive pin.
- No persistent result cache, no rate-limit-aware batching, no real scheduler dependency (Celery
  or similar) -- all explicitly deferred (see Design Notes); a handful of claim/notice links
  checked at most weekly has no demonstrated scale need for any of the three.
- Not wired into any CLI command yet -- `validate_for_publish` is a library call a future story
  (Epic 9) wires into the actual `herald success publish` flow; Story 6.3's own stub deliberately
  does not call it.

## I/O & Edge-Case Matrix

| Scenario | Input | Expected | Notes |
|---|---|---|---|
| 200 | live URL | `is_valid=True, status=200` | |
| 299 | edge of range | `is_valid=True` | inclusive upper bound |
| 404 / 403 | dead/forbidden URL | `is_valid=False` | |
| Connection failure | `httpx2.ConnectError` | `is_valid=False, status=None` | never raises |
| 0-3 redirects, final 200 | redirect chain | `is_valid=True, redirects=N` | not an off-by-one |
| 4th redirect (`TooManyRedirects`) | loopy chain | `is_valid=False` | client's own cap enforced |
| Chain > 2 hops | 3-hop chain, final 200 | valid + a `WARNING` log line | |
| `validate_for_publish`, broken | 404 URL | `EvidenceLinkError` naming the URL | |
| `schedule_async_validation`, overdue entry | `last_validated_at` 10 days old | `is_stale=True` | pre-run staleness, batch `now` |
| `schedule_async_validation`, recent entry | `last_validated_at` 1 day old | `is_stale=False` | |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/evidence.py` -- create -- `LinkValidation`,
  `validate_link`, `validate_for_publish`, `schedule_async_validation`, `_HttpClient` protocol,
  `MAX_REDIRECTS`, `WARN_REDIRECT_CHAIN_LENGTH`, `STALE_AFTER`.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/errors.py` -- edit -- `EvidenceLinkError`
  (falls through to exit 1).
- `src/shared/packages/pyforge-herald/pyproject.toml` -- edit -- `httpx2>=2.5.0` added to
  `dependencies` (explicit, alongside the pre-existing `mcp>=1.28.1`).
- `src/shared/packages/pyforge-herald/pixi.toml` -- edit -- `httpx2 = ">=2.5.0"` added to
  `[package.run-dependencies]`.
- `../../../../pixi.toml` (repo root) -- edit -- `httpx2 = ">=2.5.0"` added to
  `[feature.pyforge-herald.dependencies]` (test-env visibility).
- `src/shared/packages/pyforge-herald/tests/test_evidence.py` -- create -- the I/O matrix's rows,
  `FakeHttpClient`/`FakeResponse` (hand-written, no `unittest.mock`).

## Design Notes

**Judgment call: `httpx2`, declared explicitly, not consumed silently via `mcp`'s transitive
pin.** `evidence.py` imports it directly, so per this repo's own convention of declaring what a
module actually uses (rather than riding an undeclared transitive dependency that a future `mcp`
bump could drop or rename out from under this module), the pin is added to all three manifest
locations (`pyproject.toml`, the package's own `pixi.toml`, and the root workspace `pixi.toml`'s
test-env feature block) at the same version floor `mcp` itself already requires (`>=2.5.0`).

**Deliberately not implemented -- a persistent result cache.** AD-15's implementation notes
mention "cache validation results." No caller of this library exists yet (Epic 9/10 are still
ahead), so there is no concrete access pattern to design a cache key/TTL around; `schedule_async_
validation`'s own `previous: Sequence[LinkValidation]` parameter already gives a caller the
means to persist and pass back results between runs, which is the actual mechanism a future
caller needs -- adding a second, in-module cache on top would be speculative weight against this
repo's own "Simplicity First" principle.

**Deliberately not implemented -- rate-limit-aware batching.** Same rationale: a weekly check
over a handful of evidence links (the claims/notices Epic 9/10 will eventually store) has no
demonstrated need for concurrency control or backoff; `schedule_async_validation` already
processes its batch sequentially over one shared `client`, which is the simplest correct
behavior until a real caller's URL count says otherwise.

**Deliberately not implemented -- a real scheduler (Celery, cron-in-process).** Per the
implementation notes' own "don't add a heavyweight dependency for this" guidance and this repo's
lean-dependency doctrine: `schedule_async_validation` is a plain synchronous callable, the
schedulable unit itself. Whatever this repo already uses to trigger periodic work (a pixi task, a
cron entry) can call it directly; wiring an actual trigger is out of this story's scope entirely
(no AC asks for one).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 424 passed, 2 skipped
  (whole-package total after all five Epic 6 stories).
- `ruff format --check` / `ruff check` -- clean.

**Manual checks:**
- `grep -n "httpx2" pyproject.toml pixi.toml` (package) and the root `pixi.toml`'s
  `[feature.pyforge-herald.dependencies]` block -- all three declare the pin.
- `python -c "import httpx2; print(httpx2.__version__)"` inside the `pyforge-herald` pixi env --
  resolves without a `requests` install anywhere in that env.

## Spec Change Log

## Review Triage Log

### 2026-08-07 -- Self-review pass (single agent, no independent second reviewer)

Adversarial re-read targeting specifically: is the 3-hop redirect cap actually 3 and not an
off-by-one, and does `schedule_async_validation`'s staleness math use the right clock.

- `[medium]` `[patch]` **`schedule_async_validation` originally stamped each result's
  `last_validated_at` with the real wall-clock time inside `validate_link` itself**, not the
  injected `now`. A test asserting the batch's own `now` appeared on every result failed:
  `validate_link` always calls `datetime.now(UTC)` (correct for its own standalone contract), but
  a caller that had gone to the trouble of injecting a deterministic `now` for the *batch* would
  have gotten a mix of that `now` and real wall-clock time, defeating the determinism the
  parameter exists for. Fixed: `schedule_async_validation` now re-stamps every result with the
  batch's own `current_time` after calling `validate_link`, so one run shares one timestamp and
  an injected `now` is honored end to end. Caught by
  `test_schedule_async_validation_marks_an_overdue_entry_stale`'s own assertion, not a
  pre-existing gap in coverage -- the test was written with the correct expectation and the
  implementation was wrong under it.
- `[low]` `[verified, no patch]` Explicitly exercised the 3-vs-4-hop boundary via
  `test_validate_link_up_to_three_redirects_still_valid_on_a_final_200` (parametrized 0-3, all
  valid) and `test_validate_link_too_many_redirects_raised_by_the_client_is_invalid` (a 4th hop,
  via `httpx2.TooManyRedirects` raised by the fake client) -- confirms `max_redirects=3` is
  genuinely "up to 3 hops," not "up to 2" or "up to 4."
- `addressed_findings`: 1 (medium). No `intent_gap`, no `bad_spec`, no `defer`, no `reject`.

**Re-verification (2026-08-07, after the patch):** `pixi run --frozen -e pyforge-herald
pyforge-herald-test` -- 424 passed, 2 skipped; `ruff format --check`/`ruff check` clean.
