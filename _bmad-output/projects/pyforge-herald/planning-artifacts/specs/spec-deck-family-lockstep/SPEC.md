---
id: SPEC-deck-family-lockstep
spec: deck-family-lockstep
status: ready
owner-dream: docs/dreams/deck-family-lockstep.md
companions: []
surface:
  - presentations/pyforge-*/project/*.dc.html
  - presentations/pyforge-*/src/marp/**
  - presentations/pyforge-*/src/pptx/**
  - presentations/{unity-data-stack,wasm-analytics-stack,deckcraft,presenton-pixi-image}/**
  - scripts/deck_facts.py
  - scripts/deck_trio.py
sources:
  - ../../../../../../docs/dreams/deck-family-lockstep.md
open_questions: []
---

> **Canonical contract.** This SPEC is the complete contract for what to build, test and validate.
> `docs/dreams/deck-family-lockstep.md` is listed in `sources:` for narrative rationale.
>
> **Binds, never re-mints.** The standard is `spec-deck-family-currency` CAP-1 and its companion
> `infographic-standard.md`; the fact ledger is CAP-2 and `facts-ledger.md`; the staleness check and
> the mechanical refresh are CAP-5 and CAP-6. This Spec extends those to the surfaces and decks that
> Spec deferred, and mints nothing they already cover.

# The whole deck family moves together

## Why

A pain to solve. Epic 20 made one surface of ten decks true and left the rest visibly behind: every
deck README now says its Infographic head and Infographic Deck are "standalone ahead", the heads are
14–48 KB against posters of 112–295 KB, every marp source and both PPTX per deck are dated
2026-07/08, and four decks in `presentations/` never entered the wave at all — 15–19 KB stubs with no
fact ledger and registry sections too malformed to read, so `herald deck status` sees 10 of 15. The
bridge's editing half is also unexercised on current content: nothing rebuilt has been through a
Design-side visual pass. The fix is not more authoring. The head's body *is* the standalone's body by
definition, so the divergence is removable by transform rather than by discipline.

## Capabilities

- **CAP-1**
  - **intent:** The trio derives from the standalone — a verb turns a current standalone into its
    Infographic head (`.dc.html`, `x-dc` wrapper, styles in the helmet) and its Infographic Deck (the
    same sections re-laid as 1920×1080 slides), so the three can no longer disagree.
  - **success:** Run over a rebuilt deck, the head's body matches the standalone's exactly modulo the
    wrapper and style placement, the Infographic Deck carries one slide per numbered section, both
    render without error, and a second run changes nothing.
- **CAP-2**
  - **intent:** Every marked surface of a deck refreshes together — `deck-facts <slug> --refresh`
    walks the poster, head, Infographic Deck, exec summary and marp sources, so one ledger move
    updates all of them.
  - **success:** After a tracked ledger changes, one `--refresh` leaves every surface of that deck at
    0 `mismatch`, and `--check` reports per surface.
- **CAP-3**
  - **intent:** The Standard export set is current in every format — the exec summary and marp
    sources carry marked facts, and `deck-export` regenerates both PPTX from them.
  - **success:** For every deck the six companions are regenerated from current sources and dated the
    rebuild day; no README still reads "standalone ahead".
- **CAP-4**
  - **intent:** Fourteen decks, not ten — the four chain decks are rebuilt to the standard from their
    own fact ledgers, registered and linked.
  - **success:** `herald deck status` reports every deck in `presentations/` linked with its project
    id, and each of the four meets the `infographic-standard.md` floors at 0 unmarked / 0 mismatch.
- **CAP-5**
  - **intent:** The Design side is used as a design surface — at least one deck goes through a real
    visual pass in Claude Design and returns through a byte-exact pull.
  - **success:** A dated Design-side edit is pulled to git, the read-back is byte-identical after the
    harness strip, the deck README records the etag, and the pull discipline is demonstrated end to
    end.

## Constraints

- **Derive, never re-author.** A hand-written divergence between a standalone and its head is the
  defect this Spec removes; the rule that governs facts governs structure.
- **The marked-fact contract is unchanged**, and the three hazards `--refresh` cannot cover stay in
  force: hand-counted prose, swept SVG `<text>` labels, and `.tag{display:inline-flex}` fusing a
  marked token to its neighbour.
- **Never restrict size at authoring time**; `infographic-standard.md`'s floors are a floor.
- **One PR per deck**, worktrees and physical paths, never `bmad-switch` inside a parallel agent,
  `maintenance` label on every non-recipe PR.
- **Checks stay advisory** — never a second PR gate.
- **Machinery is untouched:** no new deck engine, no change to `deck_export.py`'s semantics, no
  change to the `.pptx` pipeline.
- **Design polish ends with a pull.** No visual act is complete until git holds the bytes.

## Non-goals

- Re-authoring any poster Epic 20 already landed.
- Design-side polish beyond the one proving pass CAP-5 names.
- A new deck engine, a second PR gate, or a change to `deck_export.py`'s semantics.
- The React decks' slide extraction and `dist/` builds.

## Success signal

Open any deck in `presentations/` and every surface tells the same, current story: the poster, the
head, the Infographic Deck, the exec summary and the exports all resolve to the same `facts.yaml`
derived that day; no README says "standalone ahead"; `herald deck status` reports all fourteen
linked; and at least one deck carries a Design-side visual improvement that came back to git
byte-exact.
