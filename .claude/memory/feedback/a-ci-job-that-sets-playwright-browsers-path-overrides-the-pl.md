---
name: "a-ci-job-that-sets-playwright-browsers-path-overrides-the-pl"
description: "A CI job that sets PLAYWRIGHT_BROWSERS_PATH overrides the playwright-browsers-base activation hook, which deliberately…"
metadata:
  type: feedback
---

A CI job that sets PLAYWRIGHT_BROWSERS_PATH overrides the playwright-browsers-base activation hook, which deliberately leaves an existing value alone, so Playwright looks in that directory instead of the environment's share/ms-playwright and reports 'Executable doesn't exist'. Since steward Story 131.1 the browsers come from the lock: no workflow or test environment should set PLAYWRIGHT_BROWSERS_PATH or run playwright install for chromium (PR #2376's atlas-test shards failed exactly this way).
