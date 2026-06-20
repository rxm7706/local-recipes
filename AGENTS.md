# AGENTS.md — cross-tool guide for this repo

This is the **framework-neutral** entry point for any coding agent or agentic framework
(Claude Code, Cursor, GitHub Copilot, Gemini, Devin, Codex, Aider, BMAD, Agno, CrewAI, …).
It is intentionally tool-agnostic: the **spec is the contract; the agent/framework is
interchangeable.**

## Spec-driven: where specs live

**All specs live in `docs/specs/*.md`** — plain markdown, version-controlled, neutral. Before
implementing anything, read the relevant spec there. Specs are the durable source of truth; they
do **not** live inside any framework's working tree.

## Spec-first workflow (MANDATORY — every agent, every framework)

1. **No non-trivial work without a spec.** Before implementing a feature, migration, packaging
   effort, or refactor, a spec MUST exist in `docs/specs/<name>.md`. If none exists, **create it
   first** (use the `spec-driven-development` skill, `bmad-create-*`, or hand-author one matching the
   existing specs) and get it to `status: ready` before writing code.
2. **Keep the spec's `status:` current** — it is the framework-neutral source of truth for whether
   work is a draft or implemented. Transition it as you go:
   `draft → ready → in-progress → shipped` (set `implemented_by:` + `shipped_ref:` when shipped).
   This applies **no matter who does the work** — Claude, Cursor, Gemini, Devin, Copilot, a human,
   or any agentic framework (BMAD, Agno, CrewAI…). Don't leave a shipped feature marked `draft`, or
   a draft marked `shipped`.
3. **Frontmatter contract** for every `docs/specs/*.md`:
   ```yaml
   status: draft | ready | in-progress | shipped | workflow | superseded | abandoned
   implemented_by: bmad-quick-dev | human | cursor | devin | …   # who did it (when in-progress/shipped)
   shipped_ref: "conda-forge-expert v8.6.0" | "PR #33764" | "<commit>"   # evidence (when shipped)
   spec_updated: YYYY-MM-DD
   ```
4. **Verify:** `pixi run -e local-recipes bmad-drift-check --specs` lists every spec's status +
   whether it's indexed; `bmad-drift-check` HARD-fails on misfiled specs and flags un-indexed ones.

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
