---
title: 'Warden poster rebuilt to the standard from its ledger'
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

**Problem:** `presentations/pyforge-warden/project/Warden Infographic standalone.html` was the
operator-designated best poster in the family — 411,764 B, 18 sections, the density and
visual-form reference — but it had no act bands, every stat was a July-2026 planning claim
(`5 epics · 20 stories`, `Status — In progress · Planning complete`, license / currency /
baseline / fix-PRs still "next"), and none of its numbers cited a source. Measured at the
branch base it was also not the plain HTML the standard requires: a Claude Design bundle whose
real page content (192,472 B) sat JSON-encoded inside a `__bundler/template` script tag beside
~205 KB of base64 fonts and Design runtime scripts, wrapped in `<x-dc>`, with tables as
`sc-raw-*` pseudo-elements and icon glyphs whose `viewBox` had been mangled.

**Approach:** Keep the form that made it the reference — its cast-card and section richness,
its div-built diagrams, its fourteen icon glyphs (re-labelled where a stat changed, `viewBox`
restored), its 70-row integration matrix in the original inline-badge style — and (a)
restructure it under the six-act arc with full-bleed act bands, renumbering sections
mechanically; (b) re-derive every count, version, status and date from
`presentations/pyforge-warden/facts.yaml` (re-derived with `deck-facts pyforge-warden` at the
branch base) as `data-fact` marks whose text is the row's `value` or a `shown_as` literal; (c)
add the standard's sections Warden lacked — the eight full cast cards with ledger chips, the
engines-and-feeds table in the sub-agent slot, the persona/skills map, the phase × persona ×
skills table, the autonomy gradient, the relay, the doctrine band, the stack table,
escalation and the ledger, enterprise and air-gap, proof, the dated seed, now/next/later and
the creed; (d) add four genuine 1128-wide SVG diagrams (spine topology, seven-rungs-to-four-exits
ladder, autonomy gradient, relay); (e) never shrink it. Anything without a fact row is left
out. Render headless at 1240 px, look at every 2500 px tile, fix clipping and overlap, record
the measurements in the deck README ledger with the Design etag `PENDING-PUSH`.

## Boundaries & Constraints

**Always:**
- Touch only `presentations/pyforge-warden/{project/Warden Infographic standalone.html,
  facts.yaml, README.md}` plus this spec; keep the exact poster filename.
- Modernist tokens inlined in `<head>`; only the Google Fonts `<link>` is remote; no
  `<x-dc>` wrapper, no `support.js`, no scripts, no raster images; `.tag{display:inline-block}`.
- Six full-bleed act bands in arc order; ≥ 18 continuously numbered sections; ≥ 3 inline
  `<svg>` diagrams (viewBox 1128 wide, Archivo text, ink/accent/light/tint palette, `<marker>`
  arrows); ≥ 3 real tables; ≥ 90,000 bytes; larger than the poster it replaces; full cast cards
  for all eight stations.
- Facts from `facts.yaml` only; never hand-edit `facts.yaml`; dates only from the `dream_log_*`
  and `tree_commit_date` rows (never `poster_last_commit_date`); no two-part or third-party
  versions; exit codes as separate code literals or in their own table cells.

**Never:**
- Never edit the Spec folder, `pixi.toml`, `docs/`, `scripts/`, sprint ledgers or
  `scripts/.spec-surface-baseline.json` (operator reconciles).
- Never run `scripts/bmad-switch`; never restrict size at authoring time; never invent a fact
  row; never merge the PR; never touch another deck's folder.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fact check | `deck-facts pyforge-warden --check` on the rebuilt poster | `0 unmarked, 0 mismatch`; `unshown` may be non-zero | exit 0 always (advisory); iterate until clean |
| A wanted number has no row | population figures, `20k+` fleet, `14 days`, `~1,950` corpus, `31/31`, `43/43`, test counts | omitted from the poster or written as prose without a literal | — |
| Adjacent code literals | `0600` / `0700` temp-file modes | written as "file mode … and directory mode …" so the sweep never reads a fraction | caught by the first `--check` (`1 unmarked`), fixed |
| Bundle vs content bytes | the 411,764 B reference is a Design bundle | README ledger records the honest content comparison (192,472 → 295,079 B) | — |
| Render | Playwright Chromium, viewport 1240 × 900, full page in 2500 px tiles | PNG with no clipped, overlapping or blank region; height recorded | fall back to headless Chrome if Playwright missing |
| Spec-surface | `python -m pyforge.doctor.sources spec-surface` | drift-presumed lines only for this story's files against `spec-deck-family-currency` | anything else reported, not fixed |

</intent-contract>

## Tasks & Acceptance

**Execution:** hand-authored 2026-09-13 in worktree `lr-wa-warden` on branch
`herald/20-10-warden-poster` from `origin/main` `fbefe6eea6` (Wave A, one of four parallel
worktree agents; physical paths, no `bmad-switch`; the worktree has no pixi envs, so the main
checkout's `local-recipes` and `pyforge-herald` interpreters ran the repo scripts from the
worktree root).

**Acceptance Criteria:** poster meets every floor in `infographic-standard.md` and is larger
than the content it replaces; `--check` reports `0 unmarked, 0 mismatch`; full-page PNG
reviewed with no clipped/overlapping/blank region; README ledger carries measured values,
`PENDING-PUSH` etag, render date, page height, "standalone ahead" and the note that this file
remains the family's density/visual reference; PR carries the `maintenance` label and touches
only this deck's folder plus this spec.

## Auto Run Result

**Summary:** Unpacked the Design bundle to recover the 192,472 B of real content, then rewrote
the poster as plain standalone HTML: masthead (kicker, `Warden` display brand, spec slug, thesis,
six tag chips, five-cell fact strip) · hero with the six-axis strip (four `live`, two `vision`) ·
Act I problem tiles / two ecosystems + axis grid / six formats + lockfiles + construct-matrix
table / the spine SVG + identity predicate / twelve-CAP grid · Act II eight full cast cards with
ledger chips, engines-and-feeds table, persona/skills map · Act III five-step pipeline, three
path columns, lattice ladder + seven-rungs-to-four-exits SVG + suppression table, autonomy
gradient SVG, phase × persona × skills table, relay SVG · Act IV `warden scan` cards with every
flag grouped, outputs, nine-line doctrine band, workstation mode, stack table, which-tool-when,
escalation with exit-code and error-kind routing tables · Act V scale, three rings, eight leader
cards, control-plane grid, OSS policy cards, air-gap, 70-row integration matrix + standards +
seams · Act VI proof (bignums, twelve-row CAP table, fleet table), dated seed, now/next/later
(eight shipped, four next, eight later cards), on-ramp · creed band. `deck-facts pyforge-warden`
wrote `facts.yaml` at tree `fbefe6eea6` (41 rows). README ledger section appended.

**Measurements:** 295,079 B · 33 `<section` (32 numbered + creed) · 6 acts (ACT I..VI) ·
26 `<svg` (4 diagrams + 22 icon glyphs) · 11 `<table` · 91 `data-fact` marks · page 34715 px
at 1240 px wide · 0 scripts, 0 `<x-dc>`, 0 raster images. Content grew 192,472 → 295,079 B;
the 411,764 B bundle figure is not comparable (base64 fonts and Design runtime).

**`--check` summary:** `pyforge-warden: 0 unmarked, 0 mismatch, 0 drifted, 0 unsourced,
1 unshown; facts 91/91` — the `unshown` row is `poster_last_commit_date`, not printed by rule.

**Visual QA:** first render (34681 px) showed five defects — the autonomy-gradient header
labels colliding and its last rung overflowing the right edge, the ladder's second caption line
clipped, six spine-rail sub-labels overflowing their 250 px boxes, the right-rail header clipped,
and the masthead CLI cell wrapping mid-flag; all fixed (rails widened to 270 px, captions split,
labels shortened, cell restructured) and re-rendered (34715 px); every tile and the four
repaired regions re-inspected clean.

**Left out for lack of a fact row:** `~850K packages` / `~30K feedstocks` / the `20% / 80%`
footprint split, the `20k+` fleet target, the `14 days` waiver default, `5 epics · 20 stories`,
`Python 3.12+` and every two-part or third-party version (CycloneDX spec, report schema, deptry
and osv-scanner ranges), `31/31` / `43/43` story counts, the `~1,950` corpus size, test counts
(`--with-tests` not run), and the retired duplicate Dream's creation date. The old roadmap's
`v1` / `v1.x` / `v2` labels were replaced by shipped / next / later per the Spec.

**Verification:** `deck-facts pyforge-warden --check` clean; Playwright full-page PNG and
2500 px tiles at `.herald/deck-qa/pyforge-warden/` reviewed; tag balance verified with
`html.parser` (no stray or unclosed tags); `spec-surface` verdict recorded in the PR body.
