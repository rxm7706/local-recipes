---
title: Marshal Dependency-Aware Dispatch — the fleet orders its own backlog and forgets nothing it kills
type: dream
owner: marshal
status: specified
---

# Marshal Dependency-Aware Dispatch

## The Dream

Every station's backlog already carries its own dependency graph — `epics.md`'s
`Deps:` line on every story. Nobody reads that graph but a human (or an agent
standing in for one), by hand, right before dispatching, every single time.
`factory drain --mode drain_to_zero` walks the tracked `sprint-status-ledger.yaml`
in raw ledger order — an order that has no relationship to `Deps:` — and gets away
with it only when raw order and dependency order happen to coincide. When they
don't, a station can dispatch a story whose hard dependency isn't `done` yet,
burning a worktree and a session on a run that was never eligible to succeed.

Marshal already has a caller-supplied escape hatch for this — `--stories` (Story
22.11, FR-193 CAP-10) lets a human hand it an explicit order. But a human
deriving that order is exactly the busywork a dependency-aware `factory drain`
should be doing on its own. The dream is a drain that reads `Deps:` the same way
it reads `sprint-status-ledger.yaml`, computes a valid topological order itself,
and only falls back to raw ledger order for stories with no unmet dependency
either way. `--stories` stays — as an explicit override, not the only path to a
correct sequence.

The second half of the same dream: **a run marshal itself ends should never be
indistinguishable from a run that genuinely failed.** Today, killing a dispatch
session (SIGTERM, from outside marshal's own ladder — an operator reprioritizing,
not a story going wrong) gets journaled as `MRS-DRAIN-005: ended 'failed' by git
and process facts`, and that story is "never auto-retried, never forced past" by
`--stories` or `drain` again. The only way back in discovered live: a bare
`factory dispatch <slug> <story>` call sidesteps `drain`'s own journal check
entirely and just launches fresh — an inconsistency, not a sanctioned unblock
path. If a bare dispatch is safe to retry with, `drain`/`--stories` should offer
the same retry without requiring the operator to know the workaround. And the
operator-initiated case (a deliberate stop, not a story that broke) should be
distinguishable from a genuine failure in the first place, so it doesn't cost the
story a strike it didn't earn.

## What is real — the incident this Dream is written from

2026-08-31, this session, both findings hit inside twenty minutes of each other:

**Finding 1 — no dependency-derived ordering.** Asked to sequence `pyforge-atlas`'s
18 remaining backlog stories (Epics 21–23), the only way to get it right was to
open `epics.md`, read every `Deps:` line by hand, and topologically sort 18 nodes
myself — catching a real risk in the process: `23.9` depends on `22.1`, a
cross-epic dependency `drain_to_zero`'s ledger-order walk has no way to know
about. The already-running `drain_to_zero` (no `--stories`) had started on `21.7`
— correct, but by luck of ledger order, not by design.

**Finding 2 — no sanctioned retry after a killed-not-failed run.** Restarting
`pyforge-atlas` with the derived explicit order (`marshal factory dispatch
pyforge-atlas --stories 21.7,21.8,...`) was refused:

```
finding MRS-DRAIN-005: station 'pyforge-atlas': story '21.7' is blocked --
the last dispatch of '21.7' ... ended 'failed' by git and process facts.
It stays in the backlog, is never auto-retried, and is never forced past;
re-run with --mode skip_on_blocked to move on to this station's next story.
```

`skip_on_blocked` is the wrong tool here — it moves *past* `21.7`, and `21.8`
depends on `21.7`. The only way back in was a bare `marshal factory dispatch
pyforge-atlas 21.7` (no `--stories`), which provisions fresh and launches without
ever consulting the journal `drain` had just refused against. It worked because
it happened to skip the check, not because marshal offered a real "yes, retry
this" path.

The same session then surfaced the stakes of getting this wrong silently: killing
`pyforge-atlas`'s `21.7` dispatch cost nothing (the worktree held only a
`status: in-progress` bookkeeping stamp on the spec file). Killing
`pyforge-marshal`'s `28.2` dispatch minutes later cost a **647-line, 11-file,
fully uncommitted diff** — real implementation work, parked in
`.worktrees/dispatch-pyforge-marshal-28.2` with no marshal-native recovery path
beyond "the worktree still has the files, go look." A story a few minutes into a
kill and a story deep into real work get exactly the same `MRS-DRAIN-005` verdict
today — there's no distinction between "cheap to redispatch fresh" and "this
diff needs to be preserved before anything touches this worktree again."

## What this Dream asks for

**A. Dependency-derived ordering, by default.**
- `factory drain` (no `--stories`) parses each backlog story's `Deps:` line from
  the tracked `epics.md` (or an equivalent structured source, if `Deps:` moves to
  frontmatter/YAML — see Gates) and computes a topological order before
  dispatching, instead of walking `sprint-status-ledger.yaml` raw order.
- Cross-epic dependencies (`23.9` → `22.1`, in this incident) are honored the same
  as same-epic ones — the graph doesn't stop at epic boundaries.
- Optional stories (marked `Optional: yes`) are included in the computed order
  by default, not silently dropped — matching this session's own ask ("include
  the optional vizro identity pages"). Whether to offer an opt-out flag to
  exclude them is a Gate below.
- `--stories` remains as an explicit override for when an operator wants a
  different order than the derived one (partial runs, deliberate re-sequencing,
  a story the graph doesn't know about yet).
- Ties (multiple stories with no unmet dependency between them) fall back to
  ledger order, so the algorithm is deterministic and doesn't invent an ordering
  preference the ledger didn't express.

**B. A sanctioned retry path that survives an operator-initiated stop.**
- Distinguish, in the journal, *why* a dispatch ended: a genuine failure
  (verdict-gated, review-rejected, crashed) vs. an external stop (SIGTERM from
  outside marshal's own ladder) vs. a clean landing. `MRS-DRAIN-005` today
  collapses all non-success endings into one "failed by git and process facts"
  verdict.
- A story stopped externally (not failed) should be retryable through the normal
  `drain`/`--stories` path without a workaround — either it doesn't get journaled
  as `failed` in the first place, or `drain`/`dispatch --stories` grows an
  explicit, documented "clear and retry" affordance that does what the bare
  `dispatch <slug> <story>` workaround does today, on purpose instead of by
  accident.
- Before any retry (sanctioned or the existing workaround) touches a worktree
  that already has uncommitted changes, surface that fact loudly — size of diff,
  files touched — rather than silently letting a fresh dispatch clobber or ignore
  real work. The gap this incident exposed: nothing marshal-native flagged that
  `28.2`'s worktree held 647 real lines while `21.7`'s held three bookkeeping
  ones; a human had to `git status`/`git diff --stat` both by hand to find out.

## Guardrails — what this Dream refuses to do

- Does not touch the actual kill ladder (idle-strand detection, budget-ceiling
  stop/retry/defer) — that machinery already exists and works; this is about
  ordering *before* dispatch and recovery *after* an external stop, not about
  when marshal itself decides to stop a story.
- Does not weaken `MRS-DISP-011` (refusing redispatch while a session process is
  genuinely still alive) — that check is correct and stays.
- Does not make retry automatic/silent. A previously-killed story getting
  redispatched should still be a visible, journaled event — the ask is a
  sanctioned path, not a hidden one.
- Does not invent a second graph/ordering engine — if `Deps:` parsing already
  exists anywhere in the codebase (`bmad-sprint-planning`'s readiness gate, or
  the planning-graph work in Epic 28/Story 28.9), this dream extends that, it
  doesn't duplicate it.

## Gates and open questions

- **Where does `Deps:` parsing belong?** `factory drain` itself (marshal-native),
  or a shared library also used by `bmad-sprint-planning`'s readiness gate (which
  already reasons about story ordering during planning)? Reuse is preferable if
  the parsing logic is close enough to share.
- **Optional-story inclusion:** default include (as this Dream currently asks)
  or default exclude with an `--include-optional` flag? This session wanted them
  included; a different campaign might not.
- **Failed vs. stopped, mechanically:** can the supervisor actually distinguish
  "process received SIGTERM from outside" from "process crashed" from "verdict
  said no" using facts already available (exit code, signal, journal state at
  time of exit), or does marshal need a new signal handler to record intent
  before it dies?
- **Worktree-diff surfacing:** a `marshal factory status`-style check before
  retry, or baked into the retry command itself as a confirmation step?
- **Natural home:** this looks like a direct extension of the same surface Story
  22.11 (FR-193 CAP-10, station-scoped drain) already owns — `factory drain` /
  `factory dispatch --stories` — rather than a new epic. Decomposition (this
  Dream → Spec → epic/story placement in `pyforge-marshal`) will confirm.
