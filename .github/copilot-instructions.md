# AI Agent Instructions

**CRITICAL SYSTEM PROMPT:** 
Before answering any questions, analyzing the codebase, writing any code, or taking any actions, you MUST read the exact contents of the `CLAUDE.md` file located in the root of this repository. 

`CLAUDE.md` is the absolute master source of truth for:
1. Behavioral guidelines (BMAD Method)
2. Project context and codebase architecture
3. Formatting rules (recipe.yaml vs meta.yaml)
4. Allowed tools, workflows, and MCP servers

You must adopt the persona and follow all the rules defined in `CLAUDE.md` for this session. Do not proceed without referencing it.

## Spec-driven workflow (also read `AGENTS.md`)

This repo is **spec-driven and framework-neutral** — see **`AGENTS.md`** at the repo root.
- **Specs live in `docs/specs/*.md`** — read the relevant spec before implementing.
- Tier model (do not cross): Tier-1 intake = `docs/specs/`; Tier-2 planning =
  `_bmad-output/projects/<slug>/planning-artifacts/`; Tier-3 execution output =
  `_bmad-output/projects/<slug>/implementation-artifacts/` (gitignored/local-only).
- An intake spec always belongs in `docs/specs/`, never in a Tier-3 output dir.
