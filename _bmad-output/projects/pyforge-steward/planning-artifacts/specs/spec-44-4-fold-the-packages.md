---
title: 'Fold the packages'
type: 'feature'
created: '2026-09-13'
status: 'backlog'
difficulty: heavy
story: 44.4
spec: python-foundry-cutover
surface: ["src/shared/packages/**", "src/platform/**", "pixi.toml"]
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Foundry still has no `src/packages/` workspace. Station envs
and the host cannot boot from the lasting root.

**Approach:** After 44.12, `steward cutover apply --phase 1a` folds
`src/shared/packages/*` to `src/packages/` **in foundry**, rewrites
consumer paths from manifest rows, gives each `django-*` a `pixi.toml`,
removes host `COPY src/shared/packages/...` and `COPY . /app` of package
source. Distribution and import names stay byte-identical. Replayable
until the flag flips. 44.12's regenerate supplies the package-tree rows;
44.1 (full-estate 100% + scored ledger) stays blocked.

## Boundaries & Constraints

**Always:**
- Apply into foundry via `--phase 1a` only; re-runnable.
- No `src/shared/` left in foundry after the fold.
- `ingest-keys-import` successor lands before deleting the ingest import.

**Never:**
- Never fold skills / BMAD / Dreams (44.5).
- Never flip `pyforge.cutover_root`.
- Never copy recipes.

</intent-contract>

## Acceptance Criteria

1. Foundry station envs solve; host boots from `src/packages/` members.
2. No `src/shared/`; Containerfile has none of the ten package COPY lines and no `COPY . /app` of package source.
3. Seven `django-*` packages each have `pixi.toml`.
4. Path sites (`five_tier.py`, `script_map_from_packages_root`, marshal-policy, spec `surface:`, CI `paths:`, pixi.toml) point at `src/packages/`.
5. `parent_depth` rows rewritten with no silent wrong-root fallback.
6. Ledger key `44-4-fold-the-packages` is the only 44.x key this Story may mark `done`.
