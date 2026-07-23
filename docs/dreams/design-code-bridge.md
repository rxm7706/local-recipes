---
title: The Design↔Code Bridge
type: dream
status: realized
---

# The Design↔Code Bridge — one continuous surface from vision to shipped deck

## The Dream

**Claude Design and Claude Code stop being two worlds.** Today the visual layer
(claude.ai/design, where decks and prototypes are authored) and the code layer
(this repo, where they are extracted, built, and shipped) are joined by hand: the
designer manually mirrors repo files into a Design project, works there, downloads
the export, and copies it back. The evidence of the pain is a whole Design project
— *"Local recipes repository connection"* — that exists only to hold a stale
hand-mirrored copy of `presentations/pyforge-atlas/`.

The Dream: **the prototype round-trips itself.** A persona deck starts as a seeded
Design project; a human refines it visually in Claude Design; a single ask in
Claude Code pulls the prototype straight into `presentations/<slug>/project/`,
extracts, builds, and ships the § Standard export set — zero downloads, zero
copy-paste, conflicts caught by etags instead of overwrites.

This is **Herald's** capability (see [[ecosystem-crew]] — the Proclaimer owns the
Dream→Deck rendering *and* cross-surface integration): the bridge is Herald's
first shipped organ.

## What it looks like when real

- **Push (seed):** Claude Code creates a Design project per deck, bound to the
  **Modernist** design system, pre-seeded with a contract-compliant starter
  prototype (`<section data-label data-speaker-notes style="background:#hex">` at
  1920×1080, Archivo, the family palette) whose content is distilled from the
  founding Dream and the real systems.
- **Design (human):** the user iterates visually at claude.ai/design — their
  preferred surface, no repo mechanics.
- **Pull (ship):** "pull marshal" in any Claude Code session → `read_file` the
  prototype into `project/` → `npm run extract` → `npm run build` →
  `pixi run deck-export` → commit. The deck and its six export artifacts ship
  without a single manual transfer.
- **Discipline:** etags on every read/write so a mid-edit conflict surfaces
  instead of silently clobbering either side; only the **prototype** crosses the
  bridge (never a mirrored app tree).

## Beyond the pilot (the fuller dream)

- A `herald` CLI that wraps the loop (`herald deck seed <slug>`,
  `herald deck pull <slug>`), watch-mode sync, and stale-mirror detection —
  **specced 2026-07-23** as `SPEC-design-code-bridge` (CAP-1..4), incl.
  **Marp-source pull in v1** (authored in Design, pulled to `src/marp/`;
  seeding + derived artifacts stay out).
- Retiring hand-mirror projects entirely (the CLI detects; humans retire).

## Realization log

- **2026-07-23 — pilot, both directions proven (core realized):**
  - **Push:** Design project *"PyForge Marshal deck"* created, bound to
    Modernist; `support.js` server-written, `deck-stage.js` copied server-side
    from the atlas Design project, and a 10-slide contract-compliant starter
    `PyForge Marshal.dc.html` seeded via `write_files` — the exact bytes that
    first passed `extract` (10/10 slides) + `build` locally.
  - **Pull:** "pull marshal" → `read_file` with `if_none_match` returned
    `{unchanged: true}` — identity verified with zero bytes transferred; a
    changed etag would have landed the new prototype and re-run
    extract → build → deck-export.
  - **Documented** for agents in `AGENTS.md` (§ Claude Design ↔ repo bridge),
    `CLAUDE.md`, and `docs/specs/presentation-deck.md` (§ The MCP bridge —
    canonical; manual export demoted to fallback).
  - The fuller herald-CLI automation (`herald deck seed/pull`, watch mode)
    remains future work.
- **2026-07-23 — first Dream-first `bmad-spec` run (Genesis step 2 dogfood):**
  this Dream was distilled into the herald CLI contract —
  **`SPEC-design-code-bridge`** (4 capabilities: seed / pull / status+stale-mirror
  / watch; + `bridge-protocol.md` carrying the proven tool loop) — under BMAD
  project **`pyforge-herald`**, landing in
  `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-design-code-bridge/`
  per the Dream-first tier model. No legacy `docs/specs/` file was created.
  Self-validate: coherence PASS, preservation PASS.
- **2026-07-23 — all 3 open questions resolved** (user-approved recommendations):
  transport = dual-path (pure MCP client, spike-proven, with a headless
  Claude-Code/Agent-SDK fallback) under a new **deterministic — no LLM in the
  loop** constraint; watch = 60 s etag poll + quiescence debounce + idle backoff;
  **Marp-source pull joins v1** (CAP-2). Spec re-derived; zero open questions
  remain — ready for `bmad-create-epics-and-stories`.
- **2026-07-23 — export decisions revisited** (user-directed): the bridge becomes
  **two-way for exports** — **CAP-5** pushes the regenerated derived set back into
  each Design project; the standalone HTML is preferentially the **Design-authored
  bundle** (pulled, superseding marp renders); editable PPTX generation is
  **deckcraft's** job (herald transports, never generates). Crossing rule is now
  directional: authored sources inbound, seeds + derived exports outbound.
