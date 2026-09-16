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

**Dispatch drain resilience (2026-09-01).** Token economy only pays off if unattended
drain survives harness billing walls and recoverable verify failures. Interim
machinery (see `change-history/sprint-change-proposal-2026-09-01-dispatch-autonomy-hotfixes.md`)
adds harness profile failover, transient block classification for fleet retry, and
supervisor stuck-land detection — without weakening CAP-17 warn-mode visibility.

Same stories landed. Same review fidelity. A fraction of the tokens.

## What is real

> *2026-09-09: this section is the 2026-08-30 baseline and is kept as the record. Epic 28 has
> since shipped every item below as **machinery** (24/24 `done`, verified against `main`), and
> none of it is switched on — so the **behaviour** this section describes is still the live
> behaviour. See § Addendum (2026-09-09).*

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
   aggressiveness (compression-only — model movement stays with FR-51 declared
   difficulty and the Story 3.12 upward-only floor-raise, since
   [`adaptive-model-tiering.md`](adaptive-model-tiering.md) forbids downgrades) before it ever
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

- **Availability gate — RESOLVED 2026-08-30:** `headroom-ai` (0.37.0, all
  platforms) and `caveman` (2.4.0 patched build 2, linux-64) are now ACTIVE in
  `pixi.toml`. The `conda-recipe-manager` `click==8.2.1` pin chain fell by
  moving crm+feedrattler into a grayskull-only `crm` feature (nothing in
  local-recipes invokes them), and caveman was rebuilt against nodejs 24 so its
  run-export coexists with codegraph's `nodejs >=24.19,<25` pin (details in
  [`pixi-candidate-currency.md`](pixi-candidate-currency.md)). Layers 0–1 no
  longer degrade on the linux loop fleet. `codegraph` and `caveman` are
  linux-64-only; the loop fleet is linux, so acceptable, but the policy block
  must still degrade gracefully on other platforms.
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

## Addendum (2026-08-30) — the price sheet becomes an instrument

The operator supplied the live 2026 model/cost catalog across the four active
subscriptions (Cursor Ultra, Anthropic Claude Max, GitHub Copilot Basic,
Google Gemini API). Snapshot + analysis:
`spec-marshal-token-economy/model-economics.md`. It changes the Dream in four
ways:

1. **Spend becomes legible in dollars.** The supervisor's weighted-token tally
   can be multiplied through a *declared* price table (input / output /
   cache-read / cache-write per provider/model), so journals, `marshal status`,
   and the benchmark artifact report estimated dollars next to weighted
   tokens. Declared data only — no live billing fetch, still advisory.
2. **The difficulty ladder gets a real price ladder.** Input rates span ~50×
   (Flash-Lite/Luna-class \$0.10–0.20 → Fable-class \$10 per 1M), output ~125×.
   Feeding FR-51's tier map with cross-provider (harness, model) entries —
   easy → economy class, medium → standard class, heavy → frontier class — is
   worth more than any single compression layer, and it is the same shipped
   seam, just a richer vocabulary.
3. **Subscription pools are the cheapest marginal token.** Cursor Ultra's
   included allowance and the Claude Max plan make some tokens effectively
   pre-paid; routing prefers those pools before metered API, journals which
   pool served, and falls through when a pool is exhausted — never blocks.
   (Copilot is Pro today with a downgrade pending — a transitional fall-through
   candidate only, never a preferred pool; GitHub Pro itself is repo features,
   not a model pool.)
4. **The 0.1 cache weight is provider-specific, not universal.** Anthropic,
   OpenAI, and Gemini all publish cache-read at 10% of input — NFR-14's
   `cache_read_weight = 0.1` is exactly right there — but Cursor first-party
   models sit at 0.25–0.40. Weights derive from the declared catalog, global
   constant as fallback.

Landed as CAP-11/CAP-12 in the spec and Stories 28.10/28.11 in Epic 28. The
review-stage floor is explicitly protected under routing: review misses ship
false-greens, so economy routing never touches the review model floor.

## Addendum (2026-08-31) — Layer 4 retrieval is only as good as the graph's freshness

A comparison against Mem0's OSS memory layer (docs.mem0.ai) surfaced a real gap in Layer
4 (planning-graph retrieval, CAP-6 / Story 28.9). Mem0's consolidation pipeline retrieves
the top-k semantically similar existing memories for every new fact and hands both to an
LLM, which picks ADD/UPDATE/DELETE/NOOP — fully model-judged, no heuristics, by design (an
LLM call on every write). Scribe's own supersession (Story 2.3) is the opposite: purely
**author-declared** — a memory's frontmatter carries `supersedes: "<type>/<slug>"`, and
compile mechanically walks only those declared links. Nothing detects a node that has gone
stale because its source moved and nobody wrote the link.

That gap lands on CAP-6/Story 28.9 directly: 28.9's own AC #4 already refuses to let a
graph answer replace the verbatim story contract (spec/ACs) — but it says nothing about
the surrounding *context* a graph node supplies, which could silently serve stale planning
history with no signal.

**Resolution — a deterministic check, not an LLM one.** Porting Mem0's per-write LLM
judgment is not worth it here: scribe's memories are already structured (explicit
`supersedes:`), so the only missing signal is "did the world move since this was
compiled" — a timestamp comparison, not a judgment call. `compile_graph` (which already
walks git history for other surfaces, `_read_git_surface`) gains one more cheap field:
a node is flagged `stale: true` when its source file's latest commit postdates the node's
own `valid_from` and no `supersedes:` edge points at it. Zero LLM calls, zero new
dependency, one more field on data compile already touches every run.

This is scribe's own compile-step capability (`GraphStore`/`compile_surface`, CAP-18) —
28.9 cannot own it (its own Boundaries already forbid touching Scribe's station code
beyond the consumer side). Landing: the staleness field ships as a new scribe Epic 6
story (sibling to 6.1's graphify extra); Story 28.9 gains a fifth AC consuming it — a graph
answer whose backing node is flagged stale falls back to the epic-context file path (Story
28.8's proven fallback), never served silently. Landed as CAP-13 in the spec.

## Addendum (2026-09-09) — built, unmeasured, and asymmetric across the two engines

Epic 28 closed `done` on all 24 stories, and a code-level verification against
`main` found the machinery real: the `[context]` block and
`resolve_context_layers` in `core/policy.py`, the wrapper seam in
`core/harness_profile.py` with its byte-identical prompt-prefix guarantee, the
Genesis kit in `seed/verbs/kit.py`, the ladder and per-layer savings in
`core/supervise.py` + `supervisor/`, `core/token_economy_benchmark.py` with a
`marshal benchmark compare` CLI, and `scripts/index_freshness_check.py`. All
five instruments are pinned in `pixi.toml` and three are on PATH.

**And every layer is off.** No `[context]` block is declared anywhere — not in
`_bmad-output/policy-defaults.toml`, not in any of the eight station
`marshal-policy.toml` files, not in any of the eight rendered loop-home
`.bmad-loop/policy.toml` files. CAP-1's own contract makes an absent block mean
every layer off and behaviour byte-identical to before, so the loop today reads
and says exactly what it did before Epic 28 landed. Three independent
corroborations, none of them the ledger: no caveman skill in any loop home, no
codegraph index in any loop home, and no benchmark comparison artifact anywhere.
`index-freshness-check` reports "all indices fresh or layers off" — the second
branch, a vacuous pass.

**This closes both of this Dream's open gates, and neither closes well.**

*"Measurement first — before any layer ships, a pinned benchmark story must
establish the real baseline."* Every layer shipped; the baseline was never
established. The Dream's own Why said the ledger's token findings were all
observability gaps "because nothing has ever measured it". That is still true
after the epic that set out to fix it.

*"Where does compression config live when a run spans engines? The policy block
must be rendered identically for both adapters or the savings comparison is
meaningless."* The block **is** rendered identically — `resolve_context_layers`
is the single composition site both adapters call, exactly as CAP-1 required.
But rendering is not acting. `resolve_wire_wrap` is imported in exactly one
place, `adapters/harness_bmadbuild.py`. On `factory spin` marshal launches
`bmad-loop run` and bmad-loop launches the coding CLI, so there is no argv to
prefix (`DW-FU-28-2`). Layers 3 and 4 are epic-context compile, which is
bmad-build-auto's step 01. So the honest matrix is:

| Layer | Instrument | `factory spin` | `factory dispatch` / build-auto |
|---|---|---|---|
| output | caveman | yes | yes |
| structure-graph | codegraph | yes | yes |
| wire | headroom | **yes** (Story 33.3 — bmad-loop profile overlay) | yes |
| derived-context | cocoindex | **no** | yes |
| planning-graph | graphifyy | **no** | yes |

Wire compression now acts on both engines when the configured bmad-loop adapter
has a marshal harness ``[wrapper]`` and headroom resolves (Story 33.3). Layers 3
and 4 remain build-auto-only (epic-context compile is bmad-build-auto step 01).
Cost-sensitive derived/planning work still belongs on ``factory dispatch``; wire
is no longer spin-exclusive.

**Three ledger entries stop being incidental debt and start blocking a named
outcome**, which is what should promote them out of the ledger and into stories:

- `DW-FU-28-2` — spin is never wrapped; the fix shape is a loop-home
  launcher shim, and the entry already names the seam (`bmad-loop`'s
  `adapters/profile.py` exposes `binary` / `launch_args` / `env`, and
  `.bmad-loop/profiles/*.toml` is an overlay marshal already writes).
- `DW-FU-28-2-3` — `cli/dispatch.py` folds `read_repo_policy_defaults()`;
  `cli/spin.py` does not. A repo-wide `[context]` block would act on one engine
  and vanish silently on the other. Until that is fixed, **declare the block in
  the per-project `marshal-policy.toml`**, which both engines read.
- `DW-FU-28-2-2` — `headroom wrap` defaults to proxy port 8787 and attaches to
  a running proxy instead of starting a second, so two concurrent wrapped
  dispatches share the first launcher's CCR store. The station-in-flight guard
  makes this rare per station and does nothing for fleet-wide parallel
  dispatch, which is precisely the scale case.

**And CAP-7 could not measure it even if it were on (found 2026-09-09, later).** The five
per-layer savings getters in `adapters/harness_bmadloop.py:1875-1898` — `_get_caveman_savings`
(Layer 0), `_get_headroom_savings`, `_get_codegraph_stats`, `_get_cocoindex_stats`,
`_get_graphifyy_savings` — are stubs that
`return None` with the comment "would integrate with actual … stats when available". So the
supervisor journals a savings block whose every field is null, `marshal status` renders nothing,
and the benchmark's per-layer rows (`token_economy_benchmark.py`) have no source to read. Scribe's
side of the Layer-4 seam is real (`extras/graphify.py` writes through the `GraphStore` port;
`compile.py:736-764` flags stale nodes); the read side is five `None`s. Epic 33's Track / CAP-7
story must fill these before the on-leg benchmark means anything.

**What the enablement actually costs.** Stages 0–2 are configuration, not code:
record the off-leg on the pinned story (`1-1-marshal-conformance-smoke`),
declare the block, run `marshal seed kit` (idempotent, never fails a run), then
record the on-leg and `marshal benchmark compare`. Its equivalence gate voids
the comparison when the on-leg does not match the off-leg's verdict, gate
results and reviewer engagement — a void is the answer, not a failed test.
Ceiling recalibration (§ *What Marshal itself must grow*, item 5: "50M weighted
was sized for an uncompressed world") is downstream of that artifact and of
nothing else.

**The guard this Dream needs, learned from its sibling.**
[`adaptive-model-tiering.md`](adaptive-model-tiering.md) is the same pathology
on the other cost lever — its title is literally "FR-51's model tiering is fully
wired and never turned on" — and it carries `status: realized` while its own
README row records that no story declares a `difficulty:` and no project
populates a real tier map. It was marked realized as chain bookkeeping when the
code landed, not when the saving arrived. **This Dream is not `realized` when
its next epic closes. It is `realized` when a benchmark artifact reports a
measured saving on a real story.** Nothing else counts.

Landing: `bmad-correct-course` on `spec-marshal-token-economy` (`ready`, so it
takes the correction) mints marshal **Epic 33** — Epic 32 is the highest today,
30 and 31 sit in backlog — carrying the enablement sequence plus the three
entries above. Same shape as the 2026-09-02 red-team correction that minted
steward Epic 40. No new Dream: this chain already asked both questions.

## Fold (2026-09-16) — the token-savings Dreams come home

Operator-ruled consolidation: every Dream whose center is the cost of an
iteration folds into this one, so there is **one starting point** for the
whitepapers, the analysis, and the continuity. The fold line (operator,
2026-09-16): **same owner + same center + same lifecycle** — what rides
this Dream but is not inside it is named in § *Seams* below. The five
folded files stay in place as `archived` pointers so kinship links and
Spec `owner-dream` links keep resolving; **their Specs stay live and
remain the contracts** — archiving the Dream tier never retires the chain
below it.

### Folded — the session path (from `token-economy-claude-session-path`, `dreamt`)

The seed: the factory already knows how to make an iteration cheap, but
the session that costs money never uses the kit — interactive Claude pays
the always-on doc tax and every station's policy prefers Cursor, which
cannot take the wire wrap (28.29). The Dream asked for a **session path**,
not a second compressor. Seeded 2026-09-16 and put through a deep
analysis + adversarial review the same day; the full decision record is
the Spec's ten-entry memlog. The load-bearing conclusions:

- **Token savings is not one currency.** Claude meters billed tokens
  (with prompt-cache discounts); Cursor meters subscription quota;
  Copilot premium requests; Gemini rate limits; Devin ACUs. A layer that
  helps one currency can be irrelevant to another — every saving is
  reported in its harness's own currency, never a blended number.
- **The five layers are two economies.** The shared substrate (codegraph,
  cocoindex distills, planning graph, team memory) amortizes
  understanding *once* and serves every harness — **primary**. The
  per-harness wire (headroom, caveman) is capability-bound residue —
  secondary. The biggest gap is sharing cache, knowledge, and memory
  across every agent, harness, and model (operator, 2026-09-16).
- **The substrate's four gaps:** it does not *travel* (cloud agents get
  a bare clone — no bootstrap path); *write-back* is harness-fragmented
  (`scribe capture` is the neutral ritual, habitual in none); the only
  portable cache is a canonical digest-pinned context bundle; *freshness*
  is the trust boundary (Scribe owns it). Centralization caveat: shared
  knowledge centralizes error — provenance, the freshness SLA, and
  capture hygiene are the mitigations.
- **The three open questions answered:** dispatch is the *measured* path,
  interactive a documented convenience path on the same instruments;
  repo-default `[context]` with wire as a capability-aware `"auto"`
  (resolves against the harness profile's declared `[wrapper]`; per-
  station only as force-override); thinning `CLAUDE.md`/`AGENTS.md`
  deferred to a later Dream.
- **The multi-harness matrix:** claude = full kit; copilot = full kit
  once one `[wrapper]` story lands (headroom ships `wrap copilot`);
  cursor = harness-agnostic layers only — intended economics (cursor-first
  dispatch *is* the spend avoidance), not a gap; gemini/devin resolve by
  the same `auto` rule. Correction recorded: the output layer is
  multi-harness (caveman ships 21 targets).
- **The sharpest open risk:** the prompt-cache collision — a wire
  compressor rewriting prefixes unstably can cost more in lost cache
  discounts than it saves. Claude wire savings stay *unverified* until
  per-layer benchmark legs with cache-hit rates exist.

Status at fold: `dreamt`; Spec `draft`, re-derive repoints its
owner-dream here and mints the front-door CAP, the silent-saves CAP
(tri-state, journal taxonomy, per-currency rollup, persistence advisory),
the copilot `[wrapper]` story, the substrate CAP (bootstrap, write-back
ritual, canonical bundle, freshness SLA), and per-layer benchmark legs.

### Folded — adaptive model tiering (from `adaptive-model-tiering`, `realized`)

FR-51's difficulty→model chain (Story 6.1) shipped complete and was never
fed — the Dream that taught this one its realized-guard. Corrected
2026-09-09: CAP-1 *is* fed (57 story specs across six stations declare
`difficulty:`; two stations carry real `model_tier_map` tables; two live
dispatches resolved tiered models). The live gap: six of eight stations
have no tier map and journal `"model": null`, and CAP-2's retry-triggered
floor-raise is unreachable on the dispatch engine — both halves are
Story 33.6. Status at fold: `realized` (2026-08-14 chain bookkeeping;
facts corrected 2026-09-09).

### Folded — the Cursor-native tier map (from `cursor-native-tier-map`, `specified`)

The four-verb campaign runs in Cursor, so `model_tier_map` must tell the
truth about that plane: easy/medium/heavy name Cursor-native models on
the Ultra pool in the explicit `{ harness, model }` form, so a Cursor
string never lands on `claude --model` again. Story 33.15 remaps all
eight stations. Unattended drain stays off until the wire question is
separately proven. Status at fold: `specified` (Spec
`spec-cursor-native-tier-map`).

### Folded — tier routing fails safe (from `dispatch-tier-routing-fails-safe`, `realized`)

The 2026-09-12 incident: a bare-string tier entry (`composer-2.5-fast`,
Cursor-only, all eight stations) resolved to no harness, so the base
claude adapter launched with a Cursor model string and crashed instantly
— zero tokens, reported only as "deferred." Realized the same day:
`render_policy_toml` cross-checks each tier-mapped stage's model against
the declared cost catalog (`provider_declaring_model`) and skips a
cross-provider mismatch; `resolve_stage_candidate` no longer fabricates
an answer; dispatch's own path carries the identical guard
(`MRS-DISP-043`); all eight stations reverted to the sonnet/opus
baseline. The standing rule: a cost-tier override exists only once a
second harness is verified live, in explicit `{harness, model}` form,
rolled out one station at a time.

### Folded — interactive routing (from `bmad-cursor-interactive-routing`, `specified`)

BMAD from inside Cursor's own chat, not just headless dispatch. The
CAP-1 probe **passed** 2026-09-15 (Cursor Agent chat invoked the Task
tool; context-free subagents work in-turn). CAP-2 is committed:
mechanical `.mdc` generation from the `SKILL.md` files as a maintained
pixi task plus a drift detector — never a hand-maintained fork. CAP-3b
remains the residual HALT on a no-Task surface. Dispatch home: marshal
Epic 45. Status at fold: `specified` until that epic ships.

## Seams this Dream rides (not inside, and why)

The fold line is center, not dependency — fold-by-dependency has no
stopping rule (33.5 would pull in `risk-tiered-review-depth`, 33.8
`marshal-parallel-dispatch-fanout`, the Hub track `intelligence-hub`,
and the closure is half the marshal project). These seams are named so
the boundary never has to be re-litigated:

- [[run-state-one-publisher]] — the publishing seam this Dream's savings
  telemetry (CAP-7 / Story 33.4) rides. Same owner, different center:
  it publishes *all* run state, not savings; it is the dream-first
  ruling's exemplar with its own `ready` Spec.
- [[pixi-candidate-currency]] — the five instruments' pin home.
  doctor-owned, `realized`, a perpetual currency practice — the wrong
  lifecycle to import into a Dream whose realized-guard is a measured
  saving.
- The Scribe substrate — [[scribe-knowledge-layers]],
  [[scribe-recall-modes]], [[scribe-planning-pointers]],
  [[scribe-graphify-nightly-currency]],
  [[scribe-code-navigation-owner]] — the knowledge layers this Dream's
  substrate-primary economy *is*. scribe-owned by charter: *Marshal
  consumes it, Scribe owns it* (§ Guardrails' ownership seam).
- [[pyforge-marshal]] (the station) · [[adaptive-model-tiering]]'s
  sibling lesson already cited above · [[risk-tiered-review-depth]]
  (review depth scheduling) · [[durable-runs]] ·
  [[marshal-parallel-dispatch-fanout]] · [[intelligence-hub]].

## Realization log

- **2026-09-16 (consolidation)** — Operator-ruled Dream fold: the five
  token-savings Dreams (`token-economy-claude-session-path`,
  `adaptive-model-tiering`, `cursor-native-tier-map`,
  `dispatch-tier-routing-fails-safe`, `bmad-cursor-interactive-routing`)
  fold into this Dream as the single starting point for the token-savings
  chain — same owner, same center, same lifecycle. Their files stay as
  `archived` pointers; their Specs stay live and remain the contracts.
  Exclusions named in § *Seams this Dream rides*. No status change: this
  Dream stays `specified` until a benchmark artifact reports a measured
  saving on a real story — the guard below stands, now for the whole
  folded family.
- **2026-08-30** — Seeded already `specified` (`da458df364`): `spec-marshal-token-economy` `ready`,
  decomposed as marshal Epic 28 (28.1–28.9, backlog). Same-day addendum — the price sheet becomes an
  instrument (CAP-11/CAP-12 → Stories 28.10/28.11).
- **2026-08-31** — Addendum: Layer 4 retrieval is only as good as the graph's freshness — landed as
  CAP-13; the live dispatch-ordering incident added CAP-14..CAP-17 (Stories 28.12–28.15) through
  [`marshal-dependency-aware-dispatch.md`](marshal-dependency-aware-dispatch.md).
- **2026-09-01** — Dispatch-autonomy hotfixes + Epic 28 artifact catch-up (`90c5a28bd6`).
- **2026-09-09** — Code-level verification against `main`: Epic 28's machinery is real
  and complete, and every layer is off — no `[context]` block is declared in any policy,
  repo, project or rendered. Both of § *Gates and open questions*' gates closed against
  the evidence: the measurement-first gate was bypassed (no benchmark artifact exists),
  and the cross-engine question is answered in the negative (the block renders
  identically on both adapters, but only dispatch/build-auto can act on the wire,
  derived-context and planning-graph layers). Recorded as the addendum above, with the
  `realized` guard learned from [`adaptive-model-tiering.md`](adaptive-model-tiering.md).
  Next: `bmad-correct-course` mints marshal Epic 33.
- **2026-09-09 (later)** — § *What is real* glossed as the dated baseline (kept as record). The
  Unifying Strategy currency review
  (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/currency-review-pyforge-unifying-strategy-2026-09-09.md`)
  found the same built-but-inert shape on Unifying **CAP-17** (run state as a service): marshal has
  zero imports of `django_pyforge` and `marshal/cli/init.py` still reads `~/.bmad-loops`, so the
  supervisor never receives a bmad-loop run. The Hub's Track (`hub:CAP-3` on
  `spec-intelligence-hub` — *not* this Dream's CAP-3, which is caveman output-compression
  seeding) and this Dream's savings telemetry (CAP-7) are the same publishing seam; Epic 33
  should land them together, not as two writers. *(Citation corrected 2026-09-09 — the first
  draft of this line collapsed two Specs' CAP-3.)*

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — **Epic 33 minted (10 stories)**
  by `_bmad-output/projects/pyforge-marshal/planning-artifacts/change-history/sprint-change-proposal-2026-09-09-token-economy-enablement.md`.
  Status stays **`specified`** and does not move until Story 33.1's benchmark artifact reports a
  measured saving on a real story — this Dream's own guard, learned from
  [`adaptive-model-tiering.md`](adaptive-model-tiering.md).
  The epic in order: **33.1** measurement first — the on/off benchmark artifact with CAP-7's four
  savings getters made real (`adapters/harness_bmadloop.py:1880-1898` returns `None` four times
  today); **33.2** enable the layers on `factory dispatch` (`resolve_wire_wrap` folded); **33.3**
  enable on `factory spin` (fold the repo defaults `cli/spin.py` never reads, `DW-FU-28-2-3`);
  **33.4** **CAP-18 — one publisher**: run state *and* savings telemetry to
  `django_pyforge.supervisor`, so `cli/init.py:331` and doctor's `sources/marshal.py:544` stop
  reading `~/.bmad-loops` (this is Unifying **CAP-17** — qualified, because *this* Dream's CAP-17 is
  `scope_violation_mode` — and the Hub's Track is **`hub:CAP-3`**; steward Story 49.8 is ledger
  `blocked` on 33.4); **33.5** risk-tiered review wiring; **33.6** adaptive tiering fed on all eight
  stations plus the floor-raise on dispatch; **33.7** the two Epic-20 watchdogs re-pointed off
  `~/.bmad-loops`; **33.8** the first live fan-out wave with a real `dispatch.max_parallel` key;
  **33.9** `verify_scope` at `factory dispatch`; **33.10** the derived CFE pin.
  33.2 and everything after it depend on 33.1 — the measurement-first gate this Dream's § Gates named
  and Epic 28 bypassed. Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.
- **2026-09-09 (Story 33.3 shipped)** — Ruling: the loop-home launcher shim **succeeds** through
  bmad-loop's ``adapters/profile.py`` seam. ``factory spin`` now folds
  ``read_repo_policy_defaults()`` (closing ``DW-FU-28-2-3``), and when the wire layer is enabled it
  writes a loop-home ``.bmad-loop/profiles/<adapter>.toml`` overlay that points ``binary`` at
  headroom with ``launch_args = ["wrap", "<cli>", ...]`` (closing ``DW-FU-28-2`` for the claude-class
  adapters that declare a marshal ``[wrapper]``). Spin is **not** declared a two-layer-only engine:
  wire acts on spin the same way it acts on dispatch; derived-context and planning-graph remain
  dispatch/build-auto-only. Cost-sensitive drain for those two layers still belongs on
  ``factory dispatch``.
