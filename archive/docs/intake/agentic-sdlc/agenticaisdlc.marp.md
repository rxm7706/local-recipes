---
marp: true
size: 16:9
paginate: true
theme: default
style: |
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
  section { background:#F6F4EE; color:#0E1C30; font-family:'IBM Plex Sans',sans-serif; font-size:25px; padding:70px 90px; }
  h1 { font-family:'Space Grotesk',sans-serif; font-weight:600; font-size:50px; line-height:1.07; letter-spacing:-0.02em; margin:0 0 0.4em; }
  h6 { font-family:'IBM Plex Mono',monospace; font-weight:500; letter-spacing:0.22em; text-transform:uppercase; color:#2F86DD; font-size:15px; margin:0 0 0.2em; }
  strong { color:#C8901A; font-weight:600; }
  code { font-family:'IBM Plex Mono',monospace; background:rgba(14,28,48,0.08); padding:1px 5px; border-radius:4px; }
  pre { background:rgba(14,28,48,0.05); border:1px solid rgba(14,28,48,0.18); border-radius:6px; font-size:18px; line-height:1.5; }
  pre code { background:none; padding:0; }
  ul,ol { line-height:1.5; } li { margin:0.18em 0; }
  a { color:#2F86DD; }
  section::after { color:#8A94A3; font-family:'IBM Plex Mono',monospace; font-size:14px; }
---

<!-- _backgroundColor: #0B1626 -->
<!-- _color: #F6F4EE -->

###### A FIELD GUIDE FOR ENGINEERS

# Agentic AI across the software lifecycle

Not autocomplete on steroids — a structured way to build software with AI agents as expert collaborators, from first idea to shipped code.

<!--
Open here. This deck explains what agentic AI across the software development lifecycle actually looks like in practice, using the BMad Method as our concrete framework. Audience: working engineers. The arc runs in six acts: the case for change, spec-driven development, choosing a framework, the BMAD agent team, the four phases, and scaling plus the ecosystem.
-->

---

###### CONTENTS

# The story arc, in six acts

- **The case for change** — Why AI-augmented isn’t enough
- **Spec-driven development** — The operating model — docs as the brain
- **Choosing your framework** — The SDD landscape, and why BMAD
- **The BMAD agent team** — Roles, party mode & file-based artifacts
- **The four phases** — Analysis → planning → solutioning → build
- **Scale, governance & ecosystem** — Adapting the method & extending it

<!--
The road map. Six acts. First, why the augmented SDLC most teams run isn't enough and what agentic means. Second, spec-driven development as the operating model. Third, the tool landscape and why we settle on BMAD. Fourth, how the BMAD agent team is structured. Fifth, a walk through the four phases end to end. Sixth, scaling the method, governing it, and the wider ecosystem. About forty minutes end to end; each act stands alone if you want to jump.
-->

---

<!-- _backgroundColor: #0B1626 -->
<!-- _color: #F6F4EE -->

###### ACT I

# The case for change

Why the AI-augmented SDLC most teams already run isn’t enough — and what *agentic* actually means.

<!--
Act one. Why the AI-augmented status quo isn't enough: the shift, what agentic AI-SDLC means, the maturity spectrum, and the core idea.
-->

---

###### THE SHIFT

# The problem isn't that AI writes bad code. It's that it makes decisions you never saw.

**Prompt-and-pray**

You describe a feature, the model produces average code from vague context, and the architectural choices are buried inside the output. Great for a snippet. Fragile for a system.

**Agentic development**

Specialized agents guide you through a real process — analysis, planning, design, build — producing decisions and documents you can read, review, and reuse.

<!--
Frame the problem. Most AI coding tools generate for you and leave you to sort out the mess. That works for a snippet and falls apart on a real system. The shift is from a tool that types to a collaborator that follows a process.
-->

---

###### DEFINITION

# What is the agentic AI‑SDLC?

Not a new lifecycle — the one you already know: **analyze → plan → design → build → test → ship**. What changes is *who* does the work and *how* state moves between phases.

- **Same phases** — decades of agile practice still apply; AI runs inside the process, it doesn't replace it.
- **New workers** — specialist agents (analyst, PM, architect, developer) do each phase's work; you review and decide.
- **New contract** — specs carry the state between phases, not meetings, memory, or chat scrollback.

<!--
Define the term before going further. The AI-SDLC is not a new lifecycle — it's the one you already know: analyze, plan, design, build, test, ship. What changes is who does the work and how state moves between phases. Specialized agents execute each phase, humans keep judgment and approval, and persistent specs — not meetings or chat memory — carry the state from one phase to the next.
-->

---

###### THE MATURITY SPECTRUM

# From AI-augmented to agentic: who executes the phase?

1. **Manual** — humans do everything; no AI in the loop.
2. **AI-augmented** — humans execute, AI assists (autocomplete, generated tests, review hints). Plans and decisions stay in heads and meetings.
3. **Agentic** *(this deck)* — specialist agents run each phase; humans direct and gate through specs and reviews.
4. **Autonomous** — unattended loops (dev-auto): intent in, code out; humans set direction and review outcomes.

The jump from 2 to 3 isn't better models — it's **where the context lives**: out of your head and chat history, into documents agents read and write.

<!--
Where does agentic sit relative to the AI-augmented SDLC most teams already have? It's a spectrum. Manual: humans do everything. AI-augmented: humans still execute every phase, AI assists inside each one — autocomplete, generated tests you curate, review hints. Agentic: agents execute the phases, humans direct and gate through specs — that's this deck. Autonomous: unattended loops where you set intent and review outcomes. The real jump from augmented to agentic: context moves out of your head and chat history into documents agents read and write.
-->

---

###### THE CORE IDEA

# Agents are collaborators, not oracles

Traditional AI tools do the thinking **for** you. Agentic workflows act as **expert collaborators** who bring the best thinking **out** of you.

The output isn't just code. It's a chain of reviewable artifacts — a brief, a spec, an architecture, a story — each one grounding the next.

<!--
The core idea in one line: agents are collaborators, not oracles. They pull your best thinking out through a structured process instead of doing the thinking for you. This is the whole philosophy.
-->

---

<!-- _backgroundColor: #0B1626 -->
<!-- _color: #F6F4EE -->

###### ACT II

# Spec-driven development

The operating model: treat the documentation as the brain, agents as transient workers.

<!--
Act two. The operating model everything else builds on — spec-driven development, specs as code, and the docs-are-the-brain mental model.
-->

---

###### DEFINITION

# What is spec‑driven development?

Write the specification **first** — a precise, versioned document of behavior, constraints, and acceptance criteria — then have AI generate and validate code **against it**. The spec is the contract; the code is its translation.

```
VIBE CODING    prompt → code → hope
SPEC-DRIVEN    intent → spec → human review → generate → validate
```

- **Written first** — nothing is built that wasn't specified.
- **An executable contract** — tests and reviews validate against the spec.
- **Versioned in git** — specs evolve by amendment, next to the code they govern.

<!--
Define spec-driven development before we build on it. SDD means you write the specification first — a precise, versioned document stating behavior, constraints, and acceptance criteria — and the AI generates and validates code against it. Contrast that with vibe coding: prompt, get code, hope. In SDD the pipeline is intent → spec → human review → generate → validate. The spec is the contract; a bug means the contract was wrong or violated.
-->

---

###### THE OPERATING MODEL

# Specs are code. Documentation is programmable infrastructure.

- **Institutionalize knowledge** — Individual expertise becomes a permanent, accessible markdown asset — no key-person dependencies.
- **Automate execution** — Structured specs become machine-readable instructions that drive tasks, processes, and procedures.
- **Compound intelligence** — Every document is clean semantic context — each agent run makes the next one smarter.

Work is sharded into **modular, atomic, versioned step-files** in the repo — eliminating LLM context drift.

<!--
Spec-driven development is the universal operating model. Specs aren't paperwork — they're programmable infrastructure. Three payoffs: expertise becomes a permanent asset instead of living in one person's head; structured specs become machine-readable instructions agents can execute; and every document compounds — it's semantic context that makes the next agent run smarter. V6 shards work into atomic, versioned step-files to eliminate context drift.
-->

---

###### THE MENTAL MODEL · CONTEXT ENGINEERING

# The documentation is the brain. Agents are transient workers.

Agents read from and write to persistent docs — nothing relies on an LLM’s leaky chat memory. The lifecycle is a funnel of increasing resolution:

- **WHY** — Analysis — stress-test the idea into a brief
- **WHAT** — Planning — the PRD is the source of truth; if it’s not there, it doesn’t exist
- **HOW** — Solutioning — architecture and tasks, frozen before code
- **BUILD** — Implementation — translate the spec into syntax

Each document becomes the input to the next, so every agent inherits the decisions already made — and no agent touches code until the **what** and the **how** are frozen in a text file.

<!--
The mental model that makes all of this click: the documentation is the brain, and agents are transient workers who read from and write to it. Never rely on an LLM's leaky chat memory to hold the plan. And the SDLC isn't a loop — it's a funnel of increasing resolution: why, what, how, build. No agent writes code until the what and the how are frozen in a text file.
-->

---

<!-- _backgroundColor: #0B1626 -->
<!-- _color: #F6F4EE -->

###### ACT III

# Choosing your framework

The spec-driven landscape in 2026 — and why we settle on BMAD.

<!--
Act three. SDD is a category now: the three tool families, method versus machinery, and why BMAD earns the choice.
-->

---

###### THE LANDSCAPE · 2026

# SDD is a category now — three families of tools

**Agent-team frameworks** — a simulated agile team: role personas, file-based handoffs, full lifecycle.
- **BMAD-METHOD** — the archetype: 12+ agents, MIT, this deck's framework
- **Agent OS** — standards injection for house conventions

**Spec-first scaffolding** — a specify → plan → tasks structure on a coding session.
- **GitHub Spec Kit** — constitution-driven; broadest agent support
- **AWS Kiro** — spec-native IDE; EARS requirements built in
- **GSD** — lightweight meta-prompting for solo work

**Living specs** — the spec is the evolving source of truth, synced with code.
- **OpenSpec** — delta specs; lightest fit for brownfield
- **Tessl** — betting on spec-as-source
- **Augment Intent** — agents write changes back to the spec

**Agent infrastructure** — CrewAI · Agno · LangGraph · AutoGen: orchestration SDKs (machinery, not methodology). Rules of thumb: greenfield paper trail → **BMAD** · brownfield → **OpenSpec** · broad default → **Spec Kit** · AWS-native → **Kiro**.

<!--
SDD is a category now, not one tool — 30+ frameworks by early 2026. Three broad buckets. Agent-team frameworks simulate a full agile team with role personas and file-based handoffs — BMAD is the archetype and what this deck follows. Spec-first scaffolding adds a specify-plan-tasks structure to a coding session — GitHub Spec Kit with its constitution, AWS Kiro baking specs into the IDE, GSD as the lightweight option. Living-spec tools treat the spec as the evolving source of truth — OpenSpec with delta specs for brownfield, Tessl betting on spec-as-source, Augment Intent writing changes back to the spec. Below all of these sits agent infrastructure — CrewAI, Agno, LangGraph, AutoGen — orchestration SDKs that provide multi-agent machinery, not a development methodology. Rules of thumb: complex greenfield with a paper trail, BMAD. Brownfield and lightweight, OpenSpec. Broad default, Spec Kit. AWS-native, Kiro.
-->

---

###### METHOD × MACHINERY

# Method and machinery are different layers

- **Need an SDK *with* BMAD? — usually not.** BMAD installs as skills into Claude Code, Cursor, or Codex; the host is already the runtime (tool calling, files, context) and humans drive the checkpoints. Reach for CrewAI or LangGraph only to build your own *pipeline product* — then personas become crews/nodes and BMAD's artifacts stay the contracts.
- **Need a method *with* an SDK? — for software, yes.** Orchestration SDKs are empty machinery (no roles, artifacts, or gates). Building software? **Borrow** BMAD (personas → roles, artifacts → messages, gates → edges) or reinvent every piece. Not building software — research crews, bots, data pipelines? SDD is irrelevant.

**The asymmetry** — the methodology defines *what* agents do and hand off; the SDK only changes *where* they run. Method without SDK works out of the box; SDK without method only when you're not shipping software.

<!--
Method and machinery are different layers, and engineers ask two questions when they see orchestration SDKs next to BMAD. First: do you need an SDK with BMAD? Usually not — BMAD installs as skills into your coding agent (Claude Code, Cursor, Codex), which is already the runtime: tool calling, files, context, with humans driving checkpoints. Reach for CrewAI or LangGraph only to build your own pipeline product — unattended CI loops, parallel story agents — where personas become crews or graph nodes and BMAD's artifacts stay the contracts. Second, the reverse: on an SDK already, do you need a method? For software, yes — orchestration SDKs are empty machinery with no roles, artifacts, or gates; borrow BMAD (personas become roles, artifacts the messages, gates the edges) or reinvent them. Not building software — research, bots, data pipelines? SDD is irrelevant. The relationship is asymmetric: method without SDK works out of the box; SDK without method only when you're not shipping software.
-->

---

###### WHY THIS FRAMEWORK

# Four reasons BMAD earns the choice

- **Structure without rigidity** — Guardrails, not gates: skip optional phases, load agents directly, reorder workflows once you know the flow.
- **Context persistence** — Every plan is a file in git. Start a fresh chat and agents pick up where you left off; the whole team sees the same artifacts.
- **Scale-domain-adaptive** — A bug fix gets 3 commands; an enterprise system gets security & compliance reviews. A dating app and a medical device don’t get the same planning.
- **100% free & open** — MIT license. No paywalls, no gated content, no premium tiers — and an ecosystem of modules on top.

<!--
Why this framework and not another from the landscape? Four reasons. Structure without rigidity: phases are guardrails, not gates you can't skip — drop optional phases, load agents directly, reorder once you know the flow. Context persistence: every plan is a file in git — new chat, agents pick up where you left off; the whole team sees the same artifacts. Scale-domain-adaptive: it sizes the ceremony to the work — bug fix gets three commands, an enterprise system gets compliance and security reviews — and adapts to domain: a dating app and a medical device don't get the same planning. And it's 100% free, MIT, no gated content.
-->

---

<!-- _backgroundColor: #0B1626 -->
<!-- _color: #F6F4EE -->

![bg brightness:0.45](https://dev-to-uploads.s3.amazonaws.com/uploads/articles/u0pbo16u36ywgrbym3eb.jpeg)

###### ACT IV

# The BMAD agent team

A team of named specialists — spec-driven, document-anchored, phase-gated.

**MIT** · **12+** agents · **34+** workflows · runs in your coding agent

<!--
Act four — the bridge into the concrete half of the deck. Of that landscape, we use BMAD-METHOD as the working example: the archetype of the agent-team family, and the most complete open implementation of everything covered so far — spec-driven, doc-anchored, phase-gated. Free and MIT-licensed, 12+ named agents, 34+ workflows, and it runs inside the coding agent you already use. Up next: the agent team, then the four phases end to end.
-->

---

###### THE CREW · NAMED AGENTS

# A team of specialists, one per phase

| Agent | Role | Phase | Owns |
|---|---|---|---|
| **Mary** | Business Analyst | Analysis | brainstorming, research, briefs, PRFAQs |
| **Paige** | Technical Writer | Analysis | docs, diagrams, doc validation |
| **John** | Product Manager | Planning | PRDs, epics & stories, readiness |
| **Sally** | UX Designer | Planning | experience & design specs |
| **Winston** | System Architect | Solutioning | technical architecture, alignment |
| **Amelia** | Senior Engineer | Implementation | story execution, code review, sprints |

<!--
You don't talk to one monolithic AI. You talk to named agents, each anchored to a phase and a role, each with a persona and a menu of skills. Say 'Hey Mary, let's brainstorm' and she activates. The point: it feels like a team of specialists, not a slash-command menu.
-->

---

###### WHY PERSONAS

# “Hey Mary, let’s brainstorm.” And she just gets on with it.

- **Menu** — you meet the tool halfway: memorize that brainstorming is a skill on the analyst, not the PM.
- **Blank prompt** — you guess the magic words: results depend on how you happened to phrase the ask.
- **Named agent** — you talk to a teammate: consistent persona, discoverable skills, menu as fallback.

Identity is fixed, behavior is customizable — teams reshape an agent’s principles, integrations, and templates without forking the framework.

<!--
Why personas instead of a menu or a blank prompt? A menu makes you memorize where each capability lives. A blank prompt makes you guess the magic words. Named agents invert it: you say what you want, in your words, to a teammate who already knows the work and their menu is there as a fallback.
-->

---

###### MULTI-AGENT COLLABORATION

# Party mode: the whiteboard meeting, minus the scheduling

```
you:       bmad-party-mode PM, Architect, Security — we're adding payments
PM:        what payment methods do users actually expect?
Architect: Stripe for PCI scope; idempotent webhooks for reliability
Security:  never store raw cards; rate-limit and audit-log every transaction
```

- **Design reviews** — UX, architect, and developer weigh a screen together.
- **Troubleshooting** — dev, DevOps, and DBA triangulate a production issue.
- **Architecture calls** — trade-offs argued from three seats before you commit.

<!--
One agent at a time is the default, but some decisions need several perspectives at once. Party mode brings multiple personas into one session and lets them respond in turn. Three canonical uses: a design review where UX, architect, and developer weigh in together; a troubleshooting session where dev, DevOps, and DBA triangulate a production issue; and architecture decisions where PM, architect, and security argue trade-offs before you commit. It's the whiteboard meeting, minus the scheduling.
-->

---

###### QUICK REFERENCE

# The execution matrix

| Phase | Persona | Reads | Produces |
|---|---|---|---|
| **Analysis** | Mary | Raw idea / brain dump | `brief.md` |
| **Planning** | John | `brief.md` | `prd.md` |
| **Solutioning** | Winston | `prd.md` | `architecture.md` · epics & stories |
| **Implementation** | Amelia | `architecture.md` · story files | source code + tests |

Each output becomes the next persona's input — the handoff is a **file, not a chat thread**.

<!--
One reference slide before we walk the phases: the execution matrix. Each phase has a persona, an input artifact, and an output artifact. Each output becomes the anchor for the next persona — the handoff is a file, not a chat thread. Keep this in your head as we go phase by phase.
-->

---

###### THE SKILL ROSTER · V6

# Every phase ships with skills, every skill has an owner

| Phase | Owner(s) | Skills |
|---|---|---|
| **01 Analysis** | Mary *(Analyst)* · Paige *(Writer)* | brainstorming · forge-idea · market / domain / technical-research · product-brief · prfaq · document-project |
| **02 Planning** | John *(PM)* · Sally *(UX)* | prd *(create / update / validate)* · ux |
| **03 Solutioning** | Winston *(Architect)* | architecture · create-epics-and-stories · check-implementation-readiness |
| **04 Implementation** | Amelia *(Developer)* | sprint-planning · create-story · dev-story · code-review · correct-course · sprint-status · retrospective · qa-generate-e2e-tests |

**Cross-cutting** — help · party-mode · customize · generate-project-context · advanced-elicitation · quick-dev · dev-auto

*All skills invoked as `bmad-*` — directly, or from an agent's menu.*

<!--
The full skill roster in the latest release, aligned to agents and phases. Every workflow ships as an installable skill — invoke it directly by its bmad- id, or through the owning agent's menu. Mary and Paige cover analysis, John and Sally planning, Winston solutioning, Amelia the whole implementation loop. And a set of cross-cutting skills — help, party-mode, customize, project-context generation — plus the quick-dev and dev-auto parallel track work across all phases.
-->

---

###### IN YOUR REPO

# What it physically looks like: two folders

```
your-project/
├─ _bmad/                      ← the machinery
│  └─ core/  bmm/  agents/  workflows/
└─ _bmad-output/               ← your artifacts
   ├─ planning-artifacts/
   │  ├─ PRD.md
   │  ├─ architecture.md
   │  └─ epics/                ← stories
   ├─ implementation-artifacts/
   │  └─ sprint-status.yaml
   └─ project-context.md
```

- **No context loss** — Start a new chat — agents pick up from the files.
- **Version controlled** — Plans live in git, right next to the code they govern.
- **Team visibility** — Everyone — human or agent — reads the same artifacts.
- **AI grounding** — Agents reference concrete documents, not hallucinations.

<!--
What this all physically looks like: two folders in your repo. _bmad holds the machinery — agent definitions, workflows, config. _bmad-output holds your artifacts, split in v6 into planning-artifacts (PRD, architecture, epics) and implementation-artifacts (sprint status), plus a project-context file. Four consequences: no context loss because a new chat picks up from the files; version control because plans live in git next to code; team visibility because everyone reads the same documents; and AI grounding because agents cite concrete files instead of hallucinating.
-->

---

<!-- _backgroundColor: #0B1626 -->
<!-- _color: #F6F4EE -->

![bg brightness:0.45](https://dev-to-uploads.s3.amazonaws.com/uploads/articles/ih3d75uluo0vuuad29ok.png)

###### ACT V

# The four phases

Analysis, planning, solutioning, implementation — how work flows from idea to shipped code.

<!--
Act five. Chapter break opening the phase walkthrough.
-->

---

###### THE MAP

# Four phases, one throughline

1. **Analysis** *(optional)* — explore the problem before committing. → Brainstorm · Research · Brief · PRFAQ
2. **Planning** *(what & why)* — define what to build, and for whom. → PRD · UX spec
3. **Solutioning** *(how)* — decide how, break work into stories. → Architecture · Epics · Readiness
4. **Implementation** *(build)* — build it, one story at a time. → Story · Dev · Review · Retro

<!--
This is the map for the rest of the deck. Four phases: Analysis, Planning, Solutioning, Implementation. Each is a set of workflows that produce documents. We'll walk through each one. Phase 1 is optional; the real spine is Planning to Implementation.
-->

---

###### PHASE 01 · OPTIONAL

# Analysis

Think clearly about the product before committing to build it — attack the idea from four angles.

- `bmad-brainstorming` — **Brainstorm**: coach-facilitated ideation; pulls ideas out of you, not for you.
- `bmad-*-research` — **Research**: market, domain, and technical feasibility, grounded in reality.
- `bmad-product-brief` — **Product brief**: a 1–2 page vision when your concept is already clear.
- `bmad-prfaq` — **PRFAQ**: Working Backwards — write the launch press release before the code.

<!--
Phase 1, Analysis, is optional but it makes everything downstream sharper. Four ways to think clearly before you build: brainstorm to generate, research to ground, brief to document, PRFAQ to stress-test. Skipping analysis means your PRD is built on assumptions.
-->

---

###### PHASE 01 · IN PRACTICE

# Which tool, when?

| Your situation | Reach for |
|---|---|
| “I have a vague idea, not sure where to start.” | **Brainstorming** |
| “I need to understand the market before deciding.” | **Research** |
| “I know what I want — just document it.” | **Product Brief** |
| “Make sure this is actually worth building.” | **PRFAQ** |

Brief and PRFAQ both feed the PRD — the brief is collaborative discovery; the PRFAQ is a gauntlet.

<!--
Practical guidance: which analysis tool fits your situation. Vague idea, brainstorm. Need market truth, research. Know what you want, brief. Want it stress-tested, PRFAQ. Both brief and PRFAQ feed the PRD — the difference is how much challenge you want.
-->

---

###### PHASE 02 · WHAT & WHY

# Planning

Define what to build and for whom. Everything downstream inherits the clarity — or the vagueness — you set here.

- `bmad-prd` — **Product Requirements**: facilitated discovery; one skill, three intents — create, update, validate.
- `bmad-ux` — **UX Design**: when experience matters, a spine pair — `DESIGN.md` (visual) + `EXPERIENCE.md` (behavioral).

<!--
Phase 2, Planning. This is where you define what to build and for whom. The PRD is the anchor — it answers what and why, and every downstream document inherits its clarity or its vagueness. UX runs alongside when experience matters.
-->

---

###### PHASE 03 · HOW → UNITS OF WORK

# Solutioning

Decide how to build it, then break the work into implementable units.

1. **Architecture** — make technical decisions explicit so every agent builds consistently.
2. **Epics & stories** — break requirements into focused, implementable stories.
3. **Readiness check** *(gate)* — a pass / concerns / fail decision before implementation begins.

<!--
Phase 3, Solutioning. Translate what into how. The architect makes technical decisions explicit, the PM breaks requirements into epics and stories, and a readiness gate decides pass, concerns, or fail before anyone writes code.
-->

---

###### WHY IT MATTERS

# Decide the hard things once — or agents decide them differently.

- **Without solutioning** — Agent 1 builds Epic 1 with REST, Agent 2 builds Epic 2 with GraphQL → inconsistent API, integration pain.
- **With solutioning** — the decision is made once (GraphQL for all); every agent follows it → consistent build, clean integration.

**10× cheaper** — catching alignment issues in solutioning beats discovering them mid-sprint.

<!--
Concrete reason solutioning matters. Without shared architectural decisions, two agents on two epics pick REST and GraphQL independently, and integration becomes a nightmare. Decide once, up front, and everyone follows. Catching alignment issues here is 10x cheaper than during implementation.
-->

---

###### PHASE 04 · BUILD

# Implementation

Build it one story at a time — each with complete, focused context so the dev agent never guesses. Sprint planning sequences the cycle once; then repeat the loop.

- `bmad-sprint-planning` — sequence the work
- `bmad-create-story` — prep the story with full context
- `bmad-dev-story` — working code + tests
- `bmad-code-review` — validate quality

<!--
Phase 4, Implementation. Build one story at a time. Each story carries complete, focused context so the dev agent isn't guessing. Sprint planning sequences the work once; then it's a tight loop per story.
-->

---

###### THE HEARTBEAT · PER-STORY LOOP

# A tight loop, one story at a time

- **Create story** — assemble focused context
- **Dev story** — implement: code + tests
- **Code review** — approve or revise
- **Retrospective** — at each epic's end

`correct-course` handles mid-sprint changes — and you choose how tight the automation runs.

<!--
Zoom into the loop. Create story, implement, review, and on to the next — with correct-course to handle mid-sprint changes and a retrospective at the end of each epic. Human stays in the loop; you choose how tight. This is the heartbeat of implementation.
-->

---

<!-- _backgroundColor: #0B1626 -->
<!-- _color: #F6F4EE -->

![bg brightness:0.45](https://dev-to-uploads.s3.amazonaws.com/uploads/articles/6t0wbftde1briycf653f.png)

###### ACT V · SPECIAL FOCUS

# Testing that doesn’t rot

Why AI-generated tests decay, and how the Test Architect treats testing as an engineering discipline.

<!--
Still act five — a special focus within the method: chapter break introducing the TEA testing module.
-->

---

###### TESTING · TEA MODULE

# AI-generated tests rot. Test architecture doesn’t.

“Write tests for this” produces assertions that match current behavior — flaky in three sprints. TEA treats testing as engineering: strategy before generation.

- **Design first** — risk-based priorities: probability × impact scores every scenario P0–P3.
- **Flakiness killed** — network-first patterns wait on real responses, not `waitForTimeout(2000)`.
- **Release gate** — tests map to requirements; the gate rules PASS / CONCERNS / FAIL / WAIVED with evidence.

`bmad-tea → framework → test-design → automate` — zero to a risk-planned suite in ~30 min.

<!--
The complaint heard most from teams using AI for development: the tests are garbage. They pass, they look fine in review, and three sprints later half are flaky and nobody trusts the suite — because the AI had no testing strategy, it just wrote assertions matching current behavior. TEA, the Test Architect module, treats testing as an engineering discipline: risk-based test design scores probability times impact into P0 to P3 priorities, so the checkout flow gets deep coverage and the settings page gets a smoke test. Network-first patterns kill flaky waits. And the trace workflow maps tests to requirements and issues a release-gate decision: pass, concerns, fail, or waived.
-->

---

<!-- _backgroundColor: #0B1626 -->
<!-- _color: #F6F4EE -->

![bg brightness:0.45](https://dev-to-uploads.s3.amazonaws.com/uploads/articles/kvs7iq8i1o7cij2qg1oe.png)

###### ACT VI

# Scale, governance & ecosystem

The wider ecosystem — testing, game dev, creative intelligence, and your own custom agents.

<!--
Act six. Chapter break opening the final act: governance at scale, the module ecosystem, and how to get started.
-->

---

###### SCALE-ADAPTIVE

# Three tracks, sized to the work

| Track | Best for | Documents created |
|---|---|---|
| **Quick Flow** | Bug fixes, clear scope · 1–15 stories | Tech-spec only |
| **BMad Method** | Products & platforms · 10–50+ stories | PRD + Architecture + UX |
| **Enterprise** | Compliance, multi-tenant · 30+ stories | + Security + DevOps |

Story counts are guidance, not rules — `bmad-help` recommends a track if you're unsure.

<!--
BMad v6 offers three planning tracks, and bmad-help picks one for you. Quick Flow for bug fixes and clear-scope work (1-15 stories) produces just a tech-spec. BMad Method for products and platforms (10-50+ stories) produces a PRD, architecture, and UX. Enterprise for compliance and multi-tenant systems (30+ stories) adds security and DevOps. Story counts are guidance, not definitions — choose by planning need. Same primitives throughout, different depth. Quick flow for a bug fix, simple for a small feature, complex when solutioning is required, enterprise when governance is. The process adjusts to complexity instead of forcing one-size-fits-all.
-->

---

###### PARALLEL TRACK

# Small, well-understood work skips the ceremony

- **Quick Dev** (`bmad-quick-dev`) — one unified flow: clarify intent, plan, implement, review, and present. Skips phases 1–3.
- **Dev Auto** (`bmad-dev-auto`) — one unattended development-loop iteration — small intent in, code out.

*Rule of thumb: if multiple epics could be built by different agents, you need the full method. A single well-scoped change does not.*

<!--
Not everything needs four phases. For small, well-understood work there's a parallel track: quick-dev clarifies, plans, implements, reviews, and presents in one flow; dev-auto runs a single unattended iteration. Use the full method for the enterprise system, quick flow for the bug fix.
-->

---

###### THE UNIFYING IDEA · AT SCALE

# The documents are the product’s memory — at scale, a constitution

A `project-context.md` makes a dozen separate agent runs feel like one coherent team. At enterprise scale it hardens into a constitution:

- **Single source of truth** — supersedes ad-hoc practice; when conventions conflict, it wins, for humans and agents alike.
- **Agents enforce it** — they audit every PR against the mandates and report failures by citing the specific clause violated.
- **Humans amend it** — changes go through ADRs, team consensus, and versioned amendments — a living document, not a frozen one.
- **Simplicity gate** — YAGNI is codified: complexity requires documented justification, metrics, and a plan to remove it.

<!--
Pull the docs idea together and scale it. The documents aren't paperwork — they're the product's memory. A project-context file makes a dozen separate agent runs feel like one coherent team, and at enterprise scale it matures into a constitution: a single, versioned source of truth that supersedes ad-hoc practice. The interesting part: agents are empowered to enforce it — they audit every PR and cite the exact clause a change violates. Humans amend it through ADRs and sign-off. And a simplicity gate keeps complexity honest: YAGNI, with justification required.
-->

---

###### THE FLIP SIDE

# Don’t just build with agents. Build for them.

- **Interfaces** — clean DOM hierarchies, ARIA, deterministic layouts agents can navigate. No vibe UI.
- **APIs** — idempotent & self-documenting: strict OpenAPI schemas, retry-safe mutations, errors actionable enough for an agent to self-correct mid-flight.
- **The harness** — guardrails & traces: tools explicitly exposed for LLM calling, schema validation, exhaustive run-trace logs for context.

<!--
The flip side: it's not just about using agents to build — it's about building systems agents can operate. Three layers: interfaces with semantic structure and deterministic layouts, no vibe UI; APIs that are idempotent and self-documenting with errors clear enough for an agent to self-correct; and an agent harness — explicit tool exposure, strict guardrails, exhaustive run-trace logs.
-->

---

###### THE MODULE ECOSYSTEM · V6

# One core, a growing family of modules

- **BMad Method** *(core · BMM)* — the 34+ workflow framework this deck walks through. `npx bmad-method install`. Everything else builds on it.
- **BMad Builder** *(BMB)* — create your own agents & workflows.
- **Test Architect** *(TEA)* — risk-based test strategy & automation.
- **Game Dev Studio** *(BMGD)* — Unity, Unreal & Godot workflows.
- **Creative Intelligence** *(CIS)* — brainstorming, innovation, design thinking.

All MIT, all installed the same way — unsure what's next? Ask `bmad-help`.

<!--
BMAD isn't one thing — the core is a module in a wider ecosystem, and V6 leans hard into that. The core, BMM, is the 34+ workflow framework this deck walks through. On top of it, official modules extend the same scale-adaptive discipline into new domains, each installable during setup or any time after: BMad Builder to create your own agents and workflows; Test Architect (TEA) for risk-based test strategy; Game Dev Studio for Unity, Unreal, and Godot pipelines; and the Creative Intelligence Suite for brainstorming, innovation, and design-thinking facilitation. All MIT, all installed the same way. And when you're unsure what's next, the bmad-help skill tells you what to do and what's optional.
-->

---

###### EXTEND IT · BMAD BUILDER

# When the roster doesn’t cover your domain, build your own agent

Everything is a **skill** — a folder with a `SKILL.md`, following the open Agent Skills standard. Agents come in three types:

- **Stateless** — a persona and capabilities, no memory: formatters, diagram generators, focused domain experts.
- **Memory** — keeps a persistent *sanctum* of identity & knowledge files, re-read each launch: coaches, advisors.
- **Autonomous** — adds a `PULSE` file and wakes on a schedule: monitoring, curation, maintenance between sessions.

Package skills into **modules** and distribute via GitHub.

<!--
When the built-in agents don't cover your domain — HIPAA reviews, a house deployment process — BMad Builder creates your own. The packaging model: everything is a skill, a folder with a SKILL.md, following the open Agent Skills standard; agents, workflows, and utilities all ship the same way. Agents come in three types: stateless for single-session experts; memory agents that keep a persistent 'sanctum' of identity and knowledge files and greet you by name next session; and autonomous agents that add a PULSE file and wake on a schedule to work unattended. Builders run as guided conversations, then modules package skills for distribution on GitHub.
-->

---

###### THE WIDER ECOSYSTEM

# Planning runs anywhere your LLM does

**Web bundles · 6 planning coaches** — install as ChatGPT Custom GPTs, Gemini Gems, or Microsoft Copilot agents. Do the heavy planning on a flat-rate subscription, then bring polished artifacts into the IDE for implementation.

**Modules & community** — Builder, Test Architect, Game Dev Studio, Creative Intelligence Suite; plus community tools: VS Code dashboard, GitHub Projects sync, n8n automation personas, and a growing skill marketplace.

<!--
The method isn't locked to one tool. Six planning coaches ship as web bundles you can install as ChatGPT Custom GPTs, Gemini Gems, or Microsoft Copilot agents — do the heavy planning on a flat-rate subscription, then bring the artifacts into your IDE for implementation. And a growing ecosystem of modules and community tools extends the same discipline to testing, game dev, automation, and more.
-->

---

###### SEE IT IN ACTION

# From install to artifacts — drop in your own captures

- **Install & kickoff** — `npx bmad-method install`, then your first workflow prompt
- **A live agent session** — party mode or a phase workflow running in your IDE
- **The generated artifacts** — PRD, architecture & stories in `_bmad-output/` or the docs site

*Swap in your own screenshots before presenting — live captures read better than stock diagrams. Remove this slide if you'd rather present without them.*

<!--
Optional show-and-tell slide. Drop in your own screenshots to make the method concrete: the installer running in your terminal, a real workflow or party-mode session, and the generated artifacts in your editor or the docs site. Live captures land better than stock diagrams here — swap these three in before presenting. If you'd rather not use images, this slide can be removed.
-->

---

<!-- _backgroundColor: #0B1626 -->
<!-- _color: #F6F4EE -->

###### TRY IT

# Three steps to your first run

1. **Install** — `npx bmad-method install`
2. **Open your AI IDE** — Claude Code, Cursor, or Codex
3. **Ask** — `bmad-help what should I do first?`

Prerequisites: Node.js 20.12+, Python 3.10+, uv. 100% free and open source (MIT).

<!--
How to actually try it. One install command, open your AI IDE, and if you're ever unsure, ask bmad-help and it tells you what's next. It's free and open source. The fastest way to understand it is to run it once on something small.
-->

---

<!-- _backgroundColor: #0B1626 -->
<!-- _color: #F6F4EE -->

###### WHAT TO REMEMBER

# Six principles that transfer to any tool

- **Structure beats prompting** — A process gets better output than a clever one-liner.
- **Documents are context** — Each artifact grounds the next agent’s decisions.
- **Decide hard things once** — Explicit architecture prevents agent conflicts.
- **Match ceremony to scale** — Quick flow for small; full method for complex.
- **Keep a human in the loop** — You choose how tight the automation runs.
- **Fix the doc, not the code** — Wrong output is an upstream spec flaw — correct it and rerun.

<!--
The takeaways that transfer even if you never use this specific framework. Structure beats prompting. Documents are context. Decide the hard things once. Match ceremony to complexity. Keep a human in the loop. And when output is wrong, fix the upstream document and rerun — don't patch the code. These are the durable lessons of agentic development.
-->

---

<!-- _backgroundColor: #0B1626 -->
<!-- _color: #F6F4EE -->

###### THE TAKEAWAY

# Don’t hand off your judgment. Give it a structure to work in.

Pick something small this week and run it end to end. The fastest way to understand agentic development is to do one full loop.

- ↳ docs.bmad-method.org
- ↳ github.com/bmad-code-org/BMAD-METHOD
- ↳ bmadcode.com/web-bundles

<!--
Close. Agentic development isn't about handing off your judgment — it's about giving your judgment a structure to work in. Try it on something small this week. Resources on screen.
-->
