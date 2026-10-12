---
title: REA is one pixi install away — reverse engineering as a local stdio tool
type: dream
owner: marshal
status: dreamt
---

# REA is one pixi install away — reverse engineering as a local stdio tool

## The Dream

An operator runs `pixi install -e pyforge-foundry-full` in local-recipes and the
`rea` CLI from [REA](https://github.com/morluto/rea) (`rea-agents` on npm, MIT)
is already on PATH. It does not need `npx`, a global npm, or a Node they picked
by hand. One Marshal registration task wires REA's MCP server into the harness
they use (Claude Code, Cursor, Codex, Grok Build), and after a restart they can
ask their agent "trace how X works in this app".

## Shape

- **No sidecar.** REA is a *local stdio MCP server* (`rea mcp`) that the agent
  starts on demand as a short-lived Node process. There is no long-running
  service, port, or database, unlike the DB-GPT or Langflow sidecars. The only
  child processes are the analysis engines it launches locally (for example,
  Ghidra). A container is worth considering later only as a sandbox for runtime
  capture of untrusted targets, and that is Warden's call.
- **Mason: recipe first.** `recipes/rea-agents` repackages the npm tarball
  together with its production `node_modules` and collected third-party
  licenses. It runs on `nodejs >=22.19`. The recipe is per-platform rather than
  noarch because `@lydell/node-pty` ships a native binary that is resolved per
  platform. It goes to SelfExplainML first, then to staged-recipes for
  conda-forge.
- **Opt-in `rea` pixi feature.** This is a small feature that is composed into
  `pyforge-foundry-full` only after the recipe is published. It is not part of
  this Dream's first PR, and pixi.toml/pixi.lock stay untouched until then.
- **Optional backends, also opt-in.** These are pulled from conda-forge where
  they exist (checked with the anaconda.org API on 2026-10-12):
  - Available: `openjdk` (25.0.2), `wabt` (1.0.41), `pwntools` (4.15.0),
    `binwalk` (3.1.0), `mitmproxy` (12.2.3).
  - Not on conda-forge: `ghidra`, `jadx`, `pwndbg`. Each needs its own
    onboarding ticket or stays operator-installed.
- **Commercial providers stay operator-supplied.** Hopper, IDA, and JEB are
  never packaged. They are reached only through REA's own environment
  variables, for example `REA_JEB_MCP_URL`.
- **Marshal owns registration.** A task (name to be decided; `guild-register
  rea` is a *proposal*) writes the MCP entry for each harness and copies the
  REA skill. It does not let `rea setup` rewrite agent configs. CI runs a
  readiness smoke check: `rea --help` plus an MCP `initialize` handshake.
- **Warden review before default-on.** Runtime capture executes the target, so
  Warden reviews the capability before the feature is enabled by default.
- **Lawful use.** REA is for software the operator owns or is authorised to
  analyse. The feature docs say so.

## Open questions

1. Should registration live in Marshal's MCP surface, or be a pixi task only?
2. Should ghidra and jadx be onboarded to conda-forge, or documented as
   operator installs?
3. Is the osx-64/osx-arm64 native `node-pty` build covered by the recipe as
   written? So far it has only been verified on linux-64.
