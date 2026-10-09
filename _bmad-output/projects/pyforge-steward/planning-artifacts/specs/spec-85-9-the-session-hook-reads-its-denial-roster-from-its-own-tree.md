---
title: "85.9: The session hook reads its denial roster from its own tree"
type: 'fix'
created: '2026-10-09'
status: 'in-progress'
baseline_revision: 'f7ce163b6991281695ea93a121b5c96fad299cf9'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-63-3-one-deny-list-one-hook-the-guild-session-guardrails-are-enforced-not-asserted.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-85-8-an-agent-session-never-writes-outside-this-repository.md
  - .claude/hooks/pre-shell.py
  - .claude/settings.json
  - .cursor/hooks.json
  - docs/governance/guild-roster.json
  - tests/scripts/test_pre_shell_hook.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the session hook takes its matchers from the tree the script lives in and its roster from the tree of the
tool call's cwd. When the two trees sit at different revisions, the parity check that keeps them equal fails on every
tool call, and the session cannot run a command.

- **How the hook runs.** Claude Code runs `python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/pre-shell.py` on `Bash`,
  `Edit|Write|NotebookEdit` and the three `conda_forge_server` MCP submission tools (`.claude/settings.json:51`, `:60`,
  `:69`). `$CLAUDE_PROJECT_DIR` is the primary checkout on `main`, so `MATCHERS` (`pre-shell.py:1537`-`:1554`) is
  `main`'s.
- **Where the roster comes from.** `build_context` sets `ctx.repo_root = find_repo_root(cwd)` (`:130`).
  `find_repo_root` (`:271`) returns `git rev-parse --show-toplevel` in the payload's cwd and falls back to the hook's
  own tree (`Path(__file__).resolve().parents[2]`, `:276`) only when the cwd is not in a git repository. `main()`
  then calls `load_denial_rules(ctx.repo_root)` (`:1652`), which reads
  `<repo_root>/docs/governance/guild-roster.json` (`:1565`) and raises when its `session_denials` ids differ from
  `MATCHERS` (`:1579`-`:1588`). The top-level handler turns any exception into exit 2 (`:1669`-`:1677`), which blocks
  the tool call.
- **What broke.** On 2026-10-09 a session whose cwd was `.worktrees/dispatch-pyforge-mason-25.2`, 153 commits behind
  `main` with the roster from before Story 85.8, had every Bash, Edit and Write call refused with "session_denials in
  guild-roster.json and pre-shell.py's MATCHERS have drifted: declared-but-unimplemented=[]
  implemented-but-undeclared=['outward-git-push', 'outward-github-write', 'outward-mcp-submission',
  'outward-package-submission']". The session could leave the directory only through harness tools.
- **Reproduced on `20b7e853c3`.** Running this tree's hook with a Claude Code `Bash` payload for `ls`:
  - cwd in a fresh `git init` repository holding the roster from `fc68067136` (before 85.8): exit 2, the message
    above;
  - cwd in a fresh `git init` repository with no roster: exit 2, `FileNotFoundError` on
    `<cwd>/docs/governance/guild-roster.json`;
  - cwd in this worktree: exit 0, no output.

  The reverse also fails: a worktree whose roster declares an id the hook script does not implement yet exits 2 with
  `declared-but-unimplemented=[…]`.
- **The second roster read.** `load_protected_deletion_prefixes` (`:642`, roster path `:645`) reads the roster's
  `protected_refs` through the same `ctx.repo_root`, from `match_protected_ref_deletion` (`:954`) and
  `match_unreachable_ref_deletion` (`:1003`). It falls back to the code floor (`refs/heads/main`, `refs/heads/loop/`)
  instead of raising, so today the drift crash comes first. If only the denial read moved, a worktree older than Story
  85.1 (no `protected_refs` key) would pass the parity check and then protect only the floor from deletion. Refs are
  shared by every worktree of a repository, so the list that protects them is the one beside the matchers, not the
  one in whichever checkout the cwd is in.
- **What stays cwd-relative, and why.** These read the checkout the command acts on, and none of them is part of the
  parity check:
  - `git_checkout_state` / `get_branch` / `is_worktree` (`:279`-`:300`): branch and worktree judgments, including the
    primary-checkout rule in `match_git_commit_guardrail` (`:519`);
  - `match_uv_run_outside_repo_root` (`:563`) and `match_direct_write_governed_path` (`:616`) with `is_tracked`
    (`:303`, called at `:625`): path checks;
  - `get_guild_tasks` (`:317`, called at `:454`): `pixi run` resolves tasks from the cwd's `pixi.toml`, so the
    guild-task rule must read the same file;
  - `_commit_msg_hook` (`:341`, called at `:531`): the `commit-msg` git hook that will judge the commit is the cwd
    tree's `scripts/commit_msg_hook.py`;
  - `_is_local_recipes_checkout` (`:1130`), which already compares the cwd's git common dir with the hook's own tree
    (`_hook_install_repo_root()`, `:1126`), as Story 85.8 wrote it.

**Approach:** both roster reads take the hook's own tree; nothing else moves.

- `main()` calls `load_denial_rules(_hook_install_repo_root())` instead of `load_denial_rules(ctx.repo_root)`.
- `match_protected_ref_deletion` and `match_unreachable_ref_deletion` call
  `load_protected_deletion_prefixes(_hook_install_repo_root())`.
- `load_denial_rules`, `load_protected_deletion_prefixes` and `load_protected_branch_prefixes` keep their
  `repo_root: Path` parameter, so `test_load_denial_rules_succeeds_against_the_real_repo`
  (`tests/scripts/test_pre_shell_hook.py:64`) and `test_protected_branch_prefixes_floor_when_roster_omits_loop`
  (`:586`) run unchanged. `Context.repo_root` and `find_repo_root` do not change.
- The module docstring's "THE CLOSED LIST" paragraph (`:20`-`:26`) gains one sentence: the roster is read from the
  tree the hook script lives in, so the matchers and the roster come from one revision whatever the cwd.
- **Cursor.** `.cursor/hooks.json` registers `python3 .claude/hooks/pre-shell.py`, a path relative to the directory
  Cursor starts the hook in. `Path(__file__).resolve()` resolves against that same directory when the module loads,
  and the hook never changes directory (no `os.chdir` in `pre-shell.py` on `20b7e853c3`). So the script that runs and
  the roster it reads always come from one tree, whichever tree that is, and the registration needs no change.
  Before this fix a Cursor session whose `cwd` (or first `workspace_roots` entry, `:121`-`:122`) named another
  checkout had the same drift as Claude Code.

Ledger key: `85-9-the-session-hook-reads-its-denial-roster-from-its-own-tree`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-5's session guardrails: Story 63.3's closed `session_denials`
  list, where the hook "asserts its matchers are exactly that list at every run" and a drift is "a loud failure, not a
  silent gap" (AGENTS.md § Session guardrails). The parity check is meant to catch a script and a roster that disagree
  within one revision. Comparing the script of one revision with the roster of another turns a correct hook into a
  blocked session. This fix keeps the check and gives it one revision to judge. It mints no CAP and changes no
  `SPEC.md` text.
- **Also read.** CAP-165 (FR-38): Stories 85.1 and 85.4 read the roster's `protected_refs` through
  `load_protected_deletion_prefixes`; its code floor and its union rule do not change.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag. A session guardrail behind a flag would
  allow silently, as Story 85.4 ruled.
- **Origin.** Seen 2026-10-09 in `.worktrees/dispatch-pyforge-mason-25.2`; reproduced on `20b7e853c3` (above). The
  station Dream's 2026-10-09 (hook roster) entry records it.

## Acceptance Criteria

- **(1) The hook decides from its own roster.** Given a fixture git repository (the existing `fake_repo` fixture)
  whose `docs/governance/guild-roster.json` declares every real `session_denials` entry except `pixi-add-or-update`
  and the four `outward-*` ids, When this repository's hook (`HOOK`) runs with the fixture as cwd Then a Claude Code
  `Bash` payload for `ls -la` exits 0 with empty stdout and stderr, and one for `pixi add numpy` is denied with the
  `pixi-add-or-update` reason exactly as the real roster (`REAL_ROSTER`) words it. The same holds for a Cursor
  `beforeShellExecution` payload.
- **(2) A newer cwd roster does not block either.** Given the fixture's roster declares every real entry plus one
  extra id (`not-yet-implemented`, `applies_to: bash`) When the hook runs `ls -la` with the fixture as cwd Then it
  exits 0 with empty stdout and stderr.
- **(3) A repository with no roster.** Given a `git init` directory under `tmp_path` with no `docs/` and no
  `pixi.toml` When the hook runs with it as cwd Then `ls -la` exits 0 with empty stdout and stderr, and
  `gh repo fork conda-forge/staged-recipes` is denied with the real `outward-github-write` reason (the rules loaded).
  The roster and `pixi.toml` writes in `test_outward_git_remote_add_allowed_in_unrelated_clone` (`:921`-`:922`),
  which existed only to keep the hook from crashing there, are removed and that test still passes.
- **(4) The deletion rules read their prefixes from the hook's own roster.** Given the fixture's roster with
  `protected_refs` emptied (`[]`) When the hook runs `git push origin --delete attempt-preserve/run-1` with the
  fixture as cwd Then it is denied with the `protected-ref-deletion` reason exactly as the real roster words it (the
  `refs/heads/attempt-preserve/` entry is not in the code floor).
- **(5) Drift in the hook's own tree still fails loud.** Given a copy of `pre-shell.py` at
  `<fixture>/.claude/hooks/pre-shell.py`, so the fixture is the copy's own tree:
  - with the fixture's roster missing `session_denials`, the copy exits 2 and stderr names `session_denials`;
  - with the fixture's roster lacking one declared id (`pixi-add-or-update`), the copy exits 2 and stderr contains
    `drifted`;
  - both hold when the cwd is a second repository whose roster is the real one, which shows the copy reads its own
    tree and not the cwd's.

  `test_missing_session_denials_fails_loud` (`:1155`) and `test_drifted_session_denials_fails_loud` (`:1167`) become
  these copied-hook tests; they keep their names and their exit-2 assertions.
- **(6) The floor test keeps testing the floor.** `test_protected_ref_deletion_floor_when_roster_omits_loop_prefix`
  (`:663`) runs the copy from (5) with the fixture's trimmed `protected_refs`, so the denial it asserts can come only
  from the code floor.
- **(7) Everything cwd-relative still is.** Every existing test in `tests/scripts/test_pre_shell_hook.py` that judges
  branch, worktree, primary checkout, `uv run` location, governed paths, guild tasks or commit attribution passes
  unchanged against the fixture as cwd. `Context.repo_root`, `find_repo_root`, `get_guild_tasks`, `_commit_msg_hook`,
  `is_tracked` and `_is_local_recipes_checkout` are unchanged in the diff.
- **(8) Nothing else moves.** The diff touches only `.claude/hooks/pre-shell.py` and
  `tests/scripts/test_pre_shell_hook.py`. `docs/governance/guild-roster.json`, `MATCHERS`, every matcher body except
  the two call sites, every reason, `.claude/settings.json`, `.cursor/hooks.json` and AGENTS.md are byte-identical.
  `test_matchers_match_the_real_declared_session_denials_exactly` (`:55`) and
  `tests/scripts/test_session_denial_forms.py` pass unchanged.
- **(9) Mutations fail the new tests.** Putting `ctx.repo_root` back into `main()`'s `load_denial_rules` call fails
  (1), (2) and (3). Putting it back into either deletion matcher's `load_protected_deletion_prefixes` call fails (4).
  Reading the roster from the cwd in the copied hook fails the cwd-independence half of (5).

## Boundaries & Constraints

**Always:**
- Change only `.claude/hooks/pre-shell.py` (the three call sites above, plus one sentence in the module docstring)
  and `tests/scripts/test_pre_shell_hook.py` (the new tests, the three converted tests, the removed workaround in the
  unrelated-clone test, and the module docstring's description of the subprocess layer).
- Keep the hook stdlib-only and runnable bare with `python3`, outside any pixi environment.
- Reuse `_hook_install_repo_root()`; add no second way of finding the hook's tree.
- Write every fixture, copy of the hook and second repository under `tmp_path`.

**Never:**
- Never change `docs/governance/guild-roster.json`: no entry, id, trigger, reason or `protected_refs` row moves.
- Never weaken the parity check, catch its `RuntimeError`, or make a missing or drifted own-tree roster allow
  silently: it still exits 2.
- Never move a cwd-relative judgment (the list in the Intent) to the hook's tree, and never read `pixi.toml` or
  `scripts/commit_msg_hook.py` from the hook's tree.
- Never add a rule, a count or a sentence to AGENTS.md § Session guardrails; the guardrail list stays sixteen.
- Never change `.claude/settings.json` or `.cursor/hooks.json`.
- Never edit `SPEC.md` or `sprint-status-ledger.yaml` by hand.

**At landing:** on `20b7e853c3` no Spec's surface in `scripts/.spec-surface-baseline.json` names
`.claude/hooks/pre-shell.py` or `tests/scripts/test_pre_shell_hook.py`; both are allowlisted (`.claude/**` and
`tests/**` in `scripts/spec_surface_allowlist.txt`). If `spec-surface-check` names a Spec at landing, append the
reconcile to it and stamp it scoped (AGENTS.md § Pre-PR item 5); otherwise no stamp is due.

## I/O & Edge-Case Matrix

| Hook's tree | cwd and its roster | Command | On `20b7e853c3` | After |
|---|---|---|---|---|
| primary checkout | the primary checkout | `ls` | allowed | allowed |
| primary checkout | worktree with the roster from before 85.8 | `ls` | exit 2, `drifted` | allowed |
| primary checkout | same | `gh repo fork conda-forge/staged-recipes` | exit 2, `drifted` | denied, `outward-github-write` |
| primary checkout | worktree whose roster declares an id the hook lacks | `ls` | exit 2, `drifted` | allowed |
| primary checkout | git repository with no roster (`/tmp/x-feedstock`) | `ls` | exit 2, `FileNotFoundError` | allowed |
| primary checkout | same, `origin` at conda-forge | `git push origin b` | exit 2, `FileNotFoundError` | denied, `outward-git-push` |
| primary checkout | not a git repository | `ls` | allowed (fallback to the hook's tree) | allowed |
| primary checkout | repository with the current `session_denials` and `protected_refs: []` | `git push origin --delete attempt-preserve/run-1` | not judged protected (floor only); `unreachable-ref-deletion`'s fetch remedy answers | denied, `protected-ref-deletion` |
| fixture (a copy of the hook) | anywhere | `ls`, own roster drifted | exit 2, `drifted` (when the cwd is the fixture) | exit 2, `drifted` (any cwd) |
| fixture (a copy of the hook) | anywhere | `ls`, own roster lacks `session_denials` | exit 2 | exit 2 |
| primary checkout | a main checkout (not a linked worktree) on `main` | `git commit -m x` | denied, `checkout` | denied, `checkout` (a cwd judgment) |
| primary checkout | a linked worktree whose tree has no `scripts/commit_msg_hook.py` | `git commit` with an attribution line | not denied for attribution | not denied for attribution (the cwd's commit-msg script, unchanged) |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-09 (hook roster) entry.
- Epic: Epic 85 (CAP-165; `in-progress` while Story 85.5 is `blocked`). This story fixes CAP-5's parity check.
- Ledger key: `85-9-the-session-hook-reads-its-denial-roster-from-its-own-tree`.
- Ledger status at mint: `backlog`.
- Deps: — (Story 85.8, whose roster exposed the drift, is `done`).
- Spec: `spec-pyforge-steward/.memlog.md` records the mint; `SPEC.md` untouched; no CAP minted.
- Governance: the roster, `MATCHERS` and every reason are unchanged; no `session_denials` entry is added or removed.
- Surface: `.claude/hooks/pre-shell.py` and `tests/scripts/test_pre_shell_hook.py`, both already in Epic 85's
  `[epic_surfaces]` entry (`.claude/hooks/pre-shell.py`, `tests/scripts/**`).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks (not a dispatch gate):**
- `pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_pre_shell_hook.py
  tests/scripts/test_session_denial_forms.py -q` — expected: pass.
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass (the CI `scripts-suite` twin).
- The reproduction, against the changed hook: `git init` a scratch repository, write the roster from `fc68067136`
  into it (`git show fc68067136:docs/governance/guild-roster.json`), and pipe
  `{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"ls"},"cwd":"<scratch>"}` into
  `python3 .claude/hooks/pre-shell.py` — expected: exit 0, no output. Repeat with a scratch repository that has no
  roster — expected: exit 0, no output.
- Mutation checks for AC (9), against a scratch copy of `pre-shell.py`.
- `pixi run -e pyforge-guild detectors-ci` — expected: no new finding against `main`.

## Spec Change Log

- No change yet.

## Review Triage Log

- No review has run yet.
