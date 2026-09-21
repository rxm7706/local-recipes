---
title: '63.3: One deny list, one hook — the Guild session guardrails are enforced, not asserted'
type: 'feature'
created: '2026-09-18'
status: 'in-review'
baseline_revision: '2f98ede57d5ebb7df285bbd1383782cf6a7c86af'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred:
  - summary: >-
      `match_bmad_switch_unsafe` denies `scripts/bmad-switch` in every worktree
      unconditionally, but this repo's own recorded convention says running
      `bmad-switch` inside a bmad-loop run worktree is the sanctioned
      exception (to backlink Tier-3), distinct from the "never from a
      parallel agent" rule the hook is meant to enforce.
    evidence: |-
      The intent-contract's literal trigger text ("a worktree ... is
      present") is unconditional and does not carve out the bmad-loop-run
      case. AGENTS.md's own governing rule is actually narrower ("never ...
      from a parallel agent"), and a separate team-memory entry documents
      the bmad-loop-run-worktree exception explicitly. The hook cannot
      currently distinguish a solo bmad-loop run worktree from any other
      worktree, so it would deny a documented-safe action. Resolving this
      needs an operator decision: either teach the hook a reliable signal
      for "this is a bmad-loop run's own worktree," or update the team
      memory/AGENTS.md to say the new hook supersedes the old exception.
    location: >-
      .claude/hooks/pre-shell.py:404-413 (match_bmad_switch_unsafe)
    severity: high
  - summary: >-
      `direct-write-governed-path` only fires for Claude's `Edit`/`Write`
      tool_input; a write to a governed path via a `Bash` heredoc or
      redirect (`cat > SPEC.md <<EOF ... EOF`) is invisible to the hook
      entirely, even though this repo's own documented workaround for a
      restricted path is exactly that Bash/heredoc technique.
    evidence: |-
      `session_denials`' `direct-write-governed-path` rule declares
      `"applies_to": "edit_write"`, so `main()` never evaluates it for a
      `kind == "bash"` tool call, regardless of tokenizer quality. Closing
      this fully needs Bash-side write/redirect detection (heredocs, `sed
      -i`, `python -c "...write(...)"`, `>`/`>>`), which is materially more
      engineering than this story's ten matchers and is consistent with the
      hook's own stated "a guardrail, not a sandbox" design philosophy
      rather than a defect in the current ten rules.
    location: >-
      .claude/hooks/pre-shell.py:487-498 (match_direct_write_governed_path);
      docs/governance/guild-roster.json (direct-write-governed-path
      applies_to: edit_write)
    severity: medium
  - summary: >-
      `.cursor/hooks.json` invokes the script with a bare relative path
      (`python3 .claude/hooks/pre-shell.py`) while `.claude/settings.json`
      deliberately uses the cwd-independent `$CLAUDE_PROJECT_DIR` env var;
      if Cursor ever runs a hook with a process cwd other than the
      workspace root, the relative path would fail to resolve and the
      Cursor half of the guardrail would silently not run at all.
    evidence: |-
      Not independently confirmed against Cursor's actual hook-invocation
      cwd contract (whether `beforeShellExecution`/`afterFileEdit` always
      run with cwd at the workspace root, or can vary by multi-root
      workspace / a different worktree). If it can vary, the consequence is
      a full silent bypass of the Cursor-side enforcement, which would be
      high severity; settling this needs checking Cursor's hooks
      documentation/behavior directly for the cwd guarantee, or adding a
      self-check the script logs on load.
    location: >-
      .cursor/hooks.json:5,11 (command: "python3 .claude/hooks/pre-shell.py")
    severity: high (unverified)
  - summary: >-
      `git commit` opened with no `-m`/`-F`/`--message`/`--file` flag (a
      plain `git commit` or `git commit --amend` that opens `$EDITOR`)
      carries no message text on the command line at all, so
      `match_git_commit_guardrail`'s attribution check cannot see it —
      an AI-attribution or Co-Authored-By line typed into the editor is
      never caught by this pre-emptive hook.
    evidence: |-
      `_extract_commit_message` only reads argv tokens; an editor-composed
      message never appears there. This is a real, non-adversarial gap (a
      completely ordinary git workflow), not just a deliberate-evasion
      path. The only pre-shell-hook-level mitigations are either a
      behavior change (deny any `git commit` that doesn't supply a message
      via a recognized flag, forcing all commits through the flag-based,
      inspectable path) or an AGENTS.md/CLAUDE.md policy addition mandating
      explicit `-m` in agent sessions — the second is an agent-context-file
      edit, not a code fix, so it is recorded here for an operator
      decision rather than patched blind. The separate authoritative
      `commit-msg` git hook still catches this case after the fact (per
      the rule's own reason text), so this is a gap in the pre-emptive
      layer specifically, not a total gap.
    location: >-
      .claude/hooks/pre-shell.py:291-316 (_extract_commit_message),
      416-431 (match_git_commit_guardrail)
    severity: high
  - summary: >-
      `match_gh_pr_merge_squash` only denies `--squash`; AGENTS.md's own
      policy line ("never `--squash`... never `--rebase`... a rebase merge
      leaves no merge subject for landing evidence either") names
      `--rebase` as the case that actually lands undetected, since squash
      is already disabled server-side and therefore unreachable regardless
      of hook coverage.
    evidence: |-
      Confirmed: AGENTS.md's Trunk/worktrees/PRs section states squash is
      disabled in repository settings (so this hook's --squash coverage
      guards an already-unreachable case) while --rebase is not
      server-side-blocked and is called out by the same sentence as the
      one that breaks landing-evidence detection. The story's own literal
      Given/When/Then names only `gh pr merge --squash` as the trigger, and
      the intent-contract explicitly frames the closed list as "adding to
      it is a governance act" -- so extending coverage to `--rebase` is a
      deliberate, separate governance act on guild-roster.json, not a
      defect in this story's faithful implementation of its own named
      trigger.
    location: >-
      docs/governance/guild-roster.json (session_denials:
      gh-pr-merge-squash); .claude/hooks/pre-shell.py:434-440
      (match_gh_pr_merge_squash)
    severity: medium
  - summary: >-
      The Problem statement names four deployment modes by name ("Claude
      Code local or web, Cursor IDE or Cloud"), but the hook and its docs
      only distinguish two harness families (claude vs cursor) by JSON
      shape; nothing confirms or documents whether Claude Code web and
      Cursor Cloud (background agents) actually load and enforce the same
      settings.json/hooks.json the way the IDE/local surfaces do.
    evidence: |-
      `detect()` and every comment in pre-shell.py, `.cursor/hooks.json`,
      and AGENTS.md's new section treat "claude"/"cursor" as monolithic.
      The one live-verification citation in the diff is scoped to Cursor's
      IDE hooks schema; there is no equivalent citation for Cursor Cloud or
      Claude Code web. If either of those two surfaces does not load the
      same config the same way, the Problem statement's own named coverage
      would be silently incomplete rather than named as an exception the
      way Gemini/Copilot/Devin are. Settling this needs confirming,
      per-surface, that project-level `.claude/settings.json` and
      `.cursor/hooks.json` are honored identically in Claude Code web and
      Cursor Cloud.
    location: >-
      .claude/hooks/pre-shell.py:12-23 (module docstring, detect());
      AGENTS.md Session guardrails section
    severity: medium (unverified)
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** an agent — Claude Code local or web, Cursor IDE or Cloud — is about to run a shell command or edit a file in this repo

**Approach:** the hook denies with a one-line reason naming the sanctioned form (`-e pyforge-guild`, "a dependency is a pixi.toml change in a PR", "`uv run _bmad/scripts/memlog.py` then re-derive", …) — and never denies anything not on the list (the list is closed; adding to it is a governance act on `guild-roster.json`)

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-63-3-one-deny-list-one-hook-the-guild-session-guardrails-are-enforced-not-asserted.md` (CHAIN-STANDARD §5).
- This file is the tracked dispatch target for `marshal factory dispatch` / `resolve_story_spec_path`.

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| an agent — Claude Code local or web, Cursor IDE or Cloud — is about to run a shell command or edit a file in this repo | the command or path matches a `session_denials` entry: `pixi run -e local-recipes <guild task>` (the `guild-tasks` set… | the hook denies with a one-line reason naming the sanctioned form (`-e pyforge-guild`, "a dependency is a pixi.toml change in a PR", "`uv run _bmad/scripts/memlog.py` then re-derive", …) — and never… | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | the same script serves both harnesses; harnesses without a verified deny surface (Gemini CLI, Copilot CLI, Devin) are named as instruction-only in `AGENTS.md`, not silently assumed covered | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: `docs/governance/guild-roster.json` (a new closed `session_denials` list, the ONE declared source), `.claude/hooks/pre-shell.py` (new; registered `PreToolUse` on `Bash` and on `Edit`/`Write` in `.claude/settings.json`, `permissionDecision: deny` + reason), `.cursor/hooks.json` (new, force-tracked; `beforeShellExecution` deny — Cursor has no before-edit deny, so file rules there are `afterFileEdit` warn), tests under `tests/` for the script (the hook is repo-level, not a station package).
Ledger key: `63-3-one-deny-list-one-hook-the-guild-session-guardrails-are-enforced-not-asserted`.
Ledger status at mint (unchanged): `backlog`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-63-3-one-deny-list-one-hook-the-guild-session-guardrails-are-enforced-not-asserted.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).
- `pixi run -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass (runs `tests/scripts/test_pre_shell_hook.py`; the station command above does not reach repo-root `tests/scripts/`, added at review 2026-09-20).

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** S-63.1 • **FR/AD:** spec-pyforge-steward CAP-5; marshal-token-economy:CAP-20 (silent saves; the front door)
**Surface:** `docs/governance/guild-roster.json` (a new closed `session_denials` list, the ONE declared source), `.claude/hooks/pre-shell.py` (new; registered `PreToolUse` on `Bash` and on `Edit`/`Write` in `.claude/settings.json`, `permissionDecision: deny` + reason), `.cursor/hooks.json` (new, force-tracked; `beforeShellExecution` deny — Cursor has no before-edit deny, so file rules there are `afterFileEdit` warn), tests under `tests/` for the script (the hook is repo-level, not a station package).
**Given** an agent — Claude Code local or web, Cursor IDE or Cloud — is about to run a shell command or edit a file in this repo
**When** the command or path matches a `session_denials` entry: `pixi run -e local-recipes <guild task>` (the `guild-tasks` set read from `pixi.toml`, never a copy); `pip install` / `uv pip install` / `conda install` / `npx <x>` except `npx skills add`; `pixi add` / `pixi update`; `scripts/bmad-switch` when a worktree or `BMAD_ACTIVE_PROJECT` is present; `git commit` on `main` or in the primary checkout, or with `Co-Authored-By` / AI attribution; `gh pr merge --squash`; `gh pr create` without `--repo rxm7706/local-recipes`; `uv run` with cwd ≠ repo root; `spec_surface_check.py --write-baseline` without `--spec`; a direct write to `SPEC.md`, `sprint-status-ledger.yaml`, or a tracked path under `implementation-artifacts/`
**Then** the hook denies with a one-line reason naming the sanctioned form (`-e pyforge-guild`, "a dependency is a pixi.toml change in a PR", "`uv run _bmad/scripts/memlog.py` then re-derive", …) — and never denies anything not on the list (the list is closed; adding to it is a governance act on `guild-roster.json`)
**And** the same script serves both harnesses; harnesses without a verified deny surface (Gemini CLI, Copilot CLI, Devin) are named as instruction-only in `AGENTS.md`, not silently assumed covered
**Status:** backlog

## Review Triage Log

### 2026-09-20 — Review pass
- verdicts: 26 findings — high 8, medium 5, low 9, false 2, maybe-false 2
- findings:
  - `[high]` `[patch]` Blind Hunter: governance-drift crash path exits 1, but Claude Code's `PreToolUse` only blocks the tool call on exit 2 (other non-zero codes are non-blocking) — a missing/drifted `session_denials` silently lets the command through despite "fail loud". Fixed: top-level handler now exits 2.
  - `[false]` `[reject]` Blind Hunter: `match_gh_pr_create_missing_repo` has no escape hatch for an operator-authorized external PR — the intent-contract's own literal trigger names this exact unconditional denial with no carve-out, so the code faithfully implements what was asked; not a defect.
  - `[medium]` `[patch]` Blind Hunter: `match_adhoc_package_install` omits `mamba`/`micromamba` (common `conda install` drop-ins). Fixed: added to the checked patterns.
  - `[high]` `[defer]` Blind Hunter: `match_bmad_switch_unsafe` denies `bmad-switch` in every worktree unconditionally, conflicting with this repo's documented bmad-loop-run-worktree exception. Deferred — needs an operator decision on which side changes (see frontmatter `deferred`).
  - `[medium]` `[defer]` Blind Hunter: the Bash tokenizer has no `$(...)`/redirect handling and `direct-write-governed-path` only fires on `edit_write`, so a governed-path write via `cat > SPEC.md <<EOF` from Bash is invisible to the hook. Deferred — real, but closing it needs dedicated Bash-write-detection engineering beyond this story's ten matchers (see frontmatter `deferred`).
  - `[low]` `[patch]` Blind Hunter: `match_direct_write_governed_path` matches `SPEC.md`/`sprint-status-ledger.yaml` by basename alone, with no path-prefix scoping. Fixed: added a `_bmad-output/projects/*/planning-artifacts` path check.
  - `[low]` `[patch]` Blind Hunter: `NotebookEdit` bypasses `direct-write-governed-path` (matcher/settings.json only cover `Edit`/`Write`). Fixed: added `NotebookEdit` to the settings.json matcher and `detect()`.
  - `[maybe-false]` `[defer]` Blind Hunter: `.cursor/hooks.json`'s relative-path command vs `.claude/settings.json`'s `$CLAUDE_PROJECT_DIR`-anchored one could silently fail to resolve if Cursor ever runs a hook from a non-workspace-root cwd; Cursor's actual cwd contract for hooks was not independently verified. If true, severity is high (full silent bypass of the Cursor half). Deferred (see frontmatter `deferred`).
  - `[high]` `[defer]` Blind Hunter: a `git commit`/`--amend` with no `-m`/`-F` flag opens `$EDITOR`, so an attribution line typed there is invisible to `_extract_commit_message` — a normal, non-adversarial workflow bypasses the pre-emptive check entirely (the authoritative `commit-msg` git hook still catches it after the fact). Deferred — the fix is either a behavior change (deny editor-based commits) or an AGENTS.md policy addition, an operator call either way (see frontmatter `deferred`).
  - `[low]` `[reject]` Blind Hunter: `main()` returns on the first matcher hit, so a command tripping two rules only surfaces one reason. Rejected — cosmetic (doesn't allow anything that should be denied), and combining all matched reasons adds real branching complexity for marginal benefit.
  - `[high]` `[patch]` Edge Case Hunter + Verification Gap (same root cause, grouped): the tokenizer's `_SEPARATOR_RE` splits on a literal `&&`/`||`/`;`/`\n`/`|` before any quote-aware parsing, so a quoted multi-line argument (e.g. a heredoc-embedded `-m "$(cat <<'EOF' ... Co-Authored-By ... EOF)"`) shatters into fragments and the attribution text never reaches `match_git_commit_guardrail` as part of the message. Fixed: separator split is now quote-aware.
  - `[high]` `[patch]` Edge Case Hunter + Verification Gap (same root cause, grouped): `match_guild_task_via_local_recipes` checks every token in `rest`, not just the task-name position, so `pixi run -e local-recipes resolve-name mypy` is wrongly denied (`resolve-name` is the actual, `local-recipes`-only task; `mypy` is a positional argument value that happens to equal a Guild task name) — confirmed against `pixi.toml`. Fixed: restricted the check to the task-name position only.
  - `[low]` `[patch]` Edge Case Hunter: `npx` invoked via an absolute/relative path (`/usr/bin/npx`) bypasses the exact-token check. Fixed: match on `Path(tok).name`.
  - `[medium]` `[patch]` Edge Case Hunter: `python3.14 -m pip install` (versioned interpreter, plausible in this py3.14-pinned repo) bypasses the literal `python`/`python3` check. Fixed: version-tolerant pattern match.
  - `[low]` `[patch]` Edge Case Hunter: `BMAD_ACTIVE_PROJECT` set to an empty string is treated as absent by the truthiness check. Fixed: check key presence instead of truthiness.
  - `[low]` `[patch]` Edge Case Hunter: `uv-run-outside-repo-root` compares `os.path.abspath` on both sides, so the same directory reached via different symlinks would wrongly compare unequal. Fixed: compare `os.path.realpath` instead.
  - `[low]` `[patch]` Edge Case Hunter: `is_tracked` receives `ctx.file_path` without resolving it against `ctx.cwd` first; if the path were ever relative to cwd rather than repo_root, the tracked-check would look up the wrong location. Fixed: resolve to an absolute path before the tracked check (defensive; not confirmed the harnesses ever send a relative path).
  - `[low]` `[patch]` Edge Case Hunter: `spec_surface_check.py --write-baseline` invoked as a module (`python -m scripts.spec_surface_check`) bypasses the `.endswith("spec_surface_check.py")` check. Fixed: also match the bare module/script name without the `.py` suffix.
  - `[high]` `[patch]` Edge Case Hunter: `_extract_commit_message` doesn't recognize bundled short flags (`git commit -am "..."`), a very common invocation shape, so attribution added this way is never inspected. Fixed: recognize a token matching a bundled short-option cluster ending in `m` the same as `-m`.
  - `[medium]` `[defer]` Verification Gap ("Other findings"): `match_gh_pr_merge_squash` only covers `--squash` (already blocked server-side per AGENTS.md, so redundant), while AGENTS.md's own policy names `--rebase` as the case that actually lands without a merge subject and is not server-blocked. Deferred — the story's own literal trigger names only `--squash`; extending the closed list to `--rebase` is a separate governance act on `guild-roster.json`, not a defect in this story (see frontmatter `deferred`).
  - `[maybe-false]` `[defer]` Intent Alignment Auditor: the Problem statement names four deployment modes ("Claude Code local or web, Cursor IDE or Cloud") but the implementation and docs only distinguish two harness families; whether Claude Code web and Cursor Cloud actually load the same settings.json/hooks.json the same way as their IDE/local counterparts was not independently confirmed. If false, severity is medium (silently incomplete coverage of a Problem-statement-named surface). Deferred (see frontmatter `deferred`).
  - `[low]` `[reject]` Intent Alignment Auditor: automated tests can only prove the script's own JSON-in/JSON-out contract, not that a live Claude Code/Cursor session actually invokes it and honors the decision. Rejected — this is an inherent limit of hook unit-testing, not a fixable defect at this layer, and is not actionable within this story's scope.
  - `[medium]` `[patch]` Intent Alignment Auditor: the tracked spec's own `## Verification` section names only `pixi run --frozen -e pyforge-steward pyforge-steward-test`, which does not run the new `tests/scripts/test_pre_shell_hook.py` (a separate `pyforge-ci`-feature task) — confirmed against `pixi.toml`. Fixed: added the missing command to `## Verification`.
  - `[false]` `[reject]` Intent Alignment Auditor: Cursor's `afterFileEdit` warn-vs-deny gap vs. the Approach text's "the hook denies". Rejected — this is disclosed in three places (module docstring, `.cursor/hooks.json` comment, AGENTS.md) and covered by `test_cursor_after_file_edit_warns_not_denies`; not an undisclosed gap.

