---
title: 'CFE comes home'
type: 'feature'
created: '2026-09-13'
status: 'backlog'
difficulty: medium
story: 44.6
spec: python-foundry-cutover
surface: [".claude/skills/conda-forge-expert/**", "src/shared/packages/pyforge-mason/**", "pixi.toml"]
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Mason still resolves conda-forge-expert from `local-recipes`.
Retros and recipe wrap must land in the lasting repo.

**Approach:** After 44.5, move the CFE cell to
`skills/domain/conda-forge-expert` in foundry. Mason's resolve chain
(flag → `MASON_CFE_ROOT` → cwd walk) treats that as a repo root. Recipe
build/submit/update become `pixi run --manifest-path factory/pixi.toml`
subprocesses. Invoke `conda-forge-expert` and close with a Rule-2 CFE
retro. Mason 15.1 is already `done`. Range floor for surface checks is
the foundry epoch (`6e0607b`); a zero-commit range is exit 2.

## Boundaries & Constraints

**Always:**
- Rule 1 / Rule 2 of `conda-forge-expert` apply.
- Epoch SHA is the check range floor.

**Never:**
- Never open a conda-forge PR.
- Never leave `MASON_CFE_ROOT` pointing at `local-recipes` for a foundry checkout.
- Never flip `pyforge.cutover_root`.

</intent-contract>

## Acceptance Criteria

1. CFE cell lives under `skills/domain/conda-forge-expert/` in foundry.
2. Mason resolve in a foundry checkout does not use `local-recipes`.
3. `mason-cfe-surface-check` + `cfe-rebuild-guard-check` pass with epoch floor (zero-commit → exit 2).
4. Rule-2 CFE retro lands on the skill CHANGELOG.
5. Ledger key `44-6-cfe-comes-home` is the only 44.x key this Story may mark `done`.
