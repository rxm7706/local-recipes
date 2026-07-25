---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - docs/dreams/pyforge-scribe.md
  - docs/dreams/sentinel.md
  - docs/intake/sentinel/README.md
  - docs/intake/gists/llm-powered-knowledge-bases-by-andrej-karpathy/LLM Powered Knowledge Bases.md
workflowType: 'research'
lastStep: 6
research_type: 'domain'
research_topic: 'Developer/team knowledge capture and graph-compilation domain — ADR discipline, local-first software architecture, embedded graph storage, and the air-gap/regulatory environment Scribe must ship into'
research_goals: 'Ground Scribe''s architecture-facing decisions (storage engine posture, capture format, air-gap positioning) in current domain practice and technical trends, distinct from the market-research report''s competitor analysis'
user_name: 'Rxm7706'
date: '2026-07-25'
web_research_enabled: true
source_verification: true
mode: 'headless-express — run via a single autonomous pass, no interactive Q&A; ambiguities recorded as inline Assumption notes rather than paused on'
---

# Research Report: Domain Research — Team Knowledge Capture & Graph Compilation

**Date:** 2026-07-25
**Author:** Rxm7706
**Research Type:** Domain

---

## Research Overview

**Assumption:** run headless/express, as a companion to the market-research report — that report placed Scribe against its four nearest product analogues (Mem0, Zep/Graphiti, Khoj, Glean); this report instead surveys the **domain practices and technical substrate** Scribe's architecture phase will need: how software teams already capture decisions (ADR discipline), the software-architecture movement Scribe's local-first posture belongs to, the state of the embedded-graph-storage technology it would compile into, and the regulatory environment that makes an air-gap posture a real, not aspirational, differentiator.

**Method:** targeted web search (2026-07-25) across four domain angles — decision-capture practice (ADRs), local-first software architecture, embedded graph database technology, and air-gapped/regulated AI deployment — cited inline throughout.

---

## Domain Analysis: Decision Capture as Existing Practice

Architecture Decision Records (ADRs) are the dominant lightweight practice for exactly the capture problem Scribe's Dream describes: a short document recording a single decision, its context, and consequences, explicitly *not* edited in place when the decision changes — instead a new ADR supersedes the old one and the two are linked, so "the chain of decisions is the value, not any single record" _(Source: https://adr.github.io/)_. This maps almost exactly onto Scribe's stated curation behavior ("dedup, supersede, and link") and validates that Scribe's `scribe capture --type decision` primitive is not a novel format invention — it is formalizing an already-standard practice.

**Where ADRs already live — and why that matters for Scribe's storage posture:** the dominant convention, per Martin Fowler and the current 2026 guides, is markdown files in the repo itself (`docs/adr/` or `docs/decisions/`), specifically *because* "ADRs live where engineers already work, version with the code, show up in pull request reviews, and can be diffed and linked like any other artifact" _(Source: 2026 ADR guide survey, multiple sources including https://www.catio.tech/blog/architecture-decision-record and https://www.john-pratt.com/architecture-decision-record)_. This is direct domain validation of Scribe's git-native posture: the practice Scribe formalizes is already git-native by convention, before any tooling exists.

**The known failure mode ADRs have today — Scribe's opening:** "ADRs often go stale because decisions don't stay in the file — they change in Slack, GitHub and Jira, and nobody updates the ADR" — described as the core problem newer tooling is trying to solve _(Source: 2026 ADR guide survey)_. This is the Sentinel Dream's diagnosis in domain-specific form ("knowledge is lossy; the graph is there; nobody writes it down") and directly motivates `scribe graph compile --nightly` reading multiple real tools rather than trusting a single static file to stay current.

**A new, 2026-specific motivation for ADR discipline — AI-agent readability:** "AI coding agents will refactor away reasoning they can't see [so] ADRs put that reasoning somewhere durable that both new hires and agents can read" _(Source: 2026 ADR guide survey)_. This reframes ADR/decision capture from a human-onboarding nicety into an **agent-context problem** — precisely Scribe's framing ("every agent and every session knows"). It is evidence the domain is independently arriving at Scribe's thesis.

**Emerging (SaaS) direction to note as a threat, not a template:** some 2026 tools are moving from static ADR files toward "a system of record for architecture decisions tied to the live system state... a queryable, drift-aware decision layer," letting teams ask the decision corpus questions in natural language grounded in what's actually running _(Source: 2026 ADR guide survey, e.g. https://docs.align.tech/blog/architecture-decision-records-complete-guide/)_. This is architecturally adjacent to `scribe recall`, but built as a hosted/live-system-coupled product — the same air-gap/SaaS gap identified in the market-research report reappears at the domain-tooling layer, not just among the four named competitors.

---

## Technical Trends

### Local-first software architecture — the movement Scribe belongs to

"Local-first" (coined by Ink & Switch's 2019 essay, still the reference framing in 2026) means the local copy is the primary source of truth and "the availability of another computer should never prevent you from working" — distinct from mere offline-first caching _(Source: https://wal.sh/research/local-first; https://rxdb.info/articles/local-first-future.html)_. Production examples cited include Linear, Obsidian, and Figma's offline mode. **Assumption:** Scribe is local-first in the *file/repo* sense (git as the source of truth, no required external service) rather than the *CRDT sync-engine* sense the 2026 local-first conference community is mostly focused on (Automerge, Yjs, Loro, ElectricSQL, PowerSync) — those tools solve concurrent multi-writer conflict resolution for live documents, which is a different problem than compiling a graph from artifacts that already resolve conflicts via git's own merge model. This distinction should be made explicit in the architecture phase so Scribe isn't mis-scoped as "needs a CRDT sync engine" when git itself already is the team's existing conflict-resolution layer.

Directly relevant adjacent trend: local AI models "crossed the line" for real coding work in early 2026 (Qwen3-Coder-Next, Llama 4 Scout, DeepSeek V3.2 class models), with a growing tool ecosystem (Cline, Continue, Aider, Tabby, Goose) built around private, offline, self-hosted operation _(Source: https://nimbalyst.com/blog/best-local-first-ai-coding-tools-2026/)_. This is evidence the surrounding tool ecosystem is already normalizing "no required cloud call" as a baseline expectation for dev-tooling in 2026, not a fringe position — Scribe's air-gap posture rides an existing current, not a lonely one.

_Source: [Local-First Software: Principles, Patterns, and Technologies](https://wal.sh/research/local-first)_
_Source: [Why Local-First Software Is the Future and its Limitations (RxDB)](https://rxdb.info/articles/local-first-future.html)_
_Source: [Best Local-First AI Coding Tools 2026 (Nimbalyst)](https://nimbalyst.com/blog/best-local-first-ai-coding-tools-2026/)_

### Embedded graph storage — a live technical-risk finding for the architecture phase

**Material finding, flagged for the architecture phase, not resolved here:** KuzuDB — the leading embedded (in-process, SQLite/DuckDB-style) graph database and the most natural "compile a local knowledge graph, no server required" storage engine — was **archived in October 2025 after its team was acquired by Apple**; open-source development stopped (no new features, fixes, or community support) _(Source: https://biggo.com/news/202510130126_KuzuDB-embedded-graph-database-archived)_. A community successor, **LadybugDB**, has emerged, explicitly positioned as "DuckDB for graphs... built for agentic AI in highly regulated industries," with a "graph lakehouse" design that interoperates with DuckDB/Arrow/Parquet rather than requiring data migration into a proprietary format _(Source: https://ladybugdb.com/; https://thedataquarry.com/blog/from-kuzu-to-ladybug/)_. Other alternatives surfaced in the same search (DuckPGQ as a graph-query extension on top of DuckDB itself, CozoDB, SurrealDB) are less mature or not embedded.

**Why this matters for Scribe specifically:** Scribe's Dream explicitly wants a nightly-compiled graph "from the tools the team already uses" with no external service (air-gap posture) — an embedded graph engine is the natural fit, but the one previously dominant option (KuzuDB) is now an orphaned dependency risk, one release-cycle after the fact. **Open question carried to architecture:** does Scribe adopt an embedded graph engine (LadybugDB, or plain DuckDB with a graph-shaped schema) for `scribe graph compile`, or does it stay at the flat-file/markdown-plus-index level (closer to the existing `.claude/memory/MEMORY.md` pattern) and defer a real graph engine until the flat-file model provably runs out of headroom? Either choice is defensible; the KuzuDB archival is a concrete reason not to default to "just use Kuzu" without checking current status first — which this research already did.

_Source: [KuzuDB, the Promising Embedded Graph Database, is Suddenly Archived](https://biggo.com/news/202510130126_KuzuDB-embedded-graph-database-archived)_
_Source: [From Kuzu to Ladybug: The embedded graph ecosystem powers onward](https://thedataquarry.com/blog/from-kuzu-to-ladybug/)_
_Source: [LadybugDB: DuckDB for Graphs — The KuzuDB Successor](https://ladybugdb.com/)_

### Regulatory Focus — why air-gap is a real buying trigger, not a niche preference

The **EU AI Act's** high-risk-system obligations (Articles 9–17 provider, Article 26 deployer) become binding **2026-08-02**; a proposed delay to late 2027 was floated but **not enacted into law**, so enterprises are advised to treat August 2026 as the operative deadline _(Source: https://labs.cloudsecurityalliance.org/research/csa-research-note-eu-ai-act-high-risk-compliance-deadline-20/)_. Air-gapped deployment is increasingly framed **as a compliance architecture, not just a security posture** — it eliminates entire categories of regulatory exposure (GDPR Article 28 processor obligations, HIPAA Business Associate Agreement triggers) because the vendor never touches the data at all _(Source: https://www.truefoundry.com/blog/air-gapped-ai-deploying-enterprise-llms-in-highly-regulated-industries)_. A sharp distinction is drawn between "on-prem" and truly "air-gapped": most on-prem deployments still reach out to package managers, pull container images from external registries, and send telemetry to a SaaS vendor — "not truly air-gapped" even though it lives in the enterprise's own data center _(Source: https://datacendia.com/learn/air-gapped-ai-deployment/)_. This is a precise, citable bar for what "air-gap posture" must mean architecturally if Scribe claims it: no telemetry, no required registry reachability at runtime, no vendor cloud dependency, by default — not merely "can be self-hosted."

Regulated sectors named as air-gap-first buyers: defense/ITAR (zero cloud connectivity required for ITAR-controlled data), CUI/classified environments, aerospace/defense contractors building "entirely inside the security boundary already approved," and finance/healthcare referencing DoD IL5/IL6, FedRAMP High, and HIPAA standards _(Source: https://www.outcomeops.ai/blogs/air-gapped-ai-coding-defense-aerospace)_.

_Source: [EU AI Act High-Risk Deadline: Enterprise Readiness Gap](https://labs.cloudsecurityalliance.org/research/csa-research-note-eu-ai-act-high-risk-compliance-deadline-20/)_
_Source: [Air-Gapped AI: Deploying LLMs in Defense & Regulated Finance](https://www.truefoundry.com/blog/air-gapped-ai-deploying-enterprise-llms-in-highly-regulated-industries)_
_Source: [Air-Gapped AI Deployment: Complete Guide for Enterprises (Datacendia)](https://datacendia.com/learn/air-gapped-ai-deployment/)_
_Source: [Air-Gapped AI Coding for Defense and Aerospace (2026)](https://www.outcomeops.ai/blogs/air-gapped-ai-coding-defense-aerospace)_

---

## Internal Prior Art (domain-adjacent, not market evidence)

Two in-repo artifacts function as this domain's closest existing implementation and are directly load-bearing for the architecture phase:

- **The `bmad-spec` memlog discipline** (`.memlog.md`, append-only, canonical — derived artifacts re-render from it) is a working, already-shipped instance of "capture as you decide, compile derived views from the append-only record" — structurally the same shape as `scribe capture` → `scribe graph compile`. Multiple `.memlog.md` files already exist across BMAD projects in this repo (e.g. `_bmad-output/projects/pyforge-warden/planning-artifacts/.memlog.md`), so this is proven, not speculative.
- **The Karpathy "LLM-powered knowledge bases" method** (`docs/intake/gists/llm-powered-knowledge-bases-by-andrej-karpathy/`), identified in the Sentinel Dream's realization log as the origin essay behind the 2026-04-18 deck: raw notes compiled by an LLM into a linked wiki with backlinks. This is the specific compile-loop shape referenced by the Scribe Dream ("the Karpathy knowledge-base method... is the Scribe's compile loop").
- **The personal auto-memory pipeline** (30+ entries, `MEMORY.md` indexing) is the single-operator prototype already proven at small scale, per both the Scribe Dream and the legacy `claude-team-memory` spec.

These are not competitors to benchmark against (the market-research report covers that) — they are working precedent inside the exact codebase Scribe ships into, which lowers implementation risk relative to a from-scratch design.

---

## Domain Synthesis & Architecture-Facing Recommendations

1. **Scribe's capture format should be ADR-shaped, not invented from scratch** — one decision per record, never edited in place, new records supersede and link old ones. This is now doubly validated: it was already the dominant convention before Scribe, and 2026 practice reframes it as agent-context infrastructure, which is exactly Scribe's pitch.
2. **The graph-compile storage engine choice is genuinely open and should be an explicit architecture decision**, not a default — KuzuDB's October 2025 archival is a live cautionary example of embedded-graph-engine vendor risk; LadybugDB is the most current embedded successor but is new (2026) and unproven at scale; a flat-file/markdown-plus-index approach (extending the existing `.claude/memory/MEMORY.md` pattern) is the lowest-risk fallback and should be weighed against a real graph engine on the merits of query needs, not novelty.
3. **"Air-gap posture" must be defined precisely in the architecture doc**, per the domain's own bar: no runtime telemetry, no required package-registry reachability, no vendor cloud dependency — "self-hostable" is not sufficient to claim air-gap; this distinction should be a testable architecture constraint, not a marketing line.
4. **Local-first framing should be scoped to "git as source of truth," not "needs a CRDT sync engine"** — the 2026 local-first community's central tooling debate (Automerge/Yjs/Loro/sync engines) solves concurrent-multi-writer document convergence, a problem Scribe does not have in the same form because git already resolves that for the artifacts Scribe compiles from. Borrowing the philosophy, not the CRDT tooling, avoids scope inflation.
5. **The EU AI Act's August 2026 deadline is a live external clock**, not a distant regulatory abstraction — if Scribe's roadmap intends to pitch the air-gap posture as an enterprise/regulated-sector value proposition, the PRD should note this date as context for why the timing argument is credible now, not hypothetical.

---

## Open Questions Carried Forward (to Architecture phase)

- Embedded graph engine (LadybugDB or equivalent) vs. flat-file/index model for `scribe graph compile` — genuinely undecided here; needs an architecture-phase spike or explicit ADR (fittingly).
- What does "compiled nightly from the tools the team already uses" concretely mean as an input list for v1 — git log/PR history, `.memlog.md` files, retros, CHANGELOGs, `docs/dreams/`? The Sentinel Dream names the aspiration; the input surface is a PRD-phase scope decision.
- Should Scribe formally adopt the ADR term/format (`docs/adr/` convention) as its capture unit, or keep its own `scribe capture --type decision` vocabulary that happens to be ADR-shaped? Naming/interop question for the PRD.

---

## Sources

- [Architectural Decision Records (ADR) — adr.github.io](https://adr.github.io/)
- [Architecture Decision Records: the complete guide (2026) — Align Docs](http://docs.align.tech/blog/architecture-decision-records-complete-guide/)
- [Architecture Decision Records (ADRs): The 2026 Guide — Catio](https://www.catio.tech/blog/architecture-decision-record)
- [Architecture Decision Records: A Practical Guide for 2026 — John Pratt](https://www.john-pratt.com/architecture-decision-record)
- [Architecture Decision Record — Martin Fowler](https://www.martinfowler.com/bliki/ArchitectureDecisionRecord.html)
- [Local-First Software: Principles, Patterns, and Technologies](https://wal.sh/research/local-first)
- [Why Local-First Software Is the Future and its Limitations — RxDB](https://rxdb.info/articles/local-first-future.html)
- [Best Local-First AI Coding Tools 2026 — Nimbalyst](https://nimbalyst.com/blog/best-local-first-ai-coding-tools-2026/)
- [KuzuDB, the Promising Embedded Graph Database, is Suddenly Archived — BigGo News](https://biggo.com/news/202510130126_KuzuDB-embedded-graph-database-archived)
- [From Kuzu to Ladybug: The embedded graph ecosystem powers onward — The Data Quarry](https://thedataquarry.com/blog/from-kuzu-to-ladybug/)
- [LadybugDB: DuckDB for Graphs — The KuzuDB Successor](https://ladybugdb.com/)
- [EU AI Act High-Risk Deadline: Enterprise Readiness Gap — Cloud Security Alliance](https://labs.cloudsecurityalliance.org/research/csa-research-note-eu-ai-act-high-risk-compliance-deadline-20/)
- [Air-Gapped AI: Deploying LLMs in Defense & Regulated Finance — TrueFoundry](https://www.truefoundry.com/blog/air-gapped-ai-deploying-enterprise-llms-in-highly-regulated-industries)
- [Air-Gapped AI Deployment: Complete Guide for Enterprises — Datacendia](https://datacendia.com/learn/air-gapped-ai-deployment/)
- [Air-Gapped AI Coding for Defense and Aerospace (2026) — OutcomeOps](https://www.outcomeops.ai/blogs/air-gapped-ai-coding-defense-aerospace)
- `docs/dreams/sentinel.md`, `docs/dreams/pyforge-scribe.md` (internal — problem statement, not domain evidence)
- `docs/intake/sentinel/README.md`, `docs/intake/gists/llm-powered-knowledge-bases-by-andrej-karpathy/LLM Powered Knowledge Bases.md` (internal prior art)
- `_bmad-output/projects/pyforge-warden/planning-artifacts/.memlog.md` (internal — memlog discipline exemplar)
