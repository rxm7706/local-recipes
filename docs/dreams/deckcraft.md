---
title: Deckcraft — editable decks from primitives, air-gapped
type: dream
owner: herald
status: seeded
---

# Deckcraft — the deck pipeline that works behind the firewall

## The Dream

An air-gapped, conda-forge-native AI pipeline that generates **editable**
PowerPoint, Marp markdown, infographics, and images — from primitives, not by
repackaging someone's SaaS. Multi-surface by design: a Claude Skill, an MCP
server for Copilot/MS365, and a CLI — so the same deck machinery serves an
interactive session, an enterprise Office stack, and a headless factory run.

## Why it matters now (its first consumer)

The 2026-07-23 export revisit designated deckcraft **the editable-PPTX engine
for the deck family's Standard export set** (`presentation-deck.md` § Export
decisions revisited): `marp --pptx` renders image-slides — fine for
distribution, useless for editing — so `deck-export` grows a deckcraft backend,
and every family deck's PPTX becomes real, editable slides.

## What is real

- The BMAD project `deckcraft` (registered, active; complements
  [[presenton-pixi-image]] — built from primitives, not a repackage).
- The toolchain already in the pixi envs: `python-pptx`, `pptxgenjs`, `marp-cli`,
  markitdown, chart + local-image-gen deps.
- **Found assets (2026-07-23, Sentinel Design project):** a working design-tokens
  pipeline — `tokens-to-potx.py`, `potx-to-tokens.py`, Figma-variable bridges —
  i.e. the PPTX-template half of the dream already has code ([[modernist-identity]]).

## Realization log

- **2026-07** — project registered in PROJECTS.md.
- **2026-07-23** — designated the family PPTX engine; token-pipeline assets
  discovered and claimed. Awaits its `bmad-spec` run; air-gap posture per
  [[enterprise-airgap]].
- **2026-07-23 (gist audit)** — its intake brief already exists: `docs/intake/gists/open-source-powerpoint-agent-skills/` — a BMAD-ready Project Intent for MIT/Apache pptx agent skills.
