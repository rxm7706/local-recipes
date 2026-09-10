---
title: '`DEFERRED_SPECS` stops reading as a live exemption when it is not one'
type: 'feature'
created: '2026-09-10'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `board.py:716`'s guard is `if status not in OPEN_SPEC_STATUSES or slug in
DEFERRED_SPECS: continue` — an entry naming a Spec whose status has already left
`{draft,ready,in-progress}` suppresses nothing (the first half of the `or` already
exempts it), yet it keeps reading as a *live, load-bearing* exemption to every human
and agent who greps the dict. Audited 2026-09-09: **3 of 7** entries are in that
state. Two entries also carry stale content (a wrong open-question list, a
factually-outdated rationale clause), and one constitutive Spec
(`spec-pyforge-charter`) that genuinely needs the exemption is registered nowhere.

**Approach:** Reconcile `DEFERRED_SPECS` against live Spec statuses: delete the two
entries whose Specs are already terminal with no further condition, conditionally
delete a third pending its own status flip, correct the two entries whose content has
drifted from their Specs, register the one missing constitutive entry with a stated
reason, and rewrite the comment above the dict to carry the invariant plus the second
exit condition it currently lacks. Add a unit test asserting every entry's named Spec
resolves to an open status, so the next inert entry fails the suite instead of
silently accumulating.

## Boundaries & Constraints

**Always:**
- Every entry that remains in `DEFERRED_SPECS` must name a Spec whose live `status:`
  is in `OPEN_SPEC_STATUSES` — an entry naming a terminal-status Spec is stale by
  definition and must be removed.
- The comment above the dict states the invariant *and* the second exit condition the
  rule lacks today (a Spec reaching a terminal status exempts it via `:716`'s own
  first clause, so a `DEFERRED_SPECS` entry is never the only thing standing between a
  terminal Spec and a finding).
- Content corrections (the `spec-golden-path-conda-blind-spot` open-question list, the
  `spec-intelligence-hub` rationale clause) are corrected to match what the named
  Spec's own `SPEC.md` says today, not restated from memory.
- The new unit test resolves each entry's Spec status live (reads the tracked
  `SPEC.md`), not against a frozen fixture, so it catches the next inert entry rather
  than only today's three.

**Never:**
- Never leave an entry whose Spec has already gone terminal in the dict "just in
  case" — the guard's own `or` already makes it inert, and an inert-but-present entry
  is exactly the defect this story exists to close.
- Never register `spec-pyforge-charter` (or any entry) without a stated reason in the
  dict comment or docstring — a silent registration is indistinguishable from the
  stale entries this story is removing.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Entry naming an already-terminal Spec, no further condition | `spec-agentic-sdlc-autonomy`, `spec-artifact-chain-reconciliation` in `DEFERRED_SPECS` | Both entries deleted | n/a |
| Entry naming a Spec pending a status flip this same pass | `spec-chain-currency-sweep`, flipping to `shipped` this pass | Deleted **iff** the Spec reads a terminal status at implementation time; otherwise left as-is | n/a |
| Entry with a stale open-question list | `spec-golden-path-conda-blind-spot` entry lists 4 questions, only 2 of which match the Spec's actual 5 (`SPEC.md:13-17`) | List corrected to the Spec's actual five (selector grammar, provisioning, coverage floor, warn-promotability, unscoped-union default); de-registration criterion kept verbatim | n/a |
| Entry with a factually wrong rationale clause | `spec-intelligence-hub` entry's rationale says "only nebari-infrastructure-core is absent" (false since `recipes/nebari-infrastructure-core/recipe.yaml` landed 2026-09-07) | Clause dropped; entry de-registered **iff** the Spec reads `ready` at implementation time | n/a |
| Constitutive Spec with no entry today | `spec-pyforge-charter`, `in-progress`, eight capabilities, zero epics/ledger keys, registered nowhere | Registered with reason "a constitutive Spec whose CAP-1/4/5/6/8 are document-integrity properties no story can pick up" | n/a |
| A future inert entry | Any `DEFERRED_SPECS` entry whose named Spec later reaches a terminal status | New unit test fails the suite | Test failure, not silent |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py` — the `DEFERRED_SPECS` dict (`:87-135`), its exit-rule comment (`:84-86`), and the guard at `:716`.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_board.py` — new/updated test asserting every `DEFERRED_SPECS` entry's named Spec resolves to an open status.

## Tasks & Acceptance

**Execution:**
- `feature` — reconcile `DEFERRED_SPECS`: delete `spec-agentic-sdlc-autonomy` and `spec-artifact-chain-reconciliation`; conditionally delete `spec-chain-currency-sweep`.
- `feature` — correct the `spec-golden-path-conda-blind-spot` open-question list and the `spec-intelligence-hub` rationale clause; conditionally de-register the latter.
- `feature` — register `spec-pyforge-charter` with its stated reason.
- `docs` — rewrite the comment above the dict to carry the invariant plus the second exit condition.
- `feature` — add a unit test that resolves every entry's Spec status live and fails on the next inert entry.

**Acceptance Criteria:**
- Given the guard at `board.py:716`, when an entry names a Spec outside `OPEN_SPEC_STATUSES`, then that entry is deleted rather than left inert (`spec-agentic-sdlc-autonomy`, `spec-artifact-chain-reconciliation` deleted; `spec-chain-currency-sweep` deleted iff its Spec reads terminal at implementation time).
- The `spec-golden-path-conda-blind-spot` entry's open-question list is corrected to the Spec's actual five (selector grammar, provisioning, coverage floor, warn-promotability, unscoped-union default), with its de-registration criterion kept verbatim.
- The `spec-intelligence-hub` entry's rationale drops the "only nebari-infrastructure-core is absent" clause and the entry is de-registered iff that Spec reads `ready` at implementation time.
- `spec-pyforge-charter` is registered with the reason "a constitutive Spec whose CAP-1/4/5/6/8 are document-integrity properties no story can pick up."
- The comment above the dict carries the invariant "every slug in this dict names a Spec whose `status:` is in `OPEN_SPEC_STATUSES`" plus the second exit condition ("or its Spec reaches a terminal status, at which point `:716` exempts it anyway").
- A unit test asserts every entry's named Spec resolves to an open status, so the next inert entry fails the suite instead of accumulating.

## Spec Change Log

## Review Triage Log
