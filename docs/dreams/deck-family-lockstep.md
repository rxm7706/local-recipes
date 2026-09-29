---
title: The whole deck family moves together — every surface, every deck, one ledger
type: dream
owner: herald
status: archived
archived-reason: absorbed
---
> **Consolidated into [[pyforge-herald]]** on 2026-09-17 (one-chain-per-station herald fold; folded from `deck-family-lockstep`).
# The whole deck family moves together — every surface, every deck, one ledger

## The Dream

Epic 20 made one surface true. Ten PyForge posters read as of the day you open them, every number
traceable to a tracked row, the Design mirror byte-exact. But a deck is not one file. Beside each
rebuilt poster sits an **Infographic head**, an **Infographic Deck**, an **Executive Summary**, a
marp source and two PowerPoint exports — and all of them still carry July's facts. Four more decks
in `presentations/` never entered the wave at all. And nothing has yet been through the visual
editing surface the whole bridge exists to reach.

The Dream is that **the family moves as one**: every artifact of every deck derives from the same
`facts.yaml`, so a ledger that moves moves all of them; every deck in `presentations/` meets the
standard, not just the ten; and the Design side is a place the family is *improved*, not merely
mirrored — with git still the archive of record.

> A deck whose poster is current and whose slides are three months stale is not a current deck.

## Why now — measured, not feared

| Finding | Where it is visible |
|---|---|
| Every deck README says its head and Infographic Deck are **"standalone ahead"** — ten decks, three surfaces each, all still at their July content | the `## Ledger — 2026-09-13` section of each `presentations/pyforge-*/README.md` |
| The heads are 14–48 KB against posters of 112–295 KB; the Infographic Decks likewise | `presentations/pyforge-*/project/*- Infographic.dc.html` vs the standalone beside it |
| The marp sources and both PPTX per deck are dated 2026-07/08 and were never re-derived | `presentations/pyforge-*/src/marp/`, `src/pptx/` |
| Four decks never entered the wave: unity-data-stack, wasm-analytics-stack, deckcraft, presenton-pixi-image — 15–19 KB stubs, no act bands, no `facts.yaml` | `presentations/{unity-data-stack,wasm-analytics-stack,deckcraft,presenton-pixi-image}/project/` |
| Those four report `linked: false` and their `## Design project` sections are malformed for `registry.read` | `herald deck status --repo-root .` — 10 of 15 linked |
| No deck has been through a Design-side visual pass since the rebuild; the bridge's editing half is unexercised on current content | `spec-deck-family-currency` § Non-goals, and every README ledger's "Design etag" row |
| The mechanical path already exists and is unused for this: the standalone **is** the head's body, minus the `x-dc` wrapper, with styles moved into `<head>` | `docs/specs/presentation-deck.md` § *Artifact dependency tree*; the trio's own definition |

## What it looks like when real

- **The trio derives, it is not re-authored.** A verb turns a current standalone into its
  Infographic head and Infographic Deck mechanically — the body is already identical by definition —
  so "standalone ahead" stops being a state a README can be in.
- **The exec summary and the exports follow the same ledger.** The one-page summary and the marp
  sources carry marked facts too, and `deck-export` regenerates the PPTX from them, so the Standard
  export set is current in every format at once.
- **Fourteen decks, not ten.** The four chain decks are rebuilt to the standard from their own fact
  ledgers, registered, and linked; `herald deck status` reports the whole of `presentations/`.
- **The Design side is used as a design surface.** At least one deck goes through a real visual pass
  in Claude Design and comes back through a byte-exact pull, proving the loop the bridge was built
  for — and the pull discipline holds: git stays the archive of record.
- **One sweep covers everything.** `deck-facts <slug> --refresh` walks every marked surface of a
  deck, not just its poster, and the standing sweep keeps fourteen decks current in one pass.

## Constraints / Non-goals

- **Derive, never re-author.** The head and Infographic Deck come from the standalone by transform;
  a hand-written divergence between them is the defect this Dream removes. The same rule that
  governs facts governs structure.
- **The marked-fact contract is unchanged.** Every number on every surface is a `data-fact` mark
  over a tracked `facts.yaml` row; the three hazards `--refresh` cannot cover (hand-counted prose,
  swept SVG labels, `inline-flex` fusing a token) stay in force.
- **Never restrict size at authoring time**; the floors in `infographic-standard.md` are a floor.
- **Design polish ends with a pull.** No visual act is complete until git holds the bytes.
- **Not a new engine.** The React deck, `deck_export.py`'s semantics and the `.pptx` pipeline are
  untouched; this Dream re-derives content, it does not rebuild machinery.
- **Not a second gate.** The checks stay advisory.
- **One PR per deck, worktrees, physical paths** — the parallel-agent discipline Epic 20 proved.

## Kinships

[[deck-family-currency]] (the realized parent — the standard, the fact ledger, CAP-6; this Dream
finishes the surfaces it deferred) · [[pyforge-herald]] (the station; the bridge and the deck family)
· [[deck-visual-qa]] (the render gate every rebuilt surface passes) · [[pptx-deck-generation]] and
[[pptx-custom-shapes]] (the export half the exec summary and marp sources feed) ·
[[chain-currency-sweep]] (the same detector-plus-reconciler shape, one tier up).

## Realization log

- **2026-09-13** — Seeded at Epic 20's closeout, from the three slices that epic deferred by operator
  ruling (trio lockstep, the four chain decks, Design-side polish). Every row of § *Why now* was
  measured on `main` that day, after all fourteen Epic 20 stories landed. Next act: `bmad-spec`
  derives the Spec under `pyforge-herald`.
- **2026-09-13 (same day)** — Specified. `spec-deck-family-lockstep` is `ready` with
  `open_questions: []` — the parent Spec and Epic 20's retro settled every decision this one would
  otherwise have had to ask, so it mints only CAP-1..5 and binds the rest. Epic 21 carries eleven
  stories with Given/When/Then and named surfaces, and eleven `backlog` rows sit in the tracked
  sprint ledger. Nothing else is owed before dispatch: the standard, the fact ledger, the refresh
  verb and the registry all shipped with Epic 20. Next act: drain Epic 21, starting with 21.1 —
  21.2 through 21.5 depend on it.
- **2026-09-16** — Dream-append: dispatching Story 21.4 (`bmad-build-auto`) surfaced a real,
  independently-reproduced blocker on the push+read-back leg — `herald deck push` raises
  `ImportError: cannot import name 'streamablehttp_client' from 'mcp.client.streamable_http'` on
  `main`, before any credential or network check. `mcp` 2.2.0 (what `pyforge-herald`'s pixi
  environment actually resolves) renamed the symbol to `streamable_http_client`;
  `pyforge.herald.transport.mcp_transport` (Story 1.2, 2026-08-07) never updated. Confined to
  herald's own transport — atlas's parallel `mcp` 2.x usage doesn't touch this symbol. A second
  claim from the same dispatch (missing Design credential) was re-checked directly and found stale
  — `resolve_design_credential()` succeeds live once `/design-login` had completed; not a standing
  gap. Minted `spec-deck-family-lockstep` CAP-6 for this (binds here rather than a new Dream/Spec
  file — governance ruling `spec-one-chain-per-station`, `chain-sprawl-check` enforces it live).
  Blocks 21.4, 21.6–21.9's push leg, and all of `spec-design-sync-loop`'s Epic 23. Next act: mint
  Story 21.12 in `epics.md` citing CAP-6, then implement via `bmad-build` (quick-dev — a single,
  low-external-blast-radius fix).
- **2026-09-16 (same day)** — Story 21.12 landed. The fix was two distinct `mcp` 2.2.0 symbol
  renames, not one — the second (`CallToolResult.isError` → `is_error`) only surfaced on a
  completed live call, after the first was fixed, which is exactly why the story's own AC
  insisted on a live push+read-back proof rather than an import-level check. Live-proved: `herald
  deck push pyforge-warden` succeeded for real against Design; `deck-facts pyforge-warden --check`
  reported 0 `mismatch` afterward. Found along the way, NOT fixed (orthogonal, deferred on the
  story spec): `herald deck pull` hits two separate pre-existing bugs on large/oddly-named decks
  (a 256 KiB `read_file` cap, and a `prototype_filename`-guessing mismatch) — both reach the fixed
  transport successfully before failing on unrelated causes. `pyforge-herald-test`: 1262 passed, 4
  skipped. Next act: Story 21.4 (the ten-deck sweep) and 21.6–21.9's push legs are now unblocked
  for real dispatch.
