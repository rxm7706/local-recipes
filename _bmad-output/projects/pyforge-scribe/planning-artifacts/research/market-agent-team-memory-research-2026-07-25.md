---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - docs/dreams/pyforge-scribe.md
  - docs/dreams/team-memory.md
  - docs/dreams/sentinel.md
  - docs/dreams/ecosystem-crew.md
  - docs/specs/claude-team-memory.md
workflowType: 'research'
lastStep: 6
research_type: 'market'
research_topic: 'Agent/team knowledge-memory systems — persistent shared memory + compiled knowledge graphs for AI coding agents and teams'
research_goals: 'Place Scribe (dist pyforge-scribe / CLI scribe) against the 4 nearest analogues, identify exploitable market gaps for a git-native, local-first, capture-as-you-work competitor'
user_name: 'Rxm7706'
date: '2026-07-25'
web_research_enabled: true
source_verification: true
mode: 'headless-express — run via a single autonomous pass, no interactive Q&A; ambiguities recorded as inline Assumption notes rather than paused on'
---

# Research Report: Market Research — Agent/Team Knowledge-Memory Systems

**Date:** 2026-07-25
**Author:** Rxm7706
**Research Type:** Market

---

## Research Overview

**Assumption:** this report was run headless/express (per the pyforge-scribe planning-chain task) — the topic, goals, and scope below were supplied directly rather than elicited turn-by-turn; the workflow's `research_type = market`, `research_topic`, and `research_goals` fields are pre-set from that brief rather than a live Q&A.

**Why this research exists:** Scribe is being scoped as a real installable package (dist `pyforge-scribe`, module `pyforge.scribe`, CLI `scribe`) that (1) captures decisions/ADRs/runbooks as they happen (`scribe capture`), (2) compiles a knowledge graph nightly from the tools a team already uses (`scribe graph compile --nightly`), and (3) answers from that memory so every session starts already knowing what the team knows (`scribe recall`). Before writing the Project Brief / PRD, this report places Scribe against the nearest commercial and open-source analogues to find real gaps rather than assumed ones.

**Method:** targeted web search (2026-07-25) across four analogue categories the brief specified — agent memory layer (Mem0), temporal knowledge graph for agent memory (Zep/Graphiti), self-hosted personal knowledge management (Khoj, with an Obsidian-plugin note), and enterprise knowledge search/graph (Glean) — plus one pass over the current academic literature on LLM-agent memory architectures to ground the graph-compilation design choice. Every factual claim below is cited inline; broader context is drawn from the four Dream documents and the legacy `claude-team-memory` spec, which are source documents, not market evidence.

**Scope discipline:** this is a positioning report, not an exhaustive industry study. It analyzes exactly the four analogues plus academic grounding, synthesizes the gap Scribe can occupy, and stops there — sized to ground one Project Brief, not a standalone market-sizing exercise.

---

## The Problem Space (from the Dream documents)

Three internal Dreams converge on the same diagnosis, which functions as this report's problem statement:

- **Sentinel** (the ancestor Dream, 2026-04-18/19): an engineer touches six tools in the first hour; the knowledge the team runs on — the *why* of code X, rejected tradeoffs, the 3am runbook — is scattered and lossy; AI without the graph hallucinates; knowledge-base products sell a better editor when the bottleneck is the round-trip. Thesis: "the graph is the product," compiled nightly from the tools the team already uses, not authored in a separate app.
- **Team memory** (adopted by Scribe): today's memory is *personal* — Claude Code's auto-memory writes to a per-machine, per-user path (`~/.claude/projects/<encoded-path>/memory/`), invisible to teammates and other agents. The only current promotion path is manual `CLAUDE.md` editing — friction-laden and easy to skip (motivating incident: a rule shipped to user-local memory *and* had to be hand-duplicated into `CLAUDE.md`).
- **Scribe** (this Dream): "what the team knows, every agent and every session knows" — decisions, rejected tradeoffs, and runbooks captured as they happen, curated so it stays true, compiled into a graph, answerable on demand.

This is a narrower, more concrete problem than "enterprise knowledge management" — it is specifically about **coding-agent and developer-team memory**, git-native, inside the repo the team already works in.

---

## Competitive Landscape

### Key Market Players

**1. Mem0 — the agent memory layer (SaaS-first, open-core)**

Mem0 is an intelligent memory layer for AI agents and LLM applications: it intercepts conversations, uses an LLM to extract what's worth remembering, stores it in a vector database (graph database on Pro+), and retrieves relevant memories at the start of each new session — explicitly framed as solving agent statelessness _(Source: https://mem0.ai/blog/state-of-ai-agent-memory-2026)_. The core `mem0ai` package is Apache-2.0 and has 58.4K+ GitHub stars as of June 2026; the hosted platform layers managed infra, analytics, and graph memory on top _(Source: https://theaiagentindex.com/agents/mem0)_. Pricing is SaaS-tiered: Free (10K memories), Starter $19/mo, Growth $79/mo, Pro $249/mo (capped at 500K memory adds), Enterprise custom _(Source: https://theaiagentindex.com/agents/mem0)_. It is backed by YC plus a $24M Series A (Oct 2025) and is the default memory provider for AWS's Agent SDK _(Source: https://rywalker.com/research/mem0)_.

- **Target user:** application developers bolting persistent memory onto a production LLM agent — not specifically a coding-team knowledge problem.
- **Core mechanism:** LLM-driven fact extraction from conversation turns → vector (or graph) store → similarity retrieval at session start. Memory is a byproduct of chat, not an authored artifact.
- **Deployment posture:** open-core SDK usable self-hosted, but the flagship product and the roadmap (graph memory, analytics) are the hosted SaaS; "single-vendor, VC-backed open-core" carries standard relicensing risk for anyone depending on the free tier long-term _(Source: https://theaiagentindex.com/agents/mem0)_.

**2. Zep / Graphiti — temporal knowledge graph for agent memory (enterprise SaaS + OSS engine)**

Zep is agent memory "at enterprise scale," built on Graphiti, its open-source temporally-aware knowledge-graph engine _(Source: https://blog.getzep.com/)_. Graphiti's bi-temporal model tracks both when a fact was true and when it was ingested — every edge carries validity intervals, so superseded facts are invalidated rather than deleted, preserving history without recomputation _(Source: https://arxiv.org/abs/2501.13956)_. Retrieval combines cosine similarity, BM25, and graph traversal with reranking; memory is organized in three tiers — episodic (raw messages), semantic (entities/facts), and community summaries _(Source: https://neo4j.com/blog/developer/graphiti-knowledge-graph-memory/)_. Graphiti (the open-source engine) has 20,000+ GitHub stars; Zep (the commercial "Context Lake" service) reported 30x usage growth in two weeks during a recent enterprise adoption wave _(Source: https://neo4j.com/blog/developer/graphiti-knowledge-graph-memory/)_.

- **Target user:** enterprises running many agents against a shared, governed memory service — a platform team's infrastructure choice, not a per-repo developer tool.
- **Core mechanism:** ingests conversational + structured business data into a temporal graph (stored on Neo4j) with real-time incremental entity/relationship resolution — this is the closest architectural analogue to "compile a knowledge graph from what happened," and its bi-temporal fact-invalidation model is directly relevant to Scribe's "curate: dedup, supersede, and link" goal.
- **Deployment posture:** Graphiti itself is self-hostable OSS (Neo4j-backed); Zep the product is a managed enterprise service. No git-native or air-gap-first framing — it is a database-backed service, not a repo-native compile step.

**3. Khoj — self-hosted personal knowledge management (open-source, AGPL-3.0)**

Khoj is an open-source AI personal assistant (AGPL-3.0, 34K+ GitHub stars, YC W24) that indexes a user's own documents (PDF, Markdown, Word, Notion, and more) into a vector store (pgvector) for semantic search and chat, with pluggable LLM backends (local via Ollama or cloud) _(Source: https://hoangyell.com/khoj-explained/)_. It is explicitly "stateful and knowledge-indexed" as its differentiator from stateless chat tools, integrates into Obsidian as a vault-wide plugin, and self-hosts via `pip install khoj` or `docker-compose up` — though a full deployment is four services (app server, Postgres+pgvector, a code-execution sandbox, and SearxNG for web search) _(Source: https://railway.com/deploy/khoj; https://community.obsidian.md/plugins/khoj)_.

- **Target user:** an individual knowledge worker with a personal note vault (the Obsidian-class PKM pattern) — single-operator by default; "team research assistant" is listed as a use case but requires multi-user auth bolted on, not a first-class team-graph model.
- **Core mechanism:** semantic search index over documents the user already wrote (closer to RAG-over-notes than a compiled relationship graph) — no ADR/decision-specific capture surface, no temporal fact-supersession model.
- **Deployment posture:** the closest analogue to "local-first" among the four, and the only one with a real self-hosted OSS deployment story by default — but it is a 4-service application stack (Postgres, sandbox, search proxy) layered *on top of* the repo, not a lightweight compile step that reads tools the team already runs.

**4. Glean — enterprise knowledge search + permissions-aware graph (SaaS, sales-led)**

Glean builds a knowledge graph mapping relationships between people, content, and interactions across an organization's connected SaaS tools, and uses it to personalize search/AI answers by role, project, and collaborators _(Source: https://futurumgroup.com/insights/glean-doubles-arr-to-200m-can-its-knowledge-graph-beat-copilot/)_. It doubled ARR to $200M in nine months (2026), reaching a $7.2B valuation, and has expanded from search into an "Agentic Engine" and a governance SKU ("Glean Protect Plus") _(Source: https://futurumgroup.com/insights/glean-doubles-arr-to-200m-can-its-knowledge-graph-beat-copilot/)_. Pricing is enterprise quote-based, converging around $40–75+/user/month base licensing with a ~100-seat minimum (~$60K/year ACV), and total first-year cost commonly $300K–$1M+ once integration and the AI add-on tier are included _(Source: https://www.vendr.com/marketplace/glean; https://www.gosearch.ai/faqs/glean-enterprise-search-pricing-explained-costs-tiers-hidden-fees-gosearch-comparison/)_.

- **Target user:** large enterprises (100+ seats) buying a company-wide search/answer layer across many SaaS silos (Slack, Confluence, Drive, Jira, etc.) — an IT/knowledge-management procurement decision, several org-sizes above a single engineering team or repo.
- **Core mechanism:** connector-based ingestion across many external SaaS surfaces into a permissions-aware graph, ranked by an org chart / activity model — breadth over depth; not repo-native, not capture-as-you-decide.
- **Deployment posture:** pure SaaS, no air-gap or local-first story found in the sources reviewed; economics and integration surface are built for enterprise IT, not a single git repo.

### Academic Grounding — memory architectures for LLM agents (2025–2026)

The current literature (survey: "From Storage to Experience: A Survey on the Evolution of LLM Agent Memory Mechanisms," arXiv:2605.06716, which itself cites the Zep/Graphiti paper as foundational) frames memory design as an architectural decision set — what to store, when to retrieve, how to update, what to discard — rather than a solved problem _(Source: https://arxiv.org/pdf/2605.06716)_. Graph-based memory (knowledge graphs, temporal graphs, hierarchical trees, hybrid graphs) is identified as the 2025–2026 frontier specifically because it models relational dependencies better than flat vector stores _(Source: https://lin-guanguo.github.io/llm-memory-research/memory.literature-scan/)_. Standard benchmarks (LoCoMo, LongMemEval) evaluate long-conversation recall accuracy, which is a different axis than what Scribe needs to prove (recall of *decisions*, not chat turns) — flagged as an open question below rather than assumed solved.

_Source: [Zep: A Temporal Knowledge Graph Architecture for Agent Memory (arXiv:2501.13956)](https://arxiv.org/abs/2501.13956)_
_Source: [From Storage to Experience: A Survey on the Evolution of LLM Agent Memory Mechanisms (arXiv:2605.06716)](https://arxiv.org/pdf/2605.06716)_
_Source: [2026 Memory Literature Scan](https://lin-guanguo.github.io/llm-memory-research/memory.literature-scan/)_

### Market Share / Positioning Map

No independent market-share data exists for this category (too new, too fragmented) — the sources above are traction proxies (GitHub stars, ARR, funding), not share figures. Positioned qualitatively:

| Player | Unit of memory | Compile trigger | Deployment | Team-native? | Repo-native? |
|---|---|---|---|---|---|
| Mem0 | extracted conversational facts | per-turn (real-time) | SaaS-first, open-core SDK | No (per-agent, per-user) | No |
| Zep/Graphiti | temporal graph facts + entities | real-time incremental | Managed service (Graphiti OSS engine, Neo4j-backed) | Yes (enterprise, multi-agent) | No |
| Khoj | document embeddings | on-index (batch) | Self-hosted OSS (4-service stack) or SaaS | No (personal vault) | No |
| Glean | cross-SaaS connector graph | continuous crawl | SaaS only | Yes (org-wide) | No |
| **Scribe (proposed)** | decisions/ADRs/runbooks + compiled graph | authored capture + `--nightly` compile | **git-native, local-first, air-gap-capable** | **Yes (team, in-repo)** | **Yes** |

**Assumption:** the "Repo-native" column is the report's own classification, not a claim any vendor makes about itself — it is the axis this report concludes is unoccupied (see Market Differentiation below).

### Strengths and Weaknesses

- **Mem0** — Strength: fastest bolt-on for an existing agent, strong funding/traction, AWS distribution. Weakness: memory is conversation-derived, not authored; no team/repo model; open-core relicensing risk for a long-lived internal dependency.
- **Zep/Graphiti** — Strength: the strongest *architectural* precedent for Scribe's graph-compile step (bi-temporal fact supersession is exactly the "curate: dedup, supersede, link" behavior Scribe's Dream calls for); Graphiti itself is genuinely self-hostable OSS. Weakness: requires standing up Neo4j + a service; not designed to compile *from the tools a team already uses* (git, ADRs, retros) — it ingests conversation/business-data streams, not repo artifacts; no air-gap-first packaging story in the sources reviewed.
- **Khoj** — Strength: closest to "local-first," real self-hosted OSS deployment, Obsidian integration shows the graph-of-notes pattern works for a knowledge worker. Weakness: single-operator by default, no decision/ADR-specific capture surface, four-service deployment footprint is heavy for "a package in a pixi workspace," and its "memory" is a semantic index over pre-existing docs, not a compiled temporal graph with supersession.
- **Glean** — Strength: proves the enterprise willingness-to-pay for a knowledge graph over connected tools exists. Weakness: SaaS-only, enterprise-procurement pricing and seat minimums make it irrelevant to a single-repo, air-gap-capable, engineering-team tool; no evidence of local/offline deployment.

### Market Differentiation — the gap Scribe can occupy

Cross-referencing the four analogues against Scribe's three stated capabilities (`scribe capture`, `scribe graph compile --nightly`, `scribe recall`) surfaces three simultaneous gaps, none of which any single analogue occupies:

1. **Git-native, local-first, air-gap-capable.** None of the four have an air-gap-first deployment story: Mem0 and Glean are SaaS-first; Zep is a managed service (Graphiti the engine is self-hostable but needs Neo4j); Khoj self-hosts but as a 4-service application, not a package that lives inside the repo's existing pixi/CI workflow. A CLI that ships as an ordinary Python package (`pyforge-scribe`) with no required external service is architecturally unlike all four.
2. **Compiles from the tools the team already uses, not a separate ingestion app.** Mem0 ingests conversation turns; Zep ingests conversation + business-data streams into its own database; Khoj indexes documents the user points it at; Glean crawls connected SaaS via connectors. Scribe's Dream is explicit that the graph compiles *nightly from the tools the team already uses* — i.e., the repo's own git history, ADRs, retros, memlogs — which is a narrower, repo-scoped ingestion model none of the four implement as their core loop.
3. **Capture-as-you-decide, not passive log ingestion.** `scribe capture` is an authored action ("ADR-005b: in-house gateway replaces LiteLLM") at decision time, distinct from Mem0/Zep's conversation-log extraction or Khoj/Glean's document/connector indexing. This is closer to the Dream's own "memlog discipline" (`bmad-spec`'s append-only `.memlog.md`) than to any of the four competitors' capture model — it is a proprietary-to-this-ecosystem pattern already proven at small scale (30+ personal auto-memory entries, MEMORY.md indexing) rather than a market-validated one, which is itself a risk to flag (see Recommendations).

### Competitive Threats

- **Mem0 or Zep adding a "repo mode."** Both are well-funded and iterating fast (Mem0's 2026 token-optimization playbook, Zep's enterprise Context Lake); either could ship a git-aware ingestion connector, eroding gap #2 above. Scribe's durable moat would then be gaps #1 (air-gap) and #3 (authored capture), not the graph-compile mechanism alone.
- **Claude Code (or a competing agent harness) shipping first-class team-shared memory natively** — the legacy `claude-team-memory` spec explicitly names this as a ruled-out alternative because it is not yet shipped (open feature request `anthropics/claude-code#38536`); if Anthropic ships this, Scribe's `.claude/memory/` layer specifically (not the broader graph-compile capability) would need to fold into or defer to the native surface.
- **Khoj-class PKM tools adding team/multi-repo modes.** Khoj already lists "team research assistant" as a use case; if it matures a graph-of-decisions model with git awareness, it becomes a closer competitor than it is today.

### Opportunities

- **Position Scribe explicitly as "the git-native alternative to Zep/Graphiti's architecture"** — borrow the bi-temporal fact-supersession pattern (proven, cited, arXiv-published) without borrowing the Neo4j-and-managed-service deployment model.
- **The existing personal auto-memory pipeline is a working prototype at small scale** (30+ entries, MEMORY.md indexing, promotion discipline already documented in `docs/specs/claude-team-memory.md`) — Scribe's differentiation is proven internally before it needs to prove itself externally, which de-risks the PRD's core mechanism.
- **Air-gap posture is a real enterprise buying trigger** (Glean's pricing data shows enterprises will pay $300K–$1M+ for a knowledge graph — but only the ones who can tolerate SaaS; regulated/air-gapped shops are explicitly locked out of all four analogues today per the sources found).

---

## Customer Pain Points

*(Condensed per headless scope; full persona-interview-style elicitation not run — the Dream documents and the legacy spec's "motivating incident" serve as the primary voice-of-customer evidence available.)*

- **Knowledge trapped per-machine, per-user** — Claude Code's auto-memory is explicitly per-encoded-path, invisible across teammates; the only escape hatch today is manual `CLAUDE.md` editing (source: `docs/specs/claude-team-memory.md` Background, motivating incident commit `d43899c1cb`).
- **The graph exists conceptually but nobody compiles it** — Sentinel's diagnosis, unchanged since 2026-04: "the graph is there; nobody writes it down."
- **Six tools in the first hour** — a new contributor (human or agent) has no single place to ask "why did we do X" and get an answer grounded in the team's actual decision history, as opposed to a generic LLM guess.

## Customer Behavior & Decisions

- Today's workaround behavior is **manual and duplicative**: the same rule gets written once to user-local memory and a second time, by hand, into `CLAUDE.md` — the friction this report's problem statement is built on.
- Adoption of the *personal* auto-memory pattern (30+ entries) shows the underlying habit (capture a correction as a memory entry) is already sticky for a single operator; the open question is whether that habit generalizes to a team without an explicit promotion tool (this is exactly what the legacy `claude-team-memory` spec's `team-memory` skill was scoped to solve, and its scope migrates into this PRD).

---

## Strategic Synthesis & Recommendations

1. **Ground the PRD's differentiation in the three-gap framing above** (git-native/air-gap, compile-from-real-tools, capture-as-you-decide) rather than a generic "better memory" pitch — this is the concrete, citable positioning versus Mem0/Zep/Khoj/Glean.
2. **Borrow Graphiti's bi-temporal fact-supersession model conceptually** for the graph-compile design (architecture-phase input): facts get invalidated, not deleted, when superseded — directly matches the Scribe Dream's "curate: dedup, supersede, link" goal and is the one piece of prior art worth explicitly architecting toward.
3. **Do not over-claim recall-accuracy parity with Mem0/Zep at this stage** — their benchmark claims (LoCoMo, LongMemEval) measure conversational recall, a different task than decision/ADR recall; flag this as an open question for the PRD rather than asserting Scribe will "outperform" them on a benchmark it hasn't been evaluated against.
4. **The legacy `claude-team-memory` spec's 10 stories are a validated starting scope**, not something to re-derive from zero — its Wave A/B/C structure, team-relevance test, and pointer-stub convention should fold directly into the PRD's functional requirements (see PRD's migration mapping).
5. **Watch the "native team memory in Claude Code" threat** (`anthropics/claude-code#38536`) as an open question through the PRD and architecture phases — it does not block Scribe today (unshipped) but should inform how tightly Scribe couples to the current `.claude/memory/` file convention versus a more portable storage format.

---

## Open Questions Carried Forward

- Does Scribe need its own recall-accuracy benchmark (LoCoMo/LongMemEval-style) before claiming parity with Mem0/Zep, or is "grounded, cited, git-diffable" a sufficient differentiator without a benchmark claim? (Recommendation #3)
- If `anthropics/claude-code#38536` ships during Scribe's build, does the `.claude/memory/` file layer get absorbed into the native surface, or does Scribe's value shift entirely to the graph-compile + recall layer? (Recommendation #5)
- Is there a real self-hosted deployment precedent worth studying further (Graphiti's Neo4j-backed self-host mode) before the architecture phase locks in a storage engine, or does "git-native flat files" fully replace the need for a graph database? (Architecture-phase question, not resolved here.)

---

## Sources

- [AI Agent Memory 2026: Progress Benchmark Report Evaluations (Mem0)](https://mem0.ai/blog/state-of-ai-agent-memory-2026)
- [Mem0 Review (2026): Pricing, Pros & Alternatives](https://theaiagentindex.com/agents/mem0)
- [Mem0 | Ry Walker Research](https://rywalker.com/research/mem0)
- [Zep: A Temporal Knowledge Graph Architecture for Agent Memory (arXiv:2501.13956)](https://arxiv.org/abs/2501.13956)
- [Graphiti: Knowledge graph memory for an agentic world (Neo4j)](https://neo4j.com/blog/developer/graphiti-knowledge-graph-memory/)
- [Zep — Agent memory at enterprise scale](https://blog.getzep.com/)
- [Khoj Explained — HoangYell](https://hoangyell.com/khoj-explained/)
- [Deploy Khoj | Open Source Personal AI Assistant (Railway)](https://railway.com/deploy/khoj)
- [Khoj — Obsidian Plugin](https://community.obsidian.md/plugins/khoj)
- [Glean Doubles ARR to $200M. Can Its Knowledge Graph Beat Copilot? (Futurum Group)](https://futurumgroup.com/insights/glean-doubles-arr-to-200m-can-its-knowledge-graph-beat-copilot/)
- [Glean Software Pricing & Plans 2026 (Vendr)](https://www.vendr.com/marketplace/glean)
- [Glean enterprise search pricing explained (GoSearch)](https://www.gosearch.ai/faqs/glean-enterprise-search-pricing-explained-costs-tiers-hidden-fees-gosearch-comparison/)
- [From Storage to Experience: A Survey on the Evolution of LLM Agent Memory Mechanisms (arXiv:2605.06716)](https://arxiv.org/pdf/2605.06716)
- [2026 Memory Literature Scan — LLM Agent Research](https://lin-guanguo.github.io/llm-memory-research/memory.literature-scan/)
- `docs/specs/claude-team-memory.md` (internal spec — motivating incident, ruled-out alternatives, 10-story scope)
- `docs/dreams/pyforge-scribe.md`, `docs/dreams/team-memory.md`, `docs/dreams/sentinel.md`, `docs/dreams/ecosystem-crew.md` § 7 (internal Dream documents — problem statement, not market evidence)
