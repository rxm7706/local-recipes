---
title: 'Story 6.1 — Slice map and campaign state'
type: 'feature'
created: '2026-08-21'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
baseline_revision: '8549892cce'
final_revision: '23130ee53f545761189b17ecb45ac3ac6a6e49e2'
updated: '2026-09-18'
---

<intent-contract>

## Intent

**Problem:** The CFE rebuild campaign (`spec-conda-forge-expert-rebuild` CAP-1 / CAP-4)
cannot start until the live skill is divided into named slices with explicit ordering
and a file-based campaign state that a fresh session can resume from. The Dream
hypothesized three seams (recipe-authoring, atlas-intelligence, project-scanning/MCP)
and ~67 scripts; those numbers are guesses until they are derived from the live tree.

**Approach:** Derive a tracked slice map under the rebuild Spec directory from the live
CFE surface (canonical scripts, CLI wrappers, MCP registrations, pixi tasks, knowledge
sections, Mason `cfe.py` callers) and initialize `campaign-state.yaml` with the CAP-4
status vocabulary and the first slice named **recipe generation** at `mapped`. Do not
brief or compile a slice in this story.

## Boundaries & Constraints

**Always:**
- Land two companions beside the rebuild Spec:
  `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/slice-map.md`
  and `campaign-state.yaml`.
- Derive, do not declare: every counted file/tool appears in exactly one slice. An
  unclassified file is a failing check, not a gap.
- Name the first slice explicitly (recipe generation) and fix slice ordering in both
  artifacts so Story 6.2 can brief slice 1 from state alone.
- Record per-slice status vocabulary that later stories can advance:
  `mapped → briefed → compiled → parallel → audited`, with `cut-over` / `retired` as
  campaign-end states (CAP-3's `parallel` state is part of the vocabulary even though
  CAP-4's original prose omitted it).
- This story only requires the vocabulary to exist and the first slice initialized at
  `mapped`. No slice reaches `parallel` / `audited` / `cut-over` / `retired` here.
- Resume protocol: a fresh session reads `campaign.current_focus`, finds that slice
  under `slices:`, and reads `next_action`.

**Never:**
- Never write a Skill-Forge brief or compile a replacement (Stories 6.2 / 6.3).
- Never flip any caller off the live skill; the live CFE path stays authoritative.
- Never mint `.claude/skills/pyforge-mason/` — recipe work stays `conda-forge-expert`.
- Never edit `recipes/**`.
- Never hand-edit `sprint-status-ledger.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Live-tree derivation | CFE scripts / wrappers / `@mcp.tool` registrations at skill v8.82.3 | Slice map totals equal live counts with zero unclassified files | Re-count from the tree; do not trust the Spec's "~67 scripts" estimate |
| Dream 3-seam hypothesis | recipe-authoring · atlas-intelligence · project-scanning/MCP | Confirm atlas and scanning seams; split recipe-authoring into Generation + Lifecycle; name Shared Infrastructure as a 5th seam | Document confirmation vs correction in `slice-map.md` |
| First slice | CAP-1 / CAP-2 name recipe generation first | Slice 1 listed first; campaign `current_focus` points at it; status `mapped` | Later slices stay unbriefed |
| Resume from state alone | Fresh session, no prior chat | `campaign-state.yaml` is enough to know slices, status, and next action | Pointers to `slice-map.md` for full file lists |
| Cross-slice imports | Shared helpers or sibling imports | Named as cross-slice dependencies, not force-assigned to one owner | Shared Infrastructure slice for truly shared modules |

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/slice-map.md` — CAP-1 artifact; live-tree derivation (68 scripts / 57 wrappers / 46 MCP tools at landing).
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml` — CAP-4 resumable pointer; status vocabulary + first slice `mapped`.
- `.claude/skills/conda-forge-expert/scripts/*.py`, `.claude/scripts/conda-forge-expert/*.py`, `.claude/tools/conda_forge_server.py` — read-only derivation sources.
- `src/shared/packages/pyforge-mason/src/pyforge/mason/cfe.py` — Mason caller inventory (`_CFE_SCRIPTS`); read-only.

## Tasks & Acceptance

**Execution:**
- `docs` — derive `slice-map.md` from the live CFE tree; confirm or correct the Dream's three seams; name recipe generation first.
- `docs` — initialize `campaign-state.yaml` with status vocabulary and slice 1 at `mapped`, resumable from state alone.

**Acceptance Criteria:**
- Given the CFE surface (3 tiers, ~67 canonical scripts, 106 gotchas), when this story lands, then CAP-1's slice map exists with explicit ordering and the first slice named (recipe generation), and CAP-4's file-based campaign state initializes (mapped → briefed → compiled → parallel → audited; cut-over/retired are campaign-end states), resumable from state alone.
- Coverage is total against the live counted surfaces (scripts, wrappers, MCP tools) with zero unclassified files.
- No Skill-Forge brief is written and no caller flips.

## Spec Change Log

- 2026-09-18: Promoted a tracked `spec-<ledger-key>.md` from `epics.md` + landing evidence (PR #570 / `23130ee53f`). The original intent-contract was never promoted out of the landing commit; this file is the durable source of record.

## Review Triage Log

### 2026-08-21 — Landing review (from `23130ee53f`)

Adversarial + edge-case review applied 9 patches on the slice map / campaign-state pair
and deferred 3 pre-existing findings (`DW-6-1-1`..`DW-6-1-3`) cited in the landing
commit message. Those DW ids are **not** present in the tracked
`deferred-work-ledger.md` (the ledger predates Epic 6 and was not extended by 6.1).
Substance lives in `slice-map.md` (method, coverage reconciliation, seam corrections).

## Design Notes

`skf-analyze-source` is scoped to onboarding a fresh external repo into new
`skill-brief.yaml` recommendations, not to re-seaming an existing in-repo skill.
`slice-map.md` § Method records the sanctioned fallback: derive from `find`/`grep`
over the three counted surfaces, cross-checked against import graphs, pixi tasks,
SKILL.md sections, and `cfe.py`'s `_CFE_SCRIPTS` table.

The Spec's "~67 scripts" undercounted the live 68. Recipe-authoring is two slices
because the live import/wrapper/MCP grouping does not support one seam. Shared
Infrastructure (`_http.py`, `_paths.py`, `_cfy_template.py`, `_sbom.py`) is a fifth
seam the Dream did not name.

## Verification

**Commands:**
- `test -f _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/slice-map.md`
- `test -f _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml`

**Landing evidence:**
- Commit `23130ee53f` — `land mason 6.1: slice map and campaign state`
- Merge `806cb63046` — PR #570 (`land/mason-6-1`)
- Live-tree totals at derivation: 68 / 57 / 46; first slice = Recipe Generation.

## Auto Run Result

Status: done

**Summary:** Derived the CFE rebuild slice map and initialized resumable campaign
state. Confirmed atlas-intelligence and project-scanning/MCP; split recipe-authoring
into Recipe Generation (first) and Recipe Lifecycle; named Shared Infrastructure.
Coverage 68 scripts / 57 wrappers / 46 MCP tools, zero unclassified.

**Files changed (original landing):**
- `spec-conda-forge-expert-rebuild/campaign-state.yaml` (new)
- `spec-conda-forge-expert-rebuild/slice-map.md` (new)
- `sprint-status-ledger.yaml` (6.1 → done; not re-touched by this promotion)
