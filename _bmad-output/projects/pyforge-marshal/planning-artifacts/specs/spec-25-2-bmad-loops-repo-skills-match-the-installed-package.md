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
