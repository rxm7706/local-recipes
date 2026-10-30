---
name: mason-package
description: >
  Build a wheel and sdist from a teammate project directory without a pixi
  environment name. Upload is a separate confirmed command. The station
  command is pyforge mason package. Until pyforge-mason is published, the
  local build is pyproject-build.
---

# @mason/package

Marketplace id `mason/package`. Install this folder into both
`.agents/skills/mason-package/` and `.claude/skills/mason-package/`.
The human runbook is [steps.md](steps.md); the verified tool versions live
there.

Run from the teammate's project directory.
Do not prefix commands with a pixi environment selector.

## When pyforge-mason is installed

Build writes artifacts and uploads nothing:

```bash
pyforge mason package build . --target library
```

`--target library` is the v1 target.

### Upload

Upload is a separate confirmed command, and this skill does not run it.
`ship` prints a plan and uploads nothing unless `--yes` is present:

```bash
pyforge mason package ship --to pypi-test
pyforge mason package ship --to pypi-test --yes
```

`--to` accepts `pypi-test`, `pypi`, `channel:<name>`, and `conda-forge`.
After `--yes` the station uploads; `TWINE_USERNAME` and `TWINE_PASSWORD`
must already be set before a PyPI or TestPyPI target builds. `steps.md`
step 4 names what the station runs then, and what not to run from this
skill.

## Until that package is published

`pyforge-mason` and `pyforge-core` are not on PyPI, conda-forge, or
SelfExplainML (404 on 2026-10-21). The wheel and sdist command the station
assembles, from the engine module `pyforge.mason.engines.pep517`, is
`pyproject-build --no-isolation` with the project directory as the working
directory (`steps.md` step 2; the build-backend precondition is step 0).
The conda artifact command, from the engine module
`pyforge.mason.engines.pixi`, is `pixi build --output-dir <dir>` (step 3).

## What this skill is not

Recipe submission stays in conda-forge-expert.
