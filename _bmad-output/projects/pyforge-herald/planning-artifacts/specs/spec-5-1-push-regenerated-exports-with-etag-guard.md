---
title: 'Push regenerated exports with etag guard'
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

**Problem:** `bridge-protocol.md` § *Export push-back (CAP-5, per export-revisit resolution)* names
a fifth CAP the earlier epics never implement: after a pull's own re-derivation runs
`deck-export`, the freshly regenerated derived exports sit only in the repo -- Design has no way to
know they changed, so it drifts back out of sync with the repo's own artifact set the moment an
operator edits directly in Design and pulls again. Nothing in this package pushes anything into
Design; every prior CAP (1, 2) is repo-bound (`seed` writes once at creation, every `pull_*` only
ever reads).

**Approach:** Add `deck_pipeline.push_exports`, the first write-to-Design CAP built on top of CAP-2's
`_require_seeded_state` seam. For each discovered derived export file: compute its current content
hash, compare against a `state.py`-tracked "last-pushed hash" record (namespaced
`f"export:{filename}"` in the same `DeckState.etags` map pull already uses, `absent == never
pushed`), skip files whose hash is unchanged (no `write_files` call at all), and for every changed
file, declare it via one batch `finalize_plan` call and write it via `write_files` using the
server's own current etag for that path (`plan.base_etags`, `"0"` for a path that does not exist
there yet) as the `if_match` guard.

## Boundaries & Constraints

**Always:**
- `deck_pipeline.push_exports(transport, *, slug, repo_root, export_dir=None, state_path=None) ->
  ExportPushResult(slug, pushed: tuple[str, ...], skipped: tuple[str, ...])`.
- Requires a prior `seed` -- reuses `_require_seeded_state` (Story 2.1's seam) unchanged; refuses
  before any transport call when the slug has no recorded `state.DeckState`.
- Skip decision: a file's freshly computed `sha256` content hash compared against
  `existing.etags.get(f"export:{filename}")`; equal -> skipped, no `write_files` call for it (FR-19,
  NFR-08). Absent record (`None`) never equals a real hash, so a first-ever push for that filename
  always attempts the write.
- Write guard: when at least one file changed, ONE `finalize_plan(project_id=..., writes=[<changed
  filenames>])` call declares the whole changed batch; each file is then written with its own
  `write_files` call using `plan.base_etags.get(filename, "0")` as `if_match` -- `"0"` naturally
  covers both "never seen by finalize_plan" and "does not exist on the server yet" (FR-18).
- On any write success: `state.py`'s `f"export:{filename}"` record is updated to the new content
  hash. Nothing else in `existing.etags` (prototype/marp/standalone-bundle keys from CAP-2) is ever
  touched -- `push_exports` always writes back a *copy* of `existing.etags` with only the
  successfully-pushed keys added, never a fresh dict.
- No export files discovered on disk yet (`deck-export` never ran for this slug) is a no-op --
  `ExportPushResult(pushed=(), skipped=())`, not an error, and makes no transport call at all.
- `herald deck push <slug> [--repo-root ...]` -- a new, separate `deck` subcommand (see Design Notes
  for why not folded into `deck pull`), routed through `dispatch` (AD-6) exactly like `deck
  seed`/`deck pull`.

**Block If:** N/A -- no spike, no live gate.

**Never:**
- No PPTX push in this story. `DesignTransport.write_files`'s `data` field is documented and proven
  (by `seed`/`pull_prototype`) only as inline *text* content; `docs/specs/presentation-deck.md` §
  *Standard export set* names two PPTX companions that are binary, and no story in this package has
  observed or proven a binary `write_files` wire shape. `_discover_export_files` covers only the
  text-content standalone HTML poster (`{slug}-infographic-standalone-*.html`) -- see Design Notes.
- No auto-trigger from `deck pull`'s own completion -- `push` is its own subcommand (Design Notes).
- No live MCP call in this package's own test suite.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| First push | no `export:` record for the filename | `finalize_plan` + `write_files` with `if_match="0"`; hash recorded | No error |
| Unchanged | stored hash == current file hash | no `finalize_plan`/`write_files` call for that file | No error |
| Changed after a prior push | stored hash != current file hash | pushed again with the server's current `base_etags` value as `if_match` | No error |
| Nothing to push | no derived file on disk (`deck-export` never ran) | `ExportPushResult(pushed=(), skipped=())`, zero transport calls | No error |
| Not seeded | no state entry | refused before any transport call | `HeraldError` |
| Multiple changed files | >1 file needs pushing | one `finalize_plan` declares the whole batch; one `write_files` call per file | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py` -- edit -- new CAP-5
  section: `ExportPushResult`, `_ExportCandidate`, `_EXPORT_ARTIFACT_PREFIX`,
  `_discover_export_files`, `push_exports`.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` -- edit -- `deck push` subparser +
  `_run_deck_push`, wired through `_route`/`dispatch`.
- `src/shared/packages/pyforge-herald/tests/test_deck_pipeline.py` -- edit -- `FakePushTransport`,
  `_write_export_html`, the `push_exports` happy-path/skip/no-op/not-seeded test rows.
- `src/shared/packages/pyforge-herald/tests/test_cli_push.py` -- new -- `deck push` CLI wiring tests,
  mirroring `test_cli_pull.py`'s shape.

## Design Notes

**Judgment call: `herald deck push` is a standalone subcommand, not an auto-trigger on `deck pull`'s
completion.** `bridge-protocol.md`'s prose describes push-back as following a pull + `deck-export`
cycle, which reads as sequential narrative, not literally "one CLI invocation must do both". Folding
the push into `deck pull` would make `deck pull`'s own success/failure story conditional on a second,
independently-failable write operation (a Design-side conflict on an export file would then make a
*pull* command report failure, which is confusing -- the pull itself genuinely succeeded). Keeping
them separate mirrors `deck seed`/`deck pull`'s own precedent (each is one verb, one clear
success/failure story) and lets an operator re-run just the push after resolving a conflict (Story
5.2) without re-pulling or re-exporting anything.

**Judgment call: PPTX push deferred, only the standalone HTML poster is covered.** Recorded in full
in `deck_pipeline.py`'s own CAP-5 module comment: `DesignTransport.write_files` is proven only for
text (`seed`'s prototype write, `pull_prototype`), and no story anywhere in this package has observed
a binary wire shape -- inventing a base64/encoding convention unverified against the real server
would be exactly the kind of "unpinned wire shape" guess `seed`'s own module doc already flags as a
known risk (DW-1-2-5) for a *conflict* response; doing the same for a *binary write* would compound
it. `_discover_export_files` is written to be trivially extensible (add a glob + binary handling)
once a real `write_files` binary shape is proven live -- flagged as a verification gap below, not
silently assumed away.

**Judgment call: the "last-pushed" record stores a local content hash, not a Design-returned etag.**
The write-precondition `if_match` always comes fresh from `finalize_plan`'s own `base_etags` (the
server's live answer at plan time, exactly the pattern `seed` already established with
`plan.base_etags.get(path, _FRESH_ETAG)`) -- there is no need to remember a prior server etag for
that purpose. What Story 5.1's AC actually needs remembered is "did this file's *content* change
since we last successfully pushed it", a purely local question a content hash answers directly and
unambiguously (no server round-trip needed to decide whether to skip). The `etags` field name is
`state.py`'s own general-purpose opaque-string map (documented as "stores and round-trips the map
without interpreting its keys" and, by the same reasoning, values); repurposing it to hold a local
hash under a distinct `export:`-prefixed key is consistent with that contract and required no schema
change.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- full suite green.
- `ruff format --check` / `ruff check` clean on every file this story touches.
- `herald deck push --help` -- shows the new subcommand.

**Verification gap (not closed by this story):** the two PPTX companions named in
`docs/specs/presentation-deck.md` § *Standard export set* are not pushed by this implementation --
see the Design Notes judgment call above. A future story should prove a binary `write_files` shape
live before extending `_discover_export_files` to cover them.

**Deferred live-MCP proof (NOT run by this session):** the orchestrating session must run one real
`herald deck push pyforge-warden` against the live endpoint (after a real `deck-export` regeneration)
to confirm `write_files` accepts the standalone HTML's actual byte size/content over the real wire,
and that the Design project ends up holding a file whose name matches the repo's exactly.

## Spec Change Log

## Review Triage Log

### 2026-08-07 — Self-review pass (single agent, no independent second reviewer)

Adversarial re-read focused on the skip/write-guard mechanics and on whether any write path could
ever reach the transport without a valid `if_match` precondition.

- `[none]` No defects found. Verified directly:
  - `test_push_exports_skips_a_file_whose_local_hash_is_unchanged` proves the skip path makes zero
    `finalize_plan`/`write_files` calls -- not merely that the result looks right.
  - `test_push_exports_first_push_uses_the_0_sentinel_etag` proves `if_match == "0"` for a path
    `finalize_plan`'s fake answered with no `base_etags` entry, matching `seed`'s own established
    `_FRESH_ETAG` fallback.
  - `test_push_exports_nothing_to_push_makes_no_transport_calls` proves the no-derived-file-yet path
    never even calls `finalize_plan` -- an empty `writes` list would otherwise be a genuine
    `TransportCallError` risk (`McpTransport.finalize_plan` refuses an empty paths-scope plan).
  - `grep` sweep for MCP tool-name literals over `deck_pipeline.py`'s new section: clean (only
    `transport.<method>(...)` calls, docstrings, comments).
- `addressed_findings`: 0. `followup_review_recommended: true` retained -- this story's own
  Verification section already names the PPTX gap and the deferred live-MCP proof.

**Verification:** `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 488 passed, 2 skipped
(was 470 passed, 2 skipped before Epic 5; +18 net new tests across Stories 5.1/5.2 combined: 11 in
`test_deck_pipeline.py`, 7 in `test_cli_push.py`). `ruff format --check` / `ruff check` clean on
every file this story touches.
