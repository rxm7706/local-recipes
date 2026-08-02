---
spec: fleet-chain-completeness
status: draft
owner-dream: docs/dreams/fleet-chain-completeness.md
surface: []          # frontier — no code exists yet; a PRD/architecture pass will claim a surface
companions: []
sources:
  - ../../../../../../docs/dreams/fleet-chain-completeness.md
open_questions:
  - "Q1 — invocation shape unspecified. The Dream names the 4 skills to orchestrate (bmad-spec, bmad-prd, bmad-architecture, bmad-create-epics-and-stories) but not how the orchestrator itself is invoked non-interactively — a new bmad-* skill, a Workflow tool script, or a subagent chain is undecided."
  - "Q2 — error/resume semantics undefined. If a mid-chain phase (e.g. PRD generation) fails or needs human clarification, the Dream does not specify whether the run halts, retries, or resumes from that phase on a second invocation."
  - "Q3 — Phase 8's git integration is unspecified. The Dream says cleanup 'stages for human review in IDE' but does not say whether that means git add without commit, an unstaged working-tree diff, or something else."
  - "Q4 — Phases 2 (Research Generation) and 3 (Brief Generation) have no confirmed 1:1 skill mapping. Verified 2026-08-02: this repo ships bmad-product-brief and bmad-prfaq but no dedicated bmad-research skill; whether Phase 2/3 map onto bmad-product-brief, get folded together, or need new tooling is unresolved."
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what to build, test, and validate. `docs/dreams/fleet-chain-completeness.md` is listed in `sources:` for narrative rationale this contract intentionally omits.

# SPEC — fleet chain completeness

## Why

The factory's planning chain has eight layers — Dream, Spec, Research, Brief, PRD,
Architecture, Epics, Code — and keeping them coherent end-to-end is manual and fragile today.
When a Dream is updated or several dreams consolidate into one, downstream layers fall out of
sync by hand: specs reference deleted dreams, epics reference orphaned specs, code traces
break. This session's own 2026-08-02 dream-consolidation pass across all 8 PyForge stations is
itself the proof — every satellite retirement and every extended Spec/PRD/epics update was
done by hand, one station at a time, with no tooling verifying the chain stayed coherent
afterward. A repeatable, reviewable regeneration workflow closes that gap: run it once after a
Dream changes, review the diff, commit clean.

## Capabilities

- **CAP-1 — orchestrated chain regeneration.**
  - **intent:** From a consolidated Dream, run `bmad-spec` → `bmad-prd` → `bmad-architecture`
    → `bmad-create-epics-and-stories` in sequence, each phase's output feeding the next,
    without a human hand-carrying files between skill invocations.
  - **success:** a single invocation against a consolidated Dream produces a coherent
    Spec/PRD/Architecture/Epics chain with no manual hand-off required between phases.

- **CAP-2 — code-status preservation.**
  - **intent:** Regenerating the planning chain does not clobber existing Code implementation
    status (shipped versions, story completion state) recorded in `epics.md`.
  - **success:** re-running the workflow against an already-partially-implemented project
    leaves every story's done/in-progress/backlog status exactly as it was before the run.

- **CAP-3 — chain-completeness audit mode.**
  - **intent:** A verify-only pass, independent of regeneration, answers whether a project's
    8-layer chain is complete, coherent, and free of orphaned or stale artifacts, without
    generating or changing anything, and that verdict is visible on the fleet dashboard, not
    only in the operator's terminal.
  - **success:** run in audit mode against any of the 8 PyForge stations and get a pass/fail
    per contract checkpoint, matching what a manual read of the chain plus `dream_chain_check`
    would find, with the dashboard reflecting each audited station as chain-complete or naming
    its gap.

- **CAP-4 — orphan detection with review-gated cleanup.**
  - **intent:** Identify artifacts the regenerated chain no longer references — old spec
    folders, epics from replaced specs, dream-deleted references — and stage their removal
    for human review. Never delete, commit, or push unattended.
  - **success:** after a consolidation run, the operator sees a named list of orphan
    candidates and a reviewable diff, and nothing is deleted or committed without their
    explicit action.

- **CAP-5 — configurable per-project invocation.**
  - **intent:** `project_slug`, `dream_path`, `preserve_code_status` (default true),
    `auto_commit` (default false), and `delete_orphans` (default true-with-review-pause) are
    parameters, not hardcoded per station.
  - **success:** the same workflow definition runs unmodified against any of the 8 stations by
    varying only its parameters.

## Constraints

- **Wrap, never absorb.** This workflow orchestrates `bmad-spec`, `bmad-prd`,
  `bmad-architecture`, and `bmad-create-epics-and-stories` in sequence; it never reimplements
  any of their derivation logic itself.
- **The memlog-derivation invariant is not bypassed.** `bmad-spec`/`bmad-prd` derive `SPEC.md`
  / `prd.md` from an append-only `.memlog.md` and re-render on each run. This workflow must
  drive that same append-then-rerender path per phase, never hand-overwrite a downstream
  artifact directly — bypassing it would break the exact invariant this Spec exists to protect.
- **Derive completeness signals, do not declare them** (`EXEMPLAR-STANDARD.md` provenance
  rule). CAP-3's audit-mode pass/fail per layer is computed by checking real artifact presence
  and cross-references each run, never a cached or hardcoded per-station table.
- **Cross-station runs stay on physical paths.** If a future implementation regenerates more
  than one station's chain in the same run, each station's phases are addressed by literal
  `_bmad-output/projects/<slug>/planning-artifacts/...` paths with `BMAD_ACTIVE_PROJECT=<slug>`
  passed per invocation, never by concurrent `scripts/bmad-switch` calls (CLAUDE.md
  parallel-agent physical-path rule). Within one station's own chain the 8 phases are
  inherently sequential — this constraint only bites at the cross-station level.
- **Never auto-commits or auto-pushes.** Cleanup (CAP-4) stages orphan removal for review;
  regeneration output (CAP-1) is left for the operator to review and commit.

## Non-goals

- **Not a code generator.** Code remains hand-written; CAP-2 preserves its recorded status,
  nothing here produces or edits implementation code.
- **Not an auto-committer.** Every run pauses for human review before anything lands on a
  branch, matching CAP-4's review-gated cleanup and the constraint above.
- **Not a replacement for human judgment.** Specs and epics produced by CAP-1 still need
  review, thought, and iteration — this workflow removes hand-carrying between phases, not the
  thinking within them.
- **Not a one-way pipeline.** Re-runnable whenever the Dream changes; CAP-1 is idempotent
  against an unchanged Dream.

## Success signal

A consolidated Dream (the kind this session produced by hand eight times, once per PyForge
station) drives its own Spec, PRD, Architecture, and Epics regeneration through one workflow
invocation instead of eight separate hand-run skill invocations stitched together manually —
with existing Code-implementation status intact, orphaned artifacts named for review rather
than silently deleted, and nothing committed without the operator's explicit action.

## Open Questions

- Q1 — invocation shape unspecified. The Dream names the 4 skills to orchestrate (`bmad-spec`,
  `bmad-prd`, `bmad-architecture`, `bmad-create-epics-and-stories`) but not how the orchestrator
  itself is invoked non-interactively — a new `bmad-*` skill, a Workflow tool script, or a
  subagent chain is undecided.
- Q2 — error/resume semantics undefined. If a mid-chain phase (e.g. PRD generation) fails or
  needs human clarification, the Dream does not specify whether the run halts, retries, or
  resumes from that phase on a second invocation.
- Q3 — Phase 8's git integration is unspecified. The Dream says cleanup "stages for human
  review in IDE" but does not say whether that means `git add` without commit, an unstaged
  working-tree diff, or something else.
- Q4 — Phases 2 (Research Generation) and 3 (Brief Generation) have no confirmed 1:1 skill
  mapping. Verified 2026-08-02: this repo ships `bmad-product-brief` and `bmad-prfaq` but no
  dedicated `bmad-research` skill; whether Phase 2/3 map onto `bmad-product-brief`, get folded
  together, or need new tooling is unresolved.
