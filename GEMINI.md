# Gemini — read AGENTS.md

This repo is **Dream-first and framework-neutral**. Read **`AGENTS.md`** at the repo root for the
full convention.

Key points:
- **Everything starts with a Dream in `docs/dreams/*.md`** — the raw aspiration; BMAD-method
  turns it into the spec (`bmad-spec`, or the planning chain for product scope).
- **The active spec is a BMAD artifact** in `_bmad-output/projects/<slug>/planning-artifacts/`.
- Tier model (do not cross): Tier-0 Dream = `docs/dreams/`; Tier-1 = `docs/specs/`
  (**LEGACY** — kept for in-flight efforts, author no new specs there); Tier-2 spec & planning =
  `_bmad-output/projects/<slug>/planning-artifacts/`; Tier-3 execution output =
  `_bmad-output/projects/<slug>/implementation-artifacts/` (gitignored/local-only).
- A spec never belongs in a Tier-3 output dir.
