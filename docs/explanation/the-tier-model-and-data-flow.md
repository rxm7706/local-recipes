---
sources:
  - AGENTS.md
  - docs/MAP.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - scripts/promote_sprint_status.py
  - _bmad-output/PROJECTS.md
verified: 2026-10-24
---

# The Tier Model and Data Flow

The PyForge Estate operates under the **BMAD (Build More Architect Dreams)** method, which enforces a strict hierarchy for planning and execution data. This model ensures that autonomous agents do not overwrite human intentions and that architectural drift is caught structurally.

This document explains the rationale behind the tiers of the PyForge data flow, including the retired Tier 1.

## Tier 0: Dreams (`docs/dreams/`)
**Role:** Human aspiration and raw intake.
**Nature:** Tracked, permanent, forward-looking.

Dreams are markdown files authored by humans. They represent feature requests, bug reports, and architectural aspirations, and they are the seed for the entire pipeline. Agents *append* to a Dream (a Realization-log entry, a sibling acknowledgement) rather than rewriting it, and the Dream-append-first rule enforced by `chain-sprawl-check` prefers appending to a station's living Dream over minting a new Dream file. A Dream is live or archived, never both: once a folded Dream's body is in its station Dream, the file moves to `archive/docs/dreams/` (CHAIN-STANDARD §11).

## Tier 1: Legacy Specs (retired 2026-10-10)
**Role:** Former hand-authored specifications.
**Nature:** Retired; its files are archived.

<!-- governance-currency:ignore-start (the retired legacy folder, named because it was removed) -->
Humans once wrote intake specs by hand in `docs/specs/`. The Dream → `bmad-spec` flow superseded that tier. `shipped` and `superseded` specs moved to `archive/docs/specs/` by their own frontmatter `status:` (Story 23.3), and doctor Story 37.1 (2026-10-10) emptied the folder and retired the tier: the last done spec and the three `workflow` stubs went to `archive/docs/specs/`, and the one unfinished spec, `feedstock-refresh.md`, became a companion of `spec-pyforge-mason`.
<!-- governance-currency:ignore-end -->
`AGENTS.md`'s tier table now lists Tiers 0, 2 and 3; the numbers did not shift. Author new specs only in Tier 2.

## Tier 2: Planning Artifacts (`_bmad-output/projects/*/planning-artifacts/`)
**Role:** Active, agent-derived specifications and ledgers.
**Nature:** Tracked, governed, machine-checked.

Once a Dream exists, `bmad-spec` derives a formal Specification (Spec) and places it into Tier 2. This directory holds:
- **Specs:** The technical contract for the capability (`specs/spec-<slug>/SPEC.md` plus its append-only `.memlog.md`).
- **Epics & Stories:** Breakdowns of the Spec into actionable units (`epics.md`).
- **Story specs:** A run drafts each story spec in Tier 3; once the story merges, the spec is promoted into the tracked `planning-artifacts/specs/` and becomes the source of record.
- **Ledgers:** The tracked `sprint-status-ledger.yaml` twin records exactly which story keys are `backlog`, `in-progress`, `blocked`, or `done`.

**The Golden Rule:** Tier 2 artifacts are tracked by Git. An agent modifying code *must* have an accompanying Tier 2 tracking artifact (a Story) that justifies the code change, and each station keeps one Dream, one Spec, one PRD, one spine, and one epic chain — "one chain per station."

## Tier 3: Implementation Scratch (`_bmad-output/projects/*/implementation-artifacts/`)
**Role:** Runtime execution and scratch space for active agents.
**Nature:** Ephemeral, `.gitignore`d.

When an agent executes a Story, it does so within a dedicated Git worktree. Its story drafts, sprint feed (`sprint-status.yaml`), raw tool outputs, and intermediate data files are written to Tier 3. `pixi run -e pyforge-guild sprint-ledger-sync -- --project <station>` promotes that feed into the tracked Tier 2 twin when a story lands. The twin is never hand-edited; a feed that has fallen behind it is repaired from the twin first, and the sync names each repaired key.

Because this directory is `.gitignore`d, nothing in it may ever be git-tracked (the `tracked-impl-artifact` finding). Two gitignored symlinks at `_bmad-output/planning-artifacts` and `_bmad-output/implementation-artifacts` point the BMAD skills at the active project's Tier 2 and Tier 3 directories; parallel agents address projects by physical path instead of moving that switch. Only `implementation-artifacts/` is shared across a project's worktrees (backlinked to the primary checkout); `planning-artifacts/`, ledger included, is an ordinary tracked copy in each worktree, so a status write goes to the worktree's own file.

## Summary: Why the Strict Hierarchy?
By rigidly separating human intent (Tier 0) from machine planning (Tier 2) and ephemeral execution (Tier 3), PyForge ensures that a "runaway" agent can only ever corrupt its own isolated worktree. It cannot rewrite the fundamental goals of the repository, and the tracked ledgers plus the detector suite (`story-status-check`, `spec-surface-check`, `chain-sprawl-check`) catch a Tier 2 that drifts from what actually landed.
