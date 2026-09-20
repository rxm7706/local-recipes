---
sources:
  - AGENTS.md
  - docs/MAP.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - scripts/promote_sprint_status.py
  - _bmad-output/PROJECTS.md
verified: 2026-09-20
---

# The Tier Model and Data Flow

The PyForge Estate operates under the **BMAD (Build More Architect Dreams)** method, which enforces a strict hierarchy for planning and execution data. This model ensures that autonomous agents do not overwrite human intentions and that architectural drift is caught structurally.

This document explains the rationale behind the four tiers of the PyForge data flow.

## Tier 0: Dreams (`docs/dreams/`)
**Role:** Human aspiration and raw intake.
**Nature:** Tracked, permanent, forward-looking.

Dreams are markdown files authored by humans. They represent feature requests, bug reports, and architectural aspirations, and they are the seed for the entire pipeline. Agents *append* to a Dream (a Realization-log entry, a sibling acknowledgement) rather than rewriting it, and the Dream-append-first rule enforced by `chain-sprawl-check` prefers appending to a station's living Dream over minting a new Dream file.

## Tier 1: Legacy Specs (`docs/specs/` — phasing out)
**Role:** Superseded hand-authored specifications.
**Nature:** Legacy; no new files.

Historically, humans wrote intake specs by hand in this directory. That tier is superseded by the Dream → `bmad-spec` flow: `shipped` and `superseded` specs have been sunset to `archive/docs/specs/` by their own frontmatter `status:` (Story 23.3), and `docs/specs/` keeps only the still-`in-progress` specs plus three `workflow` stubs whose bodies moved to `docs/how-to/`. Author no new specs in Tier 1.

## Tier 2: Planning Artifacts (`_bmad-output/projects/*/planning-artifacts/`)
**Role:** Active, agent-derived specifications and ledgers.
**Nature:** Tracked, governed, machine-checked.

Once a Dream exists, `bmad-spec` derives a formal Specification (Spec) and places it into Tier 2. This directory holds:
- **Specs:** The technical contract for the capability (`specs/spec-<slug>/SPEC.md` plus its append-only `.memlog.md`).
- **Epics & Stories:** Breakdowns of the Spec into actionable units (`epics.md`).
- **Ledgers:** The tracked `sprint-status-ledger.yaml` twin records exactly which story keys are `backlog`, `in-progress`, `blocked`, or `done`.

**The Golden Rule:** Tier 2 artifacts are tracked by Git. An agent modifying code *must* have an accompanying Tier 2 tracking artifact (a Story) that justifies the code change, and each station keeps one Dream, one Spec, one PRD, one spine, and one epic chain — "one chain per station."

## Tier 3: Implementation Scratch (`_bmad-output/projects/*/implementation-artifacts/`)
**Role:** Runtime execution and scratch space for active agents.
**Nature:** Ephemeral, `.gitignore`d.

When an agent executes a Story, it does so within a dedicated Git worktree. Its story drafts, sprint feed (`sprint-status.yaml`), raw tool outputs, and intermediate data files are written to Tier 3. `pixi run -e pyforge-guild sprint-ledger-sync` promotes that feed into the tracked Tier 2 twin when a story lands.

Because this directory is `.gitignore`d, nothing in it may ever be git-tracked (the `tracked-impl-artifact` finding). Two gitignored symlinks at `_bmad-output/planning-artifacts` and `_bmad-output/implementation-artifacts` point the BMAD skills at the active project's Tier 2 and Tier 3 directories; parallel agents address projects by physical path instead of moving that switch.

## Summary: Why the Strict Hierarchy?
By rigidly separating human intent (Tier 0) from machine planning (Tier 2) and ephemeral execution (Tier 3), PyForge ensures that a "runaway" agent can only ever corrupt its own isolated worktree. It cannot rewrite the fundamental goals of the repository, and the tracked ledgers plus the detector suite (`story-status-check`, `spec-surface-check`, `chain-sprawl-check`) catch a Tier 2 that drifts from what actually landed.
