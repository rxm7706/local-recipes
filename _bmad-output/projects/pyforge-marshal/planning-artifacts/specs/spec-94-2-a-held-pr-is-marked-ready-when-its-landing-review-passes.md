---
title: "94.2: A held PR is marked ready when its landing review passes"
type: 'fix'
created: '2026-10-11'
status: 'in-progress'
baseline_revision: 'e9ee1dd23aba03d12006d6a6a1017966c7d7cd4c'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-83-18-a-re-dispatched-send-back-waits-for-its-landing-review.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_harness_done.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/forge.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/forge_gh.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_landing.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 83.18 holds a send-back's landing at a draft PR until the review is done. Its AC4 releases the hold
two ways: the operator marks the PR ready on GitHub, or the spec reads `landing_review: passed`. Only the first works.
Marshal marks a PR a draft and never marks one ready, so with `landing_review: passed` the landing skips the hold and
asks GitHub to merge a draft, which GitHub refuses. On 2026-10-11 steward 87.5's land-only re-dispatch refused that
way, and the PR was marked ready by hand. Line numbers below are at `c0956c0f14`.

**How the hold works.** `execute_dispatch_land` (`dispatch_land.py:1255`) judges the hold twice through
`resolve_hold_dispatch_landing` (`core/dispatch_harness_done.py:178`):
- Before it opens or updates the PR (`:1362`, with `pr_ready_for_review=None`). A held landing opens the PR as a draft
  (`create_pr(..., draft=hold_after_verify)`), or marks an existing ready PR a draft (`set_pr_draft(..., draft=True)`,
  `:1600`).
- After the check wait (`:1771`, with `pr_ready_for_review=not pr.is_draft`). A held landing keeps or makes the PR a
  draft (`:1779`), records `held_for_review` (`:1803`) and returns `HELD_FOR_REVIEW`. Otherwise it calls
  `forge.merge_pr` (`:1821`).

`landing_review_permits_merge` (`:167`) releases the hold when `landing_review_passed` (`:162`) reads `passed` or the
forge reports the PR is not a draft.

**What goes wrong.** Nothing in the package calls `set_pr_draft(..., draft=False)`. Its adapter,
`GhForge.set_pr_draft` (`adapters/forge_gh.py:268`-`:283`), already runs `gh pr ready <n> --repo <repo>` for
`draft=False`, and that branch has no caller. A spec that reads `passed` clears the hold at both judgements, so the
landing updates the PR (it stays the draft the held landing left) and calls `forge.merge_pr` on it. `gh pr merge` refuses
a draft. The merge fails, and the landing refuses with `MRS-DISP-020`.

**The evidence (the run journal, the branch and the PR timeline).**
- **The hold.** Steward 87.5's supervisor (run `pyforge-steward-20261011T085345666Z-55f786aa`) journaled a
  `dispatch-land` OUTCOME `held-for-review` for PR #2111 at 09:27:58Z. The PR was opened as a draft (its timeline has
  no `convert_to_draft` event).
- **The refusal.** The spec on `dispatch/pyforge-steward/87.5` reads `landing_review: 'passed'` and
  `status: 'in-review'`. The land-only re-dispatch journaled a verified `dispatch-verification` at 12:52:17Z, then
  refused with `MRS-DISP-020`: `gh pr merge 2111 ... --match-head-commit ad5b3126d1 ...` failed because the PR was
  still a draft. The land-only path journals no `dispatch-land` entry of its own; the refusal is in the dispatch
  command's envelope.
- **The workaround.** PR #2111's timeline shows `ready_for_review` at 13:12:38Z: `gh pr ready 2111`, run by hand.
- **The test that missed it.** `test_execute_dispatch_land_merges_after_landing_review_passed`
  (`tests/unit/test_dispatch_landing.py:3858`) uses `FakeForge`, whose `find_open_pr` returns `None`, so the landing
  opens a fresh PR that was never a draft. Its `merge_pr` also accepts a draft. No test lands a passed review over an
  existing draft.

**Approach:** release the draft at the one place the landing has decided to merge. Nothing else changes.
- In `execute_dispatch_land`, after the check wait and the hold decision at `:1771`, and immediately before
  `forge.merge_pr`: when `landing_review_passed(story_spec_text)` is true and `pr.is_draft` is true, call
  `forge.set_pr_draft(repo_ref, pr.number, draft=False)` and take its returned `PrInfo` as `pr`.
- On success, set `data["marked_ready_for_review"] = True`, then merge as today.
- When the call raises `ForgeCommandError`, or its answer still reads `is_draft`, refuse with `MRS-DISP-018` naming
  the PR. Never call `merge_pr` (AD-8). This is the shape of the existing draft-call failure at `:1779`-`:1800`.
- Journal the field on both callers, the same way `landing_checks` (`LANDING_CHECKS_FIELD`) already travels:
  - `dispatch_once`'s land-only path copies `marked_ready_for_review` from the landing envelope into its own `data`
    beside `land_verdict` (`cli/dispatch.py:3384`-`:3389`).
  - The supervisor's `dispatch-land` OUTCOME payload carries it when the landing envelope's data does
    (`dispatch_supervisor/__main__.py:2100`-`:2117`).
- **Unchanged:** `parse_landing_review`, `landing_review_requires_hold`, `landing_review_passed`,
  `landing_review_permits_merge` and `resolve_hold_dispatch_landing`; both hold judgements and the draft calls at
  `:1600` and `:1779`; the `ForgePort.set_pr_draft` signature and `GhForge`; every finding code (no new code;
  `MRS-DISP-018` is reused); the land-only spec gate of Stories 89.1 and 94.1; the check wait; the merge, its heal and
  the finalize.

Ledger key: `94-2-a-held-pr-is-marked-ready-when-its-landing-review-passes`.
Type / Effort / Deps: fix / S / 94.1 (the queue order the operator's fold implies; no code dependency).

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-marshal` CAP-169 (← `spec-marshal-single-story-dispatch` CAP-11): Story 29.2's
  land-only path, extended by Stories 83.7, 83.10 and 83.18. Story 83.18 added the landing hold and its AC4 release.
  This story realizes AC4's spec route, so it mints no CAP and changes no `SPEC.md`. CAP-229, the other CAP Story 94.1
  binds, is not bound here: the promotion does not change.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag: it restores behaviour Story 83.18
  promised, and a flag would keep the defect reachable.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, 2026-10-11 (a held PR is never marked ready).
  Operator ruling 2026-10-11, verbatim label: "Fold into 94.1 (Recommended)"; option text: "Widen marshal Story 94.1
  (not yet dispatched; both are land-only landing-review bugs): when landing_review is passed, land-only marks the PR
  ready before merging. Memlog decision + spec AC; no new epic." Story 94.1 had already been dispatched when the
  ruling arrived, so the fold is this second story in Epic 94, with no new epic (the `spec-pyforge-marshal` memlog
  records how the ruling was applied).

## Acceptance Criteria

The landing tests drive `execute_dispatch_land` with the fakes in `tests/unit/test_dispatch_landing.py`
(`FakeVcs(merged=False)`, `FakeProcess`, green check runs) and the `_seed_hold_spec` fixture. The forge fake for
this story (a subclass of `FakeForge`):
- returns an open PR from `find_open_pr` whose `is_draft` is the case's value (the PR a held landing left);
- records every forge call in order, including `check_runs`;
- flips its draft state on `set_pr_draft`;
- raises `ForgeCommandError` from `merge_pr` while the PR is a draft, as `gh pr merge` does.

- **AC1 — A passed review lands its held draft.**
  - **Given** an open draft PR for the branch, a spec that reads `landing_review: passed`, verification `VERIFIED`
    and green checks.
  - **When** `execute_dispatch_land` runs.
  - **Then** the forge receives exactly one `set_pr_draft(<n>, draft=False)`, after the last `check_runs` call and
    before `merge_pr`. `merge_pr` runs once, the verdict is `LANDED`, `envelope.data["marked_ready_for_review"]` is
    `True`, and the findings hold no `MRS-DISP-018` or `MRS-DISP-020`. (At `c0956c0f14` the same fixture refuses with
    `MRS-DISP-020`: `merge_pr` runs against the draft.)
  - **And** the quoted form `landing_review: 'passed'` that steward 87.5's spec carries gives the same result.
  - **And** `--hold-landing` (`hold_landing_cli=True`) with a spec that reads `passed` gives the same result: `passed`
    releases the hold, as `resolve_hold_dispatch_landing` already rules.
- **AC2 — A held story still holds.**
  - `landing_review: required` with an existing ready PR: the forge receives `set_pr_draft(<n>, draft=True)` and never
    `draft=False`. Nothing merges, the verdict is `HELD_FOR_REVIEW`, `held_for_review` is `True` and
    `marked_ready_for_review` is absent.
  - `landing_review: required` with an existing draft: no `set_pr_draft` call at all, and the landing holds the same
    way.
  - `--hold-landing` with no `landing_review:` key and an existing draft: held, and no `draft=False` call.
  - Story 83.18's landing tests (`tests/unit/test_dispatch_landing.py:3809`-`:3898`) pass unchanged.
- **AC3 — Nothing to mark, nothing marked.**
  - A spec that reads `passed` whose PR is not a draft (newly opened, or an existing ready PR): no `set_pr_draft`
    call, the verdict is `LANDED`, and `marked_ready_for_review` is absent.
  - An existing draft whose spec has no `landing_review:` key, with no `--hold-landing`: no `set_pr_draft(...,
    draft=False)` call. Marshal does not release a draft it was not told to release. The landing refuses with
    `MRS-DISP-020`, as at `c0956c0f14`.
- **AC4 — A failed ready call refuses.**
  - With AC1's fixture, when `set_pr_draft(..., draft=False)` raises `ForgeCommandError`: the verdict is `REFUSED`.
    One `MRS-DISP-018` names the PR number, `merge_pr` is never called, and `marked_ready_for_review` is absent.
  - The same holds when `set_pr_draft` returns a `PrInfo` whose `is_draft` is still `True`.
- **AC5 — The checks come first.** With AC1's fixture and a red check run (`MRS-DISP-056`) or a check-wait timeout
  (`MRS-DISP-057`): the landing refuses as at `c0956c0f14`, `set_pr_draft(..., draft=False)` is never called, and the
  PR is still a draft.
- **AC6 — The journal records it.**
  - `dispatch_once`'s land-only path copies `marked_ready_for_review` from the landing envelope into its own `data`.
    The test mirrors `test_harness_done_land_carries_the_landing_checks_record_into_the_command_data`
    (`tests/unit/test_dispatch.py:2336`).
  - The supervisor's `dispatch-land` OUTCOME payload carries `marked_ready_for_review: true` when the landing
    envelope's data does, and omits the key otherwise. The test sits beside the `landing_checks` journal tests in
    `tests/unit/test_dispatch_supervisor_spec_block.py`.
- **AC7 — Everything else is unchanged.**
  - The hold predicates in `core/dispatch_harness_done.py` and their tests are unchanged.
  - So are `ForgePort.set_pr_draft`, `GhForge` and the existing `FakeForge`.
  - No finding code is added, and every existing marshal test passes.
  - The dev names any changed expectation, with its reason, in the Spec Change Log.
- **AC8 — Mutation.**
  - Removing the ready call fails AC1: the fake's `merge_pr` refuses the draft (`MRS-DISP-020`).
  - Marking any draft ready, whatever its spec reads, fails AC2 and AC3.
  - Moving the ready call before the check wait fails AC5.
  - Merging after a failed ready call fails AC4.

## Boundaries & Constraints

**Always:**
- Release the draft through `ForgePort` inside `execute_dispatch_land`, at the edge (AD-4); the hold predicates in
  `core/` stay pure and unchanged.
- Treat a ready call that fails, or whose answer still reads draft, as a refusal (AD-8), never as a merge attempt.
- Reconcile every governed path the change touches on the memlogs of the Specs that govern it, then stamp those Specs
  scoped: `spec-pyforge-marshal`, plus every co-governor `spec-surface-check` names (`spec-pyforge-core` co-governs
  station `src/`) (AGENTS.md pre-PR item 5).

**Never:**
- Never mark a PR ready unless its spec reads `landing_review: passed`.
- Never change the hold rule, its predicates, the draft calls at `:1600` and `:1779`, the `ForgePort` signature or any
  finding code here.
- Never edit a story spec's `landing_review:` key, or a ledger key, to get past a hold.
- Never act on steward 87.5's PR #2111 (merged at `92e94afea2`) from this story.

**Residual risk:**
- The ready mark shows on GitHub before the merge. If the merge then fails (a conflict its heal cannot clear), the PR
  is left ready rather than a draft. The spec still reads `passed`, so the review the hold waited for is done, and a
  later re-dispatch merges it as today.
- No workflow under `.github/workflows/` triggers on `ready_for_review` at `c0956c0f14`, so the ready mark starts no
  new check runs on the head the wait just read. A workflow that adds that trigger later could make the merge race
  fresh runs.

## I/O & Edge-Case Matrix

| Spec `landing_review` | `--hold-landing` | PR at the landing | At `c0956c0f14` | After |
|---|---|---|---|---|
| `passed` | no | draft (a held landing left it) | merges a draft; `MRS-DISP-020` | marked ready, recorded, merged |
| `passed` | yes | draft | same as above (`passed` releases the hold) | marked ready, recorded, merged |
| `passed` | any | not a draft, or newly opened | merged | unchanged; no ready call |
| `passed` | no | draft; the ready call fails or still reads draft | not reached | `MRS-DISP-018`; nothing merges; still a draft |
| `passed` | no | draft; a check is red or the wait times out | `MRS-DISP-056` / `MRS-DISP-057` | unchanged; still a draft |
| `required` | any | not a draft | marked a draft; `held-for-review` | unchanged |
| `required` | any | draft | kept a draft; `held-for-review` | unchanged |
| absent | yes | any | a draft; `held-for-review` | unchanged |
| absent | no | draft | merges a draft; `MRS-DISP-020` | unchanged; marshal never marks it ready |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-11 (a held PR is never marked ready) entry.
- Epic: Epic 94, its second story. The operator ruled "Fold into 94.1 (Recommended)", with no new epic; Story 94.1
  had already been dispatched, so the fold is this story. Story 94.1 has since landed (`635508ffc4`), so `epic-94`
  reopens from `done` to `in-progress` while this story is open (the roll-up `sprint-ledger-sync` derives; doctor
  Story 41.5 admits it).
- Ledger key: `94-2-a-held-pr-is-marked-ready-when-its-landing-review-passes`.
- Ledger status at mint: `backlog`.
- Deps: 94.1, the queue order the fold implies; 94.1 is `done` (landed at `635508ffc4`), so the dep is met. No code
  depends on 94.1: it changes `adapters/vcs_git.py` and `ports/vcs.py`, and this story changes `dispatch_land.py`,
  `cli/dispatch.py` and `dispatch_supervisor/__main__.py`.
- Surface: `[epic_surfaces]` `"94"` in `marshal-policy.toml` (the default surface and every Spec memlog).
- Related: steward 87.5 landed at `92e94afea2` (PR #2111 merged at 13:43:16Z) only after the PR was marked ready by
  hand at 13:12:38Z.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `python scripts/spec_surface_reconcile.py` — expected: exit 0 (the derived surface guard).

**Manual checks (not a dispatch gate):**
- The four mutations of AC8 — expected: each fails its named test. Restore each.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconciles and the
  scoped stamps.
- `grep -n "draft=False" src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py` — expected: one
  call site, after the check wait and the hold decision and before `forge.merge_pr`.

## Named, not fixed here

- **A ready mark under `required` is re-drafted.** With the spec still at `landing_review: required`, an operator's
  ready mark on GitHub is undone at `:1600`, before the hold is judged again at `:1771`. A PR that is not a draft
  cannot be told apart from one opened before the send-back (herald 35.1's case, which Story 83.18 exists to stop), so
  the spec route (`landing_review: passed`) is the reliable release. This story makes that route work and does not
  change the forge route.
- **A draft left by `--hold-landing` alone.** A story held only by the flag, whose spec never gains a
  `landing_review:` key, still needs the operator's ready mark. That mark is Story 83.18's forge signal; marshal does
  not release a draft it was not told to release.
- **Steward 87.5** has landed (`92e94afea2`), after PR #2111 was marked ready by hand; nothing of it is left here.

## Spec Change Log

## Review Triage Log
