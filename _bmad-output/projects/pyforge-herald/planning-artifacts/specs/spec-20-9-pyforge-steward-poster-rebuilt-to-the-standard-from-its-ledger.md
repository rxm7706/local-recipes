---
title: 'PyForge Steward poster rebuilt to the standard from its ledger'
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

**Problem:** `presentations/pyforge-steward/project/PyForge Steward Infographic standalone.html`
was the 2026-07-24 stub — 14,475 B, six sections, no act bands, no inline diagram — quoting an
estate of "12 pixi envs" and "4 duties" with no source for any number. It predates every one of
Steward's own epics (the four contract duties, the Marshal seam, the Canopy chain Epics 18–43,
the cutover under contract) and the family standard.

**Approach:** Author the poster repo-side to `spec-deck-family-currency/infographic-standard.md`
(Unifying Strategy = structure/acts/length; Warden = density/visual form; the doctor poster =
the finished Wave A shape) from `presentations/pyforge-steward/facts.yaml`, re-derived with
`deck-facts pyforge-steward` at the branch base. Every count, version, status and date is a
`<span data-fact="…">` mark whose text is the row's `value` or a `shown_as` literal; anything
without a row is left out or enumerated by name. Steward's own doctrine is the spine: provision /
deploy / keys / budget as the four contract duties, the registered duty set (sync, workspace,
upgrade, suite, the bootstrap family, restore, revoke), the nine ADs (wrap never reimplement,
one chokepoint, age at rest, reconcile don't remember, exit-code sole ownership), DutyResult as
frozen evidence, and the Canopy — `src/platform/`, one chrome / session / grammar / event
backbone / query plane — as Steward's flagship chain. Render headless to a full-page PNG at
1240 px, look at every tile, fix clipping/overlap, record the measurements in the deck README
ledger with the Design etag `PENDING-PUSH`.

## Boundaries & Constraints

**Always:**
- Touch only `presentations/pyforge-steward/{project/PyForge Steward Infographic standalone.html,
  facts.yaml, README.md}` plus this spec.
- Modernist tokens inlined in `<head>`; only the Google Fonts `<link>` is remote; no `<x-dc>`
  wrapper, no `support.js`, no scripts, no raster images; `.tag{display:inline-block}`.
- Six full-bleed act bands in arc order; ≥ 18 continuously numbered sections; ≥ 3 inline
  `<svg>` (viewBox 1128 wide, Archivo text, ink/accent/light/tint palette, `<marker>` arrows,
  labels inside their boxes); ≥ 3 tables; ≥ 90,000 bytes; full cast cards for all eight stations.
- Facts from `facts.yaml` only; never hand-edit `facts.yaml`; dates only from the `dream_log_*`
  and `tree_commit_date` rows (`poster_last_commit_date` is not printed); other stations'
  progress only from `<station>_stories_done_total` / `_epics_done_total` rows; no two-part or
  third-party versions; exit codes in their own table cells, never slash-adjacent.

**Never:**
- Never edit the Spec folder, `pixi.toml`, `docs/`, `scripts/`, the sprint ledgers or
  `scripts/.spec-surface-baseline.json` (operator reconciles).
- Never run `scripts/bmad-switch`; never restrict size at authoring time; never invent a fact
  row; never merge the PR.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fact check | `deck-facts pyforge-steward --check` on the rebuilt poster | `0 unmarked, 0 mismatch`; `unshown` may be non-zero | exit 0 always (advisory); iterate until clean |
| A wanted number has no row | the Canopy's CAP count, its realization-log dates, the five-tier `n/n`, the duty count, plugin count, third-party versions | omitted, or entities enumerated by name (the Canopy table lists canopy:CAP-1..canopy:CAP-19 as rows; the duty table lists every duty) | — |
| Exit codes in prose | `0 · 1 · 2 · 3 · 70 · 130` | one code per table cell as a code literal, never `n/n` adjacent (the sweep would read `0/1` as a fraction) | — |
| Render | Playwright Chromium, viewport 1240 × 900, `networkidle` + fonts settled, full page in ~2500 px tiles | PNG with no clipped, overlapping or blank region; height recorded | tile to the full-page PNG's real height, not only `scrollHeight` |
| Spec-surface | `python -m pyforge.doctor.sources spec-surface` | drift-presumed lines only for this story's files against `spec-deck-family-currency` | anything else reported, not fixed |

</intent-contract>

## Tasks & Acceptance

**Execution:** hand-authored 2026-09-13 in worktree `lr-wa-steward` on branch
`herald/20-9-pyforge-steward-poster` from `origin/main` `fbefe6eea6` (Wave A, one of four
parallel worktree agents; physical paths, no `bmad-switch`; repo scripts run with the main
checkout's interpreters from the worktree root).

**Acceptance Criteria:** poster meets every floor in `infographic-standard.md`; `--check`
reports `0 unmarked, 0 mismatch`; full-page PNG reviewed with no clipped/overlapping/blank
region; README ledger carries measured values, `PENDING-PUSH` etag, render date, page height
and "standalone ahead"; PR carries the `maintenance` label and touches only this deck's folder
plus this spec.

## Auto Run Result

**Summary:** Rewrote the poster as a 23-numbered-section, six-act page (masthead · hero ·
Act I problem / four-duty contract grid + table / estate topology SVG / the Canopy's five doors +
CAP-1..19 table · Act II eight full cast cards with ledger chips, the registered-duty table,
persona + skills · Act III credential-journey table, three-flows SVG, autonomy-gradient SVG,
phase × persona × skills table, relay SVG · Act IV nine CLI cards, the nine-AD doctrine band,
stack table, which-tool-when, escalation + exit-code table · Act V leaders, the deployed
estate / air-gap, seams · Act VI proof (CAP table + fleet table), the seed (two sourced dates,
the rest labelled by epic range), now/next/later · creed band). `deck-facts pyforge-steward`
refreshed `facts.yaml` (tree `fbefe6eea6`, 39 rows). README ledger section appended.

**Measurements:** 163,529 B · 24 `<section` (23 numbered + creed) · 6 acts (ACT I..VI) ·
4 `<svg` · 10 `<table` · 83 `data-fact` marks · page 25069 px full-page PNG at 1240 px wide
(DOM `scrollHeight` 24899 px) · 0 scripts, 0 raster images, 0 `<x-dc>`, 0 `support.js`.

**`--check` summary:** `pyforge-steward: 0 unmarked, 0 mismatch, 0 drifted, 0 unsourced,
1 unshown; facts 83/83` (the unshown row is `poster_last_commit_date`, not printed by rule).

**Visual QA:** first render (24893 px) showed six defects — the flows SVG's "ACT · ONLY WHEN
WARRANTED" header colliding with "PROVE" and three box captions overflowing; the gradient
SVG's centre label colliding with the right label, the "Mutate on ask" captions crossing the
dashed line, and the rightmost rung clipping at the viewBox edge; the relay SVG's two
doubled-station boxes a hair too tight; the §17 tint's `flex-direction:column` splitting every
inline `<span class="code">` onto its own line; the §06 Chain column wrapping "CAP-3"
mid-token; and the creed footer cut because the tile loop stopped at `scrollHeight` while the
full-page PNG is 170 px taller. All fixed and re-rendered; the five affected tiles re-inspected
clean and the final tile recaptured to the PNG's real height.

**Left out for lack of a fact row:** the Canopy Spec's capability count and every
realization-log date of `docs/dreams/pyforge-unifying-strategy.md` (only
`docs/dreams/pyforge-steward.md`'s one entry, `2026-07-23`, has a row), the five-tier
`40/40` figure, the registered-duty count (enumerated by name instead), the deploy-profile
plugin count (named instead), all two-part and third-party versions (interpreter floor, Django,
PostgreSQL, Redis, MCP SDK, Liquibase), test counts (`--with-tests` not run), and
`poster_last_commit_date` by rule. Exit codes appear as code literals in their own cells.

**Verification:** `deck-facts pyforge-steward --check` clean; Playwright full-page PNG at
`.herald/deck-qa/pyforge-steward/standalone.png` plus ten tiles reviewed; tag balance verified
with `html.parser` (no errors, nothing unclosed); `spec-surface` verdict recorded in the PR body.
