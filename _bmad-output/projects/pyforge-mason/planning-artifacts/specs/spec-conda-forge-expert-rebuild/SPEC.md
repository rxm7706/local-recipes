---
id: SPEC-conda-forge-expert-rebuild
spec: conda-forge-expert-rebuild
status: draft
owner-dream: docs/dreams/conda-forge-expert-rebuild.md
surface:
  - .claude/skills/conda-forge-expert/**      # the skill being rebuilt slice by slice (cutover target)
  - .claude/scripts/conda-forge-expert/**     # CLI wrapper layer — each slice redirects its wrappers
  - .claude/tools/conda_forge_server.py       # MCP registrations — each slice redirects its tools
sources:
  - ../../../../../../docs/dreams/conda-forge-expert-rebuild.md
  - ../spec-pyforge-mason/SPEC.md                                              # D-1 (wrap, never fork) — reopened for CFE only, untouched for Mason
  - ../../research/market-mason-packaging-automation-2026-08-08.md             # CFE ground truth: v8.81.0, 67 canonical scripts, 46 MCP tools
  - ../../../pyforge-atlas/planning-artifacts/retros/epic-1-wave-0-skill-forge.md  # the rebuild-without-migration precedent this Spec is structured against
---

> **Canonical contract (draft).** Distilled from the Dream via `bmad-spec`. This is the
> five-field contract for the rebuild effort; the planning chain (PRD → epics) decomposes
> it per slice once the Open Questions below are answered.

# conda-forge-expert rebuild — Skill-Forge-authored, slice by slice, hard cutover

## Why

`conda-forge-expert` is the repo's largest and most actively maintained asset: ~41,410 LOC,
v8.81.0 with 100+ dated releases, 106 gotchas and 10 hard constraints earned one build
failure at a time, 67 canonical scripts, ~57 CLI wrappers, 46 MCP tool registrations, and
a 3-tier layout (skill scripts → CLI wrappers → MCP server) that every pixi recipe task and
every BMAD conda-forge effort routes through. It was accreted, not designed — and the repo
now carries Skill Forge (`_bmad/skf/`: `skf-analyze-source`, `skf-brief-skill`,
`skf-create-skill`, `skf-audit-skill`, `skf-campaign`), a toolchain built to compile skills
from briefs with drift auditing and campaign-scale resume.

The user explicitly reopened Mason's D-1 ("wrap, never fork the craft") **for CFE itself
only** and chose **full scope** — all tiers, all tools — but bound to one non-negotiable
discipline: **hard cutover per slice**. The `pyforge-atlas` precedent is the reason: ~29,000
rebuilt lines (PRs #58–#105, all merged) that never displaced the 8,902-LOC legacy
`conda_forge_atlas.py`, because migration was deferred to a future that never came. Every
slice here ships its own migration in the same epic that builds it, or it does not ship.

This Spec is honest about scale: full scope is a **multi-epic, multi-session campaign**
comparable to the atlas migration (32 stories). The contract therefore commits concretely
to the slice map and the **first slice end-to-end** (build + cutover + audit + retire), and
commits to the remainder only as campaign-tracked sequence, re-scoped after the first
slice's real cost is measured.

## Capabilities

- **CAP-1 — the slice map, derived not guessed**
  - **intent:** Before any brief is written, `skf-analyze-source` runs against the live
    skill (`.claude/skills/conda-forge-expert/`) to confirm or correct the Dream's
    hypothesized seams (recipe-authoring · atlas-intelligence · project-scanning/MCP) and
    produce the authoritative slice map.
  - **success:** A tracked slice-map artifact under this Spec's directory lists every slice
    with: its canonical scripts, its CLI wrappers, its MCP tool registrations, its pixi
    tasks, its SKILL.md/reference/guides knowledge sections, and its **complete caller
    inventory** (including Mason's `cfe.py` adapter surface). Coverage is total — every one
    of the 67 scripts, ~57 wrappers, and 46 MCP tools appears in exactly one slice (derive,
    don't declare); an unclassified file is a failing check, not a gap. The map fixes the
    slice ordering and names the first slice explicitly.

- **CAP-2 — first slice: recipe generation, built + cut over + retired in one epic**
  - **intent:** The recipe-generation slice — `scripts/recipe-generator.py` and its
    satellites, the `generate_recipe_from_pypi` / `update_recipe_from_github` MCP tools,
    their wrappers and pixi tasks, plus the generator's knowledge (G54 source-decision
    order, G91 build-system mirroring, G94c/G98 naming, the CFE-block emission contract) —
    is compiled as a Skill-Forge-authored replacement and **fully cut over** in the same
    epic. Chosen first because it is the skill's most volatile surface (v8.69/v8.70/v8.81
    all churned it), has the richest regression-test net, and has a small, enumerable
    caller set.
  - **success:** `skf-brief-skill` produces the slice brief with the relevant gotchas and
    constraints as verbatim inputs; `skf-create-skill` compiles the replacement; every
    caller (pixi tasks, MCP registrations in `conda_forge_server.py`, CLI wrappers, and —
    verified, not assumed — Mason's `cfe.py` port) resolves to the new path; the old
    generator code path is deleted or carries an explicit dated deprecation stub; the
    slice's existing regression tests pass unmodified against the replacement (behavioral
    equivalence, not rewritten expectations); and `skf-audit-skill` reports zero drift.

- **CAP-3 — the anti-atlas guard: cutover enforced by a detector, not by discipline**
  - **intent:** The one failure mode this Dream exists to prevent — a rebuilt slice sitting
    unused beside its live original — is made structurally impossible by a repo detector,
    in the style of `scripts/dream_chain_check.py`.
  - **success:** A detector (registered in `scripts/detectors.py`) reads the slice map and
    fails CI when any slice marked `rebuilt` still has a reachable legacy path: a pixi task,
    wrapper, or MCP registration resolving to retired code, or retired code still present
    without a deprecation marker. It exits green on the pre-rebuild state (no slices
    rebuilt) and is proven red by a fixture before the first slice lands. No slice may be
    marked `rebuilt` in campaign state until this detector passes.

- **CAP-4 — campaign state: the sequence survives sessions**
  - **intent:** The multi-slice sequence is tracked by `skf-campaign`'s file-based state
    with resume, so the effort behaves like a `bmad-loop` run — interruptible, resumable,
    auditable — rather than living in any one session's memory.
  - **success:** Campaign state records per-slice status (mapped → briefed → compiled →
    cut-over → audited → retired), survives session teardown, and a fresh session can
    resume from state alone; after the first slice completes, a dated re-scope note in the
    campaign state records the measured cost and the go/adjust/stop decision for the
    remaining slices before any second brief is written.

## Constraints

- **Rule-1 delegation must never break mid-rebuild.** CFE (or its slice-wise successors)
  remains the authoritative, invocable skill for all conda-forge work at every commit on
  `main`. Mason's `cfe.py` wrap-by-subprocess, every pixi recipe task, and every MCP tool
  stay functional throughout; entry-point compatibility per slice is a gate, and an
  incompatible drift is a defect in this effort, not a license to reopen Mason's D-1.
- **Hard cutover per slice, non-negotiable.** No slice's migration story may be deferred
  to a separate future effort. Build-everything-migrate-later is the explicitly rejected
  shape (the atlas outcome), and CAP-3's detector is its enforcement.
- **No knowledge loss.** The 106 gotchas and 10 critical constraints in `SKILL.md` /
  `reference/` / `guides/` are verbatim inputs to each slice's brief; Skill Forge never
  re-derives them, and each slice's audit checks its gotchas survived into the replacement.
- **Rule 1 and Rule 2 continue to bind** whatever replaces CFE: the successor skill's
  guidance stays authoritative over BMAD stories, and every conda-forge effort — including
  each slice epic of this rebuild — still closes with a retro that lands skill edits, a
  CHANGELOG entry, and a semver bump.
- **Mason's own architecture is out of scope.** This Spec changes what lives at the CFE
  root, never how Mason reaches it. No edit to Mason's PRD, ARCHITECTURE-SPINE, or Epic 5.
- **The test net is the safety rail.** Existing CFE tests (unit + meta, ~1,186 across the
  suite) run green at every slice boundary; a slice may add tests but may not weaken or
  delete existing ones to pass.

## Non-goals

- **Not a big-bang cutover.** Full scope, delivered as independently complete slices.
- **Not a redesign of the lifecycle.** The 10-step loop, Operating Principles, Build
  Failure Protocol, and the gotcha corpus are carried forward, not reinvented.
- **Not an atlas re-rebuild.** The `pyforge.atlas` Kedro stack and the legacy
  `conda_forge_atlas.py` question is *informed by* this effort's cutover discipline but is
  not in this Spec's scope; if the atlas-intelligence slice reaches the front of the queue,
  its brief decides whether to cut over to the legacy path's rebuild or to `pyforge.atlas`
  — a decision recorded then, not now.
- **Not a change to Mason's verbs, seam, or knowledge deny-list.**

## Success signal

A session six months from now invokes conda-forge recipe generation and lands on
Skill-Forge-authored code with zero legacy generator path remaining; the CAP-3 detector is
green in CI; campaign state shows every completed slice as cut-over-and-retired with none
parked in "built, unmigrated"; and no user of `mason recipe`, the pixi tasks, or the MCP
tools noticed the transition except through the CHANGELOG.

## Open Questions

1. **Is this genuinely Mason's to own, or cross-station?** The Dream is owned by `mason`
   (so this chain lives here per INV-2), but CFE is repo-wide infrastructure serving every
   station, and the atlas-intelligence tier arguably belongs to `atlas`. Should the slice
   map assign per-slice station ownership (mason owns the campaign, atlas owns its tier's
   briefs), or does mason own the whole rebuild? Needs an operator decision before any
   slice beyond the first.
2. **Can `skf-create-skill` actually carry ~41K LOC of *implementation*?** Skill Forge
   compiles skills (knowledge + progressive capability); CFE is knowledge *plus* a large
   tested Python codebase. The first slice must establish whether "Skill-Forge-authored"
   means Forge compiles the knowledge layer while code migrates conventionally under the
   brief's contract, or Forge genuinely drives code generation. The answer re-scopes
   everything after CAP-2.
3. **Does full scope survive the first slice's measured cost?** The user chose full scope
   with eyes open; CAP-4's re-scope gate is where that choice gets its first real price
   tag. Stopping after a clean first slice is an allowed outcome of the gate, not a
   failure of the Spec.
4. **What is the deprecation posture for the long tail?** Delete-on-cutover is cleanest
   for the detector; a dated stub is kinder to out-of-repo callers (Mason installed
   elsewhere). Per-slice choice, but the default needs deciding in the slice map.
5. **How do Rule-2 retros work mid-campaign?** Each slice epic ends with a retro — but
   does it edit the legacy `SKILL.md`, the successor slice's skill, or both during the
   overlap window? The first slice's retro sets the precedent.
