---
title: 'Named docs join the compile'
type: 'feature'
created: '2026-09-13'
status: 'done'
---

<intent-contract>

## Intent

Compile `docs/how-to/*.md` (except README) as ordinary `doc` nodes and
`docs/reference/library-llms-full.md` as a `##` heading extract. Never
`docs/**`.

## Boundaries & Constraints

**Always:** named paths only.

**Never:** how-to README; tutorials; explanation; wholesale catalog body.

</intent-contract>

## Spec Change Log

- **2026-09-13:** minted for Story 14.1 / `spec-scribe-named-docs` CAP-1.
- **2026-09-13:** implemented — how-tos as `doc` bodies; catalog as `##` extract.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `c91e2d41e9` (2026-09-13, "Merge pull request #1316 from rxm7706/scribe/14-1-named-docs"). Ledger row `14-1-named-docs-join-the-compile: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/README.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-14-1-named-docs-join-the-compile.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/.memlog.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-graphify-nightly-currency/.memlog.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-in-flight-story-specs/.memlog.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-knowledge-layers/.memlog.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-knowledge-layers/later-caps.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-named-docs/.memlog.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-named-docs/SPEC.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-planning-pointers/.memlog.md` (+9 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `ready-for-dev` → `done` (ledger row `14-1-named-docs-join-the-compile: done`).
- `## Auto Run Result` reconstructed from git (none survived).
