---
name: "2026-11-27-landed-marshal-s-suite-splits-by-the-durations-it"
description: "2026-11-27 LANDED: marshal's suite splits by the durations its tests take now. PR #2442 merged as c8d08f77e5 (Merge pyf…"
metadata:
  type: project
---

2026-11-27 LANDED: marshal's suite splits by the durations its tests take now. PR #2442 merged as c8d08f77e5 (Merge pyforge-steward/117-34 into main; steward Story 117.34, spec-pyforge-steward CAP-175 realized with no text change), with 18 checks passed. tests/durations/pyforge-marshal.json was stored again from empty under pyforge-marshal-test at four workers. Scored by fresh times, its split gives each shard about 59.5 s of work, where it gave 47, 77, 46 and 68 s; locally the four groups took 25.1, 24.1, 22.2 and 22.4 s, where they took 20.4, 27.9, 17.7 and 24.4 s. Not yet seen on CI: marshal-test did not run on the PR. Measured and dropped the same day: planning the local preflight for more cores than the machine has. At 24 planned cores it used more CPU and was no faster, and back-to-back runs slow as the laptop throttles. Levers still open: atlas-test (101 to 114 s, the longest station job); Detectors' scripts-suite (stdlib) at 94 s, where test_pre_shell_hook.py is 58 of the suite's 94 serial seconds, 597 subprocess runs of the hook; other stations' durations files, each checked by its local four-worker split against a fresh store; and Platform CI's fixed setup per shard.
