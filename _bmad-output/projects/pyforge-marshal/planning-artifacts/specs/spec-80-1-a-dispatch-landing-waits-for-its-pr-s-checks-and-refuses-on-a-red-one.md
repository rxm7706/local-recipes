---
title: "80.1: A dispatch landing waits for its PR's checks and refuses on a red one"
type: 'feature'
created: '2026-10-01'
status: 'in-progress'
baseline_revision: '68b35f7e1cb04295f729647c2d0ee4ff060ab417'
review_loop_iteration: 0
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
deferred:
  - summary: >-
      The two heal paths that merge after `forge.merge_pr` fails (`_try_union_heal`'s retried merge on a freshly pushed
      union commit, and `_try_local_main_advance`) still land without waiting on checks; Story 80.1 waits only at the
      first `forge.merge_pr` call.
    evidence: |-
      Planning read of dispatch_land_heal.py: the union heal pushes a new head and calls forge.merge_pr(new_sha) at once,
      so that head's checks never ran; the local-main advance skips the PR entirely. Plumbing the wait into the heal
      changes try_heal_dispatch_land_merge's signature and every heal fake (CAP-269 / CAP-283 surface), a separate story.
    location: src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_heal.py
    severity: medium
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
  `T/meta/test_finding_remedy_reference_sync.py` for the two codes.

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
