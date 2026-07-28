---
spec: factory-console
status: shipped
owner-dream: docs/dreams/factory-console.md
program: regenerable-factory (Wave 2)
surface:
  - docs/dashboard/**
surface-drift-exclude:
  - docs/dashboard/data.js   # generated on every dashboard-gen run (regenerate-at-will)
companions:
  - console-contract.md
sources:
  - ../../../../../../docs/dreams/factory-console.md
open_questions: []
---

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

`pixi run -e local-recipes dashboard-gen` (and `--source git`) regenerate
`data.js` with correct counts and warnings; the Pages deploy publishes only
`docs/dashboard/`; the regeneration drill (spec-regenerable-factory CAP-4)
rebuilds `generate.py` from `console-contract.md` alone with equivalent
output.
