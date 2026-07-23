How We Operate

## Welcome to the team 🙌

<!--

**Here are some ideas to get you started:**

🙋‍♀️ A short introduction - what is your organization all about?
👀 Contribution guidelines - how do team members dive in?
👩‍💻 Useful resources - where do you keep your docs? Is there anything else the team should know?
🍪 Fun facts - what is your team's favorite snack?
🧙 Remember, you can do mighty things with the power of [Markdown](https://docs.github.com/github/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax)
-->

# HOW-WE-OPERATE.md

This document defines our universal engineering and operational philosophy. We build systematically, eliminate structural friction, and treat documentation as programmable infrastructure.

---

## 🤖 1. We Build for Autonomous AI Agents—Not Just Humans

Every system, interface, dataset, and presentation artifact we produce must be inherently legible to, and controllable by, machine intelligence.

### 1. Optimize for Web Agents
* **Semantic Structure:** Maintain pristine HTML, clear ARIA attributes, and logical DOM hierarchies.
* **Deterministic Layouts:** Build structured layouts that scraper and browser agents can navigate without getting stuck.
* **No Vibe UI:** Design applications and interfaces with explicit selectors and predictable user pathways.

### 2. Design APIs for Agent Workflows
* **Self-Documenting Schemas:** Enforce strict, up-to-date OpenAPI/Swagger specifications.
* **Idempotency First:** Ensure agents can safely retry network requests without introducing duplicate mutations.
* **Hyper-Clear Error Messages:** Return actionable error payloads so LLMs can auto-diagnose and self-correct mid-flight.

### 3. Build the AI Layer / "Agent Harness"
* **Tool-Calling Ready:** Expose native functionalities explicitly formatted and wrapped for LLM tool execution.
* **Strict Guardrails:** Implement rigid schema validation layers to catch erratic or out-of-bounds agent behavior.
* **State Management:** Log exhaustive run-trace histories so agents maintain absolute context of their operational state.

---

## 📐 2. Spec-Driven Development is Our Universal Operating Model

We do not build, analyze, or design on a whim. Spec-driven development is our universal operating model for everything we do. This approach creates a structured, semantic knowledge base that powers our LLMs and agentic workflows to:

1. **Extract and institutionalize human knowledge**, eliminating key-man dependencies by converting individual expertise into permanent, accessible markdown assets.
2. **Remove operational bottlenecks and automate execution**, turning structured specs into machine-readable instructions that drive automated tasks, processes, and procedures.
3. **Fuel continuous, compounding AI intelligence**, building our organizational "brain" by transforming everyday documentation into clean semantic context that trains our LLMs and autonomous agents to make better, faster decisions.

---

## 🔄 3. The BMAD Universal Workflow (v6.8.0 Framework)

To enforce this, deliverables leverage the full BMAD Method Module (BMM) workflow, executing through an explicit agent team ecosystem. Instead of relying on sprawling, monolithic documents, version 6 utilizes a **Step-File Architecture** to break work down into modular, atomic, and versioned markdown assets inside the project repository to entirely eliminate LLM context drift.

[ Analyst Agent ] ──> [ Product Manager ] ──> [ Architect Agent ] ──> [ Developer & QA Loop ]
(Project Briefs) (Sharded PRD Steps) (System Contracts) (Automated Delivery Review)


* **The Analyst:** Formulates the foundational Project Brief, isolating the core business challenge, analytics hypothesis, presentation objectives, or user needs.
* **The Product Manager:** Translates the brief into explicit, decoupled Epics and atomic User Stories, structurally sharded into machine-readable, step-by-step markdown files.
* **The Architect:** Hardens system contracts, standardizing technical data schemas, API definitions, visual layout models, and systemic guardrails.
* **The Developer & QA Loop:** Code, analytics pipelines, or slide layouts are generated incrementally against the specific step files, then strictly validated by back-to-back testing and automated Delivery Review agents before hitting production.

Referances: https://gist.github.com/rxm7706/860af4c6d82a8c00560d62545b71e830
1. **[BMAD-Method: AI-Driven Agile Development Series' Articles](https://dev.to/bspann/series/35551)** (Published: 2026-04-01)
2. **[Using GitHub Copilot CLI in Spec Driven Development with the BMad Method](https://www.linkedin.com/pulse/using-github-copilot-cli-spec-driven-development-bmad-goncalves-esh1e/)** (Published: 2026-01-20)
3. **[BMAD Method + Claude Code: How I Actually Ship Projects with Spec-Driven AI Development](https://dev.to/bspann/bmad-method-claude-code-how-i-actually-ship-projects-with-spec-driven-ai-development-1eei)** (Published: 2026-05-27)
4. **[BMAD-METHOD Framework Repository](https://github.com/bmad-code-org/BMAD-METHOD)** (Updated: 2026-05-25)
5. **[The BMAD Method Official Documentation](https://bmad-method.org/)** (Updated: 2026-06-14)
6. **[What is BMAD-METHOD™? A Simple Guide to the Future of AI-Driven Development](https://medium.com/@visrow/what-is-bmad-method-a-simple-guide-to-the-future-of-ai-driven-development-412274f91419)** (Published: 2025-09-08)
7. **[The Complete Business Analyst's Guide to BMAD-METHOD™](https://medium.com/@hieutrantrung.it/the-complete-business-analysts-guide-to-bmad-method-from-zero-to-expert-project-planning-in-30-3cf3995a0480)** (Published: 2025-09-24)
8. **[Skill Forge (SKF) Module: Automating Skill Creation](https://github.com/armelhbobdad/bmad-module-skill-forge)** (Published: May 2026)
9. **[BMad Builder Module & Skills Guide](https://github.com/bmad-code-org/bmad-builder)** (Published: May 2026)
10. **[BAD: BMAD Autonomous Development](https://github.com/stephenleo/bmad-autonomous-development)** (Updated: 2026-04-11)

---

## 🚀 Repository Scaffolding

Initialize the core framework and setup your localized workspace directory (`_bmad/`):

```bash
pixi install bmad-method
```
