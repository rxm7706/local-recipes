---
name: "a-cached-local-pixi-false-greens-a-lock-whose-path-dependenc"
description: "A cached local pixi false-greens a lock whose path-dependency run-dependency string drifted: 'pixi lock --dry-run --che…"
metadata:
  type: feedback
---

A cached local pixi false-greens a lock whose path-dependency run-dependency string drifted: 'pixi lock --dry-run --check' reads the lock as current, but a fresh pixi (every CI runner) re-derives the source package's run-dependencies from its pyproject.toml and compares the string with pixi.lock's, so every lane fails 'pixi install --locked' with 'lock file not up-to-date with the workspace' within seconds. Why: on 2026-10-25 marshal Story 103.1's PR #2307 went red on every CI lane because pyproject said mcp>=2.2 while pixi.lock recorded mcp >=2.2.0 (written when the package pixi.toml said >=2.2.0; a later auto-checkpoint shortened it with no re-lock), and the local check had passed. How to apply: after any edit to a path package's pyproject.toml or pixi.toml dependencies, verify the lock in a clean clone (git clone --shared into the scratchpad, then 'pixi install -e <env> --locked -v'); its INFO lines name the source package and the added/removed strings. Declare the exact string the lock records, or re-lock.
