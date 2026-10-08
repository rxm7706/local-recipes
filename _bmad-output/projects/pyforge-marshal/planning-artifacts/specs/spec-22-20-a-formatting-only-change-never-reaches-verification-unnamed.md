---
title: "22.20: A formatting-only change never reaches verification unnamed"
type: 'fix'
created: '2026-10-08'
status: 'in-progress'
baseline_revision: 'ce29e073d3375a852b194f034613d4f249a67d10'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-85-5-the-verify-fix-turn-s-edits-get-the-spec-surface-reconcile-before-re-verification.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_ruff_format.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - scripts/spec_surface_reconcile.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** after a verify fix turn, the supervisor stamps the spec-surface baseline and only then runs the pre-verify
ruff pass. A file the ruff pass reformats is then drift that no memlog names, so re-verification refuses on the
surface guard and the story parks over a change a formatter made.

- **The order today.** `dispatch_supervisor/__main__.py` `_maybe_run_verify_fix_turn` (about :1216-:1604) does three
  things after a fix turn ends:
  1. It commits the turn's edits (`_commit_pre_verify_wip`, about :1524).
  2. It runs Story 85.5's reconcile (`_reconcile_fix_turn_spec_surface`, about :1547). That reconcile is
     `dispatch_land._reconcile_spec_surface_drift` over the paths changed since the turn's recorded HEAD. It appends
     memlog entries, runs a scoped `--write-baseline --spec … --accept …` and commits the baseline.
  3. It re-verifies (`_run_and_journal_verification`, about :2313). That function first runs the Story 83.9/83.15
     ruff pass (`_run_and_journal_ruff_format`, about :2256, through `dispatch_verify.run_dispatch_ruff_format_before_verify`
     and `core/dispatch_ruff_format.apply_dispatch_ruff_format_before_verify`), which runs `ruff check --fix` and
     `ruff format` on the story's changed `.py` files and commits whatever changed. Only then does it verify, and the
     verify commands include the S-13.7 guard `python scripts/spec_surface_reconcile.py`.

  A file the ruff pass changes in step 3 was stamped in step 2. Its hash no longer matches the baseline and its Spec's
  memlog has not moved since the stamp, so the guard reports it as drift.
- **The live case.** Herald 29.2, run `pyforge-herald-20261007T183712284Z-b952633b`, on branch
  `dispatch/pyforge-herald/29.2`, on 2026-10-07:
  - The first verification refused on `pyforge-core-test` (19:36:32Z), and a fix-only turn ran (19:36:33Z-19:39:17Z).
  - The reconcile then journaled `step: reconcile`, `outcome: reconciled` (19:39:31Z) and committed `104929ec89`
    (`spec-pyforge-herald` memlog), `3b3d2a8fec` (`spec-pyforge-core` memlog) and `ef558bf954` (the baseline).
  - The ruff pass then journaled `dispatch-ruff-format` (19:39:32Z) and committed `f1b8184bd1`, a one-line format of
    `src/shared/packages/pyforge-herald/tests/unit/test_station_api.py`.
  - Re-verification (19:44:53Z) refused at `MRS-GATE-001`: `python scripts/spec_surface_reconcile.py` exited 1 with
    `[drift] pyforge-herald/spec-pyforge-herald: src/shared/packages/pyforge-herald/tests/unit/test_station_api.py
    changed but the spec's memlog did not move`. The story parked with `MRS-DISP-060`.
  - An operator named the path on both memlogs by hand (`428a12b699`) before the story could go on.
- **Where the order is already right.** The first verification (`_run_supervisor_finalize_sequence`, about :1611) and
  the land-only verification (`cli/dispatch.py` `_verification_verdict_for_cap4`, about :1061) both run the ruff pass
  and then verify, and no reconcile comes between them. The landing's own reconcile (`dispatch_land.py`, about :1553)
  runs after verification has passed, so the ruff pass has already run. Only the fix turn puts a stamp between the
  ruff pass and the verification that reads it.

**Approach:** in the fix turn, run the ruff pass before the reconcile.

- In `_maybe_run_verify_fix_turn`, call `_run_and_journal_ruff_format` once after `_commit_pre_verify_wip` succeeds
  and before `_reconcile_fix_turn_spec_surface`. The ruff commit lands after the turn's recorded HEAD, so the
  reconcile's `vcs.changed_files(..., base=head_before_turn)` already includes every file the ruff pass changed. One
  reconcile then names the fix and the formatting together and stamps once.
- `_run_and_journal_verification` keeps its own ruff pass unchanged, because the first verification and every other
  caller rely on it. In the fix turn it runs again on files that are already formatted, so it changes nothing,
  commits nothing and journals nothing.
- When the turn has no recorded HEAD (`head_before_turn is None`, so no reconcile runs), the ruff pass still runs
  before re-verification, as it does today.

**Why this option, not "re-run the reconcile after any ruff commit".** The fix turn is the only sequence where a stamp
comes between the ruff pass and the verification that reads the guard. Moving the pass fixes that sequence and adds
nothing to the others. Re-running the reconcile inside the ruff pass would add a supervisor stamp before the first
verification and the land-only verification. In those sequences S-13.7 leaves naming a story's paths to the session
itself. It would also add a second reconcile commit to every fix turn that the formatter touches. The order this
story picks gives one reconcile, one stamp and one set of memlog lines. That is the same result as the operator's
hand fix `428a12b699`.

Ledger key: `22-20-a-formatting-only-change-never-reaches-verification-unnamed`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-marshal` CAP-286 (FR-233): Story 85.1's verify fix turn and Story 85.5's
  reconcile of the turn's paths. CAP-261 (b): Story 53.2's `_reconcile_spec_surface_drift`, reused and never copied.
  The pre-verify ruff pass of Stories 83.9 and 83.15 runs on CAP-161's independent verification
  (← `spec-marshal-single-story-dispatch` CAP-3; Story 22.3). The story closes a gap between shipped behaviours, so it
  needs no new CAP.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag. `pyforge.marshal.verify_fix_loop`, the
  flag the fix turn already sits behind, is unchanged.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, 2026-10-08 (verify and landing order).

## Acceptance Criteria

- **The 29.2 order verifies.** Given a fix turn that commits an edit to a governed story file and leaves it
  `ruff format`-dirty, with every other path of the session and the turn already named on its Specs' memlogs (the
  herald 29.2 shape), When `_maybe_run_verify_fix_turn` runs after the turn exits 0, Then:
  - the run journal holds a `dispatch-ruff-format` OUTCOME (`committed: true`, `paths` naming that file) before the
    fix turn's `step: reconcile` observation;
  - that observation's `paths` include the reformatted file;
  - the reconcile names the file on its Spec's memlog and stamps that Spec scoped;
  - re-verification journals no second `dispatch-ruff-format` entry;
  - re-verification's `python scripts/spec_surface_reconcile.py` exits 0, and the story's verification reads
    `verified`.
- **Nothing to format.** Given a fix turn whose files are already formatted When the turn's edits are committed Then
  the ruff pass changes nothing and journals nothing, and the reconcile and re-verification behave exactly as today.
- **No recorded HEAD.** Given a fix turn intent with no `worktree_head_before_turn` When the turn ends Then the ruff
  pass runs before re-verification, no reconcile runs, and the order is otherwise as today.
- **Other sequences unchanged.** Given the first verification (`_run_supervisor_finalize_sequence`) or a land-only
  verification (`_verification_verdict_for_cap4`) When either runs Then the order is still ruff pass, then
  verification, with no reconcile between them. A test pins each order.
- **Foreign drift is still not absorbed.** Given a fix turn whose Spec also drifted on a path that neither the turn
  nor the ruff pass changed When the supervisor re-verifies Then that drift is not reconciled, re-verification refuses,
  and the story parks with `MRS-DISP-060` as today.
- **A reconcile that cannot be applied.** Given the reconcile refuses (`MRS-DISP-048`) after the ruff pass committed
  When the turn ends Then the story parks without re-verifying (`failed_step: reconcile`), as today. The ruff commit
  stays on the branch.
- **Mutation.** Given the ruff pass moved back after the reconcile (or removed from the fix turn) When the station suite
  runs Then the first criterion's test fails, and re-verification refuses at `MRS-GATE-001` on
  `python scripts/spec_surface_reconcile.py`.

## Boundaries & Constraints

**Always:**
- One ruff implementation (`run_dispatch_ruff_format_before_verify` / `apply_dispatch_ruff_format_before_verify`) and
  one reconcile implementation (`_reconcile_spec_surface_drift`), each reused and never copied.
- In the fix turn, the order is: commit the turn's edits, run the ruff pass, reconcile, then re-verify.
- Name every changed governed path on the memlogs of the Specs that govern it, then stamp those Specs scoped
  (`spec-pyforge-marshal` and the co-governor `spec-pyforge-core`; AGENTS.md pre-PR item 5).

**Never:**
- Never stamp the baseline in the first verification or the land-only verification. Never run a bare
  `--write-baseline`.
- Never reconcile a path that neither the fix turn nor the ruff pass changed.
- Never change which files the ruff pass touches (the story's changed `.py` files, each package's own ruff
  configuration), and never change its commit subject.
- Never change `scripts/spec_surface_reconcile.py`, the verify commands, or the fix turn's flag.

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-08 (verify and landing order) entry.
- Epic: Epic 22 (a fix joins its own epic, which stays `in-progress`; doctor Story 41.5).
- Ledger key: `22-20-a-formatting-only-change-never-reaches-verification-unnamed`.
- Ledger status at mint: `backlog`.
- Deps: none.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- Mutation: move the ruff pass back after `_reconcile_fix_turn_spec_surface` in `_maybe_run_verify_fix_turn` and re-run the station suite. The 29.2-order test fails, and re-verification refuses at `MRS-GATE-001`. Restore it.
- On the next fix turn that leaves a story file unformatted, the run journal shows `dispatch-ruff-format` before the turn's `step: reconcile` observation, and re-verification passes the surface guard with no hand memlog edit.
- `pixi run --frozen -e pyforge-guild spec-surface-check`: exit 0 after the memlog reconciles and scoped stamps.
