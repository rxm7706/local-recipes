---
name: "ci-resume-operator-2026-10-16-unpause-everything-gh-workflow"
description: "CI resume (operator 2026-10-16: unpause everything): gh workflow enable for test-all.yml, test-linux.yml and kedro-viz-…"
metadata:
  type: project
---

CI resume (operator 2026-10-16: unpause everything): gh workflow enable for test-all.yml, test-linux.yml and kedro-viz-publish.yml, the three paused-manually rows ci resume refuses; their registry rows set live with pause metadata cleared, in the same PR as the ci resume of PAUSE_CI_CANARY, PAUSE_CONTAINER_BUILDS and PAUSE_PLATFORM_CONTAINER_BUILDS. No PAUSE_* repo variable remains and no workflow is disabled.
