---
name: "write-pixi-lock-only-with-the-pixi-version-the-workspace-pin"
description: "Write pixi.lock only with the pixi version the workspace pins (requires-pixi and every workflow's pixi-version; 0.80.0…"
metadata:
  type: feedback
---

Write pixi.lock only with the pixi version the workspace pins (requires-pixi and every workflow's pixi-version; 0.80.0 on 2026-11-18), never with a newer local pixi. Why: on 2026-11-18 PR #2373's build, lint-types and Platform CI test jobs failed after a lock re-solved with a local pixi 0.84.2 was pushed: 0.84.2 records the unix virtual package per platform, and pixi 0.80.0 reads that as 'lock file not up-to-date with the workspace' within seconds, while every local lane, 'pixi lock --check' and a full pr-preflight passed on 0.84.2. Platform CI's two warden promotion-verdict tests also read warn instead of clean, because they shell to a plain 'pixi run -e pyforge-warden' that re-solves a lock CI considers stale. How to apply: 'pixi exec --spec pixi=<pinned> pixi lock', then prove it in a clean clone ('git clone --shared', then 'pixi exec --spec pixi=<pinned> pixi install -e <env> --locked'); when adding a tool that an older lock already carries in another environment (git 2.55.0), solve once with the version capped to the locked line and once more with the cap removed, so the solver does not take a newer build that moves unrelated pins. docs/how-to/run-and-read-pr-preflight.md carries the procedure.
