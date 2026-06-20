# AGENTS.md — cross-tool guide for this repo

This is the **framework-neutral** entry point for any coding agent or agentic framework
(Claude Code, Cursor, GitHub Copilot, Gemini, Devin, Codex, Aider, BMAD, Agno, CrewAI, …).
It is intentionally tool-agnostic: the **spec is the contract; the agent/framework is
interchangeable.**

## Spec-driven: where specs live

**All specs live in `docs/specs/*.md`** — plain markdown, version-controlled, neutral. Before
implementing anything, read the relevant spec there. Specs are the durable source of truth; they
do **not** live inside any framework's working tree.

## The three tiers (do not cross them)

| Tier | Location | Purpose | Git |
|---|---|---|---|
| **1 — Intake spec** | `docs/specs/*.md` | The "what to build" contract every tool reads | tracked, permanent |
| **2 — Planning** | `_bmad-output/projects/<slug>/planning-artifacts/` | PRD, architecture, API/interface specs, epics+stories list, gate reports (BMAD-generated) | tracked, permanent |
| **3 — Execution output** | `_bmad-output/projects/<slug>/implementation-artifacts/` (BMAD); your own tool dir for others | story files, sprint YAMLs, test outputs, retros, derived per-effort specs | **local-only / gitignored** |

**Rules:**
- An **intake spec belongs in Tier 1 (`docs/specs/`)** — never drop it into a Tier-3 output dir.
- Each tool writes its working output into **its own** area (BMAD → `implementation-artifacts/`;
  Cursor → `.cursor/`; etc.) and **reads the spec from `docs/specs/`**.
- `implementation-artifacts/` is gitignored/local-only — **nothing there should be git-tracked.**

## How each tool discovers this

| Tool | Entry file (thin pointer → this file + `docs/specs/`) |
|---|---|
| Claude Code | `CLAUDE.md` (full repo guidance) |
| Cursor | `.cursor/rules/specs.mdc` |
| GitHub Copilot | `.github/copilot-instructions.md` |
| Gemini CLI | `GEMINI.md` |
| Devin / Codex / Factory / Zed | this `AGENTS.md` |
| Agentic frameworks (BMAD, Agno, CrewAI, LangGraph) | load the `docs/specs/<X>.md` markdown into the agent's task context programmatically (BMAD: `bmad-quick-dev` consumes it) |

## Keeping the BMAD planning docs accurate

The `_bmad-output/projects/local-recipes/` artifacts are kept in sync with the live repo by a
detector + reconciler loop — run `pixi run -e local-recipes bmad-drift-check` and follow
`_bmad-output/projects/local-recipes/SYNC-RUNBOOK.md`. The detector also enforces the tier rules
above (e.g. it HARD-fails if a spec is git-tracked under `implementation-artifacts/`).
