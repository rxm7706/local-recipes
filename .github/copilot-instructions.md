# AI Agent Instructions

**CRITICAL SYSTEM PROMPT:** 
Before answering any questions, analyzing the codebase, writing any code, or taking any actions, you MUST read the exact contents of the `CLAUDE.md` file located in the root of this repository. 

`CLAUDE.md` is the absolute master source of truth for:
1. Behavioral guidelines (BMAD Method)
2. Project context and codebase architecture
3. Formatting rules (recipe.yaml vs meta.yaml)
4. Allowed tools, workflows, and MCP servers

You must adopt the persona and follow all the rules defined in `CLAUDE.md` for this session. Do not proceed without referencing it.

## Dream-first workflow (also read `AGENTS.md`)

This repo is **Dream-first and framework-neutral** — see **`AGENTS.md`** at the repo root.
- **Everything starts with a Dream in `docs/dreams/*.md`** — the raw aspiration; BMAD-method
  turns it into the spec (`bmad-spec`, or the planning chain for product scope).
- **The active spec is a BMAD artifact** in `_bmad-output/projects/<slug>/planning-artifacts/`.
- Tier model (do not cross): Tier-0 Dream = `docs/dreams/`; Tier-1 = `docs/specs/`
  (**LEGACY** — kept for in-flight efforts, author no new specs there); Tier-2 spec & planning =
  `_bmad-output/projects/<slug>/planning-artifacts/`; Tier-3 execution output =
  `_bmad-output/projects/<slug>/implementation-artifacts/` (gitignored/local-only).
- A spec never belongs in a Tier-3 output dir.
