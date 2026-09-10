---
title: '`DEFERRED_SPECS` stops reading as a live exemption when it is not one'
type: 'feature'
created: '2026-09-10'
status: 'done'
baseline_revision: '2e49ad54af52cd352a4ae25c1052e69cf1ac6fd4'
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

- 2026-09-10 — Review pass 1: added `test_deferred_specs_story_21_1_reconciliation` to pin de-registrations (`spec-intelligence-hub`, shipped pair) and `spec-pyforge-charter` registration; switched live-status test to public `board._frontmatter`.

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 14 findings — high 0, medium 1, low 2, false 8, maybe-false 1, reject 2
- findings:
  - `[false]` `[reject]` AC lists deleting `spec-agentic-sdlc-autonomy` but diff keeps it — live Spec reads `ready` (open); Boundaries invariant requires removal only for terminal status, so keep is correct.
  - `[false]` `[reject]` `spec-golden-path-conda-blind-spot` should de-register because narrative criteria met — status still `ready`; de-registration awaits operator confirmation per dict precedent, not status alone.
  - `[low]` `[reject]` Unit test only checks open status, not narrative de-registration criteria — out of story scope; open-status guard is the stated deliverable.
  - `[medium]` `[patch]` `spec-intelligence-hub` de-registration not pinned — added `test_deferred_specs_story_21_1_reconciliation` negative membership assertions.
  - `[low]` `[patch]` `spec-pyforge-charter` registration not test-adopted — same test asserts key presence and exact reason string.
  - `[false]` `[defer]` Charter SPEC.md still says unregistered — pre-existing doc drift in steward/governance prose; no chain-completeness consumer.
  - `[false]` `[defer]` Code Map line refs stale (`:716`, `:87-135`) — cosmetic spec doc only.
  - `[false]` `[patch]` Test used `_frontmatter_from_text` instead of `_frontmatter` — switched to public path reader.
  - `[maybe-false]` `[defer]` Glob could return ambiguous slug matches — sorted first match; no duplicate slug paths exist today.
  - `[low]` `[reject]` `read_text` OSError unhandled in test — pytest surfaces read failures; acceptable for monorepo gate.
  - `[false]` `[reject]` Empty triage/changelog at review start — filled during finalize.
  - `[false]` `[defer]` `spec-bmad-cursor-interactive-routing` rationale narrower than Spec — incidental `draft`→`ready` sync; not a defect.
  - `[false]` `[reject]` Blind hunter: story AC not amended for agentic-sdlc keep — intent-contract is read-only; live-status reconciliation supersedes stale audit slug list at implementation time.

## Auto Run Result

Status: done

**Summary:** Reconciled `DEFERRED_SPECS` in `board.py` against live Spec statuses: removed three inert/ready-to-de-register entries (`spec-artifact-chain-reconciliation`, `spec-chain-currency-sweep`, `spec-intelligence-hub`), corrected drifted rationale for `spec-golden-path-conda-blind-spot` and `spec-bmad-cursor-interactive-routing`, registered `spec-pyforge-charter`, rewrote the invariant comment, and added unit tests that read live `SPEC.md` files plus pin Story 21.1 membership changes.

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py` — dict reconciliation and invariant comment
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_board.py` — live open-status invariant + Story 21.1 membership pins
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-21-1-…md` — build-auto metadata

**Review:** 2 patches applied (membership pin test, `_frontmatter` reader); 8 findings rejected as false or out-of-scope; 4 deferred (governance doc drift, ambiguous glob edge, cursor rationale breadth, charter SPEC self-description).

**Follow-up review recommendation:** false (0 high patches; 1 medium patch only)

**Verification:** `pixi run -e pyforge-doctor pyforge-doctor-test` — 1485 passed, 1 skipped (40.76s).

**Residual risks:** `spec-agentic-sdlc-autonomy` retained because live status is `ready` (contradicts static AC slug list from the 2026-09-09 audit snapshot). `spec-golden-path-conda-blind-spot` remains registered while its narrative de-registration criteria appear satisfied — operator-confirmed removal still pending.
