---
title: "85.1: The session hook refuses deleting protected branches and loop homes"
type: 'fix'
created: '2026-10-04'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - .claude/hooks/pre-shell.py
  - docs/governance/guild-roster.json
  - tests/scripts/test_pre_shell_hook.py
  - AGENTS.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** On 2026-10-04 an operator session cleaned up branches with a hand-rolled script instead of `scripts/worktree_sweep.py`. It removed every worktree whose `git status --porcelain` was empty, which included the eight station loop homes `~/.bmad-loops/pyforge-<station>`: porcelain hides gitignored files, so the loop homes' runtime state went with them. It also deleted the eight `loop/pyforge-<station>` branches, because their tips were ancestors of main, and 41 `attempt-preserve/*` branches, local and remote. The operator had approved the deletion by tier. The refs were restored from GitHub's branch-deletion activity log (`before` sha) through `gh api -X POST …/git/refs`, and the loop homes with `marshal init`. The gitignored run history was lost. Nothing in the session guardrails stops an agent from deleting a protected branch or a loop home, though both are named as never-touched by `scripts/worktree_sweep.py`.

**Approach:** Add one entry to the closed `session_denials` list in `docs/governance/guild-roster.json`, with id `protected-ref-deletion`. It is a governance act; the operator ruled it on 2026-10-04. Add its matcher to `.claude/hooks/pre-shell.py`, and add `protected_ref_prefixes: ["loop/", "attempt-preserve/", "recover/", "rescue/"]` to the roster as the one list (marshal Story 87.1's sweeper reads it too).

The matcher denies:
- deleting a branch of `main` or of any of those prefixes through `git push … --delete`, `-d`, or a `:refs/heads/<name>` refspec, `git branch -d/-D`, or `gh api -X DELETE …/git/refs/heads/<name>`;
- `git worktree remove` of a path under `~/.bmad-loops/`, resolved.

Each denial's reason names the sanctioned form: `python scripts/worktree_sweep.py --retire <branch>` for a protected branch, and an operator decision for a loop home. Update `AGENTS.md` § *Session guardrails*: the rule count and the list.

Ledger key: `85-1-the-session-hook-refuses-deleting-protected-branches-and-loop-homes`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-steward` CAP-5 (the session guardrails, steward Story 63.3). A defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given `git push origin --delete loop/pyforge-marshal` (and the `-d`, `:refs/heads/…`, multi-branch and `git -C <dir>` forms) When the hook runs Then it denies with the `protected-ref-deletion` reason; the same for `attempt-preserve/`, `recover/`, `rescue/` and `main`
- Given `git branch -D attempt-preserve/x` or `gh api -X DELETE repos/o/r/git/refs/heads/loop/x` When the hook runs Then it denies
- Given `git worktree remove --force ~/.bmad-loops/pyforge-atlas` (also as an absolute path, or through a symlink that resolves there) When the hook runs Then it denies
- Given `git push origin --delete feature/x`, `git branch -d feature/x` or `git worktree remove .worktrees/x` When the hook runs Then it allows
- Given the roster and the script When `load_denial_rules()` runs Then the new id matches one callable in `MATCHERS`, and the parity check still fails loud on drift
- Given `AGENTS.md` When it is read Then § *Session guardrails* names the new rule and the right count, and the scribe instruction-parity meta-test stays green
- Given the matcher removed or loosened When the new tests run Then they fail (mutation)

## Boundaries & Constraints

**Always:** One script for both harnesses; read the prefixes from the roster; the reason names the sanctioned form.

**Never:** Never deny a non-protected branch or worktree. Never add a denial the roster does not name.

</intent-contract>

## Binding

Parent: steward Story 63.3 (the session guardrails hook).
Dream: `docs/dreams/pyforge-steward.md`, the 2026-10-04 entry.
Ledger key: `85-1-the-session-hook-refuses-deleting-protected-branches-and-loop-homes`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-04 at the operator's request ("chain the sweeper fixes"); the new `session_denials` entry is the operator's governance ruling of the same date.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_pre_shell_hook.py -q` — expected: pass.
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0.

## Review Triage Log

- No review has run yet.
