---
title: '82.8: Status reads landings the way deploy does and filters findings with rows, and teardown keeps nested worktrees'
type: 'fix'
created: '2026-10-02'
status: 'in-review'
baseline_revision: '80fb2fe128e547ab06fc37540084e86061f26c84'
warnings: [oversized]
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

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py` -- `_MainSubjects.read` (reads local `main` only), `_merged_keys_for_slug` (the one policy-read-then-`merged_story_keys` sequence), the failed-patch fold and the `--escalations` filter inside `run_status`, `_reconcile_ledger`'s own `commit_subjects` read. `_landing_superseded` also reads through `_MainSubjects`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py` -- read-only reference: `_scan_promotions` builds `combined_subjects = origin + main` (origin best-effort, `main` required) and reports `subjects_examined` / `subjects_matched` from `core.promotion.count_conforming_subjects`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py` -- read-only: `merged_story_keys` stays the one owner of "landed"; `count_conforming_subjects(subjects, template, slug)` is a raw per-subject count.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py`, `core/verdict.py` -- register the new `MRS-STATUS-014` (WARN) beside `MRS-STATUS-010` / `-011`; `tests/unit/test_findings.py` pins the registry.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/init.py` -- `run_teardown`: the dirty probe for the home, the `reasons` list feeding `MRS-TEARDOWN-003`, and the `remove_worktree` call; no `list_worktrees` / `prune_worktrees` use today.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/vcs.py` -- `list_worktrees`, `has_uncommitted_changes`, `prune_worktrees` already exist on `VcsPort`; no port change.
- `src/shared/packages/pyforge-marshal/tests/unit/test_status.py`, `test_status_landing_superseded.py`, `test_init.py` -- fakes (`_FakeVcs`, `FakeVcs`) and the tests whose `commit_subjects_calls == ["refs/heads/main"]` assertions become `[ORIGIN_MAIN, "refs/heads/main"]`.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` -- close DW-FU-4-14-9, DW-FU-4-14-10, DW-FU-4-14-12, DW-1-8-5.

## Tasks & Acceptance

**Execution:**
- `cli/status.py` -- add `_read_landing_subjects(vcs, root)` (`ORIGIN_MAIN` best-effort, then local `main`, required, concatenated as `deploy` does); `_MainSubjects.read` and `_reconcile_ledger` both call it -- one read, never two views
- `cli/status.py` -- `_merged_keys_for_slug` also returns the conforming-subject count; the fold sets every patch of a home to `done: None` and emits one `MRS-STATUS-014` (examined N, matched 0) instead of the per-patch `MRS-STATUS-010`s when the history is non-empty and nothing conforms
- `cli/status.py` -- collect each home's findings as `(slug, finding)`; under `--escalations` keep fleet-wide findings and the findings of homes still in `rows`, and name only kept homes in the sweep-wide `MRS-STATUS-011` (omit it when none are left)
- `core/findings.py`, `core/verdict.py`, `tests/unit/test_findings.py` -- register `MRS-STATUS-014` as WARN
- `cli/init.py` -- `run_teardown`: list registered worktrees under the home's registered path; a dirty one joins `reasons` (existing `MRS-TEARDOWN-003`, naming each) and a clean one blocks nothing; after `remove_worktree`, `prune_worktrees` when nested worktrees were found
- `tests/unit/test_status.py`, `test_status_landing_superseded.py`, `test_init.py` -- one test per intent AC (origin-only landing, 50-subject history, `--escalations` with no escalated home, dirty nested refuses, clean nested prunes); update the read-order assertions; each new test fails with its fix reverted
- `deferred-work-ledger.md` -- the four rows to `status: closed` with a `resolved:` line naming Story 82.8

**Acceptance Criteria:** the six in the intent contract.

## Spec Change Log

## Design Notes

- The count is per slug (template and slug are `count_conforming_subjects`' inputs), so `MRS-STATUS-014` is per home, like `MRS-STATUS-011`'s second cause; a home with no patches never pays for it. An empty history is not this case: it keeps today's `done: false` reading.
- `done: None` (not `false`) is what stops `MRS-STATUS-010`: the fold already treats `None` as "landed-status could not be determined" and the finding names why.
- Dirty-nested refusal reuses `MRS-TEARDOWN-003`, appended after the home's own dirty reason so existing refusals keep their relative order; `--force` carries past it exactly as it carries past the home's own dirt.

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
