---
title: "BMAD-method whitepaper — captured text and claim verification against the installed estate"
chain: "pyforge-unifying-strategy"
created: "2026-09-25"
updated: "2026-09-25"
type: research
owner: steward
head: 5ab472318b
status: draft   # research input for the 2026-09-25 consolidation; no decision taken here
---

# BMAD-method whitepaper — captured text and claim verification

**What this is.** The operator pasted *Architectural Specification and Execution Paradigms of the
BMad Method* into a session on 2026-09-25 as an input to the Unifying Strategy and the foundry
cutover. It has no public URL. This file is where it lives in the repo: the text as captured
(§ 3), checked claim by claim against what this estate actually installs (§ 1). The Dream cites
this file, not the text. **Nothing here is an adoption decision.** Where the whitepaper and an
installed skill disagree, the installed skill wins (`CLAUDE.md` § BMAD Method Documentation).

**Treatment.** Same as [`docs/dreams/intelligence-hub.md`](../../../../../docs/dreams/intelligence-hub.md)
gives the OpenTeams whitepaper: the source is kept whole and cited, and the Dream carries only what
bears on the strategy, in our own words. The two papers overlap only in their closing Frames / Cogs /
Ops section; this one is BMAD-centric (the three execution modes, the `bmad-code-org` module
ecosystem), the other is Hub-centric.

**Provenance caveat.** The text in § 3 is the copy captured in the operator's session on
2026-09-25. Some middle sections read as condensed relative to a typical long-form paper; treat
§ 3 as the captured record, not a guaranteed byte-for-byte original.

## 1. Claim verification (2026-09-25, `main` `5ab472318b`)

Checked against `.claude/skills/bmad-*/`, `_bmad/`, `recipes/bmad-*/`, the adoption register
(`specs/spec-bmad-suite-lifecycle/adoption-register.md`), the installed `bmad_loop` package and
`.claude/docs/bmad-method-llms-full.txt`. Installed versions: BMAD core and bmm **6.12.0**
(`_bmad/_config/manifest.yaml`, `installShims: false`); `bmad_loop` **0.11.1** in `bmad-suite-full`;
the `local-recipes` env also carries a stale `bmad_loop-0.8.1.dist-info` beside 0.11.1.

| # | Claim | Verdict | Evidence | What is actually true |
|---|---|---|---|---|
| 1 | `bmad-spec` kernel = Why · Capabilities (CAP-N) · Constraints · Non-Goals · Success Signals | verified, nuance | `.claude/skills/bmad-spec/SKILL.md:9,55,67`; `assets/spec-template.md:11-45` | Five fields; the fifth is "Success signal" (singular). The template also carries Assumptions and Open Questions. |
| 2 | Review is three lenses: Blind Hunter, Edge Case Hunter, Acceptance Auditor (= Verification Gap Finder) | **contradicted** | `bmad-code-review/customize.toml:48-100`; `bmad-build/customize.toml:83-120`; `bmad-build-auto/customize.toml:54-105` | `bmad-code-review` has four lenses — Blind Hunter, Edge Case Hunter, Verification Gap Reviewer, Acceptance Auditor (the Auditor is separate and runs only at `review_mode="full"`). `bmad-build` has three and no Auditor; `bmad-build-auto` adds an Intent Alignment Auditor. |
| 3 | `bmad-build-auto` lifecycle draft → ready-for-dev → in-progress → in-review → done, plus blocked; repair loop capped at 5 | verified | `bmad-build-auto/spec-template.md:5`; `step-04-review.md:70` | The cap counts bad-spec loopbacks via `review_loop_iteration`. |
| 4 | Halts `blocked: no subagents` when the harness cannot spawn subagents | verified | `bmad-build-auto/workflow.md:53` | — |
| 5 | Six standardized blocking reasons | partly true | `step-01..04`; `llms-full.txt:3562-3576` | All six exist, but the docs call the list "typical" and name 13 (e.g. `matrix ambiguity`, `patch verification failed`, `finalization left repository dirty`). |
| 6 | Intent-gap patch preserved under implementation artifacts; recovery = `git apply` + status `in-review` + re-invoke | verified | `step-04-review.md:71`; `llms-full.txt:3578` | — |
| 7 | Five invocation shapes incl. folder-and-identifier dispatch over `stories.yaml` | verified | `llms-full.txt:3453-3459`; `step-01-clarify-and-route.md:33-43` | — |
| 8 | `bmad-loop`: `[scm] isolation = "worktree"`, `[sweep] auto = true`, `[sweep] repeat = true`, `sweep` / `decisions` subcommands, `.bmad-loop/decisions.json` | partly contradicted | `bmad_loop/policy.py:29,330,334,510,1038-1040`; `cli.py:4201,4262`; `decisions.py:14,33` | `sweep.auto` is an enum (`never` \| `per-epic` \| `run-end`) — `auto = true` fails validation. `repeat` is a bool; `isolation = "worktree"` is valid (default `none`); the subcommands and `decisions.json` exist. |
| 9 | Sprint mode (`sprint-status.yaml`) and stories mode (`stories.yaml`) | verified | `bmad_loop/sprintstatus.py:1`; `stories_engine.py:1-4` | In this estate the feed is per-project and has a tracked twin (`sprint-status-ledger.yaml`). |
| 10 | Persona codes Mary `BA-01` … Amelia `SE-05`, Murat `TA-06` | **contradicted** | `_bmad/config.toml:28-66` | The roster keys agents by skill id with name, title and icon; no such codes exist. Murat is TEA, outside that roster. |
| 11 | `bmad-builder` validation = "19 structural rules across 6 categories" | unverifiable here | `bmad-workflow-builder/references/scan-orchestration.md:3,11-28` | Analyze runs 4 checking scripts then 5 LLM lenses; no 19/6 count found. |
| 12 | TEA: 36-row criteria registry, write-time file hook, `tea-test-review` headless gate, nine workflows | partly true | `recipes/bmad-method-test-architecture-enterprise/recipe.yaml:32,60-63`; adoption register `:40` | `tea-test-review` CLI and nine workflows confirmed (a pixi task since steward Story 46.3). The 36-row registry and write-time hook were not found. |
| 13 | Three config layers (shipped / `_bmad/custom/` / `_bmad/config.user.toml`) with an "anti-subtraction" invariant | partly contradicted | `bmad-customize/SKILL.md:66-79,94`; `_bmad/config.toml:1-10` | Per-skill layers are `customize.toml` → `_bmad/custom/{skill}.toml` → `_bmad/custom/{skill}.user.toml`; `_bmad/config.user.toml` is installer-owned central config. "Anti-subtraction" is not a term in the skills: merges have no delete step, but an override can empty a lens's `instruction` and so drop it silently. |
| 14 | `bmad-quick-dev` → `bmad-build`, `bmad-dev-auto` → `bmad-build-auto` with forwarding shims; `bmad-quick-dev.toml` migrates | partly true | `_bmad/bmm/v6-shims/README.md:9-10`; `bmad_loop/policy.py:273-274` | Renames and shims are real; this install runs with shims off. No text prescribes the `.toml` migration. `[dev] skill = "bmad-dev-auto"` survives as a permanent adapter discriminator (`AGENTS.md` pitfalls). |
| 15 | bmad-suite = 13 active members; parked list | verified | `recipes/bmad-suite/recipe.yaml:31-45`; `suite-members.yaml:6-13,82-93` | The table is **this repo's own** register (it cites doctor Story 19.1) — so it is downstream of us, not independent evidence. `bmad-story-automator` is "retired without a local recipe", not a parked member. |
| 16 | Readiness gate yields PASS / CONCERNS / FAIL | verified | `bmad-sprint-planning/SKILL.md:52,57` | — |
| 17 | `bmad-prd` modes in `steps-c/`, `steps-e/`, `steps-v/`; trade-offs in `.memlog.md` | partly contradicted | `bmad-prd/SKILL.md:14,24,30-36` | Create/Update/Validate are modes inside `SKILL.md` + `references/validate.md`; the `steps-c/e/v` layout is TEA's. Rejected alternatives go to `addendum.md`. |
| 18 | `forge-report.html` / `forged-idea.md`; `brainstorm.html` / `brainstorm-intent.md` | verified | `bmad-forge-idea/SKILL.md:12,100,104`; `bmad-brainstorming/references/finalize.md:20-21` | `forged-idea.md` only when the idea ends "Hardened"; brainstorm artifacts are opt-in outside "Ideate for me". |

**Tally.** 8 of 18 claims hold as stated (3, 4, 6, 7, 9, 15, 16, 18); 1 holds with a nuance (1);
6 are partly true or partly contradicted (5, 8, 12, 13, 14, 17); 2 are contradicted (2, 10); 1 is
unverifiable here (11).

**Reading.** Reliable on the `bmad-build-auto` worker contract (lifecycle, halts, dispatch shapes,
patch recovery), `bmad-loop`'s two modes, and suite membership. Unreliable on review-lens naming,
persona codes, customization layers and several specific counts. Any Spec that wants to lean on a
claim in § 3 re-verifies it against the installed skill first.

## 2. What bears on the estate

1. **Three execution modes are already the estate's modes.** `bmad-build` (interactive) is the
   session path; `bmad-build-auto` (worker) is what `marshal factory dispatch` runs; `bmad-loop`
   (orchestrator) is `spin` / the drains. The paper supplies outside names, not new mechanism.
2. **"Deterministic infrastructure over model persuasion"** is the estate's own direction
   (the `pre-shell.py` deny hook, `pr-preflight`, the detectors). The 2026-09-25 drain stop
   showed where it is still missing: the shared BMAD marker (`MRS-DISP-041`) and a landing
   harness that reported two successful stories as failed (`MRS-GATE-001`).
3. **In-the-loop → on-the-loop** (its adoption stages) names the transition the fleet is in:
   unattended drains work, but cross-station parallel autonomy is still gated by one shared
   marker per working tree.
4. **Frames / Cogs / Ops** corroborates the Unifying Dream's § *What the Foundry becomes* and
   [`intelligence-hub.md`](../../../../../docs/dreams/intelligence-hub.md); it does not extend
   either.
5. **TEA as an independent gate** (`tea-test-review`) is installed (steward 46.3) but is not a
   merge gate. Whether it becomes one is an open candidate, not a decision.
6. **Machine-local observation, not a repo fact:** a stale `bmad_loop-0.8.1.dist-info` beside
   0.11.1 in the primary checkout's `local-recipes` env (gitignored `.pixi/`; a fresh worktree's
   env has only 0.11.1).

## 3. The text as captured (2026-09-25)

### Architectural Specification and Execution Paradigms of the BMad Method: Spec-Driven Engineering, Autonomous Loops, and Repository Ecosystem

#### Executive Synthesis

The rapid acceleration of generative artificial intelligence across software engineering has produced an acute industry paradox: while raw code synthesis has become frictionless, the cognitive and structural overhead required to deliver robust, production-grade software has escalated. Unstructured "vibe coding" and unbounded conversational agents routinely translate implicit assumptions, ambiguous constraints, and unstated edge cases into silent technical debt, brittle interfaces, and decaying test suites. In contrast to frameworks that attempt to displace human oversight with probabilistic autonomy, the [BMad Method](https://bmadcode.com/) establishes an enterprise-grade engineering paradigm predicated on a rigorous foundational principle: artificial intelligence functions as the operational facilitator, while human engineering judgment remains the authoritative domain expert.

Created by Brian Madison and governed within the open-source [bmad-code-org](https://github.com/bmad-code-org) ecosystem, the BMad Method structures the entire software development lifecycle (SDLC) into deterministic, auditable, and repo-native workflows. By enforcing a strict "spec is the work" doctrine, BMad front-loads domain modeling, architectural trade-offs, and boundary definitions before a single line of executable code is written. Rather than relying on transient chat transcripts or remote proprietary control planes, the framework commits all specifications, decision records, and acceptance criteria directly into the project repository alongside the source tree.

Crucial to the operational scalability of the framework is its tripartite execution architecture. The platform supports three distinct modes of execution tailored to varying degrees of task ambiguity, risk tolerance, and workflow maturity:

1. **Interactive Guided Implementation (`bmad-build`)**: A developer-in-the-loop paradigm characterized by proactive codebase reconnaissance, intent gap discovery, interactive plan approval gates, and multi-lens code review.
2. **Autonomous Single-Session Worker Execution (`bmad-build-auto`)**: A self-contained, unattended worker primitive that processes a single session-sized unit of work from an immutable contract, executing planning, implementation, and verification across a formal frontmatter state machine before halting with deterministic terminal signals.
3. **Orchestrated Continuous Development Loops (`bmad-loop`)**: An external, deterministic Python-based orchestration engine that drives multi-story epics, manages disposable fresh-context agent sessions, enforces git worktree isolation, automates deferred-work sweeps, and closes the delivery cycle with evidence-based retrospectives.

This whitepaper provides an exhaustive technical analysis of the BMad architecture, its foundational philosophy, the full module ecosystem hosted under [GitHub bmad-code-org](https://github.com/bmad-code-org), the technical operational contracts of its execution modes, and the organizational patterns required for enterprise transition from "in-the-loop" oversight to "on-the-loop" governance.

---

#### Foundational Philosophy: The Mechanics of Human Expertise and Machine Amplification

##### The Inversion of the AI Development Bottleneck

The prevailing direction of commercial AI tooling focuses on accelerating implementation speed. Auto-complete engines, inline diff generators, and single-prompt scaffolding tools treat the writing of syntax as the primary constraint on delivery throughput. The [BMad Philosophy](https://bmadcode.com/philosophy) articulates that this premise misdiagnoses the software engineering bottleneck. Modern large language models (LLMs) synthesize code with high fluency, but they lack intrinsic awareness of unstated business requirements, latent architectural invariants, regulatory constraints, and long-term maintainability goals. Left unguided, an autonomous model inevitably invents decisions that no stakeholder approved, selecting arbitrary library conventions, unvetted data schemas, and fragile integration points.

Consequently, the productivity bottleneck has inverted: writing code is trivial, but reviewing, validating, and debugging synthetic code is extraordinarily cognitively expensive. The BMad Method addresses this inversion by investing computational and human effort into the phases preceding code generation. By formalizing ambiguity reduction into structured analysis and planning artifacts, the framework ensures that downstream coding agents execute within tightly bounded operational corridors.

##### Mission Planning vs. Ad-Hoc Prompting

A foundational premise articulated in the [BMad Philosophy](https://bmadcode.com/philosophy) is that dispatching an autonomous agent into a complex repository is an exercise in military-style mission planning rather than conversational prompting. When an agent is launched unattended, it possesses only its immediate objective, the context provided in its context window, and the operational boundaries configured by its execution harness. It operates across repository terrain that the human supervisor cannot actively monitor in real time. The further an agent must navigate and the more contested or ambiguous the architectural route, the higher the degree of pre-computation and planning required to guarantee safe arrival.

Under this mission-planning doctrine, open-ended conversational prompting is replaced by immutable specification contracts. The human architect defines the non-negotiable boundaries—what must be accomplished, what must not change, and what is explicitly excluded from scope—empowering the machine to optimize implementation details without risking mission drift or destructive side effects.

##### Evolution of Agile Delivery and the Epic-Centric Cadence

The emergence of AI-native engineering invalidates several legacy Agile ceremonies while amplifying the necessity of Agile's foundational values. The BMad Method maintains that Agile practice has evolved rather than been superseded:

- **Collapse of the Two-Week Sprint**: Fixed two-week sprints and arbitrary story point estimations were mechanisms designed to throttle human implementation throughput. Because generative models collapse development cycles from days to minutes, artificial time-boxing becomes counterproductive.
- **The Epic as the Core Operational Unit**: Within BMad, the epic replaces the multi-week sprint as the primary unit of delivery. Each epic functions as a self-contained, high-velocity micro-sprint that initiates with an inception gate, executes across a sequence of focused story units, and concludes with automated integration, codebase refactoring, and evidence-based retrospective analysis.
- **Replacement of Story Points with Human Attention Grading**: Story points historically served as proxies for cognitive complexity and resource scheduling. In BMad, work items are triaged based on the degree of human intervention required: whether a task demands deep interactive human pairing, lightweight supervisory check-in, or unattended autonomous dispatch.
- **Evidence-Based Retrospectives**: Traditional retrospectives rely on subjective engineer recall. BMad retrospectives are programmatic audits that ingest Git commit logs, test execution traces, and artifact logs, evaluating delivered changes against the original specification and holding subsequent epics accountable to documented remediation actions.

---

#### The Four-Phase SDLC Delivery Lifecycle

The BMad Method structures development into four distinct phases as formalized in [The Method Overview](https://bmadcode.com/method) and [BMad Method Documentation](https://docs.bmad-method.org/). The lifecycle is non-dogmatic and right-sized: engineers enter at whichever phase corresponds to the maturity of the incoming change request, while all implementation paths mechanically converge upon identical verification standards.

| Phase 1: Analysis (Optional) | Phase 2: Planning & Solutioning | Phase 3 & 4: Implementation & Verification |
|---|---|---|
| bmad-brainstorming | bmad-prd | bmad-build (Interactive) |
| bmad-forge-idea | bmad-ux | bmad-build-auto (Worker) |
| bmad-deep-recon | bmad-architecture | bmad-loop (Orchestrator) |
| bmad-product-brief | bmad-spec | Blind / Edge / Audit Review |
| bmad-prfaq | bmad-sprint-planning | bmad-retrospective |

##### Phase 1: Problem Space Analysis and Idea Hardening

Phase 1 provides structured discovery workflows for greenfield initiatives, ambiguous product concepts, or strategic pivots:

- **`bmad-brainstorming`**: Facilitates structured ideation sessions across three selectable operating modes (Facilitator, Creative Partner, or Ideate for Me). It captures brainstorming intent into structured documents (`brainstorm.html`, `brainstorm-intent.md`) and maintains an append-only memory log.
- **`bmad-forge-idea`**: Implements Socratic, adversarial pressure-testing. The skill interrogates the user's premise one question at a time, forcing resolution on user definitions, value propositions, and operational assumptions. It produces a comprehensive `forge-report.html` and, upon successful validation, extracts a durable `forged-idea.md`.
- **`bmad-deep-recon`**: Gathers targeted domain, market, and technical intelligence to substantiate architectural or commercial decisions, compiling empirical findings into a structured `research.md`.
- **`bmad-product-brief` & `bmad-prfaq`**: Synthesize customer-backward narratives, executive summaries, and initial product boundaries without prematurely generating engineering constraints.

##### Phase 2: Systematic Planning and Invariant Specification Architecture

Phase 2 translates validated intent into durable, machine-readable specifications that govern implementation:

- **`bmad-prd`**: Generates or validates comprehensive Product Requirements Documents (`prd.md`). It supports three distinct operational modes—Create (`steps-c/`), Update (`steps-e/`), and Validate (`steps-v/`)—and logs all trade-offs into `.memlog.md`.
- **`bmad-ux`**: Formalizes user experience flows, information architecture, and UI behavior contracts, generating `DESIGN.md` and `EXPERIENCE.md`.
- **`bmad-architecture`**: Formulates the technical blueprint, producing the system's `ARCHITECTURE-SPINE.md`. It standardizes data schemas, API contracts, cross-cutting security boundaries, and assigns stable architectural decision identifiers (`AD-N`) that downstream stories inherit as non-negotiable constraints.
- **`bmad-spec`**: Serves as the central translation engine of the planning phase. It ingests upstream documentation and condenses it into the canonical 5-field specification kernel (`SPEC.md`). The five immutable fields comprise:
  1. **Why**: The commercial, operational, or technical justification for the change.
  2. **Capabilities (`CAP-N`)**: Discrete functional features, tagged with persistent identifiers.
  3. **Constraints**: Non-negotiable technical, operational, performance, or regulatory boundaries.
  4. **Non-Goals**: Explicit exclusions preventing scope creep and agentic hallucination.
  5. **Success Signals**: Measurable, deterministic criteria establishing verifiable completion.
- **`bmad-sprint-planning` & Readiness Gates**: Prior to entering implementation, epics undergo an adversarial readiness audit evaluating whether any developer or agent would need to invent undocumented decisions. The gate yields an explicit status: `PASS`, `CONCERNS`, or `FAIL`, establishing the machine-readable board state in `sprint-status.yaml`.

##### Phase 3: Convergent Implementation and Context Hydration

Regardless of whether an engineering effort originates from an enterprise PRD, an epic breakdown, or an ad-hoc bug report, all work converges onto a standardized implementation unit. The unit of work is strictly bounded to a single session-sized goal (typically under 500 lines of modified functional code across a cohesive file cluster). Context hydration injects only relevant specification slices, repository maps, and recent decision records into the LLM context window, mitigating attention degradation and catastrophic forgetting.

##### Phase 4: Verification, Multi-Lens Adversarial Audit, and Retrospective Traceability

Implementation outputs must undergo multi-tiered verification before merging:

- **Tri-Lens Code Review**: Evaluates diffs through three isolated, parallel perspectives:
  - *Blind Hunter*: Inspects code quality, syntax correctness, and security vulnerabilities without prior knowledge of intent, identifying defects that stand out purely on code merit.
  - *Edge Case Hunter*: Traces boundary conditions, state mutation race conditions, null pointer paths, and concurrency hazards.
  - *Acceptance Auditor / Verification Gap Finder*: Reconciles code changes strictly against acceptance criteria, ensuring complete capability delivery and verifying that adequate automated tests accompany the changes.
- **`bmad-retrospective`**: Evaluates completed epics against the durable repository evidence. The retrospective cross-references commit logs and test reports against `SPEC.md` and `stories.yaml`, logging systemic insights into `sprint-status.yaml` to govern future iterations.

---

#### Architectural Breakdown of the Three Execution Modes

The core execution layer of BMad bridges the gap between high-level specifications and repository file mutations. As documented across [Build a Change](https://docs.bmad-method.org/build/build-a-change/) and [Autonomous Development Loops](https://docs.bmad-method.org/build/autonomous-development-loops/), the framework establishes three specialized execution modes.

| Architectural Dimension | Interactive Mode (`bmad-build`) | Autonomous Worker (`bmad-build-auto`) | Orchestrated Loop (`bmad-loop`) |
|---|---|---|---|
| Primary Execution Harness | AI Coding IDE (Claude, Cursor, Copilot) | AI Harness with Subagent Capabilities | External Python CLI / TUI Engine |
| Human Interaction Model | Synchronous, in-the-loop pairing | Asynchronous, completely unattended | Asynchronous supervisory ("on-the-loop") |
| Scope of Authority | Single goal, interactive refinement | Single session-sized unit / story | Full epic / multi-story backlog |
| Backlog Awareness | None (acts on immediate input) | None (isolated worker contract) | Full (linear scheduler over story inventory) |
| Failure / Ambiguity Handling | Interactive elicitation & prompt dialogue | Immediate deterministic halt (`blocked`) | Checkpoint pause, TUI escalation, resume |
| Isolation Mechanism | Active working directory | Active working directory | Git worktree sandboxing (`[scm] isolation`) |
| Review Execution | Integrated tri-lens review with prompt | Subagent-driven multi-lens audit | Post-run verify commands & sweep bundles |
| Repository Mutation | Local diff and optional commit | Local commit on success; patch on halt | Automated commits, merges, and sweep logs |

##### Mode 1: Interactive Guided Implementation (`bmad-build`)

`bmad-build` serves as the primary interactive driver for engineers operating inside AI coding IDEs (such as Claude Code, Cursor, Copilot Workspace, or Codex). It is engineered for exploratory work, foundational system design, and high-risk stories where implementation choices establish patterns for subsequent modules.

**Operational Workflow:**

1. **Intent Ingestion and Evidence Reconnaissance**: The engineer invokes `/bmad-build` accompanied by an intent expression—ranging from a conversational problem description to a bug tracker URL or a formal story file. The skill inspects the repository, locating relevant files, architectural constraints, and configuration files before prompting the user.
2. **Intent Gap Discovery**: Rather than executing an exhaustive preliminary questionnaire, `bmad-build` identifies only material ambiguities that cannot be resolved through codebase inspection. Gaps are categorized across three dimensions: *Intent Gaps* (unstated assumptions that directly alter functional output), *Irreversible Actions* (destructive schema migrations, external API invocations, or data deletions), *Footprint* (cross-system file modifications exceeding safe single-session thresholds).
3. **Interactive Plan Approval**: If significant gaps or risks are detected, the agent drafts a lightweight implementation plan and prompts the engineer for approval. The engineer may refine assumptions, narrow scope, or reject flawed architectural directions.
4. **Implementation and Self-Healing Review**: Upon plan approval, the skill generates code, runs local test suites, and initiates the multi-lens code review pipeline. Deficiencies attributable to the current task are fixed autonomously; pre-existing codebase defects are captured and redirected to `deferred-work.md`.
5. **Human Walkthrough and Terminal Hand-off**: The workflow concludes by presenting a diff summary, offering guided verification via `bmad-walkthrough`, and preparing a localized Git commit with conventional commit semantics.

##### Mode 2: Autonomous Single-Session Worker Execution (`bmad-build-auto`)

Located at [skills/bmad-build-auto](https://github.com/bmad-code-org/BMAD-METHOD/tree/main/skills/bmad-build-auto), `bmad-build-auto` represents the unattended execution primitive. Unlike interactive tools, `bmad-build-auto` does not query the user, negotiate trade-offs, or manage backlogs. It operates as an isolated, idempotent worker assigned to execute exactly one session-sized unit of work.

**Core Operational Characteristics:**

- **Subagent Dependency**: The skill requires an underlying harness capable of spawning subordinate subagents. If subagent capabilities are absent, the workflow deterministically halts with the status `blocked: no subagents`.
- **Durable Machine-Readable Contract**: Progress is tracked through a structured frontmatter state machine embedded directly within the markdown specification artifact (`spec-<slug>.md` or `stories/<id>-<slug>.md`).
- **Deterministic Halting Policy**: The moment an unresolvable obstacle is encountered—such as an ambiguous requirement, missing test dependency, or non-converging review repair loop—the skill halts immediately, sets its frontmatter status to `blocked`, writes diagnostic context, and returns control to the caller.
- **Localized Scoping**: The worker modifies code and verifies tests, recording its baseline Git commit revision. It commits changes locally to ensure a clean working tree upon completion, but it is strictly prohibited from pushing upstream or selecting subsequent backlog items.

##### Mode 3: Orchestrated Continuous Development Loops (`bmad-loop`)

Hosted in its dedicated repository at [bmad-code-org/bmad-loop](https://github.com/bmad-code-org/bmad-loop), `bmad-loop` is an external, deterministic Python-based CLI and Terminal User Interface (TUI) orchestrator. It automates the execution of entire epics by coordinating a sequence of `bmad-build-auto` worker sessions.

**Core Operational Characteristics:**

- **Clean Separation of Concerns**: Pure Python manages all deterministic scheduling, file parsing, Git repository state, and CLI/TUI rendering. The LLM is confined exclusively to creative implementation and review within isolated, disposable agent contexts.
- **Git Worktree Isolation**: Under `[scm] isolation = "worktree"`, `bmad-loop` clones independent Git worktrees for story execution. If an autonomous worker fails catastrophically or pollutes the workspace, the failure is quarantined without corrupting the developer's primary checkout.
- **Dual Pipeline Ingestion**: The orchestrator schedules work from either classic `sprint-status.yaml` boards (Sprint Mode) or structured `stories.yaml` files within an epic directory (Stories Mode).
- **Automated Deferred Sweeps**: Review findings and split-off tasks deferred by workers are collected, triaged, and bundled into follow-up implementation runs through automated sweep policies (`[sweep] auto = true`).

---

#### Deep Dive: The Worker Contract and State Machine of `bmad-build-auto`

##### Primary Invocation Shapes

`bmad-build-auto` accepts five distinct invocation input shapes: Free-Form Intent (raw natural language directive), Issue or Ticket Pointer, Intent File Path, Existing Spec Path (resume execution), Folder-and-Identifier Dispatch (epic spec folder + story identifier).

##### Spec Frontmatter Lifecycle and Deterministic State Transitions

```
[Invocation]
     |
     v
  [draft] --(Validation Failure)--> [blocked: intent gap / unclear intent]
     |
     v (Passes Ready Gate)
[ready-for-dev]
     |
     v
[in-progress] --(Verification Failure)--> [blocked: verification failed]
     |
     v
 [in-review] --(Loop Exceeded > 5)--> [blocked: non-convergence]
     |
     v (Review Passed)
   [done] (Terminal Success)
```

| Lifecycle State | Operational Meaning | Permitted Next States |
|---|---|---|
| `draft` | Spec initialized; undergoing requirements and validation analysis | `ready-for-dev`, `blocked` |
| `ready-for-dev` | Requirements and architectural invariants validated; ready to build | `in-progress`, `blocked` |
| `in-progress` | Source code modifications and local test additions underway | `in-review`, `blocked` |
| `in-review` | Implementation completed; multi-lens adversarial review in progress | `done`, `in-progress` (repair), `blocked` |
| `done` | Implementation and review completed successfully; clean commit created | Terminal State (or re-review) |
| `blocked` | Unsafe to proceed unattended; execution halted with diagnostic reason | Terminal Halt (requires human re-arm) |

##### Folder-and-Identifier Dispatch Mechanisms

Folder+ID dispatch decouples the worker from hardcoded file naming conventions. When invoked with `<spec-folder>` and `<story-id>`: the worker reads `<spec-folder>/stories.yaml`, extracts the matching record, inspects `<spec-folder>/stories/` for an existing file. **First Dispatch** (no file exists): verifies parent `SPEC.md` exists, hydrates context from parent spec + preceding completed stories, creates the story file, transitions `draft` → `ready-for-dev`. **Resume Dispatch** (exactly one matching file): evaluates existing frontmatter status and resumes at the corresponding phase. Multiple matches or an existing `blocked` file: halts immediately to prevent destructive overwrites.

##### Blocking Conditions, Intent Gap Patches, and Recovery Protocols

- **Standardized Blocking Reasons**: `unclear intent`, `intent gap`, `no subagents`, `implementation verification failed`, `review repair loop exceeded 5 iterations`, `story already blocked`.
- **Intent-Gap Patch Preservation**: If the review stage identifies functionally robust code that implements an interpretation contrary to an unstated constraint, the worker reverts the working tree but serializes the entire attempted diff as a patch file under `{implementation_artifacts}/`, referenced in the spec's review log.
- **Deterministic Recovery Protocol**: A human/orchestrator applies the saved patch via `git apply`, resets frontmatter status to `in-review`, and re-invokes the worker — which bypasses re-implementation and proceeds directly to validation.

---

#### Deep Dive: Orchestration Mechanics and Sweep Architecture of `bmad-loop`

##### Architecture of the Python Orchestration Engine

`bmad-loop` is architected as an external control process written in modern Python (leveraging `uv` for dependency resolution). **Process Isolation**: launches coding agents in distinct, non-persistent processes, terminating each session upon story completion to fully reset LLM context memory between backlog items. **TUI**: real-time telemetry — active story progress, token burn estimates, verification status, pending human decisions.

##### Workspace Isolation via SCM Worktrees

Under `[scm] isolation = "worktree"`, the engine instantiates a dedicated secondary worktree outside the primary repository checkout. `bmad-build-auto` executes within this isolated tree; on success the engine merges the resulting commit back; on unrecoverable failure the entire worktree is discarded without collateral impact.

##### Dual Backlog Processing: Sprint Mode vs. Stories Mode

1. **Sprint Mode (Default)**: Ingests `_bmad-output/implementation-artifacts/sprint-status.yaml`. Traverses sequentially, dispatching workers for `ready-for-dev` stories, updating status through `in-progress` → `review` → `done`.
2. **Stories Mode (Opt-In)**: Ingests `<spec-folder>/stories.yaml` generated by `bmad-spec`. Strict Folder+ID dispatch, validating linear dependencies, reading output states from individual story spec files.

##### Deferred Work Sweeps, Decision Triage, and Auto-Bundling

- **Structured Deferral**: `bmad-build-auto` records out-of-scope defects into the spec's `deferred` frontmatter list (summary, evidence, source location, severity: `high`/`medium`/`low`).
- **Deferred Sweeps (`bmad-loop sweep`)**: At epic boundaries, aggregates all deferred items, correlates duplicates, filters false positives, groups into "sweep bundles."
- **Out-of-Band Decision Triage (`bmad-loop decisions`)**: Unresolved ambiguities surfaced via CLI/TUI; operator dismisses, approves for bundling, or logs into `.bmad-loop/decisions.json`.
- **Iterative Sweep Cycles**: `[sweep] repeat = true` re-triages after each cycle until zero actionable findings or a cycle threshold.

---

#### The BMad Organization Repository and Module Ecosystem

The open-source org at [GitHub bmad-code-org](https://github.com/bmad-code-org):

##### Core Framework: `BMAD-METHOD`
[bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) — primary methodology, workflows, templates, agent definitions.

**Specialized Personas**: Mary (`BA-01`, Business Analyst), John (`PM-02`, Product Manager), Sally (`UX-03`, UX Designer), Winston (`SA-04`, System Architect, authors `AD-N` decision records), Amelia (`SE-05`, Senior Software Engineer, drives both `bmad-build` and `bmad-build-auto`).

##### Autonomous Execution Engine: `bmad-loop`
[bmad-code-org/bmad-loop](https://github.com/bmad-code-org/bmad-loop) — unattended execution cycles, worktree sandboxing, backlog sweeps.

##### Agent and Module Authoring: `bmad-builder` (BMB)
[bmad-code-org/bmad-builder](https://github.com/bmad-code-org/bmad-builder) — conversational authoring for custom agents/skills/modules. Guided Discovery (conversational interviews for persona/constraint/contract definition). Static Quality Validation: 19 structural rules across 6 categories (syntax, path conventions, invocation schemas, frontmatter variables).

##### Quality Engineering: Test Architecture Enterprise (TEA)
[bmad-method-test-architecture-enterprise](https://github.com/bmad-code-org/bmad-method-test-architecture-enterprise) — Persona Murat (`TA-06`, Master Test Architect). Strict P0–P3 risk prioritization matrix, replacing line-coverage targets with behavior-driven validation. Nine testing workflows (TEA Academy, framework setup, CI integration, ATDD, Playwright E2E, NFR evidence audits). 36-row criteria registry, write-time file hook blocking anti-patterns pre-disk, `tea-test-review` headless CLI gate for CI/CD.

##### Developer Experience: `bmad-method-ui`
[bmad-code-org/bmad-method-ui](https://github.com/bmad-code-org/bmad-method-ui) — VS Code Extension (IDE sidebar GPS, parses `sprint-status.yaml`) and Next.js Standalone Dashboard (`MyBMAD`, browser-based team visibility, no local IDE required).

##### Creative Intelligence Suite (CIS) and Domain Modules
`bmad-module-creative-intelligence-suite` (lateral thinking, adversarial red-teaming), `bmad-module-game-dev-studio` (GDD/mechanics/level design), `bmad-method-wds-expansion` (Whiteport Design System tokens).

##### Deprecated Predecessors and Migration Pathways
`bmad-automator` — archived, superseded by `bmad-loop`. Legacy identifiers unified: `bmad-quick-dev` → `bmad-build`, `bmad-dev-auto` → `bmad-build-auto`, with non-destructive compatibility forwarding shims.

---

#### Governance, Data Privacy, and Repository-Local State

##### The Zero-Telemetry Architecture and Local Storage Paradigm

- **Zero Remote Runtime**: no centralized cloud service, hosted database, or intermediary proxy. Outbound traffic restricted to installation (`npm`/`uv`) and declared Git remotes.
- **Code and Prompt Residency**: flows exclusively between local IDE client and the enterprise's own authorized LLM endpoint. No BMad server receives telemetry or source code.
- **Repository as Single Source of Truth**: PRDs, UX diagrams, system spines, story backlogs, memory logs all committed as plain markdown/YAML.

##### Three-Layer Configuration Hierarchy and Anti-Subtraction Policies

1. **Shipped Defaults** — base instructions/templates/personas bundled with installed modules.
2. **Team Overrides (`_bmad/custom/`)** — committed, shared across contributors.
3. **Personal Overrides (`_bmad/config.user.toml`)** — uncommitted, gitignored.

**Anti-Subtraction Invariant**: customization permits addition and replacement but explicitly forbids silent deletion — nobody can secretly remove safety gates, verification passes, or architectural reviews established upstream.

---

#### Enterprise Adoption Patterns and Operational Recommendations

##### Staged Organizational Transition: In-the-Loop to On-the-Loop

1. **Stage 1 (Assisted Individuals)**: `bmad-build` for discrete tasks — interactive human-in-the-loop pairing.
2. **Stage 2 (Structured Pod Delivery)**: `bmad-spec`, `bmad-prd`, TEA — shared repo-native contracts, automated multi-lens review.
3. **Stage 3 (On-the-Loop Autonomous Orchestration)**: `bmad-loop` executes entire backlogs unattended across sandboxed worktrees — engineering bandwidth shifts to architectural curation and retrospective evaluation.

##### The Pod-of-Four Organizational Topology

Four multi-disciplinary engineers + shared PM/EM leadership. At least one member strong in product-systems thinking (spec fidelity, business alignment); another as AI Enabler (prompt harnesses, tooling, execution loops). Because cycle times collapse, one PM/EM pair can support multiple autonomous pods simultaneously.

##### Establishing Quality Gates and Mitigating Test Suite Rot

- **Mandate TEA Integration** — prohibit purely synthetic self-generated test suites; enforce risk-based P0–P3 coverage and test-to-requirement traceability.
- **Enforce Headless CI Gates** — `tea-test-review` mechanically blocks merges with unaddressed high-severity defects or broken acceptance criteria.
- **Audit Retrospective Action Items** — treat retrospective findings as binding constraints on subsequent epics.

---

#### Analysis of Recent Blog Insights and Engineering Paradigms

1. **Sharded Multi-Layer Review Architecture** — isolated adversarial perspectives (Blind Hunter, Edge Case Hunter, Acceptance Auditor) mitigate LLM confirmation bias; an agent reviewing its own code with full intent-knowledge systematically overlooks missing validations.
2. **Deterministic Infrastructure Over Model Persuasion** — structural enforcement increasingly delegated to deterministic code (Python worktree managers, 19-rule static skill linters, Git hooks) rather than elaborate system prompts, for enterprise-grade reproducibility.
3. **The Pre-Planning Halt as an Economic Lever** — the "intent gap" halt in `bmad-build-auto` is a major economic optimization: halting during planning costs one conversational turn; permitting an ambiguous run through code/tests/review expends tens of thousands of unnecessary tokens and produces diffs that must be reverted.

---

#### The bmad-quick-dev Pathway: Lineage, Architectural Role, and Evolution

In BMAD v5/early v6, `bmad-quick-dev` (Developer Amelia's menu trigger `QD`) was the primary implementation workflow. Post-v6.2.0 consolidation, refactored/unified into `bmad-build` (`BD`) and its headless counterpart `bmad-build-auto`. The "Quick Dev Path" is an accelerated trajectory: direct intent/issue → single-session spec → tri-lens verified implementation, optimized for changes under 500 LOC (vs. the full PRD → UX → Architecture → Epics → Stories path). Legacy configs migrate `_bmad/custom/bmad-quick-dev.toml` → `bmad-build.toml`.

#### The Canonical bmad-suite Ecosystem: Package Topology and Governance

The `bmad-suite` metapackage is the single source of truth for ecosystem population, enforced across `recipes/bmad-suite/recipe.yaml` run requirements, the `pyforge-doctor` suite watched set (Story 19.1), and the `steward` suite pipeline-truth cross-check.

| Active Member | Description and Role |
|---|---|
| `bmad-method` | Core Agile AI-driven development framework |
| `bmad-loop` | Deterministic Python ralph-loop orchestrator |
| `bmad-method-test-architecture-enterprise` | Enterprise test strategy, ATDD, release-gate governance (TEA) |
| `bmad-builder` | AI module and agent scaffolding expansion |
| `bmad-creative-intelligence-suite` | Innovation, storytelling, design thinking agents (CIS) |
| `bmad-module-skill-forge` | Instructions synthesis across Quick/Forge/Forge+/Deep tiers |
| `bmad-eval-quality` | Behavioral Evaluation Contracts compiler and scorer (joined 2026-09-05) |
| `bmad-utility-skills` | Contributor skills for PR review, triage, changelog, RCA |
| `bmad-labs-skills` | Community marketplace for Claude Code (22 general-purpose skills) |
| `bmad-module-template` | Scaffolding template for authoring new installable modules |
| `bmad-manticore` | AI video-production pipeline module (15 mc-* skills) |
| `bmad-dashboard` | VS Code extension for live project telemetry |
| `mybmad-dashboard` | Self-hosted web dashboard for BMad Method V6 projects |

**Deprecated/Parked** (never in `recipe.yaml` deps): `bmad-method-wds-expansion` (retired 2026-09-05, folded into `bmad-ux`), `bmad-autopilot`/`bmalph` (superseded by `bmad-loop`), `bmad-dashboard-extension` (superseded by `bmad-dashboard`), `bmad-story-automator` (recipe deleted 2026-08-21). Packaging via Pixi + conda-forge for pinning and release auditing.

---

#### Toward the Sovereign OpenIntelligence Hub: Integrating the OpenTeams Frame Spec and Own Your Intelligence Architecture

The BMad Method converges with the [Own Your Intelligence](https://ownyourintelligence.ai/) manifesto to establish a Sovereign AI paradigm for enterprise engineering. Rejects the "one moon fallacy" and dependency on commercial AI-as-a-service — organizations must not "rent their brains." Prioritizes private VPC/on-premise open-weight model deployment (vLLM, Nebari) so IP and operational intelligence stay under enterprise control.

##### The Triad Operating Model

- **Frames (The Dictionary / Context Layer)**: [OpenTeams Frame Spec](https://github.com/openteams-ai/frame-spec) — versioned Markdown/YAML capturing tacit domain knowledge, regulatory bounds, BMad's immutable five-field intent specs (Why, Capabilities, Constraints, Non-Goals, Success Signals).
- **Cogs (The Writer / Synthesizer Layer)**: BMad persona agents (Mary, John, Winston, Amelia, Murat) as operational facilitators executing within the active Frame's boundaries.
- **Ops (The Deterministic Machinery)**: Pure code pipelines — `bmad-loop` scheduling, Git worktree isolation, Conda/Pixi packaging, automated test runners.

##### Emerging Frame Spec Developments & Standards

`openteams-ai/frame-spec` introduces a frontmatter metadata protocol for schema conformance and Frame inheritance/composability (`extends`/`imports`) mirroring BMad's config cascade and "no silent subtraction" invariant. Establishes an Accountability Plane binding commit hashes, test traces, and Frame versions; conformance validation linters; dynamic MCP server resource hydration for IDEs.

##### The OpenIntelligence Hub Blueprint

Built on Nebari and the scientific Python stack (NumPy, SciPy, PyTorch, Dask, Conda) as private execution foundation. Requires the "Pod of Four" topology — engineers shift from "in-the-loop" prompting to "on-the-loop" supervisory governance as Frame Custodians.

#### Diagrams (as given)

**Four-Phase Agentic SDLC:**
```
graph TD
  P1[Phase 1: Analysis & Ideation] --> P2[Phase 2: Requirements & Solutioning]
  P2 --> P3[Phase 3: Implementation Slicing]
  P3 --> P4[Phase 4: Execution & Review]
  P4 --> |Feedback Loop| P2
```

**Autonomous Worker State Machine (Mode 2):**
```
stateDiagram-v2
  [*] --> draft
  draft --> blocked: Intent Gap / Unclear
  draft --> ready_for_dev: Passes Ready Gate
  ready_for_dev --> in_progress
  in_progress --> blocked: Verification Failed
  in_progress --> in_review
  in_review --> in_progress: Repair (Loop < 5)
  in_review --> blocked: Non-convergence / Stash Patch
  in_review --> done: Review Passed
  done --> [*]
```

---

#### Synthesis and Strategic Conclusions

BMad is a fundamental architectural departure from both naive AI code completion and unconstrained autonomous agent frameworks: primacy of the specification, repo-native plain-text state persistence, disciplined three-tiered execution (`bmad-build`, `bmad-build-auto`, `bmad-loop`) — a defensible, auditable foundation for scaling AI-native software engineering.

- **Invest in Front-Loaded Intent** — the highest-leverage contribution occurs before code generation; rigorous specs are the sole defense against codebase degradation.
- **Select the Appropriate Execution Mode** — interactive (`bmad-build`) for foundational/pattern-setting work; autonomous workers/loops once architectural patterns have stabilized.
- **Enforce Independent Quality Gates** — couple autonomous loops with TEA so test suites stay durable, behavior-focused, and immune to generative rot.

#### References

1. [BMad Code Official Portal](https://bmadcode.com/)
2. [BMad Method Architectural Overview](https://bmadcode.com/method)
3. [The BMad Philosophy of the AI-SDLC](https://bmadcode.com/philosophy)
4. [BMad Method Official Documentation](https://docs.bmad-method.org/)
5. [Autonomous Development Loops Documentation](https://docs.bmad-method.org/build/autonomous-development-loops/)
6. [Build a Change Documentation](https://docs.bmad-method.org/build/build-a-change/)
7. [Choose a Planning Path Documentation](https://docs.bmad-method.org/plan/choose-a-planning-path/)
8. [BMad Method Core Repository](https://github.com/bmad-code-org/BMAD-METHOD)
9. [BMad Loop Autonomous Orchestrator](https://github.com/bmad-code-org/bmad-loop)
10. [BMad Builder Repository](https://github.com/bmad-code-org/bmad-builder)
11. [Test Architecture Enterprise](https://github.com/bmad-code-org/bmad-method-test-architecture-enterprise)
12. [BMad Method UI Repository](https://github.com/bmad-code-org/bmad-method-ui)
13. [BMad Method v6.2.1 Changelog and Announcements](https://www.bmadcode.com/bmad-method-v6-2-1-rebuilt-code-review-smarter-quick-dev-and-a-growing-global-community/)
