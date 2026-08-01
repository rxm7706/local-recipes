<!-- Promoted from implementation-artifacts/ to tracked specs on 2026-08-04 -->
---
title: 'Story 1.4: Provision a loop home'
type: 'feature'
created: '2026-07-30'
status: 'done'
baseline_revision: 'e868b607a10a8fbfba046a191d5ac637bde42f80'
final_revision: '2cd302bfbb3df8f70b9648bea11b5b476c1977a4'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** Standing up a loop home today is three manual commands (`bmad-loop-worktree`, its internal `bmad-switch` call, remembering `BMAD_ACTIVE_PROJECT`) glued together by shell scripts nobody owns as a product surface — FR-1/FR-2, AD-11, AD-21.

**Approach:** Add `marshal init <slug>`: an idempotent `cli/init.py` command that reconciles-then-acts (AD-21) over a git worktree on `loop/<slug>` plus that home's own active-project marker and `planning-artifacts` symlink, via new `VcsPort`/`FsPort` protocols backed by `adapters/vcs_git.py` (subprocess `git`) and `adapters/fs_local.py`. Ports the existing scripts (`scripts/bmad-loop-worktree` provision path + `scripts/bmad-switch`'s marker/symlink logic) into Marshal's own architecture rather than reinventing the mechanism.

## Boundaries & Constraints

**Always:**
- `cli/init.py` orchestrates only; all subprocess/filesystem I/O goes through `ports.VcsPort` / `ports.FsPort`, implemented solely by `adapters/vcs_git.py` / `adapters/fs_local.py` (Structural Seed: `cli/` = "argparse tree, envelope rendering, exit-code emission only").
- Loop-home root: `$BMAD_LOOP_HOME_ROOT` or `~/.bmad-loops`; home path = `<root>/<slug>` (the live convention `scripts/bmad-loop-worktree` already uses for 8 concurrent homes — do not reinvent the sibling-repo layout the FR-1 wording nostalgically references).
- The new branch is always created FROM `main` (`git worktree add -b loop/<slug> <home> main`) — `main` itself is never checked out into the new tree.
- Re-running against a converged home performs zero writes and exits 0, reporting every step `done|skipped|failed` (AD-21, NFR-7).
- Symlink written before marker (mirrors `scripts/bmad-switch`'s ordering rationale: the marker must never advance past a symlink that failed to move).
- Reuse `core.policy._is_valid_project_slug`'s shape check for the slug argument rather than a second regex (spec-1-3's reviews repeatedly killed exactly this drift class).
- Every failure/success path returns via the envelope (AD-14) with registered `MRS-INIT-*` codes (AD-15); no bare exception escapes the CLI handler.

**Block If:** none — this ports a working local script into Marshal's own code; no new product decision is required.

**Never:**
- No Tier-3/`implementation-artifacts` backlink (Story 1.5), isolation verification or enumeration (Story 1.6), preflight or adapter seeding (Story 1.7), or teardown (Story 1.8).
- No harness invocation or `.bmad-loop/policy.toml` rendering (Story 1.10's `adapters/harness_bmadloop.py` stays unwired; not this story's job).
- No new runtime dependency — `git` via stdlib `subprocess`, matching AD-4 (adapters are the only impure code).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fresh provision | Valid slug, no existing worktree, `_bmad-output/projects/<slug>/` exists on `main` | Worktree created on `loop/<slug>`, marker written, `planning-artifacts` symlink points at `projects/<slug>/planning-artifacts`, launch line printed, exit 0 | n/a |
| Idempotent re-run | Same slug, home already converged | All steps report `skipped`, zero writes, exit 0 | n/a |
| Unknown project | Slug with no `_bmad-output/projects/<slug>/` on `main` | No worktree created | `MRS-INIT-002`, `Verdict.UNEVALUABLE` |
| Malformed slug | Empty string, path separator, or char outside the slug charset | No I/O attempted | `MRS-INIT-001`, `Verdict.UNEVALUABLE` |
| Worktree op fails | `git worktree add` errors (locked index, permission) | Partial state left as-is, never auto-cleaned | `MRS-INIT-004`, `Verdict.ERROR` |
| Marker/symlink desync | Prior partial failure left marker and symlink naming different slugs | Blocking finding before any further write | `MRS-INIT-003`, `Verdict.ERROR` |

</intent-contract>

## Code Map

- `src/pyforge/marshal/ports/vcs.py` -- NEW: `VcsPort` Protocol -- `repo_common_root`, `branch_exists`, `worktree_path_for_branch`, `add_worktree`
- `src/pyforge/marshal/ports/fs.py` -- NEW: `FsPort` Protocol -- `read_text`, `write_text_atomic`, `read_symlink_target`, `repoint_symlink_atomic`, `is_dir`
- `src/pyforge/marshal/adapters/vcs_git.py` -- NEW: `GitVcs`, subprocess `git` implementation
- `src/pyforge/marshal/adapters/fs_local.py` -- NEW: `LocalFs`, `os`/`pathlib` implementation
- `src/pyforge/marshal/cli/init.py` -- NEW: `add_init_subparser`, `run_init` -- reconcile-then-act over the four steps, envelope rendering, launch-line print
- `src/pyforge/marshal/cli/main.py` -- EDIT: wire `init_cli.add_init_subparser(subparsers)`
- `src/pyforge/marshal/core/findings.py` -- EDIT: register `MRS-INIT-001..004`
- `src/pyforge/marshal/core/verdict.py` -- EDIT: classify the 4 new codes
- `src/shared/packages/pyforge-marshal/pyproject.toml` -- EDIT: add `[tool.pytest.ini_options] markers = ["slow: ..."]` (mirrors `pyforge-warden`'s convention, needed by the new integration test)
- root `pixi.toml` -- EDIT: `pyforge-marshal-test` task gains `-m "not slow"`; follow-up review adds the `pyforge-marshal-test-slow` counterpart task (mirrors `pyforge-warden-test-corpus-oracle`'s split)
- `tests/unit/test_vcs_git.py`, `tests/unit/test_fs_local.py` -- NEW: adapter tests against real temp git repos / tmp_path
- `tests/unit/test_init.py` -- NEW: orchestration + I/O-matrix scenarios
- `tests/unit/test_cli.py`, `tests/unit/test_findings.py` -- EXTEND
- `tests/meta/test_ad11_write_boundary.py` -- NEW: asserts every observed write during `init` resolves under the provisioned home
- `tests/integration/test_init_worktree.py` -- NEW, `@pytest.mark.slow`: end-to-end against a throwaway temp repo shaped like this one

## Tasks & Acceptance

**Execution:**
- [x] `ports/vcs.py`, `ports/fs.py` -- define the two Protocols -- the seam `cli/init.py` depends on, never a concrete adapter
- [x] `adapters/vcs_git.py` -- implement `GitVcs` over `subprocess` -- mirrors `scripts/bmad-loop-worktree`'s `run()`/`provision()` git calls
- [x] `adapters/fs_local.py` -- implement `LocalFs` -- mirrors `scripts/bmad-switch`'s marker/symlink primitives (atomic tmp-then-`os.replace` repoint)
- [x] `cli/init.py` -- `run_init(slug)`: validate shape via `core.policy._is_valid_project_slug`; resolve home path; reconcile worktree, marker, symlink each as `done|skipped|failed`; detect desync before writing; print the launch line `cd <home> && export BMAD_ACTIVE_PROJECT=<slug>`; build envelope
- [x] `cli/main.py` -- wire the `init` subparser
- [x] `core/findings.py`, `core/verdict.py` -- register + classify `MRS-INIT-001..004`
- [x] `tests/unit/test_vcs_git.py`, `test_fs_local.py`, `test_init.py` -- cover the I/O matrix above plus idempotent re-run
- [x] `tests/meta/test_ad11_write_boundary.py` -- write-boundary guard for this story's active surface (the home)
- [x] `tests/integration/test_init_worktree.py` -- one real end-to-end provision + re-run against a temp repo

**Acceptance Criteria:**
- Given a project slug with no existing loop home, when `marshal init <slug>` runs, then a git worktree exists at `<loop-home-root>/<slug>` on branch `loop/<slug>`, with its own active-project marker and `planning-artifacts` symlink agreeing with each other and independent of the main checkout and any other home
- Given the same slug and an already-converged home, when `marshal init <slug>` runs again, then every step reports `skipped`, nothing changes on disk, and exit code is 0
- Given a successful run, when it completes, then stdout includes a directly pasteable launch line exporting `BMAD_ACTIVE_PROJECT=<slug>`
- Given any I/O failure or a detected marker/symlink desync, when `marshal init` runs, then it reports the specific `MRS-INIT-*` finding and exits non-zero, and `main` is never checked out into the new worktree
- Given the `init` command's full write surface, when the AD-11 meta-test runs, then every observed write resolves under the provisioned home path

## Spec Change Log

## Review Triage Log

### 2026-07-30 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 1, medium 4, low 1)
- defer: 8: (high 0, medium 4, low 4)
- reject: 7: (high 0, medium 0, low 7)
- addressed_findings:
  - `[high]` `[patch]` A worktree git still registers via `git worktree list` but whose directory was deleted by hand (not via `git worktree remove` — this repo's own history: a failed removal still de-registers) was trusted blindly as "already provisioned," silently writing the marker/symlink into a phantom, non-functioning path. `cli/init.py`'s worktree step now checks `fs.is_dir(home)` before marking `skipped`, reporting a blocking `MRS-INIT-004` naming `git worktree prune` otherwise. New unit test `test_stale_worktree_entry_reports_finding_instead_of_skipping`.
  - `[medium]` `[patch]` `MRS-INIT-002` only checked the parent `_bmad-output/projects/<slug>/` directory, not `planning-artifacts` itself, so a project missing that subdirectory passed the gate and the symlink step created a DANGLING link — a regression vs. `scripts/bmad-switch`'s own `repoint_links`, which validates each target directory before writing. Now checks `_bmad-output/projects/<slug>/planning-artifacts` directly. New unit test `test_project_dir_without_planning_artifacts_reports_mrs_init_002`.
  - `[medium]` `[patch]` A missing `git` executable raised a raw `FileNotFoundError` straight through `GitVcs`, contradicting the module's own "never lets a raw ... invocation escape this module" contract. `_run()` now wraps `FileNotFoundError` into `VcsCommandError`. New unit test `test_run_wraps_missing_git_executable`.
  - `[medium]` `[patch]` `subprocess.run()` had no `timeout=`, so a hung `git` process would block `marshal init` forever — unacceptable for a command meant to run unattended under bmad-loop. Added `timeout=30.0`, wrapping `subprocess.TimeoutExpired` into `VcsCommandError`. New unit test `test_run_wraps_a_hung_git_process`.
  - `[medium]` `[patch]` `branch_exists` used a bare `git rev-parse --verify <branch>`, which resolves a same-named TAG before a branch per git's own disambiguation order — a `loop/<slug>` tag with no matching branch would report a false "branch exists," making `add_worktree` attach to what it thinks is the existing branch. Fixed by verifying `refs/heads/<branch>` explicitly in `branch_exists` (the detection step). Empirically verified LIVE against a real repo that the actual attach call (`git worktree add <path> <bare-name>`) is separately safe against a branch/tag collision via the bare name (git recognizes the branch and checks it out non-detached, with only a warning) — a fully-qualified `refs/heads/<branch>` argument there was tried and found to instead force DETACHED HEAD, so that call site deliberately keeps the bare name. New unit tests `test_add_worktree_creates_a_new_branch_when_only_a_same_named_tag_exists` and `test_add_worktree_attaches_the_branch_even_when_a_same_named_tag_exists`.
  - `[low]` `[patch]` The CLI usage-error test for a missing `slug` positional only asserted "some stderr was produced," which would pass for any unrelated argparse usage error. Strengthened to assert the message names `slug`.

### 2026-07-30 — Follow-up review pass (review_loop_iteration 0, post-`done` re-review)
- intent_gap: 0
- bad_spec: 0
- patch: 13: (high 0, medium 6, low 7)
- defer: 1: (high 0, medium 1, low 0)
- reject: 2: (high 0, medium 0, low 2)
- addressed_findings:
  - `[medium]` `[patch]` The MRS-INIT-002 gate validated the MAIN CHECKOUT's working tree while the symlink resolves inside the HOME's own checked-out tree (minted from `main` or a pre-existing `loop/<slug>` branch) — an uncommitted brand-new project passed the gate and init exited 0 having created a DANGLING symlink. Added a blocking in-home gate after the worktree step probing `home/_bmad-output/projects/<slug>/planning-artifacts` (MRS-INIT-004, both mint and attach paths); the pre-flight stays as a cheap fail-fast with its inaccurate "on main" message corrected to "in the main checkout". New tests `test_project_missing_from_home_tree_blocks_before_symlink` + `test_project_missing_from_a_preexisting_home_tree_blocks_too`.
  - `[medium]` `[patch]` The flat 30s subprocess timeout could SIGKILL `git worktree add` mid-checkout on a large repo (this one is a staged-recipes fork), leaving a registered-but-partial worktree a re-run then blesses as converged. Split into two tiers (`_GIT_TIMEOUT_S=30` for queries, `_GIT_CHECKOUT_TIMEOUT_S=600` for the tree-populating add); an add timeout now names `git worktree remove --force` + `git worktree prune` in its message — partial state itself stays as-is per this spec's own edge-case matrix (never auto-cleaned). New test `test_add_worktree_timeout_names_the_cleanup_commands`.
  - `[medium]` `[patch]` A relative `BMAD_LOOP_HOME_ROOT` split the two writers: `git -C <repo_root>` resolved the home against the repo root while `LocalFs` resolved against the CWD — exit 0 over a split-brain home. `_loop_home_root` now anchors a relative override to the CWD once, so every consumer sees one absolute path. New test `test_relative_loop_home_root_is_anchored_absolute`.
  - `[medium]` `[patch]` A present-but-unparseable `planning-artifacts` symlink target (absolute path, wrong depth — evidence of hand configuration) bypassed the MRS-INIT-003 desync block, whose condition required BOTH slugs to parse, and was then silently repointed — exactly the overwrite the code exists to refuse. Now blocks with MRS-INIT-003 whenever a symlink exists whose target is not shaped `projects/<slug>/planning-artifacts`. New test `test_unparseable_symlink_target_blocks_as_desync`.
  - `[medium]` `[patch]` Environment failures escaped the envelope as raw tracebacks: `Path.cwd()` raises `OSError` when the invocation directory was deleted (routine around concurrent worktree teardown), and `Path.home()`/`expanduser` raise `RuntimeError` when HOME is unresolvable (cron/systemd — Marshal's own unattended context). Both now land as MRS-INIT-004. New tests `test_deleted_cwd_reports_mrs_init_004` + `test_unresolvable_home_reports_mrs_init_004`.
  - `[medium]` `[patch]` The integration test — the only end-to-end proof of both worktree ACs with the real adapters — was unreachable through the project's task surface: the default task excludes `slow` and no slow counterpart existed (pyforge-warden, the convention the pyproject comment cites, ships `pyforge-warden-test-corpus-oracle`). Added `pyforge-marshal-test-slow` to `pixi.toml`; runs green.
  - `[low]` `[patch]` `branch_exists` conflated every git failure with "branch absent" (`returncode == 0` only) — a held `index.lock` or corrupt refs sent `add_worktree` down the mint-new-branch path, masking the real cause. `--verify --quiet` exit 1 is now "absent"; any other exit raises `VcsCommandError`. New test `test_branch_exists_raises_on_a_real_git_failure`.
  - `[low]` `[patch]` Three adapter exception-domain leaks closed: `read_text` let `UnicodeDecodeError` (a `ValueError`, outside the `OSError` catch) escape on a corrupt marker; `_run` let it escape on git output undecodable in the process locale (now `errors="replace"`); pathlib on the declared 3.12 floor propagates `PermissionError` from `is_dir` and from `read_symlink_target`'s `is_symlink()` probe (now suppressed-to-False / wrapped into the port's error). New tests `test_read_text_wraps_undecodable_bytes`, `test_run_replaces_undecodable_git_output`, `test_is_dir_false_on_unsearchable_ancestor`.
  - `[low]` `[patch]` A stale temp file from a crashed, pid-recycled run wedged `write_text_atomic` permanently (`O_EXCL` → `FileExistsError` on every retry, no self-heal) while `_tmp_sibling`'s docstring claimed the collision impossible. Any pre-existing file at the tmp name is now unlinked before the open (safe: pid+tid names cannot belong to a live writer) and the docstring states the real invariant. New test `test_write_text_atomic_survives_a_stale_temp_file`.
  - `[low]` `[patch]` `FsWriteError` was raised by the READ paths too, producing self-contradicting messages ("reading marker/symlink state: ... FsWriteError") and an API wart Story 1.5 would inherit — renamed to `FsError` across the package while the surface is one story old.
  - `[low]` `[patch]` Slug shapes valid per the shared shape check but invalid as a git branch-name component (`x.lock`, `.foo`, `foo.`, `a..b`) died later as an opaque MRS-INIT-004 carrying raw git stderr. A git-ref constraint check on TOP of the shared check (not a second slug regex — the spec's single-shape-check rule holds) now rejects them pre-I/O as MRS-INIT-001. New parametrized test `test_git_ref_invalid_slug_shapes_report_mrs_init_001`.
  - `[low]` `[patch]` The module docstring claimed every envelope's `data.steps` reports all three steps, but the pre-provisioning gates (MRS-INIT-001/-002, repo-root failure) exit before `steps` exists — a JSON consumer coded to the docstring would KeyError on exactly the failure envelopes it most needs. Docstring restated.
  - `[low]` `[patch]` The AD-11 meta-test docstring implied the real adapter could satisfy "every observed write resolves under the home", which a real `git worktree add` cannot (the new branch ref and `$GIT_DIR/worktrees/<id>` admin data land in the main repo's `.git`). Restated the guarded invariant as: every FS-port write plus the worktree TARGET path land under the home; git-internal bookkeeping is deliberately exempt.

### 2026-07-30 — Follow-up review pass 2 (post-`done` re-review of the full baseline diff)
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 0, medium 2, low 4)
- defer: 1: (high 0, medium 1, low 0)
- reject: 10: (high 0, medium 0, low 10)
- addressed_findings:
  - `[medium]` `[patch]` `repoint_symlink_atomic`'s refuse-to-clobber guard (and the except-block cleanup probe) sat OUTSIDE the `OSError → FsError` translation, so on the 3.12 floor an unsearchable ancestor — or `path.exists()` following the symlink into an unreadable target — escaped as a raw `PermissionError` traceback past `run_init`'s typed handlers, violating the spec's "no bare exception escapes the CLI handler" constraint (the exact pathlib class this story already fixed in `read_symlink_target`/`is_dir`). Guard moved inside the try, probe order swapped to `not is_symlink() and exists()` so a symlink never gets followed, cleanup probe made non-raising. New test `test_repoint_symlink_atomic_wraps_an_unsearchable_ancestor`.
  - `[medium]` `[patch]` `_run` wrapped only `FileNotFoundError` and `TimeoutExpired`; a `PermissionError`/ENOEXEC `OSError` from launching git (broken shim, corrupt binary) propagated raw through `GitVcs` and out of the CLI, contradicting the module's own never-escapes contract. Added a general `except OSError` wrap. New test `test_run_wraps_a_git_launch_permission_error`.
  - `[low]` `[patch]` `_run` decoded git output with the process-locale codec (`text=True` without `encoding=`): under a non-UTF-8 locale (cron/systemd — Marshal's own unattended context) a valid UTF-8 worktree path degraded to replacement characters, corrupting the reconcile comparison into a false MRS-INIT-004 on a converged home — and `test_run_replaces_undecodable_git_output`'s `"�"` assertion itself only held under a UTF-8 locale. Pinned `encoding="utf-8"`; the test is now locale-independent.
  - `[low]` `[patch]` The launch line embedded the home path unquoted, so a `BMAD_LOOP_HOME_ROOT` override containing a space produced a line that word-splits on paste — failing the "directly pasteable" AC (this was also sitting in the deferred-work ledger from the first pass; fixed now rather than re-deferred since it is a one-line `shlex.quote`). New test `test_launch_line_quotes_a_home_path_with_spaces`.
  - `[low]` `[patch]` A `git worktree list --porcelain` block carrying a `branch` line but no `worktree` line (a worktree path containing a blank line splits one block in two) raised a raw `KeyError` out of `worktree_path_for_branch` instead of the port's error. Now raises `VcsCommandError`. New test `test_worktree_path_for_branch_raises_on_a_block_without_worktree_line`.
  - `[low]` `[patch]` Two test names still carried the pre-rename `fs_write_error` spelling after the first follow-up pass's `FsWriteError → FsError` rename — the exact self-contradicting-naming wart that rename existed to eliminate. Renamed to `..._fs_error_...`.

**Why port `scripts/bmad-loop-worktree` + `scripts/bmad-switch` rather than shell out to them.** Marshal's AD-11 write-boundary meta-test needs every write to route through its own `FsPort`/`VcsPort` so it can be asserted against; a subprocess call to an external script is an opaque write Marshal can't observe or classify into `MRS-INIT-*`. The scripts remain the design reference (their comments already carry the hard-won rationale — path-length panic mitigation for the `~/.bmad-loops` root, symlink-before-marker ordering), not a runtime dependency.

**Scope boundary vs. Story 1.5.** `_bmad-output/implementation-artifacts` (Tier-3) is deliberately left untouched by this story — `scripts/bmad-switch`'s `ensure_tier3_backlink` is Story 1.5's `AD-11`/`FR-3` surface, gated to land immediately after this one per epics.md's Cross-Story Dependencies. A fresh home has only `planning-artifacts` symlinked until 1.5 lands.

## Verification

**Commands:**
- `pixi run -e pyforge-marshal pyforge-marshal-test` -- expected: all unit + meta tests pass, `-m "not slow"` excludes the new integration test by default
- `pixi run -e pyforge-marshal pyforge-marshal-test-slow` -- expected: the integration test passes against a real throwaway repo
- `pixi run -e pyforge-marshal marshal init <existing-project-slug>` run twice in a scratch clone -- expected: second run reports all `skipped`, exit 0

## Auto Run Result

Status: done (second follow-up review pass, invoked on the `done` spec per `followup_review_recommended: true`)

**Summary:** Fresh adversarial + edge-case review of the full baseline diff (`e868b607` → `30045b80`). No intent gaps, no spec defects — the intent contract and code architecture held. Six findings patched (2 medium, 4 low), all localized hardening of the two new adapters plus the launch line; one finding deferred to the ledger; ten rejected as noise or previously-adjudicated design. Committed as `2cd302bfbb`.

**Files changed this pass:**
- `adapters/fs_local.py` — `repoint_symlink_atomic`'s clobber guard + cleanup probe moved inside the `OSError → FsError` translation (raw `PermissionError` no longer escapes the CLI); probe order swapped so the symlink is never followed
- `adapters/vcs_git.py` — `_run` wraps generic launch `OSError` (EACCES/ENOEXEC) and pins `encoding="utf-8"`; `worktree_path_for_branch` raises `VcsCommandError` instead of a raw `KeyError` on an unparseable porcelain block
- `cli/init.py` — launch line `shlex.quote`d (directly-pasteable AC now holds for spaced home paths)
- `tests/unit/test_fs_local.py`, `test_vcs_git.py`, `test_init.py` — one new regression test per behavioral fix (4 new tests) + two stale `fs_write_error` test names renamed

**Review findings breakdown:** 6 patched (2 medium exception-escape contract violations, 4 low), 1 deferred (the slow integration suite is wired into no automated gate — needs an orchestrator-owned placement decision; new ledger entry appended), 10 rejected (previously-adjudicated design trade-offs, spec-scoped Story-1.5 deferrals, and no-realistic-trigger boundary cases).

**Follow-up review recommendation:** false — all fixes are narrow exception-path wraps, an encoding pin, quoting, and test renames; no happy-path behavior, API, or data-shape change.

**Verification:** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` → 533 passed (was 528; +5 new, 1 deselected). `pixi run --frozen -e pyforge-marshal pyforge-marshal-test-slow` → 1 passed.

**Residual risks:** the deferred-work ledger carries the known residuals — no last-resort `except Exception` clamp in `cli/main.py` (Story 1.1/1.3 spine decision), the untested default `~/.bmad-loops` fallback, no total-path-length guard, the duplicated `_git` test helper, and the unwired slow suite added this pass. A home provisioned before Story 1.5 lands intentionally carries only the `planning-artifacts` symlink (documented Scope boundary).

