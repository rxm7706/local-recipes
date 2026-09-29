---
title: 'marshal seed adopt'
type: 'feature'
created: '2026-08-21'
status: 'done'
baseline_revision: '573d2861ea837276b9d1f1d56898ab58af23dfa6'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: [oversized]
---

<intent-contract>

## Intent

**Problem:** `marshal seed adopt` (`cli/seed.py::run_adopt`) is a Story-7.1 stub that always
prints "not yet implemented" and exits 0, so a brownfield repo has no way to layer the seed model
on without a human hand-wiring every artifact.

**Approach:** Add `seed/verbs/adopt.py`, orchestrating the already-landed foundation
(`detect.inventory.classify`, `plan.build.build_plan`, `verbs.preconditions.check_preconditions`,
`verbs.skips`, `apply.run.run_apply`, `state.store.write_state`) into `resolve → detect → plan →
confirm → apply → state-write`, mirroring `seed/verbs/check.py`'s detect+plan composition pattern
but adding the write side. Wire `cli/seed.py::run_adopt` with `--apply`/`--yes`/`--agents`/
`--repo-root`/`--skip`/`--force` flags, matching `run_check`'s established shape (manifest
injection seam, `SeedError` exit-code mapping, the widened try/except backstop from the 10.5
review).

## Boundaries & Constraints

**Always:**
- No flags (dry-run, the default): `detect → plan` runs, the plan is written to
  `.marshal/plan.json` via `plan.build.write_plan`/`default_plan_path` (FR-82 — a plan IS written
  to disk in dry-run, unlike `check`, which never writes anything at all) and printed, but no
  OTHER repo file changes and no `.marshal/seed-state.yml` write.
- `--apply` executes the plan via `apply.run.run_apply`; without `--yes`, `--apply` prompts for
  confirmation on stdin before applying (this package's CLI has zero existing interactive-prompt
  precedent anywhere else — this is a deliberate, first-of-its-kind confirmation gate, not a
  reused pattern). `--yes` skips the prompt (unattended/CI use). The confirmation mechanism must
  be an injectable seam (a `confirm: Callable[[], bool]` parameter on the verb function, defaulted
  by the CLI layer to a real `input()`-based implementation) — mirroring `run_check`'s existing
  `manifest=` test-injection convention — so tests never block on real stdin. A closed/EOF stdin
  during a real prompt is treated as "no" (abort, refuse to apply), never a hang or a crash.
- `present-legacy` artifacts are preserved and recorded in `state.legacy[]`, never modified
  (FR-81) — `check`'s own `PRESENT_LEGACY` short-circuit is the precedent.
- **The FR-83/FR-84 interaction (the one genuine gap `build_plan` does not close — read this
  carefully):** `build_plan` (Story 9.6, already shipped and heavily tested — do not modify it)
  never emits an `Action` for a `PRESENT_CONFORMANT` classification, for ANY class, including
  `copied-managed`/`generated-derived` (confirmed by direct reading of `plan/build.py`'s
  `_ACTIONABLE_STATES` gate and its own module docstring: "`PRESENT_CONFORMANT` and
  `PRESENT_LEGACY` never [produce an Action]"). `detect.inventory.classify` also has no
  `state` parameter at all — it cannot see `state.managed[]`, so it cannot distinguish "already
  adopted, up to date" from "never adopted, something happens to already exist at this path."
  FR-83 requires the second case (copied-managed/generated-derived, present, but NOT yet a
  Genesis-owned artifact) to be overwritten/claimed, not preserved — a repo being adopted
  brownfield may already have an unrelated file at a `generated-derived` artifact's path, and
  Genesis must claim it, not defer to whatever was there. FR-84 simultaneously requires a SECOND
  adopt on an unchanged repo to produce an EMPTY plan. These are compatible, not contradictory,
  ONLY if the forced-claim behavior is gated on the ABSENCE of an existing `state.managed[]`
  record for that entry's id — fires once, on first adopt; never fires again once the artifact is
  tracked (`state.managed[]` has a record for it), at which point ordinary `build_plan` behavior
  (no `Action` for `PRESENT_CONFORMANT`) already delivers FR-84's idempotence for free. Implement
  this as a narrow, separately-tested augmentation in `seed/verbs/adopt.py` — e.g.
  `_augment_plan_with_first_claims(plan, inventory, manifest, state) -> Plan` — that adds one
  `Action` (mirroring `build_plan`'s own `Action(...)` construction shape at its `PRESENT_CONFORMANT`
  call site: `current_state=target_state=ArtifactState.PRESENT_CONFORMANT`, `chosen_anchor=None`
  for a whole-file class, a rationale naming "first-claim, tool-owned class") per entry that is
  `PRESENT_CONFORMANT`, whose `artifact_class` is `COPIED_MANAGED` or `GENERATED_DERIVED`, and
  whose id has no record in `state.managed` (or `state is None`). Re-sort the merged actions by
  `artifact_id` before constructing the augmented `Plan` (matching `build_plan`'s own sort
  convention).
- A second `adopt` on an unchanged, already-adopted repo (dry-run or `--apply`) produces an
  **empty plan and writes nothing** (FR-84, SC-03, AD-60) — the direct, testable consequence of
  the bullet above.
- `--agents <list>` takes one comma-separated value (`--agents claude,cursor`, matching the
  epics AC's own `--agents <list>` singular-flag syntax) and is recorded into `state.agents` as a
  de-duplicated tuple (idempotent union with any
  existing `state.agents` on a re-adopt, never a silent replace that would drop a previously
  requested agent). No per-agent conditional materialization exists yet (Story 11.1, not landed)
  — every `generated-derived`/agent-related manifest entry materializes unconditionally regardless
  of `--agents`'s value; this story only closes the state-bookkeeping half of FR-116, not the
  fan-out gating half.
- `check_preconditions` (Story 10.4) runs before any write, including before writing
  `.marshal/plan.json` in dry-run — pass `dry_run=True` when no `--apply`, which bypasses only the
  clean-worktree rung (10.4's own established rule: "dry-run invocations bypass the clean-worktree
  requirement — reading is always safe"); the not-a-git-repo, escaping-target, never-write, and
  hand-edited-managed-content rungs still apply in dry-run. `--force` maps to
  `check_preconditions(force=True)`, bypassing only the hand-edited-managed-content rung.
- `--skip <glob>` (repeatable) is applied via `skips.apply_skips`/`skips.managed_after_skips`
  before both `check_preconditions` and `run_apply`, and the pattern is recorded in
  `state.skips[]` (FR-87, matching 10.4's own AC).
- After a successful `--apply` whose plan was NON-empty, build a fresh `SeedState`
  (`mode="adopt"`, `adopted_at`/`last_update` via `state.store.utc_timestamp()`, `agents`,
  `managed[]` built from the post-apply repo — re-read each materialized whole-file entry's
  content and hash it, use `regions.parse` for each materialized hybrid entry's inserted span —
  `legacy[]` from `inventory.legacy`, `migrations_applied=()`, `opted_out=()` on a first adopt)
  and write it via `state.store.write_state` — the ONLY write that happens after `run_apply`
  returns successfully, matching Story 10.2's "state is written last, after all file writes
  succeed" invariant. FR-84 says "a second run... writes nothing," literally, not "writes nothing
  except a refreshed timestamp": when the (possibly augmented) plan is EMPTY, `run_apply` is a
  no-op (10.3's own AC) and `adopt` must skip the state write entirely — no `last_update` refresh,
  no re-write of byte-identical content. Gate the state write on `plan.actions` (post-augmentation)
  being non-empty, not merely on "`--apply` was passed."
- `run_apply`'s `commit` callback (the parameter `adopt` must supply) wraps
  `engine.copier.materialize` per `Action` — `run_apply` itself imports no `engine`/`copier`
  (confirmed by direct reading of `apply/run.py`); materializing content is entirely this
  callback's job.

**Block If:** none identified — the FR-83/FR-84 interaction above looked at first read like it
might need a human call (the two ACs read as contradictory in isolation), but direct reading of
`build_plan`'s and `classify`'s actual code resolves it to a single coherent, testable design
(state-presence-gated first-claim, documented above) with no remaining ambiguity.

**Never:**
- No modification to `plan/build.py`'s `build_plan` itself — the FR-83 gap is closed by
  `adopt`-local augmentation, never by changing the shared, already-tested classification→action
  function every other verb (`check`, future `init`/`update`) also depends on.
- No real interactive `input()` call reachable from a test — the confirmation step must be
  injectable.
- No touching `preconditions.py`/`skips.py`'s own internals — call them, don't reimplement them.
- No `--json` flag (not in this story's AC; `check` has one, `adopt` does not need one — a
  written `plan.json` already IS the machine-readable artifact FR-82 asks for).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Dry-run (no flags) on a never-adopted repo | clean git repo, nothing adopted | `.marshal/plan.json` written with the full computed plan; plan printed; no other file changed; no `seed-state.yml` written | none |
| `--apply --yes` on the same repo | same, immediately after | every planned artifact materialized; `seed-state.yml` written last; exit 0 | none |
| Second `adopt` (dry-run) on the now-adopted, unchanged repo | state exists, nothing changed since | empty plan (`actions == ()`); `plan.json` still written (it's always written in dry-run) but names zero actions; no other write | none |
| Second `adopt --apply --yes` on the unchanged repo | same | `run_apply` on an empty plan is a no-op (10.3's own AC); `seed-state.yml` is NOT rewritten at all (FR-84 "writes nothing" is literal — no `last_update` refresh) | none |
| Brownfield repo already has an unrelated file at a `generated-derived` artifact's path | first adopt, file present, `state is None` | `--apply` overwrites it (first-claim rule); the pre-existing content is gone, replaced by Genesis's own render | none — this is FR-83's own explicit, intentional behavior |
| `--apply` without `--yes`, confirmation declined | interactive `confirm` seam returns `False` | plan.json still written (dry-run's write already happened before the prompt, or is re-written identically); no apply; no state write; exit reflects "declined," not a `SeedError` | none |
| Dirty worktree, `--apply` (no `--yes` needed to reach this) | uncommitted changes present | refused, `PreconditionFailure` (exit 3), remedy names the dirty state | no traceback |
| Dirty worktree, dry-run | uncommitted changes present | dry-run still runs and writes `plan.json` (10.4: dry-run bypasses the clean-worktree rung) | none |
| Hand-edited managed content on a re-adopt | `state.managed[]` record's hash no longer matches | refused, `PreconditionFailure` (exit 3), unless `--force` | no traceback |
| `--force` on hand-edited content | same | overwrites, matching `--force`'s documented semantics | none |
| `present-legacy` artifact present | e.g. a recognized legacy convention file | recorded in `state.legacy[]`, never touched by apply | none |
| `--agents claude,cursor` then a later `adopt --agents gemini` | already-adopted repo | `state.agents` becomes the de-duplicated union of both calls, never drops `claude`/`cursor` | none |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/adopt.py` -- NEW: the verb
  orchestration (resolve → detect → plan → augment (FR-83 first-claim) → confirm → apply →
  state-write), mirroring `verbs/check.py`'s composition style.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/seed.py` -- wire `run_adopt` to
  the new verb module; add `--apply`/`--yes`/`--agents`/`--repo-root`/`--skip`/`--force` flags to
  `adopt_parser`; reuse the exact widened try/except + `_print_seed_error` pattern `run_check`
  already established (10.5 review finding).
- `.../seed/apply/run.py` -- reuse `run_apply(plan, *, repo_root, never_write, commit)` (Story
  10.3, already shipped); `adopt` supplies the `commit` callback wrapping
  `engine.copier.materialize`.
- `.../seed/verbs/preconditions.py` -- reuse `check_preconditions(plan, *, repo_root,
  never_write, managed=(), force=False, dry_run=False, process=None)` (Story 10.4).
- `.../seed/verbs/skips.py` -- reuse `apply_skips`/`managed_after_skips`.
- `.../seed/plan/build.py` -- reuse `build_plan`, `write_plan`, `default_plan_path`; reuse the
  `Action`/`Plan` dataclasses for the FR-83 augmentation; **do not modify** `build_plan` itself.
- `.../seed/detect/inventory.py` -- reuse `classify`.
- `.../seed/state/store.py` -- reuse `write_state`, `utc_timestamp`, `read_state`, `state_path`.
- `.../seed/engine/copier.py` -- reuse `MaterializeRequest`/`MaterializeResult`/`materialize` from
  the `commit` callback.
- `.../seed/errors.py` -- reuse the six-leaf taxonomy (no new leaves).
- `.../seed/regions/apply.py` -- reuse `insert_region` (never `substitute_region` -- `adopt` only
  ever inserts a NOT-PRESENT region, per `Action.chosen_anchor`'s own "pending regions only"
  contract; an already-present-but-drifted region body is `check`'s/a future `update`'s concern,
  never `build_plan`'s).
- `.../seed/regions/parse.py` -- reuse `parse_regions` to re-locate a just-inserted region's span
  when building the post-apply `ManagedArtifact` record.
- `.../seed/detect/hashes.py` -- reuse `hash_content`/`region_body_text` for the FR-83 augmentation's
  fingerprint hash and for the post-apply `ManagedArtifact.body_sha`.
- `.../seed/model/manifest.py` -- reuse `AppliesTo`; landing-time addition beyond the spec's
  original Code Map: `_manifest_for_adopt` filters `manifest.entries` to `applies_to in (ADOPT,
  BOTH)` before `classify`/`build_plan` ever see it (an `init`-only entry, e.g. `starter-dream`'s
  `docs/dreams/{{ slug }}.md`, has no `--slug` here and would otherwise plan a literal,
  un-rendered path) -- see `verbs/adopt.py`'s own module docstring for the full rationale.
- `pyforge.core.process.PosixProcess` -- landing-time addition: `verbs/adopt.py::
  _repo_is_dirty_now` (a narrow, locally-owned duplicate of `plan.build._repo_is_dirty`, matching
  `verbs/preconditions.py::_is_dirty`'s own precedented duplication of the same private function)
  refreshes ONLY the plan's `RepoFingerprint.dirty` flag immediately before `run_apply`, to
  correct for `write_plan` itself having just introduced `.marshal/plan.json` as an untracked
  file on a never-before-adopted repo (whose `.gitignore` region has not been installed yet) --
  without this, `apply.run.run_apply`'s own fresh `fingerprint_drift` re-check would immediately
  refuse the very plan this call just wrote and confirmed as `stale-plan`, confirmed by direct
  execution during this story's own development.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_adopt.py` -- NEW: cover every
  row of the I/O matrix above, especially the FR-83/FR-84 interaction (first-claim then
  idempotent), the confirm-seam (accepted/declined/injectable), and dry-run's `plan.json` write.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_cli_seed_adopt.py` -- NEW: CLI-level
  flag wiring and exit codes, mirroring `test_seed_cli_seed_check.py`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_scaffold.py` -- `adopt` removed from
  the stub-verb parametrization, given its own smoke test (mirrors 10.5's landing-time edit to
  this file for `check`).
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_integration_adopt_prd_j2.py` -- NEW:
  the PRD J2 integration test (epics AC's own explicit requirement): a repo with an existing
  `CLAUDE.md` (managed-region host) and a legacy convention (`docs/adr/`) adopts cleanly — the
  region is inserted into `CLAUDE.md` preserving the rest, the legacy convention is recorded and
  untouched, an unrelated "build-relevant" file (`pyproject.toml`, not named by the manifest at
  all) stays byte-identical, and a second adopt on the committed, unchanged repo is a true no-op.
  Deliberately exercises the REAL production defaults end to end (no injected `commit=`/
  `template_path=`) using only `hybrid-managed-region` entries, whose content is read from the
  REAL packaged `seed/templates/files/*.j2` fragments — see `verbs/adopt.py`'s own module
  docstring for why a whole-file class is not exercised against the packaged template tree (it
  ships no whole-file content yet, a named, pre-existing gap this story does not close).

## Tasks & Acceptance

**Execution:**
- [x] `seed/verbs/adopt.py` -- implement the full orchestration, including the FR-83/FR-84
  first-claim augmentation and the injectable `confirm` seam.
- [x] `cli/seed.py` -- wire `--apply`/`--yes`/`--agents`/`--repo-root`/`--skip`/`--force` on
  `adopt_parser`; `run_adopt(args)` calls the verb module and maps `SeedError`/unanticipated
  failures to exit codes (10.5's widened try/except pattern).
- [x] `tests/unit/test_seed_verbs_adopt.py` -- full I/O matrix coverage.
- [x] `tests/unit/test_seed_cli_seed_adopt.py` -- CLI flag/exit-code coverage.
- [x] `tests/unit/test_seed_scaffold.py` -- move `adopt` out of the stub parametrization.
- [x] PRD J2 integration test (existing `CLAUDE.md` + legacy convention, build-relevant files
  untouched).

**Acceptance Criteria:**
- Given an existing repository, when `marshal seed adopt` runs with no flags, then a plan is
  written to `.marshal/plan.json` and printed, and no other repo file changes.
- Given `--apply --yes`, when the plan is non-empty, then it executes and `seed-state.yml` is
  written last, after every file write succeeds.
- Given a second `adopt` on an unchanged, already-adopted repo, then the plan is empty and nothing
  is written beyond `plan.json` itself.
- Given a brownfield repo with a pre-existing file at a `generated-derived`/`copied-managed`
  artifact's path and no prior adoption, when `adopt --apply --yes` runs, then that file is
  overwritten and the artifact is recorded in `state.managed[]`.
- Given `present-legacy` artifacts, when adopt runs, then they are recorded in `state.legacy[]`
  and never modified.
- Given `--apply` without `--yes` and a declined confirmation, then nothing is applied and nothing
  written beyond `plan.json`.
- Given a dirty worktree, when `--apply` runs, then it refuses with `PreconditionFailure` (exit 3)
  naming the dirty state; the same dirty worktree under dry-run still succeeds.
- Given hand-edited managed content on a re-adopt, when `--apply` runs without `--force`, then it
  refuses; with `--force`, it overwrites.

## Spec Change Log

## Review Triage Log

### 2026-08-21 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 10: (high 2, medium 6, low 2)
- defer: 4: (high 0, medium 2, low 2)
- reject: 1
- addressed_findings:
  - `[high]` `[patch]` `_augment_plan_with_first_claims` trusted an id-only match against `state.managed` (`entry.id in claimed_ids`) to decide "already claimed," the same class of trap fixed for `verbs/check.py` in Story 10.5 -- but here it silently PERMANENTLY ORPHANED an artifact whose manifest path moved (worse direction: a stale match was trusted, not distrusted). Fixed by also comparing `record.path == entry.path`; a path mismatch now falls through to re-claim at the current path, and `_build_state_after_apply`'s existing `touched_ids` filter correctly drops the stale old-path record.
  - `[high]` `[patch]` `_repo_is_dirty_now`'s "narrow" dirty-flag refresh was a TAUTOLOGY: it re-derived the SAME unrestricted `git status` signal `apply.run.fingerprint_drift` independently re-checks moments later, so the two could never disagree -- silently defeating dirty-drift protection for the entire confirm-prompt window, not merely for the self-inflicted `plan.json` write it existed to correct for. First fix attempt (excluding `.marshal/plan.json` via a git pathspec) broke every apply outright, because `--untracked-files=normal` reports a wholly-new untracked directory as itself, never its contents, so the file-level exclusion never matched. Root-caused via a standalone Python/git repro (not the actual fix). Correctly redesigned into two functions: `_repo_is_dirty_now` stays UNRESTRICTED (the only signal `fingerprint_drift`'s own un-parameterized re-check can ever agree with), and a new `_unexpected_dirt_since_plan_write` (excluding `.marshal/` via pathspec) runs BEFORE `run_apply` as this module's OWN explicit, clearly-messaged refusal -- the actual mechanism that now catches an operator dirtying the repo with something unrelated during the confirm pause.
  - `[medium]` `[patch]` `_staged_bytes_for` silently picked the first staged path tailing a target, with no ambiguity detection, contradicting this package's "refuse loudly" convention. Now raises `InternalError` naming every ambiguous candidate.
  - `[medium]` `[patch]` `_read_region_fragment` silently picked the alphabetically-first fragment on a region-name stem collision. Same fix: raises `InternalError` naming every candidate.
  - `[medium]` `[patch]` No runtime guard enforced the "packaged region fragments contain no Jinja syntax" invariant the whole bypass-`materialize()` design rests on -- a future fragment containing `{{ mode }}` would splice un-rendered text silently into a real repo file. `_read_region_fragment` now raises `InternalError` if a fragment's text contains `{{`.
  - `[medium]` `[patch]` `_managed_artifact_after_apply`'s `spans[region_name]` was a bare dict lookup that could raise `KeyError` AFTER `run_apply` had already written to disk, leaving a real file change with no `ManagedArtifact` recorded. Now uses `.get()` with a named `InternalError`.
  - `[medium]` `[patch]` `_repo_is_dirty_now` let `PosixProcess.run`'s `ProcessError` (missing `git`, launch timeout) escape uncaught -- folded into the dirty-check redesign; both `_repo_is_dirty_now` and `_unexpected_dirt_since_plan_write` now funnel through a shared `_git_status_porcelain` helper that catches `ProcessError` and raises a targeted `PreconditionFailure`.
  - `[medium]` `[patch]` A first-claim (FR-83, overwrite) action was rendered in the printed plan with no visual distinction from an ordinary "create" action, despite this feature's whole safety model being "a human reviews the plan before anything destructive happens." `cli/seed.py::_render_plan_text` now prefixes such actions with `[OVERWRITES EXISTING FILE]`, detected via a new shared `adopt.FIRST_CLAIM_MARKER` constant (not a duplicated string).
  - `[low]` `[patch]` `_default_commit`'s `commit()` used a bare `next(...)` for a region-name lookup in `entry.regions` that could raise `StopIteration` mid-apply. Now raises a named `InternalError`.
  - `[low]` `[patch]` `cli/seed.py::_real_confirm` caught only `EOFError`, not `KeyboardInterrupt`, during the confirmation prompt -- a Ctrl-C would propagate as a raw `BaseException` instead of the documented graceful decline. Now catches both.
  - `[medium]` `[defer]` `_default_commit`'s hybrid-region path never checks `regions.apply.insert_region`'s return value for an unexpected outcome (e.g. `ALREADY_PRESENT`). Whether this is reachable at all needs a focused read of `regions/apply.py`'s own contract before a correct fix can be written without risking a false refusal. Logged as `DW-FU-10-6`.
  - `[medium]` `[defer]` Whole-file `--apply` is non-functional against the REAL packaged manifest for ~20/43 entries (no whole-file template content shipped yet) -- correctly out of this story's scope (verb mechanics vs. template-content authoring) and fails with a clean `InternalError`, not a traceback, but untested against the real manifest and not literally satisfying the story's own "Given `--apply --yes` ... it executes" AC for the shipped default. Logged as `DW-FU-10-6-2`.
  - `[low]` `[defer]` `_default_commit`'s hybrid-region path re-reads the packaged fragment from disk on every region insertion, unlike the whole-file path's deliberate once-per-run materialize. Low-severity perf/consistency nit. Logged as `DW-FU-10-6-3`.
  - `[low]` `[defer]` `_managed_records`'s silent-exclude-on-stale-manifest-entry (inherited from `verbs/check.py`'s identical precedent) is now load-bearing for a MUTATING verb -- a hand-edit to an artifact whose manifest entry vanished between adopts sails through precondition checking unnoticed. Logged as `DW-FU-10-6-4`.
  - `[reject]` "No `{{` in the packaged fragments today" -- verified independently true by both reviewers; the actionable follow-up (guard against a FUTURE regression) is the Jinja-injection-guard patch above, not a separate finding.

Added regression tests proving every high/medium patch: `test_first_claim_reclaims_when_a_stale_record_names_a_different_path`, `test_operator_dirtying_the_repo_during_the_confirm_pause_is_still_caught`, `test_repo_is_dirty_now_wraps_a_launch_failure_as_precondition_failure`, `test_staged_bytes_for_raises_on_ambiguous_tail_match`, `test_region_body_from_template_raises_on_ambiguous_fragment_match`, `test_region_body_from_template_raises_on_jinja_syntax_in_fragment`, `test_region_body_from_template_reads_a_single_unambiguous_static_fragment`, and `test_first_claim_action_is_visually_marked_in_the_printed_plan`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: full `pyforge-marshal`
  suite green, including the new `adopt` tests.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- expected: green (cross-station dependency
  hygiene gate this project's policy requires on every change).

## Auto Run Result

**Summary:** Implemented `marshal seed adopt` (Story 10.6) -- the first MUTATING verb in this
package: dry-run-by-default brownfield adoption, `--apply`/`--yes`/`--agents`/`--skip`/`--force`,
composing every already-landed Epic 9/10 primitive into `resolve -> detect -> plan -> augment ->
confirm -> apply -> state-write`. Resolves the real FR-83/FR-84 interaction identified during
planning (a state-presence-gated "first-claim" plan augmentation). One review pass (Blind Hunter +
Edge Case Hunter) found 10 patch-worthy findings (2 HIGH), including a real bug in the first-claim
logic matching a known precedent from Story 10.5's own review, and a fundamentally broken
dirty-worktree-refresh mechanism that required a full redesign (not a one-line fix) after the
first correction attempt broke every `--apply` outright.

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/adopt.py` (new) -- the verb
  orchestration.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/seed.py` (edited) -- CLI wiring,
  `--apply`/`--yes`/`--agents`/`--skip`/`--force` flags, the `_real_confirm` prompt, first-claim
  plan-rendering marker.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_adopt.py` (new) -- verb-level
  unit tests, full I/O matrix coverage plus 8 new review-driven regression tests.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_cli_seed_adopt.py` (new) -- CLI-level
  tests plus the first-claim marker regression test.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_integration_adopt_prd_j2.py` (new) --
  the PRD J2 integration test.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_scaffold.py` (edited) -- `adopt`
  removed from the stub-verb parametrization, given its own smoke test.
- `_bmad-output/projects/pyforge-marshal/implementation-artifacts/deferred-work.md` (edited) --
  four new defer entries (`DW-FU-10-6` through `DW-FU-10-6-4`).

**Review findings breakdown:** 10 patch (2 high, 6 medium, 2 low) -- all auto-fixed with
regression-test proof; 4 defer (2 medium, 2 low) -- logged to the Tier-3 deferred-work ledger; 1
reject (noise); 0 intent_gap; 0 bad_spec.

**Follow-up review recommendation:** `true` -- unambiguously, for reasons well beyond the volume
threshold: the two HIGH fixes changed load-bearing safety mechanisms (which artifacts get claimed
on first adopt; whether a dirty-worktree race during the confirm pause is actually caught), the
dirty-check fix required a genuine architectural redesign after the first attempt was proven wrong
by running the suite (not merely a style nit caught on inspection), and the whole confirm/dirty/
apply interaction is inherently the highest-blast-radius code in this story (the first verb in the
package that writes to a real repo). This combination warrants one more independent look before
Epic 11's migration work builds on top of it.

**Verification performed:** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- 4951
passed, 9 deselected. `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- 84 passed. `ruff
check` clean on all six changed/new files.

**Residual risks:** the four deferred findings are real but explicitly scoped out (three
pre-existing/inherited, one needing focused follow-up research before a safe fix). Whole-file
`--apply` against the real packaged manifest remains untested end-to-end (no template content
exists yet for ~20/43 entries) -- covered instead via the `template_path=` test-injection seam, per
the module's own documented, disclosed limitation. The `_unexpected_dirt_since_plan_write`/
`_repo_is_dirty_now` split is a genuinely new design pattern in this package (no prior precedent)
and, while now proven correct by execution and covered by regression tests, is exactly the kind of
subtle git-state-timing logic worth a second independent read.

## Status reconcile 2026-09-20

- frontmatter `status` `in-review` → `done` (ledger row `10-6-marshal-seed-adopt: done`).
