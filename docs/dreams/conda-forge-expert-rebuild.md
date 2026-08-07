---
title: Rebuild conda-forge-expert as a Skill-Forge-authored skill, slice by slice
type: dream
owner: mason
status: dreamt
---

# Rebuild conda-forge-expert as a Skill-Forge-authored skill, slice by slice

## The Dream

`conda-forge-expert` — the ~41,410-LOC skill that has carried this repo's entire recipe
lifecycle (generate → validate → build → submit) since it began, encoding 106 gotchas and 10
hard constraints earned the hard way, one build failure at a time — gets rebuilt, not wrapped.
Not the whole thing at once, and not by hand: `skf-*` (Skill Forge, already installed in this
repo's `.claude/skills/`) does the compiling, slice by slice, along the skill's own existing
3-tier seams (recipe-authoring, atlas-intelligence, project-scanning), with `skf-campaign`
orchestrating the sequence and `skf-audit-skill` proving each slice is drift-free once it lands.

This explicitly reopens [[pyforge-mason]]'s D-1 ("wrap, never fork the craft") — but only for
CFE itself, not for Mason. Mason's own wrap decision doesn't need to change: `mason recipe`
shells out through `cfe.py` to whatever lives at the CFE root, and as long as this rebuild
preserves compatible entry points, Mason keeps working through the transition unmodified.
This is a standalone effort, motivated by the same underlying wish Mason's D-1 already weighed
and rejected once — and the user chose to reopen it anyway, with eyes open about why it was
rejected the first time.

**The precedent this Dream has to answer to, explicitly:** `pyforge-atlas` took the "extract
and re-implement" path once already, in this exact repo. 80 files / 14,461 src LOC + 110 files
/ 14,682 test LOC, 32 stories, PRs #58–#105 all merged — and the legacy `conda_forge_atlas.py`
(8,902 LOC) is *still the live runtime*. Every `build-cf-atlas` / `atlas-phase` /
`query-cf-atlas` task and every atlas MCP tool still shells out to the old path. Nothing routes
to `pyforge.atlas`. ~29,000 lines did not displace the original, because the rebuild had no
migration step — Mason's own D-1 rationale names this as reason #2 of three independent,
each-sufficient reasons not to rebuild CFE the same way.

This Dream exists specifically to not repeat that outcome: the user chose full scope (rebuild
all 30+ MCP tools and scripts, not a narrow pilot) but paired it with **hard cutover per
slice** — every rebuilt capability retires its old CFE path, redirects every caller (pixi
tasks, the MCP tool registration, Mason's own `cfe.py` port), in the *same* migration story
that builds it, never a separate future effort. That pairing is the whole bet: broad scope,
but no slice is allowed to become a second, unused ~29,000 lines.

## What it looks like when real

- CFE's existing 3-tier architecture (recipe-authoring, atlas-intelligence,
  project-scanning/MCP layer — see `.claude/skills/conda-forge-expert/SKILL.md`) is sliced
  into Skill-Forge-sized units, each with a Brief.
- `skf-analyze-source` run against the existing skill confirms or corrects the slicing before
  any Brief is written — the boundaries come from what's actually there, not a guess.
- Per slice: `skf-create-skill` compiles the replacement → a migration story in the *same*
  epic redirects every caller (pixi tasks, `.claude/tools/conda_forge_server.py`'s MCP tool
  registrations, Rule-1/Rule-2 references, Mason's `cfe.py` port) from the old path to the
  new one → the old code for that slice is removed or explicitly deprecated → `skf-audit-skill`
  confirms zero drift.
- `skf-campaign` tracks the whole multi-slice sequence with file-based state and resume, so
  the effort survives across sessions the way `bmad-loop` runs do for other stations.
- At the end: no `.claude/skills/conda-forge-expert/` code path is dead weight sitting next to
  a newer, unused replacement — every slice that shipped is the slice that's actually called.
  The 106 gotchas and 10 constraints are carried forward into the new skill's own briefs, not
  re-derived from scratch and not lost.
- Rule 1 (SKILL.md is authoritative) and Rule 2 (every conda-forge effort ends with a retro
  that improves the skill) continue to apply to whatever replaces CFE — this Dream does not
  reopen *those* rules, only the wrap-vs-build seam for CFE's own implementation.

## What is real

Nothing built yet. This is a `dreamt`-stage placeholder, captured at the moment the decision
to reopen D-1 was made explicitly, with the scope and cutover-discipline questions already
answered (see Realization log) — the next step is a Spec (`bmad-spec`), not code.

## Constraints

- **Hard cutover per slice, non-negotiable.** No slice's migration story may be deferred to
  "later" — this is the one discipline atlas's rebuild lacked, and it is the entire reason
  this Dream is structured the way it is.
- **Mason's own D-1 is untouched.** `mason recipe`'s wrap-by-subprocess design does not change;
  this rebuild only changes what's *at* the CFE root, not how Mason reaches it. If entry
  points drift incompatibly, that's a defect in this Dream's execution, not a license to also
  reopen Mason's architecture.
- **No knowledge loss.** The 106 gotchas and 10 constraints currently living in CFE's
  `SKILL.md`/`reference/`/`guides/` are inputs to each slice's Brief, not something
  Skill Forge re-discovers from scratch.
- **Rule 1 / Rule 2 continue to bind** whatever skill(s) replace CFE.

## Non-goals

- Not a change to Mason's PRD, architecture, or Epic 5 ("Prove the seam holds") — those stay
  exactly as specified; Epic 5 keeps proving Mason's wrap against whichever CFE is live.
- Not a big-bang single cutover — full scope was chosen, but delivered as a sequence of
  independently-complete slices, each with its own proof.

## Kinships

[[pyforge-mason]] (the D-1 decision this Dream reopens, for CFE only — not for Mason itself) ·
[[packaging-factory]] (the practice CFE has always served; this Dream rebuilds the tool, not
the practice) · [[pyforge-atlas]] (the rebuild-with-no-migration cautionary tale this Dream is
structured specifically to not repeat).

## Realization log

- **2026-08-07** — Dream captured. User asked whether Mason should rebuild conda-forge-expert
  via `bmad-builder`/Skill Forge; clarified that Mason's own D-1 explicitly decided the
  opposite (wrap, never fork) for exactly this reason, citing the atlas precedent (~29,000
  rebuilt lines never displaced the original 8,902-line legacy runtime) and CFE's own moat (106
  gotchas, 10 constraints) as the cost of forking. User confirmed they want to reopen D-1
  anyway, for CFE specifically (not Mason). Asked to choose rebuild scope and cutover
  discipline before any plan was drafted: user chose **full scope** (all 30+ MCP tools and
  scripts, not a narrow pilot) paired with **hard cutover per slice** (every slice's migration
  lands in the same epic that builds it — explicitly rejecting the "build everything, migrate
  later" shape that produced atlas's outcome). This Dream captures that decision; next step is
  `bmad-spec`, not code.
