---
id: SPEC-marshal-verify-fail-terminalization
spec: marshal-verify-fail-terminalization
status: shipped
updated: "2026-09-09"
owner-dream: docs/dreams/marshal-dependency-aware-dispatch.md
covers-dreams:
  - docs/dreams/marshal-dependency-aware-dispatch.md   # addendum E (2026-09-01)
related:
  - ../spec-28-13-sanctioned-retry-after-an-operator-initiated-stop.md
  - ../spec-marshal-token-economy/SPEC.md
  - ../spec-marshal-parallel-dispatch-fanout/SPEC.md
sources:
  - ../../../../../../docs/dreams/marshal-dependency-aware-dispatch.md
surface:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_supervisor_state.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_retry.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
open_questions: []
  # ANSWERED 2026-09-09, both retired (operator, fleet-readiness batch rows mars-B-B7 / mars-B-B8):
  # oq1 retry cap -> 3 PER STORY PER CAMPAIGN, policy-declared, default 3 -- NOT unlimited.
  #   Unlimited transient retry is how a red repo-global gate becomes an infinite drain: the
  #   MRS-GATE-001 pandas incident (drain-self-resolution addendum F) was a repo-global gate
  #   28.17 would have re-hit every tick, and CAP-5's pre-existing-gate WARN narrows but does
  #   not bound it. Rejected: keep unlimited -- defensible only once pre-existing-gate
  #   classification is proven over a full campaign. Supersedes the v1 non-goal below.
  # oq2 auto-apply the preserve patch -> KEEP v1. The patch is left at
  #   `failed/<story>/changes.patch` and is NEVER auto-applied on redispatch. Fleet-wide
  #   standing policy is non-destructive preserve-then-restore, operator-driven; the 647-line
  #   uncommitted 28.2 diff is the motivating loss. Rejected: auto-apply -- it silently
  #   re-bases a diff the operator has not reviewed.
---

> **Canonical contract.** Story **28.17** (sibling to **28.13**, not a replacement).
> **28.13** owns SIGTERM/stopped taxonomy and liveness split; this spec owns
> **verify-fail + dead session** terminalization so overnight drains advance.

# Verify-fail terminalization and transient auto-redispatch

## Why

**2026-09-01 atlas 23.1:** build finished, session died, verify refused
(`MRS-GATE-001` / `kedro-test`), git-fact WIP remained. Story **22.2**
`judge_dispatch_completion()` correctly returned **`LIVE`** (dead process +
progress). The dispatch supervisor **heartbeated forever** — preserve ran only
on **`FAILED` exit**, which never happened. The atlas `--stories` chain froze;
the operator had to manual preserve, kill supervisor, reset worktree, bare
redispatch.

Overnight autonomy requires **every non-success path to reach a terminal journal
state** so the fleet campaign supervisor's next `--once` cycle can advance.

## Capabilities

- **CAP-1 — Verify-refusal terminalization (supervisor)**
  - **intent:** When `session_alive == false`, independent verify outcome is
    `refused`, and git shows progress beyond baseline, the dispatch supervisor
    **stops heartbeating as LIVE**: journals `dispatch-completion` → **`failed`**,
    runs **`dispatch-preserve`** (`failed/<story>/changes.patch`), exits.
  - **success:** Fixture: dead session + journaled verify refuse + WIP commit →
    supervisor exits within one tick; preserve ref exists; completion verdict
    `failed`. Live session + verify refuse → still **LIVE** (agent may recover).
  - **verified:** 2026-09-11 — mechanical re-verification (operator-directed capability-effect sweep): `core.dispatch_supervisor_state.should_terminalize_verify_refusal` gates on dead session + refused verdict + git progress; `dispatch_supervisor/__main__.py:1064` sets `verdict = FAILED` when it fires, which triggers `dispatch-completion: failed` and (`:1263`) `_journal_dispatch_preserve` when git progress exists. `test_terminalize_verify_refusal_when_dead_session_and_refused` plus the four sibling non-firing-case tests in `test_dispatch_hotfix.py`, and `test_terminalize_verify_refusal_unchanged` in `test_dispatch_supervisor_state.py`, all pass.

- **CAP-2 — Transient auto-redispatch (fleet drain, compose with hotfix)**
  - **intent:** After CAP-1, `classify_dispatch_block` (existing hotfix) treats
    retriable gates (`MRS-GATE-001`..`006`, etc.) as **TRANSIENT** →
    `story_blocked_reason` returns **None** → next `factory drain --once` tick
    **dispatches the same backlog head again** without bare-`dispatch` workaround.
  - **success:** Integration test or documented cycle: failed+preserve run →
    next fleet cycle launches a new dispatch for the same story key when ledger
    still backlog; no `MRS-DRAIN-005` permanent block for `MRS-GATE-001`.
  - **verified:** 2026-09-11 — mechanical re-verification (operator-directed capability-effect sweep), PARTIAL: `core.dispatch_retry.classify_dispatch_block` classifies `MRS-GATE-001`..`006`/`010`/`011`/`015` as `TRANSIENT` (`test_transient_block_on_verify_gate` passes), and `cli/dispatch.py:1407-1408`'s `station_story_block_facts` returns `None` (no block evidence, so no `MRS-DRAIN-005`) whenever `block_kind is TRANSIENT` — the literal success criterion holds. **The Constraints section's separate "3 redispatches per story per campaign, policy-declared, default 3" cap is NOT implemented** — a repo-wide grep for any per-story/per-campaign retry counter or policy field (`transient_retry`, `retry_cap`, `max_transient`, `per_story_per_campaign`) finds nothing in `src/shared/packages/pyforge-marshal/`; transient retries are currently unbounded, unlike the 2026-09-09 Assumptions/Constraints text claims. Flagged as a real gap, not fixed here (a persisted per-story-per-campaign counter is a real design decision, not a mechanical fix within this sweep's scope).

- **CAP-3 — Observability**
  - **intent:** `marshal status` / completion payload names
    `verify_refusal_terminalized: true` (or equivalent journal field) when CAP-1
    fires; fleet-picture ATTENTION unchanged unless retry cap exceeded (future).
  - **success:** Journal observation entry or completion payload includes failed
    gate code from verify outcome when terminalizing.
  - **verified:** 2026-09-11 — mechanical re-verification (operator-directed capability-effect sweep): no literal `verify_refusal_terminalized` field exists, but the equivalent the SPEC's own intent hedges for is live — every `dispatch-verification` OUTCOME journal entry carries `failed_gate`/`failed_message` (`dispatch_supervisor/__main__.py:844,859`), surfaced to `marshal status` as `dispatch_verification_failed_gate` (`core/status.py:1015,1220-1222`; `cli/status.py:903`) — observed live earlier this session in a real `marshal status --format json` run. `test_story_with_gate_verdict_is_named`, `test_story_without_gate_verdict_is_null_not_fabricated`, and `test_full_run_detail_reports_stories_gate_verdicts_budget_and_open_intent` pass.

## Relationship to 28.13

| Concern | Owner |
|---------|--------|
| SIGTERM / operator stop vs genuine failure | **28.13** |
| Dead session + dirty worktree liveness split (general) | **28.13** |
| Verify refused + dead session + git progress (this incident) | **28.17** CAP-1 |
| Diff surfacing before retry touches worktree | **28.13** (28.17 v1 relies on preserve patch + new run) |

## Explicit non-goals (v1)

- No automatic `git apply` of preserve patch on redispatch — **re-affirmed 2026-09-09** as
  standing policy, not a v1 shortcut: the preserve patch is operator-restored, never
  auto-rebased.
- ~~No retry cap policy knob (unlimited transient retries via drain ticks)~~ **SUPERSEDED
  2026-09-09:** the transient-retry cap is **3 per story per campaign, policy-declared,
  default 3**. See the Constraint below.
- No change to `judge_dispatch_completion()` global semantics (supervisor override only)

## Constraints (2026-09-09)

- **Transient retry is bounded:** at most **3 redispatches per story per campaign**,
  policy-declared with default 3. An unbounded transient retry turns a red repo-global gate into
  an infinite drain (the `MRS-GATE-001` pandas incident); CAP-5's pre-existing-gate WARN narrows
  the blast radius but does not bound the count.
- **The preserve patch is never auto-applied.** A terminalized story leaves
  `failed/<story>/changes.patch` for an operator-driven restore; no redispatch path rebases it
  silently.

## Decomposition

| Capability | Story | Spec file |
|------------|-------|-----------|
| CAP-1..3 | **28.17** | `spec-28-17-verify-fail-terminalization-and-transient-auto-redispatch.md` |

**Deps:** — (composes with existing `dispatch_retry.py` hotfix; **28.13** remains independent backlog)

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — includes
  `test_dispatch_hotfix.py` CAP-1 pure helpers + regression suite
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`
