---
project: pyforge-marshal
date: '2026-08-31'
trigger: docs/dreams/marshal-dependency-aware-dispatch.md
status: proposed
---

# Sprint Change Proposal — Dependency-Aware Dispatch fold-in to Epic 28

## 1. Issue Summary

**Trigger.** This session, sequencing `pyforge-atlas`'s 18-story backlog required
hand-deriving a topological order from `epics.md`'s `Deps:` lines by hand, because
`marshal factory drain --mode drain_to_zero` (no `--stories`) walks the tracked
`sprint-status-ledger.yaml` in raw ledger order, which has no relationship to the
dependency graph. It got the first story right by luck of ledger order, not by
design — and the derived order surfaced a real cross-epic dependency
(`23.9` → `22.1`) raw ledger order has no way to know about.

**Compounding finding.** Restarting `pyforge-atlas` with the hand-derived explicit
order via `marshal factory dispatch pyforge-atlas --stories ...` was refused:
`MRS-DRAIN-005` — the prior SIGTERM-killed run of `21.7` (an operator-initiated
stop, not a story failure) was journaled as `'failed' by git and process facts`
and is "never auto-retried, never forced past." The only way back in was a bare
`marshal factory dispatch pyforge-atlas 21.7` (no `--stories`), which happens to
skip `drain`'s journal check entirely rather than offering a sanctioned retry.

**Evidence of stakes.** The same session killed `pyforge-marshal`'s own `28.2`
dispatch minutes later. `21.7`'s worktree held 3 lines of bookkeeping (cheap to
discard). `28.2`'s worktree held **647 uncommitted lines across 11 files** — real
implementation work, with nothing marshal-native distinguishing "cheap to
redispatch fresh" from "this diff needs preserving first." A human had to
`git status`/`git diff --stat` both by hand to find out which was which.

Full narrative and incident detail: `docs/dreams/marshal-dependency-aware-dispatch.md`.

## 2. Impact Analysis

- **Epic impact:** Epic 28 (Token economy) is unaffected in its existing 11
  stories — this is additive scope, not a redefinition. Two new stories append
  at the end of the epic's story list.
- **Story impact:** No existing story's ACs, Deps, or status changes. Two new
  stories (28.12, 28.13) are added, both with `Deps: —` (they depend on marshal's
  existing `factory drain`/`dispatch` machinery, not on any other Epic 28 story).
- **Spec impact:** `spec-marshal-token-economy/SPEC.md` gains CAP-14 and CAP-15.
- **Artifact conflicts:** None with the PRD or architecture docs — this is
  marshal-internal tooling reliability, not user-facing product scope.
- **Naming tension (flagged, not silently resolved):** `spec-marshal-token-economy`
  is framed around *token* economy specifically (compression, context, spend).
  CAP-14/15 are about *dispatch-ordering and work-loss* economy — real waste
  (a wrong-order dispatch burns a worktree and a session; a mishandled kill can
  discard real work), but not token-shaped waste. The Dream itself already notes
  that `factory drain`'s own surface (Epic 22, Story 22.11 / FR-193 CAP-10 —
  station-scoped drain, the same command family) is the mechanically more natural
  home. Proceeding with Epic 28 placement per explicit operator instruction; the
  spec's `## Why` section is not being rewritten to justify the fit — the two new
  CAPs stand on their own rationale within the existing capability list.

## 3. Recommended Approach

**Direct Adjustment** — append two new stories to Epic 28's existing story list,
extend `spec-marshal-token-economy` with two new CAPs, add both story keys to
`sprint-status-ledger.yaml` as `backlog`. No rollback, no MVP re-scope. This is a
Minor-scope change: no other epic, story, PRD section, or architecture doc is
touched.

**Effort/risk:** Both stories are independent (`Deps: —`), so they can dispatch
in either order or in parallel once queued. Low risk — they modify
`factory drain`/`factory dispatch` internals only; no schema, no cross-station
contract change.

## 4. Detailed Change Proposals

### 4.1 `spec-marshal-token-economy/SPEC.md` — new capabilities

```
OLD (end of Capabilities section, after CAP-13):
  (CAP-13 is the last entry)

NEW (append):
- **CAP-14**
  - **intent:** `factory drain` (no caller-supplied `--stories`) derives dispatch
    order from each backlog story's `Deps:` line instead of walking
    `sprint-status-ledger.yaml` raw order — a topological sort over the tracked
    dependency graph, honoring cross-epic edges, falling back to ledger order
    only among stories with no unmet dependency either way. `--stories` remains
    as an explicit caller override.
  - **success:** A station whose backlog has a cross-epic dependency (verified:
    `pyforge-atlas` Story 23.9 → Story 22.1) dispatches in an order that never
    violates a declared `Deps:` edge, without an operator hand-deriving it first;
    a station with no `--stories` override still produces a valid order;
    `--stories` continues to work unchanged as an override.
- **CAP-15**
  - **intent:** A dispatch ended by an external stop (SIGTERM outside marshal's
    own idle/budget ladder) is distinguished, in the journal, from a genuine
    failure (verdict-gated, review-rejected, crashed) — and is retryable through
    the normal `drain`/`dispatch --stories` path without an undocumented
    workaround. Before a retry touches a worktree carrying uncommitted changes,
    the size and file list of that diff is surfaced, not silently ignored or
    discarded.
  - **success:** An externally-stopped story is not journaled `MRS-DRAIN-005
    failed`; it dispatches again through `drain`/`--stories` without requiring
    the bare-`dispatch <slug> <story>` workaround; a retry against a worktree
    with uncommitted changes reports the diff (files, line count) before
    proceeding; `MRS-DISP-011`'s live-session-process refusal is unchanged.

id/status/companions/sources: unchanged except `sources:` gains
`../../../../../../docs/dreams/marshal-dependency-aware-dispatch.md`.
```

### 4.2 `epics.md` — Epic 28 header + two new stories

```
OLD (Epic 28 header, "Decomposes" line):
Decomposes `spec-marshal-token-economy` (CAP-1..CAP-12; CAP-11/CAP-12 added
2026-08-30 from the operator's model/cost catalog — Stories 28.10/28.11;
Dream: `docs/dreams/marshal-token-economy.md`).

NEW:
Decomposes `spec-marshal-token-economy` (CAP-1..CAP-15; CAP-11/CAP-12 added
2026-08-30 from the operator's model/cost catalog — Stories 28.10/28.11;
CAP-14/CAP-15 added 2026-08-31 from a live dispatch-ordering/retry incident —
Stories 28.12/28.13; Dream: `docs/dreams/marshal-token-economy.md` +
`docs/dreams/marshal-dependency-aware-dispatch.md`).
```

```
NEW (append after Story 28.11, before the epic's closing `---`):

### Story 28.12: Dependency-derived dispatch ordering

As a marshal operator,
I want `factory drain` to compute dispatch order from each story's declared
`Deps:` instead of raw ledger order,
So that a station's backlog never dispatches a story ahead of an unmet
dependency, including across epics.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** token-economy CAP-14
**Given** a station's tracked backlog with a `Deps:` graph spanning more than one
epic **When** `factory drain` runs with no `--stories` override **Then** the
computed dispatch order never violates a declared `Deps:` edge
**And** stories with no unmet dependency either way fall back to ledger order
(deterministic, no invented preference)
**And** `--stories` continues to work unchanged as an explicit override

### Story 28.13: Sanctioned retry after an operator-initiated stop

As a marshal operator,
I want an externally-stopped dispatch distinguished from a genuinely failed one,
and a documented retry path for the former,
So that stopping a run to reprioritize never permanently blocks that story, and
a retry never silently steps on uncommitted work.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** token-economy CAP-15
**Given** a dispatch session stopped by SIGTERM from outside marshal's own
idle/budget ladder **When** the journal records the outcome **Then** it is not
recorded as `failed` the way a genuine verdict/review/crash failure is
**And** the story is retryable through `drain`/`dispatch --stories` without the
undocumented bare-`dispatch <slug> <story>` workaround
**And** a retry against a worktree already carrying uncommitted changes reports
the diff (file count, line count) before proceeding
**And** `MRS-DISP-011`'s refusal while a session process is genuinely still
alive is unchanged
```

### 4.3 `sprint-status-ledger.yaml` — two new backlog entries

```
NEW (append under development_status, alongside the other 28-* keys):
  28-12-dependency-derived-dispatch-ordering: backlog
  28-13-sanctioned-retry-after-an-operator-initiated-stop: backlog
```

No other epic, story, or ledger key is touched.

## 5. Implementation Handoff

**Scope classification: Minor.** Both stories are self-contained additions to an
existing epic/spec/ledger with no cross-artifact ripple beyond the three files
above. Route to: Developer agent (`bmad-build` / `bmad-build-auto`) for direct
implementation once dispatched — no PM/Architect replan needed.

**Success criteria:** `factory drain` (no `--stories`) on a station with a
cross-epic `Deps:` graph produces a valid topological order without operator
intervention (28.12); an externally-stopped story is retryable through
`drain`/`--stories` without the bare-dispatch workaround, and worktree diffs are
surfaced before a retry touches them (28.13).
