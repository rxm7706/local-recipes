---
title: 'Recall modes join the CLI'
type: 'feature'
created: '2026-09-13'
status: 'done'
---

<intent-contract>

## Intent

Add `--mode planning|memory|code` as exclusive kind bags. Default
recall stays the CAP-4 bag. Internal lexical/semantic `mode=` is
unchanged.

## Boundaries & Constraints

**Always:** exclusive with `--kind`; unknown mode exits 2.

**Never:** portal argv change; semantic as default.

</intent-contract>

## Spec Change Log

- **2026-09-13:** minted for Story 16.1 / `spec-scribe-recall-modes` CAP-1.
- **2026-09-13:** implemented — `--mode` bags; exclusive with `--kind`.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `e04babcf33` (2026-09-13, "Merge pull request #1318 from rxm7706/scribe/16-1-recall-modes"). Ledger row `16-1-recall-modes-join-the-cli: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `.claude/skills/pyforge-scribe/0.1.0/pyforge-scribe/SKILL.md`, `AGENTS.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/README.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-16-1-recall-modes-join-the-cli.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/.memlog.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-knowledge-layers/.memlog.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-knowledge-layers/later-caps.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-marshal-fact-visibility/.memlog.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-portal-recall-defaults/.memlog.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-recall-modes/.memlog.md` (+12 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `ready-for-dev` → `done` (ledger row `16-1-recall-modes-join-the-cli: done`).
- `## Auto Run Result` reconstructed from git (none survived).
