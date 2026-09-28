---
name: "2026-09-27-close-the-short-name-base-ref-hardening-is-comple"
description: "2026-09-27 close: the short-name base-ref hardening is complete. PRs #1633-#1637 (marshal 60.1-63.1, doctor 31.1-32.1,…"
metadata:
  type: project
---

2026-09-27 close: the short-name base-ref hardening is complete. PRs #1633-#1637 (marshal 60.1-63.1, doctor 31.1-32.1, mason 18.1, warden 13.1, steward 70.1) make every read of the remote's main name refs/remotes/origin/<b> -- marshal core/refs.py and local branches, doctor.refs, pyforge-testing-kit branch_diff_guard (ORIGIN_MAIN), scripts/coverage_gates_ci.py and coverage-gates.yml, pyforge-station-tests.yml, the four recipe test-*.yml, warden's TEA advisory, steward's tea-test-review task and marshal's review lens, the platform diff guard, and steward workspace start/status/clean. The real bug found on the way: past a local branch or tag named origin/main at an unmerged tip, steward workspace clean --merged-only removed the worktree and deleted its branch. Guards: tests/scripts/test_workflow_diff_bases_name_full_refs.py scans every workflow; per-station shadow tests pin the rest. No DW row of this class is open; kedro-viz-publish.yml's --set-upstream-to=origin/main is left (depth-1 checkout, no tags: not exposed).
