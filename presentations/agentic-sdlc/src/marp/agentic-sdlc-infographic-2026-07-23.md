---
marp: true
size: 16:9
paginate: true
theme: default
style: |
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
  section { background:#F6F4EE; color:#0E1C30; font-family:'IBM Plex Sans',sans-serif; font-size:24px; padding:64px 84px; }
  h1 { font-family:'Space Grotesk',sans-serif; font-weight:600; font-size:46px; line-height:1.08; letter-spacing:-0.02em; margin:0 0 0.35em; }
  h2,h3 { font-family:'Space Grotesk',sans-serif; font-weight:600; letter-spacing:-0.01em; }
  h6 { font-family:'IBM Plex Mono',monospace; font-weight:500; letter-spacing:0.22em; text-transform:uppercase; color:#2F86DD; font-size:14px; margin:0 0 0.2em; }
  strong { color:#C8901A; font-weight:600; }
  code { font-family:'IBM Plex Mono',monospace; background:rgba(14,28,48,0.08); padding:1px 5px; border-radius:4px; }
  pre { background:rgba(14,28,48,0.05); border:1px solid rgba(14,28,48,0.18); border-radius:6px; font-size:17px; line-height:1.5; }
  pre code { background:none; padding:0; }
  a { color:#2F86DD; }
  ul { font-size:.9em; } li { margin:0.16em 0; }
  hr { border:none; border-top:3px solid #0E1C30; margin:.3em 0; }
  table { font-size:.66em; border-collapse:collapse; }
  th { background:#0E1C30; color:#F6F4EE; text-align:left; }
  th,td { border:1px solid #D8D3C7; padding:5px 9px; }
  section::after { color:#8A94A3; font-family:'IBM Plex Mono',monospace; font-size:14px; }
---

<!-- _backgroundColor: #0B1626 -->
<!-- _color: #F6F4EE -->

###### A FIELD GUIDE FOR ENGINEERS · INFOGRAPHIC

# Agentic AI across the software lifecycle

Not autocomplete on steroids — a **structured, spec-driven** way to build software with AI agents as expert collaborators, from first idea to shipped code. The concrete framework: the open-source **BMAD Method**.

Spec-driven development · agent-team framework · human-in-the-loop · MIT

---

## At a glance

| Framework | Install | Runs in | Story counts | License |
| --- | --- | --- | --- | --- |
| BMAD Method (core · BMM) | `npx bmad-method install` | Claude Code · Cursor · Codex | 1 → 50+ (scale-adaptive) | MIT |

### The story arc — six acts

**I** The case for change · **II** Spec-driven development · **III** Choosing your framework · **IV** The BMAD agent team · **V** The four phases · **VI** Scale, governance & ecosystem

---

<!-- _backgroundColor: #0B1626 -->
<!-- _color: #F6F4EE -->

###### PART I

# The idea

Why the AI-augmented status quo isn't enough — and what *agentic* actually means.

---

## The shift — from a tool that types to a collaborator that follows a process

**Prompt-and-pray** — you describe a feature, the model produces average code from vague context, and the architectural choices are buried inside the output. Great for a snippet, fragile for a system.

**Agentic development** — specialist agents guide you through a real process — analysis, planning, design, build — producing decisions and documents you can read, review, and reuse.

The output isn't just code. It's a chain of reviewable artifacts — a brief, a spec, an architecture, a story — each grounding the next.

---

## The maturity spectrum — who executes the phase?

| Level | Who executes | Where the context lives |
| --- | --- | --- |
| 1 · Manual | Humans do everything | Heads & meetings |
| 2 · AI-augmented | Humans execute, AI assists | Heads & chat history |
| 3 · **Agentic** *(this deck)* | Agents run each phase; humans direct & gate | **Documents agents read & write** |
| 4 · Autonomous | Unattended loops — intent in, code out | Documents + run traces |

The jump from **2 to 3** isn't better models — it's **where the context lives**: out of your head and chat history, into specs.

---

## Spec-driven development — the operating model

Write the specification **first** — a precise, versioned document of behavior, constraints, and acceptance criteria — then have AI generate and validate code **against it**.

```
VIBE CODING    prompt → code → hope
SPEC-DRIVEN    intent → spec → human review → generate → validate
```

- **The documentation is the brain** — agents are transient workers that read and write persistent docs; nothing relies on leaky chat memory.
- **A funnel, not a loop** — **WHY** (brief) → **WHAT** (PRD) → **HOW** (architecture) → **BUILD** (code); no agent writes code until the *what* and *how* are frozen.

---

<!-- _backgroundColor: #0B1626 -->
<!-- _color: #F6F4EE -->

###### PART II

# The method

A team of named specialists — spec-driven, document-anchored, phase-gated.

---

## The crew — a team of specialists, one per phase

| Agent | Role | Phase | Owns |
| --- | --- | --- | --- |
| **Mary** | Business Analyst | Analysis | brainstorming, research, briefs, PRFAQs |
| **Paige** | Technical Writer | Analysis | docs, diagrams, doc validation |
| **John** | Product Manager | Planning | PRDs, epics & stories, readiness |
| **Sally** | UX Designer | Planning | experience & design specs |
| **Winston** | System Architect | Solutioning | technical architecture, alignment |
| **Amelia** | Senior Engineer | Implementation | story execution, code review, sprints |

You don't talk to one monolithic AI — you talk to named teammates. *"Hey Mary, let's brainstorm,"* and she gets on with it. Identity is fixed; behavior is customizable.

---

## Four phases, one throughline

1. **Analysis** *(optional)* — explore the problem before committing. → Brainstorm · Research · Brief · PRFAQ
2. **Planning** *(what & why)* — define what to build, and for whom. → PRD · UX spec
3. **Solutioning** *(how)* — decide how, break work into stories. → Architecture · Epics · Readiness gate
4. **Implementation** *(build)* — build it, one story at a time. → Story · Dev · Review · Retro

**Decide the hard things once** — or Agent 1 builds Epic 1 with REST while Agent 2 builds Epic 2 with GraphQL. Catching alignment in solutioning is **10× cheaper** than mid-sprint.

---

## The execution matrix — the handoff is a file, not a chat thread

| Phase | Persona | Reads | Produces |
| --- | --- | --- | --- |
| Analysis | Mary | Raw idea / brain dump | `brief.md` |
| Planning | John | `brief.md` | `prd.md` |
| Solutioning | Winston | `prd.md` | `architecture.md` · epics & stories |
| Implementation | Amelia | `architecture.md` · story files | source code + tests |

The per-story heartbeat: **create story → dev story → code review → (retro at each epic's end)**, with `correct-course` for mid-sprint changes. Everything lands in `_bmad-output/` in git — new chat, same artifacts.

---

<!-- _backgroundColor: #0B1626 -->
<!-- _color: #F6F4EE -->

###### PART III

# At scale

Sizing the method, building *for* agents, and the wider ecosystem.

---

## Ceremony sized to the work

| Track | Best for | Documents created |
| --- | --- | --- |
| **Quick Flow** | Bug fixes, clear scope · 1–15 stories | Tech-spec only |
| **BMad Method** | Products & platforms · 10–50+ stories | PRD + Architecture + UX |
| **Enterprise** | Compliance, multi-tenant · 30+ stories | + Security + DevOps |

**Parallel track** — `bmad-quick-dev` (clarify → plan → implement → review in one flow) and `bmad-dev-auto` (one unattended iteration) skip phases 1–3 for small, well-understood work. *Rule of thumb: if multiple epics could be built by different agents, you need the full method.*

---

## The flip side — don't just build *with* agents, build *for* them

- **Interfaces** — clean DOM hierarchies, ARIA, deterministic layouts agents can navigate. No vibe UI.
- **APIs** — idempotent & self-documenting: strict schemas, retry-safe mutations, errors actionable enough to self-correct mid-flight.
- **The harness** — guardrails & traces: tools explicitly exposed for LLM calling, schema validation, exhaustive run-trace logs.

### One core, a growing family of modules

**BMM** *(core)* · **BMB** Builder — your own agents · **TEA** Test Architect — risk-based test strategy · **BMGD** Game Dev · **CIS** Creative Intelligence. All MIT, all `npx`-installed.

---

## Six principles that transfer to any tool

- **Structure beats prompting** — a process gets better output than a clever one-liner.
- **Documents are context** — each artifact grounds the next agent's decisions.
- **Decide hard things once** — explicit architecture prevents agent conflicts.
- **Match ceremony to scale** — quick flow for small; full method for complex.
- **Keep a human in the loop** — you choose how tight the automation runs.
- **Fix the doc, not the code** — wrong output is an upstream spec flaw; correct it and rerun.

---

<!-- _backgroundColor: #0B1626 -->
<!-- _color: #F6F4EE -->

###### THE TAKEAWAY

# Don't hand off your judgment. Give it a structure to work in.

Pick something small this week and run it end to end — the fastest way to understand agentic development is to do one full loop.

↳ docs.bmad-method.org · ↳ github.com/bmad-code-org/BMAD-METHOD · ↳ bmadcode.com/web-bundles
