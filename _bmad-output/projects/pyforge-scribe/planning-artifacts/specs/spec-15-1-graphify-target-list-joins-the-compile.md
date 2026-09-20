---
title: 'Graphify target list joins the compile'
type: 'feature'
created: '2026-09-13'
status: 'done'
---

<intent-contract>

## Intent

When graphify ingest has no explicit target, walk
`src/shared/packages`, `src/platform`, and `scripts`. Never default to
`recipes/` or the repo root.

## Boundaries & Constraints

**Always:** named list; extra still off by default.

**Never:** implicit `recipes/` or `.`; warn on missing optional dirs.

</intent-contract>

## Spec Change Log

- **2026-09-13:** minted for Story 15.1 / `spec-scribe-graphify-target-list` CAP-1.
- **2026-09-13:** implemented — `DEFAULT_GRAPHIFY_TARGETS`; extra-off unchanged.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `6a49e9f223` (2026-09-13, "Merge pull request #1317 from rxm7706/scribe/15-1-graphify-targets"). Ledger row `15-1-graphify-target-list-joins-the-compile: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `.claude/skills/pyforge-scribe/0.1.0/pyforge-scribe/SKILL.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/README.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-15-1-graphify-target-list-joins-the-compile.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/.memlog.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-graphify-nightly-currency/.memlog.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-graphify-target-list/.memlog.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-graphify-target-list/SPEC.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-in-flight-story-specs/.memlog.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-knowledge-layers/.memlog.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-knowledge-layers/later-caps.md` (+14 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `ready-for-dev` → `done` (ledger row `15-1-graphify-target-list-joins-the-compile: done`).
- `## Auto Run Result` reconstructed from git (none survived).
