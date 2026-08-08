---
title: 'Poll loop with quiescence debounce'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: true
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** Epics 1-2 built `herald deck seed` (CAP-1) and `herald deck pull` (CAP-2, manual). CAP-4
("Design -> repo, automatic") is entirely unwired: nothing in this package polls a Design-side deck
for edits on its own, so keeping a repo in sync with an in-progress Design edit is a manual
`herald deck pull` an operator must remember to run, and running it mid-edit races a half-saved
prototype.

**Approach:** Implement `bridge-protocol.md`'s watch-loop poll/debounce contract as a new bridge-core
module, `watch.py`, wired to `herald deck watch <slug> [<slug> ...]` via `cli.py`'s third
`dispatch`-routed deck subcommand. Each watched deck is polled independently on its own schedule for
its prototype's etag (`transport.read_file` with `if_none_match`); a detected change is never pulled
on the same poll that discovered it -- only once the same candidate etag is seen again on the
following poll (i.e. it has held across one full interval) does the real pull
(`deck_pipeline.pull_prototype`) fire. This story is the loop + the debounce only: idle backoff
(Story 4.2) and an explicit halt-on-auth-error test/spec (Story 4.3) are separate stories, though the
halt behavior itself is already present in this story's code as an absence -- `watch` never wraps a
poll or a pull in `try`/`except`, so any `HeraldError` (including `AuthError`) already propagates
un-retried the moment this story lands; 4.3 adds the explicit proof and documentation, not new logic.

## Boundaries & Constraints

**Always:**
- `watch.watch(transport, *, slugs, repo_root, interval=DEFAULT_POLL_INTERVAL, state_path=None, max_polls_per_deck=None, pull=None, now=None, sleep=None, on_event=None) -> None`
  is the new CAP-4 entry point. Every watched slug must already carry a `state.py` entry
  (`_require_seeded_state`, reused from `deck_pipeline.py` -- the same precondition `pull_prototype`
  itself enforces) -- checked for every slug before the loop's first poll, so a typo'd slug fails
  immediately rather than mid-loop.
- Each poll is exactly one `transport.read_file(project_id=..., path=..., if_none_match=<reference
  etag>)` call and nothing else -- no other `DesignTransport` method is ever called from `watch.py`
  itself (the injected `pull` callable, defaulting to `deck_pipeline.pull_prototype`, is what actually
  lands a change; `watch.py` never duplicates that logic).
- Debounce state machine per deck: a `confirmed_etag` (seeded from `state.py`, updated only after a
  real pull lands) and an optional `pending_etag` (a candidate seen on the previous poll). No
  candidate: poll against `confirmed_etag`; unchanged -> idle, do nothing; changed -> record the new
  etag as `pending_etag`, do not pull. A candidate exists: poll against `pending_etag`; unchanged ->
  the candidate has now held across one full interval -> pull for real, clear the candidate; changed
  again -> replace the candidate, still do not pull. This is FR-15's literal "settled" test.
- `interval` is clamped up to `MIN_POLL_INTERVAL` (30s, NFR-09) before it is ever used -- a caller
  requesting less never gets less.
- Time and sleep are both injected (`now: Callable[[], datetime]`, `sleep: Callable[[float], None]`),
  mirroring `deck_pipeline.py`'s own `now` convention -- no test in this suite ever sleeps for real or
  depends on wall-clock time.
- `watch.py` joins `_BRIDGE_CORE_MODULES` in `test_bridge.py` (it is bridge-core, not the CLI layer or
  a transport adapter) and reaches `transport.base` only under `TYPE_CHECKING`, exactly like
  `bridge.py` itself (a `DesignTransport` type annotation only, never a runtime value) -- proven by a
  new `test_importing_watch_does_not_load_the_transport_package` subprocess probe, mirroring
  `bridge.py`'s own.
- `cli.py`'s `deck watch <slug> [<slug> ...] [--interval N] [--repo-root PATH]` subcommand is
  `dispatch`'s third deck-level consumer, mirroring `seed`/`pull`'s own composition shape
  (`McpTransport` built inside the `operation` closure, never before `dispatch`).

**Block If:** N/A -- no spike, no live gate.

**Never:**
- No idle backoff yet (Story 4.2) -- every poll in this story uses the same clamped `interval`
  throughout a run; nothing doubles it.
- No live MCP call anywhere in this package's own test suite -- every test injects a hand-written fake
  `DesignTransport` and a hand-written `pull` spy (never the real `pull_prototype`, which would need a
  real `npm`/`pixi` subprocess); the `deny_network` autouse fixture is the backstop.
- No change to `McpTransport`/`AgentSdkTransport`/`transport.base` (the read/etag plumbing already
  exists from Epic 1-2 and needs no edit).
- `watch.py` never catches `HeraldError` itself -- that stays `cli.dispatch`'s sole job (AD-6); adding
  a `try`/`except` here would be a second, parallel error-reporting path.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Steady-state idle | every poll answers `{unchanged: true}` against `confirmed_etag` | zero pulls, zero writes, over N simulated polls | No error |
| Change detected | poll against `confirmed_etag` returns a new etag | `pending_etag` recorded; no pull this cycle | No error |
| Change settles | next poll against `pending_etag` answers unchanged | real pull fires; `confirmed_etag` updated from the pull result | No error |
| Change still moving | next poll against `pending_etag` returns yet another etag | `pending_etag` replaced; still no pull | No error |
| `interval` below 30s | `interval=5` | clamped to `MIN_POLL_INTERVAL` (30.0) | No error |
| `interval` at/above 30s | `interval=90` | used as given | No error |
| No slugs | `slugs=[]` | refused before any transport call | `ValueError` |
| An unseeded slug | no `state.py` entry | refused before any poll for that slug | `HeraldError` naming `herald deck seed` |
| CLI wiring: single slug | `herald deck watch <slug>` | `watch.watch` called with `slugs=[<slug>]`, resolved `repo_root`, default interval | No error |
| CLI wiring: multiple slugs | `herald deck watch a b` | `slugs=["a", "b"]` | No error |
| CLI wiring: `--interval` | `--interval 90` | forwarded as `90.0` | No error |
| CLI `HeraldError` | `watch.watch` raises | one stderr line; exit per `errors.exit_code_for` | per error type |
| `herald deck watch` (no slug) | argparse | usage error | exit 2 |
| `herald deck watch --help` | argparse | help text | exit 0 |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/watch.py` -- create -- `DEFAULT_POLL_INTERVAL`,
  `MIN_POLL_INTERVAL`, `WatchEvent`, `_DeckWatch`, `_clamp_interval`, `_make_deck`, `_poll_deck`,
  `watch`.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` -- edit -- `deck watch <slug>...`
  subparser (`--repo-root`, `--interval`), `_run_deck_watch`, `main` routes
  `deck_command == "watch"`; module docstring's "status/watch land in Epics 3-4" note narrowed to
  "status still lands in Epic 3" (the parallel Epic-3 agent owns that half).
- `src/shared/packages/pyforge-herald/tests/test_bridge.py` -- edit -- `watch` joins
  `_BRIDGE_CORE_MODULES` and the `transport.base`-only sweep; a new
  `test_importing_watch_does_not_load_the_transport_package` probe.
- `src/shared/packages/pyforge-herald/tests/test_watch.py` -- create -- `FakeWatchTransport`,
  `FakePull`, the I/O matrix's `watch()` rows.
- `src/shared/packages/pyforge-herald/tests/test_cli_watch.py` -- create -- the I/O matrix's CLI rows;
  `watch.watch` monkeypatched so only the CLI's own composition is under test.

## Design Notes

**Judgment call: the debounce is per-deck, not per-loop-cycle.** Each watched deck runs on its own
independent schedule (a `{slug: seconds-until-next-poll}` map, always servicing whichever deck is next
due) rather than all watched decks being polled in lockstep on one shared tick. This matters once
Story 4.2's per-deck backoff lands (a quiet deck's interval grows independently of an active one's) --
building the per-deck schedule now, even though every deck shares the same `interval` in this story,
avoids a second restructuring pass in 4.2.

**Judgment call: "etag-only poll" is the steady-state guarantee, not an absolute one.** FR-14/NFR-08
say a poll transfers no body unless a pull is triggered. The literal steady-state path (nothing
changing) holds this exactly: the `if_none_match` hit short-circuits to `{unchanged: true}` with no
body on the wire. The one poll that *detects* a still-moving edit (the `pending_etag` branch's
"changed again" case) unavoidably receives a body, because the `read_file` port has no lighter-weight
"etag only, always" primitive than its own conditional-read short-circuit -- there is no way to ask
for just the current etag when the reference doesn't match. This is the cost of the debounce itself,
not the steady-state cost the ACs target; documented explicitly in `watch.py`'s own module docstring
so a future reader does not mistake it for a bug.

**Judgment call: `watch` requires every slug to already be seeded, no bootstrap-adopt fallback.**
Mirrors `pull_prototype`'s own precedent (Story 2.1's spec, same judgment call, same rationale) rather
than reintroducing `seed`'s registry-fallback logic for a command that isn't `seed`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- full suite green. Baseline before this
  story: 470 passed, 2 skipped (Epic 1-2 close-out). After this story: 490 passed, 2 skipped (+20: 5 in
  `test_bridge.py`'s sweep/probe additions, 7 in `test_watch.py`, 8 in `test_cli_watch.py`).
- `herald deck watch --help` -- exit 0.
- `herald deck watch` (no slug) -- exit 2.

**Deferred live-MCP proof (NOT run by this session):** per this package's own established pattern
(Story 2.1's spec), the orchestrating session must run one real, time-bounded `herald deck watch
pyforge-marshal --interval 30` against the live `claude-design` endpoint before this branch merges,
confirming a real Design-side edit is detected on one poll and pulled on the next (not immediately),
and that a fully quiet deck makes only etag-only `read_file` calls with no body transferred. This
package's own test suite never makes this call (constraint: never a live MCP call from this session).

## Spec Change Log

## Review Triage Log

### 2026-08-07 — Self-review pass (single agent, no independent second reviewer)

Adversarial re-read after the suite was green, looking specifically for: a pull firing on the SAME
poll that first detected a change (the debounce's whole point), the etag-only claim's actual scope,
and the determinism-boundary sweep genuinely covering the new module.

- `[none]` No defects found. Verified directly:
  - `test_a_changed_etag_is_not_pulled_until_it_holds_one_full_interval` asserts the sequence of
    `if_none_match` values sent (`["E0", "E1"]`) and that `pull.calls` has length 1, recorded only
    after the SECOND poll -- the first poll that saw `E1` triggered no pull.
  - `test_each_poll_is_etag_only_and_unchanged_polls_never_pull` and
    `test_consecutive_unchanged_polls_perform_zero_writes` cover the steady-state etag-only claim over
    N polls with a before/after `state.read` equality check.
  - `test_importing_watch_does_not_load_the_transport_package` (subprocess probe, mirrors `bridge.py`'s
    own) confirms the `TYPE_CHECKING`-only import genuinely holds at runtime, not only in the AST
    sweep.
- `addressed_findings`: 0. `followup_review_recommended: true` is set above per this repo's own
  practice of treating a same-agent self-review as insufficient on its own for a story introducing a
  new bridge-core module with real state-reading side effects; the orchestrating session's independent
  pass plus the deferred live-MCP smoke test are the two checks this pass could not perform itself.

**Verification:** `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 490 passed, 2 skipped.
