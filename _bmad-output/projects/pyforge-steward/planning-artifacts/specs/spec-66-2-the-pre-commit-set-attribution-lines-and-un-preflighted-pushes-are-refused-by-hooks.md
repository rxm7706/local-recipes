---
title: '66.2: The pre-commit set — attribution lines and un-preflighted pushes are refused by hooks'
type: 'feature'
created: '2026-09-20'
status: 'done'
baseline_revision: '5e70a51cc1'
final_revision: 'pending — the merge commit of PR #1553'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/bootstrap.py
  - AGENTS.md
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** As the operator who found the 2026-09-20 coverage-floor miss (PR #1551 pushed after `pyforge-station-tests` + `detectors-ci`, not `pr-preflight`) and a `Co-Authored-By` rule that lives only in prose, I want a `.pre-commit-config.yaml` whose `commit-msg` hook refuses attribution trailers and whose `pre-push` hook runs `pr-preflight`, installed by `steward setup` / `initrepo`, So that both rules are enforced where the mistake happens and the managed block's two `TODO:` lines can retire under ground 2.

**Approach:** `.pre-commit-config.yaml` (new) with `scripts/commit_msg_check.py` (`commit-msg` stage; refuses `Co-Authored-By:` and AI-attribution trailers, names the rule) and `scripts/pre_push_preflight.sh` (`pre-push` stage; `pixi run -e pyforge-guild pr-preflight`; one documented opt-out env var, journaled); `steward setup` / `initrepo`'s existing hooks step (`bootstrap._run_pre_commit_install`) installs it unchanged; a CI check reds a missing file or hook; the two `TODO:` lines retire via `bmad-project-context record` in the same landing.

Ledger key: `66-2-the-pre-commit-set-attribution-lines-and-un-preflighted-pushes-are-refused-by-hooks`.
Ledger status (do not edit the ledger): `done`.

### Living CAP citations

- `spec-pyforge-steward` CAP-154 (Deps: S-66.1 — the `pre-push` hook runs the `pr-preflight` that 66.1 completes).

## Acceptance Criteria

- Given neither rule is enforced anywhere, When this story lands, Then a commit carrying `Co-Authored-By:` is refused locally with the rule named.
- A push from a branch whose `pr-preflight` is red is refused unless the one documented opt-out env var is set (and then the skip is journaled).
- `steward setup` on a fresh clone installs both hooks (the existing hooks step; no new duty, duty-count invariants unchanged).
- CI reds a missing `.pre-commit-config.yaml` or a missing hook.
- The two `TODO:` lines in `AGENTS.md`'s managed block are gone (bmad-project-context ground 2), the surrounding rules kept.

## Boundaries & Constraints

- `src/platform`'s `platform-ci` lane and `platform-ci-local` stay untouched; this story is about the ten `pyforge-*` packages and the repo's hooks.
- The CI lane and the `pr-preflight` leg call the SAME pixi tasks — never a second invocation that can drift.
- Only `pyforge-guild` exists at runtime (CAP-152): every new task lives in `guild-tasks` and runs from `-e pyforge-guild`.
- `pixi.toml` is shared surface: regenerate `environment.yaml`, run `pyforge-station-tests` before pushing.

## Surface

- `.pre-commit-config.yaml`, `scripts/commit_msg_check.py`, `scripts/pre_push_preflight.sh`, `.github/workflows/` (the existence check), `AGENTS.md` (managed block, via the skill), `src/shared/packages/pyforge-steward/tests/unit/test_bootstrap_remedies.py`, `tests/scripts/`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary checkout's copy of this file).

**Manual checks:**
- Commit with a planted `Co-Authored-By:` trailer → refused, rule named. Push a branch with a planted red preflight → refused; set the opt-out → pushed and journaled.
- Fresh clone: `steward setup` reports the hooks step ok.

</intent-contract>

## Review Triage Log

### 2026-09-20 — hand-driven pass (operator: "we implement and do this now")
  - `[high]` `[patch]` `.pre-commit-config.yaml` (new): `commit-msg-no-attribution` → `scripts/commit_msg_hook.py` (refuses `Co-Authored-By:`, `Generated with/by <AI>`, a leading 🤖; names the rule and the line); `pre-push-preflight` → `scripts/pre_push_preflight.sh` (runs `pixi run --frozen -e pyforge-guild pr-preflight`; `PYFORGE_PREFLIGHT_SKIP=1` is the one opt-out, journaled to `.steward/preflight-skips.log`; `dispatch/*` remote refs skip, journaled — the supervisor pushes `wip:` checkpoints every few minutes and is gated by verify_commands + S-13.7 + CI). `default_install_hook_types: [commit-msg, pre-push]` so `steward setup`'s bare `pre-commit install` installs both.
  - `[high]` `[patch]` Both hooks are `language: script`, never pixi-invoked: pre-commit stashes unstaged changes while a hook runs, and a pixi-invoked hook re-synced the Guild env against a momentarily reverted `pixi.lock` (seen live 2026-09-20 — the second probe commit found no `pre_commit`).
  - `[medium]` `[patch]` `bootstrap._PRE_COMMIT_CONFIG_RELATIVE_PATH` looked for a dotless `pre-commit-config.yaml` — the hooks step could never have found the canonical file; fixed. Stray husky v4 stubs (a 2025-11 kedro-viz `npm install` leftover in the primary `.git/hooks`) were chained as `.legacy` by the first install and dropped with `-f`; local machine state, not tracked.
  - `[medium]` `[patch]` `scripts/precommit_config_check.py` (repo detector, in `detectors-ci`) reds a missing file, a missing hook type or a missing/misrouted hook; the two `TODO:` lines in `AGENTS.md`'s managed block retired under bmad-project-context ground 2 in the same splice that added the pre-push and lint-types lines.

## Auto Run Result

**Status:** done
**Summary:** attribution lines are refused at `commit-msg`, un-preflighted pushes at `pre-push`; `steward setup` installs both; the block's prose TODOs are gone because the rules are enforced.
**Verification:** live on this worktree — a planted `Co-Authored-By:` commit refused with the rule named (`commit refused -- AGENTS.md § Policy…`, line 3); the real landing commit `ee38838825` passed the hook; `precommit-config-check` ok; `tests/scripts/test_lint_types_gate.py` 11 passed (refuse ×3 shapes, accept, comment lines ignored, hook script executable and naming the opt-out); the push of this PR runs `pr-preflight` through the hook itself.
**Files changed:** see the Surface.
**Residual risks:** `pr-preflight` costs ~20 minutes per push; the opt-out is journaled, not forbidden — the journal is the operator's to read.
**Follow-up review recommendation:** false
