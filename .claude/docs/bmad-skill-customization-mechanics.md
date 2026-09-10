# BMAD skill customization & step-file override mechanics

Captured live 2026-09-10 by fetching BMAD's official sources directly (not
inferred from this repo's own prior analysis alone) — motivated by marshal's
token-economy effort needing to know, definitively, whether wiring a new
context-layer reference into `bmad-build-auto`'s `step-01-clarify-and-route.md`
can be expressed through a sanctioned BMAD customization surface, or whether
it requires this repo's own in-place-edit-and-govern pattern.

**Sources fetched** (WebFetch, 2026-09-10 — each summarized by a small model
from the live page, not a raw dump; re-fetch to verify currency, since
`llms-full.txt` was discontinued by BMAD-METHOD 6.12.0 and there is no
living single-file source to diff against anymore, per `CLAUDE.md` and
`.claude/docs/bmad-method-llms-full.txt`'s own header):

- `https://docs.bmad-method.org/customize/customize-bmad/` (fetched twice, two different questions)
- `https://docs.bmad-method.org/` (site structure map)
- `https://docs.bmad-method.org/customize/add-modules/`
- `https://github.com/bmad-code-org/BMAD-METHOD` (README)
- `https://bmadcode.com/`

## The finding, stated plainly

**There is no sanctioned BMAD mechanism to extend or patch an existing
installed skill's step-file prose content.** Three independent surfaces were
checked and all three confirm this from different angles:

### 1. The override-layer (`_bmad/custom/<skill>.toml` / `.user.toml`)

Schema-bound, structured-field-only. Each customizable skill ships its own
`customize.toml` as the schema — "read it to see what is customizable." What
it covers:

- Agent persona fields: role, identity statement, communication style,
  principles, icon, menu, persistent facts, activation hooks
- Workflow configuration: output paths, templates, toggles
- Array fields keyed for merge (`[[agent.menu]]`, `[[workflow.review_layers]]`)
- `activation_steps_prepend` / `activation_steps_append` — inject something
  *around* a workflow's run, not *into* a specific numbered instruction item

An override **deep-merges structured tables and arrays** — it does not
replace file content, and "an override cannot delete a base item."

**Priority order** (highest wins): user (`_bmad/custom/<skill>.user.toml`,
usually gitignored) → team (`_bmad/custom/<skill>.toml`, committed) → the
skill's own shipped `customize.toml` defaults (overwritten on every upgrade).
`_bmad/custom/` itself starts empty and the installer/upgrader never touches
it — so anything placed there really is upgrade-safe, but only for what the
schema exposes.

Two customization categories exist under this layer:
1. **Per-skill overrides** (agents & workflows) — `_bmad/custom/<skill>.toml`
2. **Central configuration** — org-wide settings, install answers, the
   global agent "roster" other skills (e.g. party mode) read

### 2. "Forking a skill" (BMAD's own suggested path when step prose must change)

The docs mention forking only once, as a last resort for restructuring an
array further than override merging allows — and provide **no formal fork
mechanism**: no directory convention, no manifest entry, no update-aware
tracking. Installed skill folders are documented as strictly read-only:
*"Never edit it; updates overwrite it."* A fork is described in the docs'
own words as *"informal, self-managed... without built-in safeguards."*

### 3. The module system (`Customize and Extend > Add Modules`)

Purely additive, purely isolated. A custom module installs as a
self-contained new skill/workflow set alongside official modules in
`_bmad/` — it has **no hook into an existing installed skill's step files**.
To get different behavior from an existing skill, BMAD's own guidance is to
build an entirely separate new skill via BMad Builder, not modify the
existing one. The architecture prioritizes isolation over integration by
design.

## What this means for this repo

This repo's own pattern — confirmed correct, not merely "the best we found"
— for the class of change "add/change prose inside an installer-owned step
file": **spec-surface governance + Story 14.8's automated reapply**, per
`_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-method-core-upgrade/customization-inventory.md`
row C5:

1. Edit the installer-owned file directly (e.g.
   `.claude/skills/bmad-build-auto/step-01-clarify-and-route.md`).
2. Name that file in an **owning marshal spec's `surface:` list** (already
   true today for all eleven files this repo customizes this way — Story
   31.4 widened the pool from 7 to 11 and closed the "4 ungoverned" gap).
3. Record the edit in that spec's own `.memlog.md` — `spec-surface-check`
   (run every session via `pixi run -e local-recipes detectors`) reds
   `drift` on any planted edit to a governed file with no matching memlog
   line, and reports `uncovered` for a customized file named in no spec at
   all.
4. Story 14.8 / CAP-8 (steward, delivered 2026-09-06) is the real safety
   net for the *next BMAD update*, not spec-surface: `build_preflight_report`
   does a marker-free byte-diff scan against the cached upstream package,
   finding every live customization (verified live against a real 6.12.0
   install — found all 7 at the time, now widened to 11), and
   `apply_bmad_core_upgrade` **3-way-merges each one after the core
   installer runs** — a clean customization re-applies automatically, a
   real conflict leaves the installer's bytes untouched and writes a
   `.customization-conflict` sibling file rather than silently dropping the
   edit or silently keeping stale content.

Nothing here is guesswork carried over from before this research pass — the
prior state (before Story 14.8) genuinely lost customizations silently on
6.12.0's install (recovered by hand, commit `0ee58ca58c`, "re-apply the
seven in-repo skill customizations 6.12 regenerated away"). BMAD provides
no equivalent of its own; this repo built one because it had to.

## How to refresh this document

Re-run the same five `WebFetch` calls against the URLs listed under
**Sources fetched** above, diff the summaries against this file's own
claims, and update both this file and
`customization-inventory.md`'s Addendum if BMAD has shipped a real
extension/hook mechanism since 2026-09-10 (watch specifically for a future
`docs.bmad-method.org/customize/` page whose title suggests step-level
overrides, or a module-system change that adds a hook point into an
existing skill rather than only new isolated skills).
