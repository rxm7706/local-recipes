# GitHub Copilot — read AGENTS.md

`AGENTS.md` at the repo root is the whole cross-tool contract (verified `bmad:context` block,
Dream-first workflow, tier model, team memory, pre-PR checklist). The Copilot cloud agent and the
Copilot CLI load it natively (root and nested, nearest wins); VS Code chat loads it through
`.vscode/settings.json` → `chat.useAgentsMdFile`. This file is the Copilot-only addendum and must
not repeat `AGENTS.md` (`spec-pyforge-scribe` CAP-27 — a scribe meta-test reds a duplicated
section).

Copilot-specific:
- The cloud agent's sandbox is provisioned by `.github/workflows/copilot-setup-steps.yml`
  (job `copilot-setup-steps`) with **`pyforge-guild`** — the session default for every harness
  (detectors, ledger sync, surface stamps, marshal dispatch, steward; ~860 MB, frozen). Never
  install `local-recipes` (Mason's 10 GB recipe-factory environment) unless the task is a conda
  recipe. A session has a 59-minute hard cap — plan one story, not an epic.
- Because the agent also ingests `CLAUDE.md` and `GEMINI.md`, never copy their content here.
- Verify with `/instructions` (CLI) or the **References** list on a chat reply that `AGENTS.md` was
  loaded.
- Before the 59-minute session ends, run `scribe capture` — the session-close ritual for every
  harness (`AGENTS.md` § *Team memory*), not a Copilot-specific step.
