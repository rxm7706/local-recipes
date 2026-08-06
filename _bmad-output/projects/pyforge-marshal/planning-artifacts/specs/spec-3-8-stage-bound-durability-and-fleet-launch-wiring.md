---
title: 'Stage-bound durability, and fleet-launch wiring'
type: 'feature'
created: '2026-08-05'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md']
warnings: []
baseline_revision: '060fc7352f06515d5b0f4cdf34bd581e6f5034a7'
---

<intent-contract>

## Intent

**Problem:** worst-case data loss today is bounded only by whatever wall-clock interval an operator remembers to configure (or forgets to) — there is no push tied to a run's own structure, and no watcher starts unless someone invokes one by hand. This is the gap FR-61/AD-46 name: durability that scales with an arbitrary timer instead of the run's own stage transitions, and a watcher nobody remembers to start.

**Approach:** add a `VcsPort.push` primitive (git push only, no force, no rewrite — mirrors the read-only-except-for-`add_worktree`/`remove_worktree`/`delete_branch` discipline the rest of `VcsPort` already keeps); a new pure `supervisor/durability.py` module classifying `RunStatusSnapshot`-shaped task-phase transitions into push triggers (`review-verdict-recorded`, `dev-commit-landed`, `story-merged`) plus an interval fallback; and supervisor tick-loop + `run_spin` wiring so every `factory spin` launch starts the interval-push watcher automatically, with no separate CLI action.

## Boundaries & Constraints

**Always:**
- `VcsPort.push(repo_root, branch)` is a **plain `git push`** against the branch's already-configured upstream (or `origin <branch>` if none is configured yet) — read-only against the working tree, and the **only** write is the remote-tracking ref update a push performs by construction. No `--force`, no `--force-with-lease`, no `push -u` that would silently rewrite a remote branch's tracking config against the operator's own choice. Raises `VcsCommandError` on any git failure; the caller treats a push failure as a registered `WARN`, never a run-halting condition (AD-46 names durability as best-effort against transient network conditions, never a new refusal gate).
- Stage-boundary detection is a **pure classification** over two consecutive `RunStatusSnapshot`-derived task-phase reads (mirrors `evaluate_escalation`'s and `evaluate_ceiling`'s shape — no I/O in `core`/`supervisor/durability.py`'s classifying function itself). `supervisor/durability.py::classify_push_triggers(previous_phases: Mapping[str, str], current_phases: Mapping[str, str]) -> tuple[PushTrigger, ...]` returns one `PushTrigger(story_key, boundary)` per story whose phase crossed one of the three named transitions since the last observation — `review-verdict-recorded` (`Phase.REVIEW_VERIFY` newly reached), `dev-commit-landed` (a story's `commit_sha` newly non-`None`), `story-merged` (`Phase.DONE` newly reached). A story can cross more than one boundary between two ticks (the whole point of tick-based observation, not event streaming) — every crossed boundary in the interval is reported, not just the last.
- The tick loop keeps the previous tick's phase/commit-sha snapshot (mirrors 3.7's already-journaled `set[str]` pattern for deferrals) and diffs against the current one every tick while `watched_alive`; each `PushTrigger` observed pushes the run's station branch (the loop-home's own integration branch, e.g. `loop/<slug>`) and, when the triggering story ran in worktree-isolation mode (`task.branch` non-empty), that story's own per-story branch too. One `"stage-push"` journal observation per push attempt (`story_key`, `boundary`, `branch`, `outcome: pushed | push-failed`), never silently skipped.
- The **interval-push watcher is the floor**, not the primary mechanism: a separate, coarser timer (default matching the existing supervisor poll interval's order of magnitude — reuse the already-configured idle-threshold-derived cadence rather than inventing a new policy key) that pushes unconditionally on expiry, catching whatever the three named boundaries miss (a long `DEV_RUNNING` stretch with no phase crossing yet, a story that never reaches `DONE` because the run itself pauses first). It is wired into `run_spin` directly — every `factory spin` launch starts it as part of the same supervisor sidecar the idle ladder and budget ceilings already run inside, with no new CLI flag and no separate `marshal factory watch` action.
- The watcher **exits when the fleet does**: it is not a separate process — it lives inside the same supervisor tick loop `run_spin` already spawns, so it terminates exactly when that loop's own detach/exit path runs, with no independent lifetime to leak.

**Never:**
- No new Marshal policy/SEED key for "should durability pushing run" — AD-46 makes it unconditional ("wired in by default rather than a separate manual invocation"), matching this project's existing precedent (Story 3.7) of not inventing an opt-out where the architecture states a default-on behavior.
- No push of `main`/the repo's primary branch — only the loop-home's own station branch and per-story branches, the same scope `VcsPort`'s other write methods (`remove_worktree`, `delete_branch`) already confine themselves to.
- No new `HarnessPort` method: stage-boundary detection reads `RunStatusSnapshot` (Story 3.7's own `run_status_snapshot`, already returning per-task phase via `deferred`'s sibling data — extend the port method's return value if the current shape doesn't expose per-task `phase`/`commit_sha`, rather than adding a second, overlapping bmad-loop-state-reading method).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Review verdict recorded | A task's phase reads `REVIEW_VERIFY` on this tick, was not on the previous tick | One `PushTrigger(story_key, "review-verdict-recorded")`; station branch pushed; per-story branch pushed if worktree-isolated | Push failure -> `WARN` finding, tick continues |
| Dev commit lands | A task's `commit_sha` is non-`None` on this tick, was `None` on the previous tick | One `PushTrigger(story_key, "dev-commit-landed")`; same push behavior | Same |
| Story merges | A task's phase reads `DONE` on this tick, was not `DONE` previously | One `PushTrigger(story_key, "story-merged")`; same push behavior | Same |
| Two boundaries in one tick | Both `commit_sha` newly set and phase newly `DONE` between two ticks (a fast tick interval relative to engine progress) | Two `PushTrigger`s reported for the same story; two `"stage-push"` observations, each named distinctly | No error expected |
| No RunStatusSnapshot available | `run_status_snapshot` returns `None` (malformed/missing `state.json`) | No stage-boundary push attempted this tick; interval watcher remains the sole fallback | Never raises |
| Interval watcher expiry | Configured interval elapses with no intervening stage-boundary push for the run's station branch | Unconditional push attempted; journaled `"stage-push"` with `boundary: "interval"` | Push failure -> `WARN`, tick continues |
| `git push` fails (no network, rejected non-fast-forward) | `VcsPort.push` raises `VcsCommandError` | Caught at the call site, one `WARN` finding registered, tick loop continues unaffected | Never propagates past the tick |
| Run has no remote configured for the branch | `git push` with no upstream and no `origin` reachable | Same `VcsCommandError` path as any other push failure — no special-cased detection, no silent skip | Same `WARN` handling |
| `run_spin` launches | Any `factory spin` invocation | Interval-push watcher starts inside the same supervisor sidecar, no separate invocation, no new argv flag | N/A |
| Supervisor detaches / run ends | Tick loop's normal exit path runs (idle-defer, budget breach, escalation, clean finish) | Watcher stops with the tick loop — no orphaned timer, no separate process to reap | N/A |


</intent-contract>

## Code Map

- `src/pyforge/marshal/ports/vcs.py` — EDIT. `VcsPort.push(self, repo_root: Path, branch: str) -> None` — plain `git push`, no force. Docstring follows the existing method-doc convention (states the exact git invocation and its read-only/single-write scope).
- `src/pyforge/marshal/adapters/vcs_git.py` — EDIT. Implement `push`: resolve whether `branch` already has an upstream (`git rev-parse --abbrev-ref <branch>@{upstream}`); if so, `git push`; if not, `git push origin <branch>` (first push for a brand-new station/per-story branch). Raises `VcsCommandError` on failure, matching every other method in the file.
- `src/pyforge/marshal/ports/harness.py` — EDIT (only if `RunStatusSnapshot`/its per-task data does not already expose phase + `commit_sha` per story — verify against the Story 3.7 shape before touching; if the existing `deferred`/other fields already carry enough, extend `RunStatusSnapshot` with a `tasks: tuple[TaskPhaseSnapshot, ...]` field instead of a new port method, where `TaskPhaseSnapshot` is a frozen dataclass of `story_key`, `phase`, `commit_sha`).
- `src/pyforge/marshal/adapters/harness_bmadloop.py` — EDIT. Populate the new `tasks` field on `run_status_snapshot`'s existing `load_state`-derived read (no new bmad-loop import site — reuse the module already carrying the AD-3 import-linter exception).
- `src/pyforge/marshal/supervisor/durability.py` — NEW. `PushTrigger` (frozen dataclass: `story_key`, `boundary` — `Literal["review-verdict-recorded", "dev-commit-landed", "story-merged"]`), `classify_push_triggers(previous, current) -> tuple[PushTrigger, ...]` — pure, no I/O, mirrors `evaluate_escalation`'s/`evaluate_ceiling`'s shape and gets the same style of millisecond-fast synthetic-sample unit tests.
- `src/pyforge/marshal/supervisor/__main__.py` — EDIT. Tick loop gains: (1) a retained previous-tick `Mapping[str, TaskPhaseSnapshot]`, diffed via `classify_push_triggers` every tick while `watched_alive`, each trigger driving a station-branch push (+ per-story branch push when isolated) and a `"stage-push"` journal observation; (2) an interval timer (reuse the existing poll-interval config seam) that fires an unconditional push + `"stage-push"` observation (`boundary: "interval"`) on expiry, independent of the stage-boundary path.
- `src/pyforge/marshal/cli/spin.py` — EDIT (wiring only, no new argv). `_spawn_supervisor_sidecar`/`run_spin`'s existing argv construction passes through whatever new constructor args `run_supervisor` needs for the durability watcher (station branch, isolation-mode per-story branch resolution) — no new CLI flag, per the Never clause.
- `src/pyforge/marshal/core/findings.py` / `core/verdict.py` — EDIT. One new code, e.g. `MRS-SUPV-008` (durability push failed, WARN) — reuses `MRS-SUPV-007`'s pattern (notify-file write failure) as the direct precedent for "a best-effort durability side-effect failed; warn, never block."
- `src/pyforge/marshal/tests/unit/test_durability.py` — NEW. `classify_push_triggers` transition matrix: no change, each boundary individually, two boundaries in one diff, a story regressing phase (should never happen from bmad-loop, but the classifier must not crash on it — treat as no trigger, not an error).
- `src/pyforge/marshal/tests/unit/test_vcs_git.py` — EDIT. `push` against a real temp git repo: with upstream configured, without (first push), and a failure case (no remote at all) asserting `VcsCommandError`.
- `src/pyforge/marshal/tests/unit/test_supervisor.py` — EDIT. Stage-boundary push wiring (each trigger causes exactly one push call to the fake `VcsPort`), interval-watcher firing independent of stage boundaries, watcher lifetime tied to the tick loop's own exit.
- `src/pyforge/marshal/tests/unit/test_spin.py` — EDIT. `run_spin` starts the durability watcher with no new flag; existing argv-shape tests gain an assertion that no new positional/flag was introduced (the Never clause is testable, not just documented).

## Tasks & Acceptance

**Execution:**
- [x] `ports/vcs.py` + `adapters/vcs_git.py` — `push`, no force, upstream-aware.
- [x] `ports/harness.py` + `adapters/harness_bmadloop.py` — verify/extend `RunStatusSnapshot` with per-task phase + `commit_sha` (only if not already present).
- [x] `supervisor/durability.py` — `PushTrigger`/`classify_push_triggers`, pure core.
- [x] `supervisor/__main__.py` — per-tick stage-boundary push wiring + interval-watcher fallback, both scoped to the tick loop's own lifetime.
- [x] `cli/spin.py` — pass-through wiring only; confirm no new CLI surface.
- [x] `core/findings.py` / `core/verdict.py` — register and classify the new durability-push-failure code.
- [x] Unit tests for every new/edited module, including the full I/O matrix above.
- [x] `deferred-work.md` — log any scope narrowed during implementation (e.g. if per-story branch push for non-isolated runs turns out to be a no-op worth naming explicitly).

**Acceptance Criteria:**
*(Story 3.8's ACs from `epics.md`, preserved as the contract of record.)*
- Given a running story, when the dev commit lands, the review verdict is recorded, or the story merges, then the supervisor pushes the affected station and per-story branches at that boundary, never on a wall-clock interval alone
- And push is read-only against working trees and remotes — never a force-push, never a rewrite
- Given a fleet launch, when it starts, then the interval-push watcher (the floor for whatever the stage hooks miss) starts automatically, with no separate manual invocation required
- And the watcher exits on its own when the fleet does

## Design Notes

**"Fleet launch" is `factory spin`, not a separate multi-project command.** No `marshal factory fleet`/multi-project launch command exists in the shipped CLI (`cli/spin.py` has only `spin`/`attach`/`resume`); Epic 3's own goal statement — "the operator can launch a gated run and walk away" — and AD-46's own text ("wired into fleet launch by default rather than a separate manual invocation") read together as: a single `factory spin` run already drives a *fleet of stories* through the loop unattended, and that run is the "fleet launch" the watcher wires into. If a genuine multi-project fleet-launch command lands later (none is currently scoped in any backlog epic), the watcher wiring described here still applies unchanged — it lives in the supervisor sidecar every launch path already spawns.

**Why boundary detection is two-consecutive-snapshot diffing, not a single-read classifier.** `evaluate_escalation`/`evaluate_ceiling` classify a single observation because escalation and budget-breach are level-triggered (true or not, right now). A stage boundary is edge-triggered — "review verdict just got recorded" is only knowable by comparing against what was true last tick. Reusing a level-triggered shape here would either push on every tick a story sits in `REVIEW_VERIFY` (spam, and no `"stage-push"` count would mean anything) or need its own separate already-journaled `set[str]` per boundary type, three of them — the diff-against-previous-snapshot shape is the simpler primitive and is verified in one pure function instead of three ad hoc dedup sets.

**Why `commit_sha` newly-non-`None` stands in for "the dev commit lands" rather than a dedicated bmad-loop phase.** Verified against the installed `bmad_loop` 0.9.0 engine (`engine.py`): there is exactly one real git commit per story, made inside `_commit` (called from `_review_and_commit`, after `Phase.REVIEW_VERIFY`), immediately followed by `advance(task, Phase.DONE)`. There is no engine phase distinctly named "dev commit landed" separate from the final commit. `commit_sha` transitioning from `None` is the only externally-observable signal for "a commit now exists for this story", and it happens to land at nearly the same tick as `Phase.DONE` in the current engine — the three named boundaries are kept as three distinct classifier outputs anyway (per AD-46's own naming and to stay correct if a future engine version separates dev-commit from final-commit, e.g. an isolation-mode per-unit commit before review), but implementers should expect `dev-commit-landed` and `story-merged` to frequently fire in the same tick against today's engine, not as a bug.

## Spec Change Log

**1. Code Map inaccuracy (`classify_push_triggers`'s own parameter shape) — adapted, not the contract itself.** The Boundaries text spells the signature literally as `classify_push_triggers(previous_phases: Mapping[str, str], current_phases: Mapping[str, str])` — a phase-only mapping. But the SAME paragraph defines `dev-commit-landed` as "a story's `commit_sha` newly non-`None`", a fact a phase-only mapping cannot carry (there is no second `commit_sha`-keyed argument named anywhere in the contract either). Implemented as `classify_push_triggers(previous: Mapping[str, TaskPhaseSnapshot], current: Mapping[str, TaskPhaseSnapshot])` instead — one pair of full per-task readings, mirroring `RunStatusSnapshot.tasks`'s own shape — so one function can classify all three boundaries from one diff, rather than needing a second, parallel `commit_sha`-only mapping pair. Verified: `tests/unit/test_durability.py`'s own commit/phase-combination tests (`test_commit_sha_newly_non_none_fires_dev_commit_landed`, `test_commit_landing_and_story_merging_in_the_same_tick_fires_both`) exercise exactly the case the literal signature could not express.

**2. Code Map inaccuracy (`TaskPhaseSnapshot`'s own field count) — extended, not the contract itself.** The Code Map's one-line description names `TaskPhaseSnapshot` as "a frozen dataclass of `story_key`, `phase`, `commit_sha`" — three fields. But the story's own Always bullet requires a stage-boundary push to also push "that story's own per-story branch too" when the triggering story ran worktree-isolated ("`task.branch` non-empty") — and no field on the literal three-field type names a branch. Added a fourth, trailing-defaulted field, `branch: str = ""` (`StoryTask.branch` verbatim, mirroring `DeferredStory.branch`'s own convention), so `supervisor/__main__.py::_process_stage_pushes` can resolve the per-story branch from the SAME reading `classify_push_triggers` already diffs, rather than a second `HarnessPort` read. Verified: `tests/unit/test_supervisor.py::test_a_dev_commit_landing_pushes_both_the_station_and_per_story_branch` / `test_a_non_isolated_story_pushes_only_the_station_branch` pin both the isolated and non-isolated shapes.

**3. Code Map inaccuracy (`cli/spin.py` needed no diff at all) — confirmed, not implemented.** The Code Map describes `cli/spin.py` as "EDIT (wiring only, no new argv)... passes through whatever new constructor args `run_supervisor` needs for the durability watcher (station branch, isolation-mode per-story branch resolution)". In practice `run_supervisor` needs no new constructor arg from its caller at all: the station branch is `f"loop/{slug}"`, derivable inside `run_supervisor` from the `slug` positional it already receives (this package's own established convention, `cli/init.py`'s identical formula), and the interval watcher's own cadence reuses `idle_threshold_minutes`, also already passed. `cli/spin.py` is therefore untouched by this story — `run_supervisor` gained one new DI kwarg (`vcs: VcsPort | None = None`, defaulting to `GitVcs()`), mirroring `notify`'s own Story 3.7 precedent, with nothing for any caller to pass through. Verified: `tests/unit/test_spin.py::test_spin_introduces_no_new_argv_surface_for_durability` pins the argv at exactly 10 positionals (unchanged since Story 3.6), and `lint-imports` confirms `cli/spin.py` needed no new import either.

**4. Verification-section inaccuracy (`supervisor/durability.py`'s own import surface) — corrected description, not the module.** The Verification section's own text claims `supervisor/durability.py` "still import[s] no adapter/port directly" alongside `core/supervise.py`. `supervisor/durability.py` DOES import `TaskPhaseSnapshot` from `ports/harness.py` — a plain frozen-dataclass TYPE import for its own function signature, never an adapter, an I/O call, or a port INSTANCE. This does not violate purity (AD-20: "no port, no clock call, no I/O" — behavioral, not about type imports) or any import-linter contract (`ports/` importing into `supervisor/` is unrestricted; only `bmad_loop` and `pyforge.marshal.cli` are forbidden source targets for `pyforge.marshal.supervisor`). Verified live: `lint-imports` reports "3 kept, 0 broken", identical to Story 3.7's own baseline.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: all green, new tests included, zero regressions.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` — expected: all import-linter contracts hold (`supervisor/durability.py` and `core/supervise.py` still import no adapter/port directly).

**Manual checks (if no CLI):**
- Launch a real `factory spin` run against a throwaway loop home with a story that reaches `REVIEW_VERIFY` and then `DONE`; confirm the station branch is pushed at each observed boundary (`git log --oneline <remote>/loop/<slug>` advances without a manual push) and that a `"stage-push"` observation appears in the run journal for each.

## Review Triage Log

### 2026-08-05 — Review pass 1 (Blind Hunter + Edge Case Hunter, parallel)

- intent_gap: 0
- bad_spec: 0
- patch: 6 (high 1, medium 3, low 2)
- defer: 3 (medium 3)
- reject: 2 (low 2)
- addressed_findings:
  - `[high]` `[patch]` **`_push_branch`'s durability push helper caught only `VcsCommandError`, letting any other `VcsPort` exception (`OSError`, `subprocess.SubprocessError`) escape and crash the whole tick loop.** Independently found by both reviewers. `VcsPort` is an interface — `GitVcs` itself wraps every subprocess failure into `VcsCommandError`, but a future or alternate implementation could raise a launch-level `OSError` or a `subprocess.SubprocessError` directly, contradicting this story's own core invariant ("never a run-halting condition", AD-46's "never a new refusal gate"). Fixed: widened the except clause to `(VcsCommandError, OSError, subprocess.SubprocessError)`, journaling the same `MRS-SUPV-008` WARN regardless of exception type. New test: `test_an_unexpected_exception_type_from_vcs_push_does_not_crash_the_tick`.
  - `[medium]` `[patch]` **`GitVcs.push` reused `_GIT_CHECKOUT_TIMEOUT_S` (sized for a local `worktree add`) for the network `git push` call.** A push is a remote round-trip, not a local tree-populating checkout, and can legitimately take longer under a slow/congested network than the checkout tier anticipates. Fixed: added a dedicated `_GIT_PUSH_TIMEOUT_S = 120.0` constant, used only for the `_run` call inside `push`.
  - `[medium]` `[patch]` **`push`'s upstream-resolution check treated ANY non-zero `git rev-parse --abbrev-ref <branch>@{upstream}` exit as "no upstream configured", silently falling back to `git push origin <branch>`.** That conflates the genuine no-upstream case with an ambiguous/corrupted rev-parse failure (a nonexistent local branch, e.g.), which could push to a remote/branch the caller never intended. Fixed: the fallback now fires only when the failure's stderr carries git's own `"no upstream configured for branch"` wording (verified live against real git output); any other non-zero exit raises `VcsCommandError` instead. New test: `test_push_raises_rather_than_falls_back_on_a_non_missing_upstream_rev_parse_failure`.
  - `[medium]` `[patch]` **The `MRS-SUPV-008` durability-push-failed finding interpolated the raw `VcsCommandError`/git stderr text directly into the journal message, bypassing this package's own redaction-at-capture idiom for subprocess-derived text (AD-34).** Every other session/subprocess-derived free-text string this package journals (`adapters/observer_mux.py`, `adapters/harness_bmadloop.py`) routes through `to_redacted({"k": text}); json.loads(redacted.text)["k"]` before it enters a durable sink; the push-failure path did not. Fixed: the exception text is now round-tripped through the same `to_redacted` idiom before it enters the finding message.
  - `[low]` `[patch]` **Adding `RunStatusSnapshot.tasks` forced the pre-existing `deferred` field to gain a default value it never had before, silently weakening its previously-required, fail-fast construction contract.** Fixed: `RunStatusSnapshot` is now `@dataclass(frozen=True, kw_only=True)`, restoring `deferred` to no default while `tasks`/`finished` keep theirs — keyword-only fields have no positional-ordering constraint forcing the tradeoff. Verified every existing call site (`adapters/harness_bmadloop.py`, `tests/unit/test_spin.py`, `tests/unit/test_supervisor.py`) already constructs this type by keyword; none needed updating.
  - `[low]` `[patch]` **`GitVcs.push`'s pre-existing "malformed upstream" defensive branch (an `@{upstream}` resolution with no `<remote>/<remote_branch>` shape) had no test exercising it.** Fixed: added `test_push_raises_on_a_malformed_upstream_with_no_remote_slash`, reproducing the shape live via `git branch --set-upstream-to=<local-branch>`.
- deferred (not fixed in this pass, appended to `deferred-work.md` as NEW entries):
  - `[medium]` The durability interval-push watcher's clock baseline (`last_durability_push_monotonic`) is process-local and reset on every supervisor restart/reattach, never reconciled against the journal's own last `stage-push` entry — so the advertised "floor" guarantee is not actually durable across a crash-and-reattach cycle.
  - `[medium]` A story's phase regressing away from `DONE` and back (or a story silently vanishing from `RunStatusSnapshot.tasks` between two ticks) would re-fire `story-merged` as a fresh legitimate merge, or silently lose that story's tracked history — both rest on the unverified assumption that bmad-loop's own engine never does either. Should be verified against the installed `bmad_loop` engine's actual behavior in a future pass, the way Story 3.7 verified its own similar assumptions.
  - `[medium]` Station-branch and per-story-branch pushes triggered by the same boundary crossing are journaled as two independent `stage-push` observations with no shared correlation id, making it harder for a future consumer to reconstruct "these two pushes were one logical event" from the journal alone.
- rejected (contract-mandated or already-deliberate):
  - `[low or as-assessed]` Multiple simultaneous boundary crossings pushing the same branch redundantly — contract-mandated by this story's own I/O & Edge-Case Matrix ("Two boundaries in one tick" row explicitly names two separate PushTrigger/stage-push observations as expected).
  - `[low]` Durability cadence coupled to the idle-threshold policy key — contract-mandated by this story's own Boundaries & Constraints Always bullet ("reuse the already-configured idle-threshold-derived cadence rather than inventing a new policy key").

## Suggested Review Order

**Pure classification core**

- Entry point: the pure diff-two-snapshots classifier every push decision routes through — read this first to understand the design.
  [`durability.py:104`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/supervisor/durability.py#L104)

- The value type each classified boundary crossing takes — one story, one named boundary.
  [`durability.py:89`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/supervisor/durability.py#L89)

**Tick-loop wiring (stage pushes + interval floor)**

- Per-tick diff → push dispatch, including the post-loop flush for the "last tick" gap and the P1 broadened exception catch.
  [`__main__.py:992`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/supervisor/__main__.py#L992)

- Stage-boundary orchestration: keeps the previous snapshot, calls the classifier, pushes station + per-story branches.
  [`__main__.py:1051`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/supervisor/__main__.py#L1051)

- Interval-watcher fallback: unconditional push on expiry, reusing the idle-threshold cadence (a deliberate, contract-mandated coupling — see Review Triage Log).
  [`__main__.py:1385`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/supervisor/__main__.py#L1385)

- Post-loop flush call, mirroring 3.7's own last-tick fix for deferrals.
  [`__main__.py:2171`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/supervisor/__main__.py#L2171)

**Git push primitive (VcsPort)**

- Port contract: plain push, no force, no rewrite.
  [`vcs.py:158`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/vcs.py#L158)

- Implementation: upstream-aware push with the P3 narrowed no-upstream check and the P2 dedicated network timeout.
  [`vcs_git.py:476`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/vcs_git.py#L476)

**RunStatusSnapshot extension**

- New per-task phase/commit-sha shape the classifier reads, and the P5 `kw_only=True` fix that restored `deferred`'s fail-fast contract.
  [`harness.py:261`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/harness.py#L261)

- Adapter populating the new `tasks` field from the same `state.json` read `deferred` already uses.
  [`harness_bmadloop.py:1`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py#L1)

**Finding registration**

- The new `MRS-SUPV-008` (durability push failed) code and its WARN classification, including the P4 AD-34 redaction-at-capture fix.
  [`findings.py:1`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py#L1)
  [`verdict.py:1`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py#L1)

**Tests (peripherals)**

- Pure classifier transition matrix.
  [`test_durability.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_durability.py#L1)

- Push implementation + P2/P3/P6 patch coverage.
  [`test_vcs_git.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_vcs_git.py#L1)

- Tick-loop wiring, P1 exception-widening coverage, interval/stage-boundary interaction.
  [`test_supervisor.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_supervisor.py#L1)

- Proof no new CLI argv was introduced.
  [`test_spin.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_spin.py#L1)
