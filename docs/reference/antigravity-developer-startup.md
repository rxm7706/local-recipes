# Antigravity 2.0 Developer Startup Guide & Gist
**Developer:** rxm7706  
**Primary Workspace:** `/home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes`  
**Generated Date:** 2026-08-23  

---

## 1. Antigravity 2.0 Ecosystem & Versioning Overview

The Antigravity platform consists of three integrated user surfaces that share the same underlying AI agent engine:

1. **Antigravity 2.0 Platform**: The overall generation/brand name for the suite (Desktop App v2.1.x, IDE, CLI v1.1.x, and SDK).
2. **Antigravity CLI (`agy`)**: The terminal-bound command-line interface. Versioned in the `1.1.x` release stream (currently `1.1.19`).
3. **Antigravity Desktop Application**: Standalone operations hub for agent management, scheduled tasks, and artifact rendering.
4. **Antigravity IDE**: Standalone AI-first code editor (built on VS Code) featuring inline completions, code lenses, visual diff overlays, and linter auto-fixing.

> [!NOTE]
> Seeing **`Antigravity CLI 1.1.x`** on startup is expected. The CLI tracks `1.1.x` binary patch releases designed for the Antigravity 2.0 platform ecosystem.

---

## 2. Launch Commands Quick Reference

| Surface | Terminal Command | Launch Description |
| :--- | :--- | :--- |
| **Antigravity CLI** | `agy` | Launches interactive TUI agent session in current terminal |
| **Antigravity Desktop App** | `antigravity &` | Opens standalone Desktop App (runs in background) |
| **Antigravity IDE (Current Folder)** | `antigravity-ide . &` | Opens the current directory in Antigravity IDE |
| **Antigravity IDE (Specific Path)** | `antigravity-ide /path/to/project &` | Opens specified repository in Antigravity IDE |

---

## 3. Surface Decision Guide: Desktop vs. IDE vs. CLI

| Use Case / Workflow | Best Surface | Why |
| :--- | :---: | :--- |
| **Hands-on Coding & Editing** | **Antigravity IDE** | Active tab autocomplete, inline `Ctrl+I` refactoring, and line-by-line visual diffs. |
| **Compiler & Lint Error Auto-fixing** | **Antigravity IDE** | Click-to-fix diagnostic integrations directly inside open code tabs. |
| **Background Cron / Scheduled Tasks** | **Desktop App** | Configure recurring background jobs and one-shot timer tasks. |
| **Multi-Project & Agent Orchestration** | **Desktop App** | HTML Auxiliary Pane for Artifact previews, Subagent trees, and project switching. |
| **Terminal & Headless Environments** | **Antigravity CLI** | Fast, keyboard-first TUI workflow directly inside shell sessions. |

---

## 4. System Installation & Primary Workspace Setup

Your primary project [`/home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes`](file:///home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes) is pre-configured and trusted across all surfaces.

### Verified Executable & Config Paths
- **CLI Executable:** [`/home/rxm7706/.local/bin/agy`](file:///home/rxm7706/.local/bin/agy)
- **Desktop Executable:** `/usr/local/bin/antigravity`
- **IDE Executable:** `/usr/local/bin/antigravity-ide`
- **Global Config Directory:** [`/home/rxm7706/.gemini/`](file:///home/rxm7706/.gemini/)
- **Project Registration File:** [`/home/rxm7706/.gemini/projects.json`](file:///home/rxm7706/.gemini/projects.json)
- **Trusted Workspaces File:** [`/home/rxm7706/.gemini/antigravity-cli/settings.json`](file:///home/rxm7706/.gemini/antigravity-cli/settings.json)
- **Repo Agent Guidelines:** [`/home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes/AGENTS.md`](file:///home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes/AGENTS.md)

---

## 5. Helpful CLI Commands

- **Check CLI Version:** `agy --version`
- **Update CLI to Latest Patch:** `agy update`
- **View Recent CLI Changelog:** `agy changelog`
- **List Installed Models:** `agy models`
- **List Active Plugins:** `agy plugin list`

---

## 6. Model Availability & Quota Comparison

### Available Models (`agy models`)
- **Google Gemini Series:** `Gemini 3.7 Flash` (High/Med/Low), `Gemini 3.6 Flash`, `Gemini 3.5 Flash`, `Gemini 3.1 Pro` (High/Low)
- **Anthropic Claude Series:** `Claude Sonnet 4.6 (Thinking)`, `Claude Opus 4.6 (Thinking)`
- **Open Source Models:** `GPT-OSS 120B`

### Quota Structure (`agy -p "/quota"`)
Antigravity features **dual rolling 5-hour quota pools** (separate pools for Gemini and Claude/GPT models) that continuously refresh every 5 hours, supported by a weekly safety cap.

### Comparison: Antigravity vs. Cursor ($20/mo) vs. Claude ($200/mo)

| Feature / Metric | **Antigravity (Google Tier)** | **Cursor Pro ($20/mo)** | **Claude Team / Max ($200/mo)** |
| :--- | :--- | :--- | :--- |
| **Model Selection** | **Gemini 3.7 Flash, 3.1 Pro** + **Claude Sonnet 4.6 & Opus 4.6 (Thinking)** + **GPT-OSS 120B** | Claude Sonnet 3.5/3.7, GPT-4o, o1 / o3-mini | Claude 3.5/3.7 Sonnet & Opus only |
| **Quota Structure** | **Dual Rolling 5-Hour Pools** (continuous 5-hour refresh for Gemini & Claude/GPT) | **500 fast requests / month** total across premium models (throttled afterwards) | Shared organization message limits (refreshes every 5 hours) |
| **Context Window Size** | **Up to 1M – 2M tokens** (Gemini 3.x series) | ~128k – 200k tokens | ~200k tokens |
| **Agent Capabilities** | Full terminal execution, subagent orchestration, background tasks, artifacts, IDE & CLI integration | Cursor Agent (in-editor terminal & edits) | Web/Desktop Chat canvas & Artifacts (no background subagents or native CLI loops) |
| **Effective Cost Value** | Included in your Google AI / Antigravity tier | $20 / month per user | $200 / month per user |

---

## 7. Quota Expansion & BMAD-Method Optimization Strategies

### 1. Direct Quota Expansion
- **G1 Plan Upgrade & Credits:** Upgrade your plan or purchase G1 compute credits at [`https://antigravity.google/g1-upgrade`](https://antigravity.google/g1-upgrade).
- **In-CLI Credits Manager:** Run `agy -p "/credits"` to view credit balance and link automatic credit spillover.
- **Enable Credit Buffer:** Set `UseG1Credits: true` in settings so autonomous agent loops continue seamlessly when standard 5-hour quota dips.

### 2. High-Efficiency BMAD & PyForge Development
- **Dual Pool Model Switching:** Alternate between **Gemini** (`Gemini 3.7 Flash`) and **Claude** (`Claude Sonnet 4.6 Thinking`) pools since each has its own independent 5-hour rolling limit.
- **Subagent Model Scoping:** Configure subagents to inherit `'flash'` or `'flash_lite'` for routine file searches, keeping your high-reasoning quota focused on architecture and verification.
- **Reasoning Effort Tuning:** Use `--effort medium` for standard story coding and reserve `--effort high` for complex spec decomposition.


