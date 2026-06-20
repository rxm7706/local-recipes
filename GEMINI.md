# Gemini — read AGENTS.md

This repo is **spec-driven and framework-neutral**. Read **`AGENTS.md`** at the repo root for the
full convention.

Key points:
- **Specs live in `docs/specs/*.md`** — read the relevant spec before implementing.
- Tier model (do not cross): Tier-1 intake = `docs/specs/`; Tier-2 planning =
  `_bmad-output/projects/<slug>/planning-artifacts/`; Tier-3 execution output =
  `_bmad-output/projects/<slug>/implementation-artifacts/` (gitignored/local-only).
- An intake spec always belongs in `docs/specs/`, never in a Tier-3 output dir.
