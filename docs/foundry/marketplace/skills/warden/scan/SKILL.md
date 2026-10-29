---
name: warden-scan
description: >
  Scan the current project with the warden CLI. No pixi environment name
  and no path inside local-recipes. The station command is warden scan
  (or pyforge warden scan). pyforge-warden is not published yet. deptry
  and osv-scanner are the engines the CLI calls; their output is not a
  warden verdict.
---

# @warden/scan

Marketplace id `warden/scan`. Install this folder into both
`.agents/skills/warden-scan/` and `.claude/skills/warden-scan/`.
The human runbook is [steps.md](steps.md); the verified tool versions live
there.

Run from the teammate's project directory. Do not `cd` into local-recipes.
Do not prefix commands with a pixi environment selector.

## When pyforge-warden is installed

```bash
warden scan .
pyforge warden scan .
warden scan --doctor
```

`warden scan .` prints the compliance report. `--format json` prints one
JSON report. `--warn-only` does not block. `--doctor` checks the scanner
environment (its exit codes are `steps.md` step 1) and is not a second
subcommand.

`pyforge warden` forwards to the `warden` console script
(`pyforge.core.dispatch`). Do not import `pyforge.warden`. Do not treat
another tool's exit code as this gate.

## Until that package is published

`pyforge-warden` and `pyforge-core` are not on PyPI, conda-forge, or
SelfExplainML (404 on 2026-10-21). The scan command cannot be replaced by
a hand-run of its engines; `deptry --version` and `osv-scanner --version`
are the probes that run today (`steps.md` step 2).

## What this skill is not

Not a conda-forge recipe skill. Not a second PR gate. This folder does not
replace the estate procedure under `.claude/skills/pyforge-warden/`.
