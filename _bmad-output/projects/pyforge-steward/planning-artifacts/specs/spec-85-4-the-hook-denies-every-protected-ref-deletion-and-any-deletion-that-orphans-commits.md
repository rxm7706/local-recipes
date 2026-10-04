---
title: "85.4: The hook denies every protected-ref deletion and any deletion that orphans commits"
type: 'feature'
created: '2026-10-04'
status: 'ready-for-dev'
flag-exempt: detector-or-gate   # a session guardrail; a gated guardrail allows silently
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-85-1-the-session-hook-refuses-deleting-protected-branches-and-loop-homes.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04-review.md
  - .claude/hooks/pre-shell.py
  - docs/governance/guild-roster.json
  - tests/scripts/test_pre_shell_hook.py
  - AGENTS.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 85.1's rule denies only branch deletion, and only by name. The 2026-10-04 cleanup ran `git push --delete origin fix/x bmad-loop/…` and left 98 tips reachable from nothing. 83 of those 98 were under no protected name, so a repeat passes every layer (review B3). These forms also pass:
- tag deletion;
- `update-ref -d`;
- `push --mirror`, and a `push --prune` or `fetch --prune --prune-tags` covering a listed prefix;
- `rm -rf` of a loop home;
- `gh pr merge --delete-branch` on a `loop/` head.

The operator made two new governance rulings on 2026-10-04: (A) a reachability-guarded deletion denial for every branch and tag; (B) the protected-ref denial widened to these forms.

**Approach:**
- **Ruling B: widen `protected-ref-deletion`.** It now covers every deletion form for a listed ref on its scope: `git tag -d`; `git push <remote> :refs/tags/<name>` and `git push --delete <remote> <tag>`; `gh api -X DELETE …/git/refs/tags/<name>`; `git update-ref -d`; `git push --mirror`; a `git push --prune` or `git fetch --prune --prune-tags` whose refspec covers a listed prefix; `rm -r[f]` or `git worktree remove` of a path resolving under `~/.bmad-loops/`. It also denies `gh pr merge --delete-branch` when the command names a `loop/` head explicitly; a head the matcher cannot see is left to marshal Story 87.6.
- **Ruling A: new entry `unreachable-ref-deletion`.** For every branch and tag the list does not name, it denies a deletion when the ref's tip is not an ancestor of `refs/remotes/origin/main` and no `preserve/` or `archive/` tag contains it. The deletion forms are a push delete, a `:refs/…` refspec, `git branch -d/-D`, `git tag -d`, `gh api -X DELETE` or `update-ref -d`. The hook resolves a remote ref's tip from its remote-tracking ref and denies one it cannot resolve, with a fetch remedy. The reason names `marshal preserve tag` and `python scripts/worktree_sweep.py --retire` as the sanctioned forms.
- **Governance.** Both are `session_denials` entries, a governance act. The parity check between `MATCHERS` and the roster stays loud.
- **AGENTS.md.** § *Session guardrails* gains both rules, the new count, and two cautions. A matcher is a denylist, and a git config such as `fetch.pruneTags=true` bypasses any command matcher, so the server ruleset is the guarantee and the hook is defence in depth. Harnesses with no hook deny surface are guarded by the rulesets alone.

Ledger key: `85-4-the-hook-denies-every-protected-ref-deletion-and-any-deletion-that-orphans-commits`.
Type / Effort / Deps: feature / M / S-85.1.

### Living CAP citations

- `spec-pyforge-steward` CAP-165 (FR-38), extending CAP-5 (Story 63.3's guardrails). Flag-exempt `detector-or-gate`. Operator governance rulings A and B of 2026-10-04 (review B3, M6; Q7, Q8).

## Acceptance Criteria

- Given `git tag -d archive/x`, `git push origin :refs/tags/preserve/a/b/c`, `git push --delete origin rescue/dangling-20260801-abcd1234`, `gh api -X DELETE repos/o/r/git/refs/tags/archive/y`, `git update-ref -d refs/heads/loop/x`, `git push --mirror origin`, `git push --prune origin 'refs/tags/*:refs/tags/*'` or `git fetch --prune --prune-tags origin` When the hook runs Then it denies with the widened `protected-ref-deletion` reason.
- Given `rm -rf ~/.bmad-loops/pyforge-atlas` (also as an absolute path or through a symlink that resolves there) When the hook runs Then it denies; `rm -rf .worktrees/x` is allowed.
- Given `gh pr merge 12 --delete-branch --head loop/pyforge-marshal` (an explicit `loop/` head) When the hook runs Then it denies; `gh pr merge 12 --merge --delete-branch` with no visible head is allowed.
- Given a real repository and bare remote where `fix/x` holds commits nothing else reaches When `git push origin --delete fix/x` or `git branch -D fix/x` runs Then the hook denies with the `unreachable-ref-deletion` reason naming the sanctioned forms; after a `preserve/` tag contains the tip, or once the tip is an ancestor of `origin/main`, the same command is allowed.
- Given `git tag -d feature-tag` on an ancestor of `origin/main` When the hook runs Then it allows.
- Given a remote branch with no remote-tracking ref When its deletion runs Then the hook denies with a fetch remedy.
- Given the roster and the script When `load_denial_rules()` runs Then both ids match callables in `MATCHERS`, and the parity check still fails loud on drift; `AGENTS.md` names both rules, the right count and the bypass a git config leaves open, and the instruction-parity meta-test stays green.
- Given each matcher removed or loosened When the new tests run Then they fail (mutation).

## Boundaries & Constraints

**Always:** One script for both harnesses. Read the list from the roster, unioned with the code floor. Resolve reachability with git, never by name. Every reason names the sanctioned form.

**Never:** Never deny the deletion of a ref whose content is reachable elsewhere. Never add a denial the roster does not name. Never claim the hook is the guarantee.

</intent-contract>

## Binding

Parent: `spec-pyforge-steward` CAP-165 (FR-38), CAP-5 (Story 63.3).
Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-04 (later) entry.
Research: drafts' Story 85.1 change 2; review B3, M6, Q7, Q8.
Ledger key: `85-4-the-hook-denies-every-protected-ref-deletion-and-any-deletion-that-orphans-commits`.
Ledger status at mint: `backlog`.
Deps: S-85.1.
Minted 2026-10-04 under the operator's governance rulings of the same day.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_pre_shell_hook.py -q` — expected: pass.
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass (the CI `scripts-suite` twin).
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass (the instruction-parity meta-test reads `AGENTS.md`).
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0.

## Spec Change Log

- No change yet.

## Review Triage Log

- No review has run yet.
