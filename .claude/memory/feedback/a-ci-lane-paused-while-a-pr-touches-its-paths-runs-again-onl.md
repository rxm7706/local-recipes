---
name: "a-ci-lane-paused-while-a-pr-touches-its-paths-runs-again-onl"
description: "A CI lane paused while a PR touches its paths runs again only on the next PR that touches them, so its red lands on an…"
metadata:
  type: feedback
---

A CI lane paused while a PR touches its paths runs again only on the next PR that touches them, so its red lands on an unrelated PR (2026-10-16: cfe-regression-net was paused through Pages PR #2240, which broke the fleet-picture attention meta test; herald 45.1's #2244 was the first PR the resumed lane ran on and went red). Before merging a PR while a lane it touches is paused, run that lane's local twin; for cfe-regression-net: pixi run --frozen -e local-recipes python -m pytest .claude/skills/conda-forge-expert/tests/meta -q.
