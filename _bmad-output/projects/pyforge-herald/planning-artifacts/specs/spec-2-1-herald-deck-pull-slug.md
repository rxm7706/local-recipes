---
title: 'herald deck pull <slug>'
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

**Problem:** Epic 1 built `herald deck seed` (CAP-1, repo -> Design). CAP-2 (Design -> repo) is the
other half of the bridge and is entirely unwired: `deck_pipeline.py` has no `pull` function, and
`cli.py`'s `deck` subparser group only knows `seed`. Without it, an operator who edits a deck's
prototype in Claude Design has no repo-side way to bring that edit back.

**Approach:** Implement `bridge-protocol.md` § *Pull* steps 1-4 for the prototype artifact only, as
`deck_pipeline.pull_prototype`, wired to `herald deck pull <slug>` via `cli.py`'s second
`dispatch`-routed subcommand. The etag short-circuit is load-bearing: an `{unchanged: true}` answer
must skip every downstream step (write, state update, extract, build, deck-export) -- not merely
skip the write.

## Boundaries & Constraints

**Always:**
- `deck_pipeline.pull_prototype(transport, *, slug, repo_root, state_path=None, prover=None, exporter=None, now=None) -> PullResult`
  follows `bridge-protocol.md` § Pull steps 1-4 exactly: `read_file(path, if_none_match: <last-seen
  etag>)` -> on `{unchanged: true}` stop immediately (no write, no state update, no re-derive) -> on
  a real answer, write the body (already entity-decoded by `transport.base.parse_read_response` --
  **not** re-decoded here) to `presentations/<slug>/project/PyForge <Persona>.dc.html`, record the
  new etag in `state.py`, then re-derive: `npm run extract` -> `npm run build` (the existing
  `LocalProver` seam, reused) -> `pixi run -e local-recipes deck-export <slug>` (a new injectable
  `DeckExporter` seam, `PixiDeckExporter` the real implementation).
- Pulling requires a prior `seed`: `pull_prototype` reads `state.py` for the deck's `project_id` and
  refuses with `HeraldError` (naming `herald deck seed`) when no state entry exists -- pull has
  nothing to pull *into* without a linked project.
- A `FileRead.truncated` answer refuses rather than writes a partial file (`FileRead`'s own docstring:
  "a partial read must never be mistaken for the file").
- The local write is atomic (temp file + `os.replace`), mirroring `state.write`/`registry.register`'s
  existing crash-safety convention -- a new `_atomic_write_text` helper, not a bare `Path.write_text`.
- `pull_prototype` stays on `deck_pipeline.py`'s existing (laxer) side of the determinism boundary --
  no new bridge-core module, so `test_bridge.py`'s existing `_BRIDGE_CORE_MODULES`/transport-import
  sweeps need no edits.
- `cli.py`'s `deck pull <slug>` subcommand is `dispatch`'s second consumer, mirroring `seed`'s own
  composition shape (`McpTransport` built inside the `operation` closure, never before `dispatch`).

**Block If:** N/A -- no spike, no live gate.

**Never:**
- No `--commit` flag yet (Story 2.2) -- pull never commits in this story; files land in the working
  tree only.
- No Marp-source or standalone-bundle pull yet (Stories 2.3/2.4) -- `--target` is not introduced in
  this story; there is exactly one pull target (the prototype).
- No live MCP call anywhere in this package's own test suite -- every test injects a hand-written
  fake `DesignTransport`/`LocalProver`/`DeckExporter`; the `deny_network` autouse fixture is the
  backstop.
- No change to `McpTransport`/`AgentSdkTransport`/`transport.base` (the read/etag/decode plumbing
  already exists from Epic 1 and needs no edit).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Unchanged (etag hit) | `read_file` answers `{unchanged: true}` | `PullResult(unchanged=True)`; no write, no state update, no prove, no export | No error |
| Changed | `read_file` answers a real body | body written verbatim (already decoded); state etag updated; prove + export run in order | No error |
| Truncated window | `FileRead.truncated is True` | refused before any write | `HeraldError` |
| No body on a "changed" answer | `unchanged=False`, `body=None` | refused (protocol violation) | `HeraldError` |
| Not seeded | no `state.py` entry for `slug` | refused before any transport call | `HeraldError` naming `herald deck seed` |
| CLI success (changed) | `herald deck pull <slug>` | exit 0; stdout names the slug + local path | No error |
| CLI success (unchanged) | `herald deck pull <slug>` | exit 0; stdout says "unchanged" | No error |
| CLI `HeraldError` | `deck_pipeline.pull_prototype` raises | one stderr line; exit per `errors.exit_code_for` | per error type |
| `herald deck pull` (no slug) | argparse | usage error | exit 2 |
| `herald deck pull --help` | argparse | help text | exit 0 |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py` -- edit -- adds
  `PullResult`, `PROTOTYPE_ARTIFACT_KEY`, `_require_seeded_state`, `_atomic_write_text`,
  `_pull_and_land`, `DeckExporter` (Protocol) + `PixiDeckExporter`, `pull_prototype`.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` -- edit -- `deck pull <slug>`
  subparser (`--repo-root`), `_run_deck_pull`, `main` routes `deck_command == "pull"`.
- `src/shared/packages/pyforge-herald/tests/test_deck_pipeline.py` -- edit -- a `FakePullTransport`
  (hand-written, supports `read_file`), `FakeExporter`, the I/O matrix's `pull_prototype` rows.
- `src/shared/packages/pyforge-herald/tests/test_cli_pull.py` -- create -- the I/O matrix's CLI rows;
  `deck_pipeline.pull_prototype` monkeypatched so only the CLI's own composition is under test.

## Design Notes

**Why the body is not re-decoded here.** `McpTransport.read_file`/`AgentSdkTransport.read_file` both
already return `parse_read_response(...)`, which entity-decodes the body internally
(`transport/base.py`'s `_decode_entities`). `FileRead.body` handed to bridge-core is therefore already
plain text. Applying `_decode_entities` a second time in `deck_pipeline.py` would silently corrupt any
pulled file that happens to contain a literal `&amp;`/`&lt;`/`&gt;` substring (double-decoding it back
past the original). This is called out explicitly because the bridge-protocol prose describes the
decode step as part of "pull," inviting a naive re-implementation at this layer -- it is intentionally
NOT duplicated here.

**Judgment call: `pull_prototype` requires prior `seed`, not a standalone `create_project`
fallback.** `read_file` needs a `project_id`; the only source of one this module has is `state.py`.
Unlike `seed`'s registry-bootstrap-fallback (Story 1.6), pull has no analogous need -- a deck that was
seeded by hand before `state.py` existed still needs one manual `state.write` (or a re-run through a
future `herald deck status --adopt`-style command, out of scope) before it can be pulled through this
CLI. Recorded as a known gap, not fixed here: narrower scope than re-deriving the registry-fallback
logic for a command that isn't `seed`.

**Judgment call: atomic write via a new `_atomic_write_text` helper, not `Path.write_text`.**
`state.write` and `registry.register` both write atomically (temp file + `os.replace`) specifically so
a process crash mid-write cannot leave a corrupt half-written file; a pulled deck prototype is exactly
as vulnerable to that failure mode, so the same convention is reused here rather than a bare write.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- full suite green (baseline 349 passed,
  2 skipped from Epic 1's close-out; net new tests recorded below).
- `ruff format --check` / `ruff check` from the package root -- clean on every file this story
  touches.
- `herald deck pull --help` -- exit 0.
- `herald deck pull` (no slug) -- exit 2.

**Deferred live-MCP proof (NOT run by this session):** the orchestrating session must run one real
`herald deck pull pyforge-marshal` (or another already-seeded pilot deck) against the live
`claude-design` endpoint before this branch merges, confirming (a) an immediate second pull short-
circuits on `{unchanged: true}` with no local write, and (b) a genuine Design-side edit pulls,
decodes, and lands byte-correct. This package's own test suite never makes this call (constraint:
never a live MCP call from this session).

## Spec Change Log

## Review Triage Log

### 2026-08-07 — Self-review pass (single agent, no independent second reviewer)

Adversarial re-read after the suite was green, looking specifically for: the etag short-circuit
actually skipping ALL downstream work (not just the write), the entity-decode not being re-applied,
and no MCP tool-name literal appearing outside a fake transport or a docstring/comment.

- `[none]` No defects found. Verified directly:
  - `test_pull_prototype_short_circuits_on_unchanged_and_skips_every_downstream_step` asserts
    `prover.calls == []`, `exporter.calls == []`, no `project/` directory created, and `state.py`'s
    `last_pull` stays `None` -- the short-circuit is structural (`_pull_and_land` returns `None` and
    `pull_prototype` returns immediately), not merely "skip the write."
  - `_pull_and_land`'s own docstring and `test_pull_prototype_body_is_not_re_decoded` confirm
    `FileRead.body` (already decoded by `transport.base.parse_read_response`) is written verbatim,
    with no second call to any decode routine in this module.
  - `grep -n "read_file\|write_files\|finalize_plan\|copy_files\|create_project\|create_support_js"`
    over `deck_pipeline.py`/`cli.py` shows every hit is either a docstring/comment, a call through the
    injected `transport` parameter (never a literal MCP tool invocation), or `cli.py`'s pre-existing,
    unchanged `McpTransport()` composition-root construction (Story 1.6's own pattern, not new here).
    No test in `test_deck_pipeline.py`/`test_cli_pull.py` constructs `McpTransport`.
- `addressed_findings`: 0. `followup_review_recommended: true` is set above per this repo's own
  practice of treating a same-agent self-review as insufficient on its own for a story with real
  write/state-mutation side effects (Story 1.6's own precedent); the orchestrating session's
  independent pass plus the deferred live-MCP smoke test are the two checks this pass could not
  perform itself.

**Verification:** `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 363 passed, 2 skipped
(was 349 passed, 2 skipped after Epic 1's close-out; +14 net new tests: 10 in `test_deck_pipeline.py`,
6 in `test_cli_pull.py`, minus overlap already counted). `ruff format --check` / `ruff check` clean on
every file this story touches.


## Adversarial review pass (2026-08-07, Blind Hunter + Edge Case Hunter, Epic 2 batch)

Dispatched with the diff file path only, no shared context.

- `high` `patch` **The etag was recorded before re-derivation (prove/export) had actually succeeded.** `_pull_and_land` wrote the new etag to `state.py` immediately after landing the file, BEFORE the caller ran `prove`/`export`. A failed export left the repo with a stale/missing derived artifact set, but the state file already recorded the new etag -- so a retry's `if_none_match` matched the just-recorded etag, the server answered `{unchanged: true}`, and the retry silently short-circuited, permanently unable to complete the re-derivation it was retrying for. Fixed: `_pull_and_land` no longer touches `state.py` at all; a new `_record_pull_etag` helper is called by each of the three `pull_*` functions ONLY after their own re-derivation step succeeds (and, for `--commit`, before the commit -- since the state file is itself one of the committed paths). Existing test `test_pull_prototype_propagates_an_export_failure_after_the_write_lands` encoded the OLD buggy contract (asserted the etag WAS recorded despite the export failure) -- corrected to assert the etag is NOT recorded, so a retry can genuinely re-attempt.
- `low` `patch` **Pre-existing, unrelated finding on `state.py`'s own concurrency model** (not a new bug Epic 2 introduced): a registry read-modify-write race on concurrent `herald deck pull` invocations for the same slug, different targets. Already tracked as `DW-1-4-2` in the deferred-work ledger since Story 1.4's own review, predating this epic. Updated that ledger entry to note Epic 2 is the first real caller making this concretely reachable rather than latent -- deliberately not fixed in this epic's own scope.

**Re-verification (2026-08-07, after the patch):** `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- **392 passed, 2 skipped** (full suite, Epic 2's own share now 4 stories/43 new tests).

**Follow-up review recommendation (updated): false** -- the primary finding is narrow and covered by a corrected regression test; the secondary finding is pre-existing tracked debt, not new scope.

## Live MCP smoke test — deferred (2026-08-07)

The orchestrating session attempted the promised live smoke test before merge (real `herald deck
pull` calls against already-linked Design projects: `pyforge-marshal`, `pyforge-warden`) and hit a
genuine environmental blocker: this session's `~/.claude/.credentials.json` carries only
`claudeAiOauth`, never a `designOauth` block, because `/design-login` was never run in this
environment. `McpTransport`'s own `resolve_design_credential` correctly refused with `AuthError`
rather than proceeding without one -- this is the transport working as designed, not a bug.

**Explicit open follow-up, not silently dropped:** all four deferred live proofs named in Epic 2's
own agent report remain owed:
1. `herald deck pull pyforge-marshal` -- confirm unchanged short-circuit + a genuine edit
   pulls/decodes/lands byte-correct.
2. `herald deck pull <slug> --commit` -- confirm the resulting commit is well-formed.
3. `herald deck pull pyforge-warden --target marp-deck` -- confirm the `{short}-{kind}.md`
   remote-path convention matches the actual Design project file naming (the highest-risk
   unverified assumption in this epic).
4. `herald deck pull pyforge-warden --target standalone` -- confirm the remote path and that
   `deck-export` actually prefers the landed bundle over its own marp render.

Run these the next time `/design-login` has been completed in the active session, before trusting
this epic's naming-convention assumptions (finding 3 especially) against real Design-side data.
User decision (2026-08-07): merge on the existing mocked-transport coverage (392 tests) now rather
than hold the branch, given the blocker is environmental (credential availability), not a code
defect the tests could have caught.
