---
title: 'The Canopy poster re-derived and its Design project created'
type: 'feature'
created: '2026-09-13'
status: 'done'
baseline_revision: 6a49e9f223
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

**Problem:** `presentations/pyforge-unifying-strategy/project/PyForge Unifying Strategy
Infographic standalone.html` (display brand **The Canopy**) is the family's *structure, acts
and length* reference — 128,783 B, 21 sections, six acts, nine inline SVGs — and it is the one
deep poster whose shape is already correct. What is wrong is its facts: it was frozen at its
2026-08-26 authoring date and cited no source for any number. It still read "CAP-1..18 closed
2026-08-26 · CAP-19 live", "Five-tier symmetry — declared complete, 40/40", "Py 3.12", a
six-cell timeline of August dates, and a set of third-party pins (`mcp 2.0.0`,
`liquibase 5.0.4+`, `Django >=5.2.17,<6`) that no tracked ledger can source.

**Approach:** Facts only — the arc, section order, diagrams and length are left alone. Re-derive
`presentations/pyforge-unifying-strategy/facts.yaml` with `deck-facts pyforge-unifying-strategy`
at the branch base, then make every printed count, version, status and date a
`<span data-fact="…">` mark whose text is the row's `value` or a `shown_as` literal. Replace
stale literals with the row's current value. Anything with no row is rewritten as prose without
a literal count or date — never guessed, never carried over from the poster itself. Re-anchor
the Act V timeline on the Dream's live `dream_log_*` rows, since its own August entries have
been archived out of the living Realization log. Render headless at 1240 px, look at it in
~2500 px tiles to prove the marks changed no layout, and record the measurements in the deck
README ledger with the Design etag `PENDING-PUSH`.

## Boundaries & Constraints

**Always:**
- Touch only `presentations/pyforge-unifying-strategy/{project/PyForge Unifying Strategy
  Infographic standalone.html, facts.yaml, README.md}` plus this spec.
- Preserve the structure reference exactly: six act bands in arc order, 21 sections in their
  existing order, nine inline SVGs, ≥ 90,000 bytes. This story changes facts, not shape.
- Facts from `facts.yaml` only; never hand-edit `facts.yaml`; dates only from the
  `dream_log_*` and `tree_commit_date` rows. `poster_last_commit_date` is never printed.
- `.tag { display:inline-block }` so a `data-fact` mark inside a chip keeps its spacing.

**Never:**
- Never edit the Spec folder, `pixi.toml`, `docs/`, `scripts/`, sprint ledgers or
  `scripts/.spec-surface-baseline.json` (operator reconciles).
- Never touch another deck's folder or the main checkout; never run `scripts/bmad-switch`;
  never invent a fact row; never merge the PR.
- Never restrict size at authoring time.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fact check | `deck-facts pyforge-unifying-strategy --check` | `0 unmarked, 0 mismatch`; `unshown` may be non-zero | exit 0 always (advisory); iterate until clean |
| A printed number has no row | `40/40`, `1/8`, third-party pins, MCP protocol revision dates | rewritten as prose without a literal count/date | — |
| A date has no row | the §15 August milestone chips (archived out of the living log) | chip becomes an ordinal label; the lede cites the live `dream_log_*` rows instead | — |
| Adjacent literals fuse | `Lane 1 <code>/</code> <b>200</b>` normalizes to the fraction `1/200` | reordered so no digit sits either side of a `/` | the sweep reports it as `unmarked`; fix the prose, never the checker |
| Render | Playwright Chromium, viewport 1240 × 900, full page | PNG with no clipped, overlapping or blank region; height recorded | inspect in ~2500 px tiles |
| Spec-surface | `spec-surface-check` | drift-presumed lines only for this story's files | anything else reported, not fixed |

</intent-contract>

## Tasks & Acceptance

**Execution:** hand-authored 2026-09-13 in worktree `lr-wb-unify` on branch
`herald/20-12-canopy-poster` from `origin/main` `6a49e9f223` (Wave B; physical paths, no
`bmad-switch`).

**Acceptance Criteria:** every count, version, status and date the poster prints resolves to a
`facts.yaml` row; `--check` reports `0 unmarked, 0 mismatch`; the structure reference's arc,
section order, diagram set and length class are unchanged; full-page PNG reviewed with no
clipped/overlapping/blank region; README ledger carries measured values, the `PENDING-PUSH`
etag, render date, page height and "standalone ahead"; PR carries the `maintenance` label and
touches only this deck's folder plus this spec.

## Auto Run Result

**Scope note — this is the poster half only.** The Design half of Story 20.12 is the operator's:
the Design project **"PyForge Unifying Strategy deck"** (`1e4020bc-7f7f-43b2-9219-0904d4863df6`,
bound to Modernist `fbc1d6c8-b35f-4df6-9044-a64d2675427b`) was already created and seeded with
the family by the operator before this run, and the push of the re-derived poster, the byte-exact
read-back, the returned etag and the canonical `## Design project` registry section in the deck
README remain theirs. This run wrote no Design-side state and registered nothing; the README
ledger records the etag as `PENDING-PUSH`.

**Summary:** `deck-facts pyforge-unifying-strategy` re-derived `facts.yaml` at tree
`6a49e9f223` (41 rows). 36 `data-fact` marks added across the masthead, the meta strip, the
capability grid, Acts III–VI. Stale literals replaced from the ledger: the masthead status line
(`CAP-1..18 closed 2026-08-26 · CAP-19 live` → `Spec ready · CAP-1..19 · Dream specified`), the
capability chip and Scope cell (`spec_capabilities`), the Owner cell (now carries
`steward_stories_done_total` — this chain's ledger proxy, the story having no station package),
and the Host cell (`Py 3.12` → `Py 3.14`, the fixed floor in the Spec's `stack.md`). A new box
under the §17 five-tier matrix carries the eight stations' story and epic rows plus the fleet
totals, and a provenance line closes §15 with `tree_commit_date`, `bmad_core_version`,
`bmad_loop_version` and `groundtruth_pixi_envs`. `.tag` moved from `inline-flex` to
`inline-block`. The arc, section order, nine diagrams and length class are untouched.

**Measurements:** 132,338 B · 21 `<section` · 6 acts (ACT I..VI) · 9 `<svg` · 0 `<table` but
four grid-rendered table equivalents (§05 capability grid, §12 directive grid, §17 five-tier
matrix, §19 which-surface-when) · 36 `data-fact` marks · page 13,790 px at 1240 px wide ·
0 scripts, 0 raster images.

**`--check` summary:** `pyforge-unifying-strategy: 0 unmarked, 0 mismatch, 0 drifted,
0 unsourced, 9 unshown; facts 36/36` — re-verified at the final base after two mid-run rebases
(main moved three times during the run; five rows — `herald_stories_done_total`,
`scribe_stories_done_total`, `scribe_epics_done_total`, `fleet_stories_done_total`,
`fleet_epics_done_total` — were re-synced to the fresh ledger values by a mechanical pass over
the `data-fact` spans, never by hand-editing `facts.yaml`).

**Rewritten as prose for lack of a row:** `40/40` (meta strip + §17 heading), `1/8` (§01 stat),
the dated closeout claims (`closed 2026-08-26`, `Minted 2026-08-26`, `Live proof · CRC
2026-08-26` ×2, `OQ ruling · 2026-08-26` ×3, `declared 2026-08-26`), the §15 timeline chips
(`Day one … Day four`, with the lede now citing `dream_log_2026-09-01/-02/-04/-09/-12`), the MCP
protocol revisions `2025-03-26 → 2026-07-28` (body prose and the §04 SVG label), the tier ids
`01/02`, and the third-party pins `mcp 2.0.0`, `liquibase 5.0.4+`, `cachebox`/`6.2.5`,
`vizro-ai 0.4.2`, `Django >=5.2.17,<6`. One fused token — `Lane 1 <code>/</code> <b>200</b>`
normalizing to `1/200` — was resolved by reordering the sentence.

**Left `unshown` (allowed):** `poster_last_commit_date` (deliberately never printed),
`recipes_count`, `groundtruth_mcp_tools` / `_atlas_phases` / `_schema_version` / `_gotcha_max`
(factory facts not germane to this chain), and `dream_log_2026-09-03/-05/-10`.

**Visual QA:** rendered at 1240 px after a throwaway warm-up screenshot; page 13,790 px,
inspected in six ~2500 px tiles. One regression found and fixed: the lengthened masthead status
line wrapped mid-date, so `tree <date>` was dropped from the masthead (the row is still marked
in the §15 provenance line). No other layout change; the marks are inline spans only.

**Verification:** `deck-facts pyforge-unifying-strategy --check` clean; Playwright full-page PNG
at `.herald/deck-qa/pyforge-unifying-strategy/standalone.png` plus `tile0..5.png` reviewed;
`spec-surface` verdict recorded in the PR body.
