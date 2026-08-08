---
title: 'Stale hand-mirror detection'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: true
context: ['spec-3-1-herald-deck-status-slug.md']
warnings: []
---

<intent-contract>

## Intent

**Problem:** Before Herald existed, at least one Design project (the cautionary
`"Local recipes repository connection"` fixture named in `bridge-protocol.md` § Pilot evidence, a
hand-mirrored copy of `presentations/pyforge-atlas/`) was built by manually copying an entire repo
app-tree into Claude Design file-by-file -- exactly the workflow the bridge exists to replace. Nothing
in Herald can currently tell an operator that a given Design project is secretly one of these stale
mirrors rather than a normal bridge project; an operator has to notice by eye.

**Approach:** Add `stale_mirror: bool` to every `DeckStatus` `deck_pipeline.status` (Story 3.1)
returns, computed by a small, concrete, testable heuristic (`_is_stale_mirror`) over
`transport.list_files`'s answer for the deck's linked project: a legitimate bridge project holds a
handful of flat, project-root-named files; a hand-mirrored repo copy holds many files, several of
them under nested paths reproducing the repo's own directory structure. Both conditions -- file count
past a threshold, and a minimum count of nested paths -- must hold together, so neither condition
alone can false-positive.

## Boundaries & Constraints

**Always:**
- `_is_stale_mirror(files: Sequence[ListedFile]) -> bool` in `deck_pipeline.py`: `False` unless
  `len(files) >= _STALE_MIRROR_FILE_COUNT_THRESHOLD` (15) **and** the count of entries whose `path`
  contains `"/"` is `>= _STALE_MIRROR_NESTED_PATH_THRESHOLD` (5). Both thresholds are named module
  constants with their own reasoning documented alongside them (see Design Notes).
- `_status_for_slug` (Story 3.1) calls `_is_stale_mirror(transport.list_files(project_id=...))` once
  per linked deck and threads the result into `DeckStatus.stale_mirror`. An unlinked deck is never
  flagged (`stale_mirror: False`, no `list_files` call at all -- there is no project to enumerate).
- The heuristic has both a positive and a negative fixture in the test suite:
  `_hand_mirrored_repo_files()` (the cautionary pattern: dozens of files, several under `src/...`,
  `.claude/...`-style nested paths) must flag `True`; `_normal_bridge_project_files()` (the runtime
  pair, one prototype, three Marp sources, one standalone bundle, all flat) must flag `False`. A third
  fixture proves neither condition alone is sufficient: many flat files (`False`) and few nested files
  under the count threshold (`False`).
- `cli.py`'s `deck status` JSON output includes `stale_mirror` for every deck in the report (already
  wired as part of Story 3.1's own `_run_deck_status`, since both stories' code landed together).

**Block If:** N/A -- no spike, no live gate. This story never calls `list_files` against the real
cautionary fixture project (`e2a3ed13-7c0b-46ff-9d70-c41eeb93c2ea`, per `bridge-protocol.md`'s own
pilot table) -- that live confirmation is recorded as an explicit deferred follow-up below, mirroring
Epic 2's own precedent for deferred live-MCP smoke tests.

**Never:**
- No file-content inspection -- the heuristic reads only `ListedFile.path` (never fetches any file's
  body via `read_file`); `stale_mirror` detection must stay as cheap as the rest of `status` (an
  etag-only comparison, no body pull).
- No new CLI flag -- `stale_mirror` is unconditionally part of every `deck status` JSON entry, not an
  opt-in `--check-mirror` toggle.
- No auto-remediation -- this story only flags; retiring or cleaning up a flagged project is an
  operator decision, entirely out of scope here (and out of Herald's scope generally -- Herald never
  deletes a Design project).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Hand-mirrored fixture | `list_files` returns 23 entries, 13 nested | `stale_mirror: true` | No error |
| Normal bridge project | `list_files` returns 7 flat entries | `stale_mirror: false` | No error |
| Many flat files, no nesting | 20 entries, 0 nested | `stale_mirror: false` (count alone insufficient) | No error |
| Few nested files, under count threshold | 3 entries, 2 nested | `stale_mirror: false` (nesting alone insufficient) | No error |
| Unlinked deck | no state entry | `stale_mirror: false`; `list_files` never called | No error |
| `herald deck status <slug>` on a flagged deck | CLI | JSON entry's `stale_mirror` is `true` | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py` -- edit (same commit set
  as spec-3-1) -- `_STALE_MIRROR_FILE_COUNT_THRESHOLD`, `_STALE_MIRROR_NESTED_PATH_THRESHOLD`,
  `_is_stale_mirror`, `DeckStatus.stale_mirror` field, wired into `_status_for_slug`.
- `src/shared/packages/pyforge-herald/tests/test_deck_status.py` -- create (same commit set as
  spec-3-1) -- `_normal_bridge_project_files`/`_hand_mirrored_repo_files` fixtures, direct
  `_is_stale_mirror` unit tests, and `status()`-level tests threading the flag through for both a
  flagged and an unflagged deck, plus the never-flags-an-unlinked-deck case.
- `src/shared/packages/pyforge-herald/tests/test_cli_status.py` -- create (same commit set) --
  `test_deck_status_reports_a_stale_mirror_flag`.

## Design Notes

**Why both conditions, not either alone.** File count alone would false-positive the moment a future
story gives a deck legitimately many tracked artifacts (e.g. per-locale Marp sources) -- nothing in
`bridge-protocol.md`'s conventions caps how many flat artifacts a real deck could eventually carry.
Nested-path count alone would false-positive on one stray file (an operator manually dragging a single
misplaced file into an otherwise-normal project). Requiring both together only fires on the actual
shape a hand-mirrored repo copy produces: many files, several genuinely nested.

**Why 15 / 5 as the specific thresholds.** `bridge-protocol.md`'s own conventions bound a legitimate
bridge project's file count at roughly eight (the runtime pair, one prototype, up to three Marp
sources, one standalone bundle) -- 15 is comfortably above that ceiling without being so high that a
real mirror (which reproduces a genuine repo tree, realistically dozens to hundreds of files) could
sit under it. Zero legitimate artifact name in this bridge ever contains `/` (every one is a flat,
project-root filename per convention) -- five nested paths is a small, deliberately conservative floor
that a real repo-tree mirror clears many times over (its own top two directory levels alone produce
far more than five nested entries) while comfortably exceeding what one or two accidental/transitional
files could produce.

**Judgment call: the heuristic is path-shape-only, not name-content matching.** An alternative design
matched specific filenames (`pyproject.toml`, `package.json`, `.gitignore`) against a known-repo-marker
list. Rejected: a marker list is brittle against repo restructuring and does not generalize to a
mirror of a *different* repo than this one; path nesting is a structural property every hand-mirrored
copy of any repo shares, and requires no maintained list.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- **502 passed, 2 skipped** (shared
  commit set with spec-3-1; see that spec's own Verification section for the full baseline delta).
- `ruff format --check` / `ruff check` -- clean on every file this story touches.
- Direct unit coverage: `test_is_stale_mirror_flags_the_hand_mirrored_repo_fixture`,
  `test_is_stale_mirror_does_not_flag_a_normal_bridge_project`,
  `test_is_stale_mirror_requires_both_file_count_and_nesting`.

**Deferred live-MCP proof (NOT run by this session, mirroring Epic 2's own precedent):** the
orchestrating session should run one real `herald deck status` (once `list_files` support is
confirmed live) against the actual `"Local recipes repository connection"` project
(`e2a3ed13-7c0b-46ff-9d70-c41eeb93c2ea`) to confirm the heuristic's thresholds hold against the real
fixture's real file count and path shapes, not only the hand-authored test fixtures here. This
package's own test suite never makes this call (constraint: no live MCP call from this session).

## Spec Change Log

## Review Triage Log

### 2026-08-07 — Self-review pass (single agent, no independent second reviewer)

Adversarial re-read after the suite was green, looking specifically for: whether the two thresholds
individually gate correctly (an off-by-one at either boundary), whether an unlinked deck could ever
reach `_is_stale_mirror` at all, and whether the heuristic reads any file body (it must not).

- `[none]` No defects found. Verified directly:
  - `test_is_stale_mirror_requires_both_file_count_and_nesting` exercises exactly the two "only one
    condition holds" cases (20 flat files; 3 files with 2 nested) and both correctly return `False`.
  - `test_status_never_flags_stale_mirror_for_an_unlinked_deck` asserts `stale_mirror is False` *and*
    `transport.calls == []` for an unknown slug -- `_is_stale_mirror`/`list_files` are never reached
    on the unlinked path, confirmed structurally (`_status_for_slug` returns before the linked branch)
    rather than merely by the flag's default value happening to be `False`.
  - `_is_stale_mirror`'s own body reads only `listed.path` off each `ListedFile` -- grepped
    `deck_pipeline.py` for any `read_file`/body access anywhere near the stale-mirror code path; none
    found outside the pre-existing `pull_*` functions this story does not touch.
- `addressed_findings`: 0. `followup_review_recommended: true` is set above for the same reason as
  spec-3-1's own entry: no independent second reviewer has looked at this pass, and the deferred live
  fixture confirmation against the real `"Local recipes repository connection"` project is still owed.
