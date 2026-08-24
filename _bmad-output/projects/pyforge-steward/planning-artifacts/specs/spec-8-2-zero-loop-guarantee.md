---
title: 'Zero-loop guarantee (Epic 8 Story 8.2, pyforge-steward)'
type: 'feature'
created: '2026-08-10'
status: done
baseline_revision: 'd409cdca9c23511a4c9a10cbcfc120760e10ec6b'
final_revision: 'cf7edf793b8a74eb6117c6f33973ac6d157c2a48'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-jira-github-projects-sync/SPEC.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** CAP-2 (zero-loop guarantee) claims the AD-5/AD-10 value-baseline mechanism 8.1
implemented prevents a synced update from ever echoing back — "holds by construction" — but no
test has ever called `reconcile()` more than once against the same stateful transport. The claim
is undemonstrated, and FR-28 requires it be proven by test, never asserted.

**Approach:** Add conformance tests that call `reconcile()` N (>=5) times in a row against a
single, stateful `FakeTransport` after seeding exactly one human-made change, and assert only the
first call propagates while every later call is a true no-op with zero new transport calls — for
both directions (GitHub-initiated, Jira-initiated) and the both-sides-converge-to-the-same-value
case.

## Boundaries & Constraints

**Always:**
- Reuse `reconcile()`, `FakeTransport`, and `CONFIG` from
  `test_sync_reconcile_propagation.py` verbatim; no changes to `sync.py`'s public surface.
- Every round-trip test drives the SAME `FakeTransport` instance across all N calls — a fresh
  transport per call proves nothing about echoing.
- Assert "no new writes" via a snapshot of `len(transport.calls)` taken between rounds, not by
  resetting the log (the log accumulates across the whole test by design).
- `dry_run` stays `False` for every round in these tests — `dry_run=True` reports a decision
  without persisting state, which breaks the stateful-convergence premise being proven.
- If a round-trip test surfaces a genuine local defect in `reconcile()`'s existing AD-5/AD-10
  logic (not an architecture-level gap), fix it in `sync.py` in this story — this is proof work
  over an already-final, already-implemented mechanism, not new design.

**Block If:** the tests reveal the AD-5/AD-10 baseline mechanism is structurally unable to
guarantee zero-loop for some case regardless of local fixes (an architecture-level defect, the
same class of finding that halted 8.1 the first time) — HALT rather than paper over it; do not
re-litigate AD-5/AD-10 unilaterally.

**Never:**
- Never mock or patch `reconcile()`'s internals to fake the property — observe it only through
  `DutyResult` and the transport's own call log, matching this test file's existing idiom.
- Never claim this story also proves idempotency (CAP-3/Story 8.3) or fail-loud semantics
  (CAP-4/Story 8.4) — out of scope here.
- Never reduce N below 5, and never treat "round 2 was a no-op" alone as sufficient — the property
  is that EVERY round from 2..N is a no-op, not just the next one.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| GitHub-initiated, N round trips | GH status differs from its baseline; Jira matches its own baseline; `reconcile()` called 5x against the same transport | Round 1: `decision=push_to_jira`, Jira updated, both baselines refreshed. Rounds 2-5: `decision=no_op`, zero new transport calls each round | No error expected |
| Jira-initiated, N round trips | Jira status differs from its baseline; GH matches its own baseline; `reconcile()` called 5x | Round 1: `decision=push_to_github`, GH updated, both baselines refreshed. Rounds 2-5: `decision=no_op`, zero new calls | No error expected |
| Both sides independently converge to the same value, N round trips | both sides differ from their own baseline but already equal each other; `reconcile()` called 5x | Round 1: decision downgraded to `no_op` (convergence check) but both baselines still refreshed (were stale); Rounds 2-5: true no-op, zero new calls | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/tests/conformance/test_sync_reconcile_propagation.py` --
  ADD three new test functions for the N-round-trip zero-loop proof; reuse the existing `CONFIG`
  constant and `FakeTransport`/`write_calls()`/`_status_push_calls()`/`_baseline_write_calls()`
  helpers already defined in this file (do not reinvent them).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py` -- read-only reference;
  touch only if a new test finds a genuine local defect (see Boundaries).

## Tasks & Acceptance

**Execution:**
- [x] `test_sync_reconcile_propagation.py` -- add
  `test_zero_loop_github_initiated_n_round_trips` -- calls `reconcile()` 5x with a GH-side
  change seeded and asserts round 1 propagates, rounds 2-5 are zero-write no-ops.
- [x] `test_sync_reconcile_propagation.py` -- add
  `test_zero_loop_jira_initiated_n_round_trips` -- same shape, Jira-side change seeded.
- [x] `test_sync_reconcile_propagation.py` -- add
  `test_zero_loop_convergent_same_value_n_round_trips` -- both sides pre-diverged to the
  identical new value; asserts round 1 has zero API writes but refreshes both baselines, rounds
  2-5 are true no-ops with zero new calls.
- [x] `test_sync_reconcile_propagation.py` -- add
  `test_zero_loop_survives_a_baseline_refresh_failure` -- covers the non-atomic
  baseline-refresh failure path (`sync.py:869-880`), required by the audit's dispatch note
  (`epics.md:664-665`, `implementation-readiness-report-20260810.md:15`). Reuse the existing
  `test_baseline_exceeding_the_field_size_ceiling_is_a_named_failure_after_the_value_push`
  fixture shape (a status value over Jira's 255-char baseline-field ceiling
  `_JIRA_BASELINE_FIELD_CEILING`) driven through 3 `reconcile()` ticks against the SAME
  transport, using the same `write_calls()`-snapshot-between-rounds pattern as the other three
  tests in this list. Tick 1: `ok is False`, `"Mode B"` in summary (the value push already
  succeeded; the baseline refresh failed before either baseline field was written -- matches the
  existing single-tick test). Ticks 2-3: each must independently assert `ok is False` again (the
  convergence check makes the value push a no-op on these ticks, since both sides already hold
  the pushed value, but the baseline refresh is retried and fails again for the same reason) and
  `len(transport.write_calls())` unchanged from its value after tick 1 -- proving the
  persistent-failure steady state never re-pushes the tracked value even though it never
  self-heals.

**Acceptance Criteria:**
- Given one human-made change on either board and no other divergence, when `reconcile()` runs 5
  times in a row against the same transport, then exactly the first call propagates and every
  call from 2 through 5 reports `decision == "no_op"` with zero new transport calls — for both
  directions.
- Given both sides independently changed to the identical new value, when `reconcile()` runs 5
  times in a row, then the first call makes zero API writes (already converged) while still
  refreshing both stale baselines, and every call from 2 through 5 is a true no-op with zero new
  calls.
- Given a baseline-refresh failure after a successful value push (an oversized baseline value
  over Jira's 255-char ceiling), when `reconcile()` runs 3 times in a row against the same
  transport, then every tick reports `ok is False` and `write_calls()` grows only on tick 1 (the
  original value push) -- zero new writes on ticks 2 and 3 -- proving this persistent-failure
  steady state never re-propagates the pushed value, even though it does not self-heal without
  operator/Mode-B intervention.
- Given the full suite, when `pixi run -e pyforge-steward pyforge-steward-test` runs, then it
  exits 0 including the four new tests, with zero live network calls.

## Design Notes

**Round-trip test skeleton** (the one non-obvious idiom — snapshot the call-log length between
rounds rather than resetting it). **Corrected in review pass 1:** snapshot
`len(transport.write_calls())`, not raw `len(transport.calls)` — `reconcile()` re-reads both
sides on every call by design (AD-9: "a webhook or schedule tick is only ever a wake-up, never a
value source"), so a genuinely no-op round still makes two fresh READ calls and raw
`transport.calls` necessarily grows every round even when the round is a true no-op. The
property this story exists to prove is zero new *writes*, which `write_calls()` (already defined
in the test file) captures directly:

```python
transport = FakeTransport()  # seed one side's status away from its baseline
transport.github_fields["gh_status"] = "Done"  # baseline still "Todo" -> gh_changed

first = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)
assert first.details["decision"] == "push_to_jira"
writes_after_first = len(transport.write_calls())

for _ in range(4):  # rounds 2-5
    result = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)
    assert result.details["decision"] == "no_op"
    assert len(transport.write_calls()) == writes_after_first  # zero new writes this round
```

**Baseline-refresh-failure round trip (added review pass 1, per audit dispatch note
`epics.md:664-665`):** unlike the other three round-trip tests, tick 1 here already fails
(`ok is False`) — there is no successful round 1 to snapshot after, so snapshot
`len(transport.write_calls())` after tick 1 (not before), same pattern as the other three tests,
then assert it stays unchanged across ticks 2-3. The audit's dispatch note guessed "next tick
re-propagates"; that is not what the landed code does — once the value already matches on both
sides (from tick 1's already-completed push), the convergence check (`sync.py:806-808`)
downgrades every later tick's decision to `no_op` before the baseline-refresh block fails again,
so the zero-loop property (no repeat writes) holds even in this persistent-failure mode.

## Verification

**Commands:**
- `pixi run -e pyforge-steward pyforge-steward-test` -- expected: all tests pass including the
  four new zero-loop round-trip tests, exit 0, zero live network calls.
- `pixi run -e pyforge-steward pyforge-steward-dogfood` -- expected: unaffected (`steward
  --version && steward keys audit --drift` still succeeds).

## Review Triage Log

### 2026-08-10 — Review pass 1
- intent_gap: 0
- bad_spec: 1 (high 1)
- patch: 1 (low 1)
- defer: 4 (medium 1, low 3)
- reject: 5 (low 5)
- addressed_findings:
  - `[high]` `[bad_spec]` Tasks & Acceptance omitted a test for the non-atomic
    baseline-refresh-failure path (`sync.py:869-880`), explicitly required by the audit's
    dispatch note (`epics.md:664-665`, `implementation-readiness-report-20260810.md:15`).
    Amended Tasks & Acceptance / Acceptance Criteria / Design Notes to add
    `test_zero_loop_survives_a_baseline_refresh_failure`; looped back to step-03 to re-derive.

### 2026-08-10 — Review pass 2
- intent_gap: 0
- bad_spec: 0
- patch: 1 (low 1)
- defer: 2 (medium 1, low 1)
- reject: 9 (low 9)
- addressed_findings:
  - `[low]` `[patch]` Shared comment block's "assert only the first call propagates" was
    imprecise for `test_zero_loop_convergent_same_value_n_round_trips` (round 1 there is itself
    already a no-op, nothing to propagate). Reworded the block comment to state this explicitly;
    re-ran the full suite (312 passed) to confirm no regression.

## Spec Change Log

### 2026-08-10 — Amendment 1 (review pass 1, bad_spec)

**Triggering finding:** Blind Hunter review flagged that this story's frozen Tasks & Acceptance
covered only the three happy-path N-round-trip scenarios (GH-initiated, Jira-initiated,
convergent-same-value) and omitted the non-atomic baseline-refresh failure path
(`sync.py:869-880`) — a test explicitly required by the audit's dispatch note
(`epics.md:664-665`: "8.2's test must also cover the non-atomic baseline-refresh failure path";
`implementation-readiness-report-20260810.md:15`: "the test must also cover the non-atomic
baseline-refresh failure... a happy-path-only N-cycle test proves less than the AC claims").
Hand-tracing the existing
`test_baseline_exceeding_the_field_size_ceiling_is_a_named_failure_after_the_value_push` fixture
through a second `reconcile()` tick (independently re-verified against `sync.py:762-887`)
confirmed the actual behavior: after tick 1 pushes the value but fails to refresh either
baseline, tick 2+ never re-push (the convergence check catches that both sides already hold the
pushed value) but DO retry and fail the baseline refresh again every time, returning
`ok=False` forever with zero new tracked-field writes — a persistent-failure steady state, not
the "next tick re-propagates" recovery the audit note guessed at. This is the accepted
non-atomicity the code's own comment at `sync.py:876-880` already documents; it does not violate
the zero-loop guarantee (no runaway writes), but was never demonstrated by test.

**What was amended:** Added a fourth item to `## Tasks & Acceptance` § Execution and a matching
Acceptance Criterion, requiring a round-trip test over this failure path. Added a Design Notes
paragraph describing the exact fixture and multi-tick assertions needed, and corrected the
existing round-trip skeleton to snapshot `len(transport.write_calls())` rather than raw
`len(transport.calls)` (`reconcile()` re-reads both sides every call by design — AD-9 — so raw
call count grows every round even in a true no-op; only the write count is flat). No change to
`<intent-contract>`.

**Known-bad state avoided:** Shipping this story's demonstration test suite as done while
missing the one path the project's own most recent audit explicitly named as required — which
would have left the persistent-failure steady state (`ok=False` forever after a
baseline-refresh failure, needing Mode-B/operator intervention to recover) proven only by ad hoc
hand-tracing during review, never by a regression test.

**Known-real findings deferred (not this story's frozen scope — the intent-contract's Approach
explicitly scopes to "exactly one human-made change"; these all involve two independent changes
or additional entry-point variations):**
- `_bmad-output/implementation-artifacts/deferred-work.md` — N-round-trip zero-loop coverage for
  the real AD-4 conflict path (both sides differ from baseline to genuinely different values),
  both the GitHub-wins default and the `field_overrides` Jira-wins variant.
- `_bmad-output/implementation-artifacts/deferred-work.md` — N-round-trip zero-loop coverage
  re-entering `reconcile()` via the opposite identifier (or both identifiers) between rounds,
  not just the identifier used in round 1.
- `_bmad-output/implementation-artifacts/deferred-work.md` — N-round-trip zero-loop coverage for
  the field-cleared-push scenario (`target_value=None`).
- `_bmad-output/implementation-artifacts/deferred-work.md` — N-round-trip zero-loop coverage for
  the first-link (never-synced) scenario.

**KEEP instructions (must survive re-derivation):**
- Keep all three already-implemented tests verbatim: `test_zero_loop_github_initiated_n_round_trips`,
  `test_zero_loop_jira_initiated_n_round_trips`, `test_zero_loop_convergent_same_value_n_round_trips`.
  They passed, are individually correct against the I/O & Edge-Case Matrix, and were not the
  subject of this finding.
- Keep the `len(transport.write_calls())`-based snapshot-between-rounds assertion pattern (not
  raw `len(transport.calls)`) for the same reason recorded above — now reflected directly in the
  Design Notes skeleton, so this is no longer a documented deviation from this section.
  This does deviate from the literal `len(transport.calls)` wording of the frozen
  `<intent-contract>`'s "Always" bullet; that wording could not be honored literally without
  making every round-2+ assertion fail even in the correct, zero-loop case (confirmed
  independently by reading `sync.py:684-697`'s unconditional per-call reads). The intent-contract
  itself is frozen and was not amended; this is recorded here as the resolution rationale for
  the apparent conflict.
- Keep the per-round loop asserting rounds 2 through 5 (or 2-3, for the new failure-path test)
  individually, not just round 2, per the intent-contract's own "never treat 'round 2 was a
  no-op' alone as sufficient."

## Auto Run Result

**Summary.** Added four conformance tests to `test_sync_reconcile_propagation.py` proving
`reconcile()`'s zero-loop guarantee (CAP-2/FR-28) by calling it repeatedly against a single
stateful `FakeTransport`: GitHub-initiated and Jira-initiated single-change round trips (5
calls each), a both-sides-converge-to-the-same-value round trip (5 calls), and — added via a
review-pass-1 spec amendment — a non-atomic baseline-refresh-failure round trip (3 ticks) that
the project's own 2026-08-10 audit dispatch note explicitly required and the frozen spec had
omitted. All four assert every round/tick from 2..N individually, snapshotting
`len(transport.write_calls())` between rounds rather than raw `len(transport.calls)` (the latter
necessarily grows every round because `reconcile()` re-reads both sides on every call by design,
AD-9) — a deviation from the frozen intent-contract's literal "Always" bullet, disclosed and
justified in the Spec Change Log's KEEP instructions rather than applied silently.

**Files changed:**
- `src/shared/packages/pyforge-steward/tests/conformance/test_sync_reconcile_propagation.py` —
  +164 lines: four new test functions plus a section-banner comment block (reworded once in
  review pass 2 for accuracy). No other file in the tracked repo changed;
  `sync.py` was read-only reference throughout — no local defect was found in either
  implementation pass.

**Review findings breakdown (2 passes, Blind Hunter + Edge Case Hunter each, no shared context):**
- Pass 1: 1 `bad_spec` (high) — frozen Tasks & Acceptance omitted the audit-required
  baseline-refresh-failure test; spec amended (Tasks & Acceptance, Acceptance Criteria, Design
  Notes), code reverted and re-derived. 1 `patch` (low, moot — duplication across tests, not
  applied since code was re-derived). 4 `defer` (1 medium, 3 low — conflict-path round-trip
  coverage incl. `field_overrides`, alternating-identifier coverage, field-cleared-push
  coverage, first-link coverage — all out of this story's frozen "exactly one human-made
  change" scope). 5 `reject` (low noise / findings contradicted by the frozen contract).
- Pass 2 (post re-derivation): 0 `intent_gap`, 0 `bad_spec`. 1 `patch` (low) — applied: reworded
  the shared comment block's "only the first call propagates" claim, imprecise for the
  convergent-same-value test where round 1 is itself already a no-op. 2 `defer` (1 medium, 1
  low — a GH-side mirror of the baseline-refresh-failure direction; a pre-existing,
  incidentally-surfaced gap where no test anywhere exercises a first-link item with an unset
  CURRENT status value, the `_MISSING`-vs-`None` distinction AD-10 exists to protect). 9
  `reject` (low noise, largely re-litigating constraints the frozen intent-contract already
  settles explicitly — N>=5, `dry_run=False`, snapshot-and-compare idiom).
- Total: 6 items appended to `deferred-work.md` across both passes (all `[low]`/`[medium]`,
  none blocking); 0 items remain in a `patch`-pending state.

**Follow-up review recommendation: false.** The one substantive (high-severity) finding from
pass 1 already drove a full spec amendment + code re-derivation + an independent second
adversarial+edge-case review pass, which found nothing beyond a single cosmetic wording fix in
the amended code. A third review pass would be re-litigating ground pass 2 already covered.

**Verification performed:**
- `pixi run -e pyforge-steward pyforge-steward-test` — 312 passed, exit 0, zero live network
  calls (re-run independently by this session after each implementation pass and after the
  pass-2 comment-wording patch).
- `pixi run -e pyforge-steward pyforge-steward-dogfood` — `steward --version` and `steward keys
  audit --drift` both clean, re-run independently after the first implementation pass.
- Manual inspection: read the full diff both passes; independently traced `reconcile()`'s
  decision logic (`sync.py:713-894`) by hand to verify the bad_spec finding's premise (the
  persistent-failure steady state) before amending the spec, rather than trusting the review
  agent's claim alone.

**Residual risks:** the 6 deferred items describe real, out-of-frozen-scope coverage gaps in
the zero-loop property for the true two-sided-conflict path, the `field_overrides` override
path, alternating-identifier re-entry, the field-cleared-push scenario, a GH-side mirror of the
baseline-refresh-failure test, and the `_MISSING`-vs-`None` first-link edge case — none
contradicts CAP-2's guarantee as demonstrated for the three named scenarios plus the
audit-required failure path, but a future story or respec should absorb them (per this repo's
own established pattern for prior stories' deferred findings) rather than let them accumulate
unowned.
