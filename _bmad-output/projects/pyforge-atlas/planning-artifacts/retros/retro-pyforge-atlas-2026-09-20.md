---
title: 'pyforge-atlas — Retrospective (2026-09-20: the fleet lint / type gate lands)'
project: pyforge-atlas
created: '2026-09-20'
updated: '2026-09-20'
scope: 'One landing, fleet-wide: steward Story 66.1 (spec-pyforge-steward:CAP-153) gave every pyforge-* package [tool.ruff] / [tool.mypy], reformatted every .py, and put the gate in CI and pr-preflight. This note records what the first run of the gate said about THIS station — the code moved today (`code→retro` currency edge), and this is the retrospective that follows it.'
evidence:
  - 'PR #1553 (2026-09-20): src/shared/packages/pyforge-atlas/pyproject.toml, every .py under src/ and tests/'
  - 'pixi run -e pyforge-guild lint-types — exit 0 on the landed tree'
---

## What the gate found on its first run

- **Type baseline:** 22 modules baselined (10 error codes). Every entry is `[[tool.mypy.overrides]]` per module with exactly the error codes that module trips — never `ignore_errors` — so the gate is live for every other module and code. Tighten or drop an entry whenever its module is touched; the baseline is a ratchet, not a floor.
- **Lint:** an ambiguous single-letter loop variable in `pipelines/pypi_intelligence/nodes.py` and `== True/False` comparisons in the derived-artifacts tests — style, not bugs.
- **Format:** every file now `ruff format`ted at 120 columns; the diff is mechanical and the station suite is green on it.

## What to carry forward

- Run `pixi run -e pyforge-guild lint-types` before pushing — it is `pr-preflight`'s first leg and the `pre-push` hook runs it; the CI lane calls the same task, so local and runner agree by construction.
- A `# type: ignore[...]` in a baselined module is now `unused-ignore`: drop it when you see one.
