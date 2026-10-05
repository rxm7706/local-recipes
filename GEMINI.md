# Gemini CLI — the neutral contract

This repo is Dream-first and framework-neutral — read `AGENTS.md` at the repo root for the
full cross-tool guide. The sections below are generated from the SAME fragments `AGENTS.md`'s
own managed regions render from — same tiers, same paths, same git dispositions — framed for
the Gemini CLI.

## The tiers (do not cross them)

| Tier | Location | Purpose | Git |
|---|---|---|---|
| **0 — Dream** | `docs/dreams/*.md` | The raw human aspiration / starting point (BMAD — *Build More Architect Dreams*); Herald renders it into a deck, and BMAD turns it into the spec | tracked, permanent |
| **1 — Intake spec (LEGACY)** | `docs/specs/*.md` | Former hand-authored spec tier — kept for existing efforts, **superseded by Tier 2**; author no new files here | tracked, phasing out |
| **2 — Spec & planning (BMAD)** | `_bmad-output/projects/<slug>/planning-artifacts/` | The `bmad-spec` output + PRD, architecture, API/interface specs, epics+stories, gate reports — produced from the Dream. **The active spec lives here.** | tracked, permanent |
| **3 — Execution output** | `_bmad-output/projects/<slug>/implementation-artifacts/` (BMAD); your own tool dir for others | story files, sprint YAMLs, test outputs, retros | **local-only / gitignored** |

**Rules:**
- The **active spec is a BMAD artifact in Tier 2** — produced from a Tier-0 Dream. Don't hand-author
  a new spec in the legacy `docs/specs/` (Tier 1), and never drop one into a Tier-3 output dir.
- Each tool writes its working output into **its own** area (BMAD → `implementation-artifacts/`;
  Cursor → `.cursor/`; etc.) and **reads the spec from the BMAD planning folder** (Tier 2) — or a
  legacy `docs/specs/` file for an existing effort.
- `implementation-artifacts/` is gitignored/local-only — **nothing there should be git-tracked.**


## Portability contract (why this stays framework-neutral)

BMAD *produces* the spec, but the spec stays portable — you are **not locked to BMAD**. The
neutral / framework-specific line runs *through* the spec:

- **Shared, portable layers:** the **Dream** (`docs/dreams/`, the WHY) and the **neutral
  Spec** (`bmad-spec`'s output — the WHAT + machine-checkable acceptance criteria, i.e. the
  verification oracle). Both are framework-agnostic by construction.
- **Per-framework layers:** decomposition (BMAD epics/stories vs. CrewAI crews vs. LangGraph
  nodes) and execution (orchestration, sprints, run traces) belong to whichever framework runs —
  BMAD, CrewAI, Agno, LangGraph, Devin, ….

So another framework has **two entry points**: (1) start from the **Dream** and do everything its
own way, or (2) consume the **neutral Spec** and diverge only at decomposition/execution —
which also lets you verify (and compare) any framework's build against the *same* oracle.

**The one property to protect:** the Spec's acceptance criteria must stay
framework-agnostic and machine-checkable (behavior + oracle — never "BMAD story 3.2 passed").
Keeping the Dream → spec handoff portable across agents is **Herald's** job.


## Dream-first workflow (MANDATORY — every agent, every framework)

1. **No non-trivial work without a Dream + spec.** Before implementing a feature, migration,
   packaging effort, or refactor, a **Dream** must exist in `docs/dreams/<slug>.md`, and BMAD must
   have produced its **spec** (via `bmad-spec` or the planning chain) in
   `_bmad-output/projects/<slug>/planning-artifacts/`. Never code from a bare prompt.
2. **Keep the spec's status current** as work proceeds (`draft → ready → in-progress → shipped`) —
   no matter who does the work (Claude, Cursor, Gemini, Devin, Copilot, a human, or any agentic
   framework). BMAD specs track status in the framework; legacy `docs/specs/*.md` track it in
   `status:` frontmatter.
3. **Autonomy.** Marshal (`bmad-loop` / `bmad-build-auto`) can watch `docs/dreams/`, run `bmad-spec`
   on a new Dream, and drive the build unattended — so "a Dream is written" can trigger "BMAD
   creates the spec" with no human in the loop.

