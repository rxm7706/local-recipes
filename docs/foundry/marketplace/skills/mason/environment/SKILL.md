---
name: mason-environment
description: >
  Lock a teammate project's manifests into one conda-lock file, then check
  that lockfile, from the project directory and without a pixi environment
  name. The station command is pyforge mason environment. Until
  pyforge-mason is published, the lock step is the conda-lock command that
  station assembles.
---

# @mason/environment

Marketplace id `mason/environment`. Install this folder into both
`.agents/skills/mason-environment/` and `.claude/skills/mason-environment/`.
The human runbook is [steps.md](steps.md); the verified tool versions live
there.

Run every command from the teammate's project directory (the directory that
holds `pyproject.toml` or `environment.yml`). Do not prefix the command
with a pixi environment selector.

## Until pyforge-mason is published

`pyforge-mason` and `pyforge-core` are not on PyPI, conda-forge, or
SelfExplainML (404 on 2026-10-21). The lock command the station assembles,
from the engine module `pyforge.mason.engines.condalock`, is:

```bash
conda-lock lock -f pyproject.toml --lockfile conda-lock.yml
```

One `-f` per manifest the project holds; the substitutions and the `-p`
platform rule are `steps.md` step 2; the check, and why not to run
`--check-input-hash` against the real lockfile, is step 3.

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

## What this skill is not

Recipe authoring stays in conda-forge-expert.
