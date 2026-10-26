---
name: "2026-10-26-platform-ci-test-job-timeouts-runs-39925508594-40"
description: "2026-10-26 Platform CI test-job timeouts (runs 39925508594, 40306113110, 40351088193 attempt 1) were the apt mirror ins…"
metadata:
  type: project
---

2026-10-26 Platform CI test-job timeouts (runs 39925508594, 40306113110, 40351088193 attempt 1) were the apt mirror inside 'playwright install --with-deps chromium' (636-668 s at 38-43 kB/s), never the pixi install (26-32 s cold). Steward Story 112.1 / CAP-174 / FR-48 / Epic 112 (PR #2325): the step installs the browser alone, runs install-deps only when a launch probe fails and probes again, timeout-minutes 15 -> 25 (worst path 1,033 s). Same exposure left open: pyforge-station-tests.yml atlas job runs --with-deps unconditionally (open question on spec-pyforge-steward CAP-174). Draft PR #2274 claims steward capability ids 169-173, FR-42..47 and Epic 109, so the next free steward ids are CAP-175, FR-49 and Epic 113.
