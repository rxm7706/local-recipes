---
id: SPEC-marshal-verify-fail-terminalization
spec: marshal-verify-fail-terminalization
status: ready
updated: "2026-09-01"
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
open_questions:
  - "Retry cap per story per campaign (default unlimited transient) — defer to policy knob."
  - "Apply preserve patch automatically on redispatch vs fresh session reads patch — v1 leaves patch at failed/<story>/changes.patch only."
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

- **CAP-2 — Transient auto-redispatch (fleet drain, compose with hotfix)**
  - **intent:** After CAP-1, `classify_dispatch_block` (existing hotfix) treats
    retriable gates (`MRS-GATE-001`..`006`, etc.) as **TRANSIENT** →
    `story_blocked_reason` returns **None** → next `factory drain --once` tick
    **dispatches the same backlog head again** without bare-`dispatch` workaround.
  - **success:** Integration test or documented cycle: failed+preserve run →
    next fleet cycle launches a new dispatch for the same story key when ledger
    still backlog; no `MRS-DRAIN-005` permanent block for `MRS-GATE-001`.

- **CAP-3 — Observability**
  - **intent:** `marshal status` / completion payload names
    `verify_refusal_terminalized: true` (or equivalent journal field) when CAP-1
    fires; fleet-picture ATTENTION unchanged unless retry cap exceeded (future).
  - **success:** Journal observation entry or completion payload includes failed
    gate code from verify outcome when terminalizing.

## Relationship to 28.13

| Concern | Owner |
|---------|--------|
| SIGTERM / operator stop vs genuine failure | **28.13** |
| Dead session + dirty worktree liveness split (general) | **28.13** |
| Verify refused + dead session + git progress (this incident) | **28.17** CAP-1 |
| Diff surfacing before retry touches worktree | **28.13** (28.17 v1 relies on preserve patch + new run) |

## Explicit non-goals (v1)

- No automatic `git apply` of preserve patch on redispatch
- No retry cap policy knob (unlimited transient retries via drain ticks)
- No change to `judge_dispatch_completion()` global semantics (supervisor override only)

## Decomposition

| Capability | Story | Spec file |
|------------|-------|-----------|
| CAP-1..3 | **28.17** | `spec-28-17-verify-fail-terminalization-and-transient-auto-redispatch.md` |

**Deps:** — (composes with existing `dispatch_retry.py` hotfix; **28.13** remains independent backlog)

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — includes
  `test_dispatch_hotfix.py` CAP-1 pure helpers + regression suite
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`
