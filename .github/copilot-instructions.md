# AI Agent Instructions (GitHub Copilot)

Read `AGENTS.md` at the repo root first: its `bmad:context` block carries the verified
policy, gates, and pitfalls every tool must follow. Then read `CLAUDE.md` for the
Claude-specific detail it adds (conda-forge-expert lifecycle, BMAD multi-project switch,
PR CI gates, skill reference).

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
