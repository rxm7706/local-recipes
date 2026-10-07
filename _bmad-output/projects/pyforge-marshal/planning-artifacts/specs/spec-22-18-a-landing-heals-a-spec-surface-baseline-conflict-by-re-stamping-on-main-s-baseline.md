---
title: "22.18: A landing heals a spec-surface baseline conflict by re-stamping on main's baseline"
type: 'fix'
created: '2026-10-07'
status: 'done'
baseline_revision: 'b36482389641efd2591a9d5b5c8a883bcafcf746'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_landing.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_heal.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py
  - scripts/spec_surface_check.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** two dispatch landings that both stamped `scripts/.spec-surface-baseline.json` cannot both land. The
second is refused with `MRS-DISP-038` and waits for a human to merge `origin/main` into its branch.

- **Why the baseline conflicts.** Since Story 53.2 (and Story 82.3's loop), `dispatch_land.py`
  `_reconcile_spec_surface_drift` (about :374-:826) names the branch's governed paths on their Specs' memlogs, runs
  `scripts/spec_surface_check.py --write-baseline --spec <Spec> … --accept <path> …` and commits the baseline on the
  dispatch branch (`baseline_rel` about :517, the stamp about :725). When another landing stamps the same Spec on
  `main` after the branch's merge base, both sides rewrote the same entry and the merge conflicts on that file.
- **Why the heal refuses.** `core/dispatch_landing.py` `is_mechanical_conflict_path` (about :173) treats only Spec
  memlogs, the landing project's own sprint ledger and deferred-work ledger, and `.claude/memory/MEMORY.md` as
  mechanical. `unknown_conflict_paths` (about :202) returns every other path. `dispatch_land_heal.py`
  `try_heal_dispatch_land_merge` (about :69-:197) returns that path in `escalated_paths`, and `dispatch_land.py`
  (about :1600-:1625) refuses with `MRS-DISP-038`: "merge of PR #N has unknown conflict path(s)
  (scripts/.spec-surface-baseline.json) — refusing to merge or heal mechanically".
- **The live case.** On 2026-10-07 marshal 22.17 (PR #1899, run `pyforge-marshal-20261007T090238879Z-39903546`)
  verified and was refused with exactly that finding. Warden 14.2, steward 74.2 and the doctor and marshal chain PRs had
  merged first. Since the merge base, the branch had stamped `pyforge-marshal/spec-pyforge-core`, and `main` had
  stamped the same Spec plus `pyforge-steward/spec-pyforge-steward` and `pyforge-steward/spec-pyforge-unifying-strategy`.
  An operator merged `origin/main` into the branch by hand (`1e2334036d`), kept `main`'s baseline and unioned the
  memlogs. `spec-surface-check` then passed with no further stamp, because the memlogs already named the paths.
- **The rule already exists.** `scripts/spec_surface_check.py`'s docstring (DW-12-5-3) states that per-worktree
  stamps can only meet as a git conflict, and that the fix is to re-stamp the Specs each side reconciled, never to
  hand-merge the JSON.

**Approach:** the heal treats the baseline as mechanical, but only together with a re-stamp:

- `core/dispatch_landing.py` classifies `scripts/.spec-surface-baseline.json` as mechanical. The path becomes a
  constant there, and `dispatch_land.py`'s `baseline_rel` reuses it. A pure helper reads two baseline texts and returns
  the Spec names whose entries differ. Given the merge base and the branch head, that is the set of Specs the branch
  stamped.
- `try_heal_dispatch_land_merge` resolves the conflicted baseline to `origin/main`'s text in the same `resolutions`
  map that `_try_union_heal` already merges with. On the merged tree it then runs the landing's own reconcile, seeded
  with the Specs the branch stamped. Memlog, ledger, deferred-work and team-memory conflicts are resolved in the same
  merge as today.
- The reconcile is `_reconcile_spec_surface_drift` itself, passed to the heal as a callable by
  `execute_dispatch_land`, the same way Story 80.1 passes `await_checks`. The heal never imports `dispatch_land`, and
  the loop is never copied. The reconcile gains one input: the Specs to include in its first stamp's `--spec` list, as
  well as those the verdict names. It runs with `push_when_done=False`. The heal pushes once, after the reconcile, then
  waits for the healed head's checks (Story 80.1) and retries the merge.
- The reconcile's finding goes back to the landing: `MRS-DISP-047` (WARN) when it stamped, or `MRS-DISP-048`
  (ERROR) when it refused. A refusal leaves nothing pushed and no merge retried. That matches how the landing
  reconcile behaves today: it commits as it goes and pushes once, after the loop.

Ledger key: `22-18-a-landing-heals-a-spec-surface-baseline-conflict-by-re-stamping-on-main-s-baseline`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-marshal` CAP-137 (← `spec-marshal-drain-self-resolution` CAP-3; Story 28.20,
  the CAP-4 heal: mechanical land-conflict union, unknown paths escalate by name), on CAP-162's dispatch landing (←
  `spec-marshal-single-story-dispatch` CAP-4; Story 22.4). It reuses CAP-261's scoped reconcile (Story 53.2; Story
  82.3's re-read loop and `--accept` contract) and CAP-284's wait for the healed head's checks (Story 80.1). This
  closes a gap between two shipped behaviours, so it needs no new CAP.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, 2026-10-07 (baseline conflict).

## Acceptance Criteria

- Given a real-git fixture with these commits since the merge base: the dispatch branch changed a path governed by
  its station Spec A and by a co-governor Spec C, named it on both memlogs and scoped-stamped A and C. `main` changed a
  different path governed by C, named it on C's memlog and stamped C, and it also changed and stamped a path governed by
  a Spec B that the branch never touched. This is the 22.17 / warden 14.2 / steward 74.2 shape. When the landing's
  first `forge.merge_pr` fails, and `try_heal_dispatch_land_merge` runs with the landing's reconcile passed in, Then:
  - the heal merges `origin/main` into the branch with the baseline resolved to `main`'s text;
  - it re-stamps with `--spec` for A and C and no other Spec, and `--accept` only for the branch's own paths and the
    files the reconcile writes;
  - it pushes once and retries the merge with the pushed head's sha;
  - in the landed baseline, B's entry equals `main`'s byte for byte, and A's and C's entries equal what a scoped
    stamp computes on the merged tree;
  - `gather_spec_surface` reports no drift on the landed tree, and no `MRS-DISP-038` is raised.
- Given the same fixture with the branch's Specs already reading clean on the merged tree (the memlogs moved and name
  every path, as with 22.17) When the heal runs Then it still lands, the landed baseline holds `main`'s entry for every
  Spec the branch did not stamp, and `gather_spec_surface` reports no drift.
- Given `main` also changed a path governed by A or C that no memlog names (foreign drift) When the heal's scoped
  stamp runs Then the stamp refuses, the landing is refused with `MRS-DISP-048` naming that path, nothing is pushed,
  `forge.merge_pr` is not called again, and no `MRS-DISP-038` is raised.
- Given the baseline and one other non-mechanical path both conflict When the heal runs Then it escalates with
  `MRS-DISP-038` naming the other path, and no merge, stamp or push happens.
- Given no reconcile is passed to the heal (a direct caller, as with `await_checks=None`) When the baseline conflicts
  Then the heal escalates it with `MRS-DISP-038` as it does today and stamps nothing.
- Given the healed head's checks are red or still pending (Story 80.1) When the heal has pushed its re-stamped head
  Then no merge is retried, and the landing reports the wait's own finding, as today.
- Given the baseline branch removed from `is_mechanical_conflict_path` (mutation) When the station suite runs Then
  the first criterion's test fails with `MRS-DISP-038`.

## Boundaries & Constraints

**Always:**
- Only a scoped stamp. Its `--spec` list is the Specs the branch stamped since the merge base (read from git: the
  baseline at the merge base against the branch head) plus the Specs the verdict names for the branch's own paths.
  Its `--accept` list is the branch's own changed paths plus the files the reconcile writes.
- One reconcile loop. `_reconcile_spec_surface_drift` runs for both the pre-merge reconcile and the heal's, and it is
  passed to the heal as a callable.
- `main`'s baseline is the merge result for that path, and the re-stamp runs on the merged tree after every other
  mechanical resolution, memlog unions included.
- Name every changed governed path on the memlogs of the Specs that govern it, then stamp those Specs scoped
  (`spec-pyforge-marshal` and the co-governor `spec-pyforge-core`; AGENTS.md pre-PR item 5).

**Never:**
- Never a bare `--write-baseline`, and never `--spec` for a Spec the branch did not touch.
- Never hand-merge or textually union the baseline JSON.
- Never classify any path other than `scripts/.spec-surface-baseline.json` as newly mechanical. Every other unknown
  path still escalates with `MRS-DISP-038`.
- Never change `scripts/spec_surface_check.py`'s stamp semantics, and never change doctor's `gather_spec_surface`.

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-07 (baseline conflict) entry.
- Epic: Epic 22 (a fix joins its own epic, which stays `in-progress`; doctor Story 41.5).
- Ledger key: `22-18-a-landing-heals-a-spec-surface-baseline-conflict-by-re-stamping-on-main-s-baseline`.
- Ledger status at mint: `backlog`.
- Deps: —.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- Mutation: remove the baseline from `is_mechanical_conflict_path` and re-run the station suite. The real-git landing test fails with `MRS-DISP-038`. Restore it.
- On the next real landing that meets a baseline conflict, the journal shows the heal's re-stamp (`MRS-DISP-047`, or nothing when the merged tree already reads clean), and `pixi run -e pyforge-guild spec-surface-check` is green on `main` after the merge.
- `pixi run --frozen -e pyforge-guild spec-surface-check`: exit 0 after the memlog reconciles and scoped stamps.
