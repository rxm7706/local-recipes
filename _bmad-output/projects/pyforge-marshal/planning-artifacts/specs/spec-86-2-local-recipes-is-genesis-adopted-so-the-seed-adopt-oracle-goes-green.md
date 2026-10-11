---
title: "86.2: local-recipes is genesis-adopted so the seed-adopt oracle goes green"
type: 'fix'
created: '2026-10-03'
status: 'in-progress'
baseline_revision: 47397de509c4b12b68309f77022ca915db29d5b5
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The SC-02 slow oracle (a `marshal seed adopt` dry run on this repo) is red. The 2026-09-30 reproduction planned 21 actions: 5 absent hybrid regions (AGENTS.md, CLAUDE.md, .gitignore, README.md, `_bmad-output/PROJECTS.md`), 12 first-claims of files that already exist, and the `{{ slug }}`/loop-home paths Story 70.1 fixed for `seed check`. The first attempt (PR #1872, closed unmerged; branch `dispatch/pyforge-marshal/86.2` at `ac2d88a29f`) inserted the AGENTS.md, CLAUDE.md and PROJECTS.md regions. Those regions copy and contradict text the files already carry (`spec-pyforge-scribe` CAP-27, point, don't copy). The attempt also dropped two scripts' execute bits, tracked `.marshal/plan.json` against AD-57, and first-claimed three per-tool files by hand-editing `body_sha`. The operator held the story on 2026-10-05.

**Approach:** Operator ruling 2026-10-10: "Explicit seed skips (Recommended)". A fresh run from `origin/main` runs the bootstrap `marshal seed adopt --apply` on this repo. The AGENTS.md, CLAUDE.md and `_bmad-output/PROJECTS.md` hybrid regions are recorded as explicit skips (`--skip <path>`), which `.marshal/seed-state.yml` `skips:` keeps; every later adopt and update leaves those files alone (Story 86.1). Adopt inserts only the regions this repo does not already carry (`.gitignore`, `README.md`) and makes every first-claim itself. The execute-bit loss is fixed where the write lives, `.marshal/plan.json` stays untracked, and the oracle runs in a named CI lane (NFR-M2).

Ledger key: `86-2-local-recipes-is-genesis-adopted-so-the-seed-adopt-oracle-goes-green`.
Type / Effort / Deps: fix / M / S-70.1.

### Living CAP citations

- The capabilities that shipped each behaviour (see each row); a `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

1. Given the adopt has applied, when the branch's own diff `git diff origin/main...HEAD -- AGENTS.md CLAUDE.md _bmad-output/PROJECTS.md` runs, then it prints nothing, and `.marshal/seed-state.yml` `skips:` lists all three paths.
2. Given the recorded skips, when the oracle (`tests/integration/test_local_recipes_empty_plan.py`) runs in this checkout and in a fresh `git clone` that never ran `scripts/bmad-switch`, then `plan.actions` is empty once the three `unclassified-deferred` ids are filtered out. The filter is unchanged (K-02). The test also asserts that the artifact ids in `plan.skipped` equal a documented constant beside `UNCLASSIFIED_DEFERRED_ARTIFACT_IDS`, each id with its reason, so a new skip turns the oracle red instead of hiding drift.
3. Given `GEMINI.md`, `.github/copilot-instructions.md`, `.cursor/rules/specs.mdc` and the per-checkout `_bmad-output/planning-artifacts` and `_bmad-output/implementation-artifacts` symlinks, when the adopt applies, then the branch's own diff leaves each file untouched and each symlink is untouched (absent in a fresh clone). Each is recorded in `skips:` and in the documented constant with its reason: the per-tool addenda belong to scribe's parity test, and the symlinks are per-checkout links that `scripts/bmad-switch` creates. `src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py` passes.
4. Given the adopt writes or first-claims an existing file, when `git ls-files -s` is read after the apply, then every pre-existing path keeps its mode: `scripts/bmad-switch` and `scripts/bmad-loop-worktree` stay `100755`. The fix lives in the seed write path, not in a post-apply `chmod`, and a unit test that fails without it pins it.
5. Given the adopt has applied, when `git ls-files .marshal/plan.json` and `git check-ignore -q .marshal/plan.json` run, then the first prints nothing and the second exits 0, because the inserted `.gitignore` region carries the template's rule (AD-57). `model-ignores.gitignore.j2` still lists `.marshal/plan.json`, and `test_state_file_is_not_git_ignored_by_the_packaged_template` (`tests/unit/test_seed_state_store.py:1405`) is unchanged.
6. Given `.marshal/seed-state.yml`, when its history is read, then every `managed` record and every `body_sha` came from `marshal seed adopt --apply` itself, never from a hand edit. A `marshal seed update` dry run in a fresh clone plans zero actions.
7. Given the `.gitignore` region the adopt inserts, when `.gitignore` is read, then each ignore rule appears once. A pre-existing line that the region now carries is removed outside the region; the region itself is never hand-edited.
8. Given a manifest path holding `{{ slug }}`, when `seed adopt` or `seed update` plans or writes it, then it renders through Story 70.1's renderer, so no literal `{{ slug }}` path is written, and a `required_in: loop-home` entry is planned only in a loop home. The oracle reads loop-home placement through the same resolver adopt uses, never a hardcoded value. Each fix is pinned by a test.
9. Given CI runs, when the oracle runs, then it runs in a named lane: a `pixi.toml` task and a `.github/workflows/` job. `environment.yaml` is regenerated in the same change (`pixi project export conda-environment -e build > environment.yaml`, stderr kept out of the file).
10. Given this story lands, when `DW-FU-12-2` is read, then it is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` of the `skips:` record and of the oracle's skipped-set assertion, never line 1 of a file.

## Boundaries & Constraints

**Always:** Start from `origin/main`; the closed attempt's commits are evidence, never a base. Record this repo's differences in its own seed state (`skips:`), never in the shared manifest. Review every inserted region against AGENTS.md § *Instruction files* before committing. Fix each defect where the shipped behaviour lives and pin it with a test that fails without the fix. Before finishing, run the scribe parity test and the fresh-clone oracle by hand: neither is in marshal's `verify_commands`.

**Never:** Never widen the oracle's exclusion set (K-02). Never exempt this repo by name. Never edit the packaged manifest (`seed/templates/manifest.yaml`). Never change shared seed behaviour to special-case this repo: other adopting repos read it. Never hand-edit `.marshal/seed-state.yml`. Never rewrite AGENTS.md, CLAUDE.md, `_bmad-output/PROJECTS.md`, GEMINI.md, `.github/copilot-instructions.md` or `.cursor/rules/specs.mdc`. Never track `.marshal/plan.json`.

</intent-contract>

## Deferred-work rows this story closes (operator rulings 2026-10-03 and 2026-10-10)

- `DW-FU-12-2` — Phase 3 (2026-10-03): after Story 70.1, seed adopt renders `{{ slug }}` and honours `required_in: loop-home` through 70.1's renderer, the bootstrap `marshal seed adopt --apply` lands on local-recipes, and the oracle joins a CI lane. 2026-10-10: the AGENTS.md, CLAUDE.md and `_bmad-output/PROJECTS.md` regions are recorded as explicit seed skips, not inserted.

## Design Notes

**The skip mechanism.** The ruling says the seed manifest records the regions as skips. The record that does this per repo is `.marshal/seed-state.yml` `skips:` (`SeedState.skips`, `seed/state/store.py:652`). `marshal seed adopt --skip <glob>` writes it (`cli/seed.py:1259`; persisted at `seed/verbs/adopt.py:1145-1147`). `run_adopt` applies the recorded and the run's patterns after first-claim augmentation (`with_recorded_skips` and `apply_skips`, `seed/verbs/adopt.py:1224-1228`). `apply_skips` moves each matched action into `Plan.skipped` (`seed/plan/types.py:334`), and `managed_after_skips` drops the matched records from rung 6 (`seed/verbs/skips.py`). Update honours the same record (Story 86.1). The packaged manifest (`seed/templates/manifest.yaml`) is shared by every adopting repo, so it stays unchanged. The skip patterns carry no reason field, which is why the oracle's documented constant (AC 2) is where each reason lives.

**Execute bits.** `seed/apply/run.py:56-60` documents the residue: `atomic_write_bytes` leaves `0o666 & ~umask`, and `fs.write` (`seed/fs.py:447`) has no `mode=` passthrough. A first-claim overwrite of `scripts/bmad-switch` therefore loses `100755`.

**A fresh run, never the closed attempt's commits.** `_ensure_dispatch_worktree` (`cli/dispatch.py:1568`) reuses an existing `dispatch/pyforge-marshal/86.2` branch or `.worktrees/dispatch-pyforge-marshal-86.2` worktree. Both still exist, at `ac2d88a29f`, and the tip is also on `origin`. Before dispatch, the operator: preserves the tip (`marshal preserve tag --story pyforge-marshal 86.2 --producer dispatch --from .worktrees/dispatch-pyforge-marshal-86.2`, then `marshal preserve push`); removes that worktree; deletes the local branch; and retires the remote branch, so a later landing push is not a non-fast-forward. `resolve_dispatch_branch` then finds no branch, and provisioning creates the branch with `vcs.add_worktree(..., base=ORIGIN_MAIN)` (`cli/dispatch.py:1594`).

## Binding

Parent: The capabilities that shipped each behaviour (see each row)
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-03 (Phase 3) entry.
Ledger key: `86-2-local-recipes-is-genesis-adopted-so-the-seed-adopt-oracle-goes-green`.
Ledger status at mint: `backlog`.
Deps: S-70.1 (done).
Minted 2026-10-03 from the operator's Phase 3 rulings (rulings page `rulings` collection; "group them by module, as Phase 2 did"). Re-scoped 2026-10-10 by the operator's explicit-seed-skips ruling (`spec-pyforge-marshal` memlog).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010/011 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010/011 binding).
- `python scripts/spec_surface_reconcile.py` — expected: exit 0 (the derived surface guard; every governed path this story moves is named in its owning Spec's memlog).

**Manual checks:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test-slow -k test_local_recipes` — expected: pass in this checkout and in a fresh `git clone` of the branch run from a temp dir (AC 2).
- `pixi run --frozen -e pyforge-scribe python -m pytest -q src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py` — expected: pass (AC 3).
- `git diff origin/main...HEAD -- AGENTS.md CLAUDE.md _bmad-output/PROJECTS.md GEMINI.md .github/copilot-instructions.md .cursor/rules/specs.mdc` — expected: empty (AC 1, AC 3).
- `git ls-files -s scripts/bmad-switch scripts/bmad-loop-worktree` — expected: both `100755` (AC 4).
- `git ls-files .marshal/plan.json` empty and `git check-ignore -q .marshal/plan.json` exit 0 (AC 5).
- `pixi run --frozen -e pyforge-marshal marshal seed update` (dry run) in a fresh clone — expected: zero planned actions (AC 6).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Spec Change Log

- 2026-10-10 — Operator ruling "Explicit seed skips (Recommended)". Changed: Intent, Acceptance Criteria (four became ten), Boundaries, Design Notes and Verification are re-derived. The 2026-10-03 AC that let the inserted AGENTS.md and CLAUDE.md regions stand is withdrawn: those files and PROJECTS.md are now recorded skips. Known-bad state avoided: the closed attempt's duplicated instruction text, lost execute bits, a tracked `.marshal/plan.json` and hand-edited first-claims. KEEP: K-02, the named CI lane, Story 70.1's renderer and the DW-FU-12-2 closure. `lint-types` moved from Commands to Manual checks; dispatch still runs it as a derived command. Status `ready-for-dev`; the ledger key is already `backlog`.

## Review Triage Log

### 2026-10-05 — Independent review of the closed attempt (PR #1872, `ac2d88a29f`), carried from the branch

Carried from the closed attempt's own spec on `dispatch/pyforge-marshal/86.2` at `ac2d88a29f`, which never reached `main`. CI was green after that attempt's fixes (`marshal-local-recipes-seed-oracle`, `scribe-test`).

HIGH:
1. AGENTS.md:215-227, 275-293, 314-329 — the inserted regions copied AGENTS.md's own sections and contradicted them (Herald's versus Marshal's Dream-to-spec handoff; "via bmad-spec or the planning chain" versus "is not a substitute"); two numbered lists restarted under one heading; `seed update` would regenerate the regions.
2. CLAUDE.md:50-65 and 70-132 — copies of AGENTS.md § The tiers and the 60-line Multi-Project text Story 21.1 moved out; the `bmad-switch`-from-a-worktree ban was dropped; the scribe parity test compares headings only, so it stayed green.
3. `scripts/bmad-switch` and `scripts/bmad-loop-worktree` went from 100755 to 100644 (wip commit 37b4bea948).
4. `.marshal/plan.json` was tracked, and `model-ignores.gitignore.j2` stopped ignoring it, against marshal ARCHITECTURE-SPINE.md:1056-1065 (AD-57). The guard at `test_seed_state_store.py:1417` was flipped to match, and a dry-run adopt left the file modified with a local absolute path.
5. The three per-tool files were first-claimed by hand-editing `body_sha` in `.marshal/seed-state.yml`; a `seed update` dry run in a fresh clone planned 18 actions, including regenerating them.

MEDIUM: `adopt.py:870-880` recorded a repo's own content as tool-written, which affects other adopting repos; no test covered the new behaviour; `update.py` still wrote `{{ slug }}` literally; `_bmad-output/PROJECTS.md` gained a duplicate Projects table.

LOW: the `.gitignore` region duplicated existing rules; the DW-FU-12-2 `verified:` line cited line 1 of three files; the oracle hardcoded `in_loop_home=False`.

Root cause: this repo's AGENTS.md, CLAUDE.md and PROJECTS.md already carry the content the seed's hybrid regions insert. PR #1872 closed unmerged, and the operator held the story pending a decision.

### 2026-10-10 — Operator ruling: explicit seed skips; a fresh run from origin/main

- ruling (verbatim answer): "Explicit seed skips (Recommended)"; the option read: "Seed manifest records those regions as skips; re-run fixes execute bits, untracks .marshal/plan.json, drops hand-edited claims. Closes DW-FU-12-2." Of the three options the 2026-10-05 review left (explicit seed skips; templates that wrap existing text; keep holding), it takes the first.
- HIGH 1 (AGENTS.md) → AC 1 (a recorded skip, byte-identical). HIGH 2 (CLAUDE.md) → AC 1, plus AC 3's parity test. HIGH 3 (execute bits) → AC 4. HIGH 4 (AD-57) → AC 5. HIGH 5 (hand-edited first-claims) → AC 3 (the per-tool files are skips, not claims) and AC 6.
- MEDIUM: `adopt.py:870-880` → resolved by the fresh run (that change is not carried) and the Never boundary on shared seed behaviour; no test → the Always boundary and ACs 2, 4, 8; `update.py` `{{ slug }}` → AC 8; the duplicate Projects table → AC 1 (PROJECTS.md is a skip).
- LOW: `.gitignore` duplicates → AC 7; the line-1 `verified:` line → AC 10; the hardcoded `in_loop_home` → AC 8.
- The first landing refusal's items (the oracle red in a fresh clone because of the per-checkout symlinks; per-tool files rewritten; `pixi.toml` without `environment.yaml`) → ACs 2, 3 and 9.
- chain: the ruling is in the `spec-pyforge-marshal` memlog; `DW-FU-12-2` carries a `ruled:` line and stays open until this story lands. Status `ready-for-dev`. The ledger key already reads `backlog` on `main` (the 2026-10-05 hold was recorded on the branch only), so the sync moves nothing.
