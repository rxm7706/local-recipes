---
sources:
  - .gemini/settings.json
  - GEMINI.md
verified: 2026-11-18
---

# Antigravity developer startup

Use the Antigravity CLI (`agy`) to open an agent session on this repository that starts from the same contract as every other coding agent here. Antigravity is a supported harness: the repository wires it through two checked-in files, and you set nothing per machine.

## When to Use This

- You are starting your first Antigravity or Gemini CLI session in this checkout.
- A session does not seem to know the rules in `AGENTS.md`.
- You need the `agy` flags for a one-shot prompt, a reasoning effort or a permission mode.

:::note[Prerequisites]
- The Antigravity CLI installed and on `PATH`. This repository does not install it and no pixi environment carries it.
- A checkout of this repository. Work in your own worktree and land through a PR, as `AGENTS.md` § *Trunk, worktrees, PRs* says.
:::

## What this repository wires

| File | What it does |
| --- | --- |
| `AGENTS.md` | The one cross-tool contract. Every rule an agent follows here is in it. |
| `.gemini/settings.json` | Sets `context.fileName` to `["AGENTS.md", "GEMINI.md"]`, so Gemini CLI and Antigravity load `AGENTS.md` first. Without it they never read `AGENTS.md`. |
| `GEMINI.md` | The Gemini-only addendum. It points back at `AGENTS.md` and must not repeat it. |

[How to configure your coding agent](configure-your-coding-agent.md) covers the other harnesses.

:::caution[Instruction-only rules]
The session hook that denies certain commands for Claude Code and Cursor has no verified deny surface for Gemini CLI or Antigravity. The rules in `AGENTS.md` § *Session guardrails* still apply to you, but nothing enforces them in this harness.
:::

## Steps

### 1. Check the CLI

```bash
agy --version
```

On 2026-11-18 this printed `1.5.10` on the operator's macOS laptop.

### 2. Start a session from the repository root

```bash
cd <your worktree of this repository>
agy
```

Start from the root so the checked-in `.gemini/settings.json` is the project's settings file.

### 3. Confirm the contract loaded

In the session, run `/memory show`. Both `AGENTS.md` and `GEMINI.md` must appear. After you edit either file, run `/memory reload`.

### 4. Close the session

Before you end a session, run `scribe capture`, the session-close step for every harness (`AGENTS.md` § *Team memory*).

## CLI flags and subcommands

From `agy --help` in `1.5.10`, checked 2026-11-18. The table lists the ones this page's readers reach for; `agy --help` prints them all.

| Form | What it does |
| --- | --- |
| `agy -p "<prompt>"` (`--print`) | Runs one prompt without the interactive session and prints the response. |
| `agy -i "<prompt>"` (`--prompt-interactive`) | Runs an initial prompt, then continues the session. |
| `agy -c` (`--continue`) | Continues the most recent conversation. |
| `agy --effort <level>` | Sets reasoning effort: `low`, `medium`, `high`, `xhigh` or `max`. |
| `agy --mode <mode>` | Sets the execution mode: `accept-edits`, `auto` or `plan`. |
| `agy --model <model>` | Chooses the model for the session. |
| `agy --add-dir <dir>` | Adds a directory to the workspace; repeatable. |
| `agy --sandbox` | Runs with terminal restrictions enabled. |
| `agy --settings <json or path>` | Applies settings for this session only; never saved. |
| `agy models` | Lists available models. |
| `agy agents` | Lists available agents. |
| `agy plugin list` | Lists installed plugins. |
| `agy mcp` | Manages MCP servers (add, remove, list, enable, disable). |
| `agy changelog` | Shows the changelog and release notes. |
| `agy update` | Updates the CLI. |

:::caution
`--dangerously-skip-permissions` approves every tool request without asking. With no deny hook in this harness, do not use it on this repository.
:::

## What You Get

A session whose context holds `AGENTS.md` and `GEMINI.md`, shown by `/memory show`. From there the agent works under the same Dream-first workflow, tier rules and pre-PR checklist as any other harness.

## Vendor notes as of 2026-08-23, not verified by this repository

One operator recorded the notes below on a Linux workstation on 2026-08-23. Nothing in this repository can check them, and they change with Antigravity releases. Treat them as a starting point and confirm against the vendor's own documentation.

**Surfaces.** The platform has three surfaces that share one agent engine: the CLI (`agy`), a desktop application for agent management and scheduled tasks, and an IDE built on VS Code. The CLI carries its own `1.x` version number, separate from the "Antigravity 2.0" platform name.

**Launch commands and paths on that workstation.** The desktop app started with `antigravity &` and the IDE with `antigravity-ide . &`. The CLI was at `~/.local/bin/agy`, the desktop and IDE executables under `/usr/local/bin/`, and the global configuration under `~/.gemini/`.

**Models.** `agy models` listed Gemini 3.7 Flash, 3.6 Flash, 3.5 Flash and 3.1 Pro; Claude Sonnet 4.6 and Opus 4.6 (Thinking); and GPT-OSS 120B. Run `agy models` for today's list.

**Quota.** Usage drew on two rolling 5-hour pools, one for Gemini models and one for Claude and GPT models, under a weekly cap. `agy -p "/quota"` showed the pools and `agy -p "/credits"` the credit balance. Because the pools are separate, switching between a Gemini and a Claude model spread the load.

**Upgrades.** Plan upgrades and compute credits were sold at `https://antigravity.google/g1-upgrade`.
