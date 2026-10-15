---
title: "102.1: A landing reuses its verified verdict when only a merge of main moved the branch"
type: 'fix'
created: '2026-10-15'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/schemas/policy.json
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verification_journal.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_landing.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_harness_done.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** when a dispatch's PR conflicts with `main`, someone merges `main` into the dispatch branch, the head
moves, and the story is re-landed through the land-only path. That path re-runs the station's whole
`verify_commands` (station suite, coverage gate, `lint-types` and the derived whole-tree checks) before it waits for
GitHub CI again, even when not one byte of the story's own code changed. Line numbers are at `fccf4f3ee7`.

- **The seam.** A re-dispatch whose latest run journaled a refused (or held) landing, or a verification refusal with a
  moved head, takes the land-only path: `dispatch_once` (`cli/dispatch.py:3402`, `should_take_harness_done_land_only`
  and `should_take_verification_refusal_land_only`) calls `_attempt_harness_done_cap4` (`:1296`), whose
  `_verification_verdict_for_cap4` (`:1185`) runs the three pre-verify passes and then `evaluate_dispatch_verification`
  in full, every time. The fleet drain's campaign supervisor re-runs the same `dispatch_once`, so both re-landers meet
  here. The supervisor verifies once per run (`_run_and_journal_verification`, `dispatch_supervisor/__main__.py:2526`)
  and never re-lands after a refused landing.
- **What the journal cannot say today.** A `dispatch-verification` OUTCOME (`dispatch_verification_journal.py:105`)
  records the verdict and the failed gate but not the head it judged, so no later reader can tell whether a verified
  verdict still describes the branch.
- **The cost, measured from steward's 2026-10-14 run journals.** Steward 99.6 (`fb66b9e1`) was verified at 06:29:06,
  its landing refused at 06:31:22 on an unknown memlog conflict (MRS-DISP-038), and after `main` was merged in, its two
  land-only re-verifications took until 06:50:43 and 07:17:23 and both refused, on `pyforge-steward-test` (exit 1) and
  `deferred-work-check` (exit 2). Steward 102.1 (`13b43142`) was verified at 20:35:26 on `fbb3ee095b`; its landing then
  pushed two reconcile stamps (`9da5f985d4`, a memlog line; `3d6908f191`, `scripts/.spec-surface-baseline.json`) and
  refused (MRS-DISP-047, MRS-DISP-020), and `main` was merged in as `b937a1371e`, whose one conflict (replayed with
  `git merge-tree`) was `spec-pyforge-herald/.memlog.md`. Nothing in that chain touched the story's code, yet a re-land
  would have re-run everything. Steward 103.1's re-verification took about 52 minutes and then hit a load flake
  (coordinator report, 2026-10-15). Each landing makes every other open branch stale, so serial landing multiplies it.

**Approach:**
- **The setting.** A new key in marshal's closed `dispatch` policy block: `landing_reverify`, one of `"always"` (the
  default: today's behaviour) or `"on-code-change"`. `_valid_dispatch_block` validates it like the block's other keys,
  so any other value (a typo, a bool, an empty string, another case) is `MRS-POLICY-002` naming `dispatch` and the
  layer is skipped, falling back to the layer below and floored at `"always"`. `resolve_landing_reverify` reads it at
  the consumer, as `resolve_landing_check_settings` reads the check-wait knobs. `schemas/policy.json`'s `dispatch`
  description names it.
- **The head a verdict judged.** Every `dispatch-verification` OUTCOME gains `mode` (`"full"` or `"reused"`) and, when
  the worktree was clean right after the verification, `head_sha`, the worktree `HEAD` it judged. The supervisor's
  `_run_and_journal_verification` and the land-only `_journal_cap4_verification` both record it through the shared
  builder. A dirty tree records no head, so its verdict can never be reused.
- **The decision, pure (`core/dispatch_reverify.py`).** The candidate is the run's latest `dispatch-verification`
  OUTCOME: it must read `verified`, and either be a full verification carrying `head_sha` (V), or a reused one, whose
  own `reused_verification_id` and `reused_head_sha` name the full verdict it reused. A reused verdict is never itself
  reused: V is always the head of a full, independent verification. Given V, the current head H (the worktree clean),
  the story's own diff (`git diff --name-only --no-renames origin/main...V`) and the first-parent chain from H down to
  V, the reuse is **exempt** when:
  - H equals V (`basis: head-unchanged`), or every commit on the chain is one of (`basis: merge-of-main`):
    - **a merge of main:** exactly two parents, the second an ancestor of `refs/remotes/origin/main`; replaying it
      (`git merge-tree --write-tree P1 P2`) reports no conflict in a non-planning path; its first-parent diff
      (`P1..M`) touches no non-planning path of the story's own diff; and its tree differs from the replay only in
      planning paths (no hand-made change outside them);
    - **a planning-only commit:** one parent, every changed path a planning path (marshal's own reconcile stamps and
      memlog unions land this way, as on steward 102.1's branch);
  - and the story's own diff is not empty.

  A **planning path** is under `_bmad-output/projects/*/planning-artifacts/`, `docs/dreams/` or `.claude/memory/`, any
  `.memlog.md` or `deferred-work-ledger.md`, or `scripts/.spec-surface-baseline.json`, except every
  `marshal-policy.toml` (it holds the verify commands) and the story's own tracked spec (its success signal and
  declared surface bind the verification). Anything else is **not exempt** and names one reason:
  `no-verified-verdict`, `dirty-worktree`, `no-story-diff`, `not-on-first-parent-chain`, `story-commit`,
  `octopus-merge`, `merge-not-of-main`, `merge-conflict-outside-planning`, `merge-touches-story-file`,
  `merge-resolution-outside-planning`, `git-read-failed`.
- **The git reads (`dispatch_verify.py`, beside the commit checks).** Read-only `git` through the `ProcessPort`
  seam, as `check_branch_commit_attribution` reads (`gather_reuse_facts`): one `rev-list --first-parent --parents V..H`, the story diff,
  and per chain commit its first-parent diff, plus, for a merge, `merge-base --is-ancestor`, `merge-tree` and a tree
  diff. A walk longer than 64 commits, or one that does not end on V, is `not-on-first-parent-chain`.
- **The narrow re-check.** When exempt, the land-only path runs the full verification's own planning-surface commands
  and its two commit checks, never the station's suites: `python scripts/spec_surface_reconcile.py` (the S-13.7 guard,
  the same `gather_spec_surface` verdict as `spec-surface-check`), `pixi run --frozen -e pyforge-guild
  story-status-check`, `pixi run --frozen -e pyforge-guild deferred-work-check`, `check_branch_commit_attribution` and
  `check_unsanctioned_cfe_commits` (the merge commits are new, and no reused verdict judged their messages). All
  green: the verdict is reused. Any red: the reuse is declined (`recheck-failed`) and the full verification runs, so
  the shortcut can never refuse a landing the full path would pass.
- **The journal.** A reused verdict is one `dispatch-verification` INTENT/OUTCOME pair in the run's journal: `verdict:
  verified`, `ok: true`, `mode: reused`, `head_sha` H, `reused_verification_id` (the full verdict's `{writer_id,
  counter}`), `reused_head_sha` V, `reuse_evidence` (the basis, the story diff's size and, per chain commit, its kind,
  the merge's second parent, the count of paths main brought, and the planning conflicts and resolutions; offloaded to
  a sidecar like `scope_violation_advisories` when large) and the reused verdict's own scope advisories. A declined
  reuse under `"on-code-change"` adds `reuse_declined: {reason, detail}` to the full verification's OUTCOME. The
  dispatch envelope's data gains `verification_mode`.
- **Landing is unchanged.** The reused verdict goes to `execute_dispatch_land` as `VERIFIED`, which then pushes, waits
  for the PR head's checks (Story 80.1) and refuses on a red one (`MRS-DISP-056`) exactly as today.
- **Opt in.** `[dispatch] landing_reverify = "on-code-change"` goes into the tracked `marshal-policy.toml` of herald,
  steward, atlas and doctor, the four Pages stations, as the operator's speed ask. Marshal, mason, scribe and warden
  keep the default.

**Why this keeps CAP-161's "no landing on self-report":** the reused verdict is marshal's own independent verification
(CAP-161 / single-story-dispatch CAP-3), never a session's report. Under the exemption every non-planning path of the
story's own diff is byte-identical at H and at V, and every other non-planning change came from `main`, which landed
only through its own verification and green CI. The combined tree is still judged by GitHub CI on the PR head before
any merge (CAP-284), and the planning files the merge touched are re-checked by the narrow re-check. What the reuse
gives up is a second local run of the station's suites over main's new code beside the story's unchanged code; CI
arbitrates that, as the operator ruled for this push path.

**Adjustments to the brief, with reasons:**
- **`[dispatch] landing_reverify`, not a new `[landing]` table.** Marshal's policy vocabulary is closed at 35 keys
  (`schemas/policy.json`, `additionalProperties: false`), and the dispatch landing's other knobs (`landing_check_*`,
  Story 80.1; `verify_fix_*`, Story 85.1) already live in the closed `dispatch` block, whose validator refuses an
  unknown value. A `landing` key would widen the vocabulary, and the top-level `landing_*` keys are AD-40's `marshal
  land` keys, a different engine. The block is never rendered into bmad-loop's `policy.toml`, so `bmad_loop.policy`
  never sees it.
- **The default is Marshal's built-in default, not `_bmad-output/policy-defaults.toml`.** A repo-defaults `[dispatch]`
  block would replace the code default's whole block for every station without one (`_merge_field` replaces a block
  whole), and `compose_dispatch_policy` never reads that layer.
- **Planning-only commits are allowed on the chain.** The landing's own spec-surface reconcile (MRS-DISP-047) and the
  heal's memlog unions commit planning files after the verified head; steward 102.1's real branch carries two. They
  are the files the narrow re-check judges.
- **Planning overlap and planning conflicts are allowed.** The brief's "touches no file in the story's own diff" read
  literally would decline every merge that conflicts on a memlog the story appended to, the commonest case. Only the
  non-planning part of the story's diff must be untouched; the narrow re-check judges the rest.
- **An unmoved head reuses its own verdict.** "On code change" with no change at all is the plainest reuse (a landing
  refused on a red check and re-run, steward 99.2's case). It is still narrow-checked and still waits for CI.
- **The narrow re-check is the full verification's own planning-surface commands plus `story-status-check`.**
  `spec-surface-check` runs as the S-13.7 guard script (the same verdict, no pixi start, the constant the full
  verification already uses). `deferred-work-check` joins because the full verification runs it over the deferred-work
  ledgers a merge unions. The commit checks join because a reused verdict never saw the merge commits.
- **A red narrow re-check declines the reuse instead of refusing.** The full verification never runs
  `story-status-check`, so refusing on it would turn a landing the full path passes into a refusal.
- **`type: fix`, no flag.** The defect is the re-landing that re-runs a verification its own journal already answers,
  then flakes and refuses a verified story. Under `spec-feature-flag-governance` Q1 a `fix` carries no flag, and the
  operator ruled "this story adds no flag; use a marshal policy key". The key's default keeps today's behaviour.
- **No SKILL.md edit.** `.claude/skills/pyforge-marshal` documents no landing.
- **The git reads live in `dispatch_verify.py`, not a new top-level module** (decided while implementing). A new
  `pyforge.marshal.*` module must be listed in the AD-3 import contract in the package `pyproject.toml`
  (`test_ad3_source_modules_cover_every_submodule_except_adapters`), and a `pyproject.toml` change moves the chain's
  code stage past the PRD, the spine and the last retro (`chain-currency-sweep-check`: `behind-code` for the PRD and
  spine, the code→retro edge). `dispatch_verify.py` already holds the verify-command runner and both commit checks the
  narrow re-check runs, so the reads sit beside them and no contract or chain stage moves.

**Rejected:**
- **Diffing `V..H` alone.** A merge of main changes hundreds of files; the diff cannot tell main's changes from a
  story edit made in the merge.
- **Trusting a merge's first-parent diff without replaying it.** A modify/delete conflict resolved by keeping the
  story's file leaves both the first-parent diff and the tree diff empty; only the replayed conflict shows it.
- **Reusing a reused verdict as the base.** The chain would then hang on a verdict no full verification produced.
- **Refusing on a red narrow re-check.** See above.
- **A flag.** See above.

Ledger key: `102-1-a-landing-reuses-its-verified-verdict-when-only-a-merge-of-main-moved-the-branch`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- **`spec-pyforge-marshal` CAP-161** (← `spec-marshal-single-story-dispatch` CAP-3, FR-193): verification is the
  product; before any landing the driver itself runs the gates, and no landing occurs on self-report. This story lets
  a re-landing reuse the driver's own verdict when the story's code is unchanged. It mints no CAP and changes no
  `SPEC.md` text.
- **`spec-pyforge-marshal` CAP-162** (← single-story-dispatch CAP-4): the landing composes the existing machinery,
  unchanged. **CAP-284:** the landing waits for its PR's checks and refuses on a red one, unchanged. **CAP-7:** policy
  composition, the validation this key rides.
- **AD-4:** the decision is pure in `core/`; the git reads live outside `core/`. **AD-16:** the key composes through
  the four layers.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, the 2026-10-15 (a landing re-verifies when only main
  moved) entry; the operator's rulings of 2026-10-15.

## Acceptance Criteria

- **AC1 — The key.** `compose` accepts `dispatch.landing_reverify` of `"always"` and `"on-code-change"` with no
  finding; Marshal's default `dispatch` block carries `"always"`; a block whose value is any other string, a bool, an
  int or `None` is `MRS-POLICY-002` naming `dispatch` and falls back to the layer below. `resolve_landing_reverify`
  reads `"always"` for an absent key and for a stored value that bypassed validation. Composing each of the four
  stations' tracked `marshal-policy.toml` gives no `MRS-POLICY-002` and resolves `"on-code-change"`; marshal's
  resolves `"always"`.
- **AC2 — The head is recorded.** A `dispatch-verification` OUTCOME from the supervisor and from the land-only path
  carries `mode: "full"` and, when the worktree was clean after verification, `head_sha` equal to its `HEAD`. A dirty
  worktree's OUTCOME carries no `head_sha`.
- **AC3 — The exemption, on a scratch git repository.** With real `git`:
  - (a) a merge of main that changed only files outside the story's diff → exempt, `basis: merge-of-main`;
  - (b) a merge whose only conflict was a memlog both sides appended to, resolved by union, followed by a
    baseline-only commit → exempt;
  - (c) a commit after V that changes a file of the story's diff → `story-commit`;
  - (d) a merge with a content conflict in a code file → `merge-conflict-outside-planning`; and a modify/delete
    conflict on a story code file resolved by keeping the story's version → `merge-conflict-outside-planning`;
  - (e) a merge in which main changed a story code file without conflict → `merge-touches-story-file`;
  - (f) a merge with a hand-made change to a non-story code file → `merge-resolution-outside-planning`;
  - (g) a merge of a branch not on `origin/main` → `merge-not-of-main`;
  - (h) H equal to V → exempt, `basis: head-unchanged`;
  - (i) a change to `marshal-policy.toml` or to the story's own spec is not a planning change.
- **AC4 — The candidate.** `latest_reusable_verdict` returns none for a run with no OUTCOME, a latest OUTCOME that
  reads `refused`, or a full OUTCOME without `head_sha`; it returns the full verdict's id and head for a latest full
  OUTCOME, and for a latest reused one it returns the verdict that one reused.
- **AC5 — The land-only path reuses.** With `on-code-change`, a run journal holding a verified OUTCOME with `head_sha`
  V and the worktree at a merge-only H, `dispatch_once`'s land-only path never calls `evaluate_dispatch_verification`,
  runs the narrow re-check, journals an OUTCOME with `verdict: verified`, `ok: true`, `mode: reused`, `head_sha` H,
  `reused_verification_id` naming V's OUTCOME, `reused_head_sha` V and `reuse_evidence.basis` `merge-of-main`, and
  hands `execute_dispatch_land` `VERIFIED`.
- **AC6 — Declines re-verify in full.** A red narrow re-check runs the full verification and its OUTCOME carries
  `mode: full` and `reuse_declined.reason` `recheck-failed`; a non-exempt chain (a story commit) does the same with its
  reason; no prior verified verdict does the same with `no-verified-verdict`.
- **AC7 — `"always"` is unchanged.** With the key absent or `"always"`, the land-only path calls
  `evaluate_dispatch_verification` even when the exemption would hold, makes no reuse git read, and the OUTCOME
  carries `mode: full` and no `reuse_declined`.
- **AC8 — Mutation.** Each change fails a named test, and the Auto Run Result records which: dropping the replayed
  conflict check (AC3 d, the modify/delete case); treating a single-parent commit that changes a story file as exempt
  (AC3 c); ignoring the policy mode (AC7).
- **AC9 — Landing untouched.** `dispatch_land.py` is not edited: the check wait and `MRS-DISP-056` run on a reused
  verdict exactly as on a full one.

## Boundaries & Constraints

**Always:**
- Reuse only a full, independent verification's verdict, and only when the worktree is clean.
- Re-verify in full on any doubt: an unreadable git fact, an unknown chain shape, a red narrow re-check.
- Await GitHub CI on every landing.
- Reconcile every governed path on the memlogs of the Specs that govern it (`spec-pyforge-marshal`, and
  `spec-pyforge-core`, which co-governs station `src/`), then stamp scoped (AGENTS.md pre-PR item 5).

**Never:**
- Never land on a session's self-report, and never reuse a refused verdict.
- Never edit `dispatch_land.py`'s check wait or `MRS-DISP-056`, and never skip the CI wait.
- Never add a flag, a CAP or a `SPEC.md` text change; never edit `AGENTS.md` or `flags.json` (steward 103.6 owns
  them).
- Never write git state from the decision: every git call it makes is a read (`merge-tree --write-tree` writes only
  unreferenced objects, as the landing's own merge preview does).

**Residual risk:**
- A reused verdict never ran the station's suites over main's new code beside the story's code. A semantic break
  between them reaches only GitHub CI, which every landing awaits.
- A verdict journaled before this story lands carries no `head_sha`, so the three dispatches in flight today
  re-verify in full, as they do now.
- `merge-tree` replays with today's git; a merge made by a git with different conflict rules could replay
  differently, and any extra conflict it reports declines the reuse.

## I/O & Edge-Case Matrix

| Since the verified head V | Decision |
|---|---|
| nothing (H = V) | exempt, `head-unchanged` |
| merges of main, conflicts only in planning paths, no story code touched | exempt, `merge-of-main` |
| a planning-only commit (a reconcile stamp, a memlog union) and merges of main | exempt, `merge-of-main` |
| any commit changing a non-planning path | `story-commit` |
| a merge with a code conflict, including modify/delete | `merge-conflict-outside-planning` |
| a merge in which main changed a story code file | `merge-touches-story-file` |
| a merge with a hand-made non-planning change | `merge-resolution-outside-planning` |
| a merge whose second parent is not on `origin/main` | `merge-not-of-main` |
| a merge with three or more parents | `octopus-merge` |
| V not on H's first-parent chain, or more than 64 commits | `not-on-first-parent-chain` |
| a dirty worktree | `dirty-worktree` |
| no verified OUTCOME with a `head_sha`, or the latest OUTCOME refused | `no-verified-verdict` |
| a git read fails | `git-read-failed` |
| exempt, narrow re-check red | `recheck-failed`, full verification |
| policy `"always"` or absent | full verification, no reuse read |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-marshal` CAP-161 (← `spec-marshal-single-story-dispatch` CAP-3, FR-193). No
  CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-15 (a landing re-verifies when only main
  moved) entry.
- Epic: Epic 102 (new), minted with this story, because Epic 101 is a different concern and still `backlog`.
  `epic-102` and `epic-102-retrospective` are minted with it.
- Ledger key: `102-1-a-landing-reuses-its-verified-verdict-when-only-a-merge-of-main-moved-the-branch`.
- Deps: —.
- Surface: `marshal-policy.toml` `[epic_surfaces]."102"`, added with this mint.
- Minted 2026-10-15 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, with AC1–AC7's tests (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_reverify.py src/shared/packages/pyforge-marshal/tests/unit/test_policy.py -q` — expected: pass.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `python3 scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps.
- The three mutations of AC8 — expected: each fails its named test. Restore each.
- `git diff origin/main...HEAD --stat -- src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py` — expected: empty (AC9).

## Spec Change Log

- 2026-10-15: minted from the Dream entry of 2026-10-15 (a landing re-verifies when only main moved) at the operator's
  rulings "chain it now and I'll mint the story chain and implement it" and "make sure we include this - Optional,
  marshal: a landing re-verification setting". `type: fix`, no flag, no CAP.
- 2026-10-15: implemented and moved to `in-review`. The git reads and the narrow re-check sit in `dispatch_verify.py`,
  not a new top-level module (see Adjustments), so no import contract or package `pyproject.toml` moves.

## Review Triage Log

- No review has run yet.

## Auto Run Result

Status: in-review (hand-implemented on `chain-marshal-102-1-landing-reverify-on-conflict-2026-10-15`; an independent
reviewer follows).

Summary: `dispatch.landing_reverify` (`"always"` by default, or `"on-code-change"`) is validated in the closed
`dispatch` block. Every `dispatch-verification` OUTCOME records `mode` and, on a clean tree, `head_sha`. Under
`"on-code-change"` the land-only path reuses the run's latest full verified verdict when only merges of main and
planning-only commits moved the branch, after a narrow re-check; anything else re-verifies in full, with
`reuse_declined` naming the reason. `dispatch_land.py` is untouched. Herald, steward, atlas and doctor opt in.

Files: `core/policy.py`, `schemas/policy.json`, `core/dispatch_reverify.py` (new), `dispatch_verify.py`,
`dispatch_verification_journal.py`, `cli/dispatch.py`, `dispatch_supervisor/__main__.py`, `cli/config.py` (stale
dispatch-block comments: the block has eight keys, not five); tests `tests/unit/test_dispatch_reverify.py` (new),
`tests/unit/test_policy.py`, `tests/unit/test_dispatch_supervisor_verify_fix.py` (its pinned "main's OUTCOME keys"
gain `mode`); the four stations' `marshal-policy.toml`.

Verification (solo lanes, each exit code read from `$?`):
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — exit 0 (13139 passed, 20 skipped).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — exit 0 (130 passed, 3 skipped).
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` — exit 0 (6 touched modules ≥ 80%:
  `core/dispatch_reverify.py` 97%, `dispatch_verify.py` 93%, `dispatch_verification_journal.py` 98%,
  `core/policy.py` 92%, `dispatch_supervisor/__main__.py` 93%, `cli/dispatch.py` 85%).
- `pixi run --frozen -e pyforge-guild lint-types` — exit 0.
- `chain_currency_sweep_check.py --project pyforge-marshal` — exit 0, after the move (with a `pyproject.toml` change
  it read `behind-code` for the PRD and spine).
- `spec-surface-check` — exit 0 after the memlog entries and the scoped stamps of `pyforge-marshal/spec-pyforge-marshal`
  and `pyforge-marshal/spec-pyforge-core`.
- `git diff origin/main...HEAD --stat -- .../marshal/dispatch_land.py` — empty (AC9).

Mutations (AC8), each restored after its run:
- Dropping the replayed conflict check (`code_conflicts = []`): exit 1.
  `test_a_modify_delete_conflict_kept_as_the_story_s_file_re_verifies` fails because the decision is now exempt.
  `test_a_content_conflict_in_code_re_verifies` fails because the reason becomes `merge-touches-story-file`.
- Treating a single-parent commit that changes a story file as exempt (`outside = []`): exit 1. These fail:
  `test_a_story_file_change_after_the_verified_head_re_verifies`,
  `test_a_policy_or_story_spec_change_is_never_a_planning_change` and
  `test_a_story_commit_declines_the_reuse_and_re_verifies_in_full`.
- Ignoring the policy mode (no `"always"` early return): exit 1. Both cases of
  `test_always_re_verifies_in_full_and_reads_no_reuse_fact` fail.

Real history: replayed with `gather_reuse_facts` and `judge_verdict_reuse` against `7555e62f3e` as `origin/main`,
steward 102.1's branch `fbb3ee095b → b937a1371e` reads exempt (`merge-of-main`). Its three commits are the two
planning-only reconcile stamps and the merge, whose one planning conflict is `spec-pyforge-herald/.memlog.md`. The
story's own fix, `→ 0fea7f20e0`, reads `story-commit` (`.github/workflows/pages.yml` and its meta test).

Residual risk: as in Boundaries. A supervisor still running the old code composes a `[dispatch]` block that holds
`landing_reverify` as `MRS-POLICY-002` and falls back to the default block until it restarts. For herald, atlas and
doctor that default is what they had. For steward it is the 15-minute fix turn; no steward dispatch is live.
