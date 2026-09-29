---
title: 'PyForge Mason poster rebuilt to the standard from its ledger'
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

**Problem:** `presentations/pyforge-mason/project/PyForge Mason Infographic standalone.html`
was the 2026-07-25 stub — 14,404 B, six sections, no act bands, no inline diagram — and its
numbers (a feedstock count, a gotcha count, an atlas-phase count, a CFE version) were July
claims that no ledger could re-derive. It predates the station's realization (Epics 6–16,
the seam proof, the realization-gate residue) and the family standard.

**Approach:** Author the poster repo-side to `spec-deck-family-currency/infographic-standard.md`
(Unifying Strategy = structure/acts/length; Warden = density/visual form) from
`presentations/pyforge-mason/facts.yaml`, re-derived with `deck-facts pyforge-mason` at the
branch base. Every count, version, status and date is a `<span data-fact="…">` mark whose text
is the row's `value` or a `shown_as` literal; anything without a row is left out. Mason's own
doctrine is the spine: wrap-never-fork over `conda-forge-expert` through the one port
(`cfe.py`), the capability tiers (CFE-dependent recipe verbs and the `conda-forge` target;
everything else native), the dual-ship motion with a receipt whose `pending` is never
success, conda-lock binding, the five-engine bench, credential blindness, dry-run by default,
and the seam-holds proof suite. Render headless to a full-page PNG at 1240 px, look at it, fix
clipping/overlap, record the measurements in the deck README ledger with the Design etag
`PENDING-PUSH`.

## Boundaries & Constraints

**Always:**
- Touch only `presentations/pyforge-mason/{project/PyForge Mason Infographic standalone.html,
  facts.yaml, README.md}` plus this spec.
- Modernist tokens inlined in `<head>`; only the Google Fonts `<link>` is remote; no
  `<x-dc>` wrapper, no `support.js`, no scripts, no raster images; `.tag` is
  `display:inline-block` so whitespace around marked spans survives.
- Six full-bleed act bands in arc order; ≥ 18 continuously numbered sections; ≥ 3 inline
  `<svg>` (viewBox 1128 wide, Archivo text, ink/accent/light/tint palette, `<marker>` arrows,
  no fact tokens inside SVG text); ≥ 3 tables; ≥ 90,000 bytes; full cast cards for all eight
  stations.
- Facts from `facts.yaml` only; never hand-edit `facts.yaml`; dates only from the
  `dream_log_*` and `tree_commit_date` rows (`poster_last_commit_date` deliberately not
  printed — it goes stale on the landing commit); other stations' progress only through
  `<station>_stories_done_total` / `_epics_done_total` rows.

**Never:**
- Never edit the Spec folder, `pixi.toml`, `docs/`, `scripts/`, sprint ledgers or
  `scripts/.spec-surface-baseline.json` (operator reconciles).
- Never run `scripts/bmad-switch`; never restrict size at authoring time; never invent a fact
  row; never print a two-part or third-party version; never merge the PR.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fact check | `deck-facts pyforge-mason --check` on the rebuilt poster | `0 unmarked, 0 mismatch`; `unshown` may be non-zero | exit 0 always (advisory); iterate until clean |
| A wanted number has no row | e.g. the feedstock count, the CFE line count, engine versions | omitted from the poster, or the entities enumerated by name (three nouns, five engines, four targets) | — |
| Exit codes and ship states | `0 · 1 · 2 · 3 · 130` | each in its own table cell, never slash-adjacent (the sweep would read `0/1` as a fraction) | — |
| SVG captions | topology, dual-ship flow, gradient, relay | every label inside its box; column labels never collide; footnotes wrap inside the viewBox | re-render and re-inspect after each fix |
| Render | Playwright Chromium, viewport 1240 × 900, full page in 2500 px tiles | PNG with no clipped, overlapping or blank region; height recorded | fall back to headless Chrome if Playwright missing |
| Spec-surface | `python -m pyforge.doctor.sources spec-surface` | drift-presumed line against `spec-deck-family-currency` only | anything else reported, not fixed |

</intent-contract>

## Tasks & Acceptance

**Execution:** hand-authored 2026-09-13 in worktree `lr-wa-mason` on branch
`herald/20-7-pyforge-mason-poster` from `origin/main` `fbefe6eea6` (Wave A, one of four
parallel worktree agents; physical paths, no `bmad-switch`; the worktree has no pixi envs, so
`scripts/deck_facts.py` and Playwright ran under the main checkout's `local-recipes` and
`pyforge-herald` interpreters from the worktree root).

**Acceptance Criteria:** poster meets every floor in `infographic-standard.md`; `--check`
reports `0 unmarked, 0 mismatch`; full-page PNG reviewed with no clipped/overlapping/blank
region; README ledger carries measured values, `PENDING-PUSH` etag, render date, page height
and "standalone ahead"; PR carries the `maintenance` label and touches only this deck's folder
plus this spec.

## Auto Run Result

**Summary:** Rewrote the poster as a 23-numbered-section, six-act page (masthead · hero ·
Act I problem / the seam tiers table / topology SVG / thirteen-CAP grid · Act II eight full
cast cards, the engines-on-the-bench table, persona + the skill deliberately not minted ·
Act III recipe-journey table (eight verbs × wrapped script × invariant), dual-ship flow SVG,
autonomy-gradient SVG, phase×persona×skills table, relay SVG · Act IV four CLI cards + the
six-global-flags table, doctrine band, stack table, which-tool-when, escalation grid + exit-code
and ship-state tables · Act V leaders, air-gap + the Presenton satellite, seams · Act VI proof
(CAP table + fleet table + the realization-gate box), dated seed, now/next/later · creed
band). `deck-facts pyforge-mason` refreshed `facts.yaml` (tree `fbefe6eea6`, `recipes_count`
7872 → 7864). README ledger section appended.

**Measurements:** 151,188 B · 24 `<section` (23 numbered + creed) · 6 acts (ACT I..VI) ·
4 `<svg` · 11 `<table` · 91 `data-fact` marks · page 21820 px at 1240 px wide · 0 scripts,
0 raster images.

**`--check` summary:** `pyforge-mason: 0 unmarked, 0 mismatch, 0 drifted, 0 unsourced,
0 unshown; facts 91/91`.

**Visual QA:** first render (21802 px) showed four SVG defects — the topology's two mid-rail
annotations ("SUBPROCESS ONLY", "ONE ADAPTER PROTOCOL") sitting on the spoke curves, the
topology's idempotence footnote overflowing the right edge, the dual-ship "TARGETS · EACH
ATTEMPTED INDEPENDENTLY" column label running into "RECEIPT", and two edge-tight captions
(the conda-lock box, the alias rail); all fixed and re-rendered (21820 px), tiles 1 and 3 and
the page bottom re-inspected clean. The creed footer was verified in place by geometry
(21702–21764 of 21820) and a scrolled viewport screenshot after a full-page bottom clip
appeared to cut it.

**Left out for lack of a fact row:** the feedstock count (the July stub's "769"), the CFE
line count, the hard-constraint count, test counts (`--with-tests` not run), engine versions
(pixi / twine / conda-lock / build / gh ranges), the PRD/NFR/AD counts, `poster_last_commit_date`
by rule, and every date outside the Dream's realization log (the August rebuild directive,
the fleet-ledger completion date, the verification-pass dates). Exit codes and ship states
appear as code literals in their own cells, not as counts; small structural counts (three
nouns, five engines, four targets, six flags, eight verbs) are enumerated by name on the
poster. Presenton's `archived`/`blocked` statuses have no row and are described in prose
("parked at its Phase-0 decision gate") rather than printed as status words.

**Verification:** `scripts/deck_facts.py pyforge-mason --check` clean; Playwright full-page
PNG at `.herald/deck-qa/pyforge-mason/standalone.png` (gitignored) reviewed in nine 2500 px
tiles; tag balance verified with `html.parser`; `spec-surface` verdict recorded in the PR
body.
