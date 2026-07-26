---
title: Agent portability — BMAD on any agent, never vendor-locked
type: practice
owner: marshal
status: dreamt
---

# Agent portability — the method outlives the tool

## The Dream

Marshal's reach (re-scoped from Herald in the 2026-07-23 ownership review —
Herald keeps the communication face): **the operating model runs on whichever
agent the team uses** —
Devin, GitHub Copilot (and its agents), Claude, Cursor, Gemini — and planning
runs on flat-rate subscriptions instead of metered IDE tokens. The method is
the asset; the agent is a socket. Corollary (the AGENTS.md Portability
contract): the Dream and the neutral Spec are the shared layers; only
decomposition and execution are per-framework — so any framework's build can be
verified against the same oracle.

## What it looks like when real

- A Copilot subscription driven as a local model backend (five bridge patterns:
  `copilot-api`, `litellm`, `copilot-openai-api`, `copilot-api-proxy`, `c2p`).
- A sideload VS Code extension wrapping the bridge, with BMAD-runner +
  multiproject stories backing unattended `bmad-loop` on non-Claude backends.
- The `@bmad` Copilot-Chat adapter upstreamed into the official `bmad-dashboard`
  extension; BMAD web bundles installed as Gemini Gems / Custom GPTs.
- Cross-tool entry files (AGENTS.md → CLAUDE.md / `.cursor/rules` / GEMINI.md /
  copilot-instructions) staying in lockstep — enforced, not hoped.

## What is real

- The copilot-api bridge patterns (`copilot-api`, `litellm`, `copilot-openai-api`,
  `copilot-api-proxy`, `c2p`) — decision tree, auth flows, config. _(The standalone
  reference doc was removed 2026-07-24; the patterns live on in the specs below.)_
- Specs ready: `copilot-bridge-vscode-extension.md` (incl. stories 13–15),
  `bmad-copilot-adapter-upstream.md` (draft — contribution-path decision open).
- The Portability contract landed in AGENTS.md (2026-07-23); the four-pointer
  entry-file family synced the same day.

## Realization log

- **2026-07** — copilot-to-api research consolidated; extension spec waved.
- **2026-07-23** — Dream retro-seeded; named as Herald's "BMAD everywhere"
  responsibility in [[pyforge-charter]].
- **2026-07-23 (gist audit)** — grounding: `docs/intake/gists/awesome-bmad-…/` (the curated BMAD ecosystem list) + `run-bmad-in-microsoft-copilot/` (declarative-agent setup for the 6 web bundles).
- **2026-07-23 (ownership review)** — re-scoped to **Marshal** (alternate
  agents = alternate lines on the same floor); Herald retains docs/comms.
