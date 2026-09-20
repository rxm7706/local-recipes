---
story: 25-2-bmad-loops-repo-skills-match-the-installed-package
epic: 25
status: done
completion_path: not-loop-native
date: 2026-08-22
---
# Story 25.2 — bmad-loop's repo skills match the installed package

Hand-driven (bmad-build path, operator-verified). Contract: spec-bmad-611-era-alignment CAP-2.

Provenance verified before refresh: the repo copies were pristine 0.8.1 installs
(single history commit, W2 adoption 8f2da76d39, never hand-edited), so package
canon was taken verbatim — no local customization existed to preserve. The extra
`bmad-loop-setup/scripts/` (cleanup-legacy/merge-config/merge-help-csv) was
0.8.1's config-writing behavior removed upstream (#258: the installer owns
BMAD config); deleted with it.

Result: module_version 0.8.1 -> 0.11.0, 10 files +398/-1075. Verification:
`bmad-loop validate` 8/8 homes zero warnings post-refresh; retired-ID guard +
bmad-artifacts integrity meta tests green (`.claude/skills/**` is outside the
guard's include-list by design — skills carry their own names).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `618837f0d8` (2026-08-22, "Merge pull request #609 from rxm7706/marshal/25-2-bmad-loop-skill-refresh"). Ledger row `25-2-bmad-loops-repo-skills-match-the-installed-package: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `.claude/skills/bmad-loop-resolve/SKILL.md`, `.claude/skills/bmad-loop-setup/SKILL.md`, `.claude/skills/bmad-loop-setup/assets/module.yaml`, `.claude/skills/bmad-loop-setup/scripts/cleanup-legacy.py`, `.claude/skills/bmad-loop-setup/scripts/merge-config.py`, `.claude/skills/bmad-loop-setup/scripts/merge-help-csv.py`, `.claude/skills/bmad-loop-sweep/SKILL.md`, `.claude/skills/bmad-loop-sweep/automation-mode.md`, `.claude/skills/bmad-loop-sweep/deferred-work-format.md`, `.claude/skills/bmad-loop-sweep/migration-mode.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
