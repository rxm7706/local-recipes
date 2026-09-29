---
sources:
  - AGENTS.md
  - CLAUDE.md
  - .gemini/settings.json
  - .vscode/settings.json
  - scripts/claude_instruction_mode_check.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/claude.toml
  - src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py
verified: 2026-09-20
---

# How to Configure Your Coding Agent for This Repo

Use the instruction-surface conventions in `AGENTS.md` to make any coding agent (Claude Code, Gemini CLI, Cursor, GitHub Copilot, Devin or another `AGENTS.md`-native tool) start every session with the same contract. `AGENTS.md` is the one file that carries the rules; each harness reaches it through a native reader, a one-line pointer, or a setting. This guide gives the setting or command per harness and a way to check it took.

## When to Use This

- You are setting up a new machine or a new coding agent against this repo.
- An agent keeps missing a rule that lives in `AGENTS.md`, such as the pre-PR checklist or the team-memory boot read.
- A subtree rule, like the one in the atlas child file `src/shared/packages/pyforge-atlas/AGENTS.md`, seems ignored.
- `pixi run -e pyforge-guild claude-instruction-mode-check` reports a finding.

:::note[Prerequisites]
A clone of the repo with the `pyforge-guild` pixi environment installed (`pixi install -e pyforge-guild`), and the coding agent itself installed and signed in. For Claude Code, version 2.1.277 or later adds the native `AGENTS.md` reader; older versions still work through the import described below.
:::

## Claude Code

Claude Code reads `CLAUDE.md`, and `CLAUDE.md` imports `AGENTS.md` with a bare `@AGENTS.md` line. That import is the floor: it works on every version and on Bedrock, Vertex and Foundry deployments. Since 2.1.277 (2026-09-18) Claude Code also ships a built-in `agents-md` mod that can read `AGENTS.md` files natively, and this repo pins it to the one mode that loads nested `AGENTS.md` files, which the import cannot do.

### 1. Pin the instruction-file mode

The mod's default mode, `claude-md-or-agents-md`, stays out of any project that has a `CLAUDE.md`, which includes this one. Set the mode in your **user** settings, since the project's `.claude/settings.json` is not read for plugin options:

```json
{
  "pluginConfigs": {
    "agents-md@builtin": {
      "options": { "instructionFiles": "claude-md-and-agents-md" }
    }
  }
}
```

Merge that into `~/.claude/settings.json`, or pick it interactively with `/config` under "Project instructions". The legacy key `projectInstructions: "both"` maps to the same mode.

In `claude-md-and-agents-md` every `AGENTS.md` loads beside `CLAUDE.md`, deduplicated by path, so the root file is never loaded twice through the import. A nested `AGENTS.md` attaches the first time you `Read` a file beneath it, which is how the atlas subtree rules reach the agent.

### 2. Check the host

```bash
pixi run -e pyforge-guild claude-instruction-mode-check
```

It reads `claude --version` and your user settings and prints one line: `ok` on 2.1.277+ with the pinned mode, a `warn` naming what to change otherwise (exit 1), and `could-not-run` (exit 2) when the version output cannot be parsed. With no `claude` binary on the host it is silent and exits 0. The check is advisory and never joins `detectors-ci`; the import keeps working whatever it reports.

### 3. Confirm the nested file attaches

Open a session at the repo root and read any file under `src/shared/packages/pyforge-atlas/`. The session's context should announce `src/shared/packages/pyforge-atlas/AGENTS.md` alongside the root files; if it doesn't, the mode is not pinned for the settings this session loaded.

:::tip[Dispatched sessions are pinned for you]
Sessions launched by `marshal factory dispatch` pass the same option on the command line (`--settings`, from the claude harness profile), so a dispatched story loads nested `AGENTS.md` files regardless of whose machine launched it. The host check is about your own interactive sessions.
:::

## Gemini CLI and Antigravity

There is nothing to set per machine, because the repo's `.gemini/settings.json` names the context files in order:

```json
{ "context": { "fileName": ["AGENTS.md", "GEMINI.md"] } }
```

`GEMINI.md` carries the Gemini-only additions and points back at `AGENTS.md` for everything else, so an agent asked for the pre-PR checklist should quote `AGENTS.md`'s numbered list.

## VS Code with Copilot chat

The repo's `.vscode/settings.json` sets `chat.useAgentsMdFile` to `true`, which makes Copilot chat load `AGENTS.md` for the workspace. `.github/copilot-instructions.md` carries the Copilot-only additions. Verify by opening the Copilot chat panel and asking which pixi environment is the session default; the answer should be `pyforge-guild`.

## Cursor, GitHub Copilot agent, Devin and other native readers

Cursor, the GitHub Copilot cloud agent and CLI, Devin, Codex, Jules, Zed, Warp, Aider, goose, Windsurf, Amp and Factory read `AGENTS.md` natively, root and nested, with the closest file winning, so none of them needs a per-machine setting. Cursor also loads the glob-scoped rules under `.cursor/rules/*.mdc`; Devin's Knowledge ingests `CLAUDE.md` and the `.mdc` rules too, which is why those files carry pointers rather than copies.

## Why the import stays

`CLAUDE.md` keeps its `@AGENTS.md` line even though Claude Code can now read `AGENTS.md` directly. Runtimes below 2.1.277 and the enterprise deployments have no mod, and in the mod's default mode the presence of `CLAUDE.md` switches it off anyway. The import costs nothing in the pinned mode because the mod deduplicates by path. Deleting `CLAUDE.md` to "default to `AGENTS.md`" would drop the Claude-only additions it carries and break every runtime without the mod.

## What You Get

- Every harness on the machine starts from the same `AGENTS.md` contract.
- Claude Code sessions, interactive and dispatched, load nested `AGENTS.md` files.
- A one-line host check that tells you when a Claude Code upgrade or a settings change is due.
- The scribe parity meta-tests (`pixi run -e pyforge-scribe pyforge-scribe-test`) keep the pointers, the settings and the harness table honest in CI.
