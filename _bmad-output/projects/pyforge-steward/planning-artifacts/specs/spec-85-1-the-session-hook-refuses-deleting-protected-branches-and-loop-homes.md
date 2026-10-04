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
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04-review.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** On 2026-10-04 an operator session cleaned up branches with a hand-rolled script instead of `scripts/worktree_sweep.py`. It removed every worktree whose `git status --porcelain` was empty, which included the eight station loop homes `~/.bmad-loops/pyforge-<station>`: porcelain hides gitignored files, so the loop homes' runtime state went with them. It also deleted the eight `loop/pyforge-<station>` branches, because their tips were ancestors of main, and 41 `attempt-preserve/*` branches, local and remote. The operator had approved the deletion by tier. The refs were restored from GitHub's branch-deletion activity log (`before` sha) through `gh api -X POST …/git/refs`, and the loop homes with `marshal init`. The gitignored run history was lost. Nothing in the session guardrails stops an agent from deleting a protected branch or a loop home, though both are named as never-touched by `scripts/worktree_sweep.py`.

**Approach:** Add one entry to the closed `session_denials` list in `docs/governance/guild-roster.json`, with id `protected-ref-deletion`. It is a governance act; the operator ruled it on 2026-10-04. Add its matcher to `.claude/hooks/pre-shell.py`.

*(Amended 2026-10-04 (later), architecture review M3 and M6; see the Spec Change Log.)* Add the one declared list to the roster as `protected_refs`. Each entry is a full-refname prefix with a `kind` (`operational-branch`, `preserve-tag`, `archive-tag`, `legacy`) and a `scope` (`origin`, `local`, `both`). Marshal Story 87.1's sweeper and steward Story 85.2's parity check read the same key. The entries are:
- `refs/heads/loop/` (operational-branch, both);
- `refs/heads/attempt-preserve/` (legacy, both, until marshal Story 87.12 retires it);
- `refs/tags/preserve/` (preserve-tag, both);
- `refs/tags/archive/` (archive-tag, both);
- `refs/tags/rescue/` (legacy, both).

The `recover/` and `rescue/` *branch* entries drop: they have no producer and no instance. The hook unions the roster with its own code floor, `refs/heads/main` and `refs/heads/loop/`, so a roster edit can only add.

This story's matcher enforces the branch entries only, with the deletion forms the operator ruled. The tag entries are declared here and enforced from Story 85.4, under its own ruling.

The matcher denies:
- deleting a branch of the floor or of a branch entry through `git push … --delete`, `-d`, or a `:refs/heads/<name>` refspec, `git branch -d/-D`, or `gh api -X DELETE …/git/refs/heads/<name>`;
- `git worktree remove` of a path under `~/.bmad-loops/`, resolved.

Each denial's reason names the sanctioned form: `python scripts/worktree_sweep.py --retire <branch>` for a protected branch (it writes an archive twin when deletion would orphan commits), and an operator decision for a loop home. Update `AGENTS.md` § *Session guardrails*: the rule count and the list.

Ledger key: `85-1-the-session-hook-refuses-deleting-protected-branches-and-loop-homes`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-steward` CAP-5 (the session guardrails, steward Story 63.3). A defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given `git push origin --delete loop/pyforge-marshal` (and the `-d`, `:refs/heads/…`, multi-branch and `git -C <dir>` forms) When the hook runs Then it denies with the `protected-ref-deletion` reason; the same for `attempt-preserve/` and `main`
- Given a roster whose `protected_refs` omits `refs/heads/loop/`, or lacks the key When the hook runs on a `loop/` or `main` branch deletion Then it still denies (the code floor)
- Given `git push origin --delete recover/x` or `rescue/x` (branches) When the hook runs Then this rule allows it (no such entry; Story 85.4's reachability guard judges it)
- Given the roster When it is read Then `protected_refs` carries the five entries with their kind and scope, and no `protected_ref_prefixes` key exists
- Given `git branch -D attempt-preserve/x` or `gh api -X DELETE repos/o/r/git/refs/heads/loop/x` When the hook runs Then it denies
- Given `git worktree remove --force ~/.bmad-loops/pyforge-atlas` (also as an absolute path, or through a symlink that resolves there) When the hook runs Then it denies
- Given `git push origin --delete feature/x`, `git branch -d feature/x` or `git worktree remove .worktrees/x` When the hook runs Then it allows
- Given the roster and the script When `load_denial_rules()` runs Then the new id matches one callable in `MATCHERS`, and the parity check still fails loud on drift
- Given `AGENTS.md` When it is read Then § *Session guardrails* names the new rule and the right count, and the scribe instruction-parity meta-test stays green
- Given the matcher removed or loosened When the new tests run Then they fail (mutation)

## Boundaries & Constraints

**Always:** One script for both harnesses; read the list from the roster, unioned with the code floor; the reason names the sanctioned form.

**Never:** Never deny a non-protected branch or worktree under this rule. Never add a denial the roster does not name. Never enforce the tag entries or widen the deletion forms here (Story 85.4 does, under its own ruling).

</intent-contract>

## Binding

Parent: steward Story 63.3 (the session guardrails hook).
Dream: `docs/dreams/pyforge-steward.md`, the 2026-10-04 entry.
Ledger key: `85-1-the-session-hook-refuses-deleting-protected-branches-and-loop-homes`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-04 at the operator's request ("chain the sweeper fixes"); the new `session_denials` entry is the operator's governance ruling of the same date. Amended 2026-10-04 (later) by the preserved-work refs chain (`spec-pyforge-steward` CAP-165; `spec-pyforge-marshal:CAP-287`).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_pre_shell_hook.py -q` — expected: pass.
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass (the CI `scripts-suite` twin).
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0.

## Spec Change Log

- **2026-10-04 (later): amended before any dispatch, by the preserved-work refs chain (`spec-pyforge-steward` CAP-165; architecture review of the same day; operator ruling accepting its defaults).** Trigger: review M3, M6 and M9, and the drafts' required changes to 85.1. Amended: (1) the roster key is `protected_refs`, holding full refnames with kind and scope, not `protected_ref_prefixes` (M3), so marshal 87.1 and the parity check read one structure; (2) the hook unions it with a code floor (`refs/heads/main`, `refs/heads/loop/`), and the roster can only add; (3) the `recover/` and `rescue/` branch entries drop (review Q18 / research Q6: no producer, no instance); (4) this story lands as ruled, branch deletion forms only. The widened forms (tags, `update-ref -d`, prune and mirror, `rm` of homes) and the reachability guard need their own ruling, so they move to Story 85.4 (M6); (5) `## Verification` names only the station's `verify_commands` plus lint-types, and the rest move to manual checks (MRS-GATE-011). Known-bad state avoided: a replacement read that drops `loop/` on a roster edit, and a matcher wider than its governance ruling. KEEP: the id `protected-ref-deletion`, the loop-home rule, the reasons naming the sanctioned form, and the AGENTS.md update.

## Review Triage Log

- No review has run yet.
