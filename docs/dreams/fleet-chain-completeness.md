---
title: Fleet Chain Completeness — Orchestrated Dream-to-Code Regeneration
type: dream
owner: herald
status: dreamt
---

# Fleet Chain Completeness — Orchestrated Dream-to-Code Regeneration

## The Dream

The factory has **eight layers** in the planning chain: Dream · Spec · Research · Brief · PRD · Architecture · Epics · Code. A project with **Fleet Chain Completeness** has all eight layers coherent, up-to-date, and traceable end-to-end. No gaps. No orphans. No outdated artifacts.

Today, keeping the chain complete is **manual and fragile**: when a Dream is updated or consolidated, the downstream layers fall out of sync. Specs reference deleted dreams. Epics reference orphaned specs. Code traces break.

**The Dream**: An autonomous workflow that **regenerates the entire planning chain from a consolidated Dream**, ensuring every layer stays coherent with no gaps or blockers. Run it once. Review. Commit clean. Repeat when the Dream changes.

## What This Solves

1. **Consolidation** — When multiple dreams merge into one (like Herald's four capability dreams → one consolidated dream)
2. **Drift Prevention** — After dream updates, regenerate all downstream layers automatically
3. **Completeness Verification** — Audit any project's chain: is it complete? Are all layers present? Do they agree?
4. **Cleanup** — Delete orphaned artifacts, old spec folders, stale epics from replaced specs
5. **Review Hygiene** — Generate everything, pause for human review in the IDE, then commit clean

## The Workflow: Eight Orchestrated Phases

**Phase 1: Spec Generation**
- Input: Consolidated Dream file
- Process: Run `bmad-spec` on the Dream
- Output: `spec-<project>/SPEC.md` (five-field kernel contract)
- Preserves: Capability IDs, decision log, assumptions, open questions

**Phase 2: Research Generation**
- Input: Dream + Spec
- Process: Extract research needs, generate research artifacts
- Output: Research.md or research/ folder with context, market analysis, requirements
- Preserves: Nothing yet (first time, so creates fresh)

**Phase 3: Brief Generation**
- Input: Dream + Spec + Research
- Process: Generate intake brief from consolidated inputs
- Output: Brief artifact summarizing scope, intent, success signal
- Preserves: Nothing yet (first time)

**Phase 4: PRD Generation**
- Input: Dream + Spec + Research + Brief
- Process: Run `bmad-prd` to produce full PRD
- Output: PRD with capabilities, constraints, success metrics, non-goals
- Preserves: Nothing yet (first time)

**Phase 5: Architecture Generation**
- Input: Dream + Spec + PRD
- Process: Run `bmad-architecture` to design system
- Output: Architecture artifact with components, data flow, constraints
- Preserves: Nothing yet (first time)

**Phase 6: Epics & Stories Generation**
- Input: Dream + Spec + PRD + Architecture
- Process: Run `bmad-create-epics-and-stories` to decompose into epics and stories
- Output: `epics.md` with full epic/story breakdown, IDs, acceptance criteria
- **Preserves**: Existing Code implementation status (shipped versions, v1.0 markers, story completion state)

**Phase 7: Code Verification**
- Input: Regenerated specs + epics
- Process: Trace Code implementation back to specs/epics/dream
  - Does Code still reference the correct specs?
  - Are shipped versions documented?
  - Are story completions still valid?
- Output: Linkage verification report (all traces intact, or gaps identified)
- Preserves: Code itself (read-only verification, no changes)

**Phase 8: Cleanup & Commit**
- Input: All regenerated layers + old artifact inventory
- Process:
  1. Identify old artifacts (orphaned spec folders, deleted-dream references, stale epics)
  2. Delete old files that are no longer needed
  3. Verify fleet structure is clean
  4. Audit: every file has a purpose in the chain
- Output: Cleanup report (what was deleted, what remains, fleet structure verified)
- **Does NOT commit or push** — stages for human review in IDE

## The Contract: Fleet Chain Completeness

A project achieves **Fleet Chain Completeness** when:

✓ Dream exists and is current
✓ Spec is derived from the Dream (via bmad-spec)
✓ Research artifacts exist and are current
✓ Brief exists and synthesizes Dream + Spec + Research
✓ PRD is derived from Dream + Spec (via bmad-prd)
✓ Architecture is derived from Spec + PRD (via bmad-architecture)
✓ Epics decompose the Architecture (via bmad-create-epics-and-stories)
✓ Code traces back to Epics, Specs, Dream
✓ All layers agree on scope, intent, success signal
✓ No orphaned or stale artifacts
✓ No broken references

## Configurable Parameters

When running the workflow, specify:

- **`project_slug`** — which dream/project to regenerate (e.g., `herald`, `pyforge-atlas`)
- **`dream_path`** — path to the consolidated dream file (e.g., `docs/dreams/herald-pitch.md`)
- **`preserve_code_status`** — whether to preserve existing Code implementation status (default: true)
- **`auto_commit`** — whether to auto-commit the regenerated chain (default: false — always review first)
- **`delete_orphans`** — whether to delete old spec folders and stale epics (default: true, with review pause)

## Success Criteria

- [ ] Workflow orchestrates all eight phases in sequence
- [ ] Each phase completes without manual intervention
- [ ] Spec preserves capability IDs and decision log
- [ ] Code implementation status is preserved (v1.0 shipped, stories done)
- [ ] All old/orphaned artifacts are identified and deletable
- [ ] Workflow pauses for human review before committing
- [ ] Dashboard shows project as "Fleet Chain Complete" (all eight layers present, coherent)
- [ ] Can be re-run whenever a Dream changes
- [ ] Configurable per-project without code changes

## Use Cases

1. **Dream Consolidation** (like Herald): Multiple dreams merge → one consolidated dream → run workflow → regenerate entire chain coherently
2. **Drift Recovery**: A Dream was updated → specs fell out of sync → run workflow → regenerate to match new dream
3. **Onboarding New Projects**: New dream → run workflow → automatically populate entire planning chain
4. **Audit Completeness**: Before shipping → run workflow in audit mode → verify no gaps in the chain
5. **Archive Cleanup**: Retiring a project → run workflow with `preserve_code_status=false` → clean slate for decommission

## What This Is Not

- Not a code generator (Code remains hand-written)
- Not an auto-committer (always pauses for review)
- Not a replacement for human judgment (specs and epics still need review, thought, and iteration)
- Not a one-way pipeline (can re-run at any time when the Dream changes)

## Realization Log

- **2026-08-01** — Dream seeded after running Herald Fleet Chain Completeness workflow manually. Realized the pattern is reusable, configurable, and valuable as a repeatable capability: "When a consolidated dream is ready, regenerate the entire planning chain autonomously, preserve code status, pause for review, then commit clean."
