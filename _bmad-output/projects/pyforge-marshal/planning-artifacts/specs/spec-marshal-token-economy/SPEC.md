---
id: SPEC-marshal-token-economy
spec: marshal-token-economy
status: ready
owner-dream: docs/dreams/marshal-token-economy.md
companions:
  - integration-layers.md
  - model-economics.md
surface:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_profile.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/**
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/**
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/supervisor/**
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/supervise.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/check.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
sources:
  - ../../../../../../docs/dreams/marshal-token-economy.md
  - ../../../../../../docs/dreams/marshal-dependency-aware-dispatch.md
open_questions: []
---

> **Canonical contract.** This SPEC, `integration-layers.md`, and `model-economics.md` are
> the complete, preservation-validated contract for what to build, test, and validate.
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
    supervisor raises compression aggressiveness before the stop-retry-defer ladder fires.
    The ladder is compression-only: it never changes the model — model selection stays with
    FR-51 declared difficulty (static) and the Story 3.12 struggle-triggered floor-raise
    (dynamic, upward only; `spec-adaptive-model-tiering` forbids downgrades).
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
- **CAP-11**
  - **intent:** A declared model-cost catalog: policy carries a price table (per
    provider/model: input / output / cache-read / cache-write per 1M, subscription-pool
    membership; seed snapshot in `model-economics.md`); telemetry (CAP-7) and the benchmark
    (CAP-9) render estimated dollar figures alongside weighted tokens, and per-provider
    token weights (e.g. `cache_read_weight`) derive from the declared ratios — the global
    constant stays the fallback for undeclared providers.
  - **success:** Journals, `marshal status`, and the benchmark artifact show dollar
    estimates when the catalog is declared and omit them (never fabricate) when absent; a
    Cursor-pool run provably weighs cache reads at its declared ratio (0.25–0.40) instead
    of the Anthropic 0.10 constant; no code path fetches prices from a network.
- **CAP-12**
  - **intent:** Difficulty tiers route across providers and pools: the `model_tier_map`
    vocabulary extends so a tier's stage entry can name a (harness profile, model) pair —
    easy stories launch on economy-class models, medium on standard-class, heavy on
    frontier-class (ladder in `model-economics.md`) — preferring subscription-covered pools
    before metered API where the catalog marks them.
  - **success:** A declared difficulty demonstrably launches different provider/model pairs
    per the map on both engines (rendered-launch diff); the serving pool is journaled; an
    exhausted or unavailable pool falls through to the next preference, never blocks; the
    FR-51 seam remains the only selection mechanism and run-level batching is unchanged.
- **CAP-13**
  - **intent:** Graph-node staleness flag: `compile_graph` (Scribe's own compile-step,
    CAP-18) flags a node `stale: true` when its source file's latest git commit postdates
    the node's own `valid_from` and no `supersedes:` edge points at it — CAP-6 retrieval
    consumes the flag and falls back to the epic-context file path (CAP-5) instead of
    silently serving a stale graph answer.
  - **success:** A node whose source changed since compile with no declared supersession is
    flagged stale; an unchanged source or a properly superseded node is never flagged; a
    retrieval that hits a stale node demonstrably falls back, never serves it; zero LLM
    calls and no new dependency (a git-timestamp comparison on data compile already walks).
- **CAP-14**
  - **intent:** `factory drain` (no caller-supplied `--stories`) derives dispatch order
    from each backlog story's `Deps:` line instead of walking `sprint-status-ledger.yaml`
    raw order — a topological sort over the tracked dependency graph, honoring cross-epic
    edges, falling back to ledger order only among stories with no unmet dependency either
    way. `--stories` remains as an explicit caller override.
  - **success:** A station whose backlog has a cross-epic dependency (verified:
    `pyforge-atlas` Story 23.9 → Story 22.1) dispatches in an order that never violates a
    declared `Deps:` edge, without an operator hand-deriving it first; a station with no
    `--stories` override still produces a valid order; `--stories` continues to work
    unchanged as an override.
- **CAP-15**
  - **intent:** A dispatch ended by an external stop (SIGTERM outside marshal's own
    idle/budget ladder) is distinguished, in the journal, from a genuine failure
    (verdict-gated, review-rejected, crashed) — and is retryable through the normal
    `drain`/`dispatch --stories` path without an undocumented workaround. Before a retry
    touches a worktree carrying uncommitted changes, the size and file list of that diff is
    surfaced, not silently ignored or discarded. Liveness detection for a station's current
    dispatch does not treat "worktree has uncommitted changes" alone as proof a session
    process is still alive.
  - **success:** An externally-stopped story is not journaled `MRS-DRAIN-005 failed`; it
    dispatches again through `drain`/`--stories` without requiring the bare-`dispatch <slug>
    <story>` workaround; a retry against a worktree with uncommitted changes reports the
    diff (files, line count) before proceeding; `MRS-DISP-011`'s refusal correctly reflects
    actual process liveness, not stale worktree state left behind by an external kill;
    `MRS-DISP-011`'s live-session-process refusal is otherwise unchanged.
- **CAP-16**
  - **intent:** `policy_surface` resolution (feeding AD-27's existing narrow-only
    `compute_effective_surface` combinator, unchanged) auto-derives a safe per-station
    default at `spin`/`dispatch` policy composition — the station's own full package tree
    (`src/shared/packages/pyforge-<slug>/**`), its planning/implementation-artifact trees,
    and the common bookkeeping paths every hand-authored `[epic_surfaces]` entry already
    repeats (`.gitignore`, `pixi.toml`, `pixi.lock`, `environment.yaml`,
    `scripts/.spec-surface-baseline.json`) — without requiring an `[epic_surfaces]` entry to
    exist. An explicit `[epic_surfaces]` entry still narrows further via the existing
    intersection when an operator wants tighter containment than the station-wide default.
  - **success:** A story touching only files under its own station's package tree and the
    common bookkeeping paths passes `MRS-GATE-007` with zero `[epic_surfaces]` entry
    declared; a story touching a *different* station's package, or repo config outside the
    computed default, still fails it — the cross-station containment property is preserved,
    only the within-station per-file enumeration toil is removed; an existing
    `[epic_surfaces]` entry that narrows further continues to behave exactly as today.
- **CAP-17**
  - **intent:** A policy-declared, per-station scope-violation enforcement mode with three
    values — `hard` (today's non-waivable `SCOPE_VIOLATION` refuse), `warn` (`MRS-GATE-007`/
    `008` still fire, still name the offending path, land as an advisory finding — journaled
    AND surfaced in `marshal status`/`fleet-picture`, never journal-only — but never block
    landing), `off` (the check does not run at all: no finding, no journal entry, zero scope
    containment). **Default is `warn`**, not `hard` — an explicit operator decision (2026-08-
    31, after this exact gate stalled two live dispatches for over an hour apiece with no
    self-service recovery path) that visible-but-non-blocking is the right steady state once
    CAP-16's auto-derivation is trusted, with `hard` and `off` both available as an explicit
    opt-in for a station that wants tighter or looser posture. `pyforge-marshal` is set to
    `off` immediately as an operational stopgap (unblocks the live Epic 28 drain campaign
    without waiting on CAP-16/17's own implementation) — this story ships the real `hard`/
    `warn`/`off` mechanism to replace that stopgap, not to introduce it.
  - **success:** A station with no mode declared runs `warn` (visible, non-blocking) — the
    new default, not today's `hard`; `hard` declared for a station reproduces exactly
    today's non-waivable refuse behavior; `off` declared for a station means `MRS-GATE-007`/
    `008` are not evaluated at all for that station — zero findings, zero journal entries,
    by design; `marshal status`/`fleet-picture` render a `warn`-mode violation finding, not
    only the journal; the mode is per-station, so one station's choice never changes
    another's.

## Constraints

- **Never compress the contract:** story specs, acceptance criteria, gate verdicts, and
  escalation context cross the wire intact — compression applies to what the agent reads
  along the way and says, never to what it is bound by.
- **Never break the provider prompt cache (NFR-14):** any layer that rewrites the prompt
  prefix is inadmissible; live-zone-only compression is the admission requirement, proven by
  prefix byte-comparison.
- **Reversible or absent:** lossy-with-retrieval (CCR) is acceptable; silently-lossy is
  not — a compressed FATAL line must be recoverable byte-exact.
- **Staleness detection is deterministic, never LLM-judged (CAP-13):** a git-timestamp
  comparison against the node's `valid_from`, not a per-write model call deciding
  ADD/UPDATE/DELETE/NOOP (Mem0's OSS pattern) — consistent with the standing rule that
  Scribe capture/recall is the fleet's only memory face (no `mem0.add` in its place).
- **BSL boundary:** the caveman input proxy (`@caveman-ai/cli`, BSL-1.1) stays unpackaged
  and unwired; headroom-ai (Apache-2.0) is the input side.
- **Telemetry stays advisory:** savings numbers and dollar estimates inform ceilings and
  tiering, never a pass/fail verdict — no second PR gate.
- **Declared prices only:** the cost catalog is hand-refreshed policy data (dated snapshot
  in `model-economics.md`) — never a live price/billing fetch (air-gap).
- **The review floor holds under routing:** cross-provider tier routing never places the
  review stage below the policy-declared review floor — review misses ship false-greens,
  the one place the strongest model pays for itself.
- **Graceful degradation per layer:** an unavailable instrument (platform gap, pixi
  blocker) disables its layer with a named finding, never blocks a run. The
  headroom-ai/caveman pixi activation LANDED 2026-08-30 (headroom-ai 0.37.0 all
  platforms; caveman 2.4.0 build 2 linux-64 — see `docs/dreams/pixi-candidate-currency.md`),
  so on the linux loop fleet all five layers are live; degradation still governs
  non-linux platforms (caveman/codegraph are linux-64-only) and any future regression.

## Non-goals

- **Not** altering BMAD skill semantics: the story contract, gates, and review occurrence
  are untouched; only the encoding of what flows through changes.
- **Not** replacing the spend brakes — ceilings, idle ladder, and tiering stay.
- **Not** a second knowledge graph inside marshal: the GraphStore seam is Scribe-owned;
  marshal consumes it.
- **Not** the pixi unblocking work itself (owned by the pixi-candidate-currency ledger).
- **Not** review-depth scheduling (owned by `spec-risk-tiered-review-depth`).
- **Not** a billing integration: dollar figures are estimates from declared prices ×
  observed token counts, never reconciled live against provider dashboards.
- **Not** multimodal surfaces: the catalog's audio/TTS/video/music/robotics/embedding
  models are out of scope.

## Success signal

The pinned benchmark story runs twice — layers off, layers on — and the on-run lands the
same story (same verdict, same gate results, reviewer never skipped) at a measurably lower
weighted-token total, with the per-layer savings visible in the run's journal and in
`marshal status` while it runs. Ceilings are then recalibrated citing that measurement.
