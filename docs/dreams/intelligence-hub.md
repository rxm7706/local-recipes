---
title: The Distributed AI Economy — Intelligence Hubs, Frames, Cogs, Ops, and the Accountability Plane
type: dream
owner: steward
status: dreamt
---

# The Distributed AI Economy — Intelligence Hubs, Frames, Cogs, Ops, and the Accountability Plane

> **Seed Dream.** It carries the OpenTeams whitepaper *The Distributed AI Economy: Intelligence
> Hubs, Frames, Cogs, Ops, and the Accountability Plane* (Travis Oliphant, August 2026, Revision 9)
> into the Dream tier, section by section, so that `bmad-spec` can derive a contract from it. The
> whitepaper stays the source of record; this file is a complete distillation in our own words, with
> a few short attributed quotations — not a copy. Nothing below is an adoption decision.

## Source

- **Document:** https://ownyourintelligence.ai/downloads/Intelligence_Hub_Whitepaper_v9.pdf
  — 46 pages, US letter, produced with LibreOffice 24.2, file dated 2026-08-16; footer
  *OpenTeams | nebari.dev | August 2026 | Revision 9*.
- **Author / publisher:** Travis Oliphant (creator of NumPy and SciPy; CEO, OpenTeams). Companion
  sites: ownyourintelligence.ai, nebari.dev.
- **Integrity:** sha256 `5dabf2bec9cde59e5cc5bfa38eb08d3cd536daf20a6e6d7e815d76cd401dbe41`, captured
  2026-09-05. The PDF is **not** checked in (third-party copyright, 1 MB); re-fetch by URL and
  compare the hash before trusting a later revision against this text.
- **Evidence base:** 34 cited sources — McKinsey (×4), PwC (×2), Deloitte (×3), Stanford HAI
  AI Index 2025 + 2026, Brookings, OSI/OpenLogic State of Open Source 2026, Financial Times,
  Nadella at WEF Davos 2026, Hugging Face, NBER (×2), PEX Network, Dataversity, AlixPartners,
  Gartner (×2), Robert F. Smith (Vista), EU AI Act (Reg. 2024/1689, Arts. 12/14/19), NCSL state
  AI legislation, LinuxInsider, NIST AI RMF 1.0 + GenAI Profile, ISO/IEC 42001:2023, OWASP Top 10
  for LLM Applications, Black Duck OSSRA, Cloudflare OS, Earendil Works, IBM "What is the AI
  stack?". The paper notes that entries it could not re-verify are marked as such, and that one
  attribution (PwC operations survey) was corrected from Deloitte in an earlier revision. Every
  statistic below is the paper's claim, not ours — re-verify at intake before any Spec leans on it.

## The Dream

An organisation owns its intelligence. Its context, its AI workers, its workflows, the checks on
their work and the evidence they leave all live inside a perimeter the organisation governs, built
from shared abstractions that many parties can build to — so that the value of applied AI accrues
to the people who produced the context, and the AI era grows into an open economy rather than a
landlord-and-tenants arrangement.

PyForge is already such a hub in miniature: an owned factory on pixi and conda-forge, with its
context in tracked files, its workers as station skills, its workflows as bmad-loop runs, its
checks as detectors and Warden, and its evidence in ledgers. The Dream is that the Foundry speaks
the whitepaper's vocabulary — Frames, Cogs, Ops, Guards, Gates, Tracks, Organizational Memory —
deliberately rather than by accident, and that the Spec derived from this seed decides *which* of
those shapes PyForge adopts, aligns to, or merely names.

## The whitepaper, distilled

### Preface — why the author wrote it

Three decades of shared abstractions (SciPy, NumPy, Numba, conda, NumFOCUS, now the Applied AI
Society) taught the author one lesson: when a foundational layer is open an ecosystem forms and
value accrues broadly; when it is closed "a landlord forms, and everyone else rents." Enterprise AI
is at that fork. Frontier models are magnificent but rented, and the context, judgment and evidence
that make them valuable inside an organisation are leaking into systems the organisation does not
control. The proposal: organisations organise and adapt their existing IT into self-owned,
self-controlled, governed **Intelligence Hubs**; information technology evolves into **Intelligence
Infrastructure**; accountable intelligence must be intimate with the most important data, and that
intimacy is only safe when both data and intelligence are owned. Six abstractions carry the
argument — Frames, Cogs, Ops, Guards, Gates, Tracks. The paper is explicitly "not a product pitch";
OpenTeams is one contributor among many, and most of the value described is expected to accrue to
organisations the author has never met, as it did with NumPy.

### Executive summary

The next decade of enterprise AI will be defined by who deploys, governs and exchanges AI
capability as owned operational infrastructure — a shift from renting intelligence through
black-box APIs to sovereign, reproducible, auditable deployments. The architecture is three layers
plus one cross-cutting plane:

| Plane / layer | Core units | Does |
|---|---|---|
| Layer 1 — Infrastructure | Intelligence Hub · Nebari · Nebi | Own, deploy and integrate AI as sovereign infrastructure |
| Layer 2 — Execution | Frames · Cogs · Ops | Carry context, perform work, orchestrate outcomes |
| Accountability plane (cross-cutting) | Guards · Gates · Tracks | Verify the work, decide whether it proceeds, record the evidence |
| Layer 3 — Economy | The marketplace | Discover, exchange and monetise artifacts across Hubs |

Every Op declares a **Validation Strategy** so AI-generated work becomes accountable operational
intelligence rather than unverifiable output. The one essential first interface is a **Desktop/Web
Application** through which knowledge workers combine Frames, converse with Frame-oriented Cogs,
run Ops and share context. Market framing: McKinsey sizes sovereign AI at $500–600B by 2030; PwC's
29th CEO Survey (n=4,454) finds 56% of CEOs report zero financial impact from AI and 12% report
both cost and revenue benefit — the investment-to-outcome gap the architecture is meant to close.

### Where this sits in the AI stack

Not a rival stack. The shared abstractions sit inside the familiar layers — Frames at the data
layer, Cogs at the work layer, Ops at the application layer — and the accountability plane is the
paper's concrete answer to what the industry calls observability and governance, made shippable
with the artifacts themselves. Around an owned Hub a second economy of products forms (Hub
experience apps, compute and model management, Track stores, Gate consoles, Op and Cog builders,
Guard libraries, segment-specific Ops).

The paper's own honesty table, as of Revision 9:

| Status | Covers |
|---|---|
| Exists today | Nebari and `nebari-infrastructure-core`; Nebi (packaging and reproducibility, built on pixi, which built on conda); owned Hubs in production; Frames as governed artifacts with storage, identity and connectors; a Desktop/Web Application; owned model serving on open weights |
| In active development | Cogs and Ops as first-class installable objects with declared tools and permissions; the Op manifest with a declared validation strategy; multi-organisation Hubs; the first Guard libraries |
| Thesis | The accountability-plane runtime at scale; a marketplace exchanging artifacts across many independent Hubs; the distributed AI economy itself |

Nebi is singled out as the thesis in miniature: it builds on pixi, which built on conda, rather
than inventing distribution anew — shared abstractions compounding across generations.

### 1. The problem — rented intelligence is fragile, and context leaks away

Organisations know AI is strategic yet depend on vendor-controlled black boxes they cannot inspect,
reproduce, audit or own (the paper names Codex, Claude Code/Cowork, Grok and Gemini), and even when
they can deploy capable AI they cannot capture and propagate the organisational context — rules,
terminology, goals, style, norms — that turns generic AI into specialised work. Eight failure modes,
each with a root cause and a business impact: **vendor lock-in** (third-party APIs → strategic
dependency, cost unpredictability); **security leaks** (data leaves → lost moat and IP, regulatory
exposure in healthcare/finance/government); **execution opacity** (no visibility → cannot audit or
reproduce); **integration fragility** (no standard for how AI plugs into workflows → cost and
breakage); **value leakage** (capabilities cannot be shared or monetised); **context dissipation**
(no portable container for rules, terminology, norms, skills, tools, prompts and processes →
repetitive re-setup, brand and policy drift, the ROI-fuelling context does not stay with its
producer); **governance vacuum** (1 in 5 organisations has mature agent governance — Deloitte 2026;
AI incidents up 56.4% in 2024 — Stanford HAI; 43% have no formal AI governance policy — PEX);
**talent scarcity** (worker skills the #1 barrier — McKinsey; only 20% report high talent
preparedness — Deloitte). The root cause is architectural: no standard model for what an owned
deployment looks like, how capabilities are packaged into executable units, or how organisational
knowledge is encoded, inherited, shared and exchanged. Two market voices frame it: Satya Nadella at
Davos 2026 — sovereignty means embedding the firm's tacit knowledge in weights the firm controls,
otherwise "you're leaking enterprise value to some model somewhere" — and Robert F. Smith of Vista,
who is "shocked" that CEOs on an ARR race have leaked intellectual property.

### 2. The vision — a distributed economy of owned intelligence

Every organisation — enterprise, government, research institution, startup — runs its own Hubs:
sovereign, governed environments integrating its data, legacy applications, AI-native workflows,
policies and models inside its own perimeter, appropriately virtualised across private cloud and
edge. The sovereignty argued for is realistic, not absolutist: Brookings (Feb 2026) finds
full-stack AI sovereignty structurally infeasible for almost any country, so the market for trusted
intermediaries is permanent; Stanford HAI names four sovereign-AI objectives (cultural autonomy,
national security, economic competitiveness, regulatory oversight); McKinsey (Mar 2026) calls
sovereign AI "an ecosystem play" with sovereignty applied deliberately at critical control points.
Control your model choice, data paths, policies and evidence — without fabricating chips or
training a frontier model.

Hubs need not stay isolated: they connect "as a drawbridge connects walled castles", so derived
results flow under the policies of the organisations accountable for the data. Four versioned,
exchangeable artifacts travel those pathways: **Frames** (scoped context, inherited across scopes,
shareable internally and externally), **Cogs** (specialised AI workers oriented by Frames —
reproducible, modular, self-contained cognitive workers), **Ops** (installable, versioned programs
of AI-influenced work, accountable to human oversight) and **Guards** (installable, versioned test
and verification code).

Two framings complete the vision. First, the **Intelligent Ops Factory**: where AI-native software
factories capture requirements, architecture and structured context upstream and feed it to agents
so they produce governed software, an Ops Factory produces and continuously maintains an
organisation's standard operating procedures inside its own Hub — the output is operational
intelligence the organisation owns, not an application; many parties can operate such factories
because the abstractions are shared. Second, **no "Hub to rule them all"**: a distributed fabric of
owned Hubs interoperating through shared open standards, not a shared owner. OpenTeams
participates by contributing Nebari and Nebi, operating a public reference Hub for small
organisations, building products around the Hub and offering maintenance — and argues a
**services / concierge layer** is necessary because the open-source AI ecosystem (model servers,
vector databases, orchestration, observability, identity) is vast, fast-moving and fragmented. The
concierge role is deliberately non-exclusive.

### 3. Layer 1 — Infrastructure

The canonical relationship, held throughout: **Nebari** is OpenTeams' flagship open-source
contribution; **Nebi** is the reproducibility and distribution mechanism; the **Intelligence Hub**
is a customer-specific assembly of open-source and proprietary components that someone integrates,
governs and maintains. No single tool is the infrastructure.

**3.1 Nebari.** Since June 2025 the project has been rearchitected into a modular, composable stack:
`nebari-infrastructure-core` plus more than fifteen software packs at varying maturity, from the
original Jupyter data-science use case to serving open-weight LLMs and GenAI chat. Within its scope
it standardises compute and environment management across cloud and on-premise, model deployment
and versioning, tooling interoperability, and RBAC / audit logging / governance primitives. It is
open-source and additive — usable à la carte on top of existing infrastructure. Stewards named:
Travis Oliphant and Dharhas Pothina. A Hub "is not a Nebari deployment"; Nebari may play a role but
rarely the only one. Market support: OSI's 2026 State of Open Source (n=700+) finds lock-in
avoidance cited by 55% of respondents, up 68% year over year; Black Duck OSSRA on open-source
prevalence; a January 2026 industry quote that open standards let the ecosystem inspect, test and
harden the protocols agents use.

**3.2 Nebi.** The installation foundation: definition, installation and lifecycle management of
complex deployable environments, built and working today on pixi and conda. It defines the common
format by which Frames, Cogs, Ops and Guards are packaged; manages dependencies and environment
snapshots so an Op installed in one Hub behaves identically (within generative-AI limits) in
another; enables versioned rollout and rollback of AI systems, Frames and dependent Cogs; and is the
installation primitive and reproducibility guardrail that makes a marketplace technically possible.
Because it can package anything the open-source community creates, it bridges the ecosystem's
varied standards and the Frame/Cog/Op/Guard ecosystem — without it those artifacts would be
application-layer agreements with no infrastructure-layer enforcement.

**3.3 The Accountable Intelligence Hub.** A particular configuration of open-source components
deployed inside an organisational perimeter, the concrete realisation of the standard and the
centrepiece of the architecture: where Frames are made manifest and connected to Cogs, where Cogs
are installed, configured and run, where Ops orchestrate Cogs, and where the organisation connects
outward to the marketplace as consumer and, over time, publisher. Seven characteristics: operates
inside the organisation's perimeter (cloud, on-prem, hybrid); integrates with ERP/CRM/warehouses/
APIs; enforces governance on model behaviour and data access; stores, versions and manages the
inheritance graph of Frames; provides full auditability of AI actions; stores and governs Tracks;
connects bidirectionally to the marketplace. No two Hubs are identical, by design; nobody is asked
to migrate. Market support: Deloitte sizes the on-prem hybrid market above $50B for 2026 and finds
77% of enterprises weigh a vendor's country of origin, 58% build primarily with local vendors;
McKinsey's "key control points are sovereign by design"; PwC finds 87% of operations leaders
hampered by poor data quality, with McKinsey adding that localisation does not make data usable —
strong sovereign ecosystems build data products and sharing mechanisms.

**3.4 Organizational Memory.** The persistent context substrate that turns a Hub from a server-side
deployment of AI tools into a compound learning system. Frames hold **intentional** context (what
humans chose to make explicit); Cogs and Ops generate **emergent** context (what actually happened);
Guards, Gates and Tracks are part of the same memory. It is a capability on a continuum, not a
product: at the simplest end a version-controlled directory of Frame files; at the richest, full
conversational records of every Cog interaction, semantic retrieval over them, structured records of
every Op execution with its human decisions, knowledge graphs of concepts/decisions/people/outcomes,
existing knowledge bases and ERP data, and time-aware retrieval. The Hub prescribes no technology —
it provides integration points and governance hooks — and the paper offers a menu: versioned Frame
repositories (Git/GitHub/GitLab or object storage), wikis (Confluence, Notion, Obsidian), vector
stores (Chroma, Weaviate, Qdrant, Milvus, pgvector), AI memory frameworks (Mem0, Letta, Zep;
LangChain/LlamaIndex modules), observability platforms (LangSmith, Arize Phoenix, Helicone),
knowledge graphs (Neo4j, ArangoDB), lakes and warehouses (Snowflake, Databricks, Iceberg,
BigQuery, PostgreSQL). A typical configuration combines an object store for Frame versioning, a
vector database for Cog conversations and an observability platform for Op executions. Governance
is essential: access controls, retention policies, anonymisation/redaction, audit trails, and **the
ability to forget**. Memory belongs to the organisation that produced it — "intimacy without
ownership is exposure" — so a Hub cannot be rented or bought whole; vendors and contractors may
maintain parts of it.

### 4. Layer 2 — Execution: Frames, Cogs and Ops

**4.1 From models to work.** The gap is not at the model layer but at execution: turning a capable
model into a reliable, auditable, governable unit of work, while keeping the organisational context
with the organisation instead of dissipating it into one-off prompts and vendor-side logs. Evidence:
72% of enterprises have sovereign AI on the roadmap but 13% are on track (McKinsey); 12% / 56% CEO
figures (PwC); 34% of organisations genuinely reimagining with AI and 1% self-described AI-mature
(Deloitte). The **progression of value**: models predict tokens → Frames orient humans and Cogs to
shared context → Cogs perform specialised work under Frames, skills, tools, memory, permissions and
Guards → Ops orchestrate outcomes with human oversight. A **running example** threads the paper: an
accounts-payable analyst launches a *Vendor Fraud Review* Op; Company Policy, Procurement Rules and
Fraud Detection Methodology Frames orient every step; Invoice Extraction, Vendor Risk and Anomaly
Summary Cogs do the work; Schema, Source, Privacy and Consensus Guards check it; low confidence or
high vendor risk routes the case to a human before any vendor is flagged; the full Track is retained.

**4.2 Where agents fit.** The industry converged on the agent — a model in a loop with tools pursuing
a goal — and the hard problem is no longer building one but **employing** one: who does it work for,
whose context and policies govern it, which tools and data may it touch and under whose identity,
how much autonomy was granted and by whom, who checks the work before it has consequences, what
record remains. "Agent" is a runtime blur across three things the architecture keeps separate: the
**capability** (a Cog — installable, versioned, auditable before it runs), the **engagement** (an Op
— goal, autonomy budget, checkpoints, validation strategy) and the **continuing actor** (identity,
credentials, memory, history — held by the Hub: identity from its directory, credentials brokered
and scoped, memory in Local and Organizational Memory, history in Tracks). An agent, precisely, is a
Cog engaged through an Op, given identity and memory by the Hub; fused into one word, these are how
vendors capture instance state and why governance cannot be tailored. The employment mapping:
Frames are the context and policies; a Cog is the qualified hire; an Op is the assignment; Guards
check the work; Gates are the autonomy budget; Tracks are the personnel record; the Hub is the
workplace. Autonomy is granted per engagement, not per platform (a drafting Op may run nearly
unattended, a payments Op may need approval at every step) — the shape Gartner now insists on,
predicting that by 2027 40% of enterprises will demote or decommission autonomous agents over
governance gaps found only after incidents. Cloudflare OS validates the category (workspace grounded
in organisational context, policy-enforcing "Gatekeepers", persistent app platform) while showing
openness and sovereignty are different properties — Apache-2.0 code designed for one vendor's
network, self-hosting an in-progress escape hatch; Earendil Works documents providers making
sessions deliberately non-portable. Whoever holds an agent's context, memory and history owns the
agent. Agents operating infrastructure (installing, provisioning, patching) are Ops like any other:
Guards pre-check authority, Tracks record actions, Nebi pins artifacts. "Agents are the hands; the
Hub is the employer of record."

**4.3 Frames — shared cultural alignment.** A Frame is a scoped, text-based artifact (a file or folder
of files using an open protocol) carrying the cultural and operational context within which work
happens — the brand voice, terminology, regulatory constraints, conventions and norms that today
live in wikis, Slack history and senior heads. "Context, in this sense, is capital": every prompt
that re-explains the organisation is capital spent as an expense; a Frame is the same context
accreting as a versioned asset. Frames are first-class — authored, discovered, exchanged and
inherited independently of Cogs and Ops. Typical contents: rules, terminology, goals, style, norms,
skills, tool specifications (Nebi or similar spec files), output Guards, prompts, architecture
descriptions, business-process details. Six essential properties: **scoped** (organisation,
department, team, project, role or relationship), **inheritable** (child extends parent; the chain
of authority is auditable), **composable** (company + department + project + ad-hoc for one
session), **shareable** (internally, or selectively externally with reviewed subsets), **discoverable**
(internal libraries, communities of practice, open registries — most Frames spread by community
adoption, not sale) and **owned** (by an accountable human or group — the slice of direct human
accountability in the context). A Frame may declare a Guard that must run on the system's output.
Why a distinct layer rather than "just prompts" or "just skills": a Frame is an organisational
artifact governed by its owner — versioned, audited, inherited, exchanged — the cultural commons made
explicit and portable yet protectable. Illustrative Frames: Brand Voice (marketing), Healthcare
Compliance (legal, pointing to a mandatory Guard), a Q4 Sales Playbook, an External Vendor Frame
with selectively shared sections, a Pharma R&D Compliance Frame published by a consortium. Five use
cases OpenTeams runs itself: internal alignment (a Company Frame every division/team/project/person
inherits), sister companies and ecosystem peers (Product Direction Frames), open-source communities
(Community Frames — Nebari among them), partner engagement (a Partner Frame: "the Frame is the
contract of context") and investor messaging (an Investor Frame against message drift). The **Frame
protocol** — an open specification for the artifact's structure — is the standard that makes the
exchange possible: Nebari standardises infrastructure, Nebi packaging, the Frame protocol cultural
alignment.

**4.4 Cogs — AI workers oriented by Frames.** A Cog is a discrete AI-powered worker, the atomic unit
of AI work — "an AI worker you can hold to account": an assembly of a (possibly specialised) model,
a context including one or more Frames, the skills/tools/APIs it may use, and its governance
parameters (data it may access, actions it may take, what needs human approval), that can be named,
versioned, inspected and replaced. Cogs are the key artifact Nebi distributes and can carry all code,
dependencies and weights. Three types: **model-heavy** (deploys the foundation model), **context-heavy**
(the data and context, pointing at a model by dependency or API endpoint) and **combined** (a complete
isolated worker). Context management is the central discipline: Frames are the durable governed
foundation, around which retrieved documents, slices of Organizational Memory, conversation history,
tool outputs, real-time data and task instructions are assembled at invocation — "a well-constructed
Cog is, in large part, a well-managed context." The **harness explosion** (agent loops, tool-calling
frameworks, graph orchestration, memory scaffolds, skill libraries, evaluation hooks, new ones
monthly) is read as evidence that weights alone are not a worker; a harness is a capability a Cog
builder uses, not a competitor to the Cog, and the Cog abstraction makes the harness choice an
internal detail — a vertical specialist can build a Contract Review Cog on one harness while a
community builds an Invoice Extraction Cog on another and an Op composes both. Cogs are the level at
which AI behaviour becomes auditable like a worker: not "what did the model do?" but "what did this
Cog do, with what inputs, under which Frames, with what outcome?" Productivity evidence: the NBER
"Generative AI at Work" study (5,179 support agents) found a 14% average gain and 34% for novices;
NBER WP 34984 (n=750 executives) finds positive, sector-varying gains expected to strengthen in
2026. Cogs are not usually standalone agents — they can be run directly for debugging, validation,
analysis or simple operations, but normally live inside an Op.

**4.5 Ops — orchestrated AI workflows.** An Op is "the application of the distributed AI economy": the
supervised workflow a human at the keyboard launches, mapping onto how knowledge workers think about
their job — "Close the books", "Onboard this customer", "Qualify this lead", "Draft this campaign",
"Review this vendor for fraud". Composition: one or more Cogs (each with embedded Frames);
workflow-level Frames; a supervising model that sequences, parallelises and handles the unexpected;
human-in-the-loop checkpoints; a declared Validation Strategy (Guards, Gates, Track); integration
logic to enterprise systems; a Nebi-compatible manifest (dependencies, environment, configuration).
Invocation from wherever the user already is: an icon in the Desktop/Web launcher, a CLI or chat
command, a button or link inside a business application, a scheduled or event-triggered job.
Authored once and installed into any compliant Hub, picking up the local Frames — the npm/pip
analogy, for supervised Frame-aware workflows rather than libraries. Market support: Deloitte
anticipates agent marketplaces and argues advantage lies with organisations that redesign
end-to-end processes around agents; 74% of companies plan agentic AI within two years. Seven
characteristics: **versioned** (identifier and changelog), **installable** (via Nebi), **Frame-oriented**
(declares required/applied Frames), **supervised** (coordinating model + human checkpoints),
**triggerable**, **self-contained** (Cogs, logic, integration specs, Frame declarations) and **composable**
(Ops call Ops).

### 5. The accountability plane — Guards, Gates and Tracks

Every AI-assisted workflow must answer two questions: what context should guide this work (Frames),
and how do we know the result can be trusted (Guards, Gates, Tracks). The plane cuts across all
three layers rather than sitting beside them. Without validation AI work stays fragile; with it, it
becomes operational intelligence — and in enterprise, government, healthcare, finance and legal
settings output must be verifiable, governable, auditable and accountable, not merely useful. The
validation gap: rising incident counts with rare standardised evaluations (Stanford HAI); McKinsey's
"gen AI paradox" — ~80% deployed, ~80% no material earnings impact, under 10% of use cases past
pilot — with the prescribed remedy being exactly this layer. Validation runs during Frame
construction, Cog development and Op execution. The paper's own summary line: *"Frames guide the
work. Cogs perform the work. Ops orchestrate the work. Guards verify the work. Gates decide whether
the work proceeds. Tracks make the work accountable."*

**5.1 Guards.** Reusable verification and protection components that check whether a Cog's or Op's
output or action is correct, safe, policy-compliant and ready for use. Broader than tests: some
deterministic, some probabilistic, some comparing independent Cogs, some requiring human review;
running before, during or after work. A Guard can check that the right Frames were applied, that
output matches a schema, that answers are grounded in approved sources, that a proposed action does
not violate policy, that no sensitive data is exposed, that independent Cogs agree, that confidence
is high enough for autonomous action, that a human expert must review, and that behaviour is not
drifting from previously validated behaviour. Named library shapes: Schema, Source, Policy, Privacy,
Consensus, Drift and Expert Guards. The principle: Frames *may* declare Guards; every Op *must*.
Validation is part of Frame and Op design, not a policy-team afterthought.

**5.2 Gates.** Decision points where the results of one or more Guards determine what happens next:
continue, pause, request human approval, escalate to an expert, retry with a different Cog, run more
validation, or stop. "Guards check. Gates decide." Examples: unsupported claims → pause for revision;
low confidence → human review; sensitive data → stop before external transmission; strong Cog
disagreement → expert escalation; all pass → proceed. Gates encode the fact that not all failures
are alike — some need correction, some review, some escalation, some termination — and in the
running example a low extraction confidence or a high vendor-risk score is a routing decision, not a
failure state. Regulation expects formal Gates: the EU AI Act's human-oversight article (Art. 14)
requires that a natural person can interpret, decline, override, reverse or stop the system —
timelines under the AI Omnibus political agreement of December 2027 for standalone high-risk
systems and August 2028 for AI embedded in regulated products.

**5.3 Tracks.** The durable record of an Op or Cog execution: the Op run, Cogs invoked and Frames
applied; input data and source references; model versions and configuration; Guards executed with
results and confidence; Gates passed, failed or escalated; human approvals, edits and overrides;
final outputs or actions; timestamps, user identity, permissions and environment; links to
Organizational Memory. Purposes: auditability (reconstruct why), governance (verify procedure),
learning (corrections become signals for improving Frames, Cogs, Ops and Guards), debugging and
trust. "The Track is not just a log file. It is a structured accountability artifact." Unlike the
other four artifacts, Tracks are usually not exchanged — retained under the producing Hub's
governance, produced only for audits or regulators: "Evidence is not for sale." The EU AI Act
requires automatic event recording and deployer log retention (Arts. 12 and 19); Tracks satisfy
that by construction.

**5.4 Validation across the Op lifecycle.** Four stages, each with its core question and example
controls: **pre-flight** (is this Op allowed and configured? — permission, required-Frame, data
authorisation and model availability checks), **in-flight** (is the work within policy and bounds? —
tool-use, privacy, confidence, policy checks, intermediate review Gates), **post-run** (is the output
correct, useful, safe, actionable? — source grounding, schema validation, expert sampling,
consensus, final approval Gates) and **continuous** (is quality improving, degrading or drifting? —
regression tests, drift detection, benchmark suites, incident reviews, sampled expert audits). A
low-risk drafting Op may need format checks and user review; a high-risk fraud Op may need source
grounding, multiple independent Cogs, expert sampling and a Track retained for years; clinical,
legal, financial and public-sector Ops may need formal Gates before any recommendation becomes an
action. The lifecycle aligns with NIST AI RMF 1.0 (govern, map, measure, manage) and its Generative
AI Profile — declaring Guards, Gates and Tracks per Op is how that framework becomes executable.

**5.5 Seven categories of Guards.** **Algorithmic** (deterministic rules or known results — code
passes tests, SQL executes, totals reconcile, JSON matches schema); **Source-Grounding** (claims
supported by approved evidence; cited passages actually support the conclusion); **Consensus**
(agreement across independent Cogs, prompts, models or paths — two of three must agree; a verifier
Cog reviews another); **Expert** (human judgment on sampled or high-risk outputs — periodic 5%
sampling, mandatory review of high-risk classifications, approval before external communication);
**Policy & Safety** (inside allowed boundaries — no private-data release, no unapproved tools or
sources, no action beyond the user's permissions, brand/legal/ethical constraints); **Regression &
Drift** (golden sets after model updates, rising error rates, a new Frame that degrades performance);
**Outcome** (the intended business result — fewer false positives, shorter onboarding, more contract
risks caught, lower cost without added risk). The strongest are algorithmic; the most
business-meaningful are Outcome Guards; Policy & Safety Guards connect directly to Frames.

**5.6 The Validation Strategy — part of every Op's contract.** Every Op declares which Guards it uses,
where Gates occur, what Tracks are retained and when human review is required, answering: what must
be checked before running and which Frames, Cogs, tools and data are authorised; which outputs need
algorithmic validation and which claims need grounding; when consensus is required; when human or
expert review is required and at what thresholds; what evidence the Track must preserve and for how
long; how failures, corrections and overrides feed back into Organizational Memory. ISO/IEC 42001
(the first AI management-system standard) asks for lifecycle management, independent audit and
continual improvement; a declared strategy makes that concrete and machine-checkable. "An Op is not
complete unless it declares how its work will be verified." The paper sketches the running example
as a validation-aware **Op manifest**: the Op's name; its three Frames; its three Cogs; Guards grouped
by stage (pre-flight: required-Frame, permission, data-source authorisation; in-flight: tool-use
policy, sensitive-data, confidence; post-run: schema, source-grounding, consensus, expert-sampling);
Gates as threshold rules (confidence below 0.80 → human review required; consensus disagreement
above 0.25 → expert review; sensitive data detected → stop and escalate; vendor risk high → human
approval); and a Track block with a seven-year retention and an include list (Frames used, Cogs
invoked, source documents, Guard results, Gate decisions, human approvals, final output).

**5.7 How validation completes the architecture.** Frames define the rules; Guards verify the work
stayed faithful to them (a Healthcare Compliance Frame's rules, a Privacy Guard's check). Cogs
perform; Guards check reliability — and some Guards are themselves Cogs when validation needs
interpretation. Ops orchestrate; Gates decide whether they proceed. Tracks flow into Organizational
Memory, closing an eight-step **Accountability Loop**: Frames orient → Cogs perform → Ops orchestrate
→ Guards validate → Gates control action → Tracks preserve evidence → Organizational Memory learns →
Frames, Cogs, Ops and Guards improve.

**5.8 Validation as an open-source opportunity.** Guard libraries, benchmark suites, prompt-injection
test harnesses (prompt injection tops the OWASP Top 10 for LLM applications), source-grounding
validators, schema and format Guards, domain compliance Guards, red-team datasets, expert-sampling
frameworks, drift monitors, Track schemas, evidence-record viewers, audit and governance dashboards.
Trust cannot be built by one company; it compounds when the ecosystem can inspect, improve and share
the validation tools. "Open Guards can become to accountable AI what open test frameworks became to
software quality."

### 6. Layer 3 — the marketplace

**6.1 Four classes of exchanged artifact,** each with its own publishers, audience and dynamics: **Ops**
(service-as-software under subscription, usage or outcome arrangements), **Cogs** (rented, purchased,
given away or subscribed), **Frames** (the vast majority shared freely within and between organisations;
a few offered commercially as licensed expertise) and **Guards** (many published openly by communities
and experts; commercial libraries encoding regulated-industry expertise — a HIPAA Privacy Guard, a
KYC Source Guard, a Contract Citation Guard, a Prompt Injection Guard). Organising around four
classes rather than one is a deliberate decision: the work, the workers, the context that orients
them and the validation that makes them trustworthy. **Horizontal vs vertical AI:** horizontal Ops
are authored once and installed across many Hubs; vertical specialisation — historically bespoke
consulting that dies with the engagement — becomes portable when the same horizontal Op picks up an
organisation's Frames, is checked by its Guards and leaves Tracks under its governance. **What is
scarce when code is free:** verification, context and accountability. A HIPAA Guard is valuable for
who stands behind it; a Frame is distilled expertise with a named owner; an Op with a thousand
validated Tracks is trustworthy in a way a fresh one is not, and that cannot be faked because Tracks
only accumulate through governed real use — "when generation is free, provenance is the product."
The Frame side of the economy is coordination and shared abstraction more than transaction
(communities of practice, consortia, open-source ecosystems, internal departments). Tracks are not
exchanged, though anonymised or aggregated Track data can inform quality rankings and trust
signals. Pricing trajectory: Gartner (via Deloitte) projects at least 40% of enterprise SaaS spend
shifting to usage-, agent- or outcome-based pricing by 2030; AlixPartners says incumbents must
consider dismantling the pricing models they were built on.

**6.2 The network flywheel — and its brakes.** More Hubs → a larger market for publishers → more
artifacts make each new Hub more valuable → more deployments generate more data on what works →
better artifacts strengthen the marketplace → more Hubs. The paper names four brakes: **cold start**
(the first artifacts are the ones organisations build for themselves anyway; a Hub is valuable
before it exchanges anything), **fragmentation** (three incompatible Frame formats would be worse
than none — standards work is a first-class deliverable), **quality collapse** (Guards nobody trusts,
Ops that pass their own checks and fail in the world — provenance is the defence; lose it and the
marketplace degrades to a code repository) and **incumbent bundling** (a large vendor ships the whole
shape free on rented compute — "the brake most likely to bite"; the only durable answer is that
ownership must be easier than renting). Macro tailwinds: the FT on deglobalisation as a supplier
windfall; Nvidia's $30B sovereign revenue in FY2025; Stanford HAI's $581.7B global corporate AI
investment in 2025 (+130% YoY).

**6.3 Who participates.** Enterprises (deploy Hubs, author Frames, install artifacts); AI developers
(build and publish Ops and Cogs); domain experts (author Frames, configure Cogs, define Op logic);
communities and consortia (open Frames codifying methodologies and vocabularies); consultancies and
agencies (methodology Frames, mostly open); system integrators (deploy and customise Hubs, bespoke
Ops and Frames); open-source contributors (extend Nebari, Nebi, the Frame protocol, Cog and Op
standards); Guard publishers and validation experts (Guards, Gate policies, benchmark suites, Track
audits); regulators and standards bodies (rules, schemas, test profiles, reference Guards).

### 7. Products around the Hub — the Desktop/Web Application as worked example

**7.1** Architecture alone does not create adoption. A second economy forms around an owned Hub —
experience applications, compute and model management, Track stores and viewers, Gate and review
consoles, Op and Cog builders, Guard libraries, segment-specific Ops, integration and operations
services — every one buildable by many parties and integrable into a Hub the organisation owns.
The Desktop/Web Application is worked through as one such product, not the category.

**7.2 Target user:** knowledge workers in sales, marketing, project success, accounting, legal, HR, IT
and shared services — people who operate inside well-defined contexts, apply organisational norms to
every task, need AI that respects those contexts without re-orientation, routinely share context
across boundaries, and are not engineers.

**7.3 Memory in the application.** A personal **Local Memory** absorbs the user's active Frames —
Company on joining, Department layered on, Project composed further, marketplace Frames installed,
personal Frames authored — and becomes the substrate every conversation and Op inherits. Beyond it,
a permissioned window into **Organizational Memory**: the user's own past Cog conversations and Op
runs, their team's where access is granted, and the documents and records their role authorises. The
boundary is policy-controlled (a sales rep sees their accounts, not others'; a clinician their care
team's protocols and summaries, not records outside it) with uniform access controls, retention,
anonymisation and audit. Local Memory is private by default and promotion outward is the user's
call; reach into Organizational Memory is Hub-governed, visible, auditable and reversible by
administrators.

**7.4 Three modes of engagement:** **Applications** (Ops as launcher icons — "the buttons that do the
job", optionally picking up the user's active Frames or pinned to pre-loaded ones), **Conversations**
(chat with Cogs already oriented by the active Frames — brand voice, terminology, goals and tools
without setting the stage) and the **Cog Library** (load a Cog directly as a standalone tool for
analysis, validation, debugging, one-offs, or to explore what exists).

**7.5 Frame management** is the application's most distinctive capability: install Frames from the
marketplace, the internal library or partners; combine them for a session with the application
managing the inheritance graph; author or extend; share internally or externally with field-level
controls; give feedback either as scores on particular concepts on a six-point scale (−10, −1, −0,
+0, +1, +10) or as suggested changes routed to the accountable author; publish back to the
organisation's library, a community board, a user, or the open marketplace. The application is
both a productivity surface and a context exchange.

**7.6 Hub health and governance** for administrators: resource utilisation and model-serving status,
an audit-log browser (AI actions, human interventions, Frame applications, data accesses), policy
management across Frames/Ops/Cogs, and user/role management.

**7.7 Making validation visible** without overwhelming users: Guard status per Op run or Cog output,
Gate prompts in-workflow, a Track view for authorised users, confidence and risk indicators, a
correction workflow that feeds Organizational Memory, and validation badges. Plain language for
users ("This Op passed all required Guards", "This result needs expert review", "A Track has been
saved for audit"); deeper views for compliance (Guard configuration, Gate thresholds, retention,
sampling rates, drift reports, failure trends).

**7.8 Products as market development:** they lower the barrier to Hub deployment, make discovery
app-store-like, create a usage feedback loop for artifact quality, serve the Applied AI Society's
credentialing as a training environment, and demonstrate an owned Hub in the most persuasive way — a
knowledge worker doing their job, with AI, under the right Frames.

**7.9 Technical architecture:** cross-platform native (macOS, Windows, Linux) plus web; local-first
(full function against a local Hub when remote Hub or marketplace is unreachable); Hub-agnostic
(any standards-compliant Hub); Nebi-integrated (artifact install and lifecycle through the Nebi
client); marketplace-connected; local-memory-backed; validation-aware; extensible via a plugin
architecture for Op developers' custom Cog configuration UIs.

### 8. Ecosystem strategy — Nebari, Nebi and the startup ecosystem

**8.1 Open source as the trust foundation.** The marketplace only works if an Op behaves the same in
any Hub, a Frame is interpreted the same by any Cog, and the protocols are stable and open — trust
grounded in open source. Nebari is company-backed to be nurtured with focus but is establishing
community governance, the dynamic that made Python the default language of AI. Adoption is
self-reinforcing, and OpenTeams as primary steward captures some value through enterprise services,
marketplace fees and its own Cogs and Ops.

**8.2 Nebi as the distribution mechanism** — pip to Python, npm to JavaScript: the plumbing that lets
everyone focus on authoring and using artifacts rather than deployment mechanics. Its trust role:
dependencies resolved and pinned, installations logged, every deployment auditable.

**8.3 The startup ecosystem.** As Kubernetes spawned cloud-native startups, Nebari and Nebi can
found a generation of domain-expert AI businesses that publish vertical Ops, Cogs and Guards and —
uniquely — Frames monetising accumulated industry knowledge: a healthcare-informatics expert's HIPAA
Compliance Frame, a consultancy's methodology Frame, a law firm's Contract Review Frame, and the
same pattern across energy, agriculture, legal, financial services and government. No single company
should build every vertical artifact; the economy needs infrastructure and a marketplace that make
it attractive for experts to build them. McKinsey: up to 40% of AI workloads in the public sector and
regulated industries could move to sovereign environments; Hugging Face's Spring 2026 report: open
source remains the foundational layer for building, evaluating and governing AI.

### 9. The landscape

Two axes — how open the standards are, how much the organisation ends up owning — and six rows, each
a legitimate choice: **foundation model providers** (OpenAI, Anthropic, Google — frontier capability
via API, the models most Cogs will call; but context, session state and evidence live in the
provider's system); **cloud AI platforms** (SageMaker, Azure ML — managed scale; the cloud's
standards, limited portability, no shared abstractions for context or work); **agent frameworks**
(LangChain, AutoGen and many harnesses — rapid construction; a harness is a capability, not a
governance model, and a natural layer inside a Cog); **agent OS platforms** (Cloudflare OS — the whole
shape, open source and usable; designed for one vendor's network, self-hosting maturing, standards
governed by one company); **enterprise software vendors** (Salesforce, ServiceNow — AI where the work
happens; context bound to one suite); and **an owned Hub on shared abstractions** (this paper — open
standards and owned deployment together, portable context, accountability shipping with the
artifacts; younger, dependent on an ecosystem forming, and the organisation shoulders ownership
responsibilities others would carry). None is a competitor to defeat; several are components an
owned Hub uses. The durable claim is compounding — open-source trust, portable context, accountable
execution and four-class network effects reinforcing each other — and the room is set by the
readiness gap: 88% of CEOs not achieving meaningful AI returns (PwC), 1% AI-mature (Deloitte), 13%
on track (McKinsey).

### 10. Strategic roadmap

Timing is set by forces beyond any participant: EU AI Act obligations phasing in (governance and
transparency first; many high-risk obligations December 2027 / August 2028 under the AI Omnibus
agreement; fines to €35M or 7% of global turnover); over 1,100 AI bills across 45 US states in 2025;
McKinsey's observation that sovereign cloud and AI migrations take three to four years because of
organisational, not technical, work. Three phases: **Phase 1 (now–6 months)** — Hub deployment
hardened, Nebi packaging standard defined, **Frame protocol published**, first Ops/Cogs/Frames/Guards
built, Desktop/Web Application released; **Phase 2 (6–18 months)** — public marketplace live, 50+ Ops
and 100+ Frames, application GA, first vertical ecosystems (health, energy, legal), initial
open-source Guard libraries; **Phase 3 (18–36 months)** — 1,000+ deployed Hubs, 500+ Ops and 2,000+
Frames, consultancies/communities/experts publishing Frames and Guards, Applied AI Society
credentialing, international Hub networks.

### 11. Conclusion

The Intelligence Economy is the next stage of enterprise computing: IT becomes Intelligence
Infrastructure; AI capability is owned, controlled, deployed, exchanged and governed as core
operational infrastructure, kept intimate with the organisation's most important data because the
organisation owns both; and organisational context is itself a first-class artifact. Nebari
anchors the open infrastructure; Hubs are the organisational loci; Frames the portable context;
Cogs the governed workers; Ops the installable units of work protected by Guards, Gates and Tracks;
Nebi the distribution mechanism; products around the Hub the way everyday knowledge workers reach
it. Accountable AI needs validation as much as context and automation. The abstractions are offered
in the spirit of NumPy, SciPy and Anaconda — shared, so the value accrues broadly. The paper's own
one-sentence framing: a distributed AI economy is "the Linux + App Store for accountable enterprise
AI".

## Where this meets PyForge — observations, not decisions

The paper's vocabulary has a near-neighbour for almost every PyForge surface. The map is for the
Spec to test; each "gap" is a candidate, not a commitment.

| Whitepaper | Nearest thing here today | Gap the paper would name |
|---|---|---|
| Intelligence Hub | The Foundry estate — `src/platform/`, the eight stations, [`pyforge-unifying-strategy.md`](pyforge-unifying-strategy.md); air-gap by design ([`enterprise-airgap.md`](enterprise-airgap.md)), OCP profile ([`local-ocp-hybrid-environment.md`](local-ocp-hybrid-environment.md)) | Nothing installable *into* the Hub as a Frame/Cog/Op/Guard object; the Hub is code, not a runtime for artifacts |
| Nebi | pixi + conda-forge + this recipe factory + the SelfExplainML channel + the bmad-suite metapackage — the very lineage the paper cites (pixi on conda) | No package format for Frames/Cogs/Ops/Guards; whether Nebi/Nebari are packaged anywhere we can consume is unverified |
| Frames | `CLAUDE.md`, the verified `AGENTS.md` block, `docs/dreams/`, Specs and memlogs, `.claude/memory/` team memory (Scribe), each skill's `SKILL.md`, `docs/governance/` | Inheritance (repo → station → story) is real but informal; no open protocol, no field-level sharing, no feedback channel to an accountable owner beyond git review |
| Cogs | Station skills and personas (`bmad-agent-*`), `conda-forge-expert`, the harness = Claude Code / bmad-loop; the bmad-suite conda packages are the closest "installable unit with declared tools" | Not versioned as a worker with declared permissions and governance parameters; harness choice is not hidden behind a Cog boundary |
| Ops | bmad-loop runs, `marshal factory spin`, the CFE lifecycle loop, pixi tasks, the legacy workflow specs (`feedstock-platform-expansion`, `feedstock-failure-remediation`) | No Op manifest; no *declared* validation strategy per run — the checks exist but are implicit in policy TOML and detectors |
| Guards | ~30 `*-check` detectors, Warden (sole PR verdict), pyforge-doctor sources (advisory), `bmad-review` lenses, [`bmad-eval-quality.md`](bmad-eval-quality.md) (measuring the reviewer) | Categories present: algorithmic, consensus (parallel adversarial review), expert (operator gates), regression/drift (`bmad-drift-check`, spec-surface). Thin or absent: source-grounding of LLM output, outcome Guards |
| Gates | bmad-loop `gate_mode`, `bmad-loop-resolve` escalation, the landing rules of [`pr-lifecycle.md`](pr-lifecycle.md), the operator-confirmation policies in `AGENTS.md` | Autonomy is a repo-wide setting, not granted per engagement — the same observation [`risk-tiered-review-depth.md`](risk-tiered-review-depth.md) makes |
| Tracks | `sprint-status-ledger.yaml`, [`landing-evidence-grammar.md`](landing-evidence-grammar.md), [`durable-runs.md`](durable-runs.md), the deferred-work ledger, run `state.json`, memlogs | No single structured evidence record per run with an explicit retention policy; evidence is spread across several files with different shapes |
| Organizational Memory | Scribe's GraphStore + `.claude/memory/` + per-user auto-memory + `_bmad-output/` | We sit at the paper's simplest tier (a versioned directory); no semantic retrieval over runs, no "ability to forget" policy |
| Desktop/Web Application | The `django-*` station portals, the factory console, the artifact console, Atlas's Vizro board ([`secure-live-dashboards.md`](secure-live-dashboards.md)) | No Frame composition UI, no in-workflow Gate prompts, no Track view for non-admins |
| Marketplace | conda-forge itself, plus the SelfExplainML channel ([`bmad-suite-channel-product.md`](bmad-suite-channel-product.md)) | Exchanges packages, not Frames/Guards with provenance attached |
| Intelligent Ops Factory | The "Dream to Code" pipeline — this repo *is* an ops factory for packaging and station software | The paper's factory produces an organisation's SOPs as installable Ops; ours produces code and recipes |

One honest tension the Spec must carry: the paper lists Claude Code among the rented black boxes,
and this factory runs on it. In the paper's own terms PyForge rents the model and the harness while
owning the context, the workflows, the checks and the evidence — which is exactly the split the
paper says matters most, but it should be stated, not assumed.

## What it might look like when real — candidate shapes for the Spec, none chosen

1. **Vocabulary alignment only.** A mapping from the Charter's Lexicon and the station roster to
   Frames/Cogs/Ops/Guards/Gates/Tracks, recorded once in [`pyforge-charter.md`](pyforge-charter.md)
   or the Unifying Strategy — the cheapest possible realisation; no code.
2. **Frames as first-class.** Once the Frame protocol is published (a Phase 1 milestone in the paper,
   not yet observed), publish the repo's own context — the `AGENTS.md` block, station personas,
   the recipe-authoring conventions — as Frame-shaped artifacts with named owners; a Community
   Frame for local-recipes would be the paper's use case 3 applied to ourselves.
3. **A declared validation strategy per run.** A bmad-loop run or `marshal factory spin` declares its
   Guards by stage, its Gates as threshold rules and its Track contents/retention; the several
   evidence files converge on one structured Track. Landing-evidence grammar and durable-runs are
   the precedents.
4. **Guards as a library.** Expose detectors, Warden axes and review lenses as reusable Guards with a
   declared category (the paper's seven), so a Spec can say which categories it lacks.
5. **Package the Nebari/Nebi lineage where missing.** A Mason/CFE lane: verify with `lookup_feedstock`
   and `pypi_intelligence` whether `nebari`, `nebari-infrastructure-core` and `nebi` exist on
   conda-forge or PyPI, and build local recipes if not — a green local build ends the task, no
   external PR without an ask.

## What is real

Nothing in the repo yet; only the whitepaper and this seed. By the paper's own status table, Cogs
and Ops as installable objects and the Op manifest are "in active development", the Frame protocol
is a milestone not yet published, and the accountability-plane runtime and the marketplace are
"thesis". Dream-first applies: `bmad-spec` under `pyforge-steward` produces the contract, and the
contract chooses among the candidates above before any code.

## Constraints

- **Dream-first.** No code from this file; the Spec decides scope.
- **The whitepaper is the source of record.** This distillation must not drift into claims the paper
  does not make; re-verify any statistic or vendor fact at intake (the paper itself marks entries it
  could not re-verify), and re-fetch by URL + hash before citing a later revision.
- **Copyright.** Distilled in our words with short attributed quotations; the PDF is not tracked and
  is not to be committed.
- **Foundry invariants stand.** `src/platform/` never imports `pyforge.*`; the infra-kinds lock and
  AD-1 (re-affirmed 2026-09-05) are untouched by anything here — the paper's Organizational Memory
  menu is *its* menu, not a licence to add stores to the platform.
- **One PR verdict.** Warden stays the sole gate; doctor findings stay advisory; "Guard" language must
  not mint a second verdict.
- **No implied platform adoption.** Naming Nebari/Nebi here does not adopt them; the Unifying Strategy
  owns the platform shape.
- **No new `docs/specs/` file; no external PRs; no outward dispatch without operator confirmation.**

## Non-goals

- Building a marketplace or a Desktop/Web Application.
- Replacing the Foundry with a Nebari deployment, or `conda-forge-expert` with anything.
- Endorsing or marketing OpenTeams; this is an architecture-and-vocabulary seed.
- Reproducing the whitepaper — this file summarises it; readers who need the text go to the source.

## Open questions for the Spec

- **Owner.** Seeded under `steward` because the Hub is the estate and Steward already owns the
  Unifying Strategy, eval-quality and the channel product. Marshal (Ops, Gates) and Scribe (Frames,
  memory) are the plausible alternatives; owning is the post, not the product.
- Is the **Frame protocol** published yet, and where? Nothing Frame-shaped should be specified before
  the open specification exists. → research backlog **RB-1**.
- Are **Nebari, `nebari-infrastructure-core`, Nebi** on conda-forge or PyPI, and under what licence?
  → research backlog **RB-2**.
- Which of the **seven Guard categories** does the repo lack entirely, and is source-grounding of LLM
  output the first to add?
- Does a **bmad-loop run** already emit enough to constitute a Track, and what retention would the
  operator want?
- Do we want the repo's **own context published as Frames** (a Community Frame for local-recipes)?

## Research backlog (pre-Spec)

Two research items queued 2026-09-05 at the operator's request. They are prerequisites for the
Spec, not stories; each closes by appending its finding here (dated, with the evidence) and by
updating the open question it answers. **Neither has been run yet.**

- **RB-1 — Has the Frame protocol been published?** The paper lists "Frame protocol published" as a
  Phase 1 (now–6 months) milestone and calls the protocol the standard that makes Frame exchange
  possible. Verify: search nebari.dev, the `nebari-dev` GitHub organisation (`gh api
  /orgs/nebari-dev/repos`, `gh search repos --owner nebari-dev frame`), ownyourintelligence.ai and
  OpenTeams' public repositories for a specification, schema or reference implementation. Record the
  URL, version, licence and the file/folder structure it prescribes — or record "not published as of
  <date>". Gates candidate shape 2 (Frames as first-class): nothing Frame-shaped is specified before
  an open specification exists.
- **RB-2 — Are Nebari, `nebari-infrastructure-core` and Nebi on conda-forge (and PyPI)?** Verify each
  name — plus the hyphen/underscore, `-py` and `-python` spellings the PyPI→conda mapping rule
  requires — with `lookup_feedstock`, `get_conda_name` and `pypi_intelligence` from the conda-forge
  MCP server, and cross-check the `nebari-dev` GitHub organisation for the source repositories.
  Record feedstock / PyPI name, latest version, licence, maintainers and whether rxm7706 can modify
  the feedstock. Gates candidate shape 5 (package the lineage where missing); this is a Mason /
  `conda-forge-expert` lane — a green local build ends the task, and no external PR is opened
  without an ask.

## Kinships

- [`pyforge-unifying-strategy.md`](pyforge-unifying-strategy.md) — the Foundry as the owned Hub; the
  platform shape this seed must not re-decide.
- [`pyforge-charter.md`](pyforge-charter.md) — the Guild and its Lexicon; Smiths are the nearest
  thing to Cogs, and the Lexicon is where a vocabulary alignment would land.
- [`packaging-factory.md`](packaging-factory.md), [`bmad-suite-channel-product.md`](bmad-suite-channel-product.md),
  [`bmad-suite-metapackage.md`](bmad-suite-metapackage.md) — the conda/pixi lineage the paper cites as
  Nebi's own foundation; the channel as a marketplace in miniature.
- [`bmad-eval-quality.md`](bmad-eval-quality.md), [`risk-tiered-review-depth.md`](risk-tiered-review-depth.md)
  — Guards on the reviewer and risk-proportional validation: the accountability plane already
  arriving piecemeal.
- [`landing-evidence-grammar.md`](landing-evidence-grammar.md), [`durable-runs.md`](durable-runs.md),
  [`deferred-work-visibility.md`](deferred-work-visibility.md), [`pr-lifecycle.md`](pr-lifecycle.md) —
  Tracks and Gates as we practise them today.
- [`team-memory.md`](team-memory.md) (archived into [`pyforge-scribe.md`](pyforge-scribe.md)) —
  Organizational Memory at the paper's simplest tier.
- [`agentic-sdlc-autonomy.md`](agentic-sdlc-autonomy.md) — the four views of autonomy; the paper's
  "autonomy granted per engagement" is the same axis seen from the employer's side.
- [`agent-portability.md`](agent-portability.md) (archived) — harness-agnostic Cogs echo the
  Portability contract in `AGENTS.md`.
- [`enterprise-airgap.md`](enterprise-airgap.md), [`local-ocp-hybrid-environment.md`](local-ocp-hybrid-environment.md)
  — sovereignty as we already build it.
- [`regenerable-factory.md`](regenerable-factory.md) — the Dream → Spec → code chain is our Frame
  inheritance graph and our Track of record at once.

## Realization log

- **2026-09-05** — Seeded from the whitepaper (Revision 9, August 2026), read in full (46 pages);
  section-complete distillation with the vocabulary map, candidate shapes and open questions above.
  No adoption decided; owner `steward` as the post. Next: `bmad-spec` under `pyforge-steward`
  (dream-chain INV-1 names the expected Spec path) to choose which shape PyForge takes up.
- **2026-09-05 (later)** — Research backlog added at the operator's request: RB-1 (is the Frame
  protocol published?) and RB-2 (are Nebari, `nebari-infrastructure-core` and Nebi on conda-forge /
  PyPI?). Neither has been run; both precede the Spec.
