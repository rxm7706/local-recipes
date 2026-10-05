---
title: "83.24: A rename out of the CFE surface is caught, and the station guards read the one CFE owner"
type: 'fix'
created: '2026-10-04'
status: 'done'
baseline_revision: '74235c8884012b55b0e64b830718df0aa41c613d'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-83-19-dispatch-never-commits-the-cfe-surface-outside-a-sanctioned-retro.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_cfe_commit.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/worktree_checkpoint.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_retry.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/vcs_git.py
  - src/shared/packages/pyforge-testing-kit/src/pyforge/testing_kit/cfe_surface.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 83.19 landed as #1860 (849c94b9ca) on 2026-10-04. Its independent review, run against the 83.19 spec before the merge, found defects the operator chose to fix forward. 83.19's merge also added the marshal chain-currency finding (its branch history touched marshal's `pyproject.toml`); this story does not touch `pyproject.toml`.

- **HIGH — a rename out of the CFE surface is committed outside a retro.** `paths_excluding_cfe` (`core/dispatch_cfe_commit.py`, around :67) judges only a path's new name. `changed_files` reports a rename by its new path, and `GitVcs.commit_paths` (`adapters/vcs_git.py`, around :302 and :1016) adds the rename's original to the pathspec. Reproduced on real git: `git mv .claude/skills/conda-forge-expert/helper.py src/helper.py`, then `commit_worktree_checkpoint`, produced `wip: 99.1 (auto-checkpoint)` carrying `R100 .claude/skills/conda-forge-expert/helper.py -> src/helper.py`. The intent-to-add form (`mv` plus `git add -N`) does the same. The same path runs through `worktree_checkpoint.py` (around :60) and the supervisor (`__main__.py` around :220, :875, :1549). Verification then refuses (MRS-GATE-020), so it fails safe, but the branch can land only after a history rewrite, the exact failure 83.19 exists to stop. `pending_cfe_paths` reads the same new-path list, so the retro step cannot see the CFE-side deletion either.
- **MEDIUM — the "one owner" of the CFE surface exists only on paper.** The four station guards still hardcode `.claude/skills/conda-forge-expert`, and none reads `pyforge.testing_kit.cfe_surface`: atlas `tests/meta/test_skf_skill_and_persona.py` (around :232), marshal `tests/meta/test_skf_domain_skill.py` (around :158), steward `tests/meta/test_skf_steward_skill.py` (around :137), mason `tests/meta/test_persona_consults_cfe.py` (around :309). Marshal's runtime mirror covers more (the skill, `.claude/scripts/conda-forge-expert/` and `conda_forge_server.py`). So a story that edits only `.claude/scripts/conda-forge-expert/` with no CHANGELOG change passes the guards but is refused by dispatch.
- **LOW — the retro subject names Story 83.19 forever.** `RETRO_CFE_COMMIT_SUBJECT` (`core/dispatch_cfe_commit.py:58`) is the literal `retro(cfe): dispatch session CFE changes (Story 83.19)`, so every later story's retro commit is labelled 83.19 and carries no CFE version.
- **LOW — MRS-GATE-020 is retriable in every case.** `core/dispatch_retry.py` (around :38) lists it as retriable. For an unsanctioned commit already on the branch (83.19 AC4), a retry or a fix turn is refused again; only a history rewrite clears it.
- **LOW — the push precedes the CFE refusal.** Finalize pushes the branch (`__main__.py` around :1592) before verification runs (around :1679), so in the AC4 case the session's unsanctioned commit reaches origin before the refusal. 83.19's Approach said refuse "before anything is pushed".
- **LOW — one test fake is too broad.** `_fake_git_log_empty` (`tests/unit/test_dispatch_verification.py`, around :49) answers every `git … diff …` call with empty output. It masks nothing today, but it would hide any later process-level `git diff`.

**Approach:**
- Classify changed paths from `git status --porcelain -z` records, so a rename carries both sides. A record is CFE when either side is CFE. Such a pair stays out of every non-retro commit and joins the retro commit's pending set.
- Point the four station guards at `pyforge.testing_kit.cfe_surface` (its pathspecs and its classifier), so one list decides what the CFE surface is.
- Build the retro subject from the dispatched story key and the live CFE version: `retro(cfe): v<version> -- dispatch session CFE changes (Story <N.M>)`.
- Classify an unsanctioned CFE commit already on the branch as terminal (no retry, no fix turn), under its own code. Keep the uncommitted case retriable.
- Run the CFE branch check before finalize pushes, and refuse the push when it fails.
- Narrow the test fake to the exact git arguments the code under test issues.

Ledger key: `83-24-a-rename-out-of-the-cfe-surface-and-the-station-guards-read-the-one-cfe-owner`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- Story 83.19 (Stories 34.2, 28.24). Defects of shipped behaviour, so no new CAP. Under `spec-feature-flag-governance` Q1, a `fix` needs no flag.

## Acceptance Criteria

- Given a session that renames a CFE-surface file out of the surface (`git mv`, or `mv` plus `git add -N`) When the auto-checkpoint, finalize, pre-verify or blocked-halt commit runs Then neither side of the rename is in that commit, and the retro commit carries both sides
- Given each of the four station guards When the CFE pathspec list in `pyforge.testing_kit.cfe_surface` gains a path Then each guard covers it with no edit of its own; a guard with a hardcoded CFE path fails a test
- Given a story `N.M` and CFE version `X.Y.Z` When dispatch writes the retro commit Then its subject is `retro(cfe): vX.Y.Z -- dispatch session CFE changes (Story N.M)`
- Given an unsanctioned CFE commit already on the branch When verification refuses Then the code is terminal and no fix turn launches; the uncommitted case stays retriable
- Given an unsanctioned CFE commit on the branch When finalize runs Then it refuses before pushing, and origin's branch does not move
- Given each rule removed When the tests run Then its test fails (mutation); the narrowed fake still answers every git call the tests make

## Boundaries & Constraints

**Always:**
- Keep marshal's runtime free of `pyforge.testing_kit` imports (83.19's mirror plus parity tests stay); the station guards are tests, so they may import the kit.
- Keep the fail-closed reads: a git error refuses (MRS-GATE-009), never reads as clean.

**Never:**
- Never touch marshal's `pyproject.toml`, `pixi.toml` or `pixi.lock`.
- Never weaken `unsanctioned_commits` or the commit-msg rule.

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-04 (83.19 review) entry.
- Epic: Epic 83.
- Ledger key: `83-24-a-rename-out-of-the-cfe-surface-and-the-station-guards-read-the-one-cfe-owner`.
- Ledger status at mint: `backlog`.
- Deps: —.
- Minted 2026-10-04 at the operator's request ("proceed"), from 83.19's independent review (#1860).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

### 2026-10-04 — Review pass
- verdicts: 3 findings — high 0, medium 0, low 0, false 3, maybe-false 0
- findings:
  - `[false]` `[reject]` Porcelain rename partitioning might still commit the CFE source path via `commit_paths` pathspec alone — `non_retro_commit_paths` and checkpoint/supervisor call sites use porcelain records first; unit tests cover CFE rename out of surface.
  - `[false]` `[reject]` Pre-push CFE check might run after push — finalize sequence calls unsanctioned CFE commit check before `git push`; supervisor main-loop test asserts ordering.
  - `[false]` `[reject]` Station guards might miss `.claude/scripts/conda-forge-expert/` — guards now diff against `cfe_surface.CFE_GIT_PATHSPECS`; kit parity meta-tests pin the shared list.

## Auto Run Result

- **Summary:** Dispatch classifies renames from porcelain (both sides), excludes CFE rename pairs from non-retro commits, retro subject includes story key and live CFE version, MRS-GATE-021 is terminal for on-branch CFE commits, finalize refuses push when branch carries unsanctioned CFE commits; atlas/marshal/steward/mason meta guards import `pyforge.testing_kit.cfe_surface`.
- **Files changed:** marshal core (`dispatch_cfe_commit`, `vcs_git`, `worktree_checkpoint`, `dispatch_verify`, supervisor finalize, `dispatch_retry`, `findings`, `verdict`, `dispatch_verify_fix`, `ports/vcs`); marshal unit/meta tests; four station SKF meta tests; co-governor `.memlog.md` reconciles (spec-pyforge-core, spec-pyforge-marshal, spec-pyforge-mason, spec-pyforge-steward, spec-pyforge-atlas).
- **Review:** 0 patches, 0 deferred; 3 false positives rejected (see triage log).
- **Follow-up review recommended:** false
- **Verification:** `pyforge-marshal-test` 11683 passed; `pyforge-ci pyforge-deps-test` 130 passed (prior run); `lint-types` exit 0; `python scripts/spec_surface_reconcile.py` exit 0 after memlog reconcile.
- **Residual risks:** VCS test doubles without `status_porcelain_z_records` still fall back to path-only exclusion (documented in `non_retro_commit_paths`).
