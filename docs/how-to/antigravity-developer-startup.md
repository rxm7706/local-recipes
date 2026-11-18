---
sources:
  - .gemini/settings.json
  - GEMINI.md
verified: 2026-11-17
---

# Antigravity 2.0 Developer Startup Guide & Gist

Use this page to launch the Antigravity CLI, desktop app or IDE against this repository.

> [!NOTE]
> This is one operator's snapshot, generated 2026-08-23 on a Linux workstation with the checkout at
> `/home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes`. Executable paths, the model list,
> quotas and prices below are that snapshot and were not re-checked; they change with every
> Antigravity release. Re-checked 2026-11-17: the `agy` subcommands and flags named here, and the
> repository wiring in section 4.

## 1. Antigravity 2.0 Ecosystem & Versioning Overview

The Antigravity platform consists of three integrated user surfaces that share the same underlying AI agent engine:

1. **Antigravity 2.0 Platform**: The overall generation/brand name for the suite (Desktop App v2.1.x, IDE, CLI v1.x, and SDK).
2. **Antigravity CLI (`agy`)**: The terminal-bound command-line interface. It carries its own version number, separate from the 2.0 platform name: `1.1.19` when this page was written, `1.5.10` on 2026-11-17.
3. **Antigravity Desktop Application**: Standalone operations hub for agent management, scheduled tasks, and artifact rendering.
4. **Antigravity IDE**: Standalone AI-first code editor (built on VS Code) featuring inline completions, code lenses, visual diff overlays, and linter auto-fixing.

> [!NOTE]
> Seeing **`Antigravity CLI 1.x`** on startup is expected. The CLI's `1.x` releases belong to the Antigravity 2.0 platform.

## 2. Launch Commands Quick Reference

| Surface | Terminal Command | Launch Description |
| :--- | :--- | :--- |
| **Antigravity CLI** | `agy` | Launches interactive TUI agent session in current terminal |
| **Antigravity Desktop App** | `antigravity &` | Opens standalone Desktop App (runs in background) |
| **Antigravity IDE (Current Folder)** | `antigravity-ide . &` | Opens the current directory in Antigravity IDE |
| **Antigravity IDE (Specific Path)** | `antigravity-ide /path/to/project &` | Opens specified repository in Antigravity IDE |

## 3. Surface Decision Guide: Desktop vs. IDE vs. CLI

| Use Case / Workflow | Best Surface | Why |
| :--- | :---: | :--- |
| **Hands-on Coding & Editing** | **Antigravity IDE** | Active tab autocomplete, inline `Ctrl+I` refactoring, and line-by-line visual diffs. |
| **Compiler & Lint Error Auto-fixing** | **Antigravity IDE** | Click-to-fix diagnostic integrations directly inside open code tabs. |
| **Background Cron / Scheduled Tasks** | **Desktop App** | Configure recurring background jobs and one-shot timer tasks. |
| **Multi-Project & Agent Orchestration** | **Desktop App** | HTML Auxiliary Pane for Artifact previews, Subagent trees, and project switching. |
| **Terminal & Headless Environments** | **Antigravity CLI** | Fast, keyboard-first TUI workflow directly inside shell sessions. |

## 4. System Installation & Primary Workspace Setup

On the snapshot workstation the checkout was registered and trusted across all surfaces.

### Repository wiring

- **Agent contract:** `AGENTS.md` at the repo root is the cross-tool contract.
- **Loader:** the checked-in `.gemini/settings.json` sets `context.fileName` to `["AGENTS.md", "GEMINI.md"]`, so Gemini CLI and Antigravity load `AGENTS.md` first.
- **Addendum:** `GEMINI.md` carries the Gemini-only notes. Confirm the load with `/memory show`; both files must appear.

### Executable and config paths (Linux snapshot)

- **CLI Executable:** `~/.local/bin/agy`
- **Desktop Executable:** `/usr/local/bin/antigravity`
- **IDE Executable:** `/usr/local/bin/antigravity-ide`
- **Global Config Directory:** `~/.gemini/`
- **Project Registration File:** `~/.gemini/projects.json`
- **Trusted Workspaces File:** `~/.gemini/antigravity-cli/settings.json`

## 5. Helpful CLI Commands

- **Check CLI Version:** `agy --version`
- **Update CLI to Latest Patch:** `agy update`
- **View Recent CLI Changelog:** `agy changelog`
- **List Installed Models:** `agy models`
- **List Active Plugins:** `agy plugin list`

## 6. Model Availability & Quota Comparison

### Available Models (`agy models`, as of 2026-08-23)
- **Google Gemini Series:** `Gemini 3.7 Flash` (High/Med/Low), `Gemini 3.6 Flash`, `Gemini 3.5 Flash`, `Gemini 3.1 Pro` (High/Low)
- **Anthropic Claude Series:** `Claude Sonnet 4.6 (Thinking)`, `Claude Opus 4.6 (Thinking)`
- **Open Source Models:** `GPT-OSS 120B`

### Quota Structure (`agy -p "/quota"`)
Antigravity features **dual rolling 5-hour quota pools** (separate pools for Gemini and Claude/GPT models) that continuously refresh every 5 hours, supported by a weekly safety cap.

### Comparison: Antigravity vs. Cursor ($20/mo) vs. Claude ($200/mo), as of 2026-08-23

| Feature / Metric | **Antigravity (Google Tier)** | **Cursor Pro ($20/mo)** | **Claude Team / Max ($200/mo)** |
| :--- | :--- | :--- | :--- |
| **Model Selection** | **Gemini 3.7 Flash, 3.1 Pro** + **Claude Sonnet 4.6 & Opus 4.6 (Thinking)** + **GPT-OSS 120B** | Claude Sonnet 3.5/3.7, GPT-4o, o1 / o3-mini | Claude 3.5/3.7 Sonnet & Opus only |
| **Quota Structure** | **Dual Rolling 5-Hour Pools** (continuous 5-hour refresh for Gemini & Claude/GPT) | **500 fast requests / month** total across premium models (throttled afterwards) | Shared organization message limits (refreshes every 5 hours) |
| **Context Window Size** | **Up to 1M – 2M tokens** (Gemini 3.x series) | ~128k – 200k tokens | ~200k tokens |
| **Agent Capabilities** | Full terminal execution, subagent orchestration, background tasks, artifacts, IDE & CLI integration | Cursor Agent (in-editor terminal & edits) | Web/Desktop Chat canvas & Artifacts (no background subagents or native CLI loops) |
| **Effective Cost Value** | Included in your Google AI / Antigravity tier | $20 / month per user | $200 / month per user |

## 7. Quota Expansion & BMAD-Method Optimization Strategies

### 1. Direct Quota Expansion
- **G1 Plan Upgrade & Credits:** Upgrade your plan or purchase G1 compute credits at [`https://antigravity.google/g1-upgrade`](https://antigravity.google/g1-upgrade).
- **In-CLI Credits Manager:** Run `agy -p "/credits"` to view credit balance and link automatic credit spillover.
- **Enable Credit Buffer:** Set `UseG1Credits: true` in settings so autonomous agent loops continue seamlessly when standard 5-hour quota dips.

### 2. High-Efficiency BMAD & PyForge Development
- **Dual Pool Model Switching:** Alternate between **Gemini** (`Gemini 3.7 Flash`) and **Claude** (`Claude Sonnet 4.6 Thinking`) pools since each has its own independent 5-hour rolling limit.
- **Subagent Model Scoping:** Configure subagents to inherit `'flash'` or `'flash_lite'` for routine file searches, keeping your high-reasoning quota focused on architecture and verification.
- **Reasoning Effort Tuning:** Use `--effort medium` for standard story coding and reserve `--effort high` for complex spec decomposition (`agy --effort` takes `low`, `medium`, `high`, `xhigh` or `max`).


