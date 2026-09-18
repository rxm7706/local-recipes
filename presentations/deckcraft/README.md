# Deckcraft deck (`deckcraft`)

**Status: authored 2026-07-25 — 10 slides, extract + build green.** Wave C poster rebuild
2026-09-15 (Story 21.8) was corrupted (96% boilerplate-repeat from byte offset 6235) and briefly
pushed to Design; **fixed 2026-09-17** (§ Ledger below) — the standalone poster was rewritten for
real from the archived `spec-deckcraft` planning chain, verified, and pushed corrective content to
Design, read back byte-identical. Story 21.8 is `done`. Engine + glue copied
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
Prototype lives in Claude Design project **"Deckcraft deck"** (`59c42e9c-7c90-431d-adae-b0021dd3f727`):
https://claude.ai/design/p/59c42e9c-7c90-431d-adae-b0021dd3f727?file=Deckcraft.dc.html

### Provenance

Bound to the **Modernist** design system (`fbc1d6c8-b35f-4df6-9044-a64d2675427b`). Pull it with
the MCP bridge ("pull deckcraft") — see `docs/specs/presentation-deck.md` § *The MCP bridge*.

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

## BLOCKED — 2026-09-17 (superseded below): the pushed content was corrupted

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
`presenton-pixi-image` posters from the same commit (Stories 21.6/21.7/21.9) — unaffected by
the fix below, each needs its own content pass.

## Fixed — 2026-09-17: real content, verified, pushed and read back clean

Everything from byte offset 6235 to EOF (the corrupted ~96%) was rewritten for real — 41 numbered
sections across the canonical 6 act bands (floor 18), 4 inline SVG diagrams (floor 3: pipeline
topology, document-journey flow, hardware-tier ladder, now/next/later roadmap), 25 tables
(floor 3), 93,813 bytes (floor 90,000). Content is sourced from the archived `spec-deckcraft`
planning chain (`archive/_bmad-output/projects/pyforge-herald/planning-artifacts/{specs/spec-deckcraft/SPEC.md,
epics-deckcraft.md, architecture/architecture-deckcraft-2026-05-10/architecture.md,
briefs/product-brief-deckcraft{,-distillate}.md, prds/prd-deckcraft-2026-05-10/*, research/*.md}`)
— that project's own planning is complete (brief → distillate → PRD, validated → architecture →
epics, 6 epics / 28 stories → readiness `READY_WITH_CAVEATS` → sprint plan) but **zero
implementation exists**: no `apps/deckcraft/`, Spike-0 (the gate benchmark) never run. The poster
says so plainly rather than implying the pipeline ships today. Numbers with no `facts.yaml` row
(the 28-story/6-epic/52-FR/23-NFR/15-AD/10-pattern/9-CAP counts, all from the archived planning
docs, not the live ledger) are stated as plain prose, never `data-fact`-marked — matching the
convention the untouched intro paragraphs already established for the pymupdf item.

Verified honestly, not just mechanically: `deck-facts deckcraft --check` → 0 unmarked, 0
mismatch (12 `drifted` — expected, the ledger's 2026-09-15 snapshot vs. today's live fleet
counts; `facts.yaml` was used as-is, untouched, per this story's own boundary). The full file
was read back and eyeballed section by section — real, varied, six-act prose, not a repeated
sentence (the check that failed last time). Rendered headless at 1240px (Playwright,
`scrollHeight` 20,453px); every `section`/`act`/`table`/`svg` element has a non-zero bounding
box; PNG crops of the header, an SVG diagram, a mid-document table run, and the closing Creed
band were visually inspected.

Pushed via `pyforge.herald.transport.mcp_transport.McpTransport` directly (`herald deck push`'s
CLI verb only covers the CAP-5 marp export, not this file). Read the live file first: still the
corrupted content (etag `1789639747822045`, 145,025 B, SHA-256 `5cb3f51d…`, matching the
corrupted-content hash already on record above). `finalize_plan` + `write_files` with `if_match`
on that etag → new etag `1789645287157037`. Read back in full (93,813 B, under the 256 KiB cap,
not truncated) and SHA-256-compared: **byte-identical to the local file**
(`97e9b48538d69a44dac049a440876e7fbe7dc4c51d57132a533b6b65f321ebe9`). Explicitly re-checked the
read-back body for the corruption pattern: `"factory already runs a tracked fleet"` occurs **0**
times (was 72) — the corrupted Design copy is gone. Story 21.8 is `done` — see
`_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-21-8-deckcraft-rebuilt-to-the-standard.md`.

| Artifact | Measured | Design etag | Notes |
|---|---|---|---|
| `Deckcraft Infographic standalone.html` | 93,813 B · 41 sections · 6 acts · 4 SVG · 25 tables · facts 0 unmarked/0 mismatch | `1789645287157037` | rendered 2026-09-17, page 20453 px at 1240 px; corrective push, read back byte-identical, corruption confirmed gone |
