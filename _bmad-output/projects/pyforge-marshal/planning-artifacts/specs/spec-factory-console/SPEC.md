---
spec: factory-console
status: superseded
updated: "2026-09-09"
superseded_by: _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md#cap-2--lane-1-is-cms-managed-and-it-is-the-only-front-door
owner-dream: docs/dreams/factory-console.md
program: regenerable-factory (Wave 2)
surface:
  - docs/dashboard/README.md
  - docs/dashboard/index.html
  - docs/dashboard/kedro-viz/**
  - scripts/fleet_scan.py
surface-drift-exclude:
  - docs/dashboard/kedro-viz/**   # generated wholesale by `kedro viz build` + viz-publish-stage (atlas 12-2, FR-62); CI republishes it on every push touching atlas pipelines, and the asset filenames are content-hashed, so per-file governance would red this detector on every legitimate rebuild. The GENERATOR is governed (pixi tasks viz-build/viz-publish-stage + tools/normalize_viz_build.py under spec-pyforge-atlas); the OUTPUT is not.
companions:
  - console-contract.md
sources:
  - ../../../../../../docs/dreams/factory-console.md
open_questions: []
---

> **Superseded 2026-08-24; generator deleted 2026-08-25 (steward Story 30.2).**
> Lane 1 Wagtail (steward `spec-pyforge-unifying-strategy` CAP-2) is
> the estate front door. The Guildhall `generate.py`, four pixi tasks, scheduled
> Pages regen, and `data.js` blob are **gone**. Operator surfaces: `/console/`.
> `docs/dashboard/kedro-viz/**` is atlas-owned publish output and remains.

# SPEC — factory console (program console + Dreamscape)

## Why

One public page where the whole "Dream to Code" pipeline is legible: every
Dream in its lifecycle stage, every build program's story progress, nothing
hand-maintained. Repo private, page public — the Pages workflow uploads ONLY
`docs/dashboard/`, and that scope is a security boundary.

## Capabilities

- **CAP-1 — local status sync.** Intent: refresh each project's per-story
  status in `data.js` from its Tier-3 `sprint-status.yaml` (full fidelity:
  done/active/gated/pending; may downgrade). Success: every mapped story
  reflects its sprint file; unmatched ids are reported, never silently
  dropped.
- **CAP-2 — hands-off CI refresh.** Intent: derive DONE-only story upgrades
  from `main`'s commit subjects at Pages deploy time (no bot commit-back);
  committed `data.js` is the floor — never downgraded. Success: a story
  flips done on the live site once its merge/story commit lands on `main`.
- **CAP-3 — Dreamscape scan.** Intent: rescan `docs/dreams/*.md` frontmatter
  (title/status/owner) into the data on every run, warning on unknown
  status or missing owner (the de-facto Dream frontmatter detector).
  Success: the board always shows all Dreams; a bad frontmatter edit is
  named in the run output.
- **CAP-4 — stable data contract.** Intent: `data.js` carries hand-curated
  narrative plus generated state; the generator mutates ONLY story statuses,
  the dreams list, and the snapshot timestamp. Success: any other field
  survives a regeneration byte-identical.

## Constraints

- Generator is stdlib-only Python (runs in bare CI). The exact behavioral
  contract (CLI, file formats, parse rules, regexes, output shape) is
  normative in `console-contract.md` — a rebuild from that companion alone
  must be behavior-equivalent (the CAP-4 regeneration drill).
- The render shell (`index.html`) is self-contained: no external assets,
  theme-aware, data read exclusively from `window.DASHBOARD_DATA`.

## Non-goals

- Replacing the official BMad Method UI (per-project live kanban); this is
  the curated cross-project committed view.
- Serving private content: Dream bodies, sprint files, and journals never
  enter `docs/dashboard/`.

## Success signal

Lane 1 `/console/` is the operator console. `retired-console-check` fails if
the Guildhall generator, `data.js`, or the four retired pixi tasks return.
Pages still publishes `docs/dashboard/` (Kedro-Viz + stub). The CAP-4
regeneration drill is historical — `generate.py` is gone.

## Surface no longer describes its files (2026-09-09)

This Spec is `superseded` but still governs two paths whose meaning changed **under** it:

- `docs/dashboard/index.html` — now a 14-line *"console moved"* stub, since steward Story 30.2.
- `scripts/fleet_scan.py` — a **parser library only**. The `data.js` write CLI is retired
  (`fleet_scan.py:6`, `:93`) and `main()` returns 2 at `:3505-3511`.

**CROSS-STATION:** steward Cutover Story 44.1 requires 100 % of tracked files to resolve to
stays / dies / a destination, and both of these currently resolve only to a superseded Spec whose
surface no longer describes them. **A destination decision for both is owed to 44.1 — routed to
steward.** Status stays `superseded`; nothing is re-homed here.
