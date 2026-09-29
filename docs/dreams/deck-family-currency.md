---
title: The deck family stays current — infographics re-derived from the ledgers, not
  remembered
type: dream
owner: herald
status: archived
archived-reason: absorbed
---
> **Consolidated into [[pyforge-herald]]** on 2026-09-17 (one-chain-per-station herald fold; folded from `deck-family-currency`).
# The deck family stays current — infographics re-derived from the ledgers, not remembered

## The Dream

Herald's infographics are the ecosystem's explainer surface and the input corpus for video
production. Today each one is frozen at the day it was authored: the Marshal poster still quotes
the tooling versions and fleet counts of 2026-07-31, and eleven of the fourteen posters never grew
past the six-section stub they were seeded as. The Dream is that every
`presentations/<slug>/project/<Name> Infographic standalone.html` reads as **true on the day you
open it** — its counts, versions, statuses and dates derived from the same ledgers the console
reads, its structure held to one codified standard (six-act arc, full-depth section set, inline
diagrams), and the whole family re-derivable on trigger the way code is re-built. Design stays the
visual editing surface; git stays the archive of record; **facts come from the ledger, never from
memory.**

> An infographic that quotes last month's ledger is a claim the estate can no longer stand behind.

## Why now — measured, not feared

| Finding | Where it is visible |
|---|---|
| Fourteen of fifteen deck folders carry a standalone poster; **eleven are July stubs** — 14–48 KB, zero inline SVGs, zero act bands | `presentations/*/project/*Infographic standalone.html`; `git log -1` per file: 2026-07-24/25 |
| Only three are at exemplar depth — warden 412 KB / 18 sections / 15 SVGs / no acts; marshal 91 KB / 19 / 3 / six acts; unifying-strategy 129 KB / 21 / 9 / six acts | same files, measured by `<section` / `<svg` / `ACT I..VI` counts |
| **The deep ones are stale too.** Marshal quotes `bmad-method 6.10.0`, `bmad-loop 0.9.0`, "128/333 fleet-wide", "Herald 4/27", "Mason 4/48", "Doctor 5/18", "Scribe 2/13", "Steward 3/26" | `presentations/pyforge-marshal/project/*.html`; live: BMAD core 6.12.0 (`_bmad/_config/manifest.yaml`); ledgers marshal 248/249, herald 67/68, mason 66/66, doctor 95/95, scribe 20/20, steward 206/222, atlas 94/95, warden 49/49; fleet 846/865 stories, 183/188 epics (`fleet-picture`) |
| Main has moved **4,414 commits** since the family-wide sync of 2026-07-24/25 | `git rev-list --count --since=2026-07-24 main` |
| The Design side holds nothing newer to pull: Unity Data Stack's Infographic head and standalone are the 2026-07-25 six-section stub, body-identical to disk; the Warden project's file set is unchanged since July | DesignSync `list_files` / `get_file`, 2026-09-13, projects `0494e2b0` and `100ca8cc` |
| `herald deck status` reports **all fifteen decks `linked: false`** — no `.herald/bridge-state.json` exists, and every README `## Design project` section predates the canonical two-line shape (DW-1-5-1) | `pixi run -e pyforge-herald herald deck status --repo-root .` |
| `pyforge-unifying-strategy` has **no Design project** — authored repo-side 2026-08-26, never seeded | its README carries no project id; no `design/p/` link anywhere in the tree |
| No fact in any poster cites its source, and nothing detects poster staleness: the chain-currency sweep covers planning spines, and the exemplar program names the deck/infographic family as a *purely manual* exemplar | [[chain-currency-sweep]]; [[fleet-hygiene-verification-exemplar-program]] § "narrower, purely-manual exemplars" |

## What it looks like when real

- **One standard, written once.** `docs/specs/presentation-deck.md` carries the infographic
  standard as a checklist: the six-act arc with full-bleed act bands, the full-depth section set
  (problem · pipeline · cast · journey · flows · autonomy · phase×persona table · relay · shipped
  product · doctrine · stack · which-tool-when · escalation · per-leader value · enterprise ·
  seams · proof · seed · roadmap · creed, adapted per subject), at least three inline SVG diagrams,
  the 90 KB+ class, and a source line for every number. **Unifying Strategy is the structure,
  acts and length reference; Warden is the density and visual-form reference.**
- **A fact ledger per deck.** `presentations/<slug>/facts.yaml` lists every count, version,
  status and date the poster shows, each with the command or file it was derived from, its value,
  and the date derived. A derivation step re-emits it from live sources (`fleet-picture`, the
  tracked `sprint-status-ledger.yaml` files, each station's `pyproject.toml`, the BMAD manifest,
  `SPEC.md` capability tables, `bmad-groundtruth`); the deck README ledger summarizes it; a check
  reds when a rendered fact disagrees with its ledger row.
- **Every PyForge-branded poster rebuilt to the standard from its ledger** — the eight station
  decks, genesis and unifying-strategy — authored repo-side, pushed byte-exact to the deck's
  Design project with the DesignSync local-path pipeline, README sync ledger updated with the
  returned etags, and pulled back to prove the round trip.
- **The rendered page is looked at.** A headless full-page PNG of each standalone sits beside the
  report — the render gate proves it RUNS, the PNG proves it LOOKS right.
- **The bridge sees the family.** `herald deck status` reports every seeded deck linked, and
  unifying-strategy has a Design project bound to Modernist.
- **Later slices, named now.** The trio head, Infographic Deck and Executive Summary are
  re-derived from the same ledger so the family is back in lockstep; the four chain decks (unity,
  wasm, deckcraft, presenton) follow in their own wave; Design-side visual polish is its own act,
  always closed by a byte-exact pull.

## Constraints / Non-goals

- **Derive, never declare.** A number, version, status or date without a `facts.yaml` row does not
  ship. Story counts come from the tracked ledgers, versions from `pyproject.toml` and the BMAD
  manifest, capability counts from `SPEC.md`, fleet totals from `fleet-picture` — never from a
  prior poster or from memory.
- **Never restrict size at authoring time.** Lay everything out; cutting is a later, visual act.
- **Repo-side first.** This slice authors in the repo and pushes; no Design-chat authoring and
  no visual polish in Design. When polish happens later it ends with a byte-exact pull, per the
  deck spec's standing rule.
- **The standalone leads this slice — a dated, deliberate exception to trio lockstep.** The deck
  spec says the trio moves together; the operator chose the standalone first (2026-09-13). Each
  README ledger marks the head and Infographic Deck "standalone ahead" until the lockstep slice
  re-derives them.
- **Scope of this slice is the ten PyForge-branded decks.** The chain decks and `agentic-sdlc`
  (BMAD-branded, no standalone in `project/`) are out of this slice by decision, not omission.
- **Advisory, not a second gate.** The facts check reports; it does not become a PR verdict
  unless a later Spec promotes it.
- **One PR per deck; four worktree agents per wave; physical paths, never `bmad-switch` inside a
  parallel agent.** Non-recipe PRs carry the `maintenance` label.
- **Marp-derived renders stay derived.** `src/marp/*-infographic-standalone-*.html` remain
  `deck-export` outputs; this Dream does not redefine them.

## Kinships

[[pyforge-herald]] (the station — the bridge CLI, the deck family, the standard's home) ·
[[deck-visual-qa]] (the render-to-PNG discipline this extends to the standalone poster) ·
[[chain-currency-sweep]] (the same detector-plus-reconciler pattern, applied to presentation
surfaces instead of planning spines) · [[fleet-hygiene-verification-exemplar-program]] (names the
deck/infographic family as a purely manual exemplar — this is its graduation path) ·
[[pyforge-unifying-strategy]] (the structure, acts and length reference) · [[pyforge-warden]] (the
density and visual-form reference) · [[pyforge-charter]] (the Genesis deck this refreshes) ·
[[pptx-deck-generation]] (the export set the same ledger feeds in a later slice).

## Realization log

- **2026-09-13** — Seeded (operator direction: the Design-side infographics are outdated; every
  line is to be verified; plan first). Every row of § *Why now* was measured this date. Decisions
  of record from the operator, same date: (1) the ten PyForge-branded decks first, the four chain
  decks later; (2) a structure/acts/length reference plus Warden as the density/visual reference;
  (3) the standalone poster first, family lockstep as follow-up; (4) repo-side authoring from the
  fact ledger with a DesignSync push, no Design polish this session; (5) a tracked `facts.yaml`
  per deck summarized in the README ledger; (6) create the unifying-strategy Design project in its
  wave; (7) four worktree agents per wave, one PR per deck. **Reference ruling, confirmed by the operator the same date:** the operator had first named
  Unity Data Stack as the structure reference; verified this date that Unity's Design-side head
  and standalone are the 2026-07-25 six-section stub with no act bands, so the family's only
  six-act, exemplar-depth posters are Unifying Strategy and Marshal — the operator confirmed
  **Unifying Strategy as the structure, acts and length reference** and **Warden as the density
  and visual-form reference**. Next act: `bmad-spec` derives the Spec under `pyforge-herald`.
- **2026-09-13** — Specified. `bmad-spec` (headless, express) derived
  `spec-deck-family-currency` under `pyforge-herald`: CAP-1 the standard, CAP-2 the fact ledger,
  CAP-3 the rebuild, CAP-4 the mirror proof, CAP-5 the staleness check; companions
  `infographic-standard.md`, `facts-ledger.md`, `deck-inventory.md`; `status: ready`,
  `open_questions: []`, two assumptions (the claude-design MCP is reconnected before Wave B and
  before any >256 KiB read-back; Warden's Design-side standalone is unchanged since 2026-07-24).
  Dream `dreamt → specified` per README § status. Next act: Epic 20 and its ledger rows in
  `pyforge-herald`, then Story 20.1/20.2 before any file outside `docs/dreams/` or the Spec
  folder changes.
- **2026-09-13 (later the same day)** — Wave A landed. Story 20.2 shipped `deck-facts`
  (PR #1295; four-layer review, 45 findings, 32 patched); the eight station posters were rebuilt
  to the standard from their ledgers by worktree agents, reviewed against the floors, the facts
  check and a full-page render, pushed to their Design projects, merged (PRs #1297, #1298,
  #1300, #1301, #1303–#1306) and read back byte-identical once the claude-design MCP
  reconnected (etags in each README ledger). Two facts the wave corrected: the 411,764 B Warden
  "reference" was a Design bundle (192,472 B of content; the rebuild is 295,079 B), and
  `recipes_count` had read the working tree (now `git ls-files`). One capability the wave
  minted: **CAP-6, mechanical refresh** — the moment round 1 merged, the posters read `mismatch`
  on the fleet counts their own landings moved; CAP-5 detected it and nothing could repair it
  without hand edits, so `deck-facts --refresh` (Story 20.14) rewrites stale marked literals from
  the ledger. The Unifying Strategy Design project now exists (`1e4020bc`, seeded with the
  family). Wave B (20.11 genesis, 20.12 the Canopy) in flight; 20.13 and the closeout follow.
- **2026-09-13 (closeout)** — **Realized.** Epic 20 closed 14/14 in twelve PRs. The standard has one
  home and floors that can be checked; every PyForge poster meets them (112,847–295,083 B, six acts
  each, 21–33 sections, 4–26 inline diagrams); 833 facts across the ten carry a `data-fact` mark over
  a tracked `facts.yaml` row and every deck reports `0 unmarked, 0 mismatch, 0 drifted, 0 unsourced`;
  each poster was pushed to its Design project and **read back byte-identical, 10 of 10**; and
  `herald deck status` reports the ten linked where it reported none this morning. The decay this
  Dream named turned out to be faster than expected — a poster goes stale on its own merge — so CAP-6
  was minted mid-epic and its first sweep refreshed 96 stale literals across nine posters in one
  pass. Deliberately left: the trio lockstep, the four chain decks, and Design-side polish. Retro:
  `_bmad-output/projects/pyforge-herald/planning-artifacts/retros/retro-epic-20-2026-09-13.md`.
