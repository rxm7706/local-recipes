---
id: SPEC-deck-family-currency
spec: deck-family-currency
status: ready
owner-dream: docs/dreams/deck-family-currency.md
companions:
  - infographic-standard.md
  - facts-ledger.md
  - deck-inventory.md
surface:
  - presentations/pyforge-*/project/* Infographic standalone.html
  - presentations/pyforge-*/facts.yaml
  - presentations/pyforge-*/README.md
  - presentations/README.md         # the family index — carries the standard's pointer line
  - scripts/deck_facts.py
  - pixi.toml                       # the deck-facts task only
  - docs/specs/presentation-deck.md # legacy tier (allowlisted); carries the pointer to infographic-standard.md
sources:
  - ../../../../../../docs/dreams/deck-family-currency.md
open_questions: []
---

> **Canonical contract.** This SPEC, `infographic-standard.md`, `facts-ledger.md` and
> `deck-inventory.md` are the complete, preservation-validated contract for what to build, test,
> and validate. `docs/dreams/deck-family-currency.md` is listed in `sources:` for narrative
> rationale this contract intentionally omits.
>
> **Binds, never re-mints.** The bridge mechanics (seed, pull, status, push-back) are
> `spec-pyforge-herald` HER-1..3 and the herald CLI's Epics 1–5; the render-to-PNG discipline
> is `spec-deck-visual-qa` CAP-1; the deck-family workflow and its export set are
> `docs/specs/presentation-deck.md`. This Spec names only what none of those cover: the
> standard, the fact ledger, the rebuild, the mirror proof, and the staleness check.

# The deck family stays current — infographics re-derived from the ledgers, not remembered

## Why

A pain to solve and a mandate to meet. Herald's posters are the ecosystem's explainer surface
and the input corpus for video production, and every one of them is frozen at its authoring
date. Measured 2026-09-13: eleven of fourteen `Infographic standalone.html` posters are the
2026-07-24/25 six-section stubs (14–48 KB, no inline diagram, no act band); the three at
exemplar depth quote the tooling and fleet of July — the Marshal poster says `bmad-method
6.10.0`, `bmad-loop 0.9.0`, "128/333 fleet-wide" and "Herald 4/27" against a live BMAD 6.12.0,
846/865 stories and herald 67/68. Main has moved 4,414 commits since the family-wide sync. The
Design side holds nothing newer to pull, the herald CLI reports every deck unlinked, and no
poster cites a source for any number it shows, so nothing can even detect the decay. The
operator's standing rules already say how posters must be made — full depth, six acts, facts
from ledgers — and the exemplar program names this family as the fleet's purely manual
exemplar. This Spec is its graduation: one written standard, one fact ledger per deck, ten
posters rebuilt from it, the Design mirror proven, and staleness made visible.

## Capabilities

- **CAP-1**
  - **intent:** One codified infographic standard exists that any author or reviewer can check
    a poster against — the six-act arc with act bands, the full-depth section set adapted per
    subject, the inline-diagram floor, the length class and the source-cited-facts rule —
    with Unifying Strategy as the structure, acts and length reference and Warden as the
    density and visual-form reference.
  - **success:** `infographic-standard.md` is the standard's single home and
    `docs/specs/presentation-deck.md`'s verify checklist points to it; each rebuilt poster's
    README ledger records its measured values (sections, act bands, inline SVGs, bytes, cited
    facts) against the floors; a poster below any floor is not marked current.
- **CAP-2**
  - **intent:** Every count, version, status and date a poster shows is traceable to a live
    source through a per-deck fact ledger, `presentations/<slug>/facts.yaml`, re-derivable on
    demand from the tracked ledgers and manifests — never from a prior poster or from memory.
  - **success:** Each of the ten decks has a `facts.yaml` whose rows carry `id`, `value`,
    `source`, `method` and `derived_at`; every numeric, version or status token the poster
    shows resolves to a row; re-deriving on an unchanged tree reproduces the values
    byte-identically; re-deriving after a tracked ledger changes reports the changed rows.
- **CAP-3**
  - **intent:** Each PyForge-branded poster is rebuilt to the standard from its fact ledger,
    repo-side and at full depth.
  - **success:** All ten `presentations/pyforge-*/project/<Name> Infographic standalone.html`
    meet CAP-1's floors and cite CAP-2's rows; each renders headless to a full-page PNG with no
    clipped or blank region, and the README ledger records the render date and page height;
    each lands through its own PR.
- **CAP-4**
  - **intent:** The Design mirror carries the same bytes as git for every rebuilt poster, and
    the bridge knows about it.
  - **success:** Each poster is pushed to its Design project through the DesignSync local-path
    pipeline; the README ledger records the returned etag and byte count; a read-back is
    byte-identical (content-identical after the harness strip above 256 KiB); `herald deck
    status` reports the deck linked; `pyforge-unifying-strategy` has a Modernist-bound Design
    project holding its poster.
- **CAP-5**
  - **intent:** Poster staleness is detectable — an advisory check compares each poster's fact
    tokens against a fresh derivation and names the stale posters and rows.
  - **success:** After a tracked ledger changes a value a poster shows, the check names that
    poster and row; on an unchanged tree it reports clean; it always exits 0 and is invocable
    as a pixi task.

## Constraints

- **Derive, never declare.** No number, version, status or date ships without a `facts.yaml`
  row. Sources are tracked artifacts CI can see — `fleet-picture`, the
  `sprint-status-ledger.yaml` files, `pyproject.toml`, `_bmad/_config/manifest.yaml`, `SPEC.md`
  capability tables, `bmad-groundtruth`, skill frontmatter, CLI subparsers, `pytest
  --collect-only` — never gitignored Tier-3 files, never a prior poster, never memory. Sprint
  status is read with the real parser, never a regex.
- **Never restrict size at authoring time.** The 90 KB+ class is a floor; cutting is a later
  visual act.
- **Repo-side first.** Author in git; push with DesignSync `finalize_plan` → `write_files`
  (`localPath`) so bytes never relay through model context. No Design-chat authoring or visual
  polish in this slice; any later Design edit session ends with a byte-exact pull.
- **The standalone leads — a dated exception to trio lockstep (operator, 2026-09-13).** Each
  README ledger marks the Infographic head and Infographic Deck "standalone ahead" until the
  lockstep slice re-derives them from the same `facts.yaml`.
- **Filename and form contract unchanged.** `<Persona> Infographic standalone.html` at
  `presentations/<slug>/project/` and at the Design project root (the herald CLI derives the
  remote name from the persona); display brand in content, slug in paths; Modernist tokens
  inlined in `<head>`; renders from disk; Google Fonts online with system fallback; inline SVG
  only; no external scripts.
- **One PR per deck**, carrying the `maintenance` label; four worktree agents per wave;
  parallel agents address projects by physical path and never call `bmad-switch`.
- **Advisory, not a second gate.** The facts check exits 0 and warns; it becomes a PR verdict
  only if a later Spec promotes it.
- **Wave order.** Wave A is the eight station decks; Wave B is genesis and unifying-strategy.
  The unifying-strategy Design project is created through the claude-design MCP
  `create_project` bound to Modernist (`fbc1d6c8-b35f-4df6-9044-a64d2675427b`); DesignSync's
  `create_project` mints design-system-typed projects only.
- **Above 256 KiB, verify through the MCP path** (`render_preview` → `curl` → strip); DesignSync
  `get_file` caps at 256 KiB. Marp-derived `src/marp/*-infographic-standalone-*.html` stay
  `deck-export` outputs, untouched.

## Non-goals

- Re-deriving the Infographic head, Infographic Deck or Executive Summary — the lockstep
  follow-up slice, named in the Dream and scheduled after this one.
- The four chain decks (unity-data-stack, wasm-analytics-stack, deckcraft,
  presenton-pixi-image) and `agentic-sdlc`.
- Design-side visual polish, deck prototypes, the React decks, the PPTX exports.
- A new deck engine, or any change to `deck_export.py`'s semantics.
- A second PR gate.

## Success signal

On the day the ten PRs are merged, opening any PyForge-branded poster shows a six-act,
exemplar-depth page whose every number matches its `facts.yaml` re-derived that day; the deck
README ledgers carry Design etags proving the mirror holds the same bytes; `herald deck status`
lists all ten decks linked; and the advisory check reports clean — then names the first stale
poster the moment a tracked ledger moves.

## Assumptions

- The claude-design MCP is reconnected (`/mcp`) before Wave B's project creation and before any
  read-back above 256 KiB; Wave A pushes proceed on DesignSync alone.
- Warden's Design-side standalone is unchanged since 2026-07-24 (file set unchanged; etag not
  re-verifiable without the MCP), so the disk copy (411,764 B) is the visual reference.
