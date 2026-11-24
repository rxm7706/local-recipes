---
name: "2026-11-23-landed-steward-story-131-1-epic-131-spec-pyforge"
description: "2026-11-23 LANDED: steward Story 131.1 (Epic 131, spec-pyforge-steward CAP-5), PR #2376 merged as 20f5977014. Playwrigh…"
metadata:
  type: project
---

2026-11-23 LANDED: steward Story 131.1 (Epic 131, spec-pyforge-steward CAP-5), PR #2376 merged as 20f5977014. Playwright's browsers come from the lock, not playwright install: playwright-chromium, playwright-chromium-headless-shell and playwright-ffmpeg (recipes/playwright-*, channel SelfExplainML, linux-64/osx-arm64/win-64) are in the detectors, platform-ci-test, pyforge-atlas and pyforge-herald features; the conda activation hook points PLAYWRIGHT_BROWSERS_PATH at $CONDA_PREFIX/share/ms-playwright. Every environment holds the playwright driver at >=1.64.0,<1.65 (docs/governance/pin-policy.yaml, authority spec-131-1) because browsers.json inside the driver fixes the browser revisions (1.64.x: chromium r1248, firefox r1555, webkit r2370, ffmpeg r1013). To move the driver: rebuild the five browser recipes at the new revisions, have the operator upload them to SelfExplainML, then move the cap and re-lock with the pinned pixi; the lock can be written before the upload through a localhost mirror and PIXI_HOME (conda-forge-expert G131).
