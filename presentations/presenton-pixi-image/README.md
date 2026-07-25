# Presenton, Conda-Native deck (`presenton-pixi-image`)

**Status: authored 2026-07-25 — 10 slides, extract + build green.** Engine + glue copied
**verbatim** from `presentations/pyforge-steward/` (Archivo / Modernist system). Dream:
`docs/dreams/presenton-pixi-image.md`; the Spec and its planning chain live in
`_bmad-output/projects/presenton-pixi-image/planning-artifacts/`.

`presenton-pixi-image` repackages the open-source Presenton AI deck generator as a signed,
fully air-gapped, conda-forge-native OCI image for Red Hat OpenShift — zero LibreOffice,
zero external CDN, no call home. It is **deckcraft's complement**, not its competitor: this
is the repackaged *app*; deckcraft is the from-primitives *pipeline*. Mason repackages;
Steward deploys and operates the OpenShift service.

Display title is **"Presenton, Conda-Native"**; file/dir names drop the comma
(`Presenton Conda-Native.dc.html`) and the repo slug is `presenton-pixi-image`.

Workflow: `docs/specs/presentation-deck.md` (prototype contract, § Standard export set,
§ The MCP bridge). `npm install && npm run extract && npm run dev`.
Engine files stay byte-identical across every deck.

## Artifact map (the § Standard 6-artifact family)

| Artifact | Path |
|---|---|
| Deck prototype (source of truth) | `project/Presenton Conda-Native.dc.html` — 10 sections at 1920×1080 |
| Executive summary | `project/Presenton Conda-Native - Executive Summary.dc.html` |
| Infographic (trio head — edit here) | `project/Presenton Conda-Native - Infographic.dc.html` (1240×2560 one-pager) |
| Infographic standalone | `project/Presenton Conda-Native Infographic standalone.html` (same body, no `x-dc`, styles in `<head>`) |
| Infographic Deck | `project/Presenton Conda-Native - Infographic Deck.dc.html` (8 slides — same sections at 1920×1080) |
| Marp sources | `src/marp/presenton-pixi-image-{deck,executive-summary,infographic}-2026-07-25.md` |
| Derived exports | `src/marp/presenton-pixi-image-infographic-standalone-2026-07-25.html`, `src/pptx/presenton-pixi-image-deck-2026-07-25.pptx`, `src/pptx/presenton-pixi-image_infographic_deck-2026-07-25.pptx` |

Regenerate the derived set with `pixi run -e local-recipes deck-export presenton-pixi-image`
(all three targets green 2026-07-25; PPTX is Chrome-backed).

## Slides (10)

Cover · Act I — 11pm in a SCIF · Two gates that don't collapse · The supply-chain math ·
Act II — Two planes · One true port · Act III — Phase 0 gates the build ·
Exit 6a — the Redmond contingency · Exit 6b — the memory-subsystem call · The complement

The deck names both open **Phase-0** calls rather than hiding them: **6(a)** — Microsoft's
disconnected stack (Azure Local disconnected operations + Microsoft 365 Local + Foundry
Local) went GA worldwide 2026-02-24 and whether it carries a deck-generation application
layer is unconfirmed (Risk R3, existential; the standing watch missed the announcement);
and **6(b)** — `mem0ai` + `fastembed-vectorstore` are unconditional Presenton dependencies
with no conda-forge presence, making the v1 recipe count 5-or-7, not a fixed six.

## Design project (the bridge's far end)

Prototype lives in Claude Design project **"Presenton, Conda-Native deck"**
(`c824a332-8e43-4b17-bf84-f38307085289`), bound to the **Modernist** design system
(`fbc1d6c8-b35f-4df6-9044-a64d2675427b`):
https://claude.ai/design/p/c824a332-8e43-4b17-bf84-f38307085289?file=Presenton+Conda-Native.dc.html
Pull it with the MCP bridge ("pull presenton") — see
`docs/specs/presentation-deck.md` § *The MCP bridge*.

Seeded 2026-07-25 (every upload byte-verified against the local file):

| Design path | Source | Bytes |
|---|---|---|
| `support.js` | `create_support_js` (server-provided runtime) | 66404 |
| `deck-stage.js` | `copy_files` from the steward project (`573d6554-…`) | 133230 |
| `reference/Warden Infographic standalone.html` | `copy_files` from steward — the designated-best infographic exemplar | 411764 |
| `Presenton Conda-Native.dc.html` | `project/Presenton Conda-Native.dc.html` | 36612 |
| `Presenton Conda-Native - Executive Summary.dc.html` | same path locally | 7812 |
| `src/marp/presenton-pixi-image-deck-2026-07-25.md` | same path locally | 7517 |
| `src/marp/presenton-pixi-image-executive-summary-2026-07-25.md` | same path locally | 3802 |
| `src/marp/presenton-pixi-image-infographic-2026-07-25.md` | same path locally | 4104 |

**seeded 2026-07-25 via DesignSync (byte-exact localPath upload).dc.html`, `Infographic standalone.html`,
`- Infographic Deck.dc.html`). The `DesignSync` tool was not exposed in the authoring session
and MCP `write_files` accepts inline `data` only, so these three await a DesignSync pass
(`finalize_plan` with `localDir`, then `write_files` with `localPath`).
