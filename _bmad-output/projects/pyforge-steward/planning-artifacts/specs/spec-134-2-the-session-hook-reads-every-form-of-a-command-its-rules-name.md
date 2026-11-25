---
title: '134.2: The session hook reads every form of a command its rules name'
type: 'fix'
created: '2026-11-25'
status: 'done'
story: 134-2-the-session-hook-reads-every-form-of-a-command-its-rules-name
spec: spec-pyforge-steward
difficulty: 'hard'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - '.claude/hooks/pre-shell.py'
  - '.claude/hooks/post-tool-call.py'
  - '.claude/settings.json'
  - 'tests/scripts/test_pre_shell_hook.py'
  - 'tests/scripts/test_session_denial_forms.py'
  - '.claude/skills/conda-forge-expert/tests/unit/test_provenance_hook.py'
  - '.claude/skills/conda-forge-expert/CHANGELOG.md'
  - '.claude/skills/conda-forge-expert/SKILL.md'
  - '_bmad-output/projects/pyforge-marshal/planning-artifacts/PRD.md'
  - '_bmad-output/projects/pyforge-marshal/planning-artifacts/index.md'
  - '_bmad-output/projects/pyforge-marshal/planning-artifacts/source-tree-analysis.md'
  - '_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture-bmad-infra.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - docs/governance/guild-roster.json
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `DW-steward-review-2026-11-24-4`. A reviewer probed `.claude/hooks/pre-shell.py` and reported forms of refused commands the hook lets through; the session lead did not re-run the probes. The row's evidence is `.claude/hooks/pre-shell.py:465-488,585,643,686,912,954-957,1006-1007,1091,1103,1362-1428,1464-1468,1527,1619-1621`.

1. **A prefix skips a matcher anchored on the first token.** An environment assignment (`FOO=1 git commit ...`), `env`, `command`, `time`, a subshell (`( pixi add x )`) or an absolute path to the executable (`/usr/bin/git`, `/opt/pixi/bin/pixi`) carries the command past `git-commit-guardrail`, `pixi-add-or-update`, `uv-run-outside-repo-root`, `outward-github-write` and `gh-pr-merge-squash`.
2. **`gh api` is read only in one spelling.** `-X` or `--method` after the endpoint, `--method=DELETE`, and the field flags in their `=` forms (`--field=`, `--raw-field=`, `-f=`, `-F=`) pass the outward-write and protected-ref rules.
3. **Four deletion forms pass the protected-ref rules:** `git fetch -p -P`, `git branch -Df`, `git update-ref --no-deref -d` and `git push origin +:<ref>`.
4. **A commit message on stdin passes the attribution check:** `git commit -F -` fed by a here-document or a pipe the command text carries.
5. **`.claude/hooks/post-tool-call.py` is registered by no harness** (carried from `DW-steward-review-2026-11-24-2`, defect 12): `grep -c post-tool-call .claude/settings.json .cursor/hooks.json` prints 0 for both.

The row also names two **false denials**: a redirection read as a remote, and any token ending `submit_pr.sh`. Fixing either loosens a safety hook. They are **not in this story** and stay open on the row for the operator.

**Approach:** Tightening only. Write each reported form first as a case in `tests/scripts/test_session_denial_forms.py` (or `test_pre_shell_hook.py`) that fails on the unchanged hook; a form the unchanged hook already denies is recorded as not a defect. Then:

- Normalise every subcommand once, before any rule reads it: strip leading environment assignments (the hook's own `_strip_env_prefix`), strip the wrappers `env` (with its own options and assignments), `command`, `time`, `nice`, `nohup` and `exec`, unwrap a subshell or a brace group, and reduce the executable to its basename. Every matcher reads the normalised tokens; git is read through the existing `_git_subcommand_tokens`, so `git -c x=y commit` and `git -C dir commit` are one form.
- Read the HTTP method of `gh api` wherever it stands (`-X VALUE`, `-XVALUE`, `--method VALUE`, `--method=VALUE`) and treat any field flag, in either spelling, as a write unless the method is an explicit `GET`, as the rule's reason already says.
- Recognise the four deletion forms in the protected-ref and unreachable-ref rules.
- Where the command text carries the commit message on stdin (a here-document or a here-string on the same command, or `printf`/`echo` piped into `git commit -F -`), read it for the attribution check. A message the text does not carry cannot be read by a `PreToolUse` hook; the `commit-msg` hook remains the guarantee for it, and the Spec Change Log says so.
- `.claude/hooks/post-tool-call.py`: this story expects it to be **retired with its test**. It only observes (it posts the edited file's path to `http://localhost:<port>/api/provenance/call` and cannot deny), but the port comes from a `<hash>-provenance-port.txt` file that no file in the tree writes and no server in the tree serves, so a registered hook would exit 1 with "Could not determine API port" after every edit. The implementer confirms that by search. If a server is found in the tree, the hook is registered instead as a `PostToolUse` hook on `Edit|Write|NotebookEdit` in `.claude/settings.json`. Retiring it removes `.claude/skills/conda-forge-expert/tests/unit/test_provenance_hook.py`, which is an edit under the conda-forge-expert skill: invoke that skill first and close with its `CHANGELOG.md` entry and version bump. The marshal planning pages that say the file exists (`PRD.md` FX.8, `index.md`, `source-tree-analysis.md`, `architecture-bmad-infra.md`) are corrected to say it was retired, with the date.

Ledger key: `134-2-the-session-hook-reads-every-form-of-a-command-its-rules-name`.

### Living CAP citations

- spec-pyforge-steward CAP-5 (the closed `session_denials` list and its parity check) and CAP-165 (the protected refs); each realized, no text change; no AD moves.

## Boundaries & Constraints

**Always:**
- Reproduce before fixing: one failing case per reported form, written and run on the unchanged hook first.
- Keep every case the two test modules pass today passing: a command the hook allowed and the tests pin as allowed stays allowed.
- Keep one script for both harnesses, standard library only, and keep the run-time assertion that the matchers equal `session_denials`.
- Deny with the reason the rule already gives; a reason's text does not change.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never add a rule to, or remove one from, `docs/governance/guild-roster.json` `session_denials`; that file is not in this surface.
- Never loosen a matcher: the two false denials the row names are not touched, and no change in this story makes the hook allow a command it denies today.
- Never run a refused command to test the hook; the tests feed the hook its JSON payload on stdin.
- Never register `post-tool-call.py` while nothing in the tree serves its endpoint.
- Never edit `AGENTS.md` § *Session guardrails*: the list of what the hook covers does not change.

## Acceptance Criteria

**Given** `DW-steward-review-2026-11-24-4` reports, from a reviewer's probes, that matchers anchored on the first token are skipped by an environment assignment, `env`, `command`, `time`, a subshell or an absolute path (commit on `main`, `pixi add` and `pixi update`, `uv run` off the root, outward `gh`, a squash merge); that `gh api` with `-X` after the endpoint or a `--field=` form passes the outward-write rule; that `--method=DELETE`, `git fetch -p -P`, `git branch -Df`, `git update-ref --no-deref -d` and `git push origin +:<ref>` pass the protected-ref rules; that a commit message on stdin passes the attribution check; and that `.claude/hooks/post-tool-call.py` is registered by no harness
**When** each reported form is first written as a test case that fails on the unchanged hook, and then every subcommand is normalised once before any rule reads it (assignments and wrappers stripped, the executable reduced to its basename, git read through the existing subcommand helper), the method and field flags of `gh api` are read wherever they stand, the listed deletion forms are recognised, and a commit message the command text carries on stdin is read for the attribution check
**Then** every reported form is denied with the reason its rule already gives, every command the hook's tests allowed before is still allowed, and the hook's matchers still equal the twenty ids of `session_denials`, which does not change
**And** the two false denials the row names (a redirection read as a remote; any token ending `submit_pr.sh`) are not changed by this story and stay open on the row for the operator, since each loosens a safety hook
**And** `.claude/hooks/post-tool-call.py` is retired with its test, because it posts to a local provenance server no file in the tree starts and would fail after every edit if a harness ran it; should the implementer find such a server, it is registered as a `PostToolUse` hook instead, and the story spec records which and why

- **AC1 — Every reported form is a named case, and the hook's two test modules pass.** The cases cover, for each of the five first-token rules, each of the six prefixes (assignment, `env`, `command`, `time`, subshell, absolute path); the four spellings of the `gh api` method after the endpoint and the four `=` field forms; the four deletion forms; and a commit message carried on stdin. Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_pre_shell_hook.py tests/scripts/test_session_denial_forms.py -q
  ```

- **AC2 — The denial list did not move.** Expected: exit 0 (no difference from the base of the branch).

  ```bash
  git diff --quiet origin/main -- docs/governance/guild-roster.json
  ```

- **AC3 — The hook still matches the list.** The hook is fed one harmless Bash payload; it exits 0 only when its matchers equal the roster's ids. Expected: exit 0.

  ```bash
  printf '%s' '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"true"},"cwd":"."}' | python3 .claude/hooks/pre-shell.py
  ```

- **AC4 — The unregistered hook has one outcome.** Either the file and its test are gone, or the file is registered. Expected: exit 0.

  ```bash
  { ! test -e .claude/hooks/post-tool-call.py && ! test -e .claude/skills/conda-forge-expert/tests/unit/test_provenance_hook.py; } || grep -q "post-tool-call.py" .claude/settings.json
  ```

- **AC5 — The scripts suite passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test
  ```

- **AC6 — Nothing tracked names a file that is gone.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild governance-currency
  ```

- **AC7 — Every reported form has its line.** For each of the five numbered items of the Problem, the Spec Change Log holds one line: "reproduced and fixed" with the case that failed on the unchanged hook, or "not a defect" with the case that showed the unchanged hook already denies it; and one line for the two false denials reading "left open". Expected: prints 6, exit 0.

  ```bash
  grep -c -E "(item [1-5]|false denials): (reproduced and fixed|not a defect|retired|registered|left open) - " _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-134-2-the-session-hook-reads-every-form-of-a-command-its-rules-name.md
  ```

- **AC8 — The row says what closed and what did not.** `DW-steward-review-2026-11-24-4` carries a `resolution:` line naming this story and the two false denials it leaves open, and its `status:` stays `open` for them. Expected: prints 1, exit 0.

  ```bash
  grep -c -E "^  resolution: 2026-[0-9-]+, steward Story 134\.2 " _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-5 and CAP-165 (each realized, no text change); no AD moves.
- Dream: `docs/dreams/pyforge-steward.md`, the 2026-11-25 entry (the open rows close, and one verb says whether a machine is ready); operator ruling of 2026-11-25: "fix all these issues / left open items".
- Epic: Epic 134, minted with this story.
- Ledger key: `134-2-the-session-hook-reads-every-form-of-a-command-its-rules-name`.
- Deferred-work row: `DW-steward-review-2026-11-24-4` (closed in part: the two false denials stay open for the operator).
- Surface: `marshal-policy.toml` `[epic_surfaces]."134"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry and the operator's ruling of the same date. Not implemented. Read at mint: `.claude/hooks/post-tool-call.py` (115 lines) posts `{"file_path", "timestamp"}` to `/api/provenance/call` on a port read from `<md5 of CLAUDE_PROJECT_DIR>-provenance-port.txt` in the temporary directory and returns 1 on any failure; a search of the tree for `provenance-port` and `api/provenance` finds the hook, its test and four marshal planning pages, and no writer of the port file and no server.
- 2026-11-25: implemented, uncommitted, on branch `open-rows-and-onboarding-2026-11-25`. Every case is `tests/scripts/test_pre_shell_hook.py::test_134_2_*`, data on the hook's stdin; no refused command was run. On the unchanged hook 170 of the 306 new cases failed and 136 passed; on the changed hook the module's 513 cases pass. `tests/scripts/test_session_denial_forms.py` and `.claude/settings.json` are unchanged.
- 2026-11-25: item 1: reproduced and fixed - `test_134_2_prefixed_git_commit_on_main_denied`, `..._pixi_add_or_update_denied`, `..._uv_run_outside_repo_root_denied` and `..._outward_github_write_denied` failed on the unchanged hook for every prefix (assignment, `env`, `command`, `time`, subshell, absolute path), the one exception being the assignment before outward `gh`, which the unchanged hook already denied. For `gh pr merge --squash` only the absolute path, the glued subshell `(gh ...` and an assignment before `bash -c` failed; the other prefixes were already denied (`test_134_2_prefixed_gh_pr_merge_squash_denied`), since that rule reads its tokens anywhere. `git -c k=v commit`, `git -C dir commit` and `git --no-pager commit` failed too (`test_134_2_git_global_options_before_commit_denied`). Fix: `normalised_subcommands` adds each subcommand's normal form beside the tokens as written (assignments kept in front, `env`/`command`/`time`/`nice`/`nohup`/`exec`/`timeout`/`sudo`/`builtin` taken off, a subshell or brace opener taken off, the executable reduced to its basename); the first-token rules read past the assignments (`_command_tokens`); the commit rule reads git through `_git_subcommand_tokens` and judges the checkout `-C` names.
- 2026-11-25: item 2: reproduced and fixed - `test_134_2_gh_api_write_read_wherever_it_stands` failed for `-X POST`, `-XPOST`, `--method POST` and `--method=POST` after the endpoint, for `-XPOST` before it, and for `--field=`, `--raw-field=` and `--input=`. `-f=` and `-F=` were already denied (not a defect: the glued-flag check reads them). Fix: `_gh_api_methods` reads every method the line names; the three `=` field forms count as fields. An explicit `GET` is recognised exactly as before, so `gh api -XGET ... -f q=x` is still denied.
- 2026-11-25: item 3: reproduced and fixed - `test_134_2_protected_ref_deletion_forms_denied` failed for `gh api ... --method=DELETE` and `-X=DELETE`, `git fetch -p -P` (and `-pP`, `--prune -P`, `-p --prune-tags`), `git branch -Df` (and `-fD`, `-f -D`, `-r -d`, `--force --delete`), `git update-ref --no-deref -d` (and `-m <reason> -d`), `git push origin +:<ref>`, `git push -fd`, `git tag -f -d`, and every protected form behind `git -c k=v` or `/usr/bin/git`; `test_134_2_unreachable_ref_deletion_forms_denied` failed for the same forms on an unmerged branch. `-X DELETE`, `-XDELETE` and `--method DELETE` after the endpoint were already denied. Fix: `_branch_or_tag_deletions` reads the delete flag wherever it stands and in a bundle, for both rules; `_git_subcommand_tokens` skips the value of `-c`, `--namespace` and `--config-env`, which it used to return as the subcommand.
- 2026-11-25: item 4: reproduced and fixed - `test_134_2_commit_message_on_stdin_read_for_attribution` failed for `git commit -F -` (also `--file=-`, `--file -`, `-aF -`, `-F /dev/stdin`) fed by a here-document, a here-string, `printf`, `echo` or `cat <<EOF`, and `test_134_2_commit_message_file_redirected_to_stdin_read` for `< file` and `cat file |`. `git commit -m'<message>'` in one token failed as well. Fix: `_stdin_text_in_command` reads what the command text carries. A message the text does not carry (stdin from another process, a file written by an earlier tool call and not named on the line) cannot be read before the command runs; the `commit-msg` hook in `.pre-commit-config.yaml` remains the guarantee for it. A message file is read only when it is a regular file, and only its first megabyte.
- 2026-11-25: item 5: retired - `.claude/hooks/post-tool-call.py` and `.claude/skills/conda-forge-expert/tests/unit/test_provenance_hook.py` are removed. Confirmed by search: `git grep -e provenance-port -e api/provenance` finds no writer of the port file and no server, only the hook, its test and planning pages. conda-forge-expert is 8.106.1 with its `CHANGELOG.md` entry; the four marshal planning pages say the hook was retired on 2026-11-25. The version bump also touched `config/skill-config.yaml` and `MANIFEST.yaml`, which carry the same version and are not in this story's surface.
- 2026-11-25: false denials: left open - a redirection read as a remote, and any token ending `submit_pr.sh`, are unchanged; each fix loosens the hook, so both stay on `DW-steward-review-2026-11-24-4` for the operator.
- 2026-11-25: same class, met while fixing and fixed with it: `nice`, `nohup`, `exec`, `time -p`, `{ ...; }`, `if ...; then <command>`, `! <command>`, `sleep 1 & <command>`, `FOO=1 bash -c '<command>'` and `env GH_REPO=<foreign> gh ...`; the prefixed forms of `guild-task-via-local-recipes` and `outward-package-submission`; `git -c k=v push <foreign>` for `outward-git-push`.
- 2026-11-25: tightening checked two ways. The pinned cases: `test_134_2_allowed_forms_stay_allowed_and_the_hook_exits_cleanly`, `..._documented_pushes_stay_allowed`, `..._commit_in_a_worktree_off_main_stays_allowed`, `..._git_dash_c_worktree_commit_from_the_primary_checkout_stays_allowed` and `..._merged_branch_and_tag_deletions_stay_allowed` hold `PYFORGE_PREFLIGHT_SKIP=1 git push origin <branch>`, `BMAD_ACTIVE_PROJECT=<slug> pixi run ...`, `git -C <worktree> commit`, `gh pr create --repo rxm7706/local-recipes ...`, `gh api` reads, and malformed input (`(`, `&`, `env -S`, an unbalanced quote) on both harnesses, exit 0 and no output. And a scratch comparison of the unchanged and changed hook over 25,968 commands (328 commands from the test module, 20 wrappers, 4 working directories): 0 commands the unchanged hook denied are allowed, 0 exceptions.
- 2026-11-25: left open, same class, not in the row: a command inside `$(...)` or backticks, `xargs <command>`, `eval`, a global flag between the executable and its verb (`pixi --quiet add`, `uv --quiet run`), and `cd <dir> && uv run`. `git --no-pager -C <dir> push` is still judged at the session's directory, as before. Each wants its own row on the ledger.
- 2026-11-25: verification. AC1 exit 0 (513 passed, 1 skipped in `pyforge-ci`; the skip is `test_session_denial_forms.py`, whose 17 cases pass in `pyforge-guild`). AC2, AC3, AC4, AC6 exit 0; AC7 prints 6. AC5 exit 1: 1,264 passed, 2 failed, both `tests/scripts/test_tea_playwright_check.py`, because `test-architecture.md` has no row yet for Stories 134.1 to 135.3 and mason 42.1; that file is the lead's. AC8 is not met here: the ledger is the lead's to write. `ruff check` on the hook and its test: exit 0. Scribe's `test_instruction_surface_parity.py`: 49 passed. Steward's `tests/unit/test_estate.py`, which loads the hook: 34 passed. The live session reads the primary checkout's copy of the hook, so none of this takes effect until the branch lands.
- 2026-11-25: review findings closed, each test-first. (1) A write method beside an explicit GET: `gh api --method GET <foreign> -X DELETE`, `-X GET ... --method POST -f title=x` and six more orderings failed `test_134_2_gh_api_write_read_wherever_it_stands` on the hook as it stood; `_gh_api_is_write` now reads every method the line names before the explicit-GET check, so any write method anywhere makes the line a write (gh keeps the last value given). A bare explicit GET with fields (`-X GET ... -f q=x`) stays a read, as before. (2) A NUL in a `git -C` path raised ValueError out of `_git` (exit 2); `_git` and `_git_exit_code` now catch it and degrade as a missing directory does (`git -C /tmp/a<NUL>b commit -m x` and `... status` in `test_134_2_allowed_forms_stay_allowed_and_the_hook_exits_cleanly`). (3) The backreferencing here-document regex is replaced by `_heredoc_bodies`, one linear pass over the lines; an unterminated here-document now runs to the end of the text, as bash runs it, which reads more, never less. `test_134_2_here_document_scan_matches_the_old_pattern` holds it equal to the old pattern on every terminated case, `..._reads_more_never_less` holds every old body inside what it returns, `test_134_2_unterminated_here_document_reads_to_the_end` denies an unterminated attribution, and `test_134_2_many_unterminated_here_documents_scan_quickly` (10,000 openers each way) returns in 0.2 s against a 10 s bound. (4) `epics-regenerable-factory.md` E3.S9 says the hook was retired on 2026-11-25, worded as PRD.md FX.8. `guild-roster.json` and `.claude/settings.json` unchanged; no denial removed, narrowed or reordered; no rule added.
- 2026-11-25: second review finding closed, test-first: two NUL paths still raised ValueError out of `os.path.realpath` (exit 2 with a traceback). `_is_loop_home` and the chain-write path matcher `_chain_path` now catch `(OSError, ValueError)`, so an unusable path degrades as a missing one does (judged no loop home; judged outside the checkout). `test_rm_rf_loop_home_path_with_nul_does_not_crash` and `test_chain_write_path_with_nul_does_not_crash` failed on the hook as it stood and pass now; each also holds that the same path without the NUL is still denied. No denial removed, narrowed or reordered; no rule added; `guild-roster.json` unchanged. `tests/scripts/test_pre_shell_hook.py`: 544 passed, exit 0; `ruff check --select E4,E7,E9,F` on the hook and its test: exit 0.
- 2026-11-25: closed. Implemented, independently reviewed against this spec, its findings applied and re-reviewed; the full local `pr-preflight` gates the PR that lands it (branch `open-rows-and-onboarding-2026-11-25`).
