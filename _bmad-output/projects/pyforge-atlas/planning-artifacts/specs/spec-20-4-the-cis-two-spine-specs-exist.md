---
title: 'Story 20.4: The CIS two-spine specs exist (CAP-7)'
type: 'feature'
created: '2026-08-27'
status: 'ready'
updated: '2026-08-27'
baseline_revision: 'cc8b3b2b1c09d6e56a5aebf752e25f507c846571'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
  - _bmad-output/projects/pyforge-atlas/spec-archive/ATLAS-BMAD-SPECS-CONSOLIDATED.md
  - recipes/bmad-creative-intelligence-suite/recipe.yaml
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** DW-D2-1 has recorded, since Story D2 shipped, that the full 28-page Vizro
inventory is blocked on the "CIS two-spine specs" (`DESIGN.md` + `EXPERIENCE.md`) — output of
the **Creative Intelligence Suite (CIS)**, a standalone BMad module whose Carson (Brainstorming
Coach) and Maya (Design Thinking Maestro) personas were named as the intended producers (original
spec § 2.4). As of the 2026-08-27 `epics.md` check, that precondition STILL blocks: the spine
files were never produced, and there has been no evidence-update since the 2026-07-30
verification.

**Approach:** run the CIS Carson/Maya planning pass to produce both spine files, covering every
one of the 19 unshipped Vizro pages, under `planning-artifacts/`, then close DW-D2-1 citing this
story. Concretely: the CIS module IS already conda-packaged and installed in the `local-recipes`
pixi environment (`recipes/bmad-creative-intelligence-suite`, v0.3.1 — six agents including
`bmad-cis-agent-brainstorming-coach` (Carson) and `bmad-cis-agent-design-thinking-coach` (Maya),
plus the `bmad-cis-design-thinking` workflow) — but its skills have NOT yet been copied into
`.claude/skills/` (confirmed: no `bmad-cis-*` skill is discoverable today). The package's own
`about.description` states the precondition plainly: "After installation, run `bmad-cis-install`
in your project directory to copy the skills into `.claude/skills/` so Claude Code can discover
them." This story's first real action is therefore running `bmad-cis-install`, THEN invoking the
design-thinking workflow (Carson for divergent ideation on the 19 pages, Maya for the
human-centered design pass) to actually author `DESIGN.md` + `EXPERIENCE.md`. The workflow's own
default output filename (`design-thinking-{date}.md`) is generic — this story must land the two
spine artifacts under the project's own established `DESIGN.md`/`EXPERIENCE.md` naming (per every
prior reference to them in `epics.md`/`deferred-work-ledger.md`/the original spec § 2.4), not the
workflow's raw default output name.

## Acceptance Criteria

Lifted verbatim from `epics.md` (Story 20.4):

> **Given** DW-D2-1 — checked 2026-08-27: the CIS DESIGN/EXPERIENCE gap STILL BLOCKS (the
> `DESIGN.md` + `EXPERIENCE.md` spine specs were never produced; no evidence-update since the
> 2026-07-30 verification) **When** the CIS Carson/Maya planning pass runs **Then** both spine
> files land under `planning-artifacts/` covering every one of the 19 unshipped pages **And**
> DW-D2-1's close cites them **And** until this story lands, S-20.5 must not expand the page set
> past the live-confirmed core.

## Boundaries & Constraints

**Always:** `BMAD_ACTIVE_PROJECT=pyforge-atlas`; ledger key
`20-4-the-cis-two-spine-specs-exist`; land both spine files under
`_bmad-output/projects/pyforge-atlas/planning-artifacts/` by literal physical path — never via
`scripts/bmad-switch` or the `_bmad-output/planning-artifacts` symlink; this is a
PLANNING/documentation story — its deliverable is the two spine files, not application code;
cover every one of the 19 unshipped pages (28-page target minus the 9 already in
`dashboard/app.py::PAGE_INVENTORY`) — a partial spine that skips pages does not satisfy the AC.

**Block If:** `bmad-cis-install` (or the CIS skills it copies into `.claude/skills/`) is not
available/does not run cleanly in this environment — report and stop; do not hand-author
`DESIGN.md`/`EXPERIENCE.md` as plain prose bypassing the CIS personas the spec (§ 2.4) and this
epic explicitly name as the intended producers. **This spec is minted `status: ready` for
dispatch, but the operator has not yet confirmed `bmad-cis-install` succeeds in this repo's
current session — verify that first; if it fails, the correct outcome is a documented BLOCKED
finding against this story, not an improvised substitute.**

**Never:** expand `dashboard/app.py::PAGE_INVENTORY` past its current 9 live-confirmed pages in
this story (that is Story 20.5's job, and it is explicitly gated on this story's completion);
implement any of the 19 pages themselves; touch the query-plane code from Stories 20.1–20.3.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | `bmad-cis-install` succeeds; Carson + Maya run the design-thinking workflow over all 19 unshipped pages | `DESIGN.md` + `EXPERIENCE.md` land under `planning-artifacts/`, covering all 19 pages | none |
| CIS_INSTALL_FAILS | `bmad-cis-install` errors or the CIS skills fail to register in `.claude/skills/` | story reports BLOCKED, cites the failure; does not hand-author a substitute | no spine files fabricated without the named personas |
| PARTIAL_PAGE_COVERAGE | the planning pass covers fewer than 19 pages | AC not satisfied — story is not done | do not close DW-D2-1 on partial coverage |
| STALE_ALREADY | DW-D2-1 is re-checked and still shows no evidence-update | story confirms the block is unchanged, proceeds to run the pass anyway (that is this story's entire job) | matches the epics.md framing exactly |

</intent-contract>

## Code Map

This is a planning/documentation story — there is no application code to touch. The relevant
map is of the CIS tooling and the deliverable's landing location:

- `recipes/bmad-creative-intelligence-suite/recipe.yaml` — the conda-forge recipe for the CIS
  module (v0.3.1), already built and installed in the `local-recipes` pixi environment
  (`.pixi/envs/local-recipes/share/bmad-creative-intelligence-suite/`). Its `tests.script`
  section proves `bmad-cis-install --help` and the `skills/` tree are present in that env.
- `.pixi/envs/local-recipes/share/bmad-creative-intelligence-suite/module.yaml` and
  `skills/bmad-cis-agent-brainstorming-coach/SKILL.md` (Carson) +
  `skills/bmad-cis-agent-design-thinking-coach/SKILL.md` (Maya) + `skills/bmad-cis-design-thinking/`
  (the workflow, `default_output_file = "{output_folder}/design-thinking-{date}.md"`) — the
  installed-but-not-yet-copied-into-`.claude/skills/` CIS assets this story activates via
  `bmad-cis-install`.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/` — the landing directory for the two
  spine files (`DESIGN.md` + `EXPERIENCE.md`), matching the physical-path convention every other
  Epic 20 spec in this same directory uses.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/app.py::PAGE_INVENTORY` (lines
  63-109) — the CURRENT 9-page live-confirmed inventory the two spine files must cover the
  REMAINING 19 pages beyond (28-page target per `epics.md`/the original spec's FR-9). Read-only
  reference for this story — the actual page-set expansion is Story 20.5's job.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md` `DW-D2-1`
  (line 351) — the entry this story closes, citing the two new spine files, per `epics.md`'s own
  instruction.
- `_bmad-output/projects/pyforge-atlas/spec-archive/ATLAS-BMAD-SPECS-CONSOLIDATED.md:166-168` —
  the original § 2.4 definition of CIS and its Carson/Maya personas, for full context on why
  those two specific agents (not a generic UX pass) are named.
