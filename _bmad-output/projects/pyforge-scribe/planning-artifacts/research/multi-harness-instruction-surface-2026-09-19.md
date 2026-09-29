---
doc_type: research
project: pyforge-scribe
date: 2026-09-19
updated: 2026-09-20
status: current
subject: How every agent harness discovers this repo's instructions, memory and skills — and what a multi-agent estate should do about it
triggered_by: PR #1513 review (a parallel session's AGENTS.md / GEMINI.md governance PR)
sources_checked_live: 2026-09-19
---

# The instruction surface across harnesses — adversarial review of the scribe chain (2026-09-19)

## 0. Why this exists

PR #1513 proposed (a) an "Auto-Memory Engine" section telling every harness to read five memory files,
(b) four new pre-PR checklist items, and (c) a 60-line GEMINI.md manual duplicating AGENTS.md and
CLAUDE.md. Reviewing it against the scribe Dream / Spec / PRD raised the real question: **how does each
harness the estate runs (Claude Code, Cursor, Gemini CLI/Antigravity, GitHub Copilot cloud agent +
CLI, Devin, Codex, BMAD's own installer) actually discover instructions, memory and skills in 2026 —
and is the repo's "one AGENTS.md + thin per-tool pointers" design still the right shape?** Every
claim below was checked against the vendor's live docs on 2026-09-19; the repo facts against `main`
at `71c7fe93a2`.

## 1. What each harness reads today (verified)

| Harness | Native instruction discovery | Memory / notes | Skills | Repo state today |
|---|---|---|---|---|
| **Claude Code** | `CLAUDE.md` (+ `.claude/CLAUDE.md`, `CLAUDE.local.md`) load at launch; **`AGENTS.md` loads only when NO `CLAUDE.md` exists in cwd or above** (v2.1.277+; default `claude-md-or-agents-md`). With a `CLAUDE.md` present, `AGENTS.md` is read only through an explicit `@AGENTS.md` import. Target **under 200 lines** per file; `.claude/rules/` path-scoped rules; imports max 5 hops. | Auto memory (per-user, `~/.claude/projects/<encoded>/memory/`, first 200 lines / 25 KB loaded); team memory only via an import. | `.claude/skills/` (Agent Skills standard) | `CLAUDE.md` = 357 lines, `AGENTS.md` = 402 lines; **`CLAUDE.md` does not import `AGENTS.md`** → the `bmad:context` verified block (no-attribution rule, never hand-edit the ledger, scoped stamps…) is **never loaded in a Claude Code session here**. `@.claude/memory/MEMORY.md` is imported. |
| **Cursor** | `AGENTS.md` at root and **nested** (layered, more specific wins) natively; `.cursor/rules/*.mdc` (always / glob / agent-requested / manual; keep < 500 lines, split). | Cursor "Memories" (per-user, cloud-side; not repo-visible). | project skill dirs (Agent Skills) | 5 `.mdc` rules (`specs`, `trunk-worktree-pr`, `scribe-recall`, `bmad-build`, `bmad-build-auto`); `.cursor/environment.json` installs `pyforge-guild`. |
| **Gemini CLI / Antigravity** | `GEMINI.md` by default, hierarchical + `@file` imports; **reads `AGENTS.md` only if `context.fileName` is set** (`.gemini/settings.json` project-level or `~/.gemini/settings.json`), e.g. `["AGENTS.md","GEMINI.md"]`. | none repo-side | `gemini skills` / `/skills` (Agent Skills) | `GEMINI.md` = 14-line pointer; **no `.gemini/settings.json` in the repo**; operator's `~/.gemini/settings.json` has no `context.fileName` → Gemini never loads `AGENTS.md`. |
| **GitHub Copilot — cloud/coding agent** | Reads **all of**: `AGENTS.md` (root + nested, nearest wins), `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md` (`applyTo` globs), **`CLAUDE.md` and `GEMINI.md`**. Ephemeral GitHub Actions env; `.github/workflows/copilot-setup-steps.yml` (job must be named `copilot-setup-steps`; 59-min hard cap on a session; firewall allowlist); custom agents `.github/agents/*.agent.md` (≤ 30 000 chars, `tools:` allowlist); hooks; skills. | none repo-side | `.github/skills` / `~/.copilot/skills` (Agent Skills; `gh skill` installs) | `copilot-instructions.md` = 18-line pointer; `copilot-setup-steps.yml` installs `pyforge-guild` (steward 63.2). No `.github/agents/`, no `.github/instructions/`. |
| **Copilot CLI / VS Code chat** | `copilot-instructions.md` default-on; `AGENTS.md` needs `chat.useAgentsMdFile: true` in VS Code (experimental, off by default); CLI discovers instruction files up the path and `/instructions` lists them. | — | as above | no `.vscode/settings.json` pin. |
| **Devin** | Looks for `AGENTS.md` "before it starts coding" (root or anywhere). **Knowledge** auto-pulls from `.rules`, `.mdc`, `.cursorrules`, `.windsurf`, `CLAUDE.md`, `AGENTS.md` — *not* general `.md` files — plus trigger-scoped entries pinned per repo; Playbooks for repeatable tasks; DeepWiki; environment = machine snapshot + Repo Setup (deps, lint, tests, secrets) "the single highest-leverage thing"; MultiDevin = a coordinator session launching child sessions in isolated VMs with ACU limits. | Knowledge (org/repo, cloud-side; sessions report "Accessed Knowledge") | Playbooks | nothing Devin-specific; it would ingest AGENTS.md, CLAUDE.md and every `.mdc` into Knowledge — **duplicated content becomes duplicated, possibly conflicting Knowledge entries**. |
| **Codex / Jules / Zed / Warp / Aider / goose / Windsurf / Amp / Factory …** | `AGENTS.md` (agents.md open format; "closest file wins; explicit chat prompts override"). | — | Agent Skills (`~/.codex/skills`, `.agents/skills` emerging as the neutral path) | covered by the root `AGENTS.md`. |
| **BMAD-METHOD** (the tool most of the estate's process runs on) | `bmad-project-context` writes **only** the `<!-- bmad:context -->` block in `AGENTS.md` and *"proposes a one-line `@AGENTS.md` import for the tools you use"*; content rule: *"only what is expensive to rediscover, or that the agent learns only after it has already gone wrong"*; *"Repo overviews, directory trees, and tech-stack lists never enter"*; monorepo components get their own nested file listed as pointers in the parent; never commits. Installs skills through the Skills CLI (`npx skills add …`), a Claude Code plugin and a Codex plugin — i.e. BMAD itself is multi-harness by construction. Party mode: separate agents keep reasoning independent ("one model voicing five personas tends to make them agree"). | — | `.claude/skills/bmad-*` (76 here) | verified block last refreshed 2026-09-06 (`99e595cc6a`); the proposed `@AGENTS.md` import was never taken. |

## 2. Findings (adversarial, ranked)

1. **The repo's most important rules are invisible to its most-used harness.** `CLAUDE.md` exists, so Claude
   Code never reads `AGENTS.md`, and `CLAUDE.md` does not import it. The verified block's "no
   `Co-Authored-By`, no AI attribution", "never hand-edit `sprint-status-ledger.yaml`", "never flip a
   `blocked` key" rules therefore bind every harness *except* Claude Code. Evidence: four PRs today
   (#1507, #1511, #1512, #1514) carry `Co-Authored-By` trailers written by a Claude Code session that
   was following the harness's own default. **Fix: one line — `@AGENTS.md` in `CLAUDE.md`** (BMAD's own
   recommendation), then deduplicate what `CLAUDE.md` repeats.
2. **Mirroring the manual into every tool file is the wrong mechanism in 2026.** Copilot's coding agent
   and Devin read *all* of `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` and the `.mdc` rules at once; a
   60-line manual copied into `GEMINI.md` and `copilot-instructions.md` is loaded two or three times
   by those harnesses and turns any later edit into a contradiction (Claude Code docs: "if two rules
   contradict each other, Claude may pick one arbitrarily"). Cursor, Codex, Jules, Devin and Copilot
   already read `AGENTS.md` natively; Gemini needs one settings line; Claude Code needs one import.
   **The parity mechanism is configuration that points at one file, not copies of the file.**
3. **Gemini is the one harness with no path to `AGENTS.md` today** — no `.gemini/settings.json` in the
   repo, none in the operator's home. A checked-in `.gemini/settings.json` with
   `"context": {"fileName": ["AGENTS.md", "GEMINI.md"]}` closes it; `GEMINI.md` stays a thin
   Gemini-only addendum (Gemini also supports `@AGENTS.md` imports as an alternative).
4. **PR #1513's memory section points at files that are not in the repo.** The five cited
   `feedback_*.md` files are one operator's Claude Code auto-memory (`~/.claude/projects/…`); the
   repo's team memory (`.claude/memory/`, scribe CAP-1) holds 10 entries and none of those five.
   Cross-tool memory = `.claude/memory/MEMORY.md` reached through `AGENTS.md`, filled by
   `scribe capture` — the scribe Spec's own mechanism, which the PR bypassed.
5. **Size.** Claude Code's guidance is < 200 lines per instruction file; BMAD's is "only what is
   expensive to rediscover". `AGENTS.md` is 402 lines, `CLAUDE.md` 357, and a Copilot/Devin session
   loads both plus `GEMINI.md`. The 2026 pattern is a short root file + nested `AGENTS.md` per
   component (atlas already has one, 107 lines) + path-scoped rules (`.claude/rules/`,
   `.github/instructions/*.instructions.md` with `applyTo`, `.cursor/rules` globs) + skills for
   procedures. This is a later story, not this PR.
6. **Skills are Claude-pathed.** 76 BMAD + 7 SKF skills live only under `.claude/skills/`; the Agent
   Skills standard is read by Cursor, Codex, Gemini CLI, Copilot (`gh skill`) and Antigravity from their
   own or the neutral `.agents/skills` path. Verify each harness's project-level path, then expose the
   same tree (symlink or `gh skill`-managed install) — future story.
7. **Scribe's inputs are Claude-only.** CAP-17/18 mine `~/.claude/projects/**/*.jsonl`; Cursor, Gemini,
   Copilot and Devin sessions never reach the promote gate. AD-3's schema parity with Claude's
   auto-memory is fine as *storage*; *ingestion* needs one adapter per harness log format — future CAP.
8. **`scribe recall` is unreachable from a cloud agent.** It needs `-e pyforge-scribe`; Copilot's
   `copilot-setup-steps.yml` and Cursor Cloud install `pyforge-guild` only, and a Copilot session has
   59 minutes. Recall through the Guild env or the station MCP (`/stations/scribe/mcp`) — future CAP;
   PRD FR-13 ("queryable by any session, any operator") should read "any harness".
9. **Multi-lane bookkeeping conflicts are structural.** Every parallel landing today conflicts on
   `scripts/.spec-surface-baseline.json` (one JSON for every spec) and on co-governor memlog tails
   (`spec-pyforge-core`). Append-only memlogs union cleanly; the single baseline file does not. A
   per-spec baseline file is the fix (doctor/marshal-owned; recorded here, not built).
10. **Devin and Copilot have first-class analogues of marshal's dispatch that the estate does not use**:
    Devin Playbooks ≈ story-dispatch prompts, MultiDevin ≈ `factory drain`, Devin Repo Setup / machine
    snapshot ≈ the Guild env; Copilot custom agents (`.github/agents/*.agent.md`) ≈ SKF station
    personas; `copilot-setup-steps.yml` already exists. Opportunity, not a defect: the SKF persona
    files could be projected into `.github/agents/` and a Devin Playbook per station.
11. **Checklist hygiene in the PR:** item 9 prescribes `django.apps.apps.get_model` and a path
    (`src/pyforge/<station>/…`) that does not exist — the real invariant is steward
    `tests/meta/test_invariants.py` (no module-level `django`/`channels`/`dashboard` import outside the
    `dashboard/` extra; one sanctioned `importlib` reach); items 10 and 12 duplicate items 5 and 2;
    item 11 is right but must name `pr-preflight`'s known gaps (atlas WASM under `CI=1`, containers,
    herald browser, scribe Postgres) or "exit 0 across all local suites" is unachievable.

## 3. What "optimised for multi-agent, multi-harness" looks like (target state)

- **One contract, discovered natively.** `AGENTS.md` (root, short) is the only place the contract is
  written. Claude Code: `@AGENTS.md` in `CLAUDE.md`. Gemini: `.gemini/settings.json`
  `context.fileName`. Cursor / Codex / Copilot / Devin / Jules: native. VS Code chat:
  `chat.useAgentsMdFile` in `.vscode/settings.json`. Each per-tool file shrinks to tool-specific
  addenda only.
- **A parity gate, not parity copies.** A scribe meta-test asserts: `CLAUDE.md` imports `AGENTS.md`;
  `.gemini/settings.json` lists `AGENTS.md` first; `GEMINI.md`, `copilot-instructions.md` and the
  `.cursor/rules` pointers contain no section that also exists in `AGENTS.md` (duplication is the
  failure); every path/skill named in the pointer files resolves (`governance-currency` already covers
  `AGENTS.md`/`CLAUDE.md`; extend its `DOCUMENTS` to the pointer files).
- **Team memory reaches every harness** through one `AGENTS.md` line ("read `.claude/memory/MEMORY.md`
  at session start; add to it with `scribe capture`"), and team-relevant lessons are promoted with
  `scribe capture` (direct) or `scribe capture --promote` (sweep) — never cited from a home directory.
- **Nested `AGENTS.md` per station package** carrying only that station's expensive-to-rediscover rules
  (atlas is the exemplar); root file under 200 lines.
- **Skills on the neutral path**, one tree, every harness.
- **Scribe ingests every harness's sessions** and **recall is reachable from the Guild env / MCP**.
- **Per-spec surface baselines** so parallel lanes stop colliding on one JSON file.

## 5. How each claim was verified — and what was NOT (honesty table)

| Harness | Verified how | Live-tested here? |
|---|---|---|
| **Claude Code** | Docs + **live**: a fresh `claude -p` session in the PR worktree (with `@AGENTS.md`) quoted the verified block's attribution bullet verbatim; the same prompt in the `main` checkout (no import) answered `NOT LOADED`. | **Yes** (2026-09-19) |
| **Gemini CLI / Antigravity** | Docs only (`context.fileName`, `/memory show`). Not run: it would send the repo's instruction files to the Gemini API on the operator's key. Verify with `gemini` → `/memory show` after merge. | No |
| **Cursor** | Docs only (native `AGENTS.md`, nested, `.mdc`). The `cursor-agent` CLI is installed but the account is out of usage today. | No |
| **GitHub Copilot cloud agent / CLI / VS Code chat** | Docs only. Cloud-agent verification = assign an issue and read the PR's **References**; VS Code = the References list on a chat reply; CLI = `/instructions`. | No |
| **Devin** | Docs only — three pages: `onboard-devin/agents-md` ("Devin will look for the file before it starts coding"), `onboard-devin/knowledge-onboarding` (Knowledge auto-pulls from `.rules`, `.mdc`, `.cursorrules`, `.windsurf`, `CLAUDE.md`, `AGENTS.md` — not general `.md`), `cli/reference/configuration/read-config-from` (Devin CLI imports `AGENTS.md` / `AGENTS.local.md`, `.cursor/rules/*.mdc`, `CLAUDE.md`, `.claude/skills/**/SKILL.md`, `.github/skills/`, MCP configs; project config `.devin/config.json`). **Playbooks are app-native only** ("Create the playbook directly in the web app") — there is no repo-side playbook file; **Repo Setup / machine snapshot** is likewise configured in the app ("just ask Devin to do it"). No Devin session or CLI was available here. | No |
| **Codex / Jules / Zed / Warp / Aider / goose / Windsurf / Amp / Factory** | agents.md's native-support list only. | No |
| **Microsoft Copilot (M365 / Copilot Studio)** | Not a repo-file harness at all: it does not clone or read `AGENTS.md`; BMAD reaches it only through a declarative agent with a knowledge source (the intake gist *Run-BMad-in-Microsoft-Copilot*). Out of scope for a file-discovery mechanism; recorded on the Dream. | n/a |

**What this means for Devin specifically.** Devin is served by this PR in exactly one way: it reads
`AGENTS.md` natively and its Knowledge ingests `AGENTS.md`, `CLAUDE.md`, the `.mdc` rules and the
`.claude/skills/**/SKILL.md` tree — which is *why* the no-duplication rule matters more for Devin than
for anyone (duplicated sections become duplicated, possibly conflicting Knowledge entries). Everything
else Devin needs is **app-side and not in this repo**: a Repo Setup snapshot that runs
`pixi install -e pyforge-guild` (the same lean env `copilot-setup-steps.yml` and Cursor's
`environment.json` install), Knowledge pinned to this repo, and a Playbook per repeatable task (the
natural one: "land one story" — the marshal dispatch prompt's Procedure / Specifications / Forbidden
Actions, e.g. never `bmad-switch`, never commit on the shared checkout, `--merge` only). None of that
was done or claimed here; it is Dream item (10) and needs an operator with a Devin seat.

## 6. Sources (live, 2026-09-19)

- agents.md open format — https://agents.md/
- Claude Code memory docs (AGENTS.md rules, `@import`, 200-line target, `.claude/rules/`) — https://code.claude.com/docs/en/memory
- Gemini CLI context files (`context.fileName`, `@` imports) — https://geminicli.com/docs/cli/gemini-md/
- Cursor rules and AGENTS.md — https://cursor.com/docs/rules
- Copilot coding agent: AGENTS.md support — https://github.blog/changelog/2025-08-28-copilot-coding-agent-now-supports-agents-md-custom-instructions/ ; `.instructions.md` — https://github.blog/changelog/2025-07-23-github-copilot-coding-agent-now-supports-instructions-md-custom-instructions/ ; about the coding agent — https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-coding-agent ; environment (`copilot-setup-steps.yml`) — https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/customize-the-agent-environment ; custom agents — https://docs.github.com/en/copilot/reference/custom-agents-configuration ; VS Code custom instructions — https://code.visualstudio.com/docs/agent-customization/custom-instructions ; Copilot CLI instructions — https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions
- Devin: AGENTS.md — https://docs.devin.ai/onboard-devin/agents-md.md ; Knowledge — https://docs.devin.ai/onboard-devin/knowledge-onboarding.md ; environment — https://docs.devin.ai/onboard-devin/environment.md ; advanced (MultiDevin) — https://docs.devin.ai/work-with-devin/advanced-capabilities.md ; repo setup — https://docs.devin.ai/tutorial-library/repo-setup.md ; index — https://docs.devin.ai/llms.txt
- BMAD-METHOD: project context — https://docs.bmad-method.org/existing-codebases/set-and-maintain-project-context/ ; multi-agent discussions — https://docs.bmad-method.org/customize/run-multi-agent-discussions/ ; repo — https://github.com/bmad-code-org/BMAD-METHOD
- Agent Skills standard and `gh skill` — https://github.blog/changelog/2026-04-16-manage-agent-skills-with-github-cli/ ; https://docs.github.com/en/copilot/concepts/agents/about-agent-skills ; https://code.visualstudio.com/docs/agent-customization/agent-skills

## 7. Addendum — 2026-09-20: Claude Code's built-in `agents-md` mod (2.1.277+)

Verified against the mod's README and source (`anthropics/claude-code` → `mods/agents-md`), the
2026-09-19 MindStudio write-up, and the strings embedded in this host's installed binary
(`~/.local/share/claude/versions/2.1.278`: `AGENTS_NAMES = ["AGENTS.md", ".claude/AGENTS.md"]`,
`CLAUDE_NAMES = ["CLAUDE.md", ".claude/CLAUDE.md", "CLAUDE.local.md"]`, the four mode strings and
the `instructionFiles` / `projectInstructions` keys).

| Fact | Consequence for this repo |
|---|---|
| Shipped in 2.1.277 (2026-09-18); unavailable on Bedrock / Vertex / Foundry. | The `@AGENTS.md` import in `CLAUDE.md` stays the floor. `test_claude_md_imports_agents_md_as_a_bare_line` keeps it. |
| Four modes via `instructionFiles`: `claude-md`, **`claude-md-or-agents-md` (default)**, `claude-md-and-agents-md`, `managed-only`. Legacy key `projectInstructions` (`claude` / `agents-fallback` / `both` / `none`). | — |
| Default mode: a `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md` anywhere from the root down to the cwd "leaves the whole project to the engine, and the plugin stays out." | In this repo the mod does nothing by default — §2's finding F-1 ("Claude Code reads AGENTS.md only through the import") was exactly right for the default mode, and stays right for every runtime below 2.1.277. |
| `claude-md-and-agents-md`: every `AGENTS.md` loads beside `CLAUDE.md`, deduped by path then content — "a file `CLAUDE.md` already `@`-imports … is not loaded a second time"; nested `AGENTS.md` files attach on `Read` of files beneath them. | The only way `src/shared/packages/pyforge-atlas/AGENTS.md` (the atlas child, Story 19.1's Children rule) ever reaches Claude Code. The root import is not double-loaded. This is the mode this repo pins. |
| The option is read from `~/.claude/settings.json`, `--settings`, or managed settings — "Project's `.claude/settings.json` is not read for plugin options." | The pin cannot live in the repo. Operators: user settings (`/config` → "Project instructions"). Dispatched sessions: marshal's claude harness profile passes it via `--settings` (Story 46.11, `spec-pyforge-marshal:CAP-262`). `scripts/claude_instruction_mode_check.py` (runtime scope) warns when the host is below 2.1.277 or not pinned. |
| Known limits (README): nested files attach on text `Read` only; not restored after compaction; `--add-dir` directories contribute no `AGENTS.md`; `@` imports outside the working directory need the same approval as `CLAUDE.md`'s. | Documented in `AGENTS.md`'s Claude Code row; no repo change. |

**Decisions (operator, 09:35Z–09:50Z):** keep `CLAUDE.md` (import vehicle + Claude-only addenda such as 46.8's "Interactive session path"); pin `claude-md-and-agents-md` for every Claude runtime we drive; state version + mode in the harness table; collapse the one duplicate the H2 guard missed (`CLAUDE.md` "Behavioral Guidelines" ↔ `AGENTS.md` "Behavioural guidelines (every harness)") and make the guard compare normalised headings; repoint `.claude/settings.json`'s `customInstructions` at `AGENTS.md`. → `spec-pyforge-scribe` CAP-29 / Story 19.3; `spec-pyforge-marshal:CAP-262` / Story 46.11.
