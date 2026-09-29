# local-recipes — the BMAD estate, derived (bmad-estate-llms-full.md)

> Purpose: one current picture of the BMAD Method this repository runs on — the installed
> core and modules, every skill by family, the bmad-suite roster with its wielding station
> and provisioning path, the pins, the marshal↔bmad-loop harness range and the release
> cadence — so a session never acts on a retired skill name or a hand-carried version.
>
> **Generated, never hand-written** (`spec-pyforge-scribe` CAP-32). Every fact below is
> read from the source named beside it; a verdict, wielder or hazard is only ever quoted
> from steward's adoption register (AD-2), and a version the sources disagree on is shown
> as a disagreement, never resolved here.
>
> Generated: 2026-09-29. Regenerate: `pixi run -e pyforge-guild scribe catalog bmad-estate --write`.
> Drift detector: `pixi run -e pyforge-guild bmad-estate-check` (structured: a section reds when
> its derived facts move, prose is exempt).

<!-- bmad-estate-digest: installed=58220a6d9490 -->
<!-- bmad-estate-digest: skills=2036acf58e2b -->
<!-- bmad-estate-digest: phases=b74a30513e46 -->
<!-- bmad-estate-digest: suite=99320657c0ef -->
<!-- bmad-estate-digest: pins=4c42a2caf3a4 -->
<!-- bmad-estate-digest: harness=c35ae088e6fe -->
<!-- bmad-estate-digest: cadence=bd38c415273d -->
<!-- bmad-estate-digest: pipeline-truth=44136fa355b3 -->

## 1. Installed core and modules

Source: `_bmad/_config/manifest.yaml`, `_bmad/_config/skf-manifest.yaml`.

- **bmad-method core:** `6.12.0` — `installShims: false`; installed 2026-04-30T17:24:22.503Z, last updated 2026-09-07T01:39:38.942Z.
- **Skill Forge (skf):** `2.1.0`, installed 2026-09-07T01:39:39.614Z.

| Module | Version | Source |
|---|---|---|
| `core` | 6.12.0 | built-in |
| `bmm` | 6.12.0 | built-in |
| `skf` | main | custom |

## 2. Skills by family

Source: `.claude/skills/*/SKILL.md` frontmatter (`name`, `description`); the
core/bmm split comes from `_bmad/_config/bmad-help.csv`. 128 skills.

### BMAD core (8)

| Skill | Description |
|---|---|
| `bmad-advanced-elicitation` | Push the LLM to reconsider, refine, and improve its recent output. Use when user asks for deeper critique or mentions a known deeper critique method, e.g. socratic, first principles, pre-mortem, red team |
| `bmad-brainstorming` | Facilitate a brainstorming session using diverse creative techniques. Use when the user says 'help me brainstorm' or 'help me ideate' |
| `bmad-customize` | Authors and updates customization overrides for installed BMad skills. Use when the user says 'customize bmad', 'override a skill', 'change agent behavior', or 'customize a workflow' |
| `bmad-deep-recon` | Research a topic to support a decision, three ways: draft a research prompt for the user to run in their own tool (ChatGPT, Gemini, Grok, Perplexity, …), turn a finished research report into a short summary with cited so |
| `bmad-forge-idea` | Test a half-formed idea in a questioning conversation, with different personas probing its weak points, until the user can act on it or drop it with confidence. Optionally writes a short brief for planning skills to buil |
| `bmad-help` | Analyzes current state and user query to answer BMad questions or recommend the next skill(s) to use. Use when user asks for help, bmad help, what to do next, or what to start with in BMad |
| `bmad-party-mode` | Orchestrates lively group discussions between installed BMAD agents or custom personas, and helps author custom parties. Use when the user requests party mode, a roundtable, or multiple agent perspectives — or wants to c |
| `bmad-review` | Runs one or more installed review lenses — adversarial critique, edge cases, verification gaps, structure, prose — and reports triaged findings. Use when, and only when, the user asks you to review a diff, a pull request |

### BMad Method (bmm) (15)

| Skill | Description |
|---|---|
| `bmad-architecture` | Work out and record the architecture decisions that keep separately built parts of a system consistent, in a short architecture document. Creates, updates, or validates one; works from a spec, a raw idea, or an existing |
| `bmad-build` | Turns implementation work into working code, reviewed and verified. Use when the user delegates a feature, story, bug fix, or meaningful change; a bare story or issue link counts. Skip obvious, low-risk mechanical mainte |
| `bmad-code-review` | Review code changes with several independent reviewers in parallel, then triage and present the findings. Use when the user says "run code review" or "review this code" |
| `bmad-correct-course` | Assess the impact of a significant change during sprint execution across the PRD, epics, architecture, and UX documents, and produce a sprint change proposal. Use when the user says "correct course" or "propose sprint ch |
| `bmad-create-epics-and-stories` | Break requirements into epics and user stories. Use when the user says "create the epics and stories list" |
| `bmad-prd` | Create, update, or validate a PRD. Use when the user wants help producing, editing, or validating a PRD |
| `bmad-prfaq` | Test a product concept with Amazon's Working Backwards method: write the press release for the finished product first, then answer hard customer and stakeholder questions, ending in a complete PRFAQ document. Use when th |
| `bmad-product-brief` | Create, update, or validate a product brief. Use when the user wants help producing, editing, or validating a brief |
| `bmad-project-context` | Set up, adopt, refresh, or audit a repository's agent instructions (the AGENTS.md block) so AI agents work well in that repo. Also records observed agent mistakes as pitfalls. Use when invoked by name |
| `bmad-qa-generate-e2e-tests` | Generate automated API and end-to-end tests for implemented features. Use when the user says "create qa automated tests for [feature]" |
| `bmad-retrospective` | Review a completed epic against the evidence it left behind — spec, stories, diffs, commits, sprint status — and produce a retrospective with sourced findings, action items, and an acceptance decision. Use when the user |
| `bmad-spec` | Condense any input — an idea, brief, PRD, transcript, or mixed notes — into a short spec: SPEC.md plus supporting files that downstream skills build from. Also updates and validates existing specs, and can break a spec i |
| `bmad-sprint-planning` | Check that planning is complete enough to implement, then generate the sprint status file from the epics. Can also summarize sprint progress and validate or repair the tracking file. Use when the user says "run sprint pl |
| `bmad-ux` | Capture the user's UX vision in two documents: DESIGN.md for how the product looks and EXPERIENCE.md for how it behaves. Use when the user says "lets create UX design" or "create UX specifications" or "help me plan the U |
| `bmad-walkthrough` | Walk the user through reviewing a change: what it is for, what to look at closely, and how to test it. Use when the user says "walkthrough", "walk me through this change", or "human review" |

### Personas (bmad-agent-*) (13)

| Skill | Description |
|---|---|
| `bmad-agent-analyst` | Business analyst for market research, competitive analysis, and requirements. Use when the user asks to talk to Mary or requests the business analyst |
| `bmad-agent-architect` | System architect and technical design leader. Use when the user asks to talk to Winston or requests the architect |
| `bmad-agent-atlas` | Atlas station persona. Acts only through pyforge atlas grammar and POST /stations/atlas/mcp. Use when the operator addresses the atlas station as a persona. |
| `bmad-agent-dev` | Senior software engineer who implements stories and code changes. Use when the user asks to talk to Amelia or requests the developer agent |
| `bmad-agent-doctor` | Doctor station persona. Acts only through pyforge doctor grammar and POST /stations/doctor/mcp. Findings stay advisory — not a second PR gate. Use when the operator addresses the doctor station as a persona. |
| `bmad-agent-herald` | Herald station persona. Acts only through pyforge herald grammar and POST /stations/herald/mcp. Use when the operator addresses the herald station as a persona. |
| `bmad-agent-marshal` | Marshal station persona. Acts only through pyforge marshal grammar and POST /stations/marshal/mcp. Use when the operator addresses the marshal station as a persona. |
| `bmad-agent-mason` | Mason station persona. Consults conda-forge-expert and acts only through pyforge mason grammar and POST /stations/mason/mcp. Use when the operator addresses the mason station as a persona. |
| `bmad-agent-pm` | Product manager for PRD creation and requirements discovery. Use when the user asks to talk to John or requests the product manager |
| `bmad-agent-scribe` | Scribe station persona. Acts only through pyforge scribe grammar and POST /stations/scribe/mcp. Use when the operator addresses the scribe station as a persona. |
| `bmad-agent-steward` | Steward station persona. Acts only through pyforge steward grammar and POST /stations/steward/mcp. Use when the operator addresses the steward station as a persona. |
| `bmad-agent-ux-designer` | UX designer and UI specialist. Use when the user asks to talk to Sally or requests the UX designer |
| `bmad-agent-warden` | Warden station persona. Acts only through pyforge warden grammar and POST /stations/warden/mcp. Does not publish a second PR-gate verdict. Use when the operator addresses the warden station as a persona. |

### BMad Builder (bmb) (5)

| Skill | Description |
|---|---|
| `bmad-agent-builder` | Builds, edits or analyzes Agent Skills through conversational discovery. Use when the user requests to "Create an Agent", "Analyze an Agent" or "Edit an Agent". |
| `bmad-bmb-setup` | Sets up BMad Builder module in a project. Use when the user requests to 'install bmb module', 'configure BMad Builder', or 'setup BMad Builder'. |
| `bmad-eval-runner` | Run a skill's evals and report results. Use when the user wants to evaluate a skill, run evals, benchmark a skill, validate triggers, optimize a description, or grade skill outputs. |
| `bmad-module-builder` | Plans, creates, and validates BMad modules. Use when the user requests to 'ideate module', 'plan a module', 'create module', 'build a module', or 'validate module'. |
| `bmad-workflow-builder` | Builds, edits, and analyzes workflows and skills. Use when the user requests to "build a workflow", "modify a workflow", "quality check workflow", or "analyze skill". |

### Test Architect (tea, bmad-testarch-*) (10)

| Skill | Description |
|---|---|
| `bmad-tea` | Master Test Architect and Quality Advisor. Use when the user asks to talk to Murat or requests the Test Architect. |
| `bmad-teach-me-testing` | Teach testing progressively through structured sessions. Use when user says "lets learn testing" or "I want to study test practices" |
| `bmad-testarch-atdd` | Generate red-phase acceptance test scaffolds using the TDD cycle. Use when the user says "lets write acceptance tests" or "I want to do ATDD" |
| `bmad-testarch-automate` | Expand test automation coverage for codebase. Use when user says "lets expand test coverage" or "I want to automate tests" |
| `bmad-testarch-ci` | Scaffold CI/CD quality pipeline with test execution. Use when the user says "lets setup CI pipeline" or "I want to create quality gates" |
| `bmad-testarch-framework` | Initialize test framework with Playwright or Cypress. Use when the user says "lets setup test framework" or "I want to initialize testing framework" |
| `bmad-testarch-nfr` | Audit NFR evidence for performance, security, reliability, and maintainability. Use when implementation evidence exists and the user says "audit NFR evidence", "audit NFRs", or "evaluate non-functional requirements" |
| `bmad-testarch-test-design` | Create system-level or epic-level test plans. Use when the user says "lets design test plan" or "I want to create test strategy" |
| `bmad-testarch-test-review` | Review test quality using best practices validation. Use when user says "lets review tests" or "I want to evaluate test quality" |
| `bmad-testarch-trace` | Generate traceability matrix and quality gate decision. Use when the user says "lets create traceability matrix" or "I want to analyze test coverage" |

### Creative Intelligence Suite (bmad-cis-*) (10)

| Skill | Description |
|---|---|
| `bmad-cis-agent-brainstorming-coach` | Elite brainstorming specialist for facilitated ideation sessions. Use when the user asks to talk to Carson or requests the Brainstorming Specialist. |
| `bmad-cis-agent-creative-problem-solver` | Master problem solver for systematic problem-solving methodologies. Use when the user asks to talk to Dr. Quinn or requests the Master Problem Solver. |
| `bmad-cis-agent-design-thinking-coach` | Design thinking maestro for human-centered design processes. Use when the user asks to talk to Maya or requests the Design Thinking Maestro. |
| `bmad-cis-agent-innovation-strategist` | Disruptive innovation oracle for business model innovation and strategic disruption. Use when the user asks to talk to Victor or requests the Disruptive Innovation Oracle. |
| `bmad-cis-agent-presentation-master` | Visual communication and presentation expert for slide decks, pitch decks, and visual storytelling. Use when the user asks to talk to Caravaggio or requests the Presentation Expert. |
| `bmad-cis-agent-storyteller` | Master storyteller for compelling narratives using proven frameworks. Use when the user asks to talk to Sophia or requests the Master Storyteller. |
| `bmad-cis-design-thinking` | Guide human-centered design processes using empathy-driven methodologies. Use when the user says "lets run design thinking" or "I want to apply design thinking" |
| `bmad-cis-innovation-strategy` | Identify disruption opportunities and architect business model innovation. Use when the user says "lets create an innovation strategy" or "I want to find disruption opportunities" |
| `bmad-cis-problem-solving` | Apply systematic problem-solving methodologies to complex challenges. Use when the user says "guide me through structured problem solving" or "I want to crack this challenge with guided problem solving techniques" |
| `bmad-cis-storytelling` | Craft compelling narratives using story frameworks. Use when the user says "help me with storytelling" or "I want to create a narrative through storytelling" |

### Utility skills (bmad-os-*) (11)

| Skill | Description |
|---|---|
| `bmad-os-audit-file-refs` | Audit BMAD source files for file-reference convention violations using parallel Haiku subagents. Use when users requests an "audit file references" for a skill, workflow or task. |
| `bmad-os-changelog` | Analyzes changes since last release and drafts them directly into the project's CHANGELOG.md. Use when users requests 'update the changelog' or 'prepare changelog release notes' |
| `bmad-os-changelog-social` | Generate social media announcements for Discord, Twitter/X, Facebook, and LinkedIn from the latest changelog entry. Use when user asks to 'create release announcement' or 'create social posts' or share changelog updates. |
| `bmad-os-diataxis` | Create, update, fix, or refine documentation using Diataxis framework and BMad Method style guide. Use when user asks to 'create a doc', 'update docs', 'fix docs style', 'refine docs', or 'improve docs writing'. |
| `bmad-os-docs-audit` | Orchestrates a repository-wide documentation audit. Discovers unmapped Markdown files, identifies persona gaps, and delegates writing tasks to bmad-os-diataxis. Use when user asks to 'audit docs', 'find missing documenta |
| `bmad-os-editorial-review-translation` | Review translated documentation for content fidelity — detect injected, off-topic, or unauthorized content by comparing against the English source. Use when reviewing translation PRs or translated docs. |
| `bmad-os-findings-triage` | Orchestrate HITL triage of review findings using parallel agents. Use when the user says 'triage these findings' or 'run findings triage' or has a batch of review findings to process. |
| `bmad-os-gh-triage` | Analyze all github issues. Use when the user says 'triage the github issues' or 'analyze open github issues'. |
| `bmad-os-review-pr` | Dual-layer PR review tool (Raven's Verdict). Runs adversarial cynical review and edge case hunter in parallel, merges and deduplicates findings into professional engineering output. Use when user asks to 'review a PR' an |
| `bmad-os-root-cause-analysis` | Perform root cause analysis on a bug fix. Use when the user says 'run RCA on [commit/PR]', 'root cause analysis', or 'analyze what caused this bug'. Accepts a commit SHA, PR number, issue, or description of a fix. |
| `bmad-os-skill-to-bundle` | Convert a BMad skill into a downloadable web bundle (Gemini Gem + ChatGPT Custom GPT) with a persona, install instructions, and knowledge files. Use when a user wants to publish a skill to consumer LLM platforms (Gemini, |

### bmad-loop (bmad-loop-*) (3)

| Skill | Description |
|---|---|
| `bmad-loop-resolve` | Interactive escalation-resolution workflow for the bmad-loop orchestrator. A bmad-loop run paused on a CRITICAL escalation (a contradiction or gap a dev/review session could not safely resolve alone); you and the human d |
| `bmad-loop-setup` | Sets up BMAD Loop Skills module in a project. Use when the user requests to 'install bmad-loop module', 'configure BMAD Loop Skills', or 'setup BMAD Loop Skills'. |
| `bmad-loop-sweep` | Triage the deferred-work ledger for the bmad-loop orchestrator: verify every selected open entry against the actual codebase and return a machine-readable partition (bundles, already-resolved, blocked, skip, human decisi |

### Skill Forge (skf-*) (16)

| Skill | Description |
|---|---|
| `skf-analyze-source` | Discover what to skill in a large repo and produce recommended skill briefs. Use when the user requests to "analyze source for skills" or "discover skill opportunities." |
| `skf-audit-skill` | Drift detection between skill and current source code. Use when the user requests to "audit a skill" or "audit skill" for drift. |
| `skf-brief-skill` | Design a skill scope through guided discovery. Use when the user requests to "create a skill brief" or "brief a skill". |
| `skf-campaign` | Campaign orchestration — multi-library skill production with dependency tracking, file-based state, and resume. Use when the user asks to "run a campaign" or "orchestrate skills." |
| `skf-create-skill` | Compile a skill from a brief. Supports --batch for multiple briefs. Use when the user requests to "create a skill" or "compile a skill." |
| `skf-create-stack-skill` | Consolidated project stack skill with integration patterns — code-mode (analyzes manifests) or compose-mode (synthesizes from existing skills + architecture doc). Use when the user requests to "create a stack skill", "fo |
| `skf-drop-skill` | Drop a specific skill version or an entire skill — soft (deprecate) or hard (purge) with platform context rebuild. Use when the user requests to "drop" or "remove a skill." |
| `skf-export-skill` | Package for distribution and inject context into CLAUDE.md/AGENTS.md/.cursorrules. Use when the user requests to "export" or "package a skill." |
| `skf-forger` | Skill compilation specialist — the forge master. Use when the user asks to "talk to Ferris" or requests the "Skill Forge agent." |
| `skf-quick-skill` | Fast skill from a package name or GitHub URL — no brief needed. Use when the user requests a "quick skill" or "skill from URL" or "skill from package." |
| `skf-refine-architecture` | Improve architecture doc using verified skill data and VS feasibility findings. Use when the user requests to "refine skill architecture" or "improve architecture doc." |
| `skf-rename-skill` | Rename a skill across all its versions — transactional copy-verify-delete with platform context rebuild. Use when the user requests to "rename a skill." |
| `skf-setup` | Initialize forge environment, detect tools, and set capability tier (Quick/Forge/Forge+/Deep). Use when the user requests to "set up" or "initialize the forge". |
| `skf-test-skill` | Cognitive completeness verification — quality gate before export. Use when the user requests to "test a skill" or "verify skill completeness." |
| `skf-update-skill` | Smart regeneration preserving [MANUAL] sections after source changes. Use when the user requests to "update a skill" or "regenerate a skill." |
| `skf-verify-stack` | Pre-code stack feasibility verification against architecture and PRD documents. Use when the user requests to "verify a tech stack" or "verify stack." |

### labs-skills, by consent (4)

| Skill | Description |
|---|---|
| `mcp-builder` | Guide for creating high-quality MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools. Use when building MCP servers to integrate external APIs or services, |
| `multi-repo-git-ops` | Manages git operations (branching, committing, pushing) across multi-repo systems with git submodules. Use this skill whenever the user wants to create a feature branch, commit changes, push code, sync submodules, or man |
| `release-please` | Set up and configure Google's release-please for automated versioning, changelog generation, and publishing via GitHub Actions. Covers pipeline creation, Conventional Commits formatting, pre-release workflows, monorepo c |
| `slides-generator` | Generate interactive presentation slides using React + Tailwind, and export to standalone single-file HTML. Triggers on keywords like "slides", "presentation", "PPT", "demo", "benchmark", or when user requests export. Us |

### PyForge station skills (pyforge-*) (7)

| Skill | Description |
|---|---|
| `pyforge-atlas` | Kedro/Dagster/DuckDB factory intelligence for conda-forge (pyforge.atlas). Use when running atlas pipelines, listing catalog datasets, or reading the station MCP surface. Invoke via `pyforge atlas …` (FR-13) — do not imp |
| `pyforge-doctor` | Pre-flight and fleet-watch diagnostics via the doctor CLI (check, monitor, diagnose, backlog-intake). Use when running pyforge doctor grammar, POST /stations/doctor/mcp, or working in src/shared/packages/pyforge-doctor/. |
| `pyforge-herald` | Seeds, pulls, and reports Claude Design deck bridge state via the herald CLI. Use when running herald deck seed / pull / status, or working in src/shared/packages/pyforge-herald/. Do not import pyforge.herald internals; |
| `pyforge-marshal` | Deterministic BMAD-loop supervisor: fleet status, loop homes, detector check, and Genesis seed via the marshal CLI. Use when running marshal status / homes / check / seed, or working in src/shared/packages/pyforge-marsha |
| `pyforge-scribe` | Captures team-memory decisions into .claude/memory, compiles the scribe knowledge graph, and recalls cited answers via the scribe CLI. Use when writing or retrieving team memory, running scribe capture / graph compile / |
| `pyforge-steward` | Provisioner's station CLI — keys, deploy, provision, budget, sync, workspace, upgrade, suite, and machine bootstrap. Use when running steward duties, pyforge steward grammar, or working in src/shared/packages/pyforge-ste |
| `pyforge-warden` | Runs the warden dependency-hygiene and vulnerability gate via the warden CLI (scan / scan --doctor). Use when scanning Python/Conda/Pixi manifests, checking the scanner environment, or working in src/shared/packages/pyfo |

### Other bmad-* skills (2)

| Skill | Description |
|---|---|
| `bmad-build-auto` | One iteration of an unattended development loop. Use when invoked by name |
| `bmad-sprint-ledger-query` | Pluggable, extensible, hookable, feature-flagged Sprint Ledger Query & Telemetry Reporting engine across all eight PyForge stations. |

### Other repo skills (24)

| Skill | Description |
|---|---|
| `api-and-interface-design` | Principles for creating stable, usable interfaces across REST APIs, GraphQL schemas, module boundaries, and component contracts. |
| `browser-testing-with-devtools` | Use Chrome DevTools MCP to verify browser-based code through live inspection rather than static analysis. |
| `cf-atlas-legacy` | Hallucination-free legacy provenance oracle for the cf_atlas-to-Kedro migration (BMAD project pyforge-atlas). Models the legacy conda_forge_atlas.py orchestrator (8,902 LOC, 23 cataloged phases, schema v29) plus bootstra |
| `ci-cd-and-automation` | Automate CI/CD pipelines to enforce quality standards. Shift-left philosophy — catch problems early, not in production. |
| `code-review-and-quality` | Multi-dimensional code review framework. Evaluate across correctness, readability, architecture, security, and performance before merging. |
| `code-simplification` | Simplify code to enhance readability without altering functionality. Preserve behavior, follow conventions, prefer clarity. |
| `conda-forge-expert` | Autonomous conda-forge packaging agent. Manages the entire recipe lifecycle, from generation, security scanning, and building to debugging, maintenance, and PR submission. USE THIS SKILL WHEN: creating or updating conda |
| `context-engineering` | Feed agents the right information at the right time. Context is the single biggest lever for agent output quality. |
| `debugging-and-error-recovery` | Systematic root-cause diagnosis. Six-step triage checklist. Stop-the-Line Rule when unexpected behavior occurs. |
| `deprecation-and-migration` | Systematic approach to removing outdated code and safely transitioning to replacement systems. Code is a liability. |
| `documentation-and-adrs` | Capture WHY decisions were made, not just what code does. ADRs are the highest-value documentation. |
| `frontend-ui-engineering` | Standards for production-quality UIs. Component architecture, state management, accessibility, avoiding AI aesthetics. |
| `git-workflow-and-versioning` | Disciplined version control. Trunk-based development, atomic commits, descriptive messages, right-sized changes. |
| `idea-refine` | Transform raw concepts into actionable plans via three phases: divergent thinking, convergence, and sharpening. |
| `incremental-implementation` | Build in thin vertical slices. One piece at a time, test it, verify it, then expand. Each increment leaves the system working. |
| `marshal-run-watch` | Reusable ops-manager status check for marshal-supervised BMAD work — one pinned run, a whole station (project), or the entire fleet (all projects). Covers both the multi-story bmad-loop orchestrator pattern and the one-s |
| `performance-optimization` | Measure before optimizing. Five-step workflow: Measure → Identify → Fix → Verify → Guard. No guessing. |
| `planning-and-task-breakdown` | Decompose work into manageable, verifiable tasks. Read-only mode first. Vertical slicing, not horizontal. Checkpoints every 2–3 tasks. |
| `security-and-hardening` | Security-first development. Three-tier boundary system: Always Do / Ask First / Never Do. Prevents OWASP Top 10 vulnerabilities. |
| `shipping-and-launch` | Production deployment best practices. Pre-launch checklist, staged rollouts, feature flags, monitoring, rollback plan. |
| `source-driven-development` | Ground code decisions in official documentation, not memory or training data. Detect → Fetch → Implement → Cite. |
| `spec-driven-development` | Create detailed specifications before implementing. Four gated phases: Specify → Plan → Tasks → Implement. Human review between phases. |
| `test-driven-development` | Write failing tests before writing the code that makes them pass. RED-GREEN-REFACTOR cycle. Tests are proof, not afterthoughts. |
| `using-agent-skills` | Meta-skill for discovering and applying the right engineering skill for any task. Decision tree by development phase. |

Directories under `.claude/skills/` with no `SKILL.md` (not skills): `knowledge`, `shared`.

## 3. BMAD phases and sequence

Source: `_bmad/_config/bmad-help.csv` (installer-generated; what `bmad-help` reads).
Module docs — BMad Method: <https://docs.bmad-method.org/>.
Module docs — Core: <https://docs.bmad-method.org/>.

| Skill | Module | Phase | Required | Preceded by | Followed by |
|---|---|---|---|---|---|
| `bmad-prd` | BMad Method | 2-planning | true | bmad-product-brief | — |
| `bmad-ux` | BMad Method | 2-planning | false | bmad-prd | — |
| `bmad-project-context` | BMad Method | anytime | false | — | — |
| `bmad-spec` | BMad Method | anytime | false | — | — |
| `bmad-correct-course` | BMad Method | anytime | false | — | — |
| `bmad-sprint-planning` | BMad Method | anytime | false | — | — |
| `bmad-brainstorming` | BMad Method | plan | false | — | — |
| `bmad-product-brief` | BMad Method | plan | false | — | — |
| `bmad-prfaq` | BMad Method | plan | false | — | — |
| `bmad-architecture` | BMad Method | plan | true | — | — |
| `bmad-create-epics-and-stories` | BMad Method | plan | true | bmad-architecture | — |
| `bmad-sprint-planning` | BMad Method | plan | true | — | — |
| `bmad-build` | BMad Method | ship | true | bmad-sprint-planning | bmad-code-review |
| `bmad-code-review` | BMad Method | ship | false | bmad-build | — |
| `bmad-walkthrough` | BMad Method | ship | false | — | — |
| `bmad-qa-generate-e2e-tests` | BMad Method | ship | false | bmad-build | — |
| `bmad-retrospective` | BMad Method | ship | false | bmad-code-review | — |
| `bmad-brainstorming` | Core | anytime | false | — | — |
| `bmad-party-mode` | Core | anytime | false | — | — |
| `bmad-help` | Core | anytime | false | — | — |
| `bmad-customize` | Core | anytime | false | — | — |
| `bmad-advanced-elicitation` | Core | anytime | false | — | — |
| `bmad-review` | Core | anytime | false | — | — |
| `bmad-forge-idea` | Core | anytime | false | — | — |
| `bmad-deep-recon` | Core | anytime | false | — | — |
| `skf-forger` | skf | anytime | false | — | — |
| `skf-setup` | skf | anytime | false | — | skf-analyze-source,skf-brief-skill,skf-quick-skill,skf-verify-stack,skf-campaign |
| `skf-campaign` | skf | anytime | false | skf-setup | — |
| `skf-analyze-source` | skf | anytime | false | skf-setup | skf-brief-skill |
| `skf-brief-skill` | skf | anytime | false | skf-setup,skf-analyze-source | skf-create-skill |
| `skf-create-skill` | skf | anytime | false | skf-brief-skill | skf-test-skill,skf-create-stack-skill |
| `skf-quick-skill` | skf | anytime | false | skf-setup | skf-test-skill |
| `skf-create-stack-skill` | skf | anytime | false | skf-create-skill | skf-test-skill |
| `skf-update-skill` | skf | anytime | false | skf-export-skill | — |
| `skf-audit-skill` | skf | anytime | false | skf-export-skill | — |
| `skf-verify-stack` | skf | anytime | false | skf-setup | skf-refine-architecture |
| `skf-refine-architecture` | skf | anytime | false | skf-verify-stack | — |
| `skf-test-skill` | skf | anytime | false | skf-create-skill,skf-create-stack-skill,skf-quick-skill | skf-export-skill |
| `skf-export-skill` | skf | anytime | false | skf-test-skill | skf-update-skill,skf-audit-skill,skf-rename-skill,skf-drop-skill |
| `skf-rename-skill` | skf | anytime | false | skf-export-skill | — |
| `skf-drop-skill` | skf | anytime | false | skf-export-skill | — |
| `skf-forger` | skf | anytime | false | — | — |
| `skf-forger` | skf | anytime | false | — | — |

## 4. The bmad-suite roster

Source: `recipes/bmad-suite/suite-members.yaml` (the population) joined with
`_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md` § 1 (verdict, wielder, provisioning path, hazards — quoted,
never re-decided) and each member's `recipes/<member>/recipe.yaml`. 13 active members.

| Member | Register version | Install class | Verdict | Wielder | Provisioning path | Hazards | Local recipe |
|---|---|---|---|---|---|---|---|
| `bmad-method` | 6.12.0 | installer-tree | wield (substrate) | all stations | steward Epic 14 (`upgrade bmad-core`) | installed-stage caveat: pipeline-truth reads conda-meta, not `_bmad/_config/manifest.yaml` | 6.12.0 |
| `bmad-loop` | 0.11.1 | runner-home | wield | marshal (wrap, never absorb) | `steward provision --runner bmad-loop --env …` | npm-invisible; uv-from-git native path | 0.12.0 |
| `bmad-method-test-architecture-enterprise` | 1.24.0 | module | **wield — full adoption** | marshal (workflows, review lens), warden (advisory) | `steward provision --module tea` | replaces `_bmad/scripts/bmad_tea_playwright.py` + 2 meta-tests (equivalence check first) | 1.27.2 |
| `bmad-builder` | 2.2.2 | module | **wield — beside skf** | steward (module/agent authoring), mason | `steward provision --module bmb` | never `--legacy-dir` / `cleanup-legacy.py` (`rmtree` of `_bmad/core/config.yaml`); npm stale 1.1.0 | 2.2.2 |
| `bmad-creative-intelligence-suite` | 0.3.2 | module | wield | herald, scribe | `steward provision --module cis` (idempotent re-provision) | npm stale 0.1.9 vs GitHub 0.3.2 | 0.3.2 |
| `bmad-module-skill-forge` | 2.1.0 | own-installer (custom-module registration kept) | wield | all stations (domain skills) | `bmad-module-skill-forge install/update`; `--module skf` refused | never `uninstall` (deletes 121 skill dirs); marketplace.json omits `skf-campaign` | 2.2.0 |
| `bmad-eval-quality` | 0.2.0.dev0 @3172162f | cli | wield (pilot) | warden, marshal (reviewer measurement) | pixi pin; tasks `eval-quality-smoke` / `-review-twin-run` / `-review-replay` | npm 0.1.0 lacks `score`; exact commit pin load-bearing; `__win` variant missing | 4.3.0 |
| `bmad-utility-skills` | 2.0.0 @HEAD | module | **wield** | herald, doctor, warden, scribe, marshal, steward (§ 2) | `steward provision --module utility-skills` | no upstream tags; no LICENSE file upstream (recipe vendors MIT text; conda-forge submission held) | 2.0.0 |
| `bmad-labs-skills` | 1.0.0.dev0 @HEAD | plugin-path (consent) | **wield — skill-by-skill** | atlas (`mcp-builder`), herald (`slides-generator`), marshal (`multi-repo-git-ops`), steward (`release-please`) | `steward provision --plugin labs --skill <name>` (the one wrapped, pinned writer — AD-1; 46.5) | third-party (thuantan2060); `bmad-skills` on npm is unrelated (bacoco) | 1.0.0.dev0 |
| `bmad-module-template` | 0.1.0 @HEAD | scaffold | wield (authoring tool only) | steward / `bmad-builder` | none (never `steward provision --module` into `.claude/skills/`) | placeholder LICENSE is not a reason to copy it into the live skill tree | 0.1.0 |
| `bmad-manticore` | 3.1.0.dev0 @c9bcf759 | module (`--custom-source`) | **wield — Herald studio** | herald | native: `npx bmad-method install --directory $PYFORGE_STUDIO_ROOT --custom-source https://github.com/bmad-code-org/bmad-manticore --yes --tools <full tool-id list>` in `$PYFORGE_STUDIO_ROOT` (default `~/pyforge-studio/`, declared once per machine — AD-3); `--directory` and `--yes --tools <ids>` are REQUIRED for a non-interactive run (the bare command hangs on an unanswerable `Installation directory:` prompt, proven across 3 attempts) — full command in `docs/reference/manticore-studio.md` (this cell cites, never restates) | 3.0 upgrade wipes the studio's `_bmad/` + `_bmad-output/`; G109 renumber (tag 1.0.1 vs 3.1.0.dev0); needs uv, ffmpeg, node, git (ffmpeg confirmed absent on this machine, 46.6); the installed module tracks `main`/`next` (unpinned, floating) — unlike every other custom module in this register (skf pinned v2.1.0, this same package's OWN conda recipe pinned @c9bcf759) — so re-running the sanctioned command later can silently install a different Manticore version with no lockfile or version-check anywhere (review finding, 46.6, recorded as an open reproducibility risk, not resolved here) | 3.1.0.dev0 |
| `bmad-dashboard` | 1.2.2.dev0 | vscode-extension | wield (opt-in dev surface) | marshal | `bmad-dashboard-install` pixi task | npm `bmad-dashboard` is an unrelated collision; never the console (`retired-console-check`) | 1.2.2.dev0 |
| `mybmad-dashboard` | 0.1.0.dev0 | vscode-extension (a Next.js app) | wield (sidecar: estate Postgres schema mybmad + estate OIDC) | steward (host chrome tile) | `mybmad` launcher; Prisma `?schema=mybmad` on estate `DATABASE_URL`; Keycloak `COMPONENT_OIDC_*` | consume sidecar — not `/console/`, not station nine, not Better Auth on the wielded path; launcher `pg_ctl` + Better Auth is DEV FALLBACK ONLY | 0.1.0.dev0 |

Deprecated catalog rows (kept for drift completeness, never a metapackage run-dep): `bmad-method-wds-expansion`, `bmad-autopilot`, `bmad-dashboard-extension`, `bmalph`.

### Sources disagree

| Member | Source | Source | Source |
|---|---|---|---|
| `bmad-loop` | `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md` → 0.11.1 | `pixi.toml` → 0.12.0 | `recipes/bmad-loop/recipe.yaml` → 0.12.0 |
| `bmad-method-test-architecture-enterprise` | `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md` → 1.24.0 | `pixi.toml` → 1.27.2 | `recipes/bmad-method-test-architecture-enterprise/recipe.yaml` → 1.27.2 |
| `bmad-module-skill-forge` | `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md` → 2.1.0 | `pixi.toml` → 2.2.0 | `recipes/bmad-module-skill-forge/recipe.yaml` → 2.2.0 |
| `bmad-eval-quality` | `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md` → 0.2.0.dev0 @3172162f | `pixi.toml` → 4.3.0 | `recipes/bmad-eval-quality/recipe.yaml` → 4.3.0 |
| `bmad-utility-skills` | `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md` → 2.0.0 @HEAD | `pixi.toml` → 2.0.0 | `recipes/bmad-utility-skills/recipe.yaml` → 2.0.0 |
| `bmad-labs-skills` | `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md` → 1.0.0.dev0 @HEAD | `pixi.toml` → 1.0.0.dev0 | `recipes/bmad-labs-skills/recipe.yaml` → 1.0.0.dev0 |
| `bmad-module-template` | `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md` → 0.1.0 @HEAD | `pixi.toml` → 0.1.0 | `recipes/bmad-module-template/recipe.yaml` → 0.1.0 |
| `bmad-manticore` | `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md` → 3.1.0.dev0 @c9bcf759 | `pixi.toml` → 3.1.0.dev0 | `recipes/bmad-manticore/recipe.yaml` → 3.1.0.dev0 |

Rendered as read; the reconcile is steward's (a deferred-work row), never this generator's.

### Skill routing (register § 2 — one wielding station per adopted skill)

| Skill(s) | Source member | Wielding station | Story |
|---|---|---|---|
| `bmad-os-changelog`, `bmad-os-changelog-social` | utility-skills | herald | herald 18.2 |
| `bmad-os-root-cause-analysis` | utility-skills | doctor | doctor 20.4 |
| `bmad-os-review-pr`, `bmad-os-findings-triage` | utility-skills | warden (advisory lens) | warden 11.1 |
| `bmad-os-diataxis`, `bmad-os-audit-file-refs`, `bmad-os-editorial-review-translation` | utility-skills | scribe | scribe 7.1 |
| `bmad-os-gh-triage` | utility-skills | marshal | marshal 31.6 |
| `bmad-os-skill-to-bundle` | utility-skills | steward | 46.2 |
| `bmad-testarch-*` (9 workflows), `tea-test-review` | TEA | marshal (workflows, review lens); warden (advisory) | marshal 31.1–31.3, warden 11.2 |
| `bmad-agent-builder`, `bmad-workflow-builder`, `bmad-module-builder`, `bmad-eval-runner`, `bmad-bmb-setup` | bmad-builder | steward | 46.4 |
| `mc-*` (15) | manticore | herald (studio only) | herald 18.1 |
| `mcp-builder` | labs | atlas | atlas 24.1 |
| `slides-generator` | labs | herald | herald 18.3 |
| `multi-repo-git-ops` | labs | marshal | marshal 31.6 |
| `release-please` | labs | steward | 46.5 |
| `eval-quality` CLI | eval-quality | warden / marshal | 45.2 |
| `bmad-cis-*` (10) | CIS | herald, scribe | 46.8 |
| `skf-*` (16) | skf | all stations | — |

## 5. Pins (`bmad-*` in `pixi.toml`)

Source: `pixi.toml` — every dependency table that names a `bmad-*` / `mybmad-*` key.

| Package | Table | Spec |
|---|---|---|
| `bmad-builder` | `feature.local-recipes.dependencies` | `>=2.2.2` |
| `bmad-builder` | `feature.pyforge-guild.dependencies` | `>=2.2.2` |
| `bmad-creative-intelligence-suite` | `feature.local-recipes.dependencies` | `>=0.3.2` |
| `bmad-creative-intelligence-suite` | `feature.pyforge-guild.dependencies` | `>=0.3.2` |
| `bmad-dashboard` | `feature.bmad-ui.dependencies` | `>=1.2.2.dev0` |
| `bmad-dashboard` | `feature.local-recipes.dependencies` | `>=1.2.2.dev0` |
| `bmad-dashboard` | `feature.pyforge-guild.dependencies` | `>=1.2.2.dev0` |
| `bmad-eval-quality` | `feature.local-recipes.dependencies` | `>=4.3.0` |
| `bmad-eval-quality` | `feature.pyforge-guild.dependencies` | `>=4.3.0` |
| `bmad-eval-quality` | `feature.pyforge-steward.dependencies` | `>=4.3.0` |
| `bmad-labs-skills` | `feature.local-recipes.dependencies` | `>=1.0.0.dev0` |
| `bmad-labs-skills` | `feature.pyforge-guild.dependencies` | `>=1.0.0.dev0` |
| `bmad-loop` | `feature.local-recipes.dependencies` | `>=0.12.0` |
| `bmad-loop` | `feature.pyforge-guild.dependencies` | `>=0.12.0` |
| `bmad-loop` | `feature.pyforge-marshal.dependencies` | `>=0.12.0` |
| `bmad-manticore` | `feature.local-recipes.dependencies` | `>=3.1.0.dev0` |
| `bmad-manticore` | `feature.pyforge-guild.dependencies` | `>=3.1.0.dev0` |
| `bmad-method` | `feature.local-recipes.dependencies` | `>=6.12.0` |
| `bmad-method` | `feature.python.dependencies` | `>=6.12.0` |
| `bmad-method-test-architecture-enterprise` | `feature.local-recipes.dependencies` | `>=1.27.2` |
| `bmad-method-test-architecture-enterprise` | `feature.pyforge-guild.dependencies` | `>=1.27.2` |
| `bmad-module-skill-forge` | `feature.local-recipes.target.linux-64.dependencies` | `>=2.2.0` |
| `bmad-module-skill-forge` | `feature.pyforge-guild.target.linux-64.dependencies` | `>=2.2.0` |
| `bmad-module-template` | `feature.local-recipes.dependencies` | `>=0.1.0` |
| `bmad-module-template` | `feature.pyforge-guild.dependencies` | `>=0.1.0` |
| `bmad-suite` | `feature.bmad-suite-full.dependencies` | `>=2026.9.26` |
| `bmad-utility-skills` | `feature.local-recipes.dependencies` | `>=2.0.0` |
| `bmad-utility-skills` | `feature.pyforge-guild.dependencies` | `>=2.0.0` |
| `mybmad-dashboard` | `feature.bmad-ui.dependencies` | `>=0.1.0.dev0` |

## 6. Marshal ↔ bmad-loop harness

Source: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py` (`HARNESS_VERSION_RANGE_TEXT`, read as text).

- Supported bmad-loop range: `>=0.11.0,<0.13`.
- Marshal wraps bmad-loop through that one module (import-linter enforced); `.bmad-loop/policy.toml`
  is a derived, gitignored artifact rendered from Marshal's policy fold, never hand-edited.

## 7. The release cadence

Source: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/release-cadence.md` (the numbered step titles; owner → verb).

- 1. Doctor — detect.
- 2. Steward — catalog.
- 3. Steward — pre-flight (report-only).
- 4. Steward — apply.
- 5. Steward — prove-landed.
- 6. Marshal — era round.
- 7. Mason — suite refresh.
- 8. Steward — flips.
- 9. Steward — record.

## 8. Pipeline truth (optional input)

Not rendered: pass `--pipeline-truth <file>` (the output of `steward suite pipeline-truth --json`)
to add the six-stage columns. The generator itself makes no network call.
