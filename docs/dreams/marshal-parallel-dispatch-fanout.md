---
title: Parallel dispatch fan-out when dependencies and surfaces are disjoint — without breaking the zombie guards
type: dream
owner: marshal
status: specified
---

# Parallel dispatch fan-out when dependencies and surfaces are disjoint

## The Dream

Today marshal's factory drain is **fast across stations, serial within one**.
`pyforge-marshal` and `pyforge-atlas` can run at the same time — Story **22.5**
(FR-193 CAP-5) explicitly allows that. But on a **single station**, the same
story forbids a second dispatch the moment *any* story is judged **live**, even
when the two stories share no dependency edge, touch no overlapping frozen
surface, and would land on separate worktrees anyway. Epic 28's eight-story
remainder and atlas's sixteen-story workbook-retirement path therefore spend
wall-clock time waiting in a queue that dependency math says could have been a
**wave** — not because the harness cannot run two cursor sessions, but because
22.5's mutex is intentionally coarse.

**Story 28.12** (backlog) will fix *order*: derive a topological sequence from
`Deps:` instead of raw ledger order or hand-maintained
`fleet-drain-queue.yaml`. This Dream fixes *width*: among stories that are
**simultaneously eligible** (dependencies satisfied), launch **more than one**
when their **declared surfaces are provably disjoint**, up to a policy cap,
while leaving Story **22.2**'s completion judge untouched — every story still
owns its own session PID, supervisor, journal run, worktree, and git-fact
verdict. A zombie on story A must never block story B when B's surface cannot
 collide with A's WIP and B does not depend on A.

The aspiration is not "turn marshal into a thread pool." It is **wave scheduling**:
each drain cycle computes a **ready set** (deps met, backlog, not done), partitions
that set into **parallel-safe batches** (pairwise surface-disjoint under the
existing AD-27 narrow-only combinator), launches one detached dispatch per batch
member, waits for the wave to **terminalize** (complete, failed-with-preserve, or
verified land) before advancing dependents — and journals the wave explicitly so
`fleet-picture` and `marshal status` show *which* stories were intentionally
in flight together, not an accident of timing.

## What is real — the incident this Dream is written from

**2026-09-01**, running Epic 28 and atlas drains in parallel:

- **Cross-station parallelism worked.** Marshal 28.7 and atlas 23.1 ran as
  separate stations — exactly what 22.5 allows.
- **Within-station parallelism did not.** The operator asked whether independent
  Epic 28 stories (or atlas stories with satisfied deps) could fan out together.
  Answer: **no** — `station_in_flight_conflict()` refuses *any* second story on
  the same station while *any* journal row is `LIVE`, with `MRS-DISP-021`.
- **`--stories` is a serial chain, not a fan-out.** Story 22.11 chains one
  dispatch at a time via the fleet supervisor; it does not interpret the list as
  a parallel batch.
- **22.2 zombie guards did their job — painfully.** Killing Claude mid-28.7 left
  four dirty paths in `.worktrees/dispatch-pyforge-marshal-28.7`. Verdict stayed
  `LIVE` ("still live by git facts") even with no process — correct for *that*
  story, but it also blocked the entire station slot until verify/preserve/land
  reconciled. The Dream must **not** loosen "uncommitted progress = live for the
  story that owns it"; it must stop that live story from blocking **unrelated**
  stories.
- **28.12 is ordering-only.** Topological sort answers "what next in sequence";
  this Dream answers "what else **now**, beside the head of the queue."

Related dreams already in flight:

- [`marshal-dependency-aware-dispatch.md`](marshal-dependency-aware-dispatch.md)
  — ordering (28.12), sanctioned retry (28.13), scope automation (28.14/28.15).
- [`marshal-single-story-dispatch.md`](marshal-single-story-dispatch.md) — the
  validated pattern; addendum already named "parallel when surfaces are disjoint"
  as an open Spec question.
- [`horizontal-run-concurrency.md`](horizontal-run-concurrency.md) — bmad-loop
  `max_parallel` stub; **this Dream is factory-dispatch fan-out**, not in-loop
  Phase 5.

## What this Dream asks for

### A. Wave scheduler beside serial drain (opt-in, default unchanged)

- **`factory drain` / `dispatch --stories` gain an explicit parallel mode**
  (name TBD: `--parallel`, `--max-in-flight`, or policy `dispatch.max_parallel`
  per station) — **default remains 1** so today's serial semantics are
  byte-identical when unset.
- **A wave** = the set of stories launched together in one fleet-supervisor cycle
  on one station, each with the existing one-worktree-one-branch provisioning
  (`dispatch/<station>/<story>`).
- **Between waves:** the supervisor waits until every member of the current wave
  reaches a **terminal dispatch outcome** (completed land, failed with preserve,
  or blocked with explicit operator classification) before computing the next
  ready set. Dependents never start in the same wave as an unfinished dependency.

### B. Ready set from the dependency graph (28.12-adjacent, shared hook)

- Reuse the **same `Deps:` graph** Story 28.12 will introduce for ordering:
  a story is *ready* when every declared dependency is `done` on the tracked
  ledger (cross-epic edges included).
- Among ready stories, **28.12 ledger-order tie-break** still applies when
  choosing batch members — parallelism does not invent a second preference.

### C. Surface-disjointness as the parallel safety proof

- Two stories may share a wave **only if** their **effective frozen surfaces**
  (AD-27: `policy_surface ∩ spec_surface`, same machinery as `MRS-GATE-007`) are
  **pairwise disjoint** — path-level, not heuristic.
- **Overlap within a station is a hard refusal** for that pair (stronger than
  today's cross-station `MRS-DISP-022` advisory). Disjointness is the proof that
  parallel landings cannot fight over the same files.
- Stories with **empty or unknown surface** do not fan out with others until
  surface is declared — conservative default, same posture as scope gates today.

### D. 22.2 zombie guards preserved per story, relaxed per station

**Do not change** `judge_dispatch_completion()`:

```text
LIVE  := session_alive OR has_git_progress(for this story's worktree)
FAILED := session dead AND no git progress AND not merged
```

**Do change** `station_in_flight_conflict()`:

| Today (22.5) | This Dream |
|---|---|
| Any `LIVE` story blocks **all** other stories on the station | Story X blocks story Y only if **Y depends on X** (transitive) **OR** surfaces overlap **OR** same story key (existing `MRS-DISP-011`) |
| Zombie with WIP blocks unrelated backlog | Zombie with WIP blocks **only** dependents and surface colliders |

Mechanically: walk in-flight journals; for each candidate next story, refuse
only on **dependency** or **surface intersection** or **same-key redispatch** —
not merely "something else is live."

Preserve capture (`dispatch-preserve` patch on failed kill) stays **per story**;
parallel story B's landing path never resets story A's worktree.

### E. Observability and operator trust

- Journal a **`dispatch-wave`** intent/outcome: member story keys, computed
  disjointness evidence (surface hashes or path lists), cap applied, refused
  candidates with reason (`dep-unmet`, `surface-overlap`, `cap`).
- `marshal status` / `fleet-picture` show **in-flight count per station** and
  wave id — not a flat "28.7" that hides a second concurrent 28.10.
- Fleet-wide advisory lock (two campaigns racing one station) **unchanged**.

## Minimal design sketch (28.12-adjacent)

```text
each supervisor tick:
  ready := backlog stories where all Deps: are done on ledger
  if max_parallel == 1:
    dispatch first(ready, ledger_tie_break)   # today
  else:
    batch := []
    for s in ready ordered by ledger_tie_break:
      if len(batch) >= max_parallel: break
      if any(dep(s, b) or surface_overlap(s, b) for b in batch): continue
      batch.append(s)
    for s in batch: dispatch_once(s)   # detached, existing path
  wait until all batch members terminal OR tick sleep
```

**Integration points** (for later Spec, not this Dream):

- `core/dispatch_fleet.py` — wave batch builder + cap
- `cli/dispatch.py` — `station_in_flight_conflict` narrowing; wave journal kinds
- `core/dispatch.py` — reuse 28.12 topo/ready helper; surface overlap already
  partially exists for `MRS-DISP-022`
- `planning-artifacts/marshal-policy.toml` — `dispatch.max_parallel` (default 1)

**Explicit non-goals in v1:**

- No shared worktree / no multi-story branch
- No automatic retry of parallel wave members (28.13 stays separate)
- No cross-station batching (stations already parallel)
- No weakening verify/land — each story still runs full gate ladder independently

## Guardrails — what this Dream refuses to do

- **Does not** replace Story 28.12 — ordering and fan-out compose; 28.12 ships
  first or in the same epic tranche, but this Dream is not "28.12 with extra steps."
- **Does not** weaken **22.2** per-story LIVE semantics or reintroduce
  notification-based completion.
- **Does not** weaken **22.3** verify-before-land or allow one story's land to
  skip another's gates.
- **Does not** silently raise `max_parallel` — cap must be declared in policy or
  flags; `fleet-picture` calls out when a station runs >1.
- **Does not** fan out stories whose surfaces are unknown — unknown means serial.
- **Does not** duplicate bmad-loop Phase 5 — that stub remains upstream; factory
  dispatch owns its own scheduler.

## Gates and open questions

- **Story placement:** **resolved 2026-09-01** — Epic 28 Story **28.16**, sibling
  to 28.12; spec `spec-marshal-parallel-dispatch-fanout/SPEC.md` (CAP-1..5).
- **Cap semantics:** fixed integer vs "as many disjoint as ready" vs token-budget
  aware (ties to token-economy Epic 28 stories 28.10/28.11).
- **Partial wave failure:** if one member of a wave fails verify and another
  succeeds, does the wave close asymmetrically or hold the survivor until the
  failed story is classified (28.13 stopped vs failed)?
- **Surface proof cost:** pairwise intersection on every tick vs precomputed
  surface index at spec-promotion time (Scribe/graph seam, 28.9-adjacent).
- **Operator override:** `--stories a,b,c` with `--parallel` — treat list as
  explicit wave (operator asserts disjoint) or re-validate surfaces and refuse?
- **Live proof required:** no fan-out ships without a fixture pinning two
  disjoint pyforge-marshal stories landing in one wave while a third overlapping
  story is correctly refused.

## Relationship to the active drain (2026-09-01)

Until this Dream is specified and built, operators should assume **serial
within station**: hand-maintained `fleet-drain-queue.yaml` order,
`--stories` chains, and cross-station parallelism only. The Epic 28 + atlas
campaigns running today are the baseline behavior this Dream improves — not
the other way around.

---

## Realization log

- **2026-09-01** — Dream captured from live Epic 28 + atlas drain session: 22.5
  mutex, 22.2 git-fact zombies, 28.12 ordering gap, and operator ask for
  composer/cursor fan-out when deps and surfaces allow.
- **2026-09-01** — `bmad-spec` → Story **28.16** +
  `spec-marshal-parallel-dispatch-fanout/SPEC.md` (CAP-1 wave scheduler,
  CAP-2 narrowed conflict, CAP-3 journal, CAP-4 explicit cap default 1, CAP-5
  compose with 28.12). Status: `specified`.
