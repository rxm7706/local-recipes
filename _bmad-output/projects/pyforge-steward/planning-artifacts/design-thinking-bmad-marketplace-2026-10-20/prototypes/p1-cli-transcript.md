# P1 — Marketplace CLI, paper prototype (terminal transcript)

> **ILLUSTRATIVE / MOCK OUTPUT.** Nothing below has been run. Commands, versions, URLs, hosts
> (`github.example.com`, `artifactory.example.com`) and checksums are sample data for testing the design.

## CLI name decision: `bmp` (standalone), sharing the engine with `steward catalog`

- **Why not just extend `steward catalog`:** today the command is
  `pixi run -e pyforge-steward pyforge steward catalog …`. Teammates would need the pixi env and
  `pyforge-steward`, which pulls in Django and is the estate's provisioner (keys, deploy, suite install).
  That's too heavy and too estate-specific for someone who only wants to install a skill.
- **What we keep:** `catalog.py`'s engine. It needs only `yaml` plus four steward-internal imports
  (`bootstrap.repo_root`, `frames.preflight_frames`, `interfaces.DutyResult`, `suite.*`), so it can move into a
  small library both commands use. `steward catalog check|render|ship` stays the **maintainer/CI face** on
  rxm7706's estate; `bmp` is the **teammate face** (find, install, create, publish).
- **Name:** `bmp` = "BMAD marketplace". Short and pip/conda-installable. *Open: check it doesn't collide with an
  internal tool; the storyboard's `mp` is too generic.*

Install the CLI itself (either source):
```console
$ pip install bmp --index-url https://artifactory.example.com/api/pypi/pypi-internal/simple
$ conda install -c https://artifactory.example.com/api/conda/conda-internal bmp
```

---

## 1. Configure sources (once per machine)

```console
$ bmp source list
NAME         KIND        URL                                                         DEFAULT
github       gh-release  https://github.example.com/team/bmad-marketplace             yes
artifactory  conda       https://artifactory.example.com/api/conda/conda-internal    no

$ bmp source default artifactory
Default install source: artifactory  (written to ~/.config/bmp/config.toml)
```
*Open: does the index itself come from Pages (`https://pages.example.com/bmad-marketplace/index.json`) or from the
git repo? Prototype assumes Pages JSON, falling back to a git clone.*

## 2. Find — task-based search

```console
$ bmp search "lock our conda and pip env"
Index: pages.example.com/bmad-marketplace (refreshed 2026-10-20 18:55 CDT, 41 listings)

  @mason/environment     skill   1.2.0   estate-reviewed  verified 2026-10-19
      Lock mixed conda + pip requirements into one lockfile and check it isn't stale.
      tasks: lock-env, check-env-drift
  @mason/package         skill   0.9.1   estate-reviewed  verified 2026-10-19
      Build wheel, sdist and conda packages from one manifest and ship to Artifactory.
  @dana/artifactory-auth skill   0.1.0   community        verified 2026-10-20
      Fix "401 from Artifactory conda channel" by refreshing the token in .condarc / pip.conf.

3 results. `bmp info <name>` for details.
```

## 3. Info

```console
$ bmp info @mason/environment
@mason/environment 1.2.0 — skill (instructions + code-backed lane)
  Lock mixed conda + pip requirements into one lockfile and check it isn't stale.
  Owners:     @rxm7706 (mason)          Trust: estate-reviewed (review #14, 2026-10-18)
  Verified:   2026-10-19 clean-machine CI ✓ linux-64, osx-arm64 · ✗ win-64 not tested
  Requires:   python >=3.10, pyforge-mason >=0.2 (installed with the skill from the same source)
  Installs:   .agents/skills/mason-environment/   .claude/skills/mason-environment/
  Card:       https://pages.example.com/bmad-marketplace/skills/mason/environment/
  Sources:    github      gh-release  mason-environment-1.2.0.zip  sha256:3f1c…a9
              artifactory conda       conda-internal::bmp-skill-mason-environment==1.2.0
              artifactory pip         bmp-skill-mason-environment==1.2.0
  Bundles:    python-env-starter, new-hire-pack
```

## 4. Install a skill (both sources shown)

```console
$ bmp install @mason/environment --source github
Resolving @mason/environment 1.2.0 from github (gh-release)…
  ↓ mason-environment-1.2.0.zip  48 KB  sha256 ✓
  ✓ requires: python 3.12 ✓  pyforge-mason missing → installing pyforge-mason 0.2.3 (pip, github wheel) ✓
Wrote:
  .agents/skills/mason-environment/SKILL.md          (+ scripts/, references/)
  .claude/skills/mason-environment/SKILL.md          (copy; symlink with --link)
  skills.lock                                         (+1 entry)
Readable for: Cursor, Copilot, Devin, Gemini CLI, Codex (.agents/skills) · Claude Code, Cursor, Copilot (.claude/skills)
Try it: ask your AI tool "lock this project's environment", or read the steps: bmp steps @mason/environment

$ bmp install @mason/environment --source artifactory      # same result, different bytes source
Resolving @mason/environment 1.2.0 from artifactory (conda)…
  ↓ conda-internal::bmp-skill-mason-environment-1.2.0-noarch  sha256 ✓ (matches github release)
…same files written…
```
*Open: copy vs symlink into `.claude/skills` (symlinks on Windows; does each tool follow them?). Commit
`.agents/skills` to the project repo or gitignore it and rely on `skills.lock` + `bmp sync`?*

`skills.lock` (project root):
```yaml
# generated by bmp — commit this; `bmp sync` reproduces the set
lock_version: 1
index: https://pages.example.com/bmad-marketplace/index.json
skills:
  "@mason/environment":
    version: 1.2.0
    source: artifactory:conda
    sha256: 3f1c…a9
    targets: [.agents/skills/mason-environment, .claude/skills/mason-environment]
```

## 5. Install an agent (requires checks + generated adapters)

```console
$ bmp install @scribe/agent
Resolving @scribe/agent 0.3.0 — agent (BMAD-built persona)…
Checking requires:
  ✓ python >=3.10
  ✓ pyforge-scribe CLI  → will install pyforge-scribe 0.4.0 (artifactory pip)
  ! scribe station MCP server  NOT REACHABLE (http://localhost:8000/stations/scribe/mcp)
      optional: agent runs in "CLI-only" mode; recall works, live fleet views disabled
  ✗ _bmad/ project folder  not found
      → run `bmp init --bmad` to create a minimal _bmad/ (config only), or use --no-bmad (persona without customize.toml merge)
Continue with CLI-only mode and create _bmad/? [y/N] y
Wrote:
  .agents/skills/scribe-agent/SKILL.md                 persona-as-skill (works in all 6 tools)
  .claude/skills/scribe-agent/SKILL.md
  Adapters (generated from the same persona):
    .claude/agents/scribe.md                           Claude Code subagent      (format: unconfirmed path, see matrix)
    .cursor/agents/scribe.md                           Cursor subagent           ✓ confirmed
    .github/agents/scribe.agent.md                     Copilot custom agent      ✓ confirmed
    .gemini/agents/scribe.md                           Gemini CLI subagent       ✓ confirmed
    .codex/agents/scribe.toml                          Codex subagent            ✓ confirmed
    Devin: no repo-local agent file; agent ships as the skill (plugin agents are CLI/Desktop-only) — skipped
  _bmad/config.toml  (minimal)
  skills.lock  (+1 entry, mode: cli-only)
```
*Open: do adapters add value over the persona skill alone (all six read the skill)? Is "CLI-only mode" an honest
degraded mode for every station agent, or does it need per-agent design?*

## 6. Outdated / update

```console
$ bmp outdated
NAME                 LOCKED   LATEST   NOTE
@mason/environment   1.2.0    1.3.0    changelog: adds `check --strict`; re-verified 2026-10-27
@scribe/agent        0.3.0    0.3.0    —

$ bmp update @mason/environment
Updated @mason/environment 1.2.0 → 1.3.0 (artifactory:conda) · skills.lock updated
Local edits detected in .agents/skills/mason-environment/SKILL.md → kept as SKILL.md.local, review with `bmp diff`
```

## 7. Uninstall

```console
$ bmp uninstall @scribe/agent
Removed .agents/skills/scribe-agent, .claude/skills/scribe-agent, 4 adapter files; skills.lock updated.
Kept pyforge-scribe (installed as a dependency; remove with --deps). Kept _bmad/ (shared).
```

## 8. Create — scaffold via bmad-builder

```console
$ bmp new skill @dana/artifactory-auth
Scaffolding with bmad-builder (bmad-workflow-builder)…
  ✓ skills/dana/artifactory-auth/SKILL.md        frontmatter: name, description, tasks, owners
  ✓ skills/dana/artifactory-auth/steps.md        human-readable runbook (renders on the Pages card)
  ✓ skills/dana/artifactory-auth/listing.yaml    index entry (P2 schema), lane: instructions-only
Next: edit, then `bmp lint` and `bmp publish`.

$ bmp new agent @dana/release-captain
Scaffolding with bmad-builder (bmad-agent-builder)…
  ✓ agents/dana/release-captain/SKILL.md          persona-as-skill
  ✓ agents/dana/release-captain/customize.toml    BMAD agent menu
  ✓ agents/dana/release-captain/listing.yaml      kind: agent, requires: [], adapters: auto
```
*Open: does `new` need the full BMAD install (bmad-builder) on the teammate's machine, or a thin template that
bmad-builder also produces?*

## 9. Capture — "skillify this session"

Inside any AI tool, with `@bmp/skillify` installed (itself a skill), the teammate says:
"turn what we just did into a skill". The skill writes a draft, then calls the CLI:

```console
$ bmp new skill @dana/artifactory-auth --from-session ./.bmp/session-notes.md
Drafted from session notes (12 steps → 6 after merge):
  1. Detect 401 from conda channel   2. Read token expiry   3. Refresh token via `jf` CLI
  4. Rewrite ~/.condarc channel_alias   5. Mirror to pip.conf   6. Verify with `conda search -c …`
Redacted: 1 token-like string, 2 internal hostnames → placeholders
Review skills/dana/artifactory-auth/SKILL.md before publishing.
```
*Open: which tools can export a session transcript? Prototype assumes the AI writes the notes file itself.*

## 10. Publish — PR + lint + clean-machine CI

```console
$ bmp lint skills/dana/artifactory-auth
  ✓ frontmatter (name matches folder, description, owners)
  ✓ no absolute or local-recipes paths      ✓ no secrets (gitleaks)      ✓ license: MIT
  ✓ size 6 KB (< 200 KB)                    ✓ steps.md present
  lane: instructions-only (no scripts/) → fast lane

$ bmp publish skills/dana/artifactory-auth
Pushed branch dana/artifactory-auth-0.1.0 to github.example.com/team/bmad-marketplace
Opened PR #57 "Add @dana/artifactory-auth 0.1.0" → https://github.example.com/team/bmad-marketplace/pull/57
Checks:
  ✓ lint                         12s
  ✓ clean-machine (linux-64)     1m48s  installed via bmp, SKILL.md parsed by 6 tool loaders
  ◌ clean-machine (win-64)       queued
  ◌ review: CODEOWNERS @rxm7706 (mason area)   requested
On merge: listed as community · release zip + Artifactory package built from the same tag
Promotion to estate-reviewed: reviewer runs `bmp review approve @dana/artifactory-auth` (writes reviews/…yaml)
```
*Open: "parsed by 6 tool loaders" — which tools offer a headless check? Without one, CI can only lint the
format and run the scripts.*
