---
title: Factory console — the whole pipeline on one page
type: dream
owner: marshal
status: archived
archived-reason: absorbed
---

> **Narrative consolidated 2026-08-02 (dream-level only).** This Dream's narrative now lives
> in [`docs/dreams/pyforge-marshal.md`](pyforge-marshal.md) under "Kept separate on purpose."
> **Its downstream chain stays fully live and untouched**: `spec-factory-console` (companions
> `console-contract.md`, `drill-evidence.md`) remains the current, binding reference for this
> Dream's still-unbuilt frontier (per-Dream drill-through, a delivery/notables feed, a
> fleet-health strip). No PRD exists for it yet — only this top-level Dream file consolidates;
> nothing downstream was merged, retired, or reworded.

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

- **2026-07** — Warden+Atlas program console built and published on Pages
  during the bmad-loop runs; `--source git` auto-refresh added so the public
  page tracks `main` hands-off.
- **2026-07-23** — retro-seeded as a Dream (the console predates the
  Dream-first model); Dreamscape lifecycle board added the same day —
  the console now lists every Dream and its stage.
