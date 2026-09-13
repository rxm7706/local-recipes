---
title: 'PyForge Genesis poster rebuilt to the standard from its ledger'
type: 'feature'
created: '2026-09-13'
status: 'done'
baseline_revision: bc8ae85dd1
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

**Problem:** `presentations/pyforge-genesis/project/PyForge Genesis Infographic standalone.html`
was the 2026-07-25 poster — 47,877 B, nine sections, no act bands, no inline diagram — and none
of its numbers cited a source. It still described the pre-2026-07-25 world: a "PYFORGE CREW"
kicker, "25 Dreams on the board", "9 spec kernels", "32/32 Atlas stories", "27/31 Warden
stories", a six-axis Warden billed without its vision-tier caveat, and a Guildhall model that
predates three constitutional amendments. It is the **Guild-wide / Charter deck** — the master
vision deck for the whole PyForge Guild, not one station — so its staleness is the family's
most visible.

**Approach:** Author the poster repo-side to `spec-deck-family-currency/infographic-standard.md`
(Unifying Strategy = structure/acts/length; Warden = density/visual form; the finished Wave A
Doctor and Marshal posters = the worked shape) from `presentations/pyforge-genesis/facts.yaml`,
re-derived with `deck-facts pyforge-genesis` at the branch base. Every count, version, status
and date is a `<span data-fact="…">` mark whose text is the row's `value` or a `shown_as`
literal; anything without a row is enumerated by name instead of printed as a number. The
Charter is the spine: the Dream-to-Code tiers, the seven-noun Lexicon, the doctrine, the eight
Smiths as full cast cards, the branding law, the autonomy gradient, the Master Pipeline relay,
the seed (greenfield/brownfield), the fleet, and the Dream tier by status. Render headless to a
full-page PNG at 1240 px, look at it in tiles, fix clipping/overlap, record the measurements in
the deck README ledger with the Design etag `PENDING-PUSH`.

**Grounding sources (tracked only):** `docs/dreams/pyforge-charter.md`,
`docs/governance/spec-pyforge-charter/SPEC.md`, `archive/docs/governance/spec-pyforge-genesis/SPEC.md`,
`docs/governance/guild-roster.json`, `docs/dreams/README.md`, `AGENTS.md`,
`docs/dreams/agentic-sdlc-autonomy.md`, `docs/dreams/pyforge-unifying-strategy.md`, and the
prior poster's still-true prose. No number, version, status or date from any of them ships
without a `facts.yaml` row.

## Boundaries & Constraints

**Always:**
- Touch only `presentations/pyforge-genesis/{project/PyForge Genesis Infographic standalone.html,
  facts.yaml, README.md}` plus this spec.
- Modernist tokens inlined in `<head>`; only the Google Fonts `<link>` is remote; no `<x-dc>`
  wrapper, no `support.js`, no scripts, no raster images; `.tag{display:inline-block}` (not
  `inline-flex`, which swallows whitespace around marked spans and can fuse fact tokens).
- Six full-bleed act bands in arc order; ≥ 18 continuously numbered sections; ≥ 3 inline
  `<svg>` (viewBox 1128 wide, Archivo text, ink `#201e1d` / accent `#ec3013` / light `#f3f2f2`
  / tint `#fbe4de`, `<marker>` arrows, labels inside their boxes); ≥ 3 tables; ≥ 90,000 bytes;
  full cast cards for all eight stations with role, motto, paragraph, CLI verbs and ledger chips.
- Facts from `facts.yaml` only; never hand-edit `facts.yaml`; never print
  `poster_last_commit_date`; never print a two-part or third-party version (no row exists).

**Never:**
- Never edit the Spec folder, `pixi.toml`, `docs/`, `scripts/`, the sprint ledgers or
  `scripts/.spec-surface-baseline.json` (operator reconciles).
- Never run `scripts/bmad-switch`; never touch the primary checkout or another deck's folder;
  never restrict size at authoring time; never invent a fact row; never merge the PR.
- Never use "Canopy" as a product name — retired by `pyforge-unifying-strategy`'s 2026-08-24
  grounding; the enterprise/air-gap section says "the estate" instead.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fact check | `deck-facts pyforge-genesis --check` on the rebuilt poster | `0 unmarked, 0 mismatch`; `unshown` may be non-zero | exit 0 always (advisory); iterate until clean |
| The ledger has no status/date rows | genesis resolves no `spec_status`/`dream_status`/`dream_log_*` | the poster prints **no** date but `tree_commit_date`, and no Dream/Spec status word; history is narrated by name | — |
| A wanted count has no row | the Charter Spec's capabilities, the seven Lexicon nouns, the L1–L5 rungs | enumerated by name in a table; the count itself is never printed | — |
| `pitched` Dream status | no `dreams_pitched` row derived at this tree | table cell reads "no row" with the reason, never a guessed zero | — |
| Tokens inside SVG `<text>` | the sweep parses SVG text as visible text | no `n/n`, `x.y.z` or `YYYY-MM-DD` literal in any SVG label | — |
| Two rows share a value | `cfe_skill_version` and `groundtruth_skill_version` are both `8.90.5` | both marked, in different sections; each resolves against its own id | — |
| Render | Playwright Chromium, viewport 1240 × 900, full page, read in 2500 px tiles | PNG with no clipped, overlapping or blank region; height recorded | warm-up screenshot first so font metrics settle before `scrollHeight` |
| Spec-surface | `python -m pyforge.doctor.sources spec-surface` | drift-presumed lines only for this story's files | anything gating reported, not fixed |

</intent-contract>

## Tasks & Acceptance

**Execution:** hand-authored 2026-09-13 in worktree `lr-wb-genesis` on branch
`herald/20-11-pyforge-genesis-poster` from `origin/main` `bc8ae85dd1` (Wave B; physical paths,
no `bmad-switch`, primary checkout untouched).

**Acceptance Criteria:** poster meets every floor in `infographic-standard.md`; `--check`
reports `0 unmarked, 0 mismatch`; full-page PNG reviewed with no clipped/overlapping/blank
region; README ledger carries measured values against the floors, the `PENDING-PUSH` etag, the
render date, the page height and "standalone ahead"; PR carries the `maintenance` label and
touches only this deck's folder plus this spec.

## Auto Run Result

**Summary:** Rewrote the poster as a 27-numbered-section, six-act page. Masthead (kicker · `PyForge
Genesis` · slug line · thesis · six tag chips · five-cell stat strip, every stat marked) · hero
strip (Charter / Spec / Stations / Guildhall) · **Act I** the problem · the Dream-to-Code tiers
(SVG) · the Lexicon · the Charter's doctrine · the constitutive contract at a glance · **Act II**
the eight Smiths as full cast cards · the topology (SVG) · the branding law · the two persona
layers · the armory (+ a five-cell ground-truth strip) · **Act III** one Dream's journey · three
ways work flows · the autonomy gradient (SVG) · phase × persona × skills · the Master Pipeline
relay (SVG) · **Act IV** what shipped · the never-false-green doctrine band · the stack · which
station when · escalation and the ledgers · **Act V** what each leader gets · enterprise and
air-gap · integration seams · **Act VI** proof (fleet stats + per-station table) · the seed ·
the Dream tier by status · now/next/later · creed band. `deck-facts pyforge-genesis` refreshed
`facts.yaml` at tree `bc8ae85dd1` (36 rows). README ledger section appended.

**Measurements:** 142,316 B · 28 `<section` (27 numbered + creed) · 6 acts (ACT I..VI) ·
4 `<svg` · 14 `<table` · 94 `data-fact` marks · page 24046 px at 1240 px wide, `scrollWidth`
1240 (no horizontal overflow) · 0 scripts, 0 raster images, 0 `<x-dc>`. The deepest poster in
the family (Doctor 135,606 B; Unifying Strategy 128,783 B) — as the master deck should be.

**`--check` summary:** `pyforge-genesis: 0 unmarked, 0 mismatch, 0 drifted, 0 unsourced,
1 unshown; facts 94/94`. The single `unshown` row is `poster_last_commit_date`, which the story
forbids printing.

**Visual QA:** first render (24081 px) showed four defects — the autonomy-gradient SVG's
"TODAY'S PRODUCTION CEILING" label colliding with "REACHED BY MOVING THE BOUNDARY" and its L3
description running into L2's; the creed footer's two spans overlapping; the hero headline
breaking mid-hyphen at "Production-ready"; and a `↔` glyph Archivo lacks rendering as a double
hyphen. Re-laid out the gradient on separate bands, gave the footer `flex-wrap` + gap, widened
the headline to the full frame, and replaced the glyph with "Design-to-code". A fifth defect
found on re-inspection — the tier SVG's dashed Realization-log return path crossing the LAND
band's caption text — was fixed by insetting the band and routing the return leg orthogonally
down the left gutter. Final render 24046 px; all ten tiles re-inspected clean.

**Left out for lack of a fact row:** every date except `tree_commit_date` (the genesis ledger
resolves no `dream_log_*` rows, because the constitutive Dream is `pyforge-charter`, not
`pyforge-genesis`) — so the Charter's amendment history, the 2026-07-23 ownership audit, the
2026-08-08 genesis fold and the 2026-08-02 project dissolution are narrated by name and act
rather than dated; the Dream's and the Spec's `status:` words (no `dream_status` /
`spec_status` rows); the Charter Spec's capability count (no `spec_capabilities` row — the
eight are enumerated by name in §05 instead); the count of Lexicon nouns, of autonomy rungs and
of BMAD sub-agents (all enumerated, never counted); the Python floor and every two-part or
third-party version; `dreams_pitched` (no row derived at this tree — the table says so
explicitly rather than printing a zero). Per-station `package_version` and `cli_verbs` rows do
not exist for this deck either, so the cast cards name verbs without version strings.

**Re-base during the story:** `origin/main` advanced `0bfa4d44d3` → `bc8ae85dd1` mid-authoring
(eleven fleet stories and six Dreams landed, among them Story 20.14's own `deck-facts --refresh`).
Eight rows drifted: `dreams_total` 148→154, `dreams_specified` 44→50, `fleet_stories_done_total`
859/885→870/892, `fleet_epics_done_total` 184/191→190/197, `herald_stories_done_total` 73/81→78/82,
`scribe_stories_done_total` 27/27→33/33, `scribe_epics_done_total` 10/10→16/16, and
`poster_last_commit_date`. `deck-facts pyforge-genesis --refresh` rewrote the 28 stale marked
literals from the fresh ledger; one hand-counted piece of prose the refresh cannot see — "three
stations are complete on both rows" — was corrected to four (warden, mason, doctor, scribe). The
ledger was then re-derived on a clean tree so its `tree:` header records the branch base rather
than a dirty working copy, and the poster re-rendered and re-inspected.

**Verification:** `deck-facts pyforge-genesis --check` clean; Playwright full-page PNG at
`.herald/deck-qa/pyforge-genesis/standalone.png` plus ten 2500 px tiles reviewed by eye;
`python -m pyforge.doctor.sources spec-surface` verdict recorded in the PR body.
