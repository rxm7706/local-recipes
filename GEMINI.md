# Gemini CLI / Antigravity — read AGENTS.md

`AGENTS.md` at the repo root is the whole cross-tool contract (Dream-first workflow, tier model,
team memory, pre-PR checklist). Gemini loads it **first** through the checked-in
`.gemini/settings.json` (`context.fileName: ["AGENTS.md", "GEMINI.md"]`); this file is the
Gemini-only addendum and must not repeat `AGENTS.md` (`spec-pyforge-scribe` CAP-27 — a scribe
meta-test reds a duplicated section).

Gemini-specific:
- Confirm the load with `/memory show` (both files must appear) and `/memory reload` after editing.
- `GEMINI.md` may `@import` other files, but everything cross-tool belongs in `AGENTS.md`, not here.
- Work in your own worktree and land through a PR (`AGENTS.md` § *Trunk, worktrees, PRs*); never run
  `scripts/bmad-switch` from a parallel session — pass `BMAD_ACTIVE_PROJECT=<slug>` instead.
- Before ending a session, run `scribe capture` — the session-close ritual for every harness
  (`AGENTS.md` § *Team memory*), not a Gemini-specific step.
