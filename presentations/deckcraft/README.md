# Deckcraft deck (`deckcraft`)

**Status: authored 2026-07-25 — 10 slides, extract + build green.** Wave C poster rebuild
2026-09-15 (Story 21.8) is **CORRUPTED** (§ Ledger — 2026-09-17 below) — 96% of the standalone
poster's body was mistakenly pushed to Design and read back byte-identical 2026-09-17 before
the corruption was discovered; Story 21.8 is `blocked` pending a content fix. Engine + glue copied
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

**Resolved 2026-09-17 (Story 21.8):** `Deckcraft - Infographic.dc.html` and
`Deckcraft - Infographic Deck.dc.html` were confirmed already byte-identical on Design (no
push needed — read back and SHA-256-compared, matched on the first read); only
`Deckcraft Infographic standalone.html` was still the July stub server-side and needed the
push below.

## Ledger — 2026-09-15 Wave C local rebuild (Story 21.8)

| Artifact | Measured | Design etag | Notes |
|---|---|---|---|
| `Deckcraft Infographic standalone.html` | 145025 B · 21 sections · 6 acts · 3 SVG · 3 tables · facts 53/53 | `1789639747822045` | rendered 2026-09-15, page 18763 px at 1240 px; 0 unmarked / 0 mismatch; no dream_status row |
| `facts.yaml` | 30 facts at tree `506ad58622` | — | Dream file missing; spec_status omitted; no package/CLI rows |

## Ledger — 2026-09-17 push + read-back (Story 21.8)

`pyforge-herald`'s `mcp` 2.2.0 transport symbol drift (Story 21.12) is fixed and merged, so
`resolve_design_credential()` succeeds this session. Compared every `project/` trio file
against Design via `pyforge.herald.transport.mcp_transport.McpTransport.read_file` (SHA-256,
whole-file reads, none truncated) before pushing anything, per the "check, don't assume"
rule:

| Artifact | Local SHA-256 (first 12) | Design state | Action |
|---|---|---|---|
| `Deckcraft.dc.html` | `2bddbdde2095` | matched | none — already synced |
| `Deckcraft - Executive Summary.dc.html` | `62948f2893d9` | matched | none — already synced |
| `Deckcraft - Infographic.dc.html` | `194bd5a03a08` | matched | none — already synced |
| `Deckcraft - Infographic Deck.dc.html` | `325ba760dd5e` | matched | none — already synced |
| `Deckcraft Infographic standalone.html` | `5cb3f51dbf33` | mismatch (15,774 B July stub) | pushed via `finalize_plan` → `write_files` (inline `data`), new etag `1789639747822045` |

Push target was under the 256 KiB `read_file` cap (145,025 B), so a single read-back call plus
SHA-256 comparison is the proof — no windowing needed. Read-back SHA-256
(`5cb3f51dbf33e8e499a0658626654130211ecf5f7cc3569a987b0dabcbcb62f0`) is identical to the
local file. `deck-facts deckcraft --check` still reads 0 unmarked / 0 mismatch afterward.
Design now matches disk for every `project/` trio file — **but see the correction below: disk
itself was corrupted, so this byte-faithful push mirrored the corruption to Design.**

## BLOCKED — 2026-09-17: the pushed content is corrupted (do not push further)

The push above was byte-faithful (SHA-256 confirms Design matches disk exactly) — the problem
is that disk was already wrong. `deck-facts --check`'s 0 unmarked / 0 mismatch result is **not**
a content-sanity check — it only validates `data-fact` span presence, and does not catch this.

Live inspection found `Deckcraft Infographic standalone.html` corrupted from byte offset 6235
to near EOF: a boilerplate paragraph ("The factory already runs a tracked fleet: stories 930 of
998 and epics 207 of 225. BMAD core 6.12.0, ...") repeats **72 times**, with **every character
space-separated** ("T h e   f a c t o r y ..."), replacing real section content across ~96% of
the file's span. Confirmed via direct byte-offset/regex inspection of both the local file and
the live Design copy (etag `1789639747822045`, the one pushed above) — the corruption is
present in both, byte-for-byte identical, which is expected since the push was byte-faithful.

`git blame` traces the corruption to commit `e483288d54f` ("Rebuild the four chain-deck posters
from their fact ledgers", 2026-09-15) — already on `main`, predating this session. The same
corruption independently affects the sibling `unity-data-stack`, `wasm-analytics-stack`, and
`presenton-pixi-image` posters from the same commit (Stories 21.6/21.7/21.9).

**No content fix attempted here** — restoring the poster's real prose is a content-authoring
task outside this ledger entry's own scope; a fresh push + read-back cycle is needed once a
fix lands. **No further push attempted.** The corrupted Design copy is left as-is pending an
operator decision on remediation (fix-and-repush, or revert Design to the prior July-stub
copy as an interim measure). Story 21.8 is `blocked`, not `done` — see
`_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-21-8-deckcraft-rebuilt-to-the-standard.md`.
