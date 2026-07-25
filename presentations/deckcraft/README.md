# Deckcraft deck (`deckcraft`)

**Status: authored 2026-07-25 — 10 slides, extract + build green.** Engine + glue copied
**verbatim** from `presentations/pyforge-steward/` (Archivo / Modernist system). Dream:
`docs/dreams/deckcraft.md`; the Spec and its planning chain live in
`_bmad-output/projects/deckcraft/planning-artifacts/`.

Deckcraft is the air-gapped, conda-native pipeline that generates **editable** PPTX, Marp
and infographics **from primitives** — not by repackaging a SaaS — surfaced as a Claude
Skill, an MCP stdio server and a CLI. It is also the PyForge deck family's designated
editable-PPTX engine (§ *Export decisions revisited*, 2026-07-23), so this deck's own
PowerPoint exports are interim artifacts until deckcraft ships.

Workflow: `docs/specs/presentation-deck.md` (prototype contract, § Standard export set,
§ The MCP bridge). `npm install && npm run extract && npm run dev`.
Engine files stay byte-identical across every deck.

## Artifact map (the § Standard 6-artifact family)

| Artifact | Path |
|---|---|
| Deck prototype (source of truth) | `project/Deckcraft.dc.html` — 10 sections at 1920×1080 |
| Executive summary | `project/Deckcraft - Executive Summary.dc.html` |
| Infographic (trio head — edit here) | `project/Deckcraft - Infographic.dc.html` (1240×2280 one-pager) |
| Infographic standalone | `project/Deckcraft Infographic standalone.html` (same body, no `x-dc`, styles in `<head>`) |
| Infographic Deck | `project/Deckcraft - Infographic Deck.dc.html` (7 slides — same sections at 1920×1080) |
| Marp sources | `src/marp/deckcraft-{deck,executive-summary,infographic}-2026-07-25.md` |
| Derived exports | `src/marp/deckcraft-infographic-standalone-2026-07-25.html`, `src/pptx/deckcraft-deck-2026-07-25.pptx`, `src/pptx/deckcraft_infographic_deck-2026-07-25.pptx` |

Regenerate the derived set with `pixi run -e local-recipes deck-export deckcraft`
(all three targets green 2026-07-25; PPTX is Chrome-backed).

## Slides (10)

Cover · Act I — The last mile · Three people, one gap · Never rasterized ·
Act II — From primitives · Three swap points · Act III — The honest ledger ·
The moat moved · The blocker on the desk · The family's engine

The deck states both open items rather than hiding them: **`pymupdf` is AGPL-3.0 / Artifex
dual-licensed** against the project's founding MIT-or-Apache-2.0-only bar (a human call,
blocking Story 3.2), and the **moat moved** — `ppt-master` (MIT, 41,032 stars) now matches
the editability bar, so the air-gap posture carries the differentiation.

## Design project (the bridge's far end)

Prototype lives in Claude Design project **"Deckcraft deck"** (`59c42e9c-7c90-431d-adae-b0021dd3f727`),
bound to the **Modernist** design system (`fbc1d6c8-b35f-4df6-9044-a64d2675427b`):
https://claude.ai/design/p/59c42e9c-7c90-431d-adae-b0021dd3f727?file=Deckcraft.dc.html
Pull it with the MCP bridge ("pull deckcraft") — see
`docs/specs/presentation-deck.md` § *The MCP bridge*.

Seeded 2026-07-25 (every upload byte-verified against the local file):

| Design path | Source | Bytes |
|---|---|---|
| `support.js` | `create_support_js` (server-provided runtime) | 66404 |
| `deck-stage.js` | `copy_files` from the steward project (`573d6554-…`) | 133230 |
| `reference/Warden Infographic standalone.html` | `copy_files` from steward — the designated-best infographic exemplar | 411764 |
| `Deckcraft.dc.html` | `project/Deckcraft.dc.html` | 30545 |
| `Deckcraft - Executive Summary.dc.html` | `project/Deckcraft - Executive Summary.dc.html` | 7623 |
| `src/marp/deckcraft-deck-2026-07-25.md` | same path locally | 6055 |
| `src/marp/deckcraft-executive-summary-2026-07-25.md` | same path locally | 3540 |
| `src/marp/deckcraft-infographic-2026-07-25.md` | same path locally | 3309 |

**seeded 2026-07-25 via DesignSync (byte-exact localPath upload).dc.html`, `Infographic standalone.html`,
`- Infographic Deck.dc.html`). The `DesignSync` tool was not exposed in the authoring session
and MCP `write_files` accepts inline `data` only, so these three await a DesignSync pass
(`finalize_plan` with `localDir`, then `write_files` with `localPath`).
