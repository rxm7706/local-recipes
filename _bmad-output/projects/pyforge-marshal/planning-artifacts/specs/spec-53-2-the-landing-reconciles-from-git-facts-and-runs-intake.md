---
title: '53.2: The landing reconciles from git facts and runs intake'
type: 'feature'
created: '2026-09-20'
status: 'in-progress'
baseline_revision: '7f5584a2e49412b4fe9ee000d8f8b1760d024c4b'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py'
  - '{project-root}/scripts/spec_surface_reconcile.py'
  - '{project-root}/scripts/deferred_work_intake.py'
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** even with the producer told and gated (53.1), a session can exit with drift on its own files, and today that lands green and leaves `main` red until a human writes "Story X landed: <paths>" on the owning Spec and every co-governor the detector names, stamps exactly those Specs, and runs `deferred_work_intake` — the four fallout PRs of 2026-09-20 (#1533, #1537, #1544, #1546) were nothing but that ritual.

**Approach:** `dispatch_land`, after verification and before `forge.merge_pr`, runs the spec-surface verdict over the branch's changed governed paths (`git diff` against the merge base). For every Spec whose drift consists only of this branch's files, it appends one event on that Spec's memlog and on each co-governor the verdict names — the story key, the run id, each path — through `_bmad/scripts/memlog.py append`, scoped-stamps exactly those Specs through `scripts/spec_surface_check.py --write-baseline --spec`, commits onto the dispatch branch, journals `MRS-DISP-047` (warn: the session left N paths unreconciled; the landing named them), and merges. A Spec whose drift includes a file this branch did not change is foreign drift: the landing is refused with `MRS-DISP-048` naming those paths. `dispatch_land_finalize` runs `scripts/deferred_work_intake.py --fix --project <station>` and journals any refusal.

## Boundaries & Constraints

**Always:**
- The entry is derived from `git diff` — per-file naming, never a self-report and never a blanket stamp; the stamp is scoped to the Specs the entry named and nothing else
- Foreign drift refuses the landing (`MRS-DISP-048`) with every foreign path named; it is never absorbed
- A session that reconciled itself produces no entry, no stamp and no finding
- `MRS-DISP-047` is a warn, journaled, visible in `marshal watch` and `fleet-picture`'s ATTENTION rows
- The loop path (`cli/land.py`, CAP-239) is untouched; doctor's `sources/chain.py` is read, never changed

**Never:**
- Never a bare `--write-baseline`; never a stamp for a Spec with foreign drift
- Do not merge with the landing's own reconcile commit unpushed — the push precedes `forge.merge_pr` as today
- Do not add a second gate or verdict owner; the spec-surface verdict stays doctor's

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the 2026-09-20 fixture | the changed paths of 26.1, 61.3, 51.11, 29.1, 61.4, 46.7 on branches with no memlog entry | every path named on the owner + the co-governors the verdict names; those Specs stamped; `spec-surface` green on the merged tree; `MRS-DISP-047` ×6 | n/a |
| session reconciled itself | memlog already names every path | no entry, no stamp, no finding | n/a |
| foreign drift on a shared Spec | the Spec's drift includes a path the branch did not touch | refused, `MRS-DISP-048` names the foreign paths, nothing stamped | refusal journaled, worktree preserved |
| deferral without `location:` at finalize | intake refuses it | refusal journaled with the spec path and the rule | never silent |
| memlog append fails (locked / missing frontmatter) | `memlog.py` errors | landing refused naming the Spec; nothing merged | refusal journaled |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-261` (b).
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py` (the reconcile step between verify and merge), `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` (`MRS-DISP-047`, `MRS-DISP-048`), `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py` (intake), tests in `tests/unit/` with the 2026-09-20 fixture.
Ledger key: `53-2-the-landing-reconciles-from-git-facts-and-runs-intake`.
Minted 2026-09-20 from `epics.md`; dispatch after 53.1.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- The first autonomous landing after this story: `pixi run -e pyforge-guild spec-surface-check` on `main` is green with no human memlog edit; the run's journal carries `MRS-DISP-047` iff the session had not reconciled.
