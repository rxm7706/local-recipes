---
name: "a-new-feature-flag-in-src-platform-config-flags-json-must-jo"
description: "A new feature flag in src/platform/config/flags.json must join THREE shipped-flag tables or CI reds: pyforge-core tests…"
metadata:
  type: feedback
---

A new feature flag in src/platform/config/flags.json must join THREE shipped-flag tables or CI reds: pyforge-core tests/unit/test_flags.py (_SHIPPED_CLOCKS, the per_environment table, and the running-clocks test's _LATER_KILL_SWITCHES when it carries a cleanup_by), and src/platform/tests/test_openfeature_file_flags.py (_SHIPPED_BOOLEANS). The local pr-preflight never runs the platform suite, so only Platform CI catches the third. Also: a preflight test that assumes the machine's core count passes on a 16-core laptop and reds on the 4-core runner -- inject logical_cores and derive the expectation from the same input. Both caught on PR #2332 (2026-10-27).
