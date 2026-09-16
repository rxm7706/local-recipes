---
title: Factory console — the whole pipeline on one page
type: dream
owner: marshal
status: archived
archived-reason: absorbed
---

> **Consolidated into [[pyforge-marshal]]** on 2026-09-16 (one-chain-per-station CAP-8 pilot; folded from `factory-console`).

> **Narrative consolidated 2026-08-02 (dream-level only).** This Dream's narrative now lives
> in [`docs/dreams/pyforge-marshal.md`](pyforge-marshal.md) under "Kept separate on purpose."
> **Planning superseded 2026-08-24:** `spec-factory-console` is retired in favor of steward
> `spec-pyforge-unifying-strategy` CAP-2 (Lane 1 Wagtail front door). The generator under
> `docs/dashboard/` remains until steward Story 30.2; Kedro-Viz (`docs/dashboard/kedro-viz/**`)
> is atlas-owned and out of scope for retirement. Companions `console-contract.md` and
> `drill-evidence.md` remain historical references for the generator until deletion.

# Factory console — the whole pipeline on one page

## The Dream

One public page where the entire "Dream to Code" factory is legible at a
glance: **every Dream and where it sits in the lifecycle**
(seeded → in-deck → in-spec → realized), every build program's epic/story
progress live from `main`, the in-flight story's clock, and the deliveries as
they land. The console is how a human governs *intent* without reading logs —
[[pyforge-marshal]]'s "every run stays visible" doctrine given a front door,
and (in the persona ideal) the stage from which Herald proclaims.

Nothing on the console is hand-maintained: sprint state derives from
`sprint-status.yaml` locally and from `main`'s commit subjects in CI; Dream
state derives from `docs/dreams/*.md` frontmatter. If the repo moved, the
console already knows.

## What is real

- **The program console** — `docs/dashboard/` (index.html + data.js +
  generate.py), published on **GitHub Pages**
  (https://rxm7706.github.io/local-recipes/) by a workflow that uploads *only*
  `docs/dashboard/` (the repo is private; the page is public — scope is a
  security boundary, never widen it without re-checking).
- **Two-source refresh** — `dashboard-gen` locally (richest: done/active/
  gated/pending from Tier-3 sprint files); `--source git` at Pages deploy time
  (derives DONE from bmad-loop merge subjects; upgrade-only, never downgrades).
- **The Dreamscape board** — every `docs/dreams/*.md` scanned at generate
  time; the board renders each Dream in its lifecycle stage, doubling as the
  frontmatter-status detector the drift-checker never had.

## The frontier

- Per-Dream drill-through: link a Dream to its deck, spec folder, and BMAD
  project row (the no-straggler policy, made visible).
- Delivery feed: notables/releases marshalled onto the page (today they live
  in commit history and CHANGELOGs).
- Fleet health strip from [[pyforge-doctor]]; run telemetry (attempt counts,
  gate outcomes) from [[pyforge-marshal]].

## Kinships

[[pyforge-marshal]] (visibility doctrine — the console is its ledger) ·
[[pyforge-steward]] (owns the Pages deployment surface) ·
[[pyforge-charter]] (the pipeline the console makes legible) ·
[[modernist-identity]] (a candidate restyle; today the console has its own
mono/panel language).

## Realization log

- **2026-08-24** — `spec-factory-console` superseded by steward Canopy CAP-2; Wagtail Lane 1
  replaces the static Guildhall as the estate front door (generator until steward 30.2).

- **2026-08-09** — Reopened for the fleet roll-up. Five stations ran in parallel
  overnight and the operator's first question was one the board could not answer:
  *how much is done, how much is left, and is anything waiting on me?* The board
  had the per-epic story lists all along but no total, and — worse — its own
  story states are `done`/`active`/`pending` only, so a BLOCKED story is
  indistinguishable from one merely not started. Six stories that will never run
  looked exactly like 119 that will. Split deliberately: the tracked half
  (done/total/blocked, roll-up) renders on Pages, the live half (run state,
  projection, ATTENTION) stays local, because it derives from tmux and
  `~/.bmad-loops` and CI has neither — publishing it would publish a number the
  deploy cannot measure.

- **2026-07** — Warden+Atlas program console built and published on Pages
  during the bmad-loop runs; `--source git` auto-refresh added so the public
  page tracks `main` hands-off.
- **2026-07-23** — retro-seeded as a Dream (the console predates the
  Dream-first model); Dreamscape lifecycle board added the same day —
  the console now lists every Dream and its stage.

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — Status kept `realized` (in effect
  via Lane 1); **the governing Spec's `surface:` no longer describes its own files.**
  `spec-factory-console` is `superseded` yet still governs two paths whose meaning changed under it:
  `docs/dashboard/index.html` is now a **14-line "console moved" stub** since steward Story 30.2, and
  `scripts/fleet_scan.py` is a **parser library only** — the `data.js` write CLI is retired
  (`fleet_scan.py:6`, `:93`; `main()` returns 2 at `:3505-3511`) and `docs/dashboard/data.js` is gone
  from disk. **Cross-station:** steward Cutover **Story 44.1** requires 100 % of tracked files to
  resolve to `stays` / `dies` / a destination, and both of these currently resolve only to a
  superseded Spec whose surface no longer describes them. A destination decision for both is owed to
  44.1 — and it is the same decision [[dashboard-velocity-captures-hand-driven-work]] needs for
  `scan_timing`'s orphaned CAP-1..3. Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.
