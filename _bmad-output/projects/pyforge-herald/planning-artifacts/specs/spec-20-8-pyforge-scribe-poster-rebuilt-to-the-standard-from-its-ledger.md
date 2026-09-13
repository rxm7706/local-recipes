---
title: 'PyForge Scribe poster rebuilt to the standard from its ledger'
type: 'feature'
created: '2026-09-13'
status: 'done'
baseline_revision: fbefe6eea6
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

**Problem:** `presentations/pyforge-scribe/project/PyForge Scribe Infographic standalone.html`
was the 2026-07-24 stub — 15,978 B, six sections, no act bands, no inline diagram — and its
numbers (a "6 tools" figure, "30+" memory entries, "10+" memlogs, "25 Dreams", "100%") cited
no source. It predated the station's own realization (Epics 2–8: the graph, the transcript
surface, the plugin drivers, the persona and portal, the docs skills, the nightly trigger)
and the family standard.

**Approach:** Author the poster repo-side to `spec-deck-family-currency/infographic-standard.md`
(Unifying Strategy = structure/acts/length; Warden = density/visual form; the finished Wave A
Doctor poster as the worked template) from `presentations/pyforge-scribe/facts.yaml`,
re-derived with `deck-facts pyforge-scribe` at the branch base. Every count, version, status
and date is a `<span data-fact="…">` mark whose text is the row's `value` or a `shown_as`
literal; anything without a row is left out or named without a count. Scribe's own doctrine
is the spine: append-only `capture` as the single write path, the proposal-then-confirm
promotion boundary (`--promote`, `--transcripts`), the nightly full-rebuild `graph compile`
through the `GraphStore` port and its three plugin drivers, supersede-never-delete, the
git-timestamp staleness flag, and `recall` that cites or returns the explicit miss — the
inward voice to Herald's outward. Render headless to a full-page PNG at 1240 px, look at it in
2500 px tiles, fix clipping/overlap, record the measurements in the deck README ledger with
the Design etag `PENDING-PUSH`.

## Boundaries & Constraints

**Always:**
- Touch only `presentations/pyforge-scribe/{project/PyForge Scribe Infographic standalone.html,
  facts.yaml, README.md}` plus this spec.
- Modernist tokens inlined in `<head>`; only the Google Fonts `<link>` is remote; no
  `<x-dc>` wrapper, no `support.js`, no scripts, no raster images; `.tag` is `inline-block`.
- Six full-bleed act bands in arc order; ≥ 18 continuously numbered sections; ≥ 3 inline
  `<svg>` (viewBox 1128 wide, Archivo text, ink/accent/light/tint palette, `<marker>` arrows,
  labels inside their boxes); ≥ 3 tables; ≥ 90,000 bytes; full cast cards for all eight
  stations with ledger chips.
- Facts from `facts.yaml` only; never hand-edit `facts.yaml`; dates only from the
  `dream_log_*` and `tree_commit_date` rows — `poster_last_commit_date` is not printed.
- Exit codes in their own table cells, never slash-adjacent; two-part and third-party
  versions never printed.

**Never:**
- Never edit the Spec folder, `pixi.toml`, `docs/`, `scripts/`, sprint ledgers or
  `scripts/.spec-surface-baseline.json` (operator reconciles).
- Never run `scripts/bmad-switch`; never restrict size at authoring time; never invent a fact
  row; never merge the PR.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fact check | `deck-facts pyforge-scribe --check` on the rebuilt poster | `0 unmarked, 0 mismatch`; `unshown` may be non-zero | exit 0 always (advisory); iterate until clean |
| No `cli_verbs` row | the `scribe` parser is typer, not argparse-literal — the derivation omits the row | verbs named in prose from the SKILL/runbooks, never counted | — |
| A wanted number has no row | module/line counts, test counts, transcript file/byte figures, synonym-map size, embedding dim, cluster port, cron time, bound sizes, the legacy spec's story count, the stale "19/19" | omitted, or written as prose without a literal | — |
| Exit codes in prose | `0` and `2` | separate table cells; "exits two" / "exit zero" in prose | — |
| Render | Playwright Chromium, viewport 1240 × 900, full page | PNG with no clipped, overlapping or blank region; height recorded from the settled capture | fonts forced via `document.fonts.load`; height re-read after the first capture's reflow |
| Spec-surface | `python -m pyforge.doctor.sources spec-surface` | drift-presumed lines only for this story's files | anything else reported, not fixed |

</intent-contract>

## Tasks & Acceptance

**Execution:** hand-authored 2026-09-13 in worktree `lr-wa-scribe` on branch
`herald/20-8-pyforge-scribe-poster` from `origin/main` `fbefe6eea6` (Wave A, one of four
parallel worktree agents; physical paths, no `bmad-switch`).

**Acceptance Criteria:** poster meets every floor in `infographic-standard.md`; `--check`
reports `0 unmarked, 0 mismatch`; full-page PNG reviewed in tiles with no clipped/overlapping/
blank region; README ledger carries measured values, `PENDING-PUSH` etag, render date, page
height and "standalone ahead"; PR carries the `maintenance` label and touches only this deck's
folder plus this spec.

## Auto Run Result

**Summary:** Rewrote the poster as a 23-numbered-section, six-act page (masthead with five
marked stats · hero · Act I problem/record table/topology SVG/CAP grid · Act II eight full
cast cards with ledger chips, the GraphStore drivers table, persona and skills · Act III
decision-journey table, write-path/projection/read-path SVG, autonomy-gradient SVG,
phase×persona×skills table, relay SVG · Act IV six CLI cards, doctrine band, stack table,
which-tool-when, escalation + exit-code table · Act V leaders, air-gap, seams · Act VI proof
(CAP table + fleet table), dated seed, now/next/later · creed band). `deck-facts
pyforge-scribe` refreshed `facts.yaml` at tree `fbefe6eea6` (41 rows; `cli_verbs` omitted by
the derivation). README ledger section appended.

**Measurements:** 144,946 B · 24 `<section` (23 numbered + creed) · 6 acts (ACT I..VI) ·
4 `<svg` · 9 `<table` · 95 `data-fact` marks · page 21684 px at 1240 px wide (settled
full-page capture; `scrollHeight` reads 21574 before the first capture's font-metrics reflow) ·
0 scripts, 0 raster images, 0 `<x-dc>`, 0 `inline-flex`.

**`--check` summary:** `pyforge-scribe: 0 unmarked, 0 mismatch, 0 drifted, 0 unsourced,
1 unshown; facts 95/95` — the one unshown row is `poster_last_commit_date`, deliberately not
printed.

**Visual QA:** first render showed six defects — the stat-strip date wrapping mid-hyphen, §01's
long paragraph leaving the three stat columns mostly blank, two topology hub lines within ~3 px
of the hub edge, the gradient's last rung label overflowing the viewBox's right edge,
`scribe capture --transcripts` wrapping after `--`, and the §17 tint box (a flex column)
breaking its inline `graph.json` span onto its own line; all fixed and re-rendered. A seventh
finding was a measurement artifact, not a defect: the creed footer appeared cut because the
page height was read before the first full-page capture's reflow; the settled capture shows it
whole. Tiles were then cut from the true PNG and re-inspected clean.

**Left out for lack of a fact row:** CLI verb count (typer parser — verbs named in prose),
module and line counts, test counts (`--with-tests` not run), transcript-surface file/byte
figures and the three bound sizes, the synonym-map size and embedding dimension, the cluster
port, the cron time and the freshness period, the legacy intake spec's story count, the
Dream's stale "19/19" (the ledger says 20/20), the satellite Dreams' own log dates, and every
third-party or two-part version (typer, pydantic, psycopg, graphifyy, cocoindex, Python).
Exit codes appear as code literals in separate cells, never as counts.

**Verification:** `deck-facts pyforge-scribe --check` clean; Playwright full-page PNG at
`.herald/deck-qa/pyforge-scribe/standalone.png` (gitignored) reviewed in nine tiles plus the
true bottom crop; tag balance verified with `html.parser` (no stray, mismatched or unclosed
tags); `spec-surface` verdict recorded in the PR body.
