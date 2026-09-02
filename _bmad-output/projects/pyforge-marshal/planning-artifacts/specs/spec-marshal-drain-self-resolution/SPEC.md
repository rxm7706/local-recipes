---
id: SPEC-marshal-drain-self-resolution
spec: marshal-drain-self-resolution
status: ready
updated: "2026-09-01"
owner-dream: docs/dreams/marshal-dependency-aware-dispatch.md
covers-dreams:
  - docs/dreams/marshal-dependency-aware-dispatch.md   # addendum F (2026-09-01)
  - docs/dreams/marshal-drain-self-resolution.md       # archive pointer only
related:
  - ../spec-22-7-fleet-wide-drain-is-a-marshal-orchestrated-mode.md
  - ../spec-28-13-sanctioned-retry-after-an-operator-initiated-stop.md
  - ../spec-marshal-verify-fail-terminalization/SPEC.md
  - ../spec-marshal-single-story-dispatch/SPEC.md
  - ../spec-marshal-token-economy/SPEC.md
sources:
  - ../../../../../../docs/dreams/marshal-dependency-aware-dispatch.md
surface:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_fleet.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_landing.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_retry.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
assumptions:
  - "28.12–28.17 remain the contracts for Deps: order, SIGTERM taxonomy, surfaces, and verify-fail terminalization."
  - "Campaign pyforge-marshal-20260901T123110026Z-bb6c1de1 is the incident fixture."
open_questions: []
---

# Drain self-resolution (addendum F)

## Why

A `drain_to_zero` that names a refuse and then waits for a chat is not
unattended. 2026-09-01: `MRS-DISP-005` never re-preflighted after a spec
landed; CAP-4 died on a ledger-only conflict and then on GitHub `DIRTY`;
28.13 never left the worktree; `MRS-GATE-001` was a pandas collection hole;
fleet-picture stayed STUCK after the supervisor had already `failed`.

Parent Dream addendum F. Composes FR-193 + CAP-4 land + 28.13 / 28.17.

## Locked v1 decisions (former open questions)

| Question | v1 lock |
|---|---|
| Auto-author a stub story spec? | **No.** Escalate `awaiting-operator` with the missing path. |
| Re-preflight cost | Cheap predicates every tick (spec glob, GitHub mergeable). Expensive `verify_commands` only when predicate-hash changes. |
| Land without `gh pr merge` | **Yes** for this repo when `merge-tree` is clean. |
| Blast radius | Classify in marshal verify (sibling pixi-task narrowing allowed, not required to ship CAP-6). |

## Capabilities

- **CAP-1 — Re-preflight when the refuse predicate can change.**
  Live fleet supervisor re-evaluates a refused backlog head when the refuse
  depends on disk/API state. Identical refuse is rate-limited, not a
  permanent `MRS-DRAIN-005` for the campaign.
  *Success:* After `spec-39-4-*.md` appears, the next eligible tick
  dispatches 39.4 without bare `factory dispatch`.
  *Story:* 28.18

- **CAP-2 — Missing-spec escalates; never idle-with-backlog.**
  `MRS-DISP-005` sets the station `awaiting-operator` (or equivalent
  fleet-picture ATTENTION) with a one-line remedy naming the expected
  `spec-<e>-<n>-*.md` path. Remaining > 0 + idle is a finding.
  *Success:* Fixture: ledger key + epics.md + empty specs glob → escalate,
  not silent idle.
  *Story:* 28.19

- **CAP-3 — Mechanical land-conflict union + local-clean when DIRTY.**
  CAP-4, on conflicts only in `sprint-status-ledger.yaml` (and optionally
  spec `status:` ready/done), unions keys (`done` beats `backlog`),
  commits, pushes, retries. If git is clean and GitHub `mergeable` is
  false, advance `main`, retire the PR, resync ledger (PR #985 path).
  Unknown conflicts escalate with paths named.
  *Success:* Replay #985 → land without chat.
  *Story:* 28.20

- **CAP-4 — Push the dispatch branch before verify can strand it.**
  `origin/dispatch/<slug>/<story>` exists once the session has a
  commitable result. Verify refuse must not be the only thing between
  work and a reachable ref.
  *Success:* After a worktree commit, `git ls-remote` shows the branch
  even if verify later refuses.
  *Story:* 28.21

- **CAP-5 — Verify blast radius (`pre-existing-gate`).**
  A `verify_commands` failure whose failing files/imports are outside
  the story diff and effective surface is WARN, not `MRS-GATE-001`
  story-refuse. Transient redispatch into the same unrelated red
  command is forbidden.
  *Success:* 28.13-shaped diff + packaging pandas collection error → no
  story-refuse; `pyforge-marshal-test` still gates marshal diffs.
  *Story:* 28.22

- **CAP-6 — Terminal overlay + stranded-work signal.**
  `derive_dispatch_phase` is `None` when completion is `failed` /
  `stopped_externally` and the tail is dead (partial: `20e88e8b0f`).
  fleet-picture STUCK only for live refuse. Unpushed dispatch branch
  or open unmerged PR is named in ATTENTION.
  *Success:* Dead+failed → not STUCK; unpushed 28.13-shaped ref → ATTENTION.
  *Story:* 28.23

- **CAP-7 — Supervisor finalizes when the harness cannot run shell.**
  A session that claims done (or leaves a commitable dirty worktree) but
  cannot invoke `git` / `pixi` is not a story refuse. The dispatch
  supervisor commits the leftover, pushes (CAP-4 / 28.21), and runs
  `verify_commands`. Redispatch over `MRS-DISP-036` dirt without that
  attempt is forbidden. If supervisor shell fails, `awaiting-operator`
  names the worktree — not idle, not another Cursor session.
  *Success:* Replay 28.18 pass-41 dirty tree + “shell unavailable” →
  commit + `origin/dispatch/…` without chat; #1000-shaped land.
  *Story:* 28.24

## Constraints

- AD-49 / `MRS-GATE-007` hard scope unchanged.
- Story-caused red CI still blocks land.
- No `scripts/bmad-switch` from drain/land.
- Recoveries run in marshal, not only in an interactive agent.

## Non-goals

- Auto-authored story specs (v2).
- Silent merge of unknown conflicts.
- Replacing 28.13 / 28.17.
- Loop-home ff-merge (archived `loop-home-fleet-refresh`).

## Decomposition

| Capability | Story | Ledger key |
|---|---|---|
| CAP-1 | 28.18 | `28-18-re-preflight-when-the-refuse-predicate-can-change` |
| CAP-2 | 28.19 | `28-19-missing-spec-escalates-never-idle-with-backlog` |
| CAP-3 | 28.20 | `28-20-cap-4-land-heals-mechanical-and-dirty-prs` |
| CAP-4 | 28.21 | `28-21-push-the-dispatch-branch-before-verify-can-strand-it` |
| CAP-5 | 28.22 | `28-22-verify-blast-radius-pre-existing-gate` |
| CAP-6 | 28.23 | `28-23-stranded-work-signal-after-terminal-verify-fail` |
| CAP-7 | 28.24 | `28-24-supervisor-finalizes-when-harness-cannot-run-shell` |

## Success signal

A `drain_to_zero` hitting the 2026-09-01 refuse set reaches
ledger-complete **without** a chat session issuing bare dispatch,
`gh pr merge`, cherry-pick, or a chat commit after “shell unavailable.”
Escalations are named `awaiting-operator` with a preserve/ref — never
idle-with-backlog, never STUCK-on-dead-tail, never dirt-redispatch
without a supervisor finalize attempt.
