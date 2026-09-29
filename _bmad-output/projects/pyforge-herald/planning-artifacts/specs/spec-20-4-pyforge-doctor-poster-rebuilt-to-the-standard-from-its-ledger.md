---
title: 'PyForge Doctor poster rebuilt to the standard from its ledger'
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

**Problem:** `presentations/pyforge-doctor/project/PyForge Doctor Infographic standalone.html`
was the 2026-07-24 stub — 14,419 B, five sections, no act bands, no inline diagram — and none
of its numbers cited a source. It predates Doctor's own realization (CAP-5..9, Epics 4–22) and
the family standard.

**Approach:** Author the poster repo-side to `spec-deck-family-currency/infographic-standard.md`
(Unifying Strategy = structure/acts/length; Warden = density/visual form) from
`presentations/pyforge-doctor/facts.yaml`, re-derived with `deck-facts pyforge-doctor` at the
branch base. Every count, version, status and date is a `<span data-fact="…">` mark whose text
is the row's `value` or a `shown_as` literal; anything without a row is left out. Doctor's own
doctrine is the spine: pre-flight `check`, continuous `monitor`, ranked `diagnose --prescribe`,
the source registry and the two exit-code domains, findings advisory and never a second PR
gate. Render headless to a full-page PNG at 1240 px, look at it, fix clipping/overlap, record
the measurements in the deck README ledger with the Design etag `PENDING-PUSH`.

## Boundaries & Constraints

**Always:**
- Touch only `presentations/pyforge-doctor/{project/PyForge Doctor Infographic standalone.html,
  facts.yaml, README.md}` plus this spec.
- Modernist tokens inlined in `<head>`; only the Google Fonts `<link>` is remote; no
  `<x-dc>` wrapper, no `support.js`, no scripts, no raster images.
- Six full-bleed act bands in arc order; ≥ 18 continuously numbered sections; ≥ 3 inline
  `<svg>` (viewBox 1128 wide, Archivo text, ink/accent/light/tint palette, `<marker>` arrows);
  ≥ 3 tables; ≥ 90,000 bytes; full cast cards for all eight stations.
- Facts from `facts.yaml` only; never hand-edit `facts.yaml`; dates only from the
  `dream_log_*`, `tree_commit_date`, `poster_last_commit_date` rows.

**Never:**
- Never edit the Spec folder, `pixi.toml`, `docs/`, sprint ledgers or
  `scripts/.spec-surface-baseline.json` (operator reconciles).
- Never run `scripts/bmad-switch`; never restrict size at authoring time; never invent a fact
  row; never merge the PR.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fact check | `deck-facts pyforge-doctor --check` on the rebuilt poster | `0 unmarked, 0 mismatch`; `unshown` may be non-zero | exit 0 always (advisory); iterate until clean |
| A wanted number has no row | e.g. detector count, Charter ratification date | omitted from the poster or written as prose without a literal | — |
| Exit codes in prose | `0 · 2 · 130` and `0 / 1 / 2` | rendered as separate code literals, never `n/n` adjacent (the sweep would read `0/2` as a fraction) | — |
| Render | Playwright Chromium, viewport 1240 × 900, full page | PNG with no clipped, overlapping or blank region; height recorded | fall back to headless Chrome if Playwright missing |
| Spec-surface | `spec-surface-check` | drift-presumed lines only for this story's files | anything else reported, not fixed |

</intent-contract>

## Tasks & Acceptance

**Execution:** hand-authored 2026-09-13 in worktree `lr-wa-doctor` on branch
`herald/20-4-pyforge-doctor-poster` from `origin/main` `b5fe5e46fc` (Wave A, one of four
parallel worktree agents; physical paths, no `bmad-switch`).

**Acceptance Criteria:** poster meets every floor in `infographic-standard.md`; `--check`
reports `0 unmarked, 0 mismatch`; full-page PNG reviewed with no clipped/overlapping/blank
region; README ledger carries measured values, `PENDING-PUSH` etag, render date, page height
and "standalone ahead"; PR carries the `maintenance` label and touches only this deck's folder
plus this spec.

## Auto Run Result

**Summary:** Rewrote the poster as a 23-numbered-section, six-act page (masthead · hero · Act I
problem/chart/topology/CAP grid · Act II eight full cast cards, source registry, persona map ·
Act III journey table, pipeline SVG, autonomy-gradient SVG, phase×persona×skills table, relay
SVG · Act IV CLI cards, doctrine band, stack table, which-tool-when, escalation + exit-code
table · Act V leaders, air-gap, seams · Act VI proof (CAP table + fleet table), dated seed,
now/next/later · creed band). `deck-facts pyforge-doctor` refreshed `facts.yaml` (tree
`b5fe5e46fc`, `recipes_count` 7872 → 7864). README ledger section appended.

**Measurements:** 135,606 B · 24 `<section` (23 numbered + creed) · 6 acts (ACT I..VI) ·
4 `<svg` · 9 `<table` · 85 `data-fact` marks · page 20012 px at 1240 px wide · 0 scripts,
0 raster images.

**`--check` summary:** `pyforge-doctor: 0 unmarked, 0 mismatch, 0 drifted, 0 unsourced,
0 unshown; facts 85/85`.

**Visual QA:** first render (20002 px) showed five SVG defects — topology hub rail and two
instrument captions overflowing their boxes, three pipeline captions overflowing, gradient
labels colliding, relay label sitting on its dashed curve, plus an awkward stat-strip wrap;
all fixed and re-rendered (20012 px), strips 1/3/4 re-inspected clean.

**Left out for lack of a fact row:** detector/source counts (registry deliberately uncounted),
the Charter §6 ratification date, the ledger-sync incident's marker count, the SPEC `verified:`
dates, the `mcp` version floor, test counts (`--with-tests` not run). Exit codes appear as
code literals, not counts.

**Verification:** `pixi run -e local-recipes deck-facts pyforge-doctor --check` clean;
Playwright full-page PNG at `.herald/deck-qa/pyforge-doctor/standalone.png` reviewed;
tag balance verified with `html.parser`; `spec-surface-check` verdict recorded in the PR body.
