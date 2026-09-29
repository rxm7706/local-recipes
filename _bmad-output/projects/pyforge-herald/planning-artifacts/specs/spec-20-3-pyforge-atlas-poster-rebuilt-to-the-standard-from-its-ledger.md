---
title: 'PyForge Atlas poster rebuilt to the standard from its ledger'
type: 'feature'
created: '2026-09-13'
status: 'done'
baseline_revision: b5fe5e46fc
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
verdict_mode: advisory
---

<intent-contract>

## Intent

**Problem:** `presentations/pyforge-atlas/project/PyForge Atlas Infographic standalone.html` was
the 2026-07-24 stub — 15,678 B, six sections, no act bands, no inline SVG — and every number it
showed ("32/32", "19,726 feedstocks", "shipped 2026-07-18", "28 CLIs", "23 phases") was a
remembered July claim with no source line, several of them stale against the station's own
ledgers (the station has grown well past the migration: 94/95 stories across 24 epics).

**Approach:** Author the poster repo-side, at full depth, to `infographic-standard.md`
(spec-deck-family-currency CAP-1) with Unifying Strategy as the structure/acts/length reference
and Warden/Marshal as the density and cast-card references; take every count, version, status
and date from `presentations/pyforge-atlas/facts.yaml` (CAP-2, re-derived at the branch base) and
wrap each as a `data-fact` mark; ground the Atlas-specific substance (the Kedro/Dagster/DuckDB
dataflow, the sealed pipelines and their riders, the Boring Semantic Layer and Vizro read surface,
the MCP face and the CLI ⇄ tool parity gate, the A2A channel, run admission, the degradation and
exit contracts, the trending-candidates discovery engine and its Mason handoff, the Unity/Wasm
satellites) in the Dream, `spec-pyforge-atlas/SPEC.md` and its companions, `epics.md`, the SKF
content skill and the package's own module docstrings; render headless to a full-page PNG, look
at it, fix every overlap; record the measured values in the deck README ledger (CAP-3). The
Design mirror push (CAP-4) is left to the operator after review, recorded as `PENDING-PUSH`.

## Boundaries & Constraints

**Always:**
- Every count, version, status and date on the poster is a `data-fact` mark whose literal equals a
  `facts.yaml` row's `value` or one of its `shown_as` strings; `deck-facts pyforge-atlas --check`
  reports `0 unmarked, 0 mismatch`.
- Six full-bleed act bands `ACT I`…`ACT VI` in arc order; ≥ 18 continuously numbered sections;
  ≥ 3 inline `<svg>` in Modernist tokens (viewBox 1128 wide, Archivo text, `<marker>` arrows);
  ≥ 3 tables; ≥ 90,000 bytes; eight full station cards with ledger chips; closing creed band on
  the accent colour.
- Self-contained: Modernist tokens inlined in `<head>`; the Google Fonts `<link>` is the only
  remote resource; no `<x-dc>`, no `support.js`, no scripts, no raster images.
- Touch only this deck's folder plus this story spec; physical paths only; never `bmad-switch`.

**Never:**
- Never print a number, version, status or date that has no ledger row — leave it out (the
  legacy LOC count, the feedstock population, page/phase/pipeline/dataset counts, PR numbers,
  non-ledger dates and third-party versions were all left out for this reason; entity counts are
  enumerated by name instead of counted).
- Never hand-edit `facts.yaml`; never take a fact from a prior poster or from memory.
- Never edit the Spec folder, `pixi.toml`, `docs/`, the sprint ledgers or
  `scripts/.spec-surface-baseline.json` — the operator reconciles those.
- Never push to Design or merge in this story.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Facts check | rebuilt poster + `facts.yaml` at `b5fe5e46fc` | `0 unmarked, 0 mismatch, 0 drifted, 0 unsourced`; `unshown` rows allowed | a mismatch is fixed in the poster, never in the ledger |
| Ledger disagrees with an earlier derivation | `recipes_count` 7872 (unclean checkout) vs 7864 (clean tree) | the poster prints the clean-tree value; the README records the correction | — |
| A wanted fact has no row | e.g. page inventory count, legacy LOC | the number is omitted; the concept is described or enumerated | — |
| A row would go stale on landing | `poster_last_commit_date` | deliberately unshown (the one `unshown` row) | — |
| Render | headless Chromium, 1240 px wide, full page | PNG with no clipped, blank or overlapping region; 0 elements overflow the frame | overlaps found in the first render (3 SVGs, ledger table, creed footer) were fixed and re-rendered |
| Governance | files outside `recipes/` | PR carries the `maintenance` label; `spec-surface-check` drift-presumed lines name only this deck's files and this spec | anything else is reported to the operator |

</intent-contract>

## Tasks & Acceptance

**Execution:** hand-implemented 2026-09-13 in worktree `lr-wa-atlas` on branch
`herald/20-3-pyforge-atlas-poster` from `origin/main` `b5fe5e46fc` (Wave A, one of four).

**Acceptance Criteria (epics.md Story 20.3):** poster authored to the standard from `facts.yaml`
(six act bands, ≥ 18 sections, ≥ 3 inline SVGs, ≥ 90 KB, every count/version/status/date a ledger
row) ✓ · rendered headless to a full-page PNG and reviewed ✓ · README ledger carries the measured
values against the floors, the render date and page height, "standalone ahead" for the head and
Infographic Deck ✓ · Design etag recorded as `PENDING-PUSH` (CAP-4 push is the operator's step
after review — the claude-design MCP was not connected in this session and the push is
deliberately not part of the agent's scope) · `deck-facts pyforge-atlas --check` reports every
token resolved ✓ · PR carries `maintenance`, touches only this deck's folder plus this spec ✓.

## Auto Run Result

**Summary:** Rewrote `presentations/pyforge-atlas/project/PyForge Atlas Infographic standalone.html`
(15,678 B / 6 sections / 0 acts / 0 SVG → 132,410 B / 23 `<section` (22 numbered + creed) / 6 acts /
4 SVG / 8 tables / 77 `data-fact` marks). Re-derived `presentations/pyforge-atlas/facts.yaml`
(tree `b5fe5e46fc`; `recipes_count` 7872 → 7864 on the clean tree). Appended
`## Ledger — 2026-09-13 standard rebuild (Story 20.3)` to `presentations/pyforge-atlas/README.md`.

**Verification:**
- `deck-facts pyforge-atlas --check` → `summary   pyforge-atlas: 0 unmarked, 0 mismatch, 0 drifted,
  0 unsourced, 1 unshown; facts 77/77` (unshown: `poster_last_commit_date`, by design). Run as
  `scripts/deck_facts.py` under the `local-recipes` env interpreter from the worktree root — the
  same command the pixi task wraps; the fresh worktree carries no pixi environments.
- Render: Playwright headless Chromium, viewport 1240 px, full page → `.herald/deck-qa/pyforge-atlas/standalone.png`,
  page height **20835 px**, `scrollWidth` 1240, 0 elements outside the frame. First render surfaced
  five defects (tier labels/arrows colliding in the topology SVG, sub-labels overflowing boxes in
  the flow SVG, box titles/lines overflowing in the ladder SVG, a mid-token date wrap in the ledger
  table, an awkward creed footer wrap) — all fixed and re-rendered; final tiles reviewed clean.
- Floors: bytes 132,410 ≥ 90,000 · acts 6 · sections 22 ≥ 18 · SVG 4 ≥ 3 · tables 8 ≥ 3 · eight
  full cast cards · no `<x-dc>` / `support.js` / `<script` / `<img`.
- Left out for lack of a ledger row: legacy LOC (~10k), feedstock population (19,726), the
  page-inventory count (34), phase/pipeline/dataset/gate counts, PR ranges (#58–#105), non-ledger
  dates (2026-07-18, 2026-08-26, 2026-09-11 …), third-party versions (Django, Dagster, duckdb-server,
  pandas, GX). Durations (TTL days, the 90-day velocity window), the frozen exit codes and story/CAP
  identifiers are kept as contract parameters and identifiers, not facts.
