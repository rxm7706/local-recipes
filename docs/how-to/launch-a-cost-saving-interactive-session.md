---
sources:
  - CLAUDE.md
  - pixi.toml
  - docs/dreams/pyforge-marshal.md
verified: 2026-09-24
---

# How to Launch a Cost-Saving Interactive Session

Use `headroom` and `caveman` to cut token cost in your own interactive Claude Code terminal session, the same compression layers `marshal factory dispatch` already applies automatically to its own runs.

## When to Use This

- You run an interactive session yourself, outside `marshal factory dispatch`/`spin`, and want the same savings those runs get for free.
- You are setting up a new machine and need the one-time skill install done.
- You want to confirm which compression layers are actually active in a running session.

:::note[Prerequisites]
The `pyforge-guild` pixi environment installed (`pixi install -e pyforge-guild`) and Claude Code itself installed and signed in.
:::

## Understand the two layers

`headroom` and `caveman` compress different things, and you turn each one on separately:

- **`headroom`** is a local HTTP proxy. Wrapping a session with it points `ANTHROPIC_BASE_URL` at the proxy, which then compresses API traffic in transit — this is the wire-compression layer.
- **`caveman`** is a Claude Code skill. Once installed, it compresses output tokens by roughly 65% (`pixi.toml`'s own pin comment), independent of whether the session is wrapped by headroom.

Marshal's dispatched sessions install both automatically as part of their launch. An interactive terminal session gets neither unless you set it up yourself, because nothing wraps your terminal's `claude` invocation for you — `headroom wrap claude` has to be the process that launches Claude Code, and only you can start your own terminal session.

## Install the caveman skill

Run this once per machine:

```bash
pixi run -e pyforge-guild caveman-install --only claude --with-hooks
```

This installs the output-compression skill for Claude Code and its `SessionStart`/`UserPromptSubmit` hooks plus a statusline badge, so you can see at a glance when it is active. Re-running the command is safe; it skips any target that reports already installed.

## Launch wrapped by headroom

Run this from the repo root every time you start a session you want wrapped:

```bash
pixi run -e pyforge-guild headroom wrap claude --code-memory none
```

`--code-memory none` skips registering headroom's Serena code-memory MCP server, which is the default otherwise. Add other flags after `claude` as needed — `--memory` for persistent cross-session memory, `--1m` to keep the 1M context window (a custom `ANTHROPIC_BASE_URL` otherwise caps Claude Code at 200k), or `-- -p` to launch in print mode.

:::caution[Remote Control turns off]
Claude Code disables the `/remote-control` (`/rc`) command while `ANTHROPIC_BASE_URL` points at a custom endpoint, which a headroom-wrapped session always does. Run Claude Code without headroom for any session that needs Remote Control.
:::

## Confirm both layers are active

A wrapped session prints its own confirmation on launch, including the proxy URL it is routing through. For caveman, check the statusline badge the install step added, or run `caveman stats` in a separate terminal to see compression activity for the current session.

## What You Get

- The same wire-compression and output-compression layers marshal's dispatched sessions already get, now available in your own terminal.
- A one-time skill install that survives across every future session on the machine.
- A single launch command to remember instead of two separate setup steps each time.

This is the documented convenience path (`CLAUDE.md` § Interactive session path), not a separately measured one — `marshal factory dispatch`/`spin` remain the measured, benchmarked path for anything where the savings need to be tracked.
