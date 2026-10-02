---
title: '82.8: Status reads landings the way deploy does and filters findings with rows, and teardown keeps nested worktrees'
type: 'fix'
created: '2026-10-02'
status: 'done'
baseline_revision: '80fb2fe128e547ab06fc37540084e86061f26c84'
warnings: [oversized]
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
deferred:
  - summary: >-
      No CI lane runs the pyforge-marshal tests marked slow, so every real-git end-to-end test in tests/integration/test_init_worktree.py, including this story's two nested-worktree teardown tests, runs only when someone invokes pyforge-marshal-test-slow by hand.
    evidence: |-
      pytest's marker setup in src/shared/packages/pyforge-marshal/pyproject.toml excludes slow from the default pyforge-marshal-test task (pixi.toml passes -m "not slow"). pyforge-marshal-test-slow is defined at pixi.toml:738 and a grep over .github, pixi.toml and scripts finds no other reference to it; scripts/coverage_gates_ci.py and scripts/run_station_coverage_gate.py also pass "not slow". Story 82.8's acceptance criterion that git worktree list --porcelain shows no prunable entry after a clean teardown is therefore pinned in the default suite only through FakeVcs, whose remove_worktree and prune_worktrees model the behaviour themselves; the real-git assertion lives only in the slow tests. This predates the story (every end-to-end test in that file shares it, e.g. the Story 1.8 teardown ones), so it is deferred, not patched here. What would settle it: a CI or pr-preflight lane that runs pyforge-marshal-test-slow, or a decision that the slow lane is intentionally manual.
    location: >-
      src/shared/packages/pyforge-marshal/pyproject.toml:75
    severity: medium
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

### 2026-10-02 — Review pass
- verdicts: 37 findings — high 0, medium 2, low 23, false 12, maybe-false 0
- findings:
  - `[low]` `[reject]` Blind Hunter: MRS-STATUS-014 fires on a healthy history because `count_conforming_subjects` is slug-scoped — the templated merge shape carries no station token (`core/promotion.py`, `known_keys` docstring), so any history holding a templated `Merge <key> into main` conforms for every slug; only a project with neither shape reads zero, and the message says "a project with no merge on it yet". Spec Design Notes pin the count per slug. Unlikely in everyday use and the repo-wide alternative is more than a direct correction.
  - `[low]` `[reject]` Blind Hunter: `examined` double-counts ancestry shared by `origin/main` and `main` — it is `len(origin + main)`, the same raw figure `marshal deploy promote` reports as `subjects_examined`, and `count_conforming_subjects` is documented as deliberately not deduplicated; matching deploy is the intent.
  - `[low]` `[reject]` Blind Hunter: 014 is per home though its cause is repo-wide, so a shallow clone repeats it — per home because the count is per slug, like MRS-STATUS-011's second cause; each finding names that home's own patches. Noise, not a wrong answer.
  - `[low]` `[reject]` Blind Hunter: a failed prune after removal leaves orphans a re-run never prunes — real but rare (`git worktree prune` failing after `worktree remove` succeeded), the leftover prunable registration is cosmetic, and the fix adds a prune to the branch-only path. The test comment's claim (a re-run reconciles the branch) is accurate.
  - `[low]` `[reject]` Blind Hunter: `git worktree prune` is repo-wide, so "harmless" overstates it — the intent names `VcsPort.prune_worktrees` and Story 51.1 already calls it the same way; a per-entry removal contradicts the intent.
  - `[low]` `[patch]` Blind Hunter: `--escalations` can change verdict and exit code, and nothing pins MRS-STATUS-008, 014 or the fleet-row finding under the flag — the verdict change is by design (every per-home finding is WARN, exit stays 0, asserted); the gap was real for 008 (no test with `escalations=True`). Patched: `test_unpushed_work_is_reported_only_for_the_escalated_home`.
  - `[low]` `[patch]` Blind Hunter: the teardown `description` and `--force` help still name only the home as dirty — confirmed in `add_teardown_subparser`, no test pins the strings. Patched: both now name a nested registered worktree.
  - `[false]` `[reject]` Blind Hunter: a detached-HEAD nested worktree can lose commits silently — bmad-loop provisions every run worktree on a branch (`bmad_loop/verify.py:6415-6420`, `git worktree add -b <branch>`), and the ledger evidence says committed nested work survives as `bmad-loop/...` refs.
  - `[low]` `[reject]` Blind Hunter: `_merged_keys_for_slug` returning a 3-tuple is intrusive and counts on every call — the count is one pass over about 2,400 subjects, run once per refused row; no named harm, and a result type is more than a direct correction.
  - `[low]` `[reject]` Blind Hunter: teardown test gaps (the `FsError` arm, the forced listing-failure reason text, nested orphans in the branch-only path, a hand-rolled stdout swap) — each arm mirrors the home probe's already-covered handling; nits, not defects.
  - `[low]` `[reject]` Blind Hunter: integration assertions are weak (`refused_exit != 0`, a text-format substring, counting `"worktree "`) — they fail on the real regressions (mutants M4 and M5 below are caught); cosmetic.
  - `[low]` `[reject]` Blind Hunter: `origin/main` failures are swallowed silently, and the CAP-5 resolutions name no pinning tests — `deploy` swallows `origin/main` identically and the intent calls a missing one the ordinary case; the `resolved:` lines meet the Boundaries (closed, naming this story).
  - `[low]` `[reject]` Blind Hunter: MRS-STATUS-014 is registered ahead of 012/013 so three lists are out of numeric order — cosmetic, no reader depends on order (`REGISTERED_CODES` is a frozenset, the table a dict).
  - `[low]` `[reject]` Edge Case Hunter: prune failure skips branch deletion and a re-run never re-prunes — same defect and same reasoning as the Blind Hunter prune row above; carried.
  - `[low]` `[reject]` Edge Case Hunter: prune is repo-wide and could drop unrelated stale registrations — same as the Blind Hunter prune-scope row; carried.
  - `[false]` `[reject]` Edge Case Hunter: a detached-HEAD nested worktree holds unreferenced commits — same as the Blind Hunter row; bmad-loop never creates one.
  - `[false]` `[reject]` Edge Case Hunter: a locked nested registration survives prune — bmad-loop never takes a worktree lock (no `git worktree lock` anywhere in `bmad_loop`), so the trigger is not reachable here.
  - `[low]` `[reject]` Edge Case Hunter: `--escalations` drops the finding of an `unknown`-state home (unreadable journal) — that home's row is already excluded by the pre-existing filter, and the intent's Approach and third acceptance criterion drop every per-home finding whose home is not in the rows.
  - `[low]` `[reject]` Edge Case Hunter: an `origin/main` read error (timeout, corruption) is swallowed and 014's text names `origin/main` though unread — identical to `deploy`'s tolerance; at worst it falls back to the old main-only reading.
  - `[low]` `[reject]` Edge Case Hunter: corroboration runs per subject, so an overlapping `origin/main` + `main` costs about two `git show` per station-branch merge naming the row's key — only for a refused row's own key; negligible, and deduplicating would break the `examined` match with `deploy`.
  - `[low]` `[reject]` Edge Case Hunter: 014's "zero conforming means shallow or grafted" claim is slug-scoped — same as the first Blind Hunter row; the message already names the other cause.
  - `[low]` `[reject]` Edge Case Hunter: `_reconcile_ledger` reads git facts from `origin/main` but the ledger from the local working tree, so a window shows `merged-not-done-in-ledger` — the intent requires this read for the view; the discrepancy is the view's purpose, and a landing's ledger promotion is a separate later commit, so the gap exists on `origin/main` too.
  - `[low]` `[patch]` Edge Case Hunter: two comments still say `run_status` reads `vcs.commit_subjects(root, "main")` — confirmed stale (the comment above `_reconcile_ledger`, the block before `main = _MainSubjects()`). Patched: both name `_read_landing_subjects`.
  - `[medium]` `[defer]` Verification Gap: the two real-git nested-worktree teardown tests are `slow` and no CI lane runs the slow marker — confirmed: `pyforge-marshal-test-slow` appears only at `pixi.toml:738`, nothing under `.github`; the coverage-gate scripts pass `"not slow"`. Predates the story (every end-to-end test in that file shares it). Deferred, ledger twin `DW-marshal-82-8`; I ran the two tests by hand and they pass.
  - `[low]` `[patch]` Verification Gap: the `keys_available and` guard on MRS-STATUS-014 is unpinned — confirmed by mutant (297 passed with the operand removed). Patched: `test_a_withheld_policy_already_degraded_the_home_so_014_never_fires`; the mutant now fails it.
  - `[false]` `[reject]` Intent Alignment (1): status expectations are exercised only with in-process fakes — `run_status` is the command's entry point and every test asserts the emitted JSON envelope, the convention of the whole file; `GitVcs.commit_subjects` is already used with the same ref constants by `deploy`.
  - `[medium]` `[defer]` Intent Alignment (2): the "no prunable entry" acceptance criterion lives only in slow tests — same defect as the Verification Gap deferral; carried.
  - `[false]` `[reject]` Intent Alignment (3): mutation evidence is only a memlog line — refuted: I ran the mutants myself on a copy in a scratch git repo with a green-baseline gate; all eight were killed (six on the first run, two on the patch round).
  - `[low]` `[reject]` Intent Alignment (4): "zero conforming" is read per slug, not repo-wide — same as the first Blind Hunter row.
  - `[low]` `[reject]` Intent Alignment (5): "examined 50" holds only when `origin/main` adds nothing — same as the `examined` row; deploy's own figure.
  - `[false]` `[reject]` Intent Alignment (6): `done` goes from `false` to `null` under 014 — `null` is the field's existing "landed-status unknown" value (MRS-STATUS-011 uses it); `false` would assert "unlanded" off a history that proves nothing, and the intent says 014 replaces the per-patch 010s, which fire only for `false`.
  - `[false]` `[reject]` Intent Alignment (7): the sweep-wide MRS-STATUS-011 is narrowed under `--escalations` — the Problem is alarms naming homes the filter dropped; the narrowed finding names only listed homes and is omitted when none remain; pinned by tests.
  - `[false]` `[reject]` Intent Alignment (8): MRS-STATUS-008 now depends on its home being listed — its code, message, severity and trigger are unchanged (the Never bullet), and the third acceptance criterion says no per-home finding names a filtered home; now pinned by a test.
  - `[false]` `[reject]` Intent Alignment (9): nesting is measured against the registered worktree path, not the computed home — removal and the existing dirty probe act on git's registered path, the same paths `git worktree list --porcelain` reports.
  - `[false]` `[reject]` Intent Alignment (10): no nested handling when no worktree is registered — the existing "leftover on disk" refusal fires first on that path, so there is nothing nested to check.
  - `[false]` `[reject]` Intent Alignment (11): the follow-up-review row of `_landing_superseded` still reads only the post-launch-tip range — it already reads `origin/main`, not local `main`; DW-FU-4-14-9 is about local-main-only reads.
  - `[false]` `[reject]` Intent Alignment (12): extra behaviours (probe failures block only an unforced teardown, a missing nested path is skipped, prune after a failed listing) — they mirror the home probe's own rule; no harm named.

## Auto Run Result

Status: done

**Summary.** `marshal status` now judges every landing from one history — `origin/main` (best-effort) then local `main` (required), concatenated as `marshal deploy promote` builds it — through `_read_landing_subjects`, shared by `_MainSubjects.read` and `_reconcile_ledger`. A non-empty history in which nothing conforms to a merge-subject pattern reads each patch of that home `done: null` with one `MRS-STATUS-014` (examined N, matched M) in place of the per-patch `MRS-STATUS-010`s. `--escalations` filters findings with the rows (sweep-wide ones stay; the sweep-wide `MRS-STATUS-011` names only listed homes). `marshal teardown` lists registered worktrees under the home, refuses without `--force` when one is dirty (naming each, under `MRS-TEARDOWN-003`), lets clean ones through, and prunes the registrations removal orphans.

**Files changed.**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py` -- the shared landing read, the 014 branch, findings filtered with rows, refreshed comments
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/init.py` -- nested-worktree refusal and prune in `run_teardown`, updated teardown help
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py`, `core/verdict.py` -- `MRS-STATUS-014` registered as WARN
- `src/shared/packages/pyforge-marshal/tests/unit/test_status.py`, `test_status_landing_superseded.py`, `test_init.py`, `test_findings.py`, `tests/integration/test_init_worktree.py` -- one test per acceptance criterion plus the review patches, and two real-git slow tests
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` -- DW-FU-4-14-9, -10, -12 and DW-1-8-5 closed; `DW-marshal-82-8` added for the deferred item
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md`, `spec-pyforge-core/.memlog.md` -- surface reconcile entries; no baseline stamped

**Review findings.** 37 findings. Patches applied: 4, all low (the `--escalations` / MRS-STATUS-008 test, the teardown help text, two stale comments, the 014-guard test). Deferred: 1 item on two rows (the slow-lane gap, medium, ledger twin `DW-marshal-82-8`). Rejected: 31, each with its reason in the triage log above.

**Follow-up review recommendation:** `false`. Patched entries at entry verdict: high 0, medium 0, low 4. No unverified risk is left that a second pass would settle.

**Verification performed.**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`: exit 0, 10061 passed, 1 skipped, 14 deselected (run after the patches).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`: exit 0, 130 passed, 3 skipped.
- `pixi run --frozen -e pyforge-guild lint-types`: exit 0.
- The two new real-git teardown tests (`-m slow -k nested`): exit 0, 2 passed.
- `python scripts/spec_surface_reconcile.py`: exit 0, no drift. `deferred-work-check`, `spec-surface-check`, `story-status-check`, `chain-completeness-check` and `ledger-regression-check`: all exit 0.
- Mutation, on a copy of the package in a scratch git repo (never the worktree, which auto-checkpoints), baselines green first: eight single-fix mutants, every one killed (local-main-only read in the sweep and in `--reconcile-ledger`; no 014 branch; unfiltered findings under `--escalations`; dirty nested worktree ignored; no prune after removal; the dropped 014 guard; MRS-STATUS-008 exempted from the filter).
- Not run: the full `pr-preflight` (it covers lanes this diff does not trigger beyond the ones above) and `pyforge-marshal-test-coverage`.

**Residual risks.**
- The real-git proof of "no prunable entry" lives in `slow` tests no CI lane runs (deferred, `DW-marshal-82-8`).
- `MRS-STATUS-014` counts per slug, so a repo with no templated merge subject and no native-shape merge for a project reads that project's patches `null`, not `false`.
- Pre-existing, untouched: the slow test `test_preflight_end_to_end_converges_seeds_and_acknowledges` fails on a hardcoded `harness_version: 0.11.0` against the installed bmad-loop 0.12.0.
