---
id: SPEC-marshal-token-economy
spec: marshal-token-economy
status: ready
owner-dream: docs/dreams/marshal-token-economy.md
companions:
  - integration-layers.md
surface:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_profile.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/**
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/**
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/supervisor/**
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/supervise.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/check.py
sources:
  - ../../../../../../docs/dreams/marshal-token-economy.md
open_questions: []
---

> **Canonical contract.** This SPEC and `integration-layers.md` are the complete,
> preservation-validated contract for what to build, test, and validate.
> `docs/dreams/marshal-token-economy.md` is listed in `sources:` for narrative
> rationale this contract intentionally omits.

# The loop reads less, says less, and re-learns nothing

## Why

A pain to solve. Marshal's token posture is brakes only: per-story/per-run weighted
ceilings (E3.6, 50M/500M defaults), the idle-strand ladder, prompt-cache TTL discipline
(NFR-14), model tiering (FR-51, wired but rarely fed), single-story dispatch (E22). Nothing
anywhere in marshal, bmad-loop, or bmad-build-auto *shrinks* what an iteration reads or
writes. Every fresh session re-reads ~23k tokens of identical repo docs, re-explores an
unchanged codebase, receives test logs that are 80–95% passing noise, pays the tax again for
each of up to four fresh reviewer lenses, and narrates its work in full prose — the
heaviest-weighted tokens in the tally. Five instruments that attack exactly these sinks are
already packaged in `recipes/` (headroom-ai, caveman, codegraph, cocoindex, graphifyy) and
none is wired into the loop. The deferred-work ledger's token findings are all observability
gaps (`DW-FU-3-6-6`), never "context is too big" — because nothing has ever measured it.

## Capabilities

- **CAP-1**
  - **intent:** A declared context pipeline: a `[context]` block in `EffectivePolicy`,
    rendered into every launch surface identically for both engines (bmad-loop spin and
    bmad-build-auto dispatch) — which layers are on, aggressiveness, store paths.
  - **success:** Rendered output carries the block from one composition site; a run on
    either engine resolves the same declaration; an absent block means every layer off and
    today's behavior byte-identical.
- **CAP-2**
  - **intent:** Wire compression at the harness seam: when policy enables it, sessions
    launch through the compression layer (agent wrap / proxy) so tool outputs, logs, and
    file reads are compressed before the provider call, with originals in a loop-home-scoped
    CCR store the agent can retrieve from.
  - **success:** The launched command is demonstrably wrapped; a compressed artifact is
    retrievable byte-exact; the prompt prefix (system prompt, tool definitions, older turns)
    is byte-identical wrapped vs unwrapped.
- **CAP-3**
  - **intent:** Output-compression seeding: Genesis deploys the caveman skill per loop home
    so dev-session speech compresses (~65%), while review verdicts, journals, and escalation
    context stay fully articulated.
  - **success:** `marshal seed check` verifies deployment; a landed story's verdict and
    journal read as normal prose.
- **CAP-4**
  - **intent:** Structure from the graph: loop-home provisioning builds/syncs the codegraph
    index and wires the agent integration, so structure questions resolve from the graph
    instead of file re-reads.
  - **success:** Seed check proves the index present and fresh at admission; a session
    answers a structure query without re-reading the files it names.
- **CAP-5**
  - **intent:** Incremental derived context: epic-context / continuity distills become
    incrementally-maintained derived artifacts (cocoindex) recomputed only when their
    planning sources change.
  - **success:** Unchanged sources yield zero recompute across two consecutive iterations; a
    source edit yields exactly one refresh.
- **CAP-6**
  - **intent:** Planning-graph retrieval: story routing retrieves the scoped planning
    context a story binds to (graph query via the Scribe-owned GraphStore seam over
    graphifyy) instead of loading `epics.md`/`prd.md` wholesale; degrades to epic-context
    files when the seam is absent.
  - **success:** An epic-path iteration completes within the epic-context token target with
    zero full-document loads; the fallback is proven by disabling the seam.
- **CAP-7**
  - **intent:** Savings telemetry: the supervisor journals per-story spend AND per-layer
    savings (wire-compression stats, output-compression delta, graph-hit vs file-read
    counts); `marshal status` renders both mid-run.
  - **success:** Journal entries carry savings fields; status shows them while a run is
    live (chips at `DW-FU-3-6-6` mid-session blindness).
- **CAP-8**
  - **intent:** A graduated compression ladder: as a story approaches its token ceiling the
    supervisor raises compression aggressiveness (and may lower the model floor via existing
    FR-51 tiering) before the stop-retry-defer ladder fires.
  - **success:** A test proves ladder ordering — compression escalation strictly precedes
    kill — and that no gate or reviewer is ever skipped by escalation.
- **CAP-9**
  - **intent:** A measured baseline: a pinned, re-runnable benchmark (same story, layers on
    vs off) reports before/after weighted tokens per layer.
  - **success:** The benchmark artifact reproducibly emits the comparison; ceiling
    recalibration cites it.
- **CAP-10**
  - **intent:** Index freshness is an admission signal: `marshal check` gains advisory
    codegraph/cocoindex staleness findings.
  - **success:** A stale index yields a named finding; the exit-code domain
    `{0, 1, 2, 3, 4, 130}` is unchanged; the finding never blocks a run by itself.

## Constraints

- **Never compress the contract:** story specs, acceptance criteria, gate verdicts, and
  escalation context cross the wire intact — compression applies to what the agent reads
  along the way and says, never to what it is bound by.
- **Never break the provider prompt cache (NFR-14):** any layer that rewrites the prompt
  prefix is inadmissible; live-zone-only compression is the admission requirement, proven by
  prefix byte-comparison.
- **Reversible or absent:** lossy-with-retrieval (CCR) is acceptable; silently-lossy is
  not — a compressed FATAL line must be recoverable byte-exact.
- **BSL boundary:** the caveman input proxy (`@caveman-ai/cli`, BSL-1.1) stays unpackaged
  and unwired; headroom-ai (Apache-2.0) is the input side.
- **Telemetry stays advisory:** savings numbers inform ceilings and tiering, never a
  pass/fail verdict — no second PR gate.
- **Graceful degradation per layer:** an unavailable instrument (platform gap, pixi
  blocker) disables its layer with a named finding, never blocks a run — the
  headroom-ai/caveman pixi activation is a prerequisite tracked in
  `docs/dreams/pixi-candidate-currency.md`, not silently assumed.

## Non-goals

- **Not** altering BMAD skill semantics: the story contract, gates, and review occurrence
  are untouched; only the encoding of what flows through changes.
- **Not** replacing the spend brakes — ceilings, idle ladder, and tiering stay.
- **Not** a second knowledge graph inside marshal: the GraphStore seam is Scribe-owned;
  marshal consumes it.
- **Not** the pixi unblocking work itself (owned by the pixi-candidate-currency ledger).
- **Not** review-depth scheduling (owned by `spec-risk-tiered-review-depth`).

## Success signal

The pinned benchmark story runs twice — layers off, layers on — and the on-run lands the
same story (same verdict, same gate results, reviewer never skipped) at a measurably lower
weighted-token total, with the per-layer savings visible in the run's journal and in
`marshal status` while it runs. Ceilings are then recalibrated citing that measurement.
