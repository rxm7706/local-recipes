# Round 0 desk test — 2026-10-29

The Round 0 desk test of `docs/foundry/marketplace/MANUAL-CHECKLIST.md`, recorded per tool. This file holds the
Claude Code leg, run on 2026-10-29 by an agent session on the operator's machine. The other tools (Cursor, GitHub
Copilot in VS Code, Google Gemini CLI, Devin, Codex, and no AI tool) are the operator's to run and add here, one
section each. The Wizard-of-Oz pilot (P4) has not started.

## Claude Code leg

### Setup

| Item | Value |
|---|---|
| Tool | Claude Code `2.1.311`, driven non-interactively with `claude -p`, session persistence off |
| Skill | `@warden/scan`, folder `docs/foundry/marketplace/skills/warden/scan/` |
| Marketplace source | `main` at `cb601ac369` (the PR #2274 merge) |
| Projects | Three scratch git repositories outside any local-recipes checkout, each a minimal Python project with a `pyproject.toml` and one module |

The three scratch projects:

- `proj-both`: the folder copied into `.claude/skills/warden-scan/` and `.agents/skills/warden-scan/`.
- `proj-agents-only`: the folder in `.agents/skills/warden-scan/` only.
- `proj-plugin`: no folder copy; the plugin install path instead.

Skill visibility was read from the `skills` list of the `system/init` event of `claude -p --output-format
stream-json --verbose`, not from a model's answer. The same project with no skill copied listed 116 skills.

### Checklist rows

- [x] **Read the index and open one card.** Read live at `/marketplace/` rather than `site/`, so no local server was
  needed. The index links the three cards; all three return 200. The `@warden/scan` card's sections run Install,
  Unpublished packages, Steps, Related, Sources, Contribute. All six links on the card resolve: the index, the two
  sibling cards, and the README, `MANUAL-CHECKLIST.md` and the tool matrix on github.com at the deployed commit
  `cb601ac369`. The mounted `skills/warden/scan/{SKILL.md,steps.md,listing.yaml}` and the `pages-site` release's
  `warden-scan.zip` and `.sha256` are present.
- [x] **Copy the folder into both directories.** Done in `proj-both`, from a checkout at `main`. The copies are
  byte-identical to the source. The zip path was not exercised.
- [x] **The tool picks the folder up.** Claude Code lists `warden-scan` from `.claude/skills/` (117 skills against the
  116 baseline). From `.agents/skills/` alone it lists nothing (`proj-agents-only`: 116, no `warden-scan`). Matrix
  outcome: `tool: Claude Code — Driveable: yes`. The README's and the matrix's "reads `.agents/skills/`: uncertain"
  cell for Claude Code is, on 2.1.311: **not read**. The copy into both directories stays the install rule, because
  the other tools read `.agents/skills/`.
- [x] **Claude Code plugin path.** Run as the non-interactive equivalents of the `/plugin` commands, at local scope in
  `proj-plugin`:
  - `claude plugin marketplace add <checkout>/docs/foundry/marketplace --scope local` returned ok, marketplace
    `pyforge-bmad-marketplace`.
  - `claude plugin install warden-scan@pyforge-bmad-marketplace --scope local` returned ok.
  - The skill **appears**, as `warden-scan:warden-scan` (namespaced by plugin). `claude plugin details` shows one
    skill, about 115 always-on tokens, read from the folder itself.
  - The plugin install therefore exposes the skill, and `.claude-plugin/marketplace.json` is more than a discovery
    pointer for Claude Code. Afterwards the plugin was uninstalled, the marketplace removed and the plugin cache
    directory deleted; `installed_plugins.json` and `known_marketplaces.json` are identical to their state before the
    test.
- [ ] **Codex only.** Not run in this leg; the operator's.
- [x] **Follow `steps.md` from the top** (`proj-both`):
  - *Before you start* holds today. `pyforge-warden` and `pyforge-core` return 404 on PyPI, conda-forge and
    SelfExplainML (re-checked 2026-10-29).
  - *Step 0* was **not run as written**. The session's pre-shell hook refuses ad hoc `pip` and `conda` installs, so the
    two tools came from an existing environment on the host, standing in for the teammate's install. Published
    versions on 2026-10-29: `deptry` 0.25.1 on PyPI and conda-forge, matching the runbook; `osv-scanner` 2.7.0 on
    conda-forge, where the runbook verified 2.4.0.
  - *Step 1* **stopped** on the unpublished package. With a teammate's `PATH`, `warden` and `pyforge` are not found, and
    `warden scan .` exits 127.
  - *Step 2* ran: `deptry 0.25.1` and `osv-scanner version: 2.4.0` (the stand-in binaries), both exit 0.
  - *Step 3*: stop.
- [x] **Which step ran, which stopped.** Steps 0 (stand-in) and 2 ran. Step 1 stopped because `pyforge-warden` (and
  `pyforge-core` for `pyforge warden`) is unpublished.
- [x] **A tool that cannot be driven.** Not applicable; Claude Code was driveable.
- [x] **No step asked for `pixi run -e` or a path inside local-recipes.** `steps.md` names neither. `SKILL.md` names
  local-recipes only as a prohibition; see observation 3.
- [x] **The card's unpublished-package list matches what the desk test hit.** The card lists `pyforge-warden` and
  `pyforge-core`. Step 1 stopped on `warden` (`pyforge-warden`) and on `pyforge` (`pyforge-core`'s dispatch).

### Driving the skill through the tool

In `proj-both`, Claude Code was asked "I want to scan this project for dependency hygiene the way our team does it.
What can I run today?", with shell and edit tools disabled. It invoked the `warden-scan` skill unprompted, read
`steps.md`, and answered correctly:

- `warden scan .` (or `pyforge warden scan .`) is the command, and it cannot run yet.
- Only the two `--version` probes run today.
- The install commands for the two tools.
- Probe output is not a warden verdict.

### Observations for the pilot

1. **The card's Sources block contradicts the release.** It reads "GitHub release: not published", while the
   `pages-site` release carries `warden-scan.zip` and its checksum, and the card's own Install section says so. This
   is `DW-steward-109-3-4`; a teammate would hit it.
2. **The verified version has drifted.** `osv-scanner` is 2.7.0 on conda-forge against the runbook's verified 2.4.0.
   The runbook pins what it verified, so a fresh install gets a newer version than the one named.
3. **Estate wording reaches the teammate.** The skill's guard "no path inside local-recipes" surfaced in Claude Code's
   answer as "no `cd` into local-recipes". A teammate in their own repository has no local-recipes. The guard is for
   the estate's agents; the teammate-facing text could say "run from your project directory" alone.
4. **The README, the tool matrix and the cards.** This leg's results moved the README's tool table and plugin
   paragraph and the matrix's Claude Code row (the same pull request as this record). The skill cards' Install
   section and the catalog's `github_note` still say the matrix marks `.agents/skills/` as uncertain for Claude
   Code and that `marketplace.json` is a discovery pointer until Round 0; that text is generated by
   `pyforge.steward.marketplace_pages` and `pyforge.steward.catalog` and is not changed here.
5. **Plugin and folder copy side by side.** With both installed, the skill would likely appear twice (`warden-scan`
   and `warden-scan:warden-scan`). This leg did not test that; the pilot should say which one teammates use.

### Not covered by this leg

- The zip-and-checksum install path (`sha256sum -c … && unzip … -d .claude/skills/`).
- An interactive `/plugin` and `/skills` session; the CLI verbs were used instead.
- A single copy in `.agents/skills/` with a symlink from `.claude/skills/`.
- The other two skills.
- A real `pip` or `conda` install for step 0.
