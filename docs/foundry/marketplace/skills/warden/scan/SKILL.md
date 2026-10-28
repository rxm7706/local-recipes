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
Claude Code's documented project skill path is `.claude/skills/`. Devin's is
`.agents/skills/`. The tool matrix does not confirm the other directory for
either of those two tools.
The human steps are [steps.md](steps.md). The verified tool versions are
recorded there, not here.

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
environment and exits 0 when healthy, else 2. It never exits 1, and it is
not a second subcommand.

`pyforge warden` forwards to the `warden` console script
(`pyforge.core.dispatch`). Do not import `pyforge.warden`. Do not treat
another tool's exit code as this gate.

## Until that package is published

`pyforge-warden` and `pyforge-core` are not on PyPI, conda-forge, or
SelfExplainML (404 on 2026-10-21). The scan command cannot be replaced by
a hand-run of its engines. The CLI calls `deptry .` (with its own
requirements file) and `osv-scanner scan --offline`. Those binaries can be
probed. Their stdout is not a warden report.

## What this skill is not

Not a conda-forge recipe skill. Not a second PR gate. This folder does not
replace the estate procedure under `.claude/skills/pyforge-warden/`.
