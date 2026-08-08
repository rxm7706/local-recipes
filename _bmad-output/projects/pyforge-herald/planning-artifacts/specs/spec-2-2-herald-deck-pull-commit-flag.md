---
title: '--commit opt-in flag on herald deck pull'
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

**Problem:** Story 2.1 shipped `herald deck pull` writing the pulled + re-derived files into the
working tree only -- `bridge-protocol.md` § Pull step 5 says "commit is the operator's (or
`--commit`'s) move -- never implicit," but there is no `--commit` yet.

**Approach:** Add an opt-in `--commit` flag that, only when the pull produced a real change (never
on an `{unchanged: true}` short-circuit), stages and commits the pulled artifact plus its re-derived
outputs plus the updated `.herald/bridge-state.json` in one commit, via a new injectable
`GitCommitter` seam mirroring `LocalProver`/`DeckExporter`'s existing pattern -- Herald has no
pre-existing git-wrapping convention of its own to reuse (Epic 1 never touched git); the shape it
adopts (`git add -- <paths>` then `git commit -m <message> -- <paths>`) mirrors
`pyforge-marshal`'s own `GitVcs.commit_paths` primitive, the one git-commit convention already
established anywhere in this monorepo.

## Boundaries & Constraints

**Always:**
- `pull_prototype` gains `commit: bool = False` and `committer: GitCommitter | None = None`
  parameters. When `commit=True` and the pull was NOT unchanged, `committer.commit(...)` runs after
  `prover`/`exporter`, staging `presentations/<slug>/` (the whole deck directory -- the prototype pull
  plus whatever `deck-export` regenerated under it) and the bridge-state file, then committing both
  with one message naming the slug and artifact.
- When `commit=True` and the pull WAS unchanged, no commit runs (nothing changed) -- `committed`
  stays `False` on the returned `PullResult`, same as the `commit=False` default.
- `GitCommitter` is a `runtime_checkable` `Protocol` (`commit(*, repo_root, paths, message) -> None`);
  `SubprocessGitCommitter` is the real implementation, two bounded `subprocess.run` calls (`git add
  --`, `git commit -m ... --`), mirroring `NpmLocalProver`/`PixiDeckExporter`'s existing
  error-mapping shape (`TimeoutExpired` -> `HeraldError`, launch `OSError` -> `HeraldError`, non-zero
  exit -> `HeraldError` with the stderr tail). Never invoked by this package's own tests.
- `herald deck pull <slug> --commit` wires the flag through to `pull_prototype`; CLI output notes
  when a commit happened.

**Block If:** N/A -- no spike, no live gate.

**Never:**
- No commit ever happens for an unchanged pull -- `--commit` is not "commit unconditionally," it is
  "commit if this pull actually changed something."
- No new git dependency (no `GitPython`/`pygit2`) -- `git` is invoked as an external process exactly
  like every other subprocess seam in this package (`npm`, `pixi`, the nested `claude` CLI).
- No git identity/signing override -- unlike `pyforge-marshal`'s `is_branch_merged`'s throwaway
  `commit-tree` object, this commit is meant to survive, so it uses the operator's own git
  identity/signing config (`GitVcs.commit_paths`'s own precedent for a real, persistent commit).
- This package's own test suite never runs a real `git add`/`git commit` -- every `pull_prototype`
  commit test injects a hand-written `FakeCommitter`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `--commit`, real change | pull changed the prototype | `committer.commit` called with `presentations/<slug>` + state path; `PullResult.committed is True` | No error |
| `--commit`, unchanged | `{unchanged: true}` | `committer.commit` never called; `committed is False` | No error |
| No `--commit` (default) | any pull outcome | `committer.commit` never called; `committed is False` | No error |
| Commit failure | `committer.commit` raises | propagated after the local write/state-update already landed (files are NOT rolled back) | `HeraldError` |
| CLI `--commit` success | `herald deck pull <slug> --commit` | exit 0; stdout notes the commit | No error |
| CLI without `--commit` | `herald deck pull <slug>` | exit 0; stdout unchanged from Story 2.1 | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py` -- edit -- adds
  `GitCommitter` (Protocol) + `SubprocessGitCommitter`; `pull_prototype` gains `commit`/`committer`.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` -- edit -- `deck pull` gains
  `--commit`; `_run_deck_pull` forwards it and reports commit status.
- `src/shared/packages/pyforge-herald/tests/test_deck_pipeline.py` -- edit -- `FakeCommitter`; the
  I/O matrix's commit rows.
- `src/shared/packages/pyforge-herald/tests/test_cli_pull.py` -- edit -- the I/O matrix's CLI
  `--commit` row.

## Design Notes

**Judgment call: commit the whole `presentations/<slug>/` directory, not an enumerated file list.**
`deck-export`'s own output filenames (PPTX, SVG, standalone HTML) are that external tool's business,
not this module's -- enumerating them here would duplicate knowledge this module has no business
owning and would silently miss a file the moment `deck-export`'s own output set changes.
`git add -- presentations/<slug>` (a directory pathspec) stages everything the pull + re-derive step
touched under it in one call, tracked or newly-created; anything `deck-export` leaves gitignored
(e.g. `dist/`, per `artifact-tracking-matrix.md`) is silently skipped by `git add` itself, exactly as
intended. `.herald/bridge-state.json` is added as a second, explicit path alongside it, since it
lives outside `presentations/`.

**Judgment call: a commit failure does not roll back the already-written files or the already-updated
state.** The local write and `state.py` update happen (Story 2.1's own sequence) before `committer
.commit` runs; if the commit itself fails (a dirty index lock, no git identity configured, `git` not
on PATH), the operator is left with the pulled files present but uncommitted -- exactly the state a
plain `--commit`-less pull leaves them in, so nothing is lost, only the commit step needs a manual
retry. Rolling back a successful file write because a *subsequent, independent* step failed would be
a bigger surprise than leaving it in place.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- full suite green.
- `ruff format --check` / `ruff check` clean on every file this story touches.
- `herald deck pull --help` -- shows `--commit`.

**Deferred live-MCP proof (NOT run by this session):** the orchestrating session must run one real
`herald deck pull <slug> --commit` against an already-seeded pilot deck with a genuine Design-side
edit pending, confirming the resulting commit is well-formed (correct paths staged, sensible message,
no unrelated files swept in). Never run from this session (constraint: never a live MCP call).

## Spec Change Log

## Review Triage Log

### 2026-08-07 — Self-review pass (single agent, no independent second reviewer)

- `[none]` No defects found. Verified directly:
  - `test_pull_prototype_commit_true_never_commits_an_unchanged_pull` proves the unchanged branch
    returns before `commit`/`committer` are even consulted (same early-return path Story 2.1's
    short-circuit test exercises) -- `--commit` cannot turn a no-op pull into a commit.
  - `test_pull_prototype_without_commit_never_calls_the_committer` proves the default
    (`commit=False`) never touches `committer` at all.
  - `grep -n "read_file\|write_files\|finalize_plan\|copy_files\|create_project\|create_support_js"`
    over `deck_pipeline.py` shows no new literal MCP tool call outside `transport.<method>(...)` or a
    docstring/comment; `git`/`SubprocessGitCommitter` names no MCP tool at all (git is not part of the
    `claude-design` surface), so the "no live MCP call" constraint is orthogonal to this story's own
    new subprocess seam and was re-checked anyway as part of the same sweep.
  - `test_pull_prototype_propagates_a_commit_failure` confirms the write + state update are not rolled
    back on a commit failure, matching the story's own documented judgment call.
- `addressed_findings`: 0. `followup_review_recommended: true` retained for the same reason as Story
  2.1: this is still a same-agent pass over code with real filesystem/git side effects, and the
  deferred live-MCP-adjacent proof below (a real `git commit`, not `claude-design`) is something this
  session cannot run either.

**Verification:** `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 371 passed, 2 skipped
(was 363 passed, 2 skipped after Story 2.1; +8 net new tests: 4 in `test_deck_pipeline.py`, 4 in
`test_cli_pull.py`). `ruff format --check` / `ruff check` clean on every file this story touches.


## Adversarial review pass (2026-08-07, Blind Hunter + Edge Case Hunter, Epic 2 batch)

Dispatched with the diff file path only, no shared context.

- `medium` `patch` **`SubprocessGitCommitter.commit` mishandled a non-trivial relative `repo_root`.** `rel_paths` only stripped `repo_root` from `paths` when `p.is_absolute()`; a relative `repo_root` (e.g. `--repo-root some/subdir`) left `paths` (already prefixed with `repo_root`, e.g. `repo_root / "presentations" / slug`) unchanged, and since the subprocess runs with `cwd=repo_root`, this doubled the prefix (`some/subdir/some/subdir/...`) -- git failed with a pathspec error even though the pull itself had succeeded. Fixed: both `repo_root` and each `p` are resolved to absolute paths first, then `relative_to` is computed unconditionally -- correct regardless of whether `repo_root` was absolute or relative to begin with. New tests: `test_subprocess_git_committer_commits_with_an_absolute_repo_root` and `test_subprocess_git_committer_commits_with_a_relative_repo_root`, both against a REAL scratch git repo (matching this repo's own "prove concurrency/subprocess claims against real state, not mocks" convention) -- the real `SubprocessGitCommitter` implementation was previously never exercised by this package's own test suite at all (every `pull_*` test injects a fake committer).

**Re-verification (2026-08-07, after the patch):** `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- **392 passed, 2 skipped** (full suite).

**Follow-up review recommendation (updated): false** -- narrow fix, covered by dedicated real-subprocess regression tests.
