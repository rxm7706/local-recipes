---
title: '72.1: The dispatch supervisor reads merge facts from origin/main'
type: 'fix'
created: '2026-09-28'
status: 'backlog'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-67-1-a-landed-dispatch-reads-completed-when-the-primary-checkout-cannot-be-fast-forwarded.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `dispatch_supervisor/__main__.py::gather_dispatch_git_facts` reads one fact from two refs. It diffs from `_BASE_REF = ORIGIN_MAIN` (`:94`, `:340`) and reads each candidate spec's status at `origin/main` (`dispatch_core.spec_text_at_ref`, `:386`), but:
- `branch_merged` asks `vcs.is_branch_merged(repo_root, <resolved dispatch branch>, into=_MERGE_INTO)` with `_MERGE_INTO = "main"` (`:95`, `:371`), and `adapters/vcs_git.py::is_branch_merged` builds `refs/heads/{into}` itself (`:386`), so the port cannot be handed a remote-tracking ref;
- `story_merged_on_main` reads its merge subjects from `local_branch_ref(_MERGE_INTO)`, `refs/heads/main` (`:376`).

Local `main` moves only when finalize can fast-forward the primary checkout (Story 51.9), which it skips for a dirty primary or one not at `main`'s tip. With local `main` behind, a story merged by another route reads unmerged, and three decisions go wrong:
- the land trigger — verified, not `story_merged_on_main`, no landing journaled (`:1560-1573` and `:1647-1662`) — fires again;
- the stuck-land retry (`core/dispatch_supervisor_state.should_retry_stuck_land`, fed at `:1574-1579` and `:1657-1662`) counts it stuck;
- the exit decision (`supervisor_should_exit`, fed at `:1862-1866`) sees no merge.

`resolve_terminal_session_verdict` reads the same facts. The supervisor fetches `origin main` at start (`:1422-1425`) and every fifth tick (`_maybe_fetch_origin_main`, `:136-142`), but not between its own land and the re-gather that follows (`:1601-1611`, `:1683-1693`). CAP-276 (Story 67.1) makes the post-land verdict trust the landing it journaled; this story removes the local-`main` read that makes that necessary.

*(Widened 2026-09-28, operator ruling.)* `dispatch land` reads the same fact from local `main`: `dispatch_land.py::execute_dispatch_land` reads `main_subjects = vcs.commit_subjects(git_repo_root, local_branch_ref(_MERGE_BASE))` (`:687`, `_MERGE_BASE = "main"` at `:49`), refuses with `MRS-DISP-016` naming `main` when that read fails (`:688-701`), and answers ALREADY_LANDED when the key is among `promotion.corroborated_merged_story_keys` over those subjects (`:716-727`). The landing itself merges through the forge (`forge.find_open_pr` / `create_pr`, `:778-797`), so a story merged on GitHub reads unlanded until finalize fast-forwards the primary checkout, and `dispatch land` pushes and opens a PR for it again. The module already imports `ORIGIN_MAIN` (`:36`) and fetches `origin main` before its merge-tree preview (`:145`). The operator ruled that every merge fact the dispatch path judges moves to `origin/main` in this one story.

**Approach:**
- `VcsPort.is_branch_merged` (`ports/vcs.py`) gains a keyword-only full-ref target, for example `into_ref: str | None = None`. When given, `GitVcs.is_branch_merged` uses it verbatim in place of `refs/heads/{into}` for both the ancestry check and the patch-id fallback. The branch-name `into` form is unchanged for `cli/retire.py:362` and `cli/init.py:2438`. Every fake `VcsPort` that implements the method accepts the new keyword.
- `gather_dispatch_git_facts` calls `is_branch_merged(…, into=…, into_ref=ORIGIN_MAIN)` and reads subjects with `vcs.commit_subjects(repo_root, ORIGIN_MAIN)`. `_MERGE_INTO` is removed.
- At both call sites of `_land_or_journal_block`, the supervisor calls `vcs.fetch(repo_root, "origin", "main")` before the re-gather, swallowing `VcsCommandError` as `_maybe_fetch_origin_main` does.
- **`dispatch land` (widened 2026-09-28).** Before the ALREADY_LANDED read, `execute_dispatch_land` calls `vcs.fetch(git_repo_root, "origin", "main")`, swallowing `VcsCommandError` (the read then uses the last-fetched remote-tracking ref, never local `main`; the merge-tree preview's own fetch at `:145` still refuses a landing it cannot preview). It reads the subjects with `vcs.commit_subjects(git_repo_root, ORIGIN_MAIN)`; a failed read stays `MRS-DISP-016`, REFUSED, its message naming `origin/main` (`ORIGIN_MAIN_SHORT`). `_MERGE_BASE` stays the PR base (`ForgeRef(_MERGE_BASE)`), the fetch argument and the heal's `base`.
- Unchanged: CAP-276's journal-first rule (`_landing_succeeded` before `resolve_terminal_session_verdict`), `DispatchGitFacts`'s field names, the `VcsCommandError` handling of a failed gather (the tick continues; an unreadable `origin/main` is never a merged story), the fetch cadence.

Ledger key: `72-1-the-dispatch-supervisor-reads-merge-facts-from-origin-main`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / 67.1.

### Living CAP citations

- `spec-pyforge-marshal` CAP-280 (FR-227; widened 2026-09-28, operator ruling: `dispatch land`'s ALREADY_LANDED read moves too).
- Kinship: `spec-pyforge-marshal` CAP-276 (Story 67.1, the journal-first verdict this story no longer leans on); CAP-270 (Story 60.1, the full-ref reads).

## Acceptance Criteria

- Given a fake `VcsPort` whose `origin/main` subjects carry the story's corroborated merge subject (its spec `done` at `origin/main`) and whose local `main` subjects do not, the session verified and no landing journaled When the supervisor loop ticks Then `gather_dispatch_git_facts` returns `story_merged_on_main=True` and `branch_merged=True`, `_land_or_journal_block` is not called, `stuck_land_ticks` stays 0, and `supervisor_should_exit` is true for the tick's facts
- Given the reverse fixture (local `main` carries the merge, `origin/main` does not) When the gather runs Then both facts read false
- Given a land path through `_land_or_journal_block` When the supervisor re-gathers Then the fake records `fetch("origin", "main")` before the re-gather's `commit_subjects`
- Given a real repository with a bare remote where the dispatch branch is merged into `origin/main` but not into local `main` When `GitVcs.is_branch_merged(repo, branch, into="main", into_ref="refs/remotes/origin/main")` runs Then it returns true, and `is_branch_merged(repo, branch, into="main")` returns false
- Given `commit_subjects` at `ORIGIN_MAIN` raising `VcsCommandError` When the gather runs Then it raises as today and the loop continues without landing or exiting
- Given Story 67.1's fixtures (a land journaled `landed` with local `main` behind) When the suite runs Then they pass unchanged
- Given the gather reverted to local `main` When the lagging fixture runs Then a land is attempted and the test fails (mutation)
- Given a `dispatch land` fixture whose fake `VcsPort` holds the story's corroborated merge subject at `ORIGIN_MAIN` but not at `refs/heads/main` When `execute_dispatch_land` runs Then it returns ALREADY_LANDED with `already_landed: true`, calls neither `push` nor `create_pr`, and the fake records `fetch("origin", "main")` before `commit_subjects(ORIGIN_MAIN)` (widened 2026-09-28)
- Given the reverse `dispatch land` fixture (the merge at `refs/heads/main` only) When it runs Then it does not answer ALREADY_LANDED and proceeds to the push
- Given the fetch raising `VcsCommandError` When `execute_dispatch_land` runs Then it still reads `ORIGIN_MAIN`; given `commit_subjects(ORIGIN_MAIN)` raising `VcsCommandError` Then the result is REFUSED with `MRS-DISP-016` naming `origin/main`
- Given `dispatch land`'s read reverted to `refs/heads/main` When the first `dispatch land` fixture runs Then it pushes and the test fails (mutation)

## Boundaries & Constraints

**Always:** Implement only the Surface named in `epics.md` Story 72.1. Read every merge fact the supervisor and `dispatch land` judge from `core/refs.ORIGIN_MAIN`. Keep CAP-276's journal-first verdict first. Keep the port's branch-name form for its other callers; add the full-ref target as keyword-only.

**Never:**
- Do not read local `main` for any merge fact in the supervisor or in `dispatch land`'s ALREADY_LANDED check, and do not fast-forward or write the primary checkout from either.
- Do not treat an unreadable `origin/main` as merged, or an unmerged one as merged on a guess.
- Do not change `cli/retire.py`, `cli/init.py` or `dispatch_land_finalize`. In `dispatch_land.py` change only the ALREADY_LANDED read (`:687`), its fetch and its `MRS-DISP-016` message; `_MERGE_BASE` stays the PR base, the preview and heal paths are unchanged (widened 2026-09-28; the prior rule left `dispatch_land.py` untouched).
- Do not move the local-`main` reads outside the dispatch path (`cli/status.py`, `cli/deploy.py`, `cli/retire.py`, `supervisor/__main__.py`); they are not this story's (recorded as an open question in the Spec's memlog).
- Do not change the fetch cadence (`_FETCH_EVERY_N_TICKS`) beyond the one post-land fetch.
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`; do not run `scripts/bmad-switch`.

Co-governing Specs: `spec-pyforge-marshal` (owner of `src/shared/packages/pyforge-marshal/**`) and `spec-pyforge-core` (co-governs every station's `src/`) — reconcile each one the spec-surface detector names.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| merged on `origin/main`, local `main` lags | verified, no landing journaled | merged facts true; no land; exit allowed | none |
| merged locally only | `origin/main` without the merge | merged facts false | none |
| own land just ran | `_land_or_journal_block` returned | fetch `origin main`, then re-gather | a failed fetch is tolerated |
| `origin/main` unreadable | `VcsCommandError` from the gather | tick continues; no land, no exit on that tick | as today |
| landing journaled `landed` | CAP-276 path | COMPLETED from the journal first | unchanged |
| retire / init callers | branch-name `into` | `refs/heads/<into>` as today | unchanged |
| `dispatch land`, merged on `origin/main`, local `main` lags | corroborated subject at `ORIGIN_MAIN` only | ALREADY_LANDED; no push, no PR | none |
| `dispatch land`, merged locally only | subject at `refs/heads/main` only | proceeds to land | as today |
| `dispatch land`, fetch fails | `VcsCommandError` from `fetch` | reads the last-fetched `ORIGIN_MAIN` | tolerated |
| `dispatch land`, `origin/main` unreadable | `VcsCommandError` from `commit_subjects` | REFUSED | `MRS-DISP-016` naming `origin/main` |

</intent-contract>

## Source

Contract authored from the operator's 2026-09-28 direction, `docs/dreams/pyforge-marshal.md`'s 2026-09-28 entry (*the dispatch supervisor judges a merge from `origin/main`*) and `spec-pyforge-marshal` CAP-280 with its 2026-09-28 direction entry in the Spec's `.memlog.md` (the file:line evidence), decomposed the same session as Epic 72's mint. Widened the same day from the operator's ruling that `dispatch land`'s ALREADY_LANDED read moves too (the Spec's `.memlog.md` decision entry of 2026-09-28 and CAP-280's widened text).

## Binding

Parent Spec capability: `spec-pyforge-marshal` CAP-280 (FR-227).
Ledger key: `72-1-the-dispatch-supervisor-reads-merge-facts-from-origin-main`.
Ledger status at mint: `backlog`.
Deps: Story 67.1 (`67-1-a-landed-dispatch-reads-completed-when-the-primary-checkout-cannot-be-fast-forwarded`) — the same function region; land it first so its journal-first fixtures pin the verdict this story's re-gather feeds.
Widened 2026-09-28 (operator ruling): `dispatch_land.py`'s ALREADY_LANDED read; key, status and Deps kept.
Policy: no `[epic_surfaces]` entry; the Surface, including `dispatch_land.py`, is inside marshal's default surface.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
