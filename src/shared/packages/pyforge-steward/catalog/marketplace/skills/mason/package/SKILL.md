---
name: mason-package
description: >
  Build a wheel and sdist from a teammate project directory without a pixi
  environment name and without a path inside local-recipes. Upload is a
  separate confirmed command. The station command is pyforge mason package.
  Until pyforge-mason is published, the local build is pyproject-build.
---

# @mason/package

Marketplace id `mason/package`. Install this folder into both
`.agents/skills/mason-package/` and `.claude/skills/mason-package/`.
Claude Code's documented project skill path is `.claude/skills/`. Devin's is
`.agents/skills/`. The tool matrix does not confirm the other directory for
either of those two tools.
The human steps are [steps.md](steps.md).

Run from the teammate's project directory. Do not `cd` into local-recipes.
Do not prefix commands with a pixi environment selector.

## When pyforge-mason is installed

Build writes artifacts and uploads nothing:

```bash
pyforge mason package build . --target library
```

Ship prints a plan and uploads nothing unless `--yes` is present:

```bash
pyforge mason package ship --to pypi-test
pyforge mason package ship --to pypi-test --yes
```

`--to` accepts `pypi-test`, `pypi`, `channel:<name>`, and `conda-forge`.
`pypi` is irreversible once the upload succeeds. `TWINE_USERNAME` and
`TWINE_PASSWORD` must already be set before a PyPI or TestPyPI target
builds. This pilot does not run a real upload.

## Until that package is published

`pyforge-mason` and `pyforge-core` are not on PyPI, conda-forge, or
SelfExplainML (404 on 2026-10-21). The wheel and sdist command the station
assembles, from `engines/pep517.py`, is `pyproject-build --no-isolation`
with the project directory as the working directory. The same module
documents that console script as `python -m build --no-isolation --outdir dist`.
Verified: `build` 1.6.1.

The conda artifact command in `engines/pixi.py` is `pixi build --output-dir <dir>`.
Verified: `pixi` 0.82.0. That build is local. It is not a pixi environment run.

Do not run `twine upload` or `pixi upload` from this skill. Those are the
commands the station runs only after `--yes` (`twine upload
--non-interactive --disable-progress-bar`, and `pixi upload prefix
--channel <name>`). Verified present: `twine` 7.0.0. Running them publishes.

## What this skill is not

Recipe submission stays in conda-forge-expert. This folder does not replace
the estate procedure under `.claude/skills/mason-package/`.
