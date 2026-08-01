# Narration script — Agentic SDLC

> Extracted from `Agentic SDLC.dc.html` speaker notes (regenerable — do not hand-edit; edit the deck's `data-speaker-notes` in Design and re-extract). 45 scenes.

## Scene 01 — Title

Open here. This deck explains what agentic AI across the software development lifecycle actually looks like in practice, using the BMad Method as our concrete framework. Audience: working engineers. The arc runs in six acts: the case for change, spec-driven development, choosing a framework, the BMAD agent team, the four phases, and scaling plus the ecosystem.

## Scene 02 — Contents

The road map. Six acts. First, why the augmented SDLC most teams run isn't enough and what agentic means. Second, spec-driven development as the operating model. Third, the tool landscape and why we settle on BMAD. Fourth, how the BMAD agent team is structured. Fifth, a walk through the four phases end to end. Sixth, scaling the method, governing it, and the wider ecosystem. About forty minutes end to end; each act stands alone if you want to jump.

## Scene 03 — Act I

Act I opener: the problem framing.

## Scene 04 — The shift

Frame the problem. Most AI coding tools generate for you and leave you to sort out the mess. That works for a snippet and falls apart on a real system. The shift is from a tool that types to a collaborator that follows a process.

## Scene 05 — What is AI-SDLC

Define the term before going further. The AI-SDLC is not a new lifecycle — it's the one you already know: analyze, plan, design, build, test, ship. What changes is who does the work and how state moves between phases. Specialized agents execute each phase, humans keep judgment and approval, and persistent specs — not meetings or chat memory — carry the state from one phase to the next.

## Scene 06 — Maturity spectrum

Where does agentic sit relative to the AI-augmented SDLC most teams already have? It's a spectrum. Manual: humans do everything. AI-augmented: humans still execute every phase, AI assists inside each one — autocomplete, generated tests you curate, review hints. Agentic: agents execute the phases, humans direct and gate through specs — that's this deck. Autonomous: unattended loops where you set intent and review outcomes. The real jump from augmented to agentic: context moves out of your head and chat history into documents agents read and write.

## Scene 07 — Core idea

The core idea in one line: agents are collaborators, not oracles. They pull your best thinking out through a structured process instead of doing the thinking for you. This is the whole philosophy.

## Scene 08 — Act II

Act II opener: spec-driven development.

## Scene 09 — What is SDD

Define spec-driven development before we build on it. SDD means you write the specification first — a precise, versioned document stating behavior, constraints, and acceptance criteria — and the AI generates and validates code against it. Contrast that with vibe coding: prompt, get code, hope. In SDD the pipeline is intent → spec → human review → generate → validate. The spec is the contract; a bug means the contract was wrong or violated.

## Scene 10 — Spec-driven

Spec-driven development is the universal operating model. Specs aren't paperwork — they're programmable infrastructure. Three payoffs: expertise becomes a permanent asset instead of living in one person's head; structured specs become machine-readable instructions agents can execute; and every document compounds — it's semantic context that makes the next agent run smarter. V6 shards work into atomic, versioned step-files to eliminate context drift.

## Scene 11 — Mental model

The mental model that makes all of this click: the documentation is the brain, and agents are transient workers who read from and write to it. Never rely on an LLM's leaky chat memory to hold the plan. And the SDLC isn't a loop — it's a funnel of increasing resolution: why, what, how, build. No agent writes code until the what and the how are frozen in a text file.

## Scene 12 — Act III

Act III opener: the tool landscape and the BMAD choice.

## Scene 13 — SDD landscape

SDD is a category now, not one tool — 30+ frameworks by early 2026. Three broad buckets. Agent-team frameworks simulate a full agile team with role personas and file-based handoffs — BMAD is the archetype and what this deck follows. Spec-first scaffolding adds a specify-plan-tasks structure to a coding session — GitHub Spec Kit with its constitution, AWS Kiro baking specs into the IDE, GSD as the lightweight option. Living-spec tools treat the spec as the evolving source of truth — OpenSpec with delta specs for brownfield, Tessl betting on spec-as-source, Augment Intent writing changes back to the spec. Below all of these sits agent infrastructure — CrewAI, Agno, LangGraph, AutoGen — orchestration SDKs that provide multi-agent machinery, not a development methodology. Rules of thumb: complex greenfield with a paper trail, BMAD. Brownfield and lightweight, OpenSpec. Broad default, Spec Kit. AWS-native, Kiro.

## Scene 14 — Method vs machinery

Method and machinery are different layers, and engineers ask two questions when they see orchestration SDKs next to BMAD. First: do you need an SDK with BMAD? Usually not — BMAD installs as skills into your coding agent (Claude Code, Cursor, Codex), which is already the runtime: tool calling, files, context, with humans driving checkpoints. Reach for CrewAI or LangGraph only to build your own pipeline product — unattended CI loops, parallel story agents — where personas become crews or graph nodes and BMAD's artifacts stay the contracts. Second, the reverse: on an SDK already, do you need a method? For software, yes — orchestration SDKs are empty machinery with no roles, artifacts, or gates; borrow BMAD (personas become roles, artifacts the messages, gates the edges) or reinvent them. Not building software — research, bots, data pipelines? SDD is irrelevant. The relationship is asymmetric: method without SDK works out of the box; SDK without method only when you're not shipping software.

## Scene 15 — Why BMAD

Why this framework and not another from the landscape? Four reasons. Structure without rigidity: phases are guardrails, not gates you can't skip — drop optional phases, load agents directly, reorder once you know the flow. Context persistence: every plan is a file in git — new chat, agents pick up where you left off; the whole team sees the same artifacts. Scale-domain-adaptive: it sizes the ceremony to the work — bug fix gets three commands, an enterprise system gets compliance and security reviews — and adapts to domain: a dating app and a medical device don't get the same planning. And it's 100% free, MIT, no gated content.

## Scene 16 — Cover · Framework

Chapter break into the concrete half of the deck: the BMAD framework itself.

## Scene 17 — The crew

You don't talk to one monolithic AI. You talk to named agents, each anchored to a phase and a role, each with a persona and a menu of skills. Say 'Hey Mary, let's brainstorm' and she activates. The point: it feels like a team of specialists, not a slash-command menu.

## Scene 18 — Why named agents

Why personas instead of a menu or a blank prompt? A menu makes you memorize where each capability lives. A blank prompt makes you guess the magic words. Named agents invert it: you say what you want, in your words, to a teammate who already knows the work and their menu is there as a fallback.

## Scene 19 — Party mode

One agent at a time is the default, but some decisions need several perspectives at once. Party mode brings multiple personas into one session and lets them respond in turn. Three canonical uses: a design review where UX, architect, and developer weigh in together; a troubleshooting session where dev, DevOps, and DBA triangulate a production issue; and architecture decisions where PM, architect, and security argue trade-offs before you commit. It's the whiteboard meeting, minus the scheduling.

## Scene 20 — Execution matrix

One reference slide before we walk the phases: the execution matrix. Each phase has a persona, an input artifact, and an output artifact. Each output becomes the anchor for the next persona — the handoff is a file, not a chat thread. Keep this in your head as we go phase by phase.

## Scene 21 — Skill roster

The full skill roster in the latest release, aligned to agents and phases. Every workflow ships as an installable skill — invoke it directly by its bmad- id, or through the owning agent's menu. Mary and Paige cover analysis, John and Sally planning, Winston solutioning, Amelia the whole implementation loop. And a set of cross-cutting skills — help, party-mode, customize, project-context generation — plus the quick-dev and dev-auto parallel track work across all phases.

## Scene 22 — Repo artifacts

What this all physically looks like: two folders in your repo. _bmad holds the machinery — agent definitions, workflows, config. _bmad-output holds your artifacts, split in v6 into planning-artifacts (PRD, architecture, epics) and implementation-artifacts (sprint status), plus a project-context file. Four consequences: no context loss because a new chat picks up from the files; version control because plans live in git next to code; team visibility because everyone reads the same documents; and AI grounding because agents cite concrete files instead of hallucinating.

## Scene 23 — Cover · Phases

Chapter break opening the phase walkthrough.

## Scene 24 — Phase map

This is the map for the rest of the deck. Four phases: Analysis, Planning, Solutioning, Implementation. Each is a set of workflows that produce documents. We'll walk through each one. Phase 1 is optional; the real spine is Planning to Implementation.

## Scene 25 — Phase 1 · Analysis

Phase 1, Analysis, is optional but it makes everything downstream sharper. Four ways to think clearly before you build: brainstorm to generate, research to ground, brief to document, PRFAQ to stress-test. Skipping analysis means your PRD is built on assumptions.

## Scene 26 — Choosing a tool

Practical guidance: which analysis tool fits your situation. Vague idea, brainstorm. Need market truth, research. Know what you want, brief. Want it stress-tested, PRFAQ. Both brief and PRFAQ feed the PRD — the difference is how much challenge you want.

## Scene 27 — Phase 2 · Planning

Phase 2, Planning. This is where you define what to build and for whom. The PRD is the anchor — it answers what and why, and every downstream document inherits its clarity or its vagueness. UX runs alongside when experience matters.

## Scene 28 — Phase 3 · Solutioning

Phase 3, Solutioning. Translate what into how. The architect makes technical decisions explicit, the PM breaks requirements into epics and stories, and a readiness gate decides pass, concerns, or fail before anyone writes code.

## Scene 29 — Why solutioning

Concrete reason solutioning matters. Without shared architectural decisions, two agents on two epics pick REST and GraphQL independently, and integration becomes a nightmare. Decide once, up front, and everyone follows. Catching alignment issues here is 10x cheaper than during implementation.

## Scene 30 — Phase 4 · Implementation

Phase 4, Implementation. Build one story at a time. Each story carries complete, focused context so the dev agent isn't guessing. Sprint planning sequences the work once; then it's a tight loop per story.

## Scene 31 — The dev loop

Zoom into the loop. Create story, implement, review, and on to the next — with correct-course to handle mid-sprint changes and a retrospective at the end of each epic. Human stays in the loop; you choose how tight. This is the heartbeat of implementation.

## Scene 32 — Cover · Testing

Chapter break introducing the TEA testing module.

## Scene 33 — TEA testing

The complaint heard most from teams using AI for development: the tests are garbage. They pass, they look fine in review, and three sprints later half are flaky and nobody trusts the suite — because the AI had no testing strategy, it just wrote assertions matching current behavior. TEA, the Test Architect module, treats testing as an engineering discipline: risk-based test design scores probability times impact into P0 to P3 priorities, so the checkout flow gets deep coverage and the settings page gets a smoke test. Network-first patterns kill flaky waits. And the trace workflow maps tests to requirements and issues a release-gate decision: pass, concerns, fail, or waived.

## Scene 34 — Cover · Ecosystem

Chapter break opening the ecosystem section.

## Scene 35 — Scale-adaptive

BMad v6 offers three planning tracks, and bmad-help picks one for you. Quick Flow for bug fixes and clear-scope work (1-15 stories) produces just a tech-spec. BMad Method for products and platforms (10-50+ stories) produces a PRD, architecture, and UX. Enterprise for compliance and multi-tenant systems (30+ stories) adds security and DevOps. Story counts are guidance, not definitions — choose by planning need. Same primitives throughout, different depth. Quick flow for a bug fix, simple for a small feature, complex when solutioning is required, enterprise when governance is. The process adjusts to complexity instead of forcing one-size-fits-all.

## Scene 36 — Quick flow

Not everything needs four phases. For small, well-understood work there's a parallel track: quick-dev clarifies, plans, implements, reviews, and presents in one flow; dev-auto runs a single unattended iteration. Use the full method for the enterprise system, quick flow for the bug fix.

## Scene 37 — Governance

Pull the docs idea together and scale it. The documents aren't paperwork — they're the product's memory. A project-context file makes a dozen separate agent runs feel like one coherent team, and at enterprise scale it matures into a constitution: a single, versioned source of truth that supersedes ad-hoc practice. The interesting part: agents are empowered to enforce it — they audit every PR and cite the exact clause a change violates. Humans amend it through ADRs and sign-off. And a simplicity gate keeps complexity honest: YAGNI, with justification required.

## Scene 38 — Build for agents

The flip side: it's not just about using agents to build — it's about building systems agents can operate. Three layers: interfaces with semantic structure and deterministic layouts, no vibe UI; APIs that are idempotent and self-documenting with errors clear enough for an agent to self-correct; and an agent harness — explicit tool exposure, strict guardrails, exhaustive run-trace logs.

## Scene 39 — Module ecosystem

BMAD isn't one thing — the core is a module in a wider ecosystem, and V6 leans hard into that. The core, BMM, is the 34+ workflow framework this deck walks through. On top of it, official modules extend the same scale-adaptive discipline into new domains, each installable during setup or any time after: BMad Builder to create your own agents and workflows; Test Architect (TEA) for risk-based test strategy; Game Dev Studio for Unity, Unreal, and Godot pipelines; and the Creative Intelligence Suite for brainstorming, innovation, and design-thinking facilitation. All MIT, all installed the same way. And when you're unsure what's next, the bmad-help skill tells you what to do and what's optional.

## Scene 40 — BMad Builder

When the built-in agents don't cover your domain — HIPAA reviews, a house deployment process — BMad Builder creates your own. The packaging model: everything is a skill, a folder with a SKILL.md, following the open Agent Skills standard; agents, workflows, and utilities all ship the same way. Agents come in three types: stateless for single-session experts; memory agents that keep a persistent 'sanctum' of identity and knowledge files and greet you by name next session; and autonomous agents that add a PULSE file and wake on a schedule to work unattended. Builders run as guided conversations, then modules package skills for distribution on GitHub.

## Scene 41 — Plan anywhere

The method isn't locked to one tool. Six planning coaches ship as web bundles you can install as ChatGPT Custom GPTs, Gemini Gems, or Microsoft Copilot agents — do the heavy planning on a flat-rate subscription, then bring the artifacts into your IDE for implementation. And a growing ecosystem of modules and community tools extends the same discipline to testing, game dev, automation, and more.

## Scene 42 — In action

Optional show-and-tell slide. Drop in your own screenshots to make the method concrete: the installer running in your terminal, a real workflow or party-mode session, and the generated artifacts in your editor or the docs site. Live captures land better than stock diagrams here — swap these three in before presenting. If you'd rather not use images, this slide can be removed.

## Scene 43 — Get started

How to actually try it. One install command, open your AI IDE, and if you're ever unsure, ask bmad-help and it tells you what's next. It's free and open source. The fastest way to understand it is to run it once on something small.

## Scene 44 — Principles

The takeaways that transfer even if you never use this specific framework. Structure beats prompting. Documents are context. Decide the hard things once. Match ceremony to complexity. Keep a human in the loop. And when output is wrong, fix the upstream document and rerun — don't patch the code. These are the durable lessons of agentic development.

## Scene 45 — Closing

Close. Agentic development isn't about handing off your judgment — it's about giving your judgment a structure to work in. Try it on something small this week. Resources on screen.
