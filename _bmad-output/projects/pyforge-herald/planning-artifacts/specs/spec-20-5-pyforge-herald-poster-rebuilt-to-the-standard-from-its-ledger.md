---
title: 'PyForge Herald poster rebuilt to the standard from its ledger'
type: 'feature'
created: '2026-09-13'
status: 'done'
baseline_revision: b5fe5e46fccc229038514b13140fe1c90aa658c4
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

**Problem:** `presentations/pyforge-herald/project/PyForge Herald Infographic standalone.html`
was the 2026-07-25 six-section stub (16,720 B, no act band, no inline SVG) and cited no source
for any number it showed — a claim the estate could not stand behind (herald Story 20.5;
`spec-deck-family-currency` CAP-3, Wave A).

**Approach:** Author the poster repo-side, at full depth, to
`spec-deck-family-currency/infographic-standard.md` — the Unifying Strategy poster's `<head>`
token block, masthead, act-band and numbered-section markup; Warden's density — from
`presentations/pyforge-herald/facts.yaml` re-derived on the clean branch point. Every count,
version, status and date is a `<span data-fact="<row>">literal</span>`; a number with no row is
left out. Render headless to a full-page PNG and look at it; record the measured values in the
README ledger; open one `maintenance`-labelled PR touching only this deck's folder plus this
story spec.

## Boundaries & Constraints

**Always:**
- Facts come from `facts.yaml` only (derived by `scripts/deck_facts.py` from tracked ledgers,
  manifests, the spec, the Dream and the CLI source); the poster is checked with
  `deck-facts pyforge-herald --check` until `0 unmarked` and `0 mismatch`.
- Six full-bleed act bands `ACT I`…`ACT VI` in arc order; sections numbered `01`… continuously;
  ≥ 18 sections, ≥ 3 inline `<svg>` (viewBox 1128 wide, Archivo text, ink/accent/light/tint,
  `<marker>` arrows), ≥ 3 tables, ≥ 90,000 bytes; full cast cards for all eight stations.
- Modernist tokens inlined in `<head>`; no `<x-dc>` wrapper, no `support.js`, no external
  scripts, no raster images; the Google Fonts `<link>` is the only remote resource.
- Physical paths only; never `scripts/bmad-switch`; never another deck's folder, `pixi.toml`,
  `docs/`, the Spec folder, the sprint ledgers or `scripts/.spec-surface-baseline.json`.

**Never:**
- Never invent or hand-edit a `facts.yaml` row; never print a bare integer, status word,
  version or date that is not a row; never restrict size at authoring time.
- Never push to the Design project from this story (CAP-4 is the operator's DesignSync push
  after review; the README etag cell reads `PENDING-PUSH`).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Derive on the clean branch point | `deck-facts pyforge-herald` at `b5fe5e46fc` | `facts.yaml` header `tree` = branch sha, no `-dirty`; 40 rows | a dirty tree would stamp `-dirty` — derive before editing |
| Check the rebuilt poster | `deck-facts pyforge-herald --check` | `0 unmarked, 0 mismatch, 0 drifted, 0 unsourced`; `unshown` rows allowed; exit 0 | iterate on marks until clean |
| A wanted number has no row | e.g. drift byte counts, stub counts, test counts, pilot dates | the sentence is written without the literal | — |
| Render | headless Chromium, 1240 px, full page | PNG under `.herald/deck-qa/pyforge-herald/` (gitignored), no clipped/blank region, page height recorded | fix layout and re-render |
| Surface check | `spec-surface-check` in the worktree | drift-presumed lines only for the poster, the README and this spec (operator reconciles) | anything else is reported |

</intent-contract>

## Tasks & Acceptance

**Execution:** hand-implemented 2026-09-13 in worktree `lr-wa-herald`, branch
`herald/20-5-pyforge-herald-poster` off `origin/main` `b5fe5e46fc`, as one of the Wave A
parallel agents (physical paths, no `bmad-switch`).

- `presentations/pyforge-herald/facts.yaml` — re-derived on the clean tree (header + `recipes_count` moved).
- `presentations/pyforge-herald/project/PyForge Herald Infographic standalone.html` — rewritten to the standard.
- `presentations/pyforge-herald/README.md` — `## Ledger — 2026-09-13 standard rebuild (Story 20.5)` appended.
- this spec — promoted to the tracked `specs/` (source of record).

**Acceptance Criteria:** the poster meets every floor in `infographic-standard.md`; every
count/version/status/date resolves to a `facts.yaml` row (`--check`: `0 unmarked, 0 mismatch`);
a full-page PNG was rendered and reviewed; the README ledger records measured values, render
date, page height, `PENDING-PUSH` for the etag and "standalone ahead" for head + Infographic
Deck; the PR carries `maintenance` and touches only this deck's folder plus this spec.

## Auto Run Result

**Summary:** Poster rebuilt from 16,720 B / 6 sections / 0 acts / 0 SVG to
**137,557 B · 24 `<section` (23 numbered + creed) · 6 act bands · 4 inline SVG (topology,
bridge-loop flow, autonomy ladder, relay) · 6 tables · 53 `data-fact` marks**. Masthead
(kicker · `PyForge Herald` · slug line · thesis · chips · five-cell stat strip, every stat
marked) → ACT I the problem & the model (01–03) → ACT II the cast (04–06; eight full cards
with role, motto, paragraph, CLI verbs and stories/epics chips) → ACT III running the line
(07–12) → ACT IV the product (13–17, doctrine band as 14) → ACT V who it serves, where it runs
(18–20) → ACT VI proof & road (21–23) → creed band on the accent colour.

**Verification:**
- `deck-facts pyforge-herald --check` → `summary   pyforge-herald: 0 unmarked, 0 mismatch,
  0 drifted, 0 unsourced, 1 unshown; facts 53/53` (unshown: `poster_last_commit_date`,
  intentionally not printed — it would drift on merge by construction).
- Render: headless Chromium 1240 px full page → `page height 17802`; PNG cut into six
  3000 px slices and each inspected — no clipped, overlapping or blank region.
- Floors: acts 6/6 · sections 24 ≥ 18 · SVG 4 ≥ 3 · bytes 137,557 ≥ 90,000 · tables 6 ≥ 3.
- Offline: only the Google Fonts `<link>` is remote; no scripts; no raster; no `<x-dc>`.

**Left out for lack of a fact row (by rule):** the hand-relay drift size and file size, the
"eleven of fourteen posters were stubs" count, the pilot/consolidation dates other than the
Dream log rows, test counts, subparser line counts, Design project ids' byte counts, the
watch-interval defaults, the DesignSync read cap in KiB. `poster_last_commit_date` (`2026-07-25`)
exists but is not printed.

**Residual risk:** `tree_commit_date` (`2026-09-13`) is printed twice; it moves with HEAD, so a
re-derive on a later day reports it `drifted` and the marks `mismatch` — the advisory check
naming exactly the row that moved (CAP-5's intended behaviour). Words for structural constants
(eight stations, six acts, four Moments, five tiers) are prose, not swept tokens, and carry no
row.
