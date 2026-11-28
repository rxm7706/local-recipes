---
name: "marshal-s-copier-update-test-can-flake-once-in-a-long-while"
description: "Marshal's copier-update test can flake once in a long while, cause unknown (2026-11-27). src/shared/packages/pyforge-ma…"
metadata:
  type: feedback
---

Marshal's copier-update test can flake once in a long while, cause unknown (2026-11-27). src/shared/packages/pyforge-marshal/tests/unit/test_seed_engine_copier.py::test_update_against_an_existing_answers_file_succeeds failed once, in a local full pr-preflight on c1c6d57e5e (44 lanes), with: CopierEngineError: copier update failed: [Errno 39] Directory not empty: '<TMPDIR>/.../copier._main.old_copy.<random>/.git'. That is the TemporaryDirectory cleanup of copier 9.19.1's own old_copy clone, inside copier.run_update. The next full preflight on the same tree was green. Not reproduced: 320 of 320 passes, 16 at a time under full CPU load, with git 2.53 and with the pyforge-marshal environment's git 2.55; and no marshal-test job failed in the last 120 CI station-test runs. Python 3.14's rmtree names the directory whose own rmdir failed, so a new entry appeared directly inside .git during the cleanup. It is not git's detached auto-maintenance: each git commit does start 'git maintenance run --auto --quiet --detach', but strace shows that process touches only .git/objects/maintenance.lock. How to apply: re-run the lane alone before reading a red as real. If it recurs, find what the new .git entry is (list old_copy/.git when the cleanup fails) before changing code. Never retry or ignore the cleanup error to hide it.
