---
title: '82.8: Status reads landings the way deploy does and filters findings with rows, and teardown keeps nested worktrees'
type: 'fix'
created: '2026-10-02'
status: 'backlog'
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

**Problem:** `marshal status` and `marshal teardown` each misreport or destroy something. Re-verified at HEAD a7cdb91fe4:

- Failed-story durability reads local `main` only (`cli/status.py::_MainSubjects.read`, `:1491`; `_reconcile_ledger`'s
  read at `:2322`), while `cli/deploy.py` passes `origin/main` and `main` combined to the same
  `core.promotion.merged_story_keys` owner (`:765`, `:3354`). A story that landed inside the fetch-versus-fast-forward
  window reads pending in `status` while `deploy promote` reads it durable (DW-FU-4-14-9).
- `core.promotion.count_conforming_subjects` (`core/promotion.py:437`) exists to tell "N subjects examined, none conformed"
  from "nothing merged", and `deploy` reports it (`cli/deploy.py:1075`), but `cli/status.py` never calls it: a shallow or
  grafted history reads as every failed-story patch being unlanded, one `MRS-STATUS-010` per patch (DW-FU-4-14-10).
- `--escalations` filters `rows` after sorting (`cli/status.py:2084-2085`) but returns every per-home finding the loop above
  already appended, so the operator gets an empty table beside alarms naming homes it filtered out (DW-FU-4-14-12).
- `cli/init.py::run_teardown` (`:2271`) interrogates only `loop/<slug>`, never calls `VcsPort.list_worktrees`
  (`ports/vcs.py:223`), and removes the home at `:2600`, recursively deleting registered run worktrees nested under it
  (`<home>/.bmad-loop/runs/<run>/worktrees/<story>`), uncommitted work included, and leaving prunable orphans (DW-1-8-5).

**Approach:**

- One subjects read for status: `origin/main` plus `main`, as `deploy` reads them; a missing `origin/main` is the ordinary
  case `deploy` already tolerates. `_reconcile_ledger` takes the same read so the module never disagrees with itself.
- The failed-patch fold counts conforming subjects with `count_conforming_subjects`; zero conforming subjects in a
  non-empty history yields one finding (a new `MRS-STATUS-*` code) saying the history cannot show what landed, with the
  examined and matched counts, in place of the per-patch `MRS-STATUS-010`s.
- `--escalations` keeps fleet-wide findings and drops per-home findings whose home is not in the filtered rows.
- `run_teardown` lists registered worktrees whose path sits under the home; it refuses without `--force` when any has
  uncommitted changes (`VcsPort.has_uncommitted_changes`, `ports/vcs.py:232`), naming each; a clean nested worktree does not
  block; after removal it prunes orphaned registrations (`VcsPort.prune_worktrees`, `ports/vcs.py:276`).

Ledger key: `82-8-status-reads-landings-the-way-deploy-does-and-filters-findings-with-rows-and-teardown-keeps-nested-worktrees`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-5 (fleet visibility, anything needing a human first) with Story 4.14 (FR-176) and Story 5.3
  (FR-38, `--escalations`); CAP-1 (loop homes) with Story 1.8 (FR-6; NFR-6; AD-29). Kinship: CAP-280 (merge facts are judged
  from `origin/main`). Defects of shipped behaviour, so no new CAP; no flag.

## Acceptance Criteria

- Given a story whose merge subject is on `origin/main` but not yet on local `main` When `marshal status` runs Then that story's failed patch is not reported pending
- Given a history of 50 subjects of which none conforms to the merge template When status folds failed patches Then one finding reports examined 50, matched 0, and no `MRS-STATUS-010` fires
- Given three homes of which none is paused on escalation When `marshal status --escalations` runs Then `homes` is empty and no per-home finding names any of them
- Given a home with a nested registered worktree holding an uncommitted file When `marshal teardown` runs without `--force` Then it refuses, names the nested worktree, and removes nothing
- Given a home whose nested worktrees are all clean When teardown runs Then the home is removed and `git worktree list --porcelain` shows no prunable entry for it
- Given each fix reverted in turn When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** `core.promotion.merged_story_keys` stays the one owner of "landed". Teardown's existing refusals keep their
order and codes. Register every new code in `core/findings.py` and `core/verdict.py`. Close DW-FU-4-14-9, DW-FU-4-14-10,
DW-FU-4-14-12 and DW-1-8-5 in `deferred-work-ledger.md` when the story lands (status `closed`, a `resolved:` line naming this
story).

**Never:** Do not refuse teardown merely because a nested worktree exists (every fleet home has them). Do not fetch from
`status` (it reads the refs the checkout holds). Do not change `MRS-STATUS-008`'s own shipped findings.

</intent-contract>

## Binding

Parent: Stories 4.14, 5.3 and 1.8, `spec-pyforge-marshal` CAP-5 and CAP-1; a defect, no new CAP.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 entry.
Ledger key: `82-8-status-reads-landings-the-way-deploy-does-and-filters-findings-with-rows-and-teardown-keeps-nested-worktrees`.
Ledger status at mint: `backlog`.
Deps: —.
Closes: DW-FU-4-14-9, DW-FU-4-14-10, DW-FU-4-14-12, DW-1-8-5.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

## Review Triage Log

- No review has run yet.
