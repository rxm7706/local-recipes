---
title: 'Authored-source pull — Marp sources'
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

**Problem:** `bridge-protocol.md` § *Authored-source pull* names a second CAP-2 target: Design-side
Marp source files (e.g. `warden-deck.md`, `warden-executive-summary.md`, `warden-infographic.md`,
authored directly in the Design project) that land at
`presentations/<slug>/src/marp/<slug>-{deck,executive-summary,infographic}-<date>.md`. Story 2.1
only pulls the prototype; there is no way yet to pull an authored Marp source.

**Approach:** Add `deck_pipeline.pull_marp_source`, reusing the same read/etag/decode loop
(`_pull_and_land`, Story 2.1) with a different remote path convention, a different local landing
path, and NO extract/build step (`deck-export` regenerates the derived set instead -- the
bridge-protocol text is explicit that this differs from the prototype pull). Wire it into
`herald deck pull` via a new `--target` flag, defaulting to `prototype` so Story 2.1/2.2's existing
CLI contract is unchanged for every caller that does not pass it.

## Boundaries & Constraints

**Always:**
- `deck_pipeline.pull_marp_source(transport, *, slug, repo_root, kind, commit=False, state_path=None, exporter=None, committer=None, now=None) -> PullResult`,
  `kind in {"deck", "executive-summary", "infographic"}`.
- Remote path: `f"{short}-{kind}.md"`, `short = slug.removeprefix("pyforge-")` -- matches
  `bridge-protocol.md`'s own worked example (`pyforge-warden` -> `warden-deck.md` inside the Warden
  Design project).
- Local landing path: `presentations/<slug>/src/marp/<slug>-<kind>-<date>.md`, `date` from the
  injected `now` clock (default UTC today, `YYYY-MM-DD`), reusing the exact `_pull_and_land` /
  `_atomic_write_text` machinery Story 2.1 already built (no re-decoding, truncation refusal, atomic
  write, state.py etag record under a new artifact key `f"marp:{kind}"`).
- No `prover`/extract/build call -- `bridge-protocol.md` is explicit ("no extract/build -- deck-export
  regenerates the derived set instead"). Only `exporter.export(slug=..., repo_root=...)` runs after a
  real change.
- `--commit` behaves identically to Story 2.2's: opt-in, never on an unchanged pull, stages
  `presentations/<slug>/` + the state file.
- `herald deck pull <slug> --target {prototype,marp-deck,marp-executive-summary,marp-infographic}`
  (the `standalone` choice is Story 2.4's) dispatches to `pull_prototype` or `pull_marp_source`
  accordingly; `--target` defaults to `prototype`, so every Story 2.1/2.2 CLI invocation and test is
  unaffected.

**Block If:** N/A -- no spike, no live gate.

**Never:**
- No standalone-bundle pull yet (Story 2.4).
- No lookup table for the Marp source filenames -- the `{short}-{kind}.md` derivation is mechanical,
  matching the persona/short-name conventions `_persona_from_slug` already established for `seed`.
- No live MCP call in this package's own test suite.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Unchanged | `read_file` answers `{unchanged: true}` for `warden-deck.md` | no write, no state update, no export | No error |
| Changed | real body | body written to `presentations/pyforge-warden/src/marp/pyforge-warden-deck-<date>.md`; state etag key `marp:deck` updated; `exporter.export` runs (no `prover`) | No error |
| Each `kind` | `deck` / `executive-summary` / `infographic` | remote/local paths + artifact key derived per-kind | No error |
| `--target marp-deck` | CLI | dispatches to `pull_marp_source(kind="deck")` | No error |
| `--target` omitted | CLI | dispatches to `pull_prototype` (Story 2.1 behavior, unchanged) | No error |
| Not seeded | no state entry | refused before any transport call | `HeraldError` |
| Truncated / no-body | as Story 2.1 | refused before write | `HeraldError` |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py` -- edit -- `_MARP_KINDS`,
  `pull_marp_source`.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` -- edit -- `deck pull` gains
  `--target` (choices: `prototype`, `marp-deck`, `marp-executive-summary`, `marp-infographic`,
  default `prototype`); `_run_deck_pull` dispatches on it.
- `src/shared/packages/pyforge-herald/tests/test_deck_pipeline.py` -- edit -- the I/O matrix's
  `pull_marp_source` rows.
- `src/shared/packages/pyforge-herald/tests/test_cli_pull.py` -- edit -- the `--target` dispatch rows.

## Design Notes

**Judgment call: one `pull_marp_source(kind=...)` call per artifact, not a batch "pull all three
Marp sources" call.** `bridge-protocol.md`'s prose lists all three sources together, but nothing in
its numbered steps requires pulling them atomically as one unit -- each is independently etagged in
`state.py` already (Story 1.4's `DeckState.etags` is a per-artifact map by design), and an operator
who only edited the executive summary in Design has no reason to force a redundant `read_file` +
no-op unchanged-check against the other two. Narrower, composable scope; a future `--target
marp-all` convenience wrapper is a trivial addition if it turns out to matter.

**Judgment call: `--target` (not a separate `pull-marp` subcommand).** Keeps `herald deck pull
<slug>` the single verb `bridge-protocol.md` names for all of CAP-2's read/etag/decode variants,
consistent with the epics AC framing ("pulls, and syncs Claude Design decks" as one bridge, not four
separate commands per artifact kind).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- full suite green.
- `ruff format --check` / `ruff check` clean on every file this story touches.
- `herald deck pull --help` -- shows `--target` with all four choices.

**Deferred live-MCP proof (NOT run by this session):** the orchestrating session must run one real
`herald deck pull pyforge-warden --target marp-deck` (or another Warden-family deck with an authored
Marp source in its Design project) against the live endpoint, confirming the remote path convention
(`{short}-{kind}.md`) matches what the Design project actually names the file. This is the one part
of this story's design that is a documented, evidence-backed convention (bridge-protocol.md's own
worked example) rather than something proven against a real project by this session -- flagged
explicitly as the highest-risk deferred item across all of Epic 2.

## Spec Change Log

## Review Triage Log

### 2026-08-07 — Self-review pass (single agent, no independent second reviewer)

- `[none]` No defects found. Verified directly:
  - `test_pull_marp_source_short_circuits_on_unchanged` proves the etag short-circuit skips
    `exporter.export` entirely (no `prover` call exists for this artifact by design -- confirmed no
    `LocalProver`/`prove` reference anywhere in `pull_marp_source`).
  - `pull_marp_source` reuses `_pull_and_land` unchanged -- the "no re-decode" guarantee Story 2.1's
    own review already verified applies here automatically, with no new decode path introduced.
  - `test_deck_pull_target_defaults_to_prototype` / `test_deck_pull_target_marp_deck_dispatches_to_pull_marp_source`
    each assert the OTHER dispatch target raises `AssertionError` if called, proving `--target`
    routes to exactly one of the two functions, never both.
  - `grep` sweep for MCP tool-name literals outside `transport.<method>(...)` and docstrings/comments:
    clean (same two `read_file` hits as Story 2.1/2.2, both inside error-message strings).
- `addressed_findings`: 0. `followup_review_recommended: true` retained -- the remote-path convention
  (`{short}-{kind}.md`) is the one piece of this story that is a documented convention, not something
  verified against a real Design project by this session; flagged as the deferred item.

**Verification:** `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 382 passed, 2 skipped
(was 371 passed, 2 skipped after Story 2.2; +11 net new tests: 7 in `test_deck_pipeline.py`, 4 in
`test_cli_pull.py`). `ruff format --check` / `ruff check` clean on every file this story touches.
