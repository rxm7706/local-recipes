# Tool support matrix — Agent Skills, AGENTS.md, subagents, MCP, plugin marketplaces

Official docs read 2026-10-20 (via web search/fetch). "Uncertain" = not confirmed in an official doc this session.

| Tool | SKILL.md skills | Skill paths (project / user) | AGENTS.md | Custom agents / subagents | MCP | Plugin marketplace |
|---|---|---|---|---|---|---|
| **Claude Code** | Yes | `.claude/skills/` / `~/.claude/skills/` [1]; reads `.agents/skills/`: **uncertain** | Yes, conditional: read when no CLAUDE.md exists; else `@AGENTS.md` import or a setting [2] | Yes (`agents/` in plugins [3]; standalone path not re-checked) | Yes (in plugins [3]) | Yes: `.claude-plugin/marketplace.json` in any git repo/dir; sources: relative path, github, git-subdir, any-host git `url`, https archive, npm; private repos OK [4] |
| **Cursor** | Yes (2.4+, Jan 2026) | `.agents/skills/`, `.cursor/skills/` / `~/.agents/skills/`, `~/.cursor/skills/`; **also loads `.claude/skills/`, `.codex/skills/`** [5] | Yes (root + nested) [6] | Yes: `.cursor/agents/*.md` / `~/.cursor/agents/` [7]; forum (Jan 2026): subagents can't use skills [8] | Yes | Yes, Cursor Marketplace plugins (skills, subagents, rules, MCP, hooks) [9]; private/self-hosted team marketplace: **uncertain** |
| **GitHub Copilot (VS Code)** | Yes (also Copilot CLI, cloud agent, JetBrains) | `.github/skills/`, `.claude/skills/`, `.agents/skills/` / `~/.copilot/skills/`, `~/.claude/skills/`, `~/.agents/skills/` [10][11] | Yes (VS Code customization docs [12]) | Yes: `.github/agents/*.agent.md` / `~/.copilot/agents/` [13] | Yes | Yes: "agent plugins" via git `marketplace.json`, `chat.plugins.marketplaces: ["owner/repo"]` [14]; GHE/GitLab hosts: **uncertain**; `gh skill` installs skills from GitHub repos [11] |
| **Devin** | Yes | `.agents/skills/<name>/SKILL.md` in connected repos; plus plugin skills at personal/org/enterprise scope [15] | Yes (first 16 KiB auto-injected) [16] | Yes: plugin `agents/<name>.md` — "CLI/Desktop-only today" [17] | Yes (stdio/SSE/HTTP; MCP marketplace) [18] | Yes: team marketplace repo with `.devin-plugin/plugin.json`, required/optional/forbidden lists; private repo via your Git integration [19] |
| **Gemini CLI** (Code Assist agent mode runs on it [20]) | Yes | `.gemini/skills/`, `.agents/skills/` / `~/.gemini/skills/`, `~/.agents/skills/` (`.agents` wins) [21] | Via setting `context.fileName: ["AGENTS.md","GEMINI.md"]`; GEMINI.md default [22] | Yes: `.gemini/agents/*.md` / `~/.gemini/agents/` [22] | Yes (also in extensions) [23] | Extensions (`gemini-extension.json`, bundle skills/agents/MCP) [23]; an internal-git marketplace: **uncertain** |
| **Gemini Code Assist (IDE, non-agent chat)** | **Uncertain** outside agent mode | — | Agent mode loads GEMINI.md / AGENT.md (per search summary, not verified) | Uncertain | Yes in agent mode [20] | Uncertain |
| **Codex (CLI/IDE/app)** | Yes | `.agents/skills/` / `~/.agents/skills/` [24] | Yes (`~/.codex/AGENTS.md` + git root → cwd) [25] | Yes: TOML in `.codex/agents/` / `~/.codex/agents/` [26] | Yes (`[mcp_servers.*]` in config.toml) | Yes: `.agents/plugins/marketplace.json`; `codex plugin marketplace add` takes owner/repo, **HTTPS or SSH git URLs, or a local dir**; admins can set marketplaces in managed config [27] |
| **No AI tool** | — | — | — | — | — | Needs a human-readable page (internal Pages) + plain install command |

## What reaches the most tools

- **One SKILL.md folder is the common unit.** Every AI tool above reads the Agent Skills format.
- **`.agents/skills/` is read by Cursor, Copilot, Devin, Gemini CLI and Codex** (5 of 6). Claude Code is documented on
  `.claude/skills/`; Cursor and Copilot also read `.claude/skills/`. **Installing each skill into both `.agents/skills/` and
  `.claude/skills/` covers all six** — no per-tool rewrite of the skill itself.
- **AGENTS.md** reaches all six, but conditionally for Claude Code (only without CLAUDE.md) and Gemini (needs a setting).
- **Marketplaces do not converge**: five different manifests (Claude `.claude-plugin/marketplace.json`, Codex
  `.agents/plugins/marketplace.json`, VS Code agent-plugin `marketplace.json`, Devin `.devin-plugin/plugin.json`, Gemini
  extensions, Cursor Marketplace). All are git-based; Claude and Codex explicitly accept any-host git URLs (fits internal
  GitHub/GitLab). A marketplace is an optional per-tool *adapter*, not the distribution backbone.
- **Agents/subagents are least portable**: five formats (`.claude/agents`, `.cursor/agents/*.md`, `.github/agents/*.agent.md`,
  `.gemini/agents/*.md`, `.codex/agents/*.toml`). Shipping "agents" as skills is the portable path.
- Implication for the work environment: a conda/pip package from Artifactory whose installer copies skill folders into
  `.agents/skills/` + `.claude/skills/` reaches every tool without github.com at install time; internal Pages is the browse
  surface for everyone, including teammates with no AI tool.

## Sources (read 2026-10-20)
[1] https://code.claude.com/docs/en/skills · [2] https://code.claude.com/docs/en/memory · [3] https://code.claude.com/docs/en/plugins/manifest-reference ·
[4] https://code.claude.com/docs/en/plugin-marketplaces · [5] https://cursor.com/docs/skills · [6] https://cursor.com/docs/rules ·
[7] https://cursor.com/docs/subagents · [8] https://forum.cursor.com/t/cursor-2-4-skills/149402 · [9] https://cursor.com/docs/plugins ·
[10] https://code.visualstudio.com/docs/agent-customization/agent-skills · [11] https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/create-skills ·
[12] https://code.visualstudio.com/docs/agent-customization/overview · [13] https://code.visualstudio.com/docs/agent-customization/custom-agents ·
[14] https://code.visualstudio.com/docs/agent-customization/agent-plugins · [15] https://docs.devin.ai/product-guides/skills ·
[16] https://docs.devin.ai/onboard-devin/agents-md · [17] https://docs.devin.ai/product-guides/plugin-ecosystem · [18] https://docs.devin.ai/work-with-devin/mcp ·
[19] https://docs.devin.ai/cli/extensibility/plugins/quickstart · [20] https://developers.google.com/gemini-code-assist/docs/gemini-cli ·
[21] https://geminicli.com/docs/cli/skills/ · [22] https://geminicli.com/docs/core/subagents/ (AGENTS.md setting per search summary of configuration docs) ·
[23] https://geminicli.com/docs/extensions/writing-extensions/ · [24] https://learn.chatgpt.com/docs/build-skills ·
[25] https://learn.chatgpt.com/docs/agent-configuration/agents-md · [26] https://learn.chatgpt.com/docs/agent-configuration/subagents ·
[27] https://developers.openai.com/plugins/build/plugins
Some rows rely on search-result summaries of those pages rather than a full page read (Claude AGENTS.md, Cursor plugins/subagents,
VS Code AGENTS.md, custom agents and plugins, Gemini subagents/AGENTS.md, Codex AGENTS.md/subagents); re-check before binding acceptance criteria.
