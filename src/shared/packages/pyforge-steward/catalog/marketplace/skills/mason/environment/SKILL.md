---
name: mason-environment
description: >
  Lock a teammate project's manifests into one conda-lock file, then check
  that lockfile, without a pixi environment name and without a path inside
  local-recipes. The station command is pyforge mason environment. Until
  pyforge-mason is published, the lock step is the conda-lock command that
  station assembles.
---

# @mason/environment

Marketplace id `mason/environment`. Install this folder into both
`.agents/skills/mason-environment/` and `.claude/skills/mason-environment/`.
The human steps are [steps.md](steps.md).

Run every command from the teammate's project directory (the directory that
holds `pyproject.toml`, `environment.yml`, or `pixi.toml`). Do not `cd` into
a local-recipes checkout. Do not prefix the command with a pixi environment selector.

## When pyforge-mason is installed

```bash
pyforge mason environment lock --output conda-lock.yml
pyforge mason environment check --lockfile conda-lock.yml
```

`pyforge` forwards the `mason` token to the `mason` console script
(`pyforge.core.dispatch`). Optional: `--platform linux-64,osx-arm64` on
either command. Pass the same platforms to check that were used to lock.
`--format json` prints one JSON document.

Giving manifest paths skips discovery. Omitting them discovers manifests in
the current directory only.

## Until that package is published

`pyforge-mason` and `pyforge-core` are not on PyPI, conda-forge, or
SelfExplainML (404 on 2026-10-21). The lock command the station actually
assembles, from `pyforge.mason.engines.condalock`, is:

```bash
conda-lock lock -f pyproject.toml --lockfile conda-lock.yml
```

Repeat `-f` for each manifest. Repeat `-p linux-64` (one flag per platform)
only when the caller asked for platforms. With no `-p`, conda-lock chooses
its own default. Verified in this repo's mason environment: `conda-lock`
4.0.2 and `mason environment --help`.

The station's check runs `conda-lock lock --check-input-hash` against a
temporary copy of the lockfile, not against the lockfile in place. Do not
point `--check-input-hash` at the real lockfile. That check is the
`pyforge mason environment check` command, and it waits on the unpublished
package.

## What this skill is not

Recipe authoring stays in conda-forge-expert. This folder does not replace
the estate procedure under `.claude/skills/mason-environment/`.
