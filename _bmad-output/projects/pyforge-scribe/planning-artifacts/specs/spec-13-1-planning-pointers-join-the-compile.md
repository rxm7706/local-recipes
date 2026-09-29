---
title: 'Planning pointers join the compile'
type: 'feature'
created: '2026-09-13'
status: 'done'
---

<intent-contract>

## Intent

Compile named Brief / PRD / Architecture-spine / `epics.md` files as
`kind=doc` **pointer** nodes (title, path, status, FR/AD/heading
extract). Never store the wholesale body.

## Boundaries & Constraints

**Always:** named globs only under `planning-artifacts/`.

**Never:** `_node_from_text_file` on this surface; `epics-*.md`;
architecture novels; addenda; research; `specs/`.

</intent-contract>

## Spec Change Log

- **2026-09-13:** minted for Story 13.1 / `spec-scribe-planning-pointers` CAP-1.
- **2026-09-13:** implemented — named-glob pointer surface; body never stored.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `8be360baa4` (2026-09-13, "Merge pull request #1315 from rxm7706/scribe/13-1-planning-pointers"). Ledger row `13-1-planning-pointers-join-the-compile: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/README.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-13-1-planning-pointers-join-the-compile.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-graphify-nightly-currency/.memlog.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-in-flight-story-specs/.memlog.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-knowledge-layers/later-caps.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-planning-pointers/.memlog.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-planning-pointers/SPEC.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-recall-stale-between-nightlies/.memlog.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/sprint-status-ledger.yaml`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/.memlog.md` (+7 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `ready-for-dev` → `done` (ledger row `13-1-planning-pointers-join-the-compile: done`).
- `## Auto Run Result` reconstructed from git (none survived).
