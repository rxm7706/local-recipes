---
title: 'Nightly compile from named tool surfaces (Story 2.2)'
type: 'feature'
created: '2026-08-07'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: '2ad677d0'
---

<intent-contract>

## Intent

**Problem:** The graph store (Story 2.1) has nothing in it. Nobody hand-
maintains a wiki of "why did we do X" -- the answer is scattered across
`.claude/memory/`, `.memlog.md` files, git history, retros, and CHANGELOGs.

**Approach:** Add `compile.py`: `compile_graph()` reads those named surfaces,
builds one `GraphNode` per source item (traceable via `citation` to the
source file/commit), and writes them through the `GraphStore` port from
Story 2.1 via a full reset-then-rebuild (never an incremental patch, AD-1) --
so re-running with no new source activity reproduces byte-identical output
(idempotency). Wire `scribe graph compile [--nightly]` in `cli.py` to call
it, replacing the Epic-1 stub.

## Boundaries & Constraints

**Always:**
- Reads exactly these five named surfaces (PRD Open Question 2, resolved
  here): `.claude/memory/{feedback,project,reference}/*.md` (via
  `parse_capture_file`), any `.memlog.md` file under `repo_root`, `git log`
  (local, no fetch/pull) for recent commits, `CHANGELOG.md` files under
  `repo_root`, and files matching `*retro*.md` under `repo_root`.
- Excludes vendored/heavy/generated directories from every repo-wide glob:
  `.git`, `.pixi`, `node_modules`, `.claude/worktrees`, `.claude/data`,
  `dist`, `dist-conda`, `build_artifacts`, `__pycache__`, `.venv`, `venv`.
- `git log` is invoked read-only (`git log`, never `git fetch`/`git pull`) --
  no network call, matching AD-6.
- The default graph-store path is `<repo_root>/.claude/data/pyforge-scribe/graph.json`
  -- already blanket-gitignored (`.gitignore:718`), never `.claude/memory/`
  (Story 2.1's Design Notes: the compiled graph is derived/disposable, AD-1,
  not a tracked artifact).
- Every run is a full `store.reset()` + rebuild from current source state +
  one `store.commit()` -- never an incremental append. Given unchanged
  sources, two consecutive runs produce byte-identical store file content
  (idempotency AC).
- `compile_graph()` never prompts (no `typer.confirm()`/`input()` anywhere in
  its call path) and completes without a human present (unattended AC) --
  `--nightly` is accepted for CLI/scheduling clarity but does not change this
  behavior (compile is unattended-by-construction either way).
- A single degraded surface (e.g. `git` binary absent, or a malformed source
  file) must not abort the whole compile -- log a warning to stderr and
  continue with the remaining surfaces; only a missing/malformed
  `memory_root` (mirroring `capture.py`'s existing contract) raises
  `ValueError` before any write.
- Zero required network calls (AD-6) -- grepped for `socket`/`http`/`urllib`/
  `requests` imports; none present.

**Block If:** none.

**Never:**
- Do not implement supersession semantics yet (Story 2.3 owns invalidating
  edges) -- this story only reads `.claude/memory/`'s existing content as-is
  (a `supersedes` field present in the source is simply carried, unused,
  until 2.3).
- Do not implement `recall.py` (Story 2.4).
- Do not use the real repo `.claude/memory/`/`.git` state in unit tests where
  a `tmp_path` fixture with a real `git init` sub-repo suffices; git-history
  reading tests may use a throwaway `git init`'d `tmp_path` repo (no network,
  no dependency on this repo's actual history).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | one `.claude/memory/feedback/*.md`, one `.memlog.md`, a tmp git repo with 2 commits | `compile_graph()` returns node_count >= 3; each node's citation resolves to a real path/commit in the fixture | No error |
| Idempotent re-run | run twice, no source change between runs | second run's store file bytes == first run's | No error |
| Unattended | no stdin available (CliRunner with no `input=`) | `scribe graph compile --nightly` completes, exit 0, no prompt | Never blocks on input |
| Missing memory_root | `.claude/memory/` does not exist | `ValueError` before any write (mirrors `capture()`'s contract) | CLI catches, prints, exits 2 |
| No `.memlog.md`/retro/CHANGELOG files present | only `.claude/memory/` has content | compile still succeeds; those surfaces contribute zero nodes | No error |
| `git` binary absent (simulated via `PATH` override) | `shutil.which("git")` returns `None` | compile logs a warning, skips git-history nodes, still succeeds for the other surfaces | Never raises |
| Malformed `.claude/memory/*.md` file (bad frontmatter) | one entry fails `parse_capture_file` | that entry is skipped with a stderr warning; other entries still compile | Never aborts the whole run |
| Zero network | any read/write during compile | zero socket construction (offline-conformance style check, reusing Story 2.1's precedent) | Verified by test |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py` (NEW) — `compile_graph()`, `CompileResult`, per-surface readers, `default_store_path()`
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py` — wire `graph_compile` to `compile_graph()`, replacing the Epic-1 stub
- `src/shared/packages/pyforge-scribe/tests/unit/test_compile.py` (NEW)
- `src/shared/packages/pyforge-scribe/tests/unit/test_cli.py` — replace `test_graph_compile_stub_touches_nothing_and_exits_0` with real-behavior coverage
- `_bmad-output/projects/pyforge-scribe/planning-artifacts/epics-with-stories.md` (L29-46) — Story 2.2's source ACs

## Tasks & Acceptance

**Execution:**
- [x] `compile.py` -- five-surface readers (memory/memlog/git/changelog/retro), `default_store_path()`, `compile_graph()` full-rebuild orchestration
- [x] `cli.py` -- wire `graph compile [--nightly]` to `compile_graph()`
- [x] `test_compile.py` -- happy path, idempotency, degraded-surface tolerance, malformed-entry tolerance
- [x] `test_cli.py` -- replace the stub test with real CLI coverage (unattended, missing memory_root exits 2)

**Acceptance Criteria:**
- Given entries in `.claude/memory/`, a `.memlog.md` file, and recent git commits, when `scribe graph compile --nightly` runs, then graph nodes are produced, each traceable to its source file/commit, via the `GraphStore` port (FR-9).
- Given a re-run with no new source activity, when it completes, then the resulting graph state is unchanged -- no duplicate nodes, no spurious edges (FR-11, idempotency).
- Given no interactive input is available, when the compile step executes, then it completes without prompting (FR-11, unattended).
- And the compile step performs zero required network calls in its default configuration (AD-6).

## Design Notes

- **Commit-count bound:** `git log` reads the most recent `max_commits`
  (default 100) commits repo-wide via `git log -n <N> --date=iso-strict
  --pretty=format:...`. This keeps each run's cost and node count bounded;
  since commits are content-addressed and immutable, two runs against an
  unchanged repo produce the exact same 100-commit window (idempotent by
  construction), and a real nightly delta/bookmark mechanism is deferred
  (out of this story's scope -- the AC only requires idempotency for "no new
  source activity", which this satisfies).
- **Degraded-surface tolerance is a deliberate design choice**, not laxity:
  an unattended nightly job that hard-fails because one memlog file has a
  typo, or because `git` happens to be temporarily unavailable, defeats the
  "reflects reality without anyone hand-maintaining it" goal worse than a
  partial compile with a logged warning would. Only a structurally broken
  `memory_root` (the one thing every other surface depends on existing)
  raises.
- **One node per file for memlog/CHANGELOG/retro surfaces** (not per-line or
  per-entry) -- the AC requires traceability to the source file, not a
  fully-parsed sub-structure; finer granularity is a natural future
  extension behind the same `GraphStore` port, not required here.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` -- expected: full suite green
- `git diff --stat` -- expected: only the files in Code Map changed

## Review Triage Log

- **Concurrency (corrected during review):** `commit()`'s lock (Story 2.1)
  only serializes the FINAL atomic write, not the whole
  reset-read-rebuild-commit window -- two overlapping `scribe graph compile`
  invocations each compute their own in-memory node set independently (no
  shared mutable state before `commit()`), then race on the write. Because
  both are full, deterministic rebuilds of the *same* source state (or, if
  source changed mid-race, each is still a fully valid rebuild of ITS
  observed state), the result is benign last-writer-wins, never a corrupted
  or partially-merged file. True mutual exclusion across the whole compile
  (not just the commit) is not required by this story's ACs and is not
  implemented -- flagged here rather than silently assumed away.
- **Idempotency:** verified via test that an unchanged fixture (same
  `.claude/memory/` content, same tmp git repo, same memlog files) produces
  byte-identical `graph.json` content across two consecutive `compile_graph()`
  calls.
- **Silent drops:** malformed `.claude/memory/*.md` entries and a
  `git`-absent environment both log a stderr warning rather than silently
  vanishing -- verified the warning text names the specific skipped path/surface.
- **AD-6:** grepped `compile.py` for `socket`/`http`/`urllib`/`requests` --
  none; `git log` is the only subprocess call, and it never contacts a
  remote (no `fetch`/`pull`/`clone`/`ls-remote`).
- **No accidental docstring drift:** `compile_graph()`'s docstring names
  exactly the five surfaces it reads; kept in sync with the Boundaries list.


## Adversarial review pass (2026-08-07, Blind Hunter + Edge Case Hunter)

Dispatched with the diff file path only, no shared context. Two findings landed here:

- `medium` `patch` **Non-UTF-8 commit content crashed the whole nightly compile.** `_read_git_surface`'s `subprocess.run` used `text=True` with no `encoding=`/`errors=`, so a commit authored with non-UTF-8 content (message or author name) raised `UnicodeDecodeError` -- a `ValueError` subclass NOT caught by the surrounding `except (OSError, subprocess.TimeoutExpired)`. Fixed: added `encoding="utf-8", errors="replace"`, matching the sibling `_node_from_text_file` reader's existing pattern. New test: `test_non_utf8_commit_message_is_replaced_not_a_crash`.
- `low` `patch` **`_EXCLUDED_DIR_NAMES`'s bare `"data"` entry silently excluded any directory literally named `data` anywhere in the repo**, not just `.claude/data` (the graph store's own gitignored home) -- a legitimate `CHANGELOG.md`/`.memlog.md`/`*retro*.md` under e.g. `src/mypackage/data/` was silently dropped from the compiled graph with no warning. Fixed: `data` is now matched only as the adjacent pair `(".claude", "data")`; every other excluded name still matches anywhere. New test: `test_data_named_directory_outside_dot_claude_is_not_excluded`.

**Re-verification (2026-08-07, after both patches):** `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` -- **88 passed** (full suite).

**Follow-up review recommendation (updated): false** -- both findings are narrow, each covered by a dedicated regression test.
