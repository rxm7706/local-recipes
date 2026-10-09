---
title: "85.8: An agent session never writes outside this repository"
type: 'feature'
created: '2026-10-09'
status: 'ready-for-dev'
baseline_revision: 'fc68067136997eb67751cfbc03f656442230581c'
flag-exempt: detector-or-gate   # a session guardrail; a gated guardrail allows silently
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-85-4-the-hook-denies-every-protected-ref-deletion-and-any-deletion-that-orphans-commits.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-85-6-every-command-a-session-denial-names-as-the-sanctioned-form-exists.md
  - .claude/hooks/pre-shell.py
  - .claude/settings.json
  - .cursor/hooks.json
  - docs/governance/guild-roster.json
  - tests/scripts/test_pre_shell_hook.py
  - tests/scripts/test_session_denial_forms.py
  - AGENTS.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the operator's rule that outward work is theirs alone is prose. The session hook enforces only one
outward form, so nothing stops an agent session pushing to a fork or feedstock, opening or commenting on another
repository's PRs, forking, or submitting and uploading packages.

- **The ruling.** On 2026-10-09 the operator ruled in chat: "everything mason does with these recipes is local — NO
  PRs to conda-forge or feedstocks — external repos". They approved this guard as the governance act that adds to
  the closed list.
- **What enforces it today.**
  - AGENTS.md § Policy says the same in prose: never open a feedstock, staged-recipes or upstream PR without an
    explicit ask (`AGENTS.md:30`), and never dispatch outward work without operator confirmation (`:31`).
  - `docs/governance/guild-roster.json`'s `session_denials` (12 entries) holds one outward form,
    `gh-pr-create-missing-repo` (`:359`-`:363`), matched by `match_gh_pr_create_missing_repo`
    (`.claude/hooks/pre-shell.py:532`).
  - `.claude/settings.json` pre-allows `Bash(git push)`, `Bash(git push *)` and `Bash(gh *)` (`:13`, `:14`, `:22`), so
    for every other form the hook is the only gate.
  - The hook runs only on `Bash` and `Edit`/`Write`/`NotebookEdit`: `detect()` (`pre-shell.py:80`) returns `other`
    for any other tool, and `main()` returns at `:1115`. So MCP tools never reach it.
- **The gaps**, each verified on `fc68067136`:
  - **`git push` to any destination but this repository.** `origin` is `https://github.com/rxm7706/local-recipes.git`.
    The loop-home remotes `marshal-home` and `mason-home` are local paths under `~/.bmad-loops/`. CFE `SKILL.md:2680`
    and `mason-feedstock-failure-remediation` `SKILL.md:277` instruct `git push https://github.com/<fork>/<feedstock>.git`.
  - **`git remote add` / `set-url`** of a foreign URL into this checkout's config, which every worktree and loop home
    shares.
  - **`gh repo fork` and `gh repo create`.**
  - **`gh pr` / `gh issue` / `gh release` write verbs aimed at another repository.** `mason-feedstock-platform-expansion`
    `SKILL.md:406` (`gh pr comment --repo conda-forge/<feedstock>-feedstock`) and `:437` (`gh pr create --repo
    conda-forge/<feedstock>-feedstock`), and CFE `SKILL.md:3311` (`gh pr edit --repo conda-forge/staged-recipes`) and
    `:3330` (`gh pr comment`). Only the `gh pr create` form is caught today.
  - **`gh api` writes to another repository's endpoints** (an explicit non-GET method, or fields without `-X GET`).
  - **Mason's outward verbs.** `recipe submit … --yes`, with or without `--prepare-only` (`pyforge-mason` `cli.py:128`,
    `:713`-`:740`), and `package ship … --yes` or `package --ship TARGETS --yes` (`:142`, `:832`). Every ship target is
    an upload: PyPI, TestPyPI, conda-forge or a named channel. Mason's console script is `mason` (`src/shared/packages/pyforge-mason/pyproject.toml:33`)
    beside `pyforge mason` and `python -m pyforge.mason`.
  - **CFE submission without `--dry-run`.** The pixi tasks `submit-pr` (`pixi.toml:1676`) and `prepare-pr` (`:1680`);
    the scripts `.claude/scripts/conda-forge-expert/submit_pr.py` and `prepare_pr.py` and their canonical
    `.claude/skills/conda-forge-expert/scripts/submit_pr.py` (`--dry-run` at `:424`); and `scripts/submit_pr.sh`, which
    has no dry run.
  - **`feedrattler`**, which always forks, pushes and opens a PR (`feedrattler/convert.py`: `create_fork`, `push`,
    `create_pull`; CFE G84, `SKILL.md:3719`-`:3727`).
  - **The `conda-smithy` subcommands that write to GitHub, CI or a token registry** (`conda_smithy/cli.py`):
    `register-github` (`:167`), `register-ci` (`:218`), `register-feedstock-token` (`:839`) and
    `update-anaconda-token` (`:996`, with aliases `rotate-anaconda-token`, `update-binstar-token` and
    `rotate-binstar-token`). `init`, `regenerate`/`rerender`, `recipe-lint`/`lint`, `ci-skeleton`,
    `generate-feedstock-token` and `azure-buildid` stay local.
  - **The `conda_forge_server` MCP tools** (`.claude/tools/conda_forge_server.py`): `submit_pr` (`:1268`) and
    `prepare_submission_branch` (`:1220`) with `dry_run` false, and `migrate_to_v1` (`:1379`), which runs feedrattler.
- **Repo code is out of the hook's sight.** Repo code that writes through `gh` runs as a subprocess the hook never
  sees: `scripts/apply_actions_policy.py --fix` (`--method PUT` on `repos/<slug>/actions/permissions`, `:79`) and
  marshal's `forge_gh.py` (`gh pr edit --repo`, `:272`, `:293`). A typed `gh api` write to
  `rxm7706/local-recipes` stays allowed.
- **No incident.** A 2026-10-09 audit found no agent-made external PR, push, fork, issue or comment since 2026-10-01.
  The external PRs were `regro-cf-autotick-bot`'s, and two fork pushes were the operator's web-UI edits. This story
  closes the gaps before they are used.

**Approach:** four `session_denials` entries, each with its matcher in `MATCHERS` (the startup parity check at
`pre-shell.py:1024` keeps the two equal). Each reason names what stays open, and says outward work is the operator's:
hand them the command and wait for explicit confirmation.

- **`outward-git-push`** (`applies_to: bash`):
  - It denies a `git push` (including `git -C <dir> push` and `--repo=<x>`) whose destination resolves to a network URL
    that does not name `rxm7706/local-recipes`.
  - The destination is resolved as git resolves it. An explicit remote name uses `git remote get-url --push <name>` in
    the command's directory. A URL argument is read as given. With no repository argument: `branch.<b>.pushRemote`,
    then `remote.pushDefault`, then `branch.<b>.remote`, then `origin`.
  - A local filesystem path or `file://` URL is allowed, which covers the loop homes. `rxm7706/local-recipes` is
    matched case-insensitively over https, ssh and scp-style URLs, with or without `.git`. A remote name that cannot be
    resolved is denied, naming `git remote -v`.
  - It also denies `git remote add <name> <url>` and `git remote set-url [--push|--add] <name> <url>` of such a URL
    when the command runs in this repository or one of its worktrees, because their config is shared. A clone
    elsewhere may add remotes, and its push is still judged by the rule above.
- **`outward-github-write`** (`applies_to: bash`):
  - It denies `gh repo fork`, `gh repo create` and `gh gist create|edit|delete` in any form.
  - It denies these write verbs when their target is not `rxm7706/local-recipes`:
    - `gh pr create|comment|review|edit|merge|close|reopen|ready`;
    - `gh issue create|comment|edit|close|reopen|delete|transfer|lock|unlock|pin|unpin`;
    - `gh release create|upload|edit|delete|delete-asset`.
  - The target is read from `--repo/-R`, else a `GH_REPO=` prefix, else a PR or issue URL argument, else the cwd
    checkout's remote as gh picks it: one marked `gh-resolved`, else the first of `upstream`, `github`, `origin`. With
    no checkout and no `--repo`, a write verb is denied.
  - It denies a `gh api` write: method `POST`, `PUT`, `PATCH` or `DELETE`, or any `-f/-F/--field/--raw-field/--input`
    without `-X GET`/`--method GET`. That covers:
    - an endpoint under `repos/<owner>/<repo>/` that is not `rxm7706/local-recipes` (a `{owner}/{repo}` placeholder
      resolves like a missing `--repo`);
    - any `repos/<owner>/<repo>/forks`;
    - `user/repos`, `orgs/<org>/repos` and `gists`.
  - Reads stay open everywhere (`view`, `list`, `checks`, `diff`, `status`, `gh api` GETs), and so does every write
    whose target is this repository.
  - `gh api graphql` is not matched: a mutation names node ids, not a repository. Denying every mutation would deny
    the review-thread replies `bmad-os-findings-triage` posts on this repository's own PRs (`SKILL.md:261`-`:276`).
    AGENTS.md names it instruction-only.
- **`outward-package-submission`** (`applies_to: bash`):
  - Mason, in all three spellings: `recipe submit … --yes`, and `package ship … --yes` or `package [--yes] --ship …
    --yes`, wherever `--yes` sits (before or after the verb).
  - CFE: the `submit-pr` and `prepare-pr` tasks and the `submit_pr.py` / `prepare_pr.py` scripts without `--dry-run`;
    `scripts/submit_pr.sh` always.
  - `feedrattler`, except `--help` or `--version`.
  - `conda-smithy` `register-github`, `register-ci`, `register-feedstock-token`, `update-anaconda-token` and its three
    aliases.
  - Every dry run stays open.
- **`outward-mcp-submission`** (`applies_to: mcp`, a new kind):
  - `detect()` returns `mcp` for a Claude Code `PreToolUse` whose `tool_name` starts `mcp__`, and `main()` evaluates
    `mcp` rules.
  - `.claude/settings.json` registers the hook on
    `mcp__conda_forge_server__submit_pr|mcp__conda_forge_server__prepare_submission_branch|mcp__conda_forge_server__migrate_to_v1`.
  - The matcher denies `submit_pr` and `prepare_submission_branch` unless `tool_input.dry_run` is `true`, and
    `migrate_to_v1` always.
  - Cursor joins only if its hook schema has a before-MCP event with a deny (checked live, as Story 63.3 checked
    `afterFileEdit`). If it has none, Cursor's MCP path is named instruction-only in AGENTS.md.
- **Reasons pass Story 85.6's check.** Every backticked span in the four reasons classifies under
  `tests/scripts/test_session_denial_forms.py`'s `_classify_span` (`:75`-`:100`) as third-party (`git …`, `gh …`) or
  resolves:
  - `pyforge mason recipe submit <recipe_dir>` and `pyforge mason package ship --to <targets>` parse in mason's parser
    (checked on `fc68067136` in `pyforge-ci`);
  - `pixi run -e local-recipes submit-pr <name> --dry-run` names a declared environment and task.

  Tool names and flags such as `dry_run`, `feedrattler` and `conda-smithy` appear without backticks, because an
  unclassified span fails the check.
- **The count moves from twelve to sixteen.** AGENTS.md § Session guardrails (`:162`, `:181`), the roster's
  `$comment_session_denials` (`:270`) and the hook's docstring (`:6`, `:15`, `:139`) name the new rules and the MCP
  registration. They also name what stays outside: `gh api graphql`, `curl` or a script calling GitHub's API, a git
  alias, and a harness with no hook.

Ledger key: `85-8-an-agent-session-never-writes-outside-this-repository`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- **Extends** `spec-pyforge-steward` CAP-5's session guardrails: Story 63.3's closed `session_denials` list, "the list
  is closed; adding to it is a governance act on `guild-roster.json`". Story 85.1 added an entry under CAP-5 the same
  way, by the operator's ruling of 2026-10-04. The operator's ruling of 2026-10-09 is this story's governance act.
- **No new CAP.** CAP-165 does not cover this: it is the protected-ref deletion contract and its rulesets, which this
  story leaves untouched. CAP-5's mechanism, a closed list extended by ruling, already covers a new denial, so nothing
  is minted.
- **Flag.** Exempt as `detector-or-gate`: a session guardrail behind a flag would allow silently, as Story 85.4 ruled.
- **Epic.** Epic 85 (CAP-165, session denials) is `in-progress` while 85.5 is `blocked`, so no reopen is needed.

## Acceptance Criteria

- **(1) Parity.** Given the roster after this story When the hook loads Then `session_denials` holds 16 entries,
  including `outward-git-push`, `outward-github-write`, `outward-package-submission` (`applies_to: bash`) and
  `outward-mcp-submission` (`applies_to: mcp`), and `MATCHERS` equals that set. Removing any one matcher fails
  `test_matchers_match_the_real_declared_session_denials_exactly` (`tests/scripts/test_pre_shell_hook.py:55`).
- **(2) Denied pushes.**
  - Given a fixture repository whose `origin` is `https://github.com/rxm7706/local-recipes.git`, plus a remote `fork`
    at `https://github.com/someone/staged-recipes.git` and a remote `home` at a local path.
  - Then these are denied with `outward-git-push`'s reason:
    - `git push fork add-recipe`;
    - `git push https://github.com/regro-cf-autotick-bot/x-feedstock.git HEAD:b`;
    - `git push git@github.com:conda-forge/x-feedstock.git b`;
    - `git -C <fixture> push fork b`;
    - `git push` on a branch whose `pushRemote` is `fork`;
    - `git remote add up https://github.com/conda-forge/staged-recipes.git` in the fixture;
    - `git remote set-url --push origin https://github.com/someone/local-recipes.git`.
  - And these are allowed:
    - `git push origin b`, `git push -u origin b` and `git push`, with `origin` as the default;
    - `git push home b`;
    - `git push https://github.com/RXM7706/local-recipes b`;
    - `git push ../other-clone b`;
    - `git remote add home2 /tmp/x`.
- **(3) Denied GitHub writes.** These are denied with `outward-github-write`'s reason:
  - `gh repo fork conda-forge/staged-recipes`, `gh repo create x` and `gh gist create f`;
  - `gh pr comment 1 --repo conda-forge/x-feedstock --body y` and `gh pr edit 1 -R conda-forge/staged-recipes`;
  - `gh pr review https://github.com/conda-forge/x/pull/1 --approve`;
  - `GH_REPO=conda-forge/x gh issue comment 1 -b y`;
  - `gh release create v1 --repo someone/x`;
  - `gh api -X POST repos/conda-forge/x/issues/1/comments -f body=y`;
  - `gh api repos/conda-forge/x/pulls -f title=t` (fields imply `POST`);
  - `gh api -X POST repos/rxm7706/local-recipes/forks`;
  - `gh api -X POST user/repos -f name=x`.

  These are allowed:
  - `gh pr create --repo rxm7706/local-recipes …`;
  - `gh pr comment 1 --body y` in this checkout;
  - `gh pr view 1 --repo conda-forge/x` and `gh pr checks 1 --repo conda-forge/staged-recipes`;
  - `gh api repos/conda-forge/x/pulls`;
  - `gh api -X GET search/issues -f q=x`;
  - `gh api -X PATCH repos/rxm7706/local-recipes/pulls/1 -f title=t`;
  - `gh api graphql -f query='mutation { … }'`;
  - `gh issue list --repo conda-forge/x`.

  A `gh pr create --repo conda-forge/x` stays denied, whether `gh-pr-create-missing-repo` or the new entry answers.
- **(4) Denied submissions.**
  - These are denied with `outward-package-submission`'s reason:
    - `pyforge mason recipe submit recipes/x --yes` and `mason recipe submit recipes/x --prepare-only --yes`;
    - `pyforge mason package --yes ship --to pypi` and `python -m pyforge.mason package --ship pypi-test --yes`;
    - `pixi run -e local-recipes submit-pr x` and `prepare-pr x`;
    - `python .claude/scripts/conda-forge-expert/submit_pr.py x`;
    - `bash scripts/submit_pr.sh x`;
    - `feedrattler x-feedstock someone`;
    - `conda-smithy register-github .` and `conda-smithy rotate-anaconda-token`.
  - These are allowed:
    - `pyforge mason recipe submit recipes/x`, `mason package ship --to pypi` and `pixi run -e local-recipes submit-pr
      x --dry-run`;
    - `feedrattler --help`;
    - `conda-smithy rerender` and `conda-smithy recipe-lint .`.
- **(5) Denied MCP calls.**
  - Given Claude Code `PreToolUse` payloads. `mcp__conda_forge_server__submit_pr` with `{"recipe_name":"x"}` or
    `"dry_run": false`, `prepare_submission_branch` likewise, and `migrate_to_v1` are each denied with
    `outward-mcp-submission`'s reason (`permissionDecision: deny`).
  - `submit_pr` with `"dry_run": true` is allowed, and so are `mcp__conda_forge_server__validate_recipe` and every
    non-`mcp__` tool.
  - `.claude/settings.json` registers the hook on the three tool names.
- **(6) The reasons resolve.** Given the four reasons When `tests/scripts/test_session_denial_forms.py` runs Then
  every backticked span is third-party or resolves, and the file's existing tests still pass.
- **(7) The instruction surfaces name the change.** AGENTS.md § Session guardrails names sixteen rules, the MCP
  registration, and the forms left outside (`gh api graphql`, `curl` or a script calling GitHub's API, git aliases,
  harnesses with no hook). The roster comment and the hook docstring say sixteen. `governance-currency` and scribe's
  `test_instruction_surface_parity.py` stay green.
- **(8) Mutations fail the new tests.** Each new matcher's denial tests fail when it returns `None`, and its
  allowed-form tests fail when it denies every command of its family.

## Boundaries & Constraints

**Always:**
- Change only these paths:
  - `docs/governance/guild-roster.json`, adding four entries and updating the count in its comment;
  - `.claude/hooks/pre-shell.py`, adding four matchers, the `mcp` kind and URL/remote resolution, stdlib only;
  - `.claude/settings.json`, adding the MCP `PreToolUse` registration;
  - `.cursor/hooks.json`, only if Cursor has a before-MCP deny;
  - `tests/scripts/test_pre_shell_hook.py`;
  - AGENTS.md § Session guardrails.
- Resolve remotes and targets with local `git` reads only. Make no network call from the hook.
- Keep every existing entry's id, trigger, reason and matcher unchanged.

**Never:**
- Never deny a read: `gh … view|list|checks|diff|status`, a `gh api` GET, `git fetch`/`clone`/`pull`.
- Never deny a write to `rxm7706/local-recipes` or a local path.
- Never add `graphql`, `curl` or a generic network matcher. The list stays closed and precise; those stay named
  instruction-only.
- Never touch the CFE or mason skill text that instructs outward steps (CFE `SKILL.md:2680`, `:3311`, `:3330`;
  `mason-feedstock-platform-expansion` `:406`, `:437`; `mason-feedstock-failure-remediation` `:277`). Rewording them to
  hand the operator the command is mason's chain: CFE edits carry the retro and semver rule. It is named here as a
  follow-up.
- Never edit `SPEC.md` or `sprint-status-ledger.yaml` by hand.

**At landing:** the roster, the hook and AGENTS.md sit in several Specs' surfaces (`spec-pyforge-steward`,
`spec-pyforge-scribe` for AGENTS.md, and others `spec-surface-check` names). Append the reconcile to each named Spec,
then one scoped stamp each (AGENTS.md § Pre-PR item 5).

## I/O & Edge-Case Matrix

| Command | Verdict |
|---|---|
| `git push origin feature` in this checkout | allowed |
| `git push marshal-home loop/x` (local path) | allowed |
| `git push fork add-recipe` (`fork` → github.com/someone/staged-recipes) | denied, `outward-git-push` |
| `cd /tmp/x-feedstock && git push origin b` (`origin` → conda-forge) | denied, `outward-git-push` |
| `git push nosuchremote b` | denied, names `git remote -v` |
| `git remote add up https://github.com/conda-forge/x` in this checkout | denied |
| same in an unrelated clone under `/tmp` | allowed (its push is judged later) |
| `gh pr comment 5 --repo conda-forge/x-feedstock` | denied, `outward-github-write` |
| `gh pr comment 5` in this checkout | allowed |
| `gh api repos/conda-forge/x/pulls` | allowed (GET) |
| `gh api -X DELETE repos/conda-forge/x/git/refs/heads/b` | denied (`unreachable-ref-deletion` may answer first; either reason) |
| `gh api graphql -f query='mutation …'` | allowed (named instruction-only) |
| `pyforge mason recipe submit recipes/x` | allowed (dry run) |
| `pyforge mason recipe submit recipes/x --yes` | denied, `outward-package-submission` |
| `pixi run -e local-recipes submit-pr x --dry-run` | allowed |
| `feedrattler x-feedstock me` | denied |
| MCP `submit_pr` with `dry_run: true` | allowed |
| MCP `migrate_to_v1` | denied, `outward-mcp-submission` |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-09 (external writes) entry.
- Epic: Epic 85 (CAP-165; `in-progress` while 85.5 is `blocked`). This story extends CAP-5's closed list.
- Ledger key: `85-8-an-agent-session-never-writes-outside-this-repository`.
- Ledger status at mint: `backlog`.
- Deps: —.
- Spec: `spec-pyforge-steward/.memlog.md` records the mint and the ruling; `SPEC.md` untouched; no CAP minted.
- Governance: the operator's ruling of 2026-10-09 adds four `session_denials` entries.
- Surface: `.claude/hooks/pre-shell.py`, `docs/governance/guild-roster.json`, `tests/scripts/test_pre_shell_hook.py`
  and AGENTS.md sit in Epic 85's `[epic_surfaces]` entry. `.claude/settings.json` and `.cursor/hooks.json` are added to
  it with this chain.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks (not a dispatch gate):**
- `pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_pre_shell_hook.py
  tests/scripts/test_session_denial_forms.py -q` — expected: pass.
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass (the CI `scripts-suite` twin).
- By hand in a session after landing:
  - `gh pr view 1 --repo conda-forge/staged-recipes` runs;
  - `gh pr comment 1 --repo conda-forge/staged-recipes --body x` is refused with the new reason, before any network
    call;
  - `git push origin <branch>` still runs.
- Mutation checks for AC (8), against a scratch copy of `pre-shell.py`.
- `pixi run -e pyforge-guild detectors-ci` — expected: no new finding against `main`.

## Spec Change Log

- No change yet.

## Review Triage Log

- No review has run yet.
