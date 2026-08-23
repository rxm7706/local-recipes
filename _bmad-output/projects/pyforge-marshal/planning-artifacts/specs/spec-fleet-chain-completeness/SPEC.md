---
spec: fleet-chain-completeness
status: ready
owner-dream: docs/dreams/fleet-chain-completeness.md
surface:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/planning.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/chain_regen.py
companions: []
sources:
  - ../../../../../../docs/dreams/fleet-chain-completeness.md
open_questions: []
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
  - **intent:** From a consolidated Dream, run the full planning chain in sequence via
    `marshal planning chain-regenerate` — each phase's output feeding the next, without a
    human hand-carrying files between skill invocations. **Default mode: Full** (all eight
    Dream phases). **Minimal mode** (`--minimal`): skips Research and Brief (phases 2–3) for
    drift repair on stations without research history.
  - **phase order (Full):**
    1. `bmad-spec` — Spec kernel from Dream
    2. `bmad-deep-recon` — headless **run**, domain type default → `planning-artifacts/research/<run-folder>/`
    3. `bmad-product-brief` — headless **create** from Dream + Spec + Research
    4. `bmad-prd`
    5. `bmad-architecture`
    6. `bmad-create-epics-and-stories`
    7. Code-linkage verify — read-only trace (no code edits)
    8. Orphan report + cleanup gates (CAP-4)
  - **success:** a single invocation against a consolidated Dream produces a coherent
    eight-layer planning chain with no manual hand-off required between phases.

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
    its gap. In **Minimal** regeneration mode, Research/Brief checkpoints pass when those
    layers were intentionally skipped and never existed for the station.

- **CAP-4 — orphan detection with review-gated cleanup.**
  - **intent:** Identify artifacts the regenerated chain no longer references — old spec
    folders, epics from replaced specs, dream-deleted references — and surface them for human
    review. Never delete, commit, or push unattended.
  - **success:** after a consolidation run, the operator sees a named orphan manifest
    (`orphans.json` + `orphans.md` under the run folder) and an unstaged working-tree diff;
    optional `--stage` stages regenerated paths and orphan deletions without commit;
    `--apply-orphans` performs disk deletes only on explicit operator action; nothing is
    committed without their explicit action.

- **CAP-5 — configurable per-project invocation.**
  - **intent:** `project_slug`, `dream_path`, `chain_mode` (`full` default | `minimal`),
    `preserve_code_status` (default true), `stage` (default false), `apply_orphans` (default
    false), and `resume` (continue from last checkpoint) are parameters, not hardcoded per
    station. `auto_commit` remains false and is not offered.
  - **success:** the same workflow definition runs unmodified against any of the 8 stations by
    varying only its parameters.

## Orchestration (resolved — operator 2026-08-23)

**Invocation (Q1):** `marshal planning chain-regenerate --project <slug> --dream <path>`
Skills are invoked headlessly through the FR-52 harness seam (same adapter pattern as
`marshal factory dispatch`). Each phase uses per-invocation `BMAD_ACTIVE_PROJECT` and
literal physical paths under `_bmad-output/projects/<slug>/planning-artifacts/`, never
`scripts/bmad-switch`. Doctor retains read-only audit (`chain-completeness`); marshal owns
regenerate.

**Error / resume (Q2):** Persisted run journal at
`planning-artifacts/.chain-regen/<run-id>/state.yaml`. On skill `complete`, advance phase and
checkpoint. On skill `blocked`, halt with journal `status: blocked` — operator fixes input and
re-invokes with `--resume`. On transient failure (timeout, rate limit), retry current phase up
to **2×** with backoff, then halt. `--resume` continues at the last incomplete phase, never
restarts from phase 1 unless operator starts a new run id.

**Git integration (Q3):** Default: all regeneration output is **unstaged**; orphan manifest
written alongside the run journal. Optional `--stage`: `git add` on regenerated paths and
`git add -u` on confirmed orphan paths only — still **no commit**. `--apply-orphans`: disk
deletes only. Never auto-commit or auto-push.

**Research / Brief mapping (Q4):** Full mode (default) **always** runs `bmad-deep-recon`
then `bmad-product-brief` before PRD. Minimal mode (`--minimal`) skips both for repair runs.

## Constraints

- **Wrap, never absorb.** This workflow orchestrates existing BMAD skills in sequence; it
  never reimplements any of their derivation logic itself.
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
- **Never auto-commits or auto-pushes.** Regeneration output and orphan cleanup are left for
  the operator to review and commit.

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
- **Not a bmad-loop replacement.** Chain regeneration is a sibling marshal verb beside
  `factory spin`/`dispatch`, not an extension of the multi-story loop orchestrator.

## Success signal

A consolidated Dream (the kind this session produced by hand eight times, once per PyForge
station) drives its own full eight-layer planning chain regeneration through one
`marshal planning chain-regenerate` invocation instead of eight separate hand-run skill
invocations stitched together manually — with existing Code-implementation status intact,
orphaned artifacts named in a manifest for review rather than silently deleted, and nothing
committed without the operator's explicit action.
