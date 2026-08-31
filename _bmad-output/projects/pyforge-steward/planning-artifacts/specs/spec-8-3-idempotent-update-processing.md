---
title: 'Idempotent update processing (Epic 8 Story 8.3, pyforge-steward)'
type: 'feature'
created: '2026-08-10'
status: done
baseline_revision: '5729fe61e19dfb63f69add6e3c5191417d9bb251'  # this run's actual starting HEAD (a59034fc4e was stale -- predates the contract re-issue merge)
final_revision: '5669eaa64ee245c97e7dc9bee92c25e759446947'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-jira-github-projects-sync/SPEC.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** CAP-3 (idempotent update processing) claims `reconcile()` is idempotent by
construction (AD-9: "redelivery must be a no-op ... out-of-order arrival must not regress
state") — re-processing the same update twice must leave both systems byte-identical to a
single delivery. No test has ever compared full end-state across a duplicate delivery (only
8.2's write-count checks across N *sequential* rounds via the *same* identifier), and no test
has ever redelivered via the *opposite* identifier (an ENTRY-POINT SYMMETRY case). FR-29
requires this be proven by test, never asserted.

> **Intent contract RE-ISSUED 2026-08-11 (operator decision, after this story's own dev pass
> escalated an intent_gap).** The original contract claimed the opposite-identifier redelivery
> "covers AD-9's out-of-order arrival". It does not: AD-9 rule 2 is *stale-value convergence*
> — "a late delivery about a superseded value converges to the current one rather than
> overwriting it" (ARCHITECTURE-SPINE.md AD-9 rule 2). Redelivering via the other identifier
> only proves the two entry points converge on the same reconcile. Both false claims below are
> corrected, and a THIRD test covering AD-9 rule 2 for real is added (operator chose
> "relabel + add the real AD-9 rule 2 test now" over relabel-and-defer). The dev session was
> right to revert rather than patch its own contract.

**Approach:** Add conformance tests that call `reconcile()` twice against a single stateful
`FakeTransport` after seeding exactly one human-made change: once via the same identifier that
made the first call, and once via the opposite identifier. Assert the second call is a true
no-op and that each side's full field state (`github_fields`, `jira_fields`) is dict-equal —
byte-identical — to the state captured immediately after the first call.

## Boundaries & Constraints

**Always:**
- Reuse `reconcile()`, `FakeTransport`, `CONFIG`, and the existing `write_calls()`/
  `_jira_status()` helpers from `test_sync_reconcile_propagation.py` verbatim; no changes to
  `sync.py`'s public surface.
- Snapshot full end-state via `dict(transport.github_fields)` and `dict(transport.jira_fields)`
  immediately after the first (real) delivery, and assert dict equality against that snapshot
  after the redelivery — this directly demonstrates CAP-3's literal "byte-identical" wording,
  not merely a write-count check.
- Also assert `len(transport.write_calls())` is unchanged after the redelivery, as a secondary,
  cheaper-to-read confirmation alongside the state-equality assertion.
- `dry_run` stays `False` for every call in these tests.
- Cover **entry-point symmetry** with a redelivery via the **opposite** identifier from the
  one that made the first call — genuinely new ground: 8.2's round-trips always reused the
  same identifier across every round. (Re-issued 2026-08-11: this is NOT AD-9 rule 2; label
  the test and its banner comment for what it proves.)
- Cover **AD-9 rule 2 — "out-of-order arrival must not regress state"** with its own test and
  its own fixture: a delivery carrying a SUPERSEDED value arrives after the pair has already
  converged on a newer one, and the engine converges to the CURRENT value rather than
  overwriting it — because the payload is never the source of truth and the engine re-reads
  both sides against their baselines (AD-5: nothing branches on a timestamp). Added
  2026-08-11 by operator decision; nothing in the suite proves this invariant today.
- If a test surfaces a genuine local defect in `reconcile()`'s existing logic, fix it in
  `sync.py` in this story.

**Block If:** the tests reveal the AD-5/AD-9/AD-10 mechanism is structurally unable to
guarantee idempotency for some case regardless of local fixes (an architecture-level defect,
the same class of finding that halted 8.1's first pass) — HALT rather than paper over it; do
not re-litigate AD-5/AD-9/AD-10 unilaterally.

**Never:**
- Never mock or patch `reconcile()`'s internals; observe only through `DutyResult` and the
  transport's own state/call log, matching this test file's existing idiom.
- Never claim this story also proves the N-round-trip zero-loop property (CAP-2/Story 8.2,
  already done) — this story's proof is specifically "delivered twice, including via the
  opposite identifier," not "N times via the same identifier."
- Never re-scope into the conflict-path, field-cleared, or first-link N-round-trip coverage
  8.2's Spec Change Log explicitly deferred (`deferred-work.md`) — those remain deferred,
  out of this story's frozen scope.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Identical redelivery, same identifier | GH status differs from its baseline; delivery 1 via `github_item_id` propagates to Jira; delivery 2 repeats the identical `reconcile(github_item_id=...)` call with no intervening change | Delivery 1: `decision=push_to_jira`, both baselines refreshed. Delivery 2: `decision=no_op`, zero new writes, `github_fields`/`jira_fields` byte-identical to the post-delivery-1 snapshot | No error expected |
| Redelivery via the opposite identifier (entry-point symmetry — NOT AD-9 rule 2; re-issued 2026-08-11) | Jira status differs from its baseline; delivery 1 via `jira_issue_key` propagates to GitHub; delivery 2 for the same converged pair arrives via `github_item_id` (the other identifier) | Delivery 1: `decision=push_to_github`, both baselines refreshed. Delivery 2 (opposite identifier): `decision=no_op`, zero new writes, state byte-identical to the post-delivery-1 snapshot | No error expected |
| **AD-9 rule 2 — stale value arrives late (added 2026-08-11)** | The pair has already converged on value B (both baselines refreshed); a delivery about the SUPERSEDED value A then arrives for the same pair | `decision=no_op` against the current state: the engine re-reads both sides, finds neither diverged from its own baseline, and does NOT write A back over B; state byte-identical to the pre-delivery snapshot | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/tests/conformance/test_sync_reconcile_propagation.py` --
  ADD three new test functions for the idempotent-redelivery proof; reuse the existing `CONFIG`
  constant and `FakeTransport`/`write_calls()`/`_jira_status()` helpers already defined in this
  file (do not reinvent them).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py` -- read-only reference;
  touch only if a new test finds a genuine local defect (see Boundaries).

## Tasks & Acceptance

**Execution:**
- [x] `test_sync_reconcile_propagation.py` -- add
  `test_idempotent_redelivery_same_identifier_is_byte_identical` -- delivers a GH-initiated
  change via `github_item_id` twice against the same transport; snapshots
  `dict(transport.github_fields)`/`dict(transport.jira_fields)` after delivery 1 and asserts
  dict equality after delivery 2, plus zero new `write_calls()`.
- [x] `test_sync_reconcile_propagation.py` -- add
  `test_idempotent_redelivery_via_the_opposite_identifier_does_not_regress` -- delivers a
  Jira-initiated change via `jira_issue_key` (propagates to GitHub), then redelivers the same
  converged pair via `github_item_id` (the opposite identifier, entry-point symmetry -- NOT
  AD-9 rule 2); asserts the second delivery is a true no-op with byte-identical state and zero
  new writes.
- [x] `test_sync_reconcile_propagation.py` -- add
  `test_late_delivery_about_a_superseded_value_does_not_regress_state_ad9_rule2` -- AD-9 rule 2
  (added to the intent contract 2026-08-11; omitted from this checklist until this dev pass
  synced it). Genuine intervening state change required: GH moves once (propagates, baselines
  refresh), then GH moves AGAIN to a second new value (propagates again), then a late/
  out-of-order redelivery -- nominally "about" the now-doubly-superseded first value -- must
  converge on the CURRENT value and be a true no-op with byte-identical state and zero new
  writes. See Design Notes for the exact fixture shape.

**Acceptance Criteria:**
- Given one human-made change on either board and no other divergence, when `reconcile()` is
  called twice in a row via the SAME identifier against the same transport, then the second
  call reports `decision == "no_op"`, makes zero new transport writes, and both sides' full
  field state (`github_fields`, `jira_fields`) is byte-identical to the state immediately after
  the first call.
- Given a change already converged by a first delivery via one identifier, when `reconcile()`
  is called again via the OPPOSITE identifier (simulating an out-of-order or duplicate delivery
  arriving through a different channel), then that call also reports `decision == "no_op"`,
  makes zero new writes, and leaves state byte-identical to the post-first-delivery snapshot.
- Given a pair that has converged on one new value and then diverges and converges on a SECOND
  new value (a genuine intervening state change), when `reconcile()` is called again
  representing a late/out-of-order notification nominally about the first (now superseded)
  value, then that call reports `decision == "no_op"`, makes zero new writes, and leaves state
  byte-identical to the post-second-convergence snapshot -- it never regresses toward the
  superseded value (AD-9 rule 2).
- Given the full suite, when `pixi run -e pyforge-steward pyforge-steward-test` runs, then it
  exits 0 including the three new tests, with zero live network calls.

## Spec Change Log

### 2026-08-11 — dev-auto step-03, pre-implementation sync
- The re-issued `<intent-contract>` (frozen 2026-08-11) added AD-9 rule 2 as a THIRD required
  test in `## Boundaries & Constraints` and the `## I/O & Edge-Case Matrix`, but the derived
  `## Tasks & Acceptance` checklist and Acceptance Criteria (outside the frozen block) were
  never updated to match — still listed only two tests. Not an intent-contract ambiguity (the
  narrative is explicit about wanting three tests); a sync gap in the planning content beneath
  it. Added the missing task + acceptance criterion, and a fully worked fixture design in
  `## Design Notes`, before handing off to implementation. No change to the frozen
  `<intent-contract>` itself.

## Review Triage Log

### 2026-08-11 — Review pass 2
- intent_gap: 0
- bad_spec: 0
- patch: 1 (low 1)
- defer: 6 (medium 3, low 3)
- reject: 8 (low 8)
- addressed_findings:
  - `[low]` `[patch]` Added `assert *.details["target_value"] is None` and `assert
    *.details["baseline"] is None` to all three new tests' final no-op assertions.
    `sync.py`'s no-op branch deterministically sets both to `None`; the existing
    byte-identical transport-state check doesn't cover `DutyResult.details`, so a
    caller-facing regression there wouldn't have been caught. Confirmed via
    `sync.py:772-776` and re-ran the full suite (315 passed) after applying.

Deduplicated against each other (Blind Hunter + Edge Case Hunter, run without shared
context): entry-point symmetry (only one direction tested) and no concurrent/overlapping
redelivery coverage were each raised independently by both reviewers and counted once.
Six defer findings appended to `deferred-work.md` (three genuinely new to this story:
entry-point-symmetry-single-direction, no-concurrent-redelivery, AD-9-rule-2-single-hop-only;
three restate gaps already logged in this spec's own pass-1 triage log — AD-4 conflict-path
redelivery, byte-identical proof missing 2 of 4 decision branches, first-link redelivery —
which were never previously appended to the ledger itself). Eight findings rejected: dry_run
redelivery untested (explicitly excluded by the frozen contract — dry_run stays False for
every call), fixture literals not factored into a shared helper with 8.2's tests (matches
this file's own pre-existing, inconsistent precedent; fixing would touch unrelated 8.2 tests),
the AD-9-rule-2 test's premise re-litigated as "not a distinct code path" (already settled by
the operator-authored contract with full awareness reconcile() is payload-less — Boundaries'
"Block If" forbids re-litigating AD-5/AD-9/AD-10 unilaterally), the raw dict-mutation
technique for the intervening change (exactly the frozen Design Notes' specified shape), no
`result.summary` substring assertion (matches the file's existing convention of only
asserting summary text on failure paths, not success/no-op paths), and three subjective
documentation-redundancy/stylistic notes.

### 2026-08-10 — Review pass 1
- intent_gap: 1 (high 1)
- bad_spec: 0
- patch: 4 (low 4)
- defer: 5 (medium 1, low 4)
- reject: 2 (low 2)
- addressed_findings:
  - none

**intent_gap finding (root cause inside `<intent-contract>`):** Blind Hunter found that
`## Boundaries & Constraints`'s "Always" bullet and the `## I/O & Edge-Case Matrix` row
mandating `test_idempotent_redelivery_via_the_opposite_identifier_does_not_regress` mischaracterize
what that test demonstrates. The frozen text claims it "covers AD-9's out-of-order arrival"
property, but `ARCHITECTURE-SPINE.md` (architecture-jira-github-projects-sync-2026-08-09) AD-9
rule 2 states: "a late delivery about a **superseded** value converges to the current one rather
than overwriting it" — this requires an intervening state change between the two `reconcile()`
calls (the tracked value changing again between delivery 1 and delivery 2). The specified test
constructs no such intervening change — both calls observe identical state — so it demonstrates
a real but different property (entry-branch equivalence: redelivery via the *other* identifier
for an already-converged pair is still a no-op), not AD-9 rule 2's stale-value-convergence
guarantee. Independently corroborated by `implementation-readiness-report-20260810.md:16`, which
narrows Story 8.3's scoped deliverable to "**the** double-invocation acceptance test" (singular,
matching CAP-3's literal "identical payload delivered twice" wording and
`spec-8-1-bidirectional-propagation.md:116-120`'s "identical-payload-twice idempotency proof" —
not a second, differently-shaped test). This is a defect in the frozen intent-contract itself
(the claim originates in `## Boundaries & Constraints` and `## I/O & Edge-Case Matrix`, both
inside `<intent-contract>`), not in the implementation, which faithfully built what the contract
specified. Code changes reverted per protocol. Two live open questions for whoever resolves this
gap: (1) should the opposite-identifier test be dropped entirely to match the audit's singular
scoping, or kept as legitimate *additional* coverage under an honest label (entry-branch
equivalence, not AD-9 rule 2)? (2) if AD-9 rule 2's stale-value-convergence property is worth a
dedicated test, it needs a fixture with a genuine intervening state change between deliveries —
distinct from anything specified here.

Lower-severity findings, logged but not acted on (moot per the intent_gap cascade — most would
resurface for triage once the contract is amended and code re-derived):
- `[patch]` `[low]` Design Notes' "cheaper secondary check" framing undersells the write-count
  assertion, which is arguably the more load-bearing check for AD-9 rule 1's redundant-API-call
  concern.
- `[patch]` `[low]` `github_snapshot`/`jira_snapshot` are shallow copies; `jira_fields["status"]`
  is itself a nested dict, so if `FakeTransport` ever mutated it in place instead of replacing it
  wholesale, the snapshot would alias the live object and the equality assertion would pass
  vacuously. Not currently exploitable (today's `FakeTransport._jira` replaces the dict
  wholesale), but a latent fragility worth a `copy.deepcopy` if this idiom is reused.
- `[patch]` `[low]` The new tests collapse to one coarse `write_calls()` count plus whole-dict
  equality, losing the finer-grained `_status_push_calls()`/`_baseline_write_calls()` split the
  immediately preceding tests in the same file use — harder to localize a future failure.
- `[patch]` `[low]` Neither test asserts `second.details["baseline"]`/`["target_value"]`
  (both should be `None`/unchanged on a no-op) — only `decision`.
- `[defer]` `[medium]` No idempotent-redelivery coverage of the real AD-4 conflict path
  (GitHub-wins default and the `field_overrides` Jira-wins variant) — the branch with the most
  decision logic, per both reviewers independently.
- `[defer]` `[low]` No idempotent-redelivery coverage of the first-link (never-synced) scenario.
- `[defer]` `[low]` No idempotent-redelivery coverage of the both-sides-converged-to-the-same-value
  case (partially covered by 8.2's N-round-trip test via write-count only, not via byte-identical
  state or opposite-identifier framing).
- `[defer]` `[low]` No coverage combining an opposite-identifier redelivery with the persistent
  baseline-refresh-failure steady state (8.2's `test_zero_loop_survives_a_baseline_refresh_failure`
  fixture shape).
- `[defer]` `[low]` No coverage of a redelivery that passes both identifiers simultaneously.
- `[reject]` `[low]` "Byte-identical" is dict/string structural equality, not literal
  byte-for-byte comparison — standard idiom inherited verbatim from CAP-3's own SPEC.md wording,
  not a real defect.
- `[reject]` `[low]` Test 1 (same-identifier redelivery) called "thin" relative to existing
  zero-loop coverage — a subjective value judgment; it is in fact the one test the audit's
  scoping names as this story's actual deliverable, and its dict-equality assertion is
  genuinely stronger than any existing check.

## Design Notes

**Byte-identical snapshot idiom** (distinct from 8.2's write-count-only assertions): capture
both sides' full field dicts right after the first delivery, then assert dict equality after
the redelivery, in addition to the write-count check 8.2 established:

```python
transport = FakeTransport(...)  # seed one side's status away from its baseline

first = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)
assert first.details["decision"] == "push_to_jira"
github_snapshot = dict(transport.github_fields)
jira_snapshot = dict(transport.jira_fields)
writes_after_first = len(transport.write_calls())

second = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)  # redelivery
assert second.details["decision"] == "no_op"
assert len(transport.write_calls()) == writes_after_first
assert transport.github_fields == github_snapshot
assert transport.jira_fields == jira_snapshot
```

For the opposite-identifier test, `first` is delivered via one identifier kwarg and `second`
via the other — same snapshot-and-compare pattern, proving idempotency holds regardless of
which side's channel redelivers the notification.

**AD-9 rule 2 fixture (the third test, synced into Tasks & Acceptance during this dev pass —
added to the intent contract 2026-08-11, not present in `test_sync_reconcile_propagation.py`
today).** `reconcile()` takes no delivered-value parameter — it always re-reads current state
against each side's own baseline (AD-5: never a timestamp, never the payload). So "a late
delivery about a superseded value" can only be represented by a GENUINE INTERVENING STATE
CHANGE between two real convergences, followed by a redelivery call that must land on the
CURRENT (second) value, not the first. This is what distinguishes it from the same-identifier
test above, whose second call has zero intervening change:

```python
transport = FakeTransport(
    github_fields={
        "gh_link": "PROJ-1",
        "gh_status": "In Progress",
        "gh_baseline": '{"status": "To Do"}',  # stale -- gh_changed
    },
    jira_fields={
        "status": {"name": "To Do"},
        "jira_link": "ITEM_1",
        "jira_baseline": '{"status": "To Do"}',
    },
    jira_transitions=[
        {"id": "31", "to": {"name": "In Progress"}},
        {"id": "41", "to": {"name": "Blocked"}},
    ],
)

# Delivery 1 (in-order): propagates "In Progress"; both baselines refresh to it.
# This is the value a late, out-of-order notification will (stalely) describe.
first = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)
assert first.details["decision"] == "push_to_jira"

# Genuine intervening state change: GH moves AGAIN, to "Blocked" — a second,
# later real event the earlier notification knows nothing about.
transport.github_fields["gh_status"] = "Blocked"
second = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)
assert second.details["decision"] == "push_to_jira"
github_snapshot = dict(transport.github_fields)
jira_snapshot = dict(transport.jira_fields)
writes_after_second = len(transport.write_calls())

# The late/out-of-order delivery: nominally "about" the now-superseded
# "In Progress" value, but reconcile() never consumes a delivered value —
# it must converge on the CURRENT value ("Blocked"), never regress to it.
late = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)
assert late.details["decision"] == "no_op"
assert len(transport.write_calls()) == writes_after_second
assert transport.github_fields == github_snapshot
assert transport.jira_fields == jira_snapshot
```

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

**Pre-implementation sync (step-03):** the re-issued `<intent-contract>` (frozen 2026-08-11)
added AD-9 rule 2 as a third required test, but the derived `## Tasks & Acceptance` checklist
and Acceptance Criteria still listed only two. Synced the checklist/AC/Code Map/Verification
to match the frozen contract and added a fully worked AD-9-rule-2 fixture to `## Design Notes`
before handing off to implementation (see `## Spec Change Log`).

**Summary of implemented change:** added three conformance tests to
`test_sync_reconcile_propagation.py` proving `reconcile()`'s CAP-3 idempotent-redelivery
claim: (1) identical redelivery via the same identifier is byte-identical, not just
write-count-equal; (2) redelivery via the opposite identifier (entry-point symmetry) is
likewise a true no-op; (3) AD-9 rule 2 — a late/out-of-order redelivery nominally "about" a
now-superseded value converges on the CURRENT value rather than regressing, proven via a
fixture with a genuine intervening state change. No changes to `sync.py`'s public surface;
no architecture-level defect surfaced (the "Block If" condition never triggered).

**Files changed:**
- `src/shared/packages/pyforge-steward/tests/conformance/test_sync_reconcile_propagation.py`
  -- added the three tests above (+161 lines).
- `_bmad-output/implementation-artifacts/spec-8-3-idempotent-update-processing.md` -- this file
  (pre-implementation sync, task/AC checkmarks, review triage log, frontmatter).
- `_bmad-output/implementation-artifacts/deferred-work.md` -- six new deferred-work entries
  from review pass 2 (gitignored Tier-3 runtime artifact, not part of the commit diff review
  cares about, but tracked here for completeness).

**Review findings breakdown (pass 2):** 1 patch applied (added `details["target_value"]`/
`["baseline"]` `is None` assertions to all three new tests' no-op checks, verified against
`sync.py`'s no-op branch and re-run green), 6 deferred to `deferred-work.md` (entry-point
symmetry single-direction, no concurrent/overlapping redelivery coverage, AD-4 conflict-path
redelivery, byte-identical proof missing 2 of 4 decision branches, first-link redelivery,
AD-9-rule-2 single-hop-only -- three restate pass-1 findings never previously appended to the
ledger), 8 rejected (dry_run exclusion is contract-mandated, fixture duplication matches this
file's own precedent, re-litigating the AD-9-rule-2 test's premise is forbidden by the frozen
contract's Boundaries, the raw-mutation technique matches the frozen Design Notes exactly,
missing `result.summary` assertions matches the file's success-path convention, and three
subjective documentation-redundancy notes).

**Verification performed:** `pixi run -e pyforge-steward pyforge-steward-test` -- 315 passed
(0 failed), zero live network calls, re-run clean after the pass-2 patch. `pixi run -e
pyforge-steward pyforge-steward-dogfood` -- `steward --version` and `steward keys audit
--drift` both succeed, drift clean. `git status`/`git diff --stat` confirm only the one test
file was modified (`sync.py` untouched, matching the Boundaries' "no changes to `sync.py`'s
public surface" default).

**Residual risks:** none blocking. The six deferred findings are all coverage gaps (untested
scenarios), not known defects -- `reconcile()`'s existing decision logic was traced by hand
against each new test and confirmed correct before assertions were written. The most
consequential deferred item is the AD-4 conflict-path redelivery gap (medium severity,
explicitly out of this story's frozen scope per its own Boundaries) -- a future story should
pick this up alongside the other AD-4 N-round-trip gap already on the ledger from Story 8.2.

