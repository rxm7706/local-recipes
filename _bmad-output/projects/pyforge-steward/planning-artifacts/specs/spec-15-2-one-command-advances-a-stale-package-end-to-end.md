---
title: One command advances a stale package end-to-end
type: feature
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 034588ccf6
---

<intent-contract>

## Intent

**Problem:** After pipeline-truth names a stale bmad-suite package, advancing it still requires the 2026-08-21 seven-stage hand ritual (spec-bmad-suite-channel-product CAP-2).

**Approach:** One steward command chains autotick (tag-mode or HEAD-advance) → local build → recipe tests → channel publish → listing verification, landing as a reviewable PR — zero improvised steps, never auto-merged. CFE Rule 1: github_updater HEAD-advance for commit-pinned dev recipes lands as conda-forge-expert skill work with its Rule-2 retro.

## Acceptance Criteria

- One command advances a package the truth-report names stale through the full chain to a reviewable PR.
- Supports tag-mode and HEAD-advance autotick paths as applicable.
- Never auto-merges; PR is reviewable.
- Fixture-covered for the chain orchestration (foreign network/channel steps mocked or dry-run where safe).
- Does not implement 15.3 provisioning-module expansion.

## Boundaries & Constraints

**Never:** Auto-merge the advance PR. Never implement 15.3+. Never `scripts/bmad-switch`. Steward 12-7 remains skipped. Finalize steward ledger only. Do not touch marshal 19-3. Invoke `conda-forge-expert` for any recipe/autotick/CFE skill edits (Rule 1) and close with Rule-2 retro if CFE changed.

</intent-contract>

## Code Map

- Steward suite advance duty (new CLI verb chaining from 15-1 truth)
- Autotick / github_updater HEAD-advance (CFE skill surface if needed)
- Local build + recipe tests + publish + listing verification orchestration
- Unit tests with mocked foreign stages

## Verification

- `pixi run --frozen -e pyforge-steward pytest …` green
- Orchestration fixture covers stages; no auto-merge
- CI: detectors, linter, package tests
- If CFE skill touched: Rule-2 retro + CHANGELOG bump


## Auto Run Result

Status: done
Summary: Shipped `steward suite advance` CAP-2 chain (autotick tag|head → build → test → publish → listing → reviewable PR, never auto-merged). CFE `github_updater --head` + Rule-2 retro to v8.84.0. Fixture tests cover orchestration.
