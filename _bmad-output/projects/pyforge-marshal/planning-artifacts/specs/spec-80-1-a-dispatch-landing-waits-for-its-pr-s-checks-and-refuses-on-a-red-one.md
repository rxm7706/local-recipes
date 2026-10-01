---
title: "80.1: A dispatch landing waits for its PR's checks and refuses on a red one"
type: 'feature'
created: '2026-10-01'
status: 'done'
baseline_revision: '68b35f7e1cb04295f729647c2d0ee4ff060ab417'
review_loop_iteration: 1
followup_review_recommended: false
warnings:
  - oversized
flag-exempt: detector-or-gate   # a gated gate reports a silent green (spec-feature-flag-governance Q2)
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - docs/dreams/pyforge-marshal.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/forge.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/forge_gh.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** a dispatch landing merges as soon as its own session verification passes. `main` has no branch protection
(`gh api repos/rxm7706/local-recipes/branches/main/protection` answers 404), and the landing policy's `landing_rules`
declare only the `maintenance` label and an ungated `linter` check, so nothing makes the landing wait for CI; and the
dispatch landing (`dispatch_land.py`) never evaluates `landing_rules` at all (only `marshal land`'s
`cli/land.py::_evaluate_required_checks` does, polling once). On 2026-10-01 doctor 38.3 (PR #1709) merged with
`Detectors / scripts-suite` already failing and reddened `main` (fixed by doctor 38.5, #1712), and steward 80.1 (#1713)
merged with Platform CI and Detectors still pending.

**Approach:**

- A pure `core/` classifier takes the check runs reported on a commit and returns green (every run concluded
  `success`, `skipped` or `neutral`), red (the runs with any other conclusion) or pending (the runs not yet concluded).
- The forge port gains a read of a commit's check runs (name, status, conclusion); the `gh` adapter reads
  `repos/<repo>/commits/<sha>/check-runs` (the endpoint `check_run_status` already calls), following pagination.
- In `dispatch_land.py`, before `forge.merge_pr`, poll the PR head's runs every `dispatch.landing_check_poll_seconds`
  (default 60) for at most `dispatch.landing_check_timeout_minutes` (default 45). Green merges; red refuses with a new
  finding naming each red run; the timeout refuses with a second new finding naming the pending runs. A head reporting no
  runs waits at least `dispatch.landing_check_grace_seconds` (default 120) before the empty set counts as green. A forge
  read error refuses (never passes). The PR stays open after a refusal, so re-running the landing merges once CI is
  green. The three keys join `DEFAULT_POLICY["dispatch"]` and the dispatch-block validation.
- The landing journal records the runs waited on and their conclusions.

Ledger key: `80-1-a-dispatch-landing-waits-for-its-pr-s-checks-and-refuses-on-a-red-one`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-284 (FR-231); AD-4 (orchestration outside `core/`), AD-8 (a pending or unevaluable signal
  is never passing), AD-40 (the landing policy; `landing_rules` unchanged).
- `flag-exempt: detector-or-gate` (`spec-feature-flag-governance` Q2: a gated gate reports a silent green).

## Acceptance Criteria

- Given every run on the PR head concluded `success`, `skipped` or `neutral` When the landing reaches the merge Then it merges and the journal lists the runs
- Given one run concluded `failure` (or `cancelled`, `timed_out`, `action_required`) When the landing reaches the merge Then it refuses with a finding naming that run, merges nothing and leaves the PR open
- Given runs still in progress at `dispatch.landing_check_timeout_minutes` When the landing reaches the merge Then it refuses with a finding naming the pending runs
- Given runs that conclude green between two polls When the landing waits Then it merges on the next poll
- Given a head reporting no runs When less than `dispatch.landing_check_grace_seconds` has passed Then it keeps waiting; past the grace the empty set counts as green
- Given the forge read fails When the landing reaches the merge Then it refuses, never merges
- Given a refused landing whose PR's CI later goes green When the landing is re-run Then it merges
- Given the three `dispatch` keys When the policy loads Then they default to 60, 45 and 120 and an invalid value is a named policy finding
- Given the wait is removed When the new tests run Then they fail (mutation)

## Tasks

1. Read `dispatch_land.py` around `forge.merge_pr` (:954), `ports/forge.py::check_run_status`, `adapters/forge_gh.py`
   (:247), `cli/land.py::_evaluate_required_checks`, and `core/policy.py`'s `dispatch` block.
2. Add the pure classifier in `core/` and the port read plus its `gh` adapter (paginated).
3. Add the bounded wait before the merge, the two findings in `core/findings.py`, the three policy keys, and the
   journal fields.
4. Tests against Story 59.1's forge fake with a fake clock for every matrix row; one adapter test parsing a recorded
   `check-runs` response; run the mutation by hand.

## Boundaries & Constraints

**Always:**
- A pending, unreadable or empty-within-grace set is never green (AD-8).
- The wait is bounded by policy.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not change `landing_rules` or `marshal land`'s single-poll contract.
- Do not close or force-merge a PR on a refusal.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| all green | every run success/skipped/neutral | merge | — |
| one red | a run failure/cancelled/timed_out/action_required | refuse, name it | PR stays open |
| still running | runs in progress at the timeout | refuse, name them | PR stays open |
| goes green | runs conclude between polls | merge on next poll | — |
| no runs yet | empty set inside the grace | keep waiting | — |
| no runs at all | empty set past the grace | merge | — |
| forge error | the read fails | refuse | never merge |

</intent-contract>

## Code Map

All paths under `src/shared/packages/pyforge-marshal/` (`PKG`); `M` = `PKG/src/pyforge/marshal`, `T` = `PKG/tests`.

- `M/core/landing_checks.py` -- NEW, pure (AD-4: no I/O, no clock). `CheckRun` (frozen: `name`, `status`, `conclusion`),
  `classify_check_runs(runs)` -> verdict with `state` in `green | red | pending | empty`, the `red` runs and the
  `pending` runs. Red beats pending (a red run refuses at once). `status != "completed"` is pending; a completed run
  is green only on `success`/`skipped`/`neutral`, any other or missing conclusion is red (AD-8). `CheckRun` lives in
  `core/` because `ports/` already imports `core/` (`ports/forge.py` imports `..core.egress`), never the reverse.
- `M/ports/forge.py:142` -- `check_run_status` is the neighbour; add `check_runs(repo: ForgeRef, ref: ForgeRef) ->
  tuple[CheckRun, ...]`. `ForgeRef` parameters only: `T/meta/test_ad34_egress_registry_completeness.py` flags a bare `str`.
- `M/adapters/forge_gh.py:247` -- `check_run_status` already calls `repos/<repo>/commits/<ref>/check-runs`. The new
  method pages it by hand (`?per_page=100&page=N` until `total_count` is reached; not `gh api --paginate`, whose
  concatenated-objects output differs across `gh` versions). GitHub's default `filter=latest` already collapses
  reruns to one run per name. A non-object payload, a missing `check_runs` list, a malformed run, a non-zero exit or
  runaway paging raises `ForgeCommandError`.
- `M/dispatch_land.py:953` -- the `forge.merge_pr` call. The reconcile head refresh at `:917-951` leaves `head_sha`
  final, so the wait goes between them. New `_wait_for_landing_checks(...)` polls `forge.check_runs`; the loop,
  not the classifier, owns the clock. `execute_dispatch_land` (`:569`) gains keyword-only `sleep` / `monotonic`
  (defaults `time.sleep` / `time.monotonic`) so tests drive a fake clock. Outcome lands in `data["landing_checks"]`.
- `M/core/findings.py:1807` (registry; docstring `:835-890`) and `M/core/verdict.py:1203` -- `MRS-DISP-056` (a red
  run, ERROR) and `MRS-DISP-057` (runs still pending at the timeout, ERROR); 050-055 are taken. A forge read error
  reuses `MRS-DISP-018` (the landing's own forge-lookup refusal) so no third code is minted.
- `M/core/policy.py:626` (`DEFAULT_POLICY["dispatch"]`) and `:921` (`_valid_dispatch_block`, a closed key set today).
  Reuse `_valid_positive_number` (`:1420`) for poll seconds and timeout minutes and `_valid_attempt_count` (`:1380`)
  for grace seconds. Consumer reads, like `cli/dispatch.py:1434`, take `dispatch.value.get(key, default)`.
- `M/dispatch_supervisor/__main__.py:1090` and `M/core/journal.py:150` -- the landing outcome payload gains the
  `landing_checks` record; the new field joins `offload_fields` beside `land_findings`.
- Read-only: `M/cli/land.py::_evaluate_required_checks` (`marshal land`'s single poll), `landing_rules`,
  `M/dispatch_land_heal.py` (see the deferred entry), `sprint-status-ledger.yaml`, every `SPEC.md`.
- Tests: `T/unit/test_landing_checks.py` NEW; `T/unit/test_dispatch_landing.py` (`FakeForge` at `:150` gains a green
  `check_runs`; every other `execute_dispatch_land` fake follows); `T/unit/test_forge_gh.py` (adapter on a recorded
  response); `T/unit/test_policy.py` (`:654` pins `{"max_parallel": 2}`); `T/unit/test_findings.py`, `test_verdict.py`,
  and `T/unit/test_findings.py` / `test_verdict.py` for the two codes (`T/meta/test_finding_remedy_reference_sync.py`
  covers Genesis `FindingType`, not `MRS-*` codes -- it needs no change). Line anchors above are as of the baseline.
- `M/dispatch_land_heal.py` -- `try_heal_dispatch_land_merge` -> `_try_union_heal`: pushes the union commit (main merged
  into the branch, a NEW head) and calls `forge.merge_pr(expected_head_sha=new_sha)` at once, so that head's runs were
  never read. `_try_local_main_advance` merges the SAME head the pre-merge wait already cleared, so it needs no second
  wait. `DispatchLandHealResult` is the return type. `T/unit/test_dispatch_land_heal.py` (`FakeForgeHeal`,
  `_HonestForge`) calls the heal directly and has no `check_runs`.
- `M/dispatch_supervisor/__main__.py:1664-1684` -- the tick loop writes its heartbeat observation and calls
  `_publisher.heartbeat(run_publish_handle)` only AFTER the landing returns; `_land_or_journal_block` ->
  `_run_and_journal_landing` (`:1031-1110`) run the landing inline. Read-only evidence:
  `src/shared/packages/django-pyforge/src/django_pyforge/supervisor.py::sweep_lost_runs` (beat-scheduled) marks a live
  run FAILED `heartbeat_lost` once `heartbeat_at` is older than `queues.station_time_limit(station)` (300 s by
  default); a published run with no `celery_task_id` is marked without asking a worker.
- `M/cli/dispatch.py:927` (`_attempt_harness_done_cap4`) -- the CLI landing path: no supervisor, no publish handle, so
  no heartbeat callback; only the `:1205` sidecar read-back pass-through changes.
- `M/cli/config.py:118,211,261` -- three comments still call the `dispatch` block a one-int-knob "factory wave cap".
- `M/core/journal.py:487-540` -- `resolve_scope_violation_advisories_from_payload` already holds the sidecar read-back
  (ref -> blob -> parse -> field); attempt 1 copied it into a second helper.

## Tasks & Acceptance

Review loop 1 (2026-10-01) re-derives the code. Attempt 1's full diff is at
`_bmad-output/projects/pyforge-marshal/implementation-artifacts/80-1-attempt-1.patch` (gitignored Tier-3; read it,
re-apply what the KEEP list in the Spec Change Log names, then do the AMEND items).

**Execution:**
- `M/core/landing_checks.py` NEW + `T/unit/test_landing_checks.py` -- KEEP attempt 1: `CheckRun`, `CheckState`
  (green / red / pending / empty), `classify_check_runs`; red beats pending; a completed run with no conclusion is red.
- `M/ports/forge.py`, `M/adapters/forge_gh.py`, `T/unit/test_forge_gh.py` -- KEEP: `ForgePort.check_runs` and the
  hand-paged `GhForge.check_runs`; a partial read raises `ForgeCommandError`. Keep the `ForgeRef` / `PrInfo` validation
  tests: the touched-module coverage floor (80%) failed on `ports/forge.py` without them.
- `M/core/policy.py`, `M/schemas/policy.json`, `T/unit/test_policy.py` -- KEEP the three keys, the subset validator and
  `resolve_landing_check_settings`. AMEND: a huge int for `landing_check_grace_seconds` (`10**400`) is rejected by the
  validator (`MRS-POLICY-002` naming `dispatch`) and the resolver never raises (`float()` of an unprobed int raises
  `OverflowError`).
- `M/core/findings.py`, `M/core/verdict.py`, `T/unit/test_findings.py` -- KEEP `MRS-DISP-056` / `MRS-DISP-057` (ERROR).
- `M/core/journal.py`, `M/cli/dispatch.py` -- KEEP `LANDING_CHECKS_FIELD`, the sidecar read-back in
  `resolve_land_findings_from_payload` and the `sidecars=` pass-through. AMEND: one reader for an offloaded field --
  `resolve_scope_violation_advisories_from_payload` uses the shared helper, not a second copy.
- `M/dispatch_land.py` -- KEEP `_wait_for_landing_checks` (order inside a poll, sleep clipped to the time left) and the
  `sleep` / `monotonic` seams. AMEND: (a) the journal record names the `head_sha` it waited on; (b) an optional
  keyword-only `on_wait_tick: Callable[[], None] | None` is called after every poll and at least every
  `min(poll_seconds, 60)` seconds; (c) the wait is passed to the heal as `await_checks` and a heal refusal reports the
  wait's own finding instead of `MRS-DISP-020`, with both heads' records journaled.
- `M/dispatch_land_heal.py` -- AMEND: `try_heal_dispatch_land_merge` and `_try_union_heal` take an optional keyword-only
  `await_checks: Callable[[str], Finding | None] | None = None`; `_try_union_heal` calls it with the pushed `new_sha`
  before its retried `forge.merge_pr` and, on a finding, returns without merging (`DispatchLandHealResult` carries it).
  Default `None` leaves every direct caller and fake unchanged. `_try_local_main_advance` takes no wait.
- `M/dispatch_supervisor/__main__.py` -- KEEP the `landing_checks` outcome payload and its offload. AMEND: pass an
  `on_wait_tick` that appends the loop's heartbeat observation (extract the builder; no second copy) and calls
  `_publisher.heartbeat(run_publish_handle)` when a handle exists.
- `M/cli/config.py` -- AMEND: the three `dispatch` comments describe the four-key block.
- `T/unit/test_dispatch_landing.py`, `T/unit/test_dispatch_land_heal.py`, `T/unit/test_dispatch_supervisor_spec_block.py`
  -- KEEP attempt 1's matrix tests (fake clock, every matrix row, post-reconcile head, re-run, record survives a failed
  merge, journal round trip) and add the AC below; `FakeForge` answers green `check_runs`.
- Run the mutations by hand on the FINAL tree and restore after each (`cmp` against a saved copy): remove the wait;
  remove the heal's `await_checks` call; make the default `sleep` a no-op; remove the tick call. Each must turn a new
  test red; record the counts under Auto Run Result.

**Acceptance Criteria** (system-level, beyond the contract's nine):
- Given a first merge that fails and a union heal that pushes a new head, when that head's runs are red or still
  pending at the timeout, then no retried merge happens, the finding is `MRS-DISP-056` / `MRS-DISP-057` (not
  `MRS-DISP-020`), and the PR stays open.
- Given the same heal and a green new head, when the wait ends, then the retried merge runs with the new sha and the
  journal records both heads' runs.
- Given a landing that waits, when it polls, then `on_wait_tick` fires at least every `min(poll_seconds, 60)` seconds
  of wait, and the supervisor writes a heartbeat observation and calls the publisher heartbeat each time; a landing
  driven from the CLI path passes no tick and behaves as before.
- Given `landing_check_grace_seconds = 10**400`, when the policy composes, then `MRS-POLICY-002` names `dispatch` and
  nothing raises.
- Given no clock seams and a pending head, when the landing waits, then the real `time.sleep` receives
  `poll_seconds` (a no-op default sleep turns this test red).

## Spec Change Log

### 2026-10-01 -- review pass 1 (bad_spec, loop 1)

- **Trigger:** two verified findings with one root each, both outside the intent contract. (1) Verification Gap VG1, Blind
  B1, Edge E10, Intent Alignment IA2: the union heal pushes a new head and merges it with no wait, so the gate leaks on
  every ledger or memlog conflict -- the common case in a parallel drain. (2) Blind B7, Edge E9, VG-other, IA1: the wait
  can block the supervisor for the whole timeout with no heartbeat, past the portal's 300 s `heartbeat_lost` limit.
- **Amended (outside the intent contract):** Code Map (the heal, the supervisor heartbeat, the CLI path, the stale
  `cli/config.py` comments, the journal helper; the wrong meta-test pointer), Tasks & Acceptance (new), Design Notes (the
  heal re-wait, the heartbeat tick, the overflow probe), and the planning-time `deferred:` entry for the heal paths is
  REMOVED -- it is now in scope, not deferred (a separate story was never a named blocker).
- **Known-bad state avoided:** a union-healed head merging with CI never read, and a published dispatch run swept to
  FAILED while its landing is still waiting.
- **Baseline:** `baseline_revision` stays `68b35f7e1cb04295f729647c2d0ee4ff060ab417`, the pre-story revision, so the
  next review reads the cumulative diff; the auto-checkpoint HEAD holds attempt 1 and is not a baseline.
- **KEEP:** the classifier and its tests; `ForgePort.check_runs` and the hand-paged `GhForge.check_runs` with its
  recorded-response and malformed-payload tests; the `ForgeRef` / `PrInfo` tests the coverage floor needs;
  `_wait_for_landing_checks`' order of checks inside a poll and its clipped last sleep; the `sleep` / `monotonic` seams;
  `MRS-DISP-056` / `MRS-DISP-057` (ERROR) and their docstring; the three policy keys, the subset validator and
  `resolve_landing_check_settings`; `LANDING_CHECKS_FIELD`, the offload and the `resolve_land_findings_from_payload`
  sidecar read-back with its `cli/dispatch.py` pass-through; the fake-clock matrix tests and the by-hand mutation (19
  red with the wait stubbed).

## Design Notes

- **The three keys are optional in a project's block.** `_merge_field` replaces a block whole, and the tracked
  `marshal-policy.toml` declares only `max_parallel`. The validator accepts any non-empty subset of the four keys; a
  missing key reads as its default at the consumer. An invalid value rejects the whole block with `MRS-POLICY-002`
  naming `dispatch`, and composition falls back to the layer below.
- **Order inside one poll:** read; red refuses; green merges; the empty set merges only once `grace` has elapsed;
  otherwise the timeout check; otherwise sleep `min(poll, time left)`. The timeout wins over the grace (a grace longer
  than the timeout refuses at the timeout, never merges on an empty set).
- **Known limit:** GitHub reports a commit's runs as workflows register, so a poll can see only the runs created so
  far. The grace bounds the empty case only; a head with two of six workflows registered and concluded reads green.
  The spec fixes the contract at "every reported run concluded"; hardening it needs the PR's expected check set.
- **The heal re-waits on the head it pushes.** The pre-merge wait clears `head_sha`. `_try_union_heal` pushes a different
  head (main merged into the branch), so its retried merge would run on a commit CI has not seen. The heal takes the wait
  as an optional callable (`head_sha -> Finding | None`, `None` = may merge); a refusal comes back on
  `DispatchLandHealResult` and `dispatch_land.py` reports that finding. `_try_local_main_advance` merges the head already
  cleared, so it takes no wait. Each head gets its own timeout; total waiting is bounded by two timeouts, never open.
- **The wait keeps the run alive.** The portal marks a live run `heartbeat_lost` after `station_time_limit` (300 s by
  default); a landing can now block for the whole timeout. The wait calls an injected tick; the supervisor owns what a
  tick does (journal heartbeat + publisher heartbeat), `dispatch_land.py` stays free of publisher knowledge. The CLI
  landing path has no run to keep alive and passes none.
- **A huge policy int is a finding, never a crash.** `_valid_attempt_count` has no magnitude probe, so `10**400` passes
  validation and `float()` raises in the resolver. Probe it in the block validator the way `_valid_parallel_count` does.

## Binding

Parent capability: `spec-pyforge-marshal` CAP-284 (FR-231).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-01 (later) entry.
Ledger key: `80-1-a-dispatch-landing-waits-for-its-pr-s-checks-and-refuses-on-a-red-one`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: `flag-exempt: detector-or-gate`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`).

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).

### 2026-10-01 — Review pass
- verdicts: 40 findings — high 0, medium 9, low 28, false 1, maybe-false 2
- routing: two `bad_spec` entries (the heal path; the heartbeat) force loop 1; every other row is `patch` (carried into the re-derivation through Tasks & Acceptance) or `reject`. Attempt 1's diff is saved at `_bmad-output/projects/pyforge-marshal/implementation-artifacts/80-1-attempt-1.patch`.
- findings:
  - Blind Hunter
    - `[medium]` `[bad_spec]` heal paths merge without a gate — verified: `_try_union_heal` pushes `new_sha` and calls `forge.merge_pr` at once (`dispatch_land_heal.py`), so CI never read the union head; `_try_local_main_advance` merges the SAME head the pre-merge wait cleared, so that half is not a leak. The planning `deferred:` entry named a signature change as the reason, which is not a Dream-sized effort or a named blocker (AGENTS.md § Behavioural guidelines 3), and the intent does not exclude the heal. Amended: Code Map, Tasks & Acceptance (heal `await_checks`), Design Notes; the `deferred:` entry is removed.
    - `[low]` `[patch]` the `landing_checks` record carries no `head_sha` — verified: it holds outcome, polls, seconds and runs; after the heal re-waits, a reader cannot tell which head a record covers. Carried: Tasks (the record names the head); the bounds already live in policy.
    - `[low]` `[reject]` one transient forge error aborts a 45-minute wait — the contract says a read error refuses (matrix row "forge error"); a retry budget adds a branch and a parameter outside it; the PR stays open and a re-dispatch merges.
    - `[low]` `[reject]` partial workflow registration reads green — documented in Design Notes; the intent defines green over the runs reported; a mitigation needs the PR's expected check set, which the intent does not supply. The wait starts after push, PR update and the merge-tree preview, so registration normally precedes it.
    - `[low]` `[reject]` Checks API only, no ignore list — the intent names the `check-runs` endpoint and "every run"; this repo's CI reports check runs.
    - `[low]` `[reject]` loose poll/timeout bounds and read overshoot — operator-set policy values the spec types as positive numbers; overshoot is one read (30 s per page) in practice; the overflow subcase is its own row below.
    - `[medium]` `[bad_spec]` no progress during the wait — verified: the heartbeat observation and `_publisher.heartbeat` run only after the landing returns (`dispatch_supervisor/__main__.py:1664-1684`), and `sweep_lost_runs` (beat-scheduled) marks a live run FAILED `heartbeat_lost` once `heartbeat_at` is older than `station_time_limit` (300 s default) with no worker check for a row without `celery_task_id`. Amended: Code Map, Tasks & Acceptance (`on_wait_tick`), Design Notes.
    - `[low]` `[reject]` the "re-run the landing" remedy is not wired — verified: `_landing_already_journaled` stops the supervisor re-landing after a refusal, but a re-dispatch of the story reaches `_attempt_harness_done_cap4`, which calls `execute_dispatch_land` again; AC 7 is stated at that function. Naming a command in the message risks naming the wrong one.
    - `[low]` `[reject]` `resolve_landing_checks_from_payload` has no production caller — it is the reader the round-trip test uses to prove the record survives the offload; no harm named.
    - `[low]` `[patch]` the offload read-back is duplicated — verified: the helper copies `resolve_scope_violation_advisories_from_payload`'s ref, blob, parse and field steps; the two copies will drift. Carried: Tasks (one reader).
    - `[low]` `[reject]` check-run validation duplicated — the same split as `PrInfo.__post_init__` and `_pr_info_from_json`: the dataclass guards direct construction, the adapter translates to `ForgeCommandError`.
    - `[low]` `[reject]` `MRS-DISP-018` reused for a checks read — the spec's own decision (no third code); the message names the checks, the PR and the head.
    - `[low]` `[reject]` test hygiene — the mutation test patches a private name because it is the committed form of the mutation criterion; `_BrokenChecksForge` defined after use resolves at call time; the `ForgeRef`/`PrInfo` tests were needed by the 80% touched-module coverage floor (`ports/forge.py` read 79.2% without them); the missing heal test is the first row.
    - `[low]` `[reject]` bookkeeping — stale Code Map anchors and a wrong meta-test pointer are spec text (the fix is to edit this build's spec; the pointer is corrected inside the amendment anyway); documenting the keys in a SKILL.md or `marshal-policy.toml` is outside the intent.
  - Edge Case Hunter
    - `[low]` `[patch]` a huge `landing_check_grace_seconds` crashes the landing — verified live: `compose(project={"dispatch": {"landing_check_grace_seconds": 10**400}})` returns no finding and `resolve_landing_check_settings` raises `OverflowError`, against its own "never raises" docstring. Carried: Tasks and an AC.
    - `[low]` `[reject]` tiny poll interval — same as the loose-bounds row above.
    - `[low]` `[reject]` runs vanish after being seen — needs a degraded API answering empty after non-empty; the guard also needs a message change beyond the contract.
    - `[low]` `[reject]` page shift during paging — a millisecond window that matters only past 100 runs; the next poll re-reads the whole set.
    - `[maybe-false]` `[reject]` same-name reruns reported beside each other — GitHub documents `filter=latest` as the default for this endpoint, and a wrong answer here is a false refusal, the safe direction. Settle with `gh api repos/<repo>/commits/<sha>/check-runs?filter=all` against the default on a commit with a rerun; if true it is low.
    - `[low]` `[reject]` transient error aborts the wait — same as the Blind Hunter row.
    - `[low]` `[reject]` legacy commit statuses are invisible — same as the Checks API row.
    - `[low]` `[reject]` read overshoot past the timeout — same as the loose-bounds row.
    - `[medium]` `[bad_spec]` no heartbeat during the wait — same root as the Blind Hunter heartbeat row; amendment as there.
    - `[medium]` `[bad_spec]` heal merges unchecked — same root as the Blind Hunter heal row; amendment as there.
    - `[false]` `[reject]` the CLI path stalls a serial drain up to 45 minutes per red or pending PR — a red head refuses at once (red beats pending), so no stall for red; waiting on pending checks is the specified behaviour.
    - `[maybe-false]` `[reject]` claim: `filter=latest` collapses reruns — same as the same-name-reruns row.
    - `[low]` `[reject]` claim: the PR stays open so a re-run merges — same as the re-run row; verified the supervisor does not re-land on its own.
    - `[low]` `[patch]` claim: the resolver "never raises" — same root as the overflow row; patch as there.
    - `[low]` `[patch]` `cli/config.py` comments still say "one int knob" / "factory wave cap" — verified at lines 118, 211 and 261. Carried: Tasks (comment-only).
  - Verification Gap
    - `[medium]` `[bad_spec]` the heal paths merge a head whose checks were never read — pre-verified; its filed disposition was `defer`, which is overridden for the reason in the first row. Same root and amendment as the heal row.
    - `[medium]` `[patch]` the default clock path is never exercised with a pending head — verified: with the default `sleep` replaced by a no-op, all 94 tests in `test_dispatch_landing.py` and `test_dispatch_supervisor_spec_block.py` still pass. Carried: Tasks, an AC and a by-hand mutation.
    - `[low]` `[patch]` other: stale `cli/config.py` comments — same row as the Edge Case Hunter deletion finding.
    - `[medium]` `[bad_spec]` other: the landing blocks the supervisor with no heartbeat — unverified when filed, now verified (see the heartbeat row). Same root and amendment.
  - Intent Alignment
    - `[medium]` `[bad_spec]` no test goes supervisor to wait to `GhForge`, and the supervisor blocks up to 45 minutes — the supervisor-blocking half is the heartbeat root; the amendment adds a supervisor-level tick test.
    - `[medium]` `[bad_spec]` heal merges bypass the wait — same root as the heal row.
    - `[low]` `[reject]` journal surface — both halves are tested (envelope data; supervisor payload with a faked landing) and joined by one shared constant; the final read's runs are what "runs waited on" means; the CLI path journals no landing finding at all, before or after.
    - `[low]` `[reject]` re-run in production is a re-dispatch — same as the re-run row.
    - `[low]` `[reject]` mutation is a private-name stub with no record in the diff — the committed test exists; the by-hand run is recorded under Auto Run Result at finalize.
    - `[low]` `[reject]` the tracked policy's `dispatch` value lacks the three keys — AC 8 holds for the composed defaults; for a project block (`max_parallel` only; `_merge_field` replaces the field whole) the resolver fills the defaults, and that is tested.
    - `[low]` `[reject]` the contract is "every reported run" — same as the partial-registration row.

### 2026-10-01 — Review pass (loop 1, after the re-derivation)
- verdicts: 41 findings — high 0, medium 1, low 36, false 3, maybe-false 1
- routing: no `bad_spec` and no `intent_gap` this pass; six `patch` entries (seven rows) sent to the same implementer; every other row is `reject`. Rows marked `carried` repeat a pass-1 row (same location, same claim); their verdict and route are kept and nothing is verified again. The Intent Alignment report reached me wire-compressed first and was resent in full by its reviewer; the rows below use the full text.
- real-world checks run for this pass (read-only `gh api` GETs, authenticated, 5000/5000 core quota): a real `check-runs` page for `origin/main` (4 runs, all completed/success) parses through the real `GhForge.check_runs` and classifies green; `filter=all` and the default returned the same `total_count` on each of the 12 most recent `main` commits (none had a same-name rerun).
- findings:
  - Blind Hunter
    - `[low]` `[reject]` carried: a partial set of runs reads green — documented limit (Design Notes); the intent defines green over the runs reported.
    - `[low]` `[reject]` an empty set merges silently after the grace — the intent says that set "counts as green"; the journal record carries `outcome: "no-runs"`, the polls and the seconds waited. A WARN finding is beyond the contract.
    - `[low]` `[reject]` carried: Checks API only — the intent names the `check-runs` endpoint.
    - `[low]` `[reject]` carried: no ignore list or opt-out — the intent says "every run"; the refusal leaves the PR open for a hand merge.
    - `[low]` `[reject]` the CLI harness-done path hides the finding text (`land_fail_operator_message` takes a verdict and a named target) — unchanged for every landing finding since before this story (MRS-DISP-047/048 are hidden the same way) and the refusal names the PR; a fix changes that function's contract.
    - `[low]` `[patch]` the CLI path drops the `landing_checks` record — verified: `_land_envelope` is discarded at `cli/dispatch.py:2564`, and this is the path a refused landing is re-run through. Patched: copy the record into the command's data, with a test.
    - `[low]` `[reject]` the CLI path blocks silently for up to 45 minutes — an operator-run command in a terminal, with no run to keep alive; the amended Design Notes say it passes no tick.
    - `[low]` `[reject]` carried: `resolve_landing_checks_from_payload` has no production caller — the reader the round-trip test uses; no harm named.
    - `[low]` `[reject]` the journal records no in-progress state (the intent entry follows the landing; the heartbeat names no pending run; `_WaitHeartbeat` freezes `git_facts`) — the heartbeat is liveness evidence, the intent asks only for the runs waited on, and a killed supervisor leaves an open PR a re-run lands.
    - `[low]` `[reject]` carried: a tiny poll interval hammers the API — operator-set policy value typed "positive number" by the spec.
    - `[low]` `[reject]` carried: the tick guarantee ignores one read's duration — a read is one 30 s `gh` call per page in practice.
    - `[low]` `[reject]` carried: a single transient read error aborts the wait — the contract says a read error refuses.
    - `[low]` `[reject]` the adapter's error messages echo `{data!r}` / `{entry!r}` — the same idiom as `_pr_info_from_json` and `pr_merge_state` in the same module; the journal offload bounds the payload.
    - `[low]` `[reject]` `landing_check_grace_seconds` is int-only and a bad value rejects the whole `dispatch` block, `max_parallel` included — `_merge_field` poisons a layer's field on one bad entry for every mapping-typed key; the spec's contract is a named finding, and `MRS-POLICY-002` names `dispatch`.
    - `[low]` `[patch]` a 138-character docstring line in `_valid_dispatch_block` — verified at `core/policy.py:957` (ruff's E501 is off in this package, so the gate does not see it). Patched: re-wrap.
    - `[low]` `[patch]` after a union heal the result and `data["head_sha"]` keep the pre-heal head — verified: `merge_sha=head_sha` and `data["head_sha"]` are untouched after the heal at the baseline revision too, but this story now records the healed head in `landing_checks.heal.head_sha`, so the two disagree on one landing. Patched: follow the healed head, with a test.
    - `[false]` `[reject]` worst-case waiting is two timeouts with no documented budget — the amended Design Notes state it ("total waiting is bounded by two timeouts, never open") and each wait is bounded by `settings.timeout_seconds`.
    - `[low]` `[reject]` `heal_waits` is a list read with `[-1]` — a closure appends to a list instead of a `nonlocal` rebinding; one element in practice, no harm.
    - `[low]` `[reject]` carried: the in-suite mutation tests patch private names — they are the committed form of the mutation criterion; the by-hand counts are under Auto Run Result.
    - `[low]` `[reject]` carried: `_BrokenChecksForge` is defined after its test — resolves at call time.
    - `[low]` `[reject]` `_GuardedClock` counts reads through a `getattr` hack — test-helper style; it guards against an unbounded loop and fails loudly.
    - `[low]` `[reject]` carried: no test for the partial-registration race or a page shift — the spec fixes neither as a contract.
    - `[false]` `[reject]` `_sleep_with_ticks` has no test of its own — verified: `test_a_poll_interval_shorter_than_a_minute_ticks_at_that_interval` and `test_a_long_poll_interval_is_sliced_so_the_wait_still_ticks_every_minute` drive it through the wait, and the by-hand mutation that removes the between-slice tick turns one test red.
    - `[low]` `[reject]` carried: the `ForgeRef` / `PrInfo` tests are unrelated — the 80% touched-module floor on `ports/forge.py` needs them.
  - Edge Case Hunter
    - `[low]` `[reject]` a healed head reads empty past the grace although the first head had runs — the intent's empty-set rule applies per head; GitHub registers a pushed head's workflows within seconds, against a 120 s grace; the guard changes the empty-set contract.
    - `[low]` `[reject]` `origin/main` moves again during the healed head's wait and the single-shot retried merge fails — fails safe (`MRS-DISP-020`, PR open, a re-run heals again); a heal-and-wait loop needs a retry budget the intent does not supply.
    - `[low]` `[reject]` the first merge error is not recorded when the healed head's checks refuse — `landing_checks.heal` records the pushed head and its runs; the first error is the reason the heal ran, not an outcome.
    - `[maybe-false]` `[reject]` carried: same-name reruns reported side by side — documented default is `filter=latest`; probed 12 recent `main` commits, `filter=all` equals the default on every one, none had a rerun. Settle with a commit that has a rerun; if true it is low and fails safe.
  - Verification Gap
    - `[medium]` `[patch]` the terminal-verdict `_land_or_journal_block` call can lose `session_alive` / `publish_heartbeat` with no test failing — pre-verified. Patched: a twin of `test_supervisor_heartbeats_the_run_through_the_landing_wait` on the terminal path, turned red by hand.
    - `[low]` `[patch]` `resolve_max_parallel` on a `dispatch` block with no `max_parallel` is unpinned — pre-verified: the validator now accepts that shape and no test composes it against the wave cap. Patched: one test.
    - `[low]` `[reject]` carried: `resolve_landing_checks_from_payload` has no production caller.
    - `[low]` `[reject]` carried: the mutation tests stub private names.
    - `[false]` `[reject]` three marshal import-linter meta tests fail without the env's `bin` on `PATH` — an environment artifact of the reviewer's shell, not the change; `pyforge-marshal-test` runs them green.
  - Intent Alignment
    - `[low]` `[reject]` carried: the tracked policy's `dispatch` value lacks the three keys — AC 8 holds for the composed defaults and a project block is filled at the consumer, tested.
    - `[low]` `[patch]` the CLI re-entry discards the envelope, so no journal record — same root and patch as the Blind Hunter CLI row; the no-tick half is the silent-block row above (rejected).
    - `[low]` `[reject]` the diff gates two merges and the local-`main` advance none — by design: that advance merges the head the pre-merge wait cleared.
    - `[low]` `[reject]` surfaces beyond the intent's list (heartbeat, offload read-back, comments) — all in scope through the loop-1 amendment, each tied to a verified finding.
    - `[low]` `[patch]` the adapter's "recorded response" is hand-built — Task 4 says recorded; a real page now exists and parses (see the checks above). Patched: commit the real payload as a fixture with one test.
    - `[low]` `[reject]` the re-run test takes `create_pr` both times, not the update path — the two paths converge before the wait, and the update path is covered by the pre-existing landing tests.
    - `[low]` `[reject]` no committed proof that other tests turn red without the wait — by-hand mutations on the final tree are recorded under Auto Run Result (34 red with the wait removed; 10 with the heal's call removed; the default-clock, tick and supervisor mutations each red).
    - `[low]` `[reject]` carried: four classifier states and the empty-set rule in the loop, not `core/` — the loop owns the clock and the grace (AD-4).

## Auto Run Result

Status: done
Blocking condition: none.

### Summary of implemented change

A dispatch landing now waits for its PR head's check runs before it merges, and refuses on a red run, at the timeout, or when the forge cannot be read. The PR stays open after every refusal, so a re-run lands once CI is green.

- **Classifier.** `core/landing_checks.py` (pure): `CheckRun`, `CheckState` (green / red / pending / empty), `classify_check_runs`. Red beats pending; a completed run with no conclusion is red; a run not `completed` is pending.
- **Port and adapter.** `ForgePort.check_runs` and the hand-paged `GhForge.check_runs` (`?per_page=100&page=N`, a 50-page runaway guard); any non-zero exit, malformed payload, short page or runaway paging raises `ForgeCommandError`, never a partial list.
- **The wait.** `_wait_for_landing_checks` in `dispatch_land.py`, between the post-reconcile head refresh and `forge.merge_pr`. Order inside one poll: read; read error refuses (`MRS-DISP-018`); red refuses (`MRS-DISP-056`); green merges; an empty set merges only past the grace; the timeout refuses (`MRS-DISP-057`); else sleep `min(poll, time left)`. `sleep` / `monotonic` are keyword-only seams.
- **Policy.** `DEFAULT_POLICY["dispatch"]` gains `landing_check_poll_seconds` (60), `landing_check_timeout_minutes` (45) and `landing_check_grace_seconds` (120). The block validator accepts any non-empty subset of its four keys; `resolve_landing_check_settings` fills an omitted key at the consumer, so the tracked `marshal-policy.toml` (which declares only `max_parallel`) still composes. A bad value is `MRS-POLICY-002` naming `dispatch`; a huge grace int (`10**400`) is rejected, never a crash.
- **Journal.** `data["landing_checks"]` names the `head_sha`, outcome, polls, seconds waited and each run's status and conclusion; the supervisor journals it in the landing outcome and offloads it beside `land_findings`; `resolve_land_findings_from_payload` now reads an offloaded `land_findings` back, so a refusal stays visible to `marshal status`. The CLI harness-done path copies the record into its command data.
- **Review-loop additions (loop 1).** The union heal re-waits on the head it pushes (`await_checks` on `try_heal_dispatch_land_merge`; a red or pending healed head merges nothing and reports `MRS-DISP-056` / `057` through `DispatchLandHealResult.checks_refusal`); a union-healed landing reports the healed head as `merge_sha` and `data["head_sha"]`; the wait ticks (`on_wait_tick`, at least every `min(poll_seconds, 60)` s) so the supervisor writes its heartbeat observation and calls the publisher heartbeat during a wait the portal would otherwise sweep as `heartbeat_lost`.

### Files changed

Under `src/shared/packages/pyforge-marshal/`.

- `src/pyforge/marshal/core/landing_checks.py` (new) -- the pure classifier.
- `src/pyforge/marshal/ports/forge.py`, `adapters/forge_gh.py` -- `check_runs` on the port and the paged `gh` read.
- `src/pyforge/marshal/dispatch_land.py` -- the wait, the tick, the healed-head wait and head reporting.
- `src/pyforge/marshal/dispatch_land_heal.py` -- `await_checks`, `checks_refusal`.
- `src/pyforge/marshal/dispatch_supervisor/__main__.py` -- the one heartbeat builder, the wait tick, the `landing_checks` outcome field and its offload.
- `src/pyforge/marshal/core/policy.py`, `schemas/policy.json`, `cli/config.py` -- the three keys, the validator, the resolver, the comments.
- `src/pyforge/marshal/core/findings.py`, `core/verdict.py` -- `MRS-DISP-056` / `057` (ERROR).
- `src/pyforge/marshal/core/journal.py`, `cli/dispatch.py` -- the field, the sidecar read-back, the CLI record pass-through.
- Tests under `tests/unit/`: `test_landing_checks.py` (new), `test_dispatch_landing.py`, `test_dispatch_land_heal.py`, `test_dispatch_supervisor_spec_block.py`, `test_dispatch_supervisor_main_loop.py`, `test_forge_gh.py`, `test_findings.py`, `test_policy.py`, `test_dispatch.py`, `test_dispatch_stop_retry.py`; fixture `tests/fixtures/check_runs_main_2026-10-01.json` (a real GitHub response for `main` at `68b35f7e1c`).
- Tracked planning: this story spec; the `.memlog.md` of `spec-pyforge-marshal` (three surface-reconcile events) and `spec-pyforge-core` (two, the co-governor the detector named). No baseline was stamped; the ledger and every `SPEC.md` are untouched.

### Review findings breakdown

Two review passes, four layers each. Attempt 1's diff is at `_bmad-output/projects/pyforge-marshal/implementation-artifacts/80-1-attempt-1.patch` (gitignored). Every row and its evidence are in `## Review Triage Log`.

- **Pass 1 (40 findings: medium 9, low 28, false 1, maybe-false 2).** Two `bad_spec` roots forced loop 1: the union heal merged a pushed head with no wait, and the wait could block the supervisor past the portal's 300 s `heartbeat_lost` limit. Seven rows were `patch` (carried into the re-derivation: the record names its head, one sidecar reader, a magnitude probe on the grace key, stale `cli/config.py` comments, the default-clock test). Twenty-five were rejected.
- **Pass 2 (41 findings: medium 1, low 36, false 3, maybe-false 1).** No `bad_spec`, no `intent_gap`. Patches applied: 6 entries (7 rows) -- medium 1 (the terminal-verdict supervisor call site could lose its heartbeat wiring unnoticed; a twin test now pins it, and turns red when the kwargs are dropped), low 5 (the CLI harness-done path discarded the `landing_checks` record; a union-healed landing reported the pre-heal head; a 138-column docstring line; `resolve_max_parallel` on a block with no `max_parallel` was unpinned; the "recorded" adapter response was hand-built, a real one is now a fixture). Thirty-four rows rejected.
- **Deferred: none.** The planning-time `deferred:` entry for the heal paths was removed when the heal was brought into scope (a separate story was never a named blocker).
- **Rejected, by reason** (per-row evidence in the log):
  - **The intent's own contract:** a read error refuses with no retry budget; green is defined over the reported runs (partial workflow registration reads green -- a documented limit); the empty set merges past the grace and journals `no-runs`; only the Checks API is read, with no ignore list (the intent names the endpoint and says "every run"); the heal and CLI-path journal surfaces beyond the record.
  - **Operator-set policy values:** a tiny poll interval or huge timeout (the spec types them as positive numbers); an int-only grace poisoning the `dispatch` block (every mapping-typed key behaves so).
  - **Already covered or false:** `_sleep_with_ticks` has no test (two tests and a mutation cover it); a serial drain stalls on a red PR (red refuses at once); two timeouts with no documented budget (documented in Design Notes); three import-linter meta failures (the reviewer's `PATH`, green under the pixi task).
  - **Idiom and test style:** duplicated validation (the `PrInfo` split), a private-name mutation test (the committed form of the mutation criterion), the `ForgeRef` / `PrInfo` tests (needed by the 80% touched-module floor), `heal_waits` as a list, `_GuardedClock`, `resolve_landing_checks_from_payload` with no production caller.
  - **Unlikely and fail-safe:** a vanished run set after runs were seen; a page shift past 100 runs; `origin/main` moving during a healed head's wait (refuses `MRS-DISP-020`, the PR stays open); same-name reruns (the maybe-false row: `filter=all` equals the default on the 12 most recent `main` commits, and a false refusal is the safe direction).
  - **Spec text:** stale Code Map anchors (fixed inside the loop-1 amendment).
- **Follow-up review recommended: `false`.** Pass 2 patched no `high` and one `medium` (patched counts: high 0, medium 1, low 5).

### Verification performed

Every verdict below was read from an exit code or a log file, never through a pipe, on the final tree.

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`: exit 0, 9422 passed, 1 skipped, 12 deselected.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`: exit 0, 130 passed, 3 skipped.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate`: exit 0, 11 touched modules at or above the 80% floor.
- `pixi run --frozen -e pyforge-guild lint-types`: exit 0 (ruff, ruff format, mypy over the ten packages, target-version, precommit-config).
- `pixi run --frozen -e pyforge-guild spec-surface-check`: exit 0, no `drift-presumed` line after the memlog entries; `python scripts/spec_surface_reconcile.py`: exit 0, "no drift". Re-checked after each memlog append.
- Matrix test audit: every row of the I/O & Edge-Case Matrix has a covering test that ran and passed -- all green, one red (four reasons), still running at the timeout, goes green between polls, empty inside the grace, empty past the grace, forge read error (also mid-wait), plus the re-run after a refusal.
- Mutations by hand on the final tree, each restored and confirmed with `cmp` (nine test files, 893 tests): the wait replaced by a green stub -- 26 failed; the terminal-verdict supervisor call site stripped of `session_alive` / `publish_heartbeat` -- 1 failed. The implementer's ten mutations on the re-derived tree before the patch pass (five landing files, 310 tests): wait removed 34 failed; the heal's `await_checks` call removed 10; the default `sleep` a no-op 1; the after-poll tick removed 4; the between-slice tick removed 1; `on_wait_tick` not passed on 4; supervisor passes no tick 5; supervisor tick forgets the counter 3; supervisor tick skips the publisher heartbeat 2; a heal refusal reported as `MRS-DISP-020` 6.
- A real `check-runs` page for `main` (4 runs) parses through the real `GhForge.check_runs` and classifies green; it is the committed fixture.
- Not run: `pr-preflight` (the full local lane set) and the container, herald-browser and scribe-Postgres lanes -- the diff touches none of the last three; `pr-preflight` is the operator's step before any push.

### Residual risks

- **Partial registration.** A head whose workflows have registered only in part reads green once the registered ones conclude (Design Notes). Closing it needs the PR's expected check set.
- **Two timeouts.** A union heal gives the pushed head its own wait, so one landing can wait up to twice `landing_check_timeout_minutes`.
- **A silent CLI wait.** The CLI harness-done path passes no tick and prints no progress during a wait of up to 45 minutes; it has no run to keep alive.
- **Re-run is a re-dispatch.** The supervisor does not re-land after a journaled refusal; a re-dispatch of the story reaches the CLI landing path, which calls the same function.
- **`filter=latest`.** The adapter relies on GitHub's documented default for same-name reruns (a wrong answer is a false refusal, the safe direction).
- **Heal paths.** The local-`main` advance takes no second wait by design (it merges the head already cleared).
