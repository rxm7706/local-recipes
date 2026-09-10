---
id: SPEC-sprint-status-promotion-regression-guard
status: shipped   # added 2026-09-10 (marshal Class-B): the key was absent, which silently
                  # exempted this Spec from chain-completeness; CAP-1 landed in PR #1142
                  # (scripts/promote_sprint_status.py widened done->* regression guard).
companions: []
sources: []
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what to build, test, and validate.

# The sprint-status promotion regression guard catches every drift away from done, not just done->backlog

## Why

`scripts/promote_sprint_status.py` (the `sprint-ledger-sync` pixi task) promotes each BMAD
project's gitignored Tier-3 `implementation-artifacts/sprint-status.yaml` into its tracked
`planning-artifacts/sprint-status-ledger.yaml` twin — the twin CI and the dashboard actually read,
since Tier-3 is invisible to both. It runs fleet-wide across all 8 pyforge stations plus
local-recipes' own dashboard render, and its own pixi task description says to run it "when a
story lands, then commit." Its regression guard exists specifically to keep this promotion
one-directional-safe: a completed story's `done` status must never be silently lost. But the
guard only tests the single transition `done -> backlog`, so `done -> blocked` (or any other
non-done status) passes through undetected. This is a pain to solve: reproduced live 2026-09-10
against pyforge-doctor, where a stale Tier-3 `blocked` value (predating a real landed commit that
correctly flipped the tracked ledger to `done`) silently overwrote the ledger's correct `done`
during a routine promotion — caught only because the operator happened to eyeball the diff before
committing. Every station's landing flow can hit this the same way.

## Capabilities

- **CAP-1**
  - **intent:** An operator promoting Tier-3 status into the tracked ledger can trust that any
    drift away from a tracked `done` — not only `done -> backlog` — is caught before it silently
    overwrites the ledger.
  - **success:** Given a tracked-ledger key whose status is `done` and whose Tier-3 twin holds
    any other status, a plain promotion run refuses and names the key exactly as it already does
    for `done -> backlog`, and `--repair-feed` restores the ledger's `done` into the Tier-3 feed
    exactly as it already does for `done -> backlog`.

## Constraints

- The existing `done -> backlog` behavior (refusal message text, exit behavior, `--repair-feed`
  write-back) stays byte-identical — only the detection condition widens from "feed holds
  `backlog`" to "feed holds anything other than `done`."
- `--allow-regression` still overrides for a genuinely-wrong tracked twin; `--project` scoping is
  unchanged.

## Non-goals

- No change to any OTHER promotion behavior (new-key handling, missing-project handling, the
  fleet-wide default scope, or the `--project` validation).
- No change to `sprint_plan.py generate`'s own separate epics.md-driven regeneration of Tier-3 —
  that is a different sync direction and a different tool.

## Success signal

- Re-running `python scripts/promote_sprint_status.py --project doctor` today (after the operator
  manually restored 20.4's `done` value) reports zero drift; a synthetic case where a tracked
  `done` key's Tier-3 twin is deliberately set to `blocked`, `in-progress`, or `review` is refused
  by a plain run and repaired by `--repair-feed`, matching the existing `done -> backlog` behavior
  in both cases.
