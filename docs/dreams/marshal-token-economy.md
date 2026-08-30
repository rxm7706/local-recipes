---
title: Marshal Token Economy — the loop that reads less, says less, and re-learns nothing
type: dream
owner: marshal
status: specified
---

# Marshal Token Economy

## The Dream

Every unattended story Marshal runs today pays a tax it never questions. The
session boots and re-reads the same repo guidance it read yesterday. It
re-explores a codebase whose structure has not changed since the last
iteration. It receives test logs that are 95% passing noise around one FATAL
line. It narrates its work in polite, fully-grammatical prose that nobody but
another machine will ever read. Then the session ends, the context evaporates,
and the next story pays the whole tax again.

Marshal already knows how to **stop runaway spend** — budget ceilings, the
idle-strand ladder, prompt-cache-aware polling, model tiering. What it cannot
yet do is **make an iteration cheap in the first place**. The dream is a loop
where every token that reaches the model earns its place: tool outputs arrive
compressed but reversible, codebase structure is answered from a pre-built
graph instead of re-read files, planning context is retrieved as the 1,500
tokens a story actually needs instead of the 65,000-token document it lives in,
derived context is recomputed only when its sources change, and the agent's own
output is stripped to its semantic payload. The operator sees, per story, not
just "how much was spent" but "how much was *saved*, by which layer" — and the
budget ceilings stop being blunt kill-switches and become calibrated contracts
a normal story never brushes against.

Same stories landed. Same review fidelity. A fraction of the tokens.

## What is real

**Marshal's existing token posture is brakes, not diet.** Shipped: per-story /
per-run weighted-token and wall-clock ceilings (E3.6, defaults 50M/500M
weighted), the idle ladder (nudge → stop-retry → defer), prompt-cache TTL
discipline (NFR-14, poll ≤60s, `cache_read_weight = 0.1`), difficulty-driven
model tiering (FR-51, wired but rarely fed — see
[`adaptive-model-tiering.md`](adaptive-model-tiering.md)), and single-story
dispatch (E22). Nothing in the marshal package or the bmad-loop/bmad-build-auto
chain compresses, indexes, or graph-serves context. The deferred-work ledger
confirms it: token findings are all observability gaps (`DW-FU-3-6-6`
mid-session ceiling blindness), never "context is too big".

**Where an iteration's tokens actually go** (fresh session per story):

| Sink | Rough size | Nature |
|---|---|---|
| Always-on repo docs (`CLAUDE.md`, `AGENTS.md`) | ~10k + ~3.6k tokens | identical every session |
| `project-context.md` (build-auto activation) | ~9k tokens | identical every iteration |
| Story spec + epic-context + sibling continuity | ~5k–16k tokens | per-story, partially redundant |
| Tool outputs mid-story (file reads, grep, test/build logs) | unbounded — often the dominant sink | 70–95% boilerplate |
| Codebase re-exploration | tens of k per session | structure that rarely changed |
| Review passes (4 fresh reviewer lenses × diff + context) | full context tax × N | multiplicative |
| Agent's own output (weighted heaviest) | prose ceremony | compressible ~65% |

**The five instruments are already forged — none is wired in:**

- **`recipes/headroom-ai/`** (0.32.1, Apache-2.0) — context-compression layer:
  SmartCrusher/ContentRouter/CodeCompressor over tool outputs, logs, JSON,
  diffs; 40–95% savings; **reversible** via the CCR store +
  `headroom_retrieve`; ships as library, transparent proxy, MCP server, and
  one-command agent wrap (`headroom wrap claude|copilot|cursor|…`). Critically,
  its live-zone-only design compresses only the newest blocks and leaves the
  provider cache hot zone untouched — it *cooperates* with NFR-14 instead of
  fighting it. Commented-out in `pixi.toml` (blocked per
  [`pixi-candidate-currency.md`](pixi-candidate-currency.md)).
- **`recipes/caveman/`** (2.4.0, MIT installer) — Claude Code skill cutting
  ~65% of **output** tokens (the heaviest-weighted kind) via ultra-compressed
  agent speech. This recipe ships only the MIT skill installer
  (`caveman-install`); upstream's input-side Caveman Proxy is a separate
  BSL-1.1 product, deliberately not packaged. Commented-out in `pixi.toml`.
- **`recipes/codegraph/`** (1.6.0, MIT) — pre-indexed code knowledge graph,
  kept synced on change; agents answer structure questions from the graph
  instead of re-reading files. Fully local. Active in pixi, linux-64 only.
- **`recipes/graphifyy/`** (0.9.44, MIT) — turns any folder of code/docs into a
  queryable knowledge graph. Active in pixi. Scribe already plans to bind it
  behind a `GraphStore` seam — ownership must be coordinated, not duplicated.
- **`recipes/cocoindex/`** (1.0.20, Apache-2.0, on conda-forge) — incremental
  indexing engine: derived indexes stay fresh from source updates with minimal
  recomputation. Active in pixi.
- *(Bonus instrument:* **`recipes/rtk/`** — "Rust Token Killer" proxy that
  shrinks `git`/`ls`/shell output before the agent sees it.)*

## The integration architecture — five layers, one policy surface

Each layer attacks a different sink; they compose because they operate at
different points of the pipeline. All of them live **outside** the BMAD
skills' semantics — the story contract, gates, and review verdicts are never
altered, only the encoding of what flows through.

```
                    ┌─ Layer 4: graphifyy ── planning-artifacts as a queryable
                    │            graph: retrieve the 1.5k tokens a story needs,
                    │            never load epics.md (65k) / prd.md (46k)
                    │
  bmad-build-auto ──┤─ Layer 3: cocoindex ── epic-context / project-context
     (per story)    │            distills recomputed ONLY when sources change
                    │
                    ├─ Layer 2: codegraph ── structure questions answered from
                    │            the pre-built graph, not file re-reads
                    │
  coding CLI  ──────┼─ Layer 1: headroom ─── every tool output / log / diff
  (claude/copilot)  │            compressed 40–95%, reversible via CCR
                    │
                    └─ Layer 0: caveman ──── the agent's own output stripped
                                 ~65%, heaviest-weighted tokens
  marshal ──────────── policy renders it, Genesis seeds it, supervisor
                       meters it: savings-per-layer in every journal
```

- **Layer 1 — wire compression (headroom-ai).** Marshal's harness profiles
  gain a wrap step: the coding CLI runs behind `headroom wrap <cli>` (or the
  transparent proxy for base-URL-only tools), so tool outputs, build/test
  logs, and file reads are compressed before the provider call. The CCR store
  lives inside the loop home (worktree-scoped, torn down with it), and the
  agent keeps `headroom_retrieve` for full originals — nothing is lost, which
  keeps the fidelity contract intact.
- **Layer 0 — output compression (caveman).** Genesis (`marshal seed`) deploys
  the caveman skill into each loop home's agent config; dev sessions talk
  caveman, review verdicts and journal entries stay fully articulated (the
  operator and the escalation path read those). Output tokens carry the
  highest weight in the tally, so this is the cheapest big win.
- **Layer 2 — structure from the graph (codegraph).** Loop-home provisioning
  indexes the worktree and wires the agent integration; the supervisor treats
  index staleness as a run-admission finding, not a mid-run surprise.
- **Layer 3 — incremental derived context (cocoindex).** The epic-context
  compile (today an "if cache invalid, re-distill" step inside bmad-build-auto)
  becomes a cocoindex flow: story specs, epic-context, and continuity summaries
  are derived artifacts that update incrementally when planning sources change
  — never recomputed from the full PRD on a hunch, never stale.
- **Layer 4 — planning knowledge graph (graphifyy).** The planning corpus
  (PRD, epics, architecture, specs) becomes a queryable graph so step-01
  routing retrieves precisely the fields a story binds to. This layer is
  shared infrastructure with Scribe's `GraphStore` seam — Marshal consumes it,
  Scribe owns it.

## What Marshal itself must grow

1. **A context-pipeline policy block.** `EffectivePolicy` → rendered
   `policy.toml` gains a `[context]` section: which layers are on, compression
   aggressiveness, CCR store path, per-profile wrap command. Declared like
   everything else Marshal renders — never hand-configured in a loop home.
2. **Harness-profile wrapping.** The packaged profiles
   (`claude.toml`, `copilot.toml`, …) gain an optional wrapper field applied
   at spin/dispatch, so Layer 1 is a profile property, not a shell hack.
3. **Genesis seeding of the toolchain.** `marshal seed` installs and `marshal
   seed check` verifies the per-loop-home kit: caveman skill deployed,
   codegraph index built, CCR store dir present, graph endpoints reachable.
4. **Savings telemetry in the journals.** The supervisor already tallies
   weighted tokens; it learns to record per-layer savings (headroom stats,
   caveman benchmark deltas, graph-hit vs file-read counts) per story. This
   also chips at the standing `DW-FU-3-6-6` mid-session-blindness finding:
   the operator finally sees spend *and* savings while the run lives.
5. **A graduated compression ladder.** Sibling to the idle ladder: as a story
   approaches its token ceiling, the supervisor can raise compression
   aggressiveness (and model tiering can lower the floor) before it ever
   reaches the kill threshold. Ceilings get recalibrated once baseline savings
   are measured — 50M weighted was sized for an uncompressed world.
6. **Index-freshness as a detector.** `marshal check` (the existing detector
   front door) gains codegraph/cocoindex staleness findings — advisory,
   consistent with the "never a second gate" doctrine.
7. **Review-pass economy.** Reviewer lenses receive the compressed diff plus
   graph-served context instead of re-exploring the worktree from zero —
   multiplied across four lenses per story, this is where Layer 1+2 pay twice.
   (Depth-scheduling itself stays with
   [`risk-tiered-review-depth.md`](risk-tiered-review-depth.md).)

## Guardrails — what this Dream refuses to do

- **Never compress the contract.** Story specs, acceptance criteria, gate
  verdicts, and escalation context cross the wire intact. Compression applies
  to what the agent *reads along the way* and *says*, never to what it is
  *bound by*.
- **Never break the cache to save tokens.** Any layer that rewrites the prompt
  prefix violates NFR-14 and costs more than it saves. Headroom's
  live-zone-only mode is the admission ticket; a compressor without that
  property stays out.
- **Reversible or absent.** Lossy-with-retrieval (CCR) is acceptable;
  silently-lossy is not. A compressed FATAL line must always be recoverable to
  its original.
- **No BSL surprises.** The caveman input-proxy (`@caveman-ai/cli`, BSL-1.1)
  stays unpackaged and unwired unless its license is explicitly accepted;
  headroom-ai (Apache-2.0) covers the input side instead.
- **Savings telemetry is advisory.** It informs ceilings and tiering; it never
  becomes a new pass/fail verdict (Warden doctrine: no second gate).

## Gates and open questions

- **Availability gate:** `headroom-ai` and `caveman` are packaged but
  commented-out in `pixi.toml` — root-caused as blocked in
  [`pixi-candidate-currency.md`](pixi-candidate-currency.md) (the
  `conda-recipe-manager==8.2.1` pin chain). Unblocking that candidate row is a
  prerequisite for Layers 0–1. `codegraph` is linux-64-only today; the loop
  fleet is linux, so acceptable, but the policy block must degrade gracefully.
- **Ownership seam:** Layer 4 must land as Scribe's `GraphStore` with Marshal
  as consumer — building a second graph inside Marshal would violate the
  station charters.
- **Measurement first:** before any layer ships, a pinned benchmark story
  (same story, wrapped vs unwrapped) must establish the real baseline —
  upstream claims (65%, 40–95%) are their benchmarks, not ours. The
  counterfactual harness caveman uses upstream is the model to copy.
- **Where does compression config live** when a run spans engines (bmad-loop
  multi-story vs bmad-build-auto dispatch)? The policy block must be rendered
  identically for both adapters or the savings comparison is meaningless.
